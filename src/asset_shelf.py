"""
The RAG library's `assets` shelf: every location, character, and prop
you have, as retrievable text.

The library is text-only -- `gemini-embedding-001` embeds strings and
`rag_documents` stores a `chunk` column -- so a reference photo cannot
itself be a row. What makes an asset searchable is its *description*,
which is why locations have always been described by vision on upload
and why characters and props are now too (`locations.describe_entity`).
Without that, the only retrievable thing about a character is the name
someone typed, never how they look.

One module owns the shelf so the upload path (app/api.py) and the
backfill below write byte-identical chunks under identical source keys
-- two formats on one shelf would mean re-ingesting an asset created
the other way silently duplicates it rather than replacing it.

Everything here is best-effort by the project's standing contract: the
asset's own save must never be lost because the vector store is down.
"""
from pathlib import Path
from typing import Optional

from . import entities, preprod, rag

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCATIONS_DIR = PROJECT_ROOT / "locations"
CHARACTERS_DIR = PROJECT_ROOT / "characters"
PROPS_DIR = PROJECT_ROOT / "props"

DOMAIN = "assets"
KINDS = ("location", "character", "prop")

PHOTO_DIRS = {
    "location": LOCATIONS_DIR,
    "character": CHARACTERS_DIR,
    "prop": PROPS_DIR,
}

# The description keys worth putting on the shelf, in reading order.
# Locations and entities have different shapes; both flatten the same way.
DESCRIPTION_KEYS = (
    "space", "look", "light_sources", "textures", "angles", "constraints",
    "features", "materials", "continuity", "notes",
)


def source_key(kind: str, slug: str, account_id: Optional[int] = None) -> str:
    """`assets/a7/character-mike`. Stable per asset, so re-saving replaces
    that asset's chunks instead of accumulating stale copies (see
    rag.ingest_records, which deletes by source first).

    THE ACCOUNT IS IN THE KEY (2026-10-11, docs/BACKLOG.md #25). It was
    `assets/character-mike` for everybody, so the second account to name
    a character "Me" REPLACED the first one's description on the shelf,
    and either of them deleting theirs dropped the other's. With no
    account (the CLI, the backfill run as nobody) it is the old flat key
    unchanged -- `a<None>` would be a shared namespace wearing a
    misleading name, media.object_key's reasoning exactly."""
    if account_id is None:
        return f"{DOMAIN}/{kind}-{slug}"
    return f"{DOMAIN}/a{int(account_id)}/{kind}-{slug}"


def _retire_flat_chunk(conn, kind: str, slug: str, project: Optional[str]) -> None:
    """Drop the element's chunk under the OLD flat key -- only when it is
    labelled as this tenant's own. A chunk written before the account was
    in the key would otherwise sit beside the new one and be retrieved
    twice; one labelled for another tenant, or not labelled at all, is
    not this caller's to remove."""
    if not project:
        return
    try:
        conn.execute("DELETE FROM rag_documents WHERE source = %s AND project = %s",
                     (source_key(kind, slug), project))
        conn.commit()
    except Exception:                                   # noqa: BLE001
        # a tidy-up: the chunk under the account's own key is what counts
        try:
            conn.rollback()
        except Exception:                               # noqa: BLE001
            pass


def slugify(name: str) -> str:
    """A name becomes a directory name -- the same rule app/main.py's
    safe_space_name applies on the way in."""
    import re
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", name or "").strip().replace(" ", "-").lower()
    return cleaned.strip("-.")


def flatten_description(desc) -> str:
    """A description dict (either shape) -> one readable line. Unknown
    keys ride along after the known ones so a future vision field isn't
    silently dropped from the shelf."""
    import json as _json
    if isinstance(desc, str):
        try:
            desc = _json.loads(desc)
        except (ValueError, TypeError):
            return desc.strip()
    if not isinstance(desc, dict):
        return ""
    parts = []
    seen = set()
    for key in DESCRIPTION_KEYS:
        if key in desc:
            seen.add(key)
            value = desc[key]
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            if value:
                parts.append(f"{key.replace('_', ' ')}: {value}")
    for key, value in desc.items():
        if key in seen:
            continue
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        if value:
            parts.append(f"{key.replace('_', ' ')}: {value}")
    return " · ".join(parts)


def chunk_text(kind: str, name: str, fields: dict) -> str:
    """The exact text stored for one asset. Both writers call this."""
    lines = [f"{kind.upper()}: {name}"]
    for label, value in fields.items():
        text = flatten_description(value) if isinstance(value, dict) else (
            "" if value is None else str(value).strip())
        if text:
            lines.append(f"{label}: {text}")
    return "\n".join(lines)


