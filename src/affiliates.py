"""
The affiliate program (2026-10-26, Mike's call: "lets have this affiliate
program up and ready by the morning"; docs/AFFILIATES.md has the terms in
plain words and the launch checklist).

THE SHAPE, IN ONE PARAGRAPH. A creator applies (`apply`), Mike reads the
channel and approves (`approve`, a CLI), and the creator gets a code and a
link (`phantra.ai/?ref=<code>`). A visitor who arrives on that link and
signs up is ATTRIBUTED to the creator (`attribute`). When that account
pays a subscription invoice, the Stripe webhook calls `on_invoice_paid`,
which books a COMMISSION that is HELD for 60 days (the refund window). A
commission still standing after the hold is paid (`release_due`): as
credits on the partner's own account by default, as cash only when Mike
turns that on for a partner. Cash is paid by hand (`python -m
src.affiliates payouts`, then `mark-paid`); nothing here moves money.

THE TIERS (Mike, 2026-10-26). Rate and window are by tier:

    starter   20% for 3 months    everyone, on approval
    pro       30% for 6 months    10 paying referrals
    partner   35% for 12 months   50 paying referrals

A tier is read off the partner's count of PAYING referrals at the moment a
referral makes its FIRST payment and is then LOCKED on that referral: a
partner who reaches Pro keeps Starter terms on the people already
referred and earns Pro terms on the next ones. That keeps every payout
knowable the day the referral pays, and it is the cheaper reading. The
thresholds (10 and 50) are the build's assumption -- Mike gave only "at
least 50" for Partner -- and are the two numbers in TIERS below.

WHAT A COMMISSION IS PAID ON. The invoice's amount actually paid, before
tax (`invoice_net_cents`): a 20%-off first month pays on the discounted
amount, a free invoice pays nothing, tax is never commissionable. Only
SUBSCRIPTION invoices count; a top-up pack is not commissionable. A yearly
invoice covers 12 months in one payment, so the window is counted in
MONTHS COVERED: a Starter partner's yearly referral earns 20% of 3/12 of
the payment, the same as three monthly payments would have, never 20% of
the whole year.

WHAT IT COSTS. Credits are paid at face value, 1 credit = 1 cent, and a
credit costs Phantra about 42% of face when redeemed (pricing.MARKUP 2.4),
so the top tier in credits is about 14.6% of the referred revenue. The
program only pays out of revenue that has already cleared Stripe and sat
out the hold; it cannot spend money it has not taken.

THE ANTI-ABUSE RULES are in `attribute` (no self-referral, one attribution
per account, none after the first payment, only to an approved partner)
and in `on_refund` (a refund inside the hold voids or scales the
commission). Chargebacks are not a separate event here: the 60-day hold
is what absorbs them.

THREE OWNED TABLES (db.OWNED_TABLES), each keyed by the PARTNER's account
because the earnings are theirs: `affiliate_partners` (one per account),
`affiliate_referrals` (one per referred account, UNIQUE), and
`affiliate_commissions` (one per Stripe invoice, UNIQUE on the invoice id,
which is what makes a redelivered webhook book nothing twice).

Nothing in this module raises into the payment path: `on_invoice_paid` and
`on_refund` are called from billing.handle_event inside a try/except that
logs, so a bug here can never keep a customer from receiving the credit
they paid for.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import db

# --------------------------------------------------------------------------
# the terms -- every number the program pays by
# --------------------------------------------------------------------------

TERMS_VERSION = "2026-10-26"

HOLD_DAYS = 60                  # a commission waits this long (refund window)
COOKIE_DAYS = 60                # how long a visit to a partner's link is remembered
CREDIT_EXPIRY_MONTHS = 12       # earned credits last a year (a plan's credits last two months)
MIN_CASH_PAYOUT_CENTS = 5000    # cash is paid out in batches of at least $50
BUYER_DISCOUNT_PERCENT = 20     # off the referred buyer's first MONTHLY payment
COUPON_ENV = "STRIPE_AFFILIATE_COUPON"   # the Stripe coupon id: 20% off, duration once

PAYOUT_MODES = ("credits", "cash")
STATUSES = ("pending", "approved", "rejected", "suspended")
CODE_MIN, CODE_MAX = 3, 40
MAX_TEXT = 600
MAX_URL = 300


@dataclass(frozen=True)
class Tier:
    key: str
    label: str
    rate_bp: int          # basis points: 2000 = 20%
    window_months: int    # how many months of a referral's payments earn
    min_paying: int       # paying referrals needed to START earning at this tier

    @property
    def percent(self) -> float:
        return self.rate_bp / 100.0


TIERS = (
    Tier("starter", "Starter", 2000, 3, 0),
    Tier("pro", "Pro", 3000, 6, 10),
    Tier("partner", "Partner", 3500, 12, 50),
)
TIER_BY_KEY = {t.key: t for t in TIERS}

RESERVED_CODES = frozenset({
    "admin", "api", "app", "billing", "help", "login", "phantra", "pricing", "root",
    "settings", "signin", "signup", "studio", "support", "team", "www", "affiliate",
    "affiliates", "partner", "partners", "ref", "referral",
})


def tier_for_count(paying_referrals: int) -> Tier:
    """The best tier a partner with this many paying referrals has earned."""
    best = TIERS[0]
    for tier in TIERS:
        if paying_referrals >= tier.min_paying:
            best = tier
    return best


def next_tier(tier: Tier) -> Optional[Tier]:
    keys = [t.key for t in TIERS]
    i = keys.index(tier.key)
    return TIERS[i + 1] if i + 1 < len(TIERS) else None


def public_terms() -> dict:
    """What the public page and the application form print. One source, so
    the page can never promise a rate the code does not pay."""
    return {
        "version": TERMS_VERSION,
        "tiers": [{"key": t.key, "label": t.label, "percent": t.percent,
                   "months": t.window_months, "min_paying": t.min_paying}
                  for t in TIERS],
        "hold_days": HOLD_DAYS,
        "cookie_days": COOKIE_DAYS,
        "buyer_discount_percent": BUYER_DISCOUNT_PERCENT,
        "credit_expiry_months": CREDIT_EXPIRY_MONTHS,
        "min_cash_payout_dollars": MIN_CASH_PAYOUT_CENTS // 100,
    }


CATALOG_PATH = "web/src/content/affiliate.json"


def export_terms(path: str = CATALOG_PATH) -> str:
    """Write public_terms() where the public page imports it. The committed
    file IS this; tests/test_affiliates.py fails when they disagree, so the
    page can never print a rate the code does not pay."""
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(public_terms(), f, indent=2)
        f.write("\n")
    return path


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS affiliate_partners (
    id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    account_id    BIGINT NOT NULL,
    code          TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',
    payout_mode   TEXT NOT NULL DEFAULT 'credits',
    channel_url   TEXT NOT NULL DEFAULT '',
    audience      TEXT NOT NULL DEFAULT '',
    plan          TEXT NOT NULL DEFAULT '',
    terms_version TEXT NOT NULL DEFAULT '',
    note          TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at   TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS affiliate_partners_account_idx
    ON affiliate_partners (account_id);
CREATE UNIQUE INDEX IF NOT EXISTS affiliate_partners_code_idx
    ON affiliate_partners (lower(code)) WHERE code IS NOT NULL;

CREATE TABLE IF NOT EXISTS affiliate_referrals (
    id                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    account_id          BIGINT NOT NULL,
    partner_id          BIGINT NOT NULL,
    referred_account_id BIGINT NOT NULL,
    attributed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    first_paid_at       TIMESTAMPTZ,
    tier_key            TEXT,
    rate_bp             INTEGER,
    window_months       INTEGER,
    months_paid         INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS affiliate_referrals_referred_idx
    ON affiliate_referrals (referred_account_id);
CREATE INDEX IF NOT EXISTS affiliate_referrals_partner_idx
    ON affiliate_referrals (account_id, partner_id);

CREATE TABLE IF NOT EXISTS affiliate_commissions (
    id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    account_id       BIGINT NOT NULL,
    partner_id       BIGINT NOT NULL,
    referral_id      BIGINT NOT NULL,
    invoice_ref      TEXT NOT NULL,
    paid_cents       INTEGER NOT NULL,
    months_covered   INTEGER NOT NULL,
    months_counted   INTEGER NOT NULL,
    rate_bp          INTEGER NOT NULL,
    commission_cents INTEGER NOT NULL,
    status           TEXT NOT NULL DEFAULT 'held',
    hold_until       TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at      TIMESTAMPTZ,
    payout           TEXT,
    lot_id           BIGINT,
    paid_at          TIMESTAMPTZ,
    payout_ref       TEXT NOT NULL DEFAULT '',
    note             TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS affiliate_commissions_invoice_idx
    ON affiliate_commissions (invoice_ref);
CREATE INDEX IF NOT EXISTS affiliate_commissions_due_idx
    ON affiliate_commissions (hold_until) WHERE status = 'held';
CREATE INDEX IF NOT EXISTS affiliate_commissions_partner_idx
    ON affiliate_commissions (account_id, partner_id);
"""

