"""
X: a member's own account (2026-10-25).

WHAT A CONNECTION IS. OAuth 2.0 with PKCE on a confidential client
(`SOCIAL_X_CLIENT_ID` / `_SECRET`, the OAuth 2.0 pair, not the v1.1
consumer keys), scopes `tweet.read tweet.write users.read media.write
offline.access`. The door hands a provider only `state`, so the PKCE
verifier is DERIVED from it (an HMAC under the client secret): the
callback carries the same state back and the verifier is derived again,
with nothing stored in between. The state is signed and single-use
(app/social_routes.py), so the verifier is too.

TOKENS. An access token lasts two hours; `offline.access` brings a refresh
token, which X ROTATES on every refresh (the old one stops working). The
row keeps the newest pair (`social_connections._renew`), and a lapsed
token with a refresh token is renewed on use, not shown as Expired.

WHAT A POST IS. `POST /2/tweets` with the words as `text` and, for a clip
or a still, one media id from the v2 chunked upload (initialize -> append
each 4 MB part -> finalize). A still is usually ready at finalize and
posts in `post_start`; a video comes back with `processing_info`, so
`post_start` leaves the row PENDING, `post_check` polls the upload's
status until `succeeded`, and `post_finish` creates the post.

WHO PAYS. Since 2026 a new X developer account is pay-per-use from
prepaid credit (docs/ops/social-apps.md): about $0.015 a post, more when
it carries a link. Phantra pays; with no credit X refuses every post,
and that refusal is shown on the post like any other.

Dated 2026-10-25 against X's OAuth 2.0 user-token guide, the v2 media
upload quickstart and POST /2/tweets.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, PostFailed, PostResult, Renewed

IDENTIFIER = "x"
NAME = "X"
CONNECTS = "your own X account"
SCOPES = ("tweet.read", "tweet.write", "users.read", "media.write", "offline.access")

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
API = "https://api.x.com"
TOKEN_URL = f"{API}/2/oauth2/token"
TOKEN_SECONDS = 2 * 3600

CLIENT_ID_ENV = "SOCIAL_X_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_X_CLIENT_SECRET"

CAPTION_MAX = 280
CHUNK_BYTES = 4 * 1024 * 1024           # X asks for at most 5 MB a part
UPLOAD_MAX_BYTES = 512 * 1024 * 1024
IMAGE_MAX_BYTES = 5 * 1024 * 1024
POST_HTTP_TIMEOUT = 120


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _request(method: str, url: str, **kw) -> requests.Response:
    """The raw call, for the one upload step that is multipart; a non-2xx
    raises like base.http does."""
    response = requests.request(method, url, timeout=kw.pop("timeout", base.HTTP_TIMEOUT), **kw)
    response.raise_for_status()
    return response


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV))


def _basic() -> dict[str, str]:
    pair = f"{_env(CLIENT_ID_ENV)}:{_env(CLIENT_SECRET_ENV)}".encode()
    return {"Authorization": "Basic " + base64.b64encode(pair).decode(),
            "Content-Type": "application/x-www-form-urlencoded"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def verifier_for(state: str) -> str:
    """The PKCE verifier for one connect: 43 characters, the same for the
    same state, unguessable without the client secret."""
    mac = hmac.new(_env(CLIENT_SECRET_ENV).encode(), b"x-pkce:" + (state or "").encode(),
                   hashlib.sha256).digest()
    return _b64url(mac)


def _challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode()).digest())


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("X is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": _env(CLIENT_ID_ENV),
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": _challenge(verifier_for(state)),
        "code_challenge_method": "S256",
    })


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    secret = _env(CLIENT_SECRET_ENV)
    verifier = verifier_for(str(query.get("state") or ""))
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri, "code_verifier": verifier,
        }, headers=_basic())
    except requests.RequestException as e:
        raise ConnectRefused("X did not accept the sign-in: " + base.problem(e, secret, code, verifier))
    access = tok.get("access_token") or ""
    if not access:
        raise ConnectRefused("X sent no token back.")
    granted = set((tok.get("scope") or "").split())
    missing = [s for s in ("tweet.write", "media.write") if granted and s not in granted]
    if missing:
        raise ConnectRefused("X was connected without permission to post. Connect again and allow it.")
    try:
        me = _http("GET", f"{API}/2/users/me", params={"user.fields": "profile_image_url,username,name"},
                   headers={"Authorization": f"Bearer {access}"})
    except requests.RequestException as e:
        raise ConnectRefused("X did not say who you are: " + base.problem(e, access))
    user = me.get("data") or {}
    user_id = str(user.get("id") or "")
    if not user_id:
        raise ConnectRefused("X did not say who you are.")
    username = str(user.get("username") or "")
    return Connected(
        external_id=user_id,
        display_name=str(user.get("name") or username or f"X {user_id}"),
        handle=username,
        avatar_url=str(user.get("profile_image_url") or ""),
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=int(tok.get("expires_in") or TOKEN_SECONDS),
        scopes=sorted(granted) or list(SCOPES),
        meta={"user_id": user_id, "username": username},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """A new pair; X rotates the refresh token, so the answer's replaces it."""
    if not refresh_token:
        return None
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "refresh_token", "refresh_token": refresh_token,
        }, headers=_basic())
    except requests.RequestException as e:
        raise ConnectRefused("X did not renew the connection: "
                             + base.problem(e, refresh_token, access_token, _env(CLIENT_SECRET_ENV)))
    new = tok.get("access_token") or ""
    if not new:
        return None
    return Renewed(access_token=new, refresh_token=tok.get("refresh_token") or refresh_token,
                   expires_in=int(tok.get("expires_in") or TOKEN_SECONDS))


