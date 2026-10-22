"""
src/orchestrator.py — the autonomous content graph over pre-production:

    planner -> ground_entities -> ground_rag
        -> gen_concept -> evaluate -> structure_prompt -> score_prompts
                ^_____________|                              |
                (corrective re-run)         keyframe -> generate_render
                                    -> qc_clip -> select_clip -> caption -> publish
                                             \\-> hold  (stop, don't post)

NO JUDGE SITS IN THE MIDDLE (2026-10-11; docs/tasks/task-higgsfield-shape.md
step 6). The prompt gate's LLM rubric scored a prompt on subject, camera,
motion, lighting and coherence and, measured against Mike's own grades,
agreed with them ~38% of the time; it was made advisory on 2026-09-07 and
is gone now. Predicting from the PROMPT whether a clip will be worth
keeping was the wrong lever: what a person does with the output is the
signal (src/outcomes.py), and the rubric's checklist lives in the writer
templates as instructions, where it costs nothing.

What `score_prompts` still does is CODE: `_structural_check` -- empty,
under fifteen words, a leftover `{token}` or TODO. A prompt that fails it
gets its bounded rework and then holds, because an unfilled placeholder
renders garbage whatever anyone thinks of the writing. Also code, and
unchanged: the `warnings` retry loop, the reference gate, the uncanny /
on-brand judge (recorded here, read at the posting decision), clip QC,
`_post_gate`, the kill switch and every credit/spend gate. The optional
concept judge (JUDGE=1) records its opinion on the card and never routes.
A camera-only concept with no prompts still holds: there is nothing to
render.

The direction is the spark the caller passes. The research scout and the
research agent that used to replace it with a crawled one were removed on
2026-10-14 (Mike's call).

The left third (planner -> gen_concept -> evaluate and its
retry edge) is the original evaluate-and-retry loop, unchanged in
behavior. The right two-thirds is the posting line, gated hard:

- generate_render and the posting APIs are DELIBERATE STUBS. The credit
  gate: real generation stays off until first-try prompt acceptance
  clears the bar, and publish never uploads anywhere. A run that
  reaches the end of the line STOPS and returns why (`held_reason`);
  nothing parks it in a queue (the hold queue went 2026-10-14, the
  per-brand channels 2026-10-13).
- The kill switch (autonomy.killed(): settings row or PHANTRA_KILL=1)
  stops every run at the end. _post_gate is the last code-enforced
  check -- clips QC'd, caption non-empty, no warnings. Code, not a
  prompt.

The evaluator combines the code-enforced `warnings` (prompts request,
code enforces) with an optional LLM-judge (JUDGE=1) scoring solo-shoot
feasibility.

The run takes photos as well as a direction. `reference_photos` is a
list of site-relative URLs -- `/refs/<sha>.jpg` uploads or asset-bank
photo URLs -- and they reach BOTH models:
as bytes the scene writer can look at, and as the shot's `refs`, which
is what the keyframe and the clip anchor on. Deliberately NOT
`picked_references`, which names RAG SOURCES: one is what the models
look at, the other is what they read.

Deps:   pip install langgraph langsmith
Env:    GEMINI_API_KEY            (required, already used by your stages)
        JUDGE=1                   (optional) turn the LLM-judge on
        GEMINI_MODEL=...          (optional) judge model; match your other stages
        PHANTRA_KILL=1           (optional) kill switch without a DB write
        LANGSMITH_TRACING=true    (optional) auto-trace the graph to LangSmith
        LANGSMITH_API_KEY=...     (optional) with the line above
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional, TypedDict

from google import genai
from langgraph.graph import END, START, StateGraph

from . import (
    accounts,
    autonomy,
    crag,
    db,
    entities,
    gemini_utils,
    preprod,
    promptgen,
    rag,
    scene_chain,
    scheduling,
    shootgen,
    spend,
    timeline,
    winners,
)
from .gemini_utils import generate_with_retry

MAX_ATTEMPTS = 3
JUDGE_MIN = 0.6
# Where a night's candidate clips land, one subdirectory per concept. A
# module-level constant rather than a path built inside generate_render,
# because a path built inside the function cannot be redirected -- and an
# output root a test cannot redirect is an output root a test eventually
# writes to for real.
GENERATED_ROOT = db.PROJECT_ROOT / "footage" / "generated"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", shootgen.MODEL)  # match the other stages




def brain_default() -> str:
    """Which model tier an unattended run writes with (2026-09-09), read
    per call.

    Defaults to `fast` ON PURPOSE, and that is the load-bearing half.
    Making unattended runs reasoning-tier is a real bill (roughly 4x the per-token price, plus
    thinking tokens billed at the output rate) and therefore a decision
    somebody makes with PHANTRA_BRAIN=reasoning, not something the
    composer's picker does to it by sharing a constant.

    An unknown value reads as the default rather than raising: this is
    an env var on a 3:30am job with nobody watching, and a typo must not
    lose the night."""
    value = (os.environ.get("PHANTRA_BRAIN") or "").strip().lower()
    return value if value in gemini_utils.BRAINS else gemini_utils.DEFAULT_BRAIN


# Two targeted rewrites per failing shot before it holds. Raised from 1
# to 2 on 2026-09-03: five held concepts (173, 177, 180, 183, 187) all
# failed the SAME judge dimension -- "too many sequential actions /
# multi-stage choreography for a single render" -- and every one of
# them used its one rework attempt without changing the verdict (180's
# reason came back byte-for-byte identical). One attempt was not the
# constraint; the REWRITE not addressing the actual failure shape was.
# The fix then was to collapse a staged prompt to one beat. That fix is
# GONE (2026-09-10): a scene may carry several timed shots now, each
# rendered as its own clip (src/timeline.py), so "too many sequential
# actions" stopped being a failure and the rework keeps the windows.
MAX_PROMPT_REWORKS = 2  # bounded rewrites of a prompt that failed the code check; then hold

# The concept judge's note, as a literal prefix rather than a structured
# record: it is read by a human on a card beside a still, and a prefix is
# also how the newest verdict replaces the previous one.
_EVAL_ADVISORY = "advisory: concept judge"


class GenState(TypedDict, total=False):
    # inputs
    goal: str
    client: Optional[str]
    spark: Optional[str]
    use_pov: bool
    seconds: int                    # the scene's total length (timeline.scene_seconds)
    brain: str                      # which model tier writes the scene
                                    # (gemini_utils.BRAINS). Set once by run();
                                    # the judges deliberately stay on the fast
                                    # tier -- they score, they do not write, and
                                    # the gates are advisory anyway.
    account_id: Optional[int]       # whose run this is. Set once by run();
                                    # every node reads it off the state rather
                                    # than taking a parameter, because
                                    # LangGraph calls a node with the state and
                                    # nothing else -- a node with an
                                    # `account_id=None` parameter would always
                                    # get None and quietly see an empty
                                    # database.
    picked_locations: list          # ids; empty/absent = all on file
    picked_characters: list
    picked_props: list
    picked_references: list         # asset-shelf source identifiers; empty/absent = no asset
    reference_photos: list          # PHOTO urls the run was handed -- /refs/<sha>.jpg
                                    # uploads, or asset-bank photo
                                    # URLs. Deliberately NOT picked_references, which
                                    # names RAG SOURCES: one is what the models look
                                    # at, the other is what they read.
                                    # grounding (craft/structuring advice still auto-grounds
                                    # -- see ground_rag)
    # grounding
    cast: str                       # formatted characters/props block
    references: str                 # CRAG-graded library block
    # the loop
    concept: dict
    concept_id: int
    critique: dict                  # {"ok": bool, "issues": [...], "score": float}
    attempts: int
    # the posting line
    run_id: str
    prompts: list                   # [{"tool", "prompt"}] for the AI shots
    prompt_scores: list             # [{prompt, score, pass, reason, dims}]
    prompt_rework_attempts: int     # bounded per-shot rewrite passes, not concept retries
    refs: list                      # the photo urls attached to the scene's shot
    ungrounded: str                 # set when the reference gate took the concept off the board
    keyframes: list                 # [{"n", "ok", "url", "error"}] -- the stills
    parked_reason: str              # what the Queue card says it is waiting on
    advisory: list                  # the concept judge's note, carried to the card
    clips: list                     # [{"tool", "prompt", "url", "ok"}]
    clip_candidates: list           # every clip qc_clip saw, before select_clip chose
    caption: str
    posted: list                    # [{"platform", "id", "url"}] once real posting exists
    autonomy: str                   # always "shadow": a run never posts
    held_reason: str                # why the run stopped where it did
    error: Optional[str]


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return genai.Client(api_key=key)


def _judge(concept: dict) -> tuple[float, list[str]]:
    """Optional LLM-judge. Never blocks: any failure returns a passing score."""
    try:
        payload = {
            "title": concept.get("title"),
            "logline": concept.get("logline"),
            "shots": [
                {"type": s.get("type"), "desc": s.get("desc"), "location": s.get("location")}
                for s in concept.get("shots", [])
            ],
        }
        prompt = (
            "You are a tough solo-filmmaker producer. Score this shoot concept for a "
            "ONE-operator, two-camera house shoot of at most 6 shots. Lower the score for "
            "shots needing a crew, impossible coverage, or vague direction. "
            'Return ONLY JSON: {"score": <0..1>, "issues": ["short issue", ...]}.\n\n'
            + json.dumps(payload)
        )
        resp = _client().models.generate_content(model=GEMINI_MODEL, contents=prompt)
        spend.record_call(stage="evaluate", model_asked=GEMINI_MODEL, response=resp)
        text = (resp.text or "").strip().strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        data = json.loads(text)
        return float(data.get("score", 1.0)), list(data.get("issues", []))
    except Exception:
        return 1.0, []


# --- nodes: the left third (the original loop) ----------------------------

def planner(state: GenState) -> GenState:
    """BUILD stub -- for now: straight to a full plan. A run always
    holds (autonomy.AUTONOMY; there are no channels since 2026-10-13).
    Also mints the run_id everything downstream logs against."""
    run_id = state.get("run_id") or uuid.uuid4().hex
    # from here every metered Gemini call carries this run's uuid and the
    # run's account (src/spend.py) -- per-night cost keys on THIS id, the
    # uuid, never on pitch_runs' integer id
    spend.bind(account_id=state.get("account_id"), run_id=run_id)
    if preprod.refs_required() and not state.get("reference_photos"):
        # MIKE'S RULE, 2026-09-08: a concept with no reference images is a
        # no-go. Measured the night before, 20 of 29 banked sparks had no
        # picture behind them and every one of them still produced a scene
        # written from words alone -- so nothing downstream ever noticed
        # that the crawl was reaching the WORDS and not the pictures.
        return {
            "autonomy": autonomy.AUTONOMY,
            "run_id": run_id,
            "error": NO_REFS_REASON,
        }
    return {
        "autonomy": autonomy.AUTONOMY,
        "run_id": run_id,
    }


NO_REFS_REASON = ("no reference images behind this spark — a scene is not "
                  "written from words alone (PHANTRA_REQUIRE_REFS=0 to allow it)")


def route_after_planner(state: GenState) -> str:
    """The one gate in front of the whole generation, and it is code, not
    taste: either there are pictures behind this direction or there are
    not. Every other gate in this graph went advisory on 2026-09-07 --
    this one is deliberately hard, because it is not predicting anything.
    """
    return "hold" if state.get("error") else "plan"


def ground_entities(state: GenState) -> GenState:
    """The chosen characters/props, formatted the way the concept
    prompt's {cast} section expects -- never "everything on file" any
    more (2026-09-03, Mike's call). Explicit picks (picked_characters/
    picked_props, or a photo in reference_photos) still win outright;
    with nobody there to pick anything on an unattended run, the spark
    text itself is name-matched against the catalogue instead of
    falling back to the whole roster -- the same rule
    scene_chain.scoped_cast_and_locations gives the Studio Create button
    and Director's brief composer, so a nightly concept only ever gets
    a face it actually has reason to use."""
    account_id = state.get("account_id")
    picked_chars = state.get("picked_characters") or []
    picked_props = state.get("picked_props") or []
    if picked_chars or picked_props:
        characters = [c for c in (entities.get_character(i, account_id=account_id)
                                  for i in picked_chars) if c]
        props = [p for p in (entities.get_prop(i, account_id=account_id)
                             for i in picked_props) if p]
        cast = shootgen.cast_for(characters, props)
    else:
        try:
            cast, _locs = scene_chain.scoped_cast_and_locations(
                state.get("spark") or "",
                state.get("reference_photos"), db_path=None,
                account_id=account_id)
        except Exception:
            cast = ""
    # Brand-scoped: a faceless brand gets no cast block at all, or the
    # {cast} socket tells it to name people it must never name.
    return {"cast": cast}


def ground_rag(state: GenState) -> GenState:
    """Two layers (narrowed again 2026-08-20 from the first
    opt-in-everything pass, once it was clear that threw out craft
    guidance along with the brand's own assets):

    - Craft/structuring advice (shootgen.AUTO_IDEATION_DOMAINS -- the
      marketing shelf: platform mechanics, edit anatomy, what earns a
      swipe) stays automatic, CRAG-graded off the spark, same as it
      always was. This isn't the brand's own material, so there's
      nothing to leak by grounding on it every run.
    - PERFORMANCE HISTORY (shootgen.PERFORMANCE_DOMAINS --
      proven_results and winning_prompts) is automatic too, since
      2026-09-02. It used to sit in the opt-in set, which made it dead
      on the only path that matters: an unattended run picks nothing,
      so nothing was ever pulled, so every nightly concept was written
      against generic craft advice while refresh_metrics ->
      promote_winners -> RAG kept filling a shelf no run read. The
      analytics loop existed end to end and never closed.
    - The brand's own STYLE assets (personal_brand voice,
      cinematography look) stay opt-in only: picked_references names
      exact source identifiers (as shown on /library or
      rag.list_sources), pulled verbatim with rag.fetch_by_sources --
      no embedding call, no similarity ranking, because the selection
      already happened. Nothing picked means nothing from these
      shelves, not even an attempt.

    Evidence automatic, taste picked. That is the line between the
    second layer and the third: what this channel published and how it
    performed has no style to impose, while which voice a run wears is
    a decision a person should still make.

    Never raises on any layer: an unreachable store, an empty spark, or
    picks that don't match anything all degrade to that layer
    contributing nothing, never a crash."""
    references = []

    query = (state.get("spark") or state.get("goal") or "").strip()
    if query:
        craft = crag.retrieve_with_crag(
            query, _client(), GEMINI_MODEL, domain=shootgen.AUTO_IDEATION_DOMAINS,
            prefer_project=accounts.slug_of(state.get("account_id")))
        if craft.get("ok") and craft.get("references"):
            print(f"Grounding in {len(craft['references'])} craft reference(s)", file=sys.stderr)
            references.extend(craft["references"])
        elif not craft.get("ok"):
            print(f"note: no craft-advice grounding: {craft.get('error', 'unavailable')}",
                  file=sys.stderr)

    if query:
        history = crag.retrieve_with_crag(query, _client(), GEMINI_MODEL,
                                          domain=shootgen.PERFORMANCE_DOMAINS)
        if history.get("ok") and history.get("references"):
            print(f"Grounding in {len(history['references'])} performance "
                  f"reference(s) -- what actually travelled", file=sys.stderr)
            references.extend(history["references"])
        elif not history.get("ok"):
            # Said out loud, because this layer failing is invisible
            # otherwise: a run grounded on nothing looks exactly like a
            # run grounded on everything, which is how the opt-in
            # version hid for weeks.
            print(f"note: no performance grounding: "
                  f"{history.get('error', 'unavailable')}", file=sys.stderr)

    picked = state.get("picked_references") or []
    if picked:
        result = rag.fetch_by_sources(picked)
        if result["ok"] and result["references"]:
            print(f"Grounding in {len(result['references'])} selected asset reference(s)",
                  file=sys.stderr)
            references.extend(result["references"])
        elif not result["ok"]:
            reason = result.get("error", "none of the selected sources were found")
            print(f"note: generating without selected assets: {reason}", file=sys.stderr)

    return {"references": rag.format_references(references)}


def gen_concept(state: GenState) -> GenState:
    # On a retry, fold the evaluator's feedback into the spark so the re-run improves.
    spark = state.get("spark")
    crit = state.get("critique")
    if crit and not crit.get("ok"):
        spark = f"{spark or ''}\nFix these issues: {'; '.join(crit.get('issues', []))}".strip()

    # human_note: standing corrections (dropped on the dev console or via
    # autonomy.add_correction) fold into the spark the same way the
    # evaluator's do, and are consumed so each note steers once.
    # Both of these STEER the generation without becoming the direction.
    # They used to be concatenated onto `spark`, which the generator then
    # stored -- so every row's `spark` column carried ~1500 characters of
    # craft notes instead of the one line it is meant to hold, and
    # the scout's novelty key hashed the notes along with the idea. Kept
    # separate now (2026-09-01): the
    # prompt sees both, the row sees the direction.
    steer_parts: list[str] = []

    notes = autonomy.pending_corrections()
    if notes:
        steer_parts.append("Notes from the filmmaker: "
                           + "; ".join(n["note"] for n in notes))
        for n in notes:
            autonomy.consume_correction(n["id"])

    # standing negative steer: patterns you've marked "didn't work" are
    # folded in so the next batch avoids repeating them (winners.avoid_guidance).
    avoid = winners.avoid_guidance()
    if avoid:
        steer_parts.append(avoid)
    steer = "\n".join(steer_parts)

    # ONE scene, ONE prompt -- the same unit the Studio has produced
    # since 2026-08-26, not the legacy multi-shot concept this node used
    # to write. That divergence stopped being cosmetic on 2026-08-29,
    # when the night's output started parking in the Queue: the Queue
    # (and pick_rate, and the scene board) key on is_scene, which is
    # len(shots) == 1, so a six-shot concept would have been generated,
    # scored, keyframed and then invisible to the surface meant to
    # approve it. `use_pov` has no meaning here -- the scene brief
    # neither offers nor names a camera -- so it stops being passed
    # rather than being passed and ignored.
    # Photos the run was handed, as bytes
    # the writer can actually look at. A scene written FROM a photograph
    # beats one told a photograph exists, which is the whole reason
    # format_cast's "(reference photos on file)" was not enough.
    handed = list(state.get("reference_photos") or [])
    image_refs = (scene_chain.as_image_refs(handed, account_id=state.get("account_id"))
                  if handed else None)

    result = shootgen.generate_scene_concept(
        spark=spark,
        steer=steer,
        gemini_client=_client(),
        db_path=None,
        references=state.get("references", ""),
        cast=state.get("cast"),
        image_refs=image_refs,
        account_id=state.get("account_id"),
        brain=state.get("brain"),
        seconds=state.get("seconds"),
    )
    # the generator returns warnings BESIDE the concept, not inside it;
    # fold them in so evaluate's code-enforced check actually sees them.
    concept = {**result["concept"], "warnings": result["warnings"]}

    # The photos this scene renders against, stored on its shot: the
    # assets it NAMED first (identity holds the anchor slot Runway reads),
    # the handed-in photos after. Never fatal -- an ungrounded
    # scene is still a scene, and attach_refs says so by returning [].
    # Scoped on the SPARK the scene was written from plus any explicit
    # pick -- the same set ground_entities offered the writer -- never on
    # the finished scene's own words (2026-09-05): reading the scene
    # back had been attaching Michael's face to crawled ideas that only
    # ever said "he".
    scope_text = state.get("spark") or ""
    for getter, ids in ((entities.get_character, state.get("picked_characters")),
                        (entities.get_prop, state.get("picked_props"))):
        for i in ids or []:
            row = getter(i, account_id=state.get("account_id"))
            if row and row.get("name"):
                scope_text += f" {row['name']}"
    refs = []
    try:
        refs = scene_chain.attach_refs(result["concept_id"], handed,
                                       idea=scope_text,
                                       db_path=None,
                                       account_id=state.get("account_id"))
        if refs:
            concept["shots"][0]["refs"] = refs
    except Exception as e:
        print(f"note: references not attached: {e}", file=sys.stderr)

    # THE REFERENCE GATE (2026-09-08, Mike's call). A scene with no
    # photographs behind it is not a candidate: it renders on its own
    # text, which is the thing this pipeline was built to stop doing.
    # So it comes off the board here, one step after the only step that
    # could have grounded it.
    #
    # Archive, never delete -- the row keeps its prompt and still
    # teaches the grade queue. And the reason is preprod.NO_REFERENCE, a
    # MACHINE reason kept out of pick_rate and the taste tally: nobody
    # judged this concept, so counting it as one Michael passed over
    # would read a grounding failure as a verdict on the writing.
    #
    # No retry edge. Regenerating cannot conjure photographs -- what the
    # writer is offered is fixed by the spark and the attached picks
    # (asset_shelf.in_scope), so a second pass produces another
    # ungrounded scene at full price.
    # Asked through preprod.refs_required(), the ONE switch (2026-09-08):
    # this gate and `planner`'s and the Queue's are the same rule at three
    # depths, and a switch that turned off only some of them would leave a
    # night holding at the far end for a reason the near end was told to
    # ignore.
    #
    # Why BOTH this and planner's, which look redundant: planner refuses a
    # DIRECTION that arrived with no photographs, before a generation is
    # paid for. This catches the scene that was written from a direction
    # that HAD photographs and still ended up attaching none -- nothing
    # the writer named resolved to a file. Neither can see the other's
    # case, and the cheap one runs first on purpose.
    ungrounded = ""
    if not refs and preprod.refs_required():
        ungrounded = preprod.NO_REFERENCE
        try:
            preprod.archive_ungrounded(result["concept_id"],
                                       account_id=state.get("account_id"))
        except Exception as e:
            # The routing above does NOT depend on this write. A row
            # that could not be archived is a row still on the board,
            # which is visible and fixable; a run that kept going
            # because the archive failed would be neither.
            print(f"note: ungrounded concept not archived: {e}", file=sys.stderr)

    return {"concept": concept, "concept_id": result["concept_id"],
            "refs": refs, "ungrounded": ungrounded,
            "attempts": state.get("attempts", 0) + 1}


def evaluate(state: GenState) -> GenState:
    """Scores the concept exactly as it always did -- the verdict is
    what the judge said, whatever the run then does: nothing routes on it
    (route_after_eval).

    A judge-only failure leaves a NOTE behind, so
    the run that carries on can still say what the judge thought when it
    parks. Written into `advisory`, never into the reason directly: the
    run has not finished yet and does not know where it will end."""
    concept = state.get("concept", {}) or {}
    issues = list(concept.get("warnings", []) or [])   # code-enforced
    score = 1.0
    if os.environ.get("JUDGE") == "1":
        score, judge_issues = _judge(concept)
        issues += judge_issues
    structural = bool(concept.get("warnings"))
    ok = (not structural) and (score >= JUDGE_MIN)
    out: GenState = {"critique": {"ok": ok, "issues": issues, "score": score}}
    if not ok and not structural:
        kept = [a for a in (state.get("advisory") or [])
                if not a.startswith(_EVAL_ADVISORY)]
        detail = "; ".join(str(i) for i in issues) or "no reason given"
        out["advisory"] = kept + [f"{_EVAL_ADVISORY} {score:.2f} < {JUDGE_MIN} — {detail}"]
    return out


def route_after_eval(state: GenState) -> str:
    """The concept gate, split by what enforced it.

    `concept["warnings"]` is CODE -- shootgen asked, validate_concept
    checked, and a shot naming a room that does not exist or a tool that
    is not in the registry is broken output, not a matter of taste. That
    still retries, and still holds when the retries run out, in BOTH
    modes.

    A low LLM-judge score is the other thing, and since 2026-09-07 it no
    longer routes: it is recorded in `critique` (and in `advisory`, which
    rides to the parked reason) and the run proceeds.
    Retrying on it bought nothing measurable -- the same rubric that
    agreed with Mike 38% of the time was deciding whether to spend
    another generation."""
    # The reference gate is HARD in both modes, and it is asked first.
    # It belongs beside `warnings` on the list of things code enforces:
    # whether a scene was handed photographs is a fact, not an opinion,
    # so no judge has a say in it. gen_concept has already taken
    # the row off the board; this is the run declining to spend a
    # keyframe and a credit on it.
    if state.get("ungrounded"):
        return "hold"
    critique = state.get("critique", {}) or {}
    if critique.get("ok"):
        return "pass"
    structural = bool((state.get("concept", {}) or {}).get("warnings"))
    if not structural:
        return "pass"               # the judge's opinion: recorded, not enforced
    if state.get("attempts", 0) < MAX_ATTEMPTS:
        return "retry"
    return "hold"                   # out of retries -> park it, don't post it


# --- nodes: the posting line ----------------------------------------------

# The still rubric lives in shootgen.STILL_RUBRIC (2026-09-02).


def _midjourney_still(shot_prompt: str) -> str:
    """The Midjourney still that anchors a Runway shot -- a motion-free
    frame prompt derived from the video prompt. It is the reference frame
    Runway builds from AND an image post in its own right. No gate:
    stills cost nothing to prompt and, per policy, need no approval.

    The rubric moved to shootgen.still_prompt (2026-09-02) so
    scene_chain can use it too -- scene_chain cannot import this module,
    the dependency runs the other way.
    """
    return shootgen.still_prompt(shot_prompt, gemini_client=_client(),
                                 model=GEMINI_MODEL)


def _technique_references(tool: str, account_id: Optional[int] = None) -> str:
    """AI-video prompt-syntax guidance for this shot's tool, CRAG-graded
    off the ai_prompting shelf -- the same never-raises degrade contract
    ground_rag keeps. Its own retrieval, separate from ground_rag's:
    ground_rag answers "what should we shoot," this answers "how do we
    phrase it for this specific tool." An unreachable store or a weak
    match just means no refinement happens, same as an ungrounded run."""
    query = (f"{tool} prompting technique for photorealistic AI video generation"
             if tool else "AI video prompting technique for photorealistic generation")
    result = crag.retrieve_with_crag(
        query, _client(), GEMINI_MODEL, domain=promptgen.REFINE_DOMAIN,
        prefer_project=accounts.slug_of(account_id))
    if result.get("ok") and result.get("references"):
        return rag.format_references(result["references"])
    return ""


def structure_prompt(state: GenState) -> GenState:
    """The AI shots' paste-ready prompts. shootgen already writes a
    first draft into the concept (validate_concept flags an AI shot
    without one); each draft is then run through promptgen.refine_prompt,
    which polishes it against real tool-specific prompting technique
    guidance (Seedance/Runway/Veo/etc. cheat codes on the ai_prompting
    RAG shelf) before it's scored. Refinement is an enhancement, never
    a gate -- a missing store, a bad client, or a rejected refinement
    all fall back to the original prompt untouched, same contract as
    ground_rag.

    Also drafts the Midjourney still that anchors each shot: the reference
    frame Runway generates from, and an image post in its own right.
    Stills need no approval, so this step is never gated.

    Every shot with a prompt is AI-eligible (the all-AI move,
    2026-08-20): source == "CAMERA" now means Michael captures reference
    material -- an acting take, a room plate -- that anchors the
    generation via the shot's reference_image, not that the shot escapes
    the pipeline. Until a reference exists the shot generates from its
    text prompt alone, same as any other; a reference is an enhancement,
    never a gate, exactly like RAG grounding. A shot with no prompt at
    all still drops out -- there is nothing to structure. When a shot
    carries a real capture, the Midjourney still is skipped: the still's
    whole job is being the anchor frame, and the capture IS one."""
    shots = [s for s in (state.get("concept", {}) or {}).get("shots", [])
             if s.get("prompt")]
    prompts = []
    for s in shots:
        tool = s.get("tool") or ""
        references = _technique_references(tool, state.get("account_id"))
        refined = promptgen.refine_prompt(s["prompt"], tool, _client(),
                                          model=GEMINI_MODEL, references=references)
        reference_image = (s.get("reference_image") or "").strip()
        # `n` is the join key the keyframe node uses to pair this prompt
        # back to its shot. It has to be stamped here, at the only place
        # that still has the shot in hand -- revise_prompts rewrites
        # entries in place (`prompts[i] = {**prompts[i], ...}`) so it
        # carries through, and without it the pairing falls back to list
        # position, which is a bug waiting for the two filters to disagree.
        entry = {"n": s.get("n", 1),
                 "tool": s.get("tool"), "prompt": refined,
                 "still": "" if reference_image else _midjourney_still(refined)}
        # carried only when attached, same as on the shot dict itself
        if reference_image:
            entry["reference_image"] = reference_image
        prompts.append(entry)
    return {"prompts": prompts}


# --- the prompt gate: nothing spends a credit until its prompt clears ------

def _structural_check(text: str) -> tuple[bool, str]:
    """Layer 1, deterministic, zero model calls -- the cheap failures:
    empty, too thin, leftover template tokens.

    NO UPPER LENGTH BOUND, deliberately (removed 2026-08-14). A ceiling
    was here (130 words, "the model will drop detail") and it was the
    wrong tool in the wrong layer: length is a quality judgment, not a
    broken-output signal, and this layer exists to catch output that is
    broken. The evidence said so too -- across the first 17 scored
    prompts (33-75 words, median 46) the ceiling never once fired, while
    six of eight judge failures were the OPPOSITE problem: missing
    camera framing, missing lens, no specified motion. Detail is what
    the gate is short of, so nothing here should push toward brevity.
    Over-stuffing, if it ever shows up, is the judge's `coherence`
    dimension to grade, not this function's to reject."""
    t = (text or "").strip()
    n = len(t.split())
    if n < 15:
        return False, "too thin — under 15 words"
    if re.search(r"\{.*?\}|\[.*?\]|TODO|TBD", t):
        return False, "leftover placeholder / template token"
    return True, ""


