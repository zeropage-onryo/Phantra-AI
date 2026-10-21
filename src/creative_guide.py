"""Conversational brief development; no concept or render mutations."""
import json
import re
import sys
from pathlib import Path
from typing import Literal, Optional

from google.genai import types
from pydantic import BaseModel, Field

from . import gemini_utils, shootgen


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class Conversation(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=40)


class Proposal(BaseModel):
    """A write the model asked for and nobody has approved (2026-09-18).

    The Guide never runs a write tool on the model's say-so: it comes
    back here, the thread draws a confirm card, and the click posts it
    to /api/creative-guide/act -- which is where `guide_tools.run` is
    called. `label` is the card's caption, `args` is exactly what the
    click will send."""
    tool: str = Field(min_length=1, max_length=64)
    args: dict = Field(default_factory=dict)
    label: str = Field(default="", max_length=200)


class ToolRun(BaseModel):
    """One read tool the model called mid-turn, for the thread to show
    ("looked at the board") so an answer's provenance is visible."""
    tool: str
    args: dict = Field(default_factory=dict)
    ok: bool = True


class Question(BaseModel):
    """One intake question as tap-able chips (2026-09-26, the assistant
    pill). Two or three options; the person can always type instead."""
    ask: str = Field(min_length=1, max_length=160)
    options: list[str] = Field(default_factory=list, max_length=3)


class Direction(BaseModel):
    """One story direction the model proposes. Graded by story_judge
    AFTER the model writes it (assistant_brain.check_directions)."""
    title: str = Field(min_length=1, max_length=80)
    logline: str = Field(min_length=1, max_length=600)
    turn: str = Field(default="", max_length=200)


class JudgedDirection(Direction):
    """A direction with the independent judge's grade attached -- never
    in the model's schema: a writer does not get to grade itself."""
    score: Optional[float] = None
    verdict: str = ""
    # which rubric graded it: "ad" (story_judge.judge_ad) or "story"
    rubric: str = ""


class Answer(BaseModel):
    """What the MODEL writes: the schema every model call is held to.
    The personal providers get this one verbatim (strict, every field
    required), and a tools turn is parsed against it too.

    questions / directions / nudge / stage were added for the assistant
    pill (2026-09-26); all default empty, so a model that ignores them
    answers exactly as it used to."""
    message: str = Field(min_length=1, max_length=3000)
    choices: list[str] = Field(default_factory=list, max_length=3)
    brief: str = Field(default="", max_length=8000)
    questions: list[Question] = Field(default_factory=list, max_length=3)
    directions: list[Direction] = Field(default_factory=list, max_length=3)
    nudge: str = Field(default="", max_length=120)
    stage: str = Field(default="", max_length=20)


class Reply(Answer):
    """What the ROUTE returns: the answer plus what the bridge added --
    never asked of the model, so never in the schema it is shown."""
    directions: list[JudgedDirection] = Field(default_factory=list, max_length=3)
    proposal: Optional[Proposal] = None
    tool_runs: list[ToolRun] = Field(default_factory=list)
    # A find_references contact sheet, when one ran this turn: the
    # thread draws it; the model only ever read its ids.
    sheet: Optional[dict] = None
    # What research_look read this turn (src/look_research.py `public`):
    # the name, the look's lines and the pages -- the thread shows where a
    # look came from; the model read the look and no address.
    research: list[dict] = Field(default_factory=list, max_length=4)


def _contents(conversation, grounding, image_refs, notes=()):
    contents = [types.Content(role="user", parts=[types.Part.from_text(
        text="Studio grounding (context only):\n" + json.dumps(grounding, default=str)[:24000])])]
    for message in conversation.messages:
        contents.append(types.Content(
            role="model" if message.role == "assistant" else "user",
            parts=[types.Part.from_text(text=message.content)]))
    contents[-1].parts.append(types.Part.from_text(
        text=f"Current composer reference images supplied: {len(image_refs)}."))
    for note in notes:
        if note:
            contents[-1].parts.append(types.Part.from_text(text=note))
    for raw, mime, label in image_refs:
        contents[-1].parts.extend([types.Part.from_text(text=label or "Reference image"),
                                   types.Part.from_bytes(data=raw, mime_type=mime)])
    return contents


