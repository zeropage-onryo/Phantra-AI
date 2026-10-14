"""The brain proposes the model a step is made on (src/model_menu.py; item 12
of docs/tasks/task-studio-agent.md). The list it reads is the studio's own
tables; a proposal is a model on a card, never a decision.

Each test names the line it guards. Nothing reaches a network or a model.
"""
import json
import re
import types as pytypes
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import (
    creative_guide,
    fal,
    gemini_utils,
    guide_tools,
    make_plan,
    model_menu,
    nano_banana,
    preprod,
    pricing,
    providers,
)

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)


@pytest.fixture
def tmp_db(pg, monkeypatch):
    preprod.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    return pg


# ---------- the list ----------

# guards: model_menu.image_menu -- the picker and the brain read one list
def test_the_still_menu_is_the_pickers_and_comes_off_the_table(keyed):
    menu = model_menu.image_menu(7)
    assert api.image_model_options(7) == menu
    ids = [m["id"] for m in menu["items"]]
    assert ids == [model_menu.NANO_ID] + list(fal.IMAGE_MODELS) and menu["default"] == "nano"
    for item in menu["items"][1:]:
        row = fal.IMAGE_MODELS[item["id"]]
        assert item["label"] == row["label"] and item["note"] == row["note"]
        assert item["references"] == bool(row.get("edit"))
        assert isinstance(item["credits"], int) and item["credits"] >= pricing.CREDIT_FLOOR


# guards: the menus follow the keys -- nothing is listed that cannot be made on
def test_a_model_is_listed_only_when_its_key_is_there(monkeypatch):
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    assert [m["id"] for m in model_menu.image_menu()["items"]] == ["nano"]
    assert model_menu.video_menu() == []
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: False)
    assert model_menu.image_menu() == {"items": [], "default": "nano"}
    assert model_menu.for_model() == "No model can be listed right now; leave `model` out."


# guards: model_menu.video_menu -- the catalogue's own rows and prices
def test_the_clip_menu_is_the_public_catalogue(keyed):
    clips = model_menu.video_menu()
    rows = pricing.catalog_models()
    assert [c["id"] for c in clips] == [r["model"] for r in rows]
    assert set(c["id"] for c in clips) <= set(fal.VIDEO_MODELS)
    for clip, row in zip(clips, rows):
        assert (clip["label"], clip["note"], clip["credits"]) == (row["name"], row["blurb"],
                                                                 row["credits"])


# guards: model_menu.for_model -- ids, the studio's own line, a price to weigh; no address
def test_the_brain_reads_ids_notes_and_credits_and_no_address(keyed):
    text = model_menu.for_model(7)
    for name, row in fal.IMAGE_MODELS.items():
        assert f"- {name} -- {row['label']}: {row['note']}" in text
    assert "- nano -- " in text and "no reference input" in text and "takes references" in text
    for _, model, name, blurb in pricing.CATALOG_MODELS:
        assert f"- {model} -- {name}: {blurb}" in text
    assert "`model` to make_image" in text and "`model` to make_video" in text
    assert "do not quote one yourself" in text
    assert "http" not in text and "fal.ai" not in text and "$" not in text


# guards: image_id / video_id / clean_why -- a closed set, and a short plain reason
def test_a_proposed_model_is_kept_only_when_the_tables_have_it():
    assert model_menu.image_id(" ideogram4.5 ") == "ideogram4.5"
    assert model_menu.image_id("nano") == "nano"
    assert model_menu.video_id("veo3.1") == "veo3.1"
    for wrong in ("veo3.1", "Ideogram 4.5", "", None, 7, "https://fal.ai/models/x"):
        assert model_menu.image_id(wrong) == ""
    for wrong in ("ideogram4.5", "nano", "kling", "", None):
        assert model_menu.video_id(wrong) == ""
    assert model_menu.clean_why("  words  in\nthe picture ") == "words in the picture"
    assert model_menu.clean_why(7) == ""
    long = model_menu.clean_why("word " * 100)
    assert len(long) <= model_menu.WHY_MAX + 1 and long.endswith("…")


# ---------- the tools ----------

# guards: guide_tools.session -- the list is the composer's, where every make is
def test_the_model_list_is_offered_only_where_every_make_is():
    composer = [s["name"] for s in guide_tools.session(local=True, maker=True)[0]]
    dock = [s["name"] for s in guide_tools.session(local=True, maker=True,
                                                   makes=("make_image",))[0]]
    plain = [s["name"] for s in guide_tools.session(local=True)[0]]
    assert "list_models" in composer and "list_models" not in dock + plain
    assert "list_models" in guide_tools.LOCAL_READ and not guide_tools.is_write("list_models")
    assert guide_tools.step_note("list_models") == "looked at the models"


