"""The /mcp mount actually builds.

WHY THIS FILE EXISTS. `mcp_mount.build` catches every exception on
purpose -- a bad MCP config must not stop the web app from starting --
so a signature drift between it and `mcp_server.build_server` fails
SILENTLY: the app boots, /mcp 404s, and the only trace is one line on
stderr. That is exactly what happened when build_server's first
parameter was renamed `path` -> `dsn` (2026-09-18, the Guide's build)
and this caller was not updated: the deployed endpoint answered 404 for
every caller and the tests, which only ever exercised build_server
directly, stayed green.

So the assertion worth making is the one nothing else makes: with the
env set the way a real deployment sets it, build() returns an app
rather than the pair of Nones it returns for every failure.
"""
import asyncio
import time

import jwt as pyjwt
import pytest
from conftest import PROJECT_ROOT

from app import mcp_auth, mcp_mount
from src import mcp_server


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv(mcp_mount.HOSTS_ENV, raising=False)
    monkeypatch.setenv(mcp_mount.ENABLED_ENV, "1")
    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "test-token")
    return monkeypatch


def test_off_unless_enabled(monkeypatch):
    monkeypatch.delenv(mcp_mount.ENABLED_ENV, raising=False)
    assert mcp_mount.build() == (None, None)


def test_refused_without_a_token(monkeypatch):
    monkeypatch.setenv(mcp_mount.ENABLED_ENV, "1")
    monkeypatch.delenv(mcp_mount.TOKEN_ENV, raising=False)
    assert mcp_mount.build() == (None, None)


def test_builds_when_configured(env, tmp_path):
    """The regression: a bad keyword here returns (None, None) quietly."""
    pytest.importorskip("mcp")
    app, sessions = mcp_mount.build(dsn=str(tmp_path / "board.db"))
    assert app is not None and sessions is not None


def test_allowed_hosts_take_the_deployment_hostname(env):
    env.setenv(mcp_mount.HOSTS_ENV, "zeropage-studio.fly.dev")
    assert "zeropage-studio.fly.dev" in mcp_mount.allowed_hosts()
    env.setenv(mcp_mount.HOSTS_ENV, "*")
    assert mcp_mount.allowed_hosts() == ["*"]


def test_the_published_resource_host_is_always_allowed(env):
    """The secret listing only the old fly.dev host must not 421 the new
    domain the OAuth metadata publishes."""
    env.setenv(mcp_mount.HOSTS_ENV, "zeropage-studio.fly.dev")
    env.setenv("ZEROPAGE_MCP_RESOURCE", "https://api.zeropage.studio/mcp")
    hosts = mcp_mount.allowed_hosts()
    assert "zeropage-studio.fly.dev" in hosts
    assert "api.zeropage.studio" in hosts
    assert "api.zeropage.studio:443" in hosts
    env.delenv("ZEROPAGE_MCP_RESOURCE", raising=False)
    assert "api.zeropage.studio" not in mcp_mount.allowed_hosts()


@pytest.mark.parametrize("header, status", [
    (None, 401),
    ("Bearer wrong", 401),
    ("Bearer right", 200),
])
def test_guarded_checks_the_bearer_token(header, status):
    import asyncio

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped = mcp_mount.guarded(inner, "right")
    headers = [(b"authorization", header.encode())] if header else []
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(wrapped({"type": "http", "headers": headers, "method": "POST",
                         "path": "/mcp/"}, receive, send))
    assert sent[0]["status"] == status


# --------------------------------------------------------------------------
# THE OAUTH DOOR (2026-09-24)
#
# The mount had one caller for its whole life: an agent holding the static
# token, acting as the bootstrap account. Letting a second person in is the
# change these tests exist for, and the failure they are written against is
# not "OAuth is broken" -- it is "OAuth works and the caller reads Mike's
# board", which looks exactly like success from the connector's side.
# --------------------------------------------------------------------------
@pytest.fixture
def site(monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://zeropage-studio.fly.dev")
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.delenv(mcp_auth.RESOURCE_ENV, raising=False)
    return monkeypatch


def test_metadata_names_this_server_and_its_authorization_server(site):
    doc = mcp_auth.protected_resource_metadata()
    assert doc["resource"] == "https://zeropage-studio.fly.dev/mcp"
    # Supabase's issuer is /auth/v1, not the project root: the root 404s
    # on every discovery path, which a client reports as "no OAuth server"
    # rather than as a wrong URL.
    assert doc["authorization_servers"] == ["https://proj.supabase.co/auth/v1"]
    # A scope this server does not enforce would be a claim, not a control.
    assert "scopes_supported" not in doc


def test_metadata_lives_under_the_resource_path(site):
    """RFC 9728 puts the resource's path AFTER the well-known segment."""
    assert mcp_auth.metadata_url() == (
        "https://zeropage-studio.fly.dev/.well-known/oauth-protected-resource/mcp")
    assert mcp_auth.metadata_url() in mcp_auth.challenge()


def test_challenge_degrades_when_there_is_no_authorization_server(site):
    site.delenv("SUPABASE_URL", raising=False)
    assert mcp_auth.configured() is False


def test_resource_can_be_overridden_for_another_public_hostname(site):
    site.setenv(mcp_auth.RESOURCE_ENV, "https://tunnel.example.com/mcp/")
    assert mcp_auth.protected_resource_metadata()["resource"] == \
        "https://tunnel.example.com/mcp"


def _drive(app, header=None):
    """Run one HTTP request through an ASGI app and return (status, seen)."""
    sent = []
    headers = [(b"authorization", header.encode())] if header else []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(app({"type": "http", "headers": headers, "method": "POST",
                     "path": "/"}, receive, send))
    return sent[0]["status"]


def _capturing():
    """An inner app that records who the transport says is calling."""
    seen = []

    async def inner(scope, receive, send):
        seen.append(mcp_server.CALLER_ACCOUNT.get())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return inner, seen


def test_the_static_token_still_acts_as_the_operator():
    """No caller named -> _account falls through to the bootstrap account,
    which is the pre-OAuth behaviour every CLI and agent depends on."""
    inner, seen = _capturing()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "invalid_token"))
    assert _drive(app, "Bearer static") == 200
    assert seen == [None]


