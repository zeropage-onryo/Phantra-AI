"""The welcome offer (src/welcome_offer.py): the first-plan discount the
out-of-credits popup shows. Stripe is a fake throughout (the suite blocks the
network): the coupon read and the Checkout session are recorded, not sent."""
from __future__ import annotations

import pytest

from src import accounts, affiliates, billing, db, ledger, welcome_offer


@pytest.fixture
def world(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    ledger.init(pg)
    affiliates.init(pg)
    welcome_offer._clear_cache()
    return pg


def make_account(dsn, slug):
    with db.connect(dsn) as conn:
        conn.execute("INSERT INTO users (id, created_at, email) VALUES (%s, 'now', %s) "
                     "ON CONFLICT DO NOTHING", (f"u-{slug}", f"{slug}@example.com"))
        acct = conn.execute(
            "INSERT INTO accounts (created_at, slug, display_name) VALUES ('now', %s, %s) "
            "RETURNING id", (slug, slug)).fetchone()["id"]
        conn.execute("INSERT INTO account_members (account_id, user_id) VALUES (%s, %s)",
                     (acct, f"u-{slug}"))
    return int(acct)


COUPON_30 = {"id": "welcome30", "valid": True, "percent_off": 30.0, "amount_off": None,
             "currency": None, "duration": "once", "duration_in_months": None}


def fake_stripe(monkeypatch, coupon=COUPON_30, *, coupon_fails=False):
    """Stripe with one coupon on file; returns (sessions, coupon reads)."""
    sessions, reads = [], []

    class FakeStripe:
        class Coupon:
            @staticmethod
            def retrieve(cid):
                reads.append(cid)
                if coupon_fails:
                    raise RuntimeError("no such coupon")
                return coupon

        class Customer:
            @staticmethod
            def create(**kw):
                return {"id": "cus_w"}

        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    sessions.append(kw)
                    return {"url": "https://checkout.stripe.test/w"}

    monkeypatch.setenv(billing.SECRET_ENV, "sk_test_x")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_STARTER_YEAR", "price_starter_year")
    monkeypatch.setenv("STRIPE_PRICE_TOPUP", "price_topup")
    monkeypatch.setenv(welcome_offer.COUPON_ENV, "welcome30")
    monkeypatch.setattr(billing, "_stripe", lambda: FakeStripe)
    return sessions, reads


# --- what the coupon says ------------------------------------------------------

@pytest.mark.parametrize("raw,label", [
    (COUPON_30, "30% off your first month"),
    ({**COUPON_30, "percent_off": 12.5}, "12.5% off your first month"),
    ({**COUPON_30, "percent_off": None, "amount_off": 500, "currency": "usd"}, "$5 off your first month"),
    ({**COUPON_30, "duration": "repeating", "duration_in_months": 3}, "30% off your first 3 months"),
    ({**COUPON_30, "duration": "forever"}, "30% off every month"),
])
def test_the_label_is_read_off_the_coupon(raw, label):
    assert welcome_offer._shape(raw)["label"] == label


@pytest.mark.parametrize("raw", [
    {**COUPON_30, "valid": False},
    {**COUPON_30, "percent_off": None, "amount_off": None},
    {**COUPON_30, "percent_off": None, "amount_off": 500, "currency": "eur"},
])
def test_a_coupon_that_would_not_apply_is_no_offer(raw):
    assert welcome_offer._shape(raw) is None


def test_no_coupon_named_is_no_offer_and_no_stripe_call(world, monkeypatch):
    _, reads = fake_stripe(monkeypatch)
    monkeypatch.delenv(welcome_offer.COUPON_ENV)
    acct = make_account(world, "w-none")
    assert welcome_offer.for_account(acct, dsn=world) is None
    assert reads == []


def test_the_coupon_is_read_once_and_cached(world, monkeypatch):
    _, reads = fake_stripe(monkeypatch)
    for _ in range(3):
        assert welcome_offer.describe()["percent_off"] == 30
    assert reads == ["welcome30"]


# --- who gets it ---------------------------------------------------------------

def test_a_trial_workspace_is_offered_it(world, monkeypatch):
    fake_stripe(monkeypatch)
    acct = make_account(world, "w-trial")
    # the sign-up trial is a promo lot: it is not a payment
    ledger.grant(acct, 100, "promo", note="trial credits (open sign-up)", dsn=world)
    offer = welcome_offer.for_account(acct, dsn=world)
    assert offer and offer["label"] == "30% off your first month"


def test_a_plan_an_exempt_account_or_a_past_payment_is_never_offered_it(world, monkeypatch):
    fake_stripe(monkeypatch)
    on_plan = make_account(world, "w-plan")
    accounts.set_plan(on_plan, "starter", dsn=world)
    exempt = make_account(world, "w-exempt")
    accounts.set_credit_exempt("w-exempt", True, dsn=world)
    paid_before = make_account(world, "w-paid")
    ledger.grant(paid_before, 500, "purchase", source_ref="pi_old", note="top-up", dsn=world)
    for acct in (on_plan, exempt, paid_before):
        assert welcome_offer.for_account(acct, dsn=world) is None, acct


def test_an_unreadable_coupon_is_no_offer(world, monkeypatch):
    fake_stripe(monkeypatch, coupon_fails=True)
    acct = make_account(world, "w-broken")
    assert welcome_offer.for_account(acct, dsn=world) is None


# --- Checkout ------------------------------------------------------------------

def test_checkout_carries_the_welcome_coupon_on_a_monthly_plan_only(world, monkeypatch):
    sessions, _ = fake_stripe(monkeypatch)
    acct = make_account(world, "w-buy")
    billing.checkout_url(acct, "starter", dsn=world)
    assert sessions[-1]["discounts"] == [{"coupon": "welcome30"}]
    assert "allow_promotion_codes" not in sessions[-1]
    billing.checkout_url(acct, "starter", interval="year", dsn=world)
    assert "discounts" not in sessions[-1] and sessions[-1]["allow_promotion_codes"] is True


def test_an_unreadable_coupon_is_a_full_price_checkout_not_a_refused_one(world, monkeypatch):
    sessions, _ = fake_stripe(monkeypatch, coupon_fails=True)
    acct = make_account(world, "w-full")
    assert billing.checkout_url(acct, "starter", dsn=world).startswith("https://")
    assert "discounts" not in sessions[-1]


def test_the_welcome_coupon_wins_over_the_affiliate_one(world, monkeypatch):
    sessions, _ = fake_stripe(monkeypatch)
    monkeypatch.setenv(affiliates.COUPON_ENV, "coupon_aff10")
    monkeypatch.setattr(affiliates, "buyer_discount_applies", lambda *a, **k: True)
    acct = make_account(world, "w-both")
    billing.checkout_url(acct, "starter", dsn=world)
    assert sessions[-1]["discounts"] == [{"coupon": "welcome30"}]
    # once the welcome offer is spent (they paid), the affiliate one is still there
    monkeypatch.setattr(welcome_offer, "applies", lambda *a, **k: False)
    billing.checkout_url(acct, "starter", dsn=world)
    assert sessions[-1]["discounts"] == [{"coupon": "coupon_aff10"}]
