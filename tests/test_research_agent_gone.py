"""The research agent after the board went (2026-10-11).

Step 3 of docs/tasks/task-higgsfield-shape.md removed the idea board's MCP
surface, which is what `src/research_agent.py` drove. The agent is not
deleted yet -- that is step 9, and Mike's call -- so until then it has to
say no plainly, in the one place every caller asks, and the graph that can
call it has to carry on. Nothing here reaches a model or spawns a server.
"""
from src import orchestrator, research_agent


# guards: research_agent.ready -- the refusal, with the reason
def test_the_agent_says_it_cannot_run_and_why(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")     # a key does not change it
    ok, reason = research_agent.ready()
    assert ok is False
    assert reason == research_agent.BOARD_GONE
    assert "2026-10-11" in reason and "task-higgsfield-shape" in reason


# guards: research_agent.run -- a refusal is a note, never a raise or a spend
def test_a_pass_is_a_note_and_spawns_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(research_agent, "STAMP_DIR", tmp_path / ".research")
    monkeypatch.setattr(research_agent, "_research",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("spawned")))
    out = research_agent.run("zeropage", force=True)
    assert out == {"ok": False, "banked": 0, "images": 0, "note": research_agent.BOARD_GONE}
    # refused before the once-a-day stamp: nothing was attempted, so
    # nothing is marked as attempted
    assert not (tmp_path / ".research").exists()


# guards: orchestrator.research -- the graph's node carries on without it
def test_the_graphs_research_node_carries_on(monkeypatch):
    state = {"research": True, "scout": True, "brand": "zeropage"}
    assert orchestrator.research(state) == {"research_note": research_agent.BOARD_GONE}
    assert orchestrator.research({"research": False, "scout": True}) == {}


# guards: research_agent.main -- by hand it prints the reason and exits 0
def test_the_cli_prints_the_reason(capsys):
    assert research_agent.main(["--brand", "zeropage", "--force"]) == 0
    assert research_agent.BOARD_GONE in capsys.readouterr().out
