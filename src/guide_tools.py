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
# what the brain decided itself when the person deferred ("you decide"),
# as the one line said above the make (2026-10-25, the Vesper audit; invideo:
# "Locking it myself: brand is RISE ... 9:16")
LOCKED_PROPERTY = {
    "type": "string",
    "description": "Only when the person left it to you (\"you decide\", \"up to you\"): ONE "
                   "line saying what you decided, naming anything you invented as invented "
                   "(\"Locking it myself: 9:16, 10 seconds; the name Halo is mine.\"). "
                   "Leave it out otherwise.",
}
MAX_LOCKED = 200


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
                                          "only when they asked for a shape. The shape goes "
                                          "HERE, never into the prompt's words."},
                "results": RESULTS_PROPERTY,
                "model": model_menu.MODEL_PROPERTY,
                "model_why": model_menu.WHY_PROPERTY,
                "locked": LOCKED_PROPERTY,
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
                "locked": LOCKED_PROPERTY,
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

# THE PROJECT'S BRAND KIT, EDITED FROM THE CHAT (2026-10-21, step 6 of
# docs/tasks/task-brand-kit-import-and-chat.md). A WRITE like the look: the
# turn ends on the call, the card shows each field before and after, and
# only Apply changes the kit (/creative-guide/act -> run_kit_tool). Handed
# only to a turn inside a project that picked a kit, with that kit as it is
# now in the tool's own description; the id it takes is held to that kit
# (src/kit_changes.py), and the act route checks it against the project
# the CLIENT is in. Nothing here spends.
KIT_TOOL = "propose_kit_change"
WRITE_LABELS[KIT_TOOL] = "Change the brand kit"


def kit_spec(kit: dict) -> dict:
    """propose_kit_change for one kit: the fields it may change as an enum,
    and the kit's values now in the description."""
    from . import kit_changes
    return {
        "name": KIT_TOOL,
        "description": (
            "Propose a change to this project's brand kit. The person applies it on a "
            "card; nothing changes until then. Pass only the fields that change, each "
            "with its whole new value.\n\n" + kit_changes.summary(kit)),
        "input_schema": {
            "type": "object",
            "properties": {
                "kit_id": {"type": "integer",
                           "description": f"The kit's id: {kit['id']}."},
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string", "enum": list(kit_changes.FIELDS)},
                            "value": {"type": "string",
                                      "description": "The field's whole new value."},
                        },
                        "required": ["field", "value"],
                    },
                },
            },
            "required": ["kit_id", "changes"],
        },
        "write": True,
    }


# AN APP SCREEN DRAWN FROM THE KIT (2026-10-22, docs/tasks/
# task-kit-products-and-screens.md Part C). A WRITE: the turn ends on the
# call, the card draws the screen (free, src/kit_screens.py) and keeps it on
# its click. Handed only to a maker turn with a kit in play (the project's
# pick, the conversation's, or a kit named), and held to that kit's id.
SCREEN_TOOL = "make_screen"
WRITE_LABELS[SCREEN_TOOL] = "Draw this screen"
_CELL = {"type": "string"}


def screen_spec(kit: dict) -> dict:
    """make_screen for one kit, its id in the description."""
    from . import kit_screens
    return {
        "name": SCREEN_TOOL,
        "description": (
            f"Draw an app screen for {kit['name']} in its own fonts, colours and logo, for "
            "free, to hold a shot that shows the brand's app or a screen to (a video model "
            "cannot draw readable UI). The person sees it on a card and keeps it there. "
            "schedule takes rows {name, role, time, status}; list_cards takes cards "
            "{title, subtitle, meta, tag}; hero_cta takes headline, body, button and "
            "an optional secondary button."),
        "input_schema": {
            "type": "object",
            "properties": {
                "kit_id": {"type": "integer", "description": f"The kit's id: {kit['id']}."},
                "template": {"type": "string", "enum": list(kit_screens.TEMPLATES)},
                "device": {"type": "string", "enum": list(kit_screens.SIZES)},
                "title": {"type": "string", "description": "The screen's title (schedule, "
                                                           "list_cards)."},
                "subtitle": {"type": "string"},
                "rows": {"type": "array", "items": {
                    "type": "object", "properties": {"name": _CELL, "role": _CELL,
                                                     "time": _CELL, "status": _CELL},
                    "required": ["name"]}},
                "cards": {"type": "array", "items": {
                    "type": "object", "properties": {"title": _CELL, "subtitle": _CELL,
                                                     "meta": _CELL, "tag": _CELL},
                    "required": ["title"]}},
                "headline": {"type": "string"},
                "body": {"type": "string"},
                "button": {"type": "string"},
                "secondary": {"type": "string"},
            },
            "required": ["kit_id", "template"],
        },
        "write": True,
    }