def score_prompts(state: GenState) -> GenState:
    """The prompt check. CODE ONLY since 2026-10-11: every extracted
    prompt gets `_structural_check` and nothing else. The LLM rubric that
    sat on top of it (subject / camera / motion / lighting / coherence,
    a bar out of 10) is gone -- see the module docstring -- and so the
    `prompt_scores` TABLE is no longer written. The state key keeps its
    name: the run's result carries it.

    An entry is {prompt, tool, still, pass, reason} and, when it failed,
    `structural: True`; there is no score and there are no dims."""
    checked = []
    for p in state.get("prompts", []):
        text = p.get("prompt", "")
        # rides along so the run's result can show the capture beside the
        # prompt it anchors; present only when the shot carries one
        ref = ({"reference_image": p["reference_image"]}
               if p.get("reference_image") else {})
        ok, why = _structural_check(text)
        checked.append({"prompt": text, "tool": p.get("tool"), "still": p.get("still"),
                        "pass": ok, "reason": why,
                        **({} if ok else {"structural": True}), **ref})
    return {"prompt_scores": checked}


def _rework_shot_prompt(original_prompt: str, verdict: dict) -> str:
    """Fix the named weakness while preserving scenes and timing. The
    weakness is the code check's own reason now (a leftover token, too
    thin); `dims` is read only for a verdict of the old shape."""
    weak = [d for d, v in (verdict.get("dims") or {}).items() if v < 2]
    reason = verdict.get("reason", "")
    weakness = f"{', '.join(weak) or 'unspecified'} -- {reason}".strip(" -")
    instruction = (
        "Rewrite the following AI video generation prompt to fix EXACTLY the "
        "weakness named below. Keep its existing layout, subject, settings, tool, "
        "grade, reference locks, camera direction, audio and negative constraints. "
        "Multiple scenes, cuts and sequential actions are allowed. Preserve scene "
        "order and transitions; never collapse the prompt to one action merely "
        "because it has multiple scenes. Keep explicit time duration markers for "
        "each scene or beat, such as (0-3s), (3-7s), (7-10s). If missing, add "
        "contiguous, non-overlapping windows from 0s to the stated total duration; "
        "if no total is supplied, choose and state one. Preserve existing timings "
        "unless the named weakness requires a timing correction. Clarify blocking "
        "and pacing within each window instead of deleting story events.\n\n"
        f"WEAKNESS TO FIX: {weakness}\n\n"
        f"ORIGINAL PROMPT:\n{original_prompt}\n\n"
        "Return ONLY the rewritten prompt text -- no preamble, no quotes, "
        "no markdown fences."
    )
    return generate_with_retry(_client(), GEMINI_MODEL, instruction,
                               stage="shot_prompt").strip()