# Which brain answers a Guide turn when the composer names none. FAST,
# not reasoning (2026-09-18, Mike's call): the Guide used to hardcode the
# reasoning tier, so "which of these three directions?" was billed at
# 3.1 Pro rates -- ~1.5c a turn, a third of a whole nightly graph run per
# chat message -- while the pill on the composer only ever reached
# Create. The tier is the person's to pick per turn, the same
# gemini_utils.BRAINS menu Create offers, clamped server-side; flip it to
# Reasoning for the turn that writes the brief.
DEFAULT_BRAIN = "fast"


# What the composer's Image | Video switch means to the model (2026-10-04).
# One line per output, appended to the person's last message beside the
# reference count -- the switch is the person's, and the model is told
# which thing a "make it" would make rather than asked to guess.
OUTPUT_NOTES = {
    "image": ("The composer is switched to IMAGE: a 'make it' means ONE still, "
              "through make_image. Talk in frames, not scenes."),
    "video": ("The composer is switched to VIDEO: a 'make it' means ONE written "
              "scene in timed shots, through make_video."),
    # the assistant pill (2026-10-08): it can draw a still -- the same step
    # card and Approve the composer shows -- but a scene is the composer's
    "still": ("This turn is in the assistant card, not the composer: a 'make it' "
              "means ONE still, through make_image -- the only make tool here. A "
              "scene is written from the Studio composer; say so rather than "
              "pretending to write one."),
}

# THE PHOTO CHECK, BEFORE A SCENE IS WRITTEN (2026-10-16, Vesper review). A
# scene with no photograph behind it is a draft every quote and approve
# refuses (preprod.reference_gate), and the person used to learn that only
# at the Render card. A Video turn with nothing to hold a scene to -- no
# photo attached, and nothing named that is one of their elements with
# photos (scene_chain.ground's cast and rooms) -- is told so up front.
NO_PHOTO_NOTE = ("NO PHOTO IS BEHIND THIS YET: nothing is attached and nothing named is one "
                 "of their elements with photos. A scene written without a photograph is a "
                 "DRAFT the studio will not price or render until it is held to one. Before "
                 "make_video, ask them to attach a photo or @-mention one of their elements "
                 "(a character, a product, a place). If they want it written anyway, write it "
                 "and say in one line that it is a draft that needs a photo before it renders.")


def photo_note(output, image_refs, grounding) -> str:
    """NO_PHOTO_NOTE for a Video turn with nothing to hold a scene to, else
    "". The rule's own switch (preprod.refs_required) turns it off too."""
    if output != "video" or image_refs:
        return ""
    if isinstance(grounding, dict) and (grounding.get("cast") or grounding.get("locations")):
        return ""
    from . import preprod
    return NO_PHOTO_NOTE if preprod.refs_required() else ""


# Which make tools a turn is handed, by its output (guide_tools.session's
# `makes`): the composer gets both, the pill only the still.
MAKES_FOR = {"image": None, "video": None, "still": ("make_image",)}


# EXPLORE (2026-10-11, item 13 of docs/tasks/task-studio-agent.md). A project
# switched to Explore (`projects.explore`) is one where a send only talks: the
# turn is handed no make tool (guide_tools.session), is not told the maker
# block, and gets this line on the person's last message IN PLACE of the
# Image | Video one above -- telling a model which tool a "make it" means
# when it has none would be asking it to pretend.
EXPLORE_NOTE = ("This project is switched to EXPLORE: this turn only talks. Nothing is "
                "made here and you have no tool that makes a still, a scene, a sheet, an "
                "effect or a plan.")


def explore_note(can_offer_switch: bool) -> str:
    """The Explore line, ending in what to do when they ask for a make:
    offer the switch where the turn was handed it, else say it in words."""
    return EXPLORE_NOTE + (
        " If the person asks for one to be made, call switch_to_make."
        if can_offer_switch else
        " If the person asks for one to be made, say it will be made once they "
        "switch the project to Make.")


# how much of a project's look a turn inside it is shown (projects.LOOK_MAX
# is 4000; a look researched by name is seven lines and well under this)
PROJECT_LOOK_SHOWN = 2000


