"""Effects by name (src/effect_names.py; 2026-10-22, group 6 checkbox 3 of
the overnight task; docs/tasks/task-vesper-v2.md): "give this a noir
grade" becomes an apply_effect proposal for `noir` -- with the table as
the authority, so a look the table does not carry yet resolves to
nothing and this branch is the product it was until the looks merge.
"""
import json
import types as pytypes

import pytest

from src import creative_guide, effect_names, effects, gemini_utils, guide_tools


@pytest.fixture
def looks_on_table(monkeypatch):
    """The free looks as table rows (effect_names.stub_rows) for one test, switched on.

    Once the free-looks module is merged its rows are already on the table but gated by
    PHANTRA_FREE_LOOKS; stub_rows() only fills what is missing, so the flag is what makes
    a named look runnable here either way."""
    monkeypatch.setenv("PHANTRA_FREE_LOOKS", "1")
    before, names = dict(effects.EFFECTS), effects.EFFECT_NAMES
    effects.EFFECTS.update(effect_names.stub_rows())
    effects.EFFECT_NAMES = tuple(effects.EFFECTS)
    try:
        yield
    finally:
        effects.EFFECTS.clear()
        effects.EFFECTS.update(before)
        effects.EFFECT_NAMES = names


def test_the_table_is_the_authority_a_look_not_on_it_resolves_to_nothing():
    for phrase in ("noir", "give this a noir grade", "make it vertical", "film grade", "make it pro"):
        if not effect_names.on_table(effect_names.resolve(phrase) or "x"):
            assert effect_names.resolve(phrase) is None, phrase
    # the standing effects resolve by their own words
    assert effect_names.resolve("upscale it to 4k") == "upscale"
    assert effect_names.resolve("add a sound pass") == "add-sound"
    assert effect_names.resolve("remove the background") == "remove-background"
    assert effect_names.resolve("add-sound") == "add-sound"
    assert effect_names.resolve("") is None and effect_names.resolve(None) is None
    assert effect_names.resolve("make it funnier") is None


def test_the_looks_resolve_once_the_table_carries_them(looks_on_table):
    assert effect_names.resolve("give this a noir grade") == "noir"
    assert effect_names.resolve("black and white, please") == "noir"
    assert effect_names.resolve("make it look cinematic with a film grade") == "film_grade"
    assert effect_names.resolve("make it vertical for reels") == "vertical_ready"
    assert effect_names.resolve("a crash zoom on the first beat") == "crash_zoom"
    assert effect_names.resolve("that 2000s flash look") == "flash_2000s"
    assert effect_names.resolve("make it pro") == "make_it_pro"
    assert effect_names.resolve("NOIR") == "noir" and effect_names.resolve("film-grade") == "film_grade"
    # the longest alias wins over a shorter one inside it
    assert effect_names.resolve("the vertical version") == "vertical_ready"


def test_the_brains_listing_names_the_words_only_for_rows_on_the_table(looks_on_table):
    text = guide_tools.effects_for_model()
    assert "noir: said as" in text and "“noir grade”" in text
    assert "upscale: said as" in text
    assert "https://" not in text          # never a vendor page
    block = effect_names.names_block()
    assert block.startswith("Looks and finishes people name in plain words")
    assert effect_names.aliases_for("nope") == ()


def test_an_apply_effect_by_alias_is_checked_as_its_id(looks_on_table):
    results = [{"n": 1, "kind": "clip", "label": "the streetlight clip"}]
    clean = guide_tools.check_args("apply_effect", {"effect": "noir grade", "on": 1}, results)
    assert clean == {"effect": "noir", "options": {}, "prompt": "", "on": 1}
    assert guide_tools.check_args("apply_effect", {"effect": "Film Grade"})["effect"] == "film_grade"
    assert guide_tools.check_args("list_effects", {"effect": "make it vertical"}) == {"effect": "vertical_ready"}
    # a word that is no look at all is refused with the table's own list
    with pytest.raises(guide_tools.Refused, match="effect must be one of"):
        guide_tools.check_args("apply_effect", {"effect": "sepia dream"})
    # the stub row before the free-looks module is merged, the real local row after it
    noir = effects.spec("noir")
    assert (noir.get("stub") is True and noir.get("endpoint") is None) or \
        (noir.get("provider") == "local" and noir.get("free") is True)


def test_the_effects_paragraph_teaches_the_looks_by_name():
    text = creative_guide.instructions(with_tools=True, maker=True, with_effects=True)
    assert "LOOKS BY NAME" in text and "noir grade" in text and "0 credits" in text
    assert "LOOKS BY NAME" not in creative_guide.instructions(with_tools=True, maker=True)


class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(role="model", parts=[]))]


def test_a_named_look_becomes_an_effect_card_in_the_thread(monkeypatch, looks_on_table):
    """The fake brain answers "give #1 a noir grade" with apply_effect
    'noir grade' (the alias, not the id): the turn resolves it to `noir`,
    ends as a proposal, and its line is the effect's own."""
    ran = []

    def generate(client, model, contents, **kw):
        if not ran:
            ran.append(1)
            return _Resp(calls=[("list_effects", {})])
        return _Resp(calls=[("apply_effect", {"effect": "noir grade", "on": 1})])

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    specs, run_tool = guide_tools.session(local=True, maker=True)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": "give #1 a noir grade"}]),
        client=object(), grounding={}, tools=specs, run_tool=run_tool, output="video",
        results=[{"n": 1, "kind": "clip", "label": "the streetlight clip"}])
    assert reply["proposal"] == {"tool": "apply_effect", "label": "Apply this effect",
                                 "args": {"effect": "noir", "options": {}, "prompt": "", "on": 1}}
    assert reply["message"] == "Noir"
    assert reply["tool_runs"] == [{"tool": "list_effects", "args": {}, "ok": True}]
    # the eval's brief for it exists and expects exactly this
    briefs = json.loads(open("evals/vesper_plans.json").read())["briefs"]
    brief = next(b for b in briefs if b["id"] == "clip-noir-grade")
    assert brief["expect"]["effect"]["any_of"] == ["noir"]
