"""The direct generators: one prompt, one model, one priced button
(2026-10-22, Mike: "make it for image too"; docs/tasks/task-direct-generators.md).

The studio's Create box is a conversation -- the brain decides whether to
talk or make, and a clip is always a scene held to the person's photos.
Someone who already knows the model they want gets nothing from that, so
/studio/image and /studio/video are the other door: pick a model, type a
prompt, see the price, press Generate. The pick is final there (in the
chat the brain may propose one; here nobody proposes anything).

Everything here is a PROJECTION of the tables that already price the
studio's work, never a copy:

- the video menu is the public catalogue's rows (pricing.catalog_rows,
  ready slots included) with each model's legal lengths and resolutions
  off providers.model_options and its text-to-video frames off
  fal.T2V_ASPECTS;
- the image menu is model_menu.image_menu (the composer's own picker),
  with the frames and the reference cap added;
- a quote is providers.check_render_choice / fal.image_usd at the pick,
  converted by ledger.charge_credits -- THE number a hold takes -- so the
  button cannot show a price the hold would not charge.

A choice off a model's legal set is REFUSED (ValueError, the route's
400), never clamped. Credits only: nothing here hands a dollar figure to
the studio.

TEXT-TO-VIDEO WITHOUT A PHOTOGRAPH (Mike's call, the same day): a clip
made here needs no reference. The reference gate (preprod.reference_gate)
still guards every SCENE -- consistency across shots is what it protects,
and one free-standing clip has no shots to keep consistent. Nothing here
writes a scene.

`src/` never imports `app/`.
"""
from __future__ import annotations

from typing import Optional

# the most pictures a still is sent with from the direct page, the
# composer's own cap (app.api.MAX_IMAGE_REFS)
IMAGE_REF_CAP = 12
# the frame a clip opens on when the model takes it: the platform vertical
VIDEO_ASPECT = "9:16"
# the frame a still opens on
IMAGE_ASPECT = "1:1"
PROMPT_MAX = 4000


def clean_prompt(raw) -> str:
    """The prompt as typed, whitespace folded; ValueError when empty or
    past PROMPT_MAX (a wall of text is refused, not cut)."""
    text = " ".join(str(raw or "").split())
    if not text:
        raise ValueError("type what you want to see")
    if len(text) > PROMPT_MAX:
        raise ValueError(f"keep the prompt under {PROMPT_MAX} characters")
    return text


# ── video ──────────────────────────────────────────────────────────────

def video_label(model: str) -> str:
    """A clip model's public name (the catalogue's), else its id."""
    return _label(model)


def _label(model: str) -> str:
    from . import pricing
    for _provider, key, name, _blurb in pricing.catalog_rows():
        if key == model:
            return name
    return model


def video_menu(account_id: Optional[int] = None) -> dict:
    """{"ready", "items": [{id, label, note, seconds (the axis), resolutions,
    resolution, aspects, aspect, credits}], "default", "exempt"} -- every
    advertised clip model with what it can be asked for and what its
    opening pick costs. `ready` False (no renderer key) lists nothing."""
    from . import fal, ledger, providers

    exempt = _exempt(account_id)
    if not fal.has_key(account_id):
        return {"ready": False, "items": [], "default": "", "exempt": exempt}
    from . import pricing
    items = []
    for provider, model, name, blurb in pricing.catalog_rows():
        try:
            spec = providers.model_options(provider, model)
            if not spec["available"]:
                continue
            opening = providers.check_render_choice(provider, model, None, None)
        except ValueError:
            continue
        aspects = list(fal.t2v_aspects(model))
        items.append({
            "id": model, "label": name, "note": blurb,
            "seconds": spec["duration"],
            "resolutions": list(spec["frame"]["values"]),
            "resolution": opening["frame"],
            "aspects": aspects,
            "aspect": VIDEO_ASPECT if VIDEO_ASPECT in aspects else aspects[0],
            "credits": ledger.charge_credits(opening["estimate_usd"]),
        })
    ids = [m["id"] for m in items]
    first = providers.default_model("fal")
    return {"ready": True, "items": items,
            "default": first if first in ids else (ids[0] if ids else ""),
            "exempt": exempt}


