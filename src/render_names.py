"""
Render file names that cannot be guessed, and who may open the ones that can.

WHY (security review, 2026-10-15). Every file under data/renders/ was
served by an open StaticFiles mount at /renders, and its name was a
timestamp: `c{concept}-s{n}-{YYYYMMDD-HHMMSS}.mp4`, `wf-{stamp}.png`,
`fx-{effect}-{stamp}.jpg`, `concept-{id}-v{n}-{tl}.mp4`. A loop over
seconds and concept ids downloaded every tenant's stills and clips --
faces included -- with no sign-in. The same names are mirrored to R2
under `m/<account>/renders/...`, so a public bucket was just as
enumerable.

TWO HALVES, both here so they cannot drift apart:

  1. `unguessable(stem)` -- every writer of a new file under data/renders
     appends `-<32 hex>` (secrets.token_hex(16), 128 bits) to the
     readable stem it always wrote. The readable prefix stays: the
     Library, the ledger ref and a person reading a folder listing all
     still see `c12-s1-...`. Nothing in the repo parses these names back
     (checked 2026-10-15: fal_requests recovers from the stored
     out_path, the poster `t/` derivative is keyed off the whole tail,
     charge.attempt_ref only prefixes them), so a suffix breaks nothing.

  2. `may_serve(rel, account_id)` -- the /renders route's decision. A
     name carrying the token is a CAPABILITY URL: whoever holds it may
     fetch it, exactly as a presigned R2 URL works. That is what keeps
     share_link's no-bucket fallback, a cross-origin studio and an
     Instagram/TikTok fetch working without a cookie. Content-addressed
     cut files (sha256 prefixes of the bytes themselves) are equally
     unguessable without already holding the content, so they pass
     too. Anything else is a LEGACY guessable name and is served only
     to the signed-in account that a row says owns it.
"""
from __future__ import annotations

import re
import secrets
from pathlib import PurePosixPath
from typing import Optional

TOKEN_BYTES = 16                        # 128 bits
TOKEN_HEX = TOKEN_BYTES * 2

# `<stem>-<32 hex>` then an optional extension, at the END of the file name
_CAPABILITY = re.compile(r"-[0-9a-f]{%d}(?:\.[A-Za-z0-9]{1,8})?$" % TOKEN_HEX)

# The cut's content-addressed files (src/cut/uploads.py, preview.py,
# index.py): named for sha256(bytes)[:24]. Unguessable to anyone who does
# not already have the bytes, so they are capabilities in their own right.
_SHA24 = r"[0-9a-f]{24}"
_CONTENT_ADDRESSED = (
    re.compile(rf"^cut/media/{_SHA24}\.[A-Za-z0-9]{{1,8}}$"),
    re.compile(rf"^cut/audio/{_SHA24}\.[A-Za-z0-9]{{1,8}}$"),
    re.compile(rf"^cut/preview/{_SHA24}/[^/]+$"),
)


def token() -> str:
    """128 random bits as 32 lowercase hex characters."""
    return secrets.token_hex(TOKEN_BYTES)


def unguessable(stem: str) -> str:
    """`stem` with the random component appended: `c12-s1-<stamp>` ->
    `c12-s1-<stamp>-<32 hex>`. Pass the stem WITHOUT its extension."""
    return f"{stem}-{token()}"


def has_token(name: str) -> bool:
    """Does this file name (or path) end in the random component?"""
    return bool(_CAPABILITY.search(PurePosixPath(str(name)).name))


def is_capability(rel: str) -> bool:
    """May `rel` (a path under data/renders, `/`-separated) be fetched by
    anyone holding the address? True for a tokened name or a
    content-addressed cut file; False for every legacy guessable name."""
    rel = str(rel or "").lstrip("/")
    if has_token(rel):
        return True
    return any(p.match(rel) for p in _CONTENT_ADDRESSED)


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# (table, columns) where a render's address is written down beside the
# account that owns it. Each column holds either the site route
# (`/renders/<rel>`), the R2 URL (`.../m/<acct>/renders/<rel>`) or the
# absolute output path (`.../data/renders/<rel>`) -- all of which END in
# `/renders/<rel>`, which is what the owner lookup matches on.
_OWNER_COLUMNS = (
    ("generated_assets", ("media_url", "output_path")),
    ("generations", ("output_path",)),
    ("cut_media", ("media_url", "output_path")),
    ("timelines", ("export_url",)),
)


def owned_by(rel: str, account_id: Optional[int], dsn: Optional[str] = None) -> bool:
    """Does a row say `account_id` owns the render at `rel`? Never raises;
    a missing table or a database error reads as "no" (the route answers
    404, never a leak)."""
    if account_id is None:
        return False
    rel = str(rel or "").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return False
    from . import db

    pattern = "%/renders/" + _like_escape(rel)
    try:
        with db.connect(dsn) as conn:
            for table, columns in _OWNER_COLUMNS:
                where = " OR ".join(f"{c} LIKE %s ESCAPE '\\'" for c in columns)
                try:
                    with conn.transaction():
                        row = conn.execute(
                            f"SELECT 1 FROM {table} WHERE account_id = %s "
                            f"AND ({where}) LIMIT 1",
                            (int(account_id), *([pattern] * len(columns)))).fetchone()
                except Exception:                               # noqa: BLE001
                    continue            # a table this database never made
                if row:
                    return True
    except Exception:                                           # noqa: BLE001
        return False
    return False


def may_serve(rel: str, account_id: Optional[int], dsn: Optional[str] = None) -> bool:
    """The /renders route's whole decision: a capability name to anyone,
    a legacy guessable name only to the account that owns it."""
    return is_capability(rel) or owned_by(rel, account_id, dsn)
