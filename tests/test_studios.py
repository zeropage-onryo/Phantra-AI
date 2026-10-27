"""The Ad Studio (2026-10-26, src/studios.py + src/addons.py).

A studio is a config over the one engine, sold as a flat add-on beside a
plan. What these pin:

- the config is honest: every format's skill is on the shelf, every shape is
  one the composer offers, every length one its tool accepts;
- a pick is cleaned, never trusted, and reaches the brain only for an
  account with the add-on -- without it the turn is the plain composer's;
- the page is open to everyone and never shows a prompt note;
- an add-on's Stripe events NEVER reach a plan branch: cancelling the Ad
  Studio must not expire a plan's credits or clear `accounts.plan` (the bug
  the spec found in billing.handle_event before any of this was built);
- the operator's grant is idempotent and will not undo a Stripe payment.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import (
    accounts,
    addons,
    assistant_store,
    billing,
    charge,
    creative_guide,
    db,
    ledger,
    pricing,
    scene_chain,
    skills,
    studios,
)
from tests.test_billing import WHSEC, checkout_paid, event, invoice_paid, post

client = TestClient(app)


# --- the config --------------------------------------------------------------

def test_the_ad_studio_config_has_no_problems():
    assert studios.problems("ads") == []


def test_every_format_rides_on_a_skill_that_exists():
    studio = studios.get("ads")
    assert studio["title"] == "Ad Studio"
    names = set(skills.names())
    for f in studio["formats"]:
        assert f["skill"] in names, f["id"]


def test_an_unknown_studio_is_none_and_problems_say_so():
    assert studios.get("fashion") is None
    assert studios.get("../ads") is None
    assert studios.problems("nope")


# --- the pick ----------------------------------------------------------------

def test_a_pick_is_cleaned_not_trusted():
    pick = studios.clean_pick({
        "id": "ads", "format": "ugc", "aspect": "16:9", "seconds": 99,
        "intake": {"platform": "tiktok", "audience": "  new   runners ", "tone": "angry",
                   "made_up": "x"}})
    # UGC is vertical only and 8-20s: both go back to the row's default
    assert pick == {"id": "ads", "format": "ugc", "aspect": "9:16", "seconds": 15,
                    "intake": {"platform": "tiktok", "audience": "new runners"}}


def test_a_pick_takes_json_and_refuses_what_it_cannot_read():
    raw = json.dumps({"id": "ads", "format": "tv_spot", "aspect": "9:16", "seconds": 20})
    assert studios.clean_pick(raw)["aspect"] == "9:16"
    assert studios.clean_pick(raw)["seconds"] == 20
    for bad in (None, "", "{", "[]", {"id": "ads"}, {"id": "ads", "format": "nope"},
                {"id": "films", "format": "ugc"}, {"id": "ads", "format": "ugc", "seconds": True}):
        got = studios.clean_pick(bad)
        assert got is None or got["seconds"] == 15, bad


def test_a_still_has_no_length():
    pick = studios.clean_pick({"id": "ads", "format": "product_still", "seconds": 10})
    assert pick["seconds"] is None and pick["aspect"] == "4:5"


def test_a_long_text_answer_is_cut_to_its_own_cap():
    pick = studios.clean_pick({"id": "ads", "format": "ugc", "intake": {"offer": "x" * 500}})
    assert len(pick["intake"]["offer"]) == 120


def test_the_turn_note_carries_the_brief():
    pick = studios.clean_pick({"id": "ads", "format": "product_showcase", "aspect": "1:1",
                               "seconds": 12, "intake": {"platform": "feed", "tone": "premium",
                                                         "offer": "Shop the drop"}})
    note = studios.turn_note(pick)
    assert note.startswith("AD STUDIO.")
    assert "Product showcase" in note and "1:1, 12 seconds" in note
    assert "Where will it run: Feed post" in note and "Tone: Premium" in note
    assert "What should they do: Shop the drop" in note
    assert "Follow the Ad recipe" in note
    assert "{" not in note           # every slot filled
    assert "Nothing else on the brief" in studios.turn_note(
        studios.clean_pick({"id": "ads", "format": "ugc"}))
    assert studios.turn_note(None) == "" and studios.turn_note({"id": "x"}) == ""


def test_the_still_note_says_no_length():
    note = studios.turn_note(studios.clean_pick({"id": "ads", "format": "product_still"}))
    assert "4:5\n" in note and "seconds" not in note.split("Work to that brief")[0]


# --- the gate ----------------------------------------------------------------

@pytest.fixture
def workspace(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    accounts.seed("mike@example.com", dsn=pg)
    addons.init(pg)
    ledger.init(pg)
    with db.connect(pg) as conn:
        account_id = int(conn.execute(
            "SELECT id FROM accounts WHERE slug = 'phantra'").fetchone()["id"])
    return {"dsn": pg, "account_id": account_id}


def test_a_pick_reaches_the_brain_only_with_the_add_on(workspace, monkeypatch):
    acct = workspace["account_id"]
    raw = {"id": "ads", "format": "ugc"}
    assert studios.for_account(raw, acct) is None
    assert studios.for_account(raw, None) is None
    addons.grant("phantra", "studios", True)
    assert studios.for_account(raw, acct)["format"] == "ugc"
    addons.grant("phantra", "studios", False)
    assert studios.for_account(raw, acct) is None
    # an installation with nothing to sell opens it to everyone
    monkeypatch.setenv(addons.GATE_ENV, "0")
    assert studios.for_account(raw, acct)["format"] == "ugc"


def test_the_grant_is_idempotent_reports_the_before_and_refuses_strangers(workspace):
    first = addons.grant("phantra", "studios", True)
    assert first["was"] is False and first["now"] is True and first["changed"]
    again = addons.grant("phantra", "studios", True)
    assert again["changed"] is False
    with pytest.raises(ValueError):
        addons.grant("nobody", "studios", True)
    with pytest.raises(ValueError):
        addons.grant("phantra", "music", True)
    # a row is never deleted: a revoke is the record of what was held
    addons.grant("phantra", "studios", False)
    assert addons.row(workspace["account_id"], "studios")["status"] == addons.REVOKED


def test_a_stripe_paid_add_on_is_not_turned_off_by_hand(workspace):
    addons.set_status(workspace["account_id"], "studios", addons.ACTIVE, source="stripe",
                      subscription="sub_9")
    with pytest.raises(ValueError, match="Stripe"):
        addons.grant("phantra", "studios", False)
    assert addons.active(workspace["account_id"])


def test_the_cli_grants_it(workspace, capsys):
    accounts.main(["studios", "phantra", "--on"])
    assert "OFF -> ON" in capsys.readouterr().out
    accounts.main(["studios", "phantra", "--on"])
    assert "already ON" in capsys.readouterr().out


def test_the_draft_keeps_a_clean_pick():
    kept = assistant_store._clean_draft({"idea": "x", "studio": {
        "id": "ads", "format": "tv_spot", "aspect": "4:5", "intake": {"tone": "bold"}}})
    assert kept["studio"] == {"id": "ads", "format": "tv_spot", "aspect": "16:9",
                              "seconds": 30, "intake": {"tone": "bold"}}
    assert assistant_store._clean_draft({"studio": {"id": "ads"}})["studio"] is None
    assert assistant_store.EMPTY_DRAFT["studio"] is None


# --- the page ----------------------------------------------------------------

@pytest.fixture
def signed_in(workspace, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "m@example.com"})
    app.dependency_overrides[auth.current_account_id] = lambda: workspace["account_id"]
    yield workspace
    app.dependency_overrides.pop(auth.current_account_id, None)


def test_the_page_is_open_to_everyone_and_shows_no_prompt_note(signed_in):
    r = client.get("/api/studios/ads")
    assert r.status_code == 200, r.text
    page = r.json()
    assert page["title"] == "Ad Studio" and page["entitled"] is False and page["gated"] is True
    assert [f["id"] for f in page["formats"]][:2] == ["product_showcase", "ugc"]
    assert all("note" not in f for f in page["formats"])
    assert page["formats"][0]["skill_title"] == "Ad"
    assert page["addon"]["key"] == "studios" and page["addon"]["has_plan"] is False
    assert page["addon"]["on_sale"] is False          # no Stripe key in the suite
    assert page["addon"]["monthly_usd"] == pricing.ADDONS["studios"].monthly_usd
    addons.grant("phantra", "studios", True)
    assert client.get("/api/studios/ads").json()["entitled"] is True
    assert client.get("/api/studios/fashion").status_code == 404


# --- the brain turn ----------------------------------------------------------

def _turn(monkeypatch, data, entitled):
    seen = {}

    async def refs(form, **kwargs):
        return [], [], []

    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "guide-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    monkeypatch.setattr(addons, "active", lambda account_id, addon="studios", dsn=None: entitled)
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.update(kw) or {"message": "ok", "choices": [], "brief": ""})
    app.dependency_overrides[auth.current_account_id] = lambda: 42
    try:
        guide = TestClient(app, headers={"X-Phantra-Model-Connection": "1"})
        job_id = guide.post("/api/creative-guide", data={**data, "conversation": json.dumps({
            "messages": [{"role": "user", "content": "An ad for my shoes"}]})}).json()["job_id"]
        for _ in range(200):
            job = guide.get(f"/api/jobs/{job_id}").json()
            if job["status"] in ("done", "failed"):
                break
            time.sleep(.01)
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)
    assert job["status"] == "done", job
    return seen, job


def test_the_turn_gets_the_pick_with_the_add_on(monkeypatch):
    pick = json.dumps({"id": "ads", "format": "ugc", "intake": {"platform": "reels"}})
    seen, job = _turn(monkeypatch, {"studio": pick}, entitled=True)
    assert seen["studio"]["format"] == "ugc" and seen["studio"]["intake"] == {"platform": "reels"}
    assert job["studio"]["format"] == "ugc"


def test_the_turn_without_the_add_on_is_the_plain_composers(monkeypatch):
    pick = json.dumps({"id": "ads", "format": "ugc"})
    seen, job = _turn(monkeypatch, {"studio": pick}, entitled=False)
    assert seen["studio"] is None and job["studio"] is None
    seen, _ = _turn(monkeypatch, {}, entitled=True)
    assert seen["studio"] is None


def test_respond_puts_the_note_on_the_last_message(monkeypatch):
    from src import gemini_utils
    sent = {}

    def generate(client, model, contents, **kwargs):
        sent["contents"] = contents
        return json.dumps({"message": "ok", "choices": [], "brief": ""})

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user", "content": "go"}]),
        client=object(), grounding={},
        studio=studios.clean_pick({"id": "ads", "format": "motion_ad"}))
    last = " ".join(p.text or "" for p in sent["contents"][-1].parts)
    assert "AD STUDIO." in last and "Motion ad" in last and "make_ad" in last


# --- billing: an add-on is its own subscription --------------------------------

@pytest.fixture
def shop(workspace, monkeypatch):
    monkeypatch.setenv(billing.WEBHOOK_ENV, WHSEC)
    for key, item in billing.products().items():
        monkeypatch.setenv(item.price_env, f"price_{key}")
        if billing.is_plan(key):
            monkeypatch.setenv(item.price_env_yearly, f"price_{key}_year")
    app.dependency_overrides[auth.current_account_id] = lambda: workspace["account_id"]
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "m@example.com"})
    yield workspace
    app.dependency_overrides.pop(auth.current_account_id, None)


def _on_a_plan(acct, dsn):
    post(checkout_paid(acct, item="topup"))                  # binds cus_1
    r = post(invoice_paid(price="price_creator", invoice="in_plan"))
    assert r.json()["action"] == "granted"
    return ledger.available(acct, dsn)


def test_buying_the_add_on_turns_it_on_and_grants_no_credit(shop):
    acct, dsn = shop["account_id"], shop["dsn"]
    before = _on_a_plan(acct, dsn)
    r = post(event("checkout.session.completed", {
        "id": "cs_add", "object": "checkout.session", "mode": "subscription",
        "customer": "cus_1", "subscription": "sub_add",
        "metadata": {"account_id": str(acct), "item": "studios"}}))
    assert r.status_code == 200 and r.json()["action"] == "addon_active", r.text
    assert addons.active(acct)
    assert addons.row(acct, "studios")["stripe_subscription_id"] == "sub_add"
    r = post(event("invoice.paid", {
        "id": "in_add", "object": "invoice", "customer": "cus_1", "subscription": "sub_add",
        "lines": {"data": [{"price": {"id": "price_studios"}, "period": {"end": 1893456000}}]}},
        eid="evt_2"))
    assert r.json()["action"] == "addon_active"
    assert addons.row(acct, "studios")["current_period_end"].startswith("2030-01-01")
    assert ledger.available(acct, dsn) == before                 # no credit
    assert accounts.plan_of(acct, dsn=dsn) == "creator"          # the plan untouched


def test_cancelling_the_add_on_never_touches_the_plan(shop):
    """The bug the spec found: an add-on's subscription.deleted fell into
    the plan's lapse and expired its credits and cleared the plan."""
    acct, dsn = shop["account_id"], shop["dsn"]
    before = _on_a_plan(acct, dsn)
    addons.set_status(acct, "studios", addons.ACTIVE, source="stripe", subscription="sub_add")
    r = post(event("customer.subscription.deleted", {
        "id": "sub_add", "object": "subscription", "customer": "cus_1", "status": "canceled",
        "items": {"data": [{"price": {"id": "price_studios"}}]}}))
    assert r.status_code == 200 and r.json()["action"] == "addon_revoked", r.text
    assert not addons.active(acct)
    assert accounts.plan_of(acct, dsn=dsn) == "creator"
    assert ledger.available(acct, dsn) == before


