"""
The publish worker: the clock behind `posts` (2026-10-22,
docs/tasks/task-publish-worker.md). The ONLY caller of a provider's
post_start / post_check / post_finish.

WHY A LOOP OVER POSTGRES AND NOT A WORKFLOW ENGINE. Postiz runs one
Temporal workflow per post, sleeping until its publish date. That buys
durable timers at a scale this studio is nowhere near, and costs a
second service to run. The same durability comes from the rows: a post
is `queued` with a `publish_at`, and a tick every TICK_SECONDS claims the
due ones with `FOR UPDATE SKIP LOCKED` -- so two workers never take the
same row, a restart loses nothing (the row is still there), and a missed
window is simply a row the next tick finds, no sweep needed.

ONE TICK:

1. CLAIM the due rows (`queued`, `publish_at` passed, not before
   `next_attempt_at`): each becomes `publishing` with this worker's name
   on it in the same statement, then `post_start` runs. 'completed' lands
   it; 'pending' writes `pending_json` and a `next_attempt_at`.
2. POLL the pending rows whose time has come: `post_check`, then
   `post_finish` when 'ready'. A row pending past PENDING_GIVE_UP_SECONDS
   is an error, not a forever.
3. STUCK rows -- `publishing`, nothing pending, held longer than
   posts.STUCK_SECONDS -- are a worker that died between the platform's
   answer and the write. They are marked `error` and NEVER re-sent on
   their own, because the platform may already have the post; the person
   checks and presses "Post again" if not.

WHAT IS RETRIED AND WHAT IS NOT. A transport failure or a 5xx from the
platform is theirs, and the row goes back to `queued` with a backoff
(attempts counted, MAX_ATTEMPTS then `error`). PostFailed (the platform
said no to THIS post) and ConnectRefused (the token needs the person) are
terminal at once: retrying a refusal is how the same wrong post arrives
five times. The reason is written on the row in plain words.

WHEN A POST LANDS: release_id and release_url on the row, a `videos` row
(the audience loop: preprod.posted_outcomes joins it by concept_id and
src.refresh_metrics reads its counts back), and outcomes.record("post")
on the render -- the kept signal.

Run it: `python -m src.publish_worker` (the loop; ops/fly/supervisord.conf
runs it beside the API), `--once` for one tick, `--account N` to narrow
to one workspace. Nothing here spends credits.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from . import db, posts, social, social_connections
from .social.base import ConnectRefused, PostFailed, PostResult

TICK_SECONDS = 20
PENDING_POLL_SECONDS = 20
PENDING_GIVE_UP_SECONDS = 15 * 60
MAX_ATTEMPTS = 5
BATCH = 10
BACKOFF_SECONDS = (60, 300, 900, 1800, 3600)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def worker_name() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


# --------------------------------------------------------------------------
# claims
# --------------------------------------------------------------------------

def _claim_due(account_id: Optional[int], who: str, now: datetime,
               dsn: Optional[str]) -> list[dict]:
    """The due queued rows, each flipped to `publishing` under this
    worker's name in the same statement (SKIP LOCKED: a second worker
    takes the next ones). `account_id` None is every workspace: the
    worker runs for all of them, and each row is then handled under the
    account_id read off it."""
    with db.connect(dsn) as conn:
        rows = conn.execute(
            """
            UPDATE posts SET state = 'publishing', locked_by = %s, locked_at = %s,
                             attempts = attempts + 1, updated_at = now()
            WHERE id IN (
                SELECT id FROM posts
                WHERE (%s::bigint IS NULL OR account_id IS NOT DISTINCT FROM %s)
                  AND state = 'queued' AND deleted_at IS NULL
                  AND publish_at <= %s
                  AND (next_attempt_at IS NULL OR next_attempt_at <= %s)
                ORDER BY publish_at, id
                LIMIT %s
                FOR UPDATE SKIP LOCKED)
            RETURNING *
            """,
            (who, now, account_id, account_id, now, now, BATCH)).fetchall()
    return [dict(r) for r in rows]


def _claim_pending(account_id: Optional[int], who: str, now: datetime,
                   dsn: Optional[str]) -> list[dict]:
    """The pending rows whose poll time has come, their next poll moved
    out in the same statement so another worker skips them."""
    with db.connect(dsn) as conn:
        rows = conn.execute(
            """
            UPDATE posts SET locked_by = %s, locked_at = %s,
                             next_attempt_at = %s, updated_at = now()
            WHERE id IN (
                SELECT id FROM posts
                WHERE (%s::bigint IS NULL OR account_id IS NOT DISTINCT FROM %s)
                  AND state = 'publishing' AND pending_json IS NOT NULL AND deleted_at IS NULL
                  AND (next_attempt_at IS NULL OR next_attempt_at <= %s)
                ORDER BY next_attempt_at NULLS FIRST, id
                LIMIT %s
                FOR UPDATE SKIP LOCKED)
            RETURNING *
            """,
            (who, now, now + timedelta(seconds=PENDING_POLL_SECONDS),
             account_id, account_id, now, BATCH)).fetchall()
    return [dict(r) for r in rows]


def _mark_stuck(account_id: Optional[int], now: datetime, dsn: Optional[str]) -> int:
    cutoff = now - timedelta(seconds=posts.STUCK_SECONDS)
    with db.connect(dsn) as conn:
        rows = conn.execute(
            """
            UPDATE posts SET state = 'error', locked_by = NULL, updated_at = now(),
                error = 'The worker stopped while this post was being sent. Check the platform '
                        'before posting it again.'
            WHERE (%s::bigint IS NULL OR account_id IS NOT DISTINCT FROM %s)
              AND state = 'publishing' AND pending_json IS NULL AND deleted_at IS NULL
              AND locked_at IS NOT NULL AND locked_at < %s
            RETURNING id, account_id
            """,
            (account_id, account_id, cutoff)).fetchall()
    for r in rows:
        posts.note(int(r["account_id"]), int(r["id"]), "error", "worker stopped mid-send", dsn=dsn)
    return len(rows)


# --------------------------------------------------------------------------
# the writes
# --------------------------------------------------------------------------

def _set(row: dict, dsn: Optional[str], **fields: Any) -> None:
    cols = ", ".join(f"{k} = %s" for k in fields)
    with db.connect(dsn) as conn:
        conn.execute(
            f"UPDATE posts SET {cols}, updated_at = now() WHERE id = %s AND account_id = %s",
            (*fields.values(), row["id"], row["account_id"]))


def _published(row: dict, result: PostResult, dsn: Optional[str]) -> None:
    now = _now()
    _set(row, dsn, state="published", release_id=result.release_id or None,
         release_url=result.release_url or None, published_at=now, pending_json=None,
         locked_by=None, error=None)
    posts.note(int(row["account_id"]), int(row["id"]), "published",
               result.release_url or result.release_id, dsn=dsn)
    video_id = _record_video(row, result, now, dsn)
    if video_id is not None:
        _set(row, dsn, video_id=video_id)
    try:
        from . import outcomes
        outcomes.record_ref("post", row["source_ref"], account_id=int(row["account_id"]),
                            source="publish_worker",
                            meta={"post_id": int(row["id"]), "provider": row["provider"]}, dsn=dsn)
    except Exception:
        pass


def _record_video(row: dict, result: PostResult, now: datetime, dsn: Optional[str]) -> Optional[int]:
    """The audience loop's row. Best effort: a post that landed is landed
    whether or not its bookkeeping wrote."""
    try:
        media = json.loads(row.get("media_json") or "{}")
    except ValueError:
        media = {}
    caption = (row.get("caption") or "").strip().splitlines()
    title = (caption[0] if caption else f"{row['provider']} post")[:120]
    try:
        video_id = db.add_video(
            title=title, platform=row["provider"], posted_at=now.strftime("%Y-%m-%dT%H:%M:%S"),
            url=result.release_url or (result.release_id or None),
            duration_s=media.get("seconds"), notes=f"post:{row['id']}", dsn=dsn,
            account_id=int(row["account_id"]))
        if row.get("concept_id"):
            with db.connect(dsn) as conn:
                conn.execute("UPDATE videos SET concept_id = %s WHERE id = %s AND account_id = %s",
                             (row["concept_id"], video_id, row["account_id"]))
        return int(video_id)
    except Exception as e:  # pragma: no cover - bookkeeping
        print(f"publish_worker: post {row['id']} landed; videos row not written: {e}", file=sys.stderr)
        return None


def _failed(row: dict, reason: str, dsn: Optional[str]) -> None:
    _set(row, dsn, state="error", error=reason[:1000], pending_json=None, locked_by=None)
    posts.note(int(row["account_id"]), int(row["id"]), "error", reason, dsn=dsn)


def _retry_later(row: dict, reason: str, dsn: Optional[str]) -> str:
    """Back to queued with a backoff, or error once the attempts are
    spent. Returns which."""
    attempts = int(row.get("attempts") or 0)
    if attempts >= MAX_ATTEMPTS:
        _failed(row, f"Gave up after {attempts} tries. Last answer: {reason}", dsn)
        return "error"
    wait = BACKOFF_SECONDS[min(attempts, len(BACKOFF_SECONDS)) - 1]
    _set(row, dsn, state="queued", next_attempt_at=_now() + timedelta(seconds=wait),
         pending_json=None, locked_by=None, error=reason[:1000])
    posts.note(int(row["account_id"]), int(row["id"]), "retry",
               f"try {attempts} failed, next in {wait}s: {reason}", dsn=dsn)
    return "retry"


# --------------------------------------------------------------------------
# one post
# --------------------------------------------------------------------------

def _fetchable(media: dict[str, Any], account_id: int) -> str:
    """The file as an address the platform can fetch: a public URL as it
    is, a local-only render pushed to the bucket. '' when neither."""
    from . import effects
    url = media.get("media_url") or ""
    path = media.get("output_path") or ""
    try:
        got = effects.fetchable_video(url, path, account_id=account_id)
    except Exception:
        got = None
    return got or (url if url.startswith("https://") else "")


def _post_body(row: dict, account_id: int) -> dict[str, Any]:
    try:
        media = json.loads(row.get("media_json") or "{}")
    except ValueError:
        media = {}
    try:
        settings = json.loads(row.get("settings_json") or "{}")
    except ValueError:
        settings = {}
    return {
        "caption": row.get("caption") or "",
        "media": {"ref": media.get("ref"), "url": _fetchable(media, account_id),
                  "kind": media.get("kind"), "seconds": media.get("seconds"),
                  "path": media.get("output_path") or ""},
        "settings": settings,
    }


def _credential(row: dict, dsn: Optional[str]):
    """(token, the connection's meta, the provider module), or raises
    ConnectRefused in the person's words."""
    mod = social.get(row["provider"])
    if mod is None or not hasattr(mod, "post_start"):
        raise PostFailed(f"Posting to {row['provider']} is not built.")
    token, conn = social_connections.token_for(int(row["account_id"]), row["provider"],
                                               connection_id=int(row["connection_id"]), dsn=dsn)
    return token, conn.get("meta") or {}, mod


def send(row: dict, dsn: Optional[str] = None) -> str:
    """Start one claimed post. Returns published | pending | retry | error."""
    account_id = int(row["account_id"])
    try:
        token, meta, mod = _credential(row, dsn)
        body = _post_body(row, account_id)
        result = mod.post_start(token, meta, body)
    except (PostFailed, ConnectRefused) as e:
        _failed(row, str(e), dsn)
        return "error"
    except requests.RequestException as e:
        from .social import base
        return _retry_later(row, base.problem(e), dsn)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return _retry_later(row, f"{type(e).__name__}: {e}"[:300], dsn)
    if result.status == "completed":
        _published(row, result, dsn)
        return "published"
    _set(row, dsn, pending_json=json.dumps({**result.pending, "since": _now().isoformat()}),
         next_attempt_at=_now() + timedelta(seconds=PENDING_POLL_SECONDS))
    posts.note(account_id, int(row["id"]), "pending", json.dumps(result.pending)[:300], dsn=dsn)
    return "pending"


def poll(row: dict, dsn: Optional[str] = None) -> str:
    """One check of a pending post. Returns published | pending | error."""
    try:
        pending = json.loads(row.get("pending_json") or "{}")
    except ValueError:
        pending = {}
    since = pending.get("since")
    try:
        started = datetime.fromisoformat(since) if since else _now()
    except ValueError:
        started = _now()
    if _now() - started > timedelta(seconds=PENDING_GIVE_UP_SECONDS):
        _failed(row, "The platform did not finish processing the post in time.", dsn)
        return "error"
    try:
        token, meta, mod = _credential(row, dsn)
        result = mod.post_check(token, meta, pending)
        if result.status == "ready":
            result = mod.post_finish(token, meta, {**pending, **(result.pending or {})})
    except (PostFailed, ConnectRefused) as e:
        _failed(row, str(e), dsn)
        return "error"
    except requests.RequestException:
        return "pending"            # asked again next poll; the deadline above ends it
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        _failed(row, f"{type(e).__name__}: {e}"[:300], dsn)
        return "error"
    if result.status == "completed":
        _published(row, result, dsn)
        return "published"
    if result.pending and result.pending != {k: v for k, v in pending.items() if k != "since"}:
        _set(row, dsn, pending_json=json.dumps({**pending, **result.pending}))
    return "pending"


# --------------------------------------------------------------------------
# the tick and the loop
# --------------------------------------------------------------------------

def tick(dsn: Optional[str] = None, *, account_id: Optional[int] = None,
         who: Optional[str] = None, now: Optional[datetime] = None) -> dict[str, Any]:
    """One pass. Never raises for one post's sake: a post that blows up is
    an error row, and the next one is tried."""
    posts.ensure(dsn)
    who = who or worker_name()
    moment = now or _now()
    out: dict[str, Any] = {"published": 0, "pending": 0, "retry": 0, "error": 0, "stuck": 0,
                           "claimed": 0, "polled": 0}
    out["stuck"] = _mark_stuck(account_id, moment, dsn)
    for row in _claim_due(account_id, who, moment, dsn):
        out["claimed"] += 1
        out[send(row, dsn)] += 1
    for row in _claim_pending(account_id, who, moment, dsn):
        out["polled"] += 1
        out[poll(row, dsn)] += 1
    return out


def run(interval: float = TICK_SECONDS, *, dsn: Optional[str] = None,
        account_id: Optional[int] = None, once: bool = False) -> None:
    stop = {"now": False}

    def _stop(signum, frame):
        stop["now"] = True
    try:
        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
    except (ValueError, OSError):  # pragma: no cover - not the main thread
        pass
    print(f"publish_worker: {worker_name()} every {interval:g}s", file=sys.stderr)
    while True:
        try:
            summary = tick(dsn, account_id=account_id)
            if any(summary[k] for k in ("claimed", "polled", "stuck")):
                print(f"publish_worker: {summary}", file=sys.stderr)
        except Exception:
            traceback.print_exc(file=sys.stderr)
        if once or stop["now"]:
            return
        slept = 0.0
        while slept < interval and not stop["now"]:
            time.sleep(min(1.0, interval - slept))
            slept += 1.0
        if stop["now"]:
            return


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="The publish worker: sends due posts.")
    ap.add_argument("--once", action="store_true", help="one tick, then exit")
    ap.add_argument("--interval", type=float, default=TICK_SECONDS)
    ap.add_argument("--account", type=int, default=None, help="only this account's posts")
    ap.add_argument("--dsn", default=None)
    args = ap.parse_args(argv)
    run(args.interval, dsn=args.dsn, account_id=args.account, once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
