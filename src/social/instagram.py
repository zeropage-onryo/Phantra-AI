"""
Instagram, through Instagram Business Login (2026-10-22): the standalone
route, no Facebook Page involved.

Mike pressed this screen on Postiz on 2026-10-22 for @phantra.ai: the
consent lists four toggles, one per scope below, and the required one is
greyed. This module asks for exactly those four and nothing more, because
Meta's reviewer asks why about every extra one.

THE TOGGLES ARE THE PERSON'S. "Access and publish content" can be switched
off and Allow still pressed. Meta answers the code exchange with the
permissions it actually granted, and a connection that cannot publish is
REFUSED here rather than stored: a channel that can read but never post
is a card that lies.

THE TOKEN. A short-lived token comes back from the code; it is exchanged
at once for a LONG-LIVED one (60 days). There is no refresh token on this
route: a long-lived token is renewed with `refresh_access_token` while it
is still valid and at least a day old, which is what `refresh` does and
what social_connections.token_for calls inside the last seven days. A
token that lapsed is a reconnect, said so on the card.

Dated 2026-10-22 against Meta's "Instagram API with Instagram Login"
(Business Login) docs: oauth/authorize, oauth/access_token,
access_token?grant_type=ig_exchange_token, refresh_access_token, /me.
The old instagram.py keeps the operator's env-token path for publishing
and insights; this one only connects.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, PostFailed, PostResult, Renewed

IDENTIFIER = "instagram"
NAME = "Instagram"
CONNECTS = "an Instagram professional (Business or Creator) account"
SCOPES = (
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_insights",
)
# Without this one the connection cannot post; without basic nothing
# answers at all.
REQUIRED = ("instagram_business_basic", "instagram_business_content_publish")

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH = "https://graph.instagram.com"
GRAPH_VERSION = "v21.0"
LONG_LIVED_SECONDS = 60 * 24 * 3600

APP_ID_ENV = "SOCIAL_INSTAGRAM_APP_ID"
APP_SECRET_ENV = "SOCIAL_INSTAGRAM_APP_SECRET"


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(APP_ID_ENV) and _env(APP_SECRET_ENV))


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("Instagram is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": _env(APP_ID_ENV),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
        # the Business Login screen, not Facebook's; ask every time so a
        # second workspace can connect a second account
        "enable_fb_login": "0",
        "force_authentication": "1",
    })


def _granted(tok: dict) -> set[str]:
    raw = tok.get("permissions")
    if isinstance(raw, list):
        return {str(p) for p in raw}
    return {p.strip() for p in str(raw or "").split(",") if p.strip()}


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    """code -> short-lived token (+ the permissions really granted) ->
    long-lived token -> the account's name and picture."""
    secret = _env(APP_SECRET_ENV)
    # Instagram appends "#_" to the code on the way back
    code = (code or "").split("#", 1)[0]
    try:
        tok = _http("POST", TOKEN_URL, data={
            "client_id": _env(APP_ID_ENV), "client_secret": secret,
            "grant_type": "authorization_code", "redirect_uri": redirect_uri,
            "code": code,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not accept the sign-in: " + base.problem(e, secret, code))
    short = tok.get("access_token") or ""
    if not short:
        raise ConnectRefused("Instagram sent no token back.")
    granted = _granted(tok)
    missing = [s for s in REQUIRED if granted and s not in granted]
    if missing:
        raise ConnectRefused("Instagram was connected without permission to publish. "
                             "Connect again and leave \"Access and publish content\" switched on.")
    try:
        long = _http("GET", f"{GRAPH}/access_token", params={
            "grant_type": "ig_exchange_token", "client_secret": secret,
            "access_token": short,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not issue a long-lived token: "
                             + base.problem(e, secret, short))
    access = long.get("access_token") or short
    expires_in = int(long.get("expires_in") or LONG_LIVED_SECONDS)
    try:
        me = _http("GET", f"{GRAPH}/{GRAPH_VERSION}/me", params={
            "fields": "user_id,username,name,profile_picture_url",
            "access_token": access,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not say which account this is: "
                             + base.problem(e, access, short))
    user_id = str(me.get("user_id") or me.get("id") or tok.get("user_id") or "")
    if not user_id:
        raise ConnectRefused("Instagram named no account id.")
    username = me.get("username") or ""
    return Connected(
        external_id=user_id,
        display_name=me.get("name") or username or f"Instagram {user_id}",
        handle=username,
        avatar_url=me.get("profile_picture_url") or "",
        access_token=access,
        refresh_token="",
        expires_in=expires_in,
        scopes=sorted(granted) if granted else list(SCOPES),
        meta={"ig_user_id": user_id},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """A long-lived token renews itself while still valid (and a day old).
    A lapsed one cannot, and the person reconnects."""
    try:
        res = _http("GET", f"{GRAPH}/refresh_access_token", params={
            "grant_type": "ig_refresh_token", "access_token": access_token,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not renew the token: " + base.problem(e, access_token))
    new = res.get("access_token") or ""
    if not new:
        raise ConnectRefused("Instagram did not renew the token.")
    return Renewed(access_token=new, expires_in=int(res.get("expires_in") or LONG_LIVED_SECONDS))


def display_label(meta: dict[str, Any]) -> str:
    return ""


# --------------------------------------------------------------------------
# posting (src/publish_worker.py is the only caller)
# --------------------------------------------------------------------------
#
# Meta's publish is two steps with a wait between: register the media as a
# CONTAINER (Meta fetches the file from a public URL and transcodes it),
# poll its status_code until FINISHED, then media_publish. The three
# functions below are those steps, so the worker can leave the row pending
# between polls instead of holding a thread for a minute per post.
# Endpoints as src/instagram.py's wrappers (graph.instagram.com, an
# Instagram-Login token), dated 2026-10-22.

CAPTION_MAX = 2200
PUBLISH_TIMEOUT = 20
SETTINGS = (
    {"key": "post_type", "label": "Post as", "type": "select", "required": False,
     "options": [{"id": "reel", "label": "Reel (or a feed image)"}, {"id": "story", "label": "Story"}]},
)


def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    kind = (source.get("kind") or "").lower()
    if kind not in ("video", "image"):
        return "Instagram takes a video (as a Reel) or an image."
    if not source.get("media_url") and not source.get("output_path"):
        return "This render has no file to post."
    if kind == "image" and settings.get("post_type") == "reel":
        return "A Reel needs a video."
    return None


def _graph(path: str) -> str:
    return f"{GRAPH}/{GRAPH_VERSION}/{path.lstrip('/')}"


def _refused(e: Exception, *secrets) -> Exception:
    """A 4xx from Meta is about THIS post (or this token); a 5xx or no
    answer is Meta's, and the worker retries."""
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None)
    said = base.problem(e, *secrets)
    if status is not None and 400 <= status < 500:
        return PostFailed("Instagram refused the post: " + said)
    return e


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    user_id = str(meta.get("ig_user_id") or "")
    if not user_id:
        raise PostFailed("This Instagram connection names no account id.")
    media = post.get("media") or {}
    url = media.get("url") or ""
    if not url.startswith("https://"):
        raise PostFailed("Instagram fetches the file from a public https address; this render has none.")
    caption = (post.get("caption") or "")[:CAPTION_MAX]
    settings = post.get("settings") or {}
    kind = (media.get("kind") or "").lower()
    body: dict[str, Any] = {"caption": caption, "access_token": token}
    if kind == "video":
        body["media_type"] = "STORIES" if settings.get("post_type") == "story" else "REELS"
        body["video_url"] = url
        if body["media_type"] == "REELS" and settings.get("share_to_feed") is False:
            body["share_to_feed"] = "false"
    else:
        body["image_url"] = url
        if settings.get("post_type") == "story":
            body["media_type"] = "STORIES"
    try:
        made = _http("POST", _graph(f"{user_id}/media"), data=body, timeout=PUBLISH_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    container = str(made.get("id") or "")
    if not container:
        raise PostFailed("Instagram returned no container for the post.")
    return PostResult(status="pending", pending={"container_id": container, "user_id": user_id})


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("media_id"):
        # finished already: a retry after a crash must not publish twice
        return PostResult(status="completed", release_id=str(pending["media_id"]),
                          release_url=str(pending.get("permalink") or ""))
    container = str(pending.get("container_id") or "")
    try:
        got = _http("GET", _graph(container), params={"fields": "status_code,status",
                                                      "access_token": token},
                    timeout=PUBLISH_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    code = str(got.get("status_code") or "").upper()
    if code == "FINISHED":
        return PostResult(status="ready", pending=pending)
    if code in ("ERROR", "EXPIRED"):
        raise PostFailed(f"Instagram could not process the file ({code.lower()}): "
                         + str(got.get("status") or "no detail"))
    return PostResult(status="pending", pending=pending)


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    if pending.get("media_id"):
        return post_check(token, meta, pending)
    user_id = str(pending.get("user_id") or meta.get("ig_user_id") or "")
    container = str(pending.get("container_id") or "")
    try:
        done = _http("POST", _graph(f"{user_id}/media_publish"),
                     data={"creation_id": container, "access_token": token},
                     timeout=PUBLISH_TIMEOUT)
    except requests.RequestException as e:
        raise _refused(e, token)
    media_id = str(done.get("id") or "")
    if not media_id:
        raise PostFailed("Instagram published nothing (no media id came back).")
    link = ""
    try:
        got = _http("GET", _graph(media_id), params={"fields": "permalink", "access_token": token},
                    timeout=PUBLISH_TIMEOUT)
        link = str(got.get("permalink") or "")
    except requests.RequestException:
        link = ""           # live either way; the id is what analytics need
    return PostResult(status="completed", release_id=media_id, release_url=link)


# --------------------------------------------------------------------------
# the feed (2026-10-22, docs/tasks/task-calendar.md)
# --------------------------------------------------------------------------

def recent_media(token: str, meta: dict[str, Any], *, limit: int = 24) -> list[dict[str, Any]]:
    """The account's own latest posts, for the Feed view's grid: what
    the queue will land on top of. One read of /{ig-user-id}/media; the
    caller caches it. Each item: id, kind (image|video), thumb (an
    address Instagram serves for a while, never stored on a row), url
    (the permalink), at, caption."""
    user_id = str(meta.get("ig_user_id") or "")
    if not user_id:
        return []
    try:
        got = _http("GET", _graph(f"{user_id}/media"),
                    params={"fields": "id,media_type,media_url,thumbnail_url,permalink,timestamp,caption",
                            "limit": max(1, min(int(limit), 50)), "access_token": token},
                    timeout=PUBLISH_TIMEOUT)
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not answer for the feed: " + base.problem(e, token))
    out = []
    for item in got.get("data") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        kind = "video" if str(item.get("media_type") or "").upper() == "VIDEO" else "image"
        out.append({
            "id": str(item["id"]),
            "kind": kind,
            "thumb": str(item.get("thumbnail_url") or item.get("media_url") or ""),
            "url": str(item.get("permalink") or ""),
            "at": str(item.get("timestamp") or ""),
            "caption": str(item.get("caption") or "")[:200],
        })
    return out