def test_a_signed_in_caller_acts_as_their_own_account():
    inner, seen = _capturing()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"))
    assert _drive(app, "Bearer someones-jwt") == 200
    assert seen == [7]
    # and the value does not outlive the request -- a leak here is one
    # caller reading the next caller's board.
    assert mcp_server.CALLER_ACCOUNT.get() is None


# ---------- the last-used stamp (the studio's Connect to Claude panel) ----------

def _person_token(sub="uid-ana"):
    # the guard reads `sub` only after `resolve` has verified the token,
    # so an unverified decode is all the stamp needs
    return pyjwt.encode({"sub": sub}, "k" * 32, algorithm="HS256")


def _stamping(resolve, clock):
    inner, seen = _capturing()
    stamped = []
    app = mcp_mount.guarded(inner, "static", resolve=resolve,
                            limiter=mcp_mount.RateLimiter(),
                            stamp=lambda account_id, user_id: stamped.append((account_id, user_id)),
                            stamps=mcp_mount.UseStamps(window_s=600, clock=clock))
    return app, seen, stamped


def test_calls_through_the_listed_door_stamp_once_per_window():
    now = [1000.0]
    app, seen, stamped = _stamping(lambda t: (7, "ok"), lambda: now[0])
    header = f"Bearer {_person_token()}"
    for _ in range(5):
        assert _drive(app, header) == 200
    assert stamped == [(7, "uid-ana")] and seen == [7] * 5
    now[0] += 601
    assert _drive(app, header) == 200
    assert stamped == [(7, "uid-ana"), (7, "uid-ana")]
    # a second person on the same account has their own window
    assert _drive(app, f"Bearer {_person_token('uid-cleo')}") == 200
    assert stamped[-1] == (7, "uid-cleo")


def test_the_operator_key_stamps_nothing():
    app, seen, stamped = _stamping(lambda t: (7, "ok"), lambda: 0.0)
    for _ in range(3):
        assert _drive(app, "Bearer static") == 200
    assert stamped == [] and seen == [None] * 3


def test_a_refused_caller_stamps_nothing():
    app, seen, stamped = _stamping(lambda t: (None, "invalid_token"), lambda: 0.0)
    assert _drive(app, f"Bearer {_person_token()}") == 401
    app, seen, stamped2 = _stamping(lambda t: (None, "no_account"), lambda: 0.0)
    assert _drive(app, f"Bearer {_person_token()}") == 403
    assert stamped == stamped2 == []


def test_a_stamp_that_fails_never_fails_the_call():
    inner, seen = _capturing()

    def broken(account_id, user_id):
        raise RuntimeError("database is down")

    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"),
                            limiter=mcp_mount.RateLimiter(), stamp=broken,
                            stamps=mcp_mount.UseStamps())
    assert _drive(app, f"Bearer {_person_token()}") == 200
    assert seen == [7]


def test_a_sign_in_with_no_membership_is_403_not_somebody_elses_board():
    inner, seen = _capturing()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "no_account"))
    assert _drive(app, "Bearer valid-but-unaffiliated") == 403
    assert seen == []


def test_the_403_says_to_sign_in_once_on_the_web(monkeypatch):
    """Mike's call (2026-10-07): the connector never creates a workspace;
    one web sign-in does. The refusal has to say that, with the address,
    rather than 'ask to be invited' (wrong under open sign-up)."""
    monkeypatch.delenv(mcp_mount.SIGNUP_ENV, raising=False)
    assert "https://zeropage.studio/signin?mode=signup" in mcp_mount.no_account_detail()
    assert "invited" not in mcp_mount.no_account_detail()
    monkeypatch.setenv(mcp_mount.SIGNUP_ENV, "https://studio.example.com")
    assert "https://studio.example.com" in mcp_mount.no_account_detail()


def test_an_unverifiable_token_is_401_and_never_reaches_the_server():
    inner, seen = _capturing()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "invalid_token"))
    assert _drive(app, "Bearer nonsense") == 401
    assert seen == []


def test_two_callers_through_the_real_transport_read_their_own_rows(env, monkeypatch):
    """The end-to-end one, and the only one that would have caught a
    context that does not propagate: tool calls through the REAL
    streamable-HTTP app, each reporting the account the tool resolved.

    `list_project_cards` (the `projects` tool, on both servers) is stood in
    for rather than reaching Postgres -- what is under test is whose id
    arrives, not what the list says. The resolver is stood in for at
    `mcp_auth.account_for_token`, which is where `guarded` reaches for it,
    so the wiring under test is the real one. A signed-in person lands on
    the listed server and the operator's key on the studio surface: the
    same tool name on two servers, and each resolves its own caller.
    """
    pytest.importorskip("mcp")
    httpx = pytest.importorskip("httpx")
    from app import mcp_auth as auth_module

    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "operator-key")
    monkeypatch.setenv(mcp_mount.HOSTS_ENV, "*")
    monkeypatch.setattr(mcp_server.accounts, "resolve_account",
                        lambda **kw: 1, raising=False)
    monkeypatch.setattr(
        mcp_server, "list_project_cards",
        lambda *a, dsn=None, account_id=None, **kw:
            {"count": 0, "projects": [], "truncated": False,
             "acting_as": mcp_server._account(account_id, dsn)})
    people = {"alice": 4, "bob": 9}
    monkeypatch.setattr(
        auth_module, "account_for_token",
        lambda token, dsn=None: (people[token], "ok") if token in people
        else (None, "invalid_token"))

    app, sessions = mcp_mount.build(dsn=":memory:")
    assert app is not None

    async def run_calls():
        # ONE session manager for the whole test: it is an async context
        # that refuses to be entered twice, the same way the app enters it
        # once in its lifespan.
        out = {}
        async with sessions.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                    transport=transport,
                    base_url="https://zeropage-studio.fly.dev") as client:
                for token in ("alice", "bob", "operator-key", "nonsense"):
                    reply = await client.post("/", headers={
                        "authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": "projects", "arguments": {}}})
                    out[token] = _acting_as(reply.text)
        return out

    acting_as = asyncio.run(run_calls())

    assert acting_as["alice"] == 4
    assert acting_as["bob"] == 9
    # the operator's own key still reads the bootstrap account
    assert acting_as["operator-key"] == 1
    # and an unverifiable token never reaches a tool at all
    assert acting_as["nonsense"] is None


