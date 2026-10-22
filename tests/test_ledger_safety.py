"""
Ledger safety, end to end through the doors a person actually spends at
(docs/tasks/task-overnight-2026-10-22.md, group 7, 2026-10-22).

tests/test_ledger.py proves the primitives (one `ledger.hold` beats its
twin under the advisory lock; a `grant` with a `source_ref` lands once).
This file proves the same three things one layer up, where a defect
would actually cost money, against the throwaway Postgres like every
other ledger test:

  (a) concurrent holds through `charge.Charge.take()` -- the seam every
      adapter spends through -- cannot double-spend one balance;
  (b) a provider call that raises inside the adapter (`effects.run` and
      `fal.generate_video`, the submit stubbed to raise) leaves the
      balance exactly where it was: the hold is released, nothing is
      settled, nothing is outstanding;
  (c) a Stripe webhook delivered twice -- the same event id replayed
      through the route with the signature check stubbed, and two
      deliveries racing each other through `billing.handle_event` --
      grants once, for a top-up, a monthly plan and a yearly plan.

Nothing here changes ledger or billing behaviour. A test that found a
defect would be left `@pytest.mark.skip(reason="defect: ...")`; none did.
"""
from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from src import accounts, billing, db, effects, fal, generative, ledger, pricing
from src import charge as charging


@pytest.fixture
def shop(pg, monkeypatch):
    """A seeded, NON-exempt account with every table a spend touches:
    accounts, generations (the cap), the ledger, and billing (the yearly
    schedule `Charge.take` releases before it reads the balance)."""
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    seeded = accounts.seed("mike@example.com", dsn=pg)
    generative.init(pg)
    ledger.init(pg)
    billing.init(pg)
    account_id = int(seeded["accounts"][0])
    assert not accounts.is_credit_exempt(account_id, dsn=pg)
    return {"dsn": pg, "account_id": account_id}


def _entries(dsn, account_id, kind):
    return [e for e in ledger.entries(account_id, dsn) if e["kind"] == kind]


# --------------------------------------------------------------------------
# (a) concurrent holds cannot double-spend
# --------------------------------------------------------------------------

