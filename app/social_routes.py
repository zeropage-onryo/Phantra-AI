"""
Connecting a social account (2026-10-22, docs/tasks/task-social-connections.md).

Two routers. `auth_router` is the OAuth door, on this origin's own
session like the rest of /auth:

    GET /auth/social/{provider}/start      signed in here -> the platform
    GET /auth/social/{provider}/callback   the platform -> a row -> the studio

`api_router` is what the settings page reads and presses, behind the
/api gate like every other route: the providers this server can connect,
the workspace's connections, a pending step's options and its pick, and
disconnect.

WHY THE DOOR IS ON THE API ORIGIN. A platform redirects to ONE registered
URL, and it has to be the server that holds the app secret -- this one.
So the settings page navigates the browser to `{AUTH_ORIGIN}/auth/social/
<p>/start` (a top-level navigation, the way sign-in and sign-out already
go to this origin), which needs this origin's session cookie. Signed out
here, it sends the person through /signin and back to the settings page.

THE STATE. `state` is signed under the session secret with its own salt
(the handoff's pattern), ten minutes, and names the workspace and the
person who started the connect, so the callback never has to trust a
cookie for whose row to write; the nonce inside it is ALSO kept in this
origin's starlette session and must match on the way back, so a start
URL lifted from one browser cannot finish in another (the OAuth-CSRF
that binds somebody else's account to your workspace). A bad state is a
404-shaped refusal, never a connection.

WHAT A FAILURE LOOKS LIKE. The person lands back on Settings → Connections
with `?error=<words>` (the provider's refusal, redacted, cut short) or
`?connected=<provider>&id=<n>` on success; a Discord connect lands with
`&pick=<n>` because the channel is still to choose. Nothing here spends,
posts, or reads the board.
"""
from __future__ import annotations

import secrets as _secrets
from typing import Any, Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel

from src import social, social_connections, upload_links
from src.social.base import ConnectRefused

from . import auth

auth_router = APIRouter(prefix="/auth/social")
api_router = APIRouter(prefix="/social")

STATE_SALT = "phantra-social-state"
STATE_MAX_AGE = 600                      # ten minutes to press Allow
STATE_SESSION_KEY = "social_connect_nonce"
SETTINGS_PATH = "/studio/settings/connections"
ERROR_MAX = 240
REDIRECT_ORIGIN_ENV = "SOCIAL_REDIRECT_ORIGIN"


# --------------------------------------------------------------------------
# addresses
# --------------------------------------------------------------------------

def redirect_origin() -> str:
    """Where the platforms send the person back: SOCIAL_REDIRECT_ORIGIN,
    else the same origin the connector's upload page uses (the API's
    public origin on Fly). The exact URL goes into each developer app."""
    import os
    raw = (os.environ.get(REDIRECT_ORIGIN_ENV) or "").strip().rstrip("/")
    return raw or upload_links.page_origin()


def redirect_uri(provider: str) -> str:
    return f"{redirect_origin()}/auth/social/{provider}/callback"


def settings_url(**params: Any) -> str:
    """The studio's connections page, with the outcome in the query.
    STUDIO_URL on a deployment; the local Next dev server otherwise."""
    base = auth.studio_url() or "http://localhost:3000"
    query = {k: v for k, v in params.items() if v not in (None, "")}
    return f"{base}{SETTINGS_PATH}" + (("?" + urlencode(query)) if query else "")


# --------------------------------------------------------------------------
# the state
# --------------------------------------------------------------------------

def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(auth._session_secret(), salt=STATE_SALT)


def mint_state(account_id: int, user_id: Optional[str], provider: str, nonce: str) -> str:
    return _state_serializer().dumps({"a": int(account_id), "u": user_id or "",
                                      "p": provider, "n": nonce})


def read_state(token: str) -> Optional[dict[str, Any]]:
    """The payload, or None for anything stale, tampered or malformed."""
    try:
        data = _state_serializer().loads(token or "", max_age=STATE_MAX_AGE)
    except BadSignature:
        return None
    if not isinstance(data, dict) or not data.get("n") or not data.get("p"):
        return None
    try:
        data["a"] = int(data["a"])
    except (KeyError, TypeError, ValueError):
        return None
    return data


# --------------------------------------------------------------------------
# the door
# --------------------------------------------------------------------------

def _provider_or_404(provider: str):
    mod = social.get(provider)
    if mod is None:
        raise HTTPException(status_code=404, detail=f"no provider {provider!r}")
    return mod


