"""The Explore / Make switch on a project (item 13 of
docs/tasks/task-studio-agent.md). A project switched to Explore is one where
a send only talks: the turn is handed no tool that makes, is told so, and
may propose one thing -- the way out, which the person's own click takes.

Each test names the line it guards. Nothing reaches a network or a model.
"""
import json
import re
import time
import types as pytypes
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import charge, creative_guide, gemini_utils, guide_tools, make_plan, model_menu, preprod, projects, scene_chain

GUARDED = {"x-zpf-model-connection": "1"}
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

# every tool that makes, and the two reads published only beside them
MAKERS = set(guide_tools.MAKE_TOOLS) | {make_plan.TOOL, guide_tools.EFFECT_TOOL}
MAKER_READS = {guide_tools.EFFECTS_READ, model_menu.TOOL}


def names(specs):
    return [s["name"] for s in specs or []]


@pytest.fixture
def tmp_db(pg, monkeypatch):
    preprod.init(pg)
    projects.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    return pg


@pytest.fixture
def signed_in(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(auth, "current_account",
                        lambda request, user=None: {"slug": "zeropage"})


client = TestClient(app)


# ---------- the project's own setting ----------

# guards: projects.init's column and projects.update(explore=) -- Make unless switched
def test_a_project_starts_in_make_and_keeps_the_switch(tmp_db):
    project = projects.create("Citrus soda launch", "FOR: a summer spot", tmp_db, account_id=None)
    assert project["explore"] is False
    on = projects.update(project["id"], tmp_db, account_id=None, explore=True)
    assert on["explore"] is True and on["brief"] == "FOR: a summer spot"
    # another field's save leaves the switch where it was
    renamed = projects.update(project["id"], tmp_db, account_id=None, title="Citrus")
    assert renamed["explore"] is True and renamed["title"] == "Citrus"
    off = projects.update(project["id"], tmp_db, account_id=None, explore=False)
    assert off["explore"] is False
    assert projects.get(project["id"], tmp_db, account_id=None)["explore"] is False
    assert projects.list_projects(tmp_db, account_id=None)[0]["explore"] is False


# guards: ProjectBody.explore -- PATCH flips it; a new project is never born exploring
def test_the_route_flips_the_switch_and_a_new_project_is_in_make(tmp_db, signed_in):
    made = client.post("/api/projects", json={"title": "Neon city", "explore": True})
    assert made.status_code == 200, made.text
    project = made.json()
    assert project["explore"] is False
    flipped = client.patch(f"/api/projects/{project['id']}", json={"explore": True})
    assert flipped.status_code == 200, flipped.text
    assert flipped.json()["explore"] is True and flipped.json()["title"] == "Neon city"
    assert client.get(f"/api/projects/{project['id']}").json()["explore"] is True
    # a save of the brief says nothing about the switch, and leaves it
    saved = client.patch(f"/api/projects/{project['id']}", json={"brief": "FOR: a night ride"})
    assert saved.json()["explore"] is True
    back = client.patch(f"/api/projects/{project['id']}", json={"explore": False}).json()
    assert back["explore"] is False and back["brief"] == "FOR: a night ride"
    assert client.patch("/api/projects/999999", json={"explore": True}).status_code == 404


# ---------- the tools a turn is handed ----------

# guards: guide_tools.session(explore=) -- no caller can hand an exploring turn a make
@pytest.mark.parametrize("makes", [None, ("make_image",)])
def test_an_exploring_turn_is_handed_nothing_that_makes(makes):
    handed = set(names(guide_tools.session(local=True, maker=True, makes=makes,
                                           in_project=True, explore=True)[0]))
    assert not handed & MAKERS and not handed & MAKER_READS
    assert guide_tools.SWITCH_TOOL in handed
    # what costs nothing is what it was
    assert {"find_references", "keep_references", "research_look", "set_project_look"} <= handed
    # ...and the same turn in Make is the turn it always was: makes, no switch
    making = set(names(guide_tools.session(local=True, maker=True, makes=makes,
                                           in_project=True)[0]))
    assert "make_image" in making and guide_tools.SWITCH_TOOL not in making
    assert handed - {guide_tools.SWITCH_TOOL} == making - MAKERS - MAKER_READS


# guards: session -- the switch rides with the assistant's own tools, never alone
def test_a_turn_with_no_tools_of_its_own_gets_none_for_exploring():
    assert guide_tools.session(maker=True, explore=True)[0] == []


# guards: is_write / is_switch / run -- proposed by the model, run by nobody
def test_the_switch_is_a_write_that_nothing_runs():
    assert guide_tools.is_write(guide_tools.SWITCH_TOOL)
    assert guide_tools.is_switch(guide_tools.SWITCH_TOOL)
    assert not guide_tools.is_make(guide_tools.SWITCH_TOOL)
    assert not guide_tools.is_project(guide_tools.SWITCH_TOOL)
    assert not guide_tools.is_look(guide_tools.SWITCH_TOOL)
    assert guide_tools.WRITE_LABELS[guide_tools.SWITCH_TOOL] == "Switch this project to Make"
    _, run_tool = guide_tools.session(local=True, in_project=True, explore=True)
    with pytest.raises(guide_tools.Refused):
        run_tool(guide_tools.SWITCH_TOOL, {"kind": "still"})
    with pytest.raises(guide_tools.Refused, match="switch"):
        guide_tools.run(guide_tools.SWITCH_TOOL, {"kind": "still"})


# guards: creative_guide_act -- the card's click is a PATCH on the project, never this route
def test_the_act_route_refuses_the_switch(tmp_db, signed_in):
    project = projects.create("Neon city", "", tmp_db, account_id=None)
    projects.update(project["id"], tmp_db, account_id=None, explore=True)
    r = client.post("/api/creative-guide/act", headers=GUARDED,
                    json={"tool": "switch_to_make", "args": {"kind": "still"},
                          "project_id": project["id"]})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_tool", r.text
    assert projects.get(project["id"], tmp_db, account_id=None)["explore"] is True


# guards: check_args(SWITCH_TOOL) -- two keys, bounded, and never a reason to fail a turn
def test_the_switch_keeps_a_kind_and_an_idea_and_nothing_else():
    check = guide_tools.check_args
    assert check("switch_to_make", {"kind": "Still", "idea": "  The can\n low on wet slate. ",
                                    "project_id": 7, "prompt": "x"}) == {
        "kind": "still", "idea": "The can low on wet slate."}
    assert check("switch_to_make", {"kind": "clip", "idea": 4}) == {}
    assert check("switch_to_make", {}) == {} and check("switch_to_make", None) == {}
    long = check("switch_to_make", {"idea": "word " * 400})["idea"]
    assert len(long) <= guide_tools.MAX_SWITCH_IDEA + 1 and long.endswith("…")
    # an address is not shown, and is not worth the person's turn either
    assert check("switch_to_make", {"kind": "scene", "idea": "see https://x.example/a"}) == {
        "kind": "scene"}
    for kind in guide_tools.SWITCH_KINDS:
        assert check("switch_to_make", {"kind": kind}) == {"kind": kind}


# guards: switch_line -- the first sentence is code's: nothing was made
def test_the_line_above_the_card_says_nothing_was_made():
    said = guide_tools.switch_line({"kind": "still", "idea": "The can low on wet slate."})
    assert said == ("This project is exploring, so nothing has been made. "
                    "The can low on wet slate.")
    bare = guide_tools.switch_line({})
    assert bare.startswith("This project is exploring, so nothing has been made.")
    assert "Switch it to Make" in bare


# ---------- what the model is told ----------

# guards: the paragraph names only tools an exploring turn can be handed, and no address
def test_the_explore_paragraph_names_real_tools_and_rides_only_when_exploring():
    text = (PROMPTS / "creative_guide_explore.txt").read_text()
    named = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text))
    assert named == {guide_tools.SWITCH_TOOL}, named
    assert "http" not in text and "www." not in text
    exploring = creative_guide.instructions("zeropage", with_tools=True, with_explore=True)
    making = creative_guide.instructions("zeropage", with_tools=True, maker=True)
    assert "THIS PROJECT IS EXPLORING" in exploring
    assert "THIS PROJECT IS EXPLORING" not in making
    assert "YOU CAN MAKE THINGS HERE" not in exploring


