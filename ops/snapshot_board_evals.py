"""A snapshot of what the idea board learned, before the board is taken
out (2026-10-11, step 0 of docs/tasks/task-higgsfield-shape.md).

The board's labels -- which scenes were picked, which were passed and why,
what the prompt gate scored, how each hold was graded, which prompts were
filed as lessons -- stop being written and read once the eval layer moves
from the idea to the output. Mike's rule for that work is that nothing is
lost, so this copies them out FIRST. It deletes nothing and changes nothing:
every table and column it reads is left exactly where it is.

It REPORTS by default (the counts, per account) and writes files only with
--write, into `data/backups/board-evals-<date>/`:

    account-<id>-<slug>.json   one per account, and `account-unowned.json`
                               for rows with no account:
        concepts   the label columns of every `shoot_concepts` row (never
                   the prompt -- the row itself stays in the database)
        holds      every graded `hold_queue` row (status other than "held")
        rates      pick_rate, shoot_rate, reason_counts and
                   evaluator_agreement as they answer today, plus
                   ungrounded_count
    shared.json                the tables that carry no account:
        prompt_scores      every score the prompt gate logged
        winning_prompts    every lesson, pending and ingested, both shelves
                           (verdict "worked" = winning_prompts, "didnt_work"
                           = avoid_prompts)
        rates              prompt_gate_agreement and first_try_pass_rate
    manifest.json              when, where it read, and the row counts

`data/backups/` is gitignored on purpose: the repository is public.

It never falls back to a database on its own: DATABASE_URL must be exported
(or --dsn given), and the report prints which host and database it read
(ops/wipe_concepts.py's rule, for the same reason).

    set -a && source .env && set +a
    venv/bin/python -m ops.snapshot_board_evals            # report only
    venv/bin/python -m ops.snapshot_board_evals --write    # save the files
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from psycopg.conninfo import conninfo_to_dict

from src import autonomy, db, preprod

ROOT = Path(__file__).resolve().parent.parent

# The label columns of a concept: who it is, and everything a person or a
# judge decided about it. A column the live table does not have is skipped.
CONCEPT_COLUMNS = (
    "id", "created_at", "brand", "title", "project_id", "prompt_hash",
    "picked_at", "archived_at", "archive_reason", "shot_done",
    "judge_overall", "judge_taste", "judge_perf", "judge_reason",
    "uncanny_overall", "uncanny_passed", "uncanny_reason",
)
# the rate functions that answer per account; a missing one is reported
ACCOUNT_RATES = (
    ("pick_rate", lambda dsn, a: preprod.pick_rate(dsn, account_id=a)),
    ("shoot_rate", lambda dsn, a: preprod.shoot_rate(dsn, account_id=a)),
    ("reason_counts", lambda dsn, a: preprod.reason_counts(dsn, account_id=a)),
    ("evaluator_agreement", lambda dsn, a: autonomy.evaluator_agreement(dsn=dsn, account_id=a)),
    ("ungrounded_count", lambda dsn, a: preprod.ungrounded_count(dsn, account_id=a)),
)
SHARED_RATES = (
    ("prompt_gate_agreement", lambda dsn: autonomy.prompt_gate_agreement(dsn=dsn)),
    ("first_try_pass_rate", lambda dsn: autonomy.first_try_pass_rate(dsn=dsn)),
)


def _where(dsn: str) -> str:
    """Host and database, never the password."""
    try:
        parts = conninfo_to_dict(dsn)
    except Exception:
        return "an unreadable DSN"
    options = parts.get("options") or ""
    return f"{parts.get('host') or 'localhost'}:{parts.get('port') or 5432}/{parts.get('dbname') or '?'}" \
        + (f" ({options})" if options else "")


def _tables(conn) -> set[str]:
    return {r["table_name"] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema()").fetchall()}


def _columns(conn, table: str) -> set[str]:
    return {r["column_name"] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s", (table,)).fetchall()}


def _rate(fn, *args) -> Any:
    """A rate as it answers today. One that cannot answer is written down
    as that, never a reason to lose the rest of the snapshot."""
    try:
        return fn(*args)
    except Exception as e:
        return f"unavailable: {type(e).__name__}: {e}"


def _account_file(account_id: Optional[int], slug: Optional[str]) -> str:
    return "account-unowned.json" if account_id is None else f"account-{account_id}-{slug or 'account'}.json"


def collect(dsn: str) -> dict[str, Any]:
    """Everything the snapshot holds, read-only:
    {"accounts": [{account_id, slug, concepts, holds, rates}], "shared":
    {prompt_scores, winning_prompts, rates}}. An account appears when it
    has a row in `accounts` or owns a concept or a graded hold; rows with
    no account are the entry whose account_id is None."""
    with db.connect(dsn) as conn:
        tables = _tables(conn)
        slugs: dict[Optional[int], Optional[str]] = {}
        if "accounts" in tables:
            for r in conn.execute("SELECT id, slug FROM accounts ORDER BY id").fetchall():
                slugs[int(r["id"])] = r["slug"]

        concepts: dict[Optional[int], list[dict]] = {}
        if "shoot_concepts" in tables:
            have = _columns(conn, "shoot_concepts")
            cols = [c for c in CONCEPT_COLUMNS if c in have]
            for r in conn.execute(
                    f"SELECT account_id, {', '.join(cols)} FROM shoot_concepts ORDER BY id").fetchall():
                row = dict(r)
                concepts.setdefault(row.pop("account_id"), []).append(row)

        holds: dict[Optional[int], list[dict]] = {}
        if "hold_queue" in tables:
            for r in conn.execute(
                    "SELECT * FROM hold_queue WHERE status <> 'held' ORDER BY id").fetchall():
                row = dict(r)
                holds.setdefault(row.get("account_id"), []).append(row)

        scores = ([dict(r) for r in conn.execute(
            "SELECT * FROM prompt_scores ORDER BY id").fetchall()]
            if "prompt_scores" in tables else [])
        lessons = ([dict(r) for r in conn.execute(
            "SELECT * FROM winning_prompts ORDER BY id").fetchall()]
            if "winning_prompts" in tables else [])

    owners = sorted(set(slugs) | {a for a in concepts if a is not None}
                    | {a for a in holds if a is not None})
    if None in concepts or None in holds:
        owners = owners + [None]
    out_accounts = []
    for account_id in owners:
        out_accounts.append({
            "account_id": account_id,
            "slug": slugs.get(account_id),
            "concepts": concepts.get(account_id, []),
            "holds": holds.get(account_id, []),
            "rates": {name: _rate(fn, dsn, account_id) for name, fn in ACCOUNT_RATES},
        })
    return {
        "accounts": out_accounts,
        "shared": {
            "prompt_scores": scores,
            "winning_prompts": lessons,
            "rates": {name: _rate(fn, dsn) for name, fn in SHARED_RATES},
        },
    }


def counts(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The row counts of a snapshot: what the report prints and the
    manifest records."""
    per_account = []
    for a in snapshot["accounts"]:
        rows = a["concepts"]
        per_account.append({
            "account_id": a["account_id"], "slug": a["slug"],
            "concepts": len(rows),
            "picked": sum(1 for r in rows if r.get("picked_at")),
            "archived": sum(1 for r in rows if r.get("archived_at")),
            "with_reason": sum(1 for r in rows if (r.get("archive_reason") or "").strip()),
            "marked_shot": sum(1 for r in rows if r.get("shot_done")),
            "graded_holds": len(a["holds"]),
        })
    lessons = snapshot["shared"]["winning_prompts"]
    return {
        "accounts": per_account,
        "prompt_scores": len(snapshot["shared"]["prompt_scores"]),
        "winning_prompts": {
            "worked_ingested": sum(1 for r in lessons if r.get("verdict") == "worked" and r.get("ingested")),
            "worked_pending": sum(1 for r in lessons if r.get("verdict") == "worked" and not r.get("ingested")),
            "avoid_ingested": sum(1 for r in lessons if r.get("verdict") != "worked" and r.get("ingested")),
            "avoid_pending": sum(1 for r in lessons if r.get("verdict") != "worked" and not r.get("ingested")),
        },
    }