def ingest_one(kind: str, slug: str, name: str, fields: dict, *,
               project: Optional[str] = None,
               account_id: Optional[int] = None) -> dict:
    """Write one asset's chunk. Never raises -- a down store returns
    {"ok": False} so the caller can report it and move on. `project` is
    the owner's tenant slug (rag.py: the label that ranks a tenant's own
    assets first without hiding anyone's). `account_id` is whose element
    it is: it goes in the source key, so two accounts' same-named
    elements are two chunks and neither save replaces the other's."""
    text = chunk_text(kind, name, fields)
    try:
        conn = rag.connect()
        try:
            rag.init_store(conn)
            written = rag.ingest_records(
                [{"source": source_key(kind, slug, account_id), "text": text,
                  "domain": DOMAIN, "project": project, "source_ref": None}],
                rag.make_client(), conn,
            )
            if account_id is not None:
                _retire_flat_chunk(conn, kind, slug, project)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return {"ok": True, "chunks": written, "error": None}
    except Exception as e:
        return {"ok": False, "chunks": 0, "error": str(e)}


def drop_one(kind: str, slug: str, *, account_id: Optional[int] = None,
             project: Optional[str] = None) -> None:
    """Deleting an asset drops its chunk too -- best-effort, same
    contract as the ingest above. With an account it drops THAT
    account's chunk, plus the old flat-keyed one only where it is
    labelled as the same tenant's: one account's delete must never take
    another's same-named element off the shelf."""
    try:
        conn = rag.connect()
        try:
            rag.delete_source(conn, source_key(kind, slug, account_id))
            if account_id is not None:
                _retire_flat_chunk(conn, kind, slug, project)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass


def photos_for(kind: str, slug: str) -> list:
    """The asset's photos on disk, newest-name-order, or []."""
    from .locations import IMAGE_EXTENSIONS
    directory = PHOTO_DIRS[kind] / slug
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def r2_photo_urls(kind: str, slug: str,
                  account_id: Optional[int] = None) -> list[str]:
    """The asset's photos as listed in the BUCKET -- the catalogue's
    answer on a machine that has no photo folder.

    2026-09-15: GET /api/assets on the deployed API answered photos: []
    for every character, location and prop, so the studio's composer
    and Elements page could attach none of them. photos_for() reads the
    folder, and characters/ props/ locations/ are gitignored AND
    dockerignored -- the bytes were in R2 and nothing looked.

    REWORKED 2026-09-18 for the media ladder (src/media.py), which
    landed between this being written and being merged. Two things the
    first version got wrong for anything above the `legacy` rung:

    - WHERE it looked. It listed the flat `characters/<slug>/`. From
      `tenant` up the masters live at `m/<account>/characters/<slug>/`,
      and the flat keys are the very thing the ladder exists to leave:
      one key for every account, so the second studio with a character
      called `michael` would have been handed the first one's face. The
      prefix is built by media.object_key -- THE writer-side key builder
      -- so the listing looks exactly where the mirror wrote, per
      account, and is the flat key unchanged on `legacy` or for a caller
      with no account.
    - WHAT it returned. It returned the raw public URL. Every other
      writer returns photo_url(): the public URL on `legacy`, the local
      route (the logical name) from `tenant` up, minted into something
      fetchable on READ by media.url_for. A listing that handed out a
      different string shape would have put URLs on rows that every
      other path treats as names.

    Filtered to what photos_for() would accept off disk (IMAGE_
    EXTENSIONS, files directly under the slug) and sorted by filename so
    the two listings agree on order -- refs[0] is the frame a clip
    anchors on. [] when R2 is off."""
    from . import media, storage
    from .locations import IMAGE_EXTENSIONS

    if not storage.configured():
        return []
    plural = next(k for k, v in URL_ROOTS.items() if v == kind)
    # one cached listing per (account, kind), not one per asset
    root = media.object_key(f"{plural}/", account_id)
    head = media.object_key(f"{plural}/{slug}/", account_id)
    names = set()
    for key in storage.keys_under(root):
        if not key.startswith(head):
            continue
        name = key[len(head):]
        if not name or "/" in name or Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        names.add(name)
    return [photo_url(kind, slug, n) for n in sheet_last(names)]


def sheet_last(names) -> list:
    """An element's photo names in listing order: by name, the drawn
    sheet LAST. `refs[0]` is the frame a clip anchors on, and a sheet is
    a derivative of the face, never evidence of it -- app/api.py's
    `_photo_names` rule, applied to every listing so the bucket's answer
    and the folder's agree."""
    def is_sheet(name) -> bool:
        return Path(str(name)).stem.lower() == "sheet"      # element_sheet.SHEET_STEM
    return sorted(names, key=lambda n: (is_sheet(n), str(n)))


