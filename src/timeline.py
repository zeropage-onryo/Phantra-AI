#!/usr/bin/env python3
"""
src/timeline.py -- a scene's timed windows, as the separate shots that get
rendered (2026-09-10, Mike's call).

A scene prompt may now carry several shots, cuts and locations, each in its
own time window -- (0-3s) one shot, (3-7s) a different one. That is how the
scene is WRITTEN. It is not how it is RENDERED: every window becomes its own
clip, rendered one after another, each by a model that has never seen the
others. So between the scene and the renderer sits one planning step, run on
the same brain the scene was written on:

    scene prompt + its reference photos
        -> continuity   the scene's memory, written once and put in front of
                        every shot (same face, same clothes, same prop, same
                        light), because nothing else carries over
        -> parts        one standalone prompt per window, each with ONLY the
                        reference photos that shot shows

Stored on the scene's ONE shot as `shot["timeline"]`, which keeps a concept
exactly the unit it has been since 2026-08-26 -- one row, one scene, one
entry in `shots`. `is_scene`, pick_rate, the Queue and the board all keep
reading `len(shots) == 1`; the parts live one level down.

Three rules worth keeping:

- **Refs are chosen by NUMBER from the scene's own set, never by URL** (the
  closed-set rule image sourcing already follows). A part can only narrow
  the scene's references, never add one -- so the reference gate asked of the
  scene still covers every part, and order within a part keeps the scene's
  order (identity first, which is what an anchor slot needs).
- **Staleness is checked on READ.** A timeline records a hash of the prompt
  and refs it was planned from; a Director edit, a Polish or a new ref makes
  it stale and `ensure` re-plans. The saved-canvas lesson (`seed_hash`): a
  route added later that rewrites a prompt cannot forget to invalidate this.
- **No timed windows means no timeline**, and the scene renders as one clip
  exactly as before. Every scene written before 2026-09-10 is that case.

Never raises. A failed planning call degrades to a deterministic split (the
window's own sentence, the rest of the scene as context, every ref), and a
scene that cannot be split at all is simply not split.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Callable, Optional

from . import preprod

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "shot_timeline_prompt.txt"

# The whole-scene length the writers are asked to fill. One number the
# composer, the night and the MCP `generate` all default to, read per call
# like every other PHANTRA_* posture.
SCENE_SECONDS_ENV = "PHANTRA_SCENE_SECONDS"
DEFAULT_SCENE_SECONDS = 10
# Bounds on what a person may ask for. The floor is one shot's worth; the
# ceiling is not a renderer limit (each window renders on its own) but a
# planning one: past ~30s a "scene" is a sequence, and the writer starts
# padding windows to fill the clock.
MIN_SCENE_SECONDS = 4
MAX_SCENE_SECONDS = 30
# The legacy /ui select's menu. The React composer's duration is a SLIDER
# over MIN..MAX (2026-10-02, Mike: "toggle it like a slider and choose any
# amount of time"), and scene_seconds takes any whole second in between.
SCENE_SECONDS_CHOICES = (5, 10, 15, 20, 30)
# There is NO cap on how many shots a scene is split into (2026-10-02,
# Mike's call: "as many shots as are needed by the prompt"). There used to
# be -- MAX_PARTS = 8, which dropped every window past the 8th without a
# word, off the card, the price and the render. Every part is its own still
# and its own clip, but every one of those is priced and sits behind a
# person's approve; the approve is the limit, not a constant here.

# --- WHAT A VIDEO MODEL IS ACTUALLY FOR (2026-09-12) ----------------------
# Every renderer this repo drives is image-to-video: it is handed a frame and
# a prompt. The frame already says what the shot LOOKS like -- so a prompt
# that describes the scene again is spending its whole budget restating what
# the model can see, and saying nothing about the only thing it has to
# invent, which is what changes across the window. Worse on the reference
# lane, where there is no locked first frame at all and the prompt is
# carrying MORE of the load, not less.
#
# Two rules, both from the shot-prompt playbook and both things the models
# get wrong by default: a clip that starts and stops from a dead stop reads
# as an obvious generation, and a camera that moves independently of the
# subject reads as arbitrary. prompts/shot_timeline_prompt.txt already ASKS
# the planner for "Start mid-motion"; this is the same rule enforced at the
# render boundary, where asking is no longer good enough -- the planner is a
# model too, and a scene written before this line existed never heard it.
#
# Deliberately ~130 characters. Prompt caps refuse rather than truncate
# (Kling v3 on fal: 2500) and a director's prompt with its continuity block
# already runs long, so anything longer would start turning working renders
# into refusals.
# PHANTRA_MOTION_DIRECTIVE=0 turns it off for a prompt that needs the room.
MOTION_DIRECTIVE = (
    "RENDER THE CHANGE, not the frame: open already mid-motion, end still "
    "moving, and move the camera only with the subject."
)


def motion_directive() -> str:
    """The directive, or "" when it is switched off. Read per call like
    every other PHANTRA_* posture, so a test can set it either way."""
    if (os.environ.get("PHANTRA_MOTION_DIRECTIVE") or "").strip() == "0":
        return ""
    return MOTION_DIRECTIVE


def for_render(prompt: str) -> str:
    """One prompt, as a VIDEO renderer should receive it: the directive
    first, because these models weight the top of a prompt most heavily,
    then whatever the scene or the part already said.

    Applied in render_target and nowhere else, on purpose. render_prompt
    also feeds scene_chain's keyframe draw, and telling a STILL to open
    mid-motion is noise at best -- the frame is the one thing in this
    pipeline that is supposed to hold still."""
    prompt = (prompt or "").strip()
    directive = motion_directive()
    if not prompt or not directive:
        return prompt
    return f"{directive}\n\n{prompt}"


def without_directive(prompt: str) -> str:
    """`prompt` with the motion directive taken back off its top, for a
    model whose own guidance contradicts it (fal.DIRECTIVE_OFF_PLATFORMS,
    2026-10-23: Grok Imagine). Anything else is returned as it came."""
    prompt = prompt or ""
    if prompt.startswith(MOTION_DIRECTIVE):
        return prompt[len(MOTION_DIRECTIVE):].lstrip("\n")
    return prompt


def scene_seconds(value=None) -> int:
    """The total length a scene is written to. `value` wins (the composer's
    select, an explicit graph argument); then PHANTRA_SCENE_SECONDS; then
    the default. Clamped, never refused: this is read from a form field and
    an env var on a 3:30am job, and a typo must write a 10s scene rather
    than fail the night -- the resolve_brain rule."""
    for raw in (value, os.environ.get(SCENE_SECONDS_ENV)):
        try:
            if raw is not None and str(raw).strip():
                seconds = int(float(str(raw).strip()))
                return max(MIN_SCENE_SECONDS, min(MAX_SCENE_SECONDS, seconds))
        except (TypeError, ValueError):
            continue
    return DEFAULT_SCENE_SECONDS


# "(0-3s)", "(0s-3s)", "(3–7 s)", "(7 - 10 sec)". At least one "s" is
# required so an ordinary parenthetical range -- "(2-3 people)" -- is not
# read as a clock.
_WINDOW = re.compile(
    r"\(\s*(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds)?\s*(?:-|–|—|to)\s*"
    r"(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds)?\s*\)",
    re.IGNORECASE)
# Where the BEATS section ends and the sound / avoid blocks begin, so the
# last window's text does not swallow them.
_SECTION_BREAK = re.compile(
    r"\n\s*(?:\d\.\s*)?(?:SOUND|AVOID|AUDIO|NEGATIVE)\b|\n\s*[45]\.\s", re.IGNORECASE)

# --- the scene's tail (2026-10-11) ------------------------------------------
# _SECTION_BREAK only sees a label that starts a LINE, and a scene is as often
# one paragraph: both writers and a chat write "... End abruptly. No background
# music. Only diegetic sound: ... Avoid: ...". Read that way the LAST window
# ran to the end of the prompt, so the sound line and the avoid-list were
# shot N's action, and no other shot heard them (found on the connector's
# scene 403; the same shape is in studio-written scenes).
#
# So the last window also ends where the scene's tail begins: a SENTENCE that
# opens with a sound or avoid line, or a LINE that opens with a look label
# (older studio scenes put "LOOK: ..." under the beats). Narrow on purpose --
# a label needs its colon, the two bare phrases are the ones the writers are
# told to use, and a look label counts only at the start of a line -- because
# a miss leaves a sound line on one shot, while a false hit moves a shot's own
# action into every shot's memory. The named group is the KIND of line; see
# _scan for why that matters.
_NUMBERED = r"(?:\d\s*[.)]\s*)?"
# A voiceover line is a kind of tail too (2026-10-22): "VO: ..." written
# after the last window is the scene's, read over the whole thing, not the
# last shot's action. _VOICE_START, below, reads the label shapes.
_VOICE_KINDS = r"(?:VOICE[\s-]*OVERS?|V\.\s*O\.?|VO|NARRAT(?:OR|ION))"
_SOUND_OR_AVOID = (
    r"(?P<sound>(?:SOUNDS?|AUDIO)(?:\s+DESIGN)?\s*:)"
    r"|(?P<avoid>(?:AVOID(?:[\s-]+LIST)?|NEGATIVES?(?:\s+PROMPT)?)\s*:)"
    r"|(?P<music>No\s+background\s+music\b)"
    r"|(?P<diegetic>(?:Only\s+)?diegetic\s+(?:sounds?|audio)\b)"
    r"|(?P<voice>" + _VOICE_KINDS + r"\s*(?:\([^)]{0,40}\))?\s*:)")
_LOOK = r"(?P<look>(?:THE\s+)?(?:LOOK|STYLE|TEXTURE)\s*:)"
_TAIL = re.compile(
    r"(?:^|(?<=[.!?;…\n])|(?<=[.!?…][\"'”’)\]]))\s*"
    + _NUMBERED + r"(?:" + _SOUND_OR_AVOID + r")"
    r"|(?<=\n)\s*" + _NUMBERED + _LOOK, re.IGNORECASE)
# Any of those at the front of what an OLD stored text carried past the
# shot's own words (see _same_shot). A stored text has its line breaks
# folded, so a look label cannot be asked to start a line here.
_TAIL_AFTER = re.compile(
    r"[\s.!?;…\"'”’)\]]+" + _NUMBERED + r"(?:" + _SOUND_OR_AVOID + r"|" + _LOOK + r")",
    re.IGNORECASE)


def parse_windows(prompt: str) -> list[dict]:
    """The timed windows a scene prompt carries, in order, each with the
    text that follows its marker: [{"start", "end", "seconds", "text"}].

    [] when the prompt has fewer than two windows -- a single window is one
    shot, which is what the scene already is, and splitting it would buy a
    planning call and nothing else. Windows that run backwards or have no
    length are dropped rather than repaired: they are model output, and
    guessing what it meant is how a 3s shot becomes a 30s render. Every
    other window is kept, however many there are: no cap."""
    windows = _windows(prompt)
    return windows if len(windows) >= 2 else []


def _scan(prompt: str) -> list:
    """Every window marker in the prompt, in the order written, with where
    its own words run: [(marker, start, end)], `prompt[start:end]` being
    that shot and nothing else.

    A window's words stop at the next marker or at a section label on a new
    line (_SECTION_BREAK). The LAST one also stops where the scene's tail
    begins (_TAIL), whether or not a line break comes first. One exception:
    a kind of line an EARLIER window carries too -- "Sound: ..." written
    under every beat -- is that scene's way of writing each shot, not its
    tail, and stays with the last shot as it stays with the others."""
    prompt = prompt or ""
    marks = [m for m in _WINDOW.finditer(prompt) if m.group(2) or m.group(4)]
    found, per_shot = [], set()
    for i, m in enumerate(marks):
        last = i + 1 == len(marks)
        body = prompt[m.end():len(prompt) if last else marks[i + 1].start()]
        brk = _SECTION_BREAK.search(body)
        cut = brk.start() if brk else len(body)
        if last:
            tail = next((t for t in _TAIL.finditer(body[:cut])
                         if t.lastgroup not in per_shot), None)
            if tail:
                cut = tail.start()
        else:
            per_shot.update(t.lastgroup for t in _TAIL.finditer(body))
        found.append((m, m.end(), m.end() + cut))
    return found


def _windows(prompt: str) -> list[dict]:
    """Every well-formed window, including a lone one."""
    prompt = prompt or ""
    windows = []
    for m, a, b in _scan(prompt):
        start, end = float(m.group(1)), float(m.group(3))
        if end <= start:
            continue
        windows.append({"start": _num(start), "end": _num(end),
                        "seconds": _num(end - start),
                        "text": " ".join(prompt[a:b].split()).strip(" .;,-")})
    windows.sort(key=lambda w: w["start"])
    return windows


def _num(x: float):
    return int(x) if float(x).is_integer() else round(float(x), 2)


# --- how many shots, and who decided --------------------------------------
# The count is the IDEA's (2026-10-02, Mike: "as many shots as are needed
# by the prompt"), cut into two or more by default, and a single continuous
# take only when the person asked for one ("I don't want just one
# continuous shot unless asked for in the prompt or chatting with the
# agent"). The writers are TOLD that (prompts/scenes_prompt.txt,
# scene_brief_prompt.txt); this is the code that checks the answer, and it
# only ever ADVISES -- a warning on the saved concept, never a rejected
# scene (prompts request, code advises).
#
# What reads as asking for one take. Generous on purpose: a phrase wrongly
# read as a one-take request only SKIPS a warning, so a miss here costs
# nothing a person can see.
_ONE_TAKE = re.compile(
    r"\b(?:one|single|1)[\s-]+(?:continuous[\s-]+|unbroken[\s-]+|uncut[\s-]+)?(?:take|shot)\b"
    r"|\b(?:continuous|unbroken|uncut)[\s-]+(?:take|shot)\b|\blong[\s-]+take\b"
    r"|\boner\b|\bno[\s-]+cuts?\b|\bwithout[\s-]+(?:a[\s-]+|any[\s-]+)?cuts?\b",
    re.IGNORECASE)
_NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_COUNT = r"(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")"
# A count of SHOTS, asked for in so many words. Strict on purpose, the
# other way round: "he fires two shots", "two shots of espresso" are not a
# request about the edit, and a phrase wrongly read as one puts a false
# warning on the card. So the number needs a word around it that makes it
# about structure ("in 2 shots", "make it two shots", "a 3-shot scene",
# "4 shots total") -- a request phrased any other way is still honoured by
# the writer, which reads the whole idea; it just isn't checked here.
_ASKED_COUNT = re.compile(
    r"\b(?:in|into|across|over|as|use|using|make\s+it|cut\s+(?:it\s+)?(?:in)?to|"
    r"just|only|exactly|down\s+to|up\s+to)\s+" + _COUNT + r"[\s-]+shots?\b(?!\s+of\b)"
    r"|\b" + _COUNT + r"[\s-]+shots?\s+(?:total|only|max(?:imum)?|in\s+all)\b"
    r"|\b" + _COUNT + r"-shot\s+(?:scene|sequence|version|cut|edit)\b",
    re.IGNORECASE)


def _count(word: str) -> Optional[int]:
    word = (word or "").lower()
    if word.isdigit():
        return int(word)
    return _NUMBER_WORDS.get(word)


def requested_shots(asked: str) -> Optional[int]:
    """How many shots the person asked for, or None when they did not say.

    Two ways of saying it. The reliable one: what they asked for already
    CARRIES its own timed windows -- the Guide writes its brief that way,
    and a count agreed there ("bring it down to 2 shots") arrives as that
    many windows, scene by scene. Otherwise a count asked for in so many
    words (_ASKED_COUNT), the last one said winning, since a later
    sentence in a conversation is the change of mind."""
    marked = _windows(asked)
    if marked:
        return len(marked)
    found = [_count(next(g for g in m.groups() if g))
             for m in _ASKED_COUNT.finditer(asked or "")]
    found = [n for n in found if n]
    return found[-1] if found else None


def one_take_requested(asked: str) -> bool:
    """Did the person ask for a single continuous take?"""
    return requested_shots(asked) == 1 or bool(_ONE_TAKE.search(asked or ""))


def shot_count_warnings(prompt: str, asked: str = "") -> list[str]:
    """Advice for a written scene whose shot count is not what was asked.

    `prompt` is the scene as written, `asked` what the person typed (the
    idea, or the Guide's brief that went in as the idea). A scene with no
    timed windows, or one window, renders as ONE clip, so both count as
    one shot. Never raises; [] when the count is fine."""
    try:
        written = max(1, len(_windows(prompt)))
        want = requested_shots(asked)
        if want is not None and written != want:
            return [f"shot 1: asked for {want} shot{'s' if want != 1 else ''}, "
                    f"the scene was written as {written}"]
        if want is None and written == 1 and not one_take_requested(asked):
            return ["shot 1: written as one continuous take, and nobody asked for "
                    "one -- it renders as a single clip"]
    except Exception as e:      # advice is never worth a failed write
        print(f"note: shot count not checked: {e}", file=sys.stderr)
    return []


def source_hash(prompt: str, refs) -> str:
    """What a timeline was planned FROM. A change to either the prompt or
    the scene's refs makes it stale -- a part cannot name a reference the
    scene no longer carries."""
    blob = (prompt or "").strip() + "\n" + "\n".join(refs or [])
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def is_current(shot: dict) -> bool:
    tl = (shot or {}).get("timeline") or {}
    return bool(tl.get("parts")) and tl.get("source") == source_hash(
        shot.get("prompt") or "", shot.get("refs") or [])


def _default_brain():
    """The tier a re-plan runs on when nobody named one: the one the
    timeline was first planned with, else the night's (PHANTRA_BRAIN).
    Read here rather than imported from orchestrator, which imports this
    module's callers."""
    return (os.environ.get("PHANTRA_BRAIN") or "").strip().lower() or None


# --- planning ---------------------------------------------------------------

def caption(url: str, roles: Optional[dict] = None) -> str:
    """The line the planner reads under a reference's number: its role's
    when it has one, the element's name and kind, or -- for one of the
    studio's own renders -- what a render is (ref_roles.RENDER_CAPTION).
    Never blank: until 2026-10-22 this was shootgen.reference_label alone,
    which is "" for a render, so a still or a frame attached out of the
    Library was listed as a bare "[3]" with nothing after it, and the
    planner, told nothing about what [3] was, put it on no shot at all
    (Mike's food scene: the chef and the dish were renders, not elements,
    and the re-plan dropped both)."""
    from . import ref_roles
    return ref_roles.label(url, roles) or "Reference photo attached to this scene:"


def build_prompt(scene: str, windows: list, refs: list, *, seconds,
                 roles: Optional[dict] = None) -> str:
    listed = "\n".join(f"- {w['start']}-{w['end']}s: {w['text']}" for w in windows)
    numbered = "\n".join(f"[{i}] {caption(url, roles)}"
                         for i, url in enumerate(refs, start=1)) or "(none attached)"
    return (PROMPT_PATH.read_text()
            .replace("{seconds}", str(seconds))
            .replace("{scene}", (scene or "").strip())
            .replace("{windows}", listed)
            .replace("{references}", numbered))


def parse_response(text: str, windows: list, refs: list) -> Optional[dict]:
    """Model text -> {"continuity", "parts"} checked against reality, or None.

    The WINDOWS come from the scene, never from the answer: the model is
    told to keep them and the code keeps them either way (prompts request,
    code enforces). So the answer has to give one shot per window, in
    order; anything else is a different scene, and None sends the caller
    to the deterministic split rather than to a timeline that disagrees
    with the prompt it claims to be.

    Ref numbers outside the scene's set are dropped, duplicates collapse,
    and what is left is put back in the SCENE's order -- identity first,
    because the first ref of a part is what its still is drawn against."""
    from .gemini_utils import strip_fences
    try:
        data = json.loads(strip_fences(text or ""))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    shots = data.get("shots")
    if not isinstance(shots, list) or len(shots) != len(windows):
        return None
    parts = []
    for n, (window, item) in enumerate(zip(windows, shots), start=1):
        if not isinstance(item, dict):
            return None
        prompt = " ".join(str(item.get("prompt") or "").split())
        if not prompt:
            return None
        picked = set()
        for raw in item.get("refs") or []:
            try:
                i = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= i <= len(refs):
                picked.add(i)
        parts.append(_part(n, window, prompt, [refs[i - 1] for i in sorted(picked)]))
    continuity = " ".join(str(data.get("continuity") or "").split())
    return {"continuity": continuity, "parts": parts}


def _part(n: int, window: dict, prompt: str, refs: list) -> dict:
    # `text` is the scene's OWN sentence for this window, kept so a re-plan
    # can tell which parts the edit actually touched (see ensure).
    return {"n": n, "start": window["start"], "end": window["end"],
            "seconds": window["seconds"], "text": window.get("text") or "",
            "prompt": prompt, "refs": list(refs),
            "reference_image": None, "media_url": None}


def fallback(scene: str, windows: list, refs: list) -> dict:
    """The split with no model in it: each window's own sentence is the
    shot, the scene with EVERY window's sentence cut out is the continuity
    (its look, sound and avoid-list without its action), and every shot
    gets all the scene's refs -- over-grounding a shot costs a little
    fidelity, under-grounding it costs the face.

    The sentences are cut out BY POSITION (_scan), marker and all. They
    used to be cut by searching the scene for each window's text, and that
    text has its line breaks folded -- so a window written across a line
    break was never found, and its action went in front of every shot as
    the scene's memory."""
    scene = scene or ""
    kept, at = [], 0
    for marker, _, end in _scan(scene):
        kept.append(scene[at:marker.start()])
        at = end
    kept.append(scene[at:])
    return {"continuity": " ".join(" ".join(kept).split()),
            "parts": [_part(n, w, w["text"] or f"shot {n}", refs)
                      for n, w in enumerate(windows, start=1)]}


# --- what the planner must not lose (2026-10-22) ----------------------------
# Three things found on one food scene, all the same shape: the planner is a
# model, the prompt ASKS it to keep them, and nothing checked the answer.
#   * the chef and the dish were earlier renders from the Library, and the
#     re-plan put neither on any shot (the caption was blank, see `caption`);
#   * a voiceover line written in a window was gone from that shot's prompt
#     ("diegetic sound only" read as "drop the voice");
#   * a shot the planner gave no refs rendered from its words alone, and the
#     card said nothing.
# `keep` is the check. It KEEPS rather than only advises, because a planned
# part has no editor -- a warning alone would leave the person with nothing
# to press -- and it says what it did in `timeline["warnings"]`, which the
# card prints beside the scene's own. The reference rule is still the
# module's: a part only ever narrows the scene's refs.

# "VO:", "V.O.:", "Voiceover:", "Voice-over (warm, low):", "Narrator:",
# "Narration:" -- at the start of a line or after a sentence; the words run
# to the closing quote when the line opens with one, else to the end of the
# line, the next window or the next labelled section.
_VOICE_START = re.compile(
    r"(?:^|(?<=[\s.!?;…\"'”’)\]]))" + _NUMBERED + _VOICE_KINDS
    + r"\s*(?:\([^)\n]{0,40}\))?\s*:\s*", re.IGNORECASE)
_QUOTE_CLOSE = {'"': '"', "“": "”", "'": "'", "‘": "’", "«": "»"}
# where an unquoted line ends: a line break, an UPPERCASE label, a sound or
# avoid line (those two in any case, as _TAIL reads them)
_LABELLED = re.compile(r"\n|\b[A-Z][A-Z /&-]{2,}:|(?i:" + _SOUND_OR_AVOID + r")")
# how fast a narrator reads: src/voiceover.py's own budget, repeated here
# rather than imported because that module pulls in the talking-photo table
VOICE_WORDS_PER_SECOND = 2.5


def voice_lines(text: str) -> list[dict]:
    """Every voiceover line in `text`, in order: [{"text", "words"}],
    `text` being the line as written (label and all) and `words` the
    spoken words alone. [] when there is none."""
    text = text or ""
    out = []
    for m in _VOICE_START.finditer(text):
        rest = text[m.end():]
        close = _QUOTE_CLOSE.get(rest[:1])
        end = rest.find(close, 1) if close else -1
        if close and end > 0:
            words, stop = rest[1:end], end + 1
        else:
            brk = _WINDOW.search(rest)
            lab = _LABELLED.search(rest)
            stop = min(x.start() for x in (brk, lab) if x) if (brk or lab) else len(rest)
            words = rest[:stop].strip().strip("\"“”'‘’«»")
        words = " ".join(words.split()).strip()
        if words:
            out.append({"text": text[m.start():m.end() + stop].strip(), "words": words})
    return out


def _spoken(text: str) -> str:
    text = (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    return " ".join(re.findall(r"[a-z0-9']+", text))


def _carries(prompt: str, words: str) -> bool:
    """Does `prompt` say these words (punctuation and case aside)?"""
    want = _spoken(words)
    return bool(want) and want in _spoken(prompt)


def _voice_fit(words: str, seconds) -> Optional[str]:
    """Why this line will not fit in `seconds`, or None when it will."""
    count = len(words.split())
    need = count / VOICE_WORDS_PER_SECOND
    if need <= float(seconds or 0):
        return None
    return (f"the voiceover is {count} words, about {math.ceil(need)}s to say, "
            f"and the window is {_num(float(seconds or 0))}s -- it will not fit")


def _outside_windows(scene: str) -> str:
    """The scene with every window's own words cut out: its head and its
    tail, where a voiceover over the whole scene is written."""
    kept, at = [], 0
    for marker, _, end in _scan(scene or ""):
        kept.append(scene[at:marker.start()])
        at = end
    kept.append((scene or "")[at:])
    return " ".join(kept)


def describe_ref(url: str, roles: Optional[dict] = None) -> str:
    """One reference, named for a warning: its role, its element, or what
    kind of picture it is."""
    from . import asset_shelf, ref_roles
    role = (roles or {}).get(str(url or "").split("?")[0])
    if role in ref_roles.ROLES:
        return f"the {ref_roles.ROLES[role][0].lower()} reference"
    ref = asset_shelf.parse_ref(url)
    if ref and ref["kind"] != "refs":
        name = ref["slug"].replace("-", " ").replace("_", " ").strip().title()
        return f"{name}, {ref['kind']}" if name else ref["kind"]
    if ref:
        return "an uploaded photo"
    if ref_roles.is_render(url):
        return "an earlier render from the Library"
    return "a reference photo"


def keep(result: dict, scene: str, windows: list, refs: list, *,
         roles: Optional[dict] = None) -> list[str]:
    """Check a planned (or split) {"continuity", "parts"} against the scene
    it was planned from, put back what was dropped, and return the
    warnings for the card. Mutates `result` in place.

      * A reference that is a SUBJECT -- a role in ref_roles.IDENTITY or
        "place", an element's photo, a render, an upload; anything but a
        look-only role -- and sits on NO shot is put on every shot, in the
        scene's order, with a line saying so. That is the fallback's own
        grounding for that one picture: over-grounding a shot costs a
        little fidelity, under-grounding it costs the face.
      * A shot left with no refs at all is said on the card. Kept as the
        planner wrote it -- an empty hallway needs no portrait -- but
        never silently.
      * A voiceover line in a window's own words reaches that shot's
        prompt; one outside every window (the scene's) reaches the
        continuity. A line that cannot be said in its window at
        VOICE_WORDS_PER_SECOND is a warning either way.
    Never raises: advice is never worth a failed plan."""
    warnings: list[str] = []
    parts = result.get("parts") or []
    try:
        from . import ref_roles
        roles = roles or {}
        for i, url in enumerate(refs or [], start=1):
            if roles.get(str(url).split("?")[0]) in ref_roles.LOOK_ONLY:
                continue
            if any(url in (p.get("refs") or []) for p in parts):
                continue
            for p in parts:
                held = set(p.get("refs") or []) | {url}
                p["refs"] = [r for r in refs if r in held]
            warnings.append(f"reference {i} ({describe_ref(url, roles)}) was on none "
                            f"of the planned shots -- it is now on every shot")
        for p in parts:
            if not p.get("refs"):
                warnings.append(f"shot {p.get('n')} ({p.get('start')}-{p.get('end')}s): "
                                f"no reference photos on this shot -- it renders from "
                                f"its words alone")
        head = result.get("continuity") or ""
        for p, w in zip(parts, windows or []):
            for line in voice_lines(w.get("text") or ""):
                # the shot's own, unless the planner moved it into the memory
                # every shot already hears (render_prompt puts that first)
                if not any(_carries(t, line["words"]) for t in (p.get("prompt") or "", head)):
                    p["prompt"] = (f"{(p.get('prompt') or '').rstrip()} "
                                   f"VOICEOVER, as written: \"{line['words']}\"").strip()
                why = _voice_fit(line["words"], p.get("seconds"))
                if why:
                    warnings.append(f"shot {p.get('n')} ({p.get('start')}-{p.get('end')}s): {why}")
        total = sum(float(w.get("seconds") or 0) for w in windows or [])
        for line in voice_lines(_outside_windows(scene)):
            said = [result.get("continuity") or "", *(p.get("prompt") or "" for p in parts)]
            if not any(_carries(t, line["words"]) for t in said):
                result["continuity"] = (f"{(result.get('continuity') or '').rstrip()} "
                                        f"VOICEOVER over the whole scene, as written: "
                                        f"\"{line['words']}\"").strip()
            why = _voice_fit(line["words"], total)
            if why:
                warnings.append(why.replace("the window is", "the scene is"))
    except Exception as e:                       # noqa: BLE001
        print(f"note: shot timeline not checked: {e}", file=sys.stderr)
    return warnings


def warnings_of(shot: dict) -> list[str]:
    """The planner's warnings on a shot whose timeline is current; [] for
    a stale one, which the next read re-plans anyway."""
    if not is_current(shot or {}):
        return []
    return [str(w) for w in (shot.get("timeline") or {}).get("warnings") or [] if w]


def _reference_contents(refs: list, resolve_photo=None, account_id=None,
                        roles: Optional[dict] = None) -> list:
    """Each ref as a numbered caption followed by its bytes, for a model
    that has to SEE what it is choosing between. A ref that does not
    resolve keeps its number (the text lists it) and simply has no
    picture -- renumbering would point every later number at the wrong
    photograph."""
    from google.genai import types

    from . import imagery
    from .gemini_utils import sniff_mime
    out = []
    for i, url in enumerate(refs, start=1):
        data = imagery.image_bytes_for_gemini(url, resolve_photo=resolve_photo,
                                              account_id=account_id)
        if data:
            out.append(f"[{i}] {caption(url, roles)}")
            out.append(types.Part.from_bytes(data=data, mime_type=sniff_mime(data)))
    return out


def plan(scene: str, refs: list, *, brain=None, gemini_client=None,
         resolve_photo: Optional[Callable] = None,
         account_id: Optional[int] = None,
         roles: Optional[dict] = None) -> Optional[dict]:
    """A scene prompt -> its timeline, or None when it has no timed windows.

    One call on `brain` (the tier the scene was written on -- "the create
    reasoning model"), shown every reference photograph under its number
    and its caption (`roles` is the shot's `ref_roles`, what each one is
    for). Any failure -- no key, a refused tier, an answer that does not
    fit the windows -- falls back to the deterministic split, and says
    which it was in `planner` so a card can tell a planned timeline from a
    guessed one. Either way the result goes through `keep` (below): what
    the planner dropped is put back and what will not fit is said in
    `warnings`. Never raises."""
    refs = list(refs or [])
    windows = parse_windows(scene)
    if not windows:
        return None
    total = _num(sum(w["seconds"] for w in windows))
    result, planner, error = None, "split", None
    try:
        from . import shootgen
        from .gemini_utils import generate_with_retry
        client = gemini_client
        if client is None:
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if key:
                from google import genai
                client = genai.Client(api_key=key)
        if client is not None:
            text = build_prompt(scene, windows, refs, seconds=total, roles=roles)
            contents = ([*_reference_contents(refs, resolve_photo, account_id, roles),
                         text] if refs else text)
            model, config, fallbacks = shootgen.brain_call(shootgen.MODEL, brain)
            answer = generate_with_retry(client, model, contents, stage="timeline",
                                         config=config, fallbacks=fallbacks,
                                         account_id=account_id)
            result = parse_response(answer, windows, refs)
            if result is not None:
                planner = brain or "fast"
            else:
                error = "the planner's answer did not fit the scene's windows"
    except Exception as e:
        error = f"planner unavailable: {e}"
    if result is None:
        if error:
            print(f"note: shot timeline fell back to a plain split: {error}",
                  file=sys.stderr)
        result = fallback(scene, windows, refs)
    warnings = keep(result, scene, windows, refs, roles=roles)
    return {"seconds": total, "planner": planner,
            "source": source_hash(scene, refs),
            "continuity": result["continuity"], "parts": result["parts"],
            "warnings": warnings,
            **({"error": error} if error else {})}


# --- the stored timeline ----------------------------------------------------

def _shot(concept: Optional[dict], shot_n=None) -> Optional[dict]:
    shots = (concept or {}).get("shots") or []
    if shot_n is None:
        return shots[0] if shots else None
    return next((s for s in shots if s.get("n") == shot_n), None)


def _save(concept_id: int, concept: dict, shots: list, *, db_path=None,
          account_id: Optional[int] = None) -> None:
    """update_concept_shots rewrites ai_json and warnings from what it is
    handed, so hand it back what the row already had."""
    preprod.update_concept_shots(
        concept_id, {"shots": shots, "duration": concept.get("duration"),
                     "ai": concept.get("ai")},
        warnings=concept.get("warnings") or [], dsn=db_path, account_id=account_id)


def _same_shot(old: dict, new: dict) -> bool:
    """Is `old` the last shot as it was stored BEFORE 2026-10-11, when the
    last window's text still ran on into the scene's sound line and
    avoid-list? Same window, same refs, and the old text is the new one
    with a tail after it. Without this the first re-plan of every scene
    saved before that day would drop its last shot's still and clip,
    though nobody touched that shot, and the next approve would buy the
    clip again."""
    if (old.get("start"), old.get("end")) != (new.get("start"), new.get("end")) \
            or list(old.get("refs") or []) != list(new.get("refs") or []):
        return False
    was, now = old.get("text") or "", new.get("text") or ""
    return bool(now) and was.startswith(now) and bool(_TAIL_AFTER.match(was[len(now):]))


def ensure(concept_id: int, shot_n=None, *, brain=None, gemini_client=None,
           resolve_photo: Optional[Callable] = None, db_path=None,
           account_id: Optional[int] = None, force: bool = False) -> Optional[dict]:
    """The scene's current timeline, planned now if it is missing or stale.

    Returns None for a scene with no timed windows (it renders as one clip)
    and never raises -- a scene that could not be split is still a scene.
    Renders already attached to a part are CARRIED OVER when the re-plan
    keeps the same window with the same sentence in the scene, so an edit
    to shot 3 does not throw away the clip of shot 1 -- keyed on the
    scene's words and not the planner's, which a re-plan rewrites anyway.
    Carried only if the part's refs are unchanged too: a still drawn
    against a face the shot no longer shows is not that shot's still.
    (One allowance, for the LAST shot of a scene stored before 2026-10-11:
    _same_shot.)"""
    try:
        concept = preprod.get_concept(concept_id, dsn=db_path, account_id=account_id)
        shot = _shot(concept, shot_n)
        if not shot:
            return None
        if not force and is_current(shot):
            return shot["timeline"]
        old = shot.get("timeline") or {}
        new = plan(shot.get("prompt") or "", shot.get("refs") or [],
                   brain=brain or old.get("brain") or _default_brain(),
                   gemini_client=gemini_client, resolve_photo=resolve_photo,
                   account_id=account_id, roles=shot.get("ref_roles") or None)
        if new is None:
            if old:
                shots = [dict(s) for s in concept["shots"]]
                target = _shot({"shots": shots}, shot.get("n"))
                target.pop("timeline", None)
                _save(concept_id, concept, shots, db_path=db_path, account_id=account_id)
            return None
        new["brain"] = brain or old.get("brain") or _default_brain()
        # a part whose words name a product or character the scene's brand
        # kit links is held to the scene's photo of it (brand_kits.part_refs,
        # docs/tasks/task-kit-products-and-screens.md Part B; unchanged for
        # no kit, or nothing named)
        try:
            from . import brand_kits
            elements = brand_kits.linked(
                brand_kits.for_concept(concept_id, db_path, account_id=account_id), db_path)
            new["parts"] = brand_kits.part_refs(new["parts"], shot.get("refs") or [], elements)
        except Exception as e:                  # a kit is an addition, never a gate
            print(f"note: kit products not held to parts: {e}", file=sys.stderr)
        before = old.get("parts") or []
        kept = {(p.get("start"), p.get("end"), p.get("text"), tuple(p.get("refs") or [])): p
                for p in before}
        for part in new["parts"]:
            prev = kept.get((part["start"], part["end"], part["text"], tuple(part["refs"])))
            if prev is None and before and part is new["parts"][-1] \
                    and _same_shot(before[-1], part):
                prev = before[-1]
            if prev:
                part["reference_image"] = prev.get("reference_image")
                part["media_url"] = prev.get("media_url")
        # Re-read before writing: planning is a model call, and the row
        # may have gained a keyframe or a ref while it ran.
        concept = preprod.get_concept(concept_id, dsn=db_path, account_id=account_id)
        shots = [dict(s) for s in concept["shots"]]
        target = _shot({"shots": shots}, shot.get("n"))
        if target is None:
            return None
        if new["source"] != source_hash(target.get("prompt") or "", target.get("refs") or []):
            return new          # edited while we planned; the next read re-plans
        target["timeline"] = new
        target["seconds"] = new["seconds"]
        _save(concept_id, concept, shots, db_path=db_path, account_id=account_id)
        return new
    except Exception as e:
        print(f"note: shot timeline not planned: {e}", file=sys.stderr)
        return None


def render_prompt(part: dict, timeline: dict) -> str:
    """What a renderer is handed for one part: the scene's memory first,
    then this shot. Composed here, in code, rather than trusted to the
    planner's wording -- continuity that depends on a model remembering to
    repeat it is continuity that drifts on the fourth shot."""
    total = len((timeline or {}).get("parts") or []) or 1
    head = (timeline or {}).get("continuity") or ""
    shot = (f"SHOT {part.get('n')} OF {total} ({part.get('start')}-{part.get('end')}s, "
            f"{part.get('seconds')}s): {part.get('prompt') or ''}").strip()
    if head:
        return f"CONTINUITY -- the same scene as every other shot, keep it identical: {head}\n\n{shot}"
    return shot


def render_target(shot: dict, part: Optional[int] = None) -> Optional[dict]:
    """The prompt, anchor frame and refs one render reads.

    `part=None` is the whole scene -- the shot's own prompt and keyframe,
    exactly what every adapter read before timelines. A part number reads
    that part: its composed prompt, ITS still as the anchor, ITS refs. None
    when the part does not exist, so an adapter can refuse cleanly rather
    than render the wrong thing.

    Both prompts go out through `for_render`, which is what makes this the
    render boundary: everything downstream of here is a video model being
    handed a frame, and the motion directive belongs to all four adapters
    rather than to whichever one remembered to add it."""
    if not shot:
        return None
    if part is None:
        return {"prompt": for_render(shot.get("prompt")),
                "reference_image": shot.get("reference_image"),
                "refs": list(shot.get("refs") or []), "seconds": shot.get("seconds"),
                "raw": {"scene": shot.get("prompt")}}
    tl = shot.get("timeline") or {}
    entry = next((p for p in tl.get("parts") or [] if p.get("n") == part), None)
    if entry is None:
        return None
    # `raw`: the pieces `prompt` was composed from, for the one reader that
    # may compose them differently for a model (src/prompts_for.py)
    return {"prompt": for_render(render_prompt(entry, tl)),
            "reference_image": entry.get("reference_image"),
            "refs": list(entry.get("refs") or []), "seconds": entry.get("seconds"),
            "raw": {"shot": entry.get("prompt") or entry.get("text"),
                    "continuity": tl.get("continuity"), "scene": shot.get("prompt")}}


def attach_part(concept_id: int, shot_n, part: int, field: str, url: str, *,
                db_path=None, account_id: Optional[int] = None) -> bool:
    """Write one part's `media_url` or `reference_image`.

    When the LAST part gets its clip, the scene's own `media_url` is set to
    shot 1's clip. That is what every existing reader means by "rendered"
    -- the Queue drops the card, the board counts it -- and it is shot 1
    ON PURPOSE rather than a stitched cut: the edit is Mike's, in Resolve
    (the L1 hold), and the parts are on the card in order for exactly that.
    A partly rendered scene stays in the Queue, so a render that stops at
    the daily cap is resumed by approving again rather than restarted."""
    if field not in ("media_url", "reference_image") or not (url or "").strip():
        raise ValueError("a part takes a media_url or a reference_image")
    concept = preprod.get_concept(concept_id, dsn=db_path, account_id=account_id)
    if concept is None:
        raise ValueError(f"no concept {concept_id}")
    shots = [dict(s) for s in concept["shots"]]
    shot = _shot({"shots": shots}, shot_n)
    if shot is None:
        raise ValueError(f"concept {concept_id} has no shot {shot_n}")
    tl = dict(shot.get("timeline") or {})
    parts = [dict(p) for p in tl.get("parts") or []]
    entry = next((p for p in parts if p.get("n") == part), None)
    if entry is None:
        raise ValueError(f"shot {shot_n} has no part {part}")
    entry[field] = url.strip()
    tl["parts"] = parts
    shot["timeline"] = tl
    if field == "media_url" and all(p.get("media_url") for p in parts):
        shot["media_url"] = parts[0]["media_url"]
    _save(concept_id, concept, shots, db_path=db_path, account_id=account_id)
    return True


def pending_parts(shot: dict) -> list:
    """The parts still without a clip, in order -- what an approve renders."""
    return [p for p in ((shot or {}).get("timeline") or {}).get("parts") or []
            if not p.get("media_url")]


def fit_seconds(axis: dict, seconds) -> int:
    """A part's window -> the length a model can actually render.

    A window is the length the SHOT is on screen; a render is what the
    model will make. Runway makes 5s or 10s and nothing between, so a 3s
    window renders at 5s and is trimmed in the edit -- rounding UP, never
    down, because a render shorter than its window is a hole in the cut
    and a longer one is a handle. The three kinds are the catalogue's
    (providers._choices / _span / _fixed), and this is the one place that
    turns a window into a legal length for each."""
    want = max(1, math.ceil(float(seconds or 0) or 1))
    kind = (axis or {}).get("kind")
    if kind == "range":
        return int(min(max(want, axis["min"]), axis["max"]))
    values = sorted(int(v) for v in (axis or {}).get("values") or [])
    if not values:
        return want
    if kind == "fixed":
        return values[0]
    return next((v for v in values if v >= want), values[-1])
