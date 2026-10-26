"""
YouTube: the member's own channel (2026-10-26).

`src/youtube.py` is the older half: public stats by API key, and an
operator-only upload from env credentials. This module is a person's own
channel through Settings -> Connections, the publish worker's provider.

WHAT A CONNECTION IS. Google OAuth on a Web application client
(`SOCIAL_YOUTUBE_CLIENT_ID` / `_SECRET`), scopes `youtube.upload` (post)
and `youtube.readonly` (which channel, and the Feed view's grid),
`access_type=offline` + `prompt=consent` so Google always hands back a
refresh token. A Google account with several channels (Brand Accounts)
picks ONE on Google's own consent page; `channels?mine=true` then answers
that one, so there is no in-between step here. An account with no channel
is refused at connect with how to make one.

TOKENS. An access token lasts an hour; the refresh token does not rotate
(Google sends none back on a refresh, so the old one is kept). While the
consent screen is in Testing, Google expires the refresh token after
seven days and the card says Reconnect: publishing the consent screen
ends that.

WHAT A POST IS. One video through the resumable upload: a POST with the
video resource (title, description, privacy, the AI disclosure) answers
a session address in `Location`, one PUT of the bytes answers the video.
It completes in `post_start`; YouTube then processes the file on its side
and the link already works. The words are the description; the title is
the post's own setting, else the words' first line (100 characters, no
`<` or `>`, YouTube's own rule). YouTube files a vertical clip of up to
three minutes as a Short by itself.

`containsSyntheticMedia` is set on every upload: Phantra makes generated
video, and YouTube asks creators to disclose realistic altered or
synthetic content. `selfDeclaredMadeForKids` is false.

QUOTA. Since 2026 an upload costs 1 unit of a separate "Video Uploads"
bucket, 100 a day per project, and an unverified project's uploads are no
longer forced private (videos.insert reference, read 2026-10-26).

Dated 2026-10-26 against videos.insert, the resumable upload protocol
and Google's OAuth 2.0 web server flow.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, PostFailed, PostResult, Renewed

IDENTIFIER = "youtube"
NAME = "YouTube"
CONNECTS = "your own YouTube channel"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly")

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
TOKEN_SECONDS = 3600

CLIENT_ID_ENV = "SOCIAL_YOUTUBE_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_YOUTUBE_CLIENT_SECRET"

CAPTION_MAX = 5000                       # the description (YouTube counts bytes)
TITLE_MAX = 100
UPLOAD_MAX_BYTES = 512 * 1024 * 1024
POST_HTTP_TIMEOUT = 300

PRIVACY = ("public", "unlisted", "private")
SETTINGS = (
    {"key": "title", "label": "Title", "type": "text", "required": False,
     "placeholder": "the words' first line", "hint": "100 characters"},
    {"key": "privacy", "label": "Who can see it", "type": "select", "required": False,
     "options": [{"id": "public", "label": "Public"}, {"id": "unlisted", "label": "Unlisted"},
                 {"id": "private", "label": "Private"}]},
)


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _request(method: str, url: str, **kw) -> requests.Response:
    """The raw call, for the upload's two steps (one answers a header, one
    sends bytes); a non-2xx raises like base.http does."""
    response = requests.request(method, url, timeout=kw.pop("timeout", base.HTTP_TIMEOUT), **kw)
    response.raise_for_status()
    return response


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV))


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("YouTube is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": _env(CLIENT_ID_ENV),
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    })


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Google did not accept the sign-in: " + base.problem(e, secret, code))
    access = tok.get("access_token") or ""
    if not access:
        raise ConnectRefused("Google sent no token back.")
    granted = set((tok.get("scope") or "").split())
    if granted and SCOPES[0] not in granted:
        raise ConnectRefused("YouTube was connected without permission to upload. "
                             "Connect again and leave the upload box ticked.")
    try:
        got = _http("GET", f"{API}/channels", headers=_bearer(access),
                    params={"part": "snippet,contentDetails", "mine": "true"})
    except requests.RequestException as e:
        raise ConnectRefused("YouTube did not say which channel: " + base.problem(e, access))
    items = got.get("items") or []
    if not items:
        raise ConnectRefused("This Google account has no YouTube channel yet. Make one at "
                             "youtube.com (your picture -> Create a channel), then connect again.")
    channel = items[0]
    snippet = channel.get("snippet") or {}
    uploads = ((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads") or ""
    handle = str(snippet.get("customUrl") or "").lstrip("@")
    thumbs = snippet.get("thumbnails") or {}
    avatar = (thumbs.get("default") or thumbs.get("medium") or {}).get("url") or ""
    channel_id = str(channel.get("id") or "")
    return Connected(
        external_id=channel_id,
        display_name=str(snippet.get("title") or handle or "YouTube channel"),
        handle=handle,
        avatar_url=str(avatar),
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=int(tok.get("expires_in") or TOKEN_SECONDS),
        scopes=sorted(granted) or list(SCOPES),
        meta={"channel_id": channel_id, "handle": handle, "uploads_playlist": uploads},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """A new access token; Google keeps the refresh token as it is."""
    if not refresh_token:
        return None
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "refresh_token", "refresh_token": refresh_token,
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Google did not renew the connection: "
                             + base.problem(e, refresh_token, access_token, secret))
    new = tok.get("access_token") or ""
    if not new:
        return None
    return Renewed(access_token=new, refresh_token=tok.get("refresh_token") or refresh_token,
                   expires_in=int(tok.get("expires_in") or TOKEN_SECONDS))


def display_label(meta: dict[str, Any]) -> str:
    handle = meta.get("handle") or ""
    return f"@{handle}" if handle else ""


# --------------------------------------------------------------------------
# posting (src/publish_worker.py is the only caller)
# --------------------------------------------------------------------------

def title_for(caption: str, settings: dict) -> str:
    """The post's own title, else the words' first line, cut to YouTube's
    100 characters."""
    title = str((settings or {}).get("title") or "").strip()
    if not title:
        lines = [ln.strip() for ln in (caption or "").splitlines() if ln.strip()]
        title = lines[0] if lines else ""
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX - 1].rstrip() + "…"
    return title


def _privacy(settings: dict) -> str:
    choice = str((settings or {}).get("privacy") or PRIVACY[0]).lower()
    return choice if choice in PRIVACY else ""


def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    if (source.get("kind") or "").lower() != "video":
        return "YouTube takes a video; this is a still."
    if not source.get("media_url") and not source.get("output_path"):
        return "This render has no file to post."
    title = title_for(caption, settings)
    if not title:
        return "A YouTube video needs a title: write the words, or a title."
    if "<" in title or ">" in title or "<" in (caption or "") or ">" in (caption or ""):
        return "YouTube does not take < or > in a title or description."
    if len((caption or "").encode()) > CAPTION_MAX:
        return f"YouTube takes a description of {CAPTION_MAX} bytes at most."
    if not _privacy(settings):
        return "Pick Public, Unlisted or Private."
    return None


def _bytes(media: dict[str, Any]) -> tuple[bytes, str]:
    from pathlib import Path
    path = media.get("path") or ""
    url = media.get("url") or ""
    if path and Path(path).is_file():
        return Path(path).read_bytes(), "video/mp4"
    if url:
        from .. import refbin
        data, kind = refbin.public_bytes(url, max_bytes=UPLOAD_MAX_BYTES)
        return data, (kind if (kind or "").startswith("video/") else "video/mp4")
    raise PostFailed("This render has no file to upload.")


def _refused(e: Exception, *secrets) -> Exception:
    """YouTube's own no (a 4xx other than 429) is terminal; a 429 or a 5xx
    goes back for the worker's retry."""
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    if status is not None and 400 <= status < 500 and status != 429:
        return PostFailed("YouTube refused the upload: " + base.problem(e, *secrets))
    return e


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    caption = post.get("caption") or ""
    settings = post.get("settings") or {}
    media = post.get("media") or {}
    if (media.get("kind") or "").lower() != "video":
        raise PostFailed("YouTube takes a video.")
    title = title_for(caption, settings)
    if not title:
        raise PostFailed("A YouTube video needs a title.")
    data, mime = _bytes(media)
    body = {
        "snippet": {"title": title, "description": caption, "categoryId": "22"},
        "status": {"privacyStatus": _privacy(settings) or "public",
                   "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
    }
    try:
        session = _request("POST", UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                           json=body, headers={**_bearer(token),
                                               "X-Upload-Content-Length": str(len(data)),
                                               "X-Upload-Content-Type": mime},
                           timeout=POST_HTTP_TIMEOUT)
        where = session.headers.get("Location") or session.headers.get("location") or ""
        if not where:
            raise PostFailed("YouTube opened no upload session.")
        done = _request("PUT", where, data=data, headers={**_bearer(token), "Content-Type": mime},
                        timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    try:
        video = done.json()
    except ValueError:
        video = {}
    video_id = str(video.get("id") or "")
    if not video_id:
        raise PostFailed("YouTube took the file but gave no video id back.")
    return PostResult(status="completed", release_id=video_id,
                      release_url=f"https://youtu.be/{video_id}")


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    # an upload completes in post_start; nothing is ever left pending
    return PostResult(status="completed", release_id=str(pending.get("video_id") or ""),
                      release_url=str(pending.get("url") or ""))


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    return post_check(token, meta, pending)


def recent_media(token: str, meta: dict[str, Any], *, limit: int = 24) -> list[dict[str, Any]]:
    """The channel's latest uploads, for the Feed view's grid: one read of
    its uploads playlist (1 unit). Each item: id, kind, thumb, url, at,
    caption."""
    playlist = str(meta.get("uploads_playlist") or "")
    if not playlist:
        return []
    try:
        got = _http("GET", f"{API}/playlistItems", headers=_bearer(token),
                    params={"part": "snippet,contentDetails", "playlistId": playlist,
                            "maxResults": max(1, min(int(limit), 50))},
                    timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise ConnectRefused("YouTube did not answer for the feed: " + base.problem(e, token))
    out = []
    for item in got.get("items") or []:
        snippet = item.get("snippet") or {}
        video_id = str((item.get("contentDetails") or {}).get("videoId")
                       or (snippet.get("resourceId") or {}).get("videoId") or "")
        if not video_id:
            continue
        thumbs = snippet.get("thumbnails") or {}
        thumb = (thumbs.get("medium") or thumbs.get("high") or thumbs.get("default") or {}).get("url") or ""
        out.append({
            "id": video_id,
            "kind": "video",
            "thumb": str(thumb),
            "url": f"https://youtu.be/{video_id}",
            "at": str((item.get("contentDetails") or {}).get("videoPublishedAt")
                      or snippet.get("publishedAt") or ""),
            "caption": str(snippet.get("title") or "")[:200],
        })
    return out
