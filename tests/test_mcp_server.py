"""
Tests for the MCP surface.

NO BOARD (2026-10-11, docs/tasks/task-higgsfield-shape.md step 3). Until
then most of this file was about the idea board's tools -- `board`,
`idea`, `search`, `capture`, `pick`, `shoot`, `archive`, `stats` -- and a
third "board" surface that carried them. They are gone, with their tests.
What is here: the two servers that are left (the studio surface and the
listed one) and what each publishes; the scene path the listed server
keeps (`write_scene` makes the scene, `quote` prices it, `approve` renders
it); the studio's spending tools; and the spark-bank and graph functions
that are still plain functions though no longer tools.

Two things are worth more than the coverage.

`test_no_render_connector_is_imported` walks the module's own AST for
the connectors that spend real money. A docstring cannot fail CI, and
the way that promise would break is somebody adding a convenience import
six months from now.

`test_caller_errors_reach_the_model` pins the ToolError translation. The
SDK relays a ToolError's message and replaces every other exception with
"Error executing tool <name>", so without the translation an agent
cannot tell a bad id from a broken server -- and its only recovery from
either is to retry the identical call.
"""
import ast
import os
from pathlib import Path

import pytest

from src import db, mcp_server, preprod


@pytest.fixture
def tmp_db(pg):
    path = pg
    preprod.init(path)
    return path


def _idea(title, **kw):
    return {"title": title, "hook": kw.get("hook", "a hook"),
            "logline": kw.get("logline", "")}


# ---------- where a scene stands ----------

def _scene(path, title="Cold Open", prompt="P", **shot):
    base = {"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
            "desc": title, "prompt": prompt}
    base.update(shot)
    return preprod.save_concept(
        {"title": title, "hook": "", "logline": "", "shots": [base]}, prompt_template="T", dsn=path, account_id=None)


def test_a_scene_says_where_it_stands_with_being_made(tmp_db):
    """The one word on a scene: no board words (open / picked / parked).
    A stamped `picked_at` with no clip is a render that was started."""
    get = lambda i: mcp_server._status_of(preprod.get_concept(i, dsn=tmp_db, account_id=None))  # noqa: E731
    (idea,) = preprod.save_concept_ideas([_idea("Just a title")],
                                         dsn=tmp_db, account_id=None)
    written = _scene(tmp_db, "Written")
    started = _scene(tmp_db, "Started")
    rendered = _scene(tmp_db, "Rendered", media_url="https://x/clip.mp4")
    removed = _scene(tmp_db, "Removed", media_url="https://x/clip.mp4")
    preprod.set_picked(started, dsn=tmp_db, account_id=None)
    preprod.set_picked(rendered, dsn=tmp_db, account_id=None)
    preprod.set_archived(removed, dsn=tmp_db, account_id=None)
    assert [get(i) for i in (idea, written, started, rendered, removed)] == \
        ["idea", "written", "render started", "rendered", "removed"]
    card = mcp_server._card(preprod.get_concept(written, dsn=tmp_db, account_id=None))
    assert card["status"] == "written" and "\n" not in card["summary"]


# ---------- the graph's verdict, with the run ----------

def test_a_held_run_reports_its_reason_with_the_run(tmp_db, monkeypatch):
    """A phone that asked for a run must not need a second call to
    learn why it held."""
    from src import autonomy, orchestrator
    monkeypatch.setenv("DATABASE_URL", tmp_db)
    autonomy.init(tmp_db)
    (cid,) = preprod.save_concept_ideas([_idea("Held One")],
                                        dsn=tmp_db, account_id=None)

    def fake_run(goal, **kw):
        return {"concept_id": cid, "held_reason": "prompt check: vague",
                "prompt_scores": [{"prompt": "p", "pass": False, "reason": "vague"}]}
    monkeypatch.setattr(orchestrator, "run", fake_run)
    out = mcp_server.run_graph("a direction")
    assert out["held_reason"] == "prompt check: vague"
    assert out["prompt_scores"][0]["reason"] == "vague"
    # the hold row the card's `gate` was read from went on 2026-10-14
    assert out["idea"]["id"] == cid and "gate" not in out["idea"]


# ---------- what it refuses ----------

FORBIDDEN = {"runway", "veo", "nano_banana", "imagery", "autopilot",
             "instagram", "scheduling"}


def test_no_render_connector_is_imported():
    """The header promises this surface cannot buy a clip. A docstring
    cannot fail CI; this can. The way the promise breaks is a
    convenience import added later to a file whose header still says
    otherwise."""
    source = Path(mcp_server.__file__).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
            if node.module:
                imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
    assert not (FORBIDDEN & imported), f"render connector imported: {FORBIDDEN & imported}"


def test_graph_refuses_to_run_with_render_live(monkeypatch):
    """PHANTRA_RENDER=1 turns generate_render from a dry stub into real
    Veo spend. A remote caller must never be what trips it."""
    monkeypatch.setenv("PHANTRA_RENDER", "1")
    with pytest.raises(mcp_server.Refused, match="PHANTRA_RENDER"):
        mcp_server.run_graph("a spark")


# ---------- generate: one graph run, from the spark it is given ----------

@pytest.fixture
def graph_calls(monkeypatch):
    from src import orchestrator
    calls = []

    def fake_run(goal, **kw):
        calls.append(dict(kw, goal=goal))
        return {"concept_id": None, "attempts": 1}
    monkeypatch.setattr(orchestrator, "run", fake_run)
    return calls


def test_generate_asks_the_create_gate(tmp_db, monkeypatch, graph_calls):
    """2026-09-29: generate spends Gemini for its caller, so it asks
    charge.create_refusal like Studio's Create -- and a refusal is
    Refused (stop asking), never a ValueError (ask again), and happens
    before the graph runs."""
    from src import charge
    monkeypatch.setenv("DATABASE_URL", tmp_db)
    monkeypatch.setattr(charge, "create_refusal",
                        lambda account_id, dsn=None: charge.CREATE_REFUSAL)
    with pytest.raises(mcp_server.Refused, match="subscribe or top up"):
        mcp_server.run_graph("a bench with one glove")
    assert graph_calls == []

    monkeypatch.setattr(charge, "create_refusal", lambda account_id, dsn=None: None)
    mcp_server.run_graph("a bench with one glove")
    assert len(graph_calls) == 1


def test_a_spark_runs_on_the_asset_bank_alone(tmp_db, monkeypatch, graph_calls):
    monkeypatch.setenv("DATABASE_URL", tmp_db)
    out = mcp_server.run_graph("a direction nobody banked")
    [call] = graph_calls
    assert call == {"spark": "a direction nobody banked", "account_id": call["account_id"],
                    "goal": "a direction nobody banked"}
    assert "finding_id" not in out


# ---------- bad input ----------

@pytest.mark.parametrize("call", [
    lambda p: mcp_server.run_graph(""),
    lambda p: mcp_server.quote_render(999999, dsn=p),
    lambda p: mcp_server.write_scene("too short", dsn=p),
    lambda p: mcp_server.get_project(999999, dsn=p),
])
def test_bad_input_raises_a_value_error(call, tmp_db):
    from src import projects
    projects.init(tmp_db)
    with pytest.raises(ValueError):
        call(tmp_db)


def _tools(server):
    import asyncio

    return asyncio.run(server.list_tools())


def _both(tmp_db):
    ok = lambda *a, **k: {}          # noqa: E731
    studio = mcp_server.build_server(dsn=tmp_db, job_status=_job_status, cancel_job=_cancel_job)
    listed = mcp_server.build_server(dsn=tmp_db, listed=True, job_status=_job_status,
                                     approve_render=ok, approve_keyframes=ok)
    return studio, listed


def test_the_database_is_never_published_to_the_model(tmp_db):
    """Every tool binds its database in the closure. Publishing it as an
    argument would let a remote caller name the database the server reads
    and writes -- and the account it reads as."""
    for server in _both(tmp_db):
        for tool in _tools(server):
            props = set(tool.input_schema.get("properties") or {})
            assert not {"dsn", "account_id", "db_path"} & props, tool.name
            # `path` is a FILE the person names for import_file, and nothing else's
            assert "path" not in props or tool.name == "import_file", tool.name


def test_read_only_tools_say_so(tmp_db):
    """The annotation is what lets a client show a confirmation before a
    write and none before a read."""
    _, listed = _both(tmp_db)
    by_name = {t.name: t for t in _tools(listed)}
    assert by_name["projects"].annotations.read_only_hint is True
    assert by_name["quote"].annotations.read_only_hint is True
    assert by_name["write_scene"].annotations.read_only_hint is False
    assert by_name["approve"].annotations.destructive_hint is True


def test_caller_errors_reach_the_model(tmp_db):
    """A ValueError from the tool layer must arrive as a ToolError, or
    the SDK replaces its message with a generic crash string and an
    agent cannot tell a bad id from a broken server."""
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError

    from src import projects
    projects.init(tmp_db)
    _, listed = _both(tmp_db)
    with pytest.raises(ToolError, match="no scene 999999"):
        asyncio.run(listed.call_tool("quote", {"scene_id": 999999}))
    with pytest.raises(ToolError, match="no project 999999"):
        asyncio.run(listed.call_tool("project", {"project_id": 999999}))


# ---------- the stdio entry point ----------

def test_main_runs_stdio_and_never_blocks_on_the_engine(tmp_db, monkeypatch):
    """Claude Desktop launches this process and talks down a pipe, so
    two things have to be true before the first tool call: the tables
    exist (a fresh clone would otherwise answer its first call with "no
    such table"), and a job registry is wired in -- a render takes minutes
    and a tool call that blocks that long is one the desktop times out.
    """
    captured = {}

    class FakeServer:
        def run(self, transport):
            captured["transport"] = transport

    def fake_build(dsn=None, start_job=None, job_status=None, **kw):
        captured.update(dsn=dsn, start_job=start_job, job_status=job_status)
        return FakeServer()

    monkeypatch.setattr(mcp_server, "build_server", fake_build)
    assert mcp_server.main(["--db", str(tmp_db)]) == 0
    assert captured["transport"] == "stdio"
    assert captured["dsn"] == str(tmp_db)
    assert callable(captured["start_job"]) and callable(captured["job_status"])


# ---------- what the directory publishes (2026-10-07) ----------
#
# A listed connector is read by strangers. Every tool's title, description
# and hints come from constants (TITLES / DESCRIPTIONS / HINTS) and the
# test pins them there, screens the vocabulary, and checks the caps and
# error shapes the connector checklist grades.

def _published(server):
    return {t.name: t for t in _tools(server)}


def _result(call_result):
    """The dict a tool returned. The studio surface answers with
    structuredContent (2026-10-09, step 7) and a human line as its first
    text block; the listed server still returns a `-> dict`, serialised as
    JSON text."""
    import json

    if call_result.structured_content is not None:
        return call_result.structured_content
    return json.loads(call_result.content[0].text)


# `search` left this set with the overnight connector build (PR 3): the name
# is back as a search of the whole studio (projects, scenes, elements,
# renders, cuts -- src/search.py), nothing to do with the board's idea search
BOARD_GONE = {"board", "idea", "capture", "pick", "shoot", "archive", "stats",
              "add_spark", "tonight", "sparks", "images", "reference",
              "imagine_reference", "research", "generate"}


def test_every_tool_is_published_from_its_constant(tmp_db):
    """The two servers together publish every constant, and nothing else:
    a title, a description or a hint with no tool behind it is a tool
    somebody thinks exists."""
    studio, listed = _both(tmp_db)
    tools = {**_published(studio), **_published(listed)}
    assert set(tools) == set(mcp_server.TITLES) == set(mcp_server.DESCRIPTIONS) \
        == set(mcp_server.HINTS)
    assert not set(tools) & BOARD_GONE
    listed_names = set(_published(listed))
    for name, tool in tools.items():
        assert tool.title == mcp_server.TITLES[name]
        # a listed server may word a tool for its own set (no save_chat there)
        expected = (mcp_server.LISTED_DESCRIPTIONS.get(name, mcp_server.DESCRIPTIONS[name])
                    if name in listed_names else mcp_server.DESCRIPTIONS[name])
        assert tool.description == expected
        hints = mcp_server.HINTS[name]
        ann = tool.annotations
        assert ann.title == tool.title
        assert ann.read_only_hint is hints["read"]
        assert ann.destructive_hint is hints["destructive"]
        assert ann.idempotent_hint is hints["idempotent"]
        assert ann.open_world_hint is hints["open_world"]
        assert len(name) <= 64


