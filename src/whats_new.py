"""What's new: the Create wall that fills itself (2026-10-25,
docs/tasks/task-whats-new.md).

Mike's call: the wall under the box is a sitewide channel that tells every
person about new models, effects, looks, skills and features, plus what is
coming soon and Phantra's own deals. Adding a model to fal's tables (or an
effect, a look, a skill) is enough to put it in front of Mike: on boot,
`sync()` compares the tables with `showcase_items` and files a PENDING row
for anything it has never seen. It spends nothing.

A row goes live only on Mike's word. Its picture is ONE render on the house
account, approved on a priced card and kept (or Redo) -- that step is the
operator's Showcase list, the next build step; this module only files,
tracks and reads. Until a row is `live` nobody but the operator sees it
(decision 1: no placeholder tiles).

Two tables:

- `showcase_items` (SHARED): one row per announcement, the same for every
  person. House renders only; no account's data is ever written here.
- `announcement_seen` (OWNED): what one person has seen, dismissed or asked
  to be told about (Coming soon's Notify me). Drives the New badge.

Statuses: pending -> rendering -> review -> live, plus skipped (never shown)
and retired (its source left its table, a deal ended, a coming-soon item
shipped as the thing it `becomes`).

Ids are `<source>:<key>`: `model:grok1.5`, `effect:kling-effect`,
`look:noir`, `skill:ad`, `feature:final_cut`, `soon:<key>`, `deal:<key>`.

Out on purpose (Mike, 2026-10-25): new social platforms and fal's own price
changes never make a row. Deals are Phantra's own discounts only.

`ensure(dsn)` inits once per process and database; nothing here runs an
init per request. Every function that reads or writes degrades: a failure
is printed and answered with an empty result, never raised into a page.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import threading
from typing import Any, Callable, Optional

from . import db

# --------------------------------------------------------------------------
# the vocabulary
# --------------------------------------------------------------------------

SOURCES = ("model", "effect", "look", "skill", "feature", "soon", "deal")
AUTOMATIC = ("model", "effect", "look", "skill")     # read off a table
HAND = ("feature", "soon", "deal")                   # written in this file

PENDING, RENDERING, REVIEW, LIVE = "pending", "rendering", "review", "live"
SKIPPED, RETIRED = "skipped", "retired"
STATUSES = (PENDING, RENDERING, REVIEW, LIVE, SKIPPED, RETIRED)

# the tag on a tile, by source (the wall's words; colours are the CSS's)
TAG = {
    "model": "NEW MODEL", "effect": "NEW EFFECT", "look": "NEW LOOK",
    "skill": "NEW SKILL", "feature": "UPDATE", "soon": "COMING SOON",
    "deal": "DEAL",
}

# what a showcase's picture is made from: a clip or a still rendered on a
# model, an existing item the operator picks (an effect needs a source to
# work on), or nothing at all (a type-only tile)
MEDIA_KINDS = ("clip", "still", "pick", "none")
SIZES = ("big", "wide", "tall", "medium", "small", "slim")

NEW_DAYS = 21              # how long a live tile is "New" from live_at
SYNC_ENV = "PHANTRA_WHATS_NEW_SYNC"
HOUSE_ENV = "PHANTRA_SHOWCASE_ACCOUNT"     # the slug whose owners run the list and pay
HOUSE_DEFAULT = "phantra"

# --------------------------------------------------------------------------
# hand-written entries
#
# One dict per entry: id (the key after the source), title, line, and any
# of accent, size, date, requires (a capability), media ("clip" | "still" |
# "pick" | "none", default "none"), prompt and model for a render, action
# (what the click does: {"fill": text} | {"href": path} | {"effect": name}
# | {"look": name} | {"talk": True}). Coming soon may add eta (words, never
# a made-up date) and becomes ("model:<key>" etc.). A deal must add starts
# and ends (ISO days); it shows only inside them.
# --------------------------------------------------------------------------

FEATURES: list[dict] = []

COMING_SOON: list[dict] = []

# Phantra's own discounts and offers only. None are live (2026-10-25).
DEALS: list[dict] = []

# Showcase copy and prompt for an automatic source, by id. Optional: a row
# not named here gets copy built from its table's label and blurb. Grok is
# the first real pair waiting for Mike (shipped 2026-10-23, PR #474, and
# never put on the wall).
SHOWCASE: dict[str, dict] = {
    "model:grok1.5": {
        "title": "Grok Imagine is here", "accent": "Grok Imagine",
        "line": "xAI's video model: up to 15 seconds, 480p to 1080p, from text or a picture.",
        "prompt": ("A rain-soaked neon street at night, a lone figure in a long coat walks "
                   "toward the camera, puddles mirroring pink and teal signs, steam rising "
                   "from a vent, slow push in, cinematic, shallow depth of field."),
        "seconds": 6, "resolution": "720p", "aspect": "16:9", "size": "big",
        "action": {"fill": "A 6-second shot on Grok Imagine: ", "model": "grok1.5"},
    },
    "model:grok1.5-lite": {
        "title": "Grok Imagine Lite", "accent": "Lite",
        "line": "The fast, low-cost Grok: drafts and quick takes up to 15 seconds.",
        "prompt": ("A golden retriever bounding through tall grass at sunset, slow motion, "
                   "warm backlight, handheld tracking shot."),
        "seconds": 6, "resolution": "720p", "aspect": "16:9", "size": "medium",
        "action": {"fill": "A quick take on Grok Imagine Lite: ", "model": "grok1.5-lite"},
    },
}

# ids that start PENDING on the first sync, when everything else already
# live is seeded as skipped so the wall is not flooded with old news
SEED_PENDING = ("model:grok1.5", "model:grok1.5-lite")

DEFAULT_CLIP_PROMPT = (
    "A cinematic showcase shot: a lone figure on a rooftop at dusk, the city lights "
    "coming on below, wind in their coat, slow orbit around them, film grain.")
DEFAULT_STILL_PROMPT = (
    "An editorial still: a ceramic coffee cup on a concrete ledge in soft morning light, "
    "shallow depth of field, muted warm palette.")

# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS showcase_items (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    key           TEXT NOT NULL,
    title         TEXT NOT NULL DEFAULT '',
    line          TEXT NOT NULL DEFAULT '',
    accent        TEXT NOT NULL DEFAULT '',
    size          TEXT NOT NULL DEFAULT 'medium',
    media_kind    TEXT NOT NULL DEFAULT 'none',
    prompt        TEXT NOT NULL DEFAULT '',
    model         TEXT NOT NULL DEFAULT '',
    params_json   TEXT NOT NULL DEFAULT '{}',
    action_json   TEXT NOT NULL DEFAULT '{}',
    requires      TEXT,
    eta           TEXT,
    becomes       TEXT,
    starts        DATE,
    ends          DATE,
    status        TEXT NOT NULL DEFAULT 'pending',
    media         TEXT,
    media_type    TEXT,
    media_account BIGINT,
    poster        TEXT,
    note          TEXT,
    credits_spent INTEGER NOT NULL DEFAULT 0,
    gen_id        TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    live_at       TIMESTAMPTZ,
    retired_at    TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS announcement_seen (
    id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id      TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    seen_at      TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    notify       BOOLEAN NOT NULL DEFAULT false
);
"""
# columns added after the table first shipped (step 2): an older table grows them
LATER_COLUMNS = (("media_type", "TEXT"), ("media_account", "BIGINT"), ("note", "TEXT"))
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_showcase_items_status ON showcase_items (status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_announcement_seen_one
    ON announcement_seen (account_id, user_id, item_id);
"""

_ready: set[str] = set()
_ready_lock = threading.Lock()


def init(dsn: Optional[str] = None) -> None:
    key = db.resolve_dsn(dsn)
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        for column, kind in LATER_COLUMNS:
            conn.execute(f"ALTER TABLE showcase_items ADD COLUMN IF NOT EXISTS {column} {kind}")
        db.own_table(conn, "announcement_seen")
        conn.execute(INDEXES)
    _ready.add(key)


def ensure(dsn: Optional[str] = None) -> None:
    key = db.resolve_dsn(dsn)
    if key in _ready:
        return
    with _ready_lock:
        if key not in _ready:
            db.run_init(lambda: init(dsn), dsn)


def sync_enabled() -> bool:
    return os.environ.get(SYNC_ENV, "1").strip().lower() not in ("0", "false", "off", "no")


def _note(msg: str) -> None:
    print(f"  what's new: {msg}", file=sys.stderr)


# --------------------------------------------------------------------------
# the sources, read now
# --------------------------------------------------------------------------


def _fit_seconds(spec: dict, want: int) -> int:
    """`want` held inside the model's legal range, when the row gives one
    as (low, high); else `want`. The render step re-checks it on the card."""
    durations = spec.get("durations")
    lo, hi = durations if isinstance(durations, (tuple, list)) and len(durations) == 2 else (want, want)
    try:
        return max(int(lo), min(int(hi), int(want)))
    except (TypeError, ValueError):
        return want


def _blurbs() -> dict[str, tuple[str, str]]:
    """{model key: (public name, blurb)} off the public catalogue."""
    try:
        from . import pricing
        return {key: (name, blurb) for _p, key, name, blurb in pricing.catalog_rows()}
    except Exception as e:
        _note(f"catalogue unread: {type(e).__name__}: {e}")
        return {}


def _entry(source: str, key: str, **fields: Any) -> dict:
    over = SHOWCASE.get(f"{source}:{key}", {})
    e = {
        "id": f"{source}:{key}", "source": source, "key": key,
        "title": "", "line": "", "accent": "", "size": "medium",
        "media_kind": "none", "prompt": "", "model": "", "params": {},
        "action": {}, "requires": None, "eta": None, "becomes": None,
        "starts": None, "ends": None,
    }
    e.update({k: v for k, v in fields.items() if v is not None})
    for k in ("title", "line", "accent", "size", "prompt", "action", "requires"):
        if k in over:
            e[k] = over[k]
    for k in ("seconds", "resolution", "aspect"):
        if k in over:
            e["params"] = {**e["params"], k: over[k]}
    return e


def _models() -> list[dict]:
    from . import fal
    out = []
    blurbs = _blurbs()
    for key, spec in fal.VIDEO_MODELS.items():
        name, blurb = blurbs.get(key, (key, ""))
        seconds = _fit_seconds(spec, int(SHOWCASE.get(f"model:{key}", {}).get("seconds", 6)))
        out.append(_entry(
            "model", key, title=f"{name} is here", accent=name,
            line=blurb or "In every clip picker now.", size="big", media_kind="clip",
            prompt=DEFAULT_CLIP_PROMPT, model=key,
            params={"seconds": seconds, "resolution": spec.get("default_resolution") or "",
                    "aspect": "16:9"},
            action={"fill": f"A shot on {name}: ", "model": key}))
    for key, spec in fal.IMAGE_MODELS.items():
        name = spec.get("label") or key
        out.append(_entry(
            "model", key, title=f"{name} is here", accent=name,
            line=spec.get("note") or "In every image picker now.", media_kind="still",
            prompt=DEFAULT_STILL_PROMPT, model=key, params={"aspect": "4:5"},
            action={"fill": f"A still on {name}: ", "model": key}))
    return out


def _effects() -> list[dict]:
    from . import effects
    out = []
    for name, row in effects.EFFECTS.items():
        look = row.get("category") == "look"
        label = row.get("label") or name
        out.append(_entry(
            "look" if look else "effect", name, title=label, accent=label,
            line=row.get("note") or "", size="tall", media_kind="pick",
            params={"effect": name},
            action={"look": name} if look else {"effect": name}))
    return out


def _skills() -> list[dict]:
    from . import skills
    return [_entry("skill", s["name"], title=s["title"], accent=s["title"],
                   line=s["summary"], size="small", media_kind="none",
                   action={"skill": s["name"]})
            for s in skills.catalogue()]


def _day(raw) -> Optional[dt.date]:
    if isinstance(raw, dt.date):
        return raw
    try:
        return dt.date.fromisoformat(str(raw)) if raw else None
    except ValueError:
        return None


def _hand(source: str, items: list[dict]) -> list[dict]:
    out = []
    for raw in items:
        key = str(raw.get("id") or "").strip()
        if not key or not raw.get("title"):
            _note(f"a {source} entry with no id or title was left out")
            continue
        if source == "deal" and not (_day(raw.get("starts")) and _day(raw.get("ends"))):
            _note(f"deal {key!r} has no starts/ends and was left out")
            continue
        media = raw.get("media") if raw.get("media") in MEDIA_KINDS else "none"
        out.append(_entry(
            source, key, title=raw["title"], line=raw.get("line") or "",
            accent=raw.get("accent") or "", size=raw.get("size") or "medium",
            media_kind=media, prompt=raw.get("prompt") or "", model=raw.get("model") or "",
            params=dict(raw.get("params") or {}), action=dict(raw.get("action") or {}),
            requires=raw.get("requires"), eta=raw.get("eta"), becomes=raw.get("becomes"),
            starts=_day(raw.get("starts")), ends=_day(raw.get("ends"))))
    return out


READERS: dict[str, Callable[[], list[dict]]] = {
    "model": _models,
    "effect_and_look": _effects,
    "skill": _skills,
}


def candidates() -> tuple[list[dict], set[str]]:
    """(every entry the sources hold right now, the sources that could be
    read). A source whose reader failed is NOT in the set, so sync never
    retires its rows on a bad read."""
    out: list[dict] = []
    read: set[str] = set()
    for name, reader in READERS.items():
        try:
            out.extend(reader())
            read.update(("effect", "look") if name == "effect_and_look" else (name,))
        except Exception as e:
            _note(f"{name} unread: {type(e).__name__}: {e}")
    out.extend(_hand("feature", FEATURES))
    out.extend(_hand("soon", COMING_SOON))
    out.extend(_hand("deal", DEALS))
    read.update(HAND)
    return out, read


# --------------------------------------------------------------------------
# sync: file what is new, retire what left. Spends nothing.
# --------------------------------------------------------------------------

_INSERT = (
    "INSERT INTO showcase_items (id, source, key, title, line, accent, size, media_kind,"
    " prompt, model, params_json, action_json, requires, eta, becomes, starts, ends, status,"
    " retired_at)"
    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
    " CASE WHEN %s = 'retired' THEN now() END)"
    " ON CONFLICT (id) DO NOTHING")


def _row(e: dict, status: str) -> tuple:
    return (e["id"], e["source"], e["key"], e["title"], e["line"], e["accent"], e["size"],
            e["media_kind"], e["prompt"], e["model"], json.dumps(e["params"]),
            json.dumps(e["action"]), e["requires"], e["eta"], e["becomes"], e["starts"],
            e["ends"], status, status)


def sync(dsn: Optional[str] = None, *, today: Optional[dt.date] = None) -> dict:
    """File a pending row for every entry never seen, retire rows whose
    source entry is gone, retire ended deals and shipped coming-soon items.

    The FIRST sync on an empty table seeds every automatic entry already
    in the tables as skipped (old news), except SEED_PENDING; hand-written
    entries are always pending. Returns counts; {} on failure."""
    today = today or dt.date.today()
    try:
        ensure(dsn)
        entries, read = candidates()
        by_id = {e["id"]: e for e in entries}
        counts = {"pending": 0, "skipped": 0, "retired": 0, "returned": 0}
        with db.connect(dsn) as conn:
            known = {r[0]: (r[1], r[2], r[3]) for r in conn.execute(
                "SELECT id, source, status, media FROM showcase_items").fetchall()}
            first = not known
            for e in entries:
                if e["id"] in known:
                    continue
                status = PENDING
                if first and e["source"] in AUTOMATIC and e["id"] not in SEED_PENDING:
                    status = SKIPPED
                conn.execute(_INSERT, _row(e, status))
                counts[status] += 1
            # hand entries: the file is the source of truth for their dates
            for e in entries:
                if e["source"] in HAND and e["id"] in known:
                    conn.execute(
                        "UPDATE showcase_items SET requires = %s, eta = %s, becomes = %s,"
                        " starts = %s, ends = %s, updated_at = now() WHERE id = %s",
                        (e["requires"], e["eta"], e["becomes"], e["starts"], e["ends"], e["id"]))
            for item_id, (source, status, media) in known.items():
                gone = source in read and item_id not in by_id
                if gone and status != RETIRED:
                    conn.execute("UPDATE showcase_items SET status = 'retired', retired_at = now(),"
                                 " updated_at = now() WHERE id = %s", (item_id,))
                    counts["retired"] += 1
                elif not gone and status == RETIRED and source in AUTOMATIC:
                    # a model taken out and put back: live again only if it was kept
                    back = LIVE if media else PENDING
                    conn.execute("UPDATE showcase_items SET status = %s, retired_at = NULL,"
                                 " updated_at = now() WHERE id = %s", (back, item_id))
                    counts["returned"] += 1
            # a render a deploy killed mid-poll: the fal sweep files the take in
            # the house Library, and the row goes back to waiting, saying so
            cur = conn.execute(
                "UPDATE showcase_items SET status = 'pending', note = %s, updated_at = now()"
                " WHERE status = 'rendering' AND updated_at < now() - interval '30 minutes'",
                ("The render was interrupted. If it finished, its take is in the Library: "
                 "pick it.",))
            counts["interrupted"] = cur.rowcount or 0
            # a deal past its end retires itself
            cur = conn.execute(
                "UPDATE showcase_items SET status = 'retired', retired_at = now(), updated_at = now()"
                " WHERE source = 'deal' AND status <> 'retired' AND ends < %s", (today,))
            counts["retired"] += cur.rowcount or 0
            # a coming-soon item whose `becomes` is live has shipped
            cur = conn.execute(
                "UPDATE showcase_items s SET status = 'retired', retired_at = now(), updated_at = now()"
                " FROM showcase_items t WHERE s.source = 'soon' AND s.status <> 'retired'"
                " AND s.becomes = t.id AND t.status = 'live'")
            counts["retired"] += cur.rowcount or 0
        counts["first_run"] = first
        return counts
    except Exception as e:
        _note(f"sync failed: {type(e).__name__}: {e}")
        return {}


def start_sync() -> None:
    """The boot hook (app.main's lifespan): one sync, under the init lock,
    unless PHANTRA_WHATS_NEW_SYNC=0. Never raises."""
    if not sync_enabled():
        return
    try:
        counts = db.run_init(lambda: sync())
        if counts and (counts.get("pending") or counts.get("retired")):
            _note(f"sync: {counts}")
    except Exception as e:
        _note(f"boot sync failed: {type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# the feed: what one person sees
# --------------------------------------------------------------------------

_COLS = ("id", "source", "key", "title", "line", "accent", "size", "media_kind",
         "action_json", "requires", "eta", "becomes", "starts", "ends", "media", "poster",
         "live_at", "media_type", "media_account")


def _still_offered(source: str, key: str) -> bool:
    """Whether the thing a live tile points at can still be used."""
    try:
        if source == "model":
            from . import fal
            return key in fal.VIDEO_MODELS or key in fal.IMAGE_MODELS
        if source in ("effect", "look"):
            from . import effects
            return key in effects.listed_names()
        if source == "skill":
            from . import skills
            return key in skills.names()
    except Exception:
        return False
    return True


def _mint(name: Optional[str], account_id: Optional[int] = None) -> Optional[str]:
    if not name:
        return None
    try:
        from . import media
        return media.url_for(name, account_id)
    except Exception:
        return name


def _poster(row: dict) -> Optional[str]:
    """A clip's resting frame: the stored poster, else the 480px derivative
    of the clip; a still is its own picture."""
    if row.get("poster"):
        return _mint(row["poster"], row.get("media_account"))
    if row.get("media") and row.get("media_type") == "video":
        try:
            from . import media
            return media.thumb_url_for(row["media"], row.get("media_account"))
        except Exception:
            return None
    return None


def feed(account_id: int, user_id: str, caps: Optional[dict] = None,
         dsn: Optional[str] = None, *, now: Optional[dt.datetime] = None) -> dict:
    """{"items": [...], "unread": n} -- the live tiles this person can use,
    New ones first. A tile is shown when it is live, its source still offers
    it, its `requires` capability is true, a deal is inside its window, and
    the person has not dismissed it. No price is in any item (a deal's own
    words may name its offer; that is the deal)."""
    caps = caps or {}
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.date()
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_COLS)} FROM showcase_items WHERE status = 'live'"
                " ORDER BY live_at DESC NULLS LAST, id").fetchall()
            marks = {r[0]: (r[1], r[2], r[3]) for r in conn.execute(
                "SELECT item_id, seen_at, dismissed_at, notify FROM announcement_seen"
                " WHERE account_id = %s AND user_id = %s", (account_id, str(user_id))).fetchall()}
            asked = {r[0] for r in conn.execute(
                "SELECT s.becomes FROM showcase_items s JOIN announcement_seen a"
                " ON a.item_id = s.id WHERE a.account_id = %s AND a.user_id = %s"
                " AND a.notify AND s.becomes IS NOT NULL",
                (account_id, str(user_id))).fetchall()}
    except Exception as e:
        _note(f"feed unread: {type(e).__name__}: {e}")
        return {"items": [], "unread": 0}
    items, unread = [], 0
    for r in rows:
        row = dict(zip(_COLS, r))
        seen, dismissed, notify = marks.get(row["id"], (None, None, False))
        if dismissed:
            continue
        if row["requires"] and caps.get(row["requires"]) is not True:
            continue
        if row["source"] == "deal" and not (row["starts"] and row["ends"]
                                            and row["starts"] <= today <= row["ends"]):
            continue
        if not _still_offered(row["source"], row["key"]):
            continue
        live_at = row["live_at"]
        is_new = bool(live_at and (now - live_at) <= dt.timedelta(days=NEW_DAYS))
        is_unread = seen is None
        unread += is_unread
        try:
            action = json.loads(row["action_json"] or "{}")
        except ValueError:
            action = {}
        if row["source"] == "soon":
            # nothing to make yet: the click is Notify me or a page about it
            action = {k: v for k, v in action.items() if k == "href"}
        items.append({
            "id": row["id"], "source": row["source"], "tag": TAG[row["source"]],
            "title": row["title"], "line": row["line"], "accent": row["accent"],
            "size": row["size"], "action": action,
            "media": {"kind": row["media_type"] or ("none" if not row["media"] else "image"),
                      "url": _mint(row["media"], row["media_account"]),
                      "poster": _poster(row)},
            "eta": row["eta"] if row["source"] == "soon" else None,
            "ends": row["ends"].isoformat() if row["source"] == "deal" and row["ends"] else None,
            "new": is_new, "unread": is_unread,
            "notify": bool(notify) if row["source"] == "soon" else None,
            "you_asked": row["id"] in asked,
            "live_at": live_at.isoformat() if live_at else None,
        })
    items.sort(key=lambda i: (not i["new"], not i["you_asked"]))
    return {"items": items, "unread": unread}


# --------------------------------------------------------------------------
# one person's marks
# --------------------------------------------------------------------------

_MARK = {
    "seen": ("seen_at = COALESCE(announcement_seen.seen_at, now())", "now()", "NULL", "false"),
    "dismissed": ("dismissed_at = now(), seen_at = COALESCE(announcement_seen.seen_at, now())",
                  "now()", "now()", "false"),
    "notify": ("notify = true, seen_at = COALESCE(announcement_seen.seen_at, now())",
               "now()", "NULL", "true"),
}


def mark(account_id: int, user_id: str, item_ids, what: str,
         dsn: Optional[str] = None) -> int:
    """Mark items seen / dismissed / notify for one person. Only ids that
    exist are marked, and notify only on a coming-soon item. Returns how
    many were marked; 0 on failure."""
    if what not in _MARK:
        raise ValueError(f"unknown mark {what!r}")
    ids = [str(i) for i in (item_ids or []) if isinstance(i, str) and i][:200]
    if not ids:
        return 0
    update, seen, dismissed, notify = _MARK[what]
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            q = "SELECT id FROM showcase_items WHERE id = ANY(%s)"
            if what == "notify":
                q += " AND source = 'soon'"
            real = [r[0] for r in conn.execute(q, (ids,)).fetchall()]
            for item_id in real:
                conn.execute(
                    "INSERT INTO announcement_seen (account_id, user_id, item_id, seen_at,"
                    f" dismissed_at, notify) VALUES (%s, %s, %s, {seen}, {dismissed}, {notify})"
                    " ON CONFLICT (account_id, user_id, item_id) DO UPDATE SET " + update,
                    (account_id, str(user_id), item_id))
        return len(real)
    except Exception as e:
        _note(f"{what} not kept: {type(e).__name__}: {e}")
        return 0


# --------------------------------------------------------------------------
# the operator's Showcase list (step 2, 2026-10-25)
#
# The house account (PHANTRA_SHOWCASE_ACCOUNT, default `phantra`) pays for
# every showcase render and its owners are the only people who see this list
# (the gate is the app's: app/whats_new_routes.py). A row moves:
#
#   pending --approve (a priced render)--> rendering --> review --keep--> live
#   pending --pick (an existing Library item)----------> review
#   pending --keep (a type-only tile, media "none")-------------------> live
#   review / live --redo--> pending (the take stays in the Library)
#   pending / review --skip--> skipped --restore--> pending
#
# Each transition is one UPDATE guarded by the status it moves from, so two
# clicks cannot both start a render. Nothing here calls a model or spends:
# the route quotes, takes the approval and runs the render job.
# --------------------------------------------------------------------------


class Refused(ValueError):
    """A move the row's status does not allow, said in plain words."""


def house_account_id(dsn: Optional[str] = None) -> Optional[int]:
    """The account showcase renders are paid by and filed under, or None
    when the database has no account with that slug."""
    slug = (os.environ.get(HOUSE_ENV) or HOUSE_DEFAULT).strip()
    try:
        with db.connect(dsn) as conn:
            row = conn.execute("SELECT id FROM accounts WHERE slug = %s", (slug,)).fetchone()
        return int(row["id"]) if row else None
    except Exception as e:
        _note(f"house account unread: {type(e).__name__}: {e}")
        return None


_ITEM_COLS = ("id", "source", "key", "title", "line", "accent", "size", "media_kind",
              "prompt", "model", "params_json", "action_json", "requires", "eta", "becomes",
              "starts", "ends", "status", "media", "media_type", "media_account", "poster",
              "note", "credits_spent", "gen_id", "first_seen_at", "live_at")


def _shape(row: dict) -> dict:
    out = dict(row)
    out["params"] = json.loads(out.pop("params_json") or "{}")
    out["action"] = json.loads(out.pop("action_json") or "{}")
    for k in ("first_seen_at", "live_at", "starts", "ends"):
        if out.get(k) is not None:
            out[k] = out[k].isoformat()
    out["tag"] = TAG.get(out["source"], "")
    out["media_url"] = _mint(out.get("media"), out.get("media_account"))
    out["poster_url"] = _poster(out)
    return out


def get(item_id: str, dsn: Optional[str] = None) -> Optional[dict]:
    ensure(dsn)
    with db.connect(dsn) as conn:
        row = conn.execute(f"SELECT {', '.join(_ITEM_COLS)} FROM showcase_items WHERE id = %s",
                           (item_id,)).fetchone()
    return _shape(dict(zip(_ITEM_COLS, row))) if row else None


def queue(dsn: Optional[str] = None,
          statuses=(PENDING, RENDERING, REVIEW, LIVE, SKIPPED)) -> list[dict]:
    """The Showcase list: waiting rows first (oldest first), then live,
    then skipped. [] on failure."""
    order = {PENDING: 0, RENDERING: 1, REVIEW: 2, LIVE: 3, SKIPPED: 4}
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_ITEM_COLS)} FROM showcase_items WHERE status = ANY(%s)"
                " ORDER BY first_seen_at, id", (list(statuses),)).fetchall()
    except Exception as e:
        _note(f"queue unread: {type(e).__name__}: {e}")
        return []
    out = [_shape(dict(zip(_ITEM_COLS, r))) for r in rows]
    out.sort(key=lambda r: order.get(r["status"], 9))
    return out