def project_note(project) -> str:
    """One line for the model when the turn runs inside a project
    (2026-10-07): which one, so "continue the story" continues it and
    create_project / save_as_project are never proposed for a
    conversation that already has one. "" outside a project."""
    if not project or not isinstance(project, dict):
        return ""
    title = " ".join(str(project.get("title") or "").split())[:120] or "untitled"
    look = project.get("look")
    look = look.strip()[:PROJECT_LOOK_SHOWN] if isinstance(look, str) else ""
    standing = project.get("standing")
    standing = " ".join(standing.split())[:400] if isinstance(standing, str) else ""
    return (f"This conversation is INSIDE the project “{title}”: its brief and what it "
            "has learned are in your instructions. Continue that project's story and "
            "work; do not propose creating or saving a project. "
            + (f"The project's LOOK, which every scene in it is held to:\n{look}" if look
               else "The project has no look set yet.")
            + (f"\nWhere it stands now, read off its scenes: {standing}" if standing else ""))


def kit_instructions(brand_kit, project=None) -> str:
    """The kit block for the system instruction, "" for no kit."""
    if not brand_kit:
        return ""
    from . import brand_kits
    picked = bool(project and isinstance(project, dict)
                  and project.get("brand_kit_id") == brand_kit.get("id"))
    try:
        return "\n\n" + brand_kits.guide_block(brand_kit, picked_by_project=picked)
    except Exception as e:                  # a kit is an addition, never a gate
        print(f"note: brand kit not shown to the brain: {e}", file=sys.stderr)
        return ""


def _attach_kit(contents, brand_kit) -> None:
    """The kit's logo and look references, on the person's last message,
    AFTER their own pictures (which the reference count names)."""
    if not brand_kit:
        return
    from . import brand_kits
    for raw, mime, label in brand_kits.guide_images(brand_kit):
        contents[-1].parts.extend([types.Part.from_text(text=label),
                                   types.Part.from_bytes(data=raw, mime_type=mime)])