def test_descriptions_carry_no_operator_or_board_vocabulary(tmp_db):
    """"The nightly", "the Dev Studio", a venv command: words a directory
    user does not have, screened out of every title and description. And
    since 2026-10-11 no description tells a caller to use a tool that is
    gone (`pick` the idea first, see `board`...)."""
    import re
    studio, listed = _both(tmp_db)
    for name, tool in {**_published(studio), **_published(listed)}.items():
        text = f"{tool.title} {tool.description}"
        for word in mcp_server.INTERNAL_WORDS:
            assert word.lower() not in text.lower(), f"{name}: {word!r}"
        # words in backticks that are not this tool's own arguments
        named = set(re.findall(r"`([a-z_]+)`", tool.description)) \
            - set(tool.input_schema.get("properties") or {})
        assert not named & BOARD_GONE, f"{name} names a removed tool: {named & BOARD_GONE}"
        assert "idea board" not in text.lower() and "idea_id" not in text
    for text in (mcp_server.INSTRUCTIONS, mcp_server.STUDIO_INSTRUCTIONS):
        assert "nightly" not in text.lower() and "board" not in text.lower()


def test_hints_are_true_to_what_the_tool_does():
    """A read is read-only and idempotent; what spends is destructive; the
    tools that reach beyond this server say so."""
    h = mcp_server.HINTS
    assert all(h[n]["read"] and h[n]["idempotent"]
               for n in ("projects", "project", "project_chat", "elements", "quote", "job"))
    assert all(h[n]["destructive"] and not h[n]["read"]
               for n in ("approve", "generate_image", "generate_video", "apply_effect"))
    # destructive since 2026-10-11: `scene_id` replaces a scene, and OpenAI
    # counts an overwrite as destructive
    assert h["write_scene"] == {"read": False, "destructive": True,
                                "idempotent": False, "open_world": False}
    assert h["scene"]["read"] and h["scene"]["idempotent"]
    assert h["images_for"]["open_world"] and h["approve"]["open_world"]


# ---------- Claude writes the scene, the studio renders it (2026-10-07) ----

SCENE = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact face. "
         "Style: soft window light, true colour, a 35mm frame at chest height. "
         "(0-4s) Sam lifts the lid of a dented biscuit tin and freezes. "
         "(4-10s) Hard cut to the hallway: Sam backs away from the open door, the tin "
         "still in one hand. No background music. Only diegetic sound: the tin lid, "
         "a floorboard. Avoid: plastic sheen, cartoon reactions.")
FACE = "/characters/sam/photo/face.jpg"


@pytest.fixture
def studio(tmp_db, monkeypatch):
    """One element with photos, the catalogue stood in for (the photos
    live on disk and in R2; what is under test is the gate), and one
    project to file a scene in."""
    from src import asset_shelf, projects

    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.delenv("QUOTE_SIGNING_SECRET", raising=False)
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "a tired courier",
                          "photos": [FACE, "/characters/sam/photo/side.jpg"]},
                         {"category": "prop", "name": "Tin", "text": "", "photos": []}])
    projects.init(tmp_db)
    project = projects.create("The Tin", "a courier, a dented tin", tmp_db, account_id=None)
    return tmp_db, project["id"]


def _scenes(path):
    return preprod.list_concepts(limit=50, dsn=path, account_id=None)


def test_elements_lists_the_accounts_photos_as_refs(studio):
    path, _ = studio
    out = mcp_server.list_elements(dsn=path)
    assert [e["name"] for e in out["elements"]] == ["Sam", "Tin"]
    assert out["elements"][0]["photos"][0] == {"ref": FACE, "label": "face.jpg"}
    assert out["elements"][1]["photos"] == []


def test_write_scene_makes_the_scene_in_a_project_or_on_its_own(studio):
    """THE CHANGE (2026-10-11): it wrote onto an idea somebody had
    captured on the board. There is no board, so it makes the row."""
    from src import projects

    path, project = studio
    assert _scenes(path) == []
    out = mcp_server.write_scene(SCENE, seconds=10, refs=[FACE], title="The Tin, cold open",
                                 project_id=project, dsn=path)
    sid = out["scene_id"]
    assert out["id"] == sid and out["title"] == "The Tin, cold open"
    assert out["project_id"] == project and out["status"] == "written"
    assert out["shots_written"] == 2 and out["reference_photos"] == 1
    assert [s["n"] for s in out["shots"]] == [1, 2] and out["prompt"] == SCENE
    assert f"scene_id={sid}" in out["next"] and "pick" not in out["next"].lower()
    concept = preprod.get_concept(sid, dsn=path, account_id=None)
    assert concept["is_scene"] and concept["project_id"] == project
    assert concept["picked"] is False                  # nothing is picked, here or later
    assert [c["id"] for c in preprod.list_concepts(dsn=path, account_id=None,
                                                   project_id=project)] == [sid]
    assert projects.get(project, path, account_id=None)

    # with no project it is a scene on its own, and with no title it is
    # named off its first words
    solo = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)
    assert solo["project_id"] is None and solo["scene_id"] != sid
    assert solo["title"].startswith("Ultra-realistic grounded video")
    assert len(_scenes(path)) == 2


def test_every_shot_of_a_scene_written_in_chat_gets_its_sound_line_and_avoid_list(studio):
    """Seen on the live connector 2026-10-11 (scene 403). A chat writes
    the scene as one paragraph, and the split made here has no model in
    it: the last beat ran to the end of the prompt, so the sound line and
    the avoid-list were shot 2's action and shot 1 was rendered with
    neither."""
    from src import timeline

    path, _ = studio
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)["scene_id"]
    shot = preprod.get_concept(sid, dsn=path, account_id=None)["shots"][0]
    assert timeline.is_current(shot)
    assert [p["text"] for p in shot["timeline"]["parts"]] == [
        "Sam lifts the lid of a dented biscuit tin and freezes",
        "Hard cut to the hallway: Sam backs away from the open door, the tin still in one hand"]
    for n in (1, 2):
        sent = timeline.render_target(shot, n)["prompt"]
        assert "No background music. Only diegetic sound: the tin lid, a floorboard." in sent, n
        assert "Avoid: plastic sheen, cartoon reactions." in sent, n
    assert "backs away" not in timeline.render_target(shot, 1)["prompt"]


def test_a_scene_answer_carries_none_of_the_operators_labels(studio):
    """`write_scene` and `scene` answer a directory user: their scene, and
    not the label it is filed under here, the direction it was banked
    from, or a judge's score."""
    path, _ = studio
    out = mcp_server.write_scene(SCENE, refs=[FACE], title="The Tin", dsn=path)
    seen = mcp_server.read_scene(out["scene_id"], dsn=path)
    for answer in (out, seen):
        for key in (*mcp_server.OPERATOR_CARD_KEYS, "gate", "judge_overall", "origin"):
            assert key not in answer, key
        # what a person follows their scene by is all still there
        assert answer["id"] == answer["scene_id"] == out["scene_id"]
        assert answer["title"] == "The Tin" and answer["status"] == "written"
        assert answer["studio_url"].endswith(f"/studio/scene/{out['scene_id']}")
    # the operator's own card is untouched
    card = mcp_server._card(preprod.get_concept(out["scene_id"], dsn=path, account_id=None))
    assert set(mcp_server.OPERATOR_CARD_KEYS) <= set(card)


def test_a_lost_job_points_at_scene_only_where_there_is_one(tmp_db):
    """`job` is on the studio surface too, and that surface has no `scene`
    tool: a message telling its caller to read one sends an agent after a
    tool that is not there."""
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError

    desk = mcp_server.build_server(dsn=tmp_db, job_status=_job_status, cancel_job=_cancel_job)
    listed = mcp_server.build_server(dsn=tmp_db, listed=True, job_status=_job_status)
    with pytest.raises(ToolError) as lost:
        asyncio.run(desk.call_tool("job", {"job_id": 7}))
    assert "no job 7" in str(lost.value) and "scene" not in str(lost.value)
    assert "scene" not in {t.name for t in _tools(desk)}
    with pytest.raises(ToolError, match="no job 7.*read `scene`"):
        asyncio.run(listed.call_tool("job", {"job_id": 7}))


def test_write_scene_with_a_scene_id_rewrites_that_scene(studio):
    path, project = studio
    first = mcp_server.write_scene(SCENE, refs=[FACE], title="Take one",
                                   project_id=project, dsn=path)
    sid = first["scene_id"]
    again = mcp_server.write_scene(SCENE.replace("freezes", "laughs"), refs=[FACE],
                                   scene_id=sid, dsn=path)
    assert again["scene_id"] == sid and again["title"] == "Take one"     # the name is kept
    assert "laughs" in again["prompt"] and len(_scenes(path)) == 1
    assert again["project_id"] == project
    with pytest.raises(ValueError, match="no scene 424242"):
        mcp_server.write_scene(SCENE, refs=[FACE], scene_id=424242, dsn=path)


def test_write_scene_refuses_before_it_writes_anything(studio, monkeypatch):
    """A URL, another account's photo, a thin prompt, a leftover
    placeholder, a project that is not the caller's: each is refused, and
    none leaves a row behind. (No photographs at all is no longer one of
    them -- see the draft tests below.)"""
    path, project = studio
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    for kwargs, match in (
            (dict(refs=["https://example.com/face.jpg"]), "not one of your elements"),
            (dict(refs=["/characters/other/photo/x.jpg"]), "not one of your elements"),
            (dict(refs=[FACE], project_id=424242), "no project 424242")):
        with pytest.raises(ValueError, match=match):
            mcp_server.write_scene(SCENE, dsn=path, **kwargs)
    with pytest.raises(ValueError, match="too short"):
        mcp_server.write_scene("a man and a tin", refs=[FACE], dsn=path)
    with pytest.raises(ValueError, match="placeholder"):
        mcp_server.write_scene(SCENE + " {look}", refs=[FACE], dsn=path)
    assert _scenes(path) == []


# ---------- a scene with no photographs is a draft (2026-10-11, Mike's D2) ----------
# docs/tasks/task-connector-elements.md. The write loosened; the spend did not.

def test_an_ungrounded_scene_is_saved_as_a_draft_and_says_so(studio, monkeypatch):
    """Until today this was refused, and a new account's first scene --
    written before it had any element -- was thrown away."""
    path, project = studio
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    out = mcp_server.write_scene(SCENE, title="No photo yet", project_id=project, dsn=path)
    sid = out["scene_id"]
    assert out["needs_reference"] is True and out["reference_photos"] == 0
    assert out["status"] == "written" and out["project_id"] == project
    assert "draft" in out["note"] and "cannot be priced or rendered" in out["note"]
    assert "add_element" in out["next"] and f"scene_id={sid}" in out["next"]
    # the words are kept, exactly as written
    concept = preprod.get_concept(sid, dsn=path, account_id=None)
    assert concept["shots"][0]["prompt"] == SCENE and concept["shots"][0]["refs"] == []
    assert not concept["archived"]              # a person's draft, never the machine's reject
    # ...and `scene` says the same thing later, to a chat that did not write it
    read = mcp_server.read_scene(sid, dsn=path)
    assert read["needs_reference"] is True and "add_element" in read["next"]


def test_an_ungrounded_draft_cannot_be_priced(studio, monkeypatch):
    """The gate that matters did not move: nothing is quoted against no
    photograph, and the refusal says how to get out of it."""
    path, _ = studio
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    sid = mcp_server.write_scene(SCENE, dsn=path)["scene_id"]
    with pytest.raises(ValueError, match="draft and cannot be priced") as refused:
        mcp_server.quote_render(sid, dsn=path)
    assert "add_element" in str(refused.value) and f"scene_id={sid}" in str(refused.value)
    for listing in mcp_server.LISTINGS:
        with pytest.raises(ValueError, match="cannot be priced"):
            mcp_server.quote_render(sid, dsn=path, listing=listing)


def test_an_ungrounded_draft_becomes_a_scene_once_it_carries_a_photo(studio, monkeypatch):
    """The way out, in one call: the same scene, rewritten with a ref. The
    draft marker goes and the quote answers."""
    path, _ = studio
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    sid = mcp_server.write_scene(SCENE, title="Draft", dsn=path)["scene_id"]
    again = mcp_server.write_scene(SCENE, refs=[FACE], scene_id=sid, dsn=path)
    assert again["scene_id"] == sid and again["title"] == "Draft"
    assert "needs_reference" not in again and again["reference_photos"] == 1
    assert "quote" in again["next"] and "add_element" not in again["next"]
    assert "needs_reference" not in mcp_server.read_scene(sid, dsn=path)
    assert mcp_server.quote_render(sid, dsn=path)["clip"]["credits"] > 0
    assert len(_scenes(path)) == 1