def per_account_bucket() -> bool:
    """Is the bucket a per-account store on THIS machine: R2 configured
    and the media ladder on `tenant` or above (`m/<account>/...` keys).
    Never raises; False when unsure."""
    from . import media, storage
    try:
        return bool(storage.configured() and media.tenant_keys())
    except Exception:                                   # noqa: BLE001
        return False


def bucket_is_store(account_id: Optional[int]) -> bool:
    """Do this account's element photos live in the bucket under keys
    that are ITS OWN? True from the `tenant` rung up, with R2 configured
    and an account named.

    WHY ANYONE ASKS (2026-10-11, found building the connector's
    `add_element`). The photo folders on disk are named by slug alone:
    `characters/me/` is one folder for every account on the machine, and
    `photo_urls` below reads it first. On a machine with one studio that
    is exactly right. On the deployed one, two people who each name a
    character "Me" between two deploys share that folder, and each is
    listed the other's photo. The bucket has no such problem from
    `tenant` up (`m/<account>/characters/me/...`), so where this answers
    True a caller that must not mix accounts reads and writes the bucket
    and leaves the shared folder alone. Never raises; False when unsure."""
    return bool(account_id is not None and per_account_bucket())


# WHOSE THE FOLDERS ARE (2026-10-11, docs/BACKLOG.md #25, Mike's call).
#
# `characters/<slug>/`, `props/<slug>/` and `locations/<slug>/` carry no
# account, so on a machine with a per-account bucket they can belong to
# at most ONE account -- and the machine has to say which. That is this
# variable: the account's slug or its id, in the machine's own .env.
#
#   Mike's Mac    ZEROPAGE_FOLDER_ACCOUNT=zeropage. The folders are his:
#                 the photos he drops into characters/<slug>/ by hand are
#                 listed and read off disk first, exactly as before.
#   the deploy    unset. The folders are NOBODY's: every account, the
#                 operator's included, writes, lists and reads its own
#                 bucket keys, and nothing is kept in a folder two
#                 accounts would share by name.
#   no bucket     (no R2, or the `legacy` rung) the folder is the only
#                 store there is, for everybody, and nothing changed.
#
# Unset is the closed answer on purpose: a machine that forgot the line
# reads the bucket, which is slower and never somebody else's photo.
FOLDER_ACCOUNT_ENV = "ZEROPAGE_FOLDER_ACCOUNT"

_OWNER_TTL = 300.0
_OWNER_HITS: dict = {}


def folder_account() -> str:
    """The account this machine's element folders belong to, as the
    machine names it (a slug or an id), or ''."""
    import os
    return (os.environ.get(FOLDER_ACCOUNT_ENV) or "").strip()


def _is_folder_account(named: str, account_id: int) -> bool:
    """Is `account_id` the account `named`? An id is compared outright;
    a slug is looked up, and the answer kept for a few minutes (it is
    asked once per element per listing). Never raises: a slug that
    cannot be read is not a match, and is asked again next time."""
    import os
    import time
    if named.isdigit():
        return int(named) == int(account_id)
    key = (named, int(account_id), os.environ.get("DATABASE_URL") or "")
    hit = _OWNER_HITS.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < _OWNER_TTL:
        return hit[1]
    from . import accounts
    slug = accounts.slug_of(account_id)
    if slug is None:
        return False
    answer = slug == named
    _OWNER_HITS[key] = (now, answer)
    return answer


def folder_is_store(account_id: Optional[int] = None) -> bool:
    """Is the folder on THIS machine where this caller's element photos
    live? THE one rule every writer, listing and reader asks.

    True where there is no per-account bucket (the folder is the only
    store), and for the one account the machine names in
    ZEROPAGE_FOLDER_ACCOUNT. False for every other account, and for
    everybody on a machine that names nobody. A caller with no account
    (a CLI, the graph run as nobody) is the folder's on a machine that
    has an owner and nobody's on one that does not."""
    if not per_account_bucket():
        return True
    named = folder_account()
    if not named:
        return False
    if account_id is None:
        return True
    return _is_folder_account(named, account_id)


def photo_urls(kind: str, slug: str,
               account_id: Optional[int] = None) -> list[str]:
    """The asset's photo URLs, the drawn sheet last.

    Where the folder is this caller's store (`folder_is_store`): the
    folder first -- this machine's own photos, off its own disk -- and
    the account's bucket listing when the folder is absent or empty.
    Everywhere else the bucket listing under the account's OWN keys and
    nothing from the folder, which every account on the machine shares
    by name."""
    if folder_is_store(account_id):
        local = [photo_url(kind, slug, name)
                 for name in sheet_last(f.name for f in photos_for(kind, slug))]
        if local:
            return local
    return r2_photo_urls(kind, slug, account_id)


