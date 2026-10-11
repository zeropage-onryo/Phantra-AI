"""An empty balance is said in a way the page can act on.

invideo's loudest complaint is the agent going quiet when the credits run
out. The server already writes a sentence of its own for that
(src/charge.py); the studio recognises it by plain phrases
(web/src/lib/out-of-credits.ts) and puts the way to add credits beside it.
This is the wire between the two: reword a refusal here without the page
knowing its new words, and this fails.
"""
import re
from pathlib import Path

from src import charge, failures, ledger

TS = Path(__file__).resolve().parent.parent / "web" / "src" / "lib" / "out-of-credits.ts"


def _phrases() -> list:
    found = re.search(r"export const PHRASES = \[(.*?)\];", TS.read_text(), re.S)
    assert found, "PHRASES moved or changed shape in out-of-credits.ts"
    phrases = re.findall(r'"([^"]+)"', found.group(1))
    assert phrases and all(p == p.lower() for p in phrases)
    return phrases


def _recognised(text: str) -> bool:
    return any(p in text.lower() for p in _phrases())


REFUSALS = [
    charge.refusal(ledger.InsufficientCredit(1, 10, 4), "this still"),
    charge.refusal(ledger.InsufficientCredit(1, 1365, 0)),
    charge.refusal(ledger.InsufficientCredit(1, 96, 0), "this effect"),
    charge.CREATE_REFUSAL,
]


def test_every_refusal_the_server_writes_is_one_the_page_recognises():
    for said in REFUSALS:
        assert _recognised(said), said


def test_they_reach_the_page_as_written():
    """`failures.plain` rewords a PROVIDER's error; the studio's own
    sentence about the person's own balance passes through untouched,
    whatever was being made."""
    for said in REFUSALS:
        for what in ("The still", "The clip", "The effect"):
            assert failures.plain(said, what) == said


def test_a_providers_balance_error_is_never_shown_as_the_customers():
    """fal's "Top up your balance at fal.ai" is about the STUDIO's account.
    It is reworded before it reaches the page, and neither form may be
    read as a reason for the customer to buy credits."""
    raw = ('HTTP Error 403: Forbidden -- {"detail":"User is locked. Reason: Exhausted '
           'balance. Top up your balance at fal.ai/dashboard/billing."}')
    assert not _recognised(raw)
    for what in ("The still", "The clip", "The effect"):
        shown = failures.plain(raw, what)
        assert not _recognised(shown) and "fal.ai" not in shown
        assert shown.endswith(failures.NOT_CHARGED)


def test_the_numbers_are_in_the_sentence_the_page_reads_them_from():
    said = charge.refusal(ledger.InsufficientCredit(1, 1365, 0), "this render")
    assert re.search(r"needs\s+1365\s+and the account has\s+0", said)
