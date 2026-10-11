"""
A post the person reviews and sends themselves (2026-10-11, Mike: make the
studio a distribution platform; docs/tasks/task-publish-review.md).

THE SHAPE. Claude (the MCP `prepare_post` tool) or a studio button can
PREPARE a post: which clip, which platform, a caption. That writes one
`publish_sessions` row and hands back a link to the studio's review page.
Nothing is sent anywhere. The page shows the clip, the account it will go
to, and every choice the platform makes the poster answer; the person
answers them and presses Post. Only that press -- a signed-in request from
the page, `submit()` -- reaches the platform. No MCP tool calls submit, and
tests/test_publish_review.py pins that none can.

WHY A PAGE AND NOT A QUOTE TOKEN. The render tools approve with a signed
quote and a yes in chat (`pricing.sign_studio`), which is right for spend:
the price is the whole decision. A post is not one decision. TikTok's
Direct Post guidelines -- what its audit checks -- require the person to
see a preview, pick the privacy level themselves (no default), set
comments / Duet / Stitch, disclose commercial content, see the declaration
they are agreeing to, and send nothing until they consent. A model saying
"yes" for them is exactly what those rules exist to stop. The page is also
the screen recording the audit asks for.

WHOSE CREDENTIALS. Publishing has been the operator's since 2026-09-02
(db.SHARED_TABLES["channels"]): tokens are env vars, not rows. This module
keeps that until per-account connections exist (the next build): the env
token is used only for the account named by PUBLISH_OPERATOR_ACCOUNT, and
every other account is told to connect its own. `token_for` is the one
seam a connections table replaces.

THE MEDIA URL. TikTok pulls the file from a URL on a domain or URL prefix
verified on the developer app, refuses anything that redirects, and
answers an unverified one with `url_ownership_unverified` only after the
press. So the check runs here first (`media_problem`): R2's own
pub-<hash>.r2.dev host is Cloudflare's, not ours, so production media is
expected to be re-hosted on a verified host via PUBLISH_MEDIA_BASE_URL,
and TIKTOK_VERIFIED_URL_PREFIXES lists what has been verified. Unset means
nothing is verified yet, which fails closed with the fix in the message.

OWNED (db.OWNED_TABLES): a session is one account's post.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from . import db, tiktok

SCHEMA = """
CREATE TABLE IF NOT EXISTS publish_sessions (
    id            TEXT PRIMARY KEY,
    account_id    BIGINT,
    platform      TEXT NOT NULL,
    source_ref    TEXT NOT NULL,
    media_url     TEXT NOT NULL,
    media_kind    TEXT NOT NULL,
    seconds       DOUBLE PRECISION,
    ai_generated  BOOLEAN NOT NULL DEFAULT TRUE,
    caption       TEXT NOT NULL DEFAULT '',
    created_via   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft',
    choices_json  TEXT,
    result_json   TEXT,
    submitted_by  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    submitted_at  TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ
);
"""
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_publish_sessions_account
    ON publish_sessions (account_id, created_at DESC);
"""

PLATFORMS = ("tiktok",)            # instagram / youtube / linkedin: adapters to come
CREATED_VIA = ("mcp", "studio")
STATUSES = ("draft", "posting", "published", "failed", "cancelled")
TTL = timedelta(hours=24)
STUCK_AFTER = timedelta(minutes=10)   # a claim whose init answer never landed
CAPTION_MAX = 2200                  # TikTok's title limit, in characters

OPERATOR_ENV = "PUBLISH_OPERATOR_ACCOUNT"
MEDIA_BASE_ENV = "PUBLISH_MEDIA_BASE_URL"
VERIFIED_ENV = "TIKTOK_VERIFIED_URL_PREFIXES"

# TikTok's own declaration lines (Content Sharing Guidelines, read
# 2026-10-11). The page prints exactly what the server returns, so the
# wording cannot drift between the page and what the audit reviewed.
DECLARATION_MUSIC = "By posting, you agree to TikTok's Music Usage Confirmation."
DECLARATION_BRANDED = ("By posting, you agree to TikTok's Branded Content Policy "
                       "and Music Usage Confirmation.")