# The site-relative URL every reference in this pipeline travels as.
# `/characters/<slug>/photo/<file>`, `/props/...`, `/locations/...` for
# the asset bank, `/refs/<sha>.jpg` for anything the composer uploaded
# or the scout downloaded. One shape, so a photo picked by hand and a
# photo found by a crawl are indistinguishable downstream.
URL_ROOTS = {"characters": "character", "props": "prop", "locations": "location"}


def parse_ref(url: str) -> Optional[dict]:
    """Any reference URL this pipeline stores -> what it points at.

    THE one parser (2026-09-08). A reference used to travel in exactly
    one shape, so half a dozen callers each did
    `url.strip("/").split("/")` and read parts[0] as the kind:
    reference_label's caption binding, in_scope's picked assets,
    picked_locations' room lock, resolve_photo's wall. The moment
    photo_url started returning an R2 URL for the same photo, every one
    of those silently stopped matching -- `https://pub-x.r2.dev/...`
    splits with parts[0] == "https:" -- and each failure is quiet: a
    caption not written, a room not locked, a face not attached. So the
    shapes are read in ONE place and the callers ask for fields.

    Returns {"kind": "refs", "filename": ...} for a bin image, or
    {"kind": "character"|"prop"|"location", "plural", "slug",
    "filename"} for an asset photo. None for anything else -- a render
    URL, a data: URI, a path that climbs.
    """
    from urllib.parse import urlparse

    raw = (url or "").split("?")[0].strip()
    if not raw:
        return None
    if "://" in raw:
        raw = urlparse(raw).path
    parts = [p for p in raw.strip("/").split("/") if p]
    if not parts or any(p in (".", "..") for p in parts):
        return None
    # the local route carries a "photo" segment the R2 key does not
    if len(parts) == 4 and parts[2] == "photo":
        parts = [parts[0], parts[1], parts[3]]
    if len(parts) == 2 and parts[0] == "refs":
        return {"kind": "refs", "plural": "refs", "slug": "",
                "filename": parts[1]}
    if len(parts) == 3 and parts[0] in URL_ROOTS:
        return {"kind": URL_ROOTS[parts[0]], "plural": parts[0],
                "slug": parts[1], "filename": parts[2]}
    return None


def r2_key(url: str) -> Optional[str]:
    """The R2 key a reference URL's bytes live under -- the exact scheme
    photo_url() builds and ops/backfill_reference_photos_r2.py uploads.
    None for a URL with no key, and for one that is already absolute:
    canonicalising an R2 URL a second time is a no-op, not a nesting."""
    if (url or "").startswith(("http://", "https://", "data:")):
        return None
    ref = parse_ref(url)
    if not ref:
        return None
    if ref["kind"] == "refs":
        return f"refs/{ref['filename']}"
    return f"{ref['plural']}/{ref['slug']}/{ref['filename']}"


def logical_ref(url: str) -> str:
    """The site-relative NAME of a reference: `/refs/<sha>.jpg`,
    `/characters/<slug>/photo/<file>`. Unchanged for anything this
    pipeline does not own.

    This is the durable half of a reference. Every reference bug this
    repo has paid for came from storing a URL instead of a name -- a
    local route true only on the machine holding the folder
    (2026-09-08), and, the moment media is signed, a URL true only for
    the next hour. A name is true everywhere and forever; the URL is
    minted from it on read by `fetch_url`.
    """
    ref = parse_ref(url)
    if not ref:
        return url
    if ref["kind"] == "refs":
        return f"/refs/{ref['filename']}"
    return f"/{ref['plural']}/{ref['slug']}/photo/{ref['filename']}"


def storable_ref(url: str) -> str:
    """What goes ON a row.

    On the `legacy` rung this is the 2026-09-08 answer unchanged -- the
    public R2 URL, because a site-relative path 404s on the deployed
    site and a renderer there anchors on nothing while the card claims
    it anchored on a face. From `tenant` up it is the logical name
    instead, because the URL is no longer a constant: it carries the
    account and, under `signed`, an expiry.

    Both shapes are read by `parse_ref` and minted by `fetch_url`, so a
    row written under either rung keeps working under the other. That is
    the whole reason the ladder is safe to climb and to climb back down.
    """
    from . import media
    if media.tenant_keys():
        return logical_ref(url)
    return canonical_url(url)


def fetch_url(url: str, account_id: Optional[int] = None) -> str:
    """What a browser, a renderer, or a server-side fetch should ask
    for. The read-time mint -- see src/media.url_for."""
    from . import media
    return media.url_for(url, account_id)


