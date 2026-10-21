"""Load a brand kit prepared as a folder into an account (2026-10-21,
docs/tasks/task-brand-kit-import-and-chat.md step 1; the Gygler kit was the
first).

The folder holds ONE `*.json` (`{"name": ..., "spec": {...}}`) and its files
named by role:

    logo_light.png  logo_dark.png              (PNG / WebP / JPEG)
    logo_light_source.svg  logo_dark_source.svg
    font_heading_<anything>.ttf|otf  font_body_<anything>.ttf|otf
    reference_<n>.jpg                          (up to 8)
    FONT_LICENCE.txt                           (names the fonts' licence)

A font goes on only when FONT_LICENCE.txt is there and says what licence it
is under -- that line is the "I may embed this font in video" box the kit
page asks a person to tick, and it is stored on the font's row.

Every check `brand_kits` runs on an upload runs here first, and nothing is
written without --write. A kit of the same name already on the account is
UPDATED (its spec replaced, files it already holds skipped), never doubled,
so a second run changes nothing:

    venv/bin/python -m ops.import_brand_kit <folder> --account <slug>
    venv/bin/python -m ops.import_brand_kit <folder> --account <slug> --write

Like src.accounts, this does NOT load .env: export DATABASE_URL first (and
the R2 settings, so the files reach the bucket the deployed app reads), or
it reports against the local throwaway database.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from psycopg.conninfo import conninfo_to_dict

from src import accounts, brand_kits, db, storage

LICENCE_FILE = "FONT_LICENCE.txt"
_ROLE_FILES = (
    ("logo_light_source", re.compile(r"^logo_light_source\.svg$", re.I)),
    ("logo_dark_source", re.compile(r"^logo_dark_source\.svg$", re.I)),
    ("logo_light", re.compile(r"^logo_light\.(png|webp|jpe?g)$", re.I)),
    ("logo_dark", re.compile(r"^logo_dark\.(png|webp|jpe?g)$", re.I)),
    ("font_heading", re.compile(r"^font_heading_.+\.(ttf|otf)$", re.I)),
    ("font_body", re.compile(r"^font_body_.+\.(ttf|otf)$", re.I)),
    ("reference", re.compile(r"^reference_.+\.(jpe?g|png|webp|heic)$", re.I)),
)


class FolderError(ValueError):
    """A folder the importer refuses, said in one line."""


def role_of(name: str) -> Optional[str]:
    for role, pattern in _ROLE_FILES:
        if pattern.match(name):
            return role
    return None


def _ref_order(path: Path):
    digits = re.findall(r"\d+", path.stem)
    return (int(digits[-1]) if digits else 0, path.name)


def read_folder(folder: Path) -> dict:
    """The kit the folder describes, every file already checked -- or
    FolderError / brand_kits.KitError naming what is wrong. Writes nothing."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FolderError(f"{folder} is not a folder")
    specs = sorted(folder.glob("*.json"))
    if len(specs) != 1:
        raise FolderError(f"{folder} needs exactly one .json (found {len(specs)})")
    try:
        raw = json.loads(specs[0].read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise FolderError(f"{specs[0].name} is not JSON: {e}") from None
    if not isinstance(raw, dict):
        raise FolderError(f"{specs[0].name} must be {{name, spec}}")
    name = brand_kits.clean_name(raw.get("name"))
    spec = brand_kits.clean_spec(raw.get("spec"))

    licence = ""
    licence_path = folder / LICENCE_FILE
    if licence_path.is_file():
        licence = " ".join(licence_path.read_text(encoding="utf-8").split())

    files, ignored = [], []
    paths = sorted((p for p in folder.iterdir() if p.is_file()), key=lambda p: p.name)
    by_role: dict[str, list[Path]] = {}
    for path in paths:
        if path.suffix.lower() == ".json" or path.name in (LICENCE_FILE, ".DS_Store"):
            continue
        role = role_of(path.name)
        if role is None:
            ignored.append(path.name)
            continue
        by_role.setdefault(role, []).append(path)
    for role, found in by_role.items():
        keep = brand_kits.ASSET_ROLES[role][3]
        if len(found) > keep:
            raise FolderError(f"{len(found)} files for {role}; a kit keeps {keep}: "
                               + ", ".join(p.name for p in found))
    for role, _pattern in _ROLE_FILES:
        found = by_role.get(role) or []
        if role == "reference":
            found = sorted(found, key=_ref_order)
        for path in found:
            if role in brand_kits.FONT_ROLES and not licence:
                raise brand_kits.KitError(
                    role, f"{path.name}: no {LICENCE_FILE} in the folder says this font "
                          "may be embedded in video")
            data, mime, meta = brand_kits.check_asset(
                role, path.read_bytes(), filename=path.name,
                licensed=role in brand_kits.FONT_ROLES, licence=licence)
            files.append({"role": role, "path": path, "mime": mime, "meta": meta,
                          "stored": brand_kits.stored_name(data, mime), "bytes": len(data)})
    return {"name": name, "spec": spec, "files": files, "ignored": ignored,
            "licence": licence, "source": specs[0].name}


def _existing(name: str, account_id: Optional[int], dsn: Optional[str]) -> Optional[dict]:
    for kit in brand_kits.list_kits(dsn, account_id=account_id):
        if kit["name"].casefold() == name.casefold():
            return kit
    return None


def plan(found: dict, existing: Optional[dict]) -> list[dict]:
    """Each file with what --write would do to it: add, replace, or skip
    (the kit already holds those exact bytes in that role)."""
    held = {(a["role"], a["stored"]) for a in (existing or {}).get("assets") or []}
    refs_held = sum(1 for a in (existing or {}).get("assets") or [] if a["role"] == "reference")
    out, new_refs = [], 0
    for f in found["files"]:
        if (f["role"], f["stored"]) in held:
            action = "skip"
        elif f["role"] == "reference":
            action = "add"
            new_refs += 1
        else:
            single = any(a["role"] == f["role"] for a in (existing or {}).get("assets") or [])
            action = "replace" if single else "add"
        out.append({**f, "action": action})
    keep = brand_kits.ASSET_ROLES["reference"][3]
    if refs_held + new_refs > keep:
        raise FolderError(f"the kit already holds {refs_held} look references and the folder "
                           f"adds {new_refs}: a kit keeps {keep}. Remove some on the kit page first")
    return out


def where_of(dsn: str) -> str:
    """Host, database and schema of a DSN -- never its user or password."""
    try:
        info = conninfo_to_dict(dsn)
    except Exception:                       # noqa: BLE001
        return "(unreadable DSN)"
    schema = ""
    if "search_path=" in (info.get("options") or ""):
        schema = " schema " + info["options"].split("search_path=", 1)[1].split()[0]
    return f"{info.get('host') or 'localhost'}/{info.get('dbname') or ''}{schema}"


def run(folder, account: Optional[str], *, write: bool = False,
        dsn: Optional[str] = None, out=sys.stdout) -> dict:
    found = read_folder(Path(folder))
    account_id = accounts.resolve_account(account, dsn)
    existing = _existing(found["name"], account_id, dsn)
    steps = plan(found, existing)

    def say(line=""):
        print(line, file=out)

    say(f"database: {where_of(db.resolve_dsn(dsn))}; account {account or '(oldest)'} = {account_id}")
    say(f"files reach the bucket: {'yes' if storage.configured() else 'NO (R2 not configured)'}")
    say(f"kit: {found['name']!r} from {found['source']} -- "
        + (f"UPDATE kit {existing['id']}" if existing else "CREATE"))
    palette = found["spec"]["palette"]
    say(f"palette: {len(palette)} roles -- "
        + ", ".join(f"{s['role']} {s['hex']}" for s in palette))
    say(f"files: {len(steps)}")
    for s in steps:
        extra = f" ({s['meta']['family']})" if s["meta"].get("family") else ""
        say(f"  {s['action']:<7} {s['role']:<18} {s['path'].name}{extra}")
    for name in found["ignored"]:
        say(f"  ignored            {name} (not a role this importer knows)")
    if found["licence"]:
        say(f"font licence: {found['licence']}")
    if "[CONFIRM" in json.dumps(found["spec"]):
        say("note: the spec still holds a [CONFIRM ...] placeholder")

    result = {"account_id": account_id, "kit_id": existing["id"] if existing else None,
              "created": False, "files": steps, "written": False}
    if not write:
        say("report only -- nothing written. Re-run with --write to apply.")
        return result

    if existing:
        kit = brand_kits.update(existing["id"], dsn, account_id=account_id,
                                spec=found["spec"])
    else:
        kit = brand_kits.create(found["name"], found["spec"], dsn, account_id=account_id)
        result["created"] = True
    result["kit_id"] = kit["id"]
    for s in steps:
        if s["action"] == "skip":
            continue
        brand_kits.add_asset(kit["id"], s["role"], s["path"].read_bytes(), dsn,
                             account_id=account_id, filename=s["path"].name,
                             licensed=s["role"] in brand_kits.FONT_ROLES,
                             licence=found["licence"])
    result["written"] = True
    kit = brand_kits.get(kit["id"], dsn, account_id=account_id)
    say(f"written: kit {kit['id']} {kit['name']!r} now holds {len(kit['assets'])} files")
    if storage.configured():
        from src import media
        missing = [a["stored"] for a in kit["assets"]
                   if not storage.key_exists(media.object_key(a["stored"].lstrip("/"),
                                                              account_id))]
        say("bucket: every file is there" if not missing
            else f"bucket: MISSING {len(missing)} -- {', '.join(missing)}")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Load a brand kit folder into an account.")
    ap.add_argument("folder")
    ap.add_argument("--account", help="account slug (default: the oldest)")
    ap.add_argument("--write", action="store_true",
                    help="actually write; without it this only reports")
    args = ap.parse_args(argv)
    try:
        run(args.folder, args.account, write=args.write)
    except (FolderError, brand_kits.KitError, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
