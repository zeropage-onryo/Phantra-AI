"""A short number on every result, usable in a sentence (src/result_refs.py;
item 11 of docs/tasks/task-studio-agent.md). The page numbers what a
conversation made; the server tells the model the list and holds any number
its tools name to it.

Each test names the line it guards. Nothing reaches a network or a model.
"""
import json
import time
import types as pytypes
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import charge, creative_guide, gemini_utils, guide_tools, result_refs, scene_chain

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

RESULTS = [
    {"n": 1, "kind": "still", "label": "the can on wet steel"},
    {"n": 2, "kind": "clip", "label": "Camera move"},
    {"n": 3, "kind": "still", "label": "the can at night"},
    {"n": 4, "kind": "scene", "label": "Night ride"},
]


# ---------- the list a page sends ----------

# guards: result_refs.clean -- a browser's list, bounded and plain
def test_the_list_is_cleaned_like_any_form_field():
    sent = json.dumps([
        {"n": 2, "kind": "CLIP", "label": "  Camera   move "},
        {"n": "#1", "kind": "still", "label": '<b>the "can"</b> see https://x.example/a.jpg'},
        {"n": 1, "kind": "still", "label": "a second number one loses"},
        {"n": 3.0, "kind": "still", "label": 7},
        {"n": 0, "kind": "still"}, {"n": 5000, "kind": "still"}, {"n": True, "kind": "still"},
        {"n": 9, "kind": "movie"}, "not a dict", {"kind": "still"},
    ])
    assert result_refs.clean(sent) == [
        {"n": 1, "kind": "still", "label": "the 'can' see"},
        {"n": 2, "kind": "clip", "label": "Camera move"},
        {"n": 3, "kind": "still", "label": ""},
    ]
    for junk in ("", "{", "null", '{"n": 1}', 7, None, b"[]"):
        assert result_refs.clean(junk) == []
    # the newest are kept, and a label is cut at a word
    many = [{"n": i, "kind": "still", "label": "word " * 60} for i in range(1, 90)]
    kept = result_refs.clean(many)
    assert len(kept) == result_refs.MAX_RESULTS and kept[-1]["n"] == 89
    assert len(kept[0]["label"]) <= result_refs.LABEL_MAX + 1 and kept[0]["label"].endswith("…")


# guards: result_refs.note -- what the model is told, and only when there is something
def test_the_note_lists_the_results_and_is_nothing_without_them():
    note = result_refs.note(RESULTS)
    assert '#1 still — "the can on wet steel"; #2 clip — "Camera move"' in note
    assert '#4 scene — "Night ride"' in note and "{results}" not in note
    assert "`on` to apply_effect" in note and "`results` to make_image or make_video" in note
    assert "http" not in note
    assert result_refs.note([]) == "" and result_refs.note(None) == ""
    # the paragraph is a prompt file, and names only tools that exist
    text = (PROMPTS / "creative_guide_results.txt").read_text()
    for tool in ("apply_effect", "make_image", "make_video"):
        assert tool in text and guide_tools.is_write(tool)


# ---------- a number a tool names ----------

# guards: result_refs.one -- an effect's `on`, held to the list and to the kind
def test_an_effect_may_name_only_a_listed_result_of_the_right_kind():
    assert result_refs.one(1, RESULTS, takes="image") == 1
    assert result_refs.one("#3", RESULTS, takes="image") == 3
    assert result_refs.one(2, RESULTS, takes="video") == 2
    assert result_refs.one(None, RESULTS, takes="image") is None
    with pytest.raises(result_refs.Unknown, match="no result #7.*#1 still"):
        result_refs.one(7, RESULTS, takes="image")
    with pytest.raises(result_refs.Unknown, match="#2 is a clip and this effect takes a still"):
        result_refs.one(2, RESULTS, takes="image")
    with pytest.raises(result_refs.Unknown, match="#1 is a still and this effect takes a clip.*#2"):
        result_refs.one(1, RESULTS, takes="video")
    with pytest.raises(result_refs.Unknown, match="#4 is a scene"):
        result_refs.one(4, RESULTS, takes="video")
    with pytest.raises(result_refs.Unknown, match="none yet"):
        result_refs.one(1, [], takes="image")
    with pytest.raises(result_refs.Unknown):
        result_refs.one("the second one", RESULTS, takes="image")
    # no list at all: a number names nothing, and nothing is refused
    assert result_refs.one(7, None, takes="image") is None