class PublishError(ValueError):
    """A refusal the person can act on; the message says what to do."""


# --------------------------------------------------------------------------
# table
# --------------------------------------------------------------------------

def init(dsn: Optional[str] = None) -> None:
    """Create and own the table. Idempotent."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        db.own_table(conn, "publish_sessions")
        conn.execute(INDEXES)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row(session_id: str, account_id: Optional[int], dsn: Optional[str]) -> Optional[dict]:
    with db.connect(dsn) as conn:
        row = conn.execute(
            "SELECT * FROM publish_sessions WHERE id = %s "
            "AND account_id IS NOT DISTINCT FROM %s",
            (session_id, account_id)).fetchone()
    return dict(row) if row else None


def _load(session_id: str, account_id: Optional[int], dsn: Optional[str]) -> dict:
    row = _row(session_id, account_id, dsn)
    if not row:
        raise PublishError("no such post on this account -- prepare it again")
    return row


def _set(session_id: str, account_id: Optional[int], dsn: Optional[str], **fields) -> None:
    cols = ", ".join(f"{k} = %s" for k in fields)
    with db.connect(dsn) as conn:
        conn.execute(
            f"UPDATE publish_sessions SET {cols} WHERE id = %s "
            "AND account_id IS NOT DISTINCT FROM %s",
            (*fields.values(), session_id, account_id))


# --------------------------------------------------------------------------
# the media URL a platform will pull
# --------------------------------------------------------------------------

def publish_url(url: str) -> str:
    """The URL a platform should pull, rewritten onto the verified media
    host when PUBLISH_MEDIA_BASE_URL is set. Only URLs under the bucket's
    own public base are rewritten (same object key, verified host); any
    other URL is returned as is and judged by media_problem."""
    from . import storage
    target = (os.environ.get(MEDIA_BASE_ENV) or "").strip().rstrip("/")
    base = storage.public_base_url()
    if target and base and url.startswith(base + "/"):
        return target + url[len(base):]
    return url


def verified_prefixes() -> list[str]:
    raw = os.environ.get(VERIFIED_ENV) or ""
    return [p.strip() for p in raw.split(",") if p.strip()]


def _host_is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _under(url: str, entry: str) -> bool:
    """A URL is owned by a verified DOMAIN entry (`media.example.com`:
    that host and its subdomains) or a URL-PREFIX entry
    (`https://example.com/videos/`: exactly that prefix) -- TikTok's two
    property kinds."""
    if entry.startswith("https://"):
        return url.startswith(entry if entry.endswith("/") else entry + "/")
    host = (urlparse(url).hostname or "").lower()
    domain = entry.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


def media_problem(platform: str, url: str) -> Optional[str]:
    """Why this platform cannot pull this URL, or None. TikTok only, for
    now: it is the platform that pulls from a verified host."""
    if platform != "tiktok":
        return None
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.hostname:
        return "TikTok pulls media over https only, and this clip has no https URL."
    if _host_is_ip(parsed.hostname):
        return "TikTok will not pull from a bare IP address."
    prefixes = verified_prefixes()
    if not prefixes:
        return (f"No media host is verified with TikTok yet ({VERIFIED_ENV} is unset). "
                "Verify the media domain on the TikTok developer app, then list it there.")
    if not any(_under(url, p) for p in prefixes):
        return (f"{parsed.hostname} is not a verified TikTok media host "
                f"(verified: {', '.join(prefixes)}). Set {MEDIA_BASE_ENV} to the "
                "verified host so clips are served from it.")
    return None


# --------------------------------------------------------------------------
# whose credentials
# --------------------------------------------------------------------------

def _account_slug(account_id: Optional[int], dsn: Optional[str]) -> Optional[str]:
    if account_id is None:
        return None
    with db.connect(dsn) as conn:
        row = conn.execute("SELECT slug FROM accounts WHERE id = %s",
                           (account_id,)).fetchone()
    return row["slug"] if row else None


def token_for(account_id: Optional[int], platform: str, dsn: Optional[str] = None) -> str:
    """The credential that posts for this account. Today: the
    installation's env token, and only for the operator's account
    (PUBLISH_OPERATOR_ACCOUNT, a slug or an id). Per-account OAuth
    connections replace this function's body; nothing else changes."""
    if platform != "tiktok":
        raise PublishError(f"posting to {platform} is not built yet")
    operator = (os.environ.get(OPERATOR_ENV) or "").strip()
    is_operator = bool(operator) and (
        operator == str(account_id) or operator == _account_slug(account_id, dsn))
    if not is_operator:
        raise PublishError("Connect your TikTok account first -- posting from this "
                           "workspace is not set up yet.")
    token = tiktok.access_token()
    if not token:
        raise PublishError("The studio's TikTok connection has no token "
                           "(TIKTOK_ACCESS_TOKEN is unset).")
    return token


