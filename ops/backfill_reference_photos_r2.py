#!/usr/bin/env python3
"""Push the reference photos on this machine's disk up to R2, under the
keys the studio READS on the media rung this machine is on. Safe to
re-run: it sends every photo again and skips nothing, so a file
replaced under the same name on disk replaces the object.

characters/, props/, locations/ and data/refs/ are gitignored AND
dockerignored, so a photo saved on this machine never reaches the
deployed Fly site's own disk; R2 gives it one real address every
machine can load (2026-09-08, Mike). The app's own upload routes mirror
as they save -- this is for a photo dropped into a folder BY HAND, and
for the backlog.

WHERE A PHOTO GOES DEPENDS ON THE RUNG (`ZEROPAGE_MEDIA`, src/media.py):

  legacy   the flat keys, as this script has written them since
           2026-09-08: `characters/<slug>/<file>`, `refs/<file>`. Every
           file in the folders, no derivative, nothing read from the
           database, and a bare run uploads. UNCHANGED, byte for byte:
           it is `_flat` below, which is the old `main`.

  tenant   the keys carry the account, so the three element folders
  signed   need an OWNER, and a folder on disk does not say whose it
           is. The owner is the one account this machine names in
           ZEROPAGE_FOLDER_ACCOUNT (a slug or an id) -- the answer every
           reader in the studio is given (asset_shelf.folder_is_store).
           Each photo goes up through media.mirror, THE mirror, so it
           lands at `m/<account>/characters/<slug>/<file>` with its
           480px derivative under `t/`: where the listing looks
           (asset_shelf.r2_photo_urls). data/refs/ is the shared bin and
           needs no owner: `m/shared/refs/<file>`.

           Until 2026-10-11 this script wrote the flat keys on every
           rung, so on `tenant` a hand-dropped photo landed where
           nothing per-account looked and reached the account's keys
           only through a second pass, `ops.migrate_media_keys --write`.

           A machine that names NO folder account is refused the
           element folders, with the reason. An owner is never guessed:
           not the oldest account, not the only one. The bin still goes
           up, and the run exits non-zero so nobody reads it as a
           finished pass.

           It REPORTS FIRST here, because a write now names an owner and
           the wrong one is a photo handed to the wrong studio:

    venv/bin/python ops/backfill_reference_photos_r2.py            # report
    venv/bin/python ops/backfill_reference_photos_r2.py --write

Run from the project root, after R2_ACCOUNT_ID / R2_ACCESS_KEY_ID /
R2_SECRET_ACCESS_KEY / R2_BUCKET / R2_PUBLIC_BASE_URL are all set in
.env -- see ops/r2-setup.md. On `legacy` it reads nothing from the
database, just walks the folders. From `tenant` up it reads the
accounts table, for the folder account's row and nothing else (the id
behind a slug, the slug behind an id), so DATABASE_URL has to reach the
database that account lives in. This script loads .env itself, which
`python -m src.accounts` does not. No key, token, signed address or
connection string is printed: what a per-account run prints is KEYS.
"""
import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv  # noqa: E402, I001

load_dotenv()

from src import asset_shelf, media, refbin, storage  # noqa: E402

# How many not-yet-uploaded keys a report names before it says "and N more".
REPORT_KEYS = 20

# Exit codes. 1 and 2 are the ones this script has always had.
NOT_CONFIGURED, FAILED, REFUSED = 1, 2, 3


class Refused(Exception):
    """The element folders have no owner this script may write under."""


def _flat() -> int:
    """The `legacy` pass: every file, flat keys, no derivative. This is
    the body `main` had before the rungs differed; do not tidy it."""
    total = uploaded = failed = 0

    # data/refs/ first: composer uploads and every image the scout has
    # ever downloaded. Same problem as the asset folders (gitignored,
    # dockerignored) plus one more -- data/ on Fly is a fresh volume, so
    # even a deploy that shipped the folder would start empty. refbin
    # mirrors new ones at save time; this is the backlog.
    if refbin.REFS_DIR.is_dir():
        for photo in sorted(p for p in refbin.REFS_DIR.iterdir() if p.is_file()):
            total += 1
            key = f"refs/{photo.name}"
            try:
                url = storage.upload_file(photo, key=key,
                                          content_type="image/jpeg")
                uploaded += 1
                print(f"  OK   {key} -> {url}")
            except Exception as e:
                failed += 1
                print(f"  FAIL {key}: {type(e).__name__}: {e}")

    for plural, directory in asset_shelf.photo_roots().items():
        if not directory.is_dir():
            continue
        for slug_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
            for photo in sorted(p for p in slug_dir.iterdir() if p.is_file()):
                total += 1
                key = f"{plural}/{slug_dir.name}/{photo.name}"
                try:
                    url = storage.upload_file(photo, key=key,
                                              content_type="image/jpeg")
                    uploaded += 1
                    print(f"  OK   {key} -> {url}")
                except Exception as e:
                    failed += 1
                    print(f"  FAIL {key}: {type(e).__name__}: {e}")

    print(f"\n{uploaded}/{total} photos uploaded" + (f", {failed} failed" if failed else ""))
    return 0 if failed == 0 else FAILED