# guards: result_refs.stills -- a make is held to stills, and only listed ones
def test_a_make_keeps_the_stills_it_named_and_drops_the_rest():
    assert result_refs.stills([3, 1], RESULTS) == [3, 1]
    assert result_refs.stills([2, "3", 4, 9, 3, True, "x"], RESULTS) == [3]
    assert result_refs.stills([1, 3], None) == [] and result_refs.stills("3", RESULTS) == []
    crowd = [{"n": i, "kind": "still", "label": ""} for i in range(1, 9)]
    assert result_refs.stills(list(range(1, 9)), crowd) == [1, 2, 3, 4]


# guards: guide_tools.check_args(results=) -- the same rules, through the bridge
def test_check_args_holds_a_named_number_to_the_turns_list():
    edit = {"effect": "nano-banana-edit", "prompt": "make it warmer", "on": 3}
    assert guide_tools.check_args("apply_effect", edit, RESULTS)["on"] == 3
    with pytest.raises(guide_tools.Refused, match="#2 is a clip"):
        guide_tools.check_args("apply_effect", {**edit, "on": 2}, RESULTS)
    with pytest.raises(guide_tools.Refused, match="no result #8"):
        guide_tools.check_args("apply_effect", {**edit, "on": 8}, RESULTS)
    # with no list the number is dropped and the call is the call it was
    assert "on" not in guide_tools.check_args("apply_effect", edit)
    assert "on" not in guide_tools.check_args("apply_effect", {"effect": "nano-banana-edit",
                                                               "prompt": "warmer"}, RESULTS)
    still = {"prompt": "the can at dawn", "results": [3, 2, 9]}
    assert guide_tools.check_args("make_image", still, RESULTS) == {
        "prompt": "the can at dawn", "results": [3]}
    assert guide_tools.check_args("make_video", {"prompt": "she lifts it", "results": [1, 3]},
                                  RESULTS)["results"] == [1, 3]
    assert "results" not in guide_tools.check_args("make_image", still)
    assert "results" not in guide_tools.check_args("make_image", {"prompt": "x", "results": [2]},
                                                   RESULTS)


# guards: the specs publish the argument, and a plan's step never carries it
def test_the_tools_publish_the_number_and_a_plan_step_does_not_take_one():
    by_name = {s["name"]: s for s in guide_tools.MAKE_SPECS + guide_tools.EFFECT_SPECS}
    assert by_name["apply_effect"]["input_schema"]["properties"]["on"]["type"] == "integer"
    for tool in ("make_image", "make_video"):
        assert by_name[tool]["input_schema"]["properties"]["results"]["type"] == "array"
        assert by_name[tool]["input_schema"]["required"] == ["prompt"]
    plan = guide_tools.check_args("make_plan", {"summary": "two", "steps": [
        {"do": "image", "prompt": "the can", "results": [1]},
        {"do": "scene", "prompt": "she lifts it", "uses": [1], "results": [1]}]}, RESULTS)
    assert all("results" not in step["args"] for step in plan["steps"])


# guards: ref_roles.label -- a still pointed at by number reaches the model captioned
def test_an_earlier_render_attached_as_a_reference_says_what_it_is():
    from src import ref_roles, shootgen
    for ref in ("/renders/nano/c12-s1.png", "https://pub.example/m/1/renders/fal/x.png?v=2"):
        assert ref_roles.is_render(ref)
        assert ref_roles.label(ref, {}) == ref_roles.RENDER_CAPTION
        assert shootgen.reference_label(ref) == ""      # the writers' own captions are as they were
    assert "keep its subject and its look" in ref_roles.RENDER_CAPTION
    # a role the person set still wins, and every other reference reads as it did
    assert ref_roles.label("/renders/a.png", {"/renders/a.png": "light"}) == ref_roles.caption("light")
    assert ref_roles.label("/refs/abc.jpg", {}) == "Reference photo supplied with this prompt:"
    assert not ref_roles.is_render("https://x.example/my-renders-folder/a.jpg")
    assert ref_roles.label("https://x.example/other.jpg", {}) == ""


# ---------- a whole turn ----------

class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(role="model", parts=[]))]


def _texts(contents):
    return [p.text for c in contents for p in (getattr(c, "parts", None) or [])
            if getattr(p, "text", None)]


def _results_back(contents):
    return [p.function_response.response["result"] for c in contents
            for p in (getattr(c, "parts", None) or []) if getattr(p, "function_response", None)]