def test_the_claude_listings_next_step_for_an_ungrounded_draft_is_a_photo(studio, monkeypatch):
    """The Claude listing rewrites `next` to point at the studio link; for
    a draft that would send the person to a page that cannot render it."""
    import asyncio

    path, _ = studio
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    server = mcp_server.build_server(dsn=path, listed="claude")
    out = _result(asyncio.run(server.call_tool("write_scene", {"prompt": SCENE})))
    assert out["needs_reference"] is True and "add_element" in out["next"]
    assert "approves the render" not in out["next"]
    grounded = _result(asyncio.run(server.call_tool(
        "write_scene", {"prompt": SCENE, "refs": [FACE]})))
    assert "approves the render" in grounded["next"]


def test_write_scene_saves_the_timed_shots_without_a_model_call(studio):
    from src import timeline

    path, _ = studio
    out = mcp_server.write_scene(SCENE, seconds=10, refs=[FACE, FACE], dsn=path)
    sid = out["scene_id"]
    assert out["shots_written"] == 2 and out["seconds"] == 10
    shot = preprod.get_concept(sid, dsn=path, account_id=None)["shots"][0]
    assert shot["prompt"] == SCENE and shot["refs"] == [FACE]
    assert shot["n"] == 1 and shot["source"] == "AI" and shot["written_by"] == "chat"
    tl = shot["timeline"]
    assert tl["planner"] == "split" and [p["n"] for p in tl["parts"]] == [1, 2]
    assert tl["parts"][0]["refs"] == [FACE]
    assert timeline.is_current(shot)          # ensure() will not re-plan it
    assert preprod.reference_gate(preprod.get_concept(sid, dsn=path, account_id=None)) is None
    # a prompt with no windows is one shot
    out = mcp_server.write_scene(SCENE.replace("(0-4s) ", "").replace("(4-10s) ", ""),
                                 seconds=8, refs=[FACE], scene_id=sid, dsn=path)
    shot = preprod.get_concept(sid, dsn=path, account_id=None)["shots"][0]
    assert out["shots_written"] == 1 and "timeline" not in shot and shot["seconds"] == 8


def test_quote_prices_the_stills_and_the_clip_and_says_what_is_affordable(studio):
    path, _ = studio
    with pytest.raises(ValueError, match="no scene 424242"):
        mcp_server.quote_render(424242, dsn=path)
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)["scene_id"]
    q = mcp_server.quote_render(sid, dsn=path)
    assert q["scene_id"] == sid and q["status"] == "written" and "picked" not in q
    assert q["keyframes"]["stills"] == 2 and q["keyframes"]["credits"] > 0
    assert q["clip"]["timed"] is True and len(q["clip"]["renders"]) == 2
    assert q["clip"]["signed"] is False and q["clip"]["renders"][0]["token"] is None
    assert q["credits_needed"] == q["keyframes"]["credits"] + q["clip"]["credits"]
    # the unowned pool has no balance to check, so nothing is refused here
    assert q["balance"] is None and q["affordable"] is True
    with pytest.raises(ValueError, match="bad renderer choice"):
        mcp_server.quote_render(sid, model="no-such-model", dsn=path)


def test_approve_runs_the_injected_bodies_and_translates_a_refusal(studio):
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError

    from src.approvals import ApproveRefused

    path, _ = studio
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)["scene_id"]
    seen = []

    def render(concept_id, account_id, body):
        seen.append(("clip", concept_id, body))
        if not body.get("tokens"):
            raise ApproveRefused(400, "missing_quote", "no quote for this render")
        return {"job_id": 7, "render": {"provider": body["provider"]}}

    def keyframes(concept_id, account_id):
        seen.append(("keyframes", concept_id))
        raise ApproveRefused(402, "out_of_credits", "top up")

    server = mcp_server.build_server(dsn=path, listed=True, approve_render=render,
                                     approve_keyframes=keyframes)
    approve = {t.name: t for t in _tools(server)}["approve"]
    assert "scene_id" in approve.input_schema["properties"]
    assert "idea_id" not in approve.input_schema["properties"]
    with pytest.raises(ToolError, match="missing_quote.*`quote`"):
        asyncio.run(server.call_tool("approve", {"scene_id": sid, "provider": "fal"}))
    out = _result(asyncio.run(server.call_tool(
        "approve", {"scene_id": sid, "provider": "fal", "tokens": ["phq.x.y"]})))
    assert out["job_id"] == 7 and "job" in out["note"]
    with pytest.raises(ToolError, match="out_of_credits: top up"):
        asyncio.run(server.call_tool("approve", {"scene_id": sid, "what": "keyframes"}))
    assert [s[0] for s in seen] == ["clip", "clip", "keyframes"]
    assert seen[1][1] == sid and seen[1][2]["tokens"] == ["phq.x.y"]
    # the scene was never picked on the way: the approve body is what stamps it
    assert preprod.get_concept(sid, dsn=path, account_id=None)["picked"] is False


def test_a_listed_approve_answers_in_credits_only(studio):
    """The approve body returns the Queue's own JSON, which carries the
    provider's estimate under dollar-named keys; the listed server drops them,
    as its `quote` does (the 2026-10-12 test-account walk read
    `render.estimate_usd` off `/mcp`'s approve)."""
    import asyncio
    import json

    path, _ = studio
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)["scene_id"]

    def render(concept_id, account_id, body):
        return {"job_id": 7, "credits": 87,
                "render": {"provider": "fal", "model": "ltx2.3", "estimate_usd": 0.36},
                "quote": {"estimate_usd": 0.36, "credits": 87,
                          "renders": [{"part": None, "credits": 87, "estimate_usd": 0.36}]}}

    def keyframes(concept_id, account_id):
        return {"job_id": 8, "stills": 2, "estimate_usd": 0.08, "credits": 20}

    server = mcp_server.build_server(dsn=path, listed=True, approve_render=render,
                                     approve_keyframes=keyframes)
    clip = _result(asyncio.run(server.call_tool(
        "approve", {"scene_id": sid, "provider": "fal", "tokens": ["phq.x.y"]})))
    assert clip["job_id"] == 7 and clip["credits"] == 87
    assert clip["render"] == {"provider": "fal", "model": "ltx2.3"}
    assert clip["quote"] == {"credits": 87, "renders": [{"part": None, "credits": 87}]}
    stills = _result(asyncio.run(server.call_tool("approve", {"scene_id": sid, "what": "keyframes"})))
    assert stills == {"job_id": 8, "stills": 2, "credits": 20, "note": "started; poll with the `job` tool"}
    assert "usd" not in json.dumps(clip).lower() and "usd" not in json.dumps(stills).lower()


def test_a_listed_refusal_for_credits_names_no_purchase_page(studio):
    """OpenAI's plugin guidelines (read 2026-10-12): a plugin may say a feature
    needs more credits than the person has, and must not link to a page that
    starts a purchase. The listed approve hint and the listed quoted-spend
    refusal say "in the studio"; the studio surface keeps its link."""
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError

    from src.approvals import ApproveRefused

    path, _ = studio
    sid = mcp_server.write_scene(SCENE, refs=[FACE], dsn=path)["scene_id"]

    def render(concept_id, account_id, body):
        raise ApproveRefused(402, "out_of_credits", "not enough credits for this render")

    def keyframes(concept_id, account_id):
        raise ApproveRefused(402, "out_of_credits", "not enough credits for these stills")

    server = mcp_server.build_server(dsn=path, listed=True, approve_render=render,
                                     approve_keyframes=keyframes)
    with pytest.raises(ToolError) as refused:
        asyncio.run(server.call_tool("approve", {"scene_id": sid, "provider": "fal", "tokens": ["phq.x.y"]}))
    assert mcp_server.CREDITS_ADDED_IN_STUDIO in str(refused.value) and "http" not in str(refused.value)


def test_a_listed_quoted_spend_refusal_names_no_purchase_page():
    """The same rule on the render listing's quoted spends (generate_image):
    the refusal keeps the numbers and loses the link. Pure, no database."""
    short = {"ok": False, "refused": "insufficient_credits", "needs": 33, "available": 5,
             "upgrade_url": mcp_server.DEFAULT_PRICING_URL,
             "note": f"Nothing was spent. Tell the person to top up at {mcp_server.DEFAULT_PRICING_URL}."}
    listed = mcp_server._listed_spend(dict(short), 1)
    assert "upgrade_url" not in listed and "http" not in listed["note"]
    assert "33 credits" in listed["note"] and "balance is 5" in listed["note"]
    # a started spend's answer is left as it is
    assert "note" not in mcp_server._listed_spend({"ok": True, "job_id": 3}, 1)


def test_approve_is_absent_without_the_approve_bodies(tmp_db):
    names = {t.name for t in _tools(mcp_server.build_server(dsn=tmp_db, listed=True))}
    assert "quote" in names and "approve" not in names


# ---------- two servers: the studio surface and the listed one (2026-10-11) ----------
# The studio surface is what Claude Desktop launches and what the
# operator's key reaches: images, video and effects, each quoted first and
# spent only after a yes in chat. The listed server is the directory
# connector's. There is no third, "board" surface any more.

SPENDS = {"generate_image", "generate_video", "apply_effect", "element_sheet", "edit_clip"}


def _job_status(i, account_id=None):
    return None


def _cancel_job(i, account_id=None):
    return None


def test_the_two_servers_publish_exactly_their_sets(tmp_db, monkeypatch):
    monkeypatch.setenv(mcp_server.ENGINE_ENV, "1")      # the flag turns nothing on any more
    studio, listed = _both(tmp_db)
    studio_names = [t.name for t in _tools(studio)]
    listed_names = [t.name for t in _tools(listed)]
    assert set(studio_names) == set(mcp_server.STUDIO_TOOLS)
    assert tuple(listed_names) == mcp_server.LISTED_TOOLS          # and in this order
    assert mcp_server.LISTED_TOOLS == (
        "projects", "project", "project_chat", "create_project",
        "elements", "add_element", "upload_link", "image_models", "video_models",
        "generate_image", "edit_image", "remove_background", "animate_still",
        "camera_move", "upscale_clip", "add_sound", "reframe_clip",
        "write_scene", "scene", "quote", "approve", "job",
        "library", "share_link", "reformat", "trim_clip", "assemble_clips",
        "balance", "search", "whoami", "recent", "credit_history", "recommend_model",
        "duplicate_scene", "feedback", "preferences", "set_preferences",
        "recipes", "recipe", "save_recipe",
        "what_works", "score_caption")
    assert mcp_server.CLAUDE_LISTED_TOOLS == (
        "projects", "project", "project_chat", "create_project",
        "elements", "add_element", "upload_link", "video_models", "write_scene", "scene",
        "quote", "job",
        "library", "share_link", "reformat", "trim_clip", "assemble_clips",
        "balance", "search", "whoami", "recent", "credit_history", "recommend_model",
        "duplicate_scene", "feedback", "preferences", "set_preferences",
        "recipes", "recipe", "save_recipe",
        "what_works", "score_caption")
    for names in (studio_names, listed_names):
        assert not set(names) & BOARD_GONE
    # the render listing carries ONE studio spending door, a still
    # (2026-10-11, Mike's call), and the effects as one tool each
    # (2026-10-20) -- never a clip from a prompt, a sheet, a clip edit or the
    # `apply_effect` runner -- the Claude listing carries none, and the studio
    # never carries the listed scene path. `job` joined the Claude listing
    # with the free edits (overnight PR 2): they start jobs, and nothing spends.
    assert set(listed_names) & SPENDS == {"generate_image"}
    assert set(mcp_server.LISTED_EFFECT_TOOLS) <= set(listed_names)
    assert not set(mcp_server.LISTED_EFFECT_TOOLS) & set(studio_names)
    assert SPENDS <= set(studio_names)
    assert not set(mcp_server.CLAUDE_LISTED_TOOLS) & (
        SPENDS | set(mcp_server.LISTED_EFFECT_TOOLS) | {"image_models", "effects", "approve"})
    assert not set(studio_names) & {"write_scene", "quote", "approve"}
    # a picture can be added from every server
    assert all("add_element" in names for names in (
        studio_names, listed_names, mcp_server.CLAUDE_LISTED_TOOLS))


def test_the_default_server_is_the_studio(tmp_db):
    """`build_server()` with nothing named used to be the board."""
    default = {t.name for t in _tools(mcp_server.build_server(dsn=tmp_db, job_status=_job_status,
                                                              cancel_job=_cancel_job))}
    assert default == set(mcp_server.STUDIO_TOOLS)


