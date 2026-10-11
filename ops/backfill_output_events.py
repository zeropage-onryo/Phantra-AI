"""Outcome events for what had already happened before they were recorded
(2026-10-11, step 4 of docs/tasks/task-higgsfield-shape.md).

`src/outcomes.py` records what a person does with an output from the day
it shipped. The rows already hold some of the same facts about earlier
work, and this reads them back into `output_events`:

    cut_add        every output on a cut's timeline, once per cut, dated at
                   the version it first appeared in
    export         every output in a version that was exported
    star           an output starred on the wall (`starred_at`)
    delete         an output taken off the wall (`deleted_at`)
    element_from   an output that became an element's photo -- only where
                   this machine holds both files, because the photo is named
                   by a hash of its bytes, not by the render it came from

Not recoverable, and not invented: downloads, references, continue
actions, regenerations and posts left no trace in the rows.

IT COUNTS, IT DOES NOT TEACH. A kept event recorded as it happens files the
prompt on the winning shelf and embeds it (src/outcomes.py). A backfilled
one does not: this script makes no model call and puts nothing on a shelf.
It does set `generations.kept` for a kept output, which is the point.

Report first. `--write` records. Re-runnable: an event this script already
wrote (same output, same kind, same detail) is not written twice. It never
guesses the database: `--dsn`, or an exported DATABASE_URL.

    set -a && source .env && set +a
    venv/bin/python -m ops.backfill_output_events            # report
    venv/bin/python -m ops.backfill_output_events --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import db, outcomes  # noqa: E402
from src.cut import doc as cut_doc  # noqa: E402

SOURCE = "backfill"
ELEMENT_DIRS = ("characters", "props", "locations")


def _gens(doc: Any) -> list[int]:
    """The outputs a timeline doc names, in first-use order."""
    try:
        handles = cut_doc.handles(doc if isinstance(doc, dict) else json.loads(doc))
    except Exception:                                           # noqa: BLE001
        return []
    out = []
    for h in handles:
        parsed = cut_doc.parse_handle(h)
        if parsed and parsed[0] == "gen":
            out.append(parsed[1])
    return out


def _element_matches(assets: list[dict], root: Path) -> list[tuple[int, str]]:
    """[(asset id, the element photo's path)] for photos this machine holds
    that are byte-for-byte a render it also holds."""
    photos: dict[str, str] = {}
    for kind in ELEMENT_DIRS:
        folder = root / kind
        if not folder.is_dir():
            continue
        for f in folder.glob("*/gen-*"):
            if f.is_file():
                # the name IS sha1(bytes)[:16] (app.api._photos_from_urls)
                photos[f.stem[len("gen-"):]] = str(f.relative_to(root))
    if not photos:
        return []
    out = []
    for a in assets:
        if a.get("media_kind") != "image" or not a.get("output_path"):
            continue
        path = Path(a["output_path"])
        path = path if path.is_absolute() else root / path
        try:
            digest = hashlib.sha1(path.read_bytes()).hexdigest()[:16]
        except OSError:
            continue
        if digest in photos:
            out.append((int(a["id"]), photos[digest]))
    return out


def plan(dsn: str, root: Optional[Path] = None) -> list[dict]:
    """Every event the rows can still prove, oldest first. Reads only."""
    found: list[dict] = []
    with db.connect(dsn) as conn:
        if not db.table_exists(conn, "generated_assets"):
            return []
        assets = [dict(r) for r in conn.execute(
            "SELECT id, account_id, media_kind, output_path, starred_at, deleted_at "
            "FROM generated_assets ORDER BY id")]
        owner = {int(a["id"]): a["account_id"] for a in assets}
        for a in assets:
            if a.get("starred_at"):
                found.append({"event": "star", "asset_id": int(a["id"]), "at": a["starred_at"],
                              "account_id": a["account_id"], "meta": {}})
            if a.get("deleted_at"):
                found.append({"event": "delete", "asset_id": int(a["id"]), "at": a["deleted_at"],
                              "account_id": a["account_id"], "meta": {}})
        if db.table_exists(conn, "timelines"):
            seen: set[tuple] = set()
            for t in conn.execute(
                    "SELECT id, account_id, project_id, version, created_at, doc, export_url "
                    "FROM timelines ORDER BY id"):
                for asset in _gens(t["doc"]):
                    # only an output the cut's own account owns
                    if owner.get(asset, object()) != t["account_id"]:
                        continue
                    if (t["project_id"], asset) not in seen:
                        seen.add((t["project_id"], asset))
                        found.append({"event": "cut_add", "asset_id": asset,
                                      "at": t["created_at"], "account_id": t["account_id"],
                                      "meta": {"cut": t["project_id"]}})
                    if t["export_url"]:
                        found.append({"event": "export", "asset_id": asset,
                                      "at": t["created_at"], "account_id": t["account_id"],
                                      "meta": {"cut": t["project_id"], "version": t["version"]}})
    for asset, photo in _element_matches(assets, root or ROOT):
        found.append({"event": "element_from", "asset_id": asset, "at": None,
                      "account_id": owner.get(asset), "meta": {"photo": photo}})
    return found


def _already(dsn: str) -> set[tuple]:
    with db.connect(dsn) as conn:
        if not db.table_exists(conn, "output_events"):
            return set()
        return {(int(r["asset_id"]), r["event"], r["meta"] or "")
                for r in conn.execute(
                    "SELECT account_id, asset_id, event, meta FROM output_events "
                    "WHERE source = %s", (SOURCE,))}


def _key(row: dict) -> tuple:
    return (row["asset_id"], row["event"],
            json.dumps(row["meta"], sort_keys=True) if row["meta"] else "")


def pending(dsn: str, root: Optional[Path] = None) -> list[dict]:
    """`plan` minus what an earlier run already wrote."""
    done = _already(dsn)
    return [row for row in plan(dsn, root) if _key(row) not in done]


def apply(rows: list[dict], dsn: str) -> int:
    """Record them. Returns how many were written."""
    outcomes.init(dsn)
    n = 0
    for row in rows:
        # teach=False: history is counted, never taught -- no model call,
        # nothing filed on the shared winning shelf
        if outcomes.record(row["event"], asset_id=row["asset_id"], account_id=row["account_id"],
                           source=SOURCE, meta=row["meta"] or None, at=row["at"],
                           teach=False, dsn=dsn):
            n += 1
    return n


def _where(dsn: str) -> str:
    """Host and database, never a credential."""
    try:
        from psycopg.conninfo import conninfo_to_dict
        d = conninfo_to_dict(dsn)
        return f"{d.get('host', 'localhost')}:{d.get('port', '5432')}/{d.get('dbname', '')}"
    except Exception:                                           # noqa: BLE001
        return "(unreadable connection string)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Record outcome events for what already happened (report by default).")
    ap.add_argument("--dsn", help="database URL (default: the exported DATABASE_URL)")
    ap.add_argument("--write", action="store_true",
                    help="record the events; without it this only reports")
    args = ap.parse_args(argv)
    dsn = args.dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        print("refusing: no --dsn and no DATABASE_URL exported -- this script never guesses "
              "which database to write", file=sys.stderr)
        return 2
    print(f"database: {_where(dsn)}")
    rows = pending(dsn)
    by_kind = Counter(r["event"] for r in rows)
    by_account = Counter(r["account_id"] for r in rows)
    if not rows:
        print("  nothing to record: every event the rows can prove is already there")
        return 0
    for kind in ("cut_add", "export", "star", "delete", "element_from"):
        print(f"  {kind:<13} {by_kind.get(kind, 0)}")
    print("  by account: " + ", ".join(f"{a}: {n}" for a, n in sorted(
        by_account.items(), key=lambda kv: str(kv[0]))))
    if not args.write:
        print("\n  report only -- nothing was written. Re-run with --write to record them.")
        return 0
    print(f"\n  recorded {apply(rows, dsn)} of {len(rows)} event(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
