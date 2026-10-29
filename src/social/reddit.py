"""
Reddit: a person's own account, posting to a subreddit they name
(2026-10-22, docs/tasks/task-social-providers.md).

WHAT A CONNECTION IS. One Reddit account (the OAuth "web app" grant with
`duration=permanent`, so a refresh token comes back and the hour-long
access token renews itself). A post goes to a SUBREDDIT, chosen per post
in the drawer (`settings.subreddit`), because the same account posts to
many; the connection is the account, not a sub.

WHAT A POST IS. A LINK post (`kind=link`) whose URL is the clip or still
on the bucket, with the caption as the TITLE (Reddit's 300 characters).
Reddit's own video upload (a media lease, a multipart upload, a poster
frame) is a later step; a link post with an https .mp4 is what most
schedulers send and what Reddit renders as a player. Optional per post:
a flair id, NSFW, spoiler. Each subreddit has rules the API does not
tell you until it refuses (flair required, no links, karma minimums):
Reddit's words come back on the row in plain text.

THE USER-AGENT. Reddit refuses the default one and rate-limits by it:
every call carries `web:ai.phantra:<version> (by /u/<operator>)`.

Dated 2026-10-22 against Reddit's OAuth2 and /api/submit docs; the Data
API free tier is 100 requests a minute per client.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, PostFailed, PostResult, Renewed

IDENTIFIER = "reddit"
NAME = "Reddit"
CONNECTS = "a Reddit account; each post names the subreddit"
SCOPES = ("identity", "submit", "read", "flair", "mysubreddits")

AUTHORIZE_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
USER_AGENT = "web:ai.phantra:1.0 (by /u/phantra_ai)"

CLIENT_ID_ENV = "SOCIAL_REDDIT_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_REDDIT_CLIENT_SECRET"

# the per-post form the drawer draws (type: text | select | boolean)
SETTINGS = (
    {"key": "subreddit", "label": "Subreddit", "type": "text", "required": True,
     "placeholder": "aivideo", "hint": "without r/"},
    {"key": "flair_id", "label": "Flair id", "type": "text", "required": False,
     "hint": "only when the sub requires one"},
    {"key": "nsfw", "label": "Mark NSFW", "type": "boolean", "required": False},
)


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _h(**extra: str) -> dict[str, str]:
    """Every call's headers: Reddit refuses the default User-Agent."""
    return {"User-Agent": USER_AGENT, **extra}


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV))


