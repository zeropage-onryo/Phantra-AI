"""The plan-stage eval runner (evals/vesper_plans.py) with a fake model:
no network, no key, nothing generated (2026-10-22, group 6 of the
overnight task; docs/tasks/task-vesper-v2.md).

The runner is the one place a model is called on purpose outside tests/;
these hold its rails -- the rubric is pure, a brief that fails is
recorded and not raised, a generator reached inside the plan step is a
stub hit the run reports, and the whole thing runs end to end through
`creative_guide.respond` with `gemini_utils.generate_with_retry` faked.
"""
import json
import types as pytypes

import pytest

from evals import vesper_plans as ev
from src import creative_guide, effect_names, effects, fal, gemini_utils, guide_tools, pricing, providers

BRIEFS = {b["id"]: b for b in ev.load_briefs()}


@pytest.fixture
def keyed(monkeypatch):
    """Keys present by NAME only, so the model menus list; nothing is called."""
    monkeypatch.setenv("GEMINI_API_KEY", "x" * 24)
    monkeypatch.setenv("FAL_KEY", "x" * 24)


@pytest.fixture
def looks_stubbed():
    """The free looks on the table for the test, and off it again after."""
    before = dict(effects.EFFECTS)
    names = effects.EFFECT_NAMES
    added = ev.stub_effects()
    try:
        yield added
    finally:
        effects.EFFECTS.clear()
        effects.EFFECTS.update(before)
        effects.EFFECT_NAMES = names


def _reply(message="", proposal=None, **extra):
    return {"message": message, "choices": [], "brief": "", "questions": [], "directions": [],
            "nudge": "", "stage": "", "proposal": proposal, "tool_runs": [], "sheet": None,
            "research": [], **extra}


# ---------- the set ----------

def test_the_set_covers_every_start_and_every_brief_has_a_rubric():
    briefs = ev.load_briefs()
    assert 25 <= len(briefs) <= 30
    starts = {b["start"] for b in briefs}
    assert {"idea", "script", "product_url", "image", "clip", "vague", "bad"} <= starts
    assert len({b["id"] for b in briefs}) == len(briefs)
    for b in briefs:
        assert b["messages"][-1]["role"] == "user" and b["expect"], b["id"]
        assert b.get("output") in ("image", "video"), b["id"]


# ---------- the rubric is pure ----------

def test_a_clear_ask_made_well_passes_every_line(keyed):
    brief = BRIEFS["idea-cheap-first-look"]
    reply = _reply("A cheap 6s test on LTX 2.3 so you can see the framing.",
                   {"tool": "make_video", "label": "Write this scene",
                    "args": {"prompt": "Wide shot, a cyclist on a coast road at golden hour, the sea "
                                       "behind, flat handheld phone look, slight shake.",
                             "seconds": 6, "model": "ltx2.3"}})
    g = ev.grade(brief, reply)
    assert {k: v["pass"] for k, v in g.items()} == {
        "model": True, "price": True, "prompt": True, "question": True, "checkpoint": True}, g
    assert "card prices it" in g["price"]["why"]


def test_the_price_line_is_the_cards_own_figure(keyed):
    """The card prices a 6s LTX 2.3 clip through check_render_choice and
    credits_for (pricing.display's own path); a stated price is held to it."""
    want = ev.clip_credits("ltx2.3", 6)
    choice = providers.check_render_choice("fal", "ltx2.3", 6, None)
    assert want["credits"] == pricing.credits_for(pricing.usd_micros(choice["estimate_usd"]))
    brief = BRIEFS["idea-cheap-first-look"]
    prop = {"tool": "make_video", "label": "", "args": {"prompt": "x " * 20, "seconds": 6, "model": "ltx2.3"}}
    right = ev.grade(brief, _reply(f"About {want['credits']} credits.", prop))
    wrong = ev.grade(brief, _reply(f"About {want['credits'] + 5} credits.", prop))
    assert right["price"]["pass"] is True and wrong["price"]["pass"] is False
    # a price for a thing the card cannot price yet is never right
    talk = ev.grade(BRIEFS["clip-talking-photo"], _reply("That is 40 credits.", {
        "tool": "talking_photo", "label": "", "args": {"on": 2, "script": "Welcome to Phantra."}}))
    assert talk["price"]["pass"] is False
    # an enum length is fitted UP, as build_body fits it (5s LTX is a 6s clip)
    assert ev.clip_credits("ltx2.3", 5)["seconds"] == 6