def check_screen(args: dict, kit: Optional[dict]) -> dict:
    """A make_screen call as its card takes it -- {kit_id, kit_name, spec,
    summary, warnings} -- held to the kit in play, or Refused naming what
    is wrong (the model may ask again)."""
    from . import kit_screens
    if not kit:
        raise Refused("no brand kit is in play here, so there is no screen to draw")
    if args.get("kit_id") not in (kit["id"], str(kit["id"])):
        raise Refused(f"make_screen draws for kit {kit['id']} ({kit['name']}) only")
    try:
        spec = kit_screens.clean({k: v for k, v in args.items() if k != "kit_id"})
    except kit_screens.ScreenError as exc:
        raise Refused(str(exc)) from exc
    return {"kit_id": kit["id"], "kit_name": kit["name"], "spec": spec,
            "summary": kit_screens.summary(spec),
            "warnings": kit_screens.check_words(spec, kit)}


def check_kit(args: dict, kit: Optional[dict]) -> dict:
    """A propose_kit_change call held to the thread's kit, with its card's
    before and after, or Refused naming the field."""
    from . import kit_changes
    try:
        return kit_changes.check(args, kit)
    except kit_changes.ChangeError as exc:
        raise Refused(str(exc)) from exc


def run_kit_tool(args: dict, *, project_id, account_id: int,
                 dsn: Optional[str] = None) -> dict:
    """The card's Apply on propose_kit_change.

    The kit is the one the project the CLIENT is in picked, read under
    `account_id`; the proposal's kit id must be that one. The changes are
    checked again against the kit as it is NOW (it may have been edited
    since the card was drawn). Returns {kit, previous, summary}: `previous`
    is the spec this replaced, which is what an Undo puts back. Raises
    Refused."""
    from . import brand_kits, kit_changes, projects

    if isinstance(project_id, bool) or not isinstance(project_id, int) or project_id <= 0:
        raise Refused("a brand kit is changed from inside its project")
    project = projects.get(project_id, dsn, account_id=account_id)
    if project is None:
        raise Refused(f"no project {project_id}")
    kit = brand_kits.for_project(project, dsn)
    try:
        checked = kit_changes.check(args, kit)
        after = kit_changes.apply(kit["spec"], checked["changes"])
    except kit_changes.ChangeError as exc:
        raise Refused(str(exc)) from exc
    updated = brand_kits.update(kit["id"], dsn, account_id=account_id, spec=after)
    if updated is None:
        raise Refused(f"no brand kit {kit['id']}")
    names = ", ".join(r["label"].lower() for r in checked["diff"])
    return {"kit": updated, "previous": kit["spec"],
            "summary": f"{kit['name']}: {names} changed"}


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

