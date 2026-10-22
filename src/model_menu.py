"""The models a step can be made on, as the brain is shown them (2026-10-11;
item 12 of docs/tasks/task-studio-agent.md, from invideo's plan cards: each
step names the model it will run on, and the person can change it).

Until now a still was drawn on whatever the composer's picker held and a
scene's Render card opened on a default, whatever the work was: a poster
with words on it and a face held to five photos went to the same model.
The studio already knows what each model is for -- every row of
fal.IMAGE_MODELS carries a `note`, every clip model a line in
pricing.CATALOG_MODELS -- and the picker and the public catalogue draw
from those. This module hands the brain the SAME rows (`for_model`, behind
the read tool `list_models`), so what it proposes comes from the tables
and never from what a model happens to believe about another model.

A proposal is advice on a card, never a decision:

- **a still**: `make_image {model}` puts that model on the step card, where
  the person can change it before Approve; the card's price follows the
  model shown.
- **a scene**: `make_video {model}` is only where the scene's Render card
  OPENS (`shot["render_model"]`, providers.render_default). The renderer,
  its price and the one button that spends are still the card's. A plan's
  render step is priced on that same default, so there the proposal is the
  model the step's own Render button names beside its price -- a click that
  always waits for the person.

A closed set, like every id the brain handles: `image_id` / `video_id` keep
an id only when the tables have it, and anything else is dropped -- the
step is then made on what the person had picked, exactly as before.

`image_menu` is also what GET /api/image-models answers (app.api delegates
here), so the picker and the brain cannot be shown different lists.

`src/` never imports `app/`.
"""
from __future__ import annotations

from typing import Optional

TOOL = "list_models"

# the picker's id for Gemini's image model on the studio key (the others
# are fal.IMAGE_MODELS' own keys)
NANO_ID = "nano"

WHY_MAX = 140


def image_menu(account_id: Optional[int] = None) -> dict:
    """{"items": [{id, provider, label, note, references, credits}],
    "default"} -- the models that can draw a still for this account, each
    with what one costs. Nano Banana needs the Gemini key, the rest FAL_KEY."""
    from . import fal, nano_banana, pricing

    items = []
    if nano_banana.has_key(account_id):
        pro = "pro" in nano_banana.MODEL
        items.append({"id": NANO_ID, "provider": "nano",
                      "label": "Nano Banana Pro" if pro else "Nano Banana",
                      "note": "Gemini's image model, on the studio key; takes references.",
                      "references": True,
                      "credits": pricing.still_credits(nano_banana.MODEL)})
    if fal.has_key(account_id):
        for opt in fal.image_options():
            items.append({"id": opt["id"], "provider": "fal", "label": opt["label"],
                          "note": opt["note"], "references": opt["references"],
                          "credits": pricing.credits_for(pricing.usd_micros(opt["usd"]))})
    default = items[0]["id"] if items else NANO_ID
    return {"items": items, "default": default}


def video_menu(account_id: Optional[int] = None) -> list[dict]:
    """[{id, label, note, tier, seconds, frame, credits}] -- the clip models
    a scene can be rendered on, from the public catalogue's own rows:
    `credits` is what a `seconds`-long clip costs at `frame`, priced by the
    estimators the Render card prices with. [] with no renderer key."""
    from . import fal, pricing

    try:
        if not fal.has_key(account_id):
            return []
        return [{"id": row["model"], "label": row["name"], "note": row["blurb"],
                 "tier": row["tier"], "seconds": row["seconds"], "frame": row["frame"],
                 "credits": row["credits"]}
                for row in pricing.catalog_models()]
    except Exception:
        return []


def image_id(raw) -> str:
    """A still model's id when the tables have it, else ""."""
    from . import fal

    name = raw.strip() if isinstance(raw, str) else ""
    return name if name == NANO_ID or name in fal.IMAGE_MODELS else ""


def video_id(raw) -> str:
    """A clip model's id when the table has it, else ""."""
    from . import fal

    name = raw.strip() if isinstance(raw, str) else ""
    return name if name in fal.VIDEO_MODELS else ""


def clean_why(raw) -> str:
    """Why this model, as one short plain line. "" for anything else."""
    if not isinstance(raw, str):
        return ""
    text = " ".join(raw.split())
    if len(text) > WHY_MAX:
        text = text[:WHY_MAX].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return text


