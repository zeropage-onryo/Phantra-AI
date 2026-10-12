#!/usr/bin/env python3
"""The connector's own OAuth client and reviewer walker (2026-10-12,
docs/tasks/task-connector-submission.md, step 1).

What it is: the client a reviewer's chat app IS, written small enough to
read. `signin` runs discovery off the door's 401 (RFC 9728 -> RFC 8414),
registers a client dynamically with the loopback redirect Claude Code uses,
runs PKCE S256, opens the authorize page in the default browser, catches the
code on localhost, exchanges it, and keeps the session in
data/connector_walk/<door>.json (mode 0600, gitignored). `call` makes one
JSON-RPC `tools/call` over streamable HTTP, refreshing the token through the
refresh grant when the hour is up. `walk` runs the whole reviewer list on the
Claude listing and writes every answer with a PASS / CHECK verdict per
expectation to a Markdown file. `upload` posts a file to a one-time upload
page. `env` prints an `export TOKEN=...` line for the shell to eval.

What it never does: print, log or commit a credential. The only thing
`signin` prints is the authorize URL and the workspace it signed in as; the
walk file redacts every token-shaped value and every URL's query string; a
refusal is repeated as the sentence the connector gave, never retried.

Nothing here imports src/ or app/: the client speaks to the deployed server
exactly as a stranger's client does, and the tests run with no database and
no network (tests/test_connector_walk.py stands a fake HTTP layer in).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html as html_lib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlencode, urlsplit

API = "https://api.zeropage.studio"
DOORS = {"claude": "/mcp/claude", "render": "/mcp"}
REDIRECT = "http://localhost:53682/callback"
LOOPBACK_PORT = 53682
CLIENT_NAME = "Zero Page connector walk"
ACCEPT = "application/json, text/event-stream"
PROTOCOL = "2025-06-18"
SESSION_DIR = Path("data") / "connector_walk"
# Refresh when this close to the expiry, so a long job wait never straddles it.
REFRESH_MARGIN_S = 90
SIGNIN_WAIT_S = 15 * 60
JOB_WAIT_S = 15          # the `job` tool's own cap
JOB_POLLS_MAX = 40       # 40 x 15 s = ten minutes for one free edit
RATE_WINDOW_FALLBACK_S = 60   # the mount's window, when a 429 carries no Retry-After


class WalkError(Exception):
    """Something the client could not do; the message is for a person."""


class Refused(Exception):
    """The connector said no: the message is its own sentence."""


class RateLimited(WalkError):
    def __init__(self, retry_after: str, detail: str):
        super().__init__(f"rate limited -- Retry-After {retry_after}s: {detail}")
        self.retry_after = retry_after


# --- HTTP, behind one method so a test can stand a fake in --------------------

class Reply:
    def __init__(self, status: int, headers=None, body=b"", url: str = ""):
        self.status = int(status)
        self.headers = {str(k).lower(): v for k, v in dict(headers or {}).items()}
        self.body = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.url = url

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    def json(self) -> Any:
        return json.loads(self.text)


class Http:
    """`requests`, imported lazily so the tests never need it on the path."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def request(self, method: str, url: str, *, headers=None, json_body=None, data=None,
                files=None, allow_redirects: bool = True) -> Reply:
        import requests

        try:
            r = requests.request(method, url, headers=headers, json=json_body, data=data,
                                 files=files, timeout=self.timeout,
                                 allow_redirects=allow_redirects)
        except requests.exceptions.RequestException as exc:
            # a dropped connection or a timeout is a fact about the call, never a
            # traceback: the walk records it as that step's error and goes on
            raise WalkError(f"{method} {url.split('?')[0]}: {type(exc).__name__}: {exc}") from exc
        return Reply(r.status_code, r.headers, r.content, r.url)


# --- discovery -----------------------------------------------------------------

def door_url(door: str, api: str = API) -> str:
    if door not in DOORS:
        raise WalkError(f"door is one of {sorted(DOORS)}, got {door!r}")
    return api.rstrip("/") + DOORS[door]


def parse_challenge(header: str) -> str:
    """The metadata URL out of `WWW-Authenticate: Bearer resource_metadata="..."`."""
    m = re.search(r'resource_metadata="([^"]+)"', header or "")
    if not m:
        raise WalkError(f"the 401 names no resource_metadata (WWW-Authenticate: {header!r})")
    return m.group(1)


def as_metadata_urls(issuer: str) -> list[str]:
    """Where an authorization server's metadata may be: the issuer with the
    well-known segment appended (what Supabase serves), then RFC 8414's form
    with the segment inserted before the issuer's path."""
    issuer = issuer.rstrip("/")
    parts = urlsplit(issuer)
    base = f"{parts.scheme}://{parts.netloc}"
    path = parts.path.rstrip("/")
    urls = [f"{issuer}/.well-known/oauth-authorization-server"]
    rfc = f"{base}/.well-known/oauth-authorization-server{path}"
    if rfc not in urls:
        urls.append(rfc)
    return urls


def authorization_server_metadata(issuer: str, http) -> dict:
    tried = []
    for url in as_metadata_urls(issuer):
        r = http.request("GET", url, headers={"Accept": "application/json"})
        tried.append(f"{url} -> {r.status}")
        if r.status != 200:
            continue
        try:
            doc = r.json()
        except ValueError:
            continue
        if not (doc.get("authorization_endpoint") and doc.get("token_endpoint")):
            continue
        # RFC 8414 section 3.3: the document's issuer is the issuer it was derived from
        if str(doc.get("issuer") or "").rstrip("/") != issuer:
            raise WalkError(f"{url} names issuer {doc.get('issuer')!r}, not {issuer}")
        return doc
    raise WalkError("no authorization server metadata found: " + "; ".join(tried))


def discover(door: str, http, api: str = API) -> dict:
    """401 -> resource metadata -> authorization server metadata."""
    url = door_url(door, api)
    r = http.request("POST", url, headers={"Accept": ACCEPT, "Content-Type": "application/json"},
                     json_body={})
    if r.status != 401:
        raise WalkError(f"{url} answered {r.status} to an unsigned call, not 401")
    meta_url = parse_challenge(r.headers.get("www-authenticate", ""))
    m = http.request("GET", meta_url, headers={"Accept": "application/json"})
    if m.status != 200:
        raise WalkError(f"{meta_url} answered {m.status}")
    try:
        meta = m.json()
    except ValueError:
        raise WalkError(f"{meta_url} did not answer JSON") from None
    # RFC 9728 section 3.3: the document's resource is the URL that was dialled
    if str(meta.get("resource") or "").rstrip("/") != url.rstrip("/"):
        raise WalkError(f"{meta_url} names resource {meta.get('resource')!r}, not {url}")
    servers = meta.get("authorization_servers") or []
    if not servers:
        raise WalkError(f"{meta_url} names no authorization_servers")
    issuer = str(servers[0]).rstrip("/")
    return {"door": door, "url": url, "metadata_url": meta_url,
            "resource": meta.get("resource"), "issuer": issuer,
            "as": authorization_server_metadata(issuer, http)}


