"""
Recipe effects (2026-10-26, Mike: "now i should add more effects"; the
Higgsfield comparison in docs/tasks/task-effect-recipes.md).

A recipe is what Higgsfield's top effects are: not a model of their own but
a carefully written prompt run on a video model with the person's photo.
Here each recipe is a row of src/effects.py like any other -- the same
quote, the same Approve, the same hold, cap, generations row and Assets
wall -- whose prompt is fixed and lives in prompts/effects/<id>.txt. The
person may add one detail where a recipe has a slot for it (the product,
the place it lands in); everything else is the recipe's.

Every recipe runs on ONE model, read off fal.VIDEO_MODELS so the endpoint
and the price per second are that table's, never a second copy: Kling 3
Turbo Pro image-to-video (1080p, $0.14/s, 3-15 s; a 5 s run is 168
credits at the house markup). Listed only with PHANTRA_EFFECT_RECIPES=1,
so the composer's gallery and the connector carry them only once Mike has
seen their examples; the Effects page shows a tile only once it has one.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ENV = "PHANTRA_EFFECT_RECIPES"
MODEL = "kling3-turbo-pro"
MODEL_LABEL = "Kling 3 Turbo Pro"     # what the panel says made it (never "fal")
DURATIONS = ("5", "10")
CHECKED = "2026-10-26"
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "effects"
SOURCE_DOC = "docs/tasks/task-effect-recipes.md"

# id -> what the gallery says. `hint` names the optional box when the recipe
# has a {detail} slot; `tags` place it on the Effects page (product / transform).
RECIPES: dict[str, dict] = {
    "float_drop": {"label": "Float Drop", "tags": ("product",),
                   "blurb": "They fall back in slow motion while everything they hold floats past the camera.",
                   "hint": "The product to linger on (optional)"},
    "window_grab": {"label": "Window Grab", "tags": ("product",),
                    "blurb": "A smash through a car window, the product snatched, a getaway run.",
                    "hint": "The product on the seat (optional)"},
    "gone": {"label": "Gone", "tags": ("transform",),
             "blurb": "They vanish in an instant and their empty clothes drop to the floor."},
    "iris_dive": {"label": "Iris Dive", "tags": ("transform",),
                  "blurb": "The camera dives into their eye and comes out in a new world.",
                  "hint": "Where the camera comes out (optional)"},
    "echo_crowd": {"label": "Echo Crowd", "tags": ("transform",),
                   "blurb": "Copies of them fill the scene, every one moving in sync."},
    "time_stop": {"label": "Time Stop", "tags": ("transform",),
                  "blurb": "They freeze mid-jump while the world keeps moving around them."},
    "city_giant": {"label": "City Giant", "tags": ("transform",),
                   "blurb": "They tower over a city street, taller than the buildings."},
    "meltdown": {"label": "Meltdown", "tags": ("transform",),
                 "blurb": "They melt into a glossy puddle, clothes and all."},
    "pocket_me": {"label": "Pocket Me", "tags": ("transform",),
                  "blurb": "A tiny copy of them in their hands, and a smaller one in its, forever."},
    "overhead_flip": {"label": "Overhead Flip", "tags": ("transform",),
                      "blurb": "The camera flips over their head and lands them somewhere new.",
                      "hint": "Where they land (optional)"},
    # 2026-10-27, Mike: anthology-horror recipes for Halloween beside the
    # Kling / PixVerse templates and the four free looks. Original settings,
    # never a show's name or characters.
    "coven": {"label": "Coven", "tags": ("transform",),
              "blurb": "A ring of candles, black lace and a crown of bone; they look up into the light.",
              "hint": "One more detail (optional): a raven on the shoulder, a spell book"},
    "sideshow": {"label": "Sideshow", "tags": ("transform",),
                 "blurb": "A 1950s carnival tent at night: they bow under a hand-painted banner.",
                 "hint": "What the banner bills them as (optional)"},
    "seance": {"label": "Séance", "tags": ("transform",),
               "blurb": "Candlelight, joined hands, a flame that bends; their eyes roll white.",
               "hint": "One more detail (optional)"},
    "the_hotel": {"label": "The Hotel", "tags": ("transform",),
                  "blurb": "The camera glides down a red-gold Art Deco hallway to where they wait.",
                  "hint": "What they are holding or wearing (optional)"},
    # 2026-10-27, Mike: "Ai halloween costume try on ... I want this out by
    # today": the photo spins into a costume the person names, face kept.
    "costume_try_on": {"label": "Costume Try-On", "tags": ("transform",),
                       "blurb": "They spin once and come back around in the costume, same face.",
                       "hint": "The costume (optional): a vampire, a pirate, Frankenstein's bride"},
}


def enabled() -> bool:
    return (os.environ.get(ENV) or "").strip() == "1"


def is_recipe(effect: str) -> bool:
    return (effect or "").strip() in RECIPES


def require_enabled(effect: str) -> None:
    """ValueError when a recipe is named on a server that has them off."""
    if is_recipe(effect) and not enabled():
        raise ValueError(f"the recipe effects are not switched on for this server ({ENV}=1)")


@lru_cache(maxsize=None)
def _sections(name: str) -> tuple[str, str, str]:
    """(prompt, detail line, default) from prompts/effects/<name>.txt."""
    text = (PROMPTS_DIR / f"{name}.txt").read_text()
    body, _, rest = text.partition("---detail---")
    detail, _, default = rest.partition("---default---")
    return body.strip(), detail.strip("\n"), default.strip()


def has_detail(name: str) -> bool:
    return "{detail}" in _sections(name)[0]


def prompt_for(name: str, note: str = "") -> str:
    """The prompt the model is sent: the recipe, with the person's one
    detail worked into its slot (or the recipe's default there)."""
    body, detail, default = _sections(name)
    note = " ".join((note or "").split())
    if name == "costume_try_on" and note:
        # a costume picked from the list (the preview's "Make it a video")
        # arrives by name; it is told to the model in full
        from . import costumes
        note = costumes.describe(note)
    fill = detail.replace("{note}", note) if note and detail else (default if "{detail}" in body else "")
    return body.replace("{detail}", fill).strip()


def row(name: str) -> dict:
    """The src/effects.py row for one recipe."""
    from . import fal
    spec = fal.VIDEO_MODELS[MODEL]
    rate = float(spec["prices"][spec["default_resolution"]])
    meta = RECIPES[name]
    return {
        "label": meta["label"], "category": "video_effect",
        "note": f"{meta['blurb']} A written recipe on {MODEL}, one photo in.",
        "endpoint": spec["i2v"], "takes": "image",
        "field": spec.get("image_field", "image_url"), "as_list": False,
        "sources": (1, 1), "prompt": "optional" if has_detail(name) else "none",
        "output": "video",
        "options": {"duration": {"values": DURATIONS, "default": DURATIONS[0]}},
        "fixed": {},
        "price": lambda o, p, rate=rate: rate * int(o["duration"]),
        "recipe": True, "tags": tuple(meta["tags"]), "hint": meta.get("hint", ""),
        "blurb": meta["blurb"], "model": MODEL, "model_label": MODEL_LABEL, "rate": rate,
        "source": spec["source"], "checked": CHECKED,
    }
