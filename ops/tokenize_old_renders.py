"""Give the renders that were written before 2026-10-15 an unguessable name.

WHY. Until PR #336 every render was named for a timestamp
(`c12-s1-20261001-120000.png`) and mirrored to the public bucket at
`m/<account>/renders/<provider>/<name>`. Anyone could walk that name space.
New renders end in a 128-bit token (src/render_names.py); the ones already in
the bucket still carry the guessable name, and the bucket is public. This
copies each one to a tokened key and rewrites every stored mention of the name.

NOTHING IS LOST, and the order is the safety:

  report (default)   read the bucket and the database; change nothing
  --write            1. write the manifest (old name -> new name) and a
                        backup of every row it will touch
                     2. COPY each object, and its t/ thumbnail, to the new key
                     3. verify the copies are there
                     4. copy the local data/renders file beside the old one
                     5. rewrite the stored names, in ONE transaction
  --revert           put the old names back on the rows (the copies stay)
  --delete-old       the step that closes the hole: remove the old keys, only
                     for entries whose new key exists AND that no row mentions
                     any more. Run it after you have looked at the studio.

The old keys keep serving until --delete-old, so every step before it is
reversible. A row's stored name is found by scanning EVERY text, varchar, json
and jsonb column of the schema for the old file name, not a fixed list of
columns, so a writer nobody remembered is still caught. A name that two
objects share, or that an owner cannot be told for, is reported and skipped.

    python -m ops.tokenize_old_renders                       # report
    python -m ops.tokenize_old_renders --write
    python -m ops.tokenize_old_renders --revert --manifest <path> --write
    python -m ops.tokenize_old_renders --delete-old --manifest <path> --write

Export DATABASE_URL first (this loads .env, but a bare shell may not be the
database you mean): the tell for the wrong one is a count of zero.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src import db, media, render_names, storage

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
LOCAL_RENDERS = ROOT / "data" / "renders"
BACKUPS = ROOT / "data" / "backups"
TEXTY = ("text", "character varying", "json", "jsonb")

# Columns that hold the name as an IDENTIFIER, not an address: the file name
# doubles as the hold reference that ties a ledger entry to its fal request
# and its render (src/charge.attempt_ref), and the rest is history. Rewriting
# them would break that audit trail, so they are reported and left alone.
IDENTIFIER_COLUMNS = {
    ("credit_entries", "ref"),
    ("fal_requests", "ref"),
    ("fal_requests", "context_json"),
    ("generated_assets", "metadata_json"),
    ("generations", "params_json"),
    ("output_events", "meta"),
}

# A name is a whole word in a string: never the middle of a longer one.
_BEFORE = r"(?<![A-Za-z0-9_.\-])"
_AFTER = r"(?![A-Za-z0-9_\-])"


# --------------------------------------------------------------------------
# what is in the bucket
# --------------------------------------------------------------------------

def legacy_objects(keys: list[str]) -> list[dict]:
    """Every master under m/<account>/renders/ whose name can be guessed."""
    out = []
    for key in keys:
        parts = key.split("/")
        if len(parts) < 4 or parts[0] != media.MASTER_PREFIX or parts[2] != "renders":
            continue
        if not parts[1].isdigit():
            continue
        tail = "/".join(parts[2:])
        rel = "/".join(parts[3:])
        if render_names.is_capability(rel):
            continue
        out.append({"account": int(parts[1]), "key": key, "tail": tail,
                    "rel": rel, "name": parts[-1]})
    return out


def split_ambiguous(objects: list[dict]) -> tuple[list[dict], list[dict]]:
    """A file name shared by two objects cannot be rewritten by name."""
    count = Counter(o["name"] for o in objects)
    return ([o for o in objects if count[o["name"]] == 1],
            [o for o in objects if count[o["name"]] > 1])


def new_name(name: str) -> str:
    """`c12-s1-<stamp>.png` -> `c12-s1-<stamp>-<32 hex>.png`."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return render_names.unguessable(name)
    return render_names.unguessable(stem) + "." + ext


