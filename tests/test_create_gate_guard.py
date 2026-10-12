"""
conftest's `create_gate_reads_its_own_schema`: the Create gate is never
answered from the throwaway's shared schema.

`charge.create_refusal_code` fails open on a read error, so a test that
asks it about an account with no database of its own gets whatever the
public schema holds on that machine -- allowed on a fresh CI Postgres, 402
on a laptop that has run the suite before. What each test guards:

- an unstubbed ask about a real account id fails by name, from the route
  and from the MCP tools' wrapper alike
- stubbing the function the code path calls is one way through
- a database of the test's own is the other, and there the REAL function
  answers (the guard holds nothing open)
- the unowned pool is never read, and a dead address still fails open
"""
import json

import pytest
from conftest import TEST_DSN, CreateGateInTest
from fastapi.testclient import TestClient

from src import accounts, charge, db, ledger


@pytest.fixture
def as_account(monkeypatch):
    """A route client acting as a made-up account id, the way a route test
    that is about something else sets one."""
    from app import auth, jobs
    from app.main import app
    started = []
    monkeypatch.setattr(jobs, "start", lambda *a, **k: started.append(a) or {"id": 1})
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@e.com"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"id": 42, "slug": "zeropage"})
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    client = TestClient(app, headers={"X-ZPF-Model-Connection": "1"})
    client.started = started
    yield client
    app.dependency_overrides[auth.current_account_id] = lambda: None


TURN = {"conversation": json.dumps({"messages": [{"role": "user", "content": "hi"}]})}


def test_an_unstubbed_ask_about_an_account_fails_by_name():
    assert db.resolve_dsn(None) == TEST_DSN        # the suite's default: the shared schema
    with pytest.raises(CreateGateInTest, match="charge.create_refusal_code"):
        charge.create_refusal_code(42)
    # the MCP tools' wrapper calls the same function by name
    with pytest.raises(CreateGateInTest, match="charge.create_refusal for src/mcp_server"):
        charge.create_refusal(42)


def test_a_route_that_asks_unstubbed_fails_instead_of_answering(as_account):
    """The bug's own shape: before the guard this was 200 on a fresh
    Postgres and 402 on a machine whose public schema held the ledger."""
    with pytest.raises(CreateGateInTest, match="account 42"):
        as_account.post("/api/creative-guide", data=TURN)
    assert as_account.started == []


def test_the_editors_twin_of_the_gate_is_covered_too(as_account):
    with pytest.raises(CreateGateInTest):
        as_account.post("/api/cut/index", json={})


def test_stubbing_the_wrapper_does_not_cover_a_route(as_account, monkeypatch):
    """tests/test_result_refs.py's miss (2026-10-11): the routes ask
    create_refusal_code; create_refusal is only the MCP tools' wrapper."""
    monkeypatch.setattr(charge, "create_refusal", lambda *a, **k: None)
    with pytest.raises(CreateGateInTest):
        as_account.post("/api/creative-guide", data=TURN)


def test_stubbing_the_function_the_route_calls_is_one_way_through(as_account, monkeypatch):
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    assert as_account.post("/api/creative-guide", data=TURN).status_code == 200
    assert len(as_account.started) == 1


def test_stubbing_the_wrapper_covers_the_mcp_path(monkeypatch):
    monkeypatch.setattr(charge, "create_refusal", lambda account_id, dsn=None: None)
    assert charge.create_refusal(42) is None


def _seeded(pg):
    accounts.seed("mike@example.com", dsn=pg)
    ledger.init(pg)
    with db.connect(pg) as conn:
        return int(conn.execute(
            "SELECT id FROM accounts WHERE slug = 'zeropage'").fetchone()["id"])


def test_an_explicit_schema_is_answered_by_the_real_gate(pg):
    account_id = _seeded(pg)
    assert charge.create_refusal_code(account_id, dsn=pg) == (
        charge.NO_PLAN_CODE, charge.CREATE_REFUSAL)
    assert charge.create_refusal(account_id, dsn=pg) == charge.CREATE_REFUSAL
    ledger.grant(account_id, 1000, "purchase", dsn=pg)
    assert charge.create_refusal_code(account_id, dsn=pg) is None


def test_a_route_pointed_at_its_own_schema_is_answered_by_the_real_gate(
        pg, as_account, monkeypatch):
    """The other way through, and proof the guard holds nothing open: the
    same route refuses the seeded account until it has credit."""
    from app import auth
    from app.main import app
    monkeypatch.setenv("DATABASE_URL", pg)
    account_id = _seeded(pg)
    app.dependency_overrides[auth.current_account_id] = lambda: account_id
    res = as_account.post("/api/creative-guide", data=TURN)
    assert res.status_code == 402
    assert res.json()["error"]["code"] == charge.NO_PLAN_CODE
    assert as_account.started == []
    ledger.grant(account_id, 1000, "purchase", dsn=pg)
    assert as_account.post("/api/creative-guide", data=TURN).status_code == 200


def test_the_unowned_pool_is_never_read():
    assert charge.create_refusal_code(None) is None
    assert charge.create_refusal(None) is None


def test_a_dead_address_still_fails_open(capsys):
    """Production's behaviour, untouched: an unreadable gate allows. The
    guard is about WHICH database answers, not about what a failed read
    means."""
    assert charge.create_refusal_code(42, dsn="postgresql://127.0.0.1:1/nowhere") is None
    assert "create gate unreadable for account 42" in capsys.readouterr().err
