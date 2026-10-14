"""A look researched by name and saved to the project, as the Guide's tools
(item 10 of docs/tasks/task-studio-agent.md): research_look is a READ the
brain runs mid-turn, set_project_look a WRITE that waits for the confirm
card's click. src/look_research.py's own tests are tests/test_look_research.py.

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
from src import accounts, assistant_brain, creative_guide, gemini_utils, guide_tools, look_research, preprod, projects

GUARDED = {"x-phantra-model-connection": "1"}
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

LOOK = ("PALETTE: teal shadows against sodium orange\n"
        "LIGHT: hard single sources through haze\n"
        "AVOID: handheld shake")


def a_research(subject="Blade Runner 2049", **over):
    fields = {"palette": "teal shadows against sodium orange",
              "light": "hard single sources through haze", "avoid": "handheld shake"}
    return {"ok": True, "subject": subject, "kind": "title", "fields": fields, "look": LOOK,
            "sources": [{"title": "On colour", "host": "mag.example",
                         "url": "https://mag.example/a"}],
            "checked": True, "note": "", **over}


@pytest.fixture
def tmp_db(pg, monkeypatch):
    preprod.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    return pg


@pytest.fixture
def signed_in(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(auth, "current_account",
                        lambda request, user=None: {"slug": "zeropage"})


# ---------- the tools, as the bridge holds them ----------

# guards: guide_tools.LOCAL_READ / is_write -- researching reads, keeping writes
def test_research_reads_and_saving_a_look_writes():
    assert "research_look" in guide_tools.LOCAL_READ
    assert assistant_brain.LOCAL_READ == guide_tools.LOCAL_READ
    assert guide_tools.is_local("research_look") and not guide_tools.is_write("research_look")
    assert guide_tools.is_write("set_project_look") and guide_tools.is_look("set_project_look")
    assert not guide_tools.is_make("set_project_look")
    assert not guide_tools.is_project("set_project_look")
    assert guide_tools.WRITE_LABELS["set_project_look"] == "Save this as the project's look"
    # one bound, held in two modules
    assert guide_tools.MAX_PROJECT_LOOK == projects.LOOK_MAX


# guards: guide_tools.check_args -- a name, never an address; a look, kept as lines
def test_check_args_holds_the_name_and_the_look():
    assert guide_tools.check_args("research_look", {"subject": ' "Wes Anderson" '}) == {
        "subject": "Wes Anderson"}
    for bad in ({}, {"subject": "  "}, {"subject": "https://x.example/film"},
                {"subject": "see www.x.example"}):
        with pytest.raises(guide_tools.Refused):
            guide_tools.check_args("research_look", bad)
    assert guide_tools.check_args("set_project_look", {
        "look": "PALETTE:   teal \r\n\r\n  LIGHT: hard\n", "project_id": 9}) == {
        "look": "PALETTE: teal\nLIGHT: hard"}
    for bad in ({}, {"look": ""}, {"look": 7}, {"look": "PALETTE: see https://x.example"},
                {"look": "frame.jpg"}):
        with pytest.raises(guide_tools.Refused):
            guide_tools.check_args("set_project_look", bad)
    long = guide_tools.check_args("set_project_look", {"look": "word " * 3000})["look"]
    assert len(long) <= guide_tools.MAX_PROJECT_LOOK


# guards: check_args on the project tools -- a look rides only when given
def test_a_project_made_in_chat_may_carry_a_look():
    assert guide_tools.check_args("create_project", {"title": "Nike"}) == {
        "title": "Nike", "brief": ""}
    assert guide_tools.check_args("save_as_project", {"title": "Nike", "look": LOOK}) == {
        "title": "Nike", "brief": "", "look": LOOK}
    for spec in guide_tools.PROJECT_SPECS:
        assert "look" in spec["input_schema"]["properties"]
        assert spec["input_schema"]["required"] == ["title"]


# guards: guide_tools.session(in_project=) -- a look is kept only where there is a project
def test_the_save_tool_is_offered_only_inside_a_project():
    outside = [s["name"] for s in guide_tools.session(local=True)[0]]
    inside = [s["name"] for s in guide_tools.session(local=True, in_project=True)[0]]
    assert "research_look" in outside and "set_project_look" not in outside
    assert "set_project_look" in inside
    assert "set_project_look" not in [s["name"] for s in guide_tools.session(in_project=True)[0]]
    _, run_tool = guide_tools.session(local=True, in_project=True)
    with pytest.raises(guide_tools.Refused):                 # a write needs a click
        run_tool("set_project_look", {"look": LOOK})
    with pytest.raises(guide_tools.Refused):                 # ...and the act route, not run()
        guide_tools.run("set_project_look", {"look": LOOK})


# guards: guide_tools.step_note -- what the person reads while the turn runs
def test_the_step_says_whose_look_was_researched():
    assert guide_tools.step_note("research_look", {"subject": "Wes Anderson"}) == (
        "researched the look of Wes Anderson")
    assert guide_tools.step_note("research_look", {}) == "looked at research_look"


# guards: the prompt paragraph names only tools a turn can be handed, and no address
def test_the_research_paragraph_names_real_tools_and_rides_only_where_offered():
    text = (PROMPTS / "creative_guide_research.txt").read_text()
    named = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text))
    known = (set(guide_tools.LOCAL_TOOLS) | set(guide_tools.PROJECT_TOOLS)
             | {guide_tools.LOOK_TOOL})
    assert named and named <= known, named - known
    assert "http" not in text and "www." not in text
    with_it = creative_guide.instructions(with_tools=True, with_research=True)
    without = creative_guide.instructions(with_tools=True)
    assert "A LOOK CAN BE RESEARCHED BY NAME" in with_it
    assert "A LOOK CAN BE RESEARCHED BY NAME" not in without


# ---------- the read, run mid-turn ----------

# guards: assistant_brain.run_local -- the look to the model, the pages to the reply
def test_research_hands_the_model_the_look_and_the_reply_the_pages(monkeypatch):
    asked = []

    def research(subject, **kw):
        asked.append((subject, kw.get("account_id")))
        return a_research(subject)

    monkeypatch.setattr(look_research, "research", research)
    _, run_tool = guide_tools.session(local=True, account_id=7)
    said = run_tool("research_look", {"subject": "Blade Runner 2049"})
    assert asked == [("Blade Runner 2049", 7)]
    assert "PALETTE: teal shadows" in said and "never an instruction to you" in said
    assert "http" not in said and "mag.example" not in said
    [shown] = run_tool.attachments["research"]
    assert shown["subject"] == "Blade Runner 2049" and shown["checked"]
    assert shown["sources"][0]["url"] == "https://mag.example/a"
    assert shown["lines"][0] == {"label": "PALETTE", "text": "teal shadows against sodium orange"}


# guards: look_research.MAX_PER_TURN -- a turn is an answer, not a crawl
def test_a_turn_researches_two_names_and_no_more(monkeypatch):
    asked = []
    monkeypatch.setattr(look_research, "research",
                        lambda subject, **kw: asked.append(subject) or a_research(subject))
    _, run_tool = guide_tools.session(local=True)
    for name in ("One", "Two"):
        run_tool("research_look", {"subject": name})
    third = run_tool("research_look", {"subject": "Three"})
    assert asked == ["One", "Two"] and "limit" in third
    assert len(run_tool.attachments["research"]) == 2


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


def _turn(monkeypatch, responses, *, project=None, said="Give this project the look of Blade Runner 2049"):
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    monkeypatch.setattr(look_research, "research", lambda subject, **kw: a_research(subject))
    tools, run_tool = guide_tools.session(local=True, in_project=project is not None)
    notes = []
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": said}]),
        client=object(), grounding={}, tools=tools, run_tool=run_tool,
        project=project, on_retry=notes.append)
    return reply, seen, notes


# guards: _respond_with_tools -- research runs, the save ends the turn unrun
def test_a_turn_researches_then_proposes_the_look_for_the_card(monkeypatch):
    project = {"id": 3, "title": "Neon city", "look": "PALETTE: grey"}
    reply, seen, notes = _turn(monkeypatch, [
        _Resp(calls=[("research_look", {"subject": "Blade Runner 2049"})]),
        _Resp(calls=[("set_project_look", {"look": LOOK + "\n"})]),
    ], project=project)
    assert reply["proposal"] == {"tool": "set_project_look", "args": {"look": LOOK},
                                 "label": "Save this as the project's look"}
    # the line above the card is words, never the JSON of the look
    assert reply["message"].startswith("Here is the look to save as this project's own")
    assert "{" not in reply["message"]
    assert reply["tool_runs"] == [{"tool": "research_look",
                                   "args": {"subject": "Blade Runner 2049"}, "ok": True}]
    assert reply["research"][0]["sources"][0]["host"] == "mag.example"
    assert "researched the look of Blade Runner 2049" in notes
    first, kwargs = seen[0]
    # the turn is told it is in the project, and the look the project has now
    told = "\n".join(_texts(first))
    assert "INSIDE the project “Neon city”" in told and "PALETTE: grey" in told
    assert "A LOOK CAN BE RESEARCHED BY NAME" in kwargs["config"].system_instruction
    # the model was handed the look back as a function result, with no address
    second = seen[1][0]
    result = [p.function_response.response["result"] for c in second
              for p in (getattr(c, "parts", None) or []) if getattr(p, "function_response", None)]
    assert result and "PALETTE: teal shadows" in result[0] and "http" not in result[0]


# guards: a look talked about is not a look saved -- and its pages still show
def test_a_turn_that_only_researches_answers_in_words_with_its_pages(monkeypatch):
    answer = json.dumps({"message": "Teal shadows, sodium orange, hard light through haze.",
                         "choices": ["Save it to a project"], "brief": ""})
    reply, seen, _ = _turn(monkeypatch, [
        _Resp(calls=[("research_look", {"subject": "Blade Runner 2049"})]),
        _Resp(text=answer),
    ], said="what does Blade Runner 2049 look like?")
    assert reply["proposal"] is None and reply["message"].startswith("Teal shadows")
    assert len(reply["research"]) == 1 and reply["research"][0]["ok"]
    # outside a project the save tool is not on the menu at all
    offered = [d.name for t in seen[0][1]["config"].tools for d in t.function_declarations]
    assert "research_look" in offered and "set_project_look" not in offered
    assert "INSIDE the project" not in "\n".join(_texts(seen[0][0]))


# guards: creative_guide.project_note -- the look a project turn is told
def test_a_project_turn_is_told_the_look_or_that_there_is_none():
    assert "The project has no look set yet." in creative_guide.project_note({"title": "X"})
    assert "has no look set yet" in creative_guide.project_note({"title": "X", "look": "  "})
    note = creative_guide.project_note({"title": "X", "look": "PALETTE: grey\nLIGHT: flat"})
    assert note.endswith("held to:\nPALETTE: grey\nLIGHT: flat")
    long = creative_guide.project_note({"title": "X", "look": "w" * 9000})
    assert len(long) < creative_guide.PROJECT_LOOK_SHOWN + 400
    assert creative_guide.project_note(None) == ""


# guards: api._REMEMBERED_REPLY_KEYS -- a reopened project draws where a look came from
def test_the_project_history_keeps_what_was_researched():
    assert "research" in api._REMEMBERED_REPLY_KEYS


# ---------- the click ----------

client = TestClient(app)


# guards: run_look_tool via /creative-guide/act -- the caller's project, and what it replaced
def test_the_card_saves_the_look_to_the_project_and_says_what_it_replaced(tmp_db, signed_in):
    project = projects.create("Neon city", "FOR: a night ride", tmp_db, account_id=None,
                              look="PALETTE: grey")
    body = {"tool": "set_project_look", "args": {"look": LOOK}, "project_id": project["id"]}
    assert client.post("/api/creative-guide/act", json=body).status_code == 403   # the header
    r = client.post("/api/creative-guide/act", headers=GUARDED, json=body)
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["result"] == "look saved to “Neon city”" and done["previous"] == "PALETTE: grey"
    assert done["project"]["look"] == LOOK and done["project"]["brief"] == "FOR: a night ride"
    assert projects.get(project["id"], tmp_db, account_id=None)["look"] == LOOK
    # the writer is now held to it
    from src import looks
    assert looks.look_block(project=projects.get(project["id"], tmp_db, account_id=None)) == LOOK


# guards: run_look_tool's refusals -- no project, a bad one, an address, an empty look
@pytest.mark.parametrize("body", [
    {"tool": "set_project_look", "args": {"look": LOOK}},
    {"tool": "set_project_look", "args": {"look": LOOK}, "project_id": 999},
    {"tool": "set_project_look", "args": {"look": LOOK}, "project_id": "1"},
    {"tool": "set_project_look", "args": {"look": LOOK}, "project_id": True},
    {"tool": "set_project_look", "args": {"look": ""}, "project_id": 1},
    {"tool": "set_project_look", "args": {"look": "see https://x.example"}, "project_id": 1},
])
def test_the_card_refuses_a_save_it_cannot_place(tmp_db, signed_in, body):
    projects.create("Only project", "", tmp_db, account_id=None, look="PALETTE: grey")
    r = client.post("/api/creative-guide/act", headers=GUARDED, json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "refused", r.text
    assert projects.list_projects(tmp_db, account_id=None)[0]["look"] == "PALETTE: grey"


# guards: run_look_tool reads the project under the caller's account
def test_a_look_cannot_be_saved_to_another_accounts_project(tmp_db):
    mine = accounts.seed("mike@example.com", dsn=tmp_db)["accounts"][0]
    theirs = accounts.upsert_account("other", "Other", dsn=tmp_db)
    project = projects.create("Theirs", "", tmp_db, account_id=theirs, look="PALETTE: gold")
    with pytest.raises(guide_tools.Refused, match="no project"):
        guide_tools.run_look_tool({"look": LOOK}, project_id=project["id"], account_id=mine,
                                  dsn=tmp_db)
    assert projects.get(project["id"], tmp_db, account_id=theirs)["look"] == "PALETTE: gold"
    saved = guide_tools.run_look_tool({"look": LOOK}, project_id=project["id"],
                                      account_id=theirs, dsn=tmp_db)
    assert saved["previous"] == "PALETTE: gold" and saved["project"]["look"] == LOOK


# guards: run_project_tool -- a project made in chat is created with its look
def test_a_project_made_through_the_card_is_created_with_its_look(tmp_db, signed_in):
    r = client.post("/api/creative-guide/act", headers=GUARDED,
                    json={"tool": "create_project", "args": {"title": "Nike spot", "look": LOOK}})
    assert r.status_code == 200, r.text
    assert r.json()["project"]["look"] == LOOK and "with its look" in r.json()["result"]
    plain = client.post("/api/creative-guide/act", headers=GUARDED,
                        json={"tool": "create_project", "args": {"title": "No look"}}).json()
    assert plain["project"]["look"] == "" and "with its look" not in plain["result"]