# A TAPPABLE QUESTION (2026-10-22, vesper_v2; docs/tasks/task-vesper-v2.md).
# The brain can ask one question as something to tap -- colour swatches,
# aspect chips, an A/B pick of numbered results, plain chips -- instead of
# a sentence the person has to answer by typing. A write in the proposal
# sense (the turn ends on it, nothing runs, `run` and /creative-guide/act
# refuse it); the thread draws it (components/studio/tappable-question.tsx)
# and a tap sends the option's words as the next message. Published only
# when the route asks (`session(questions=True)`, the vesper_v2 flag), so
# with the flag off no turn is told about it.
ASK_TOOL = "ask_choice"
WRITE_LABELS[ASK_TOOL] = "Answer with a tap"
ASK_KINDS = ("chips", "swatches", "aspect", "ab")
ASK_MIN, ASK_MAX = 2, 6
MAX_ASK = 160
MAX_ASK_LABEL = 40
MAX_ASK_VALUE = 80
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ASK_SPEC = {
    "name": ASK_TOOL,
    "description": (
        "Ask ONE question as options the person taps, instead of writing it into "
        "`message`: `kind` swatches (each option carries a #rrggbb `swatch`), aspect "
        "(the options are shapes like 4:5, 9:16, 16:9), ab (two or three of the numbered "
        "results to choose between; `on` is the number) or chips (short plain answers). "
        "Two to six options, a few words each. The tap comes back as their next message; "
        "they can always type instead. It ends the turn and makes nothing. Only for a real "
        "fork in the work, never for a yes/no and never in place of a make they asked for."),
    "input_schema": {
        "type": "object",
        "properties": {
            "ask": {"type": "string", "description": "The question, one line."},
            "kind": {"type": "string", "enum": list(ASK_KINDS)},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "A few words."},
                        "value": {"type": "string",
                                  "description": "Optional: what the tap sends when it is not "
                                                 "the label (an aspect's 4:5)."},
                        "swatch": {"type": "string",
                                   "description": "swatches: the colour, #rrggbb."},
                        "on": {"type": "integer",
                               "description": "ab: the NUMBER of the result this option is, "
                                              "from the listed results."},
                    },
                    "required": ["label"],
                },
            },
        },
        "required": ["ask", "options"],
    },
    "write": True,
}


def is_ask(name: str) -> bool:
    """The tappable question: proposed by the model, answered by the
    person's tap (never run here or by the act route)."""
    return name == ASK_TOOL


def check_ask(args: dict, results: Optional[list] = None) -> dict:
    """An ask_choice call as the card draws it, or Refused. A result named
    by number (`on`) is held to the turn's list like an effect's source."""
    from . import result_refs
    ask = " ".join(str((args or {}).get("ask") or "").split())
    if not ask:
        raise Refused(f"`{ASK_TOOL}` needs the question to ask")
    kind = str((args or {}).get("kind") or "chips").strip().lower()
    if kind not in ASK_KINDS:
        kind = "chips"
    raw = (args or {}).get("options")
    options: list[dict] = []
    for item in (raw if isinstance(raw, list) else [])[:ASK_MAX]:
        if isinstance(item, str):
            item = {"label": item}
        if not isinstance(item, dict):
            continue
        label = " ".join(str(item.get("label") or "").split())[:MAX_ASK_LABEL]
        if not label:
            continue
        value = " ".join(str(item.get("value") or "").split())[:MAX_ASK_VALUE]
        if _URL.search(label) or _URL.search(value):
            # the generic URL rule reads strings and lists of them; an
            # option is a dict inside a list, so it is read here
            raise Refused(f"`{ASK_TOOL}` does not take a URL; options are words")
        option: dict = {"label": label}
        if value and value != label:
            option["value"] = value
        swatch = str(item.get("swatch") or "").strip()
        if _HEX.match(swatch):
            option["swatch"] = swatch.lower()
        on = item.get("on")
        if isinstance(on, int) and not isinstance(on, bool) and on > 0:
            try:
                held = result_refs.one(on, results, takes="")
            except result_refs.Unknown:
                held = None
            if held is not None:
                option["on"] = held
        options.append(option)
    if len(options) < ASK_MIN:
        raise Refused(f"`{ASK_TOOL}` needs {ASK_MIN} to {ASK_MAX} options with a label each")
    if kind == "swatches" and not all(o.get("swatch") for o in options):
        kind = "chips"
    return {"ask": ask[:MAX_ASK], "kind": kind, "options": options}


def ask_line(args: dict) -> str:
    """The line above the tappable question: the question itself."""
    return str((args or {}).get("ask") or "Which one?")


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

