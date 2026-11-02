"""Charging a chat turn that runs on a PRICED brain (2026-11-02).

Model text is free on a plan: its cost rides on the render markup (pricing.py,
"the brain is free"). The Claude brains (gemini_utils.BRAINS, `priced`) are the
one exception, Mike's call -- "you can choose two models like Higgsfield, it's
priced" -- so a turn on one of them takes credits.

THE SHAPE IS THE KEYFRAME RULE'S ("the price is the most that is charged"):
a turn's cost is not known before it runs (a tool loop makes one to seven model
calls), so the person is shown a CEILING and a typical figure, the ceiling is
held up front through the same ledger every render uses, and the turn settles to
what the model actually used, never above the ceiling. Nothing is charged for a
turn that fails: the hold is released.

  hold  ->  the turn (claude_client.tally() adds up what Claude cost)  ->  settle
                                                                       \\->  release

WHAT IS DELIBERATELY NOT HERE.
- No `mark_submitted`. That stamp is what tells the reaper "the provider was
  billed, leave this for a human". A chat turn that dies mid-way leaves no row
  to find and a few cents of provider cost; the right answer is to give the
  credit back, so a never-stamped text hold is released by `ledger.reap` and by
  `release_stale` below, which runs at the start of the account's next turn
  (nothing schedules `reap`).
- No new tables, no new route. The hold, the settle and the release are the
  ledger's own, under provider "text:<model>".
- No dollars. Everything this module says to a person is credits.
"""
from __future__ import annotations

import sys
import uuid
from datetime import timedelta
from typing import Optional

from . import claude_client, ledger, pricing, spend

PROVIDER = "text"
# an abandoned turn's hold is given back after this long (a turn takes seconds)
STALE_AFTER = timedelta(minutes=15)

# THE MOST A MESSAGE COSTS, in credits, per brain (1 credit = 1 cent of price).
# Sized so a long tool-loop turn on a long conversation fits (seven model calls
# on a ~20k-token prompt, mostly cache reads), and low enough that the trial's
# 100 credits still buy several messages. Mike's to move.
CEILING_CREDITS = {"claude-sonnet": 40, "claude-opus": 80}

# A TYPICAL message, for the picker's "about N" line and nothing else: a ~20k
# token prompt of which the instructions and tools (~13k) are a warm cache hit,
# and a ~700-token answer. Measured 2026-11-02 off the real composer prompt
# (29k chars of instructions + 22k chars of tool specs, ~3.8 chars a token).
TYPICAL_PROMPT_TOKENS = 20_000
TYPICAL_CACHED_TOKENS = 13_000
TYPICAL_OUTPUT_TOKENS = 700


def ceiling(brain_key: str) -> int:
    return int(CEILING_CREDITS.get(brain_key) or 0)


def model_of(brain_key: str) -> str:
    from . import gemini_utils
    return gemini_utils.resolve_brain(brain_key)["model"]


def typical_credits(brain_key: str) -> int:
    """About what one message costs on this brain, in credits."""
    model = model_of(brain_key)
    usd = spend.estimate_cost(model, prompt_tokens=TYPICAL_PROMPT_TOKENS,
                              cached_tokens=TYPICAL_CACHED_TOKENS,
                              output_tokens=TYPICAL_OUTPUT_TOKENS)
    return pricing.text_credits(usd, model) if usd is not None else 0


def picker_note(brain_key: str, note: str) -> str:
    """The line under a brain's name in the composer's picker. A free brain
    keeps its own note; a priced one says what a message costs BEFORE it is
    sent (the repo's rule: nothing spends without a price the person saw)."""
    from . import gemini_utils
    if not gemini_utils.BRAINS.get(brain_key, {}).get("priced"):
        return note
    return (f"{note} · about {typical_credits(brain_key)} credits a message, "
            f"never more than {ceiling(brain_key)}")


class Turn:
    """One held, not-yet-settled chat turn."""

    __slots__ = ("account_id", "brain", "model", "ceiling", "ref", "hold_id", "dsn", "_done")

    def __init__(self, account_id: int, brain: str, model: str, cap: int, ref: str,
                 hold_id: Optional[int], dsn: Optional[str]) -> None:
        self.account_id, self.brain, self.model = account_id, brain, model
        self.ceiling, self.ref, self.hold_id, self.dsn = cap, ref, hold_id, dsn
        self._done = False

    def settle(self, tally: "claude_client.Tally") -> int:
        """Close the hold at what the turn used, never above the ceiling.
        Returns the credits debited (0 for an exempt account, which took no
        hold). A turn whose calls could not be priced is charged the ceiling:
        an unreadable bill is not a free turn."""
        if self._done or self.hold_id is None:
            self._done = True
            return 0
        self._done = True
        if tally.calls == 0:
            ledger.release(self.hold_id, "the turn made no Claude call", dsn=self.dsn)
            return 0
        if tally.unpriced:
            credits = self.ceiling
        else:
            credits = min(pricing.text_credits(tally.usd, self.model), self.ceiling)
        return ledger.settle(self.hold_id, credits=credits, cap=self.ceiling, dsn=self.dsn)

    def release(self, reason: str) -> int:
        """Give the whole hold back (the turn failed; nothing is charged)."""
        if self._done or self.hold_id is None:
            self._done = True
            return 0
        self._done = True
        try:
            return ledger.release(self.hold_id, reason, dsn=self.dsn)
        except Exception as exc:               # noqa: BLE001 -- the reaper gives it back
            print(f"[text_charge] release of hold {self.hold_id} failed: {exc}", file=sys.stderr)
            return 0


def begin(account_id: Optional[int], brain_key: str, *,
          dsn: Optional[str] = None) -> Optional[Turn]:
    """Hold the ceiling for a turn on `brain_key`, or None when the brain is
    free (or unavailable, which resolves to the free default). Raises
    `ledger.InsufficientCredit` BEFORE any model call when the balance cannot
    cover the ceiling, so the route can answer 402."""
    from . import gemini_utils
    if not gemini_utils.is_priced(brain_key):
        return None
    cap = ceiling(brain_key)
    if cap <= 0:
        return None
    model = model_of(brain_key)
    ledger.ensure(dsn)
    if account_id is not None:
        try:
            ledger.release_stale_holds(PROVIDER, STALE_AFTER, account_id=account_id, dsn=dsn)
        except Exception as exc:               # noqa: BLE001 -- housekeeping, never a gate
            print(f"[text_charge] stale sweep failed: {exc}", file=sys.stderr)
    ref = f"text-{uuid.uuid4().hex}"
    hold_id = ledger.hold_for_render(account_id, ref=ref, provider=f"{PROVIDER}:{model}",
                                     estimate_usd=None, credits=cap, dsn=dsn)
    return Turn(account_id, brain_key, model, cap, ref, hold_id, dsn)