def revise_prompts(state: GenState) -> GenState:
    """One bounded rework pass over score_prompts' output: shots that
    already passed are left untouched; shots that failed the code check
    get rewritten against its reason and checked again. Keeps `prompts` and
    the saved `concept`'s shots in sync with whatever text actually
    cleared the gate, so render (and the concept a human eventually
    reviews) reflect the reworked prompt, not the original weak one."""
    scores = state.get("prompt_scores", [])
    prompts = list(state.get("prompts", []))
    concept = dict(state.get("concept", {}))
    shots = list(concept.get("shots") or [])
    # MUST mirror structure_prompt's filter exactly -- these indices map
    # score entries back onto concept shots, and every shot with a
    # prompt is AI-eligible now, whatever its source (see structure_prompt)
    ai_shot_indices = [i for i, s in enumerate(shots) if s.get("prompt")]
    # Same scene-consistency anchor generate_concept/generate_shot_list
    # prepend up front -- reapplied here because the rework instruction
    # only *asks* the model to keep the same subject/setting/grade; a
    # rewrite is free to drop the exact bible wording, and this shot
    # still has to match every other shot in the concept when it renders.
    bible = shootgen.derive_scene_bible(concept.get("title"), concept.get("logline"),
                                        concept.get("grade"))

    revised = []
    for i, entry in enumerate(scores):
        if entry["pass"]:
            revised.append(entry)
            continue
        try:
            new_text = _rework_shot_prompt(entry["prompt"], entry)
            if bible and not new_text.startswith(bible):
                new_text = f"{bible}. {new_text}"
        except Exception as e:
            # couldn't get a rewrite -- leave the original score as-is,
            # route_after_score will hold once the attempt is spent
            revised.append(entry)
            print(f"note: prompt rework failed, keeping original: {e}", file=sys.stderr)
            continue

        ok, why = _structural_check(new_text)
        new_entry = {"prompt": new_text, "tool": entry.get("tool"),
                     "still": entry.get("still"), "pass": ok, "reason": why,
                     **({} if ok else {"structural": True}),
                     **({"reference_image": entry["reference_image"]}
                        if entry.get("reference_image") else {})}
        revised.append(new_entry)

        if i < len(prompts):
            prompts[i] = {**prompts[i], "prompt": new_entry["prompt"]}
        if i < len(ai_shot_indices):
            shots[ai_shot_indices[i]]["prompt"] = new_entry["prompt"]

    concept["shots"] = shots
    return {
        "prompt_scores": revised,
        "prompts": prompts,
        "concept": concept,
        "prompt_rework_attempts": state.get("prompt_rework_attempts", 0) + 1,
    }


