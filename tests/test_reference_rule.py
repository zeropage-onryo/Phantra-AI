"""
A concept with no reference images is a no-go.

Mike's rule, 2026-09-08, and a deliberate exception to the standing
convention that grounding shapes and never gates ("a crawl is an
enhancement, never a dependency"). What earned the exception: on the
night of 2026-09-07, 9 of 29 banked sparks had a photograph behind them,
and the other 20 still produced scenes -- written from words alone --
because nothing downstream ever asked. The convention protects a night
from a dead crawl; it was also keeping the crawl dead.

`orchestrator.planner` REFUSES a direction with no photographs -- the
sparks.txt rotation, a typed spark, an agent's `generate` -- and stops the
run with the reason. (The scout's bank, which passed over a bare spark,
went with the scout on 2026-10-14.)

The suite runs with the rule OFF (see tests/conftest.py); every test
here turns it on explicitly.
"""
import pytest

from src import orchestrator, preprod


@pytest.fixture
def tmp_db(pg, monkeypatch):
    path = pg
    monkeypatch.setenv("DATABASE_URL", path)
    return path


@pytest.fixture
def required(monkeypatch):
    monkeypatch.setenv("PHANTRA_REQUIRE_REFS", "1")


# ---------- the switch ----------

def test_the_rule_is_on_by_default(monkeypatch):
    monkeypatch.delenv("PHANTRA_REQUIRE_REFS", raising=False)
    assert preprod.refs_required() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "OFF"])
def test_and_can_be_turned_off_for_one_run(monkeypatch, value):
    monkeypatch.setenv("PHANTRA_REQUIRE_REFS", value)
    assert preprod.refs_required() is False


# ---------- what the graph will generate from ----------

def test_a_run_with_no_photos_holds_before_it_generates(tmp_db, required):
    from src import autonomy
    autonomy.init(tmp_db)
    out = orchestrator.planner({"spark": "a typed idea"})
    assert out["error"] == orchestrator.NO_REFS_REASON
    assert orchestrator.route_after_planner(out) == "hold"


def test_a_run_that_has_photos_proceeds(tmp_db, required):
    from src import autonomy
    autonomy.init(tmp_db)
    out = orchestrator.planner({"reference_photos": ["/refs/abc123.jpg"]})
    assert not out.get("error")
    assert orchestrator.route_after_planner(out) == "plan"


def test_with_the_rule_off_a_bare_run_proceeds(tmp_db, monkeypatch):
    from src import autonomy
    monkeypatch.setenv("PHANTRA_REQUIRE_REFS", "0")
    autonomy.init(tmp_db)
    out = orchestrator.planner({"spark": "a typed idea"})
    assert not out.get("error")
    assert orchestrator.route_after_planner(out) == "plan"


def test_the_refusal_is_wired_into_the_compiled_graph():
    """A router nothing routes through is not a gate."""
    import inspect
    source = inspect.getsource(orchestrator.build_graph
                               if hasattr(orchestrator, "build_graph")
                               else orchestrator)
    assert "route_after_planner" in source
    assert '"plan": "ground_entities"' in source