def canonical_url(url: str) -> str:
    """The form of a reference URL that is true on EVERY machine.

    A stored `/characters/michael/photo/x.jpg` is only true where that
    folder is -- characters/, props/, locations/ and data/refs/ are all
    gitignored and dockerignored, so the deployed site 404s every one of
    them (2026-09-08, Mike: "the reference photos aren't appearing" --
    four empty tiles on a Queue card whose shot carried four refs). What
    goes ON a shot is therefore the public R2 URL when R2 is on, since
    that is the same string on his Mac, on Fly, and in a renderer's
    fetch. Unchanged when R2 is off, so a local-only setup keeps working.

    The bytes must already BE in R2; this is a string map, not an upload.
    Callers that write a NEW file (refbin.save, the upload handlers) push
    it up first.

    Still THE writer for the `legacy` rung, and still what
    ops/canonicalize_shot_refs.py applies. New callers want
    `storable_ref`, which picks this or `logical_ref` by the rung.
    """
    key = r2_key(url)
    if not key:
        return url
    from . import storage
    return storage.url_for_key(key) or url


def photo_url(kind: str, slug: str, filename: str) -> str:
    """The URL a photo on disk rides on. The inverse of resolve_photo.

    2026-09-08 (Mike, "images don't load on the deployed site"): a
    reference photo saved on one machine (usually his Mac) never
    reaches the Fly deploy's own disk -- characters/props/locations are
    both gitignored and dockerignored, and there's no volume for them.
    When R2 is configured, every photo is pushed there by the upload
    handlers (app/api.py) or a one-off backfill (ops/backfill_reference_
    photos_r2.py), so the URL a photo rides on can just be the public R2
    URL directly -- true on every machine, not just the one that saved
    it. Falls back to the local `/characters/.../photo/...` route (still
    served by app/main.py) when R2 isn't set, so nothing breaks for a
    local dev setup that never turns R2 on.

    From the `tenant` rung up it returns the LOCAL route again -- not a
    regression, the opposite: the key now carries an account and the URL
    may carry an expiry, so neither can be baked into a string that gets
    stored and read back months later. `fetch_url` mints the real one at
    the moment of reading. See src/media.py.
    """
    plural = next(k for k, v in URL_ROOTS.items() if v == kind)
    from . import media, storage
    if media.tenant_keys():
        return f"/{plural}/{slug}/photo/{filename}"
    r2_url = storage.url_for_key(f"{plural}/{slug}/{filename}")
    if r2_url:
        return r2_url
    return f"/{plural}/{slug}/photo/{filename}"


def photo_roots() -> dict:
    """The URL prefix -> directory map, by the plural names the URLs use."""
    return {plural: PHOTO_DIRS[kind] for plural, kind in URL_ROOTS.items()}


def resolve_photo(url_path: str, roots=None, refs_dir=None):
    """A reference URL -> the file on disk, or None.

    THE reason this lives in src/: the nightly graph resolves references
    at 6am with no web app running, so it cannot call app/api.py's
    version. That one now delegates here, because two implementations of
    a path-traversal guard is the shape of bug where one of them is
    weaker and nobody notices.

    Handles both shapes, and refuses anything that escapes its root --
    the URL comes off a stored shot or a crawl, so nothing has vouched
    for it. None on anything unresolvable: a reference is an
    enhancement, never a gate.

    `roots` and `refs_dir` are injectable so the WALL has one
    implementation while the directories stay the caller's: app/api.py
    passes its own `_PHOTO_ROOTS`, which is what the tests point at a
    tmp_path. Defaulting them here is what lets the graph resolve a
    reference at 6am with no app around.

    THIS READER NAMES NO ACCOUNT (2026-10-11), so it opens an element
    folder only on a machine where the folder is somebody's
    (`folder_is_store()`): with no per-account bucket, or where the
    machine names its owner. On the deployed API the folders are
    nobody's and an element photo resolves to None here -- a caller that
    knows whose photo it wants asks `resolver(account_id)`, which reads
    that account's own bucket keys. The bin (`/refs/...`) is shared by
    decision (src/media.py) and resolves as it always did.
    """
    ref = parse_ref(url_path)
    if ref and ref["kind"] != "refs" and not folder_is_store():
        return None
    return _disk_photo(url_path, roots, refs_dir)