def route_after_score(state: GenState) -> str:
    """Every AI shot must pass the code check before it renders -- no
    half-rendered credit burn. A failing shot is not an automatic hold:
    the check names what is wrong (a leftover `{token}`, too thin), so a
    bounded rewrite gets to fix that one thing first -- a rewritten
    prompt that fills the token is the cheapest possible fix. A shot that
    still fails afterwards holds: an unfilled placeholder renders garbage
    whatever anyone thinks of the writing.

    There is no other way to fail here since 2026-10-11. The LLM rubric
    that used to score each prompt is gone, with the advisory / hard
    switch that decided what its verdict did.

    A camera-only concept still holds, and that is not an oversight:
    with no prompt there is nothing to keyframe and nothing to render."""
    scores = state.get("prompt_scores", [])
    if not scores:
        return "hold"
    if all(x["pass"] for x in scores):
        return "generate_render"
    if state.get("prompt_rework_attempts", 0) < MAX_PROMPT_REWORKS:
        return "rework"
    return "hold"


def keyframe(state: GenState) -> GenState:
    """What the automation actually produces overnight: a scene with its
    scored prompt stored on it, a still to look at, and a place in the
    Queue.

    Before this the right-hand side of the graph was all stub -- every
    run ended "no usable clips (render is a dry-run stub)" in the hold
    queue, so the nightly loop was structurally complete and produced
    nothing anyone could judge. A keyframe costs cents and a clip costs
    real money, so the automation goes as far as the still and stops:
    approving in the Queue is what spends.

    Two things happen here, both through src/scene_chain.py so the
    request path, the canvas and this graph share one implementation:

    - the prompt structure_prompt refined is PERSISTED onto the shot.
      It was only ever in the run's state before, which meant the row
      Runway would render from still held shootgen's first draft while
      the version that passed the gate lived in a job payload.
    - a Nano keyframe is rendered from that prompt and attached as the
      shot's reference_image -- the frame the clip will anchor on.

    Gated by the prompt gate above it, deliberately: only a scene whose
    prompt cleared the judge earns an image. Never fatal -- a keyframe
    that fails (usually NANO_DAILY_CAP, 20/day shared with every
    Director render) parks the scene as text-to-video with the reason
    on its card, which is the honest version of the same run.
    """
    concept_id = state.get("concept_id")
    if not concept_id:
        return {"keyframes": []}

    shots = [s for s in (state.get("concept", {}) or {}).get("shots", [])
             if s.get("prompt")]
    # JOINED ON THE SHOT NUMBER, not on position. This list is re-derived
    # from state["concept"], which revise_prompts rewrites in place, while
    # `prompts` comes off state["prompts"] -- two lists built by two
    # filters (structure_prompt and revise_prompts) that happen to agree
    # today. A zip() would keep agreeing right up until one of them drops
    # a shot the other keeps, and then it would render shot A's prompt
    # onto shot B, silently and at full cost, with every card in the Queue
    # looking correct. `n` is what persist_prompt and plan_timeline are
    # keyed on anyway, so it is the only join that means anything.
    by_n = {}
    for refined in state.get("prompts", []):
        n = refined.get("n")
        if n is not None:
            by_n[n] = refined
    prompts = state.get("prompts", [])
    positional = len(by_n) != len(prompts)   # no usable `n` -- fall back
    done = []
    for index, shot in enumerate(shots):
        shot_n = shot.get("n", 1)
        if positional:
            if index >= len(prompts):
                continue
            refined = prompts[index]
        else:
            refined = by_n.get(shot_n)
            if refined is None:
                done.append({"n": shot_n, "ok": False,
                             "error": "no refined prompt for this shot"})
                continue
        try:
            scene_chain.persist_prompt(concept_id, shot_n,
                                       refined.get("prompt", ""),
                                       db_path=None,
                                       account_id=state.get("account_id"))
        except Exception as e:
            done.append({"n": shot_n, "ok": False, "error": f"prompt not stored: {e}"})
            continue
        # THE SHOTS (2026-09-10), planned on the prompt that will actually
        # render -- after persist_prompt, not after gen_concept, because the
        # refine and any rework rewrite it in between -- and on the run's
        # brain, the tier that wrote the scene. Planned even when the night
        # draws nothing: the split is text, and it is what the Queue card
        # and the approve read in the morning.
        scene_chain.plan_timeline(concept_id, shot_n, brain=state.get("brain"),
                                  db_path=None, account_id=state.get("account_id"))
        if os.environ.get("PHANTRA_KEYFRAME") == "0":
            done.append({"n": shot_n, "ok": False, "error": "keyframes disabled"})
            continue
        result = scene_chain.keyframe_scene(concept_id, shot_n, db_path=None,
                                            account_id=state.get("account_id"))
        done.append({"n": shot_n, "ok": bool(result.get("ok")),
                     "url": result.get("media_url"),
                     "error": result.get("error")})

    rendered = [k for k in done if k["ok"]]
    failed = [k for k in done if not k["ok"]]
    reason = ("keyframe rendered — approve in the Queue to spend on the clip"
              if rendered else
              "no keyframe: " + (failed[0].get("error") or "unknown")
              if failed else "no shot to keyframe")
    # What the concept judge thought (JUDGE=1), carried onto the card
    # rather than thrown away: a run can reach here with a low opinion on
    # record, and whoever looks at the still should see it beside it.
    notes = [str(a) for a in (state.get("advisory") or []) if a]
    if notes:
        reason = " | ".join([reason, *notes])
    try:
        scene_chain.park_scene(concept_id, reason, db_path=None,
                               account_id=state.get("account_id"))
    except Exception:
        pass       # a scene that cannot be parked is still on the board
    return {"keyframes": done, "parked_reason": reason}