# A TALKING PHOTO (2026-10-20, src/talking_photo.py): a photo of a person
# made to speak. Like an effect it is a proposal only: the studio opens its
# card, where the person picks the photo, ticks the consent box, uploads a
# voice or writes one (the voice preview is its own priced click) and
# presses the priced Render. The brain may hand the card a still by number
# and a draft of the words; it never picks a face or spends.
TALK_TOOL = "talking_photo"
WRITE_LABELS[TALK_TOOL] = "Make a photo talk"
MAX_TALK_SCRIPT = 5000          # talking_photo.SCRIPT_MAX_CHARS
MAX_TALK_PROMPT = 1000          # talking_photo.PROMPT_MAX
TALK_SPEC = {
    "name": TALK_TOOL,
    "description": (
        "Open the talking-photo card: a photo of a person speaks (or sings) a voice "
        "track -- an uploaded recording, or a script read aloud in a chosen voice. Call "
        "it ONLY when the person asked in this turn for a photo to talk, speak, sing or "
        "lip-sync. It spends nothing: the card asks the person for the photo, their "
        "confirmation that the face is theirs or that its owner agreed, and the voice, "
        "and each spend waits for their own click beside its price. Pass `on` when they "
        "pointed at a numbered still, `script` when they said what it should say (their "
        "words, or yours when they asked you to write them), and `prompt` for the "
        "scene, movement or camera when they described one."),
    "input_schema": {
        "type": "object",
        "properties": {
            "on": {"type": "integer",
                   "description": "Optional: the NUMBER of the still that speaks, only when "
                                  "the person pointed at one and only a number from the "
                                  "listed results."},
            "script": {"type": "string",
                       "description": "Optional: the words to say, at least a sentence or "
                                      "two (a talking photo needs 4 seconds of voice). May "
                                      "carry delivery tags like [laughs] or [whispers]."},
            "prompt": {"type": "string",
                       "description": "Optional: the scene, movement and camera."},
        },
    },
    "write": True,
}

# A DUB (2026-10-26, src/dubbing.py): a clip with speech on it, spoken again
# in another language. Like the talking photo it is a proposal only: the
# studio opens its card, where the person picks the clip and the language,
# ticks the consent box (the voices are theirs, or their owners agreed) and
# presses the priced Render. The brain may hand the card a clip by number
# and a language; it never spends.
DUB_TOOL = "dub_clip"
WRITE_LABELS[DUB_TOOL] = "Dub a clip"
DUB_SPEC = {
    "name": DUB_TOOL,
    "description": (
        "Open the dub card: a clip that already has people speaking on it is spoken again "
        "in another language, in the same voices. Call it ONLY when the person asked in "
        "this turn for a clip to be dubbed, translated into another language, or "
        "localised. It spends nothing: the card asks the person for the clip, the "
        "language and their confirmation that the voices are theirs or that their owners "
        "agreed, and the spend waits for their own click beside its price. Pass `on` "
        "when they pointed at a numbered clip, and `target_language` (a two-letter code) "
        "when they named the language."),
    "input_schema": {
        "type": "object",
        "properties": {
            "on": {"type": "integer",
                   "description": "Optional: the NUMBER of the clip to dub, only when the "
                                  "person pointed at one and only a number from the listed "
                                  "results."},
            "target_language": {"type": "string",
                                "description": "Optional: the language to dub into, as a "
                                               "two-letter code (es, fr, de, ja, pt, zh)."},
        },
    },
    "write": True,
}

# A MOTION-GRAPHICS AD (2026-10-21, step 3 of docs/tasks/task-url-to-ad.md):
# the brand kit's colours, type and app screens as an ad of timed beats, with
# a voiceover script (src/cut/motion_ad.py). A proposal only: the studio
# writes the beats onto a card (free model text, behind the Create gate), the
# person reads and changes them, and Build makes the cut -- also free. It is
# never built on a send, Auto or not: the card is where the beats are read.
AD_TOOL = "make_ad"
WRITE_LABELS[AD_TOOL] = "Write this ad"
AD_SECONDS = (8, 60)                 # cut/motion_ad SECONDS_MIN / SECONDS_MAX
AD_ASPECTS = ("16:9", "9:16", "1:1")
MAX_AD_BRIEF = 1000
AD_SPEC = {
    "name": AD_TOOL,
    "description": (
        "Open the ad card: a motion-graphics ad in the project's brand kit -- big type, "
        "one faint word behind each line, the product's screens on cards, flat brand "
        "colours, a voiceover script -- written as timed beats the person reads and "
        "changes before it is built. Call it ONLY when the person asked in this turn for "
        "an ad, a promo or a launch video of their brand or product (not a filmed scene: "
        "that is make_video). It spends nothing. `brief` is what the ad sells and to whom, "
        "in a sentence or two; `seconds` and `aspect` only when they said them."),
    "input_schema": {
        "type": "object",
        "properties": {
            "brief": {"type": "string",
                      "description": "What the ad is for: the product, its one promise, who "
                                     "it is for. No web addresses."},
            "seconds": {"type": "integer",
                        "description": f"Optional: the length, {AD_SECONDS[0]}-{AD_SECONDS[1]}."},
            "aspect": {"type": "string", "enum": list(AD_ASPECTS),
                       "description": "Optional: 16:9 (the default), 9:16 or 1:1."},
        },
        "required": ["brief"],
    },
    "write": True,
}