def test_the_http_mounts_studio_server_cannot_read_the_servers_disk(tmp_db):
    """`import_file` reads the machine the server runs on: the person's
    own computer over stdio, the web server's over HTTP -- so the mount
    builds without it."""
    remote = {t.name for t in _tools(mcp_server.build_server(
        dsn=tmp_db, job_status=_job_status, cancel_job=_cancel_job, local_files=False))}
    assert remote == set(mcp_server.STUDIO_TOOLS) - {"import_file"}


@pytest.mark.parametrize("surface", ["board", "everything", ""])
def test_the_board_surface_is_refused(tmp_db, surface):
    with pytest.raises(ValueError, match="removed on 2026-10-11"):
        mcp_server.build_server(dsn=tmp_db, surface=surface)
    assert mcp_server.SURFACES == ("studio",)


@pytest.mark.parametrize("argv, env, note", [
    ([], None, False),                                 # what Claude Desktop gets
    (["--surface", "studio"], None, False),
    (["--surface", "board"], None, True),              # an old config: served, and told
    ([], "board", True),
    (["--engine"], None, False),                       # accepted and ignored
])
def test_main_serves_the_studio_whatever_an_old_config_asks(tmp_db, monkeypatch, capsys,
                                                            argv, env, note):
    captured = {}

    class FakeServer:
        def run(self, transport):
            pass

    monkeypatch.setattr(mcp_server, "build_server",
                        lambda **kw: captured.update(kw) or FakeServer())
    monkeypatch.delenv(mcp_server.ENGINE_ENV, raising=False)
    if env is None:
        monkeypatch.delenv(mcp_server.SURFACE_ENV, raising=False)
    else:
        monkeypatch.setenv(mcp_server.SURFACE_ENV, env)
    assert mcp_server.main(["--db", str(tmp_db)] + argv) == 0
    assert captured["surface"] == "studio"
    assert ("is gone" in capsys.readouterr().err) is note
    assert mcp_server.ENGINE_ENV not in os.environ     # --engine sets nothing


def test_the_studio_instructions_carry_no_operator_vocabulary():
    text = mcp_server.STUDIO_INSTRUCTIONS.lower()
    for word in mcp_server.INTERNAL_WORDS:
        assert word.lower() not in text, word
    assert "quote_token" in text and "approve_usd" not in text


# ---------- references by id ----------

def _stub_sources(monkeypatch, assets=None, cands=None, photos=None, project_refs=None):
    from src import asset_shelf, fal, imagesearch, projects, render_assets
    monkeypatch.setattr(projects, "scene_refs",
                        lambda dsn=None, account_id=None, project_id=None: [
                            {"ref": r, "concept_ids": [1], "project_ids": [2]}
                            for r in (project_refs or [])])
    monkeypatch.setattr(render_assets, "get",
                        lambda i, dsn=None, account_id=None: (assets or {}).get(i))
    monkeypatch.setattr(imagesearch, "get", lambda c, dsn=None: (cands or {}).get(c))
    monkeypatch.setattr(asset_shelf, "catalogue", lambda dsn=None, account_id=None: [
        {"category": "character", "name": "Sam", "text": "",
         "photos": list(photos if photos is not None else ["https://r2/s1.jpg", "https://r2/s2.jpg"])}])
    monkeypatch.setattr(asset_shelf, "storable_ref", lambda url: "sam/" + url.rsplit("/", 1)[-1])
    monkeypatch.setattr(asset_shelf, "fetch_url", lambda raw, acct=None: raw)
    monkeypatch.setattr(fal, "as_image_url",
                        lambda v, **kw: v if str(v).startswith("https://") else None)


def test_references_resolve_by_id(monkeypatch):
    _stub_sources(monkeypatch,
                  assets={5: {"media_kind": "image", "media_url": "https://r2/a.png"}},
                  cands={"c1": {"image_url": "https://r2/c.jpg", "source": "web"}})
    refs = [p["ref"] for p in mcp_server.list_elements()["elements"][0]["photos"]]
    assert refs == ["sam/s1.jpg", "sam/s2.jpg"]
    out = mcp_server.resolve_references(["gen:5", refs[0], refs[1], "candidate:c1", "gen:5"],
                                        limit=10, who="X")
    assert out == ["https://r2/a.png", "https://r2/s1.jpg", "https://r2/s2.jpg",
                   "https://r2/c.jpg"]


@pytest.mark.parametrize("ref", [
    "https://x/a.png", "file:///etc/passwd", "gen:99", "gen:6", "gen:7",
    "sam/nobody.jpg", "element:character/sam", "candidate:nope", "junk",
])
def test_bad_references_are_refused(ref, monkeypatch):
    _stub_sources(monkeypatch,
                  assets={6: {"media_kind": "video", "media_url": "https://r2/v.mp4"},
                          7: {"media_kind": "image", "media_url": "https://r2/d.png",
                              "deleted_at": "x"}})
    with pytest.raises(ValueError):
        mcp_server.resolve_references([ref], limit=4, who="X")


def test_reference_limits_are_enforced_before_spend(monkeypatch):
    _stub_sources(monkeypatch)
    with pytest.raises(ValueError, match="takes no reference"):
        mcp_server.resolve_references(["sam/s1.jpg"], limit=0, who="FLUX 1.1 Pro")
    with pytest.raises(ValueError, match="at most 1"):
        mcp_server.resolve_references(["sam/s1.jpg", "sam/s2.jpg"], limit=1, who="X")
    assert mcp_server.resolve_references([], limit=0, who="X") == []


def test_an_unfetchable_reference_is_refused(monkeypatch):
    _stub_sources(monkeypatch, assets={5: {"media_kind": "image", "media_url": "/local/a.png"}})
    with pytest.raises(ValueError, match="fetchable"):
        mcp_server.resolve_references(["gen:5"], limit=4, who="X")


# ---------- the approval: credits, a signed token, once (2026-10-08) ----------

@pytest.fixture
def signed(monkeypatch):
    """Quotes sign only where a test says so (conftest strips the secret)."""
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-quote-secret")


def _wallet(monkeypatch, balance=1000, exempt=False):
    """An account's balance and exemption without a database: the two reads
    the gate makes."""
    from src import ledger
    monkeypatch.setattr(ledger, "credit_exempt", lambda a, dsn=None: exempt)
    monkeypatch.setattr(mcp_server, "_balance",
                        lambda a, dsn: balance if a is not None else None)


def _approved(fn, **kwargs):
    """A person's yes, as the two calls it takes: the quote, then the SAME
    call with its token."""
    q = fn(**kwargs)
    assert q["needs_approval"] is True and q["quote"]["quote_token"], q
    return q, fn(**kwargs, quote_token=q["quote"]["quote_token"])


# ---------- images ----------

def _stub_still(monkeypatch):
    from src import fal
    calls = []

    def fake(prompt, **kw):
        calls.append({"prompt": prompt, **kw})
        return {"ok": True, "media_url": "https://x/y.jpg", "asset_id": 3}

    monkeypatch.setattr(fal, "generate_image_from_prompt", fake)
    return calls


def test_image_models_projects_the_catalogue():
    from src import fal
    out = mcp_server.list_image_models()
    assert [m["id"] for m in out["models"]] == list(fal.IMAGE_MODEL_NAMES)
    assert out["default"] == fal.DEFAULT_IMAGE_MODEL and out["aspects"] == list(fal.IMAGE_SIZES)
    limits = {m["id"]: m["max_references"] for m in out["models"]}
    assert limits["flux-pro1.1"] == 0 and limits["gpt-image-2"] == 16


def test_an_image_is_quoted_before_anything_is_spent(monkeypatch, signed):
    from src import fal, ledger
    calls = _stub_still(monkeypatch)
    _wallet(monkeypatch, balance=500)
    out = mcp_server.run_image("a can", model="seedream4.5", account_id=7)
    assert out["needs_approval"] is True and out["ok"] is False and out["can_approve"]
    usd = fal.image_usd("seedream4.5")
    q = out["quote"]
    assert q["usd"] == usd and q["credits"] == ledger.charge_credits(usd)
    assert q["charged"] is True and q["balance"] == 500
    assert q["balance_after"] == 500 - q["credits"]
    assert q["quote_token"].startswith("phq.") and q["expires_at"]
    assert f"costs {q['credits']} credits" in out["note"] and "quote_token" in out["note"]
    with pytest.raises(ValueError, match="stale_content"):     # said yes to another model
        mcp_server.run_image("a can", model="nano-banana-pro", account_id=7,
                             quote_token=q["quote_token"])
    assert calls == []


def test_an_approved_image_renders_the_chosen_model(monkeypatch, signed):
    calls = _stub_still(monkeypatch)
    _wallet(monkeypatch)
    q, out = _approved(mcp_server.run_image, prompt="  a  can ", model="ideogram4.5",
                       aspect="4:5", account_id=7)
    (c,) = calls
    assert c["prompt"] == "a can" and c["model"] == "ideogram4.5" and c["aspect"] == "4:5"
    assert c["approved"] is True and c["account_id"] == 7
    assert c["source"] == "mcp" and c["bank"] is True and c["reference_urls"] is None
    # the hold is the number the person said yes to, handed down signed
    assert c["quote"].credits == q["quote"]["credits"] and c["quote"].provider == "fal"
    assert c["quote"].account_id == 7 and c["quote"].tool == "generate_image"
    assert out["ok"] and out["quote"]["usd"] == 0.06 and out["asset_id"] == 3


def test_image_references_are_passed_and_priced(monkeypatch, signed):
    from src import fal
    _stub_sources(monkeypatch)
    calls = _stub_still(monkeypatch)
    _, out = _approved(mcp_server.run_image, prompt="a can", model="flux2-pro",
                       references=["sam/s1.jpg"])
    assert calls[0]["reference_urls"] == ["https://r2/s1.jpg"]
    assert out["quote"]["usd"] == fal.image_usd("flux2-pro", references=1) \
        > fal.image_usd("flux2-pro")
    with pytest.raises(ValueError, match="no reference"):
        mcp_server.run_image("a can", model="flux-pro1.1", references=["sam/s1.jpg"])


@pytest.mark.parametrize("kwargs", [
    {"prompt": "  "},
    {"prompt": "a can", "model": "midjourney"},
    {"prompt": "a can", "model": "flux2-pro", "aspect": "7:3"},
])
def test_run_image_refuses_instead_of_clamping(kwargs, monkeypatch, signed):
    calls = _stub_still(monkeypatch)
    with pytest.raises(ValueError):
        mcp_server.run_image(**kwargs, quote_token="phq.a.b")
    assert calls == []


# ---------- video ----------

def _stub_render(monkeypatch):
    from src import fal
    calls = []

    def fake(prompt, **kw):
        calls.append({"prompt": prompt, **kw})
        return {"ok": True, "media_url": "https://x/clip.mp4", "generation_id": 1}

    monkeypatch.setattr(fal, "generate_from_prompt", fake)
    return calls


def test_video_models_projects_the_queues_menu():
    from src import providers
    out = mcp_server.list_video_models()
    assert [m["id"] for m in out["models"]] == [m["id"] for m in providers.models_for("fal")]


def test_a_clip_is_quoted_and_a_changed_length_is_caught(monkeypatch, signed):
    calls = _stub_render(monkeypatch)
    out = mcp_server.run_video("a can", model="ltx2.3", seconds=6)
    assert out["needs_approval"] is True and out["quote"]["model"] == "ltx2.3"
    assert out["quote"]["usd"] > 0 and out["quote"]["credits"] > 0
    with pytest.raises(ValueError, match="stale_content"):     # said yes to 6s, asked for 10s
        mcp_server.run_video("a can", model="ltx2.3", seconds=10,
                             quote_token=out["quote"]["quote_token"])
    with pytest.raises(ValueError, match="stale_content"):     # ...or reworded the prompt
        mcp_server.run_video("a can on a table", model="ltx2.3", seconds=6,
                             quote_token=out["quote"]["quote_token"])
    assert calls == []