def generate_render(state: GenState) -> GenState:
    """The credit gate: rendering is dry by default (PHANTRA_RENDER != 1)
    -- every clip comes back url=None, ok=False and the run parks
    downstream, so no credits are ever spent. With PHANTRA_RENDER=1 a
    shot renders through fal (src/fal.py), which has its own second gate:
    no FAL_SPEND_OK=1 means the clip comes back ok=False -- API spend is a
    deliberate, per-run approval for an unattended night.

    FAL IS THE ONLY VIDEO RENDERER SINCE 2026-09-26 (docs/tasks/
    task-fal-only.md). A shot's planned tool picks the MODEL: KLING / LTX
    / WAN / SEEDANCE / VEO are fal bound to one model each (fal.
    PLATFORM_MODELS), and the row it writes is logged under that platform.
    RUNWAY and HIGGSFIELD -- tools a shot planned before that day may still
    carry -- read as the fal default, without the row being rewritten.

    choose_provider() is the failover after a failed attempt, and it
    excludes the provider that just failed -- with one renderer that means
    a fal failure is reported, not retried on fal through another door."""
    prompts = state.get("prompts", [])
    if os.environ.get("PHANTRA_RENDER") != "1":
        return {"clips": [{**p, "url": None, "ok": False} for p in prompts]}

    from . import fal, providers
    # One binding per fal platform (fal.PLATFORM_MODELS), so a shot planned
    # for KLING renders on Kling and is logged under "kling". The retired
    # tools read as the fal default's binding (providers.platform_default).
    connectors = {name.upper(): fal.connector(name) for name in fal.PLATFORM_MODELS}
    fallback_platform = fal.model_spec(fal.DEFAULT_MODEL)["platform"]
    for retired in providers.RETIRED_PLATFORMS:
        connectors[retired.upper()] = fal.connector(fallback_platform)
    out_root = GENERATED_ROOT / f"concept-{state.get('concept_id', 'x')}"
    account_id = state.get("account_id")
    concept_id = state.get("concept_id")
    # THE TIMED SHOTS (2026-09-22). `keyframe` plans shot["timeline"] on the
    # prompt that renders; until today this node ignored it and rendered
    # the whole scene as one clip, while the Queue's approve rendered the
    # same scene shot by shot -- two doors, two clips, for one row. Read
    # from the database, not state["concept"]: the plan is written after
    # gen_concept and the state's copy predates it.
    stored = {}
    if concept_id:
        try:
            row = preprod.get_concept(concept_id, account_id=account_id)
            stored = {s.get("n", 1): s for s in (row or {}).get("shots") or []}
        except Exception:                                   # noqa: BLE001
            stored = {}
    clips = []
    for index, p in enumerate(prompts, start=1):
        tool_name = (p.get("tool") or "").upper()
        connector = connectors.get(tool_name)
        shot = stored.get(p.get("n"))
        if (connector is not None and shot is not None
                and timeline.is_current(shot)
                and (shot.get("timeline") or {}).get("parts")):
            clips.append(_render_timed(p, shot, connector, tool_name,
                                       concept_id=concept_id, account_id=account_id))
            continue
        tried = {tool_name.lower()} if tool_name else set()
        # A connector may BE a provider under another name: the four fal
        # platforms are all provider "fal". Excluding the tool name alone
        # would let the failover "retry" on the same vendor that just
        # failed, through a different door.
        if connector is not None:
            tried.add(getattr(connector, "PROVIDER", tool_name.lower()))
        result = None
        if connector is not None:
            # account_id, or the clip is billed to nobody: the row lands
            # with account_id=NULL and its cap counts against the unowned
            # pool instead of this account's.
            result = connector.generate_candidates(
                p["prompt"], out_root / f"shot{index}", n=1, db_path=None,
                account_id=account_id)
        if result and result["ok"] and result["candidates"]:
            clips.append({**p, "url": result["candidates"][0]["path"], "ok": True})
            continue
        fallback = providers.choose_provider(account_id, exclude=tuple(tried))
        if fallback is not None:
            fb_result = providers.VIDEO_PROVIDERS[fallback].generate_candidates(
                p["prompt"], out_root / f"shot{index}", n=1, db_path=None,
                account_id=account_id)
            if fb_result["ok"] and fb_result["candidates"]:
                clips.append({**p, "url": fb_result["candidates"][0]["path"],
                              "ok": True, "tool": fallback.upper(),
                              "failover_from": tool_name or None})
                continue
        error = (result.get("error") if result
                 else f"no adapter wired for {p.get('tool')}")
        clips.append({**p, "url": None, "ok": False, "error": error})
    return {"clips": clips}


