"""The Guide's tools: what a chat turn may read, and what it may only propose.

The React studio's Guide answers and proposes actions. This module is the
policy around the tools it is handed:

- **A closed set, split read from write.** Read tools run on their own
  inside a Guide turn; write tools never run from the model's say-so --
  the turn returns a proposal, the thread draws a card, and the click is
  what runs it. Anything not in a set is not published to the model and is
  refused if named.
- **Nothing here spends, or approves a spend.** A make tool ends the turn
  as a proposal the STUDIO runs through its own priced doors; a clip is
  rendered only from a scene's Render card.
- **Closed-set ids, never URLs.** The first live research run banked six
  fabricated Unsplash URLs that all 404'd. `check_args` refuses any
  argument that looks like a URL before a tool sees it.

NO BOARD TOOLS SINCE 2026-10-11 (docs/tasks/task-higgsfield-shape.md,
Mike's call: no idea board). From 2026-09-18 this module was a bridge to
the repo's own MCP server, opened in-process, and published its board
tools to the model: `board`, `sparks`, `stats`, `tonight` to read, and
`add_spark` / `reference` to propose. The board is gone from the studio,
so those went. Two were not named in the task and went with them because
nothing was left for them to do: `reference` banks an image behind a spark
the model can no longer look up, and `images_for` was already hidden
wherever `find_references` is offered -- which is every Guide turn. With
no bridged tool left, the Guide opens no MCP server and needs no `mcp`
package; `READ_TOOLS` / `WRITE_TOOLS` stay as the (empty) names other
modules read.
"""
from __future__ import annotations

import re
from typing import Optional

from . import make_plan, model_menu

# The MCP-bridged sets, empty since 2026-10-11 (see the docstring).
READ_TOOLS: tuple = ()
WRITE_TOOLS: tuple = ()
TOOLS = READ_TOOLS + WRITE_TOOLS

# What a person sees on the confirm card, per write tool.
WRITE_LABELS: dict = {}

# The assistant's own tools (src/assistant_brain.py, 2026-09-26), run in
# this process. find_references is a READ (it hunts and looks, banks
# nothing, spends no credits); keep_references is a WRITE and waits for the
# click like every other write here. Published only when a turn asks for
# them (`session(local=True)`).
# load_skill (2026-10-10, src/skills.py) is a READ like the other two: it
# hands back one of the studio's recipes as text and makes nothing.
# list_effects (2026-10-10) reads the effects table (src/effects.py): what
# each effect takes and makes, and the legal values of its options.
# research_look (2026-10-11, src/look_research.py) reads the web for what a
# NAMED film, person, brand or era looks like and hands back labelled lines;
# it writes nothing -- keeping a look is set_project_look's click, below.
# list_models (2026-10-11, src/model_menu.py) reads the still and clip
# models this account can make on, with the studio's own line about each.
LOCAL_READ = ("find_references", "search_footage", "load_skill", "list_effects",
              "research_look", "list_models")
LOCAL_WRITE = ("keep_references",)
LOCAL_TOOLS = LOCAL_READ + LOCAL_WRITE
WRITE_LABELS["keep_references"] = "Keep these references and attach them to the composer"
MAX_KEEP_IDS = 12