EDITABLE = ("title", "line", "accent", "size", "prompt")
PARAM_KEYS = ("seconds", "resolution", "aspect")


def edit(item_id: str, fields: dict, dsn: Optional[str] = None) -> dict:
    """Change a row's words, prompt or render pick (seconds / resolution /
    aspect) before it goes live. A live row is edited by Redo first, so a
    tile people already saw never changes under them."""
    item = get(item_id, dsn)
    if item is None:
        raise Refused("there is no such announcement")
    if item["status"] not in (PENDING, REVIEW, SKIPPED):
        raise Refused(f"a {item['status']} announcement can't be edited; Redo it first")
    sets, args = [], []
    for k in EDITABLE:
        if k in fields and fields[k] is not None:
            v = str(fields[k]).strip()
            if k == "size" and v not in SIZES:
                raise Refused(f"size is one of {', '.join(SIZES)}")
            if k == "title" and not v:
                raise Refused("a tile needs a title")
            sets.append(f"{k} = %s")
            args.append(v[:2000])
    params = dict(item["params"])
    for k in PARAM_KEYS:
        if k in fields and fields[k] is not None:
            params[k] = fields[k]
    if params != item["params"]:
        sets.append("params_json = %s")
        args.append(json.dumps(params))
    if sets:
        with db.connect(dsn) as conn:
            conn.execute(f"UPDATE showcase_items SET {', '.join(sets)}, updated_at = now()"
                         " WHERE id = %s", (*args, item_id))
    return get(item_id, dsn)