def respond(conversation, *, client, grounding, image_refs=(),
            account_id=None, on_retry=None, tools=None, run_tool=None, brain=None,
            assistant=None, judge=None, links=None, output=None, project=None,
            on_text=None, skill=None, results=None, explore=False, brand_kit=None):
    """One Guide turn.

    `brand_kit` (2026-10-21, src/brand_kits.py) is the kit in play: the
    project's pick, or one of the account's kits the person named in this
    conversation. The instructions carry `brand_kits.guide_block` and the
    last message carries the kit's logo and first look references, so the
    brain answers from the brand on file instead of guessing from its name
    or hunting the web for it. None is the turn it was.

    `explore` (2026-10-11, item 13) says the project this turn runs inside
    is switched to Explore: the maker block is left out of the instructions
    and the last message carries `explore_note` instead of the output's
    line. The tools handed in are the route's to narrow
    (guide_tools.session(explore=True) publishes no make tool and adds
    switch_to_make); a call to that one ends the turn as a proposal whose
    line says nothing was made. False is the turn it was.

    `results` (2026-10-11, src/result_refs.py) is what this conversation has
    made, by the numbers the person sees on it -- [{n, kind, label}] as the
    page sent it. A turn handed a tool that can name one (make_image,
    make_video, apply_effect) is told the list on its last message, and any
    number a call names is held to it. None, or a turn with no such tool,
    is the turn it was.

    `skill` (2026-10-10, src/skills.py) is a skill the PERSON picked from
    the composer's `/` menu: its recipe rides on their last message, already
    loaded, and the reply's tool_runs names it. Separately, when the tools
    handed in include load_skill, the instructions carry the shelf's index
    so the model can load one itself. A turn handed neither is the turn it
    was.

    `project` (2026-10-07) is the studio project the turn runs inside
    (src/projects.py's row), when it does: the last message carries one
    line naming it, so the model knows it is already in one and never
    proposes creating another; its brief and memory reach the
    instructions through shootgen.project_brief as they always did.

    With `tools` (the specs `guide_tools.session` returns) and
    `run_tool`, the model may call the board's READ tools before it
    answers -- each call runs here, its text goes back as a function
    response, and the loop continues, up to MAX_TOOL_CALLS. A WRITE
    tool call ends the turn instead: nothing runs, and the reply
    carries it as `proposal` for the thread's confirm card. Without
    tools this is the plain conversation it was, byte for byte.

    `brain` is a gemini_utils.BRAINS key; anything else resolves to
    DEFAULT_BRAIN (resolve_brain's own clamp, so a typo answers cheaply
    rather than not at all).

    `assistant` (2026-09-26) turns the Guide into the assistant pill's
    brain: {name, tone, stage, page, memory} -- see
    src/assistant_brain.py. With it, the system instruction carries the
    step's playbook and what is already known, and any story directions
    the model writes are graded by story_judge (`judge`, injectable)
    before they are returned. Without it, the Guide is byte-for-byte
    what it was.

    `links` (2026-10-01) is `assistant_brain.link_sheet`'s result for the
    http(s) links the ROUTE read off the person's own last message: their
    frames go FIRST on `reply.sheet`, ahead of anything find_references
    found this turn, and the model is handed one line saying they are
    there (`assistant_brain.link_note`) -- never the address. Without it,
    nothing changes.

    `output` (2026-10-04) is the composer's Image | Video switch. With it,
    the instructions carry the maker block (prompts/creative_guide_make.txt)
    and the last message says which output a "make it" would make; the
    tools handed in by the route then include make_image / make_video
    (guide_tools.MAKE_SPECS). Without it -- the pill, every older caller --
    the turn is byte for byte what it was.

    `on_text` (2026-10-08, the assistant card) is told the answer's
    `message` as the model writes it (`partial_message` over the streamed
    JSON), "" whenever what it was told no longer stands -- a retry, or a
    tool round that starts over. It only ever hears the reply's own words;
    the return value is the whole reply, exactly as without it.
    """
    brain = gemini_utils.resolve_brain(brain or DEFAULT_BRAIN)
    feed = _Partial(on_text) if on_text is not None else None
    # The fast tier's config is None on purpose (its request is the one
    # this module has always sent); the Guide needs an object to hang
    # the system instruction and the response schema on.
    config = (brain["config"].model_copy(deep=True) if brain["config"] is not None
              else types.GenerateContentConfig())
    from . import assistant_brain, guide_tools, look_research, make_plan, model_menu, result_refs, skills

    picked = skills.clean_name(skill)
    offered = {t.get("name") for t in tools or []}
    exploring = bool(explore)
    config.system_instruction = instructions(with_tools=bool(tools), assistant=assistant,
        maker=bool(output) and not exploring,
        with_skills=skills.TOOL in offered, with_plan=make_plan.TOOL in offered,
        with_effects="apply_effect" in offered,
        with_research=look_research.TOOL in offered,
        with_models=model_menu.TOOL in offered,
        with_explore=exploring,
        with_kit=guide_tools.KIT_TOOL in offered)
    config.system_instruction += kit_instructions(brand_kit, project)
    # the kit a propose_kit_change call is held to: the project's own
    kit = None
    if guide_tools.KIT_TOOL in offered:
        from . import brand_kits
        kit = brand_kits.for_project(project)
    # the numbered results, only where a tool can take a number
    named = (results if offered & {"make_image", "make_video", "apply_effect",
                                   *guide_tools.QUICK_TOOLS} else None)
    contents = _contents(conversation, grounding, image_refs,
                         notes=(assistant_brain.link_note(links),
                                explore_note(guide_tools.SWITCH_TOOL in offered)
                                if exploring else OUTPUT_NOTES.get(output or "", ""),
                                project_note(project),
                                "" if exploring or "make_video" not in offered
                                else photo_note(output, image_refs, grounding),
                                result_refs.note(named),
                                skills.picked_note(picked)))
    _attach_kit(contents, brand_kit)
    if not tools:
        config.response_mime_type = "application/json"
        config.response_json_schema = Answer.model_json_schema()
        raw = gemini_utils.generate_with_retry(
            client, brain["model"], contents, config=config, fallbacks=brain["fallbacks"],
            stage="creative_guide", account_id=account_id, on_retry=on_retry, on_text=feed)
        reply = Reply.model_validate_json(raw).model_dump()
    else:
        reply = _respond_with_tools(client, brain, config, contents, tools, run_tool,
                                    account_id=account_id, on_retry=on_retry, feed=feed,
                                    results=named, kit=kit)
    if links:
        reply["sheet"] = assistant_brain.merge_sheets(links, reply.get("sheet"))
    if picked:
        reply["tool_runs"] = _with_skill(picked, reply.get("tool_runs"))
    if assistant is not None:
        reply = _finish(reply, client=client, judge=judge, on_retry=on_retry,
                        said=" ".join(m.content for m in conversation.messages
                                      if m.role == "user"))
    return reply