# THE BRAIN MAKES (2026-10-04, Mike's call: "it is all in one place where
# you can toggle between image and video that are connected to the
# reasoning/brain"). The composer has no Guide toggle any more: every
# send is a Guide turn, and the model decides whether the person is
# talking an idea through or asking for the thing -- a still, or a
# written scene. These two are WRITE tools in the proposal sense (the
# turn ends on the call, nothing runs here) with one difference from
# keep_references: the STUDIO runs them, not /creative-guide/act. The reply's
# proposal names the tool and the prompt the model wrote, and the
# composer posts it to the same doors a send used to post to directly
# (/api/generate/run for an image, /api/scenes/run for a scene), so the
# spend gates, the charge and the job registry are exactly what they
# were. `run` refuses them: a server that made a still off a POST body
# would be the Director's Generate node without its price. Published
# only when a turn asks (`session(maker=True)`), so the pill is unchanged.
MAKE_TOOLS = ("make_image", "make_video", "make_element_sheet")
WRITE_LABELS["make_image"] = "Generate this image"
WRITE_LABELS["make_video"] = "Write this scene"
# THE ELEMENT SHEET FROM THE COMPOSER (2026-10-09, Mike: "can you create an
# element sheet of myself" with five photos attached made a loose 4:5
# still). A make tool like the other two -- proposed here, run by the
# studio on the step card's Approve -- but what it runs is the Elements
# create route (POST /api/assets/characters with the composer's
# references as photo_urls, sheet on), so the person is saved as a
# character AND the sheet is element_sheet.draw: the landing page's
# five-panel prompt, 16:9, on the real photos. Nothing here spends.
SHEET_TOOL = "make_element_sheet"
WRITE_LABELS[SHEET_TOOL] = "Save as a character and draw the reference sheet"
MAX_SHEET_NAME = 80
MAX_SHEET_NOTES = 300
MAX_MAKE_PROMPT = 4000
MAKE_SECONDS = (4, 30)          # timeline.scene_seconds' clamp
MAKE_SHOTS = (1, 8)
# A RESULT NAMED BY ITS NUMBER (2026-10-11, src/result_refs.py): the page
# numbers what a conversation made and tells the model the list; a make may
# be held to earlier stills by their numbers, an effect applied to one. A
# closed set like every id here -- held to the list in check_args.
RESULTS_PROPERTY = {
    "type": "array", "items": {"type": "integer"},
    "description": "Optional: the NUMBERS of earlier stills to hold this to as references, "
                   "only when the person pointed at them ('like 3 but at night', 'put 1 "
                   "and 2 together') and only numbers from the listed results.",
}
MAKE_SPECS = (
    {
        "name": "make_image",
        "description": (
            "Generate ONE still from a prompt, on the image model the person picked "
            "in the composer. Call it ONLY when the person asked for an image in this "
            "turn in so many words (make / generate / draw / show me / render it / "
            "do it) or confirmed an offer you made -- never when they are bouncing "
            "ideas, asking a question, or giving notes. The prompt is what the image "
            "model is handed, in plain visual language: subject, setting, light, lens, "
            "mood. Keep every reference the person attached in mind; they ride along."),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The image, described plainly."},
                "aspect": {"type": "string",
                           "description": "Optional: 1:1, 4:5, 3:4, 9:16, 16:9, 21:9 -- "
                                          "only when they asked for a shape."},
                "results": RESULTS_PROPERTY,
                "model": model_menu.MODEL_PROPERTY,
                "model_why": model_menu.WHY_PROPERTY,
            },
            "required": ["prompt"],
        },
        "write": True,
    },
    {
        "name": "make_video",
        "description": (
            "Write ONE video scene from an idea: the studio's scene writer turns it "
            "into timed shots with its references, filed under the open project when there is "
            "one "
            "(nothing is rendered: a clip is paid for on the scene's own Render "
            "card). Call it ONLY when the person "
            "asked for the scene in this turn in so many words or confirmed an offer "
            "you made -- never while they are still deciding. The prompt is the idea "
            "as agreed: subject, turn, setting, look, pacing, sound, constraints."),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The scene idea, as agreed."},
                "seconds": {"type": "integer",
                            "description": "Optional total length, 4-30, only when asked."},
                "shots": {"type": "integer",
                          "description": "Optional shot count, only when they named one."},
                "results": RESULTS_PROPERTY,
                "model": model_menu.MODEL_PROPERTY,
                "model_why": model_menu.WHY_PROPERTY,
            },
            "required": ["prompt"],
        },
        "write": True,
    },
    {
        "name": SHEET_TOOL,
        "description": (
            "Save the PERSON in the attached photos as a character element and draw "
            "its reference sheet: one wide image, five panels -- full-body front, "
            "three-quarter, side profile, back, and a head-and-shoulders close-up -- "
            "the same face and clothes in every panel. Call it when the person asks "
            "for an element sheet, character sheet, reference sheet or turnaround of "
            "themselves or of someone in the photos they attached -- never make_image "
            "for that. It needs attached photos of the person; with none attached, ask "
            "for them instead of calling. The name is what the person called them "
            "(their own first name when it is them and you know it, else ask). Notes "
            "only when they said what the character should wear."),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string",
                         "description": "The character's name, as the person gave it."},
                "notes": {"type": "string",
                          "description": "Optional: what they wear in the sheet, only "
                                         "when the person said. Empty keeps the clothes "
                                         "in the photos."},
            },
            "required": ["name"],
        },
        "write": True,
    },
)