# --- PKCE, registration, the authorize URL --------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def pkce() -> tuple[str, str]:
    """(code_verifier, code_challenge), S256: RFC 7636 section 4."""
    verifier = _b64url(secrets.token_bytes(64))          # 86 chars, in 43..128
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def register_client(as_meta: dict, http, redirect: str = REDIRECT) -> dict:
    """Dynamic client registration (RFC 7591) as a public client with the
    loopback redirect, the way the 2026-10-08 script and Claude Code do."""
    endpoint = as_meta.get("registration_endpoint")
    if not endpoint:
        raise WalkError("the authorization server publishes no registration_endpoint")
    body = {"client_name": CLIENT_NAME,
            "redirect_uris": [redirect],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none"}
    r = http.request("POST", endpoint,
                     headers={"Accept": "application/json", "Content-Type": "application/json"},
                     json_body=body)
    if r.status not in (200, 201):
        raise WalkError(f"registration answered {r.status}: {r.text[:300]}")
    doc = r.json()
    if not doc.get("client_id"):
        raise WalkError("registration answered with no client_id")
    return doc


def authorize_url(as_meta: dict, client_id: str, challenge: str, state: str,
                  redirect: str = REDIRECT, scope: Optional[str] = None) -> str:
    params = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect,
              "code_challenge": challenge, "code_challenge_method": "S256", "state": state}
    if scope:
        params["scope"] = scope
    return as_meta["authorization_endpoint"] + "?" + urlencode(params)


# --- the loopback ------------------------------------------------------------------

_LANDED = ("<!doctype html><meta charset='utf-8'><title>Signed in</title>"
           "<body style='font:16px -apple-system,sans-serif;padding:3rem'>"
           "<h1>Signed in</h1><p>You can close this tab and go back to the terminal.</p>")
_FAILED = ("<!doctype html><meta charset='utf-8'><title>Not signed in</title>"
           "<body style='font:16px -apple-system,sans-serif;padding:3rem'>"
           "<h1>Not signed in</h1><p>The sign-in did not complete: {error}. "
           "Close this tab and run the command again.</p>")


def callback_outcome(query: dict, expected_state: str) -> tuple[str, str]:
    """What ONE /callback request means: ("code", <code>) for the sign-in we
    asked for, ("error", <words>) for the server's refusal of it, ("ignore",
    <why>) for anything else -- a stray request, a prefetch, another app's
    redirect on the same port, or a reply whose state is not ours. Only our
    own state ends the wait; a wrong-state request gets the failure page and
    the listener keeps waiting."""
    first = {k: v[0] for k, v in query.items() if v}
    if first.get("state") != expected_state:
        return "ignore", "a callback with a state that is not ours"
    if first.get("error"):
        return "error", (f"{first['error']}: {first.get('error_description') or ''}").rstrip(": ")
    if not first.get("code"):
        return "ignore", "a callback with our state and no code"
    return "code", first["code"]


def bind_loopback(port: int = LOOPBACK_PORT) -> HTTPServer:
    """The listener, bound BEFORE the browser is opened: a bind that fails
    (the port in use) is a WalkError here, not a browser that lands nowhere."""
    try:
        server = HTTPServer(("127.0.0.1", port), BaseHTTPRequestHandler)
    except OSError as exc:
        raise WalkError(f"cannot listen on 127.0.0.1:{port} for the sign-in ({exc}); "
                        "close whatever holds the port and run the command again") from exc
    server.timeout = 5
    return server


def catch_code(expected_state: str, port: int = LOOPBACK_PORT, timeout_s: float = SIGNIN_WAIT_S,
               clock: Callable[[], float] = time.monotonic,
               server: Optional[HTTPServer] = None) -> str:
    """GET /callback on the loopback until OUR sign-in lands; the code out of
    it. A request carrying another state is answered and ignored; an `error`
    from the server for our state is reported in its words."""
    got: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):                                        # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            kind, value = callback_outcome(parse_qs(parsed.query), expected_state)
            if kind == "code":
                got["code"] = value
                body = _LANDED
            else:
                if kind == "error":
                    got["error"] = value
                body = _FAILED.format(error=html_lib.escape(value))
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):                            # quiet
            return

    server = server or bind_loopback(port)
    server.RequestHandlerClass = Handler
    deadline = clock() + timeout_s
    try:
        while "code" not in got and "error" not in got:
            if clock() >= deadline:
                raise WalkError(f"no sign-in landed on {REDIRECT} in {int(timeout_s // 60)} minutes")
            server.handle_request()
    finally:
        server.server_close()
    if "error" in got:
        raise WalkError(f"the authorization server answered {got['error']}")
    return got["code"]


# --- tokens and the session file --------------------------------------------------

def _token_request(as_meta: dict, data: dict, http) -> dict:
    r = http.request("POST", as_meta["token_endpoint"],
                     headers={"Accept": "application/json",
                              "Content-Type": "application/x-www-form-urlencoded"},
                     data=data)
    if r.status != 200:
        raise WalkError(f"the token endpoint answered {r.status}: {r.text[:300]}")
    doc = r.json()
    if not doc.get("access_token"):
        raise WalkError("the token endpoint answered with no access_token")
    return doc


def exchange_code(as_meta: dict, client_id: str, code: str, verifier: str, http,
                  redirect: str = REDIRECT) -> dict:
    return _token_request(as_meta, {"grant_type": "authorization_code", "code": code,
                                    "redirect_uri": redirect, "client_id": client_id,
                                    "code_verifier": verifier}, http)


def refresh_tokens(as_meta: dict, client_id: str, refresh_token: str, http) -> dict:
    return _token_request(as_meta, {"grant_type": "refresh_token",
                                    "refresh_token": refresh_token,
                                    "client_id": client_id}, http)


def session_from_tokens(door: str, disc: dict, client_id: str, tokens: dict,
                        now: float, previous: Optional[dict] = None) -> dict:
    expires_in = int(tokens.get("expires_in") or 3600)
    return {"door": door, "url": disc["url"], "resource": disc.get("resource"),
            "issuer": disc["issuer"], "token_endpoint": disc["as"]["token_endpoint"],
            "client_id": client_id,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token") or (previous or {}).get("refresh_token"),
            "token_type": tokens.get("token_type") or "bearer",
            "expires_at": now + expires_in, "obtained_at": now,
            **({"whoami": previous["whoami"]} if previous and previous.get("whoami") else {})}


def session_path(door: str, root: Optional[Path] = None) -> Path:
    # SESSION_DIR is read at call time, not bound as a default: the test
    # suite redirects it to tmp_path (tests/conftest.py OUTPUT_ROOTS)
    return Path(root if root is not None else SESSION_DIR) / f"{door}.json"