def test_the_metadata_names_the_add_on_when_the_items_do_not(shop):
    acct, dsn = shop["account_id"], shop["dsn"]
    _on_a_plan(acct, dsn)
    addons.set_status(acct, "studios", addons.ACTIVE, source="stripe", subscription="sub_add")
    r = post(event("customer.subscription.updated", {
        "id": "sub_add", "object": "subscription", "customer": "cus_1", "status": "unpaid",
        "metadata": {"item": "studios"}}))
    assert r.json()["action"] == "addon_revoked"
    assert accounts.plan_of(acct, dsn=dsn) == "creator"
    r = post(event("customer.subscription.updated", {
        "id": "sub_add", "object": "subscription", "customer": "cus_1", "status": "active",
        "current_period_end": 1893456000, "metadata": {"item": "studios"}}, eid="evt_3"))
    assert r.json()["action"] == "addon_active" and addons.active(acct)


def test_a_plans_own_lapse_still_lapses(shop):
    acct, dsn = shop["account_id"], shop["dsn"]
    _on_a_plan(acct, dsn)
    r = post(event("customer.subscription.deleted", {
        "id": "sub_plan", "object": "subscription", "customer": "cus_1", "status": "canceled",
        "items": {"data": [{"price": {"id": "price_creator"}}]}}))
    assert r.json()["action"] == "lapsed"
    assert accounts.plan_of(acct, dsn=dsn) is None


