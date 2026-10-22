"""vesper_v2 (2026-10-22, group 6 checkbox 2 of the overnight task;
docs/tasks/task-vesper-v2.md): the autonomy dial never auto-approves a
costing step, the tappable question is a proposal that nothing runs, and
with the flag off every turn is the turn it was.
"""
import json
import time
import types as pytypes

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import creative_guide, gemini_utils, guide_tools
from src import make_plan as plans

# ---------- the plan runner never auto-approves a costing step ----------

@pytest.mark.parametrize("autonomy", plans.AUTONOMY + ("", "auto", "yes", None))
@pytest.mark.parametrize("doing", plans.PAID + ("queue",))
def test_a_costing_step_never_runs_unasked_under_any_setting(autonomy, doing):
    assert plans.costs(doing) is True
    assert plans.runs_unasked(doing, autonomy) is False


@pytest.mark.parametrize("doing", plans.FREE)
def test_a_free_step_runs_on_its_own_only_under_checkpoints_or_autopilot(doing):
    assert plans.costs(doing) is False
    assert plans.runs_unasked(doing, "checkpoints") is True
    assert plans.runs_unasked(doing, "autopilot") is True
    assert plans.runs_unasked(doing, "ask") is False
    assert plans.runs_unasked(doing, "") is False
    assert plans.runs_unasked("publish", "autopilot") is False      # not a step at all


def test_paid_and_free_are_the_whole_of_what_a_plan_can_do():
    assert set(plans.PAID) | set(plans.FREE) == set(plans.DOES)
    assert not set(plans.PAID) & set(plans.FREE)
    assert "render" in plans.PAID and "keyframes" in plans.PAID


# ---------- the tappable question ----------

RESULTS = [{"n": 1, "kind": "still", "label": "wide"}, {"n": 2, "kind": "still", "label": "close"}]


def test_a_question_is_cleaned_and_held_to_the_results():
    clean = guide_tools.check_args(guide_tools.ASK_TOOL, {
        "ask": "  Which   palette? ", "kind": "SWATCHES",
        "options": [{"label": "Warm", "swatch": "#D97A2B"}, {"label": "Cold", "swatch": "#2b6fd9", "value": "Cold"},
                    {"label": "", "swatch": "#000000"}, "Mono"]})
    assert clean["ask"] == "Which palette?"
    # one option without a colour: still asked, as chips
    assert clean["kind"] == "chips"
    assert [o["label"] for o in clean["options"]] == ["Warm", "Cold", "Mono"]
    assert clean["options"][0]["swatch"] == "#d97a2b" and "value" not in clean["options"][1]
    ab = guide_tools.check_args(guide_tools.ASK_TOOL, {
        "ask": "Which one?", "kind": "ab",
        "options": [{"label": "the wide one", "on": 1}, {"label": "the close one", "on": 2},
                    {"label": "a stranger", "on": 9}]}, RESULTS)
    assert [o.get("on") for o in ab["options"]] == [1, 2, None]
    # no list, no number: a number names nothing and is dropped
    assert "on" not in guide_tools.check_args(guide_tools.ASK_TOOL, {
        "ask": "x?", "options": [{"label": "a", "on": 1}, {"label": "b"}]})["options"][0]


@pytest.mark.parametrize("args", [
    {},
    {"ask": "x?"},
    {"ask": "x?", "options": ["only one"]},
    {"ask": "", "options": ["a", "b"]},
    {"ask": "see www.example.com", "options": ["a", "b"]},
    {"ask": "x?", "options": [{"label": "https://x.y/z.jpg"}, {"label": "b"}]},
])
def test_a_question_that_is_not_one_is_refused(args):
    with pytest.raises(guide_tools.Refused):
        guide_tools.check_args(guide_tools.ASK_TOOL, args)


def test_a_question_is_a_write_that_nothing_runs():
    assert guide_tools.is_write(guide_tools.ASK_TOOL) and guide_tools.is_ask(guide_tools.ASK_TOOL)
    assert not guide_tools.is_make(guide_tools.ASK_TOOL)
    with pytest.raises(guide_tools.Refused, match="question"):
        guide_tools.run(guide_tools.ASK_TOOL, {"ask": "x?", "options": ["a", "b"]})
    _, run_tool = guide_tools.session(local=True, questions=True)
    with pytest.raises(guide_tools.Refused, match="needs a click"):
        run_tool(guide_tools.ASK_TOOL, {"ask": "x?", "options": ["a", "b"]})


def test_the_question_is_offered_only_when_asked_for_and_so_is_its_paragraph():
    for kwargs in ({"local": True}, {"local": True, "maker": True}, {"maker": True},
                   {"local": True, "questions": False}):
        assert guide_tools.ASK_TOOL not in {s["name"] for s in guide_tools.session(**kwargs)[0]}
    assert guide_tools.ASK_TOOL in {s["name"] for s in guide_tools.session(local=True, questions=True)[0]}
    # the flag's default: a route turn is handed none of it
    assert guide_tools.ASK_TOOL not in {s["name"] for s in api._guide_tools(1, local=True, maker=True)[0]}
    assert guide_tools.ASK_TOOL in {s["name"] for s in api._guide_tools(1, local=True, questions=True)[0]}
    with_ = creative_guide.instructions(with_tools=True, with_questions=True)
    without = creative_guide.instructions(with_tools=True)
    assert "ASK WITH A TAP" in with_ and "ask_choice" in with_
    assert "ASK WITH A TAP" not in without and "ask_choice" not in without