def display_label(meta: dict[str, Any]) -> str:
    name = meta.get("username") or ""
    return f"@{name}" if name else ""


# --------------------------------------------------------------------------
# posting (src/publish_worker.py is the only caller)
# --------------------------------------------------------------------------

def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _refused(e: Exception, *secrets) -> Exception:
    """X's own no is terminal; a 429 or a 5xx goes back for the worker's
    retry."""
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    if status is not None and 400 <= status < 500 and status != 429:
        return PostFailed("X refused the post: " + base.problem(e, *secrets))
    return e


def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    kind = (source.get("kind") or "").lower()
    has_file = bool(source.get("media_url") or source.get("output_path"))
    if not has_file and not (caption or "").strip():
        return "An X post needs words or a clip."
    if has_file and kind not in ("video", "image"):
        return "X takes a video or an image."
    if len(caption or "") > CAPTION_MAX:
        return f"X takes {CAPTION_MAX} characters; this caption has {len(caption)}."
    return None


def _bytes(media: dict[str, Any]) -> tuple[bytes, str]:
    path = media.get("path") or ""
    url = media.get("url") or ""
    name = Path(path or url.split("?", 1)[0]).name or "clip.mp4"
    mime = mimetypes.guess_type(name)[0] or ("video/mp4" if media.get("kind") == "video" else "image/jpeg")
    if path and Path(path).is_file():
        data = Path(path).read_bytes()
    elif url:
        from .. import refbin
        data, kind = refbin.public_bytes(url, max_bytes=UPLOAD_MAX_BYTES)
        mime = kind or mime
    else:
        raise PostFailed("This render has no file to upload.")
    return data, mime


def _upload(token: str, data: bytes, mime: str, kind: str) -> tuple[str, dict]:
    """initialize -> append each part -> finalize. The media id and the
    processing_info X answered at finalize (empty when it is ready)."""
    if kind == "image" and len(data) > IMAGE_MAX_BYTES:
        raise PostFailed("X takes a still of 5 MB at most.")
    if len(data) > UPLOAD_MAX_BYTES:
        raise PostFailed(f"The file is over {UPLOAD_MAX_BYTES // (1024 * 1024)} MB.")
    category = "tweet_video" if kind == "video" else "tweet_image"
    try:
        init = _http("POST", f"{API}/2/media/upload/initialize", headers=_bearer(token),
                     json={"media_type": mime, "total_bytes": len(data), "media_category": category},
                     timeout=POST_HTTP_TIMEOUT)
        media_id = str((init.get("data") or {}).get("id") or "")
        if not media_id:
            raise PostFailed("X answered the upload without an id.")
        for index, start in enumerate(range(0, len(data), CHUNK_BYTES)):
            _request("POST", f"{API}/2/media/upload/{media_id}/append", headers=_bearer(token),
                     data={"segment_index": str(index)},
                     files={"media": ("part", data[start:start + CHUNK_BYTES], "application/octet-stream")},
                     timeout=POST_HTTP_TIMEOUT)
        done = _http("POST", f"{API}/2/media/upload/{media_id}/finalize", headers=_bearer(token),
                     timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    return media_id, (done.get("data") or {}).get("processing_info") or {}


def _create(token: str, meta: dict[str, Any], caption: str, media_id: str) -> PostResult:
    body: dict[str, Any] = {"text": caption}
    if media_id:
        body["media"] = {"media_ids": [media_id]}
    try:
        got = _http("POST", f"{API}/2/tweets", json=body, headers=_bearer(token),
                    timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    post_id = str((got.get("data") or {}).get("id") or "")
    if not post_id:
        raise PostFailed("X created the post but gave no id back.")
    who = meta.get("username") or "i"
    return PostResult(status="completed", release_id=post_id,
                      release_url=f"https://x.com/{who}/status/{post_id}")


def _waiting(info: dict) -> bool:
    return str(info.get("state") or "").lower() in ("pending", "in_progress")


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    caption = (post.get("caption") or "")[:CAPTION_MAX]
    media = post.get("media") or {}
    if not (media.get("path") or media.get("url")):
        return _create(token, meta, caption, "")
    kind = (media.get("kind") or "").lower()
    data, mime = _bytes(media)
    media_id, info = _upload(token, data, mime, kind)
    if str(info.get("state") or "").lower() == "failed":
        raise PostFailed("X could not process the file.")
    if _waiting(info):
        return PostResult(status="pending", pending={"media_id": media_id, "caption": caption})
    return _create(token, meta, caption, media_id)


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("post"):
        return PostResult(status="completed", release_id=str(pending["post"]),
                          release_url=str(pending.get("url") or ""))
    try:
        got = _http("GET", f"{API}/2/media/upload", headers=_bearer(token),
                    params={"command": "STATUS", "media_id": str(pending.get("media_id") or "")},
                    timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    info = (got.get("data") or {}).get("processing_info") or {}
    state = str(info.get("state") or "").lower()
    if state == "failed":
        raise PostFailed("X could not process the video.")
    if _waiting(info):
        return PostResult(status="pending", pending=pending)
    return PostResult(status="ready", pending=pending)


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("post"):
        return post_check(token, meta, pending)
    return _create(token, meta, str(pending.get("caption") or ""), str(pending.get("media_id") or ""))