# guards: explore_note -- offer the switch where it was handed, say it in words where not
def test_the_note_ends_in_what_to_do_when_asked_to_make():
    assert creative_guide.explore_note(True).endswith("call switch_to_make.")
    assert creative_guide.explore_note(False).endswith("switch the project to Make.")
    for note in (creative_guide.explore_note(True), creative_guide.explore_note(False)):
        assert note.startswith(creative_guide.EXPLORE_NOTE)


class _Resp:
    def __init__(self, text=None, calls=()):
        self.text = text
        self.function_calls = [pytypes.SimpleNamespace(name=n, args=a) for n, a in calls]
        self.candidates = [pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(role="model", parts=[]))]


def _texts(contents):
    return [p.text for c in contents for p in (getattr(c, "parts", None) or [])
            if getattr(p, "text", None)]


def _turn(monkeypatch, responses, *, explore, output="image", said="ok, draw the hero still"):
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    project = {"id": 3, "title": "Citrus soda launch", "look": "", "explore": explore}
    tools, run_tool = guide_tools.session(local=True, maker=True, in_project=True,
                                          explore=explore)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": said}]),
        client=object(), brand="zeropage", grounding={}, tools=tools, run_tool=run_tool,
        project=project, output=output, explore=explore)
    return reply, seen