def test_four_adapters_holding_at_once_cannot_overdraw_one_balance(shop, monkeypatch):
    """Four renders approved in the same instant, each 60 credits, on a
    balance of 100: exactly one takes its hold, three are refused, and
    the balance never dips below zero. Through `Charge.take()` -- the
    estimate converted by `ledger.charge_credits`, `billing.release_due`
    before the read, `hold_for_render` under the account's advisory lock
    -- so the whole seam is under test, not `ledger.hold` alone.

    The read-then-act window is widened by making the balance read
    sleep (tests/test_ledger.py's trick): without the lock all four
    would read 100 and all four would insert."""
    dsn, acct = shop["dsn"], shop["account_id"]
    ledger.grant(acct, 100, "promo", source_ref="signup:test", dsn=dsn)
    usd = 0.25                                   # 0.25 x 2.4 = 60 credits
    assert ledger.charge_credits(usd) == 60

    real_available = ledger._available

    def slow_available(conn, account_id, now=None):
        value = real_available(conn, account_id, now)
        time.sleep(0.3)
        return value

    monkeypatch.setattr(ledger, "_available", slow_available)

    n = 4
    barrier = threading.Barrier(n)
    results: list = [None] * n
    lowest: list[int] = []

    def render(i):
        c = charging.Charge(acct, provider="fal", ref=f"render-{i}.mp4",
                            estimate_usd=usd, dsn=dsn)
        barrier.wait()
        try:
            results[i] = c.take()
        except Exception as e:                   # noqa: BLE001 -- recorded, asserted below
            results[i] = e
        lowest.append(ledger.available(acct, dsn))

    threads = [threading.Thread(target=render, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    won = [r for r in results if isinstance(r, int)]
    refused = [r for r in results if isinstance(r, ledger.InsufficientCredit)]
    assert len(won) == 1, f"expected exactly one hold, got {results}"
    assert len(refused) == n - 1, f"expected {n - 1} refusals, got {results}"
    assert ledger.available(acct, dsn) == 40
    assert ledger.outstanding(acct, dsn) == 60
    assert min(lowest) >= 0, f"the balance went negative mid-race: {lowest}"
    assert len(_entries(dsn, acct, "hold")) == 1


def test_two_holds_that_each_fit_but_not_together(shop, monkeypatch):
    """The subtler shape: two holds that each fit alone (70 + 70 on 100).
    The second must see the first's entries, not the balance both read."""
    dsn, acct = shop["dsn"], shop["account_id"]
    ledger.grant(acct, 100, "subscription", source_ref="in_1", dsn=dsn)

    real_available = ledger._available

    def slow_available(conn, account_id, now=None):
        value = real_available(conn, account_id, now)
        time.sleep(0.3)
        return value

    monkeypatch.setattr(ledger, "_available", slow_available)
    barrier = threading.Barrier(2)
    results: list = [None, None]

    def take(i):
        barrier.wait()
        try:
            results[i] = ledger.hold_for_render(
                acct, ref=f"still-{i}.jpg", provider="fal", estimate_usd=None,
                credits=70, dsn=dsn)
        except Exception as e:                   # noqa: BLE001
            results[i] = e

    threads = [threading.Thread(target=take, args=(i,)) for i in (0, 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert sum(isinstance(r, int) for r in results) == 1, results
    assert sum(isinstance(r, ledger.InsufficientCredit) for r in results) == 1, results
    assert ledger.available(acct, dsn) == 30


# --------------------------------------------------------------------------
# (b) a failed provider job gives the hold back
# --------------------------------------------------------------------------

def test_a_failed_effect_restores_the_balance(shop, monkeypatch):
    """The effects door with the fal submit raising: the hold was taken
    (there is a hold entry), it was released (a release entry of the same
    size), nothing settled, nothing outstanding, and the balance is the
    grant again. tests/test_effects.py mocks `Charge.release`; this one
    lets the real ledger answer."""
    dsn, acct = shop["dsn"], shop["account_id"]
    monkeypatch.setenv("FAL_KEY", "fal-secret-key")
    monkeypatch.setattr(fal, "POLL_SECONDS", 0)
    ledger.grant(acct, 100, "promo", source_ref="signup:test", dsn=dsn)

    def boom(*a, **k):
        raise RuntimeError("fal job failed: content policy")

    monkeypatch.setattr(fal, "_submit_and_wait", boom)
    res = effects.run("remove-background", ["https://r2/a.jpg"], "", {}, usd=0.018,
                      account_id=acct, db_path=dsn)
    assert res["ok"] is False and "content policy" in res["error"]

    assert ledger.available(acct, dsn) == 100
    assert ledger.outstanding(acct, dsn) == 0
    holds, releases = _entries(dsn, acct, "hold"), _entries(dsn, acct, "release")
    assert [h["delta"] for h in holds] == [-10]          # the 10-credit floor
    assert [r["delta"] for r in releases] == [10]
    assert _entries(dsn, acct, "settle") == []
    assert all(row["drift"] == 0 and not row["orphan"]
               for row in ledger.reconcile(acct, dsn))


def test_a_failed_clip_render_restores_the_balance(shop, monkeypatch, tmp_path):
    """The clip door: `fal.generate_video` holding its own Charge at the
    estimate (an LTX 2.3 6 s 1080p clip is $0.36 -> 87 credits), the
    submit raising. The raise propagates -- the caller records the failed
    attempt -- and the money is back."""
    dsn, acct = shop["dsn"], shop["account_id"]
    monkeypatch.setenv("FAL_KEY", "fal-secret-key")
    monkeypatch.setattr(fal, "POLL_SECONDS", 0)
    monkeypatch.setattr(fal, "safe_prompt", lambda prompt, db_path=None, account_id=None: prompt)
    ledger.grant(acct, 200, "subscription", source_ref="in_1", dsn=dsn)

    def boom(*a, **k):
        raise RuntimeError("fal: 503 from the queue")

    monkeypatch.setattr(fal, "_submit_and_wait", boom)
    with pytest.raises(RuntimeError, match="503"):
        fal.generate_video("a rooftop at sunset", tmp_path / "clip.mp4", model="ltx2.3",
                           duration=6, approved=True, account_id=acct, db_path=dsn)

    assert ledger.available(acct, dsn) == 200
    assert ledger.outstanding(acct, dsn) == 0
    assert [h["delta"] for h in _entries(dsn, acct, "hold")] == [-87]
    assert [r["delta"] for r in _entries(dsn, acct, "release")] == [87]
    assert _entries(dsn, acct, "settle") == []
    assert not (tmp_path / "clip.mp4").exists()


def test_a_released_hold_cannot_be_settled_afterwards(shop):
    """The adapter releases on the raise; a caller that then settles
    anyway (a bug, a retry) must not re-debit. The ledger refuses and the
    Charge object is a no-op once done."""
    dsn, acct = shop["dsn"], shop["account_id"]
    ledger.grant(acct, 100, "promo", source_ref="signup:test", dsn=dsn)
    c = charging.Charge(acct, provider="fal", ref="r1.mp4", estimate_usd=0.10, dsn=dsn)
    c.take()
    assert ledger.available(acct, dsn) == 76                 # 0.10 x 2.4 = 24
    assert c.release("provider error") == 24
    assert c.settle() == 0                                   # the object is done
    with pytest.raises(ledger.LedgerError):
        ledger.settle(c.hold_id, credits=24, dsn=dsn)        # the ledger refuses too
    assert ledger.available(acct, dsn) == 100


# --------------------------------------------------------------------------
# (c) a replayed Stripe webhook grants once
# --------------------------------------------------------------------------

def _event(kind: str, obj: dict, eid: str = "evt_replayed") -> dict:
    return {"id": eid, "object": "event", "type": kind, "data": {"object": obj}}


def _topup(account_id: int) -> dict:
    return _event("checkout.session.completed", {
        "id": "cs_1", "object": "checkout.session", "mode": "payment",
        "customer": "cus_1", "payment_intent": "pi_1",
        "client_reference_id": str(account_id),
        "metadata": {"account_id": str(account_id), "item": "topup"},
    })


def _invoice(account_id: int, price: str, invoice: str = "in_1") -> dict:
    return _event("invoice.paid", {
        "id": invoice, "object": "invoice", "customer": "cus_1",
        "metadata": {"account_id": str(account_id)},
        "lines": {"data": [{"price": {"id": price}}]},
    })


@pytest.fixture
def prices(monkeypatch):
    for key, item in billing.products().items():
        monkeypatch.setenv(item.price_env, f"price_{key}")
        if billing.is_plan(key):
            monkeypatch.setenv(item.price_env_yearly, f"price_{key}_year")


def test_the_same_event_replayed_through_the_route_grants_once(shop, prices, monkeypatch):
    """Stripe delivers at least once. The route, with `billing.verify`
    stubbed to trust the body (the signature is Stripe's half; the grant
    guard is ours), fed the SAME event id twice: one lot, one balance."""
    dsn, acct = shop["dsn"], shop["account_id"]
    from app.main import app
    monkeypatch.setattr(billing, "verify", lambda payload, signature: json.loads(payload))
    client = TestClient(app)
    body = json.dumps(_topup(acct)).encode()

    first = client.post("/billing/webhook", content=body,
                        headers={"content-type": "application/json"})
    assert first.status_code == 200, first.text
    assert first.json()["action"] == "granted"
    again = client.post("/billing/webhook", content=body,
                        headers={"content-type": "application/json"})
    assert again.status_code == 200, again.text

    assert ledger.available(acct, dsn) == pricing.TOPUP.credits
    assert len(ledger.lots(acct, dsn)) == 1
    assert len(_entries(dsn, acct, "grant")) == 1


def test_two_deliveries_racing_each_other_grant_once(shop, prices):
    """Stripe can also deliver the same event to two workers at once. The
    grant reads for its source_ref INSIDE the account's advisory lock, so
    the second delivery finds the first's lot rather than nothing."""
    dsn, acct = shop["dsn"], shop["account_id"]
    event = _invoice(acct, "price_creator")
    barrier = threading.Barrier(2)
    results: list = [None, None]

    def deliver(i):
        barrier.wait()
        try:
            results[i] = billing.handle_event(event, dsn=dsn)
        except Exception as e:                   # noqa: BLE001
            results[i] = e

    threads = [threading.Thread(target=deliver, args=(i,)) for i in (0, 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert all(isinstance(r, dict) and r["action"] == "granted" for r in results), results
    assert results[0]["lot"] == results[1]["lot"]
    assert ledger.available(acct, dsn) == pricing.PLANS["creator"].credits
    assert len(ledger.lots(acct, dsn)) == 1
    assert accounts.plan_of(acct, dsn=dsn) == "creator"


def test_a_replayed_yearly_invoice_grants_month_one_once_and_schedules_once(shop, prices):
    """A yearly invoice is a schedule plus month one's lot; replayed, it
    must neither grant month one twice nor write a second schedule that
    would release twelve more months."""
    dsn, acct = shop["dsn"], shop["account_id"]
    event = _invoice(acct, "price_creator_year", invoice="in_year")
    first = billing.handle_event(event, dsn=dsn)
    again = billing.handle_event(event, dsn=dsn)
    assert first["action"] == again["action"] == "scheduled"
    assert first["released_now"] == 1 and again["released_now"] == 0
    assert ledger.available(acct, dsn) == pricing.PLANS["creator"].credits
    assert len(ledger.lots(acct, dsn)) == 1
    assert len(billing.schedules(acct, dsn=dsn)) == 1


def test_a_different_event_id_for_the_same_payment_still_grants_once(shop, prices):
    """The guard is the payment's own id (`source_ref`), not the event
    id: Stripe re-sends under a NEW event id after a failed delivery,
    and that must not be a second grant either."""
    dsn, acct = shop["dsn"], shop["account_id"]
    with db.connect(dsn) as conn:
        assert conn.execute("SELECT 1 FROM accounts WHERE id = %s", (acct,)).fetchone()
    one = _topup(acct)
    two = dict(one, id="evt_resent")
    billing.handle_event(one, dsn=dsn)
    billing.handle_event(two, dsn=dsn)
    assert ledger.available(acct, dsn) == pricing.TOPUP.credits
    assert len(ledger.lots(acct, dsn)) == 1
