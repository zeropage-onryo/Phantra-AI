"""
The affiliate program (2026-10-26, src/affiliates.py + app/affiliate_routes.py).

Every Stripe event is a fixture (the suite blocks the network); time is
passed in (`now=`), never slept. Guards:
- the tiers pay what the terms say (20%/3, 30%/6, 35%/12) and a tier is
  LOCKED on a referral at its first payment
- a commission is on what the customer paid before tax; free pays nothing
- a yearly payment earns the same as the months it covers, never the year
- the same invoice twice books once
- nothing is paid before the 60-day hold; a refund inside it voids/scales
- credits are a 12-month promo lot, once; cash waits for Mike
- no self-referral (same account or same person), no re-attribution,
  none after a first payment, none to an unapproved partner
- a failure in this module can never stop the customer's credit
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, affiliates, billing, db, ledger

client = TestClient(app)
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    stub = {"id": 1, "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)
    monkeypatch.setattr(
        auth, "current_account",
        lambda request, user=None: {"slug": "phantra", "display_name": "Phantra AI"})


@pytest.fixture
def world(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    ledger.init(pg)
    affiliates.init(pg)
    with db.connect(pg) as conn:
        conn.execute("DELETE FROM affiliate_commissions")
    return pg


def make_account(dsn, slug, *, user=None):
    """An account and its owner, straight into the tables."""
    uid = user or f"u-{slug}"
    with db.connect(dsn) as conn:
        conn.execute("INSERT INTO users (id, created_at, email) VALUES (%s, 'now', %s) "
                     "ON CONFLICT DO NOTHING", (uid, f"{slug}@example.com"))
        acct = conn.execute(
            "INSERT INTO accounts (created_at, slug, display_name) VALUES ('now', %s, %s) "
            "RETURNING id", (slug, slug)).fetchone()["id"]
        conn.execute("INSERT INTO account_members (account_id, user_id) VALUES (%s, %s)",
                     (acct, uid))
    return int(acct)


def approved_partner(dsn, slug="ana", code=None):
    acct = make_account(dsn, slug)
    affiliates.apply(acct, channel_url="https://youtube.com/@ana", audience="film makers",
                     plan="tutorials", accept_terms=True, dsn=dsn)
    p = affiliates.approve(slug, code=code, dsn=dsn)
    return acct, p


def invoice(n=1, cents=2900, tax=0):
    return {"id": f"in_{n}", "amount_paid": cents + tax, "total_excluding_tax": cents}


def referral(dsn, partner_slug="ana", buyer_slug="bo"):
    partner_acct, p = approved_partner(dsn, partner_slug)
    buyer = make_account(dsn, buyer_slug)
    assert affiliates.attribute(buyer, p["code"], dsn=dsn)["attributed"]
    return partner_acct, p, buyer


def commissions(dsn, partner_acct):
    with db.connect(dsn) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM affiliate_commissions WHERE account_id = %s ORDER BY id",
            (partner_acct,)).fetchall()]


# --- the terms ---------------------------------------------------------------

def test_the_terms_are_mikes_numbers():
    t = {x.key: (x.rate_bp, x.window_months, x.min_paying) for x in affiliates.TIERS}
    assert t == {"starter": (2000, 3, 0), "pro": (3000, 6, 10), "partner": (3500, 12, 50)}
    assert affiliates.tier_for_count(0).key == "starter"
    assert affiliates.tier_for_count(9).key == "starter"
    assert affiliates.tier_for_count(10).key == "pro"
    assert affiliates.tier_for_count(49).key == "pro"
    assert affiliates.tier_for_count(50).key == "partner"
    pub = affiliates.public_terms()
    assert [x["percent"] for x in pub["tiers"]] == [20.0, 30.0, 35.0]
    assert pub["hold_days"] == 60 and pub["buyer_discount_percent"] == 20


# --- applying and approving ---------------------------------------------------

def test_apply_is_one_per_account_and_validated(world):
    acct = make_account(world, "ana")
    with pytest.raises(affiliates.AffiliateError) as e:
        affiliates.apply(acct, channel_url="https://x.com/a", audience="a", plan="b",
                         accept_terms=False, dsn=world)
    assert e.value.code == "terms_required"
    with pytest.raises(affiliates.AffiliateError) as e:
        affiliates.apply(acct, channel_url="not a link", audience="a", plan="b",
                         accept_terms=True, dsn=world)
    assert e.value.code == "bad_channel"
    first = affiliates.apply(acct, channel_url="https://x.com/a", audience="a", plan="b",
                             accept_terms=True, dsn=world)
    again = affiliates.apply(acct, channel_url="https://x.com/other", audience="z", plan="z",
                             accept_terms=True, dsn=world)
    assert first["id"] == again["id"] and again["channel_url"] == "https://x.com/a"
    assert first["status"] == "pending" and first["code"] is None


def test_approval_mints_a_code_from_the_slug_and_codes_are_unique(world):
    _, p = approved_partner(world, "ana")
    assert p["status"] == "approved" and p["code"] == "ana"
    assert affiliates.link("ana").endswith("/?ref=ana")
    b = make_account(world, "ana2")
    affiliates.apply(b, channel_url="https://x.com/b", audience="a", plan="b",
                     accept_terms=True, dsn=world)
    with pytest.raises(affiliates.AffiliateError) as e:
        affiliates.approve("ana2", code="ANA", dsn=world)       # case-insensitive clash
    assert e.value.code == "code_taken"
    with pytest.raises(affiliates.AffiliateError):
        affiliates.approve("ana2", code="admin", dsn=world)     # reserved
    assert affiliates.approve("ana2", dsn=world)["code"] == "ana2"
    short = make_account(world, "yo")
    affiliates.apply(short, channel_url="https://x.com/c", audience="a", plan="b",
                     accept_terms=True, dsn=world)
    assert affiliates.approve("yo", dsn=world)["code"] == "creator-yo"


# --- attribution --------------------------------------------------------------

def test_attribution_rules(world):
    partner_acct, p = approved_partner(world)
    buyer = make_account(world, "bo")
    assert affiliates.attribute(buyer, "nope", dsn=world)["reason"] == "unknown_code"
    assert affiliates.attribute(buyer, "!!", dsn=world)["reason"] == "bad_code"
    assert affiliates.attribute(partner_acct, "ANA", dsn=world)["reason"] == "self_referral"
    # the same person's other workspace is still the same person
    sibling = make_account(world, "ana-studio", user="u-ana")
    assert affiliates.attribute(sibling, "ana", dsn=world)["reason"] == "self_referral"
    assert affiliates.attribute(buyer, "Ana", dsn=world) == {"attributed": True, "reason": "ok"}
    assert affiliates.attribute(buyer, "ana", dsn=world)["reason"] == "already_attributed"
    other = approved_partner(world, "cy")[1]
    assert affiliates.attribute(buyer, other["code"], dsn=world)["reason"] == "already_attributed"
    # a suspended partner earns nothing new
    paid = make_account(world, "dee")
    ledger.grant(paid, 1500, "subscription", source_ref="in_x", dsn=world)
    assert affiliates.attribute(paid, "ana", dsn=world)["reason"] == "already_paid"
    affiliates.set_status("ana", "suspended", dsn=world)
    late = make_account(world, "eve")
    assert affiliates.attribute(late, "ana", dsn=world)["reason"] == "unknown_code"


def test_buyer_discount_is_first_monthly_payment_only(world):
    _, _, buyer = referral(world)
    assert affiliates.buyer_discount_applies(buyer, "month", dsn=world) is True
    assert affiliates.buyer_discount_applies(buyer, "year", dsn=world) is False
    assert affiliates.buyer_discount_applies(make_account(world, "zed"), "month", dsn=world) is False
    affiliates.on_invoice_paid(buyer, invoice(), now=T0, dsn=world)
    assert affiliates.buyer_discount_applies(buyer, "month", dsn=world) is False


# --- earning ------------------------------------------------------------------

def test_starter_earns_20_percent_for_three_months_then_stops(world):
    partner, _, buyer = referral(world)
    for n in range(1, 6):
        affiliates.on_invoice_paid(buyer, invoice(n), now=T0 + timedelta(days=30 * n), dsn=world)
    rows = commissions(world, partner)
    assert [r["commission_cents"] for r in rows] == [580, 580, 580]       # 20% of $29, 3 times
    assert all(r["status"] == "held" for r in rows)
    assert rows[0]["hold_until"] == T0 + timedelta(days=30) + timedelta(days=60)


def test_commission_is_on_the_amount_paid_before_tax(world):
    partner, _, buyer = referral(world)
    affiliates.on_invoice_paid(buyer, {"id": "in_t", "amount_paid": 2900 + 290,
                                       "total_excluding_tax": 2900}, now=T0, dsn=world)
    assert commissions(world, partner)[0]["commission_cents"] == 580
    # a 20%-off first month pays on what was paid
    b2 = make_account(world, "cy2")
    affiliates.attribute(b2, "ana", dsn=world)
    affiliates.on_invoice_paid(b2, {"id": "in_d", "amount_paid": 2320, "total_excluding_tax": 2320},
                               now=T0, dsn=world)
    assert commissions(world, partner)[1]["commission_cents"] == 464
    # free pays nothing
    b3 = make_account(world, "cy3")
    affiliates.attribute(b3, "ana", dsn=world)
    assert affiliates.on_invoice_paid(b3, {"id": "in_f", "amount_paid": 0}, now=T0,
                                      dsn=world)["action"] == "nothing_paid"


def test_the_same_invoice_books_once(world):
    partner, _, buyer = referral(world)
    a = affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    b = affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    assert a["action"] == "booked" and b["action"] == "already_booked"
    assert len(commissions(world, partner)) == 1


def test_a_yearly_payment_earns_the_months_it_covers_not_the_year(world):
    partner, _, buyer = referral(world)
    r = affiliates.on_invoice_paid(buyer, {"id": "in_y", "amount_paid": 27840,
                                           "total_excluding_tax": 27840},
                                   months_covered=12, now=T0, dsn=world)
    # Starter: 3 of 12 months at 20% = 27840 * 0.20 * 3/12
    assert r["commission_cents"] == 1392
    row = commissions(world, partner)[0]
    assert (row["months_covered"], row["months_counted"]) == (12, 3)
    # and the window is spent: next year's renewal earns nothing at Starter
    again = affiliates.on_invoice_paid(buyer, {"id": "in_y2", "amount_paid": 27840,
                                               "total_excluding_tax": 27840},
                                       months_covered=12, now=T0 + timedelta(days=365), dsn=world)
    assert again["action"] == "window_over"


def test_a_tier_is_locked_at_the_referrals_first_payment(world):
    partner, p = approved_partner(world)
    first = make_account(world, "early")
    affiliates.attribute(first, "ana", dsn=world)
    # ten other referrals pay: the partner is Pro for whoever pays NEXT
    for i in range(10):
        b = make_account(world, f"buyer{i}")
        affiliates.attribute(b, "ana", dsn=world)
        affiliates.on_invoice_paid(b, invoice(100 + i), now=T0, dsn=world)
    late = make_account(world, "late")
    affiliates.attribute(late, "ana", dsn=world)
    affiliates.on_invoice_paid(late, invoice(200), now=T0, dsn=world)
    affiliates.on_invoice_paid(first, invoice(201), now=T0, dsn=world)   # attributed first, pays last
    by_invoice = {r["invoice_ref"]: r for r in commissions(world, partner)}
    assert by_invoice["in_100"]["rate_bp"] == 2000
    assert by_invoice["in_200"]["rate_bp"] == 3000                       # the 11th payer is Pro
    assert by_invoice["in_201"]["rate_bp"] == 3000                       # tier read when IT first paid
    with db.connect(world) as conn:
        w = conn.execute("SELECT window_months FROM affiliate_referrals WHERE referred_account_id = %s",
                         (late,)).fetchone()
    assert w["window_months"] == 6
    assert affiliates.summary(partner, dsn=world)["tier"]["key"] == "pro"


def test_an_unattributed_or_unapproved_payer_books_nothing(world):
    stranger = make_account(world, "solo")
    assert affiliates.on_invoice_paid(stranger, invoice(), now=T0, dsn=world)["action"] == "no_referral"
    partner, _, buyer = referral(world)
    affiliates.set_status("ana", "suspended", dsn=world)
    assert affiliates.on_invoice_paid(buyer, invoice(), now=T0, dsn=world)["action"] == "partner_not_approved"
    assert commissions(world, partner) == []


# --- refunds, the hold, and paying ---------------------------------------------

def test_a_refund_inside_the_hold_voids_or_scales_the_commission(world):
    partner, _, buyer = referral(world)
    affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    affiliates.on_invoice_paid(buyer, invoice(2), now=T0, dsn=world)
    out = affiliates.on_refund(buyer, {"invoice": "in_1", "amount": 2900, "amount_refunded": 1450},
                               dsn=world)
    assert out["action"] == "scaled" and out["commission_cents"] == 290
    out = affiliates.on_refund(buyer, {"invoice": "in_2", "amount": 2900, "amount_refunded": 2900},
                               dsn=world)
    assert out["action"] == "void"
    rows = commissions(world, partner)
    assert [(r["status"], r["commission_cents"]) for r in rows] == [("held", 290), ("void", 0)]
    assert affiliates.on_refund(make_account(world, "nobody"),
                                {"amount": 100, "amount_refunded": 100}, dsn=world)["action"] == "no_referral"


def test_nothing_is_paid_before_the_hold_and_credits_land_once_after(world):
    partner, _, buyer = referral(world)
    affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    assert affiliates.release_due(now=T0 + timedelta(days=59), dsn=world) == {
        "credited": 0, "cash_payable": 0, "skipped": 0}
    assert ledger.available(partner, world) == 0
    done = affiliates.release_due(now=T0 + timedelta(days=61), dsn=world)
    assert done["credited"] == 1
    assert ledger.available(partner, world) == 580                     # 1 credit per cent
    assert affiliates.release_due(now=T0 + timedelta(days=62), dsn=world)["credited"] == 0
    assert ledger.available(partner, world) == 580
    lot = [lot for lot in ledger.lots(partner, world) if lot["kind"] == "promo"][-1]
    assert lot["source_ref"].startswith("affiliate:")
    exp = datetime.fromisoformat(lot["expires_at"])
    assert exp > datetime.now(timezone.utc) + timedelta(days=360)
    row = commissions(world, partner)[0]
    assert row["status"] == "paid" and row["payout"] == "credits" and row["lot_id"]


def test_cash_waits_for_mike_and_a_suspended_partner_is_skipped(world):
    partner, _, buyer = referral(world)
    affiliates.set_payout_mode("ana", "cash", dsn=world)
    for n in range(1, 4):
        affiliates.on_invoice_paid(buyer, invoice(n, cents=100000), now=T0, dsn=world)
    done = affiliates.release_due(now=T0 + timedelta(days=61), dsn=world)
    assert done == {"credited": 0, "cash_payable": 3, "skipped": 0}
    assert ledger.available(partner, world) == 0
    owed = affiliates.payouts(dsn=world)
    assert len(owed) == 1 and int(owed[0]["cents"]) == 60000
    with pytest.raises(affiliates.AffiliateError):
        affiliates.mark_paid("ana", "  ", dsn=world)
    assert affiliates.mark_paid("ana", "paypal-123", dsn=world) == {"commissions": 3, "cents": 60000}
    assert affiliates.payouts(dsn=world) == []
    s = affiliates.summary(partner, dsn=world)
    assert s["earnings"]["paid_cents"] == 60000 and s["earnings"]["payable_cash_cents"] == 0
    # a suspended partner's held commissions wait
    p2, _, b2 = referral(world, "cy", "di")
    affiliates.on_invoice_paid(b2, invoice(50), now=T0, dsn=world)
    affiliates.set_status("cy", "suspended", dsn=world)
    assert affiliates.release_due(now=T0 + timedelta(days=61), dsn=world)["skipped"] == 1


def test_small_cash_balances_wait_for_the_minimum(world):
    partner, _, buyer = referral(world)
    affiliates.set_payout_mode("ana", "cash", dsn=world)
    affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    affiliates.release_due(now=T0 + timedelta(days=61), dsn=world)
    assert affiliates.payouts(dsn=world) == []                         # $5.80 < $50


# --- the dashboard -------------------------------------------------------------

def test_summary_shows_progress_and_no_names(world):
    partner, _, buyer = referral(world)
    affiliates.on_invoice_paid(buyer, invoice(1), now=T0, dsn=world)
    s = affiliates.summary(partner, dsn=world)
    assert s["status"] == "approved" and s["link"].endswith("?ref=ana")
    assert s["signups"] == 1 and s["paying_referrals"] == 1
    assert s["next_tier"]["key"] == "pro" and s["next_tier"]["needs"] == 9
    assert s["earnings"]["held_cents"] == 580
    assert "bo@example.com" not in repr(s) and "bo" not in {k for k in s}
    assert affiliates.summary(make_account(world, "plain"), dsn=world)["status"] is None


# --- the webhook, end to end -----------------------------------------------------

def _paid_event(buyer_acct, invoice_id="in_w1", cents=2900):
    return {"id": "evt_w", "type": "invoice.paid", "data": {"object": {
        "id": invoice_id, "customer": None, "amount_paid": cents, "total_excluding_tax": cents,
        "metadata": {"account_id": str(buyer_acct), "item": "starter", "interval": "month"},
        "subscription_details": {"metadata": {"item": "starter", "interval": "month"}},
        "lines": {"data": []}}}}


def test_a_paid_invoice_books_the_partners_commission(world):
    partner, _, buyer = referral(world)
    out = billing.handle_event(_paid_event(buyer), dsn=world)
    assert out["action"] == "granted"
    assert [r["commission_cents"] for r in commissions(world, partner)] == [580]
    billing.handle_event(_paid_event(buyer), dsn=world)                 # redelivered
    assert len(commissions(world, partner)) == 1


def test_a_failing_affiliate_module_never_stops_the_customers_credit(world, monkeypatch):
    _, _, buyer = referral(world)
    monkeypatch.setattr(affiliates, "on_invoice_paid",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = billing.handle_event(_paid_event(buyer, "in_w9"), dsn=world)
    assert out["action"] == "granted"
    assert ledger.available(buyer, world) > 0


def test_checkout_carries_the_buyer_discount_once(world, monkeypatch):
    _, _, buyer = referral(world)
    monkeypatch.setenv(billing.SECRET_ENV, "sk_test_x")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_STARTER_YEAR", "price_starter_year")
    monkeypatch.setenv(affiliates.COUPON_ENV, "coupon_aff20")
    seen = []

    class FakeStripe:
        class Customer:
            @staticmethod
            def create(**kw):
                return {"id": "cus_b"}

        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    seen.append(kw)
                    return {"url": "https://checkout.stripe.test/x"}

    monkeypatch.setattr(billing, "_stripe", lambda: FakeStripe)
    billing.checkout_url(buyer, "starter", dsn=world)
    assert seen[-1]["discounts"] == [{"coupon": "coupon_aff20"}]
    assert "allow_promotion_codes" not in seen[-1]
    billing.checkout_url(buyer, "starter", interval="year", dsn=world)
    assert "discounts" not in seen[-1] and seen[-1]["allow_promotion_codes"] is True
    monkeypatch.delenv(affiliates.COUPON_ENV)
    billing.checkout_url(buyer, "starter", dsn=world)
    assert "discounts" not in seen[-1]


# --- the routes ------------------------------------------------------------------

def test_routes_apply_summarise_and_attribute(world):
    partner_acct, _ = approved_partner(world)
    me = make_account(world, "newbie")
    app.dependency_overrides[auth.current_account_id] = lambda: me
    try:
        r = client.get("/api/affiliates/me")
        assert r.status_code == 200 and r.json()["status"] is None
        r = client.post("/api/affiliates/apply", json={
            "channel_url": "https://tiktok.com/@n", "audience": "bartenders", "plan": "reels",
            "accept_terms": True})
        assert r.status_code == 200 and r.json()["status"] == "pending"
        r = client.get("/api/affiliates/me")
        assert r.json()["status"] == "pending" and r.json()["link"] is None
        r = client.post("/api/affiliates/attribute", json={"code": "ana"})
        assert r.json() == {"attributed": True, "reason": "ok"}
        r = client.post("/api/affiliates/attribute", json={"code": "ana"})
        assert r.json()["reason"] == "already_attributed"
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)


def test_a_bad_application_is_a_400_with_a_code(world):
    me = make_account(world, "newbie2")
    app.dependency_overrides[auth.current_account_id] = lambda: me
    try:
        r = client.post("/api/affiliates/apply", json={
            "channel_url": "nope", "audience": "a", "plan": "b", "accept_terms": True})
        assert r.status_code == 400 and r.json()["error"]["code"] == "bad_channel"
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)


def test_the_public_page_prints_the_terms_the_code_pays():
    import json
    import pathlib
    committed = json.loads((pathlib.Path(__file__).resolve().parent.parent
                            / affiliates.CATALOG_PATH).read_text())
    assert committed == json.loads(json.dumps(affiliates.public_terms())), (
        "web/src/content/affiliate.json is stale -- run `python -m src.affiliates export`")
