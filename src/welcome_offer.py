"""The welcome offer (2026-11-10, Mike: "get people to sign up after using
credits ... maybe like a discount"): a Stripe coupon taken off the first
plan a workspace ever buys, shown on the studio's out-of-credits popup
(web/src/components/studio/upgrade-modal.tsx) and applied at Checkout.

Off until Mike makes the coupon in Stripe and names it in
`STRIPE_WELCOME_COUPON` (a percent or amount off, duration `once` for "your
first month"). Nothing about the offer is invented here: its size and its
duration are read off the coupon itself, so the popup can never promise a
discount Stripe will not give.

Who gets it: a workspace with no plan, not credit-exempt, that has never
paid (no subscription or purchase lot), buying a plan MONTHLY (a yearly
plan already carries its own 20% off). When a referred buyer also qualifies
for the affiliate discount (src/affiliates.py), this one wins: Checkout
takes one discount, and the welcome offer is the larger by design. The
partner's commission is booked off what the invoice actually charged, so
it is unaffected by which coupon was used.

Every read fails CLOSED here (no offer), the opposite of the consent page:
a missing discount costs a sale at worst, a wrong one costs money."""
from __future__ import annotations

import os
import sys
import time
from typing import Optional

from . import accounts, db

COUPON_ENV = "STRIPE_WELCOME_COUPON"

# the coupon is read from Stripe at most once an hour per process; a failed
# read is remembered for five minutes so a Stripe outage is not one call
# per balance poll
_TTL_OK = 3600.0
_TTL_FAIL = 300.0
_cache: dict[str, tuple[float, Optional[dict]]] = {}


def _log(message: str) -> None:
    print(f"[welcome-offer] {message}", file=sys.stderr)


def coupon_id() -> Optional[str]:
    return (os.environ.get(COUPON_ENV) or "").strip() or None


def _clear_cache() -> None:
    """For the suite: forget every coupon read."""
    _cache.clear()


def describe(coupon: Optional[str] = None) -> Optional[dict]:
    """The coupon as the popup prints it, or None when there is no coupon,
    Stripe is not configured, or the coupon cannot be read or is no longer
    valid. {"percent_off": 30 | None, "amount_off_cents": int | None,
    "duration": "once" | "repeating" | "forever", "months": int | None,
    "label": "30% off your first month"}."""
    coupon = coupon or coupon_id()
    if not coupon:
        return None
    now = time.monotonic()
    hit = _cache.get(coupon)
    if hit and hit[0] > now:
        return hit[1]
    info: Optional[dict] = None
    try:
        from . import billing
        raw = billing._stripe().Coupon.retrieve(coupon)
        info = _shape(dict(raw))
    except Exception as exc:  # noqa: BLE001 -- see the module docstring
        _log(f"coupon {coupon} unreadable: {exc}")
        info = None
    _cache[coupon] = (now + (_TTL_OK if info else _TTL_FAIL), info)
    return info


def _shape(raw: dict) -> Optional[dict]:
    if raw.get("valid") is False:
        return None
    pct = raw.get("percent_off")
    amt = raw.get("amount_off")
    if raw.get("currency") not in (None, "usd"):
        amt = None                       # the plans are priced in dollars
    if not pct and not amt:
        return None
    duration = raw.get("duration") or "once"
    months = raw.get("duration_in_months")
    if pct:
        pct = int(pct) if float(pct).is_integer() else float(pct)
        what = f"{pct}% off"
    else:
        dollars = amt / 100
        what = f"${dollars:,.0f} off" if dollars.is_integer() else f"${dollars:,.2f} off"
    if duration == "forever":
        when = "every month"
    elif duration == "repeating" and months and int(months) > 1:
        when = f"your first {int(months)} months"
    else:
        when = "your first month"
    return {"percent_off": pct or None, "amount_off_cents": int(amt) if amt and not pct else None,
            "duration": duration, "months": int(months) if months else None,
            "label": f"{what} {when}"}


def _has_paid(account_id: int, dsn: Optional[str]) -> bool:
    with db.connect(dsn) as conn:
        return conn.execute(
            "SELECT 1 FROM credit_lots WHERE account_id = %s AND kind IN ('subscription', 'purchase') "
            "LIMIT 1", (account_id,)).fetchone() is not None


def eligible(account_id: int, *, dsn: Optional[str] = None) -> bool:
    """Whether this workspace may have the welcome offer at all (any
    interval): a coupon is named, it has no plan, is not exempt, and has
    never paid. False on any read error."""
    if not coupon_id():
        return False
    try:
        if accounts.plan_of(account_id, dsn=dsn) or accounts.is_credit_exempt(account_id, dsn=dsn):
            return False
        return not _has_paid(account_id, dsn)
    except Exception as exc:  # noqa: BLE001 -- see the module docstring
        _log(f"eligible({account_id}) failed: {exc}")
        return False


def applies(account_id: int, interval: str, *, dsn: Optional[str] = None) -> bool:
    """Whether THIS checkout carries the welcome coupon: eligible, and a
    monthly plan."""
    return (interval or "month") == "month" and eligible(account_id, dsn=dsn)


def for_account(account_id: int, *, dsn: Optional[str] = None) -> Optional[dict]:
    """What the studio shows this workspace (the balance's `welcome_offer`):
    the coupon's description when the workspace is eligible and the coupon
    reads, else None."""
    if not eligible(account_id, dsn=dsn):
        return None
    return describe()
