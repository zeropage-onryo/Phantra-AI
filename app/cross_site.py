"""Refuse a write another site's page makes with the person's session.

QA 2026-11-02, E1. On https the session cookie is `SameSite=None; Secure`
(app/auth.issue_session: a front end on another origin reads it through a
credentialed fetch), so the browser attaches it to a form another site
posts at this API. A plain multipart form from evil.example got 200 on
`POST /api/direct/image/run` (10 credits held and settled) and on
`POST /api/assets/generated/{id}/share` (a render made public). The
mutation header (`model_connections.mutation_header`) guarded 14 routes
only.

`CrossSiteWrites` is one rule for every route instead of a header per
route. A request that writes (anything but GET, HEAD and OPTIONS) AND
carries the session cookie is refused, 403 `cross_site`, before any route
runs, when the browser says it came from another site:

- `X-Phantra-Model-Connection: 1` always passes: a custom header forces a
  CORS preflight, so only a trusted origin can have sent it.
- `Sec-Fetch-Site` (every current browser sends it) passes `same-origin`,
  `same-site` (phantra.ai beside api.phantra.ai) and `none` (typed or
  bookmarked). `cross-site` passes only from an origin the CORS list
  trusts (`auth._origin_trusted`: FRONTEND_ORIGINS, STUDIO_URL, the
  preview regex), because that is a front end we run.
- With no `Sec-Fetch-Site`, `Origin` decides the same way: this host, or a
  trusted origin. `Origin: null` (a sandboxed frame, a data: page) is
  refused.
- With neither header the caller is not a browser page (curl, a script,
  the test client), and a forged cross-site request always comes from a
  browser, so it passes.

A request with no session cookie is untouched: bearer-token callers (the
connector, the panels, the bots) and the Stripe webhook never carry it.
The studio's own fetches reach the API through the Next proxy with their
own origin's headers, so they are same-origin here.
"""
from __future__ import annotations

import json
from typing import Optional
from urllib.parse import urlsplit

from . import auth

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PASSING_FETCH_SITES = frozenset({"same-origin", "same-site", "none"})

REFUSAL = {"error": {
    "code": "cross_site",
    "message": "This request came from another website, so it was refused. "
               "Open Phantra and try again there.",
}}


def _host_of(origin: str) -> Optional[str]:
    try:
        parts = urlsplit(origin)
    except ValueError:
        return None
    return parts.netloc.lower() or None


def refused(method: str, headers: dict, has_session: bool) -> bool:
    """Whether a request is a cross-site write made with the session.
    `headers` are lower-cased names; `host` is the request's own Host."""
    if method.upper() in SAFE_METHODS or not has_session:
        return False
    if headers.get("x-phantra-model-connection") == "1":
        return False
    origin = (headers.get("origin") or "").strip()
    site = (headers.get("sec-fetch-site") or "").strip().lower()
    if site:
        if site in PASSING_FETCH_SITES:
            return False
        return not (origin and auth._origin_trusted(origin.rstrip("/")))
    if not origin:
        return False
    if origin == "null":
        return True
    host = (headers.get("host") or "").lower()
    if host and _host_of(origin) == host:
        return False
    return not auth._origin_trusted(origin.rstrip("/"))


def _has_session(cookie_header: str) -> bool:
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == auth.SESSION_COOKIE and value:
            return True
    return False


class CrossSiteWrites:
    """ASGI middleware: `refused` requests get 403 `cross_site`."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers") or []}
        if not refused(scope.get("method") or "GET", headers,
                       _has_session(headers.get("cookie", ""))):
            await self.app(scope, receive, send)
            return
        body = json.dumps(REFUSAL).encode()
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
