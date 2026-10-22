"""
One-time upload pages for the connector (2026-10-11,
docs/tasks/task-connector-overnight.md, PR 1).

A chat cannot hand this server a file: a connector tool takes text, and
the only picture a tool took until today was the https address of an
image somewhere on the web (`add_element`). A person with a photo on
their phone had no way in. `upload_link` is that way in: the tool mints
a page on the API origin, the person opens it, picks the file, and the
file lands in their studio as an `asset:<id>` (the editor's own upload
body, `src/cut/uploads.save`) -- and, when the link was minted for an
element, as that element's photo through the Elements page's own create
body.

THE TOKEN IS THE AUTH. The page needs no sign-in: the token is signed
with the session secret under its own salt (the `auth.handoff` pattern,
so it can never be presented as a session), carries the account and the
person it was minted for, expires after MAX_AGE_S, and is good ONCE. The
single use is a claim row (`upload_claims`, the shape of
`quote_redemptions`): the first POST that passes every check claims the
token with one `INSERT ... ON CONFLICT DO NOTHING`, and a second POST is
shown a plain "already used" page. A file that is refused (not a
picture, too big) gives the claim back, so the person can try again with
another file on the same link; a file that was saved spends it.

Nothing here reads a file, fetches anything or spends: it mints and
verifies tokens and records claims. The page itself is
app/upload_page.py.

OWNED (db.OWNED_TABLES): a claim is one account's upload.
"""
from __future__ import annotations

import json
import os
import secrets as _secrets
import sys
import time
from typing import Any, Optional
from urllib.parse import urlsplit

from . import db

SALT = "phantra-upload"
MAX_AGE_S = 30 * 60
PURPOSES = ("reference", "footage")
ORIGIN_ENV = "PHANTRA_UPLOAD_ORIGIN"
PAGE_PATH = "/u"

SCHEMA = """
CREATE TABLE IF NOT EXISTS upload_claims (
    token_id      TEXT PRIMARY KEY,
    account_id    BIGINT,
    user_id       TEXT NOT NULL DEFAULT '',
    purpose       TEXT NOT NULL,
    element_kind  TEXT,
    element_name  TEXT,
    claimed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    result_json   TEXT
);
"""

# `clock` is what the token's timestamp and its age are read from, a
# module attribute so a test can age a token without patching `time`
# for every other module in the process.
clock = time.time

_ready: set[str] = set()


class LinkRefused(ValueError):
    """Why a token is not honoured: `code` is bad_signature, expired or
    used; the message a sentence the page prints."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def init(dsn: Optional[str] = None) -> None:
    """Create and own the table. Idempotent; the app lifespan and the
    stdio entry point run it."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        db.own_table(conn, "upload_claims")
    _ready.add(db.resolve_dsn(dsn))


def ensure(dsn: Optional[str] = None) -> None:
    """The table, made once per process per database: a request path
    must not run the schema init on every call (two at once deadlock on
    the ShareLock, docs/BACKLOG.md's init lesson). A failed init is not
    remembered, so the next call tries again."""
    if db.resolve_dsn(dsn) in _ready:
        return
    db.run_init(lambda: init(dsn), dsn)


# --- the token --------------------------------------------------------------

def secret() -> str:
    """The session secret, read the way app/auth._session_secret reads
    it: SESSION_SECRET, else one generated for this process and put in
    the environment so the app's own serializer, asked later, reads the
    same value (and prints the same note). src/ cannot import app/, so
    the two readers agree by contract on the variable, not by import."""
    value = os.environ.get("SESSION_SECRET")
    if not value:
        value = _secrets.token_urlsafe(32)
        os.environ["SESSION_SECRET"] = value
        print("note: SESSION_SECRET not set -- generated an ephemeral one; "
              "sessions will not survive a restart", file=sys.stderr)
    return value


def _serializer():
    from itsdangerous import TimestampSigner, URLSafeTimedSerializer

    class _Signer(TimestampSigner):              # the stamp and its age read the
        def get_timestamp(self) -> int:          # module's clock, patchable
            return int(clock())

    return URLSafeTimedSerializer(secret(), salt=SALT, signer=_Signer)


def page_origin() -> str:
    """Where the page is served: PHANTRA_UPLOAD_ORIGIN, else the origin of
    the connector's own resource URI (PHANTRA_MCP_RESOURCE, the API
    origin on Fly), else SITE_URL, else the dev server. No trailing slash."""
    for raw in (os.environ.get(ORIGIN_ENV), os.environ.get("PHANTRA_MCP_RESOURCE"),
                os.environ.get("SITE_URL")):
        raw = (raw or "").strip()
        if not raw:
            continue
        parts = urlsplit(raw)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return "http://127.0.0.1:8000"