def _move(item_id: str, frm: tuple, to: str, dsn: Optional[str], *,
          extra: str = "", args: tuple = ()) -> dict:
    """One guarded transition, or Refused naming why not."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        row = conn.execute(
            f"UPDATE showcase_items SET status = %s{extra}, updated_at = now()"
            " WHERE id = %s AND status = ANY(%s) RETURNING id",
            (to, *args, item_id, list(frm))).fetchone()
    if row is None:
        item = get(item_id, dsn)
        if item is None:
            raise Refused("there is no such announcement")
        raise Refused(f"it is {item['status']}, so it can't move to {to}")
    return get(item_id, dsn)


def quote(item: dict, account_id: Optional[int]) -> dict:
    """The showcase render's price on the house account, through the
    direct generators' own quote (the number the hold takes), or Refused."""
    from . import direct
    if not renderable(item):
        raise Refused("this tile is not rendered: pick a Library item or keep it as words")
    p = item["params"]
    try:
        if item["media_kind"] == "clip":
            return direct.video_quote(account_id, model=item["model"], seconds=p.get("seconds"),
                                      resolution=p.get("resolution"), aspect=p.get("aspect"))
        return direct.image_quote(account_id, model=item["model"], aspect=p.get("aspect"))
    except ValueError as e:
        raise Refused(str(e)) from None


