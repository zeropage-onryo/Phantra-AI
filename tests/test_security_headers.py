"""Security review S10: the pages a clickjacking frame wants -- sign-in,
the connector's consent, the one-time upload page -- refuse to be framed,
and the session cookie is Secure on a real deployment only."""
import pytest
from fastapi.testclient import TestClient

from app import main, security_headers

FRAMING = ("content-security-policy", "x-frame-options")


@pytest.fixture
def client():
    return TestClient(main.app, follow_redirects=False)


@pytest.mark.parametrize("path", ["/signin", "/signin?mode=signup", "/oauth/consent",
                                  "/oauth/consent?authorization_id=x", "/u/not-a-token",
                                  "/auth/logout", "/auth/confirm"])
def test_the_auth_consent_and_upload_pages_refuse_to_be_framed(client, path):
    r = client.get(path)
    assert r.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert r.headers["x-frame-options"] == "DENY"


@pytest.mark.parametrize("path", ["/healthz", "/robots.txt"])
def test_other_pages_are_left_alone(client, path):
    r = client.get(path)
    assert not any(h in r.headers for h in FRAMING)


def test_the_path_match_is_by_segment_not_by_prefix():
    for path in ("/signin", "/signin/", "/auth/callback", "/oauth/consent", "/u/abc"):
        assert security_headers.no_frame(path)
    for path in ("/ui", "/ui/accounts", "/authors", "/oauth/consentx", "/signinx", "/",
                 "/api/me", "/mcp"):
        assert not security_headers.no_frame(path)


def test_a_route_that_sets_its_own_policy_keeps_it():
    import asyncio

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"Content-Security-Policy", b"frame-ancestors 'self'")]})
        await send({"type": "http.response.body", "body": b""})

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b""}

    asyncio.run(security_headers.NoFraming(inner)(
        {"type": "http", "path": "/signin", "headers": []}, receive, send))
    headers = sent[0]["headers"]
    assert [v for k, v in headers if k.lower() == b"content-security-policy"] == \
        [b"frame-ancestors 'self'"]
    assert (b"x-frame-options", b"DENY") in headers


@pytest.mark.parametrize("env,expected", [
    ({}, False),
    ({"SITE_URL": "http://127.0.0.1:8000"}, False),
    ({"SITE_URL": "https://phantra.ai"}, True),
    ({"PHANTRA_MCP_RESOURCE": "https://api.phantra.ai/mcp"}, True),
    ({"FLY_APP_NAME": "phantra-api"}, True),
    ({"FLY_APP_NAME": "phantra-api", "PHANTRA_SESSION_HTTPS_ONLY": "0"}, False),
    ({"PHANTRA_SESSION_HTTPS_ONLY": "1"}, True),
])
def test_the_session_cookie_is_secure_on_a_real_deployment(monkeypatch, env, expected):
    for name in ("SITE_URL", "PHANTRA_MCP_RESOURCE", "FLY_APP_NAME",
                 security_headers.HTTPS_ONLY_ENV):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    assert security_headers.session_https_only() is expected


def test_the_suite_runs_with_a_plain_session_cookie():
    from starlette.middleware.sessions import SessionMiddleware
    session = next(m for m in main.app.user_middleware if m.cls is SessionMiddleware)
    assert session.kwargs.get("https_only") is False