# PROJECTS ARE MADE THROUGH THE GUIDE (2026-10-07, Mike's call: "projects
# are only created through the Guide -- either the user tells the Guide
# to make one, or a Guide conversation is saved as a project. There is no
# 'New project' form or button on the board."). Two WRITE tools in the
# proposal sense -- the turn ends on the call, the pill or the composer
# draws the confirm card, and the click posts /creative-guide/act, which
# runs `run_project_tool` with the thread the client holds:
#   create_project    -- a named project (title, optional brief). The
#                        conversation stays an ordinary chat.
#   save_as_project   -- the conversation so far BECOMES a project: its
#                        turns are copied into the project's history and
#                        the scenes it made are filed under it.
# Published on every local turn (the pill, the composer's brain). A turn
# that already runs inside a project is told so (creative_guide.project_note)
# and asked not to propose either. Nothing here spends.
PROJECT_TOOLS = ("create_project", "save_as_project")
WRITE_LABELS["create_project"] = "Create this project"
WRITE_LABELS["save_as_project"] = "Save this conversation as a project"
MAX_PROJECT_TITLE = 120
MAX_PROJECT_BRIEF = 8000
MAX_PROJECT_LOOK = 4000     # projects.LOOK_MAX; a test holds the two together
MAX_SAVED_TURNS = 200
MAX_SAVED_SCENES = 40
PROJECT_SPECS = (
    {
        "name": "create_project",
        "description": (
            "Create a studio PROJECT -- the container a piece of work's scenes live "
            "in, with its own brief and memory. Call it ONLY when the person asked "
            "for a project in so many words ('make a project for the Nike spot', "
            "'start a new project called X') and never when they are just talking "
            "about an idea. Never call it inside a conversation that is already in "
            "a project. The title is theirs or a short name for the work; the brief "
            "is only what they said about who it is for, the look, and the rules."),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The project's name."},
                "brief": {"type": "string",
                          "description": "Optional: FOR / LOOK / ALWAYS / NEVER lines "
                                         "from what the person said. Leave empty "
                                         "rather than invent one."},
                "look": {"type": "string",
                         "description": "Optional: the look every scene in it is held "
                                        "to, as labelled lines (PALETTE: ..., LIGHT: ...), "
                                        "only when one was researched or agreed in this "
                                        "conversation and they asked for it."},
            },
            "required": ["title"],
        },
        "write": True,
    },
    {
        "name": "save_as_project",
        "description": (
            "Turn THIS conversation into a project: it is saved with every turn so "
            "far and the scenes made in it, under the title given. Call it ONLY "
            "when the person asked to save or keep this conversation as a project "
            "('make this a project', 'save this as a project called X'). Never "
            "inside a conversation already in a project."),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string",
                          "description": "The project's name -- theirs, or a short "
                                         "name for what the conversation is about."},
                "brief": {"type": "string",
                          "description": "Optional: the brief as agreed so far, in "
                                         "FOR / LOOK / ALWAYS / NEVER lines."},
                "look": {"type": "string",
                         "description": "Optional: the look every scene in it is held "
                                        "to, as labelled lines (PALETTE: ..., LIGHT: ...), "
                                        "only when one was researched or agreed in this "
                                        "conversation and they asked for it."},
            },
            "required": ["title"],
        },
        "write": True,
    },
)

# A PROJECT'S LOOK, SAVED FROM THE CHAT (2026-10-11, item 10 of
# docs/tasks/task-studio-agent.md). The look belongs to the project
# (src/looks.py) and until now was only typed by hand in the workspace.
# A WRITE in the proposal sense: the turn ends on the call, the card shows
# the look, and the click posts /creative-guide/act, which runs
# `run_look_tool` against the project the CLIENT names -- the model is
# never handed a project id. Published only to a turn that runs inside a
# project (`session(in_project=True)`); outside one, a look rides on
# create_project / save_as_project as `look`. It REPLACES the project's
# look, and the act route answers with the one it replaced so the page can
# offer Undo. Nothing here spends.
LOOK_TOOL = "set_project_look"
WRITE_LABELS[LOOK_TOOL] = "Save this as the project's look"
LOOK_SPEC = {
    "name": LOOK_TOOL,
    "description": (
        "Save a LOOK as this project's own: every scene written in the project is held "
        "to it from then on. Call it ONLY when the person asked to use, keep, save or set "
        "the look for the project in this turn -- never because a look was merely "
        "discussed or researched. It replaces the look the project has, so pass the "
        "whole look as it should read afterwards: labelled lines, each on its own line "
        "(PALETTE: ..., LIGHT: ..., LENS AND FRAMING: ..., TEXTURE AND GRADE: ..., "
        "MOVEMENT AND PACING: ..., SETS AND WARDROBE: ..., AVOID: ...), in craft words "
        "that stand without naming a film, a person or a brand."),
    "input_schema": {
        "type": "object",
        "properties": {
            "look": {"type": "string",
                     "description": "The look, as labelled lines, one per line."},
        },
        "required": ["look"],
    },
    "write": True,
}