def _with_skill(picked: str, runs) -> list:
    """The reply's tool runs with the person's picked skill first -- unless
    the model loaded that same one anyway, which is one use, not two."""
    from . import skills

    runs = list(runs or [])
    again = any(r.get("tool") == skills.TOOL and (r.get("args") or {}).get("name") == picked
                for r in runs)
    return runs if again else [skills.run_entry(picked)] + runs


def _finish(reply: dict, *, client, judge=None, on_retry=None, said: str = "") -> dict:
    """The assistant's checking step, after the model has answered:
    grade the directions with the independent judge, best first, and
    keep `stage` inside the known steps. Never raises."""
    from . import assistant_brain

    reply["stage"] = assistant_brain.clean_stage(reply.get("stage"))
    if reply.get("directions"):
        if on_retry is not None:
            on_retry("checking the directions")
        try:
            # an ad is graded as an ad; `said` is the person's side of the
            # conversation, which is where "a 6-second ad" was said
            kind, seconds = assistant_brain.direction_kind(said)
            reply["directions"] = assistant_brain.check_directions(
                reply["directions"], client=client, judge=judge,
                kind=kind, seconds=seconds)
        except Exception:                       # the unjudged list is still an answer
            pass
    return Reply.model_validate(reply).model_dump()


MAX_TOOL_CALLS = 6