def test_an_approved_price_renders_the_chosen_model_and_length(monkeypatch, signed):
    calls = _stub_render(monkeypatch)
    _wallet(monkeypatch)
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: ["https://x/still.png"] if refs else [])
    q, out = _approved(mcp_server.run_video, prompt="a  can ", model="ltx2.3", seconds=6,
                       reference="gen:12", account_id=7)
    quote = q["quote"]
    assert out["ok"] and out["quote"]["from_image"] is True
    (c,) = calls
    assert c["quote"].credits == quote["credits"] and c["quote"].tool == "generate_video"
    assert c["model"] == "ltx2.3" and c["duration"] == 6 and c["prompt"] == "a can"
    assert c["resolution"] == quote["frame"] and c["reference_image"] == "https://x/still.png"
    assert c["approved"] is True and c["account_id"] == 7 and c["source"] == "mcp"
    assert c["bank"] is True


@pytest.mark.parametrize("kwargs", [
    {"prompt": "  "},
    {"prompt": "a can", "model": "runway-gen4"},
    {"prompt": "a can", "model": "ltx2.3", "seconds": 7},
    {"prompt": "a can", "model": "ltx2.3", "frame": "144p"},
    {"prompt": "a can", "reference": "https://x/a.png"},
])
def test_video_refuses_instead_of_clamping(kwargs, monkeypatch, signed):
    _stub_sources(monkeypatch)
    calls = _stub_render(monkeypatch)
    with pytest.raises(ValueError):
        mcp_server.run_video(**kwargs, quote_token="phq.a.b")
    assert calls == []


def test_a_signed_in_caller_is_sent_to_the_scene_path(monkeypatch):
    """A person through the directory connector renders a scene they
    saved (`write_scene` -> `quote` -> `approve`), never this tool."""
    calls = _stub_render(monkeypatch)
    token = mcp_server.CALLER_ACCOUNT.set(5)
    try:
        with pytest.raises(mcp_server.Refused, match="`write_scene` and `approve`"):
            mcp_server.run_video("a can", model="ltx2.3", seconds=6, quote_token="t")
    finally:
        mcp_server.CALLER_ACCOUNT.reset(token)
    assert calls == []


def test_the_tool_quotes_inline_and_runs_an_approval_as_a_job(tmp_db, monkeypatch, signed):
    """No quote_token: the quote, no job. A bad token: refused in the
    request, before a job exists. The quote's own token: a job id -- and
    the same token again is the same job, never a second one."""
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError

    from src import quote_redemptions
    quote_redemptions.init(tmp_db)
    _stub_render(monkeypatch)
    started = []

    def start_job(kind, label, fn, cancellable=False, account_id=None):
        started.append(label)
        assert cancellable is True          # a spend can be stopped
        return {"id": 41, "status": "running"}

    server = mcp_server.build_server(dsn=tmp_db, surface="studio", start_job=start_job,
                                     job_status=_job_status)
    args = {"prompt": "a can", "model": "ltx2.3", "seconds": 6}
    quote = _result(asyncio.run(server.call_tool("generate_video", args)))
    assert quote["needs_approval"] is True and started == []
    token = quote["quote"]["quote_token"]
    with pytest.raises(ToolError, match="bad_signature"):
        asyncio.run(server.call_tool("generate_video", {**args, "quote_token": token[:-4]}))
    with pytest.raises(ToolError, match="stale_content"):
        asyncio.run(server.call_tool("generate_video",
                                     {**args, "seconds": 10, "quote_token": token}))
    assert started == []
    out = _result(asyncio.run(server.call_tool(
        "generate_video", {**args, "quote_token": token})))
    assert out["job_id"] == 41 and started == ["video ltx2.3"]
    again = _result(asyncio.run(server.call_tool(
        "generate_video", {**args, "quote_token": token})))
    assert again["job_id"] == 41 and again["already_used"] is True
    assert started == ["video ltx2.3"]                 # one yes, one job


# ---------- effects ----------

def _stub_effect(monkeypatch):
    from src import effects
    calls = []

    def fake(effect, urls, prompt, opts, **kw):
        calls.append({"effect": effect, "urls": urls, "prompt": prompt, "opts": opts, **kw})
        return {"ok": True, "media_url": "https://x/fx.mp4", "asset_id": 9}

    monkeypatch.setattr(effects, "run", fake)
    return calls


def test_effects_lists_the_catalogue_and_samples_long_enums():
    from src import effects
    out = mcp_server.list_effects()
    assert [e["id"] for e in out["effects"]] == list(effects.EFFECT_NAMES)
    kling = next(e for e in out["effects"] if e["id"] == "kling-effect")
    scene = kling["options"]["effect_scene"]
    assert scene["count"] == len(effects.KLING_EFFECTS) and len(scene["values"]) == effects.SAMPLE
    full = mcp_server.list_effects(effect="kling-effect")["effects"][0]
    assert full["options"]["effect_scene"]["values"] == list(effects.KLING_EFFECTS)
    assert {e["category"] for e in mcp_server.list_effects(category="finish")["effects"]} == {"finish"}
    with pytest.raises(ValueError):
        mcp_server.list_effects(effect="explode-everything")


def test_an_effect_is_quoted_then_run_at_the_approved_price(monkeypatch, signed):
    from src import effects
    calls = _stub_effect(monkeypatch)
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: [f"https://r2/{r}.jpg" for r in refs])
    args = dict(effect="kling-effect", sources=["gen:4"],
                options={"effect_scene": "bullet_time_360", "duration": "10"})
    q = mcp_server.run_effect(**args)
    assert q["needs_approval"] and calls == []
    assert q["quote"]["usd"] == round(0.056 * 10, 4)
    assert q["quote"]["options"] == {"effect_scene": "bullet_time_360", "duration": "10"}
    with pytest.raises(ValueError, match="stale_content"):      # a different option
        mcp_server.run_effect(**{**args, "options": {"effect_scene": "bullet_time_360",
                                                     "duration": "5"}},
                              quote_token=q["quote"]["quote_token"])
    out = mcp_server.run_effect(**args, quote_token=q["quote"]["quote_token"])
    assert out["ok"] and calls[0]["usd"] == q["quote"]["usd"]
    assert calls[0]["quote"].credits == q["quote"]["credits"]
    assert calls[0]["urls"] == ["https://r2/gen:4.jpg"] and calls[0]["source"] == "mcp"
    endpoint, body = effects.build_body("kling-effect", ["u"], "", calls[0]["opts"])
    assert endpoint.endswith("/effects") and body["input_image_urls"] == ["u"]
    assert body["effect_scene"] == "bullet_time_360" and body["duration"] == "10"


@pytest.mark.parametrize("kwargs, match", [
    ({"effect": "nope"}, "effect must be"),
    ({"effect": "kling-effect", "sources": ["gen:1"]}, "needs `effect_scene`"),
    ({"effect": "kling-effect", "sources": ["gen:1"],
      "options": {"effect_scene": "made_up"}}, "not one of"),
    ({"effect": "kling-effect", "sources": ["gen:1"],
      "options": {"effect_scene": "heart_gesture"}}, "exactly 2"),
    ({"effect": "pixverse-effect", "sources": ["gen:1"],
      "options": {"effect": "Kiss", "duration": "8"}}, "not one of"),
    ({"effect": "remove-background", "sources": ["gen:1"], "prompt": "make it pop"},
     "takes no prompt"),
    ({"effect": "flux-kontext-pro", "sources": ["gen:1"]}, "needs a prompt"),
    ({"effect": "flux-kontext-pro", "sources": ["gen:1", "gen:2"], "prompt": "x"},
     "exactly 1"),
    ({"effect": "camera-move", "sources": ["gen:1"], "prompt": "x",
      "options": {"camera_movement": "whip_pan", "speed": "fast"}}, "takes options"),
    ({"effect": "upscale", "sources": ["gen:1"], "options": {"upscale_factor": 1}},
     "without target_fps"),
])
def test_effect_refusals_happen_before_any_spend(monkeypatch, kwargs, match, signed):
    calls = _stub_effect(monkeypatch)
    monkeypatch.setattr(mcp_server, "resolve_references", lambda refs, **kw: list(refs))
    with pytest.raises(ValueError, match=match):
        mcp_server.run_effect(**kwargs, quote_token="phq.a.b")
    assert calls == []


def test_a_finishing_pass_is_priced_off_the_measured_clip(monkeypatch):
    from src import effects, render_assets
    calls = _stub_effect(monkeypatch)
    monkeypatch.setattr(render_assets, "get", lambda i, dsn=None, **kw: {
        "id": i, "media_kind": "video", "media_url": "https://r2/c.mp4", "output_path": ""})
    monkeypatch.setattr(effects, "probe_video",
                        lambda t: {"seconds": 10.0, "width": 720, "height": 1280, "fps": 24.0})
    q = mcp_server.run_effect("upscale", sources=["gen:3"])
    # 1280 * 2 = 2560 tall out -> the >1080p band, $0.08/s, 24fps -> no doubling
    assert q["quote"]["usd"] == 0.8 and q["quote"]["source_clip"]["seconds"] == 10.0
    q60 = mcp_server.run_effect("upscale", sources=["gen:3"], options={"target_fps": 60})
    assert q60["quote"]["usd"] == 1.6
    snd = mcp_server.run_effect("add-sound", sources=["gen:3"], prompt="rain on tin")
    assert snd["quote"]["usd"] == 0.01
    _, body = effects.build_body("add-sound", ["u"], "rain on tin", {}, {"seconds": 10.0})
    assert body["duration"] == 10 and body["video_url"] == "u"
    assert calls == []


def test_a_reframe_is_quoted_in_credits_off_the_clips_length(monkeypatch, signed):
    """Step 2b (2026-10-10): a clip to a new shape, priced per second of the
    measured clip, quoted like every other spend -- and a clip past Luma's
    10 seconds is refused before any quote."""
    from src import effects, ledger, render_assets
    calls = _stub_effect(monkeypatch)
    monkeypatch.setattr(render_assets, "get", lambda i, dsn=None, **kw: {
        "id": i, "media_kind": "video", "media_url": "https://r2/c.mp4", "output_path": ""})
    length = {"seconds": 8.0}
    monkeypatch.setattr(effects, "probe_video", lambda t: {
        "seconds": length["seconds"], "width": 720, "height": 1280, "fps": 24.0})
    args = dict(effect="reframe", sources=["gen:3"], options={"aspect_ratio": "16:9"},
                prompt="open sky above the roofline")
    q = mcp_server.run_effect(**args)
    assert q["needs_approval"] and q["quote"]["usd"] == 0.48
    assert q["quote"]["credits"] == ledger.charge_credits(0.48) == 116
    out = mcp_server.run_effect(**args, quote_token=q["quote"]["quote_token"])
    assert out["ok"] and calls[0]["opts"] == {"aspect_ratio": "16:9"}
    assert calls[0]["prompt"] == "open sky above the roofline" and calls[0]["usd"] == 0.48
    with pytest.raises(ValueError, match="stale_content"):       # another shape after the yes
        mcp_server.run_effect(**{**args, "options": {"aspect_ratio": "1:1"}},
                              quote_token=q["quote"]["quote_token"])
    length["seconds"] = 14.0
    with pytest.raises(ValueError, match="takes clips up to"):
        mcp_server.run_effect(**args)
    with pytest.raises(ValueError, match="needs `aspect_ratio`"):
        mcp_server.run_effect("reframe-hq", sources=["gen:3"])


def test_a_clip_source_must_be_a_render_on_the_wall(monkeypatch):
    from src import render_assets
    monkeypatch.setattr(render_assets, "get", lambda i, dsn=None, **kw: {
        "id": i, "media_kind": "image", "media_url": "https://r2/a.png"})
    for bad, match in [("https://x/y.mp4", "gen:<asset id>"),
                       ("sam/s1.jpg", "gen:<asset id>"),
                       ("gen:5", "takes a clip")]:
        with pytest.raises(ValueError, match=match):
            mcp_server.run_effect("upscale", sources=[bad])


def test_add_sound_refuses_a_clip_past_thirty_seconds(monkeypatch):
    from src import effects, render_assets
    monkeypatch.setattr(render_assets, "get", lambda i, dsn=None, **kw: {
        "id": i, "media_kind": "video", "media_url": "https://r2/c.mp4"})
    monkeypatch.setattr(effects, "probe_video",
                        lambda t: {"seconds": 31.0, "width": 720, "height": 1280, "fps": 24.0})
    with pytest.raises(ValueError, match="up to 30s"):
        mcp_server.run_effect("add-sound", sources=["gen:3"], prompt="wind")


# ---------- effects on the render listing (2026-10-13) ----------

