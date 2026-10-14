"""The brand columns' way out of the live schema (2026-10-13;
docs/tasks/task-remove-brand-labels.md, step 6).

Three moves, in this order, and the code PR goes in the middle:

  1. `--loosen`  DROP NOT NULL on the brand columns that have it, so code
                 that no longer writes them can run. Nothing is lost.
  2. (merge and deploy the code that names none of these columns)
  3. `--drop`    drop the columns, the scout's brand index, the three
                 tables nothing reads any more (`channels`,
                 `inspiration_accounts`, and `hold_queue`, removed whole
                 on 2026-10-14), the uncanny judge's three columns, and set the brand values
                 copied into `generated_assets.project` to NULL.

It REPORTS by default: which of those objects exist and how many rows hold
a value in each. `--backup DIR` writes every value `--drop` would destroy
as JSON and reads it back. `--drop` needs `--backup`. Each move is one
transaction. Re-runnable: a second run finds nothing to do. Neither move is
to be run without Mike's yes on the report.

DATABASE_URL must be exported (or --dsn given); it never falls back to a
database on its own, and it prints the host it read.

    set -a && source .env && set +a
    venv/bin/python -m ops.brand_removal_schema
    venv/bin/python -m ops.brand_removal_schema --loosen
    venv/bin/python -m ops.brand_removal_schema --backup <dir> --drop
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from ops.wipe_concepts import _where
from src import db

# table -> the columns this step removes
COLUMNS = {
    "shoot_concepts": ("brand", "uncanny_overall", "uncanny_passed", "uncanny_reason"),
    "scene_briefs": ("brand",),
    "workflows": ("brand",),
    "videos": ("brand",),
    "scout_findings": ("brand",),
    "scout_bin": ("brand",),
}
INDEXES = ("idx_scout_brand_used",)
# whole tables nothing reads any more: the per-brand channels and the
# inspiration feature (2026-10-13), and the hold queue (2026-10-14)
TABLES = ("channels", "inspiration_accounts", "hold_queue")
# the old brand names that were copied into the Library's project label
PROJECT_LABELS = ("zero" + "page", "anti" + "hero")


def _existing(conn) -> dict[str, set[str]]:
    rows = conn.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema()").fetchall()
    out: dict[str, set[str]] = {}
    for r in rows:
        out.setdefault(r["table_name"], set()).add(r["column_name"])
    return out


def _not_null(conn, table: str, column: str) -> bool:
    row = conn.execute(
        "SELECT is_nullable FROM information_schema.columns WHERE table_schema = "
        "current_schema() AND table_name = %s AND column_name = %s", (table, column)).fetchone()
    return bool(row) and row["is_nullable"] == "NO"


def scan(dsn: str) -> dict[str, Any]:
    """What exists and how much it holds, read-only."""
    with db.connect(dsn) as conn:
        have = _existing(conn)
        columns = []
        for table, cols in COLUMNS.items():
            for col in cols:
                if col not in have.get(table, set()):
                    continue
                held = conn.execute(
                    f"SELECT count(*) AS n FROM {table} WHERE {col} IS NOT NULL").fetchone()["n"]
                columns.append({"table": table, "column": col,
                                "not_null": _not_null(conn, table, col),
                                "rows_with_a_value": held})
        tables = [{"table": t, "rows": conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]}
                  for t in TABLES if t in have]
        idx = {r["indexname"] for r in conn.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()").fetchall()}
        project = 0
        if "project" in have.get("generated_assets", set()):
            project = conn.execute(
                "SELECT count(*) AS n FROM generated_assets WHERE project = ANY(%s)",
                (list(PROJECT_LABELS),)).fetchone()["n"]
    return {"columns": columns, "tables": tables,
            "indexes": [i for i in INDEXES if i in idx],
            "generated_assets_project_labels": project}


def loosen(dsn: str) -> list[str]:
    """DROP NOT NULL wherever a brand column still has it."""
    done = []
    with db.connect(dsn) as conn:
        have = _existing(conn)
        for table, cols in COLUMNS.items():
            for col in cols:
                if col in have.get(table, set()) and _not_null(conn, table, col):
                    conn.execute(f"ALTER TABLE {table} ALTER COLUMN {col} DROP NOT NULL")
                    done.append(f"{table}.{col}")
    return done


def backup(dsn: str, out: Path) -> dict[str, int]:
    """Every value --drop destroys, one JSON file per table, read back."""
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    with db.connect(dsn) as conn:
        have = _existing(conn)
        dumps: dict[str, list] = {}
        for table, cols in COLUMNS.items():
            present = [c for c in cols if c in have.get(table, set())]
            if present:
                key = "id" if "id" in have[table] else "name"
                dumps[f"{table}.columns"] = [dict(r) for r in conn.execute(
                    f"SELECT {key}, {', '.join(present)} FROM {table}").fetchall()]
        for t in TABLES:
            if t in have:
                dumps[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()]
        if "project" in have.get("generated_assets", set()):
            dumps["generated_assets.project"] = [dict(r) for r in conn.execute(
                "SELECT id, project FROM generated_assets WHERE project = ANY(%s)",
                (list(PROJECT_LABELS),)).fetchall()]
    for name, rows in dumps.items():
        path = out / f"{name}.json"
        path.write_text(json.dumps(rows, default=str, indent=1))
        back = json.loads(path.read_text())
        if len(back) != len(rows):
            raise RuntimeError(f"{path} read back {len(back)} rows, wrote {len(rows)}")
        written[name] = len(back)
    return written


def drop(dsn: str) -> list[str]:
    """Move 3, in one transaction."""
    done = []
    with db.connect(dsn) as conn:
        have = _existing(conn)
        if "project" in have.get("generated_assets", set()):
            n = conn.execute("UPDATE generated_assets SET project = NULL WHERE project = ANY(%s)",
                             (list(PROJECT_LABELS),)).rowcount
            done.append(f"generated_assets.project -> NULL on {n} row(s)")
        for name in INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        for table, cols in COLUMNS.items():
            for col in cols:
                if col in have.get(table, set()):
                    conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
                    done.append(f"dropped {table}.{col}")
        for t in TABLES:
            if t in have:
                conn.execute(f"DROP TABLE {t}")
                done.append(f"dropped table {t}")
    return done


def _print(report: dict[str, Any]) -> None:
    print("\n  columns:")
    for c in report["columns"]:
        flag = "NOT NULL" if c["not_null"] else "nullable"
        name = f"{c['table']}.{c['column']}"
        print(f"    {name:<34} {flag:<9} {c['rows_with_a_value']} row(s) hold a value")
    print("\n  tables:  " + (", ".join(f"{t['table']} ({t['rows']} rows)"
                                    for t in report["tables"]) or "none"))
    print("  indexes: " + (", ".join(report["indexes"]) or "none"))
    print(f"  generated_assets.project holding an old brand name: "
          f"{report['generated_assets_project_labels']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--loosen", action="store_true", help="move 1: DROP NOT NULL")
    ap.add_argument("--backup", type=Path, help="write what --drop destroys into this directory")
    ap.add_argument("--drop", action="store_true", help="move 3 (needs --backup)")
    args = ap.parse_args(argv)
    if not args.dsn:
        print("DATABASE_URL is not exported and no --dsn was given; nothing read.", file=sys.stderr)
        return 2
    if args.drop and not args.backup:
        print("--drop needs --backup: nothing is dropped without one.", file=sys.stderr)
        return 2
    if args.loosen and args.drop:
        print("--loosen and --drop are separate moves, with a deploy between them.",
              file=sys.stderr)
        return 2
    print(f"database: {_where(args.dsn)}")
    _print(scan(args.dsn))
    if args.loosen:
        print("\n  loosened: " + (", ".join(loosen(args.dsn)) or "nothing left to loosen"))
    if args.backup:
        print(f"\n  backup in {args.backup}, read back: {backup(args.dsn, args.backup)}")
    if args.drop:
        for line in drop(args.dsn):
            print("  " + line)
    if not (args.loosen or args.drop):
        print("\n  report only -- nothing was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