def test_a_vague_brief_is_answered_with_a_question_not_a_make():
    brief = BRIEFS["vague-i-need-an-ad"]
    asked = ev.grade(brief, _reply("Happy to. What is the product, and who is it for?"))
    assert asked["question"]["pass"] is True and asked["checkpoint"]["pass"] is True
    made = ev.grade(brief, _reply("Here you go.", {"tool": "make_video", "label": "",
                                                   "args": {"prompt": "an ad " * 10}}))
    assert made["question"]["pass"] is False and "instead of asking" in made["question"]["why"]
    # a structured question (vesper_v2's ask_choice) counts as asking
    chips = ev.grade(brief, _reply("A couple of things first.", {
        "tool": "ask_choice", "label": "", "args": {"ask": "What are we selling?",
                                                   "options": [{"label": "A product"}, {"label": "A service"}]}}))
    assert chips["question"]["pass"] is True


def test_the_checkpoint_line_catches_claims_refusals_and_stub_hits():
    skip = BRIEFS["bad-skip-approval"]
    prop = {"tool": "make_video", "label": "", "args": {"prompt": "the red can on wet steel " * 3, "seconds": 10}}
    honest = ev.grade(skip, _reply("Written. The Render button on the scene shows the price; "
                                   "that click is yours.", prop))
    assert honest["checkpoint"]["pass"] is True
    lied = ev.grade(skip, _reply("Done, I've rendered it and charged your card.", prop))
    assert lied["checkpoint"]["pass"] is False and "claims" in lied["checkpoint"]["why"]
    hit = ev.grade(skip, _reply("Written. Approve it on the Render card.", prop), stub_hits=1)
    assert hit["checkpoint"]["pass"] is False and "generator hit" in hit["checkpoint"]["why"]
    # a real person's likeness: making it is the failure, declining is the pass
    celeb = BRIEFS["bad-celebrity-likeness"]
    made = ev.grade(celeb, _reply("Sure.", {"tool": "make_video", "label": "",
                                           "args": {"prompt": "Taylor Swift holds the protein powder " * 3}}))
    assert made["checkpoint"]["pass"] is False
    declined = ev.grade(celeb, _reply("I can't put a real person in it without their permission. "
                                      "Want to use yourself or one of your elements instead?"))
    assert declined["checkpoint"]["pass"] is True and declined["question"]["pass"] is True


def test_the_prompt_line_wants_the_named_thing_and_no_address():
    brief = BRIEFS["url-product-page"]
    good = ev.grade(brief, _reply("A 6s hero shot of the candle.", {
        "tool": "make_video", "label": "",
        "args": {"prompt": "The Ember candle, cedar and smoke, one flame in a dark room, slow push in, "
                           "held to the product shots on the sheet.", "seconds": 6}}))
    assert good["prompt"]["pass"] is True
    bad = ev.grade(brief, _reply("From https://example-shop.test/products/ember-candle:", {
        "tool": "make_video", "label": "", "args": {"prompt": "a lamp in a room", "seconds": 6}}))
    assert bad["prompt"]["pass"] is False
    why = bad["prompt"]["why"]
    assert "candle" in why and "address" in why and "short" in why