def _acting_as(body: str):
    """The account a tool call resolved, read back off the SSE reply, or
    None when the call never reached a tool."""
    import json

    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[len("data:"):])
        result = payload.get("result") or {}
        # the studio surface answers typed: the payload is structuredContent,
        # and its first text block is a line for a person, not JSON
        structured = result.get("structuredContent")
        if isinstance(structured, dict) and "acting_as" in structured:
            return structured["acting_as"]
        for item in result.get("content") or []:
            if item.get("type") != "text":
                continue
            try:
                found = json.loads(item["text"])
            except ValueError:
                continue
            if isinstance(found, dict) and "acting_as" in found:
                return found["acting_as"]
    return None


def test_the_document_is_built_off_the_resource_not_off_site_url(monkeypatch):
    """The Fly case: SITE_URL is unset there (it drives the landing
    page's canonical tags, and the public site is the Vercel app), so a
    document built from it would publish a localhost resource to a
    connector reaching us at fly.dev -- discovery that fails silently."""
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.setenv(mcp_auth.RESOURCE_ENV, "https://zeropage-studio.fly.dev/mcp")
    doc = mcp_auth.protected_resource_metadata()
    assert doc["resource"] == "https://zeropage-studio.fly.dev/mcp"
    assert "127.0.0.1" not in mcp_auth.metadata_url()
    assert "127.0.0.1" not in doc["resource_documentation"]


# --------------------------------------------------------------------------
# THE DIRECTORY LISTING (2026-10-07, docs/tasks/task-directory-listing.md)
#
# A listed connector is reached by strangers. Three things have to be true
# that one operator never needed: a token minted for somebody else's
# resource, or by somebody else's issuer, or yesterday, is refused; one
# caller cannot flood the process that serves everybody; and user A cannot
# read, write or even confirm the existence of user B's rows, through the
# REAL transport, tool by tool.
# --------------------------------------------------------------------------

JWT_SECRET = "test-secret-" * 4
RESOURCE = "https://zeropage-studio.fly.dev/mcp"
ISSUER = "https://proj.supabase.co/auth/v1"


@pytest.fixture
def hs256(site):
    """The HS256 path: the project's shared JWT secret is configured."""
    site.setenv("SUPABASE_JWT_SECRET", JWT_SECRET)
    return site


def _token(secret=JWT_SECRET, alg="HS256", **claims):
    body = {"sub": "user-a", "aud": RESOURCE, "iss": ISSUER,
            "exp": int(time.time()) + 300}
    body.update(claims)
    return pyjwt.encode(body, secret, algorithm=alg)


def test_a_token_for_this_resource_verifies(hs256):
    assert mcp_auth.verify(_token())["sub"] == "user-a"


def test_an_ordinary_session_token_still_verifies(hs256):
    """`aud: authenticated` is what a zp_session sign-in carries; it is
    accepted so a token pasted from the app's own console works."""
    assert mcp_auth.verify(_token(aud="authenticated"))["sub"] == "user-a"


def test_a_token_minted_for_another_resource_is_refused(hs256):
    """MCP authorization spec, Token Handling: a token for some other
    server, signed by the same authorization server, must not work here."""
    assert mcp_auth.verify(_token(aud="https://other.example.com/mcp")) is None


def test_an_expired_token_is_refused(hs256):
    assert mcp_auth.verify(_token(exp=int(time.time()) - 60)) is None


def test_a_token_from_an_unknown_issuer_is_refused(hs256):
    """Right audience, right signature, wrong `iss`: refused. The issuer
    is the one claim that names the project, and the JWKS path trusts
    whatever key that document vouches for."""
    assert mcp_auth.verify(_token(iss="https://evil.example.com/auth/v1")) is None
    # and a token with no issuer at all does not slip through either
    tok = pyjwt.encode({"sub": "u", "aud": RESOURCE, "exp": int(time.time()) + 60},
                       JWT_SECRET, algorithm="HS256")
    assert mcp_auth.verify(tok) is None


def test_a_forged_signature_is_refused(hs256):
    assert mcp_auth.verify(_token(secret="x" * 48)) is None
    assert mcp_auth.verify("not.a.jwt") is None