def _render_timed(p: dict, shot: dict, connector, tool_name: str, *,
                  concept_id, account_id) -> dict:
    """One scene's timed shots, rendered ONE AT A TIME through the SAME
    per-shot entry point the Queue's approve uses (`generate_for_shot(...,
    part=n)`, app/api.py `_render_timeline`), so every wall is per clip
    exactly as it is there: the spend approval inside generate_video
    (`*_SPEND_OK` for an unattended run), the daily cap before each call,
    a generations row per attempt, the hold and its release. Each part's
    length is its window fitted UP to the model (timeline.fit_seconds);
    its prompt is the scene's continuity followed by that shot; its
    anchor is its own still. The clip lands on the part (attach_part), and
    when the LAST part lands the scene's media_url is shot 1's clip -- the
    marker every reader means by "rendered".

    ONE clip entry comes back for the scene, the shape the rest of the
    graph reads (qc_clip, select_clip, _post_gate): `url` is shot 1's
    file, `ok` only when every part rendered, `parts` the per-shot record.
    Parts that already have a clip are skipped and the loop stops at the
    first failure -- the Queue's rule, so a night that hits the cap on
    shot 3 leaves a scene the morning's approve resumes rather than
    re-buys. No provider failover for a timed scene: shots 1-2 on one
    vendor and 3 on another is not a scene, and the Queue can still be
    asked for the rest."""
    from . import providers

    tl = shot.get("timeline") or {}
    parts = list(tl.get("parts") or [])
    axis = None
    try:
        default = providers.platform_default(tool_name.lower())
        if default:
            axis = providers.model_options(*default).get("duration")
    except Exception:                                       # noqa: BLE001
        axis = None                       # fit_seconds falls back to the window
    shot_n = shot.get("n", 1)
    record = []
    error = None
    for part in parts:
        if part.get("media_url"):
            record.append({"n": part["n"], "ok": True, "url": None,
                           "media_url": part["media_url"], "skipped": True})
            continue
        seconds = timeline.fit_seconds(axis, part.get("seconds"))
        try:
            result = connector.generate_for_shot(
                concept_id, shot_n, db_path=None, part=part["n"],
                account_id=account_id, duration=seconds) or {}
        except Exception as e:                              # noqa: BLE001
            result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        entry = {"n": part["n"], "ok": bool(result.get("ok")),
                 "url": result.get("path"), "media_url": result.get("media_url"),
                 "seconds": seconds, "error": result.get("error")}
        record.append(entry)
        if not entry["ok"]:
            done = sum(1 for r in record if r["ok"])
            error = (f"shot {part['n']} of {len(parts)} failed: "
                     f"{entry['error'] or 'render failed'} -- {done} of {len(parts)} "
                     f"rendered; approve in the Queue to render the rest")
            break
    ok = error is None and bool(record) and all(r["ok"] for r in record)
    first = record[0] if record else {}
    return {**p, "ok": ok, "url": first.get("url") if ok else None,
            "media_url": first.get("media_url") if ok else None,
            "parts": record, "timed": True,
            **({"error": error} if error else {})}