def _respond_with_tools(client, brain, config, contents, tools, run_tool, *,
                        account_id=None, on_retry=None, feed=None, results=None, kit=None):
    from . import guide_tools, make_plan

    # Gemini refuses a JSON response schema alongside function
    # declarations, so the answer is asked for as JSON in the
    # instructions and parsed off the text; a turn that comes back
    # unparseable gets ONE more call with the schema and no tools.
    config.tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(name=t["name"], description=t["description"],
                                  parameters_json_schema=t["input_schema"])
        for t in tools])]
    runs: list[dict] = []
    proposal = None
    for _ in range(MAX_TOOL_CALLS + 1):
        if feed is not None:
            feed("")          # a tool round starts over: nothing it said stands
        response = gemini_utils.generate_with_retry(
            client, brain["model"], contents, config=config, fallbacks=brain["fallbacks"],
            stage="creative_guide", account_id=account_id, on_retry=on_retry, raw=True,
            on_text=feed)
        calls = list(response.function_calls or [])
        if not calls:
            text = (response.text or "").strip()
            break
        contents.append(response.candidates[0].content)
        parts = []
        for fc in calls:
            name, args = fc.name, dict(fc.args or {})
            if guide_tools.is_write(name):
                # The turn ends on the FIRST write: the card is the answer.
                try:
                    clean = guide_tools.check_args(name, args, results)
                    if name == guide_tools.KIT_TOOL:
                        clean = guide_tools.check_kit(clean, kit)
                except guide_tools.Refused as exc:
                    # An effect is held to a table of exact names, and the
                    # refusal lists the legal ones: the model gets it back
                    # as the call's result and may ask again, inside the
                    # same read budget. Every other refused write still
                    # fails the turn -- a URL in a proposal is not a typo.
                    if (name not in (guide_tools.EFFECT_TOOL, guide_tools.TALK_TOOL,
                                     guide_tools.KIT_TOOL, *guide_tools.QUICK_TOOLS)
                            or len(runs) >= MAX_TOOL_CALLS):
                        raise
                    runs.append({"tool": name, "args": args, "ok": False})
                    parts.append(types.Part.from_function_response(
                        name=name, response={"result": f"error: {exc}"[:12000]}))
                    continue
                if name == guide_tools.PLAN_TOOL:
                    # a plan of one step is that step's own tool
                    single = make_plan.collapse(clean)
                    if single:
                        name, clean = single
                proposal = {"tool": name, "args": clean,
                            "label": guide_tools.WRITE_LABELS.get(name, name)}
                break
            if len(runs) >= MAX_TOOL_CALLS:
                result, ok = "tool budget for this turn is spent; answer now", False
            else:
                try:
                    result, ok = run_tool(name, args), True
                except Exception as exc:          # a refusal or a tool error IS the result
                    result, ok = f"error: {exc}", False
            runs.append({"tool": name, "args": args, "ok": ok})
            if on_retry is not None:
                on_retry(guide_tools.step_note(name, args))
            parts.append(types.Part.from_function_response(
                name=name, response={"result": result[:12000]}))
        if proposal is not None:
            text = ""
            break
        contents.append(types.Content(role="user", parts=parts))
    else:                                          # loop exhausted without a plain answer
        text = ""

    # A contact sheet a read tool left behind this turn (find_references)
    # rides on the reply for the thread to draw; the model only saw ids.
    sheet = (getattr(run_tool, "attachments", None) or {}).get("sheet")
    # ... and what research_look read: the name, the look, the pages
    research = list((getattr(run_tool, "attachments", None) or {}).get("research") or [])
    if proposal is not None:
        message = (f"I can {proposal['label'].lower()}: "
                   f"{json.dumps(proposal['args'], default=str)}. Confirm on the card to do it.")
        # A make is no confirm card (2026-10-08): the composer writes a scene
        # at once and holds a still on Approve, under this line -- so the line
        # is what will be made, in the brain's own words, never the JSON.
        prompt = str(proposal["args"].get("prompt") or "").strip()
        if guide_tools.is_make(proposal["tool"]) and prompt:
            message = prompt if len(prompt) <= 1200 else prompt[:1200].rsplit(" ", 1)[0] + "…"
        if proposal["tool"] == guide_tools.PLAN_TOOL:
            # the plan's card lists the steps; this is the line above it
            message = proposal["args"]["summary"]
        if proposal["tool"] == guide_tools.EFFECT_TOOL:
            # the effect's card shows what it acts on and the price
            message = guide_tools.effect_line(proposal["args"])
        if proposal["tool"] == guide_tools.TALK_TOOL:
            # the card asks for the photo, the consent and the voice
            message = guide_tools.talk_line(proposal["args"])
        if guide_tools.is_quick(proposal["tool"]):
            # a free edit runs at once: the line says what and that it is free
            message = guide_tools.quick_line(proposal["tool"], proposal["args"])
        if proposal["tool"] == guide_tools.SWITCH_TOOL:
            # the card offers the switch; this line says nothing was made
            message = guide_tools.switch_line(proposal["args"])
        if proposal["tool"] == guide_tools.LOOK_TOOL:
            # the card shows the look itself; this is the line above it
            message = ("Here is the look to save as this project's own. Confirm it on the "
                       "card, or tell me what to change.")
        if proposal["tool"] == guide_tools.KIT_TOOL:
            # the card shows each field before and after; this is the line above it
            fields = ", ".join(r["label"].lower() for r in proposal["args"].get("diff") or [])
            message = (f"Here is the change to {proposal['args'].get('kit_name') or 'the kit'}"
                       f" ({fields}). Apply it on the card, or tell me what to change.")
        if proposal["tool"] == guide_tools.SHEET_TOOL:
            # the step card's own words: who is saved, and what is drawn
            who = proposal["args"].get("name") or "this character"
            wear = proposal["args"].get("notes")
            message = (f"Save {who} as a character from the photos you attached and draw "
                       "the reference sheet: full-body front, three-quarter, side profile, "
                       "back and a head-and-shoulders close-up"
                       + (f", wearing {wear}." if wear else ", in the clothes from the photos."))
        return Reply(message=message, proposal=proposal, tool_runs=runs,
                     sheet=sheet, research=research).model_dump()
    reply = _parse_reply(text)
    if reply is None:
        # One more call, schema on, tools off, the conversation so far
        # (tool results included) as context.
        config.tools = None
        config.response_mime_type = "application/json"
        config.response_json_schema = Answer.model_json_schema()
        contents.append(types.Content(role="user", parts=[types.Part.from_text(
            text="Answer now as the JSON described, using what the tools returned.")]))
        raw = gemini_utils.generate_with_retry(
            client, brain["model"], contents, config=config, fallbacks=brain["fallbacks"],
            stage="creative_guide", account_id=account_id, on_retry=on_retry, on_text=feed)
        reply = Answer.model_validate_json(raw)
    return Reply(**reply.model_dump(), tool_runs=[ToolRun(**r) for r in runs],
                 sheet=sheet, research=research).model_dump()