def for_model(account_id: Optional[int] = None) -> str:
    """What list_models hands the brain: every model this account can use,
    by id, with the studio's own line about it and what it costs. No vendor
    pages and no addresses."""
    stills = image_menu(account_id)["items"]
    clips = video_menu(account_id)
    lines = []
    if stills:
        lines.append("STILL MODELS -- pass an id as `model` to make_image:")
        for m in stills:
            takes = "takes references" if m["references"] else "no reference input"
            lines.append(f"- {m['id']} -- {m['label']}: {m['note']} ({takes}; "
                         f"{m['credits']} credits a still)")
    if clips:
        lines.append("CLIP MODELS -- pass an id as `model` to make_video. It only sets where "
                     "the scene's Render card opens; the person picks and pays there:")
        for m in clips:
            lines.append(f"- {m['id']} -- {m['label']}: {m['note']} (about {m['credits']} "
                         f"credits for a {m['seconds']}s clip at {m['frame']})"
                         + routing_line(m["id"]))
    if not lines:
        return "No model can be listed right now; leave `model` out."
    lines.append("Credits are for weighing one model against another. The card shows the "
                 "price; do not quote one yourself.")
    return "\n".join(lines)


SPEC = {
    "name": TOOL,
    "description": (
        "Read the models the studio can make on: every still model and every clip model "
        "this person can use, by id, with what each is for and what it costs. Costs "
        "nothing. Call it before you pass `model` to make_image or make_video -- never "
        "guess an id."),
    "input_schema": {"type": "object", "properties": {}},
    "write": False,
}

# the two arguments a make gains
MODEL_PROPERTY = {
    "type": "string",
    "description": "Optional: the id of the model to make this on, exactly as list_models "
                   "gave it, when the work plainly suits one (words in the picture, a face "
                   "to hold from references, a cheap first look). Leave it out to use what "
                   "the person has picked.",
}
WHY_PROPERTY = {
    "type": "string",
    "description": "Optional, with `model`: why that model, in a few plain words the person "
                   "will read on the card.",
}


__all__ = ["TOOL", "NANO_ID", "WHY_MAX", "image_menu", "video_menu", "image_id", "video_id",
           "clean_why", "for_model", "SPEC", "MODEL_PROPERTY", "WHY_PROPERTY",
           "routing_line", "slot_preference", "label_for"]


def routing_line(model: str) -> str:
    """The rule a READY parked slot carries (fal.SLOTS routing), as one
    clause on its menu line; "" for every other model."""
    from . import fal
    rule = fal.slot_routing(model)
    if not rule:
        return ""
    lo, hi = rule["single_shot_seconds"]
    return (f" -- prefer it for a single continuous shot of {lo}-{hi}s, or a scene held "
            f"to {rule['reference_heavy']} or more references")


def slot_preference(seconds, shots, refs: int = 0) -> Optional[tuple[str, str]]:
    """(model id, why) when a READY parked slot's routing rule fits the
    scene -- a single shot of the slot's length, or a reference-heavy one
    -- else None. With no slot ready (today) this is always None, so
    nothing a make proposes changes."""
    from . import fal
    secs = seconds if isinstance(seconds, int) and not isinstance(seconds, bool) else None
    count = shots if isinstance(shots, int) and not isinstance(shots, bool) else None
    for key in fal.ready_slots():
        rule = fal.slot_routing(key) or {}
        lo, hi = rule.get("single_shot_seconds", (0, -1))
        label = fal.SLOTS[key]["label"]
        if count == 1 and secs is not None and lo <= secs <= hi:
            return key, f"{label}: a single continuous take of {secs}s"
        if refs >= int(rule.get("reference_heavy", 10**9)):
            return key, f"{label}: a scene held to {refs} references"
    return None


def label_for(model) -> Optional[str]:
    """The public name of whatever made a render -- "FLUX.2 Pro",
    "Kling 3 Turbo Pro", "Nano Banana Pro", "Topaz upscale" -- from the
    tables the pickers read, or None for an id none of them knows.

    The Library's viewer titles a render with this (2026-10-19, Mike's
    call: the MODEL, never the platform that hosted it -- "fal" is not a
    name a person picked). A row stores the model id it was logged under
    (fal.IMAGE_MODELS / VIDEO_MODELS keys, effects.EFFECTS keys, Gemini's
    own model string); an endpoint path is matched too, for older rows."""
    from . import effects, fal, pricing

    name = model.strip() if isinstance(model, str) else ""
    if not name:
        return None
    spec = fal.IMAGE_MODELS.get(name)
    if spec and spec.get("label"):
        return spec["label"]
    for _provider, key, public, _blurb in pricing.catalog_rows():
        if key == name:
            return public
    spec = effects.EFFECTS.get(name)
    if spec and spec.get("label"):
        return spec["label"]
    low = name.lower()
    if low.startswith("gemini") and "image" in low:
        return "Nano Banana Pro" if "pro" in low else "Nano Banana"
    if low == NANO_ID:
        return "Nano Banana"
    # an endpoint path ("fal-ai/flux-2-pro/edit") names the row it belongs to
    for key, spec in fal.IMAGE_MODELS.items():
        if name in (spec.get("endpoint"), spec.get("edit")) and spec.get("label"):
            return spec["label"]
    for key, spec in fal.VIDEO_MODELS.items():
        if name in (spec.get("t2v"), spec.get("i2v")):
            return next((p for _pr, k, p, _b in pricing.catalog_rows() if k == key), None)
    return None