def _dollars(value, path="") -> list:
    """Every place a payload says dollars: a key naming usd, or a $ in text."""
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            if "usd" in str(k).lower():
                found.append(f"{path}.{k}")
            found += _dollars(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            found += _dollars(v, f"{path}[{i}]")
    elif isinstance(value, str) and "$" in value:
        found.append(f"{path}: {value[:40]}")
    return found


def test_a_listed_effect_quote_and_result_carry_no_dollars(monkeypatch, signed):
    """`listed=True` is the same gate, answered in credits: the quote, the
    dry run and the result all lose `usd` and the server's path, and the
    result gains the `gen:<id>` that names it."""
    from src import effects, ledger
    calls = []

    def ran(effect, urls, prompt, opts, **kw):
        calls.append(kw)
        return {"ok": True, "media_url": "https://x/fx.mp4", "generation_id": 4,
                "asset_id": 9, "path": "/app/data/renders/fal/fx.mp4",
                "media_kind": "video", "error": None}

    monkeypatch.setattr(effects, "run", ran)
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: [f"https://r2/{r}.jpg" for r in refs])
    monkeypatch.setattr(mcp_server, "_view", lambda url, account_id: url)
    _wallet(monkeypatch)
    args = dict(effect="kling-effect", sources=["gen:4"], account_id=7, listed=True,
                options={"effect_scene": "bullet_time_360", "duration": "10"})
    q = mcp_server.run_effect(**args)
    assert q["needs_approval"] and q["quote"]["credits"] == ledger.charge_credits(0.56)
    assert q["quote"]["balance_after"] == 1000 - q["quote"]["credits"]
    assert not _dollars(q) and calls == []
    out = mcp_server.run_effect(**args, quote_token=q["quote"]["quote_token"])
    assert out["ok"] and out["ref"] == "gen:9" and "path" not in out
    assert not _dollars(out)
    assert calls[0]["usd"] == 0.56 and calls[0]["quote"].credits == q["quote"]["credits"]
    # the studio's own answer is unchanged: dollars as detail, no `ref`
    studio = mcp_server.run_effect(**{**args, "listed": False})
    assert studio["quote"]["usd"] == 0.56 and "ref" not in studio


def test_a_token_quoted_for_one_effect_cannot_run_another(monkeypatch, signed):
    """What the yes was for is what runs: another effect, another option or
    another source with the same token is `stale_content`, and nothing ran."""
    calls = _stub_effect(monkeypatch)
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: [f"https://r2/{r}.jpg" for r in refs])
    _wallet(monkeypatch)
    said_yes_to = dict(effect="remove-background", sources=["gen:4"], account_id=7,
                       listed=True)
    token = mcp_server.run_effect(**said_yes_to)["quote"]["quote_token"]
    for other in ({"effect": "nano-banana-edit", "prompt": "make it night"},
                  {"effect": "flux-kontext-pro", "prompt": "swap the label"},
                  {"sources": ["gen:5"]},
                  {"effect": "pixverse-effect", "options": {"effect": "Kiss Me AI"}}):
        with pytest.raises(ValueError, match="stale_content"):
            mcp_server.run_effect(**{**said_yes_to, **other}, quote_token=token)
    # and the listed flag is not part of what was signed: the token still
    # runs the request it was quoted for
    assert calls == []
    assert mcp_server.run_effect(**said_yes_to, quote_token=token)["ok"]
    assert len(calls) == 1 and calls[0]["effect"] == "remove-background"


@pytest.mark.parametrize("source", [
    "https://example.com/can.png", "/props/can/photo/add-1.jpg", "candidate:abc123",
    "gen:", "gen:12abc", "asset:x", "can.png", "GEN:4"])
def test_a_listed_effect_takes_only_gen_and_asset_ids(monkeypatch, source, signed):
    """No address, no element photo, no search candidate: only the two ids
    `library` hands out -- refused before anything is read or priced."""
    calls = _stub_effect(monkeypatch)
    read = []
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: read.append(refs) or list(refs))
    for effect, extra in (("remove-background", {}), ("upscale", {})):
        with pytest.raises(ValueError, match="is not a source id") as refused:
            mcp_server.run_effect(effect, sources=[source], listed=True, **extra)
        assert "`library`" in str(refused.value)
    assert read == [] and calls == []


def test_a_listed_refusal_names_the_tools_that_door_has(monkeypatch):
    """`renders` and `import_file` are the studio's; a listed caller is
    told `library`, where its ids come from."""
    from src import render_assets
    from src.cut import store as cut_store
    monkeypatch.setattr(render_assets, "get", lambda i, dsn=None, **kw: None)
    monkeypatch.setattr(cut_store, "get_media", lambda i, **kw: None)
    for effect in ("remove-background", "upscale"):
        for source, said in (("gen:5", "no render 5"), ("asset:6", "no upload 6")):
            with pytest.raises(ValueError, match=said) as listed:
                mcp_server.run_effect(effect, sources=[source], listed=True)
            assert "`library`" in str(listed.value)
            assert not {"`renders`", "`import_file`"} & set(str(listed.value).split())
            with pytest.raises(ValueError) as studio:
                mcp_server.run_effect(effect, sources=[source])
            assert "`library`" not in str(studio.value)


def test_a_failed_listed_spend_is_said_in_a_customers_words(monkeypatch, signed, capsys):
    """The adapter's error is the provider talking to the operator (a
    vendor's billing page, a key's name). A listed answer says what
    happened and that nothing was charged; the raw text goes to the log."""
    from src import effects
    raw = ('HTTP Error 403: Forbidden -- {"detail":"User is locked. Reason: Exhausted '
           'balance. Top up your balance at fal.ai/dashboard/billing."}')
    monkeypatch.setattr(effects, "run", lambda *a, **kw: {"ok": False, "error": raw})
    monkeypatch.setattr(mcp_server, "resolve_references", lambda refs, **kw: ["https://r2/a.jpg"])
    _wallet(monkeypatch)
    args = dict(effect="remove-background", sources=["gen:4"], account_id=7)
    _, out = _approved(mcp_server.run_effect, **args, listed=True)
    assert out["ok"] is False and "fal.ai" not in out["error"]
    assert out["error"].startswith("The effect was not made") and "Nothing was charged" in out["error"]
    assert "fal.ai/dashboard/billing" in capsys.readouterr().err        # kept, off the answer
    _, studio = _approved(mcp_server.run_effect, **args)
    assert studio["error"] == raw                                      # the operator's door


def test_the_listed_descriptions_promise_no_link_and_name_no_absent_tool(tmp_db):
    """A listed refusal for credits carries no purchase link
    (`_listed_spend`), so no description may promise `upgrade_url`; and the
    spending tools point only at tools that listing has. Each effect is its
    own tool (2026-10-20): no menu, no runner, and every choice typed."""
    import re
    _, listed = _both(tmp_db)
    tools = _published(listed)
    elsewhere = set(mcp_server.TITLES) - set(mcp_server.LISTED_TOOLS)
    spending = ("generate_image",) + mcp_server.LISTED_EFFECT_TOOLS
    for name in spending:
        text = tools[name].description
        assert "upgrade_url" not in text and "with that link" not in text
        named = set(re.findall(r"`([a-z_]+)`", text)) \
            - set(tools[name].input_schema.get("properties") or {})
        assert not named & elsewhere, f"{name} names {named & elsewhere}"
        assert text.startswith("SPENDS CREDITS.") and "`quote_token`" in text
    for name in mcp_server.LISTED_EFFECT_TOOLS:
        assert "`library`" in tools[name].description
        props = tools[name].input_schema["properties"]
        assert not {"effect", "options"} & set(props)          # nothing to dispatch on
        assert {"quote_token", "project_id"} <= set(props)
    assert len(tools["animate_still"].input_schema["properties"]["template"]["enum"]) == 252
    # an element photo is not an effect's source there, and `elements` says so;
    # the Claude listing's own wording is left exactly as it was
    assert "An effect takes a `gen:<id>` or `asset:<id>`" in tools["elements"].description
    claude = _published(mcp_server.build_server(dsn=tmp_db, listed="claude",
                                                job_status=_job_status))
    assert claude["elements"].description == mcp_server.DESCRIPTIONS["elements"]
    assert not {"effects", "apply_effect", *mcp_server.LISTED_EFFECT_TOOLS} & set(claude)
    assert all(name in mcp_server.INSTRUCTIONS for name in mcp_server.LISTED_EFFECT_TOOLS)
    assert "apply_effect" not in mcp_server.INSTRUCTIONS
    assert "effect" not in mcp_server.CLAUDE_INSTRUCTIONS


# ---------- renders and the prompt guides ----------

def test_renders_lists_the_wall_as_ids(monkeypatch):
    from src import media, render_assets
    rows = [{"id": i, "media_kind": "video" if i % 2 else "image", "model": "m",
             "provider": "P", "prompt": "x" * 300, "media_url": f"https://r2/{i}"}
            for i in range(30, 0, -1)]
    monkeypatch.setattr(render_assets, "list_all", lambda dsn=None, account_id=None: rows)
    monkeypatch.setattr(media, "url_for", lambda url, account_id=None: url + "?minted")
    out = mcp_server.list_renders(kind="image", limit=3, account_id=1)
    assert [r["id"] for r in out["renders"]] == ["gen:30", "gen:28", "gen:26"]
    assert out["renders"][0]["media_url"].endswith("?minted")
    assert len(out["renders"][0]["prompt"]) == 160
    assert len(mcp_server.list_renders(limit=1000, account_id=1)["renders"]) == 30
    with pytest.raises(ValueError):        # audio is a kind since 2026-10-09 (uploads)
        mcp_server.list_renders(kind="gif", account_id=1)


def _shelf(monkeypatch, refs=None, ok=True):
    from src import rag
    monkeypatch.setattr(rag, "retrieve_references",
                        lambda text, **kw: {"ok": ok, "references":
                                            [{"source": "seedance.md", "chunk": c}
                                             for c in refs or []],
                                            "error": None if ok else "no key"})


def test_refine_hands_back_the_studios_instruction_with_the_shelf(tmp_db, monkeypatch):
    _shelf(monkeypatch, ["lead with the subject, then the camera"])
    out = mcp_server.get_prompt_craft("refine", "(0-3s) a glove on a bench",
                                      model="ltx2.3", dsn=tmp_db)
    assert "(0-3s) a glove on a bench" in out["instruction"]
    assert "lead with the subject" in out["instruction"] and out["references_found"] == 1


def test_refine_survives_an_unreachable_shelf(tmp_db, monkeypatch):
    _shelf(monkeypatch, ok=False)
    out = mcp_server.get_prompt_craft("refine", "a glove on a bench", tool="LTX", dsn=tmp_db)
    assert out["references_found"] == 0 and out["lookup_error"] == "no key"
    assert "a glove on a bench" in out["instruction"]


def test_the_other_steps_return_the_studios_rubrics(tmp_db):
    assert mcp_server.get_prompt_craft("enhance", "x", dsn=tmp_db)["instruction"]
    still = mcp_server.get_prompt_craft("still", "a push-in on a glove", dsn=tmp_db)
    assert "STILL" in still["instruction"] and "a push-in on a glove" in still["instruction"]
    beats = mcp_server.get_prompt_craft("beats", "tilt up", count=3, dsn=tmp_db)
    assert "at most 3" in beats["instruction"]


@pytest.mark.parametrize("kwargs", [
    {"step": "write", "prompt": "x"},
    {"step": "refine", "prompt": ""},
    {"step": "refine", "prompt": "x"},
    {"step": "refine", "prompt": "x", "model": "runway-gen4"},
])
def test_prompt_craft_refuses_what_it_cannot_serve(kwargs, tmp_db, monkeypatch):
    _shelf(monkeypatch)
    with pytest.raises(ValueError):
        mcp_server.get_prompt_craft(**kwargs, dsn=tmp_db)


# ---------- projects from Claude (2026-10-08) ----------
# Make a project here, reopen one made in the studio, and pull what it
# already has: its scenes, the reference images they used, its renders and
# its chat -- the same rows the studio's projects board draws.

def _project_db(tmp_db, monkeypatch):
    from src import projects, render_assets
    projects.init(tmp_db)
    render_assets.init(tmp_db)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    return tmp_db


def _scene_in(path, project_id, title, refs, **shot):
    from src import projects
    cid = preprod.save_concept(
        {"title": title, "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY", "desc": "d",
                    "prompt": f"{title}: a woman lifts the lid", "refs": refs, **shot}]},
             prompt_template="T", dsn=path, account_id=None)
    if project_id is not None:
        projects.tag_concepts([cid], project_id, path, account_id=None)
    return cid