def make_manifest(objects: list[dict], keys: set[str]) -> list[dict]:
    entries = []
    for o in objects:
        fresh = new_name(o["name"])
        new_tail = o["tail"].rsplit("/", 1)[0] + "/" + fresh
        thumb = f"{media.THUMB_PREFIX}/{o['account']}/{o['tail']}"
        entry = {
            "account": o["account"], "old_name": o["name"], "new_name": fresh,
            "old_key": o["key"],
            "new_key": f"{media.MASTER_PREFIX}/{o['account']}/{new_tail}",
            "rel": o["rel"], "new_rel": o["rel"].rsplit("/", 1)[0] + "/" + fresh
            if "/" in o["rel"] else fresh,
        }
        if thumb in keys:
            entry["old_thumb"] = thumb
            entry["new_thumb"] = f"{media.THUMB_PREFIX}/{o['account']}/{new_tail}"
        entries.append(entry)
    return entries


# --------------------------------------------------------------------------
# what the database says
# --------------------------------------------------------------------------

def text_columns(conn) -> list[tuple[str, str, str]]:
    """(table, column, data_type) for every text-like column of the schema."""
    rows = conn.execute(
        "SELECT c.table_name, c.column_name, c.data_type "
        "FROM information_schema.columns c "
        "JOIN information_schema.tables t "
        "  ON t.table_schema = c.table_schema AND t.table_name = c.table_name "
        "WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE' "
        "  AND c.data_type = ANY(%s) ORDER BY 1, 2", (list(TEXTY),)).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def _pg_pattern(names) -> str:
    return "|".join(re.escape(n) for n in sorted(names))


def scan(conn, names, skip=IDENTIFIER_COLUMNS) -> list[dict]:
    """Every row whose text mentions one of `names`, in the columns that hold
    addresses: {table, ctid, columns: {column: (type, value)}}."""
    if not names:
        return []
    pattern = _pg_pattern(names)
    grouped: dict = {}
    for table, column, kind in text_columns(conn):
        if (table, column) in skip:
            continue
        with conn.transaction():
            rows = conn.execute(
                f'SELECT ctid::text, "{column}"::text FROM "{table}" '
                f'WHERE "{column}"::text ~ %s', (pattern,)).fetchall()
        for ctid, value in rows:
            row = grouped.setdefault((table, ctid),
                                     {"table": table, "ctid": ctid, "columns": {}})
            row["columns"][column] = (kind, value)
    return list(grouped.values())


def rewrite_text(value: str, mapping: dict) -> str:
    """Swap each old name for its new one, whole names only."""
    if not value:
        return value
    pattern = re.compile(
        _BEFORE + "(" + "|".join(re.escape(n) for n in
                                 sorted(mapping, key=len, reverse=True)) + ")" + _AFTER)
    return pattern.sub(lambda m: mapping[m.group(1)], value)


def mentions(value: str, names) -> list[str]:
    if not value:
        return []
    pattern = re.compile(_BEFORE + "(" + "|".join(re.escape(n) for n in names) + ")" + _AFTER)
    return pattern.findall(value)


def apply_rewrite(conn, rows: list[dict], mapping: dict) -> int:
    """One UPDATE per row, all its columns at once (a row's ctid changes the
    moment it is updated, so a second UPDATE on it would miss)."""
    changed = 0
    for row in rows:
        sets, args = [], []
        for column, (kind, value) in row["columns"].items():
            after = rewrite_text(value, mapping)
            if after == value:
                continue
            cast = {"jsonb": "::jsonb", "json": "::json"}.get(kind, "")
            sets.append(f'"{column}" = %s{cast}')
            args.append(after)
        if not sets:
            continue
        done = conn.execute(
            f'UPDATE "{row["table"]}" SET {", ".join(sets)} WHERE ctid = %s::tid',
            (*args, row["ctid"]))
        changed += done.rowcount
    return changed


