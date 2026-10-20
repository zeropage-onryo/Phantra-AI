"""A finished render, shared on a public page (2026-10-20, the Vesper review's
"crossing card").

Nothing is public until its owner presses Share on that one item, and
Unshare takes the page down at once. Mike's calls (2026-10-20): the page
shows the video, the Vesper art and the workspace's name -- never the
prompt, the model, credits or a price -- and a video only becomes public by
that per-item button.

THE TOKEN IS THE ADDRESS. A share is a random 128-bit token in a row of this
table, never a signature: a share lives until it is taken down, so it must
be revocable, and a row can be. One live share per item: sharing again hands
back the same address; Unshare stamps `revoked_at` and the address is dead
for good (a re-share mints a new one, so an old link never comes back).

WHAT THE PAGE IS GIVEN (`public`): the media kind, a playable address minted
on read (`media.url_for` -- never stored, so it follows the bucket's rung,
including presigned URLs that expire), the 480px poster when there is one,
and the workspace's display name. A share of an item since deleted (soft:
`deleted_at`), or of a workspace's row that is gone, reads as no share at
all. Nothing here raises to the public route: a read that fails is "not
found".

Owned like every table a person's things sit in (db.OWNED_TABLES); the
public read is the one lookup by token alone, and it hands back only the
fields above.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from . import db

TABLE = "video_shares"
PAGE_PATH = "/v"

SCHEMA = """
CREATE TABLE IF NOT EXISTS video_shares (
    token         TEXT PRIMARY KEY,
    account_id    BIGINT,
    generated_id  BIGINT NOT NULL,
    created_at    TEXT NOT NULL,
    revoked_at    TEXT
);
CREATE INDEX IF NOT EXISTS video_shares_item ON video_shares (account_id, generated_id);
"""

_ready: set[str] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init(dsn: Optional[str] = None) -> None:
    """Create and own the table. Idempotent; the app lifespan runs it."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        db.own_table(conn, TABLE)
    _ready.add(db.resolve_dsn(dsn))


def ensure(dsn: Optional[str] = None) -> None:
    """The table, made once per process per database -- never an init per
    request (two at once deadlock)."""
    if db.resolve_dsn(dsn) in _ready:
        return
    db.run_init(lambda: init(dsn), dsn)


def _item(conn, generated_id: int, account_id: Optional[int]) -> Optional[dict]:
    """This account's render, not deleted, or None."""
    if not db.table_exists(conn, "generated_assets"):
        return None
    row = conn.execute(
        "SELECT * FROM generated_assets WHERE id = %s AND account_id IS NOT DISTINCT FROM %s",
        (int(generated_id), account_id)).fetchone()
    if not row:
        return None
    row = dict(row)
    return None if row.get("deleted_at") else row


def _live(conn, generated_id: int, account_id: Optional[int]) -> Optional[str]:
    row = conn.execute(
        "SELECT token FROM video_shares WHERE generated_id = %s "
        "AND account_id IS NOT DISTINCT FROM %s AND revoked_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1", (int(generated_id), account_id)).fetchone()
    return row["token"] if row else None


def status(generated_id: int, *, account_id: Optional[int],
           dsn: Optional[str] = None) -> Optional[str]:
    """The live share's token for this item of this account's, or None."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        return _live(conn, generated_id, account_id)


def share(generated_id: int, *, account_id: Optional[int],
          dsn: Optional[str] = None) -> str:
    """Share this account's render: its live token, or a new one. Raises
    LookupError for an item that is not theirs, or deleted."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        if _item(conn, generated_id, account_id) is None:
            raise LookupError(f"no item {generated_id} to share")
        live = _live(conn, generated_id, account_id)
        if live:
            return live
        token = secrets.token_urlsafe(16)
        conn.execute(
            "INSERT INTO video_shares (token, account_id, generated_id, created_at) "
            "VALUES (%s, %s, %s, %s)", (token, account_id, int(generated_id), _now()))
        return token


def unshare(generated_id: int, *, account_id: Optional[int],
            dsn: Optional[str] = None) -> int:
    """Take every live share of this item down. Returns how many."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        cur = conn.execute(
            "UPDATE video_shares SET revoked_at = %s WHERE generated_id = %s "
            "AND account_id IS NOT DISTINCT FROM %s AND revoked_at IS NULL",
            (_now(), int(generated_id), account_id))
        return cur.rowcount or 0


def public(token: str, dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """What the public page shows for a token, or None. Only the media kind,
    a playable address minted now, the poster and the workspace's name."""
    from . import media
    token = (token or "").strip()
    if not token or len(token) > 64:
        return None
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            row = conn.execute(
                "SELECT account_id, generated_id, created_at FROM video_shares "
                "WHERE token = %s AND revoked_at IS NULL", (token,)).fetchone()
            if not row:
                return None
            item = _item(conn, row["generated_id"], row["account_id"])
            if item is None or not item.get("media_url"):
                return None
            who = conn.execute("SELECT display_name FROM accounts WHERE id = %s",
                               (row["account_id"],)).fetchone() \
                if row["account_id"] is not None and db.table_exists(conn, "accounts") else None
        account = row["account_id"]
        stored = str(item["media_url"])
        poster = None
        if item.get("media_kind") == "video":
            try:
                poster = media.thumb_url_for(stored, account)
            except Exception:                                   # noqa: BLE001
                poster = None
        return {"kind": item.get("media_kind") or "video",
                "url": media.url_for(stored, account),
                "poster": poster,
                "creator": (who["display_name"] if who else "") or "",
                "shared_at": row["created_at"]}
    except Exception:                                           # noqa: BLE001
        return None


__all__ = ["TABLE", "PAGE_PATH", "init", "ensure", "status", "share", "unshare", "public"]