# The `message` string of a JSON answer still being written, opened by
# its key: the first one, which is the reply's own (Answer puts it first).
_MESSAGE_OPEN = re.compile(r'"message"\s*:\s*"')
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n",
            "r": "\r", "t": "\t"}


def partial_message(raw: str) -> str:
    """How much of the answer's `message` has been written so far, decoded.

    `raw` is the model's JSON as far as it has come -- fenced or not, the
    closing quote maybe not written yet, an escape maybe cut in half. The
    string is read up to its closing quote or to the last character that
    can be decoded; an escape not finished yet is left for the next chunk.
    "" until the key has appeared. Pure, never raises."""
    opened = _MESSAGE_OPEN.search(raw or "")
    if opened is None:
        return ""
    out, i, n = [], opened.end(), len(raw)
    while i < n:
        c = raw[i]
        if c == '"':
            break
        if c != "\\":
            out.append(c)
            i += 1
            continue
        if i + 1 >= n:
            break
        e = raw[i + 1]
        if e != "u":
            out.append(_ESCAPES.get(e, e))
            i += 2
            continue
        code = _hex4(raw, i + 2)
        if code is None:
            break
        if 0xD800 <= code < 0xDC00:              # the high half of a pair
            after = raw[i + 6:i + 8]
            if after != "\\u":
                if len(after) < 2 and "\\u".startswith(after):
                    break                        # its low half is not written yet
                i += 6                           # a lone high half is dropped
                continue
            low = _hex4(raw, i + 8)
            if low is None:
                break
            if 0xDC00 <= low < 0xE000:
                out.append(chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)))
            i += 12
            continue
        if not 0xDC00 <= code < 0xE000:          # a lone low half is dropped
            out.append(chr(code))
        i += 6
    return "".join(out)


def _hex4(raw: str, at: int):
    digits = raw[at:at + 4]
    if len(digits) < 4:
        return None
    try:
        return int(digits, 16)
    except ValueError:
        return None


class _Partial:
    """Tells `on_text` the message so far, only when it changed -- a chunk
    that only extends `choices` is not news."""

    def __init__(self, on_text):
        self.on_text, self.told = on_text, ""

    def __call__(self, raw: str) -> None:
        message = partial_message(raw)
        if message != self.told:
            self.told = message
            self.on_text(message)


def _parse_reply(text: str):
    """The model's JSON answer off a tools turn, or None when it is
    not one. Fences are stripped; a bare sentence is not an answer."""
    if not text:
        return None
    try:
        return Answer.model_validate_json(gemini_utils.strip_fences(text))
    except Exception:
        return None


