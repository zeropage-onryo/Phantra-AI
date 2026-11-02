"""The eval golden set and its runs are the operator's (QA 2026-11-02, E2).

`eval_golden` and `eval_runs` are SHARED tables: one set for the whole
product, graded on the operator's Gemini key. Every /api/evals route took
any signed-in account, so a customer could list the set, add to it,
delete from it (8 rows -> 7 in the QA) and start a run billed to the
operator. Now only an owner of the house account passes `eval_operator`;
everybody else gets 403 before the store or a model is touched.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import api, whats_new_routes
from app.main import app

client = TestClient(app)

DOORS = [
    ("get", "/api/evals/golden", None),
    ("post", "/api/evals/golden", {"query": "q", "relevant": ["r"]}),
    ("delete", "/api/evals/golden/1", None),
    ("get", "/api/evals/runs", None),
    ("get", "/api/evals/runs/1", None),
    ("post", "/api/evals/run", {}),
]


def _call(method, path, body):
    return getattr(client, method)(path, **({"json": body} if body is not None else {}))


@pytest.fixture
def untouched_store(monkeypatch):
    monkeypatch.setattr(api.auth, "current_user",
                        lambda request: {"id": 1, "email": "m@example.com"})
    calls = []
    for name in ("list_golden", "add_golden", "delete_golden", "list_runs", "get_run"):
        monkeypatch.setattr(api.evalstore, name,
                            lambda *a, _n=name, **k: calls.append(_n) or [])
    return calls


@pytest.mark.parametrize("method,path,body", DOORS)
def test_a_customer_is_refused(method, path, body, untouched_store, monkeypatch):
    monkeypatch.setattr(whats_new_routes, "_operator", lambda request, account_id: None)
    app.dependency_overrides[api.auth.current_account_id] = lambda: 7
    try:
        r = _call(method, path, body)
    finally:
        app.dependency_overrides[api.auth.current_account_id] = lambda: None
    assert r.status_code == 403
    assert untouched_store == []


def test_no_account_is_refused(untouched_store):
    # conftest's default override is the unowned pool (None)
    assert client.get("/api/evals/golden").status_code == 403
    assert untouched_store == []


def test_the_house_owner_passes(untouched_store, monkeypatch):
    monkeypatch.setattr(whats_new_routes, "_operator", lambda request, account_id: 1)
    app.dependency_overrides[api.auth.current_account_id] = lambda: 1
    try:
        r = client.get("/api/evals/golden")
    finally:
        app.dependency_overrides[api.auth.current_account_id] = lambda: None
    assert r.status_code == 200
    assert untouched_store == ["list_golden"]
