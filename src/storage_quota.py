"""What a workspace keeps in storage, the limit its plan sets, and the trash.

Mike's calls, 2026-10-20:

- Each plan carries a storage limit (pricing.Plan.storage_gb; no plan is
  pricing.FREE_STORAGE_GB; a credit-exempt workspace has none).
- Deleting a render puts it in the TRASH: it stops counting at once and can
  be restored for TRASH_DAYS days, then its file is removed from the bucket.
  Runway's own Library has no trash at all (checked in the app that day);
  this is the safety net for a clip somebody paid credits for.
- Over the limit, UPLOADS are refused (src/cut/uploads.save, the element
  create in app/api.py). Renders never are: refusing a render someone is
  paying for is the worst moment to say no, and a render lands in the
  library either way.
- The bar sits in Settings -> Plan, next to the plan (GET /api/storage).

WHAT IS COUNTED is the bucket itself: every object under the workspace's own
prefixes (src/media.py `m/<account>/` masters and `t/<account>/` thumbnails
and posters) -- renders, element photos, editor uploads, exports -- minus the
renders sitting in the trash. The shared reference bin (`m/shared/`) is
nobody's and is not counted. Where usage cannot be measured (no bucket on
this machine, or media still on the flat `legacy` keys) the answer says so
(`measured: False`) and nothing is refused: a limit checked against a guess
refuses people for nothing.

THE PURGE has no scheduler (the Fly image's one cron line is the Instagram
token keeper, and stays that way): it runs for one workspace whenever that
workspace's usage is read -- the bar, the Library's trash view, an upload's
check. A trashed render that a scene's shot or a cut still uses is NOT
purged (its file is what that scene or cut plays); it stays in the trash,
counted, and says why.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from . import db, media, storage

TRASH_DAYS = 7
GB = 1_000_000_000          # a decimal gigabyte, the unit the plans are sold in
NEAR = 0.9                  # the bar warns from here

RENDERS_ROOT = Path(__file__).resolve().parent.parent / "data" / "renders"


class StorageFull(Exception):
    """An upload that would take a workspace past its plan's storage."""

    def __init__(self, message: str, usage: dict[str, Any]):
        super().__init__(message)
        self.usage = usage


# --- the limit ----------------------------------------------------------------

def limit_bytes(account_id: Optional[int], dsn: Optional[str] = None) -> Optional[int]:
    """The workspace's storage limit in bytes, or None for no limit (an
    exempt workspace, or no account to ask about)."""
    if account_id is None:
        return None
    from . import accounts, pricing
    if accounts.is_credit_exempt(account_id, dsn=dsn):
        return None
    plan = pricing.PLANS.get(accounts.plan_of(account_id, dsn=dsn) or "")
    gb = plan.storage_gb if plan else pricing.FREE_STORAGE_GB
    return int(gb) * GB


# --- the trash ----------------------------------------------------------------