def page_url(token: str) -> str:
    return f"{page_origin()}{PAGE_PATH}/{token}"


def mint(account_id: int, user_id: Optional[str], purpose: str, *,
         element_kind: Optional[str] = None, element_name: Optional[str] = None) -> dict[str, Any]:
    """A fresh token for ONE upload into `account_id`, by `user_id` (""
    for the operator's key: nobody in particular). Returns the token, its
    id, the page's address and how long it is good for."""
    if purpose not in PURPOSES:
        raise ValueError(f"purpose must be one of {list(PURPOSES)}")
    token_id = _secrets.token_urlsafe(16)
    body = {"t": token_id, "a": int(account_id), "u": str(user_id or ""), "p": purpose}
    if element_kind:
        body["k"] = element_kind
        body["n"] = element_name or ""
    token = _serializer().dumps(body)
    return {"token": token, "token_id": token_id, "url": page_url(token),
            "expires_in_s": MAX_AGE_S}


def verify(token: str, *, max_age: int = MAX_AGE_S) -> dict[str, Any]:
    """The claims of a token this server minted, or LinkRefused. `expired`
    is told apart from `bad_signature` because a person can act on the
    first (ask the chat for a new link) and nothing can be done about the
    second but ask for a new one."""
    from itsdangerous import BadData, SignatureExpired
    try:
        data = _serializer().loads(str(token or ""), max_age=max_age)
    except SignatureExpired:
        raise LinkRefused("expired", "this upload link has expired -- ask the chat for "
                                     "a new one") from None
    except BadData:
        raise LinkRefused("bad_signature", "this is not an upload link this studio "
                                           "issued") from None
    if not isinstance(data, dict) or not data.get("t") or data.get("p") not in PURPOSES:
        raise LinkRefused("bad_signature", "this is not an upload link this studio issued")
    return {"token_id": str(data["t"]), "account_id": int(data["a"]),
            "user_id": str(data.get("u") or ""), "purpose": str(data["p"]),
            "element_kind": data.get("k") or None, "element_name": data.get("n") or None}


# --- the claim --------------------------------------------------------------

def claim(claims: dict, *, dsn: Optional[str] = None) -> bool:
    """Claim the token for its account. True when this call won it (go
    ahead and save); False when it was spent before. One INSERT ... ON
    CONFLICT DO NOTHING, so two posts racing cannot both win."""
    with db.connect(dsn) as conn:
        won = conn.execute(
            "INSERT INTO upload_claims (token_id, account_id, user_id, purpose, "
            "element_kind, element_name) VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (token_id) DO NOTHING RETURNING token_id",
            (claims["token_id"], claims["account_id"], claims.get("user_id") or "",
             claims["purpose"], claims.get("element_kind"), claims.get("element_name"))
        ).fetchone()
    return won is not None


def record(token_id: str, account_id: Optional[int], result: dict[str, Any],
           dsn: Optional[str] = None) -> None:
    """What the upload made (the asset id, the element), kept with the
    claim so the same token asked again can be told what it did."""
    with db.connect(dsn) as conn:
        conn.execute(
            "UPDATE upload_claims SET result_json = %s "
            "WHERE token_id = %s AND account_id IS NOT DISTINCT FROM %s",
            (json.dumps(result, default=str), token_id, account_id))


def forget(token_id: str, account_id: Optional[int], dsn: Optional[str] = None) -> None:
    """Give a claim back when nothing was saved (the file was refused): the
    link is still good for another try."""
    with db.connect(dsn) as conn:
        conn.execute(
            "DELETE FROM upload_claims WHERE token_id = %s "
            "AND account_id IS NOT DISTINCT FROM %s AND result_json IS NULL",
            (token_id, account_id))


def used(token_id: str, dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """The claim row for a token, or None while it is unspent."""
    with db.connect(dsn) as conn:
        row = conn.execute(
            "SELECT account_id, purpose, claimed_at, result_json FROM upload_claims "
            "WHERE token_id = %s", (token_id,)).fetchone()
    if row is None:
        return None
    return {"account_id": row["account_id"], "purpose": row["purpose"],
            "claimed_at": row["claimed_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None}


__all__ = ["SALT", "MAX_AGE_S", "PURPOSES", "LinkRefused", "init", "ensure", "secret",
           "page_origin", "page_url", "mint", "verify", "claim", "record", "forget", "used"]
