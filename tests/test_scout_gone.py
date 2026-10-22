"""The research scout, the research agent and the spark bank are gone
(2026-10-14, Mike's call; step 9 of docs/tasks/task-higgsfield-shape.md).

What is left to guard is that nothing brings them back by the side door:
the graph starts at its planner, the run takes no scout switch, and no
API route or connector function reaches a bank that does not exist.
"""
import inspect
from pathlib import Path

import pytest

import src
from src import mcp_server, orchestrator

ROOT = Path(src.__file__).resolve().parent.parent


# Checked as files rather than imports: an editable install can resolve
# `src.<name>` to another checkout of this repo on the same machine.
@pytest.mark.parametrize("path", ["src/scout.py", "src/research_agent.py", "src/refgen.py",
                                  "src/reference_hunt.py", "ops/bank.py",
                                  "prompts/scout_sources.txt"])
def test_the_modules_are_gone(path):
    assert not (ROOT / path).exists()


def test_the_graph_starts_at_the_planner():
    nodes = set(orchestrator.GRAPH.get_graph().nodes)
    assert "planner" in nodes
    assert not {"scout", "research"} & nodes


def test_a_run_takes_no_scout_switch():
    params = inspect.signature(orchestrator.run).parameters
    assert not {"scout", "research", "scout_finding_id"} & set(params)
    assert "finding_id" not in inspect.signature(mcp_server.run_graph).parameters


def test_the_spark_bank_functions_are_gone():
    for name in ("bank_spark", "next_spark", "list_sparks", "bank_reference",
                 "spark_images", "run_research", "resolve_finding", "LANES"):
        assert not hasattr(mcp_server, name), name


def test_no_route_reaches_the_scout():
    from app.main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert not any(p.startswith("/api/scout") for p in paths)