def renderable(item: dict) -> bool:
    return item["media_kind"] in ("clip", "still") and bool(item["model"]) and bool(item["prompt"])


def start_render(item_id: str, dsn: Optional[str] = None) -> dict:
    """pending -> rendering: the one door a render goes through, so a
    second click finds it already rendering and is refused."""
    item = get(item_id, dsn)
    if item is None:
        raise Refused("there is no such announcement")
    if not renderable(item):
        raise Refused("this tile is not rendered: pick a Library item or keep it as words")
    return _move(item_id, (PENDING,), RENDERING, dsn, extra=", note = NULL")


def finish_render(item_id: str, *, media: str, media_type: str, account_id: int,
                  gen_id: Optional[str], credits: int, dsn: Optional[str] = None) -> dict:
    """rendering -> review, with the take's stored NAME (never a URL)."""
    return _move(item_id, (RENDERING,), REVIEW, dsn,
                 extra=", media = %s, media_type = %s, media_account = %s, gen_id = %s,"
                       " poster = NULL, credits_spent = credits_spent + %s",
                 args=(media, media_type, account_id, gen_id, int(credits)))


def fail_render(item_id: str, reason: str, dsn: Optional[str] = None) -> dict:
    """rendering -> pending, saying why. Charging is the adapter's: a failed
    render released its hold before this runs."""
    return _move(item_id, (RENDERING,), PENDING, dsn, extra=", note = %s",
                 args=(str(reason)[:300],))


