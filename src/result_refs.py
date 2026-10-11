"""A short number on every result, usable in a sentence (2026-10-11; item 11
of docs/tasks/task-studio-agent.md, from invideo's numbered assets: "make 3
warmer").

The composer gives each thing a conversation made -- a still, a clip, a
written scene -- a small number that never changes (web/src/lib/
result-numbers.ts). A person then points at a result the way they would
across a table: "animate 2", "like 1 but at night". This module is the
server's half:

- the list the PAGE sends with a turn (`clean`: number, kind, a few words),
  bounded and stripped like everything that arrives from a browser;
- the paragraph that tells the model what the numbers are (`note`,
  prompts/creative_guide_results.txt);
- the check on any number a tool call names (`one`, `stills`): **a closed
  set**. The model may name a result only by a number from the list it was
  shown, exactly as it may name a reference only by an id a tool returned
  -- never an address, never a guess. An effect naming a number that is not
  there, or one of the wrong kind (a clip effect on a still), is REFUSED
  with what does exist, and the model gets that back as the call's result.
  A make that lists numbers keeps the stills among them and drops the rest.

With no list at all (an older tab, the dock, a plan's step) a number means
nothing and is dropped. The studio binds a number to the actual picture;
nothing here knows where a result lives.

Pure: no database, no model, nothing from `app/`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "creative_guide_results.txt"

KINDS = ("still", "clip", "scene")
# what an effect takes (src/effects.py `takes`) -> the kind of result that is
TAKES = {"image": "still", "video": "clip"}

MAX_RESULTS = 40          # the newest results a turn is told about
MAX_NUMBER = 999
LABEL_MAX = 80
MAX_NAMED = 4             # results one make may be held to

_TAG = re.compile(r"<[^>]{0,400}>")
_ADDRESS = re.compile(r"(?i)\b(?:https?://|www\.)\S+")


class Unknown(ValueError):
    """A number that names no result, or one of the wrong kind. The message
    says what does exist, for the model to read."""


def _number(raw) -> Optional[int]:
    """A result's number out of whatever arrived: 3, "3", "#3", 3.0."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    if isinstance(raw, str):
        text = raw.strip().lstrip("#").strip()
        raw = int(text) if text.isdigit() else None
    return raw if isinstance(raw, int) and 0 < raw <= MAX_NUMBER else None


def _label(raw) -> str:
    if not isinstance(raw, str):
        return ""
    text = " ".join(_ADDRESS.sub(" ", _TAG.sub(" ", raw)).split()).replace('"', "'")
    if len(text) > LABEL_MAX:
        text = text[:LABEL_MAX].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return text


def clean(raw) -> list[dict]:
    """[{n, kind, label}] out of the form field -- a list, or the JSON text
    of one. Each number once (the first wins), a known kind, a plain bounded
    label; anything else dropped, never raised. Newest MAX_RESULTS kept, in
    number order."""
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw or "[]")
        except (TypeError, ValueError):
            return []
    if not isinstance(raw, list):
        return []
    seen: dict[int, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        n = _number(item.get("n"))
        kind = str(item.get("kind") or "").strip().lower()
        if n is None or kind not in KINDS or n in seen:
            continue
        seen[n] = {"n": n, "kind": kind, "label": _label(item.get("label"))}
    return [seen[n] for n in sorted(seen)][-MAX_RESULTS:]


def _line(result: dict) -> str:
    return f"#{result['n']} {result['kind']}" + (f" — \"{result['label']}\"" if result["label"]
                                                 else "")


def listing(results: Iterable[dict]) -> str:
    return "; ".join(_line(r) for r in results)


def note(results: Optional[list]) -> str:
    """What a turn's last message says about the numbered results, or ""
    when there are none (the turn is then exactly the turn it was)."""
    if not results:
        return ""
    try:
        return PROMPT.read_text().strip().replace("{results}", listing(results))
    except OSError:
        return ""


def one(raw, results: Optional[list], *, takes: str) -> Optional[int]:
    """The number an effect call named with `on`, held to the list.

    None when nothing was named -- or when there is no list to hold it to.
    Raises Unknown for a number that is not a result, or a result an effect
    that `takes` ("image" | "video") cannot act on."""
    if raw is None or raw == "" or results is None:
        return None
    n = _number(raw)
    known = {r["n"]: r for r in results}
    if n is None or n not in known:
        have = listing(results) or "none yet"
        raise Unknown(f"there is no result #{raw}; the results are: {have}")
    wanted = TAKES.get(takes)
    if wanted and known[n]["kind"] != wanted:
        fit = [r for r in results if r["kind"] == wanted]
        raise Unknown(
            f"#{n} is a {known[n]['kind']} and this effect takes a {wanted}"
            + (f"; the {wanted}s are: {listing(fit)}" if fit else f"; there is no {wanted} yet"))
    return n


def stills(raw, results: Optional[list]) -> list[int]:
    """The numbers a make named in `results`, kept where they are stills on
    the list -- in the order named, each once, at most MAX_NAMED. A number
    that is not a still is dropped (a clip or a scene cannot be a
    reference for a new picture); with no list, all of them are."""
    if results is None or not isinstance(raw, (list, tuple)):
        return []
    ok = {r["n"] for r in results if r["kind"] == "still"}
    out: list[int] = []
    for item in raw:
        n = _number(item)
        if n is not None and n in ok and n not in out:
            out.append(n)
    return out[:MAX_NAMED]


__all__ = ["KINDS", "TAKES", "MAX_RESULTS", "MAX_NUMBER", "LABEL_MAX", "MAX_NAMED", "Unknown",
           "clean", "listing", "note", "one", "stills"]