# EXPLORE (2026-10-11, item 13 of docs/tasks/task-studio-agent.md): a project
# can be switched to Explore (`projects.explore`), where a send only talks.
# A turn inside such a project is handed NO tool that makes -- `session`
# drops every one of them, whatever the caller asked for -- and this one in
# their place: the way out. It is a write in the proposal sense (the turn
# ends on it, nothing runs) and it makes nothing: the card under the answer
# offers the switch, the click is the person's (PATCH /api/projects/<id>),
# and only then is the ask sent again, to a turn that can make. `run` and
# /creative-guide/act refuse it like a make.
SWITCH_TOOL = "switch_to_make"
WRITE_LABELS[SWITCH_TOOL] = "Switch this project to Make"
# what the person asked to have made: the card's words follow it
SWITCH_KINDS = ("still", "scene", "sheet", "effect", "plan")
MAX_SWITCH_IDEA = 600
SWITCH_SPEC = {
    "name": SWITCH_TOOL,
    "description": (
        "This project is switched to EXPLORE: nothing is made in it and you have no tool "
        "that makes. Call this ONLY when the person asked, in this turn in so many words, "
        "for something to be made -- a still, a scene, a character sheet, an effect, "
        "several of them. It makes nothing: it shows them the switch to Make, and their "
        "ask is sent again once they flip it. Never call it because making would be "
        "helpful, and never for talk, a question or notes."),
    "input_schema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": list(SWITCH_KINDS),
                     "description": "What they asked for: one still, one written scene, "
                                    "a character sheet, an effect on something that "
                                    "exists, or a plan of several."},
            "idea": {"type": "string",
                     "description": "What you would make, in one to three sentences of "
                                    "craft words. The person reads it above the switch."},
        },
    },
    "write": True,
}

# A PLAN (2026-10-10, src/make_plan.py): several of the makes above, in
# order, as ONE proposal. A make in every sense that matters here -- the
# turn ends on the call, `run` and /creative-guide/act refuse it, and the
# studio runs its steps through the doors each step always had -- but it is
# its own tool, published only to the composer (a maker turn handed EVERY
# make): the pill draws a still and nothing else.
PLAN_TOOL = make_plan.TOOL
WRITE_LABELS[PLAN_TOOL] = make_plan.LABEL

# AN EFFECT (2026-10-10, item 3 of docs/tasks/task-studio-agent.md): change
# something that already exists -- edit a still, animate one with a template
# or a camera move, upscale or add sound to a clip (src/effects.py). A make
# like the others: proposed here, run by the STUDIO through its own priced
# card and POST /api/effects/run. The brain names the effect, its options
# and its prompt, never what it acts on: the studio binds the source (what
# is attached to the box, else the newest result that fits), so no id or
# address is ever the model's to invent.
EFFECT_TOOL = "apply_effect"
EFFECTS_READ = "list_effects"
WRITE_LABELS[EFFECT_TOOL] = "Apply this effect"
EFFECT_SPECS = (
    {
        "name": EFFECTS_READ,
        "description": (
            "Read the studio's effects: without `effect`, one line per effect -- what it "
            "takes (a still or a clip), what it makes, whether it needs a prompt, and its "
            "options; with `effect`, every legal value of that effect's options (the "
            "template names, the camera moves, the sizes). Costs nothing. Call it before "
            "apply_effect whenever you need a template or move by name -- never guess one."),
        "input_schema": {
            "type": "object",
            "properties": {"effect": {"type": "string",
                                      "description": "Optional: one effect's id, for its "
                                                     "options in full."}},
        },
        "write": False,
    },
    {
        "name": EFFECT_TOOL,
        "description": (
            "Change something that already exists, with one of the studio's effects: edit "
            "a still by instruction, cut out its background, animate a still with a "
            "template or a named camera move, upscale or smooth a clip, add sound to a "
            "clip, give a clip a new shape. Call it ONLY when the person asked for that "
            "change in this turn. You name the effect, its options and (where it takes "
            "one) the prompt. What it acts on is the studio's to bind: what is attached "
            "to the box, else the newest result that fits -- unless the person pointed "
            "at a numbered result ('upscale 2'), which you pass as `on`. The card shows "
            "the person which. It waits for their Approve beside its price. Options must "
            "be values list_effects returned."),
        "input_schema": {
            "type": "object",
            "properties": {
                "effect": {"type": "string", "description": "The effect's id, from list_effects."},
                "prompt": {"type": "string",
                           "description": "What to change, or what it sounds like -- only "
                                          "for an effect that takes a prompt."},
                "options": {"type": "object",
                            "description": "The effect's options by name, with values "
                                           "exactly as list_effects gives them."},
                "on": {"type": "integer",
                       "description": "Optional: the NUMBER of the result to apply it to, "
                                      "only when the person pointed at one and only a "
                                      "number from the listed results. A still effect "
                                      "takes a still, a clip effect a clip."},
            },
            "required": ["effect"],
        },
        "write": True,
    },
)

MAX_TOOL_CALLS = 6      # read calls per turn; a Guide answer, not a crawl

_URL = re.compile(r"(?i)\b(?:https?|ftp)://|\bwww\.|\.(?:jpe?g|png|webp|gif)(?:\?|$)")


class Refused(ValueError):
    """A call this bridge will not make -- the message is for the person."""


def is_write(name: str) -> bool:
    return (name in WRITE_TOOLS or name in LOCAL_WRITE or name in MAKE_TOOLS
            or name in PROJECT_TOOLS
            or name in (PLAN_TOOL, EFFECT_TOOL, LOOK_TOOL, SWITCH_TOOL))


def is_local(name: str) -> bool:
    return name in LOCAL_TOOLS