# guards: check_args -- a still model for a still, a clip model for a scene, or nothing
def test_check_args_keeps_a_listed_model_and_drops_any_other():
    still = guide_tools.check_args("make_image", {
        "prompt": "a poster", "model": "ideogram4.5", "model_why": "words in the picture"})
    assert still == {"prompt": "a poster", "model": "ideogram4.5",
                     "model_why": "words in the picture"}
    scene = guide_tools.check_args("make_video", {"prompt": "she runs", "model": "veo3.1"})
    assert scene == {"prompt": "she runs", "model": "veo3.1"}
    # the wrong kind, a made-up id, a reason with no model: the call it was
    for args in ({"prompt": "x", "model": "veo3.1", "model_why": "y"},
                 {"prompt": "x", "model": "the best one"}, {"prompt": "x", "model_why": "y"}):
        assert guide_tools.check_args("make_image", args) == {"prompt": "x"}
    assert guide_tools.check_args("make_video", {"prompt": "x", "model": "ideogram4.5"}) == {
        "prompt": "x"}
    with pytest.raises(guide_tools.Refused):              # the URL rule still holds
        guide_tools.check_args("make_image", {"prompt": "x", "model": "nano",
                                              "model_why": "see https://x.example"})
    for tool in ("make_image", "make_video"):
        spec = next(s for s in guide_tools.MAKE_SPECS if s["name"] == tool)
        assert {"model", "model_why"} <= set(spec["input_schema"]["properties"])
        assert spec["input_schema"]["required"] == ["prompt"]


# guards: make_plan.ARG_KEYS -- a plan's image and scene steps carry the proposal
def test_a_plans_steps_carry_their_models():
    plan = guide_tools.check_args("make_plan", {"summary": "a poster, then the spot", "steps": [
        {"do": "image", "prompt": "the poster", "model": "gpt-image-2", "model_why": "text"},
        {"do": "scene", "prompt": "she runs", "model": "kling3-turbo-pro", "uses": [1]},
        {"do": "image", "prompt": "another", "model": "veo3.1"},
        {"do": "render", "scene": 2}]})
    args = [s.get("args") or {} for s in plan["steps"]]
    assert args[0]["model"] == "gpt-image-2" and args[0]["model_why"] == "text"
    assert args[1]["model"] == "kling3-turbo-pro"
    assert "model" not in args[2]
    step = make_plan.SPEC["input_schema"]["properties"]["steps"]["items"]["properties"]
    assert "model" in step and "model_why" in step


# guards: assistant_brain.run_local -- the read runs for the caller's account
def test_the_read_hands_back_this_accounts_list(keyed, monkeypatch):
    seen = []
    monkeypatch.setattr(model_menu, "for_model", lambda account_id=None: seen.append(account_id)
                        or "STILL MODELS")
    _, run_tool = guide_tools.session(local=True, maker=True, account_id=9)
    assert run_tool("list_models", {}) == "STILL MODELS" and seen == [9]


# guards: the paragraph names real tools, no address, and rides only where the tool is
def test_the_models_paragraph_rides_only_where_the_list_is_offered():
    text = (PROMPTS / "creative_guide_models.txt").read_text()
    named = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text))
    assert named == {"list_models", "make_image", "make_video", "model_why"}
    assert "http" not in text and "$" not in text
    assert "MAY PROPOSE THE MODEL" in creative_guide.instructions(with_models=True)
    assert "MAY PROPOSE THE MODEL" not in creative_guide.instructions(maker=True)


# ---------- a whole turn ----------

class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(role="model", parts=[]))]


# guards: _respond_with_tools -- the list is read, then the still names its model
def test_a_turn_reads_the_list_and_proposes_a_model_for_the_still(keyed, monkeypatch):
    responses = [
        _Resp(calls=[("list_models", {})]),
        _Resp(calls=[("make_image", {"prompt": "a poster that says OPEN LATE",
                                     "model": "ideogram4.5", "model_why": "the words must read",
                                     "aspect": "4:5"})]),
    ]
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    tools, run_tool = guide_tools.session(local=True, maker=True)
    notes = []
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": "make the poster"}]),
        client=object(), grounding={}, tools=tools, run_tool=run_tool,
        output="image", on_retry=notes.append)
    assert reply["proposal"]["args"] == {"prompt": "a poster that says OPEN LATE",
                                         "aspect": "4:5", "model": "ideogram4.5",
                                         "model_why": "the words must read"}
    assert reply["tool_runs"] == [{"tool": "list_models", "args": {}, "ok": True}]
    assert "looked at the models" in notes
    assert "MAY PROPOSE THE MODEL" in seen[0][1]["config"].system_instruction
    back = [p.function_response.response["result"] for c in seen[1][0]
            for p in (getattr(c, "parts", None) or []) if getattr(p, "function_response", None)]
    assert back and "- ideogram4.5 -- Ideogram 4.5" in back[0] and "http" not in back[0]