# guards: respond(explore=True) + _respond_with_tools -- the ask ends on the switch, unmade
def test_asked_to_make_while_exploring_the_turn_offers_the_switch(monkeypatch):
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("switch_to_make", {"kind": "still",
                                         "idea": "The can low on wet slate, one hard side light."})]),
    ], explore=True)
    assert reply["proposal"] == {
        "tool": "switch_to_make",
        "args": {"kind": "still", "idea": "The can low on wet slate, one hard side light."},
        "label": "Switch this project to Make"}
    assert reply["message"] == ("This project is exploring, so nothing has been made. "
                                "The can low on wet slate, one hard side light.")
    contents, kwargs = seen[0]
    system = kwargs["config"].system_instruction
    assert "THIS PROJECT IS EXPLORING" in system and "YOU CAN MAKE THINGS HERE" not in system
    told = "\n".join(_texts(contents))
    assert "switched to EXPLORE" in told and "call switch_to_make" in told
    # the Image | Video line would name a tool this turn does not have
    assert "The composer is switched to IMAGE" not in told
    assert "INSIDE the project “Citrus soda launch”" in told
    offered = {d.name for t in kwargs["config"].tools for d in t.function_declarations}
    assert not offered & MAKERS and "switch_to_make" in offered


# guards: an exploring turn that only talks is an ordinary answer, with no card
def test_talk_while_exploring_is_just_an_answer(monkeypatch):
    answer = json.dumps({"message": "Three ways in: the pour, the crack of the tab, the first sip.",
                         "choices": ["The pour"], "brief": "FOR: a summer spot"})
    reply, _ = _turn(monkeypatch, [_Resp(text=answer)], explore=True,
                     said="what should the ad be?")
    assert reply["proposal"] is None and reply["message"].startswith("Three ways in")
    assert reply["brief"] == "FOR: a summer spot"