def _disk_photo(url_path: str, roots=None, refs_dir=None):
    """The file a reference URL names on this machine's disk, behind the
    wall, or None. No question of whose it is -- `resolve_photo` and
    `resolver` decide that before they ask."""
    from . import refbin

    roots = roots if roots is not None else photo_roots()
    refs_root = refs_dir if refs_dir is not None else refbin.REFS_DIR
    # The shape comes from parse_ref, which reads the local route AND
    # the public R2 URL of the same photo (2026-09-08) -- a canonicalised
    # ref should still resolve to the file on the machine that HAS it,
    # rather than making his own Mac fetch its own photos over the
    # network. The wall below is unchanged and stays here: parse_ref
    # says what a URL means, this says what it is allowed to reach.
    ref = parse_ref(url_path)
    if not ref:
        return None

    # /refs/<sha>.jpg -- composer uploads and scouted research images
    if ref["kind"] == "refs":
        root = Path(refs_root).resolve()
        target = (root / ref["filename"]).resolve()
        if target.parent != root or not target.is_file():
            return None
        return target

    # /<characters|props|locations>/<slug>/photo/<file>
    base = roots.get(ref["plural"])
    if base is None:
        return None
    root = Path(base).resolve()
    target = (root / ref["slug"] / ref["filename"]).resolve()
    if root not in target.parents or not target.is_file():
        return None
    return target


# AN ACCOUNT'S OWN COPY, OUT OF THE BUCKET (2026-10-11).
#
# Until today every server-side reader of a reference read this
# machine's disk and nothing else. Measured that day with a faked bucket
# on the `tenant` rung and no file on disk: app/api.py's `_photo_bytes`,
# the keyframe stage's reader and fal's reference upload each returned
# nothing for an element photo that was in the account's bucket -- so
# such a photo was listed, stored on the shot and drawn by the browser,
# and the scene writer, the keyframe and the renderer were not handed
# it. (Not observed on the live API; the deployed machine holds no
# element folder after a restart, which is that case.) Now that an
# account's store is the bucket wherever the bucket is per-account, the
# readers have to be able to read it.
#
# The bytes land in a per-process scratch directory, under the ACCOUNT's
# own subfolder -- two accounts' `characters/me/photo.jpg` are two files
# -- and are fetched again after PHOTO_CACHE_TTL, because a key can be
# written twice (a sheet redrawn, a photo uploaded again under its name).
# A write from this process drops its cached copy at once (`forget_cached`).
PHOTO_CACHE_TTL = 600.0
PHOTO_BYTES_MAX = 15 * 1024 * 1024      # element_sheet's bound on one photo
# ...and it does not grow without end: a copy nobody has fetched for an
# hour is removed, looked for once every PHOTO_CACHE_SWEEP_EVERY writes.
# The deployed machine's disk is small and a photo can be 15 MB.
PHOTO_CACHE_KEEP = 3600.0
PHOTO_CACHE_SWEEP_EVERY = 32

_PHOTO_CACHE: Optional[Path] = None
_PHOTO_WRITES = 0


def _photo_cache() -> Path:
    global _PHOTO_CACHE
    if _PHOTO_CACHE is None or not _PHOTO_CACHE.is_dir():
        import tempfile
        _PHOTO_CACHE = Path(tempfile.mkdtemp(prefix="zp-element-photos-"))
    return _PHOTO_CACHE


def _cached_path(tail: str, account_id: Optional[int]) -> Optional[Path]:
    scope = "nobody" if account_id is None else str(int(account_id))
    root = (_photo_cache() / scope).resolve()
    target = (root / tail).resolve()
    return target if root in target.parents else None


def _sweep_photo_cache(now: Optional[float] = None) -> int:
    """Remove cached copies older than PHOTO_CACHE_KEEP. Returns how
    many went. Never raises: a file somebody else just removed, or one
    being written, is simply left for the next sweep."""
    import time
    now = time.time() if now is None else now
    gone = 0
    try:
        for path in _photo_cache().rglob("*"):
            try:
                if path.is_file() and now - path.stat().st_mtime > PHOTO_CACHE_KEEP:
                    path.unlink()
                    gone += 1
            except OSError:
                continue
    except Exception:                                   # noqa: BLE001
        pass
    return gone


def _element_tail(url: str) -> Optional[str]:
    ref = parse_ref(url)
    if not ref or ref["kind"] == "refs":
        return None
    return f"{ref['plural']}/{ref['slug']}/{ref['filename']}"


def forget_cached(url: str, account_id: Optional[int]) -> None:
    """This process just wrote that photo to the bucket: the next read
    fetches the new bytes instead of a copy of the old ones."""
    try:
        tail = _element_tail(url)
        target = _cached_path(tail, account_id) if tail else None
        if target is not None:
            target.unlink(missing_ok=True)
    except Exception:                                   # noqa: BLE001
        pass


