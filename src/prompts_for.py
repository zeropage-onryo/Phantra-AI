"""The prompt a video model is sent, shaped for THAT model (2026-10-11;
step 7 item 2 of docs/tasks/task-higgsfield-shape.md).

Until now every model on fal was sent the same text: the motion directive,
then the scene's memory and the shot (see the task doc's audit). The
vendors do not ask for the same thing. This module is the one place that
difference is written down, as a dated table read off each vendor's own
guide, and `render()` is the one function that applies it at the render
boundary (`fal.generate_for_shot`).

OFF BY DEFAULT. `PHANTRA_PROMPT_DIALECTS=1` turns it on. It changes what
a PAID render is sent, and the rule for this work was that nothing is
rendered during verification -- so it ships switched off, byte for byte
the old behaviour, until somebody has looked at real output with it on.
When it is on, the rule that shaped a prompt is written on the
generation (`prompt_rule`), so the keep rate with and without it can be
read on the Dev Studio's Stats tab instead of argued about.

ONLY WHAT A VENDOR ACTUALLY SAYS IS A RULE. Two are implemented:

- `motion` -- with a start frame, the prompt carries what moves, the
  camera and the sound, and does not re-describe what the image shows.
  LTX says it in so many words, Alibaba says the image sets subject,
  scene and style, fal's Seedance schema defines the prompt as the
  desired motion, and Kling's image-to-video guide asks for subject and
  movement. Applied to a timed scene's SHOT only: its own sentence is
  already one camera setup and one action. A scene that renders whole is
  left as written -- nothing here can tell its motion from its
  description without a model, and this module calls none.
- `negative_field` -- the Avoid list leaves the prompt and goes in the
  API's `negative_prompt`, each item naming the unwanted thing with no
  "no" in front. Only Veo's endpoint on fal takes the field, and Google's
  guide says never to write "no" or "don't" in a prompt.

Not implemented, because no first-party page was found that says it: a
hard prompt length for any model (Kling's 2,500 characters is a
recommendation, and is only noted), a rule against re-describing the
image for Veo, and any dialogue syntax (the scenes here are written with
"No background music" and diegetic sound, which all five accept as plain
sentences).

Pure: no model call, no database, no network.
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

SWITCH_ENV = "PHANTRA_PROMPT_DIALECTS"
UNCHANGED = "as written"

# Per platform (fal.VIDEO_MODELS[...]["platform"]). Every row was read on
# the date it carries; re-read the sources before trusting one.
RULES: dict[str, dict[str, Any]] = {
    "kling": {
        "checked": "2026-10-11",
        "anchored": "motion",
        "negative_field": False,
        # a recommendation on fal's schema, not a limit: noted, never cut
        "soft_max_chars": 2500,
        "sources": (
            "https://kling.ai/quickstart/image-to-video-guide",
            "https://fal.ai/models/fal-ai/kling-video/v3/turbo/pro/image-to-video/llms.txt",
        ),
    },
    "ltx": {
        "checked": "2026-10-11",
        "anchored": "motion",
        "negative_field": False,
        "sources": (
            "https://ltx.io/blog/ltx-2-3-prompt-guide",
            "https://ltx.io/blog/ltx-2-5-prompt-guide",
            "https://fal.ai/models/fal-ai/ltx-2.3/image-to-video/llms.txt",
        ),
    },
    "wan": {
        "checked": "2026-10-11",
        "anchored": "motion",
        "negative_field": False,
        "sources": (
            "https://www.alibabacloud.com/help/en/model-studio/wan3-video-generation-prompt-guide",
            "https://fal.ai/models/alibaba/wan-3.0/image-to-video/llms.txt",
        ),
    },
    "seedance": {
        "checked": "2026-10-11",
        "anchored": "motion",
        "negative_field": False,
        "sources": (
            "https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt",
            "https://docs.byteplus.com/en/docs/modelark/seedance-2-0-prompt-guide",
        ),
    },
    "veo": {
        "checked": "2026-10-11",
        # Google says the image becomes the first frame and nothing about
        # leaving its content out, so the text is not shortened
        "anchored": "full",
        "negative_field": True,
        "sources": (
            "https://fal.ai/models/fal-ai/veo3.1/image-to-video/llms.txt",
            "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide",
        ),
    },
    "grok": {
        "checked": "2026-10-23",
        # fal's i2v schema: the prompt is the "desired changes or motion" --
        # the start frame carries the picture, so an anchored shot is sent
        # as its motion and sound; there is no negative field
        "anchored": "motion",
        "negative_field": False,
        "sources": (
            "https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video/llms.txt",
            "https://fal.ai/models/xai/grok-imagine-video/v1.5/text-to-video",
        ),
    },
}


def enabled() -> bool:
    """Read per call, like every other posture: a test, or a person at a
    terminal, can flip it without a restart. Anything that is not plainly
    on is off."""
    return (os.environ.get(SWITCH_ENV) or "").strip().lower() in {"1", "true", "yes", "on"}


def rule_for(model: str) -> Optional[dict]:
    """The dated rule row for a fal video model, or None: a model this
    table does not know is sent its prompt as written."""
    try:
        from . import fal
        return RULES.get(fal.model_spec(model)["platform"])
    except Exception:                                           # noqa: BLE001
        return None


_AVOID = re.compile(r"(?:^|(?<=[\s.]))(?:\d\s*[.)]\s*)?AVOID\s*:\s*(.+?)(?=\n\s*\n|\Z)",
                    re.S | re.I)
_SOUND = re.compile(r"(No background music\.[^\n]*?)(?=\s*(?:\d\s*[.)]\s*)?AVOID\s*:|\n|\Z)",
                    re.S | re.I)


def avoid_list(text: Optional[str]) -> tuple[str, list[str]]:
    """(the text with its Avoid list taken out, the list's items). A text
    with no Avoid list comes back as it was, with no items."""
    text = text or ""
    found = _AVOID.search(text)
    if not found:
        return text, []
    items = [re.sub(r"\s+", " ", i).strip(" .;") for i in re.split(r"[,;]", found.group(1))]
    rest = (text[:found.start()].rstrip() + "\n\n" + text[found.end():].lstrip()).strip()
    return rest, [i for i in items if i]


def as_negative(items: list[str]) -> str:
    """The Avoid list as a `negative_prompt`: the unwanted things, named,
    without the "no" a prompt would have put in front of each."""
    named = [re.sub(r"^(?:no|never|without|avoid)\s+", "", i, flags=re.I).strip() for i in items]
    return ", ".join(dict.fromkeys(n for n in named if n))


def sound_line(text: Optional[str]) -> str:
    """The scene's own sound sentence ("No background music. Only ..."),
    or "". Every model here generates sound by default, so the one line
    that says what should be heard travels with a shortened prompt."""
    found = _SOUND.search(text or "")
    return re.sub(r"\s+", " ", found.group(1)).strip() if found else ""


def render(model: str, target: dict, *, anchored: bool) -> dict[str, Any]:
    """What to send for one render: {"prompt", "negative_prompt", "rule",
    "notes"}. `target` is `timeline.render_target`'s answer (its `prompt`
    is what has always been sent; `raw` holds the pieces it was composed
    from). `anchored` is whether a start frame really goes out with it.

    Switched off, or for a model with no row, the answer is the prompt as
    written and an empty negative: nothing changes."""
    base = (target or {}).get("prompt") or ""
    out: dict[str, Any] = {"prompt": base, "negative_prompt": "", "rule": UNCHANGED, "notes": []}
    rule = rule_for(model) if enabled() else None
    if not rule or not base:
        return out
    raw = (target or {}).get("raw") or {}
    applied = []
    prompt = base
    shot = (raw.get("shot") or "").strip()
    if anchored and rule.get("anchored") == "motion" and shot:
        from . import timeline
        heard = sound_line(raw.get("continuity")) or sound_line(raw.get("scene"))
        prompt = timeline.for_render(f"{shot}\n\n{heard}" if heard and heard not in shot else shot)
        applied.append("motion")
    if rule.get("negative_field"):
        rest, items = avoid_list(prompt)
        if items:
            prompt = rest
            out["negative_prompt"] = as_negative(items)
            applied.append("negative_field")
    limit = rule.get("soft_max_chars")
    if limit and len(prompt) > limit:
        out["notes"].append(f"{len(prompt)} characters; the vendor recommends under {limit}")
    if applied and prompt.strip():
        out["prompt"] = prompt
        out["rule"] = "+".join(applied)
    else:
        out["negative_prompt"] = ""
    return out
