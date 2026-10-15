"""Pages that must never be framed, and whether cookies are https-only.

Security review S10 (2026-10-15). The pages where a person types a
password, says yes to a connector or picks a file are exactly the pages a
clickjacking frame wants: an invisible /oauth/consent over a "play" button
is a connector granted without the person knowing. None of them had any
framing policy. `NoFraming` adds BOTH the modern header
(`Content-Security-Policy: frame-ancestors 'none'`) and the legacy one
(`X-Frame-Options: DENY`) to every response under those paths -- a pure
ASGI middleware, so it covers redirects and error pages too, and it never
overwrites a policy a route set itself.

`session_https_only()` is the Starlette session cookie's `Secure` flag
(Authlib's OAuth state rides on it): on for a real deployment, off for
local http dev and the test client, which would never send a Secure
cookie back over http://testserver.
"""
from __future__ import annotations

import os

# Exact paths and their sub-paths. `/u/` is the one-time upload page
# (src/upload_links.PAGE_PATH); `/auth/` is every sign-in, code, reset
# and callback route (app/auth.py's router prefix).
NO_FRAME_PATHS = ("/signin", "/auth", "/oauth/consent", "/u")

CSP_VALUE = b"frame-ancestors 'none'"
XFO_VALUE = b"DENY"

HTTPS_ONLY_ENV = "PHANTRA_SESSION_HTTPS_ONLY"


def no_frame(path: str) -> bool:
    """Whether `path` is one of the never-framed pages: the path itself
    or anything below it, never a sibling that merely shares a prefix
    (`/ui` is not `/u`, `/authors` is not `/auth`)."""
    for root in NO_FRAME_PATHS:
        if path == root or path.startswith(root + "/"):
            return True
    return False


class NoFraming:
    """ASGI middleware: the two anti-framing headers on `no_frame` paths."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not no_frame(scope.get("path") or ""):
            await self.app(scope, receive, send)
            return

        async def framed(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers") or [])
                names = {k.lower() for k, _ in headers}
                if b"content-security-policy" not in names:
                    headers.append((b"content-security-policy", CSP_VALUE))
                if b"x-frame-options" not in names:
                    headers.append((b"x-frame-options", XFO_VALUE))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, framed)


def session_https_only() -> bool:
    """Whether the session cookie is marked Secure.

    `PHANTRA_SESSION_HTTPS_ONLY` ("1"/"0") decides when it is set (the
    test suite sets "0"). Otherwise: on when this is a real deployment --
    Fly sets `FLY_APP_NAME` on every machine, and a deployment whose
    public name (`SITE_URL`, or `PHANTRA_MCP_RESOURCE`, which is what Fly
    actually carries) is https is served over https. Local dev, with
    neither, stays on plain http."""
    explicit = (os.environ.get(HTTPS_ONLY_ENV) or "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False
    if (os.environ.get("FLY_APP_NAME") or "").strip():
        return True
    return any((os.environ.get(name) or "").strip().lower().startswith("https://")
               for name in ("SITE_URL", "PHANTRA_MCP_RESOURCE"))