# --------------------------------------------------------------------------
# the report
# --------------------------------------------------------------------------

def report(dsn: Optional[str] = None) -> dict:
    keys = storage.list_keys("")
    keyset = set(keys)
    objects = legacy_objects(keys)
    usable, ambiguous = split_ambiguous(objects)
    names = {o["name"] for o in usable}
    with db.connect(dsn) as conn:
        hits = scan(conn, names)
        kept = scan(conn, names, skip=set())
    left_alone: Counter = Counter()
    for row in kept:
        for column, (_kind, value) in row["columns"].items():
            if (row["table"], column) in IDENTIFIER_COLUMNS and mentions(value, names):
                left_alone[f"{row['table']}.{column}"] += 1
    seen: dict = defaultdict(set)
    per_column: Counter = Counter()
    for row in hits:
        for column, (_kind, value) in row["columns"].items():
            found = mentions(value, names)
            if found:
                per_column[f"{row['table']}.{column}"] += 1
                seen[row["table"]].update(found)
    mentioned = set().union(*seen.values()) if seen else set()
    return {
        "objects": usable, "ambiguous": ambiguous, "keys": keyset,
        "by_account": Counter(o["account"] for o in usable),
        "by_ext": Counter(o["name"].rsplit(".", 1)[-1].lower() for o in usable),
        "thumbs": sum(1 for o in usable
                      if f"{media.THUMB_PREFIX}/{o['account']}/{o['tail']}" in keyset),
        "rows": len(hits), "per_column": per_column, "left_alone": left_alone,
        "unreferenced": sorted(names - mentioned),
    }


def print_report(r: dict) -> None:
    print(f"{len(r['objects'])} guessable render objects "
          f"({dict(r['by_account'])} by account; {dict(r['by_ext'])})")
    print(f"  with a t/ thumbnail to copy too: {r['thumbs']}")
    print(f"  skipped, name shared by more than one object: {len(r['ambiguous'])}")
    for o in r["ambiguous"][:20]:
        print(f"    ambiguous  {o['key']}")
    print(f"database rows that mention one of them: {r['rows']}")
    for col, n in sorted(r["per_column"].items()):
        print(f"    {col}: {n}")
    print("named only as an identifier (ledger and history), left alone:")
    for col, n in sorted(r["left_alone"].items()):
        print(f"    {col}: {n}")
    print(f"objects no row mentions (copied and re-keyed anyway): {len(r['unreferenced'])}")
    for n in r["unreferenced"][:25]:
        print(f"    unreferenced  {n}")
    print("\nreport only. --write copies, verifies and rewrites; the old keys "
          "keep serving until --delete-old.")


# --------------------------------------------------------------------------
# write, revert, delete
# --------------------------------------------------------------------------

def _backup_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = BACKUPS / f"tokenize-renders-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write(dsn: Optional[str] = None, out_dir: Optional[Path] = None) -> dict:
    keys = storage.list_keys("")
    keyset = set(keys)
    usable, ambiguous = split_ambiguous(legacy_objects(keys))
    entries = make_manifest(usable, keyset)
    out_dir = out_dir or _backup_dir()
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"entries": entries}, indent=1))

    mapping = {e["old_name"]: e["new_name"] for e in entries}
    with db.connect(dsn) as conn:
        rows = scan(conn, set(mapping))
    (out_dir / "rows-before.json").write_text(json.dumps(
        [{"table": r["table"], "ctid": r["ctid"],
          "columns": {c: v[1] for c, v in r["columns"].items()}} for r in rows]))

    result = {"manifest": str(manifest_path), "copied": 0, "missing": [],
              "local": 0, "rows": 0, "ambiguous": len(ambiguous)}
    for e in entries:
        for source, dest in ((e["old_key"], e["new_key"]),
                             (e.get("old_thumb"), e.get("new_thumb"))):
            if not source:
                continue
            storage.copy_key(source, dest)
            result["copied"] += 1
    for e in entries:
        if not storage.key_exists(e["new_key"]):
            result["missing"].append(e["new_key"])
    if result["missing"]:
        return result              # nothing in the database was touched
    for e in entries:
        old = LOCAL_RENDERS / e["rel"]
        if old.is_file():
            new = LOCAL_RENDERS / e["new_rel"]
            if not new.exists():
                shutil.copy2(old, new)
                result["local"] += 1
    with db.connect(dsn) as conn:       # commits once, or not at all
        result["rows"] = apply_rewrite(conn, rows, mapping)
    return result


