"""How to WRITE a prompt for each still model (2026-10-26).

The brain writes the prompt of a still, and until now it wrote the same
kind of prompt for every model: `list_models` said what a model is for and
what it costs, never how it likes to be asked. The vendors do say. This
module is the one place that is written down for stills, as a dated table
read off each vendor's own guide, and `model_menu.for_model` hands each
row to the brain beside the model it describes.

It is advice to the WRITER, not a rewrite at the render boundary:
turning a finished prompt into another shape needs a model, and a still's
prompt is free text the person can read and edit on the card before they
approve. (The clip side, `src/prompts_for.py`, is a pure rewrite behind a
switch; it needs none of this.) Costs nothing, spends nothing, and
`PHANTRA_IMAGE_PROMPT_TIPS=0` turns it off.

ONLY WHAT A VENDOR ACTUALLY SAYS IS A TIP. Where a guide is silent -- FLUX
1.1 Pro has no first-party guide this studio could read, and no guide
below says anything on negative prompts -- the row says nothing, and the
absence is on purpose. GPT Image 2.5 is written from the GPT Image 2 guide:
the same API family, and no separate 2.5 guide was found. Every row carries
the date it was read and where; re-read before trusting one.

Pure: no model call, no database, no network.
"""
from __future__ import annotations

import os
from typing import Optional

SWITCH_ENV = "PHANTRA_IMAGE_PROMPT_TIPS"

_GPT = {
    "checked": "2026-10-26",
    "tip": ("Write it in this order: scene, subject, specific details, what the image is for, "
            "constraints. Name the real things in it and give lighting, materials and lens "
            "feel instead of praise words. Put any words that must appear in quotes with "
            "their style and placement, and add 'no extra text'. Put exclusions "
            "(no watermark, no logos) in a final constraints line. For an edit on a "
            "reference, say 'change only X' and 'keep everything else the same', and name "
            "each reference by its role."),
    "sources": ("https://fal.ai/learn/tools/prompting-gpt-image-2",),
}

TIPS: dict[str, dict] = {
    # the studio key's Gemini image model (model_menu.NANO_ID) and fal's copy
    # of it speak to the same Google guide
    "nano": {
        "checked": "2026-10-26",
        "tip": ("Write subject, scene, action, context and style, in that order, then "
                "framing, lighting and aspect. For words in the picture, give the exact "
                "text with its font style and placement. With references, say what each "
                "one is for ('image 1 for the pose, image 2 for the style'). Check small "
                "text for spelling."),
        "sources": ("https://blog.google/products/gemini/prompting-tips-nano-banana-pro/",),
    },
    "flux2-pro": {
        "checked": "2026-10-26",
        "tip": ("Lead with the subject, then action, style and context, and put the "
                "requirement that matters most first: earlier words weigh more. Keep the "
                "words consistent (no 'bright sunny day' with 'moody shadows'). Exact text "
                "goes in quotes with its placement and typeface. Brand colours can be hex "
                "codes. For an edit, describe only the change."),
        "sources": ("https://fal.ai/learn/devs/flux-2-prompt-guide",),
    },
    "seedream4.5": {
        "checked": "2026-10-26",
        "tip": ("About 30 to 100 words: subject, style, composition, lighting and "
                "atmosphere, then camera detail, with the most important first. A long "
                "prompt confuses it. To rule out a look, state the look wanted ('not "
                "cartoon-like'). To blend references, say what to keep from each."),
        "sources": ("https://fal.ai/learn/devs/seedream-v4-5-prompt-guide",),
    },
    "ideogram4.5": {
        "checked": "2026-10-26",
        "tip": ("Put the exact words in quotes, early in the prompt, short, and say where "
                "they go. Describe the lettering (bold sans-serif, formal script), not a "
                "font name. Give each text block its own words, style and place, top to "
                "bottom. Keep the scene simple; long body copy belongs in a design tool."),
        "sources": ("https://docs.ideogram.ai/prompting/text-in-images.md",),
    },
    "gpt-image-2": _GPT,
    "gpt-image-2.5-flare": _GPT,
    "gpt-image-2.5-sunburst": _GPT,
}
# fal's copy of Nano Banana Pro answers to the same guide
TIPS["nano-banana-pro"] = TIPS["nano"]


def enabled() -> bool:
    """On unless plainly switched off; read per call like every posture."""
    return (os.environ.get(SWITCH_ENV) or "").strip().lower() not in {"0", "false", "no", "off"}


def tip_for(model: str) -> Optional[str]:
    """The one paragraph for a still model's id, or None: a model with no
    row (or the switch off) is shown to the brain as it always was."""
    if not enabled():
        return None
    row = TIPS.get(model)
    return row["tip"] if row else None


__all__ = ["SWITCH_ENV", "TIPS", "enabled", "tip_for"]