def instructions(with_tools: bool = False, assistant=None, maker: bool = False,
                 with_skills: bool = False, with_plan: bool = False,
                 with_effects: bool = False, with_research: bool = False,
                 with_models: bool = False, with_explore: bool = False,
                 with_kit: bool = False):
    root = Path(__file__).resolve().parent.parent
    text = (root / "prompts/creative_guide.txt").read_text()
    # Vesper's voice (2026-10-19, the Vesper review): how every message
    # sounds, on every turn -- the plain Guide, the composer and the pill
    text += "\n\n" + (root / "prompts/creative_guide_voice.txt").read_text()
    if with_tools:
        text += "\n\n" + (root / "prompts/creative_guide_tools.txt").read_text()
    if maker:
        text += "\n\n" + (root / "prompts/creative_guide_make.txt").read_text()
    if with_explore:
        # only inside a project switched to Explore, and never beside the
        # maker block (respond passes maker=False there)
        text += "\n\n" + (root / "prompts/creative_guide_explore.txt").read_text()
    if with_plan:
        # only where make_plan is offered (the composer; src/make_plan.py)
        text += "\n\n" + (root / "prompts/creative_guide_plan.txt").read_text()
    if with_effects:
        # only where apply_effect is offered (the composer; src/effects.py)
        text += "\n\n" + (root / "prompts/creative_guide_effects.txt").read_text()
    if with_models:
        # only where list_models is offered (the composer; src/model_menu.py)
        text += "\n\n" + (root / "prompts/creative_guide_models.txt").read_text()
    if with_research:
        # only where research_look is offered (src/look_research.py)
        text += "\n\n" + (root / "prompts/creative_guide_research.txt").read_text()
    if with_kit:
        # only where propose_kit_change is offered (src/kit_changes.py)
        text += "\n\n" + (root / "prompts/creative_guide_kit.txt").read_text()
    if with_skills:
        # the shelf's index, only where load_skill is offered (src/skills.py)
        from . import skills
        index = skills.index_block()
        if index:
            text += "\n\n" + index
    if assistant is not None:
        from . import assistant_brain
        text += "\n\n" + assistant_brain.instructions(
            name=assistant.get("name", ""), tone=assistant.get("tone", ""),
            stage=assistant.get("stage", ""), page=assistant.get("page", ""),
            mem=assistant.get("memory"))
    return text + "\n\nProject:\n" + shootgen.project_brief()


ASSISTANT_FIELDS = ("questions", "directions", "nudge", "stage")


def _strict(schema: dict) -> dict:
    """A strict structured-output schema: every object closed, every
    property required, no defaults -- at the top level AND in $defs,
    since Question / Direction nest (2026-09-26)."""
    def close(node: dict) -> None:
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
            for spec in node["properties"].values():
                spec.pop("default", None)
    close(schema)
    for sub in (schema.get("$defs") or {}).values():
        close(sub)
    return schema


def respond_personal(conversation, *, provider, scope, model, grounding, image_refs=(),
                     assistant=None, links=None, output=None, skill=None, brand_kit=None):
    from . import assistant_brain, personal_models, skills

    # no tools here, so the model cannot load a skill -- but one the person
    # picked rides in the prompt, exactly as it rides on a Gemini turn
    picked = skills.clean_name(skill)

    # A personal connection has no tools, so it cannot make; it is told
    # which output the composer is set to and talks toward it. The brief
    # it writes is what the composer's "Make this" button makes from.
    prompt = json.dumps({"grounding": grounding, "conversation": conversation.model_dump(),
                         "reference_images_supplied": len(image_refs),
                         "pasted_links": assistant_brain.link_note(links),
                         "composer_output": OUTPUT_NOTES.get(output or "", ""),
                         "picked_skill": skills.picked_note(picked)}, default=str)
    schema = Answer.model_json_schema()
    if assistant is None:
        # The plain Guide on a personal plan answers the three fields it
        # always did: a strict schema makes every property REQUIRED, and
        # a person's own model should not be made to emit assistant
        # fields nobody will draw.
        for key in ASSISTANT_FIELDS:
            schema["properties"].pop(key, None)
        schema.pop("$defs", None)
    schema = _strict(schema)
    # the kit in words only: a personal model is handed the person's own
    # pictures, and the reference count it is told is theirs
    system = instructions(assistant=assistant) + kit_instructions(brand_kit)
    if provider == "chatgpt":
        raw = personal_models.codex_session(scope).generate(
            prompt, system, schema, image_refs, model)
    elif provider == "claude":
        raw = personal_models.claude_generate(scope, prompt, system, schema, image_refs, model)
    else:
        raise ValueError("Unknown personal provider")
    reply = Reply.model_validate_json(raw).model_dump()
    if links:
        reply["sheet"] = assistant_brain.merge_sheets(links, reply.get("sheet"))
    if picked:
        reply["tool_runs"] = _with_skill(picked, reply.get("tool_runs"))
    if assistant is not None:
        # No judge here: it would bill this install's Gemini for a turn
        # the person's own plan is paying for. Stage is still clamped.
        reply["stage"] = assistant_brain.clean_stage(reply.get("stage"))
    return reply