def test_the_jwks_path_verifies_the_projects_key_and_nobody_elses(site, monkeypatch):
    """No shared secret configured: the token is checked against the
    project's JWKS. The fetch is stood in for at `jwt.PyJWKClient` (the
    network is blocked in tests), answering the project's public key for
    every kid -- so a token signed by another key fails on the signature,
    which is the only way it can fail once the key lookup is stubbed."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    site.delenv("SUPABASE_JWT_SECRET", raising=False)
    project_key = ec.generate_private_key(ec.SECP256R1())
    other_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = project_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    class _Key:
        key = public_pem

    class _Client:
        def __init__(self, url):
            assert url == "https://proj.supabase.co/auth/v1/.well-known/jwks.json"

        def get_signing_key_from_jwt(self, token):
            return _Key()

    monkeypatch.setattr(pyjwt, "PyJWKClient", _Client)

    def pem(k):
        return k.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption())

    assert mcp_auth.verify(_token(secret=pem(project_key), alg="ES256"))["sub"] == "user-a"
    assert mcp_auth.verify(_token(secret=pem(other_key), alg="ES256")) is None
    assert mcp_auth.verify(_token(secret=pem(project_key), alg="ES256",
                                  aud="https://other.example.com/mcp")) is None
    assert mcp_auth.verify(_token(secret=pem(project_key), alg="ES256",
                                  exp=int(time.time()) - 5)) is None


def test_account_for_token_is_the_oldest_membership_or_a_named_refusal(hs256, pg):
    """The resolver end to end on a real schema: an unverifiable token is
    `invalid_token`, a verified stranger is `no_account` (never a
    fall-through to the operator), and a member resolves to min(id) --
    the same rule auth.current_account_id uses."""
    from conftest import seed_two

    from src import accounts

    seeded = seed_two("mike@example.com", dsn=pg)
    uid = seeded["user_id"]
    assert mcp_auth.account_for_token("garbage", dsn=pg) == (None, "invalid_token")
    assert mcp_auth.account_for_token(_token(sub="nobody-yet"), dsn=pg) == (None, "no_account")
    account_id, reason = mcp_auth.account_for_token(_token(sub=uid), dsn=pg)
    assert reason == "ok"
    assert account_id == min(a["id"] for a in accounts.memberships(uid, dsn=pg))


# ---------- the rate limit ----------

def _limited_app(limiter, resolve, secret="static"):
    inner, seen = _capturing()
    return mcp_mount.guarded(inner, secret, resolve=resolve, limiter=limiter), seen


def _status(app, header):
    return _drive(app, header)


def _drive_full(app, header):
    """(status, headers) for one request."""
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(app({"type": "http", "method": "POST", "path": "/",
                     "headers": [(b"authorization", header.encode())]},
                    receive, send))
    start = sent[0]
    return start["status"], {k.decode(): v.decode() for k, v in start.get("headers", [])}


def test_a_caller_over_the_limit_gets_429_with_retry_after(monkeypatch):
    monkeypatch.setenv(mcp_mount.RATE_ENV, "3")
    limiter = mcp_mount.RateLimiter(clock=lambda: 1000.0)
    app, seen = _limited_app(limiter, resolve=lambda t: (4, "ok"))
    for _ in range(3):
        assert _status(app, "Bearer alice") == 200
    status, headers = _drive_full(app, "Bearer alice")
    assert status == 429
    assert int(headers["retry-after"]) >= 1
    # the refused call never reached the server
    assert seen == [4, 4, 4]


def test_another_account_is_unaffected(monkeypatch):
    monkeypatch.setenv(mcp_mount.RATE_ENV, "2")
    limiter = mcp_mount.RateLimiter(clock=lambda: 1000.0)
    people = {"alice": 4, "bob": 9}
    app, seen = _limited_app(limiter, resolve=lambda t: (people[t], "ok"))
    assert [_status(app, "Bearer alice") for _ in range(3)] == [200, 200, 429]
    assert [_status(app, "Bearer bob") for _ in range(2)] == [200, 200]
    assert seen == [4, 4, 9, 9]


def test_the_window_resets(monkeypatch):
    monkeypatch.setenv(mcp_mount.RATE_ENV, "1")
    now = [1000.0]
    limiter = mcp_mount.RateLimiter(clock=lambda: now[0])
    app, _ = _limited_app(limiter, resolve=lambda t: (4, "ok"))
    assert _status(app, "Bearer alice") == 200
    assert _status(app, "Bearer alice") == 429
    now[0] += mcp_mount.RATE_WINDOW_S
    assert _status(app, "Bearer alice") == 200


def test_the_operator_key_has_its_own_higher_bucket(monkeypatch):
    """Subject to the limit too -- a leaked key must not be unlimited --
    but counted apart from any account and at the operator default."""
    monkeypatch.setenv(mcp_mount.RATE_ENV, "1")
    monkeypatch.setenv(mcp_mount.RATE_OPERATOR_ENV, "2")
    limiter = mcp_mount.RateLimiter(clock=lambda: 1000.0)
    app, _ = _limited_app(limiter, resolve=lambda t: (4, "ok"))
    assert _status(app, "Bearer alice") == 200
    assert _status(app, "Bearer alice") == 429
    assert [_status(app, "Bearer static") for _ in range(3)] == [200, 200, 429]


def test_a_bad_limit_setting_falls_back_to_the_default_never_to_unlimited(monkeypatch):
    monkeypatch.setenv(mcp_mount.RATE_ENV, "lots")
    assert mcp_mount._rate(mcp_mount.RATE_ENV, 7) == 7
    monkeypatch.setenv(mcp_mount.RATE_ENV, "0")
    assert mcp_mount._rate(mcp_mount.RATE_ENV, 7) == 7
    monkeypatch.setenv(mcp_mount.RATE_ENV, "42")
    assert mcp_mount._rate(mcp_mount.RATE_ENV, 7) == 42


def test_an_unauthenticated_caller_is_refused_before_any_bucket_is_touched():
    limiter = mcp_mount.RateLimiter(clock=lambda: 1000.0)
    app, _ = _limited_app(limiter, resolve=lambda t: (None, "invalid_token"))
    assert _status(app, "Bearer nonsense") == 401
    assert limiter._windows == {}


# ---------- isolation, tool by tool, through the real transport ----------

def _listed_names(body: str) -> list:
    """Tool names off the SSE reply of one tools/list."""
    import json

    for line in body.splitlines():
        if line.startswith("data:"):
            result = json.loads(line[len("data:"):]).get("result") or {}
            return [t["name"] for t in result.get("tools", [])]
    return []


def _reply(body: str):
    """(is_error, payload) off the SSE reply of one tools/call."""
    import json

    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[len("data:"):])
        if "error" in payload:
            return True, payload["error"]
        result = payload.get("result") or {}
        text = next((c["text"] for c in result.get("content") or []
                     if c.get("type") == "text"), "")
        if result.get("isError"):
            return True, text
        # the studio surface (the operator's door) answers typed
        if isinstance(result.get("structuredContent"), dict):
            return False, result["structuredContent"]
        try:
            return False, json.loads(text)
        except ValueError:
            return False, text
    return True, body


@pytest.fixture
def two_people(pg, env, monkeypatch):
    """Alice (account a) and Bob (account b), each with one concept and
    one banked spark, behind the REAL mount: the resolver maps a bearer
    token to the account the way account_for_token would after a
    verified sign-in, and every tool runs against the throwaway schema."""
    pytest.importorskip("mcp")
    pytest.importorskip("httpx")
    from app import mcp_auth as auth_module
    from src import accounts, preprod, scout

    preprod.init(pg)
    scout.init(pg)
    seeded = accounts.seed("alice@example.com", dsn=pg)
    a = seeded["accounts"][0]
    # Bob's own workspace, the way seed_two makes a second one (the open
    # sign-up path is a separate test; what matters here is two tenants)
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob",
                         claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    assert a != b
    (a_concept,) = preprod.save_concept_ideas(
        [{"title": "Alice's concept", "hook": "h", "logline": ""}],
        brand="zeropage", dsn=pg, account_id=a)
    (b_concept,) = preprod.save_concept_ideas(
        [{"title": "Bob's concept", "hook": "h", "logline": ""}],
        brand="zeropage", dsn=pg, account_id=b)
    b_finding = scout.record("zeropage", {"spark": "Bob's private direction",
                                          "rationale": "", "evidence": "",
                                          "sources": [], "score": 1.0},
                             lanes="human", dsn=pg)

    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "operator-key")
    monkeypatch.setenv(mcp_mount.HOSTS_ENV, "*")
    people = {"alice": a, "bob": b}
    monkeypatch.setattr(
        auth_module, "account_for_token",
        lambda token, dsn=None: (people[token], "ok") if token in people
        else (None, "invalid_token"))

    jobs = {1: {"id": 1, "status": "done", "label": "bob's job", "account_id": b}}

    def job_status(job_id, account_id=None):
        job = jobs.get(job_id)
        return job if job and job["account_id"] == account_id else None

    approved: list = []

    def fake_render(concept_id, account_id, body):
        approved.append(("clip", concept_id, account_id, body))
        return {"job_id": 42, "render": {"provider": "fal"}}

    def fake_keyframes(concept_id, account_id):
        approved.append(("keyframes", concept_id, account_id))
        return {"ok": True, "job_id": 43}

    app, sessions = mcp_mount.build(dsn=pg, job_status=job_status,
                                    approve_render=fake_render,
                                    approve_keyframes=fake_keyframes)
    assert app is not None
    return {"app": app, "sessions": sessions, "a": a, "b": b,
            "a_concept": a_concept, "b_concept": b_concept,
            "b_finding": b_finding, "approved": approved}


def _calls(world, calls):
    """Run [(token, tool, args), ...] through the transport in one
    session-manager run; returns [(is_error, payload), ...]."""
    import httpx

    async def go():
        out = []
        async with world["sessions"].run():
            transport = httpx.ASGITransport(app=world["app"])
            async with httpx.AsyncClient(
                    transport=transport,
                    base_url="https://zeropage-studio.fly.dev") as client:
                for n, (token, name, args) in enumerate(calls, 1):
                    reply = await client.post("/", headers={
                        "authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": n, "method": "tools/call",
                              "params": {"name": name, "arguments": args}})
                    out.append(_reply(reply.text))
        return out

    return asyncio.run(go())


def test_another_persons_scene_is_indistinguishable_from_missing(two_people, pg):
    """`quote` and a `write_scene` rewrite on Bob's scene id, as Alice: the
    same "no scene" a nonexistent id gets, never Bob's row, never a crash --
    and nothing Alice tried changed it."""
    from src import preprod

    w = two_people
    bid = w["b_concept"]
    scene = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact "
             "face. Style: soft window light. (0-4s) Sam lifts the lid of a dented tin. "
             "(4-10s) Hard cut: Sam backs away from the open door. Avoid: plastic sheen.")
    results = _calls(w, [
        ("alice", "quote", {"scene_id": bid}),
        ("alice", "write_scene", {"prompt": scene, "scene_id": bid}),
        ("alice", "quote", {"scene_id": 987654}),
    ])
    for is_error, payload in results:
        assert is_error, payload
        assert "Bob" not in str(payload)
    assert f"no scene {bid}" in results[0][1] and f"no scene {bid}" in results[1][1]
    assert "no scene 987654" in results[2][1]
    theirs = preprod.get_concept(bid, dsn=pg, account_id=w["b"])
    assert theirs["title"] == "Bob's concept" and theirs["shots"] == []


def test_the_board_tools_are_gone_from_both_doors(two_people):
    """No idea board (2026-10-11): `board`, `idea`, `search`, `capture`,
    `pick`, `shoot`, `archive`, `stats` answer as unknown tools to a
    signed-in person AND to the operator's key -- and so do the spark
    bank's, which read a table every account shares."""
    w = two_people
    # (`search` is a listed tool again since the overnight build's PR 3 -- a
    # search of the whole studio, src/search.py -- so it is not in this list)
    gone = ("board", "idea", "capture", "pick", "shoot", "archive", "stats",
            "sparks", "tonight", "add_spark", "images", "reference", "research", "generate")
    results = _calls(w, [(who, tool, {}) for who in ("alice", "operator-key") for tool in gone])
    for (is_error, payload), (who, tool) in zip(
            results, [(who, tool) for who in ("alice", "operator-key") for tool in gone]):
        assert is_error, (who, tool, payload)
        assert "Bob's private direction" not in str(payload)
        assert "Bob's concept" not in str(payload) and "Alice's concept" not in str(payload)