def test_a_project_made_here_is_listed_and_reopened(tmp_db, monkeypatch):
    path = _project_db(tmp_db, monkeypatch)
    made = mcp_server.make_project("  Perfume   ad ", brief="gold, slow",
                                   look="soft window light", dsn=path)
    assert made["title"] == "Perfume ad" and "project_id=" in made["next"]
    listed = mcp_server.list_project_cards(dsn=path)
    assert [p["id"] for p in listed["projects"]] == [made["id"]]
    card = listed["projects"][0]
    assert card["has_look"] is True and card["brief"] == "gold, slow" and card["scenes"] == 0
    opened = mcp_server.get_project(made["id"], dsn=path)
    assert opened["look"] == "soft window light" and opened["brief"] == "gold, slow"
    assert opened["scenes"] == opened["references"] == opened["renders"] == opened["chat"] == []
    with pytest.raises(ValueError, match="needs a name"):
        mcp_server.make_project("   ", dsn=path)
    with pytest.raises(ValueError, match="no project"):
        mcp_server.get_project(999999, dsn=path)


def test_reopening_a_studio_project_brings_its_scenes_references_renders_and_chat(
        tmp_db, monkeypatch):
    from src import projects, render_assets
    path = _project_db(tmp_db, monkeypatch)
    project = projects.create("Ghost can", "an energy drink ad", path, account_id=None)
    pid = project["id"]
    first = _scene_in(path, pid, "first", ["/refs/aaa.jpg", "/characters/sam/photo/face.jpg"],
                      reference_image="https://r2/still.png")
    second = _scene_in(path, pid, "second", ["/refs/aaa.jpg", "/refs/bbb.jpg"],
                       media_url="https://r2/clip.mp4")
    _scene_in(path, None, "elsewhere", ["/refs/zzz.jpg"])
    on_scene = render_assets.record(
        generation_id=1, tool="fal", model="ltx2.3", media_kind="video", prompt="p",
        media_url="https://r2/clip.mp4", concept_id=second, dsn=path, account_id=None)
    filed = render_assets.record(
        generation_id=2, tool="fal", model="flux2-pro", media_kind="image",
        prompt="made in chat", media_url="https://r2/f.png",
        metadata={"project_id": pid}, dsn=path, account_id=None)
    render_assets.record(generation_id=3, tool="fal", model="flux2-pro", media_kind="image",
                         prompt="no project", media_url="https://r2/other.png",
                         dsn=path, account_id=None)
    for i in range(15):
        projects.append_message(pid, "user" if i % 2 == 0 else "assistant",
                                f"turn {i:02d} " + ("x" * 2000 if i == 14 else ""),
                                path, account_id=None,
                                tool_calls={"brief": "b"} if i == 13 else None)
    out = mcp_server.get_project(pid, dsn=path)
    assert {s["title"] for s in out["scenes"]} == {"first", "second"}
    refs = {r["ref"]: r for r in out["references"]}
    assert list(refs) == ["/refs/aaa.jpg", "/characters/sam/photo/face.jpg", "/refs/bbb.jpg"]
    assert refs["/refs/aaa.jpg"]["scenes"] == [first, second]
    # no source page since the scout went (2026-10-14): the label is the file
    assert refs["/refs/bbb.jpg"]["page"] is None
    assert refs["/refs/bbb.jpg"]["label"] == "bbb.jpg"
    assert refs["/characters/sam/photo/face.jpg"]["kind"] == "character"
    assert {r["id"] for r in out["renders"]} == {f"gen:{on_scene['id']}", f"gen:{filed['id']}"}
    assert len(out["chat"]) == mcp_server.CHAT_PREVIEW and out["chat_has_more"] is True
    assert out["chat"][-1]["truncated"] is True
    assert len(out["chat"][-1]["content"]) == mcp_server.CHAT_EXCERPT
    assert out["chat"][-2]["carried"] == ["brief"]

    page = mcp_server.project_history(pid, limit=10, dsn=path)
    assert [t["content"][:7] for t in page["turns"]] == [f"turn {i:02d}" for i in range(5, 15)]
    assert page["has_more"] is True and len(page["turns"][-1]["content"]) > 2000
    older = mcp_server.project_history(pid, before=page["next_before"], limit=10, dsn=path)
    assert [t["content"][:7] for t in older["turns"]] == [f"turn {i:02d}" for i in range(5)]
    assert older["has_more"] is False


def test_another_accounts_project_cannot_be_read_or_filed_into(pg):
    from conftest import seed_two

    from src import accounts, projects
    preprod.init(pg)
    projects.init(pg)
    seed_two("mike@example.com", dsn=pg)
    with db.connect(pg) as conn:
        other = conn.execute("SELECT id FROM accounts WHERE slug = 'second-studio'").fetchone()["id"]
    mine = accounts.resolve_account(dsn=pg)
    theirs = projects.create("Theirs", "", pg, account_id=other)
    projects.append_message(theirs["id"], "user", "a secret", pg, account_id=other)
    assert mcp_server.list_project_cards(dsn=pg, account_id=mine)["projects"] == []
    for call in (lambda: mcp_server.get_project(theirs["id"], dsn=pg, account_id=mine),
                 lambda: mcp_server.project_history(theirs["id"], dsn=pg, account_id=mine),
                 lambda: mcp_server.run_image("a can", model="seedream4.5",
                                              project_id=theirs["id"], dsn=pg,
                                              account_id=mine)):
        with pytest.raises(ValueError, match="no project"):
            call()


def test_a_projects_references_can_be_used_again(monkeypatch):
    _stub_sources(monkeypatch, project_refs=["https://r2/old.jpg"])
    assert mcp_server.resolve_references(["https://r2/old.jpg", "sam/s1.jpg"], limit=4,
                                         who="X") == ["https://r2/old.jpg", "https://r2/s1.jpg"]
    with pytest.raises(ValueError, match="not a reference id"):
        mcp_server.resolve_references(["https://r2/never-used.jpg"], limit=4, who="X")


def test_renders_and_effects_are_filed_under_the_project_named(tmp_db, monkeypatch, signed):
    path = _project_db(tmp_db, monkeypatch)
    project = mcp_server.make_project("Ad", dsn=path)
    pid = project["id"]
    stills, clips, fx = _stub_still(monkeypatch), _stub_render(monkeypatch), _stub_effect(monkeypatch)
    quote, _ = _approved(mcp_server.run_image, prompt="a can", model="seedream4.5",
                         project_id=pid, dsn=path)
    assert quote["quote"]["project"] == {"id": pid, "title": "Ad"}
    assert stills[0]["project_id"] == pid
    with pytest.raises(ValueError, match="stale_content"):     # the yes was for that project
        mcp_server.run_image("a can", model="seedream4.5", dsn=path,
                             quote_token=quote["quote"]["quote_token"])
    _approved(mcp_server.run_video, prompt="a can", model="ltx2.3", seconds=6,
              project_id=pid, dsn=path)
    assert clips[0]["project_id"] == pid
    monkeypatch.setattr(mcp_server, "resolve_references", lambda refs, **kw: list(refs))
    _approved(mcp_server.run_effect, effect="remove-background", sources=["gen:1"],
              project_id=pid, dsn=path)
    assert fx[0]["project_id"] == pid
    with pytest.raises(ValueError, match="no project 999999"):
        mcp_server.run_image("a can", model="seedream4.5", project_id=999999, dsn=path)
    assert len(stills) == 1


def test_the_project_tools_are_on_every_server(tmp_db, monkeypatch):
    """The studio and -- since 2026-10-08, Mike's call -- both listed
    servers: a person's projects are their own rows. `save_chat` is the
    studio's only since 2026-10-11 (OpenAI refuses a tool that takes the
    conversation)."""
    tools = {"projects", "project", "project_chat", "create_project"}
    for kwargs in ({"surface": "studio"}, {"listed": True}, {"listed": "claude"}):
        names = {t.name for t in _tools(mcp_server.build_server(dsn=tmp_db, **kwargs))}
        assert tools <= names, kwargs
        assert ("save_chat" in names) == ("listed" not in kwargs), kwargs
    assert tools <= set(mcp_server.LISTED_TOOLS) & set(mcp_server.CLAUDE_LISTED_TOOLS)


def test_the_claude_listing_carries_nothing_that_renders(tmp_db, monkeypatch):
    """Anthropic's directory refuses AI media generation: no `approve`, no
    `job`, no spending door, whatever is injected; and no description
    points at a tool that is not there."""
    monkeypatch.setenv(mcp_server.ENGINE_ENV, "1")
    ok = lambda *a, **k: {}          # noqa: E731
    server = mcp_server.build_server(dsn=tmp_db, listed="claude", job_status=_job_status,
                                     approve_render=ok, approve_keyframes=ok,
                                     cancel_job=_cancel_job)
    tools = _tools(server)
    assert tuple(t.name for t in tools) == mcp_server.CLAUDE_LISTED_TOOLS
    # `job` is on this listing since the free edits (overnight PR 2): they start
    # jobs; nothing that spends or draws is, and no description names one
    for t in tools:
        text = t.description
        assert "`approve`" not in text and "`generate_image`" not in text, t.name
        assert "save_chat" not in text and "`renders`" not in text, t.name
    with pytest.raises(ValueError):
        mcp_server.build_server(dsn=tmp_db, listed="everyone")


def test_no_listing_describes_or_instructs_a_tool_it_does_not_have(tmp_db):
    """A description that says "call `renders`" on a server with no
    `renders` sends a stranger's assistant looking for a tool that is not
    there. Every tool name in backticks -- in a listing's descriptions and
    in what the listing says about itself -- is one that listing has."""
    import re
    known = set(mcp_server.TITLES)
    ok = lambda *a, **k: {}          # noqa: E731
    for kwargs, offered, about in (
            ({"listed": True}, mcp_server.LISTED_TOOLS, mcp_server.INSTRUCTIONS),
            ({"listed": "claude"}, mcp_server.CLAUDE_LISTED_TOOLS,
             mcp_server.CLAUDE_INSTRUCTIONS)):
        server = mcp_server.build_server(dsn=tmp_db, job_status=_job_status,
                                         approve_render=ok, approve_keyframes=ok, **kwargs)
        texts = {t.name: t.description for t in _tools(server)}
        assert tuple(texts) == offered
        for name, text in {**texts, "(instructions)": about}.items():
            named = set(re.findall(r"`([a-z_]+)`", text)) & known
            assert named <= set(offered), (kwargs, name, named - set(offered))


def test_adding_a_picture_is_a_write_that_reaches_the_web_and_spends_nothing():
    """`add_element` fetches an address a person gave it, so it says it
    reaches beyond this server; it draws nothing, so it is not marked as
    something that cannot be undone the way a spend is."""
    assert mcp_server.HINTS["add_element"] == {
        "read": False, "destructive": False, "idempotent": False, "open_world": True}
    for text in (mcp_server.DESCRIPTIONS["add_element"],
                 mcp_server.LISTED_DESCRIPTIONS["add_element"],
                 mcp_server.CLAUDE_DESCRIPTIONS["add_element"]):
        assert "no credits are spent" in text and "https" in text
        assert "SPENDS CREDITS" not in text
    assert "generate_image" not in mcp_server.CLAUDE_DESCRIPTIONS["add_element"]
    assert "SPENDS CREDITS" in mcp_server.LISTED_DESCRIPTIONS["generate_image"]
    assert "dollars" not in mcp_server.LISTED_DESCRIPTIONS["image_models"]


def test_save_chat_files_the_conversation_and_reopening_shows_it(tmp_db, monkeypatch):
    path = _project_db(tmp_db, monkeypatch)
    pid = mcp_server.make_project("Ghost can", dsn=path)["id"]
    turns = [{"role": "user", "content": "make it colder"},
             {"role": "assistant", "content": "Here is a colder still."}]
    out = mcp_server.save_project_chat(pid, turns, dsn=path)
    assert out["saved"] == 2 and out["title"] == "Ghost can" and "saved" in out["note"]
    again = mcp_server.save_project_chat(pid, turns, dsn=path)
    assert again["saved"] == 0 and "nothing new" in again["note"]
    chat = mcp_server.get_project(pid, dsn=path)["chat"]
    assert [(t["role"], t["content"], t["via"]) for t in chat] == [
        ("user", "make it colder", "mcp"), ("assistant", "Here is a colder still.", "mcp")]
    assert "carried" not in chat[0]
    page = mcp_server.project_history(pid, dsn=path)
    assert [t["via"] for t in page["turns"]] == ["mcp", "mcp"]
    with pytest.raises(ValueError, match="no turns"):
        mcp_server.save_project_chat(pid, [], dsn=path)
    with pytest.raises(ValueError, match="no project"):
        mcp_server.save_project_chat(999999, turns, dsn=path)