def write(snapshot: dict[str, Any], out_dir: Path, *, where: str = "") -> list[Path]:
    """Save a snapshot under `out_dir` (created). Returns the files written.
    Refuses a directory that already holds a manifest: a snapshot is a
    record of one day, never overwritten by a later, emptier one."""
    if (out_dir / "manifest.json").exists():
        raise FileExistsError(f"{out_dir} already holds a snapshot -- move it or pass --out")
    out_dir.mkdir(parents=True, exist_ok=True)
    written_at = datetime.now(timezone.utc).isoformat()
    files: list[Path] = []
    for a in snapshot["accounts"]:
        path = out_dir / _account_file(a["account_id"], a["slug"])
        path.write_text(json.dumps({"written_at": written_at, **a}, default=str, indent=1))
        files.append(path)
    shared = out_dir / "shared.json"
    shared.write_text(json.dumps({"written_at": written_at, **snapshot["shared"]},
                                 default=str, indent=1))
    files.append(shared)
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "written_at": written_at, "database": where,
        "note": ("the idea board's labels before it was taken out "
                 "(docs/tasks/task-higgsfield-shape.md, step 0); nothing was deleted"),
        "files": [p.name for p in files], "counts": counts(snapshot)}, default=str, indent=1))
    files.append(manifest)
    return files