def qc_clip(state: GenState) -> GenState:
    """A clip may post only if the file is really there and really a
    video: exists, non-trivial size, and (when ffprobe is on the box) a
    positive duration. Code, not a prompt."""
    clips = [dict(c) for c in state.get("clips", [])]
    for clip in clips:
        clip["ok"] = _clip_passes_qc(clip.get("url"))
    return {"clips": clips}


def _clip_passes_qc(url) -> bool:
    if not url:
        return False
    path = Path(url)
    if not path.is_file() or path.stat().st_size < 1024:
        return False
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            return float((out.stdout or "0").strip() or 0) > 0.5
        except Exception:
            return False
    return True


def route_after_qc(state: GenState) -> str:
    clips = state.get("clips", [])
    return "select_clip" if clips and any(c.get("ok") for c in clips) else "hold"


# The seam for a video-level judge, and the whole point of the inversion
# (2026-09-07). The prompt gate was asking a text model to predict, from
# the prompt, whether the render would be worth posting -- 38% agreement
# with Mike's own verdict, and no rubric dimension separating it. The
# thing that CAN answer that question is a model looking at the finished
# clip, which does not exist here yet and costs real money when it does.
#
# So: `select_clip` picks with code today, and this hook is where that
# model plugs in. Set `orchestrator.JUDGE = fn` and it is called with the
# candidate list (each a clip dict as generate_render/qc_clip left it,
# `ok` already decided) and must return ONE of those dicts, or None to
# fall back to the heuristic. It is wrapped: a judge that raises, or
# answers with something that isn't one of the candidates, loses its say
# and the code choice stands -- the same never-raises contract every
# other model seam in this pipeline keeps. Deliberately a module global
# rather than an env var: what would flip it is a real implementation
# landing, not a night's configuration.
JUDGE = None


def _clip_duration(url) -> float:
    """Seconds, 0.0 for anything unreadable. Never raises -- an
    unreadable clip is one candidate scored 0, not a failed run.

    Inlined here on 2026-09-09. It used to call framebank.duration,
    which was the same ffprobe invocation living in the frame-bank
    module; that module went with the operator-footage lane, and this
    is now the only place the pipeline asks how long a clip is."""
    if not url:
        return 0.0
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(Path(url))],
            capture_output=True, text=True, timeout=60)
        return float((out.stdout or "0").strip() or 0)
    except Exception:
        return 0.0


def _clip_size(url) -> int:
    try:
        return Path(url).stat().st_size if url else 0
    except OSError:
        return 0


def _clip_rank(clip: dict) -> tuple:
    """The code-only heuristic, in the order the reasons are actually
    trustworthy: QC first (a file that isn't a video can never be the
    pick), then the LONGEST clip, then the largest file.

    Duration over size deliberately. Both are proxies -- neither knows
    whether the clip is any good -- but a render that came back short is
    usually a generation that gave up early, while a big file is often
    just a noisier one. Bytes only break the tie."""
    return (1 if clip.get("ok") else 0,
            _clip_duration(clip.get("url")),
            _clip_size(clip.get("url")))


def select_clip(state: GenState) -> GenState:
    """Choose between candidate renders AFTER the render, which is where
    the inversion actually lands: selecting from finished clips is the
    thing the prompt gate was a bad proxy for.

    A no-op on one clip, which is every run today -- generate_render asks
    each connector for n=1 -- so this node costs nothing until several
    candidates exist. Every candidate is kept in `clip_candidates`
    whether it won or not: the losers are the
    negative signal a video judge would eventually be trained or graded
    against, and this pipeline's standing rule is that the thing you
    passed over is the only evidence you passed over it."""
    clips = [dict(c) for c in state.get("clips", []) or []]
    if len(clips) <= 1:
        return {"clip_candidates": clips}

    best = max(clips, key=_clip_rank)
    if JUDGE is not None:
        try:
            picked = JUDGE(clips)
        except Exception as e:                       # never fatal, same as every seam
            print(f"note: clip judge failed, keeping the code pick: {e}", file=sys.stderr)
            picked = None
        if any(picked is c for c in clips):
            best = picked
        elif picked is not None:
            print("note: clip judge returned something that is not one of the "
                  "candidates — keeping the code pick", file=sys.stderr)
    return {"clips": [best], "clip_candidates": clips}


def caption(state: GenState) -> GenState:
    """Grounded caption via scheduling.build_caption, degrading to the
    concept's own title+hook -- a publish can't be blocked by the
    caption model being down."""
    concept = state.get("concept", {}) or {}
    fallback = " — ".join(x for x in (concept.get("title"), concept.get("hook")) if x)
    return {"caption": scheduling.build_caption(fallback, db_path=None)}


def _post_gate(state: GenState) -> tuple[bool, str]:
    """The last code-enforced check before any upload. Code, not a
    prompt -- the same line validate_concept holds."""
    clips = state.get("clips", [])
    if not clips or not all(c.get("ok") for c in clips):
        return False, "clip QC failed"
    if not (state.get("caption") or "").strip():
        return False, "caption is empty"
    if (state.get("concept", {}) or {}).get("warnings"):
        return False, "concept carries warnings"
    return True, ""


def _park(state: GenState, reason: str) -> GenState:
    """The end of every run: say why it stopped. Nothing is written --
    the hold queue that used to keep this went on 2026-10-14."""
    return {"held_reason": reason}


def publish(state: GenState) -> GenState:
    """The end of a run that cleared every check: it STOPS. Nothing here
    posts and nothing can promote a run to post (2026-10-13: the
    per-brand channels and their autonomy levels are gone). The reason
    says whether the run would have been postable, so the result still
    tells a clean run from one a check stopped."""
    if autonomy.killed():
        return _park(state, "kill switch is on")

    ok, why = _post_gate(state)
    if not ok:
        return _park(state, f"failed post-gate: {why}")
    return _park(state, "held for review")


def hold(state: GenState) -> GenState:
    """A run that failed a gate stops with its reason instead of posting."""
    failed_scores = [x for x in state.get("prompt_scores", []) if not x.get("pass")]
    if state.get("error"):
        reason = state["error"]
    elif state.get("ungrounded"):
        # Ahead of every judge branch: this run stopped before any of
        # them ran, and "prompt gate" on a scene that was never scored
        # would send the morning review looking at the wrong thing.
        reason = ("reference gate: no photos attached — archived off the board. "
                  "Bank references for this spark and run it again.")
    elif state.get("parked_reason"):
        # THE RUN GOT AS FAR AS IT CAN. The scene is in the Queue with
        # (usually) a still, waiting on a human, and `parked_reason`
        # already carries the concept judge's note keyframe appended to it.
        # Checked before the judge branch, not after: a low opinion and a
        # drawn still can be the same run, and "eval stop" would describe
        # the opinion instead of what the run actually produced.
        reason = state["parked_reason"]
    elif not (state.get("critique", {}) or {}).get("ok") and \
            (state.get("critique", {}) or {}).get("issues"):
        reason = "eval stop: " + "; ".join(
            str(i) for i in state["critique"]["issues"])
    elif failed_scores:
        # the code check's own reason, so the hold says what is broken
        reason = "prompt check: " + "; ".join(
            str(x.get("reason") or "failed") for x in failed_scores)
    elif not state.get("prompts"):
        reason = "no AI shots to render (camera-only concept)"
    elif not state.get("clips"):
        reason = "held before render"
    else:
        reason = "no usable clips (render is a dry-run stub)"
    return _park(state, reason)


# --- graph ----------------------------------------------------------------