def _parse(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def trashed(account_id: Optional[int], dsn: Optional[str] = None) -> list[dict[str, Any]]:
    """This workspace's renders in the trash (deleted, not yet purged),
    newest deletion first, each with `purge_at`."""
    with db.connect(dsn) as conn:
        if not db.table_exists(conn, "generated_assets") \
                or "purged_at" not in db.columns(conn, "generated_assets"):
            return []
        rows = conn.execute(
            "SELECT id, media_url, media_kind, tool, model, prompt, deleted_at, created_at "
            "FROM generated_assets WHERE account_id IS NOT DISTINCT FROM %s "
            "AND deleted_at IS NOT NULL AND purged_at IS NULL ORDER BY deleted_at DESC",
            (account_id,)).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        deleted = _parse(item.get("deleted_at"))
        item["purge_at"] = ((deleted + timedelta(days=TRASH_DAYS)).isoformat(timespec="seconds")
                            if deleted else None)
        out.append(item)
    return out


def _keys_of(media_url: str, account_id: Optional[int], sizes: dict[str, int]) -> list[str]:
    """The bucket objects one render occupies: its master and anything in
    its thumbnail stem (the 480px still, a clip's poster)."""
    master = media.master_key(media_url, account_id)
    thumb = media.thumb_key(media_url, account_id)
    keys = [master] if master and master in sizes else []
    if thumb:
        stem = thumb.rsplit(".", 1)[0]
        keys += [k for k in sizes if k.startswith(stem)]
    return keys


def _in_use(conn, row: dict[str, Any], account_id: Optional[int]) -> Optional[str]:
    """Why a trashed render must keep its file, or None."""
    url = row.get("media_url") or ""
    like = "%" + url.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    if url and db.table_exists(conn, "shoot_concepts"):
        hit = conn.execute(
            "SELECT id FROM shoot_concepts WHERE account_id IS NOT DISTINCT FROM %s "
            "AND shots_json LIKE %s LIMIT 1", (account_id, like)).fetchone()
        if hit:
            return f"used by scene {hit['id']}"
    if db.table_exists(conn, "timelines"):
        hit = conn.execute(
            "SELECT project_id FROM timelines WHERE account_id IS NOT DISTINCT FROM %s "
            "AND doc::text LIKE %s LIMIT 1",
            (account_id, f'%"gen:{int(row["id"])}"%')).fetchone()
        if hit:
            return "used in a cut"
    return None


def purge_due(account_id: Optional[int], dsn: Optional[str] = None, *,
              now: Optional[datetime] = None, only: Optional[int] = None) -> dict[str, Any]:
    """Empty this workspace's trash of renders deleted more than TRASH_DAYS
    ago: remove their files (bucket and this disk) and stamp `purged_at`.
    `only` narrows it to one render ("Delete forever"). Never raises;
    returns {"purged": [ids], "kept": {id: reason}}."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=TRASH_DAYS)
    result: dict[str, Any] = {"purged": [], "kept": {}}
    try:
        due = [r for r in trashed(account_id, dsn)
               if (_parse(r.get("deleted_at")) or now) <= cutoff
               and (only is None or r["id"] == only)]
        if not due:
            return result
        sizes = _account_sizes(account_id) or {}
        with db.connect(dsn) as conn:
            for row in due:
                reason = _in_use(conn, row, account_id)
                if reason:
                    result["kept"][row["id"]] = reason
                    continue
                for key in _keys_of(row["media_url"], account_id, sizes):
                    try:
                        storage.delete_key(key)
                    except Exception as e:                  # noqa: BLE001
                        print(f"  trash: could not delete {key}: {e}")
                _unlink_local(row["media_url"])
                conn.execute("UPDATE generated_assets SET purged_at = %s WHERE id = %s",
                             (now.isoformat(timespec="seconds"), row["id"]))
                result["purged"].append(row["id"])
    except Exception as e:                                  # noqa: BLE001
        print(f"  trash: purge for account {account_id} stopped: {e}")
    return result


def _unlink_local(media_url: str) -> None:
    """A render's copy on this machine, only ever under data/renders."""
    url = str(media_url or "")
    if not url.startswith("/renders/"):
        return
    target = (RENDERS_ROOT / url[len("/renders/"):]).resolve()
    if RENDERS_ROOT.resolve() in target.parents:
        target.unlink(missing_ok=True)


# --- usage --------------------------------------------------------------------

def _account_sizes(account_id: Optional[int]) -> Optional[dict[str, int]]:
    """{key: bytes} for every object under this workspace's own prefixes,
    or None when that cannot be known."""
    if account_id is None or not media.tenant_keys():
        return None
    out: dict[str, int] = {}
    for prefix in (media.MASTER_PREFIX, media.THUMB_PREFIX):
        part = storage.sizes_under(f"{prefix}/{int(account_id)}/")
        if part is None:
            return None
        out.update(part)
    return out


def usage(account_id: Optional[int], dsn: Optional[str] = None, *,
          purge: bool = True) -> dict[str, Any]:
    """{measured, used_bytes, limit_bytes, trash_bytes, trash_count,
    trash_days, near, over}. `used_bytes` leaves the trash out."""
    if purge:
        purge_due(account_id, dsn)
    limit = limit_bytes(account_id, dsn)
    in_trash = trashed(account_id, dsn)
    sizes = _account_sizes(account_id)
    out: dict[str, Any] = {
        "measured": sizes is not None, "used_bytes": None, "limit_bytes": limit,
        "trash_bytes": None, "trash_count": len(in_trash), "trash_days": TRASH_DAYS,
        "near": False, "over": False,
    }
    if sizes is None:
        return out
    trash_keys: set[str] = set()
    for row in in_trash:
        trash_keys.update(_keys_of(row["media_url"], account_id, sizes))
    trash = sum(sizes[k] for k in trash_keys)
    used = sum(sizes.values()) - trash
    out.update(used_bytes=used, trash_bytes=trash)
    if limit:
        out["near"] = used >= limit * NEAR
        out["over"] = used >= limit
    return out


def gb_text(n: Optional[int]) -> str:
    if n is None:
        return "?"
    value = n / GB
    return f"{value:.1f}" if value < 100 else f"{value:.0f}"


def check_upload(account_id: Optional[int], incoming: int,
                 dsn: Optional[str] = None) -> None:
    """Raise StorageFull when `incoming` more bytes would take the workspace
    past its limit. Passes when there is no limit or usage cannot be
    measured."""
    state = usage(account_id, dsn)
    limit = state["limit_bytes"]
    if not limit or not state["measured"]:
        return
    if state["used_bytes"] + max(0, int(incoming)) <= limit:
        return
    raise StorageFull(
        f"Out of storage: {gb_text(state['used_bytes'])} of {gb_text(limit)} GB used. "
        f"Delete renders in the Library (the trash empties after {TRASH_DAYS} days) "
        "or move to a plan with more storage.", state)


def public(state: dict[str, Any]) -> dict[str, Any]:
    """The route's answer: bytes plus the GB strings the bar prints."""
    return {**state, "used_gb": gb_text(state["used_bytes"]),
            "limit_gb": None if state["limit_bytes"] is None else gb_text(state["limit_bytes"])}


__all__ = ["TRASH_DAYS", "StorageFull", "limit_bytes", "trashed", "purge_due",
           "usage", "check_upload", "public", "gb_text"]