def test_another_persons_job_is_no_job(two_people):
    w = two_people
    (e1, p1), (e2, p2) = _calls(w, [("alice", "job", {"job_id": 1}),
                                    ("bob", "job", {"job_id": 1})])
    assert e1 and "no job 1" in p1
    assert not e2 and p2["label"] == "bob's job"


def test_the_operator_key_still_reads_the_bootstrap_account(two_people, pg):
    """Alice's account is the seeded (oldest) one, which is what the
    static key resolves to -- the pre-OAuth behaviour, unchanged. It
    reaches the STUDIO surface now, and reads that account's rows there."""
    from src import projects
    projects.init(pg)
    w = two_people
    projects.create("Alice's ad", "", pg, account_id=w["a"])
    projects.create("Bob's short", "", pg, account_id=w["b"])
    (e, listed), = _calls(w, [("operator-key", "projects", {})])
    assert not e and [p["title"] for p in listed["projects"]] == ["Alice's ad"]


def test_only_the_listed_servers_report_a_credit_balance(two_people):
    """Until the overnight connector build (PR 3) no tool on either server
    answered "what can I spend" on its own. `balance` is on BOTH listings
    now (the task's call: credits, lots and expiry, the plan -- in credits
    only); the studio surface still has none, its quotes say the balance
    beside the price."""
    import asyncio as _asyncio

    from src import mcp_server

    studio = {t.name for t in _asyncio.run(
        mcp_server.build_server(dsn=":memory:").list_tools())}
    assert not {"balance", "credits", "wallet"} & studio
    for listed in (True, "claude"):
        names = {t.name for t in _asyncio.run(
            mcp_server.build_server(dsn=":memory:", listed=listed).list_tools())}
        assert "balance" in names and not {"credits", "wallet"} & names