# --------------------------------------------------------------------------
# tenant / signed: the keys carry the account
# --------------------------------------------------------------------------

def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def _is_photo(path) -> bool:
    from src.locations import IMAGE_EXTENSIONS
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def _element_photos() -> tuple:
    """Every photo under the three element folders as (tail, path), in
    the order the flat pass walks them, and how many other files were
    passed over.

    A photo here is what the studio's own listing accepts back out of
    the bucket (an image extension, directly under the slug), so a
    .DS_Store or a notes file is not sent to sit under an account's keys
    where nothing would ever list it. The flat pass sends them; that is
    its behaviour and it is left alone."""
    found, other = [], 0
    for plural, directory in asset_shelf.photo_roots().items():
        if not directory.is_dir():
            continue
        for slug_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
            for path in sorted(p for p in slug_dir.iterdir() if p.is_file()):
                if _is_photo(path):
                    found.append((f"{plural}/{slug_dir.name}/{path.name}", path))
                else:
                    other += 1
    return found, other


def _bin_photos() -> list:
    """data/refs/ as (tail, path): composer uploads and scouted images."""
    if not refbin.REFS_DIR.is_dir():
        return []
    return [(f"refs/{path.name}", path)
            for path in sorted(refbin.REFS_DIR.iterdir()) if _is_photo(path)]


def _folder_owner() -> tuple:
    """(account_id, slug) of the account this machine's element folders
    belong to, or Refused with the reason.

    The machine names it (ZEROPAGE_FOLDER_ACCOUNT); this only looks the
    name up, and then asks asset_shelf.folder_is_store -- the ONE rule
    the studio's readers ask -- whether that account really is the one
    the folders are read as. A name the studio would not match (a slug
    in another case) is refused: the writer and the readers would
    disagree about whose these folders are.

    A database error is reported by its type alone (`_why`): its text
    can quote part of a connection string."""
    from src import accounts

    env = asset_shelf.FOLDER_ACCOUNT_ENV
    named = asset_shelf.folder_account()
    if not named:
        raise Refused(f"this machine names no folder account ({env} is unset)")
    asked = ("the database DATABASE_URL names" if os.environ.get("DATABASE_URL")
             else "the local default database (DATABASE_URL is not set)")
    try:
        if named.isdigit():
            account_id = int(named)
        else:
            # never called with an empty slug: that is its "oldest
            # account" fallback, which here would be guessing an owner
            account_id = accounts.resolve_account(named)
    except ValueError as e:                 # "no account 'x' -- try one of [...]"
        raise Refused(f"{env}={named}: {e}. Asked of {asked}") from None
    except Exception as e:                              # noqa: BLE001
        raise Refused(f"{env}={named} could not be looked up: {asked} did not "
                      f"answer ({_why(e)})") from None
    slug = accounts.slug_of(account_id)
    if slug is None:
        raise Refused(f"{env}={named} names no account that could be read from {asked}")
    if not asset_shelf.folder_is_store(account_id):
        raise Refused(f"{env}={named} is not how the studio would read it: account "
                      f"{account_id} is {slug!r}, and the name is matched exactly")
    return account_id, slug


def _why(e: Exception) -> str:
    """An error's type, and the service's own code when it carries one
    (botocore's AccessDenied, NoSuchBucket). Never its text: a driver's
    or a client's message can quote the address or the name it was
    given, and nothing this pass prints may be a credential."""
    response = getattr(e, "response", None)
    code = (response.get("Error") or {}).get("Code") if isinstance(response, dict) else None
    return type(e).__name__ + (f": {code}" if code else "")


def _in_bucket(prefixes) -> Optional[set]:
    """The keys already under these prefixes, or None when the bucket
    could not be listed. A report still stands without it; it just
    cannot say which photos are new."""
    try:
        return {key for prefix in prefixes for key in storage.list_keys(prefix)}
    except Exception as e:                              # noqa: BLE001
        print(f"note: the bucket could not be listed ({_why(e)})", file=sys.stderr)
        return None