def check_ad(args: dict) -> dict:
    """An ad proposal: a brief, and a length and shape off the motion ad's
    own lists -- refused, never clamped."""
    brief = " ".join(str(args.get("brief") or "").split())
    if not brief:
        raise Refused(f"`{AD_TOOL}` needs a brief: what the ad sells and to whom")
    out: dict = {"brief": brief[:MAX_AD_BRIEF]}
    seconds = args.get("seconds")
    if seconds is not None:
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) \
                or not AD_SECONDS[0] <= seconds <= AD_SECONDS[1]:
            raise Refused(f"`{AD_TOOL}` takes {AD_SECONDS[0]} to {AD_SECONDS[1]} seconds")
        out["seconds"] = int(round(seconds))
    aspect = args.get("aspect")
    if aspect is not None:
        if aspect not in AD_ASPECTS:
            raise Refused(f"`{AD_TOOL}` takes one of: {', '.join(AD_ASPECTS)}")
        out["aspect"] = aspect
    return out


def ad_line(args: dict) -> str:
    """The line above the ad card."""
    return ("Here is the ad as beats, in the brand kit's look. Read them, change any line, "
            "then build it; building is free and opens it in the editor.")


# FREE EDITS (2026-10-19, the Vesper review): a new shape or a range of
# something the conversation made, on the studio's own server with ffmpeg
# (src/cut/quick.py, the connector's reformat / trim_clip). They cost
# nothing, so the STUDIO runs one the moment it is proposed, the way it
# writes a scene. The source is bound by the page like an effect's: the
# result the person pointed at (`on`), else the newest one that fits.
QUICK_TOOLS = ("reformat", "trim_clip")
WRITE_LABELS["reformat"] = "Make a copy in a new shape"
WRITE_LABELS["trim_clip"] = "Make a trimmed copy"
QUICK_ASPECTS = ("9:16", "16:9", "1:1", "4:5")       # src/cut/quick.py SIZES
QUICK_FITS = ("pad", "crop")
MAX_QUICK_SECONDS = 600.0
QUICK_SPECS = (
    {
        "name": "reformat",
        "description": (
            "Make a COPY of a still or clip from this conversation in a new shape, for "
            "free (no credits; the studio's own server does it). fit=pad keeps the whole "
            "picture with black bars; fit=crop fills the frame and keeps the middle. Use "
            "it for 'make it vertical', 'square version', 'crop it for Instagram'. It does "
            "not invent new picture -- for a frame EXTENDED to a new shape, that is the "
            "paid reframe effect. Call it ONLY when the person asked for it in this turn. "
            "The original is untouched; the copy is a new numbered result."),
        "input_schema": {
            "type": "object",
            "properties": {
                "aspect": {"type": "string", "enum": list(QUICK_ASPECTS)},
                "fit": {"type": "string", "enum": list(QUICK_FITS),
                        "description": "pad (default) or crop."},
                "on": {"type": "integer",
                       "description": "Optional: the NUMBER of the still or clip to "
                                      "reshape, only when the person pointed at one and "
                                      "only a number from the listed results."},
            },
            "required": ["aspect"],
        },
        "write": True,
    },
    {
        "name": "trim_clip",
        "description": (
            "Make a COPY of a clip from this conversation holding only `start` to `end` "
            "seconds, with its sound, for free (no credits). Use it for 'cut it to the "
            "first 5 seconds', 'drop the last second'. The range must lie inside the clip. "
            "Call it ONLY when the person asked for it in this turn. The original is "
            "untouched; the copy is a new numbered result."),
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "number", "description": "Seconds from the start, >= 0."},
                "end": {"type": "number", "description": "Seconds from the start, > start."},
                "on": {"type": "integer",
                       "description": "Optional: the NUMBER of the clip to trim, only when "
                                      "the person pointed at one and only a number from the "
                                      "listed results."},
            },
            "required": ["start", "end"],
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
            or name in PROJECT_TOOLS or name in QUICK_TOOLS
            or name in (PLAN_TOOL, EFFECT_TOOL, TALK_TOOL, DUB_TOOL, LOOK_TOOL, SWITCH_TOOL,
                        KIT_TOOL, AD_TOOL, ASK_TOOL, SCREEN_TOOL))


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