def is_switch(name: str) -> bool:
    """The Explore project's way out: proposed by the model, done by the
    person's own click on the project (never run here or by the act route)."""
    return name == SWITCH_TOOL


def is_project(name: str) -> bool:
    """A project tool: proposed by the model, run by /creative-guide/act
    with the conversation the client holds (run_project_tool)."""
    return name in PROJECT_TOOLS


def is_look(name: str) -> bool:
    """The look tool: proposed by the model, run by /creative-guide/act
    against the project the client names (run_look_tool)."""
    return name == LOOK_TOOL


def is_make(name: str) -> bool:
    """A make tool: proposed by the model, run by the STUDIO (the
    composer's own send), never by this module. A plan is several of them."""
    return name in MAKE_TOOLS or name in (PLAN_TOOL, EFFECT_TOOL)


def step_note(name: str, args: Optional[dict] = None) -> str:
    """What the person reads once a read tool has run mid-turn. A skill
    is named by its title: "looked at load_skill" says nothing to them."""
    if name == "load_skill":
        from . import skills
        title = skills.title_of((args or {}).get("name"))
        if title:
            return f"read the {title} skill"
    if name == "research_look":
        from . import look_research
        who = look_research.clean_subject((args or {}).get("subject"))
        if who:
            return f"researched the look of {who}"
    if name == model_menu.TOOL:
        return "looked at the models"
    return f"looked at {name}"


def available() -> bool:
    """Whether the Guide's tools can be offered. Always, since 2026-10-11:
    they run in this process and need no `mcp` package (it answered whether
    that package was importable while the board tools were bridged)."""
    return True


def check_args(name: str, args: dict, results: Optional[list] = None) -> dict:
    """Refuse a call outside the set, or one carrying a URL.

    The URL rule is checked on every string argument, not only the two
    named `*_url`: a model told "no URLs" puts one in `title` next.

    `results` (2026-10-11, src/result_refs.py) is the turn's numbered
    results, as the page sent them: a number a call names -- `on` for an
    effect, `results` for a make -- is held to that list. None means the
    caller has no list (the act route, a plan's step, an older page), and a
    number then names nothing and is dropped.
    """
    if (name not in TOOLS and name not in LOCAL_TOOLS and name not in MAKE_TOOLS
            and name not in PROJECT_TOOLS
            and name not in (PLAN_TOOL, EFFECT_TOOL, LOOK_TOOL, SWITCH_TOOL)):
        raise Refused(f"`{name}` is not reachable from the Guide")
    if name == PLAN_TOOL:
        # every step goes back through this function under its own tool's
        # name, so the URL rule and each tool's bounds hold inside a plan
        return make_plan.check(args)
    args = dict(args or {})
    if name == SWITCH_TOOL:
        # Never refused: an empty call still says "they asked for something
        # to be made", and the card can say that much. Its words are only
        # shown, so an idea carrying an address is dropped rather than
        # failing the turn -- and nothing else is kept.
        kind = str(args.get("kind") or "").strip().lower()
        idea = args.get("idea")
        idea = " ".join(idea.split()) if isinstance(idea, str) else ""
        if _URL.search(idea):
            idea = ""
        if len(idea) > MAX_SWITCH_IDEA:
            idea = idea[:MAX_SWITCH_IDEA].rsplit(" ", 1)[0] + "…"
        clean_switch: dict = {}
        if kind in SWITCH_KINDS:
            clean_switch["kind"] = kind
        if idea:
            clean_switch["idea"] = idea
        return clean_switch
    for key, value in args.items():
        values = value if isinstance(value, list) else [value]
        if any(isinstance(v, str) and _URL.search(v) for v in values):
            raise Refused(f"`{name}` does not take a URL ({key}); "
                          "pass an id a tool returned instead")
    if name == "keep_references":
        ids = args.get("candidate_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) and i.strip()
                                                           for i in ids):
            raise Refused("`keep_references` needs candidate_ids from find_references")
        args = {"candidate_ids": [i.strip() for i in ids][:MAX_KEEP_IDS]}
    if name == "find_references":
        if not str(args.get("scene") or "").strip():
            raise Refused("`find_references` needs the scene to hunt for")
        args = {"scene": str(args["scene"])[:2000],
                "departments": [str(d)[:20] for d in (args.get("departments") or [])
                                if isinstance(d, str)][:7],
                "avoid": [str(a)[:120] for a in (args.get("avoid") or [])
                          if isinstance(a, str)][:8]}
    if name == "search_footage":
        if not str(args.get("query") or "").strip():
            raise Refused("`search_footage` needs something to look for")
        k = args.get("k")
        args = {"query": str(args["query"])[:300],
                "k": k if isinstance(k, int) and not isinstance(k, bool) else 8}
    if name in (EFFECT_TOOL, EFFECTS_READ):
        return _check_effect(name, args, results)
    if name == "research_look":
        from . import look_research
        who = look_research.clean_subject(args.get("subject"))
        if not who:
            raise Refused("`research_look` needs the name to research")
        args = {"subject": who}
    if name == LOOK_TOOL:
        look = clean_look(args.get("look"))
        if not look:
            raise Refused(f"`{name}` needs the look to save")
        args = {"look": look}
    if name == "load_skill":
        from . import skills
        wanted = skills.clean_name(args.get("name"))
        if not wanted:
            raise Refused("`load_skill` takes one of: " + ", ".join(skills.names()))
        args = {"name": wanted}
    if name == SHEET_TOOL:
        who = " ".join(str(args.get("name") or "").split())
        if not who:
            raise Refused(f"`{name}` needs the character's name")
        args = {"name": who[:MAX_SHEET_NAME],
                "notes": " ".join(str(args.get("notes") or "").split())[:MAX_SHEET_NOTES]}
    elif name in MAKE_TOOLS:
        prompt = " ".join(str(args.get("prompt") or "").split())
        if not prompt:
            raise Refused(f"`{name}` needs the prompt to make it from")
        clean: dict = {"prompt": prompt[:MAX_MAKE_PROMPT]}
        if name == "make_image":
            aspect = str(args.get("aspect") or "").strip()
            if re.fullmatch(r"\d{1,2}:\d{1,2}", aspect):
                clean["aspect"] = aspect
        else:
            for key, (lo, hi) in (("seconds", MAKE_SECONDS), ("shots", MAKE_SHOTS)):
                value = args.get(key)
                if isinstance(value, bool) or not isinstance(value, int):
                    continue
                clean[key] = max(lo, min(hi, value))
        # the model the brain proposes for this step (src/model_menu.py):
        # kept only when the tables have it -- a still model for a still, a
        # clip model for a scene -- with its reason; else no key at all, and
        # the step is made on what the person picked
        proposed = (model_menu.image_id if name == "make_image"
                    else model_menu.video_id)(args.get("model"))
        if proposed:
            clean["model"] = proposed
            why = model_menu.clean_why(args.get("model_why"))
            if why:
                clean["model_why"] = why
        # earlier stills named by number: kept where the list has them as
        # stills, dropped otherwise (no key at all when none is left)
        from . import result_refs
        named = result_refs.stills(args.get("results"), results)
        if named:
            clean["results"] = named
        args = clean
    if name in PROJECT_TOOLS:
        title = " ".join(str(args.get("title") or "").split())
        if not title:
            raise Refused(f"`{name}` needs a title for the project")
        look = clean_look(args.get("look"))
        args = {"title": title[:MAX_PROJECT_TITLE],
                "brief": str(args.get("brief") or "").strip()[:MAX_PROJECT_BRIEF]}
        if look:                 # no key at all without one: the call it was
            args["look"] = look
    return args