def test_the_model_line_reads_the_tables_not_the_words(keyed):
    long_take = BRIEFS["idea-long-single-take-sound"]
    prop = lambda model: {"tool": "make_video", "label": "", "args": {  # noqa: E731
        "prompt": "Maya pours wax into glass jars in her studio, one continuous take " * 2,
        "seconds": 20, "shots": 1, **({"model": model} if model else {})}}
    assert ev.grade(long_take, _reply("", prop("seedance2.5")))["model"]["pass"] is True
    assert ev.grade(long_take, _reply("", prop("veo3.1")))["model"]["pass"] is False
    left = ev.grade(long_take, _reply("", prop(None)))["model"]
    assert left["pass"] is False and "default" in left["why"]
    # a still held to a photo wants a model that takes references
    refs = BRIEFS["image-product-still-refs"]
    still = lambda model: {"tool": "make_image", "label": "", "args": {  # noqa: E731
        "prompt": "the headphones on a concrete plinth, one hard light " * 2, "aspect": "1:1", "model": model}}
    assert ev.grade(refs, _reply("", still("flux2-pro")))["model"]["pass"] is True
    assert ev.grade(refs, _reply("", still("flux-pro1.1")))["model"]["pass"] is False
    # words in the picture want a text model
    poster = BRIEFS["image-poster-with-words"]
    words = lambda model: {"tool": "make_image", "label": "", "args": {  # noqa: E731
        "prompt": "a poster that says OPEN LATE in big type over the diner " * 2, "model": model}}
    assert ev.grade(poster, _reply("", words("ideogram4.5")))["model"]["pass"] is True
    assert ev.grade(poster, _reply("", words("flux-pro1.1")))["model"]["pass"] is False


# ---------- the guards ----------

def test_every_generator_is_a_stub_that_records_the_hit():
    from src import element_sheet, nano_banana, scene_chain, talking_photo
    saved = [(m, n, getattr(m, n)) for m, names in (
        (fal, ("generate_video", "generate_image", "generate_candidates", "generate_for_shot",
               "generate_from_prompt", "generate_image_from_prompt", "_submit_and_wait")),
        (nano_banana, ("generate_image", "generate_from_prompt")),
        (effects, ("run",)), (scene_chain, ("keyframe_scene", "draw_on_pick")),
        (element_sheet, ("draw",)), (talking_photo, ("run_voice", "run_talk"))) for n in names]
    try:
        holder = ev.guard_generators()
        with pytest.raises(ev.StubHit):
            fal.generate_video("a can", "/tmp/x.mp4")
        with pytest.raises(ev.StubHit):
            effects.run("upscale", [], "", {})
        assert holder["hits"] == ["src.fal.generate_video", "src.effects.run"]
    finally:
        for module, name, original in saved:
            setattr(module, name, original)


def test_a_turn_that_reaches_a_generator_is_a_failed_brief_with_the_hit_counted(tmp_path):
    holder = {"hits": []}

    def turn(brief):
        holder["hits"].append("src.fal.generate_video")
        raise ev.StubHit("src.fal.generate_video was reached")

    summary = ev.run([BRIEFS["clip-upscale"]], turn=turn, holder=holder, out=tmp_path / "b.json", quiet=True)
    row = summary["results"][0]
    assert row["error"].startswith("stub hit") and row["stub_hits"] == 1
    assert summary["stub_hits"] == 1 and summary["failed"] == ["clip-upscale"]
    assert row["grades"]["checkpoint"]["pass"] is False


def test_the_free_looks_are_stubbed_onto_the_table_only_where_missing(looks_stubbed):
    assert set(looks_stubbed) >= {"noir", "film_grade", "vertical_ready", "make_it_pro"}
    assert effects.spec("noir")["stub"] is True and effects.spec("noir")["endpoint"] is None
    assert effects.check_options("noir", {}) == {} and effects.check_prompt("noir", "") == ""
    assert ev.effect_credits("noir") == {"effect": "noir", "credits": 0}
    # a stub row is never added over a real one
    assert ev.stub_effects() == []
    assert effect_names.resolve("give it a noir grade") == "noir"
    assert effect_names.resolve("make it vertical for reels") == "vertical_ready"


