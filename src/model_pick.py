"""
Which clip model for what: the connector's `recommend_model` (2026-10-11,
docs/tasks/task-connector-overnight.md PR 3).

A PURE ranking over the public catalogue (`pricing.catalog_models`: the
same rows the site's /models page prints, priced by the estimators the
Render card prices with) plus what the account has kept per model
(`outcomes`, handed in as counts). No model call, no guess at a price: a
pick's credits come from `providers.check_render_choice`, the Queue's own
check, for the seconds asked at the model's default frame.

The ranking is a handful of traits read off the words (`traits`): cheap,
quality, sound, people, long, realism. Each trait moves the models that
answer it; the words are a person's, so a trait that is not there moves
nothing. Every pick carries ONE sentence saying why, in the catalogue's
own words -- the thing a chat can repeat -- and the number of clips the
person kept on it when there were enough to mean anything.
"""
from __future__ import annotations

from typing import Any, Optional

TRAITS: dict[str, tuple[str, ...]] = {
    "cheap": ("cheap", "cheapest", "draft", "test", "rough", "quick", "budget", "affordable",
              "low cost", "low-cost", "sketch", "try", "iterate", "experiment"),
    "quality": ("final", "hero", "client", "quality", "premium", "best", "polish", "polished",
                "deliver", "deliverable", "4k", "1080", "flagship", "top"),
    "sound": ("sound", "audio", "dialogue", "dialog", "voice", "speech", "talking", "music",
              "lip"),
    "people": ("people", "person", "face", "faces", "actor", "character", "portrait",
               "human", "hands", "skin"),
    "long": ("long", "longer", "extended", "20s", "25s", "30s", "minute"),
    "realism": ("realistic", "realism", "photoreal", "documentary", "natural", "real"),
}
# catalogue blurbs that say "with sound" -- read off pricing.CATALOG_MODELS
# at rank time, not kept here, so a re-worded catalogue moves this
SOUND_WORDS = ("with sound",)
PEOPLE_WORDS = ("people", "person", "faces")
REALISM_WORDS = ("realism", "realistic")
KEEP_MIN = 3              # clips made before a keep rate is worth a sentence
PICKS = 3


def traits(what: str) -> set[str]:
    """The traits the words ask for. Plain substring matches on lowered
    words; a number of seconds is read by the caller, not here."""
    text = f" {' '.join((what or '').lower().split())} "
    found = set()
    for trait, words in TRAITS.items():
        if any(f" {w} " in text or f" {w}," in text or f" {w}." in text for w in words):
            found.add(trait)
    return found


def _fits(seconds: Optional[int], low: int, high: int) -> bool:
    return seconds is None or low <= seconds <= high


def rank(what: str, *, seconds: Optional[int] = None, budget_credits: Optional[int] = None,
         draft: Optional[bool] = None, catalogue: list[dict], price,
         kept: Optional[dict[str, tuple[int, int]]] = None,
         default_model: str = "") -> dict[str, Any]:
    """The picks, best first.

    `catalogue` is `pricing.catalog_models()` rows with each model's legal
    length span (`min_seconds`, `max_seconds`) and `draft` frame folded in
    by the caller; `price(model, seconds)` -> (credits, seconds, frame)
    or None when the model cannot make a clip that long; `kept` is
    {model: (made, kept)} for this account. Pure: nothing here reads a
    row or calls anything but `price`."""
    asked = traits(what)
    kept = kept or {}
    considered, picks, skipped = 0, [], []
    for row in catalogue:
        model = row["model"]
        low, high = int(row.get("min_seconds") or 0), int(row.get("max_seconds") or 10**6)
        if seconds is not None and not _fits(seconds, low, high):
            skipped.append({"model": model, "why": f"cannot make a {seconds}s clip "
                                                   f"(it makes {low}-{high}s)"})
            continue
        priced = price(model, seconds)
        if priced is None:
            skipped.append({"model": model, "why": "cannot be priced for that length"})
            continue
        credits, got_seconds, frame = priced
        if budget_credits is not None and credits > int(budget_credits):
            skipped.append({"model": model, "why": f"{credits} credits is over the budget "
                                                   f"of {int(budget_credits)}"})
            continue
        considered += 1
        blurb = (row.get("blurb") or "").lower()
        score, why = 0.0, []
        if "cheap" in asked:
            score += 3.0 / max(1.0, credits / 50.0)          # the cheaper, the more
            why.append(f"{credits} credits for {got_seconds}s is among the cheapest")
        if "quality" in asked:
            tier = row.get("tier")
            score += {"premium": 3.0, "creator": 1.5}.get(str(tier), 0.0)
            if tier == "premium":
                why.append("a premium-tier model")
        if "sound" in asked and any(w in blurb for w in SOUND_WORDS):
            score += 2.5
            why.append("it generates sound with the picture")
        if "people" in asked and any(w in blurb for w in PEOPLE_WORDS):
            score += 2.5
            why.append("the catalogue calls it strong on people")
        if "long" in asked:
            score += min(high, 30) / 10.0
            if high >= 20:
                why.append(f"it makes clips up to {high}s")
        if "realism" in asked and any(w in blurb for w in REALISM_WORDS):
            score += 2.0
            why.append("the catalogue calls it realistic")
        if draft is True:
            if row.get("draft"):
                score += 2.0
                why.append(f"it has a cheaper {row['draft']} draft tier")
            else:
                score -= 1.0
        made, kept_n = kept.get(model, (0, 0))
        if made >= KEEP_MIN:
            rate = kept_n / made
            score += 2.0 * rate
            why.append(f"you kept {kept_n} of the {made} clips made on it")
        if not asked and draft is None:
            # nothing asked for: the studio's default first, then by price
            score += (1.0 if model == default_model else 0.0) + 1.0 / max(1.0, credits / 100.0)
        if not why:
            why.append(row.get("blurb") or "a model in the catalogue")
        picks.append({"model": model, "name": row.get("name") or model,
                      "tier": row.get("tier"), "credits": credits, "seconds": got_seconds,
                      "frame": frame, "draft": row.get("draft") or None,
                      "kept": ({"made": made, "kept": kept_n} if made else None),
                      "reason": "; ".join(why), "_score": score})
    picks.sort(key=lambda p: (-p["_score"], p["credits"], p["model"]))
    for p in picks:
        p.pop("_score", None)
    return {"picks": picks[:PICKS], "considered": considered, "asked": sorted(asked),
            "skipped": skipped}


__all__ = ["TRAITS", "KEEP_MIN", "PICKS", "traits", "rank"]