def is_kit(name: str) -> bool:
    """The brand kit tool: proposed by the model, applied by
    /creative-guide/act against the kit of the project the client names."""
    return name == KIT_TOOL


def is_make(name: str) -> bool:
    """A make tool: proposed by the model, run by the STUDIO (the
    composer's own send), never by this module. A plan is several of them."""
    return name in MAKE_TOOLS or name in (PLAN_TOOL, EFFECT_TOOL, TALK_TOOL, AD_TOOL, DUB_TOOL)


def is_quick(name: str) -> bool:
    """A free edit (reformat, trim_clip): proposed by the model, run at once
    by the STUDIO through POST /api/quick-edit, never by this module."""
    return name in QUICK_TOOLS


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
            and name not in PROJECT_TOOLS and name not in QUICK_TOOLS
            and name not in (PLAN_TOOL, EFFECT_TOOL, TALK_TOOL, DUB_TOOL, LOOK_TOOL, SWITCH_TOOL,
                             KIT_TOOL, AD_TOOL, ASK_TOOL, SCREEN_TOOL)):
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
    if name in QUICK_TOOLS:
        return check_quick(name, args, results)
    if name == TALK_TOOL:
        return check_talk(args, results)
    if name == AD_TOOL:
        return check_ad(args)
    if name == DUB_TOOL:
        return check_dub(args, results)
    if name == ASK_TOOL:
        return check_ask(args, results)
    if name == "research_look":
        from . import look_research
        who = look_research.clean_subject(args.get("subject"))
        if not who:
            raise Refused("`research_look` needs the name to research")
        args = {"subject": who}
    if name == SCREEN_TOOL:
        # the URL rule below runs on every string; the shape and the kit are
        # check_screen's, in the turn that has the kit
        return dict(args)
    if name == KIT_TOOL:
        # the shape only; held to the thread's kit by check_kit, which
        # needs the kit (the turn and the act route both call it)
        from . import kit_changes
        try:
            return kit_changes.clean(args)
        except kit_changes.ChangeError as exc:
            raise Refused(str(exc)) from exc
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
        locked = " ".join(str(args.get("locked") or "").split())
        if locked:
            clean["locked"] = (locked if len(locked) <= MAX_LOCKED
                               else locked[:MAX_LOCKED].rsplit(" ", 1)[0] + "…")
        # earlier stills named by number: kept where the list has them as
        # stills, dropped otherwise (no key at all when none is left)
        from . import result_refs
        named = result_refs.stills(args.get("results"), results)
        if named:
            clean["results"] = named
        if name == "make_video" and not proposed:
            # a parked slot's routing rule (fal.SLOTS, 2026-10-22): only a
            # READY slot can be preferred, and only where the card opens --
            # the person still picks and pays there. None today.
            preferred = model_menu.slot_preference(clean.get("seconds"), clean.get("shots"),
                                                   refs=len(named))
            if preferred:
                clean["model"], clean["model_why"] = preferred
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
    from . import effect_names, effects, result_refs
    which = str(args.get("effect") or "").strip()
    # A LOOK BY NAME (2026-10-22, src/effect_names.py): "noir grade", "make
    # it vertical" or an id in another spelling resolves to the id the
    # table carries; a name that resolves to nothing goes to the table's
    # own refusal, which lists what is legal
    which = effect_names.resolve(which) or which
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