@auth_router.get("/{provider}/start")
def social_start(provider: str, request: Request):
    """Signed in on this origin -> the platform's consent screen."""
    mod = _provider_or_404(provider)
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse(
            f"/signin?next={quote(settings_url(), safe='')}", status_code=303)
    try:
        account_id = auth.current_account_id(request)
    except HTTPException:
        # signed in, no workspace yet: the gate's own page says so
        return RedirectResponse(settings_url(error="Sign in to a workspace first."), status_code=303)
    if not mod.configured():
        return RedirectResponse(settings_url(error=f"{mod.NAME} is not set up on this server yet."),
                                status_code=303)
    if not social_connections.vault_ready():
        return RedirectResponse(settings_url(error="This server has no secret to store a token "
                                                   "under (SOCIAL_TOKEN_SECRET)."), status_code=303)
    nonce = _secrets.token_urlsafe(16)
    request.session[STATE_SESSION_KEY] = nonce
    state = mint_state(account_id, user.get("id"), provider, nonce)
    try:
        url = mod.auth_url(redirect_uri(provider), state)
    except ConnectRefused as e:
        return RedirectResponse(settings_url(error=str(e)[:ERROR_MAX]), status_code=303)
    return RedirectResponse(url, status_code=303)


@auth_router.get("/{provider}/callback")
def social_callback(provider: str, request: Request, code: Optional[str] = None,
                    state: Optional[str] = None, error: Optional[str] = None,
                    error_description: Optional[str] = None):
    """The platform sent the person back. Finish or refuse, then land on
    the settings page either way -- a person never sees a JSON error
    from a redirect."""
    mod = _provider_or_404(provider)
    data = read_state(state or "")
    expected = request.session.pop(STATE_SESSION_KEY, None)
    if data is None or data.get("p") != provider or not expected or data["n"] != expected:
        return RedirectResponse(settings_url(error="That connect link is not valid any more. "
                                                   "Start again from this page."), status_code=303)
    if error or not code:
        said = (error_description or error or "The sign-in was cancelled.")[:ERROR_MAX]
        return RedirectResponse(settings_url(error=f"{mod.NAME}: {said}"), status_code=303)
    account_id = data["a"]
    try:
        found = mod.authenticate(code, redirect_uri(provider), dict(request.query_params))
        row = social_connections.save(account_id, provider, found,
                                      connected_by=data.get("u") or None)
    except (ConnectRefused, social_connections.VaultError) as e:
        return RedirectResponse(settings_url(error=str(e)[:ERROR_MAX]), status_code=303)
    params: dict[str, Any] = {"connected": provider, "id": row["id"]}
    if row.get("pending"):
        params["pick"] = row["id"]
    return RedirectResponse(settings_url(**params), status_code=303)


# --------------------------------------------------------------------------
# the settings page's routes
# --------------------------------------------------------------------------

def _refused(e: Exception, status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": "connect_refused", "message": str(e)}})


@api_router.get("/providers")
def social_providers(account_id: int = Depends(auth.current_account_id)):
    """Every platform the studio can connect, whether THIS server has its
    app keys, and the address a Connect button navigates to."""
    out = []
    for p in social.catalogue():
        p["start_url"] = f"/auth/social/{p['id']}/start"
        p["redirect_uri"] = redirect_uri(p["id"])
        out.append(p)
    return {"providers": out, "vault_ready": social_connections.vault_ready()}


@api_router.get("/connections")
def social_list(account_id: int = Depends(auth.current_account_id)):
    social_connections.ensure()
    return {"connections": social_connections.list_for(account_id)}


@api_router.get("/connections/{connection_id}/options")
def social_options(connection_id: int, account_id: int = Depends(auth.current_account_id)):
    try:
        return {"options": social_connections.options(account_id, connection_id)}
    except ConnectRefused as e:
        return _refused(e)


class PickBody(BaseModel):
    choice: str


@api_router.post("/connections/{connection_id}/pick")
def social_pick(connection_id: int, body: PickBody,
                account_id: int = Depends(auth.current_account_id)):
    try:
        return social_connections.pick(account_id, connection_id, body.choice)
    except ConnectRefused as e:
        return _refused(e)


class PostingTimesBody(BaseModel):
    """{"tz": "America/New_York", "days": {"mon": ["09:00", "18:30"], ...}}"""
    tz: str = "UTC"
    days: dict[str, list[str]]


@api_router.get("/connections/{connection_id}/posting-times")
def social_posting_times(connection_id: int, account_id: int = Depends(auth.current_account_id)):
    row = social_connections.get(account_id, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no such connection")
    return {"posting_times": row["posting_times"]}


@api_router.put("/connections/{connection_id}/posting-times")
def social_set_posting_times(connection_id: int, body: PostingTimesBody,
                             account_id: int = Depends(auth.current_account_id)):
    """The hours this account likes to post, by weekday, in its own zone
    (2026-10-22, docs/tasks/task-calendar.md). Nothing is sent by them;
    the calendar and the drawer read them."""
    try:
        return social_connections.set_posting_times(account_id, connection_id,
                                                    {"tz": body.tz, "days": body.days})
    except ConnectRefused as e:
        return _refused(e)


@api_router.delete("/connections/{connection_id}")
def social_disconnect(connection_id: int, account_id: int = Depends(auth.current_account_id)):
    if not social_connections.remove(account_id, connection_id):
        raise HTTPException(status_code=404, detail="no such connection")
    return {"ok": True, "id": connection_id}
