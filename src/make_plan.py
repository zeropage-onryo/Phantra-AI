"""A plan: several makes in a row, proposed as ONE answer (2026-10-10).

Item 2 of docs/tasks/task-studio-agent.md. A Guide turn used to end on the
FIRST write the model asked for, so "make an ad from these photos" could
only ever be one thing per message: a still, or the scene, never the still
and then the scene and then its keyframes. Runway's and Higgsfield's agents
answer that kind of ask with a plan -- the steps, each with what it will
make and what it costs -- and run it on approval. `make_plan` is that
answer here.

It is still ONE write, and it still ends the turn as a proposal: nothing in
this module runs anything. The studio runs a plan's steps in order through
the doors each step always had (web/src/lib/make-plan.ts): the still's own
generate route and price, the scene writer, the Elements create route, the
keyframes approve, the scene's priced render. So a plan adds no spend door
and no new charge -- it is a list of the makes the brain could already
propose one at a time, with the order written down.

What a step may be (`DOES`):

    image      one still        -> make_image's arguments
    scene      one written scene -> make_video's arguments
    sheet      a character sheet -> make_element_sheet's arguments
    keep       keep hunted frames -> keep_references' arguments
    keyframes  draw a scene step's first frames (priced once it exists)
    render     render a scene step's clip (priced once it exists)

A PLAN NEVER RENDERS A CLIP UNASKED (2026-10-11,
docs/tasks/task-higgsfield-shape.md). `render` replaced `queue`, which sent
the scene to a Queue page that no longer approves anything. A render step
is priced on the plan card once its scene exists, and it ALWAYS stops for
its own Approve -- with "Approve all" clicked, and with Auto on -- because
a clip is the one thing here that is never made on a batch yes. `queue`
from a plan saved before that day is read as `render`.

`check` is the rail. Each step's arguments go through the SAME check its
tool has on its own (guide_tools.check_args), so a URL, an unknown id or an
empty prompt is refused in a plan exactly as it is outside one. What is
broken refuses the plan (a step nobody knows, keyframes with no scene
before them); what is merely wrong about a reference is dropped, because a
step drawn without it is still the step that was asked for.
"""
from __future__ import annotations

import re
from typing import Optional

TOOL = "make_plan"
LABEL = "Run this plan"
MAX_STEPS = 8
MAX_SUMMARY = 300
MAX_WHY = 160
# VARIANTS (2026-10-29, docs/tasks/task-ad-results.md): an Ad Studio plan may
# write several versions of one ad, each changing ONE thing. A scene step's
# `variant` names that thing ("Hook: the spill"), the plan's `test` names
# what the versions test ("which opening stops the scroll"); the studio
# files each written scene as one version (src/ad_results.record_variant)
# so imported ad results read as a test. Labels only: nothing is priced or
# run differently, and a render still waits for its own button.
MAX_VARIANT = 60
MAX_TEST = 120

DOES = ("image", "scene", "sheet", "keep", "keyframes", "render")
# what a step used to be called, read as what it is now
ALIASES = {"queue": "render"}
# the tool whose own check a step's arguments go through, and the
# arguments that tool takes -- anything else on the step is dropped
TOOL_FOR = {"image": "make_image", "scene": "make_video",
            "sheet": "make_element_sheet", "keep": "keep_references"}
ARG_KEYS = {"image": ("prompt", "aspect", "model", "model_why"),
            "scene": ("prompt", "seconds", "shots", "model", "model_why"),
            "sheet": ("name", "notes"), "keep": ("candidate_ids",)}
# steps that act on a scene written earlier in the same plan
ON_SCENE = ("keyframes", "render")
# a step whose result is a picture a later step can be held to
DRAWS = ("image",)
# WHAT SPENDS, AND WHAT MAY RUN UNASKED (2026-10-22, vesper_v2's autonomy
# dial; docs/tasks/task-vesper-v2.md). A paid step -- a still, a sheet, a
# scene's keyframes, its clip -- waits at its price for the person's click
# under EVERY setting of the dial; only a free step (writing the scene,
# keeping references) may run on its own, and only when the dial says so.
# The studio's runner (web/src/lib/make-plan.ts, lib/autonomy.ts) holds the
# same rule; tests/test_vesper_v2.py and web/tests/vesper-v2.test.mjs pin it.
PAID = ("image", "sheet", "keyframes", "render")
FREE = ("scene", "keep")
AUTONOMY = ("ask", "checkpoints", "autopilot")