class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(role="model", parts=[]))]


def _turn(monkeypatch, responses, **kwargs):
    calls = []

    def generate(client, model, contents, **kw):
        calls.append({"contents": contents, **kw})
        r = responses.pop(0)
        return r if kw.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    specs, run_tool = guide_tools.session(local=True, maker=True, questions=True)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": "an ad for the can"}]),
        client=object(), grounding={}, tools=specs, run_tool=run_tool, output="video", **kwargs)
    return reply, calls


def test_a_question_ends_the_turn_as_a_proposal_whose_line_is_the_question(monkeypatch):
    reply, calls = _turn(monkeypatch, [_Resp(calls=[(guide_tools.ASK_TOOL, {
        "ask": "Which shape is it for?", "kind": "aspect", "options": ["4:5", "9:16", "16:9"]})])])
    assert reply["proposal"]["tool"] == guide_tools.ASK_TOOL
    assert reply["proposal"]["args"] == {"ask": "Which shape is it for?", "kind": "aspect",
                                         "options": [{"label": "4:5"}, {"label": "9:16"}, {"label": "16:9"}]}
    assert reply["message"] == "Which shape is it for?"
    assert reply["proposal"]["label"] == "Answer with a tap"
    assert len(calls) == 1


def test_a_refused_question_goes_back_to_the_model_which_answers_in_words(monkeypatch):
    answer = json.dumps({"message": "Portrait or landscape?", "choices": ["4:5", "16:9"], "brief": ""})
    reply, calls = _turn(monkeypatch, [_Resp(calls=[(guide_tools.ASK_TOOL, {"ask": "?", "options": ["one"]})]),
                                       _Resp(text=answer)])
    assert reply["proposal"] is None and reply["message"] == "Portrait or landscape?"
    assert reply["tool_runs"] == [{"tool": guide_tools.ASK_TOOL, "args": {"ask": "?", "options": ["one"]},
                                   "ok": False}]


def test_the_dial_is_one_line_on_the_last_message_and_never_a_spend(monkeypatch):
    answer = json.dumps({"message": "ok", "choices": [], "brief": ""})
    reply, calls = _turn(monkeypatch, [_Resp(text=answer)], autonomy="autopilot")
    said = " ".join(p.text or "" for p in calls[0]["contents"][-1].parts)
    assert "AUTOPILOT" in said and "waits for their click" in said
    _, calls = _turn(monkeypatch, [_Resp(text=answer)])
    said = " ".join(p.text or "" for p in calls[0]["contents"][-1].parts)
    assert "autonomy dial" not in said
    assert creative_guide.autonomy_note("nonsense") == "" and creative_guide.autonomy_note(None) == ""
    for note in creative_guide.AUTONOMY_NOTES.values():
        assert "credits" in note or "clear ask" in note


# ---------- the flag, and the routes ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "v2-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    yield TestClient(app, headers={"X-Phantra-Model-Connection": "1"})
    app.dependency_overrides.pop(auth.current_account_id, None)


def test_the_flag_is_off_by_default_and_read_live(monkeypatch):
    monkeypatch.delenv("PHANTRA_VESPER_V2", raising=False)
    assert api.compute_capabilities()["vesper_v2"] is False
    monkeypatch.setenv("PHANTRA_VESPER_V2", "1")
    assert api.compute_capabilities()["vesper_v2"] is True
    monkeypatch.setenv("PHANTRA_VESPER_V2", "0")
    assert api.compute_capabilities()["vesper_v2"] is False


def test_the_act_route_refuses_a_question(client):
    r = client.post("/api/creative-guide/act", json={"tool": guide_tools.ASK_TOOL,
                                                     "args": {"ask": "x?", "options": ["a", "b"]}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_tool"
    assert "question" in r.json()["error"]["message"]


@pytest.mark.parametrize("flag, sent, questions, autonomy", [
    ("", "autopilot", False, None),           # flag off: nothing sent reaches the brain
    ("1", "autopilot", True, "autopilot"),
    ("1", "bogus", True, None),               # not a setting: no line
    ("1", "", True, None),
])
def test_the_route_hands_the_question_tool_and_the_dial_only_with_the_flag_on(
        client, monkeypatch, flag, sent, questions, autonomy):
    from src import scene_chain
    seen = {}

    async def refs(form, **kwargs):
        return [], [], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(api, "_create_gate", lambda account_id: None)
    monkeypatch.setattr(api, "_gemini_key", lambda account_id=None: "k")
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    monkeypatch.setattr(api.outcomes, "taste", lambda **k: None) if hasattr(api, "outcomes") else None
    if flag:
        monkeypatch.setenv("PHANTRA_VESPER_V2", flag)
    else:
        monkeypatch.delenv("PHANTRA_VESPER_V2", raising=False)

    def respond(conversation, **kwargs):
        seen.update(kwargs)
        return {"message": "ok", "choices": [], "brief": ""}

    monkeypatch.setattr(creative_guide, "respond", respond)
    r = client.post("/api/creative-guide", data={
        "conversation": json.dumps({"messages": [{"role": "user", "content": "an ad"}]}),
        "output": "video", "autonomy": sent})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.01)
    assert job["status"] == "done", job
    assert (guide_tools.ASK_TOOL in {s["name"] for s in seen["tools"]}) is questions
    assert seen["autonomy"] == autonomy
