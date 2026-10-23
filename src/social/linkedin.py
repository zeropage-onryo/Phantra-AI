"""
LinkedIn: a member's own profile (2026-10-22, docs/tasks/task-social-providers.md).

WHAT A CONNECTION IS. One member, through the self-serve products "Sign
In with LinkedIn using OpenID Connect" + "Share on LinkedIn"
(`openid profile email w_member_social`). A Company Page is the
Community Management API, a partner application that takes weeks and is
not granted to everyone; it is NOT this module. The token lasts 60 days
and a self-serve app gets no refresh token, so `refresh` answers None
and at day 60 the card says Expired -> Reconnect.

WHAT A POST IS. The Posts API (`/rest/posts`, versioned by the
`LinkedIn-Version` header): the words as `commentary`, the clip or still
as media. An IMAGE is one upload (initializeUpload -> PUT the bytes ->
the image urn goes on the post) and completes in `post_start`. A VIDEO is
initializeUpload -> PUT each part -> finalizeUpload, then LinkedIn
processes it: `post_start` leaves the row PENDING with the video urn,
`post_check` polls the video's status until AVAILABLE, and `post_finish`
creates the post. The post's urn comes back in the `x-restli-id` header,
so the one call that needs a header reads the raw response (`_request`).

Dated 2026-10-22 against the Posts, Images and Videos APIs at
LINKEDIN_VERSION. 3000 characters.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, PostFailed, PostResult, Renewed

IDENTIFIER = "linkedin"
NAME = "LinkedIn"
CONNECTS = "your own LinkedIn profile (a Company Page needs LinkedIn's partner program)"
SCOPES = ("openid", "profile", "email", "w_member_social")

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
API = "https://api.linkedin.com"
# the Posts/Images/Videos API version this module was written against
# (YYYYMM; LinkedIn keeps a version for about a year)
LINKEDIN_VERSION = "202506"
TOKEN_SECONDS = 60 * 24 * 3600

CLIENT_ID_ENV = "SOCIAL_LINKEDIN_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_LINKEDIN_CLIENT_SECRET"

SETTINGS = (
    {"key": "visibility", "label": "Who can see it", "type": "select", "required": False,
     "options": [{"id": "PUBLIC", "label": "Anyone"}, {"id": "CONNECTIONS", "label": "Connections only"}]},
)


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _request(method: str, url: str, **kw) -> requests.Response:
    """The raw response, for the one call whose answer is a header; a
    non-2xx raises like base.http does."""
    response = requests.request(method, url, timeout=kw.pop("timeout", base.HTTP_TIMEOUT), **kw)
    response.raise_for_status()
    return response


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV))


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("LinkedIn is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": _env(CLIENT_ID_ENV),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(SCOPES),
    })


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("LinkedIn did not accept the sign-in: " + base.problem(e, secret, code))
    access = tok.get("access_token") or ""
    if not access:
        raise ConnectRefused("LinkedIn sent no token back.")
    granted = set((tok.get("scope") or "").replace(",", " ").split())
    if granted and "w_member_social" not in granted:
        raise ConnectRefused("LinkedIn did not grant posting (the 'Share on LinkedIn' permission was not allowed).")
    try:
        me = _http("GET", f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {access}"})
    except requests.RequestException as e:
        raise ConnectRefused("LinkedIn did not say who you are: " + base.problem(e, access))
    sub = str(me.get("sub") or "")
    if not sub:
        raise ConnectRefused("LinkedIn did not say who you are.")
    full = " ".join(x for x in (me.get("given_name"), me.get("family_name")) if x)
    name = str(me.get("name") or full or "LinkedIn member")
    return Connected(
        external_id=sub,
        display_name=name,
        handle="",
        avatar_url=str(me.get("picture") or ""),
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=int(tok.get("expires_in") or TOKEN_SECONDS),
        scopes=sorted(granted) or list(SCOPES),
        meta={"person_urn": f"urn:li:person:{sub}", "name": name},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """Self-serve apps get no refresh token: nothing to do, the person
    reconnects at day 60. (An app granted programmatic refresh would carry
    one; honour it when present.)"""
    if not refresh_token:
        return None
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "refresh_token", "refresh_token": refresh_token,
            "client_id": _env(CLIENT_ID_ENV), "client_secret": _env(CLIENT_SECRET_ENV),
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("LinkedIn did not renew the token: " + base.problem(e, refresh_token, access_token))
    new = tok.get("access_token") or ""
    if not new:
        return None
    return Renewed(access_token=new, refresh_token=tok.get("refresh_token") or refresh_token,
                   expires_in=int(tok.get("expires_in") or TOKEN_SECONDS))


def display_label(meta: dict[str, Any]) -> str:
    return str(meta.get("name") or "")


# --------------------------------------------------------------------------
# posting
# --------------------------------------------------------------------------

CAPTION_MAX = 3000
UPLOAD_MAX_BYTES = 200 * 1024 * 1024
POST_HTTP_TIMEOUT = 120


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}


def _refused(e: Exception, *secrets) -> Exception:
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    said = base.problem(e, *secrets)
    if status is not None and 400 <= status < 500 and status != 429:
        return PostFailed("LinkedIn refused the post: " + said)
    return e


def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    kind = (source.get("kind") or "").lower()
    if kind not in ("video", "image"):
        return "LinkedIn takes a video or an image."
    if not source.get("media_url") and not source.get("output_path"):
        return "This render has no file to post."
    return None


def _bytes(media: dict[str, Any]) -> tuple[bytes, str]:
    """The file's bytes and mime: the local file when this machine has it,
    else one fetch of the public address."""
    import mimetypes
    from pathlib import Path
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
    if len(data) > UPLOAD_MAX_BYTES:
        raise PostFailed(f"The file is over LinkedIn's {UPLOAD_MAX_BYTES // (1024 * 1024)} MB limit here.")
    return data, mime


def _upload_image(token: str, owner: str, data: bytes, mime: str) -> str:
    try:
        init = _http("POST", f"{API}/rest/images?action=initializeUpload",
                     json={"initializeUploadRequest": {"owner": owner}}, headers=_headers(token),
                     timeout=POST_HTTP_TIMEOUT)
        value = init.get("value") or {}
        _request("PUT", value["uploadUrl"], data=data,
                 headers={"Authorization": f"Bearer {token}", "Content-Type": mime}, timeout=POST_HTTP_TIMEOUT)
        return str(value["image"])
    except requests.RequestException as e:
        raise _refused(e, token)
    except KeyError:
        raise PostFailed("LinkedIn answered the image upload without an address.")


def _upload_video(token: str, owner: str, data: bytes, mime: str) -> str:
    """initializeUpload -> PUT each part -> finalizeUpload; the video urn,
    which LinkedIn then processes on its own time."""
    try:
        init = _http("POST", f"{API}/rest/videos?action=initializeUpload",
                     json={"initializeUploadRequest": {"owner": owner, "fileSizeBytes": len(data),
                                                       "uploadCaptions": False, "uploadThumbnail": False}},
                     headers=_headers(token), timeout=POST_HTTP_TIMEOUT)
        value = init.get("value") or {}
        urn = str(value["video"])
        etags = []
        for part in value.get("uploadInstructions") or []:
            first, last = int(part["firstByte"]), int(part["lastByte"])
            res = _request("PUT", part["uploadUrl"], data=data[first:last + 1],
                           headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
                           timeout=POST_HTTP_TIMEOUT)
            etags.append(res.headers.get("etag") or res.headers.get("ETag") or "")
        _http("POST", f"{API}/rest/videos?action=finalizeUpload",
              json={"finalizeUploadRequest": {"video": urn, "uploadToken": value.get("uploadToken") or "",
                                              "uploadedPartIds": etags}},
              headers=_headers(token), timeout=POST_HTTP_TIMEOUT)
        return urn
    except requests.RequestException as e:
        raise _refused(e, token)
    except KeyError:
        raise PostFailed("LinkedIn answered the video upload without an address.")


def _create_post(token: str, owner: str, caption: str, media_urn: str, kind: str, settings: dict) -> PostResult:
    visibility = "CONNECTIONS" if settings.get("visibility") == "CONNECTIONS" else "PUBLIC"
    body = {
        "author": owner,
        "commentary": caption,
        "visibility": visibility,
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"id": media_urn, "title": caption[:100] or ("Video" if kind == "video" else "Image")}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    try:
        res = _request("POST", f"{API}/rest/posts", json=body, headers=_headers(token), timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    post_urn = res.headers.get("x-restli-id") or res.headers.get("X-RestLi-Id") or ""
    if not post_urn:
        raise PostFailed("LinkedIn created the post but gave no id back.")
    return PostResult(status="completed", release_id=post_urn,
                     release_url=f"https://www.linkedin.com/feed/update/{post_urn}")


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    owner = str(meta.get("person_urn") or "")
    if not owner:
        raise PostFailed("This LinkedIn connection names no member.")
    media = post.get("media") or {}
    kind = (media.get("kind") or "").lower()
    caption = (post.get("caption") or "")[:CAPTION_MAX]
    settings = post.get("settings") or {}
    data, mime = _bytes(media)
    if kind == "video":
        urn = _upload_video(token, owner, data, mime)
        return PostResult(status="pending", pending={"video": urn, "owner": owner, "caption": caption,
                                                     "settings": settings})
    urn = _upload_image(token, owner, data, mime)
    return _create_post(token, owner, caption, urn, "image", settings)


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("post"):
        return PostResult(status="completed", release_id=str(pending["post"]),
                          release_url=str(pending.get("url") or ""))
    urn = str(pending.get("video") or "")
    from urllib.parse import quote
    try:
        got = _http("GET", f"{API}/rest/videos/{quote(urn, safe='')}", headers=_headers(token),
                    timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    status = str(got.get("status") or "").upper()
    if status == "AVAILABLE":
        return PostResult(status="ready", pending=pending)
    if status in ("PROCESSING_FAILED", "FAILED"):
        raise PostFailed("LinkedIn could not process the video.")
    return PostResult(status="pending", pending=pending)


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("post"):
        return post_check(token, meta, pending)
    owner = str(pending.get("owner") or meta.get("person_urn") or "")
    return _create_post(token, owner, str(pending.get("caption") or ""), str(pending.get("video") or ""),
                        "video", pending.get("settings") or {})