def test_a_signed_in_caller_lists_exactly_the_listed_set(two_people):
    import httpx

    w = two_people

    async def names_for(token):
        async with w["sessions"].run():
            transport = httpx.ASGITransport(app=w["app"])
            async with httpx.AsyncClient(
                    transport=transport,
                    base_url="https://zeropage-studio.fly.dev") as client:
                out = {}
                for tok in token:
                    reply = await client.post("/", headers={
                        "authorization": f"Bearer {tok}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
                    out[tok] = _listed_names(reply.text)
                return out

    listed = asyncio.run(names_for(["alice", "operator-key"]))
    assert listed["alice"] == list(mcp_server.LISTED_TOOLS)
    # the operator's key reaches the studio surface -- without `import_file`,
    # which would read the web server's own disk, and without `cancel_job`
    # here only because this fixture injects no cancel
    operator = set(listed["operator-key"])
    assert operator == set(mcp_server.STUDIO_TOOLS) - {"import_file", "cancel_job"}
    assert {"generate_image", "generate_video", "apply_effect"} <= operator
    # the listed scene path is the listed server's alone, and neither door
    # has a board or a spark bank
    assert not operator & {"write_scene", "quote", "approve"}
    for names in (operator, set(listed["alice"])):
        assert not names & {"board", "pick", "capture", "stats", "sparks", "imagine_reference"}


# ---------- what an external caller sees ----------

def test_what_an_external_caller_sees_with_the_engine_off(env, monkeypatch):
    """The exact tool set a signed-in, non-operator caller is offered by
    the mount as deployed (engine off, job registry injected), and that
    every one of them carries the annotations the directory checks."""
    pytest.importorskip("mcp")
    monkeypatch.delenv(mcp_server.ENGINE_ENV, raising=False)
    app, _ = mcp_mount.build(dsn=":memory:", job_status=lambda i, account_id=None: None)
    assert app is not None
    server = mcp_server.build_server(dsn=":memory:", listed=True,
                                     job_status=lambda i, account_id=None: None)
    tools = asyncio.run(server.list_tools())
    names = [t.name for t in tools]
    # `approve` registers only when the approve bodies are injected, which
    # the mount does and this bare build does not
    assert names == [n for n in mcp_server.LISTED_TOOLS if n != "approve"]
    # (`search` is a listed tool again since the overnight build's PR 3: a
    # search of the whole studio, not the board's idea search)
    for absent in ("research", "generate", "sparks", "tonight", "add_spark", "images",
                   "reference", "imagine_reference", "images_for",
                   "board", "idea", "capture", "pick", "shoot", "archive", "stats"):
        assert absent not in names
    # and the engine flag changes nothing on the listed server
    monkeypatch.setenv(mcp_server.ENGINE_ENV, "1")
    again = mcp_server.build_server(dsn=":memory:", listed=True)
    assert "generate" not in {t.name for t in asyncio.run(again.list_tools())}
    for t in tools:
        assert t.title, t.name
        assert t.annotations is not None
        assert t.annotations.read_only_hint in (True, False)
        assert t.annotations.destructive_hint in (True, False)
        assert t.annotations.idempotent_hint in (True, False)
        assert t.annotations.open_world_hint in (True, False)
        if not t.annotations.read_only_hint:
            # a write says whether it can be undone
            assert t.annotations.destructive_hint is not None


def test_writing_a_scene_stays_in_the_callers_account(two_people, pg, monkeypatch):
    """The first half of the render path through the real transport, as
    Alice: elements -> write_scene, which MAKES the scene, in her project.
    Bob can neither file into her project nor use her photo, and what
    Alice made does not exist for him."""
    from src import asset_shelf, preprod, projects

    w = two_people
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.delenv("QUOTE_SIGNING_SECRET", raising=False)
    projects.init(pg)
    pid = projects.create("Alice's ad", "cold light", pg, account_id=w["a"])["id"]
    # Alice owns one character with one photo; Bob owns nothing
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "",
                          "photos": ["/characters/sam/photo/face.jpg"]}]
                        if account_id == w["a"] else [])
    scene = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact "
             "face. Style: soft window light, true colour. (0-4s) Sam lifts the lid of "
             "a dented tin and freezes. (4-10s) Hard cut to the hallway: Sam backs away "
             "from the open door, the tin still in one hand. No background music. "
             "Avoid: plastic sheen, cartoon reactions.")
    face = "/characters/sam/photo/face.jpg"
    (e0, els), (e1, written), (e2, foreign), (e3, bob_els) = _calls(w, [
        ("alice", "elements", {}),
        ("alice", "write_scene", {"prompt": scene, "seconds": 10, "refs": [face],
                                  "title": "The Tin", "project_id": pid}),
        # Bob cannot file into Alice's project, nor use her photo
        ("bob", "write_scene", {"prompt": scene, "refs": [face], "project_id": pid}),
        ("bob", "elements", {}),
    ])
    assert not e0 and els["elements"][0]["photos"][0]["ref"] == face
    assert not e1 and written["shots_written"] == 2 and written["seconds"] == 10
    assert written["project_id"] == pid and written["status"] == "written"
    sid = written["scene_id"]
    assert e2 and ("not one of your elements" in foreign or f"no project {pid}" in foreign)
    assert not e3 and bob_els["count"] == 0 and "upload" in bob_els["note"]
    # the scene is Alice's, in her project, and Bob made nothing
    assert preprod.get_concept(sid, dsn=pg, account_id=w["a"])["project_id"] == pid
    assert preprod.get_concept(sid, dsn=pg, account_id=w["b"]) is None
    assert [c["title"] for c in preprod.list_concepts(dsn=pg, account_id=w["b"])] == \
        ["Bob's concept"]