def _print(report: dict[str, Any], snapshot: dict[str, Any]) -> None:
    for a, full in zip(report["accounts"], snapshot["accounts"]):
        who = "no account (unowned rows)" if a["account_id"] is None \
            else f"{a['slug'] or '?'} (id {a['account_id']})"
        print(f"\n  {who}")
        print(f"    concepts       {a['concepts']:>6}   picked {a['picked']} · archived "
              f"{a['archived']} ({a['with_reason']} with a reason) · marked shot {a['marked_shot']}")
        print(f"    graded holds   {a['graded_holds']:>6}")
        for name, value in full["rates"].items():
            line = value if isinstance(value, str) else json.dumps(value, default=str)
            print(f"    {name:<22} {line[:150]}")
    w = report["winning_prompts"]
    print("\n  shared (no account column)")
    print(f"    prompt_scores  {report['prompt_scores']:>6}")
    print(f"    lessons        worked {w['worked_ingested']} ingested + {w['worked_pending']} pending"
          f" · avoid {w['avoid_ingested']} ingested + {w['avoid_pending']} pending")
    for name, value in snapshot["shared"]["rates"].items():
        line = value if isinstance(value, str) else json.dumps(value, default=str)
        print(f"    {name:<22} {line[:150]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Snapshot the idea board's labels and eval numbers (report by default).")
    ap.add_argument("--dsn", help="database URL (default: the exported DATABASE_URL)")
    ap.add_argument("--out", help="directory to write into "
                                  "(default: data/backups/board-evals-<today>)")
    ap.add_argument("--write", action="store_true",
                    help="save the files; without it this only reports")
    args = ap.parse_args(argv)

    dsn = args.dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        print("refusing: no --dsn and no DATABASE_URL exported -- this script never "
              "guesses which database to read (`set -a && source .env && set +a`)",
              file=sys.stderr)
        return 2
    where = _where(dsn)
    print(f"database: {where}")
    snapshot = collect(dsn)
    _print(counts(snapshot), snapshot)
    if not args.write:
        print("\n  report only -- nothing was written. Re-run with --write to save it.")
        return 0
    out_dir = Path(args.out) if args.out else ROOT / "data" / "backups" / f"board-evals-{date.today()}"
    try:
        files = write(snapshot, out_dir, where=where)
    except FileExistsError as e:
        print(f"\n  stopped: {e}", file=sys.stderr)
        return 3
    print(f"\n  wrote {len(files)} file(s) to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
