"""
Mounting the MCP server on the web app.

WHY IT LIVES IN app/ AND NOT src/. `src/mcp_server.py` is the tool
surface and knows nothing about HTTP. Two things it needs are the web
process's own: the job registry in `app/jobs.py` (a thread registry
belonging to this process) and the transport. They are handed to it as
callables rather than imported by it, because `src/` never imports
`app/` -- the same injection `scene_chain` uses for the two app-layer
capabilities it needs.

THE POSTURE. Mounting is off unless ZEROPAGE_MCP=1, and a mount with no
ZEROPAGE_MCP_TOKEN is REFUSED rather than served open. That refusal is
the whole point of this module: the reason to mount MCP at all is to
reach it from off the machine, which means the endpoint is on the public
internet the moment it works. An "I'll add auth later" default here
writes scenes and projects and -- behind its approvals -- spends credits,
for anyone who finds the URL. So it fails loudly and stays unmounted.

The token is compared with `hmac.compare_digest`, not `==`, and the
check happens before the MCP app is ever entered, so an unauthenticated
caller cannot open a session or enumerate the tool list.
"""
from __future__ import annotations

import asyncio
import hmac
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional

from src import mcp_server

ENABLED_ENV = "ZEROPAGE_MCP"
TOKEN_ENV = "ZEROPAGE_MCP_TOKEN"
HOSTS_ENV = "ZEROPAGE_MCP_HOSTS"
MOUNT_PATH = "/mcp"
# The Claude directory's listing (2026-10-11): /mcp/claude, the listed
# server with nothing that renders. Same mount, same guard, same OAuth
# door; only the server a signed-in caller reaches differs.
CLAUDE_PATH = "/claude"

# --- the rate limit (2026-10-07, for the directory listing) -----------------
#
# Requests per RATE_WINDOW_S, keyed on WHO is calling once the guard has
# decided that: one bucket per signed-in account, one for the operator's
# static key. A fixed window rather than a token bucket because the
# question it answers is coarse -- "is one caller hammering a server that
# serves everybody" -- and a fixed window is the shape a person can read
# off a 429 (`Retry-After` says when the window turns over).
#
# IN-PROCESS, AND THAT IS A STATED LIMIT: the API is one Fly machine
# (fly.toml: min_machines_running = 1, one shared CPU), so one dict in
# this process IS the whole count. A second machine would mean two
# counters that each allow the full limit; the day that happens this
# moves to a shared store (Postgres is already there), and this comment
# is the reminder. The counts die with a deploy, which is fine: the limit
# protects the process that holds them.
#
# The operator's key is subject to it too, at a higher default, because
# an agent or an ops/ script polls `job` in a loop and must not be
# throttled like a stranger -- but an operator key leaked to a stranger
# must not be unlimited either.
RATE_ENV = "ZEROPAGE_MCP_RATE"                  # per account, per window
RATE_OPERATOR_ENV = "ZEROPAGE_MCP_RATE_OPERATOR"  # the static key
RATE_WINDOW_S = 60
DEFAULT_RATE = 120
DEFAULT_RATE_OPERATOR = 1200