def clean_look(raw) -> str:
    """A look as it is stored: its lines kept, each one plain, blank ones
    gone, bounded. "" for anything that is not text."""
    if not isinstance(raw, str):
        return ""
    lines = [" ".join(line.split()) for line in raw.replace("\r", "\n").split("\n")]
    return "\n".join(line for line in lines if line)[:MAX_PROJECT_LOOK].strip()


def switch_line(args: dict) -> str:
    """The answer above the switch card. The first sentence is code's, not
    the model's: whatever it wrote, nothing was made, and the line says so."""
    idea = str((args or {}).get("idea") or "").strip()
    return ("This project is exploring, so nothing has been made."
            + (f" {idea}" if idea else " Switch it to Make and I will make that."))


def _check_effect(name: str, args: dict, results: Optional[list] = None) -> dict:
    """An effect call held to the table (src/effects.py): a name that is
    not an effect, an option that is not legal, a prompt where none is
    taken -- each refused with the table's own words, which say what IS
    legal, so the next call can be right. A result named by number (`on`)
    is held to the turn's list the same way (src/result_refs.py)."""
    from . import effects, result_refs
    which = str(args.get("effect") or "").strip()
    try:
        if name == EFFECTS_READ:
            if which:
                effects.spec(which)
            return {"effect": which}
        row = effects.spec(which)
        options = args.get("options") if isinstance(args.get("options"), dict) else {}
        out = {"effect": which,
               "options": effects.check_options(which, options),
               "prompt": effects.check_prompt(which, str(args.get("prompt") or ""))}
        on = result_refs.one(args.get("on"), results, takes=row["takes"])
        if on is not None:
            out["on"] = on
        return out
    except ValueError as exc:
        raise Refused(str(exc)) from exc