def test_a_payment_mode_checkout_naming_the_add_on_grants_nothing(shop):
    acct, dsn = shop["account_id"], shop["dsn"]
    r = post(checkout_paid(acct, item="studios"))
    assert r.json()["action"] == "unknown_item"
    assert ledger.available(acct, dsn) == 0 and not addons.active(acct)


def test_the_add_on_checkout_needs_a_plan_is_monthly_and_comes_back_to_the_studio(shop, monkeypatch):
    monkeypatch.setenv(billing.SECRET_ENV, "sk_test_x")
    calls = {}

    class FakeStripe:
        class Customer:
            @staticmethod
            def create(**kw):
                return {"id": "cus_new"}

        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    calls["session"] = kw
                    return {"url": "https://checkout.stripe.test/s/2"}

    monkeypatch.setattr(billing, "_stripe", lambda: FakeStripe)
    r = client.post("/api/billing/checkout", json={"item": "studios"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "plan_required"
    assert "add-on" in r.json()["error"]["message"] and "session" not in calls
    accounts.set_plan(shop["account_id"], "starter", dsn=shop["dsn"])
    r = client.post("/api/billing/checkout", json={"item": "studios", "interval": "year"})
    assert r.status_code == 400 and "session" not in calls
    r = client.post("/api/billing/checkout", json={"item": "studios"})
    assert r.status_code == 200, r.text
    assert calls["session"]["mode"] == "subscription"
    assert calls["session"]["line_items"] == [{"price": "price_studios", "quantity": 1}]
    assert calls["session"]["subscription_data"]["metadata"]["item"] == "studios"
    assert calls["session"]["success_url"].endswith("/studio/ads?checkout=success")
    # holding it already: no second subscription
    addons.grant("phantra", "studios", True)
    r = client.post("/api/billing/checkout", json={"item": "studios"})
    assert r.status_code == 400 and "already" in r.json()["error"]["message"]


def test_the_balance_says_which_add_ons_are_held(shop):
    r = client.get("/api/billing/balance")
    assert r.status_code == 200 and r.json()["addons"] == {"studios": False}
    addons.grant("phantra", "studios", True)
    assert client.get("/api/billing/balance").json()["addons"] == {"studios": True}