# --------------------------------------------------------------------------
# prepare: Claude or a studio button -- writes a draft, sends nothing
# --------------------------------------------------------------------------

def _source(ref: str, account_id: Optional[int], dsn: Optional[str]) -> dict:
    """gen:<id> (a render on the Assets wall) or asset:<id> (an import) ->
    {media_url, output_path, media_kind, seconds, ai_generated}. URLs are
    never taken: a post goes out from something this account owns."""
    from . import render_assets
    from .cut import store as cut_store
    kind, _, rest = (ref or "").partition(":")
    if not rest.isdigit() or kind not in ("gen", "asset"):
        raise PublishError(f"{ref!r}: a post's source is gen:<id> (a render on your "
                           "Assets wall) or asset:<id> (a clip you imported)")
    if kind == "gen":
        row = render_assets.get(int(rest), dsn, account_id=account_id)
        if not row or row.get("deleted_at"):
            raise PublishError(f"no render {rest} on this account")
        return {"media_url": row["media_url"], "output_path": row.get("output_path") or "",
                "media_kind": row["media_kind"],
                "seconds": _seconds(row.get("metadata") or {}),
                "ai_generated": True}       # everything the studio renders is AI
    row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
    if not row:
        raise PublishError(f"no import {rest} on this account")
    return {"media_url": row.get("media_url") or "", "output_path": row.get("output_path") or "",
            "media_kind": row.get("kind") or "", "seconds": row.get("seconds"),
            # an import may be real footage: the person says, on the page
            "ai_generated": False}


def _seconds(meta: dict) -> Optional[float]:
    """A render's length from its metadata (render_assets.get hands back
    `metadata`, parsed). Models record it as `seconds` or `duration`, top
    level or under `params`, sometimes as "8s"; None when it is not there,
    and TikTok then judges the length itself."""
    params = meta.get("params") if isinstance(meta.get("params"), dict) else {}
    for value in (meta.get("seconds"), meta.get("duration"),
                  params.get("seconds"), params.get("duration")):
        match = re.match(r"\s*(\d+(?:\.\d+)?)", str(value)) if value is not None else None
        if match:
            return float(match.group(1))
    return None


def _fetchable(src: dict, account_id: Optional[int]) -> Optional[str]:
    """The clip as a public URL (uploaded to the bucket if it is only on
    disk). The same helper the renderers use."""
    from . import effects
    return effects.fetchable_video(src["media_url"], src["output_path"],
                                   account_id=account_id)


def review_url(session_id: str) -> str:
    """Where the person reviews and sends it: the React studio
    (STUDIO_URL), or the path alone where no studio origin is set."""
    base = "".join(ch for ch in (os.environ.get("STUDIO_URL") or "")
                   if ch.isprintable()).strip().rstrip("/")
    return f"{base}/studio/publish/{session_id}"