def test_quoting_and_approving_stay_in_the_callers_account(two_people, pg, monkeypatch):
    """quote -> approve as Alice on her own scene (no pick first), with the
    approve bodies handed HER account id; the same scene is 'no scene' to
    Bob. The scene is made up front: the transport's session manager runs
    once per test."""
    from src import asset_shelf, preprod

    w = two_people
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.delenv("QUOTE_SIGNING_SECRET", raising=False)
    face = "/characters/sam/photo/face.jpg"
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "", "photos": [face]}]
                        if account_id == w["a"] else [])
    scene = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact "
             "face. Style: soft window light, true colour. (0-4s) Sam lifts the lid of "
             "a dented tin and freezes. (4-10s) Hard cut to the hallway: Sam backs away "
             "from the open door, the tin still in one hand. Avoid: plastic sheen.")
    sid = mcp_server.write_scene(scene, refs=[face], dsn=pg, account_id=w["a"])["scene_id"]
    (e4, quoted), (e5, qforeign), (e6, clip), (e7, stills) = _calls(w, [
        ("alice", "quote", {"scene_id": sid}),
        ("bob", "quote", {"scene_id": sid}),
        ("alice", "approve", {"scene_id": sid, "what": "clip", "provider": "fal"}),
        ("alice", "approve", {"scene_id": sid, "what": "keyframes"}),
    ])
    assert not e4 and quoted["clip"]["timed"] is True and len(quoted["clip"]["renders"]) == 2
    assert quoted["keyframes"]["stills"] == 2 and quoted["balance"] is not None
    assert quoted["scene_id"] == sid and "picked" not in quoted
    assert e5 and f"no scene {sid}" in qforeign
    assert not e6 and clip["job_id"] == 42
    assert not e7 and stills["job_id"] == 43
    assert [(kind, cid, acct) for kind, cid, acct, *rest in w["approved"]] == \
        [("clip", sid, w["a"]), ("keyframes", sid, w["a"])]
    assert w["approved"][0][3]["provider"] == "fal"
    # nothing was picked on the way: the real approve body is what stamps it
    assert preprod.get_concept(sid, dsn=pg, account_id=w["a"])["picked"] is False


def _claude_calls(world, calls, path="/claude/"):
    """`_calls`, through the Claude directory's path (/mcp/claude)."""
    import httpx

    async def go():
        out = []
        async with world["sessions"].run():
            transport = httpx.ASGITransport(app=world["app"])
            async with httpx.AsyncClient(
                    transport=transport,
                    base_url="https://zeropage-studio.fly.dev") as client:
                for n, (token, method, params) in enumerate(calls, 1):
                    reply = await client.post(path, headers={
                        "authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": n, "method": method,
                              **({"params": params} if params is not None else {})})
                    out.append(reply.text)
        return out

    return asyncio.run(go())


def test_the_claude_path_lists_the_claude_set_for_every_door(two_people):
    """/mcp/claude is the Claude directory's listing: nothing that renders,
    whoever calls -- the operator's key sees exactly what a reviewer sees."""
    alice, operator = _claude_calls(two_people, [("alice", "tools/list", None),
                                                 ("operator-key", "tools/list", None)])
    assert _listed_names(alice) == _listed_names(operator) == \
        list(mcp_server.CLAUDE_LISTED_TOOLS)
    # `job` is there since the free edits (overnight PR 2); nothing that spends is
    assert "approve" not in _listed_names(alice) and "generate_image" not in _listed_names(alice)


def test_the_claude_listing_prices_and_hands_off_but_never_renders(two_people, pg,
                                                                   monkeypatch):
    """Through /mcp/claude as Alice: `scene` and `quote` on her own scene,
    the quote carrying the studio link and no tokens, `approve` refused as
    not a tool -- nothing reaches the approve bodies -- and Bob's view of
    her scene is 'no scene'."""
    from src import asset_shelf

    w = two_people
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-secret-for-quotes")
    monkeypatch.setenv("STUDIO_URL", "https://studio.example")
    face = "/characters/sam/photo/face.jpg"
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "", "photos": [face]}]
                        if account_id == w["a"] else [])
    scene = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact "
             "face. Style: soft window light, true colour. (0-4s) Sam lifts the lid of "
             "a dented tin and freezes. (4-10s) Hard cut to the hallway: Sam backs away "
             "from the open door, the tin still in one hand. Avoid: plastic sheen.")
    sid = mcp_server.write_scene(scene, refs=[face], dsn=pg, account_id=w["a"])["scene_id"]
    replies = _claude_calls(w, [
        ("alice", "tools/call", {"name": "scene", "arguments": {"scene_id": sid}}),
        ("alice", "tools/call", {"name": "quote", "arguments": {"scene_id": sid}}),
        ("alice", "tools/call", {"name": "approve",
                                 "arguments": {"scene_id": sid, "what": "clip"}}),
        ("bob", "tools/call", {"name": "scene", "arguments": {"scene_id": sid}}),
    ])
    (e1, read), (e2, quoted), (e3, approved), (e4, bobs) = [_reply(r) for r in replies]
    link = f"https://studio.example/studio/scene/{sid}"
    assert not e1 and read["studio_url"] == link and read["clips"] == []
    assert not e2 and quoted["approve_url"] == link
    assert "token" not in str(quoted["clip"]) and "signed" not in quoted["clip"]
    assert "estimate_usd" not in str(quoted)
    assert e3 and "approve" in str(approved)
    assert w["approved"] == []
    assert e4 and f"no scene {sid}" in bobs


def test_the_claude_path_challenges_with_its_own_metadata(monkeypatch):
    """A 401 on /mcp/claude names the Claude listing's own document, so a
    client that checks `resource` against the URL it dialled is satisfied."""
    from app import mcp_auth

    monkeypatch.setattr(mcp_auth.auth, "supabase_url", lambda: "https://abc.supabase.co")
    monkeypatch.setenv(mcp_auth.RESOURCE_ENV, "https://api.zeropage.studio/mcp")
    seen = {}

    async def app(scope, receive, send):  # never reached
        seen["reached"] = True

    wrapped = mcp_mount.guarded(app, "operator-key", claude_app=app,
                                resolve=lambda t: (None, "invalid_token"))
    for path, document in (("/mcp/", "/.well-known/oauth-protected-resource/mcp"),
                           ("/mcp/claude/",
                            "/.well-known/oauth-protected-resource/mcp/claude")):
        sent = []

        async def send(message):
            sent.append(message)

        asyncio.run(wrapped({"type": "http", "path": path, "root_path": "/mcp",
                             "headers": []}, None, send))
        headers = dict(sent[0]["headers"])
        assert sent[0]["status"] == 401
        assert headers[b"www-authenticate"].decode().endswith(f'{document}"')
    assert "reached" not in seen
    doc = mcp_auth.protected_resource_metadata(mcp_auth.CLAUDE_SUFFIX)
    assert doc["resource"] == "https://api.zeropage.studio/mcp/claude"