def _seconds(raw, what: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise Refused(f"`trim_clip` needs {what} as a number of seconds")
    return round(float(raw), 3)


def check_quick(name: str, args: dict, results: Optional[list] = None) -> dict:
    """A free edit held to what src/cut/quick.py makes: a shape it knows, a
    fit it knows, a range that is a range. Whether the range lies inside
    the clip is the edit's own check, when it runs. A number named with
    `on` is held to the turn's list like an effect's -- reformat takes a
    still or a clip, trim a clip."""
    from . import result_refs
    out: dict = {}
    if name == "reformat":
        aspect = str(args.get("aspect") or "").strip()
        if aspect not in QUICK_ASPECTS:
            raise Refused("`reformat` takes aspect " + ", ".join(QUICK_ASPECTS))
        fit = str(args.get("fit") or "pad").strip().lower()
        if fit not in QUICK_FITS:
            raise Refused("`reformat` takes fit pad or crop")
        out = {"aspect": aspect, "fit": fit}
        takes = None
    else:
        start, end = _seconds(args.get("start"), "start"), _seconds(args.get("end"), "end")
        if start < 0 or end <= start or end > MAX_QUICK_SECONDS:
            raise Refused("`trim_clip` needs 0 <= start < end, in seconds of the clip")
        out = {"start": start, "end": end}
        takes = "video"
    try:
        on = result_refs.one(args.get("on"), results, takes=takes or "")
    except result_refs.Unknown as exc:
        raise Refused(str(exc)) from exc
    if on is not None and name == "reformat":
        kind = next((r["kind"] for r in results or [] if r["n"] == on), None)
        if kind not in ("still", "clip"):
            raise Refused(f"#{on} is a {kind}; reformat takes a still or a clip")
    if on is not None:
        out["on"] = on
    return out


def quick_line(name: str, args: dict) -> str:
    """The line above a free edit: what is being made, and that it is free."""
    if name == "reformat":
        how = "cropped to fill" if args.get("fit") == "crop" else "padded, the whole picture kept"
        return f"A copy in {args.get('aspect')}, {how}. Free: no credits."
    return (f"A copy holding {args.get('start'):g}s to {args.get('end'):g}s, with its sound. "
            "Free: no credits.")


def check_talk(args: dict, results: Optional[list] = None) -> dict:
    """A talking-photo proposal: a still named by number held to the turn's
    list, and the words bounded. Nothing here is a spend, so nothing is
    refused for being short -- the card says what it needs."""
    from . import result_refs
    out: dict = {}
    try:
        on = result_refs.one(args.get("on"), results, takes="image")
    except result_refs.Unknown as exc:
        raise Refused(str(exc)) from exc
    if on is not None:
        out["on"] = on
    script = args.get("script")
    if isinstance(script, str) and script.strip():
        out["script"] = script.strip()[:MAX_TALK_SCRIPT]
    prompt = args.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        out["prompt"] = " ".join(prompt.split())[:MAX_TALK_PROMPT]
    return out


def check_dub(args: dict, results: Optional[list] = None) -> dict:
    """A dub proposal: a clip named by number held to the turn's list, and a
    language held to the ones offered. Nothing here is a spend, so a missing
    clip or language is not refused -- the card asks for it."""
    from . import dubbing, result_refs
    out: dict = {}
    try:
        on = result_refs.one(args.get("on"), results, takes="video")
    except result_refs.Unknown as exc:
        raise Refused(str(exc)) from exc
    if on is not None:
        out["on"] = on
    lang = args.get("target_language")
    if isinstance(lang, str) and lang.strip():
        try:
            out["target_language"] = dubbing.check_language(lang)
        except ValueError as exc:
            raise Refused(str(exc)) from exc
    return out


def dub_line(args: dict) -> str:
    """The line above the dub card: what it will do, and that nothing is
    spent until the person's own click."""
    from . import dubbing
    into = f" into {dubbing.LANGUAGES[args['target_language']]}" if args.get("target_language") else ""
    return (f"A dub{into}. Pick the clip and the language on the card; "
            "the spend waits for your click beside its price.")


def talk_line(args: dict) -> str:
    """The line above the talking-photo card: what it will do, and that
    nothing is spent until the person's own clicks."""
    words = f' saying: "{args["script"]}"' if args.get("script") else ""
    return (f"A talking photo{words}. Pick the photo and the voice on the card; "
            "each spend waits for your click beside its price.")


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
    # the plain words people use for a look (src/effect_names.py), for the
    # rows the table carries today
    from . import effect_names
    names = effect_names.names_block()
    if names:
        lines.append("")
        lines.append(names)
    return "\n".join(lines)


def _from_kit(kit: dict, name: str, args: dict) -> Optional[str]:
    """A read the brand kit answers instead of the web, or None to run it."""
    from . import brand_kits
    if name == "research_look" and brand_kits.mentions(kit, (args or {}).get("subject")):
        return brand_kits.look_for_model(kit)
    if name == "find_references" and brand_kits.mentions(kit, (args or {}).get("scene")):
        raise Refused(
            f"“{kit['name']}” is the person's brand kit: its logo, look and reference images "
            "are on file and already in front of you. Do not hunt the web for the brand. If "
            "the scene still needs photos (a venue, people, a light), call find_references "
            "again describing just that, without the brand's name.")
    return None


def run(name: str, args: dict, *, dsn: Optional[str] = None,
        account_id: Optional[int] = None, attachments: Optional[dict] = None, on_step=None) -> str:
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
    if is_ask(name):
        # a question is answered by the person's tap, never run
        raise Refused(f"`{name}` is a question for the person, not something to run")
    if is_project(name):
        # needs the conversation the client holds: run_project_tool
        raise Refused(f"`{name}` takes the conversation; the act route runs it")
    if is_look(name):
        # needs the project the client is in: run_look_tool
        raise Refused(f"`{name}` takes the project; the act route runs it")
    from . import assistant_brain
    return assistant_brain.run_local(name, args, account_id=account_id,
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
            *, local: bool = False, maker: bool = False,
            makes: Optional[tuple] = None, on_step=None, in_project: bool = False,
            explore: bool = False, kit: Optional[dict] = None,
            brand_kit: Optional[dict] = None, questions: bool = False):
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

    `kit` (2026-10-21) is the brand kit the project picked: a local turn
    in that project is also handed propose_kit_change, for that kit only.

    `questions=True` (2026-10-22, vesper_v2) also hands a local turn
    ask_choice, the tappable question (ASK_SPEC). Off -- the flag's default
    -- no turn is told it exists.

    `brand_kit` (2026-10-21, src/brand_kits.py) is the kit IN PLAY: that
    pick, or a kit of the account the person named in the conversation. A
    research_look for its own name answers from the kit with no web read,
    and a find_references hunt that names the brand is refused with the
    reason -- the web hands back other companies' logos. None is the
    session it was.
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
            if kit:
                tool_specs = tool_specs + [kit_spec(kit)]
        if explore:
            # the one thing an exploring turn may propose: the way out
            tool_specs = tool_specs + [dict(SWITCH_SPEC)]
        if questions:
            # a question the person taps (vesper_v2): makes nothing
            tool_specs = tool_specs + [dict(ASK_SPEC)]
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
            # ... and the talking-photo card (2026-10-20)
            tool_specs = tool_specs + [dict(TALK_SPEC)]
            # ... and the ad card (2026-10-21, step 3 of task-url-to-ad)
            tool_specs = tool_specs + [dict(AD_SPEC)]
            # ... and the dub card (2026-10-26)
            tool_specs = tool_specs + [dict(DUB_SPEC)]
            # ... and the free edits on what it made (2026-10-19)
            tool_specs = tool_specs + [dict(s) for s in QUICK_SPECS]
            # ... and may propose the model a still or a scene is made on,
            # from the list this read hands it (item 12, src/model_menu.py)
            tool_specs = tool_specs + [dict(model_menu.SPEC)]
            # ... and, with a brand kit in play, an app screen drawn from it,
            # free (src/kit_screens.py, 2026-10-22)
            if brand_kit:
                tool_specs = tool_specs + [screen_spec(brand_kit)]

    attachments: dict = {}

    def run_tool(name: str, args: dict) -> str:
        if is_write(name):
            raise Refused(f"`{name}` writes; it needs a click, not a model")
        if is_local(name) and not local:
            raise Refused(f"`{name}` is not reachable from the Guide")
        if brand_kit is not None:
            answered = _from_kit(brand_kit, name, args)
            if answered is not None:
                return answered
        return run(name, args, dsn=dsn, account_id=account_id,
                   attachments=attachments, on_step=on_step)

    run_tool.attachments = attachments
    return tool_specs, run_tool