def prepare(source: str, *, platform: str = "tiktok", caption: str = "",
            account_id: Optional[int], created_via: str = "studio",
            dsn: Optional[str] = None) -> dict:
    """Draft a post and return its review link. Sends nothing, spends
    nothing: the post exists only as a row until the person presses Post
    on the review page."""
    platform = (platform or "").strip().lower()
    if platform not in PLATFORMS:
        raise PublishError(f"posting to {platform or '(none)'} is not built yet -- "
                           f"available: {', '.join(PLATFORMS)}")
    if created_via not in CREATED_VIA:
        raise PublishError(f"created_via must be one of {CREATED_VIA}")
    caption = (caption or "").strip()
    if len(caption) > CAPTION_MAX:
        raise PublishError(f"the caption is {len(caption)} characters; "
                           f"{platform} takes at most {CAPTION_MAX}")
    src = _source(source, account_id, dsn)
    if src["media_kind"] != "video":
        raise PublishError(f"{source} is a {src['media_kind'] or 'file'}; "
                           "posting takes a video for now")
    url = _fetchable(src, account_id)
    if not url:
        raise PublishError(f"{source} is not in the studio's storage, so no platform "
                           "can fetch it")
    url = publish_url(url)
    session_id = secrets.token_urlsafe(16)
    expires = _now() + TTL
    with db.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO publish_sessions (id, account_id, platform, source_ref, media_url, "
            "media_kind, seconds, ai_generated, caption, created_via, expires_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (session_id, account_id, platform, source, url, src["media_kind"],
             src["seconds"], src["ai_generated"], caption, created_via, expires))
    return {"session_id": session_id, "platform": platform, "source": source,
            "review_url": review_url(session_id), "expires_at": expires.isoformat(),
            "media_problem": media_problem(platform, url),
            "note": ("Nothing has been posted. Open the review link to check the clip, "
                     "choose who can see it and press Post.")}


# --------------------------------------------------------------------------
# review: what the page renders
# --------------------------------------------------------------------------

def creator_view(raw: dict) -> dict:
    """creator_info's fields, named for the page."""
    return {
        "username": raw.get("creator_username") or "",
        "nickname": raw.get("creator_nickname") or raw.get("creator_username") or "",
        "avatar_url": raw.get("creator_avatar_url") or "",
        "privacy_options": list(raw.get("privacy_level_options") or []),
        "comment_disabled": bool(raw.get("comment_disabled")),
        "duet_disabled": bool(raw.get("duet_disabled")),
        "stitch_disabled": bool(raw.get("stitch_disabled")),
        "max_seconds": raw.get("max_video_post_duration_sec"),
    }


def _expired(row: dict) -> bool:
    return row["status"] == "draft" and row["expires_at"] <= _now()


def _public(row: dict) -> dict:
    status = "expired" if _expired(row) else row["status"]
    return {
        "session_id": row["id"], "platform": row["platform"], "status": status,
        "source": row["source_ref"], "media_url": row["media_url"],
        "media_kind": row["media_kind"], "seconds": row["seconds"],
        "ai_generated": row["ai_generated"], "caption": row["caption"],
        "created_via": row["created_via"],
        "expires_at": row["expires_at"].isoformat(),
        "choices": json.loads(row["choices_json"]) if row["choices_json"] else None,
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }


def review(session_id: str, *, account_id: Optional[int],
           dsn: Optional[str] = None) -> dict:
    """The session, plus -- while it is still a draft -- what the account
    may post right now, fetched fresh from the platform as the guidelines
    require, and the declaration the Post button carries. A post already
    sent is refreshed from the platform instead (`refresh`)."""
    row = _load(session_id, account_id, dsn)
    if row["status"] == "posting":
        return refresh(session_id, account_id=account_id, dsn=dsn)
    out = _public(row)
    out["media_problem"] = media_problem(row["platform"], row["media_url"])
    out["declarations"] = {"default": DECLARATION_MUSIC, "branded": DECLARATION_BRANDED}
    out["caption_max"] = CAPTION_MAX
    if out["status"] != "draft":
        return out
    token = None
    try:
        token = token_for(account_id, row["platform"], dsn)
        out["creator"] = creator_view(tiktok.creator_info(token))
        out["creator_problem"] = None
    except PublishError as e:
        out["creator"], out["creator_problem"] = None, str(e)
    except Exception as e:                                   # noqa: BLE001
        out["creator"] = None
        out["creator_problem"] = ("TikTok did not say what this account may post "
                                  f"({tiktok._safe_error(e, token)}). Try again in a moment.")
    return out


