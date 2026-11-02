"""The Guide route on a priced Claude brain: hold before the job, settle to what
Claude cost inside it, release on a failure, 402 on an empty balance.
Nothing reaches a network or a model."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import charge, claude_client, creative_guide, gemini_utils, ledger, preprod, projects, scene_chain, text_charge

GUARDED = {"x-phantra-model-connection": "1"}
client = TestClient(app)


class FakeTurn:
    def __init__(self):
        self.settled, self.released = None, None

    def settle(self, tally):
        self.settled = (tally.calls, round(tally.usd, 4))
        return 7

    def release(self, reason):
        self.released = reason
        return 0


@pytest.fixture
def route(monkeypatch, pg):
    preprod.init(pg)
    projects.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv(gemini_utils.CLAUDE_BRAINS_ENV, "1")
    monkeypatch.setenv(claude_client.KEY_ENV, "sk-test")
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(auth, "current_account", lambda request, user=None: {"slug": "phantra"})
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)

    async def refs(form, **kwargs):
        return [], [], []

    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    box = {"turn": FakeTurn(), "brains": []}

    def begin(account_id, brain, **kw):
        box["brains"].append(brain)
        return box["turn"] if gemini_utils.is_priced(brain) else None

    monkeypatch.setattr(text_charge, "begin", begin)

    def ask(brain, respond):
        monkeypatch.setattr(creative_guide, "respond", respond)
        data = {"conversation": json.dumps({"messages": [{"role": "user", "content": "hi"}]}),
                "guide_provider": "gemini", "brain": brain}
        r = client.post("/api/creative-guide", headers=GUARDED, data=data)
        if r.status_code != 200:
            return r, None
        job_id = r.json()["job_id"]
        for _ in range(300):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in ("done", "failed"):
                break
            time.sleep(.01)
        return r, job

    box["ask"] = ask
    return box


def one_claude_call(conversation, **kw):
    claude_client._tally.get().add("claude-sonnet-5-5", {"prompt": 1000, "output": 100, "cached": 0})
    return {"message": "ok", "choices": [], "brief": ""}


def test_a_priced_turn_settles_to_what_claude_cost_and_says_so(route):
    _, job = route["ask"]("claude-sonnet", one_claude_call)
    assert job["status"] == "done" and job["spent"] == 7
    calls, usd = route["turn"].settled
    assert calls == 1 and usd > 0
    assert route["turn"].released is None


def test_a_failed_priced_turn_is_released_not_charged(route):
    def boom(conversation, **kw):
        raise RuntimeError("model fell over")

    _, job = route["ask"]("claude-sonnet", boom)
    assert job["status"] == "failed"
    assert route["turn"].released and route["turn"].settled is None


def test_a_free_brain_takes_no_hold_and_reports_no_spend(route):
    _, job = route["ask"]("fast", lambda c, **kw: {"message": "ok", "choices": [], "brief": ""})
    assert job["status"] == "done" and "spent" not in job
    assert route["turn"].settled is None and route["turn"].released is None


def test_an_unavailable_claude_brain_runs_on_the_default_for_free(route, monkeypatch):
    monkeypatch.delenv(claude_client.KEY_ENV)
    _, job = route["ask"]("claude-opus", lambda c, **kw: {"message": "ok", "choices": [], "brief": ""})
    assert job["status"] == "done" and route["brains"][-1] == creative_guide.DEFAULT_BRAIN
    assert route["turn"].settled is None


def test_an_empty_balance_is_a_402_before_any_job(route, monkeypatch):
    def broke(account_id, brain, **kw):
        raise ledger.InsufficientCredit(account_id, 40, 3)

    monkeypatch.setattr(text_charge, "begin", broke)
    r, job = route["ask"]("claude-sonnet", one_claude_call)
    assert r.status_code == 402 and job is None