def video_quote(account_id: Optional[int] = None, *, model: str,
                seconds=None, resolution: Optional[str] = None,
                aspect: Optional[str] = None, start_frame: bool = False) -> dict:
    """One clip's price at exactly this pick, or ValueError naming the part
    of it the model does not take. {model, label, seconds, resolution,
    aspect, start_frame, credits, charged, usd}; `usd` is for the job's
    hold and log and the route strips it."""
    from . import fal, ledger, providers

    model = (model or "").strip()
    if model not in fal.VIDEO_MODELS:
        raise ValueError(f"there is no video model {model!r}")
    choice = providers.check_render_choice("fal", model, seconds, (resolution or "").strip() or None)
    band = providers.band_for("fal", model, choice["frame"])
    if band.max_seconds is not None and int(choice["duration"]) > band.max_seconds:
        raise ValueError(f"{_label(model)} renders up to {band.max_seconds}s")
    frame = None
    if not start_frame:
        legal = fal.t2v_aspects(model)
        frame = (aspect or "").strip() or (VIDEO_ASPECT if VIDEO_ASPECT in legal else legal[0])
        if frame not in legal:
            raise ValueError(f"{_label(model)} does not render {frame} -- one of {', '.join(legal)}")
    usd = float(choice["estimate_usd"])
    return {"model": model, "label": _label(model),
            "seconds": int(choice["duration"]), "resolution": choice["frame"],
            "aspect": frame, "start_frame": bool(start_frame),
            "credits": ledger.charge_credits(usd),
            "charged": not _exempt(account_id), "usd": usd}


# ── images ─────────────────────────────────────────────────────────────

def image_aspects() -> list[str]:
    from . import fal
    return list(fal.IMAGE_SIZES)


def image_max_refs(model: str) -> int:
    """How many pictures reach `model`: Nano takes the composer's cap, a
    fal model its own (0 for one that draws from text only)."""
    from . import fal, model_menu
    if model == model_menu.NANO_ID:
        return IMAGE_REF_CAP
    return min(IMAGE_REF_CAP, fal.image_max_refs(model))


def image_menu(account_id: Optional[int] = None) -> dict:
    """model_menu.image_menu (the composer's picker, the brain's list) with
    the frames every model takes and each one's reference cap."""
    from . import model_menu

    menu = model_menu.image_menu(account_id)
    items = [{**m, "max_refs": image_max_refs(m["id"])} for m in menu["items"]]
    return {"ready": bool(items), "items": items, "default": menu["default"],
            "aspects": image_aspects(), "aspect": IMAGE_ASPECT,
            "exempt": _exempt(account_id)}


def image_quote(account_id: Optional[int] = None, *, model: str,
                aspect: Optional[str] = None, references: int = 0) -> dict:
    """One still's price, or ValueError. {model, label, aspect, references
    (how many will reach it), credits, charged, usd}."""
    from . import fal, ledger, model_menu, nano_banana, pricing

    model = (model or "").strip()
    aspect = (aspect or "").strip() or IMAGE_ASPECT
    if aspect not in fal.IMAGE_SIZES:
        raise ValueError(f"a still is drawn at one of {', '.join(fal.IMAGE_SIZES)}, not {aspect}")
    try:
        count = max(0, int(references or 0))
    except (TypeError, ValueError):
        raise ValueError("references is a count") from None
    if count > IMAGE_REF_CAP:
        raise ValueError(f"attach up to {IMAGE_REF_CAP} pictures")
    if model == model_menu.NANO_ID:
        label = "Nano Banana Pro" if "pro" in nano_banana.MODEL else "Nano Banana"
        usd = float(pricing.still_usd(nano_banana.MODEL))
        used = count
    elif model in fal.IMAGE_MODELS:
        label = fal.IMAGE_MODELS[model]["label"]
        used = min(count, fal.image_max_refs(model))
        usd = float(fal.image_usd(model, aspect, references=used))
    else:
        raise ValueError(f"there is no image model {model!r}")
    return {"model": model, "label": label, "aspect": aspect, "references": used,
            "credits": ledger.charge_credits(usd), "charged": not _exempt(account_id),
            "usd": usd}


def public(quote: dict) -> dict:
    """A quote as the studio may see it: credits, never dollars."""
    return {k: v for k, v in quote.items() if k != "usd"}


def _exempt(account_id: Optional[int]) -> bool:
    from . import ledger
    try:
        return bool(ledger.credit_exempt(account_id))
    except Exception:                                   # noqa: BLE001
        return False