def own_photo_file(url: str, account_id: Optional[int] = None) -> Optional[Path]:
    """An element photo as a file, read from the bucket under the keys
    that are this ACCOUNT's (media.object_key) -- never from the element
    folder. None when R2 is off, the account has no such photo, or the
    read failed: a reference is an enhancement, never a gate."""
    import os
    import time

    from . import media, storage
    try:
        tail = _element_tail(url)
        if not tail or not storage.configured():
            return None
        target = _cached_path(tail, account_id)
        if target is None:
            return None
        if target.is_file() and time.time() - target.stat().st_mtime < PHOTO_CACHE_TTL:
            return target
        data = storage.read_key(media.object_key(tail, account_id), PHOTO_BYTES_MAX)
        if not data:
            # the bucket did not answer: an older copy of the account's
            # own photo is still the account's own photo
            return target if target.is_file() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        scratch = target.with_name(f".{target.name}.{os.getpid()}.{time.monotonic_ns()}")
        scratch.write_bytes(data)
        os.replace(scratch, target)
        global _PHOTO_WRITES
        _PHOTO_WRITES += 1
        if _PHOTO_WRITES % PHOTO_CACHE_SWEEP_EVERY == 0:
            _sweep_photo_cache()
        return target
    except Exception:                                   # noqa: BLE001
        return None


def resolver(account_id: Optional[int] = None, *, disk=None):
    """The `resolve_photo` a stage is handed, bound to WHOSE photos it
    may read: a callable, reference URL -> file or None.

    An element photo is read from the folder only where the folder is
    this account's store (`folder_is_store`), with the account's bucket
    copy behind it for a photo this machine does not hold. For every
    other account it is read from that account's own bucket keys and the
    folder is never opened -- the folder is named by slug alone, so
    `characters/me/photo.jpg` there may be somebody else's face. The bin
    (`/refs/...`) resolves as it always did.

    `disk` is the caller's own disk reader (app/api.py passes the one
    its tests point at a tmp_path); `resolve_photo` when not given."""
    read_disk = disk if disk is not None else resolve_photo

    def resolve(url_path: str):
        if _element_tail(url_path) is None:
            return read_disk(url_path)                  # the bin, or nothing
        if not folder_is_store(account_id):
            return own_photo_file(url_path, account_id)
        hit = read_disk(url_path)
        return hit if hit is not None else own_photo_file(url_path, account_id)

    return resolve


def catalogue(db_path=None, account_id: Optional[int] = None) -> list[dict]:
    """Every asset on file, in the shape shootgen.named_assets AND
    in_scope() read: {"category", "name", "photos", "text"}, photos as
    URLs and text as whatever notes/description asset_aliases can pull
    multi-word proper nouns out of.

    Same catalogue the Studio's media panel shows, built from src/ so
    the graph can have it too. Locations come from the locations table,
    characters and props from entities; the photos come off disk, since
    that is where they actually are -- photo_count on the row is a
    counter, not a listing. `text` mirrors app/api.py's _assets_all()
    field for field (notes/role/category, or a flattened location
    description) -- named_assets is written against that shape, and a
    catalogue that fed it a thinner one would silently lose every alias
    beyond a bare name.
    """
    from . import entities, preprod

    path = db_path
    items: list[dict] = []

    def photos(kind: str, name: str) -> list:
        return photo_urls(kind, slugify(name), account_id)

    for loc in preprod.list_locations(dsn=path, account_id=account_id):
        items.append({"category": "location", "name": loc["name"],
                      "photos": photos("location", loc["name"]),
                      "text": flatten_description(
                          loc.get("description") or loc.get("description_json") or "")})
    for c in entities.list_characters(dsn=path, account_id=account_id):
        items.append({"category": "character", "name": c["name"],
                      "photos": photos("character", c["name"]),
                      "text": c.get("notes") or c.get("role") or ""})
    for pr in entities.list_props(dsn=path, account_id=account_id):
        items.append({"category": "prop", "name": pr["name"],
                      "photos": photos("prop", pr["name"]),
                      "text": pr.get("notes") or pr.get("category") or ""})
    return items


def in_scope(text: str, refs, catalogue_items: list) -> list:
    """Which assets ONE generation is allowed to ground on: named in
    `text` (a typed idea/spark, or a spark rotated in with nobody
    typing), or explicitly picked -- a photo attached via `refs`, the
    same /<kind>/<slug>/photo/... URL shape a composer click, a / pick,
    or an upload all ride on. Nothing else is offered.

    Replaces the old default everywhere a generator was shown the WHOLE
    asset bank on every single run (shootgen.cast_for's unfiltered
    entities.list_characters/list_props, generate_scene_concept's
    cast=None meaning "everything", the old picked_locations-only gate
    on rooms). A Create run now stays only as wide as the idea actually
    calls for, or as wide as what was deliberately attached to it --
    2026-09-03, Mike's call: "I want every create call to ONLY use the
    idea/spark that is written and references attached."

    Order matches shootgen.named_assets (character, then prop, then
    location, then first mention) since named() already carries that
    ordering; explicitly picked assets NOT already named are appended
    after, so a named + picked duplicate isn't listed twice and the
    anchor-priority order named() computed is never disturbed by a pick
    that agrees with it.
    """
    from . import shootgen  # local: shootgen pulls in the heavier deps

    named = shootgen.named_assets(text or "", catalogue_items)
    picked_slugs = set()
    for ref in refs or []:
        parsed = parse_ref(str(ref))
        if parsed and parsed["kind"] != "refs":
            picked_slugs.add(parsed["slug"])
    if not picked_slugs:
        return named
    named_names = {a["name"] for a in named}
    picked = [a for a in catalogue_items
             if a["name"] not in named_names and slugify(a["name"]) in picked_slugs]
    return named + picked