# guards: explore=False is the turn it was -- the maker block, the output line, the makes
def test_the_same_project_in_make_is_the_turn_it_always_was(monkeypatch):
    reply, seen = _turn(monkeypatch, [
        _Resp(calls=[("make_image", {"prompt": "The can low on wet slate.", "aspect": "4:5"})]),
    ], explore=False)
    assert reply["proposal"]["tool"] == "make_image"
    contents, kwargs = seen[0]
    system = kwargs["config"].system_instruction
    assert "YOU CAN MAKE THINGS HERE" in system and "THIS PROJECT IS EXPLORING" not in system
    told = "\n".join(_texts(contents))
    assert "The composer is switched to IMAGE" in told and "EXPLORE" not in told
    offered = {d.name for t in kwargs["config"].tools for d in t.function_declarations}
    assert "make_image" in offered and "switch_to_make" not in offered


# ---------- the route: the project's row decides, never the page ----------

@pytest.fixture
def guide(monkeypatch, tmp_db, signed_in):
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def refs(form, **kwargs):          # _collect_refs takes account_id= since #268
        return [], [], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    seen = {}
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.update(kw) or {"message": "ok", "choices": [],
                                                                      "brief": ""})

    def ask(project_id, output, **more):
        seen.clear()
        data = {"conversation": json.dumps({"messages": [{"role": "user", "content": "draw it"}]}),
                "output": output, "guide_provider": "gemini", **more}
        if project_id is not None:
            data["project_id"] = str(project_id)
        response = client.post("/api/creative-guide", headers=GUARDED, data=data)
        assert response.status_code == 200, response.text
        job_id = response.json()["job_id"]
        for _ in range(200):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in ("done", "failed"):
                break
            time.sleep(.01)
        assert job["status"] == "done", job
        return job, dict(seen)

    return ask


# guards: creative_guide_reply's `exploring` -- the composer's send and the dock's, both
@pytest.mark.parametrize("output", ["image", "video", "still"])
def test_a_send_inside_an_exploring_project_reaches_the_brain_with_no_make(guide, tmp_db, output):
    project = projects.create("Citrus soda launch", "", tmp_db, account_id=None)
    projects.update(project["id"], tmp_db, account_id=None, explore=True)
    job, seen = guide(project["id"], output)
    assert job["explore"] is True and seen["explore"] is True
    handed = set(names(seen["tools"]))
    assert not handed & MAKERS and "switch_to_make" in handed
    # flipped back by the person, the very next send can make again
    projects.update(project["id"], tmp_db, account_id=None, explore=False)
    job, seen = guide(project["id"], output)
    assert job["explore"] is False and seen["explore"] is False
    assert "make_image" in names(seen["tools"]) and "switch_to_make" not in names(seen["tools"])


# guards: outside a project there is no switch -- a send is what it was
def test_a_send_outside_any_project_is_never_exploring(guide):
    job, seen = guide(None, "image")
    assert job["explore"] is False and seen["explore"] is False
    assert "make_image" in names(seen["tools"])


# guards: _remember_turn(again=) -- the ask sent again after the switch is said once
def test_the_ask_sent_again_is_not_written_to_the_history_twice(guide, tmp_db):
    project = projects.create("Citrus soda launch", "", tmp_db, account_id=None)
    guide(project["id"], "still", remember="1")
    said = [(m["role"], m["content"]) for m in
            projects.messages(project["id"], tmp_db, account_id=None)["items"]]
    assert said == [("user", "draw it"), ("assistant", "ok")]
    guide(project["id"], "still", remember="1", again="1")
    said = [(m["role"], m["content"]) for m in
            projects.messages(project["id"], tmp_db, account_id=None)["items"]]
    assert said == [("user", "draw it"), ("assistant", "ok"), ("assistant", "ok")]
    # without `remember` the flag writes nothing at all
    guide(project["id"], "still", again="1")
    assert len(projects.messages(project["id"], tmp_db, account_id=None)["items"]) == 3