_ready: set = set()
_ready_lock = threading.Lock()


def init(dsn: Optional[str] = None) -> None:
    """Create the three tables and own them. Idempotent; the app lifespan
    and tests/test_tenancy.py::_init_everything both run it."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        for table in ("affiliate_partners", "affiliate_referrals", "affiliate_commissions"):
            db.own_table(conn, table)


def ensure(dsn: Optional[str] = None) -> None:
    """init() once per process and database, for a process whose start did
    not run it (a test's fresh schema, the CLI) -- the billing shape."""
    key = db.resolve_dsn(dsn)
    if key in _ready:
        return
    with _ready_lock:
        if key not in _ready:
            db.run_init(lambda: init(dsn), dsn)
            _ready.add(key)


class AffiliateError(ValueError):
    """A refusal with a machine-readable `code`, for the route to answer."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _log(message: str) -> None:
    print(f"[affiliates] {message}", file=sys.stderr)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat(timespec="seconds") if hasattr(value, "isoformat") else str(value)


def _partner_lock(conn, partner_id: int) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"affiliate:{partner_id}",))


# --------------------------------------------------------------------------
# codes
# --------------------------------------------------------------------------

_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def normalize_code(raw: Optional[str]) -> Optional[str]:
    """A code as typed or carried in a cookie -> its stored form, or None
    when it cannot be a code. Case-insensitive, never trusted further."""
    code = (raw or "").strip().lower()
    if not (CODE_MIN <= len(code) <= CODE_MAX) or not _CODE_RE.match(code):
        return None
    return code


def _code_base(slug: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (slug or "").lower()).strip("-")[:24].strip("-")
    if len(base) < CODE_MIN or base in RESERVED_CODES:
        base = f"creator-{base}" if base else "creator"
    return base


def link(code: str) -> str:
    """The shareable address. The public site, never the API origin."""
    base = (os.environ.get("AFFILIATE_LINK_BASE") or os.environ.get("STUDIO_URL")
            or os.environ.get("SITE_URL") or "https://phantra.ai").strip().rstrip("/")
    return f"{base}/?ref={code}"


# --------------------------------------------------------------------------
# applying and approving
# --------------------------------------------------------------------------

def _clean_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise AffiliateError("channel_required", "add a link to your channel or profile")
    if not re.match(r"^https?://[^\s/]+\.[^\s/]+", value, re.I) or len(value) > MAX_URL:
        raise AffiliateError("bad_channel", "the channel must be a full link starting with https://")
    return value


def _clean_text(value: Optional[str], field: str, *, required: bool = False) -> str:
    value = " ".join((value or "").split())
    if required and not value:
        raise AffiliateError(f"{field}_required", f"tell us a little about your {field}")
    return value[:MAX_TEXT]


def get_partner(account_id: int, *, dsn: Optional[str] = None) -> Optional[dict]:
    ensure(dsn)
    with db.connect(dsn) as conn:
        row = conn.execute(
            "SELECT * FROM affiliate_partners WHERE account_id = %s", (account_id,)).fetchone()
        return dict(row) if row else None


def apply(account_id: int, *, channel_url: str, audience: str, plan: str,
          accept_terms: bool, dsn: Optional[str] = None) -> dict:
    """Record an application. One per account: applying again returns the
    existing one untouched (a rejected application is final until Mike
    reopens it by hand). Raises AffiliateError on a bad form."""
    if not accept_terms:
        raise AffiliateError("terms_required", "accept the program terms to apply")
    url = _clean_url(channel_url)
    audience = _clean_text(audience, "audience", required=True)
    plan = _clean_text(plan, "plan", required=True)
    ensure(dsn)
    with db.connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"affiliate-apply:{account_id}",))
        row = conn.execute(
            "SELECT * FROM affiliate_partners WHERE account_id = %s", (account_id,)).fetchone()
        if row:
            return dict(row)
        row = conn.execute(
            "INSERT INTO affiliate_partners (account_id, channel_url, audience, plan, terms_version) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (account_id, url, audience, plan, TERMS_VERSION)).fetchone()
        return dict(row)


def _resolve_partner(conn, who: str) -> dict:
    """A partner by account slug, code or numeric partner id (the CLI's
    way of naming one)."""
    who = (who or "").strip()
    row = None
    if who.isdigit():
        row = conn.execute("SELECT * FROM affiliate_partners WHERE id = %s", (int(who),)).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT p.* FROM affiliate_partners p JOIN accounts a ON a.id = p.account_id "
            "WHERE a.slug = %s", (who,)).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT * FROM affiliate_partners WHERE lower(code) = %s", (who.lower(),)).fetchone()
    if row is None:
        raise AffiliateError("no_such_partner", f"no affiliate matches {who!r}")
    return dict(row)


def approve(who: str, *, code: Optional[str] = None, dsn: Optional[str] = None) -> dict:
    """Approve an application (or re-approve a suspended partner): mints the
    code on first approval. `code` may be chosen; otherwise it comes from
    the account's slug. Raises AffiliateError."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        partner = _resolve_partner(conn, who)
        _partner_lock(conn, int(partner["id"]))
        chosen = partner["code"]
        if code:
            norm = normalize_code(code)
            if norm is None or norm in RESERVED_CODES:
                raise AffiliateError("bad_code", f"{code!r} cannot be a code")
            chosen = norm
        elif not chosen:
            slug = conn.execute("SELECT slug FROM accounts WHERE id = %s",
                                (partner["account_id"],)).fetchone()["slug"]
            base, n = _code_base(slug), 1
            chosen = base
            while conn.execute("SELECT 1 FROM affiliate_partners WHERE lower(code) = %s",
                               (chosen,)).fetchone():
                n += 1
                chosen = f"{base}-{n}"
        clash = conn.execute(
            "SELECT 1 FROM affiliate_partners WHERE lower(code) = %s AND id <> %s",
            (chosen.lower(), partner["id"])).fetchone()
        if clash:
            raise AffiliateError("code_taken", f"the code {chosen!r} is already in use")
        row = conn.execute(
            "UPDATE affiliate_partners SET status = 'approved', code = %s, reviewed_at = now() "
            "WHERE id = %s AND account_id = %s RETURNING *",
            (chosen, partner["id"], partner["account_id"])).fetchone()
        return dict(row)


def set_status(who: str, status: str, *, note: str = "", dsn: Optional[str] = None) -> dict:
    """reject / suspend. A suspended partner earns nothing new and is paid
    nothing until re-approved; commissions already held stay held."""
    if status not in ("rejected", "suspended"):
        raise AffiliateError("bad_status", f"status must be rejected or suspended, not {status!r}")
    ensure(dsn)
    with db.connect(dsn) as conn:
        partner = _resolve_partner(conn, who)
        row = conn.execute(
            "UPDATE affiliate_partners SET status = %s, note = %s, reviewed_at = now() "
            "WHERE id = %s AND account_id = %s RETURNING *",
            (status, note[:MAX_TEXT], partner["id"], partner["account_id"])).fetchone()
        return dict(row)


def set_payout_mode(who: str, mode: str, *, dsn: Optional[str] = None) -> dict:
    """Credits is the default; cash is Mike's per-partner switch, set once he
    trusts the partner. Takes effect on commissions released AFTER the
    change (a commission is paid the way its partner was set when the hold
    ended)."""
    if mode not in PAYOUT_MODES:
        raise AffiliateError("bad_mode", f"payout must be one of {PAYOUT_MODES}")
    ensure(dsn)
    with db.connect(dsn) as conn:
        partner = _resolve_partner(conn, who)
        row = conn.execute(
            "UPDATE affiliate_partners SET payout_mode = %s WHERE id = %s AND account_id = %s "
            "RETURNING *", (mode, partner["id"], partner["account_id"])).fetchone()
        return dict(row)


# --------------------------------------------------------------------------
# attribution
# --------------------------------------------------------------------------

def _has_paid(conn, account_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM credit_lots WHERE account_id = %s AND kind IN ('subscription', 'purchase') "
        "LIMIT 1", (account_id,)).fetchone() is not None


def attribute(account_id: int, code: Optional[str], *, dsn: Optional[str] = None) -> dict:
    """Credit a new account's future payments to the partner who owns
    `code`. Returns {"attributed": bool, "reason": str}. Never raises for a
    bad or unknown code (a stale cookie is not an error). First touch wins
    and nothing changes once the account has paid."""
    norm = normalize_code(code)
    if norm is None:
        return {"attributed": False, "reason": "bad_code"}
    ensure(dsn)
    with db.connect(dsn) as conn:
        partner = conn.execute(
            "SELECT id, account_id, status FROM affiliate_partners WHERE lower(code) = %s",
            (norm,)).fetchone()
        if partner is None or partner["status"] != "approved":
            return {"attributed": False, "reason": "unknown_code"}
        if int(partner["account_id"]) == int(account_id):
            return {"attributed": False, "reason": "self_referral"}
        shared_person = conn.execute(
            "SELECT 1 FROM account_members a JOIN account_members b ON a.user_id = b.user_id "
            "WHERE a.account_id = %s AND b.account_id = %s LIMIT 1",
            (account_id, partner["account_id"])).fetchone()
        if shared_person:
            return {"attributed": False, "reason": "self_referral"}
        _partner_lock(conn, int(partner["id"]))
        if conn.execute("SELECT 1 FROM affiliate_referrals WHERE referred_account_id = %s",
                        (account_id,)).fetchone():
            return {"attributed": False, "reason": "already_attributed"}
        if _has_paid(conn, account_id):
            return {"attributed": False, "reason": "already_paid"}
        conn.execute(
            "INSERT INTO affiliate_referrals (account_id, partner_id, referred_account_id) "
            "VALUES (%s, %s, %s)", (partner["account_id"], partner["id"], account_id))
    return {"attributed": True, "reason": "ok"}


def buyer_discount_applies(account_id: int, interval: str, *, dsn: Optional[str] = None) -> bool:
    """Whether this account's next plan checkout carries the referred buyer's
    discount: attributed to an approved partner, has not paid yet, and
    choosing a MONTHLY plan (a yearly plan already has its own 20% off).
    Any read error answers False -- a missing discount is better than a
    broken checkout."""
    if (interval or "month") != "month":
        return False
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            row = conn.execute(
                "SELECT r.first_paid_at, p.status FROM affiliate_referrals r "
                "JOIN affiliate_partners p ON p.id = r.partner_id AND p.account_id = r.account_id "
                "WHERE r.referred_account_id = %s", (account_id,)).fetchone()
            if row is None or row["status"] != "approved" or row["first_paid_at"] is not None:
                return False
            return not _has_paid(conn, account_id)
    except Exception as exc:  # noqa: BLE001 -- see docstring
        _log(f"buyer_discount_applies({account_id}) failed: {exc}")
        return False


def coupon_id() -> Optional[str]:
    return (os.environ.get(COUPON_ENV) or "").strip() or None


# --------------------------------------------------------------------------
# earning -- called from the Stripe webhook
# --------------------------------------------------------------------------

def invoice_net_cents(invoice: dict) -> int:
    """What the customer actually paid, before tax, in cents. 0 when the
    invoice was free. Falls back through the shapes Stripe has sent."""
    paid = int(invoice.get("amount_paid") or 0)
    if paid <= 0:
        return 0
    ex_tax = invoice.get("total_excluding_tax")
    if isinstance(ex_tax, int):
        return max(0, min(paid, ex_tax))
    tax = invoice.get("tax")
    return max(0, paid - int(tax)) if isinstance(tax, int) else paid


def _paying_count(conn, partner_account_id: int, partner_id: int) -> int:
    row = conn.execute(
        "SELECT count(*) AS n FROM affiliate_referrals r WHERE r.account_id = %s "
        "AND r.partner_id = %s AND r.first_paid_at IS NOT NULL AND EXISTS ("
        "  SELECT 1 FROM affiliate_commissions c WHERE c.account_id = r.account_id "
        "  AND c.referral_id = r.id AND c.status <> 'void')",
        (partner_account_id, partner_id)).fetchone()
    return int(row["n"])


def on_invoice_paid(account_id: int, invoice: dict, *, months_covered: int = 1,
                    now: Optional[datetime] = None, dsn: Optional[str] = None) -> dict:
    """A subscription invoice cleared for `account_id`. Books the
    commission, if one is owed. Idempotent on the invoice id. Returns what
    happened (for the webhook's log); may raise -- the caller swallows."""
    ensure(dsn)
    now = now or _now()
    invoice_ref = str(invoice.get("id") or "")
    if not invoice_ref:
        return {"action": "no_invoice_id"}
    basis = invoice_net_cents(invoice)
    with db.connect(dsn) as conn:
        ref = conn.execute(
            "SELECT r.*, p.status AS partner_status FROM affiliate_referrals r "
            "JOIN affiliate_partners p ON p.id = r.partner_id AND p.account_id = r.account_id "
            "WHERE r.referred_account_id = %s", (account_id,)).fetchone()
        if ref is None:
            return {"action": "no_referral"}
        _partner_lock(conn, int(ref["partner_id"]))
        ref = conn.execute(
            "SELECT r.*, p.status AS partner_status FROM affiliate_referrals r "
            "JOIN affiliate_partners p ON p.id = r.partner_id AND p.account_id = r.account_id "
            "WHERE r.referred_account_id = %s", (account_id,)).fetchone()
        if ref["partner_status"] != "approved":
            return {"action": "partner_not_approved"}
        if conn.execute("SELECT 1 FROM affiliate_commissions WHERE invoice_ref = %s",
                        (invoice_ref,)).fetchone():
            return {"action": "already_booked"}
        if basis <= 0:
            return {"action": "nothing_paid"}
        if ref["first_paid_at"] is None:
            tier = tier_for_count(_paying_count(conn, ref["account_id"], ref["partner_id"]))
            conn.execute(
                "UPDATE affiliate_referrals SET first_paid_at = %s, tier_key = %s, rate_bp = %s, "
                "window_months = %s WHERE id = %s AND account_id = %s",
                (now, tier.key, tier.rate_bp, tier.window_months, ref["id"], ref["account_id"]))
            rate_bp, window, paid_months = tier.rate_bp, tier.window_months, 0
        else:
            rate_bp, window = int(ref["rate_bp"]), int(ref["window_months"])
            paid_months = int(ref["months_paid"])
        covered = max(1, int(months_covered))
        remaining = window - paid_months
        if remaining <= 0:
            return {"action": "window_over"}
        counted = min(covered, remaining)
        cents = basis * rate_bp * counted // (10000 * covered)      # floor: never overpay
        conn.execute(
            "UPDATE affiliate_referrals SET months_paid = %s WHERE id = %s AND account_id = %s",
            (min(window, paid_months + covered), ref["id"], ref["account_id"]))
        row = conn.execute(
            "INSERT INTO affiliate_commissions (account_id, partner_id, referral_id, invoice_ref, "
            "paid_cents, months_covered, months_counted, rate_bp, commission_cents, hold_until) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (invoice_ref) DO NOTHING RETURNING id",
            (ref["account_id"], ref["partner_id"], ref["id"], invoice_ref, basis, covered,
             counted, rate_bp, cents, now + timedelta(days=HOLD_DAYS))).fetchone()
        if row is None:
            return {"action": "already_booked"}
        return {"action": "booked", "commission_id": int(row["id"]), "commission_cents": cents,
                "rate_bp": rate_bp, "partner_id": int(ref["partner_id"])}


def on_refund(account_id: int, charge: dict, *, dsn: Optional[str] = None) -> dict:
    """A charge was refunded. Inside the hold, the commission on that payment
    is voided (full refund) or scaled down in proportion (partial). The
    invoice is found by the charge's `invoice` field when Stripe sends one,
    else the account's newest held commission is the one affected. After the
    hold nothing is clawed back: that is what the hold is for."""
    ensure(dsn)
    refunded = int(charge.get("amount_refunded") or 0)
    charged = int(charge.get("amount") or 0)
    if refunded <= 0 or charged <= 0:
        return {"action": "nothing_refunded"}
    invoice_ref = charge.get("invoice")
    if isinstance(invoice_ref, dict):
        invoice_ref = invoice_ref.get("id")
    with db.connect(dsn) as conn:
        ref = conn.execute(
            "SELECT id, account_id FROM affiliate_referrals WHERE referred_account_id = %s",
            (account_id,)).fetchone()
        if ref is None:
            return {"action": "no_referral"}
        if invoice_ref:
            com = conn.execute(
                "SELECT * FROM affiliate_commissions WHERE account_id = %s AND referral_id = %s "
                "AND invoice_ref = %s AND status = 'held'",
                (ref["account_id"], ref["id"], str(invoice_ref))).fetchone()
        else:
            com = conn.execute(
                "SELECT * FROM affiliate_commissions WHERE account_id = %s AND referral_id = %s "
                "AND status = 'held' ORDER BY id DESC LIMIT 1",
                (ref["account_id"], ref["id"])).fetchone()
        if com is None:
            return {"action": "no_held_commission"}
        if refunded >= charged:
            new_cents, status, note = 0, "void", "refunded in full inside the hold"
        else:
            keep = max(0, charged - refunded)
            new_cents = int(com["commission_cents"]) * keep // charged
            status, note = "held", f"scaled for a partial refund ({refunded} of {charged} cents)"
        conn.execute(
            "UPDATE affiliate_commissions SET commission_cents = %s, status = %s, note = %s "
            "WHERE id = %s AND account_id = %s",
            (new_cents, status, note, com["id"], com["account_id"]))
        return {"action": status if status == "void" else "scaled",
                "commission_id": int(com["id"]), "commission_cents": new_cents}


# --------------------------------------------------------------------------
# paying -- credits at once, cash for Mike to send
# --------------------------------------------------------------------------

def release_due(*, now: Optional[datetime] = None, dsn: Optional[str] = None) -> dict:
    """Pay every commission whose hold has ended. For a partner on credits the
    commission becomes a `promo` lot on their account (1 credit per cent,
    12-month expiry), idempotent through the ledger's own source_ref guard;
    for a partner on cash it becomes 'released' -- payable, waiting for
    `payouts`. A partner who is not approved is skipped (their commissions
    stay held). Returns counts."""
    from . import ledger
    ensure(dsn)
    now = now or _now()
    with db.connect(dsn) as conn:
        due = [dict(r) for r in conn.execute(
            "SELECT c.*, p.status AS partner_status, p.payout_mode FROM affiliate_commissions c "
            "JOIN affiliate_partners p ON p.id = c.partner_id AND p.account_id = c.account_id "
            "WHERE c.status = 'held' AND c.hold_until <= %s ORDER BY c.id", (now,)).fetchall()]
    credited = payable = skipped = 0
    for com in due:
        if com["partner_status"] != "approved":
            skipped += 1
            continue
        cents = int(com["commission_cents"])
        if cents <= 0:
            with db.connect(dsn) as conn:
                conn.execute(
                    "UPDATE affiliate_commissions SET status = 'void', note = 'nothing owed' "
                    "WHERE id = %s AND account_id = %s", (com["id"], com["account_id"]))
            continue
        if com["payout_mode"] == "credits":
            lot_id = ledger.grant(
                com["account_id"], cents, "promo", source_ref=f"affiliate:{com['id']}",
                note=f"affiliate commission #{com['id']} ({com['rate_bp'] / 100:g}% of invoice {com['invoice_ref']})",
                expires_at=ledger._plus_months(ledger._now(), CREDIT_EXPIRY_MONTHS), dsn=dsn)
            with db.connect(dsn) as conn:
                conn.execute(
                    "UPDATE affiliate_commissions SET status = 'paid', payout = 'credits', "
                    "lot_id = %s, released_at = %s, paid_at = %s WHERE id = %s AND account_id = %s "
                    "AND status = 'held'", (lot_id, now, now, com["id"], com["account_id"]))
            credited += 1
        else:
            with db.connect(dsn) as conn:
                conn.execute(
                    "UPDATE affiliate_commissions SET status = 'released', payout = 'cash', "
                    "released_at = %s WHERE id = %s AND account_id = %s AND status = 'held'",
                    (now, com["id"], com["account_id"]))
            payable += 1
    return {"credited": credited, "cash_payable": payable, "skipped": skipped}


def payouts(*, dsn: Optional[str] = None) -> list[dict]:
    """Cash owed, by partner, for those at or over the minimum: what to send
    this month. Read-only."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT p.id AS partner_id, p.account_id, p.code, p.channel_url, a.slug, "
            "sum(c.commission_cents) AS cents, count(*) AS commissions "
            "FROM affiliate_commissions c JOIN affiliate_partners p "
            "ON p.id = c.partner_id AND p.account_id = c.account_id "
            "JOIN accounts a ON a.id = p.account_id "
            "WHERE c.status = 'released' AND c.payout = 'cash' "
            "GROUP BY p.id, p.account_id, p.code, p.channel_url, a.slug "
            "HAVING sum(c.commission_cents) >= %s ORDER BY cents DESC",
            (MIN_CASH_PAYOUT_CENTS,)).fetchall()
        return [dict(r) for r in rows]


def mark_paid(who: str, reference: str, *, now: Optional[datetime] = None,
              dsn: Optional[str] = None) -> dict:
    """Record that Mike sent a partner their released cash (all of it). The
    reference is his own note: the PayPal or Stripe transfer id."""
    if not (reference or "").strip():
        raise AffiliateError("reference_required", "give the transfer reference")
    ensure(dsn)
    with db.connect(dsn) as conn:
        partner = _resolve_partner(conn, who)
        cur = conn.execute(
            "UPDATE affiliate_commissions SET status = 'paid', paid_at = %s, payout_ref = %s "
            "WHERE account_id = %s AND partner_id = %s AND status = 'released' AND payout = 'cash' "
            "RETURNING commission_cents",
            (now or _now(), reference.strip()[:200], partner["account_id"], partner["id"]))
        rows = cur.fetchall()
        return {"commissions": len(rows), "cents": sum(int(r["commission_cents"]) for r in rows)}


# --------------------------------------------------------------------------
# what a partner sees
# --------------------------------------------------------------------------

def summary(account_id: int, *, dsn: Optional[str] = None) -> dict:
    """The dashboard for one account: status, link, tier, progress, earnings.
    Referred people are numbers, never names or emails. Credits are shown as
    credits (1 per cent); cash in cents."""
    ensure(dsn)
    out: dict[str, Any] = {"terms": public_terms(), "status": None}
    with db.connect(dsn) as conn:
        p = conn.execute("SELECT * FROM affiliate_partners WHERE account_id = %s",
                         (account_id,)).fetchone()
        if p is None:
            return out
        paying = _paying_count(conn, account_id, p["id"])
        signups = conn.execute(
            "SELECT count(*) AS n FROM affiliate_referrals WHERE account_id = %s AND partner_id = %s",
            (account_id, p["id"])).fetchone()["n"]
        sums = {r["status"]: (int(r["cents"]), int(r["n"])) for r in conn.execute(
            "SELECT status, sum(commission_cents) AS cents, count(*) AS n "
            "FROM affiliate_commissions WHERE account_id = %s AND partner_id = %s GROUP BY status",
            (account_id, p["id"])).fetchall()}
        recent = [dict(r) for r in conn.execute(
            "SELECT id, created_at, commission_cents, status, payout, rate_bp, hold_until "
            "FROM affiliate_commissions WHERE account_id = %s AND partner_id = %s "
            "ORDER BY id DESC LIMIT 12", (account_id, p["id"])).fetchall()]
    tier = tier_for_count(paying)
    nxt = next_tier(tier)
    out.update({
        "status": p["status"],
        "code": p["code"],
        "link": link(p["code"]) if p["code"] and p["status"] == "approved" else None,
        "payout_mode": p["payout_mode"],
        "paying_referrals": paying,
        "signups": int(signups),
        "tier": {"key": tier.key, "label": tier.label, "percent": tier.percent,
                 "months": tier.window_months},
        "next_tier": ({"key": nxt.key, "label": nxt.label, "percent": nxt.percent,
                       "months": nxt.window_months, "needs": max(0, nxt.min_paying - paying)}
                      if nxt else None),
        "earnings": {
            "held_cents": sums.get("held", (0, 0))[0],
            "payable_cash_cents": sums.get("released", (0, 0))[0],
            "paid_cents": sums.get("paid", (0, 0))[0],
        },
        "recent": [{"id": int(r["id"]), "date": _iso(r["created_at"]),
                    "cents": int(r["commission_cents"]), "status": r["status"],
                    "payout": r["payout"], "percent": r["rate_bp"] / 100.0,
                    "pays_on": _iso(r["hold_until"])} for r in recent],
    })
    return out


def report(*, dsn: Optional[str] = None) -> dict:
    """Mike's overview: applications waiting, partners and their numbers."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT p.id, p.account_id, p.code, p.status, p.payout_mode, p.channel_url, "
            "p.audience, p.plan, p.created_at, a.slug, "
            "(SELECT count(*) FROM affiliate_referrals r WHERE r.account_id = p.account_id "
            "  AND r.partner_id = p.id) AS signups, "
            "(SELECT count(*) FROM affiliate_referrals r WHERE r.account_id = p.account_id "
            "  AND r.partner_id = p.id AND r.first_paid_at IS NOT NULL) AS paying, "
            "(SELECT coalesce(sum(c.commission_cents), 0) FROM affiliate_commissions c "
            "  WHERE c.account_id = p.account_id AND c.partner_id = p.id AND c.status = 'held') AS held, "
            "(SELECT coalesce(sum(c.commission_cents), 0) FROM affiliate_commissions c "
            "  WHERE c.account_id = p.account_id AND c.partner_id = p.id AND c.status IN ('paid')) AS paid "
            "FROM affiliate_partners p JOIN accounts a ON a.id = p.account_id ORDER BY p.id"
        ).fetchall()
    partners = [dict(r) for r in rows]
    return {"pending": [x for x in partners if x["status"] == "pending"], "partners": partners}