def pick(item_id: str, *, media: str, media_type: str, account_id: int, gen_id: str,
         dsn: Optional[str] = None) -> dict:
    """pending/review -> review with an item already in the house Library
    (an effect's or a look's before/after, a feature's screen recording)."""
    if media_type not in ("video", "image"):
        raise Refused("a showcase is a clip or a still")
    return _move(item_id, (PENDING, REVIEW), REVIEW, dsn,
                 extra=", media = %s, media_type = %s, media_account = %s, gen_id = %s,"
                       " poster = NULL, note = NULL",
                 args=(media, media_type, account_id, gen_id))


def keep(item_id: str, dsn: Optional[str] = None) -> dict:
    """review -> live (or pending -> live for a words-only tile). Live is
    sitewide: every person who can use it sees it, with the New badge."""
    item = get(item_id, dsn)
    if item is None:
        raise Refused("there is no such announcement")
    if item["status"] == PENDING and item["media_kind"] == "none":
        return _move(item_id, (PENDING,), LIVE, dsn, extra=", live_at = now()")
    return _move(item_id, (REVIEW,), LIVE, dsn, extra=", live_at = now()")


def redo(item_id: str, dsn: Optional[str] = None) -> dict:
    """review/live -> pending. The take stays in the house Library (a paid
    output is never thrown away) and its id is kept on the row's params."""
    item = get(item_id, dsn)
    if item is None:
        raise Refused("there is no such announcement")
    params = dict(item["params"])
    if item.get("gen_id"):
        params["takes"] = [*params.get("takes", []), item["gen_id"]][-20:]
    return _move(item_id, (REVIEW, LIVE), PENDING, dsn,
                 extra=", media = NULL, media_type = NULL, media_account = NULL, gen_id = NULL,"
                       " poster = NULL, live_at = NULL, params_json = %s",
                 args=(json.dumps(params),))


def skip(item_id: str, dsn: Optional[str] = None) -> dict:
    return _move(item_id, (PENDING, REVIEW), SKIPPED, dsn)


def restore(item_id: str, dsn: Optional[str] = None) -> dict:
    return _move(item_id, (SKIPPED,), PENDING, dsn)


if __name__ == "__main__":  # pragma: no cover - by hand
    print(json.dumps(sync(), default=str))
    for row in queue(statuses=(PENDING, RENDERING, REVIEW)):
        print(f"{row['status']:9} {row['id']}")
