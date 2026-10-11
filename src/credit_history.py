"""
A customer's credit history (2026-10-11, docs/tasks/task-settings-page.md):
the ledger's entries read back as lines a person recognises, for Settings →
Usage. GET /api/billing/history (app/billing.py) is its one caller.

READ ONLY, AND IN CREDITS ONLY. Nothing here writes, and nothing here
returns a dollar: `generations.cost_usd` is never selected, so a provider's
price cannot reach the page by accident (tests/test_credit_history.py
holds that). The ledger stays the record; this is a way of reading it.

ONE ROW PER MOVEMENT, NOT PER ENTRY. `ledger.hold` writes one entry per
lot it draws from, and a settle that gives some back writes one per lot
too -- an accounting detail (which lot paid) a customer should not have to
add up. Entries that share a kind and a ref are one movement, summed; its
id is its last entry's, which is also what the history pages on.

`balance_after` is the running sum of every entry up to and including the
movement's last one, taken over the RAW entries (so it is exact however
the entries were split) -- what the ledger said the balance was at that
moment. A hold lowers it: held credit is not spendable.

WHAT A LINE SAYS comes from the render the credit was held for -- the
`generations` row an adapter writes with `ledger.ref_params(ref)` in its
params, found by the settle's `generation_id` or by that ref -- and, for a
grant or an expiry, from the lot. A hold whose render never wrote a row
(still in flight, or it died before the row) says what can be told from
the hold itself: a still or a clip.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import db, ledger

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
SUMMARY_DAYS = 30

# what a lot is, in a customer's words (web/src/lib/credits.ts names the
# same kinds on the Plan section)
LOT_LINES = {
    "subscription": "Monthly credits",
    "purchase": "Top-up",
    "promo": "Trial credits",
    "refund": "Refund",
    "adjustment": "Adjustment",
}

VIDEO_SUFFIXES = (".mp4", ".webm", ".mov")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


# --------------------------------------------------------------------------
# the ledger, grouped
# --------------------------------------------------------------------------

def movements(account_id: Optional[int], *, before: Optional[int] = None,
              limit: int = DEFAULT_LIMIT, dsn: Optional[str] = None) -> list[dict[str, Any]]:
    """This account's movements, newest first, at most `limit` of them
    with an id under `before`."""
    with db.connect(dsn) as conn:
        rows = conn.execute(
            "WITH raw AS ("
            "  SELECT id, created_at, kind, ref, delta, generation_id, provider, lot_id, "
            "         SUM(delta) OVER (ORDER BY id) AS running "
            "  FROM credit_entries WHERE account_id IS NOT DISTINCT FROM %s"
            "), moves AS ("
            "  SELECT MAX(id) AS id, MIN(created_at) AS at, kind, MAX(ref) AS ref, "
            "         SUM(delta) AS credits, MAX(generation_id) AS generation_id, "
            "         MAX(provider) AS provider, MIN(lot_id) AS lot_id, "
            "         (ARRAY_AGG(running ORDER BY id DESC))[1] AS balance_after "
            "  FROM raw GROUP BY kind, COALESCE(ref, 'entry:' || id::text)"
            ") SELECT * FROM moves WHERE (%s::bigint IS NULL OR id < %s) "
            "ORDER BY id DESC LIMIT %s",
            (account_id, before, before, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]


def _spend(account_id: Optional[int], since: str, dsn: Optional[str]) -> list[dict[str, Any]]:
    """What each render NET cost, for renders whose hold was taken at or
    after `since`: a hold plus its settle or release, as one positive
    number (0 for a hold that was released whole)."""
    with db.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT ref, MIN(created_at) FILTER (WHERE kind = 'hold') AS at, "
            "       -SUM(delta) AS credits, MAX(generation_id) AS generation_id, "
            "       MAX(provider) AS provider "
            "FROM credit_entries "
            "WHERE account_id IS NOT DISTINCT FROM %s AND ref IS NOT NULL "
            "AND kind IN ('hold', 'settle', 'release') "
            "GROUP BY ref "
            "HAVING MIN(created_at) FILTER (WHERE kind = 'hold') IS NOT NULL "
            "AND (MIN(created_at) FILTER (WHERE kind = 'hold'))::timestamptz >= %s::timestamptz",
            (account_id, since),
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# what a movement was for
# --------------------------------------------------------------------------

def _params(text: Optional[str]) -> dict:
    try:
        value = json.loads(text) if text else {}
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _context(account_id: Optional[int], moves: list[dict], dsn: Optional[str]) -> dict:
    """Everything the lines for `moves` need, in four scoped reads: the
    generations (by id, and by the ledger ref in their params), their rows
    on the Assets wall, the scenes those belong to, and the lots."""
    gen_ids = sorted({int(m["generation_id"]) for m in moves if m.get("generation_id")})
    refs = sorted({str(m["ref"]) for m in moves
                   if m.get("ref") and m["kind"] in ("hold", "settle", "release")})
    lot_ids = sorted({int(m["lot_id"]) for m in moves if m.get("lot_id") is not None})
    by_gen: dict[int, dict] = {}
    by_ref: dict[str, dict] = {}
    assets: dict[int, dict] = {}
    scenes: dict[int, str] = {}
    lots: dict[int, dict] = {}
    with db.connect(dsn) as conn:
        if (gen_ids or refs) and db.table_exists(conn, "generations"):
            # matched as text, the way ledger._generation_for matches it:
            # params_json is TEXT written at several call sites, and the
            # exact ref is checked again below once the row is parsed
            patterns = [f'%"{ledger.GENERATION_REF_KEY}": "{ref}"%' for ref in refs]
            rows = conn.execute(
                "SELECT id, tool, params_json FROM generations "
                "WHERE account_id IS NOT DISTINCT FROM %s "
                "AND (id = ANY(%s) OR params_json LIKE ANY(%s)) ORDER BY id ASC",
                (account_id, gen_ids, patterns),
            ).fetchall()
            for row in rows:
                gen = {"id": int(row["id"]), "tool": row["tool"], "params": _params(row["params_json"])}
                by_gen[gen["id"]] = gen
                ref = gen["params"].get(ledger.GENERATION_REF_KEY)
                if ref:
                    by_ref[str(ref)] = gen          # the newest row for a ref wins
        if by_gen and db.table_exists(conn, "generated_assets"):
            rows = conn.execute(
                "SELECT id, generation_id, media_kind, concept_id, deleted_at "
                "FROM generated_assets WHERE account_id IS NOT DISTINCT FROM %s "
                "AND generation_id = ANY(%s)",
                (account_id, sorted(by_gen)),
            ).fetchall()
            assets = {int(r["generation_id"]): dict(r) for r in rows}
        concept_ids = sorted({int(c) for c in (
            [a.get("concept_id") for a in assets.values()]
            + [g["params"].get("concept_id") for g in by_gen.values()]) if _is_int(c)})
        if concept_ids and db.table_exists(conn, "shoot_concepts"):
            rows = conn.execute(
                "SELECT id, title FROM shoot_concepts "
                "WHERE account_id IS NOT DISTINCT FROM %s AND id = ANY(%s)",
                (account_id, concept_ids),
            ).fetchall()
            scenes = {int(r["id"]): (r["title"] or "").strip() for r in rows}
        if lot_ids:
            rows = conn.execute(
                "SELECT id, kind, note FROM credit_lots "
                "WHERE account_id IS NOT DISTINCT FROM %s AND id = ANY(%s)",
                (account_id, lot_ids),
            ).fetchall()
            lots = {int(r["id"]): dict(r) for r in rows}
    return {"by_gen": by_gen, "by_ref": by_ref, "assets": assets, "scenes": scenes, "lots": lots}


def _utc(stamp: str) -> datetime:
    at = datetime.fromisoformat(stamp)
    return (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _is_int(value) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _model_names() -> tuple[dict, dict, dict]:
    """(video model id -> public name, image model id -> label, effect id
    -> label). Lazy and forgiving: a line with a plainer name beats a
    history that cannot be read because a table moved."""
    video, image, effect = {}, {}, {}
    try:
        from . import pricing
        video = {model: name for _, model, name, _ in pricing.CATALOG_MODELS}
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from . import fal
        image = {key: spec.get("label") or key for key, spec in fal.IMAGE_MODELS.items()}
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from . import effects
        effect = {key: row.get("label") or key for key, row in effects.EFFECTS.items()}
    except Exception:                                   # noqa: BLE001
        pass
    return video, image, effect


def _render_line(gen: Optional[dict], move: dict, names) -> tuple[str, str, str]:
    """(what, group, label) for a hold, settle or release. `group` is
    render | still | effect; `label` is the model, for the totals."""
    video, image, effect = names
    if gen is None:
        # no row to read: say what the hold itself shows
        ref = str(move.get("ref") or "").lower()
        if move.get("provider") == "nano" or ref.endswith(IMAGE_SUFFIXES):
            return "Still", "still", "Other stills"
        if ref.endswith(VIDEO_SUFFIXES):
            return "Clip", "render", "Other clips"
        return "Render", "render", "Other renders"
    tool, params = gen["tool"], gen["params"]
    model = str(params.get("model") or "")
    if params.get("effect"):
        name = effect.get(str(params["effect"])) or "Effect"
        return f"Effect · {name}", "effect", name
    if tool == "nano":
        name = "Nano Banana Pro" if "pro" in model.lower() else "Nano Banana"
        kind = "Element sheet" if params.get("source") == "element_sheet" else "Still"
        return f"{kind} · {name}", "still", name
    if tool == "fal":
        name = image.get(model) or "Image model"
        return f"Still · {name}", "still", name
    name = video.get(model) or tool.replace("_", " ").title()
    what = f"{name} clip"
    if _is_int(params.get("duration")):
        what += f", {int(params['duration'])}s"
    if _is_int(params.get("part")):
        what += f", shot {int(params['part'])}"
    return what, "render", name


def _lot_line(lot: Optional[dict]) -> tuple[str, str]:
    """(what, label) for a grant or an expiry."""
    kind = (lot or {}).get("kind") or ""
    label = LOT_LINES.get(kind, "Credits")
    if kind != "subscription":
        return label, label
    # the webhook notes which plan paid: "stripe invoice in_... (creator)"
    note = str((lot or {}).get("note") or "")
    key = note.rsplit("(", 1)[-1].rstrip(")").strip() if note.endswith(")") else ""
    try:
        from . import pricing
        plan = pricing.PLANS.get(key)
    except Exception:                                   # noqa: BLE001
        plan = None
    return (f"{label} · {plan.name}" if plan else label), label


def _link(gen: Optional[dict], ctx: dict) -> Optional[dict]:
    """Where the line can be opened: its scene when that still exists,
    else its item on the Assets wall, else nowhere."""
    if gen is None:
        return None
    asset = ctx["assets"].get(gen["id"])
    concept = (asset or {}).get("concept_id") or gen["params"].get("concept_id")
    if _is_int(concept) and int(concept) in ctx["scenes"]:
        return {"kind": "scene", "id": int(concept), "title": ctx["scenes"][int(concept)]}
    if asset and not asset.get("deleted_at"):
        return {"kind": "render", "id": int(asset["id"])}
    return None


def _generation_of(move: dict, ctx: dict) -> Optional[dict]:
    gen = ctx["by_gen"].get(int(move["generation_id"])) if move.get("generation_id") else None
    return gen or ctx["by_ref"].get(str(move.get("ref") or ""))


def describe(account_id: Optional[int], moves: list[dict],
             dsn: Optional[str] = None) -> list[dict[str, Any]]:
    """The movements as the route answers them. Every key is listed here,
    so nothing rides along from a row by accident."""
    ctx = _context(account_id, moves, dsn)
    names = _model_names()
    out = []
    for move in moves:
        kind = move["kind"]
        if kind in ("grant", "expire"):
            what, label = _lot_line(ctx["lots"].get(int(move["lot_id"])) if move.get("lot_id") is not None else None)
            if kind == "expire":
                what = f"{what} expired"
            group, link = "grant", None
        else:
            gen = _generation_of(move, ctx)
            what, group, label = _render_line(gen, move, names)
            link = _link(gen, ctx)
        out.append({
            "id": int(move["id"]),
            "at": move["at"],
            "kind": kind,
            "credits": int(move["credits"]),
            "what": what,
            "group": group,
            "label": label,
            "ref": link,
            "balance_after": int(move["balance_after"]),
        })
    return out


# --------------------------------------------------------------------------
# what the route answers
# --------------------------------------------------------------------------

def page(account_id: Optional[int], *, before: Optional[int] = None,
         limit: int = DEFAULT_LIMIT, dsn: Optional[str] = None) -> dict[str, Any]:
    """One page, newest first. `next` is the id to pass as `before` for the
    page after it, or None when this was the last."""
    limit = max(1, min(DEFAULT_LIMIT if limit is None else int(limit), MAX_LIMIT))
    moves = movements(account_id, before=before, limit=limit + 1, dsn=dsn)
    more = len(moves) > limit
    items = describe(account_id, moves[:limit], dsn)
    return {"items": items, "next": items[-1]["id"] if more and items else None}


def summary(account_id: Optional[int], *, days: int = SUMMARY_DAYS,
            now: Optional[datetime] = None, dsn: Optional[str] = None) -> dict[str, Any]:
    """Credits spent per day for the `days` days ending today (UTC), every
    day present, and the same spend by model. A render counts on the day
    its hold was taken, at what it NET cost: one that was released whole
    is no spend at all, and one still in flight counts at what it holds."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    rows = [r for r in _spend(account_id, start.isoformat(), dsn) if int(r["credits"]) > 0]
    ctx = _context(account_id, [{**r, "kind": "hold", "lot_id": None} for r in rows], dsn)
    names = _model_names()
    per_day = {(start + timedelta(days=i)).date().isoformat(): 0 for i in range(days)}
    totals: dict[str, dict] = {}
    for row in rows:
        credits = int(row["credits"])
        day = _utc(row["at"]).date().isoformat()
        if day in per_day:
            per_day[day] += credits
        _, group, label = _render_line(_generation_of(row, ctx), row, names)
        total = totals.setdefault(label, {"label": label, "group": group, "credits": 0, "count": 0})
        total["credits"] += credits
        total["count"] += 1
    return {
        "window_days": days,
        "days": [{"day": day, "credits": credits} for day, credits in per_day.items()],
        "totals": sorted(totals.values(), key=lambda t: (-t["credits"], t["label"])),
        "spent": sum(per_day.values()),
    }