# --------------------------------------------------------------------------
# the CLI -- Mike's review desk
# --------------------------------------------------------------------------

def _print_partner(p: dict) -> None:
    print(f"  #{p['id']}  {p.get('slug', '')}  [{p['status']}]  code={p['code']}  "
          f"payout={p['payout_mode']}")
    if p.get("channel_url"):
        print(f"      channel: {p['channel_url']}")
    if p.get("audience"):
        print(f"      audience: {p['audience']}")
    if p.get("plan"):
        print(f"      plan: {p['plan']}")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="affiliates",
        description="The affiliate desk. NEVER loads .env: export DATABASE_URL first "
                    "(set -a && source .env && set +a), or this acts on the local throwaway database.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export", help="write the public terms to web/src/content/affiliate.json")
    sub.add_parser("report", help="applications waiting and every partner's numbers")
    ap = sub.add_parser("approve", help="approve an application (by account slug, code or id)")
    ap.add_argument("who")
    ap.add_argument("--code", help="choose the code instead of deriving it from the slug")
    rj = sub.add_parser("reject")
    rj.add_argument("who")
    rj.add_argument("--note", default="")
    sp = sub.add_parser("suspend")
    sp.add_argument("who")
    sp.add_argument("--note", default="")
    po = sub.add_parser("set-payout", help="credits (default) or cash, per partner")
    po.add_argument("who")
    po.add_argument("mode", choices=PAYOUT_MODES)
    sub.add_parser("release", help="pay every commission whose 60-day hold has ended")
    sub.add_parser("payouts", help="cash owed per partner (at or over the minimum)")
    mp = sub.add_parser("mark-paid", help="record that you sent a partner their released cash")
    mp.add_argument("who")
    mp.add_argument("reference")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "export":
            print(f"wrote {export_terms()}")
        elif args.cmd == "report":
            rep = report()
            print(f"{len(rep['pending'])} application(s) waiting")
            for p in rep["pending"]:
                _print_partner(p)
            print(f"{len(rep['partners'])} partner row(s)")
            for p in rep["partners"]:
                print(f"  #{p['id']} {p['slug']:<20} {p['status']:<10} signups={p['signups']} "
                      f"paying={p['paying']} held={p['held']}c paid={p['paid']}c payout={p['payout_mode']}")
        elif args.cmd == "approve":
            p = approve(args.who, code=args.code)
            print(f"approved: code {p['code']}  link {link(p['code'])}")
        elif args.cmd in ("reject", "suspend"):
            p = set_status(args.who, "rejected" if args.cmd == "reject" else "suspended", note=args.note)
            print(f"{p['status']}: partner #{p['id']}")
        elif args.cmd == "set-payout":
            p = set_payout_mode(args.who, args.mode)
            print(f"partner #{p['id']} now paid as {p['payout_mode']}")
        elif args.cmd == "release":
            print(release_due())
        elif args.cmd == "payouts":
            rows = payouts()
            if not rows:
                print(f"nothing at or over ${MIN_CASH_PAYOUT_CENTS // 100} is waiting")
            for r in rows:
                print(f"  {r['slug']:<20} ${int(r['cents']) / 100:,.2f}  ({r['commissions']} commission(s))  "
                      f"{r['channel_url']}")
        elif args.cmd == "mark-paid":
            print(mark_paid(args.who, args.reference))
    except AffiliateError as e:
        print(f"refused: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
