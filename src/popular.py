"""Trending on Phantra: what the whole studio used most this week
(2026-11-02, Mike's call: "totals across all accounts";
docs/tasks/task-whats-new.md, "Later: sitewide trending").

`src/trending.py` is ONE account's week, by the tenancy rules. This is the
other half Mike asked for on 2026-10-25 and chose on 2026-11-02: a count
across every account, so the Create wall's Trending tiles say what people
are actually using instead of what was picked by hand.

WHAT CROSSES ACCOUNTS, AND WHAT NEVER DOES. The answer is a list of
catalogue keys (`effect:bullet_time`, `look:crash_zoom`, `model:kling4`)
with how many times each was used. Nothing else leaves this module: no
prompt, no render, no picture, no account id, no per-account count. The
key is the studio's own table name -- the same word every user already
sees in a picker -- so the count says "this effect is popular", never
"someone made this". It is the shape `generative.used_today(everyone=True)`
and `spend.spent_today_everyone` already have: an installation-wide
number, not anybody's rows.

THE MOST USED THINGS, NO FLOOR (Mike, 2026-11-03: "its for most popular
used things"). The list is simply what landed most this week, by total
uses; the first build (2026-11-02) held a key back until 3 accounts and 5
uses, and that floor is gone. MIN_ACCOUNTS / MIN_RUNS stay as knobs, both
at 1. Ties on uses break on how many accounts used it, then the key.

What counts as a use: a generation that LANDED (`output_path` set; a failed
attempt row has none, `generative.record_failure`) in the last DAYS, whose
attempt log names a catalogue key: an effect or a free look (`effect` in
`params_json`, `effects.run` / `free_looks.run`), else a fal model
(`provider == "fal"`, `model` in `fal.VIDEO_MODELS` / `fal.IMAGE_MODELS`).
The house account's showcase renders (`source == "showcase"`) are the wall's
own pictures, never a use. A key that is no longer offered drops out.

Read-only, never raises, cached in the process for CACHE_SECONDS: the wall
asks on every Create visit and the answer moves by the day, not the second.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import db

DAYS = 7
MIN_ACCOUNTS = 1         # no floor (Mike, 2026-11-03): the most used things, by total
MIN_RUNS = 1
TOP = 8                  # how many the wall is handed
ROWS_MAX = 50_000        # the newest landed rows read per refresh: one bounded read
CACHE_SECONDS = 600

_lock = threading.Lock()
_cache: dict = {}        # {"at": monotonic, "key": (days, min_accounts, min_runs), "items": [...]}


def _note(msg: str) -> None:
    print(f"note: popular {msg}", file=sys.stderr)


def cutoff(days: int = DAYS, now: Optional[datetime] = None) -> str:
    """`generations.created_at` is an ISO string (db._now, UTC), so the
    comparison is lexical -- trending.cutoff's rule."""
    at = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    return at.isoformat(timespec="seconds")


def _catalogue() -> tuple[dict, set, set]:
    """(effects by name -> row, video model keys, image model keys)."""
    from . import effects, fal
    return dict(effects.EFFECTS), set(fal.VIDEO_MODELS), set(fal.IMAGE_MODELS)


def key_of(params: dict, catalogue: Optional[tuple] = None) -> Optional[tuple[str, str, str]]:
    """(source, key, label) for one attempt's params, or None when it names
    nothing on the catalogue (a scene's clip on an unknown model, a cut,
    a kit screen) or is the house account's showcase render."""
    if not isinstance(params, dict) or params.get("source") == "showcase":
        return None
    fx, video, image = catalogue or _catalogue()
    name = params.get("effect")
    if isinstance(name, str) and name:
        row = fx.get(name)
        if not row:
            return None
        source = "look" if row.get("category") == "look" else "effect"
        return source, name, row.get("label") or name
    model = params.get("model")
    if params.get("provider") == "fal" and isinstance(model, str) and model:
        if model in video or model in image:
            return "model", model, _model_label(model)
    return None


def _model_label(key: str) -> str:
    try:
        from . import fal, whats_new
        if key in fal.IMAGE_MODELS:
            return fal.IMAGE_MODELS[key].get("label") or key
        return whats_new._blurbs().get(key, (key, ""))[0] or key
    except Exception:
        return key


def _offered(source: str, key: str) -> bool:
    try:
        from . import whats_new
        return whats_new._still_offered(source, key)
    except Exception:
        return False


def count(rows, *, min_accounts: int = MIN_ACCOUNTS, min_runs: int = MIN_RUNS,
          top: int = TOP, catalogue: Optional[tuple] = None) -> list[dict]:
    """The pure part: (account_id, params_json) rows -> the trending list.

    Each item is {id, source, key, label, runs}. The number of accounts is
    used to break ties and dropped: what leaves is a total, never who."""
    catalogue = catalogue or _catalogue()
    cells: dict[str, dict] = {}
    for account_id, raw in rows:
        try:
            params = json.loads(raw or "{}") or {}
        except (TypeError, ValueError):
            continue
        hit = key_of(params, catalogue)
        if not hit:
            continue
        source, key, label = hit
        cell = cells.setdefault(f"{source}:{key}", {
            "id": f"{source}:{key}", "source": source, "key": key, "label": label,
            "runs": 0, "_accounts": set()})
        cell["runs"] += 1
        cell["_accounts"].add(account_id)
    out = []
    for cell in cells.values():
        if len(cell["_accounts"]) < min_accounts or cell["runs"] < min_runs:
            continue
        reach = len(cell.pop("_accounts"))
        out.append((reach, cell))
    # most used first; a tie goes to the key more accounts used
    out.sort(key=lambda rc: (-rc[1]["runs"], -rc[0], rc[1]["id"]))
    return [c for _, c in out][:top]


def _read(since: str, dsn: Optional[str]) -> list[tuple]:
    with db.connect(dsn) as conn:
        if not db.table_exists(conn, "generations"):
            return []
        # Installation-wide ON PURPOSE (see the module docstring): the one
        # read behind the studio's Trending. account_id is selected only to
        # count how many accounts used a key to break ties; it never leaves
        # count(). Siblings: generative.used_today(everyone=True),
        # spend.spent_today_everyone.
        return [(r["account_id"], r["params_json"]) for r in conn.execute(
            "SELECT account_id, params_json FROM generations "
            "WHERE created_at >= %s AND output_path IS NOT NULL "
            "ORDER BY id DESC LIMIT %s", (since, ROWS_MAX)).fetchall()]


def top(*, days: int = DAYS, min_accounts: int = MIN_ACCOUNTS, min_runs: int = MIN_RUNS,
        dsn: Optional[str] = None, now: Optional[datetime] = None,
        fresh: bool = False) -> list[dict]:
    """What the whole studio used most in the last `days`, still offered. Never raises; [] when it cannot read."""
    key = (days, min_accounts, min_runs, dsn)
    with _lock:
        hit = _cache.get(key)
        if hit and not fresh and now is None and time.monotonic() - hit[0] < CACHE_SECONDS:
            return [dict(i) for i in hit[1]]
    try:
        rows = _read(cutoff(days, now), dsn)
        items = [i for i in count(rows, min_accounts=min_accounts, min_runs=min_runs)
                 if _offered(i["source"], i["key"])]
    except Exception as exc:                                   # noqa: BLE001
        _note(f"read skipped ({type(exc).__name__}: {exc})")
        return []
    if now is None:
        with _lock:
            _cache[key] = (time.monotonic(), items)
    return [dict(i) for i in items]


def clear_cache() -> None:
    with _lock:
        _cache.clear()