def _basic() -> str:
    import base64
    pair = f"{_env(CLIENT_ID_ENV)}:{_env(CLIENT_SECRET_ENV)}".encode("utf-8")
    return "Basic " + base64.b64encode(pair).decode("ascii")


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("Reddit is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": _env(CLIENT_ID_ENV),
        "response_type": "code",
        "state": state,
        "redirect_uri": redirect_uri,
        "duration": "permanent",
        "scope": " ".join(SCOPES),
    })


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        }, headers=_h(Authorization=_basic(), **{"Content-Type": "application/x-www-form-urlencoded"}))
    except requests.RequestException as e:
        raise ConnectRefused("Reddit did not accept the sign-in: " + base.problem(e, secret, code))
    access = tok.get("access_token") or ""
    if not access or tok.get("error"):
        raise ConnectRefused("Reddit sent no token back" + (f": {tok.get('error')}" if tok.get("error") else "."))
    granted = set((tok.get("scope") or "").split())
    if "submit" not in granted:
        raise ConnectRefused("Reddit did not grant posting (the 'submit' permission was not allowed).")
    try:
        me = _http("GET", f"{API}/api/v1/me", headers=_h(Authorization=f"Bearer {access}"))
    except requests.RequestException as e:
        raise ConnectRefused("Reddit did not say who you are: " + base.problem(e, access))
    name = str(me.get("name") or "")
    if not name:
        raise ConnectRefused("Reddit did not say who you are.")
    icon = str(me.get("icon_img") or "").split("?", 1)[0]
    return Connected(
        external_id=str(me.get("id") or name),
        display_name=f"u/{name}",
        handle=name,
        avatar_url=icon,
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=int(tok.get("expires_in") or 3600),
        scopes=sorted(granted),
        meta={"username": name},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """An hour-long access token, renewed with the permanent refresh
    token (which Reddit keeps the same)."""
    if not refresh_token:
        return None
    try:
        tok = _http("POST", TOKEN_URL, data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                    headers=_h(Authorization=_basic(), **{"Content-Type": "application/x-www-form-urlencoded"}))
    except requests.RequestException as e:
        raise ConnectRefused("Reddit did not renew the token: " + base.problem(e, refresh_token, access_token))
    new = tok.get("access_token") or ""
    if not new:
        raise ConnectRefused("Reddit did not renew the token.")
    return Renewed(access_token=new, refresh_token=tok.get("refresh_token") or refresh_token,
                   expires_in=int(tok.get("expires_in") or 3600))


def display_label(meta: dict[str, Any]) -> str:
    return f"u/{meta['username']}" if meta.get("username") else ""


# --------------------------------------------------------------------------
# posting
# --------------------------------------------------------------------------

CAPTION_MAX = 300           # a title
POST_HTTP_TIMEOUT = 60


def _sub(settings: dict) -> str:
    return str(settings.get("subreddit") or "").strip().lstrip("/").removeprefix("r/").strip("/")


def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    if not (caption or "").strip():
        return "A Reddit post needs a title (the words)."
    if not _sub(settings):
        return "Name the subreddit to post to."
    if not source.get("media_url") and not source.get("output_path"):
        return "This render has no file to post."
    return None


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    """One link post to the named subreddit: the clip's address as the
    link, the words as the title. Completed in one call."""
    settings = post.get("settings") or {}
    sub = _sub(settings)
    if not sub:
        raise PostFailed("This post names no subreddit.")
    media = post.get("media") or {}
    url = media.get("url") or ""
    if not url.startswith("https://"):
        raise PostFailed("Reddit links to the file by a public https address; this render has none.")
    title = (post.get("caption") or "").strip()[:CAPTION_MAX]
    body: dict[str, Any] = {
        "api_type": "json", "kind": "link", "sr": sub, "title": title, "url": url,
        "sendreplies": "true", "resubmit": "true",
        "nsfw": "true" if settings.get("nsfw") else "false",
        "spoiler": "true" if settings.get("spoiler") else "false",
    }
    if settings.get("flair_id"):
        body["flair_id"] = str(settings["flair_id"])
    try:
        got = _http("POST", f"{API}/api/submit", data=body,
                    headers=_h(Authorization=f"Bearer {token}"), timeout=POST_HTTP_TIMEOUT)
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        status = getattr(resp, "status_code", None)
        said = base.problem(e, token)
        if status is not None and 400 <= status < 500 and status != 429:
            raise PostFailed("Reddit refused the post: " + said)
        raise
    answer = (got.get("json") or {}) if isinstance(got, dict) else {}
    errors = answer.get("errors") or []
    if errors:
        # [["SUBMIT_VALIDATION_FLAIR_REQUIRED", "Your post must contain post flair.", "flair"], ...]
        words = "; ".join(str(e[1] if len(e) > 1 else e[0]) for e in errors if e)
        raise PostFailed(f"r/{sub} refused the post: {words}")
    data = answer.get("data") or {}
    name = str(data.get("name") or data.get("id") or "")
    link = str(data.get("url") or "")
    if not name and not link:
        raise PostFailed("Reddit answered without a post id.")
    return PostResult(status="completed", release_id=name, release_url=link)


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    return PostResult(status="completed", release_id=str(pending.get("id") or ""),
                      release_url=str(pending.get("url") or ""))


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    return post_check(token, meta, pending)


# --------------------------------------------------------------------------
# the drawer's lookups (free reads through the person's token)
# --------------------------------------------------------------------------

def flairs(token: str, subreddit: str) -> list[dict[str, Any]]:
    """The subreddit's post flairs, for the drawer's picker: [{id, text}].
    [] when the sub has none or hides them."""
    sub = _sub({"subreddit": subreddit})
    if not sub:
        return []
    try:
        got = _http("GET", f"{API}/r/{sub}/api/link_flair_v2",
                    headers=_h(Authorization=f"Bearer {token}"), timeout=20)
    except requests.RequestException:
        return []
    out = []
    for row in got if isinstance(got, list) else []:
        if isinstance(row, dict) and row.get("id"):
            out.append({"id": str(row["id"]), "text": str(row.get("text") or "")})
    return out