def test_save_chat_through_the_tool_on_the_studio_and_listed_servers(tmp_db, monkeypatch):
    import asyncio

    from mcp.server.mcpserver.exceptions import ToolError
    path = _project_db(tmp_db, monkeypatch)
    pid = mcp_server.make_project("Tool", dsn=path)["id"]
    server = mcp_server.build_server(dsn=path, surface="studio")
    out = _result(asyncio.run(server.call_tool("save_chat", {
        "project_id": pid, "turns": [{"role": "user", "content": "hello"}]})))
    assert out["saved"] == 1
    with pytest.raises(ToolError):
        asyncio.run(server.call_tool("save_chat", {
            "project_id": pid, "turns": [{"role": "system", "content": "x"}]}))
    # not on a listed server since 2026-10-11
    for listing in (True, "claude"):
        listed = mcp_server.build_server(dsn=path, listed=listing)
        with pytest.raises(ToolError):
            asyncio.run(listed.call_tool("save_chat", {
                "project_id": pid, "turns": [{"role": "assistant", "content": "hi back"}]}))
    assert [t["content"] for t in mcp_server.project_history(pid, dsn=path)["turns"]] == [
        "hello"]


def test_another_accounts_project_takes_no_chat(pg):
    from conftest import seed_two

    from src import accounts, projects
    preprod.init(pg)
    projects.init(pg)
    seed_two("mike@example.com", dsn=pg)
    with db.connect(pg) as conn:
        other = conn.execute("SELECT id FROM accounts WHERE slug = 'second-studio'").fetchone()["id"]
    mine = accounts.resolve_account(dsn=pg)
    theirs = projects.create("Theirs", "", pg, account_id=other)
    with pytest.raises(ValueError, match="no project"):
        mcp_server.save_project_chat(theirs["id"], [{"role": "user", "content": "x"}],
                                     dsn=pg, account_id=mine)
    assert projects.messages(theirs["id"], pg, account_id=other)["items"] == []


def test_a_long_chat_page_stops_before_it_is_too_big_to_carry(tmp_db, monkeypatch):
    from src import projects
    path = _project_db(tmp_db, monkeypatch)
    pid = mcp_server.make_project("Long", dsn=path)["id"]
    monkeypatch.setattr(mcp_server, "CHAT_PAGE_CHARS", 250)
    for i in range(6):
        projects.append_message(pid, "user", f"{i}" + "x" * 99, path, account_id=None)
    page = mcp_server.project_history(pid, limit=6, dsn=path)
    assert [t["content"][0] for t in page["turns"]] == ["4", "5"]
    assert page["has_more"] is True
    rest = mcp_server.project_history(pid, before=page["next_before"], limit=6, dsn=path)
    assert [t["content"][0] for t in rest["turns"]] == ["2", "3"] and rest["has_more"]


@pytest.mark.parametrize("kwargs", [{}, {"listed": True}, {"listed": "claude"},
                                    {"surface": "studio"}])
def test_every_surface_builds_under_python_3_11s_rules(tmp_db, monkeypatch, kwargs):
    """The Fly image runs Python 3.11, where pydantic refuses a
    `typing.TypedDict` in a tool's arguments -- and a server that fails to
    build leaves /mcp unmounted in production (2026-10-08, after #165) while
    CI on 3.12 stays green. So every surface is built here with pydantic
    answering as it does on 3.11, every optional tool registered."""
    import pydantic._internal._generate_schema as schema
    monkeypatch.setattr(schema, "_SUPPORTS_TYPEDDICT", False)
    monkeypatch.setenv(mcp_server.ENGINE_ENV, "1")
    server = mcp_server.build_server(
        dsn=tmp_db, job_status=lambda i, account_id=None: None,
        approve_render=lambda *a: {}, approve_keyframes=lambda *a: {}, **kwargs)
    names = {t.name for t in _tools(server)}
    assert ("save_chat" in names) == ("listed" not in kwargs)
    assert "job" in names          # on every surface since the free edits (overnight PR 2)


# ---------- element sheets from chat (2026-10-08) ----------
# Mike: "create an element sheet tool". The studio's own drawer
# (element_sheet.draw, what the Elements card's button runs), quoted first
# and drawn only after the yes, saved on the element where the studio keeps it.

def _sheet_world(monkeypatch, tmp_path, photos=("IMG_1.jpg",), has_key=True):
    from src import asset_shelf, element_sheet, media
    folder = tmp_path / "characters" / "maya"
    folder.mkdir(parents=True)
    for p in photos:
        (folder / p).write_bytes(b"\xff\xd8 jpeg")
    urls = [f"/characters/maya/photo/{p}" for p in photos]
    monkeypatch.setattr(asset_shelf, "catalogue", lambda dsn=None, account_id=None: [
        {"category": "character", "name": "Maya", "photos": urls, "text": "curly hair, mustard sweater"},
        {"category": "prop", "name": "Lamp", "photos": [], "text": ""}])
    monkeypatch.setattr(asset_shelf, "PHOTO_DIRS", {**asset_shelf.PHOTO_DIRS,
                                                    "character": tmp_path / "characters"})
    monkeypatch.setattr(asset_shelf, "resolve_photo",
                        lambda url, *a, **k: tmp_path / url.replace("/photo/", "/").lstrip("/"))
    monkeypatch.setattr(element_sheet, "available", lambda account_id=None: has_key)
    monkeypatch.setattr(element_sheet, "price_usd", lambda: 0.134)
    mirrored, drawn = [], []
    monkeypatch.setattr(media, "mirror", lambda *a, **k: mirrored.append(a))

    def fake_draw(kind, name, files, out_dir, **kw):
        drawn.append({"kind": kind, "name": name, "files": list(files), "out_dir": out_dir, **kw})
        out = out_dir / "sheet.jpg"
        out.write_bytes(b"sheet")
        return {"ok": True, "path": out, "generation_id": 41, "error": None}

    monkeypatch.setattr(element_sheet, "draw", fake_draw)
    return drawn, mirrored


def test_a_sheet_drawn_from_bucket_photos_leaves_no_folder_behind(monkeypatch, tmp_path, signed):
    """Through the operator's key the tool runs on the web server, which
    holds no element folders: the photos are fetched, and the sheet goes
    to the bucket without a folder holding only it being left on disk
    (the listing reads disk first)."""
    import requests

    from src import asset_shelf, element_sheet, media
    drawn, mirrored = _sheet_world(monkeypatch, tmp_path)
    _wallet(monkeypatch)
    folder = tmp_path / "characters" / "maya"
    for f in folder.iterdir():
        f.unlink()
    folder.rmdir()                                         # the photos are in the bucket only
    monkeypatch.setattr(asset_shelf, "resolve_photo", lambda url, *a, **k: None)
    monkeypatch.setattr(asset_shelf, "fetch_url",
                        lambda url, account_id=None: f"https://cdn.test{url}")

    class Reply:
        content = b"\xff\xd8 from the bucket"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda url, timeout=None: Reply())

    def draw(kind, name, files, out_dir, **kw):
        drawn.append({"read": [f.read_bytes() for f in files], "out_dir": out_dir})
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sheet.jpg").write_bytes(b"sheet")
        return {"ok": True, "path": out_dir / "sheet.jpg", "generation_id": 41, "error": None}

    monkeypatch.setattr(element_sheet, "draw", draw)
    monkeypatch.setattr(media, "mirror",
                        lambda path, key, *a, **k: mirrored.append((path.read_bytes(), key)))
    _, out = _approved(mcp_server.run_element_sheet, kind="character", name="Maya",
                       account_id=1)
    assert out["ok"] is True and out["sheet"].endswith("/sheet.jpg")
    assert drawn[-1]["read"] == [Reply.content]
    assert drawn[-1]["out_dir"] != folder and not folder.exists()
    assert mirrored == [(b"sheet", "characters/maya/sheet.jpg")]


def test_a_sheet_is_quoted_before_anything_is_drawn(monkeypatch, tmp_path, signed):
    from src import ledger
    drawn, _ = _sheet_world(monkeypatch, tmp_path)
    _wallet(monkeypatch)
    q = mcp_server.run_element_sheet("character", "maya", account_id=1)
    assert q["needs_approval"] and q["ok"] is False and drawn == []
    assert q["quote"]["usd"] == 0.134 and q["quote"]["replaces_sheet"] is False
    assert q["quote"]["credits"] == ledger.charge_credits(0.134) == 33
    assert q["quote"]["element"] == {"kind": "character", "name": "Maya"}
    with pytest.raises(ValueError, match="wrong_render"):       # not a token for this tool
        mcp_server.run_image("a can", model="seedream4.5", account_id=1,
                             quote_token=q["quote"]["quote_token"])
    assert drawn == []


def test_an_approved_sheet_is_drawn_from_the_real_photos_and_saved(monkeypatch, tmp_path, signed):
    drawn, mirrored = _sheet_world(monkeypatch, tmp_path, photos=("IMG_1.jpg", "sheet.jpg"))
    _wallet(monkeypatch)
    q, out = _approved(mcp_server.run_element_sheet, kind="character", name="Maya",
                       account_id=1)
    assert out["ok"] is True and out["quote"]["replaces_sheet"] is True
    # the still adapter holds it, at the signed price
    assert drawn[0]["quote"].provider == "nano" and drawn[0]["quote"].credits == 33
    assert [f.name for f in drawn[0]["files"]] == ["IMG_1.jpg"]    # never grounds on the old sheet
    assert drawn[0]["out_dir"] == tmp_path / "characters" / "maya"
    assert drawn[0]["notes"] == "curly hair, mustard sweater"
    assert mirrored and mirrored[0][1] == "characters/maya/sheet.jpg"
    assert out["sheet"].endswith("sheet.jpg") and out["generation_id"] == 41


@pytest.mark.parametrize("kind, name, match", [
    ("creature", "Maya", "kind must be one of"),
    ("character", "Nobody", "no character named"),
    ("prop", "Lamp", "no photos"),
])
def test_sheet_refusals_happen_before_any_spend(monkeypatch, tmp_path, kind, name, match):
    drawn, _ = _sheet_world(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match=match):
        mcp_server.run_element_sheet(kind, name, quote_token="phq.a.b", account_id=1)
    assert drawn == []


def test_no_image_key_is_a_refusal_not_a_retry(monkeypatch, tmp_path):
    drawn, _ = _sheet_world(monkeypatch, tmp_path, has_key=False)
    with pytest.raises(mcp_server.Refused):
        mcp_server.run_element_sheet("character", "Maya", account_id=1)
    assert drawn == []


def test_a_failed_draw_comes_back_as_ok_false(monkeypatch, tmp_path, signed):
    from src import element_sheet
    _sheet_world(monkeypatch, tmp_path)
    _wallet(monkeypatch)
    monkeypatch.setattr(element_sheet, "draw", lambda *a, **k: {
        "ok": False, "path": None, "generation_id": None, "error": "the sheet did not render"})
    _, out = _approved(mcp_server.run_element_sheet, kind="character", name="Maya",
                       account_id=1)
    assert out["ok"] is False and "did not render" in out["error"]


def test_element_sheet_is_on_the_studio_surface_only_behind_the_approval(tmp_db, monkeypatch):
    monkeypatch.delenv(mcp_server.ENGINE_ENV, raising=False)
    studio = {t.name for t in _tools(mcp_server.build_server(dsn=tmp_db, surface="studio"))}
    assert "element_sheet" in studio              # no engine flag needed: the approval gates it


# ---------- out of credits points at pricing (2026-10-11) ----------

def test_a_short_balance_refusal_carries_the_pricing_link(monkeypatch):
    """Inside Claude the refusal IS the upgrade prompt, so it names where to
    go instead of a bare 'top up in the studio'."""
    monkeypatch.delenv(mcp_server.PRICING_URL_ENV, raising=False)
    _wallet(monkeypatch, balance=1)
    stop, approved, price = mcp_server.approval_gate(
        5.0, "", tool="generate_image", args={}, what="This image",
        account_id=7, dsn=None)
    assert approved is None and stop["refused"] == "insufficient_credits"
    assert stop["upgrade_url"] == mcp_server.DEFAULT_PRICING_URL
    assert mcp_server.DEFAULT_PRICING_URL in stop["note"]


def test_the_pricing_link_can_be_pointed_elsewhere(monkeypatch):
    monkeypatch.setenv(mcp_server.PRICING_URL_ENV, "https://studio.example.com/pricing")
    assert mcp_server.pricing_url() == "https://studio.example.com/pricing"