# --------------------------------------------------------------------------
# submit: the press of Post, from the signed-in page and nowhere else
# --------------------------------------------------------------------------

def validate_tiktok(choices: dict, creator: dict, *, seconds: Optional[float],
                    ai_generated: bool) -> dict:
    """The person's answers -> TikTok's post_info fields, or a PublishError
    naming the first one that breaks a Direct Post rule. Pure: no I/O."""
    choices = choices or {}
    if choices.get("consent") is not True:
        raise PublishError("Agree to the declaration under the Post button to post.")
    privacy = choices.get("privacy_level")
    options = creator.get("privacy_options") or []
    if not privacy:
        raise PublishError("Choose who can see this post -- there is no default.")
    if privacy not in options:
        raise PublishError(f"{privacy} is not available on this account right now "
                           f"(available: {', '.join(options) or 'none'}).")
    max_seconds = creator.get("max_seconds")
    if seconds and max_seconds and float(seconds) > float(max_seconds):
        raise PublishError(f"This clip is {float(seconds):.0f}s; this account can post "
                           f"at most {max_seconds}s.")

    def allowed(key: str, disabled_key: str) -> bool:
        # an interaction the creator switched off on TikTok stays off
        return bool(choices.get(key)) and not creator.get(disabled_key)

    commercial = choices.get("commercial") or {}
    enabled = bool(commercial.get("enabled"))
    your_brand = enabled and bool(commercial.get("your_brand"))
    branded = enabled and bool(commercial.get("branded_content"))
    if enabled and not (your_brand or branded):
        raise PublishError("You said this post promotes something: choose "
                           "\"Your brand\", \"Branded content\" or both.")
    if branded and privacy == "SELF_ONLY":
        raise PublishError("Branded content cannot be posted as private (Only me).")

    # AI-made clips carry TikTok's AI-generated label; only an import of
    # the person's own footage may leave it off.
    is_aigc = True if ai_generated else bool(choices.get("is_aigc"))
    return {"privacy_level": privacy,
            "disable_comment": not allowed("allow_comment", "comment_disabled"),
            "disable_duet": not allowed("allow_duet", "duet_disabled"),
            "disable_stitch": not allowed("allow_stitch", "stitch_disabled"),
            "brand_organic_toggle": your_brand,
            "brand_content_toggle": branded,
            "is_aigc": is_aigc}


def submit(session_id: str, choices: dict, *, account_id: Optional[int],
           user_id: Optional[str], dsn: Optional[str] = None) -> dict:
    """Send the post: re-read what the account may post (never trust a
    page rendered minutes ago), check every answer, claim the session
    once, then hand TikTok the URL. TikTok publishes asynchronously, so
    this returns `posting` with the publish_id; the page polls `review`,
    which refreshes it. A second press returns the first one's state and
    sends nothing."""
    row = _load(session_id, account_id, dsn)
    if _expired(row):
        raise PublishError("This draft expired -- prepare the post again.")
    if row["status"] != "draft":
        return _public(row)
    caption = choices.get("caption", row["caption"])
    caption = (caption if isinstance(caption, str) else "").strip()
    if len(caption) > CAPTION_MAX:
        raise PublishError(f"The caption is {len(caption)} characters; "
                           f"TikTok takes at most {CAPTION_MAX}.")
    problem = media_problem(row["platform"], row["media_url"])
    if problem:
        raise PublishError(problem)
    token = token_for(account_id, row["platform"], dsn)
    try:
        creator = creator_view(tiktok.creator_info(token))
    except Exception as e:                                   # noqa: BLE001
        raise PublishError("TikTok did not say what this account may post "
                           f"({tiktok._safe_error(e, token)}). Nothing was sent.") from e
    post_info = validate_tiktok(choices, creator, seconds=row["seconds"],
                                ai_generated=row["ai_generated"])

    with db.connect(dsn) as conn:
        won = conn.execute(
            "UPDATE publish_sessions SET status = 'posting', choices_json = %s, "
            "caption = %s, submitted_by = %s, submitted_at = now() "
            "WHERE id = %s AND account_id IS NOT DISTINCT FROM %s AND status = 'draft' "
            "RETURNING id",
            (json.dumps(post_info), caption, user_id, session_id, account_id)).fetchone()
    if not won:                      # a second press, racing the first
        return _public(_load(session_id, account_id, dsn))

    privacy = post_info.pop("privacy_level")
    try:
        publish_id = tiktok.init_direct_post(row["media_url"], caption, token,
                                             privacy_level=privacy, options=post_info)
    except Exception as e:                                   # noqa: BLE001
        _set(session_id, account_id, dsn, status="failed", finished_at=_now(),
             result_json=json.dumps({"step": "init", "error": tiktok._safe_error(e, token)}))
        return _public(_load(session_id, account_id, dsn))
    _set(session_id, account_id, dsn,
         result_json=json.dumps({"publish_id": publish_id}))
    return _public(_load(session_id, account_id, dsn))