def _turn(monkeypatch, responses, *, said="make 3 warmer", results=RESULTS, maker=True):
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    tools, run_tool = guide_tools.session(local=True, maker=maker)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": said}]),
        client=object(), brand="zeropage", grounding={}, tools=tools, run_tool=run_tool,
        output="image" if maker else None, results=results)
    return reply, seen


# guards: respond(results=) -- the list on the last message, the number on the proposal
def test_a_turn_is_told_the_results_and_an_effect_names_one(monkeypatch):
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("apply_effect", {"effect": "nano-banana-edit", "prompt": "make it warmer",
                                        "on": 3})])])
    told = "\n".join(_texts(seen[0][0]))
    assert "THE RESULTS OF THIS CONVERSATION HAVE NUMBERS" in told
    assert '#3 still — "the can at night"' in told
    assert reply["proposal"]["tool"] == "apply_effect" and reply["proposal"]["args"]["on"] == 3


# guards: a wrong number goes back to the model as the call's result, not onto a card
def test_a_number_that_is_not_there_is_handed_back_to_the_model(monkeypatch):
    answer = json.dumps({"message": "There is no result 9. Do you mean 3?", "choices": [],
                         "brief": ""})
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("apply_effect", {"effect": "nano-banana-edit", "prompt": "warmer", "on": 9})]),
        _Resp(text=answer)], said="make 9 warmer")
    assert reply["proposal"] is None and reply["message"].startswith("There is no result 9")
    [back] = _results_back(seen[1][0])
    assert back.startswith("error:") and "no result #9" in back and "#3 still" in back
    assert reply["tool_runs"][0] == {"tool": "apply_effect", "ok": False,
                                     "args": {"effect": "nano-banana-edit", "prompt": "warmer",
                                              "on": 9}}


# guards: a make held to earlier stills by number
def test_a_still_made_like_an_earlier_one_carries_its_number(monkeypatch):
    reply, _ = _turn(monkeypatch, [
        _Resp(calls=[("make_image", {"prompt": "the can at dawn", "results": [1, 2]})])],
        said="like 1 but at dawn")
    assert reply["proposal"] == {"tool": "make_image", "label": "Generate this image",
                                 "args": {"prompt": "the can at dawn", "results": [1]}}


# guards: a turn with no list, or no tool that takes a number, is the turn it was
def test_without_results_or_without_a_maker_nothing_is_said(monkeypatch):
    answer = json.dumps({"message": "ok", "choices": [], "brief": ""})
    for kw in ({"results": None}, {"results": []}, {"maker": False}):
        reply, seen = _turn(monkeypatch, [_Resp(text=answer)], **kw)
        assert "HAVE NUMBERS" not in "\n".join(_texts(seen[0][0])), kw
    # and with no list, a number the model names anyway is dropped, not refused
    reply, _ = _turn(monkeypatch, [
        _Resp(calls=[("apply_effect", {"effect": "nano-banana-edit", "prompt": "warmer", "on": 3})])],
        results=None)
    assert reply["proposal"]["tool"] == "apply_effect" and "on" not in reply["proposal"]["args"]


# ---------- the route ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "guide-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "zeropage"})
    # account 42 is a made-up id with no plan and no balance: the Create
    # gate (tested in test_spend_gates.py) is held open. The route asks
    # create_refusal_code; create_refusal is the MCP tools' wrapper over it
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    yield TestClient(app, headers={"X-ZPF-Model-Connection": "1"})
    app.dependency_overrides.pop(auth.current_account_id, None)


# guards: creative_guide_reply -- the form's list reaches the turn cleaned, or not at all
@pytest.mark.parametrize("sent,expect", [
    (json.dumps([{"n": 2, "kind": "clip", "label": "Camera move"}, {"n": 0, "kind": "still"}]),
     [{"n": 2, "kind": "clip", "label": "Camera move"}]),
    ("not json", []),
    (None, None),
])
def test_the_route_hands_the_turn_the_cleaned_list(client, monkeypatch, sent, expect):
    seen = {}

    async def refs(form):
        return [], [], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.update(kw) or {"message": "ok", "choices": [],
                                                                      "brief": ""})
    data = {"conversation": json.dumps({"messages": [{"role": "user", "content": "upscale 2"}]})}
    if sent is not None:
        data["results"] = sent
    response = client.post("/api/creative-guide", data=data)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(.01)
    assert job["status"] == "done", job
    assert seen["results"] == expect