def _build(checkpointer=None):
    g = StateGraph(GenState)
    for name, fn in [
        ("planner", planner),
        ("ground_entities", ground_entities), ("ground_rag", ground_rag),
        ("gen_concept", gen_concept), ("evaluate", evaluate),
        ("structure_prompt", structure_prompt), ("score_prompts", score_prompts),
        ("revise_prompts", revise_prompts),
        ("keyframe", keyframe), ("generate_render", generate_render),
        ("qc_clip", qc_clip), ("select_clip", select_clip),
        ("caption", caption), ("publish", publish),
        ("hold", hold),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "planner")
    # No ensure_locations gate (removed 2026-08-31, Mike's call). It
    # errored a run to `hold` when the locations table was empty --
    # gating the night on described rooms that its own generator never
    # reads: build_scene_brief_prompt's entire placeholder set is
    # {brand} {cast} {example} {references} {spark}, with no
    # {locations} in it. Since 2026-08-20 every shot is AI-generated,
    # so a room is named material the scene MAY use, exactly like cast
    # -- and an empty table means "nothing filed under places yet", not
    # a reason to refuse to think.
    g.add_conditional_edges("planner", route_after_planner, {
        "plan": "ground_entities",
        "hold": "hold",
    })
    g.add_edge("ground_entities", "ground_rag")
    g.add_edge("ground_rag", "gen_concept")
    g.add_edge("gen_concept", "evaluate")
    g.add_conditional_edges("evaluate", route_after_eval, {
        "pass": "structure_prompt",
        "retry": "gen_concept",
        "hold": "hold",
    })
    g.add_edge("structure_prompt", "score_prompts")
    # revise_prompts re-scores only the shots it rewrote (leaving shots that
    # already passed untouched), so it routes back through the SAME judge --
    # never back through score_prompts, which would re-bill every already-
    # passing shot's judge call for nothing.
    # the gate's pass branch goes to `keyframe` first: the still is what
    # the morning approval actually looks at, and it is the last step
    # that does not spend real money
    g.add_conditional_edges("score_prompts", route_after_score, {
        "generate_render": "keyframe",
        "rework": "revise_prompts",
        "hold": "hold",
    })
    g.add_conditional_edges("revise_prompts", route_after_score, {
        "generate_render": "keyframe",
        "rework": "revise_prompts",  # the second bounded pass (MAX_PROMPT_REWORKS == 2),
                                      # and whatever raising that constant later allows
        "hold": "hold",
    })
    g.add_edge("keyframe", "generate_render")
    g.add_edge("generate_render", "qc_clip")
    # select_clip sits between QC and caption, not inside either: QC
    # answers "is this a video at all" (code, per clip) and selection
    # answers "which of these is the one" (a judgment, across clips).
    # Collapsing them would put the future video judge behind a function
    # whose contract is that it never guesses.
    g.add_conditional_edges("qc_clip", route_after_qc, {
        "select_clip": "select_clip", "hold": "hold",
    })
    g.add_edge("select_clip", "caption")
    g.add_edge("caption", "publish")
    g.add_edge("publish", END)
    g.add_edge("hold", END)
    return g.compile(checkpointer=checkpointer)


# The plain graph: no checkpointer, no database touched at import. This is
# what langgraph.json exposes to LangGraph Studio, and the fallback for
# every caller that cannot reach Postgres.
GRAPH = _build()

CHECKPOINT_ENV = "PHANTRA_CHECKPOINT"
_CHECKPOINTED = None   # None = not tried yet, False = tried and cannot


def checkpointing_on() -> bool:
    """On unless switched off. The cost is a few writes per node; the
    thing it buys is that a night killed at run seven of ten does not
    start again from zero."""
    raw = (os.environ.get(CHECKPOINT_ENV) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def checkpointed_graph():
    """The graph with a PostgresSaver behind it, or None.

    Built lazily and cached, never at import: `GRAPH = _build()` runs on
    every `import src.orchestrator` -- the MCP server, the CLI, the web
    app, the test suite -- and none of those should open a database
    connection just by being imported.

    FAILS SOFT, deliberately. No database, no checkpoint tables, no
    permission: say so once on stderr and hand back None so `run` uses
    the plain graph. A run that cannot be resumed is worse than one that
    can; a run that refuses to start is worse than both.
    """
    global _CHECKPOINTED
    if _CHECKPOINTED is not None:
        return _CHECKPOINTED or None
    if not checkpointing_on():
        _CHECKPOINTED = False
        return None
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        # The saver's own connection, autocommit as it requires, and NOT
        # from db.connection_pool: that pool is the web server's, sized
        # for request handlers, and a checkpointer holding one of its
        # connections for the length of a graph run would starve it.
        conn = psycopg.connect(db.resolve_dsn(None), autocommit=True,
                               connect_timeout=10)
        saver = PostgresSaver(conn)
        saver.setup()
        _CHECKPOINTED = _build(checkpointer=saver)
    except Exception as e:
        print(f"note: running without a checkpointer ({e}) -- an interrupted "
              f"run will not be resumable", file=sys.stderr)
        _CHECKPOINTED = False
        return None
    return _CHECKPOINTED


def run(goal: str, *, spark: Optional[str] = None,
        client: Optional[str] = None, use_pov: bool = False,
        picked_locations=None,
        picked_characters=None, picked_props=None, picked_references=None,
        reference_photos=None,
        account_id: Optional[int] = None, brain: Optional[str] = None,
        seconds: Optional[int] = None) -> dict:
    """
    `seconds` is the scene's total length; None reads PHANTRA_SCENE_SECONDS
    (timeline.scene_seconds), which is what the night runs on.

    There is no `brand` or `channel` to pass (2026-10-13): one label is
    written to the leftover columns and a run always holds.

    The direction is `spark` (or `goal`); nothing replaces it.
    """
    autonomy.init()
    winners.init()
    # An unattended run has no session, so it acts as the bootstrap
    # account rather than as nobody. "Nobody" is not neutral here: after
    # the tenancy backfill every row has an owner, so a run with
    # account_id=None reads an empty database, writes rows no one can
    # see, and reports a night's work that isn't there.
    if account_id is None:
        account_id = accounts.resolve_account()
    # The run's uuid is minted HERE and bound with the account before the
    # graph starts, because LangGraph executes each node in a copy of the
    # calling context: a spend.bind() inside a node reaches nothing after
    # it (measured 2026-09-04 -- a night's six metered calls landed with
    # no run id). Bound in the parent, every node inherits it; unbound
    # after, so nothing leaks into whatever this thread does next.
    run_id = uuid.uuid4().hex
    token = spend.bind(account_id=account_id, run_id=run_id)
    # The run's own id IS the checkpoint thread. One thread per run, so a
    # resume names the run it is resuming and nothing else, and the
    # checkpoint rows line up with the metered calls (spend.bind above)
    # that already carry it. Harmless on the plain graph, which ignores it.
    graph = checkpointed_graph() or GRAPH
    config = {"configurable": {"thread_id": run_id}}
    try:
        return graph.invoke({
            "run_id": run_id,
            "account_id": account_id,
        "goal": goal, "spark": spark or goal,
        "client": client, "use_pov": use_pov,
        "brain": brain_default() if brain is None else brain,
        "seconds": timeline.scene_seconds(seconds),
        "picked_locations": picked_locations or [],
        "picked_characters": picked_characters or [],
        "picked_props": picked_props or [],
        "picked_references": picked_references or [],
        "reference_photos": reference_photos or [],
        "attempts": 0,
        }, config)
    finally:
        spend.unbind(token)


def resume(run_id: str) -> dict:
    """Carry on a run that was interrupted, from its last finished node.

    What this is for: a run dies with whatever kills its process -- a
    machine that sleeps, a deploy, a kill. Before checkpointing, a run's
    paid keyframe and the concept row it had already written were simply
    orphaned: a row on the board with no hold explaining it, and nothing
    that could pick the run back up.

    `invoke(None, ...)` is LangGraph's resume: no new input, start from
    the last checkpoint on this thread. The account is read back OUT of
    that checkpoint rather than passed in, because the spend has to be
    attributed to whoever the run belonged to -- not to whoever is doing
    the resuming.
    """
    graph = checkpointed_graph()
    if graph is None:
        raise RuntimeError(
            f"cannot resume {run_id}: no checkpointer (see {CHECKPOINT_ENV} "
            f"and DATABASE_URL). Nothing was saved to resume from.")
    config = {"configurable": {"thread_id": run_id}}
    saved = graph.get_state(config)
    if not saved or not saved.values:
        raise RuntimeError(f"no checkpoint for run {run_id}")
    if not saved.next:
        raise RuntimeError(f"run {run_id} already finished -- nothing to resume")
    account_id = saved.values.get("account_id")
    token = spend.bind(account_id=account_id, run_id=run_id)
    try:
        return graph.invoke(None, config)
    finally:
        spend.unbind(token)