SPEC = {
    "name": TOOL,
    "description": (
        "Propose SEVERAL makes in a row as one plan, when what the person asked for "
        "takes more than one: a still and then the scene held to it, a scene and then "
        "its keyframes and its clip, a character sheet and then a scene with that "
        "character, several scenes for one piece of work. The person sees the steps as "
        "a checklist, can edit or skip any of them, and approves each one that costs "
        "credits beside its price; nothing runs from this call. Call it ONLY when they "
        "asked for the things in it -- for one make, call that make's own tool instead. "
        "Each step is one of: image (a still: prompt, optional aspect), scene (a written "
        "scene: prompt, optional seconds and shots), sheet (a character sheet from the "
        "attached photos: name, optional notes), keep (keep frames from a "
        "find_references sheet in this conversation: candidate_ids), keyframes (draw the "
        "first frame of each shot of an earlier scene step: scene), render (render the "
        "clip of an earlier scene step -- it is priced once the scene exists and always "
        "waits for the person's own Approve: scene). Write every prompt as the finished "
        "work, exactly as you would for that tool on its own. For VERSIONS of one ad "
        "(an A/B test), write one scene step per version, each the same ad with ONE "
        "thing changed, give each a `variant` naming that thing and the plan a `test`."),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string",
                        "description": "One line the person reads above the plan: what "
                                       "it makes, in their words."},
            "test": {"type": "string",
                     "description": "Only for versions of ONE ad: what the versions test, "
                                    "in a few words (which hook, which offer line)."},
            "steps": {
                "type": "array",
                "description": "The steps, in the order they run. Two to eight.",
                "items": {
                    "type": "object",
                    "properties": {
                        "do": {"type": "string", "enum": list(DOES)},
                        "prompt": {"type": "string",
                                   "description": "image / scene: what to make."},
                        "aspect": {"type": "string",
                                   "description": "image: 1:1, 4:5, 16:9, 9:16 -- only when "
                                                  "they asked for a shape."},
                        "seconds": {"type": "integer",
                                    "description": "scene: total length, only when asked."},
                        "shots": {"type": "integer",
                                  "description": "scene: shot count, only when they named one."},
                        "name": {"type": "string", "description": "sheet: the character's name."},
                        "notes": {"type": "string",
                                  "description": "sheet: what they wear, only when stated."},
                        "candidate_ids": {"type": "array", "items": {"type": "string"},
                                          "description": "keep: ids from find_references."},
                        "scene": {"type": "integer",
                                  "description": "keyframes / render: the number of the "
                                                 "scene step it acts on."},
                        "uses": {"type": "array", "items": {"type": "integer"},
                                 "description": "The numbers of EARLIER image steps whose "
                                                "picture this step is held to."},
                        "why": {"type": "string",
                                "description": "One short line: what this step is for."},
                        "variant": {"type": "string",
                                    "description": "scene, only for versions of ONE ad: "
                                                   "the one thing this version changes, "
                                                   "a few words (\"Hook: the spill\")."},
                        "model": {"type": "string",
                                  "description": "image / scene: optional, the id of the "
                                                 "model to make it on, exactly as "
                                                 "list_models gave it -- a still model for "
                                                 "an image, a clip model for a scene (where "
                                                 "its Render card opens)."},
                        "model_why": {"type": "string",
                                      "description": "With `model`: why that one, in a few "
                                                     "plain words."},
                    },
                    "required": ["do"],
                },
            },
        },
        "required": ["steps"],
    },
    "write": True,
}


def _line(text, limit: int) -> str:
    return " ".join(str(text or "").split())[:limit]


