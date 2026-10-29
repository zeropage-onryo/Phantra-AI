"""Effects by name: the words a person uses for a look, and the id behind
them (2026-10-22, the overnight Vesper stream, group 6 checkbox 3 of
docs/tasks/task-overnight-2026-10-22.md; docs/tasks/task-vesper-v2.md).

"Give this a noir grade" has to become an apply_effect proposal for the
effect `noir`, drawn as a priced card in the thread. The brain is handed
the effects table at runtime (`guide_tools.effects_for_model`, which reads
`effects.EFFECTS`) and never a copy of it, so a look that lands on the
table tomorrow is known to it tomorrow. What the table does NOT carry is
the plain words people reach for -- "black and white", "make it
vertical", "that 2000s flash look" -- so this module is the alias list
beside it: the ids the free-looks stream is adding (`film_grade`, `noir`,
`flash_2000s`, `crash_zoom`, `vertical_ready`, and the bundle
`make_it_pro`) with the words each answers to, and `resolve` to turn a
person's phrase (or the brain's near-miss) into the id the table has.

Two rules:

- **The table is the authority.** `aliases_for` / `resolve` only ever
  answer with an id that is ON `effects.EFFECTS` right now. A look listed
  here that the table does not carry yet is simply not resolvable (the
  brain is told nothing about it), so this branch is byte-for-byte the
  same product until the looks merge.
- **Nothing here spends.** An id is a name on a proposal; the card and
  `POST /api/effects/run` price and gate it as they always did.

`stub_rows` builds table-shaped rows for the looks that are not on the
table yet, for the plan-stage eval (evals/vesper_plans.py) and the
fake-model test only -- never for the app.
"""
from __future__ import annotations

import re
from typing import Optional

# the free looks (group 2 of the overnight task): id -> label, the words
# people use, and what the eval's stub row says it does. `category` is the
# table's closest existing bucket until the looks stream names its own.
LOOKS: dict[str, dict] = {
    "film_grade": {
        "label": "Film Grade",
        "aliases": ("film grade", "film look", "cinematic grade", "cinematic look", "grade it",
                    "colour grade", "color grade", "letterbox", "2.39", "anamorphic look",
                    "make it cinematic", "film grain"),
        "note": "LUT, grain and an optional 2.39:1 letterbox; free",
    },
    "noir": {
        "label": "Noir",
        "aliases": ("noir", "film noir", "noir grade", "black and white", "black & white",
                    "b&w", "b and w", "monochrome", "greyscale", "grayscale"),
        "note": "black-and-white LUT, vignette and grain; free",
    },
    "flash_2000s": {
        "label": "2000s Flash",
        "aliases": ("2000s flash", "2000s look", "flash look", "disposable camera", "y2k",
                    "point and shoot", "flash pops", "date stamp", "early 2000s"),
        "note": "flash pops, a 2000s grade and a date stamp; free",
    },
    "crash_zoom": {
        "label": "Crash-Zoom Hook",
        "aliases": ("crash zoom", "crash-zoom", "zoom hook", "punch in", "punch-in",
                    "snap zoom", "whip zoom", "hook zoom"),
        "note": "a timed crop zoom on the first beat with a whoosh; free",
    },
    "vertical_ready": {
        "label": "Vertical Ready",
        "aliases": ("vertical ready", "vertical version", "make it vertical", "9:16 version",
                    "for reels", "for tiktok", "for shorts", "portrait crop", "vertical crop"),
        "note": "a centred 9:16 crop; free",
    },
    # the Halloween four (2026-10-27)
    "title_sequence": {
        "label": "Title Sequence",
        "aliases": ("title sequence", "opening titles", "opening credits", "horror titles",
                    "scratched film", "film scratches", "creepy intro", "anthology horror"),
        "note": "sepia, frame jitter, scratches and strobe frames; free",
    },
    "the_ward": {
        "label": "The Ward",
        "aliases": ("the ward", "asylum look", "asylum", "hospital ward", "fluorescent flicker",
                    "flickering lights", "sickly green"),
        "note": "a cold green fluorescent grade with a flicker; free",
    },
    "haunted_manor": {
        "label": "Haunted Manor",
        "aliases": ("haunted manor", "haunted house", "haunted look", "ghost trail",
                    "ghostly", "ghost effect", "spectral"),
        "note": "a sepia-green grade with a ghost trailing the subject; free",
    },
    "found_tape": {
        "label": "Found Tape",
        "aliases": ("found tape", "found footage", "vhs", "vhs look", "camcorder",
                    "old tape", "tracking lines"),
        "note": "VHS softness, chroma split, scanlines and a tracking band; free",
    },
    "make_it_pro": {
        "label": "Make It Pro",
        "aliases": ("make it pro", "pro bundle", "make this pro", "the pro pass",
                    "polish it", "full polish"),
        "note": "Film Grade then Vertical Ready, free, with a priced Sound Pass slot",
    },
}

