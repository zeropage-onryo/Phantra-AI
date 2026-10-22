"""Trending this week, for the Create page (2026-10-22, group 4 of
docs/tasks/task-overnight-2026-10-22.md; docs/tasks/task-create-page-v2.md).

What ONE account used most over the last seven days: the effects it ran
(`generations.params_json` carries the effect's id, `src/effects.py run`),
the briefs it wrote scenes from (`shoot_concepts.spark`), and what it did
with its outputs (`output_events`, src/outcomes.py). Read-only, never
raises: a count that cannot be read is an empty answer and the page draws
nothing for it.

SCOPE IS THE CALLER'S OWN ACCOUNT, by the tenancy rules: every query on an
owned table names its `account_id` (tests/test_tenancy.py's SQL audit) and
`outcomes` reads "per account, by week, never averaged across accounts".
A studio-wide "most used" would need a shared read nothing here is
allowed to make, so the answer says `scope: "account"` and the page's
heading reads "Trending in your studio".

NO PRICES: nothing here returns credits. The Create page's cards never
show a price (Mike's call, 2026-10-22); the priced card before a spend
still does.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import db

DAYS = 7
# how many of each the page is handed
EFFECTS_MAX = 8
BRIEFS_MAX = 6
# how many recent rows are read per table before counting (per account,
# so a busy week is still one short read)
ROWS_MAX = 400

_WS = re.compile(r"\s+")


def _note(what: str, exc: Exception) -> None:
    print(f"note: trending {what} skipped ({type(exc).__name__}: {exc})", file=sys.stderr)


def cutoff(days: int = DAYS, now: Optional[datetime] = None) -> str:
    """The ISO stamp rows must be newer than: the tables stamp `created_at`
    with db._now() (UTC, seconds), so the comparison is lexical."""
    at = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    return at.isoformat(timespec="seconds")


def brief_key(text: Optional[str]) -> str:
    """Two briefs count as one when they read the same after whitespace
    and case are folded: the page shows the first spelling."""
    return _WS.sub(" ", (text or "").strip()).lower()[:200]


def _effects(conn, account_id: Optional[int], since: str) -> list[dict]:
    """{effect, label, runs, kept} by how often it ran, from the attempt
    log: `params_json` of an effect's generation names the effect
    (effects.run writes "effect": <id>). Kept = a kept event on the
    output it made (outcomes.KEPT)."""
    from . import effects as fx
    from . import outcomes

    if not db.table_exists(conn, "generations"):
        return []
    rows = conn.execute(
        "SELECT id, params_json FROM generations "
        "WHERE account_id IS NOT DISTINCT FROM %s AND created_at >= %s "
        "ORDER BY id DESC LIMIT %s",
        (account_id, since, ROWS_MAX)).fetchall()
    by_gen: dict[int, str] = {}
    for r in rows:
        try:
            params = json.loads(r["params_json"] or "{}") or {}
        except (TypeError, ValueError):
            continue
        name = params.get("effect")
        if isinstance(name, str) and name:
            by_gen[int(r["id"])] = name
    if not by_gen:
        return []
    kept_gens: set[int] = set()
    if db.table_exists(conn, "generated_assets") and db.table_exists(conn, "output_events"):
        for r in conn.execute(
                "SELECT a.generation_id FROM output_events e "
                "JOIN generated_assets a ON a.id = e.asset_id "
                "WHERE e.account_id IS NOT DISTINCT FROM %s "
                "AND a.account_id IS NOT DISTINCT FROM %s "
                "AND a.generation_id = ANY(%s) AND e.event = ANY(%s)",
                (account_id, account_id, list(by_gen), list(outcomes.KEPT))):
            kept_gens.add(int(r["generation_id"]))
    labels = {row["id"]: row["label"] for row in fx.catalogue()}
    cells: dict[str, dict[str, Any]] = {}
    for gen_id, name in by_gen.items():
        cell = cells.setdefault(name, {"effect": name, "label": labels.get(name, name),
                                       "runs": 0, "kept": 0})
        cell["runs"] += 1
        cell["kept"] += 1 if gen_id in kept_gens else 0
    out = sorted(cells.values(), key=lambda c: (-c["runs"], -c["kept"], c["label"]))
    return out[:EFFECTS_MAX]


def _briefs(conn, account_id: Optional[int], since: str) -> list[dict]:
    """{text, count, concept_id} by how many scenes were written from the
    same brief this week; `spark` is the direction the scene was written
    from, `title` stands in when a scene has none."""
    if not db.table_exists(conn, "shoot_concepts"):
        return []
    rows = conn.execute(
        "SELECT id, spark, title FROM shoot_concepts "
        "WHERE account_id IS NOT DISTINCT FROM %s AND created_at >= %s "
        "ORDER BY id DESC LIMIT %s",
        (account_id, since, ROWS_MAX)).fetchall()
    cells: dict[str, dict[str, Any]] = {}
    # oldest first, so the spelling shown is the first one written
    for r in reversed(rows):
        text = (r["spark"] or r["title"] or "").strip()
        key = brief_key(text)
        if not key:
            continue
        cell = cells.setdefault(key, {"text": text[:200], "count": 0, "concept_id": int(r["id"])})
        cell["count"] += 1
        cell["concept_id"] = max(cell["concept_id"], int(r["id"]))
    out = sorted(cells.values(), key=lambda c: (-c["count"], -c["concept_id"]))
    return out[:BRIEFS_MAX]


def _events(conn, account_id: Optional[int], since: str) -> dict[str, int]:
    """How the week's outputs were treated: kept / discarded / edited
    event counts (outcomes.KEPT, DISCARDED, EDITED)."""
    from . import outcomes

    counts = {"kept": 0, "discarded": 0, "edited": 0}
    if not db.table_exists(conn, "output_events"):
        return counts
    for r in conn.execute(
            "SELECT event, COUNT(*) AS n FROM output_events "
            "WHERE account_id IS NOT DISTINCT FROM %s AND at >= %s GROUP BY event",
            (account_id, since)):
        event, n = r["event"], int(r["n"])
        if event in outcomes.KEPT:
            counts["kept"] += n
        elif event in outcomes.DISCARDED:
            counts["discarded"] += n
        elif event in outcomes.EDITED:
            counts["edited"] += n
    return counts


def trending(*, account_id: Optional[int], days: int = DAYS,
             dsn: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    """What this account used most over the last `days`. Never raises."""
    since = cutoff(days, now)
    out: dict[str, Any] = {"days": days, "since": since, "scope": "account",
                           "effects": [], "briefs": [],
                           "events": {"kept": 0, "discarded": 0, "edited": 0}}
    try:
        with db.connect(dsn) as conn:
            out["effects"] = _effects(conn, account_id, since)
            out["briefs"] = _briefs(conn, account_id, since)
            out["events"] = _events(conn, account_id, since)
    except Exception as exc:                                    # noqa: BLE001
        _note("read", exc)
    return out