def _rate(env: str, default: int) -> int:
    """Read once per request so an operator can tune it without a
    restart being the only way to find out it was set wrongly. 0 or
    garbage means the default, never "unlimited": a typo must not open
    the door."""
    raw = (os.environ.get(env) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


class RateLimiter:
    """Fixed-window counter, one window per key, safe across the threads
    uvicorn and the job registry share. `clock` is injected so a test can
    turn the window over without sleeping."""

    def __init__(self, window_s: float = RATE_WINDOW_S,
                 clock: Callable[[], float] = time.monotonic):
        self.window_s = float(window_s)
        self.clock = clock
        self._lock = threading.Lock()
        self._windows: dict = {}        # key -> [window_start, count]

    def allow(self, key, limit: int) -> tuple[bool, int]:
        """(allowed, retry_after_seconds). retry_after is 0 when allowed."""
        now = self.clock()
        with self._lock:
            start, count = self._windows.get(key, (now, 0))
            if now - start >= self.window_s:
                start, count = now, 0
            if count >= limit:
                self._windows[key] = [start, count]
                return False, max(1, int(self.window_s - (now - start)) + 1)
            self._windows[key] = [start, count + 1]
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


LIMITER = RateLimiter()


# --- "last used", for the account menus' Connect to Claude panel ----------
#
# A request through the listed door says this person's connection works,
# and src/mcp_connections.touch writes that down. At most once per person
# per account per USE_STAMP_WINDOW_S: a connector polls `job` in a loop,
# and a database write per MCP call to keep one line of a panel fresh
# would be the wrong trade. In-process for the rate limiter's reason (one
# Fly machine); a deploy forgets the memo and the next call stamps again.
USE_STAMP_WINDOW_S = 600


class UseStamps:
    """Which (account, person) pairs are due a stamp. `due` answers True
    once per window per key and records the answer whether or not the
    write that follows succeeds: a database that is down is asked again
    next window, not on every call."""

    def __init__(self, window_s: float = USE_STAMP_WINDOW_S,
                 clock: Callable[[], float] = time.monotonic):
        self.window_s = float(window_s)
        self.clock = clock
        self._lock = threading.Lock()
        self._last: dict = {}           # key -> when it was last stamped

    def due(self, key) -> bool:
        now = self.clock()
        with self._lock:
            last = self._last.get(key)
            if last is not None and now - last < self.window_s:
                return False
            self._last[key] = now
            return True

    def reset(self) -> None:
        with self._lock:
            self._last.clear()


USE_STAMPS = UseStamps()


def _token_subject(token: str) -> str:
    """The person a token names. Read WITHOUT verifying, and only ever
    after `resolve` has verified the same token -- this is a label for
    the stamp, never a decision about access."""
    import jwt
    try:
        return str(jwt.decode(token, options={"verify_signature": False}).get("sub") or "")
    except jwt.PyJWTError:
        return ""


async def _stamp_use(account_id: int, token: str, stamp, stamps: UseStamps) -> None:
    """Best-effort, and never the request's problem: a failed write is
    logged and the call goes on to the MCP app exactly as before."""
    user_id = _token_subject(token)
    if not user_id or not stamps.due((int(account_id), user_id)):
        return
    try:
        await asyncio.to_thread(stamp, int(account_id), user_id)
    except Exception as exc:  # noqa: BLE001 -- see docstring
        print(f"[mcp] could not stamp the connection's last use: {exc}", file=sys.stderr)

# The SDK refuses any request whose Host header it does not recognise --
# DNS-rebinding protection, which defends a localhost server against a
# malicious page in the operator's own browser. Behind a tunnel the Host
# is the tunnel's hostname, so the default list 421s every real call
# with "Invalid Host header", which reads like a broken server rather
# than a setting. Hence ZEROPAGE_MCP_HOSTS.
DEFAULT_HOSTS = ("127.0.0.1", "127.0.0.1:8000", "localhost", "localhost:8000")


def allowed_hosts() -> list[str]:
    """Hosts this endpoint answers to. `*` disables the check, which is
    the right setting behind a quick tunnel whose hostname changes on
    every restart: the attack rebinding protection exists to stop is a
    browser reaching a localhost server, and a browser cannot supply the
    bearer token that `guarded` demands before the MCP app is entered.
    A NAMED tunnel has a stable hostname -- list it instead.

    The host of the published resource (`ZEROPAGE_MCP_RESOURCE`) is always
    allowed: a server that refused the very address its own OAuth metadata
    names would 421 every connector call, and that address moving (it did,
    fly.dev -> api.zeropage.studio, 2026-10-11) must not depend on a Fly
    secret being edited in step.
    """
    extra = [h.strip() for h in os.environ.get(HOSTS_ENV, "").split(",") if h.strip()]
    if "*" in extra:
        return extra
    hosts = list(DEFAULT_HOSTS) + extra
    for h in _resource_hosts():
        if h not in hosts:
            hosts.append(h)
    return hosts


def _resource_hosts() -> list[str]:
    """`host` and `host:port` of ZEROPAGE_MCP_RESOURCE, or nothing."""
    from urllib.parse import urlparse

    raw = (os.environ.get("ZEROPAGE_MCP_RESOURCE") or "").strip()
    if not raw:
        return []
    try:
        parsed = urlparse(raw)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return []
    if not host:
        return []
    out = [host]
    if port:
        out.append(f"{host}:{port}")
    else:
        out.append(f"{host}:{443 if parsed.scheme == 'https' else 80}")
    return out


def enabled() -> bool:
    return os.environ.get(ENABLED_ENV) == "1"


def token() -> str:
    return os.environ.get(TOKEN_ENV, "")


def _unauthorized(detail: str, error: str = "unauthorized", suffix: str = ""):
    from starlette.responses import JSONResponse

    from . import mcp_auth

    # The challenge names the metadata document when there is an
    # authorization server to discover; a bare "Bearer" otherwise, which
    # is the honest answer on a deployment with no Supabase configured.
    # `suffix` names the Claude listing's own document when that is the
    # path the caller asked for.
    challenge = mcp_auth.challenge(suffix) if mcp_auth.configured() else "Bearer"
    return JSONResponse({"error": error, "detail": detail},
                        status_code=401,
                        headers={"WWW-Authenticate": challenge})


def _forbidden(detail: str):
    from starlette.responses import JSONResponse

    return JSONResponse({"error": "no_account", "detail": detail}, status_code=403)


# Where a person with no workspace is sent (2026-10-07, Mike's call: one
# web sign-in first, which creates the workspace; the connector never
# creates one). Overridable because the studio's public origin is not
# this one.
SIGNUP_ENV = "ZEROPAGE_SIGNUP_URL"
# The sign-up door itself, not the homepage (2026-10-11): the site proxies
# /signin to the API, and mode=signup asks for the sign-up heading. The first
# pass through it creates the workspace and grants the trial credits.
DEFAULT_SIGNUP_URL = "https://zeropage.studio/signin?mode=signup"


def no_account_detail() -> str:
    url = (os.environ.get(SIGNUP_ENV) or "").strip() or DEFAULT_SIGNUP_URL
    return (f"this sign-in has no workspace yet -- sign in once at {url} "
            "(your workspace is created on the first sign-in), then reconnect")


class Sessions:
    """The session managers of both servers, entered together.

    The app's lifespan (and the tests) enter ONE `run()`; two servers mean
    two managers, so this is the one thing they enter. Each manager can
    be run once per instance, which `run()` keeps true by entering both
    exactly once."""

    def __init__(self, *managers):
        self.managers = [m for m in managers if m is not None]

    @asynccontextmanager
    async def run(self):
        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            for manager in self.managers:
                await stack.enter_async_context(manager.run())
            yield


def _too_many(retry_after: int, limit: int):
    from starlette.responses import JSONResponse

    # The detail says the window, so an agent that reads it stops rather
    # than retrying the identical call inside the same window.
    return JSONResponse(
        {"error": "rate_limited",
         "detail": f"over {limit} requests in {RATE_WINDOW_S}s -- wait "
                   f"{retry_after}s before calling again"},
        status_code=429,
        headers={"Retry-After": str(retry_after)})


def _sub_path(scope) -> str:
    """The path below the mount, the way Starlette's router reads it."""
    path = scope.get("path") or ""
    root = scope.get("root_path") or ""
    return path[len(root):] if root and path.startswith(root) else path


def _is_claude(scope) -> bool:
    sub = _sub_path(scope)
    return sub == CLAUDE_PATH or sub.startswith(CLAUDE_PATH + "/")


def _into_claude(scope) -> dict:
    """The same request, with the Claude sub-path moved into root_path so
    the SDK app (served at "/") routes it as its own root."""
    return {**scope, "root_path": (scope.get("root_path") or "") + CLAUDE_PATH}


def guarded(app, secret: str, resolve=None, limiter: Optional[RateLimiter] = None,
            listed_app=None, stamp=None, stamps: Optional[UseStamps] = None,
            claude_app=None):
    """Wrap an ASGI app so every request names a caller.

    A plain ASGI wrapper rather than middleware on the parent app: the
    check must not apply to /ui or /api (which have their own cookie
    session), and it must apply to every method and path under the
    mount, including the ones the transport adds itself.

    TWO DOORS, and which one a caller came through decides whose board
    they read (see app/mcp_auth.py):

    - The static token -- the operator's own key, compared with
      `hmac.compare_digest` rather than `==`, before the MCP app is ever
      entered, so an unauthenticated caller cannot open a session or
      enumerate the tool list. It acts as the bootstrap account, exactly
      as it did before OAuth existed.
    - Anything else is offered to `resolve`, which verifies it as a
      Supabase access token and answers with the caller's OWN account
      id. That id is put on `mcp_server.CALLER_ACCOUNT` for the length of
      this request and reset in a `finally` -- a leaked value here is
      one caller reading another's board, so it is never left set.

    `resolve` is injected (defaulting to `mcp_auth.account_for_token`)
    for the reason the whole mount is injected: this module is the seam
    where app-layer capability meets `src/`, and a test that has to mint
    a real Supabase JWT to exercise the guard is a test nobody writes.

    THE RATE LIMIT SITS AFTER THE IDENTITY CHECK, on purpose: the key is
    who the caller turned out to be, and an unauthenticated request is
    already refused by the cheaper check above it. `limiter` is injected
    the same way `resolve` is (default: the module's one `LIMITER`).

    TWO SERVERS, ROUTED BY DOOR (2026-10-07, Mike's call). The static key
    reaches `app` -- the STUDIO surface since 2026-10-11, when the board
    surface it used to reach was removed (docs/tasks/task-higgsfield-shape.md);
    a signed-in person reaches `listed_app`, the server built with
    `mcp_server.LISTED_TOOLS` only -- projects, elements, and the scene
    path (write_scene / quote / approve), with none of the studio's
    spending doors. Registration is per server, not per request, so hiding
    tools from one door means a second server, not a filter. With no
    `listed_app` (a test that builds one app) everybody reaches `app`.

    THE CLAUDE PATH (2026-10-11). A request under /mcp/claude reaches
    `claude_app` -- the listed server with nothing that renders, for the
    Claude directory -- whichever door it came through, so the operator
    can test exactly what a reviewer sees. Its 401 names the Claude
    listing's own metadata document. With no `claude_app` the path is
    not served (404).

    A SIGNED-IN CALL IS STAMPED as the person's connection's last use
    (`stamp`, default `mcp_connections.touch`), throttled by `stamps` --
    the studio's "Connected to Claude" line. The operator's key is not a
    connection anybody made and stamps nothing.
    """
    if resolve is None:
        from .mcp_auth import account_for_token as resolve
    if limiter is None:
        limiter = LIMITER
    if stamp is None:
        from src.mcp_connections import touch as stamp
    if stamps is None:
        stamps = USE_STAMPS

    from src import mcp_server

    async def wrapper(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        claude = _is_claude(scope)
        suffix = CLAUDE_PATH if claude else ""
        if claude and claude_app is None:
            from starlette.responses import JSONResponse
            response = JSONResponse({"error": "not_found"}, status_code=404)
            return await response(scope, receive, send)
        header = ""
        for key, value in scope.get("headers") or []:
            if key == b"authorization":
                header = value.decode("latin-1")
                break
        prefix = "Bearer "
        supplied = header[len(prefix):] if header.startswith(prefix) else ""
        if not supplied:
            response = _unauthorized("send Authorization: Bearer <token>", suffix=suffix)
            return await response(scope, receive, send)
        if hmac.compare_digest(supplied, secret):
            # The operator's own key: no caller is named, so
            # mcp_server._account falls through to the bootstrap account.
            limit = _rate(RATE_OPERATOR_ENV, DEFAULT_RATE_OPERATOR)
            ok, retry_after = limiter.allow(("operator",), limit)
            if not ok:
                response = _too_many(retry_after, limit)
                return await response(scope, receive, send)
            if claude:
                return await claude_app(_into_claude(scope), receive, send)
            return await app(scope, receive, send)
        account_id, reason = resolve(supplied)
        if reason == "no_account":
            response = _forbidden(no_account_detail())
            return await response(scope, receive, send)
        if account_id is None:
            response = _unauthorized("token not accepted", error="invalid_token",
                                     suffix=suffix)
            return await response(scope, receive, send)
        limit = _rate(RATE_ENV, DEFAULT_RATE)
        ok, retry_after = limiter.allow(("account", int(account_id)), limit)
        if not ok:
            response = _too_many(retry_after, limit)
            return await response(scope, receive, send)
        await _stamp_use(account_id, supplied, stamp, stamps)
        token = mcp_server.CALLER_ACCOUNT.set(account_id)
        # ...and the PERSON (2026-10-11): the token's subject, a label the
        # tools that bind something to one person read (`upload_link`
        # mints a page for this account AND this person). Read off the
        # token `resolve` just verified, the way the use stamp reads it.
        person = mcp_server.CALLER_USER.set(_token_subject(supplied) or None)
        try:
            if claude:
                return await claude_app(_into_claude(scope), receive, send)
            return await (listed_app or app)(scope, receive, send)
        finally:
            mcp_server.CALLER_USER.reset(person)
            mcp_server.CALLER_ACCOUNT.reset(token)

    return wrapper


def connector_element(create):
    """app/api.py's `create_element` as the connector's `add_element`
    calls it: ONE picture, already fetched and checked, saved through the
    Elements page's own body. It never draws a sheet (`sheet=False`: a
    sheet is a still that costs credits and has its own quoted tool), and
    it is `strict` -- an element with its photo, or a refusal. A refusal
    comes back in the page's words: a plain no for a tool (ValueError),
    or a deliberate stop when the account has nothing to create with."""
    if create is None:
        return None

    def add(kind, name, *, photo, notes="", account_id=None):
        from src.approvals import ElementRefused
        try:
            return create(kind, name, account_id=account_id, notes=notes,
                          uploads=[photo], sheet=False, strict=True)
        except ElementRefused as e:
            if e.status == 402:
                raise mcp_server.Refused(e.message) from e
            raise ValueError(e.message) from e
    return add


def build(dsn=None, start_job=None, job_status=None, approve_render=None,
          approve_keyframes=None, cancel_job=None, create_element=None):
    """The (asgi_app, session_manager) pair, or (None, None) when MCP is
    off or misconfigured.

    Never raises: a bad MCP config must not stop the web app from
    starting, which is the rule every other optional capability in this
    project follows. It does print, because a capability that silently
    does not exist is the failure mode that hid the dead launchd job for
    eleven nights.
    """
    if not enabled():
        return None, None

    secret = token()
    if not secret:
        print(
            f"note: {ENABLED_ENV}=1 but {TOKEN_ENV} is unset -- refusing to "
            f"mount {MOUNT_PATH} rather than serve it open. Generate one with "
            "python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            file=sys.stderr,
        )
        return None, None

    try:
        # The operator's door: the studio surface (the board surface it
        # reached until 2026-10-11 is gone). It has the spending tools, so
        # it can stop them; `import_file` reads the SERVER's disk from
        # here, so it is left off (it is the stdio server's).
        # `add_element` on all three: the Elements page's own create body
        add_element = connector_element(create_element)
        server = mcp_server.build_server(
            dsn=dsn,
            start_job=start_job,
            job_status=job_status,
            cancel_job=cancel_job,
            surface="studio",
            local_files=False,
            create_element=add_element,
        )
        listed = mcp_server.build_server(
            dsn=dsn,
            start_job=start_job,
            job_status=job_status,
            approve_render=approve_render,
            approve_keyframes=approve_keyframes,
            listed=True,
            create_element=add_element,
        )
        # the Claude directory's listing: nothing that renders, so neither
        # approve body is handed to it
        claude = mcp_server.build_server(
            dsn=dsn,
            start_job=start_job,
            job_status=job_status,
            listed="claude",
            create_element=add_element,
        )
        # streamable_http_path="/" because the parent app owns the mount
        # prefix; leaving the SDK default would serve this at /mcp/mcp.
        # stateless_http because there is no shared state between calls
        # to keep -- every tool reads the database fresh, and a stateful
        # session would only add something to lose on a --reload.
        from mcp.server.transport_security import TransportSecuritySettings

        hosts = allowed_hosts()
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection="*" not in os.environ.get(HOSTS_ENV, ""),
            allowed_hosts=hosts,
            allowed_origins=hosts,
        )
        asgi = server.streamable_http_app(streamable_http_path="/",
                                          stateless_http=True,
                                          transport_security=security)
        listed_asgi = listed.streamable_http_app(streamable_http_path="/",
                                                 stateless_http=True,
                                                 transport_security=security)
        claude_asgi = claude.streamable_http_app(streamable_http_path="/",
                                                 stateless_http=True,
                                                 transport_security=security)
    except ImportError as exc:
        print(f"note: {ENABLED_ENV}=1 but the mcp package is missing ({exc}) "
              f"-- {MOUNT_PATH} not mounted. `pip install -r requirements.txt`.",
              file=sys.stderr)
        return None, None
    except Exception as exc:  # surfaced, never silent
        print(f"note: could not build the MCP server ({type(exc).__name__}: "
              f"{exc}) -- {MOUNT_PATH} not mounted.", file=sys.stderr)
        return None, None

    hosts = ",".join(allowed_hosts())
    print(f"MCP mounted at {MOUNT_PATH} (bearer auth; the operator's key reaches "
          f"the studio surface, a signed-in person the listed tools, {MOUNT_PATH}"
          f"{CLAUDE_PATH} the Claude listing; hosts {hosts})", file=sys.stderr)
    return (guarded(asgi, secret, listed_app=listed_asgi, claude_app=claude_asgi),
            Sessions(server.session_manager, listed.session_manager,
                     claude.session_manager))


@asynccontextmanager
async def session_lifespan(manager: Optional[object]):
    """Run the transport's session manager for the life of the app.

    The streamable-HTTP app is not self-starting: its session manager
    has to be entered by whoever hosts it, and a mount without this
    answers every request with a 500 that says nothing useful. Nothing
    to run when MCP is off, so this degrades to a no-op rather than
    making the parent lifespan conditional.
    """
    if manager is None:
        yield
        return
    async with manager.run():
        yield