# words that also mean an effect ALREADY on the table (src/effects.py), so
# "a sound pass" resolves the way the new looks do
STANDING: dict[str, tuple[str, ...]] = {
    "add-sound": ("sound pass", "add sound", "sound design", "ambience", "sfx"),
    "upscale": ("upscale", "4k", "sharpen", "smooth it", "60fps", "slow mo", "slow-mo"),
    "remove-background": ("remove the background", "cut out", "cutout", "transparent background"),
    "reframe": ("reframe", "extend the frame", "outpaint"),
}

_WORD = re.compile(r"[^a-z0-9&:.]+")


def _norm(text) -> str:
    return " " + _WORD.sub(" ", str(text or "").lower()).strip() + " "


def on_table(effect_id: str) -> bool:
    """Whether the table carries this id right now."""
    from . import effects
    return effect_id in effects.EFFECTS


def aliases_for(effect_id: str) -> tuple[str, ...]:
    """The plain words for one effect, ON THE TABLE ONLY; () otherwise."""
    if not on_table(effect_id):
        return ()
    row = LOOKS.get(effect_id)
    if row:
        return tuple(row["aliases"])
    return tuple(STANDING.get(effect_id, ()))


def resolve(text) -> Optional[str]:
    """The effect id a phrase names, or None.

    An exact id wins ("noir", "add-sound", "film_grade" in any of its
    spellings); then the longest alias found in the words, so "black and
    white" beats a shorter match and "make it vertical" is a look, not a
    question. Only ids the table carries are ever returned."""
    from . import effects
    raw = str(text or "").strip()
    if not raw:
        return None
    key = raw.lower().replace("-", "_").replace(" ", "_")
    for candidate in (raw, raw.lower(), key, key.replace("_", "-")):
        if candidate in effects.EFFECTS:
            return candidate
    words = _norm(raw)
    best: tuple[int, str] = (0, "")
    for effect_id in effects.EFFECTS:
        for alias in aliases_for(effect_id):
            if f" {alias} " in words and len(alias) > best[0]:
                best = (len(alias), effect_id)
    return best[1] or None


def names_block() -> str:
    """One line per effect on the table that has plain-word aliases: what
    list_effects appends so the brain knows "noir grade" is `noir`. "" when
    no listed effect has any."""
    lines = []
    for effect_id in _ordered():
        words = aliases_for(effect_id)
        if words:
            lines.append(f"- {effect_id}: said as " + ", ".join(f"“{w}”" for w in words[:6]))
    if not lines:
        return ""
    return ("Looks and finishes people name in plain words (pass the id to apply_effect "
            "when they say one of these):\n" + "\n".join(lines))


def _ordered() -> list[str]:
    from . import effects
    return [k for k in effects.EFFECTS if aliases_for(k)]


def stub_rows() -> dict[str, dict]:
    """Table-shaped rows for the looks NOT on the table yet -- the shape
    `effects.catalogue` / `check_options` / `check_prompt` read. For the
    plan-stage eval and the fake-model test only: the app never reads
    these, and a row here has no endpoint, so nothing could run on one."""
    out = {}
    for effect_id, row in LOOKS.items():
        if on_table(effect_id):
            continue
        out[effect_id] = {
            "label": row["label"], "category": "finish", "note": row["note"],
            "endpoint": None, "takes": "video", "field": "video_url", "as_list": False,
            "sources": (1, 1), "prompt": "none", "output": "video",
            "options": {}, "fixed": {}, "price": lambda o, p: 0.0,
            "source": "local (no provider)", "checked": "2026-10-22", "stub": True,
        }
    return out


__all__ = ["LOOKS", "STANDING", "on_table", "aliases_for", "resolve", "names_block",
           "stub_rows"]
