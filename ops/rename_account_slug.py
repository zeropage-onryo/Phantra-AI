"""Rename one account's slug, everywhere the slug is stored (2026-10-14;
docs/tasks/task-remove-brand-labels.md, step 8: `zeropage` -> `phantra`).

The slug is stored in two places that matter:

  accounts.slug          the workspace's name: the account cookie, /api/me,
                         the seed and the CLI all find it by this
  rag_documents.project  the tenant that taught a reference-library row;
                         retrieval PREFERS rows whose label is the caller's
                         slug (src/rag.py), so a row left on the old name
                         would stop being preferred

`--label` also sets the account's display name (the workspace label
/api/me shows), which on live still read "Zero Page Films".

It REPORTS by default: the account, whether the new slug is free, and how
many rows of EVERY text column in the schema hold exactly the old slug. A
column holding it that this script does not know refuses the write, so a
copy of the slug nobody decided about is never left behind silently.
`--backup DIR` writes the rows it would change as JSON and reads them back;
`--write` needs it, renames in one transaction and rolls back if any count
differs from the report. Re-runnable: a second run finds nothing to do.
Not to be run without Mike's yes on the report.

DATABASE_URL must be exported (or --dsn given); it prints the host it read.

    set -a && source .env && set +a
    venv/bin/python -m ops.rename_account_slug --from zeropage --to phantra
    venv/bin/python -m ops.rename_account_slug --from zeropage --to phantra \\
        --label Phantra --backup data/backups/slug-rename-<date> --write
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

# the columns this script renames, in the order it renames them
RENAME = (("rag_documents", "project"), ("accounts", "slug"))
# columns that may hold the old slug and are not this script's to touch:
# the brand labels step 6 drops (docs/tasks/task-remove-brand-labels.md),
# which carry the same word for a different reason
IGNORE = {
    ("shoot_concepts", "brand"), ("scene_briefs", "brand"), ("workflows", "brand"),
    ("videos", "brand"), ("scout_findings", "brand"), ("scout_bin", "brand"),
    ("hold_queue", "channel"), ("channels", "name"), ("inspiration_accounts", "brand"),
    ("generated_assets", "project"),
}


def _text_columns(conn) -> list[tuple[str, str]]:
    rows = conn.execute(
        "SELECT c.table_name, c.column_name FROM information_schema.columns c "
        "JOIN information_schema.tables t ON t.table_name = c.table_name "
        "AND t.table_schema = c.table_schema "
        "WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE' "
        "AND c.data_type IN ('text', 'character varying') "
        "ORDER BY c.table_name, c.column_name").fetchall()
    return [(r["table_name"], r["column_name"]) for r in rows]


def scan(dsn: str, old: str, new: str, label: str = "") -> dict[str, Any]:
    """What the rename would do, read-only."""
    with db.connect(dsn) as conn:
        account = conn.execute("SELECT id, slug, display_name FROM accounts WHERE slug = %s",
                               (old,)).fetchone()
        taken = conn.execute("SELECT id FROM accounts WHERE slug = %s", (new,)).fetchone()
        holding: dict[str, int] = {}
        for table, col in _text_columns(conn):
            n = conn.execute(f'SELECT count(*) AS n FROM "{table}" WHERE "{col}" = %s',
                             (old,)).fetchone()["n"]
            if n:
                holding[f"{table}.{col}"] = n
    renames = {f"{t}.{c}": holding.get(f"{t}.{c}", 0) for t, c in RENAME}
    ignored = {k: v for k, v in holding.items()
               if tuple(k.split(".", 1)) in IGNORE}
    unknown = {k: v for k, v in holding.items()
               if k not in renames and k not in ignored}
    return {"old": old, "new": new, "label": (label or "").strip(),
            "account": dict(account) if account else None,
            "new_slug_taken": bool(taken),
            "renames": renames, "ignored": ignored, "unknown": unknown}


def refusal(plan: dict[str, Any]) -> str:
    """Why --write must not run, or ""."""
    if not plan["account"]:
        return f"no account has the slug {plan['old']!r}"
    if plan["new_slug_taken"]:
        return f"the slug {plan['new']!r} is already taken"
    if plan["unknown"]:
        return ("these columns hold the old slug and this script does not know them: "
                + ", ".join(f"{k} ({v})" for k, v in plan["unknown"].items())
                + " -- decide them first")
    return ""


def backup(dsn: str, plan: dict[str, Any], out: Path) -> dict[str, int]:
    """The rows --write changes, one JSON file per column, read back."""
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    with db.connect(dsn) as conn:
        for table, col in RENAME:
            have = db.columns(conn, table) if db.table_exists(conn, table) else set()
            if col not in have:
                continue
            key = "id" if "id" in have else col
            rows = [dict(r) for r in conn.execute(
                f'SELECT "{key}", "{col}" FROM "{table}" WHERE "{col}" = %s',
                (plan["old"],)).fetchall()]
            path = out / f"{table}.{col}.json"
            path.write_text(json.dumps(rows, default=str, indent=1))
            back = json.loads(path.read_text())
            if len(back) != len(rows):
                raise RuntimeError(f"{path} read back {len(back)} rows, wrote {len(rows)}")
            written[f"{table}.{col}"] = len(back)
        if plan.get("label") and plan["account"]:
            row = conn.execute("SELECT id, display_name FROM accounts WHERE id = %s",
                               (plan["account"]["id"],)).fetchone()
            path = out / "accounts.display_name.json"
            path.write_text(json.dumps([dict(row)], default=str, indent=1))
            written["accounts.display_name"] = len(json.loads(path.read_text()))
    (out / "plan.json").write_text(json.dumps(plan, default=str, indent=1))
    return written


def rename(dsn: str, plan: dict[str, Any]) -> dict[str, int]:
    """One transaction; raises (and rolls back) if a count moved."""
    why = refusal(plan)
    if why:
        raise RuntimeError(why)
    done: dict[str, int] = {}
    with db.connect(dsn) as conn:
        for table, col in RENAME:
            if not db.table_exists(conn, table):
                done[f"{table}.{col}"] = 0
                continue
            done[f"{table}.{col}"] = conn.execute(
                f'UPDATE "{table}" SET "{col}" = %s WHERE "{col}" = %s',
                (plan["new"], plan["old"])).rowcount
        if plan.get("label"):
            conn.execute("UPDATE accounts SET display_name = %s WHERE id = %s",
                         (plan["label"], plan["account"]["id"]))
        if done != plan["renames"]:
            raise RuntimeError(f"renamed {done}, the report said {plan['renames']}: rolled back")
    return done


def _print(plan: dict[str, Any]) -> None:
    acc = plan["account"]
    print(f"  account: {acc['slug']!r} (id {acc['id']}, {acc.get('display_name') or ''})"
          if acc else f"  account: none has the slug {plan['old']!r}")
    print(f"  {plan['new']!r} free: {'no' if plan['new_slug_taken'] else 'yes'}")
    if plan.get("label") and acc:
        print(f"  label: {acc.get('display_name')!r} -> {plan['label']!r}")
    print("  renames " + ", ".join(f"{k} {v}" for k, v in plan["renames"].items()))
    if plan["ignored"]:
        print("  left alone (dropped in step 6): "
              + ", ".join(f"{k} {v}" for k, v in plan["ignored"].items()))
    if plan["unknown"]:
        print("  UNKNOWN columns holding it: "
              + ", ".join(f"{k} {v}" for k, v in plan["unknown"].items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="old", required=True)
    ap.add_argument("--to", dest="new", required=True)
    ap.add_argument("--label", default="", help="also set the account's display name")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--backup", type=Path, help="write the rows --write changes here")
    ap.add_argument("--write", action="store_true", help="rename (needs --backup)")
    args = ap.parse_args(argv)
    if not args.dsn:
        print("DATABASE_URL is not exported and no --dsn was given; nothing read.", file=sys.stderr)
        return 2
    if args.write and not args.backup:
        print("--write needs --backup: nothing is renamed without one.", file=sys.stderr)
        return 2
    print(f"database: {_where(args.dsn)}")
    plan = scan(args.dsn, args.old, args.new, args.label)
    _print(plan)
    why = refusal(plan)
    if args.backup:
        print(f"  backup in {args.backup}, read back: {backup(args.dsn, plan, args.backup)}")
    if args.write:
        if why:
            print(f"refused: {why}", file=sys.stderr)
            return 1
        print(f"  renamed: {rename(args.dsn, plan)}")
    else:
        print(("  would refuse: " + why) if why else "\n  report only -- nothing was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
