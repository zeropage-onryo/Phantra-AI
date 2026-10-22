"""The brand-era data clear (2026-10-13, Mike's call: "we're starting with
fresh data"; docs/tasks/task-remove-brand-labels.md, step 5).

It REPORTS by default. `--backup DIR` also writes every row it would delete
(and every scene of the account, kept ones included) as JSON and reads the
files back. `--write` deletes, and is not to be run without Mike's yes on
the report it printed.

WHAT IT DELETES

  - the account's scenes (`shoot_concepts`) that were never rendered and
    that nothing else points at, with their saved canvases (`workflows`
    rows naming them; `concept_locations` cascades);
  - (it also cleared the account's `hold_queue` rows when it ran on
    2026-10-14; that table went whole the same day, so it is not named here)
  - `prompt_scores`: that graph's gate log (shared, keyed by run);
  - `scout_findings` and `scout_bin`: the spark bank and its image list
    (shared, every row labelled with a brand). Only the ROWS go: no file
    in the bucket or on disk is touched, so a scene that still carries a
    bin image as a reference still draws it.

WHAT IT KEEPS -- a scene survives when any of these is true: its id is in
--keep; a shot or a timed part of one carries a `media_url`; a
`generated_assets` row, a `videos` row, a live `cut_projects` row, a
`timelines` key `concept:<id>` or a `fal_requests` receipt names it. With
--keep-picked a picked or marked-shot scene survives too (the 2026-10-07
wipe's rule; off by default, because "picked" is a label from the board
that no longer exists).

It never touches another account's scenes, a render, a video or its
metrics, an element, a project, a cut, a RAG row, or any ledger, billing or
credit table.

The delete is ONE transaction; each table's deleted count is compared with
the report and any difference rolls everything back. Re-runnable.

DATABASE_URL must be exported (or --dsn given); it never falls back to a
database on its own, and it prints the host it read.

    set -a && source .env && set +a
    venv/bin/python -m ops.brand_removal_clear --account zeropage
    venv/bin/python -m ops.brand_removal_clear --account zeropage --backup data/backups/brand-removal-2026-10-13
    venv/bin/python -m ops.brand_removal_clear --account zeropage --backup <dir> --write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from ops.wipe_concepts import KNOWN_CONCEPT_COLUMNS, _rendered, _shots, _where, concept_columns
from src import accounts, db

# Shared tables cleared whole. A table missing from the schema is skipped.
SHARED = ("prompt_scores", "scout_findings", "scout_bin")
# Never read for deletion, whatever else changes here.
NEVER = ("credit_entries", "credit_lots", "credit_schedules", "generated_assets",
         "generations", "videos", "metrics", "accounts", "users", "account_members")


def _tables(conn) -> set[str]:
    return {r["table_name"] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema()").fetchall()}


def _linked(conn, tables: set[str], account_id: int) -> dict[str, set[int]]:
    def ids(sql: str) -> set[int]:
        return {int(r["concept_id"]) for r in conn.execute(sql, (account_id,)).fetchall()
                if r["concept_id"] is not None}

    out: dict[str, set[int]] = {}
    if "generated_assets" in tables:
        out["a Library item"] = ids("SELECT DISTINCT concept_id FROM generated_assets "
                                    "WHERE account_id IS NOT DISTINCT FROM %s")
    if "videos" in tables:
        out["a posted video"] = ids("SELECT DISTINCT concept_id FROM videos "
                                    "WHERE account_id IS NOT DISTINCT FROM %s")
    if "cut_projects" in tables:
        out["an edit"] = ids("SELECT DISTINCT concept_id FROM cut_projects "
                             "WHERE account_id IS NOT DISTINCT FROM %s AND deleted_at IS NULL")
    if "timelines" in tables:
        keys = conn.execute(
            "SELECT DISTINCT project_id FROM timelines WHERE account_id IS NOT DISTINCT FROM %s "
            "AND project_id LIKE 'concept:%%'", (account_id,)).fetchall()
        out.setdefault("an edit", set()).update(
            int(k["project_id"].split(":", 1)[1]) for k in keys
            if k["project_id"].split(":", 1)[1].isdigit())
    if "fal_requests" in tables:
        billed: set[int] = set()
        for r in conn.execute(
                "SELECT context_json FROM fal_requests WHERE account_id IS NOT DISTINCT FROM %s "
                "AND context_json LIKE '%%concept_id%%'", (account_id,)).fetchall():
            try:
                cid = json.loads(r["context_json"] or "{}").get("concept_id")
            except ValueError:
                cid = None
            if isinstance(cid, int):
                billed.add(cid)
        out["a billed render attempt"] = billed
    return out


def scan(dsn: str, *, account_id: int, keep_ids=(), keep_picked: bool = False) -> dict[str, Any]:
    """What the clear would do, read-only."""
    with db.connect(dsn) as conn:
        tables = _tables(conn)
        rows = conn.execute(
            "SELECT id, title, picked_at, shot_done, shots_json FROM shoot_concepts "
            "WHERE account_id IS NOT DISTINCT FROM %s ORDER BY id", (account_id,)).fetchall()
        linked = _linked(conn, tables, account_id)
        keep: dict[int, list[str]] = {}
        delete: list[int] = []
        titles: dict[int, str] = {}
        for row in rows:
            cid = int(row["id"])
            titles[cid] = row["title"] or ""
            why = []
            if cid in set(keep_ids):
                why.append("kept by id")
            if _rendered(_shots(row)):
                why.append("rendered")
            if keep_picked and row["picked_at"]:
                why.append("picked")
            if keep_picked and row["shot_done"]:
                why.append("marked shot")
            why += [f"points from {label}" for label, ids in linked.items() if cid in ids]
            if why:
                keep[cid] = why
            else:
                delete.append(cid)
        counts = {"shoot_concepts": len(delete)}
        if "workflows" in tables:
            counts["workflows"] = conn.execute(
                "SELECT count(*) AS n FROM workflows WHERE account_id IS NOT DISTINCT FROM %s "
                "AND concept_id = ANY(%s)", (account_id, delete)).fetchone()["n"]
        for table in SHARED:
            if table in tables:
                counts[table] = conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
        others = conn.execute(
            "SELECT account_id, count(*) AS n FROM shoot_concepts "
            "WHERE account_id IS DISTINCT FROM %s GROUP BY 1 ORDER BY 1", (account_id,)).fetchall()
        return {"keep": keep, "delete": delete, "titles": titles, "counts": counts,
                "other_accounts": {r["account_id"]: r["n"] for r in others},
                "unknown_columns": sorted(concept_columns(conn) - KNOWN_CONCEPT_COLUMNS)}


def _selects(account_id: int, delete: list[int], tables: set[str]) -> dict[str, tuple[str, tuple]]:
    """table -> (WHERE clause, args) for exactly the rows the clear removes."""
    out = {"shoot_concepts": ("account_id IS NOT DISTINCT FROM %s AND id = ANY(%s)",
                              (account_id, delete))}
    if "workflows" in tables:
        out["workflows"] = ("account_id IS NOT DISTINCT FROM %s AND concept_id = ANY(%s)",
                            (account_id, delete))
    for table in SHARED:
        if table in tables:
            out[table] = ("TRUE", ())
    assert not set(out) & set(NEVER)
    return out


def backup(dsn: str, *, account_id: int, plan: dict[str, Any], out: Path) -> dict[str, int]:
    """One JSON file per table under `out`, then each is read back and its
    row count compared. Returns {file stem: rows}."""
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    with db.connect(dsn) as conn:
        selects = _selects(account_id, plan["delete"], _tables(conn))
        dumps = {name: conn.execute(f"SELECT * FROM {name} WHERE {where}", args).fetchall()
                 for name, (where, args) in selects.items()}
        # every scene of the account, kept ones too: the whole picture
        dumps["shoot_concepts_all_of_account"] = conn.execute(
            "SELECT * FROM shoot_concepts WHERE account_id IS NOT DISTINCT FROM %s ORDER BY id",
            (account_id,)).fetchall()
    for name, rows in dumps.items():
        path = out / f"{name}.json"
        path.write_text(json.dumps([dict(r) for r in rows], default=str, indent=1))
        back = json.loads(path.read_text())
        if len(back) != len(rows):
            raise RuntimeError(f"{path} read back {len(back)} rows, wrote {len(rows)}")
        written[name] = len(back)
    (out / "plan.json").write_text(json.dumps(
        {"account_id": account_id, "delete": plan["delete"],
         "keep": {str(k): v for k, v in plan["keep"].items()}, "counts": plan["counts"]}, indent=1))
    for name, n in plan["counts"].items():
        if written.get(name) != n:
            raise RuntimeError(f"backup of {name} holds {written.get(name)} rows, the report says {n}")
    return written


def clear(dsn: str, *, account_id: int, plan: dict[str, Any]) -> dict[str, int]:
    """Delete what the plan lists, in one transaction. A count that differs
    from the plan raises, which rolls everything back."""
    if plan["unknown_columns"]:
        raise RuntimeError("columns this script does not know how to treat: "
                           + ", ".join(plan["unknown_columns"]))
    done: dict[str, int] = {}
    with db.connect(dsn) as conn:
        selects = _selects(account_id, plan["delete"], _tables(conn))
        # canvases first, then the scenes they name
        for name in sorted(selects, key=lambda n: n == "shoot_concepts"):
            where, args = selects[name]
            done[name] = conn.execute(f"DELETE FROM {name} WHERE {where}", args).rowcount
        if done != plan["counts"]:
            raise RuntimeError(f"deleted {done}, the report said {plan['counts']}: rolled back")
    return done


def _print(plan: dict[str, Any]) -> None:
    print(f"\n  keep {len(plan['keep'])} scene(s):")
    for cid, why in plan["keep"].items():
        print(f"    #{cid:<5} {plan['titles'][cid][:44]:<44} {', '.join(why)}")
    print(f"\n  delete {len(plan['delete'])} scene(s):")
    for cid in plan["delete"]:
        print(f"    #{cid:<5} {plan['titles'][cid][:60]}")
    print("\n  rows deleted, by table:")
    for name, n in plan["counts"].items():
        print(f"    {name:<18} {n}")
    print(f"\n  other accounts' scenes, untouched: {plan['other_accounts'] or 'none'}")
    if plan["unknown_columns"]:
        print("\n  UNKNOWN concept columns (a write is refused): " + ", ".join(plan["unknown_columns"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--account", required=True, help="the account's slug")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--keep", type=int, nargs="*", default=[], help="scene ids kept whatever else")
    ap.add_argument("--keep-picked", action="store_true",
                    help="also keep picked and marked-shot scenes")
    ap.add_argument("--backup", type=Path, help="write the JSON backup into this directory")
    ap.add_argument("--write", action="store_true", help="delete (needs --backup)")
    args = ap.parse_args(argv)
    if not args.dsn:
        print("DATABASE_URL is not exported and no --dsn was given; nothing read.", file=sys.stderr)
        return 2
    if args.write and not args.backup:
        print("--write needs --backup: nothing is deleted without one.", file=sys.stderr)
        return 2
    try:
        account_id = accounts.resolve_account(args.account, dsn=args.dsn)
    except ValueError:
        account_id = None
    if account_id is None:
        print(f"no account '{args.account}' in {_where(args.dsn)}", file=sys.stderr)
        return 2
    plan = scan(args.dsn, account_id=account_id, keep_ids=args.keep,
                keep_picked=args.keep_picked)
    print(f"database: {_where(args.dsn)}\naccount:  {args.account} (id {account_id})")
    _print(plan)
    if args.backup:
        written = backup(args.dsn, account_id=account_id, plan=plan, out=args.backup)
        print(f"\n  backup in {args.backup}, read back: {written}")
    if not args.write:
        print("\n  report only -- nothing was changed.")
        return 0
    done = clear(args.dsn, account_id=account_id, plan=plan)
    print(f"\n  deleted: {done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