def entity_fields(kind: str, row: dict) -> dict:
    """One character/prop row -> the labelled fields its chunk carries."""
    label = "role" if kind == "character" else "category"
    return {
        label: row.get(label) or "",
        "notes": row.get("notes") or "",
        "description": row.get("description") or {},
    }


def described(row: dict) -> bool:
    """Does this entity already carry a vision description (as opposed
    to only the notes someone typed)?"""
    desc = row.get("description") or {}
    return isinstance(desc, dict) and bool(desc.get("look"))


def backfill(db_path=None, describe: bool = False, gemini_client=None, account_id: Optional[int] = None) -> dict:
    """
    Put everything already on disk onto the shelf.

    `describe=True` additionally runs the vision step on any character
    or prop that has photos but no description yet -- that is a billed
    call per asset, which is why it is opt-in and why an already
    described asset is skipped rather than re-described.

    Never raises: per-asset failures are counted and reported so one
    bad photo can't lose the rest of the run.
    """
    path = db_path
    result = {"ingested": 0, "described": 0, "failed": 0,
              "skipped_no_photos": 0, "errors": []}
    from . import accounts
    project = accounts.slug_of(account_id, dsn=path)

    def record_error(what: str, error: str) -> None:
        result["failed"] += 1
        if len(result["errors"]) < 10:
            result["errors"].append(f"{what}: {error}")

    for loc in preprod.list_locations(dsn=path, account_id=account_id):
        name = loc["name"]
        outcome = ingest_one("location", slugify(name), name,
                             {"description": loc.get("description") or {}},
                             project=project, account_id=account_id)
        if outcome["ok"]:
            result["ingested"] += 1
        else:
            record_error(f"location {name}", outcome["error"])

    entity_rows = (
        [("character", r) for r in entities.list_characters(dsn=path, account_id=account_id)]
        + [("prop", r) for r in entities.list_props(dsn=path, account_id=account_id)]
    )
    for kind, row in entity_rows:
        name = row["name"]
        slug = slugify(name)
        if describe and not described(row):
            # the folder only where it is this account's store; elsewhere
            # the account's OWN photos out of the bucket -- the folder is
            # shared by name, and describing it would file another
            # account's face under this one's element
            if folder_is_store(account_id):
                photos = photos_for(kind, slug)
            else:
                photos = [f for f in (own_photo_file(u, account_id)
                                      for u in r2_photo_urls(kind, slug, account_id))
                          if f is not None]
            if not photos:
                result["skipped_no_photos"] += 1
            elif gemini_client is None:
                record_error(f"{kind} {name}", "no Gemini client for the vision step")
            else:
                from .locations import describe_entity
                try:
                    vision = describe_entity(gemini_client, kind, name, photos)
                    entities.set_description(kind, row["id"], vision, dsn=path, account_id=account_id)
                    row = {**row, "description": {**(row.get("description") or {}),
                                                  **vision}}
                    result["described"] += 1
                except Exception as e:
                    record_error(f"{kind} {name}", str(e))

        outcome = ingest_one(kind, slug, name, entity_fields(kind, row),
                             project=project, account_id=account_id)
        if outcome["ok"]:
            result["ingested"] += 1
        else:
            record_error(f"{kind} {name}", outcome["error"])

    return result


def main(argv: Optional[list] = None) -> None:
    """`python -m src.asset_shelf [--describe]` -- the backfill from a
    terminal, the same call the Dev Studio's button makes."""
    import argparse
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Put every location, character, and prop on the RAG assets shelf.")
    parser.add_argument("--describe", action="store_true",
                        help="also run the vision step on undescribed cast/props "
                             "(one billed call each)")
    args = parser.parse_args(argv)

    client = None
    if args.describe:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY (or GOOGLE_API_KEY) not set", file=sys.stderr)
            sys.exit(1)
        from google import genai
        client = genai.Client(api_key=api_key)

    result = backfill(describe=args.describe, gemini_client=client)
    print(f"{result['ingested']} ingested, {result['described']} described, "
          f"{result['failed']} failed, {result['skipped_no_photos']} without photos")
    for error in result["errors"]:
        print(f"  {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
