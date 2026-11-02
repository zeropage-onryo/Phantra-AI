"""A chat turn on a priced Claude brain (src/text_charge.py): hold the ceiling,
settle to what the turn used, release a failure. Against the throwaway Postgres.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from conftest import seed_two  # noqa: E402

from src import accounts, claude_client, db, gemini_utils, generative, ledger, pricing, text_charge


@pytest.fixture
def led(pg, monkeypatch):
    monkeypatch.setenv(gemini_utils.CLAUDE_BRAINS_ENV, "1")
    monkeypatch.setenv(claude_client.KEY_ENV, "sk-test")
    accounts.init(pg)
    seed_two("mike@example.com", dsn=pg)
    generative.init(pg)
    ledger.init(pg)
    with db.connect(pg) as conn:
        account = int(conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"])
    return pg, account


def tally(calls=1, usd=0.01, unpriced=0):
    t = claude_client.Tally()
    t.calls, t.usd, t.unpriced = calls, usd, unpriced
    return t


# --- pricing ----------------------------------------------------------------

def test_text_credits_has_a_floor_of_one_not_ten():
    assert pricing.text_credits(0.0001, "claude-sonnet-5-5") == 1
    assert pricing.text_credits(0.0001) == 1 < pricing.CREDIT_FLOOR
    assert pricing.text_credits(0.05, "claude-sonnet-5-5") == 12     # 5c * 2.4, to the cent


def test_the_picker_says_the_price_before_the_send():
    sonnet = text_charge.picker_note("claude-sonnet", "Balanced")
    opus = text_charge.picker_note("claude-opus", "Deepest reasoning")
    assert "credits a message" in sonnet and "never more than 40" in sonnet
    assert "never more than 80" in opus
    assert text_charge.picker_note("fast", "Quick") == "Quick"        # free brains unchanged


def test_brain_options_hides_claude_until_it_is_on(monkeypatch):
    monkeypatch.delenv(gemini_utils.CLAUDE_BRAINS_ENV, raising=False)
    assert {"claude-sonnet", "claude-opus"}.isdisjoint(o["id"] for o in gemini_utils.brain_options())
    assert gemini_utils.resolve_brain("claude-opus")["model"] == gemini_utils.resolve_brain(
        gemini_utils.DEFAULT_BRAIN)["model"]
    monkeypatch.setenv(gemini_utils.CLAUDE_BRAINS_ENV, "1")
    monkeypatch.setenv(claude_client.KEY_ENV, "sk-test")
    opts = {o["id"]: o for o in gemini_utils.brain_options()}
    assert opts["claude-sonnet"]["priced"] and "credits" in opts["claude-sonnet"]["note"]
    assert not opts["fast"].get("priced")


def test_a_claude_brain_with_no_key_is_not_offered(monkeypatch):
    monkeypatch.setenv(gemini_utils.CLAUDE_BRAINS_ENV, "1")
    monkeypatch.delenv(claude_client.KEY_ENV, raising=False)
    assert not gemini_utils.brain_available("claude-sonnet")


# --- the hold ---------------------------------------------------------------

def test_a_free_brain_takes_no_hold(led):
    dsn, account = led
    assert text_charge.begin(account, "fast", dsn=dsn) is None


def test_begin_refuses_an_empty_balance_before_any_model_call(led):
    dsn, account = led
    with pytest.raises(ledger.InsufficientCredit):
        text_charge.begin(account, "claude-sonnet", dsn=dsn)


def test_settle_charges_what_was_used_not_the_ceiling(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t1", dsn=dsn)
    turn = text_charge.begin(account, "claude-sonnet", dsn=dsn)
    assert ledger.available(account, dsn) == 500 - text_charge.ceiling("claude-sonnet")
    spent = turn.settle(tally(usd=0.05))
    assert spent == pricing.text_credits(0.05, turn.model)
    assert ledger.available(account, dsn) == 500 - spent
    assert turn.settle(tally(usd=9)) == 0                           # settles once


def test_settle_never_exceeds_the_ceiling(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t2", dsn=dsn)
    turn = text_charge.begin(account, "claude-sonnet", dsn=dsn)
    assert turn.settle(tally(usd=50.0)) == text_charge.ceiling("claude-sonnet")
    assert ledger.available(account, dsn) == 500 - text_charge.ceiling("claude-sonnet")


def test_an_unpriced_call_is_charged_the_ceiling(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t3", dsn=dsn)
    turn = text_charge.begin(account, "claude-opus", dsn=dsn)
    assert turn.settle(tally(usd=0.0, unpriced=1)) == text_charge.ceiling("claude-opus")


def test_a_turn_with_no_claude_call_costs_nothing(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t4", dsn=dsn)
    turn = text_charge.begin(account, "claude-sonnet", dsn=dsn)
    assert turn.settle(tally(calls=0, usd=0)) == 0
    assert ledger.available(account, dsn) == 500


def test_a_failed_turn_gives_the_whole_hold_back(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t5", dsn=dsn)
    turn = text_charge.begin(account, "claude-sonnet", dsn=dsn)
    turn.release("the turn failed")
    assert ledger.available(account, dsn) == 500
    assert turn.settle(tally()) == 0                                # no charge after a release


def test_an_abandoned_hold_is_released_at_the_next_turn(led):
    dsn, account = led
    ledger.grant(account, 100, "purchase", source_ref="pi_t6", dsn=dsn)
    text_charge.begin(account, "claude-sonnet", dsn=dsn)            # worker died: never settled
    assert ledger.available(account, dsn) == 100 - 40
    assert ledger.release_stale_holds("text", timedelta(seconds=0), account_id=account, dsn=dsn)
    assert ledger.available(account, dsn) == 100


def test_the_sweep_leaves_other_providers_and_other_accounts_alone(led):
    dsn, account = led
    ledger.grant(account, 500, "purchase", source_ref="pi_t7", dsn=dsn)
    ledger.hold_for_render(account, ref="r1", provider="fal:kling", estimate_usd=None,
                           credits=50, dsn=dsn)
    assert ledger.release_stale_holds("text", timedelta(seconds=0), account_id=account, dsn=dsn) == []
    assert ledger.release_stale_holds("text", timedelta(seconds=0), account_id=None, dsn=dsn) == []
    assert ledger.available(account, dsn) == 450
