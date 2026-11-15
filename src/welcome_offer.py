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
plan already carries its own 20% off), on a solo plan the margin guard
below allows. A buyer who came through an affiliate link gets the affiliate
discount instead, never both (the partner's commission on top of a
discounted first month loses money).

Every read fails CLOSED here (no offer), the opposite of the consent page:
a missing discount costs a sale at worst, a wrong one costs money."""
from __future__ import annotations

import os
import sys
import time
from fractions import Fraction
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


# --- the margin guard (2026-11-14, Mike: "make sure im not losing money on this")
#
# A discount is only offered on a plan where it CANNOT lose money: the first
# month is priced for the worst customer -- one who spends every credit on
# the thinnest-margin model (Veo 3.1 at 1.15x today) -- after Stripe's fee
# and the assistant's monthly estimate (pricing.BRAIN_USD). With today's
# markups that leaves room for only a few percent, so a bigger coupon is
# simply not offered on the plans it would lose on, until Mike either raises
# the thinnest markup or names an accepted loss below. `report` prints the
# numbers.
ALLOW_LOSS_ENV = "PHANTRA_WELCOME_ALLOW_LOSS_USD"


def allowed_loss_usd() -> Fraction:
    """The worst-case first-month loss Mike has accepted per new customer
    (`PHANTRA_WELCOME_ALLOW_LOSS_USD`, dollars); 0, and never negative, when
    unset or unreadable."""
    try:
        return max(Fraction(str((os.environ.get(ALLOW_LOSS_ENV) or "0").strip())), Fraction(0))
    except (ValueError, ZeroDivisionError):
        return Fraction(0)


def thinnest_markup() -> Fraction:
    """The lowest markup anything in the studio is sold at."""
    from . import pricing
    return min(Fraction(str(m)) for m in (pricing.MARKUP, *pricing.MARKUP_BY_MODEL.values()))


def worst_first_month_usd(plan_key: str, info: Optional[dict]) -> Optional[Fraction]:
    """What the plan's first month nets in the worst case with this
    discount: the price paid, less Stripe, less the assistant's estimate,
    less every credit spent at the thinnest markup. None for no such plan."""
    from . import pricing
    plan = pricing.PLANS.get(plan_key)
    if plan is None:
        return None
    price = Fraction(plan.monthly_usd)
    if info and info.get("percent_off"):
        price = price * (1 - Fraction(str(info["percent_off"])) / 100)
    elif info and info.get("amount_off_cents"):
        price = max(price - Fraction(int(info["amount_off_cents"]), 100), Fraction(0))
    stripe = price * Fraction(pricing.STRIPE_PCT) + Fraction(pricing.STRIPE_FIXED_USD)
    delivery = Fraction(plan.credits * pricing.CREDIT_CENTS, 100) / thinnest_markup()
    return price - stripe - pricing.BRAIN_USD.get(plan_key, 0) - delivery


def safe_on(plan_key: str, info: Optional[dict]) -> bool:
    """Whether this discount may be offered on this plan: a solo plan whose
    worst first month loses no more than Mike has accepted."""
    from . import pricing
    plan = pricing.PLANS.get(plan_key)
    if plan is None or plan.seats > 1:      # Agency is sold by hand, not discounted here
        return False
    worst = worst_first_month_usd(plan_key, info)
    return worst is not None and worst >= -allowed_loss_usd()


def safe_plans(info: Optional[dict]) -> list[str]:
    from . import pricing
    return [k for k in pricing.PLANS if safe_on(k, info)]


def report() -> str:
    """The guard's numbers for the coupon named now (or a 30% example)."""
    from . import pricing
    info = describe() or _shape({"percent_off": 30, "duration": "once"})
    lines = [f"welcome offer: {info['label']}  (coupon {coupon_id() or 'not set: showing 30% as an example'})",
             f"thinnest markup: {float(thinnest_markup()):.2f}x   accepted loss: ${float(allowed_loss_usd()):.2f}",
             "worst first month (every credit on the thinnest model, after Stripe and the assistant):"]
    for key, plan in pricing.PLANS.items():
        worst = worst_first_month_usd(key, info)
        full = worst_first_month_usd(key, None)
        verdict = "OFFERED" if safe_on(key, info) else "withheld"
        lines.append(f"  {plan.name:9} ${plan.monthly_usd:>4}/mo  with offer {float(worst):+8.2f}"
                     f"   full price {float(full):+8.2f}   -> {verdict}")
    return "\n".join(lines)


def applies(account_id: int, interval: str, plan_key: Optional[str] = None, *,
            dsn: Optional[str] = None) -> bool:
    """Whether THIS checkout carries the welcome coupon: eligible, a monthly
    plan, and (when the plan is named) one the margin guard allows."""
    if (interval or "month") != "month" or not eligible(account_id, dsn=dsn):
        return False
    return plan_key is None or safe_on(plan_key, describe())


def for_account(account_id: int, *, dsn: Optional[str] = None) -> Optional[dict]:
    """What the studio shows this workspace (the balance's `welcome_offer`):
    the coupon's description and the plans it is offered on, when the
    workspace is eligible, the coupon reads and the guard allows at least
    one plan; else None."""
    if not eligible(account_id, dsn=dsn):
        return None
    info = describe()
    if not info:
        return None
    plans = safe_plans(info)
    return {**info, "plans": plans} if plans else None


if __name__ == "__main__":
    print(report())
