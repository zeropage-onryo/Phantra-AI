"""The plan picker on the OAuth consent page (2026-11-03).

Mike: "do what Krea does, but still have the free plan for people that
don't have accounts". Connecting ChatGPT or Claude shows the three plans
before Allow. A workspace made in this connection may also continue on the
free trial; an older workspace with no plan must pick one; a plan, paid
credit still unspent (a reviewer's adjustment grant) or credit_exempt goes
straight through. Same fake GoTrue as test_oauth_consent; Stripe is a
stub on the two billing seams (checkout_url, checkout_completed).
"""
import pytest
from fastapi.testclient import TestClient
from test_oauth_consent import (
    AUTHZ,
    CLAIMS_CALLBACK,
    ConsentGoTrue,
    _arrive_and_sign_in,
    _csrf,
    _get,
    clean_slate,  # noqa: F401 -- the autouse fixture, shared
)
from test_oauth_consent import client as _client

from app import auth as auth_mod
from src import accounts, billing, db, ledger

client: TestClient = _client


@pytest.fixture(autouse=True)
def stripe_on(clean_slate, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_not_real")
    monkeypatch.delenv("PHANTRA_OPEN_SIGNUP", raising=False)     # Ana gets a workspace
    monkeypatch.delenv("PHANTRA_CONNECT_PAYWALL", raising=False)
    ledger.ensure(clean_slate)
    return clean_slate


@pytest.fixture
def gotrue(monkeypatch):
    fake = ConsentGoTrue()
    fake.requests[AUTHZ]["client"]["name"] = "ChatGPT"
    fake.register("ana@example.com", "anas-password-1", uid="uid-ana")
    monkeypatch.setattr(auth_mod, "gotrue", fake)
    return fake


def _account_id() -> int:
    return min(int(a["id"]) for a in accounts.memberships("uid-ana"))


def _age(dsn, account_id, hours):
    with db.connect(dsn) as conn:
        conn.execute("UPDATE accounts SET created_at = to_char(now() at time zone 'utc' "
                     "- %s * interval '1 hour', 'YYYY-MM-DD\"T\"HH24:MI:SS') WHERE id = %s",
                     (hours, account_id))


def _approve(csrf):
    return client.post("/oauth/consent", data={"authorization_id": AUTHZ,
                                               "decision": "approve", "csrf": csrf},
                       follow_redirects=False)


def test_a_new_account_sees_the_plans_and_may_continue_on_the_free_trial(gotrue):
    _arrive_and_sign_in()
    page = _get()
    assert page.status_code == 200
    assert "Connect ChatGPT to Phantra" in page.text
    for name in ("Standard", "Pro", "Max"):
        assert f"Get {name}" in page.text
    assert "Most popular" in page.text and "Save 20% on yearly plans" in page.text
    assert "Continue with free trial &middot; 100 credits" in page.text
    response = _approve(_csrf(page.text))
    assert response.status_code == 303
    assert response.headers["location"].startswith(CLAIMS_CALLBACK + "?code=c0de")


def test_an_older_account_with_no_plan_must_pick_one(stripe_on, gotrue):
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    page = _get()
    assert "Get Pro" in page.text
    assert "Continue with free trial" not in page.text
    assert 'value="approve"' not in page.text
    response = _approve(_csrf(page.text))
    assert response.status_code == 402 and "Pick a plan" in response.text
    assert gotrue.decisions == []                     # Supabase never asked


def test_a_plan_goes_straight_to_allow(stripe_on, gotrue):
    _arrive_and_sign_in()
    account_id = _account_id()
    _age(stripe_on, account_id, 48)
    accounts.set_plan(account_id, "creator", dsn=stripe_on)
    page = _get()
    assert "Allow ChatGPT to use Phantra?" in page.text and "Get Pro" not in page.text
    assert _approve(_csrf(page.text)).status_code == 303


def test_a_reviewers_granted_credit_goes_straight_through(stripe_on, gotrue):
    _arrive_and_sign_in()
    account_id = _account_id()
    _age(stripe_on, account_id, 48)
    ledger.grant(account_id, 400, "adjustment", source_ref="review:1",
                 note="directory reviewer", dsn=stripe_on)
    page = _get()
    assert "Allow ChatGPT to use Phantra?" in page.text


def test_the_switch_turns_the_picker_off(stripe_on, gotrue, monkeypatch):
    monkeypatch.setenv("PHANTRA_CONNECT_PAYWALL", "0")
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    assert "Allow ChatGPT to use Phantra?" in _get().text


def test_no_stripe_means_no_picker(stripe_on, gotrue, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY")
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    assert "Allow ChatGPT to use Phantra?" in _get().text


def test_picking_a_plan_opens_checkout_that_returns_to_this_consent(stripe_on, gotrue,
                                                                    monkeypatch):
    seen = {}

    def fake_checkout(account_id, key, **kw):
        seen.update(account_id=account_id, key=key, **kw)
        return "https://checkout.stripe.com/c/pay/cs_test_1"

    monkeypatch.setattr(billing, "checkout_url", fake_checkout)
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    csrf = _csrf(_get().text)
    response = client.post("/oauth/consent/plan",
                           data={"authorization_id": AUTHZ, "csrf": csrf,
                                 "item": "creator", "interval": "year"},
                           follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "https://checkout.stripe.com/c/pay/cs_test_1"
    assert seen["account_id"] == _account_id() and seen["key"] == "creator"
    assert seen["interval"] == "year"
    assert seen["success_url"].endswith(
        f"/oauth/consent?authorization_id={AUTHZ}&checkout=success"
        "&session_id={CHECKOUT_SESSION_ID}")
    assert seen["cancel_url"].endswith(f"authorization_id={AUTHZ}&checkout=cancelled")


def test_a_bad_item_or_csrf_opens_nothing(stripe_on, gotrue, monkeypatch):
    monkeypatch.setattr(billing, "checkout_url",
                        lambda *a, **k: pytest.fail("no checkout for a bad form"))
    _arrive_and_sign_in()
    csrf = _csrf(_get().text)
    bad_item = client.post("/oauth/consent/plan", data={"authorization_id": AUTHZ,
                                                        "csrf": csrf, "item": "topup"})
    assert bad_item.status_code == 400
    bad_csrf = client.post("/oauth/consent/plan", data={"authorization_id": AUTHZ,
                                                        "csrf": "nope", "item": "creator"})
    assert bad_csrf.status_code == 403


def test_back_from_checkout_before_the_webhook_stripe_settles_it(stripe_on, gotrue,
                                                                  monkeypatch):
    asked = []
    monkeypatch.setattr(billing, "checkout_completed",
                        lambda sid, aid: asked.append((sid, aid)) or True)
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    page = client.get(f"/oauth/consent?authorization_id={AUTHZ}&checkout=success"
                      "&session_id=cs_test_1")
    assert asked == [("cs_test_1", _account_id())]
    assert "You're subscribed" in page.text and "Allow ChatGPT" in page.text
    assert _approve(_csrf(page.text)).status_code == 303


def test_an_unconfirmed_return_still_shows_the_plans(stripe_on, gotrue, monkeypatch):
    monkeypatch.setattr(billing, "checkout_completed", lambda sid, aid: False)
    _arrive_and_sign_in()
    _age(stripe_on, _account_id(), 48)
    page = client.get(f"/oauth/consent?authorization_id={AUTHZ}&checkout=success"
                      "&session_id=cs_forged")
    assert "Get Pro" in page.text
    assert _approve(_csrf(page.text)).status_code == 402


def test_a_request_that_timed_out_during_checkout_says_the_plan_is_active(gotrue):
    _arrive_and_sign_in()
    gotrue.requests.clear()
    page = client.get(f"/oauth/consent?authorization_id={AUTHZ}&checkout=success"
                      "&session_id=cs_test_1")
    assert "Your plan is active" in page.text and "connect again" in page.text


def test_cancelled_checkout_says_nothing_was_charged(gotrue):
    _arrive_and_sign_in()
    page = client.get(f"/oauth/consent?authorization_id={AUTHZ}&checkout=cancelled")
    assert "Nothing was charged" in page.text and "Get Pro" in page.text


def test_checkout_completed_reads_only_this_accounts_finished_subscription(monkeypatch):
    sessions = {
        "cs_ok": {"status": "complete", "mode": "subscription", "client_reference_id": "7"},
        "cs_open": {"status": "open", "mode": "subscription", "client_reference_id": "7"},
        "cs_pack": {"status": "complete", "mode": "payment", "client_reference_id": "7"},
    }

    class Fake:
        class checkout:
            class Session:
                @staticmethod
                def retrieve(sid):
                    if sid not in sessions:
                        raise RuntimeError("no such session")
                    return sessions[sid]

    monkeypatch.setattr(billing, "_stripe", lambda: Fake)
    assert billing.checkout_completed("cs_ok", 7) is True
    assert billing.checkout_completed("cs_ok", 8) is False
    assert billing.checkout_completed("cs_open", 7) is False
    assert billing.checkout_completed("cs_pack", 7) is False
    assert billing.checkout_completed("cs_missing", 7) is False
    assert billing.checkout_completed("not-a-session", 7) is False