def write_session(path: Path, session: dict) -> None:
    """Owner-only, directory and file: the file holds the tokens."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(session, f, indent=2)
    os.chmod(path, 0o600)


def load_session(door: str, root: Optional[Path] = None) -> tuple[dict, Path]:
    """The door's own session, else the Claude door's for the render door:
    one Supabase token serves both (its audience is the session's), so the
    render door asks for its own sign-in only when the server refuses it."""
    own = session_path(door, root)
    if own.exists():
        return json.loads(own.read_text()), own
    if door != "claude":
        other = session_path("claude", root)
        if other.exists():
            return json.loads(other.read_text()), other
    raise WalkError(f"no session for the {door} door -- run: signin --door {door}")


# --- the streamable-HTTP caller ----------------------------------------------------

def parse_rpc_reply(reply: Reply, rpc_id: Any) -> dict:
    """The JSON-RPC message for `rpc_id` out of a JSON or an SSE body."""
    ctype = (reply.headers.get("content-type") or "").lower()
    messages: list[dict] = []
    if "text/event-stream" in ctype:
        for event in re.split(r"\r?\n\r?\n", reply.text):
            data = [line[5:].strip() for line in event.splitlines() if line.startswith("data:")]
            if not data:
                continue
            try:
                msg = json.loads("\n".join(data))
            except ValueError:
                continue
            messages.extend(msg if isinstance(msg, list) else [msg])
    else:
        text = reply.text.strip()
        if text:
            try:
                msg = json.loads(text)
            except ValueError:
                raise WalkError(f"a {reply.status} reply that is not JSON "
                                f"({ctype or 'no content-type'}): {text[:120]!r}") from None
            messages.extend(msg if isinstance(msg, list) else [msg])
    for msg in messages:
        if isinstance(msg, dict) and msg.get("id") == rpc_id and ("result" in msg or "error" in msg):
            return msg
    for msg in reversed(messages):
        if isinstance(msg, dict) and ("result" in msg or "error" in msg):
            return msg
    raise WalkError(f"no JSON-RPC reply for id {rpc_id} in the response ({ctype or 'no content-type'})")


def unwrap_result(result: dict) -> Any:
    """A tool's answer: structuredContent, else the text parsed as JSON,
    else the text. A result marked isError raises Refused with its words."""
    content = result.get("content") or []
    text = "\n".join(c.get("text", "") for c in content
                     if isinstance(c, dict) and c.get("type") == "text").strip()
    if result.get("isError"):
        raise Refused(text or "refused (no reason given)")
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    if text:
        try:
            return json.loads(text)
        except ValueError:
            return text
    return result


class Door:
    """One signed-in door. `call` does initialize once, then tools/call."""

    def __init__(self, door: str, session: dict, path: Path, http, api: str = API,
                 clock: Callable[[], float] = time.time):
        self.door = door
        self.url = door_url(door, api)
        self.session = session
        self.path = Path(path)
        self.http = http
        self.clock = clock
        self.protocol = PROTOCOL
        self.session_id: Optional[str] = None
        self.initialized = False
        self._next_id = 0

    def _headers(self) -> dict:
        h = {"Accept": ACCEPT, "Content-Type": "application/json",
             "Authorization": f"Bearer {self.session['access_token']}",
             "MCP-Protocol-Version": self.protocol}
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def refresh(self) -> None:
        token = self.session.get("refresh_token")
        if not token:
            raise WalkError(f"the session has expired and holds no refresh token -- run: "
                            f"signin --door {self.door}")
        as_meta = {"token_endpoint": self.session["token_endpoint"]}
        tokens = refresh_tokens(as_meta, self.session["client_id"], token, self.http)
        disc = {"url": self.session["url"], "resource": self.session.get("resource"),
                "issuer": self.session["issuer"], "as": as_meta}
        self.session = session_from_tokens(self.session["door"], disc, self.session["client_id"],
                                           tokens, self.clock(), previous=self.session)
        write_session(self.path, self.session)

    def ensure_fresh(self) -> None:
        # with no refresh token the access token is used until the server says
        # no (a 401 names the sign-in command); refreshing early would refuse a
        # call that would still have worked
        if not self.session.get("refresh_token"):
            return
        if float(self.session.get("expires_at") or 0) - self.clock() < REFRESH_MARGIN_S:
            self.refresh()

    def rpc(self, method: str, params: Optional[dict] = None, *, notification: bool = False,
            _retry: bool = True) -> Any:
        self.ensure_fresh()
        body: dict = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notification:
            self._next_id += 1
            body["id"] = self._next_id
        r = self.http.request("POST", self.url, headers=self._headers(), json_body=body)
        if r.status == 401 and _retry and self.session.get("refresh_token"):
            self.refresh()
            return self.rpc(method, params, notification=notification, _retry=False)
        if r.status == 401:
            raise WalkError(f"the {self.door} door refused the token ({_detail(r)}) -- run: "
                            f"signin --door {self.door}")
        if r.status == 403:
            raise WalkError(f"the {self.door} door answered 403: {_detail(r)}")
        if r.status == 429:
            raise RateLimited(r.headers.get("retry-after", "?"), _detail(r))
        if notification:
            if r.status not in (200, 202, 204):
                raise WalkError(f"{self.url} answered {r.status} to {method}")
            return None
        if r.status != 200:
            raise WalkError(f"{self.url} answered {r.status} to {method}: {r.text[:300]}")
        sid = r.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        msg = parse_rpc_reply(r, body["id"])
        if "error" in msg:
            err = msg["error"] or {}
            raise WalkError(f"JSON-RPC error {err.get('code')}: {err.get('message')}")
        return msg["result"]

    def initialize(self) -> dict:
        res = self.rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                      "clientInfo": {"name": CLIENT_NAME, "version": "1.0"}})
        self.protocol = str(res.get("protocolVersion") or PROTOCOL)
        self.initialized = True
        try:
            self.rpc("notifications/initialized", {}, notification=True)
        except WalkError:
            pass            # stateless servers need no notification; a refusal here is not ours
        return res

    def list_tools(self) -> list[dict]:
        if not self.initialized:
            self.initialize()
        return list(self.rpc("tools/list", {}).get("tools") or [])

    def call(self, tool: str, args: Optional[dict] = None) -> Any:
        if not self.initialized:
            self.initialize()
        return unwrap_result(self.rpc("tools/call", {"name": tool, "arguments": args or {}}))


def _detail(reply: Reply) -> str:
    try:
        doc = reply.json()
        return str(doc.get("detail") or doc.get("error") or reply.text[:200])
    except ValueError:
        return reply.text[:200]


def open_door(door: str, http, root: Optional[Path] = None, api: str = API) -> Door:
    session, path = load_session(door, root)
    return Door(door, session, path, http, api=api)


# --- the upload page -----------------------------------------------------------------

def html_text(markup: str) -> str:
    """A page as a person reads it: no styles, no tags, one space between words."""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html_lib.unescape(s)).strip()


def upload_file(url: str, path: Path, http) -> dict:
    """POST the file as `file` (the page's form field, app/templates/upload.html),
    then GET the same address: {posted: {status, text}, again: {status, text}}."""
    path = Path(path)
    with path.open("rb") as f:
        posted = http.request("POST", url, files={"file": (path.name, f.read())})
    again = http.request("GET", url)
    return {"posted": {"status": posted.status, "text": html_text(posted.text)},
            "again": {"status": again.status, "text": html_text(again.text)}}


# --- redaction, for anything written to a file -----------------------------------------

_TOKEN_KEY = re.compile(r"token", re.I)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}")
_QUOTE_TOKEN = re.compile(r"\bzpfq\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_UPLOAD_PATH = re.compile(r"(/u/)[A-Za-z0-9._~-]+")
_QUERY = re.compile(r"(https?://[^\s\"'<>?]+)\?[^\s\"'<>]*")


def redact_text(s: str) -> str:
    s = _QUERY.sub(r"\1?…", s)
    s = _UPLOAD_PATH.sub(r"\1…", s)
    s = _JWT.sub("…", s)
    s = _QUOTE_TOKEN.sub("zpfq.…", s)
    return s


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("…" if _TOKEN_KEY.search(str(k)) and isinstance(v, str) and v else redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def dollar_keys(value: Any, path: str = "") -> list[str]:
    """Every key naming dollars, anywhere in an answer: a listed answer must have none."""
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            here = f"{path}.{k}" if path else str(k)
            if "usd" in str(k).lower():
                found.append(here)
            found.extend(dollar_keys(v, here))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found.extend(dollar_keys(v, f"{path}[{i}]"))
    return found


# --- the reviewer walk ----------------------------------------------------------------

SCENE_PROMPT = (
    "(0-3s) Close on the Tonal One headphones resting on a slate desk in soft window light; "
    "a slow push in as dust drifts through the beam, the brushed metal of the earcup catching "
    "a thin highlight. (3-8s) Cut to a wider shot across the desk: a hand lifts the headphones "
    "and turns them once, the room falling out of focus behind, the same window light raking "
    "the headband. No background music. Only diegetic sound: the faint rustle of a sleeve, a "
    "chair creak, the headphones set down on wood. Avoid: on-screen text, logos, a second pair "
    "of hands, any face."
)
RECIPE_BODY = ("A product still before a scene: one photo of the product, one of the light, "
               "the product's photo first, a single push-in, no music.")


def _same_photo(a: Any, b: Any) -> bool:
    """Two refs name one photo when their file names agree: a door may spell
    the same photo as a storable name or as a URL."""
    if not a or not b:
        return False
    return str(a).rsplit("/", 1)[-1] == str(b).rsplit("/", 1)[-1]


def _first(items, pred):
    for item in items or []:
        if pred(item):
            return item
    return None


class Walk:
    """The reviewer list, in order, each answer kept with its verdicts."""

    def __init__(self, client: Door, *, upload: Callable[[str, Path], dict], icon: Path,
                 project_title: str = "Spring product spots", element_hint: str = "Tonal",
                 log: Callable[[str], None] = lambda s: None,
                 sleep: Callable[[float], None] = time.sleep,
                 tail_seconds: int = 8):
        self.client = client
        self.upload = upload
        self.icon = Path(icon)
        self.project_title = project_title
        self.element_hint = element_hint
        self.log = log
        self.sleep = sleep
        self.tail_seconds = tail_seconds
        self.steps: list[dict] = []
        self.ctx: dict[str, Any] = {}
        # set once the rate limit has refused a call twice: every later step
        # is recorded as not run, and nothing more is sent into the window
        self.stopped: str = ""

    # -- plumbing --
    def _call(self, rec: dict, tool: str, args: dict) -> Any:
        """One call, recorded. A 429 is honoured ONCE: wait out Retry-After,
        then the same call once more; a second 429 stops the walk. Every other
        failure is that step's `refused` or `error`, never a traceback."""
        if self.stopped:
            rec["error"] = f"not run: {self.stopped}"
            return None
        for attempt in (1, 2):
            try:
                result = self.client.call(tool, args)
                rec["result"] = result
                return result
            except RateLimited as e:
                if attempt == 1:
                    rec["waited"] = str(e.retry_after)
                    try:
                        self.sleep(float(e.retry_after) + 1)
                    except (TypeError, ValueError):
                        self.sleep(float(RATE_WINDOW_FALLBACK_S))
                    continue
                rec["error"] = str(e)
                self.stopped = str(e)
                return None
            except Refused as e:
                rec["refused"] = str(e)
                return None
            except WalkError as e:
                rec["error"] = str(e)
                return None
            except Exception as exc:                                # noqa: BLE001
                rec["error"] = f"{type(exc).__name__}: {exc}"
                return None
        return None

    def run(self, tool: str, args: Optional[dict] = None, label: str = "",
            checks: Optional[Callable[[dict, dict], None]] = None) -> dict:
        rec: dict[str, Any] = {"n": len(self.steps) + 1, "tool": tool, "label": label or tool,
                               "args": dict(args or {}), "verdicts": []}
        self._call(rec, tool, dict(args or {}))
        if checks is not None:
            try:
                checks(rec, self.ctx)
            except Exception as exc:                                # noqa: BLE001
                rec["verdicts"].append(("the checks ran", "CHECK", f"check crashed: {exc!r}"))
        self.steps.append(rec)
        self.log(f"{rec['n']:>2}. {rec['label']}: " + ", ".join(v[1] for v in rec["verdicts"])
                 if rec["verdicts"] else f"{rec['n']:>2}. {rec['label']}")
        return rec

    def wait_job(self, job_id: Any, label: str, checks=None) -> dict:
        """`job` with wait=15 until it ends -- polling a job is not retrying a refusal."""
        rec: dict[str, Any] = {"n": len(self.steps) + 1, "tool": "job", "label": label,
                               "args": {"job_id": job_id, "wait": JOB_WAIT_S}, "verdicts": [],
                               "polls": 0}
        snap: Any = None
        for _ in range(JOB_POLLS_MAX):
            rec["polls"] += 1
            snap = self._call(rec, "job", {"job_id": job_id, "wait": JOB_WAIT_S})
            if "refused" in rec or "error" in rec:
                break
            if not isinstance(snap, dict) or snap.get("status") not in ("queued", "running"):
                break
        if checks is not None:
            try:
                checks(rec, self.ctx)
            except Exception as exc:                                # noqa: BLE001
                rec["verdicts"].append(("the checks ran", "CHECK", f"check crashed: {exc!r}"))
        self.steps.append(rec)
        self.log(f"{rec['n']:>2}. {label}: {rec['polls']} poll(s), "
                 + ", ".join(v[1] for v in rec["verdicts"]))
        return rec

    # -- the list --
    def run_all(self) -> list[dict]:
        """The reviewer list, then -- whatever happened -- the preferences put
        back to what they were (or the defaults) so a second run reads the
        same state this one found."""
        try:
            self._steps()
        finally:
            self._tail()
        return self.steps

    def _tail(self) -> None:
        before = self.ctx.get("prefs_before") or {}
        args = {}
        for field, default in (("seconds", self.tail_seconds), ("video_model", "ltx2.3"),
                               ("draft_first", False)):
            args[field] = before.get(field) if before.get(field) is not None else default

        def set_back(rec, ctx):
            _verdict(rec, "refused" not in rec and "error" not in rec,
                     "preferences set back to what the walk found (or the defaults): "
                     + ", ".join(f"{k}={v}" for k, v in args.items()),
                     rec.get("refused") or rec.get("error") or "")
        self.run("set_preferences", args, label="set_preferences (back)", checks=set_back)

    def _steps(self) -> None:
        ctx = self.ctx
        V = _verdict

        def whoami(rec, ctx):
            r = rec.get("result") or {}
            ws, member = r.get("workspace") or {}, r.get("member") or {}
            V(rec, ws.get("slug") == "zp-billing-test", "whoami names zp-billing-test",
              f"slug {ws.get('slug')!r}, id {ws.get('id')!r}")
            # an invited member is `member` by default (accounts.invite); the
            # seeded owner is `owner`: either is the signed-in person, recorded
            V(rec, member.get("role") in ("owner", "member"), "the signed-in member and role are named",
              f"name {member.get('name')!r}, role {member.get('role')!r}")
            ctx["workspace"] = ws
        self.run("whoami", {}, checks=whoami)

        def prefs_found(rec, ctx):
            r = rec.get("result") or {}
            found = {k: r.get(k) for k in ("aspect", "seconds", "video_model", "image_model", "draft_first")}
            ctx["prefs_before"] = found
            V(rec, "result" in rec, "the preferences as found, before anything is set",
              json.dumps(found))
        self.run("preferences", {}, label="preferences (as found)", checks=prefs_found)

        def projects(rec, ctx):
            r = rec.get("result") or {}
            hit = _first(r.get("projects") or [],
                         lambda p: self.project_title.lower() in str(p.get("title", "")).lower())
            V(rec, hit is not None, f"projects lists '{self.project_title}'",
              ", ".join(str(p.get("title")) for p in (r.get("projects") or [])) or "no projects")
            if hit:
                ctx["project_id"] = hit.get("id")
        self.run("projects", {}, checks=projects)

        def project(rec, ctx):
            r = rec.get("result") or {}
            title = (r.get("project") or r).get("title") if isinstance(r, dict) else None
            V(rec, bool(title) and self.project_title.lower() in str(title).lower(),
              "project opens with its title", f"title {title!r}")
        if "project_id" in ctx:
            self.run("project", {"project_id": ctx["project_id"]}, checks=project)

        def elements(rec, ctx):
            r = rec.get("result") or {}
            items = r.get("elements") or []
            V(rec, len(items) >= 2, "elements lists at least two elements with photos",
              f"{len(items)} element(s)")
            tonal = _first(items, lambda e: self.element_hint.lower() in str(e.get("name", "")).lower()
                           and e.get("photos"))
            other = _first(items, lambda e: e is not tonal and e.get("kind") == "prop" and e.get("photos"))
            V(rec, tonal is not None, f"an element named like '{self.element_hint}' has a photo ref",
              str((tonal or {}).get("name")))
            if tonal:
                ctx["ref_first"] = tonal["photos"][0]["ref"]
                ctx["element_first"] = tonal.get("name")
            if other:
                ctx["ref_light"] = other["photos"][0]["ref"]
                ctx["element_light"] = other.get("name")
            ctx["elements_before"] = [e.get("name") for e in items]
        self.run("elements", {}, checks=elements)

        def upload_link(rec, ctx):
            r = rec.get("result") or {}
            url = str(r.get("url") or "")
            V(rec, url.startswith("https://") and "/u/" in url, "upload_link returns an https /u/ address",
              redact_text(url))
            V(rec, r.get("credits") == 0, "upload_link costs 0 credits", f"credits {r.get('credits')!r}")
            if url:
                ctx["upload_url"] = url
        self.run("upload_link", {"purpose": "reference", "element_kind": "prop",
                                 "element_name": "Reviewer check"}, checks=upload_link)

        if ctx.get("upload_url"):
            rec: dict[str, Any] = {"n": len(self.steps) + 1, "tool": "(upload page)",
                                   "label": "upload the icon to the one-time page, then open it again",
                                   "args": {"file": self.icon.name}, "verdicts": []}
            try:
                pages = self.upload(ctx["upload_url"], self.icon)
                rec["result"] = pages
                saved = pages["posted"]["text"]
                V(rec, pages["posted"]["status"] == 200 and "Saved" in saved, "the page says Saved",
                  f"status {pages['posted']['status']}")
                m = re.search(r"asset:(\d+)", saved)
                V(rec, m is not None, "the page names an asset:<id>", m.group(0) if m else "none")
                if m:
                    ctx["uploaded_asset"] = m.group(0)
                V(rec, "Added to Reviewer check (prop)" in saved, "the page says Added to Reviewer check (prop)",
                  saved[:200])
                V(rec, "Size" in saved, "the page shows a Size line", "")
                V(rec, "Length" not in saved, "the page shows no Length line for a picture (#284)", "")
                again = pages["again"]["text"]
                V(rec, "already used" in again, "opening the link again says already used",
                  f"status {pages['again']['status']}: {again[:160]}")
            except Exception as exc:                                # noqa: BLE001
                rec["error"] = str(exc)
            self.steps.append(rec)
            self.log(f"{rec['n']:>2}. upload page: " + ", ".join(v[1] for v in rec["verdicts"]))

        def elements_after(rec, ctx):
            r = rec.get("result") or {}
            items = r.get("elements") or []
            made = _first(items, lambda e: str(e.get("name", "")).lower() == "reviewer check")
            V(rec, made is not None and bool(made.get("photos")),
              "elements now lists the prop Reviewer check with a photo",
              f"{len(items)} element(s); before: {len(ctx.get('elements_before') or [])}")
        self.run("elements", {}, label="elements (after the upload)", checks=elements_after)

        def write_scene(rec, ctx):
            r = rec.get("result") or {}
            sid = r.get("scene_id")
            V(rec, isinstance(sid, int), "write_scene answers a scene_id", str(sid))
            roles = r.get("roles") or {}
            light = [k for k, v in roles.items() if v == "light"]
            V(rec, len(light) == 1 and _same_photo(light[0], ctx.get("ref_light")),
              "the answer carries the light role on the second photo", json.dumps(redact(roles)))
            V(rec, not r.get("needs_reference"), "the scene is not a draft (it carries photos)", "")
            if isinstance(sid, int):
                ctx["scene_id"] = sid
        args = {"prompt": SCENE_PROMPT, "title": "Reviewer check: Tonal One push-in",
                "refs": [x for x in (ctx.get("ref_first"), ctx.get("ref_light")) if x]}
        if ctx.get("ref_light"):
            args["roles"] = {ctx["ref_light"]: "light"}
        if "project_id" in ctx:
            args["project_id"] = ctx["project_id"]
        self.run("write_scene", args, checks=write_scene)

        def scene(rec, ctx):
            r = rec.get("result") or {}
            V(rec, len(r.get("shots") or []) == 2, "scene shows two shots", f"{len(r.get('shots') or [])}")
            V(rec, r.get("reference_photos") == 2, "scene counts two reference photos",
              str(r.get("reference_photos")))
            V(rec, bool(r.get("roles")), "scene answers the roles", json.dumps(redact(r.get("roles"))))
            V(rec, r.get("rendered") is False, "scene is not rendered yet", "")
        if "scene_id" in ctx:
            self.run("scene", {"scene_id": ctx["scene_id"]}, checks=scene)

        def quote(rec, ctx):
            r = rec.get("result") or {}
            V(rec, bool(r.get("approve_url")), "quote carries approve_url (the studio's Render card)",
              redact_text(str(r.get("approve_url"))))
            clip = r.get("clip") or {}
            V(rec, "signed" not in clip and not any("token" in rd for rd in clip.get("renders") or []),
              "no signed tokens on the Claude listing's quote", "")
            V(rec, isinstance(r.get("keyframes"), dict), "quote prices the keyframes", "")
            V(rec, isinstance(r.get("balance"), int), "quote shows the balance in credits",
              str(r.get("balance")))
            V(rec, not dollar_keys(r), "no dollar key in the quote", ", ".join(dollar_keys(r)))
            already = (ctx.get("prefs_before") or {}).get("video_model")
            if already:
                V(rec, (r.get("preference") or {}).get("model") == already,
                  f"quote applies the preference already set ({already})", json.dumps(redact(r.get("preference"))))
            else:
                V(rec, "preference" not in r, "no preference applied before set_preferences",
                  json.dumps(redact(r.get("preference"))))
        if "scene_id" in ctx:
            self.run("quote", {"scene_id": ctx["scene_id"]}, checks=quote)

        def library(rec, ctx):
            r = rec.get("result") or {}
            items = r.get("items") or []
            V(rec, len(items) >= 1, "library lists items", f"{len(items)}")
            clip = _first(items, lambda i: i.get("kind") == "video" and i.get("origin") == "render")
            V(rec, clip is not None, "the library holds a rendered clip", str((clip or {}).get("id")))
            if clip:
                ctx["clip"] = clip["id"]
                ctx["clip_aspect"] = clip.get("aspect")
            if ctx.get("uploaded_asset"):
                V(rec, any(i.get("id") == ctx["uploaded_asset"] for i in items),
                  "the upload is in the library", ctx["uploaded_asset"])
        self.run("library", {}, checks=library)

        def done(key):
            def check(rec, ctx):
                s = rec.get("result") or {}
                V(rec, s.get("status") == "done", "the job ends done",
                  f"status {s.get('status')!r} after {rec.get('polls')} poll(s)"
                  + (f": {s.get('error')}" if s.get("error") else ""))
                res = s.get("result") or {}
                ref = res.get("ref") or res.get("asset") or (f"gen:{res['asset_id']}"
                                                             if res.get("asset_id") else None)
                V(rec, bool(ref), "the job names its new gen:<id>", str(ref))
                V(rec, (res.get("credits") in (0, None)) and s.get("credits") in (0, None),
                  "nothing charged", f"credits {s.get('credits')!r}")
                if ref:
                    ctx[key] = ref
            return check

        if not ctx.get("clip"):
            self.steps.append({"n": len(self.steps) + 1, "tool": "(skipped)",
                               "label": "reformat, trim_clip, assemble_clips, share_link: skipped",
                               "args": {}, "verdicts": [],
                               "error": "no rendered clip in the library to edit"})
        if ctx.get("clip"):
            def reformat(rec, ctx):
                r = rec.get("result") or {}
                V(rec, isinstance(r.get("job_id"), int), "reformat starts a job", str(r.get("job_id")))
                V(rec, (r.get("plan") or {}).get("credits") == 0, "reformat costs 0 credits", "")
                if isinstance(r.get("job_id"), int):
                    ctx["reformat_job"] = r["job_id"]
            self.run("reformat", {"ref": ctx["clip"], "aspect": "1:1", "fit": "crop",
                                  "title": "Reviewer check 1:1"}, checks=reformat)
            if "reformat_job" in ctx:
                self.wait_job(ctx["reformat_job"], "job (the reformat)", checks=done("reformat_ref"))

            def trim(rec, ctx):
                r = rec.get("result") or {}
                V(rec, isinstance(r.get("job_id"), int), "trim_clip starts a job", str(r.get("job_id")))
                if isinstance(r.get("job_id"), int):
                    ctx["trim_job"] = r["job_id"]
            self.run("trim_clip", {"ref": ctx["clip"], "start": 0, "end": 1,
                                   "title": "Reviewer check first second"}, checks=trim)
            if "trim_job" in ctx:
                self.wait_job(ctx["trim_job"], "job (the trim)", checks=done("trim_ref"))

            if ctx.get("reformat_ref") and ctx.get("trim_ref"):
                def join(rec, ctx):
                    r = rec.get("result") or {}
                    V(rec, isinstance(r.get("job_id"), int), "assemble_clips starts a job",
                      str(r.get("job_id")) if "job_id" in r else rec.get("refused", ""))
                    if isinstance(r.get("job_id"), int):
                        ctx["join_job"] = r["job_id"]
                self.run("assemble_clips", {"clips": [ctx["reformat_ref"], ctx["trim_ref"]],
                                            "letterbox": True, "title": "Reviewer check joined"},
                         checks=join)
                if "join_job" in ctx:
                    self.wait_job(ctx["join_job"], "job (the join)", checks=done("join_ref"))

            share_ref = ctx.get("join_ref") or ctx.get("reformat_ref") or ctx["clip"]

            def share(rec, ctx):
                r = rec.get("result") or {}
                V(rec, str(r.get("url") or "").startswith("https://"), "share_link is an https address",
                  redact_text(str(r.get("url"))))
                V(rec, r.get("hours") == 24, "the link lasts 24 hours", str(r.get("hours")))
            self.run("share_link", {"ref": share_ref}, checks=share)

            def share_200(rec, ctx):
                V(rec, "refused" in rec and "168" in rec["refused"], "hours=200 is refused (1 to 168)",
                  rec.get("refused") or "not refused")
            self.run("share_link", {"ref": share_ref, "hours": 200}, label="share_link hours=200",
                     checks=share_200)

        def balance(rec, ctx):
            r = rec.get("result") or {}
            V(rec, isinstance(r.get("available"), int), "balance answers available credits",
              str(r.get("available")))
            V(rec, not dollar_keys(r), "no dollar key in balance", ", ".join(dollar_keys(r)))
            ctx.setdefault("balance_first", r.get("available"))
            ctx["balance_last"] = r.get("available")
        self.run("balance", {}, checks=balance)

        def history(rec, ctx):
            r = rec.get("result") or {}
            lines = r.get("lines") or r.get("items") or []
            V(rec, len(lines) >= 1, "credit_history has lines", f"{len(lines)}")
            V(rec, all("balance_after" in ln for ln in lines) if lines else False,
              "every line carries balance_after", "")
            V(rec, not dollar_keys(r), "no dollar key in credit_history", ", ".join(dollar_keys(r)))
        self.run("credit_history", {}, checks=history)

        def recent(rec, ctx):
            r = rec.get("result") or {}
            V(rec, isinstance(r, dict) and any(r.get(k) for k in ("projects", "scenes", "renders")),
              "recent lists projects, scenes or renders", ", ".join(k for k in r if r.get(k)))
        self.run("recent", {}, checks=recent)

        def search(rec, ctx):
            r = rec.get("result") or {}
            blob = json.dumps(r).lower()
            V(rec, "tonal" in blob, "search finds the Tonal One prop", "")
            V(rec, ctx.get("scene_id") is not None and str(ctx["scene_id"]) in blob,
              "search finds the written scene", str(ctx.get("scene_id")))
        self.run("search", {"q": "headphones"}, checks=search)

        def video_models(rec, ctx):
            r = rec.get("result") or {}
            models = r.get("models") or []
            V(rec, len(models) >= 3, "video_models lists the catalogue", f"{len(models)}")
            wan = _first(models, lambda m: str(m.get("id") or m.get("model")) == "wan3")
            V(rec, bool(wan) and (wan.get("draft") or {}) and ("480p" in json.dumps(wan.get("draft"))),
              "wan3 carries a 480p draft frame", json.dumps(redact((wan or {}).get("draft"))))
            V(rec, not dollar_keys(r), "no dollar key in video_models", ", ".join(dollar_keys(r)))
        self.run("video_models", {}, checks=video_models)

        def cheap(rec, ctx):
            r = rec.get("result") or {}
            picks = r.get("picks") or r.get("ranked") or r.get("models") or []
            first = str((picks[0] if picks else {}).get("id") or (picks[0] if picks else {}).get("model"))
            V(rec, first == "ltx2.3", "a cheap test ranks LTX 2.3 first", first)
            V(rec, not dollar_keys(r), "no dollar key in recommend_model", ", ".join(dollar_keys(r)))
        self.run("recommend_model", {"what": "a cheap test"}, checks=cheap)

        def long_spot(rec, ctx):
            r = rec.get("result") or {}
            picks = r.get("picks") or r.get("ranked") or r.get("models") or []
            ids = [str(p.get("id") or p.get("model")) for p in picks]
            V(rec, ids == ["seedance2.5"], "25 seconds leaves Seedance 2.5 only", ", ".join(ids) or "none")
        self.run("recommend_model", {"what": "a final client spot with sound", "seconds": 25},
                 label="recommend_model (25 s, sound)", checks=long_spot)

        def prefs(rec, ctx):
            r = rec.get("result") or {}
            values = {k: r.get(k) for k in ("aspect", "seconds", "video_model", "image_model", "draft_first")}
            before = ctx.get("prefs_before") or {}
            V(rec, values == before, "preferences read the same as at the start (unset, or as a "
              "previous walk left them)", json.dumps(values))
            V(rec, bool(r.get("choices")), "the choices are listed", "")
        self.run("preferences", {}, checks=prefs)

        def set_ok(rec, ctx):
            r = rec.get("result") or {}
            blob = json.dumps(r)
            V(rec, "refused" not in rec and "wan3" in blob and "12" in blob,
              "set_preferences took seconds=12, wan3, draft_first", rec.get("refused", ""))
        self.run("set_preferences", {"seconds": 12, "video_model": "wan3", "draft_first": True},
                 checks=set_ok)

        def set_sora(rec, ctx):
            V(rec, "refused" in rec and "video_model is one of" in rec["refused"],
              "video_model=sora is refused with the list", rec.get("refused") or "not refused")
        self.run("set_preferences", {"video_model": "sora"}, label="set_preferences video_model=sora",
                 checks=set_sora)

        if "scene_id" in ctx:
            def quote_pref(rec, ctx):
                r = rec.get("result") or {}
                pref = r.get("preference") or {}
                V(rec, pref.get("model") == "wan3", "quote applies the wan3 preference",
                  json.dumps(redact(pref)))
                V(rec, "480p" in json.dumps(pref) or "480p" in json.dumps(r.get("clip") or {}),
                  "the draft frame 480p is applied", "")
            self.run("quote", {"scene_id": ctx["scene_id"]}, label="quote (after set_preferences)",
                     checks=quote_pref)

            def quote_ltx(rec, ctx):
                r = rec.get("result") or {}
                V(rec, "preference" not in r, "a named model carries no preference", "")
            self.run("quote", {"scene_id": ctx["scene_id"], "model": "ltx2.3"}, label="quote model=ltx2.3",
                     checks=quote_ltx)

        def dup(rec, ctx):
            r = rec.get("result") or {}
            V(rec, isinstance(r.get("scene_id"), int) and r.get("scene_id") != 400,
              "duplicate_scene makes a new scene", str(r.get("scene_id")))
            V(rec, r.get("copied_from") == 400, "it names copied_from", str(r.get("copied_from")))
            V(rec, not r.get("rendered") and not r.get("clips"), "the copy carries no clip", "")
        self.run("duplicate_scene", {"scene_id": 400}, checks=dup)

        def dup_empty(rec, ctx):
            r = rec.get("result") or {}
            V(rec, r.get("needs_reference") is True or "needs_reference" in rec.get("refused", ""),
              "a copy with refs=[] is a draft (needs_reference)", rec.get("refused", "")[:160])
        self.run("duplicate_scene", {"scene_id": 400, "refs": []}, label="duplicate_scene refs=[]",
                 checks=dup_empty)

        def fb(rec, ctx):
            V(rec, "refused" not in rec and "error" not in rec, "feedback is saved",
              rec.get("refused") or rec.get("error") or "")
        self.run("feedback", {"text": "Reviewer walk, 2026-10-13: every free tool answered as the "
                                      "listing says.", "tool": "whoami"}, checks=fb)

        def recipes(rec, ctx):
            r = rec.get("result") or {}
            items = r.get("recipes") or []
            own = _first(items, lambda x: x.get("own") and x.get("name") == "reviewer-check")
            ctx["recipe_versions"] = int((own or {}).get("versions") or 0)
            V(rec, any(not x.get("own") and x.get("name") == "single-shot" for x in items),
              "recipes lists the studio's shelf (single-shot among them)",
              f"{len(items)} recipe(s); reviewer-check at version {ctx['recipe_versions']}")
        self.run("recipes", {}, checks=recipes)

        def recipe_v(step):
            def check(rec, ctx):
                r = rec.get("result") or {}
                want = ctx.get("recipe_versions", 0) + step
                V(rec, r.get("version") == want, f"save_recipe answers version {want}", str(r.get("version")))
            return check
        self.run("save_recipe", {"name": "reviewer-check", "body": RECIPE_BODY}, checks=recipe_v(1))
        self.run("save_recipe", {"name": "reviewer-check", "body": RECIPE_BODY + " Then the scene."},
                 label="save_recipe (again)", checks=recipe_v(2))

        def recipe_own(rec, ctx):
            r = rec.get("result") or {}
            note = str(r.get("note") or "").lower()
            want = ctx.get("recipe_versions", 0) + 2
            V(rec, r.get("version") == want and ("data" in note or "quoted" in note),
              f"recipe returns version {want} with the note that it is the person's own text",
              f"version {r.get('version')!r}")
        self.run("recipe", {"name": "reviewer-check"}, checks=recipe_own)

        def recipe_shelf(rec, ctx):
            r = rec.get("result") or {}
            V(rec, "refused" not in rec and bool(r), "recipe single-shot is the shelf's", "")
        self.run("recipe", {"name": "single-shot"}, label="recipe single-shot", checks=recipe_shelf)

        def works(rec, ctx):
            r = rec.get("result") or {}
            V(rec, r.get("enough_data") is False, "what_works says enough_data false",
              str(r.get("enough_data")))
            V(rec, "nothing posted" in json.dumps(r).lower(), "what_works says nothing posted", "")
            V(rec, not dollar_keys(r), "no dollar key in what_works", ", ".join(dollar_keys(r)))
        self.run("what_works", {}, checks=works)

        def caption(rec, ctx):
            r = rec.get("result") or {}
            V(rec, r.get("score") == 0.5, "score_caption is neutral at 0.5", str(r.get("score")))
            V(rec, r.get("enough_data") is False, "score_caption says enough_data false", "")
        self.run("score_caption", {"text": "Spring product spots, shot on the headphones"}, checks=caption)

        def foreign_project(rec, ctx):
            V(rec, "refused" in rec and "no project 1" in rec["refused"], "project 1 is refused as no project 1",
              rec.get("refused") or json.dumps(redact(rec.get("result")))[:160])
        self.run("project", {"project_id": 1}, label="project project_id=1 (another workspace's)",
                 checks=foreign_project)

        def foreign_scene(rec, ctx):
            V(rec, "refused" in rec and "no scene 375" in rec["refused"], "scene 375 is refused as no scene 375",
              rec.get("refused") or json.dumps(redact(rec.get("result")))[:160])
        self.run("scene", {"scene_id": 375}, label="scene scene_id=375 (another workspace's)",
                 checks=foreign_scene)

        def balance_last(rec, ctx):
            r = rec.get("result") or {}
            ctx["balance_last"] = r.get("available")
            V(rec, r.get("available") == ctx.get("balance_first"), "the balance is what it was at the start",
              f"{ctx.get('balance_first')} -> {r.get('available')}")
        self.run("balance", {}, label="balance (at the end)", checks=balance_last)



def _verdict(rec: dict, ok: bool, expectation: str, detail: str = "") -> None:
    rec["verdicts"].append((expectation, "PASS" if ok else "CHECK", detail))


def render_walk(steps: list[dict], *, door: str, date: str, account: str = "") -> str:
    """The walk as Markdown: a verdict table, then every answer, redacted."""
    out = [f"# Reviewer walk: {DOORS.get(door, door)} as {account or 'the test account'} ({date})", "",
           f"Run by `ops/connector_walk.py walk {door}`. Every answer below is the connector's own, "
           "with tokens and URL query strings redacted. PASS means the expectation held; CHECK means "
           "read it. A refusal is the connector's own sentence, never retried.", ""]
    total = sum(len(s["verdicts"]) for s in steps)
    passed = sum(1 for s in steps for v in s["verdicts"] if v[1] == "PASS")
    out += [f"**{passed} of {total} expectations PASS.**", "", "## Verdicts", "",
            "| # | tool | expectation | verdict | detail |", "|---|---|---|---|---|"]
    for s in steps:
        for exp, verdict, detail in s["verdicts"]:
            out.append(f"| {s['n']} | {s['label']} | {exp} | {verdict} | {_cell(detail)} |")
        if not s["verdicts"]:
            out.append(f"| {s['n']} | {s['label']} | (recorded) | - | |")
    flagged = _dollar_in(steps)
    out.append(f"| - | every answer | no dollar sign and no dollar-named key anywhere | "
               f"{'PASS' if not flagged else 'CHECK'} | {_cell(', '.join(flagged))} |")
    out += ["", "## Answers", ""]
    for s in steps:
        out.append(f"### {s['n']}. {s['label']}")
        out.append("")
        out.append("args: `" + json.dumps(redact(s["args"]), ensure_ascii=False) + "`")
        if s.get("polls"):
            out.append(f"polls: {s['polls']}")
        if s.get("waited"):
            out.append(f"rate limited once; waited Retry-After {s['waited']} s and asked once more")
        out.append("")
        if "refused" in s:
            out.append(f"refused: {redact_text(s['refused'])}")
        elif "error" in s:
            out.append(f"error: {redact_text(s['error'])}")
        if "result" in s:
            out.append("```json")
            out.append(json.dumps(redact(s["result"]), indent=2, ensure_ascii=False))
            out.append("```")
        out.append("")
    text = "\n".join(out).rstrip() + "\n"
    return text


def _cell(s: str) -> str:
    return redact_text(str(s or "")).replace("|", "\\|").replace("\n", " ")[:220]


def _dollar_in(steps: list[dict]) -> list[str]:
    flagged = []
    for s in steps:
        if "result" in s:
            flagged += [f"{s['n']}:{k}" for k in dollar_keys(s["result"])]
            if "$" in json.dumps(s["result"]):
                flagged.append(f"{s['n']}: a dollar sign in the answer")
        for key in ("refused", "error"):
            if "$" in str(s.get(key, "")):
                flagged.append(f"{s['n']}: a dollar sign in the {key}")
    return flagged


# --- the commands -----------------------------------------------------------------------

def _sessions(args) -> Optional[Path]:
    return Path(args.sessions) if args.sessions else None


def _say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def cmd_signin(args) -> int:
    http = Http()
    disc = discover(args.door, http, api=args.api)
    reg = register_client(disc["as"], http)
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(16)
    url = authorize_url(disc["as"], reg["client_id"], challenge, state, scope=args.scope)
    print(url, flush=True)
    if args.dry_run:
        _say("dry run: no browser opened, nothing saved")
        return 0
    server = bind_loopback()
    _say("Sign in as the test account on the page that opens (sign out of the studio first if "
         "you are signed in as yourself), press Allow, and you are done.")
    if not args.no_browser:
        webbrowser.open(url)
    code = catch_code(state, server=server)
    tokens = exchange_code(disc["as"], reg["client_id"], code, verifier, http)
    session = session_from_tokens(args.door, disc, reg["client_id"], tokens, time.time())
    path = session_path(args.door, _sessions(args))
    write_session(path, session)
    door = Door(args.door, session, path, http, api=args.api)
    who = door.call("whoami")
    ws = (who or {}).get("workspace") or {}
    session["whoami"] = {"workspace": ws, "member": (who or {}).get("member")}
    write_session(path, door.session | {"whoami": session["whoami"]})
    print(f"signed in as workspace {ws.get('slug') or ws.get('name') or ws.get('id')}", flush=True)
    return 0


def cmd_call(args) -> int:
    http = Http()
    door = open_door(args.door, http, _sessions(args), api=args.api)
    try:
        params = json.loads(args.json) if args.json else {}
    except ValueError as e:
        raise WalkError(f"--json is not JSON: {e}") from e
    try:
        result = door.call(args.tool, params)
    except Refused as e:
        print(json.dumps({"refused": str(e)}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_tools(args) -> int:
    http = Http()
    door = open_door(args.door, http, _sessions(args), api=args.api)
    tools = door.list_tools()
    for t in tools:
        print(t.get("name"))
    _say(f"{len(tools)} tools on {door.url}")
    return 0


def cmd_walk(args) -> int:
    http = Http()
    door = open_door(args.door, http, _sessions(args), api=args.api)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    date = args.date or time.strftime("%Y-%m-%d")
    account = ((door.session.get("whoami") or {}).get("workspace") or {}).get("slug") or ""
    walk = Walk(door, upload=lambda url, path: upload_file(url, path, http), icon=Path(args.icon),
                log=_say, tail_seconds=args.tail_seconds)
    steps: list[dict] = walk.steps

    try:
        walk.run_all()
    finally:
        out.write_text(render_walk(steps, door=args.door, date=date, account=account))
        _say(f"wrote {out}")
    total = sum(len(s["verdicts"]) for s in steps)
    passed = sum(1 for s in steps for v in s["verdicts"] if v[1] == "PASS")
    _say(f"{passed} of {total} expectations PASS")
    return 0 if passed == total else 1


def cmd_upload(args) -> int:
    pages = upload_file(args.url, Path(args.file), Http())
    print(json.dumps(pages, indent=2, ensure_ascii=False))
    return 0


def cmd_env(args) -> int:
    """`export TOKEN=...` to the file descriptor the caller names -- never to
    stdout, which a terminal shows and a transcript keeps. Shell use:
    `eval "$(venv/bin/python ops/connector_walk.py env claude --fd 3 3>&1 1>/dev/null)"`.
    `inspector` is the simpler door for the one thing that needs the raw token."""
    if args.fd is None:
        raise WalkError("env writes the token only to a file descriptor you name (--fd N); "
                        "for the Inspector use the `inspector` subcommand instead")
    http = Http()
    door = open_door(args.door, http, _sessions(args), api=args.api)
    door.ensure_fresh()
    with os.fdopen(os.dup(int(args.fd)), "w") as out:
        out.write(f"export TOKEN={door.session['access_token']}\n")
    return 0


INSPECTOR = ["npx", "-y", "@modelcontextprotocol/inspector", "--cli"]


def inspector_argv(url: str, token: str, method: str = "tools/list") -> list[str]:
    return INSPECTOR + [url, "--transport", "http", "--method", method,
                        "--header", f"Authorization: Bearer {token}"]


def cmd_inspector(args) -> int:
    """The MCP Inspector's CLI against one door, its listing saved to --out.
    The token goes to the child as an argument and nowhere else; what is
    printed is the count of tools the listing holds."""
    http = Http()
    door = open_door(args.door, http, _sessions(args), api=args.api)
    door.ensure_fresh()
    argv = inspector_argv(door.url, door.session["access_token"], args.method)
    run = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    if run.returncode != 0:
        raise WalkError(f"the Inspector exited {run.returncode}: "
                        f"{redact_text((run.stderr or run.stdout or '')[-600:])}")
    text = run.stdout.strip()
    try:
        doc = json.loads(text)
    except ValueError:
        raise WalkError(f"the Inspector printed something that is not JSON: {redact_text(text[:300])!r}") from None
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    names = [t.get("name") for t in (doc.get("tools") or []) if isinstance(t, dict)]
    print(f"{len(names)} tools on {door.url} -> {out}")
    for name in names:
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[1] if __doc__ else "")
    p.add_argument("--api", default=API, help=f"the API origin (default {API})")
    p.add_argument("--sessions", default=None,
                   help=f"where the session files live (default {SESSION_DIR})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("signin", help="discover, register, sign in through the browser, save the session")
    s.add_argument("--door", choices=sorted(DOORS), default="claude")
    s.add_argument("--dry-run", action="store_true", help="print the authorize URL and stop")
    s.add_argument("--no-browser", action="store_true", help="print the URL instead of opening it")
    s.add_argument("--scope", default=None, help="an OAuth scope string (omitted by default)")
    s.set_defaults(fn=cmd_signin)

    c = sub.add_parser("call", help="one tools/call; prints the result JSON")
    c.add_argument("door", choices=sorted(DOORS))
    c.add_argument("tool")
    c.add_argument("--json", default="", help="the arguments as a JSON object")
    c.set_defaults(fn=cmd_call)

    t = sub.add_parser("tools", help="list the tools the door serves to this sign-in")
    t.add_argument("door", choices=sorted(DOORS))
    t.set_defaults(fn=cmd_tools)

    w = sub.add_parser("walk", help="the reviewer list, with verdicts, into a Markdown file")
    w.add_argument("door", choices=sorted(DOORS))
    w.add_argument("--out", required=True)
    w.add_argument("--icon", default="docs/directory/icon/zeropage-studio-icon-512.png")
    w.add_argument("--date", default=None)
    w.add_argument("--tail-seconds", type=int, default=8,
                   help="the seconds preference set back at the end (default 8)")
    w.set_defaults(fn=cmd_walk)

    u = sub.add_parser("upload", help="post a file to a one-time upload page, then open it again")
    u.add_argument("url")
    u.add_argument("file")
    u.set_defaults(fn=cmd_upload)

    e = sub.add_parser("env", help="write `export TOKEN=...` to a file descriptor you name (--fd N), "
                                   "never to stdout")
    e.add_argument("door", choices=sorted(DOORS))
    e.add_argument("--fd", type=int, default=None)
    e.set_defaults(fn=cmd_env)

    i = sub.add_parser("inspector", help="run the MCP Inspector's CLI against a door; save its listing")
    i.add_argument("door", choices=sorted(DOORS))
    i.add_argument("--out", required=True)
    i.add_argument("--method", default="tools/list")
    i.set_defaults(fn=cmd_inspector)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.fn(args) or 0)
    except RateLimited as e:
        _say(str(e))
        return 3
    except WalkError as e:
        _say(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