def test_the_bare_mount_path_is_served_not_redirected():
    """`/mcp` is the address the connector publishes (the OAuth resource), and
    Starlette's Mount alone answers it with a 307 to `/mcp/`, which claude.ai's
    "Add custom connector" check reads as "Not found" (2026-10-12). The
    middleware serves the bare path as the mount's root; `/mcp/claude` and
    everything else are untouched. The first client is the control: without
    the middleware the bare path redirects."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    seen = []

    async def mounted(scope, receive, send):
        seen.append((scope.get("root_path"), scope.get("path")))
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    plain = FastAPI()
    plain.mount(mcp_mount.MOUNT_PATH, mounted, name="mcp")
    control = TestClient(plain).post("/mcp", follow_redirects=False)
    assert control.status_code == 307 and control.headers["location"].endswith("/mcp/")

    fixed = FastAPI()
    fixed.mount(mcp_mount.MOUNT_PATH, mounted, name="mcp")
    fixed.add_middleware(mcp_mount.BareMountPath)
    client = TestClient(fixed)
    for method in ("post", "get", "delete"):
        reply = getattr(client, method)("/mcp", follow_redirects=False)
        assert reply.status_code == 401, (method, reply.status_code)
    assert client.post("/mcp/", follow_redirects=False).status_code == 401
    claude = client.post("/mcp/claude", follow_redirects=False)
    assert claude.status_code == 401
    # the bare path reached the mounted app as its root; the Claude sub-path as itself
    assert ("/mcp", "/mcp/") in seen and ("/mcp", "/mcp/claude") in seen
    # nothing else is rewritten
    assert client.get("/mcpx", follow_redirects=False).status_code == 404


def test_the_web_app_installs_the_bare_path_middleware(monkeypatch):
    """The real app, reloaded with the mount on: `/mcp` answers the guard's
    401 (with the OAuth challenge), never a 307. Restored on teardown the way
    test_dev_tools does."""
    import importlib

    pytest.importorskip("mcp")
    from fastapi.testclient import TestClient

    from app import main as app_main

    monkeypatch.setenv(mcp_mount.ENABLED_ENV, "1")
    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "test-token")
    module = importlib.reload(app_main)
    try:
        assert module.MCP_APP is not None
        client = TestClient(module.app)
        for path in ("/mcp", "/mcp/", "/mcp/claude"):
            reply = client.post(path, follow_redirects=False, json={})
            assert reply.status_code == 401, (path, reply.status_code)
            assert "www-authenticate" in {k.lower() for k in reply.headers}
    finally:
        monkeypatch.delenv(mcp_mount.ENABLED_ENV, raising=False)
        monkeypatch.delenv(mcp_mount.TOKEN_ENV, raising=False)
        importlib.reload(app_main)


def test_projects_and_their_chat_are_each_persons_own(two_people, pg):
    """The project tools on the listed door (2026-10-08): Alice's project
    and its chat are hers -- Bob lists none of it, and her id reads to him
    exactly like one that does not exist. One transport run (the session
    manager runs once), so Alice's project and its chat are made up front
    and `create_project` is called through the door alongside. `save_chat`
    is not on the listed door since 2026-10-11."""
    from src import projects
    projects.init(pg)
    w = two_people
    pid = projects.create("Alice's ad", "cold light", pg, account_id=w["a"])["id"]
    turns = [{"role": "user", "content": "colder"}, {"role": "assistant", "content": "ok"}]
    projects.append_turns(pid, turns, pg, account_id=w["a"])
    results = _calls(w, [
        ("alice", "save_chat", {"project_id": pid, "turns": turns}),
        ("alice", "project", {"project_id": pid}),
        ("bob", "create_project", {"title": "Bob's short"}),
        ("alice", "projects", {}),
        ("bob", "projects", {}),
        ("bob", "project", {"project_id": pid}),
        ("bob", "project_chat", {"project_id": pid}),
        ("bob", "save_chat", {"project_id": pid, "turns": turns}),
    ])
    (e1, saved), (e2, opened), (e3, bobs), (e4, mine), (e5, theirs) = results[:5]
    assert e1 and "save_chat" in str(saved)            # not offered here
    assert not (e2 or e3 or e4 or e5)
    assert [t["content"] for t in opened["chat"]] == ["colder", "ok"]
    assert [p["title"] for p in mine["projects"]] == ["Alice's ad"]
    assert [p["title"] for p in theirs["projects"]] == ["Bob's short"] == [bobs["title"]]
    for is_error, payload in results[5:7]:
        assert is_error and f"no project {pid}" in payload
        assert "Alice" not in str(payload) and "colder" not in str(payload)
    assert results[7][0] and "colder" not in str(results[7][1])
    assert len(projects.messages(pid, pg, account_id=w["a"])["items"]) == 2


# ---------- OpenAI's domain verification (2026-10-12) ----------------------

def test_the_openai_challenge_is_served_as_plain_text_only_when_set(monkeypatch):
    """OpenAI's plugin directory reads the token at
    /.well-known/openai-apps-challenge as plain text and nothing else; while
    none is set the path does not exist. app/main.py registers the function
    beside the OAuth discovery documents, only where the mount exists."""
    from fastapi import HTTPException

    assert mcp_auth.OPENAI_CHALLENGE_PATH == "/.well-known/openai-apps-challenge"
    monkeypatch.delenv(mcp_auth.OPENAI_CHALLENGE_ENV, raising=False)
    assert mcp_auth.openai_challenge() == ""
    with pytest.raises(HTTPException) as refused:
        mcp_mount.openai_challenge_endpoint()
    assert refused.value.status_code == 404
    monkeypatch.setenv(mcp_auth.OPENAI_CHALLENGE_ENV, " openai-apps-abc123 \n")
    response = mcp_mount.openai_challenge_endpoint()
    assert response.body == b"openai-apps-abc123"
    assert response.media_type == "text/plain"
    main_source = (PROJECT_ROOT / "app" / "main.py").read_text()
    assert "app.get(mcp_auth.OPENAI_CHALLENGE_PATH)(mcp_mount.openai_challenge_endpoint)" in main_source