def refresh(session_id: str, *, account_id: Optional[int],
            dsn: Optional[str] = None) -> dict:
    """One status poll for a post TikTok is still processing; terminal
    states are written once and then simply read back."""
    row = _load(session_id, account_id, dsn)
    if row["status"] != "posting":
        return _public(row)
    result = json.loads(row["result_json"] or "{}")
    publish_id = result.get("publish_id")
    if not publish_id:
        # claimed, but the init's answer was never stored (the process died
        # between the two): after STUCK_AFTER it is failed, never a draft
        # again -- TikTok may have the post, and a second press could double it
        if row["submitted_at"] and row["submitted_at"] <= _now() - STUCK_AFTER:
            _set(session_id, account_id, dsn, status="failed", finished_at=_now(),
                 result_json=json.dumps({"step": "init", "error": (
                     "the studio lost track of this post while sending it -- check "
                     "your TikTok profile before posting it again")}))
            return _public(_load(session_id, account_id, dsn))
        return _public(row)
    token = None
    try:
        token = token_for(account_id, row["platform"], dsn)
        state = tiktok.publish_status(publish_id, token)
    except Exception as e:                                   # noqa: BLE001
        out = _public(row)
        out["poll_problem"] = tiktok._safe_error(e, token)
        return out
    if state["status"] == tiktok.PUBLISH_COMPLETE:
        _set(session_id, account_id, dsn, status="published", finished_at=_now(),
             result_json=json.dumps({**result, "post_id": state["post_id"]}))
    elif state["status"] in tiktok.PUBLISH_FAILED:
        _set(session_id, account_id, dsn, status="failed", finished_at=_now(),
             result_json=json.dumps({**result, "step": "poll",
                                     "error": state["fail_reason"] or state["status"]}))
    return _public(_load(session_id, account_id, dsn))


def cancel(session_id: str, *, account_id: Optional[int],
           dsn: Optional[str] = None) -> dict:
    """Throw a draft away. A post already sent cannot be cancelled here."""
    with db.connect(dsn) as conn:
        conn.execute(
            "UPDATE publish_sessions SET status = 'cancelled', finished_at = now() "
            "WHERE id = %s AND account_id IS NOT DISTINCT FROM %s AND status = 'draft'",
            (session_id, account_id))
    return _public(_load(session_id, account_id, dsn))


def recent(*, account_id: Optional[int], limit: int = 20,
           dsn: Optional[str] = None) -> list[dict[str, Any]]:
    """This account's latest posts, newest first."""
    with db.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT * FROM publish_sessions WHERE account_id IS NOT DISTINCT FROM %s "
            "ORDER BY created_at DESC LIMIT %s",
            (account_id, max(1, min(int(limit), 100)))).fetchall()
    return [_public(dict(r)) for r in rows]