def _per_account(write: bool) -> int:
    """The `tenant` / `signed` pass. A report unless `write`."""
    elements, other = _element_photos()
    owner = refusal = None
    if elements:                    # nothing to own, nobody to look up
        try:
            owner = _folder_owner()
        except Refused as why:
            refusal = str(why)

    # (tail, path, account). The bin first, as the flat pass has it.
    work = [(tail, path, None) for tail, path in _bin_photos()]
    if owner:
        work += [(tail, path, owner[0]) for tail, path in elements]

    print(f"Media rung: {media.mode()} -- a key carries its account "
          f"({media.MASTER_PREFIX}/<account>/...).")
    if owner:
        print(f"The element folders on this machine belong to account {owner[0]} "
              f"({owner[1]}), by {asset_shelf.FOLDER_ACCOUNT_ENV}.")
    if refusal:
        print(f"\nREFUSED  the element folders: {_count(len(elements), 'photo')} under "
              f"{', '.join(f'{p}/' for p in asset_shelf.photo_roots())}.\n"
              f"  {refusal}.\n"
              "  A folder on disk does not say whose it is, and an owner is not "
              "guessed. Name it in .env --\n"
              f"  {asset_shelf.FOLDER_ACCOUNT_ENV}=<the account's slug or id> -- "
              "and run this again (ops/r2-setup.md,\n"
              "  \"Whose the element folders are\"). Nothing under those folders "
              f"{'was' if write else 'would be'} uploaded.\n")

    code = REFUSED if refusal else 0
    if not owner:
        other = 0                   # the folders are not being sent at all
    if not write:
        _report(work, other)
        return code

    total = uploaded = failed = 0
    sent = []
    for tail, path, account_id in work:
        total += 1
        key = media.object_key(tail, account_id)
        if media.mirror(path, tail, account_id):
            uploaded += 1
            sent.append((tail, account_id))
            print(f"  OK   {key}")
        else:
            failed += 1
            print(f"  FAIL {key}  (media.mirror's note on stderr says why)")

    print(f"\n{uploaded}/{total} photos uploaded" + (f", {failed} failed" if failed else ""))
    _derivatives(sent)
    if other:
        print(f"{_count(other, 'other file')} in the element folders: not a photo, left.")
    if refusal:
        print("The element folders were NOT uploaded -- see REFUSED above.")
    return FAILED if failed else code


def _prefix(tail: str, account_id, *, thumb: bool = False) -> str:
    """The key prefix one root's photos land under, m/<scope>/<root>/,
    or its derivatives', t/<scope>/<root>/. One listing per root."""
    root = tail.split("/")[0] + "/"
    if thumb:
        return media.thumb_key_for_tail(root, account_id)
    return media.object_key(root, account_id)


def _report(work: list, other: int) -> None:
    """What a --write run would send, and where. Uploads nothing."""
    groups: dict = {}
    for tail, _path, account_id in work:
        groups.setdefault(_prefix(tail, account_id), []).append(
            media.object_key(tail, account_id))
    existing = _in_bucket(sorted(groups)) if groups else set()

    fresh = []
    print("Would upload, by where it lands:")
    for prefix, keys in groups.items():
        line = f"  {len(keys):>5}  {prefix}"
        if existing is not None:
            new = [k for k in keys if k not in existing]
            fresh += new
            line += f"   ({len(new)} not in the bucket yet)"
        print(line)
    for key in fresh[:REPORT_KEYS]:
        print(f"    new  {key}")
    if len(fresh) > REPORT_KEYS:
        print(f"    ... and {len(fresh) - REPORT_KEYS} more")

    print(f"\n{_count(len(work), 'photo')} to send"
          + ("" if existing is None else f", {len(fresh)} not in the bucket yet"))
    if other:
        print(f"{_count(other, 'other file')} in the element folders: not a photo, left.")
    print("report only -- re-run with --write to upload. Every photo is sent "
          "again, with its 480px derivative,\nnot only the new ones.")


def _derivatives(sent: list) -> None:
    """Say which uploads have no 480px derivative. media.mirror makes
    one beside every master and never fails the master for it, so a
    photo it could not decode (a HEIC with no pillow-heif) goes up alone
    and silently: its card then falls back to the full-size photo."""
    if not sent:
        return
    thumbs = {media.thumb_key_for_tail(tail, account_id): tail
              for tail, account_id in sent}
    existing = _in_bucket(sorted({_prefix(tail, account_id, thumb=True)
                                  for tail, account_id in sent}))
    if existing is None:
        return
    missing = sorted(key for key in thumbs if key not in existing)
    print(f"{len(thumbs) - len(missing)}/{len(thumbs)} have a 480px derivative "
          f"under {media.THUMB_PREFIX}/")
    for key in missing[:REPORT_KEYS]:
        print(f"    none for  {thumbs[key]}")
    if len(missing) > REPORT_KEYS:
        print(f"    ... and {len(missing) - REPORT_KEYS} more")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Push the reference photos on this machine's disk up to "
                    "R2, under the keys the media rung reads.")
    parser.add_argument("--write", action="store_true",
                        help="from `tenant` up: actually upload (the default "
                             "there is a report). On `legacy` a run always "
                             "uploads, as it always has")
    args = parser.parse_args(argv)

    if not storage.configured():
        print("R2 is not configured (see ops/r2-setup.md) -- nothing to do.")
        return NOT_CONFIGURED

    if not media.tenant_keys():
        return _flat()
    return _per_account(args.write)


if __name__ == "__main__":
    raise SystemExit(main())