def _int(value) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def check(args: dict) -> dict:
    """The plan a card can run, or guide_tools.Refused with what is wrong.

    Returns {"summary", "steps": [{"n", "do", "args", "why", "uses",
    ("scene")}]} -- `n` is 1-based and is what `uses` / `scene` name, and
    `args` is exactly what that step's own tool would have been handed.
    """
    from . import guide_tools  # it imports this module; resolved by call time

    refuse = guide_tools.Refused
    raw = (args or {}).get("steps")
    if not isinstance(raw, list) or not raw:
        raise refuse(f"`{TOOL}` needs the steps to run")
    if len(raw) > MAX_STEPS:
        raise refuse(f"a plan is at most {MAX_STEPS} steps; this one has {len(raw)}")
    for text in ((args or {}).get("summary"),) + tuple(
            s.get("why") for s in raw if isinstance(s, dict)):
        if isinstance(text, str) and guide_tools._URL.search(text):
            raise refuse(f"`{TOOL}` does not take a URL")

    steps: list[dict] = []
    for item in raw:
        n = len(steps) + 1
        if not isinstance(item, dict):
            raise refuse(f"step {n} of the plan is not a step")
        doing = str(item.get("do") or "").strip().lower()
        doing = ALIASES.get(doing, doing)
        if doing not in DOES:
            raise refuse(f"step {n}: `{doing or '?'}` is not something a plan can do "
                         f"({', '.join(DOES)})")
        step: dict = {"n": n, "do": doing, "why": _line(item.get("why"), MAX_WHY)}
        if doing in TOOL_FOR:
            handed = {k: item[k] for k in ARG_KEYS[doing] if item.get(k) is not None}
            try:
                step["args"] = guide_tools.check_args(TOOL_FOR[doing], handed)
            except refuse as exc:
                raise refuse(f"step {n}: {exc}") from exc
            if doing == "scene":
                # the studio posts this prompt as the scene writer's idea
                step["args"]["prompt"] = scene_idea(step["args"])
        else:
            step["args"] = {}
            scenes = [s["n"] for s in steps if s["do"] == "scene"]
            wanted = _int(item.get("scene"))
            if wanted is None and len(scenes) == 1:
                wanted = scenes[0]
            if wanted not in scenes:
                raise refuse(f"step {n}: {doing} needs a scene step before it in the plan")
            step["scene"] = wanted
        # a picture can only come from an EARLIER step that draws one; a
        # reference that is not there is dropped, never the step
        uses = item.get("uses") if isinstance(item.get("uses"), list) else []
        earlier = {s["n"] for s in steps if s["do"] in DRAWS}
        step["uses"] = sorted({u for u in map(_int, uses) if u in earlier})
        # a version's label rides on a scene step only; anywhere else it is dropped
        variant = _line(item.get("variant"), MAX_VARIANT) if doing == "scene" else ""
        if variant:
            if guide_tools._URL.search(variant):
                raise refuse(f"`{TOOL}` does not take a URL")
            step["variant"] = variant
        steps.append(step)

    labels = [s["variant"] for s in steps if s.get("variant")]
    if len(labels) != len(set(x.lower() for x in labels)):
        raise refuse("two versions have the same `variant`: each must say what it changes")
    summary = _line((args or {}).get("summary"), MAX_SUMMARY)
    plan = {"summary": summary or default_summary(steps), "steps": steps}
    test = _line((args or {}).get("test"), MAX_TEST) if labels else ""
    if test and not guide_tools._URL.search(test):
        plan["test"] = test
    return plan


def costs(doing: str) -> bool:
    """Whether a step spends credits (its old name read as its new one)."""
    doing = ALIASES.get(str(doing or "").strip().lower(), str(doing or "").strip().lower())
    return doing in PAID


def runs_unasked(doing: str, autonomy) -> bool:
    """May this step run without the person's own click under the dial?
    NEVER for a step that costs credits, whatever the setting; a free step
    only under checkpoints or autopilot. Anything unknown is False."""
    doing = ALIASES.get(str(doing or "").strip().lower(), str(doing or "").strip().lower())
    if doing not in DOES or costs(doing):
        return False
    return str(autonomy or "").strip().lower() in ("checkpoints", "autopilot")


_KIND = {"image": "a still", "scene": "the scene", "sheet": "a character sheet",
         "keep": "the references", "keyframes": "its keyframes", "render": "its clip"}


def default_summary(steps: list[dict]) -> str:
    """What a plan with no summary of its own is called: its steps, in order."""
    kinds = [_KIND[s["do"]] for s in steps]
    return "A plan in {} steps: {}.".format(len(steps), ", then ".join(kinds))


def collapse(clean: dict) -> Optional[tuple[str, dict]]:
    """A plan of ONE step is that step's own tool, and is proposed as that:
    a checklist of one is a card with extra clicks. (tool, args), or None
    when the plan really is a plan."""
    steps = clean.get("steps") or []
    if len(steps) != 1 or steps[0]["do"] not in TOOL_FOR:
        return None
    return TOOL_FOR[steps[0]["do"]], steps[0]["args"]


_COUNT_SAID = re.compile(r"(?i)\b\d{1,2}[\s-]+shots?\b|\(\s*\d+\s*-\s*\d+\s*s\s*\)")


def scene_idea(step_args: dict) -> str:
    """The idea a scene step hands the scene writer. A shot count the brain
    put in `shots` and not in the words is said in the words, in the form
    the writer's own check reads (timeline.requested_shots): the route
    takes no count, only an idea."""
    prompt = str(step_args.get("prompt") or "").strip()
    shots = _int(step_args.get("shots"))
    if not shots or _COUNT_SAID.search(prompt):
        return prompt
    if shots == 1:
        return f"{prompt}\n\nOne continuous shot, no cuts."
    return f"{prompt}\n\nCut it into exactly {shots} shots."