def effect_line(args: dict) -> str:
    """What an effect proposal says above its card: the effect, the look or
    move picked, and the words it was given."""
    from . import effects
    row = effects.EFFECTS.get(args.get("effect") or "") or {}
    picked = [str(v).replace("_", " ") for k, v in (args.get("options") or {}).items()
              if k in ("effect_scene", "effect", "camera_movement", "aspect_ratio")]
    line = " · ".join([row.get("label") or "Effect"] + picked)
    return f"{line}: {args['prompt']}" if args.get("prompt") else line


def _takes(row: dict) -> str:
    lo, hi = row["sources"]["min"], row["sources"]["max"]
    what = "clip" if row["takes"] == "video" else "still"
    return f"one {what}" if hi == 1 else f"{lo} to {hi} {what}s"


def effects_for_model(effect: str = "") -> str:
    """What list_effects hands the model: ids, what each takes and makes,
    and option values. No prices -- the card shows the price -- and no
    vendor pages."""
    from . import effects

    def head(row: dict) -> str:
        makes = "a clip" if row["output"] == "video" else "an image"
        return (f"{row['id']} -- {row['label']}: takes {_takes(row)}, makes {makes}; "
                f"prompt {row['prompt']}")

    if effect:
        row = effects.catalogue(effect=effect)[0]
        lines = [f"{head(row)}. {row['note']}"]
        for opt, view in row["options"].items():
            need = "required" if view["required"] else f"default {view['default']}"
            lines.append(f"- {opt} ({need}): " + ", ".join(str(v) for v in view["values"]))
        return "\n".join(lines)
    lines = ["The studio's effects (call again with `effect` for one effect's option values):"]
    for row in effects.catalogue():
        opts = ", ".join(f"{k} ({v['count']})" for k, v in row["options"].items()) or "none"
        lines.append(f"- {head(row)}; options: {opts}")
    return "\n".join(lines)


def run(name: str, args: dict, *, dsn: Optional[str] = None,
        account_id: Optional[int] = None, brand: str = "",
        attachments: Optional[dict] = None, on_step=None) -> str:
    """Run ONE tool, synchronously.

    The confirm card's click lands here (keep_references), and so does
    every read the model makes mid-turn. All of them are the assistant's
    own tools, run in this process.
    """
    args = check_args(name, args)
    if is_make(name):
        # the studio's send runs these against the generation routes,
        # where the price, the charge and the job are; a server that made
        # a still off this body would be a second spend door with no card
        raise Refused(f"`{name}` is made by the studio's own send, not here")
    if is_switch(name):
        # the switch is the person's click on the project, never a tool run
        raise Refused(f"`{name}` is the project's own switch, not something to run")
    if is_project(name):
        # needs the conversation the client holds: run_project_tool
        raise Refused(f"`{name}` takes the conversation; the act route runs it")
    if is_look(name):
        # needs the project the client is in: run_look_tool
        raise Refused(f"`{name}` takes the project; the act route runs it")
    from . import assistant_brain
    return assistant_brain.run_local(name, args, brand=brand, account_id=account_id,
                                     dsn=dsn, attachments=attachments, on_step=on_step)


def run_project_tool(name: str, args: dict, *, account_id: int, conversation=None,
                     scenes=None, dsn: Optional[str] = None) -> dict:
    """The confirm card's click on create_project / save_as_project.

    `conversation` is the thread as the client holds it -- [{role,
    content, tool_calls?}] -- and `scenes` the concept ids its sends
    made; both are user content filed under `account_id` and nothing
    else is read off them. A concept that is not this account's is
    simply not filed (projects.tag_concepts' own predicate). Returns
    {project, summary}; raises Refused for a bad call."""
    from . import projects

    if not is_project(name):
        raise Refused(f"`{name}` is not a project tool")
    args = check_args(name, args)
    try:
        project = projects.create(args["title"], args.get("brief") or "", dsn,
                                  account_id=account_id, look=args.get("look") or "")
    except ValueError as exc:
        raise Refused(str(exc)) from exc
    copied = filed = 0
    if name == "save_as_project":
        turns = [t for t in (conversation if isinstance(conversation, list) else [])
                 if isinstance(t, dict)][-MAX_SAVED_TURNS:]
        copied = projects.copy_messages(project["id"], turns, dsn, account_id=account_id)
        ids = [int(i) for i in (scenes if isinstance(scenes, list) else [])
               if isinstance(i, int) and not isinstance(i, bool) and i > 0][:MAX_SAVED_SCENES]
        if ids:
            filed = projects.tag_concepts(ids, project["id"], dsn, account_id=account_id)
    summary = f"project “{project['title']}” created" + (" with its look" if args.get("look")
                                                           else "")
    if name == "save_as_project":
        summary += (f" with {copied} turn{'s' if copied != 1 else ''}"
                    + (f" and {filed} scene{'s' if filed != 1 else ''}" if filed else ""))
    return {"project": project, "summary": summary}


