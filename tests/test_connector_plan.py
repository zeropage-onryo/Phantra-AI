"""The 2026-10-20 plan rework (Mike's calls).

- Every plan renders every model; the plan's tier refuses nothing.
- The MCP connector is a Pro and Max feature: a signed-in caller on no
  plan, or on Standard, is refused 403 plan_required; the operator's key
  and a credit-exempt account are not.
- Each plan's storage fits under the ceiling its own numbers can carry.
- The plan KEYS and Stripe price envs did not move ("don't rename the
  price ids"); only the names did.
"""
import asyncio
import json

import pytest

from app import mcp_auth, mcp_mount
from src import accounts, pricing, providers

# the real gate, captured before conftest's autouse fixture replaces it
REAL_CONNECTOR_ALLOWED = mcp_auth.connector_allowed


def test_the_keys_and_price_envs_are_the_old_ones_and_only_the_names_moved():
    assert list(pricing.PLANS) == ["starter", "creator", "studio"]
    assert [p.name for p in pricing.PLANS.values()] == ["Standard", "Pro", "Max"]
    assert [p.price_env for p in pricing.PLANS.values()] == [
        "STRIPE_PRICE_STARTER", "STRIPE_PRICE_CREATOR", "STRIPE_PRICE_STUDIO"]


def test_the_connector_comes_with_pro_and_max_only():
    assert pricing.MCP_PLANS == ("creator", "studio")
    assert "Pro and Max" in mcp_auth.connector_plan_detail()


def test_every_plan_carries_storage_its_numbers_can_pay_for():
    sizes = [p.storage_gb for p in pricing.PLANS.values()]
    assert sizes == sorted(sizes) and sizes[0] > pricing.FREE_STORAGE_GB > 0
    for plan in pricing.PLANS.values():
        assert 0 < plan.storage_gb <= pricing.storage_ceiling_gb(plan), plan.key


def test_the_catalog_publishes_storage_and_the_connector():
    catalog = pricing.public_catalog()
    assert catalog["trial"]["storage_gb"] == pricing.FREE_STORAGE_GB
    assert [(p["storage_gb"], p["mcp"]) for p in catalog["plans"]] == [
        (25, False), (70, True), (200, True)]


def test_no_tier_refuses_any_catalogued_model(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "x")
    shot = {"n": 1, "tool": "LTX", "prompt": "A man laces his boots.", "refs": ["/refs/a.jpg"]}
    for provider, model, _name, _blurb in pricing.CATALOG_MODELS:
        for tier in providers.TIERS:
            assert pricing.estimate(account_id=None, shot=shot, provider=provider,
                                    model=model, tier=tier).model == model


# --- the gate on the mount ---------------------------------------------------

def _drive(app, header):
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(app({"type": "http", "headers": [(b"authorization", header.encode())],
                     "method": "POST", "path": "/"}, receive, send))
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return sent[0]["status"], body


def _inner():
    reached = []

    async def inner(scope, receive, send):
        reached.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
    return inner, reached


def test_a_caller_off_pro_and_max_is_refused_with_the_upgrade_line():
    inner, reached = _inner()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"),
                            plan_gate=lambda a: False, stamps=mcp_mount.UseStamps())
    status, body = _drive(app, "Bearer someones-jwt")
    assert status == 403 and reached == []
    out = json.loads(body)
    assert out["error"] == "plan_required" and "Pro and Max" in out["detail"]


def test_a_caller_on_pro_or_max_goes_through():
    inner, reached = _inner()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"),
                            plan_gate=lambda a: a == 7, stamps=mcp_mount.UseStamps())
    assert _drive(app, "Bearer someones-jwt")[0] == 200 and reached == [True]


def test_the_operator_key_is_never_asked_for_a_plan():
    inner, reached = _inner()

    def boom(_a):
        raise AssertionError("the operator's key must not reach the plan gate")
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "invalid_token"),
                            plan_gate=boom)
    assert _drive(app, "Bearer static")[0] == 200 and reached == [True]


def test_a_gate_that_raises_is_a_refusal():
    inner, reached = _inner()

    def broken(_a):
        raise RuntimeError("db down")
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"),
                            plan_gate=broken, stamps=mcp_mount.UseStamps())
    assert _drive(app, "Bearer someones-jwt")[0] == 403 and reached == []


def test_connector_allowed_reads_the_plan_and_the_exemption(pg):
    accounts.init(dsn=pg)
    acct_id = accounts.upsert_account("planned", "Planned", dsn=pg)
    assert REAL_CONNECTOR_ALLOWED(acct_id, dsn=pg) is False          # no plan
    accounts.set_plan(acct_id, "starter", dsn=pg)
    assert REAL_CONNECTOR_ALLOWED(acct_id, dsn=pg) is False          # Standard
    for key in ("creator", "studio"):
        accounts.set_plan(acct_id, key, dsn=pg)
        assert REAL_CONNECTOR_ALLOWED(acct_id, dsn=pg) is True
    accounts.set_plan(acct_id, None, dsn=pg)
    accounts.set_credit_exempt("planned", True, dsn=pg)
    assert REAL_CONNECTOR_ALLOWED(acct_id, dsn=pg) is True           # the operator's own
    assert REAL_CONNECTOR_ALLOWED(None, dsn=pg) is False


@pytest.mark.parametrize("answer", [True, False])
def test_the_default_gate_remembers_an_answer(monkeypatch, answer):
    calls = []
    monkeypatch.setattr(mcp_auth, "connector_allowed",
                        lambda a, dsn=None: calls.append(a) or answer)
    gate = mcp_mount._cached_plan_gate(ttl=60)
    assert gate(3) is answer and gate(3) is answer
    assert calls == [3]
