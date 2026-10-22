"""The 2026-10-20 plan rework (Mike's calls).

- Every plan renders every model; the plan's tier refuses nothing.
- The MCP connector comes with every workspace (2026-10-21, Mike's call;
  it was Pro and Max only from 2026-10-20): a signed-in caller on no plan
  reaches the tools, and nothing at the door reads a plan.
- Each plan's storage fits under the ceiling its own numbers can carry.
- The plan KEYS and Stripe price envs did not move ("don't rename the
  price ids"); only the names did.
"""
import asyncio
import json

from app import mcp_mount
from src import accounts, pricing, providers


def test_the_keys_and_price_envs_are_the_old_ones_and_only_the_names_moved():
    assert list(pricing.PLANS) == ["starter", "creator", "studio"]
    assert [p.name for p in pricing.PLANS.values()] == ["Standard", "Pro", "Max"]
    assert [p.price_env for p in pricing.PLANS.values()] == [
        "STRIPE_PRICE_STARTER", "STRIPE_PRICE_CREATOR", "STRIPE_PRICE_STUDIO"]


def test_every_plan_carries_storage_its_numbers_can_pay_for():
    sizes = [p.storage_gb for p in pricing.PLANS.values()]
    assert sizes == sorted(sizes) and sizes[0] > pricing.FREE_STORAGE_GB > 0
    for plan in pricing.PLANS.values():
        assert 0 < plan.storage_gb <= pricing.storage_ceiling_gb(plan), plan.key


def test_the_catalog_publishes_storage_and_no_connector_flag():
    catalog = pricing.public_catalog()
    assert catalog["trial"]["storage_gb"] == pricing.FREE_STORAGE_GB
    assert [p["storage_gb"] for p in catalog["plans"]] == [25, 70, 200]
    # the connector is not a plan feature any more, so no plan says so
    assert all("mcp" not in p for p in catalog["plans"])


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


def test_a_caller_on_no_plan_goes_through_and_no_plan_is_read(monkeypatch):
    # the smoke test of 2026-10-21: a trial workspace was refused 403
    # plan_required at `initialize`, so a reviewer saw no tools at all
    def no_reads(*_a, **_k):
        raise AssertionError("the connector's door must not read a plan")
    monkeypatch.setattr(accounts, "plan_of", no_reads)
    monkeypatch.setattr(accounts, "is_credit_exempt", no_reads)
    inner, reached = _inner()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (7, "ok"),
                            stamps=mcp_mount.UseStamps())
    status, body = _drive(app, "Bearer someones-jwt")
    assert status == 200 and reached == [True]
    assert b"plan_required" not in body


def test_the_operator_key_still_goes_through():
    inner, reached = _inner()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "invalid_token"))
    assert _drive(app, "Bearer static")[0] == 200 and reached == [True]


def test_a_sign_in_with_no_workspace_is_still_refused():
    inner, reached = _inner()
    app = mcp_mount.guarded(inner, "static", resolve=lambda t: (None, "no_account"),
                            stamps=mcp_mount.UseStamps())
    status, body = _drive(app, "Bearer someones-jwt")
    assert status == 403 and reached == []
    assert json.loads(body)["error"] == "no_account"