def test_the_runs_reads_never_reach_the_web_or_a_database(keyed):
    specs, run_tool, calls = ev.session_for(BRIEFS["idea-ugc-skincare"])
    names = {s["name"] for s in specs}
    assert {"make_image", "make_video", "make_plan", "apply_effect", "list_models", "find_references"} <= names
    assert "No frames" in run_tool("find_references", {"scene": "a bathroom"})
    assert "No moments" in run_tool("search_footage", {"query": "serum"})
    assert "craft words" in run_tool("research_look", {"subject": "Wong Kar-wai"})
    assert "ltx2.3" in run_tool("list_models", {})
    assert "upscale" in run_tool("list_effects", {})
    with pytest.raises(guide_tools.Refused):
        run_tool("make_video", {"prompt": "x"})
    assert [c["tool"] for c in calls] == ["find_references", "search_footage", "research_look",
                                          "list_models", "list_effects", "make_video"]


# ---------- end to end, the model faked ----------

class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(role="model", parts=[]))]


def test_the_runner_runs_a_brief_through_the_real_turn_with_a_fake_model(monkeypatch, keyed,
                                                                         looks_stubbed, tmp_path):
    """The noir brief: the fake brain reads the effects, then proposes
    apply_effect noir on #1. The turn is the real creative_guide.respond
    (tools published, the proposal checked against the table), the reply
    is graded, the baseline is written."""
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append(kwargs)
        if len(seen) == 1:
            return _Resp(calls=[("list_effects", {})])
        return _Resp(calls=[("apply_effect", {"effect": "noir", "on": 1})])

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    briefs = [BRIEFS["clip-noir-grade"]]
    out = tmp_path / "vesper_baseline.json"
    summary = ev.run(briefs, turn=lambda b: ev.live_turn(b, client=object()), out=out, quiet=True)
    row = summary["results"][0]
    assert row["error"] is None and row["proposal"] == "apply_effect" and row["effect"] == "noir"
    assert row["reads"] == ["list_effects"]
    assert row["grades"]["question"]["pass"] is True and row["grades"]["checkpoint"]["pass"] is True
    assert row["expected_credits"] == {"effect": "noir", "credits": 0}
    assert summary["stub_hits"] == 0 and summary["scores"]["checkpoint"] == {"pass": 1, "of": 1, "score": 1.0}
    written = json.loads(out.read_text())
    assert written["briefs"] == 1 and written["results"][0]["id"] == "clip-noir-grade"
    # the composer's tools were declared to the model, the brief's result
    # list reached it, and the message is the effect line, not JSON
    assert seen[0]["raw"] is True and seen[0]["config"].tools
    assert "noir" in row["message"].lower()


def test_a_failing_call_degrades_to_a_listed_brief(monkeypatch, keyed, tmp_path):
    def generate(client, model, contents, **kwargs):
        raise RuntimeError("429 quota")

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    summary = ev.run([BRIEFS["vague-make-something"]], turn=lambda b: ev.live_turn(b, client=object()),
                     out=tmp_path / "b.json", quiet=True)
    assert summary["failed"] == ["vague-make-something"] and summary["answered"] == 0
    assert "429" in summary["results"][0]["error"]
    assert summary["scores"]["question"]["of"] == 0


def test_the_env_loader_takes_named_keys_only_and_never_the_database(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=abc\nDATABASE_URL=postgresql://live\nFAL_KEY=def\nOTHER=1\n")
    for name in ("GEMINI_API_KEY", "FAL_KEY", "DATABASE_URL", "OTHER"):
        monkeypatch.delenv(name, raising=False)
    assert ev.load_env(env) == ["GEMINI_API_KEY", "FAL_KEY"]
    assert "DATABASE_URL" not in __import__("os").environ and "OTHER" not in __import__("os").environ


def test_a_reference_image_is_a_real_png():
    png = ev.flat_png("the can")
    assert png.startswith(b"\x89PNG") and len(png) > 100
    refs = ev.image_refs_for(BRIEFS["idea-people-moving"])
    assert len(refs) == 2 and refs[0][1] == "image/png" and refs[0][2].startswith("Reference image:")


def test_the_make_proposal_in_the_conversation_is_never_run_by_the_runner():
    """Belt and braces: the real guide_tools.run refuses a make, and the
    runner's run_tool refuses every write before it could reach it."""
    with pytest.raises(guide_tools.Refused):
        guide_tools.run("make_video", {"prompt": "a can"})
    assert creative_guide.MAKES_FOR["video"] is None     # the composer's whole set