def run_look_tool(args: dict, *, project_id, account_id: int,
                  dsn: Optional[str] = None) -> dict:
    """The confirm card's click on set_project_look.

    `project_id` is the project the CLIENT is in -- the model never names
    one -- and it is read under `account_id`, so a project that is not this
    account's is "no project N", like everywhere else. Returns {project,
    previous, summary}: `previous` is the look this one replaced ("" when
    there was none), which is what an Undo puts back. Raises Refused."""
    from . import projects

    args = check_args(LOOK_TOOL, args)
    if isinstance(project_id, bool) or not isinstance(project_id, int) or project_id <= 0:
        raise Refused("a look is saved to a project: open one, or ask for one to be made")
    before = projects.get(project_id, dsn, account_id=account_id)
    if before is None:
        raise Refused(f"no project {project_id}")
    try:
        project = projects.update(project_id, dsn, account_id=account_id, look=args["look"])
    except ValueError as exc:
        raise Refused(str(exc)) from exc
    return {"project": project, "previous": before.get("look") or "",
            "summary": f"look saved to “{project['title']}”"}


def session(dsn: Optional[str] = None, account_id: Optional[int] = None,
            *, local: bool = False, brand: str = "", maker: bool = False,
            makes: Optional[tuple] = None, on_step=None, in_project: bool = False,
            explore: bool = False):
    """Everything a Guide turn needs, gathered once: the tool specs for
    the model, and a synchronous `run_tool(name, args)` for the READ
    calls the model makes mid-turn. Returns (specs, run_tool).

    `local=True` (the assistant pill, the composer's brain) publishes
    find_references / keep_references, search_footage, load_skill and the
    two project tools. A turn that asks for neither `local` nor `maker`
    has no tools at all (until 2026-10-11 it was handed the board's, read
    over an in-process MCP server). `run_tool.attachments` collects what a
    read tool left for the reply (the contact sheet).

    `maker=True` (the composer's send, 2026-10-04) also publishes
    make_image / make_video -- proposals the studio runs, see MAKE_TOOLS.

    `makes` narrows the make tools a maker turn is handed (the assistant
    pill gets ("make_image",) -- 2026-10-08); None is every one, and with
    them make_plan (src/make_plan.py).

    `on_step(done, of, detail)` hears a local tool's progress
    (find_references' hunt), for the job the turn runs in.

    `in_project=True` (2026-10-11) says the turn runs inside a studio
    project: it is also handed set_project_look. research_look itself is
    on every local turn -- a look can be researched anywhere, and kept
    only where there is a project to keep it.

    `explore=True` (2026-10-11, item 13) says that project is switched to
    Explore: NO tool that makes is published, whatever `maker` and `makes`
    say -- this is where that is held, so no caller can hand one out by
    mistake -- and a local turn is handed switch_to_make in their place.
    The free tools (references, a look, the skills, the project's own
    look) are what they were.
    """
    if explore:
        maker = False
    tool_specs: list = []
    if local:
        from . import assistant_brain
        tool_specs = tool_specs + [dict(s) for s in assistant_brain.LOCAL_SPECS]
        # the skill shelf (2026-10-10): one read tool, and only when there
        # is a skill to read
        from . import skills
        load = skills.load_spec()
        if load:
            tool_specs = tool_specs + [load]
        # a look researched by name (2026-10-11): a read on every local
        # turn; the write that keeps it only where there is a project
        from . import look_research
        tool_specs = tool_specs + [dict(look_research.SPEC)]
        if in_project:
            tool_specs = tool_specs + [dict(LOOK_SPEC)]
        if explore:
            # the one thing an exploring turn may propose: the way out
            tool_specs = tool_specs + [dict(SWITCH_SPEC)]
        # projects are made through the Guide (2026-10-07): offered on the
        # same turns the assistant's own tools are, i.e. the pill and the
        # composer's brain
        tool_specs = tool_specs + [dict(s) for s in PROJECT_SPECS]
    if maker:
        tool_specs = tool_specs + [dict(s) for s in MAKE_SPECS
                                   if makes is None or s["name"] in makes]
        if makes is None:
            # the composer, which is handed every make, may also be handed
            # several of them in a row -- and the effects (item 3), with the
            # read that lists them
            tool_specs = tool_specs + [dict(make_plan.SPEC)] + [dict(s) for s in EFFECT_SPECS]
            # ... and may propose the model a still or a scene is made on,
            # from the list this read hands it (item 12, src/model_menu.py)
            tool_specs = tool_specs + [dict(model_menu.SPEC)]

    attachments: dict = {}

    def run_tool(name: str, args: dict) -> str:
        if is_write(name):
            raise Refused(f"`{name}` writes; it needs a click, not a model")
        if is_local(name) and not local:
            raise Refused(f"`{name}` is not reachable from the Guide")
        return run(name, args, dsn=dsn, account_id=account_id, brand=brand,
                   attachments=attachments, on_step=on_step)

    run_tool.attachments = attachments
    return tool_specs, run_tool