# ---------- where a scene's Render card opens ----------

# guards: providers.render_default(model=) -- a proposal the catalogue has, ahead of the tool
def test_a_proposed_clip_model_is_where_the_card_opens():
    assert providers.render_default("kling", None)["model"] == "kling3-turbo-pro"
    assert providers.render_default("kling", None, model="veo3.1") == {
        "provider": "fal", "model": "veo3.1"}
    # a model the catalogue does not have is no proposal: the plan stands
    assert providers.render_default("kling", None, model="sora") == providers.render_default(
        "kling", None)
    assert providers.proposed_default("wan3") == ("fal", "wan3")
    assert providers.proposed_default("") is None and providers.proposed_default(None) is None
    # and the price is resolved the way the card opened
    shot = {"tool": "KLING", "render_model": "wan3"}
    assert pricing._resolve(None, shot, None, None) == ("fal", "wan3")
    assert pricing._resolve(None, shot, "fal", None) == ("fal", "wan3")
    assert pricing._resolve(None, shot, "fal", "ltx2.3") == ("fal", "ltx2.3")
    assert pricing._resolve(None, {"tool": "KLING"}, "fal", None) == ("fal", "kling3-turbo-pro")


def a_scene(dsn, account_id=None):
    return preprod.save_concept(
        {"title": "Night ride", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "KLING", "desc": "d",
                    "prompt": "she rides through the wet city at night", "refs": ["/refs/a.jpg"]}]},
             prompt_template="T", dsn=dsn, account_id=account_id)


# guards: preprod.set_shot_render_model + the Render card's state -- stored, shown, cleared
def test_a_scenes_proposal_is_stored_on_the_shot_and_opens_its_card(tmp_db, keyed, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(auth, "current_account", lambda request, user=None: {"slug": "zeropage"})
    scene = a_scene(tmp_db)
    client = TestClient(app)
    opened = client.get(f"/api/scenes/{scene}/render").json()["scene"]
    assert opened["render_default"]["model"] == "kling3-turbo-pro" and opened["render_model"] == ""
    assert preprod.set_shot_render_model(scene, 1, "veo3.1", tmp_db, account_id=None,
                                         why="sound and people") is True
    shot = preprod.get_concept(scene, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["render_model"] == "veo3.1" and shot["render_model_why"] == "sound and people"
    assert shot["tool"] == "KLING" and shot["prompt"].startswith("she rides")   # nothing else moved
    opened = client.get(f"/api/scenes/{scene}/render").json()["scene"]
    assert opened["render_default"] == {"provider": "fal", "model": "veo3.1"}
    assert opened["render_model"] == "veo3.1" and opened["render_model_why"] == "sound and people"
    # cleared, and a scene or a shot that is not there is False, never an error
    assert preprod.set_shot_render_model(scene, 1, "", tmp_db, account_id=None) is True
    shot = preprod.get_concept(scene, dsn=tmp_db, account_id=None)["shots"][0]
    assert "render_model" not in shot and "render_model_why" not in shot
    assert preprod.set_shot_render_model(scene, 9, "veo3.1", tmp_db, account_id=None) is False
    assert preprod.set_shot_render_model(99999, 1, "veo3.1", tmp_db, account_id=None) is False


# guards: GET /api/clip-models -- the composer names a proposed renderer off the same list
def test_the_composer_reads_the_clip_menu(keyed, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(auth, "current_account", lambda request, user=None: {"slug": "zeropage"})
    body = TestClient(app).get("/api/clip-models").json()
    assert body == {"items": model_menu.video_menu(None)}
    assert {"id", "label", "note", "credits", "seconds", "frame"} <= set(body["items"][0])


# guards: the proposal changes the content hash of nothing a quote signs
def test_a_proposal_does_not_change_what_a_quote_is_signed_over():
    shot = {"prompt": "she rides", "refs": ["/refs/a.jpg"]}
    assert pricing.content_hash({**shot, "render_model": "veo3.1"}) == pricing.content_hash(shot)
    assert json.dumps(model_menu.SPEC["input_schema"]) == '{"type": "object", "properties": {}}'