def _load(manifest: Path) -> list[dict]:
    return json.loads(Path(manifest).read_text())["entries"]


def revert(manifest: Path, dsn: Optional[str] = None) -> int:
    entries = _load(manifest)
    back = {e["new_name"]: e["old_name"] for e in entries}
    with db.connect(dsn) as conn:
        rows = scan(conn, set(back))
        return apply_rewrite(conn, rows, back)


def delete_old(manifest: Path, dsn: Optional[str] = None) -> dict:
    entries = _load(manifest)
    old_names = {e["old_name"] for e in entries}
    with db.connect(dsn) as conn:
        still = scan(conn, old_names)
    mentioned = set()
    for row in still:
        for _kind, value in row["columns"].values():
            mentioned.update(mentions(value, old_names))
    result = {"deleted": 0, "kept": [], "rows_still_naming": len(still)}
    client = storage._client()
    for e in entries:
        why = None
        if e["old_name"] in mentioned:
            why = "a row still names the old file"
        elif not storage.key_exists(e["new_key"]):
            why = "the new key is not in the bucket"
        elif e.get("new_thumb") and not storage.key_exists(e["new_thumb"]):
            why = "the new thumbnail is not in the bucket"
        if why:
            result["kept"].append((e["old_key"], why))
            continue
        for key in (e["old_key"], e.get("old_thumb")):
            if key:
                client.delete_object(Bucket=storage.bucket(), Key=key)
                result["deleted"] += 1
    return result


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--write", action="store_true",
                   help="act (every mode is a report without it)")
    p.add_argument("--revert", action="store_true")
    p.add_argument("--delete-old", action="store_true")
    p.add_argument("--manifest", default=None)
    p.add_argument("--dsn", default=None)
    args = p.parse_args(argv)

    if not storage.configured():
        print("R2 is not configured (the five R2_* vars) -- nothing to do.")
        return
    if (args.revert or args.delete_old) and not args.manifest:
        sys.exit("--revert and --delete-old need --manifest <path>")

    if args.revert or args.delete_old:
        entries = _load(Path(args.manifest))
        what = "revert" if args.revert else "delete the old keys of"
        if not args.write:
            print(f"would {what} {len(entries)} entries. Re-run with --write.")
            return
        if args.revert:
            print(f"rows rewritten back: {revert(Path(args.manifest), args.dsn)}")
        else:
            out = delete_old(Path(args.manifest), args.dsn)
            print(f"deleted {out['deleted']} keys; kept {len(out['kept'])}")
            for key, why in out["kept"][:25]:
                print(f"    kept  {key}  -- {why}")
        return

    if not args.write:
        print_report(report(args.dsn))
        return
    out = write(args.dsn)
    print(f"manifest and row backup: {Path(out['manifest']).parent}")
    print(f"copied {out['copied']} objects; local files copied {out['local']}; "
          f"rows rewritten {out['rows']}; skipped as ambiguous {out['ambiguous']}")
    if out["missing"]:
        print("STOPPED before touching the database: new keys missing from the bucket:")
        for k in out["missing"][:20]:
            print(f"    {k}")


if __name__ == "__main__":
    main()
