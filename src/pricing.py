"""
The only code in the repo that turns a render intent into a price
(docs/tasks/task-pricing-and-quotes.md, steps 1-3 of 6, 2026-09-17).

Everything that SHOWS a price or, later, TAKES money asks here: the Queue
card, an approve with an empty body, the Director's Generate node. Before
this module the same number was computed in four places -- providers'
check_render_choice, check_timeline_choice, the Queue's JS (twice) and
the Director's chip, which priced every node at Runway's default whatever
renderer the account would actually spend on. Two implementations of a
price is how a person is shown one number and charged another.

TWO LAYERS:

  estimate()  what the PROVIDER (fal) will charge for this render: model x
              resolution x seconds off fal.VIDEO_MODELS' dated rate card.
  quote()     what WE will charge, in credits: that estimate x MARKUP,
              rounded up to whole credits, never under CREDIT_FLOOR.

Since 2026-09-26 every render is quoted: BYOK is gone (docs/tasks/
task-fal-only.md), so there is no render "already paid for at the
provider" any more -- every video render runs on the operator's fal key
and holds credit.

What this module deliberately does NOT do:

- NO DB WRITES. A quote is a price, not a permission. The daily cap
  (generative.cap_error, counted from the generations table so a stuck
  loop hits a database wall) and the balance (ledger.hold, the only place
  that can check it without a race) stay where they are. Conflating them
  means a person near their cap sees no price instead of a price and a
  reason.
- NO SECOND RESOLVER. Which renderer an account can use is
  providers.render_default / renderer_for. An explicit provider is
  honoured EXACTLY and refused if it cannot render -- never swapped for a
  cheaper one, which would be spending on something nobody chose.
- NO SECOND CONTENT HASH. content_hash() below is timeline.source_hash,
  the staleness-on-read hash that already exists; nothing else may
  compute one.
- NO NONCE, NO QUOTE STORE. A signed quote (sign / verify, below) is
  idempotent by design: re-approving the same part with the same token is
  refused by the render loop's skip-parts-with-clips rule, not by quote
  bookkeeping. Every field of Quote is an int, a str or a tuple of them,
  so nothing in the signed body is a float that round-trips badly.
  (The STUDIO token -- sign_studio, a render no shot carries -- does
  carry a nonce, because it has no such rule; its single use is recorded
  in src/quote_redemptions.py, still not here. So does the KEYFRAMES
  token -- sign_keyframes, a scene's stills approved from a chat: two
  approves racing each other both find every still undrawn.)

MARKUP IS 2.4 SINCE 2026-09-18 (Mike's call, the spec's number): a credit
is one cent of CHARGE, a render costs its provider estimate times 2.4,
rounded up, never under CREDIT_FLOOR. The same day the ledger started
holding (src/charge.py, inside every adapter) and `ledger.charge_credits`
became the ONE conversion a hold and a quote share, so the number on the
card is the number debited by construction. PLANS below is what a person
can buy (app/billing.py sells it through Stripe) and `tier_for` is how a
plan's tier reaches the band check. The public site is GENERATED from
`public_catalog()` -- `python -m src.pricing export` writes
web/src/content/pricing.json, and tests/test_plans.py fails when the
committed file and this module disagree.
MARKUP is 2.4 (2026-09-18, Mike's call -- the spec's number): $1.00 of
provider cost is 240 credits. It landed in ONE commit with making the
signed token required on approve, because a raised markup beside an
unsigned path silently undercharges. ledger.credits_for_usd is the 1.0x
figure and no longer what a quote charges; hold_for_render (step 6)
holds quote.credits, never a re-derivation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from typing import Optional

from . import ledger, providers, timeline

# v3 (2026-09-26): fal is the only renderer and a render is priced by
# model + RESOLUTION + seconds (Seedance 2.0 is $0.3034/s at 720p and
# $0.682/s at 1080p). Every v2 token was minted for a renderer or a band
# that no longer exists, so v2 is retired, not carried: an old signed
# quote refuses as `retired_pricing` and the card re-quotes.
PRICING_VERSION = "2026-09-26-fal-v3"
# A token minted under a version not listed here is refused as
# `retired_pricing`: prices changed, re-quote. Retire a version by removing
# it, never by changing what it means.
SUPPORTED_PRICING_VERSIONS = (PRICING_VERSION,)

# One credit is one cent of CHARGE -- the ledger's existing unit.
CREDIT_CENTS = 1
# charge / provider cost. A STRING, read through Fraction, because a
# markup is a decimal and a float is not: 100000 * 1.1 is
# 110000.00000000001, and ceil() of that in cents is 12 credits for an
# 11-credit render. Move this constant, never the call sites.
MARKUP = "2.4"
# per render, per part: the least any billable render costs
CREDIT_FLOOR = 10


# --- the studio actions that are not renders ----------------------------
# A STILL costs credits (2026-09-28, Mike's call): a Nano Banana image is
# real Gemini money, charged at the render markup and floor through the
# same hold -> settle/release (src/charge.py), exempt accounts and the
# unowned pool excepted exactly as for renders.
#
# A CREATE does not (2026-09-29, Mike's call, reversing the 2026-09-28
# per-Create price): writing a scene is included in the subscription and
# its cost (~$0.04 a Create, llm_calls) is priced into the plans, not
# debited per click. The gate that remains is charge.create_refusal: no
# plan and no balance, no Create.


def still_usd(model: str) -> float:
    """One still's provider USD, off spend's price table -- the same
    number the meter records for it. A model the table does not know
    prices as the dearest image model in it, never as free."""
    from . import spend
    usd = spend.estimate_cost(model, images=1)
    if usd:
        return usd
    return max(row.get("image", 0.0) for row in spend.prices().values())


def still_credits(model: str) -> int:
    return credits_for(usd_micros(still_usd(model)))


# THE TRIAL'S THINKING (2026-10-08, Mike's call: "fix the trial"). On a
# plan the brain is free -- the Guide, Create, Direct, the index -- its cost
# carried by the render markup, the way Runway and Higgsfield carry theirs.
# The sign-up trial has no plan to carry it, and its 100 credits only bound
# what it RENDERS: without this it could think on the studio's key without
# limit and never spend a credit. So the trial includes this much model
# text, ONCE (not per day), measured by the meter (spend.thinking_spent).
# $1.00 is the trial credits' own value at the plan rate: about 25
# Creates or 250 Guide turns on Flash. PHANTRA_TRIAL_THINKING_USD
# overrides it; 0 means the trial thinks not at all.
TRIAL_THINKING_USD = 1.00
TRIAL_THINKING_ENV = "PHANTRA_TRIAL_THINKING_USD"


def trial_thinking_usd() -> float:
    """The model text, in USD, the sign-up trial includes, once."""
    raw = (os.environ.get(TRIAL_THINKING_ENV) or "").strip()
    try:
        return max(0.0, float(raw)) if raw else TRIAL_THINKING_USD
    except ValueError:
        return TRIAL_THINKING_USD


# --- the plans --------------------------------------------------------------
# What a person buys. `credits` is the monthly allowance, granted as ONE
# subscription lot per paid invoice (ledger.EXPIRY_MONTHS governs its
# life); `tier` is the highest band the plan may render (providers.TIERS).
# `price_env` names the Stripe Price id the checkout uses -- the dollars
# here are what the site prints and what tests/test_plans.py pins, the
# Stripe Price is what is actually charged, and the two are kept equal by
# a person (app/billing.py refuses a price whose amount disagrees).
# YEARLY IS A SCHEDULE, NOT A LOT (2026-09-18, second pass). A lot expires
# two months after it lands, so a year's credit granted on one invoice
# would die ten months early. A yearly invoice therefore grants month
# one and writes a 12-month release schedule (src/billing.release_due);
# each later month lands as its own lot with its own two-month clock.
# `yearly_usd` is twelve months at YEARLY_DISCOUNT off, what the toggle
# on /pricing prints; `price_env_yearly` names its Stripe Price.
YEARLY_DISCOUNT = "0.20"
MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    tier: str
    monthly_usd: int
    credits: int
    blurb: str
    price_env: str
    popular: bool = False
    # STORAGE (2026-10-20, Mike's call): what a workspace may keep in the
    # bucket, in GB. Sized so a FULL quota costs at most ~10% of the plan's
    # worst month -- a yearly subscriber spending every credit -- at R2's
    # $0.015/GB-month (STORAGE_USD_PER_GB). See storage_ceiling_gb.
    storage_gb: int = 0

    @property
    def yearly_usd(self) -> int:
        """Twelve months at the discount, in whole dollars (the three
        plans all land on integers; a plan that would not should pick a
        price that does)."""
        cents = Fraction(self.monthly_usd * 100 * MONTHS_PER_YEAR) * (1 - Fraction(YEARLY_DISCOUNT))
        assert cents.denominator == 1 and cents.numerator % 100 == 0, self.key
        return int(cents) // 100

    @property
    def yearly_monthly_usd(self) -> int:
        """What a year works out to per month -- the number the card shows
        under the toggle ($12, $28, $76)."""
        return self.yearly_usd // MONTHS_PER_YEAR

    @property
    def price_env_yearly(self) -> str:
        return f"{self.price_env}_YEAR"


PLANS: dict[str, Plan] = {
    # The KEYS and the Stripe price envs are the 2026-09-18 ones on purpose
    # (Mike, 2026-10-20: "don't rename the price ids"): a subscription row,
    # a webhook and a Stripe Price all name a key, so only the NAME moved.
    "starter": Plan("starter", "Standard", "standard", 15, 1500,
                    "For creators testing ideas and posting a few clips a month.",
                    "STRIPE_PRICE_STARTER", storage_gb=25),
    "creator": Plan("creator", "Pro", "creator", 35, 3500,
                    "For creators and filmmakers posting every week.",
                    "STRIPE_PRICE_CREATOR", popular=True, storage_gb=70),
    "studio": Plan("studio", "Max", "premium", 95, 9500,
                   "For agencies, client work and heavy solo use.",
                   "STRIPE_PRICE_STUDIO", storage_gb=200),
}

# EVERY PLAN RENDERS EVERY MODEL (2026-10-20, Mike's call). A plan's `tier`
# no longer decides which models it may use (`_check_band` refuses on the
# band's length only); every render is still priced at MARKUP, so a dear
# model costs more credits, never a margin. `tier` survives as the label a
# subscription row carries and as the model's price band on the site.

# THE MCP CONNECTOR comes with every workspace, the trial included
# (2026-10-21, Mike's call): credits pay for what it spends, so no plan
# gates it. The Pro/Max-only gate of 2026-10-20 is gone (app/mcp_mount.py).

# STORAGE. Free is the trial workspace: no plan, 150 credits once.
FREE_STORAGE_GB = 2
STORAGE_USD_PER_GB = "0.015"     # Cloudflare R2 Standard, checked 2026-10-20
STORAGE_SHARE = "0.10"           # of the worst month's margin
STRIPE_PCT, STRIPE_FIXED_USD = "0.029", "0.30"
# What the assistant (free on a plan) is allowed to cost a month, per plan,
# in the ceiling below -- an estimate, not a meter reading.
BRAIN_USD = {"starter": 1, "creator": 2, "studio": 4}


def storage_ceiling_gb(plan: Plan) -> int:
    """The most storage the plan can carry, by the rule above: a yearly
    subscriber who spends every credit (provider cost = price / MARKUP),
    less Stripe's cut on the yearly invoice and the assistant's estimate,
    with STORAGE_SHARE of what is left paying for a full quota."""
    price = Fraction(plan.yearly_usd, MONTHS_PER_YEAR)
    provider = Fraction(plan.credits * CREDIT_CENTS, 100) / Fraction(MARKUP)
    stripe = (Fraction(plan.yearly_usd) * Fraction(STRIPE_PCT) + Fraction(STRIPE_FIXED_USD)) \
        / MONTHS_PER_YEAR
    left = price - provider - stripe - BRAIN_USD.get(plan.key, 0)
    return int(left * Fraction(STORAGE_SHARE) / Fraction(STORAGE_USD_PER_GB))


@dataclass(frozen=True)
class Pack:
    key: str
    name: str
    usd: int
    credits: int
    price_env: str


# A one-time top-up: a `purchase` lot, for accounts ON A PLAN only
# (billing.checkout_url refuses the rest). 750 for $10 since 2026-09-29,
# Mike's call: 1.33c a credit against a plan's 1.0c, so a top-up is what
# you buy when your month runs out, never a cheaper way to skip the plan.
# It was 1,000 -- the same rate as Starter, which gave nobody a reason to
# subscribe. The Stripe Price is unchanged ($10); only the grant moved.
TOPUP = Pack("topup", "750 credits", 10, 750, "STRIPE_PRICE_TOPUP")


def plan_for_tier(tier: str) -> Optional[Plan]:
    return next((p for p in PLANS.values() if p.tier == tier), None)


def tier_for(account_id: Optional[int], dsn: Optional[str] = None,
             ctx=None) -> Optional[str]:
    """The band an account may render up to: its plan's tier, or None.

    None is NOT a tier and enforces nothing (`estimate` skips the band
    check on it): an account with no plan holds no credit, so the ledger
    is its wall, and a render on its own key is the provider's business.
    A plan a webhook wrote that this module no longer lists reads as
    None too -- a retired plan must not silently become the top tier.

    `ctx` is a listing's providers.RenderContext: it read the account's
    plan once for the request, so a page of cards is not a plan lookup
    per render. A door that spends passes none and reads the row.
    """
    if account_id is None:
        return None
    from . import accounts
    held = providers._held(ctx, account_id, dsn)
    key = held.plan if held is not None and held.plan_known \
        else accounts.plan_of(account_id, dsn=dsn)
    plan = PLANS.get(key or "")
    return plan.tier if plan else None

_MICROS = 1_000_000
_MICROS_PER_CENT = 10_000


# --- the signed quote -------------------------------------------------------
# ITS OWN SECRET, never SESSION_SECRET. Rotating this one invalidates at
# most an hour of outstanding quotes, and people press the button again;
# rotating the session secret signs everybody out. Tying them together
# makes the cheap rotation as expensive as the disruptive one. Different
# per environment on purpose: a dev-minted quote must not verify in
# production, which is the whole point of signing it.
SIGNING_ENV = "QUOTE_SIGNING_SECRET"
SIGNING_COMMAND = ('python -c "import base64, os; '
                   'print(base64.urlsafe_b64encode(os.urandom(32)).decode())"')
QUOTE_TTL = 3600          # long enough to quote, get up and come back
TOKEN_PREFIX = "phq"     # greppable in a log; unmistakable for an API key
TOKEN_VERSION = 1


class SigningUnconfigured(RuntimeError):
    """QUOTE_SIGNING_SECRET is unset. A route answers 503 with
    SIGNING_COMMAND -- never a 500, and never a default secret, which
    would be a quote anyone on the internet can mint."""

    def __init__(self):
        super().__init__(f"{SIGNING_ENV} is not set -- generate one with: {SIGNING_COMMAND}")


class QuoteRefused(ValueError):
    """verify() said no. `reason` is one of: bad_signature, expired,
    stale_content, wrong_account, retired_pricing, wrong_render. Raised,
    never returned as a bool: a verification a caller can forget to
    check is not a gate."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


class PricingRefused(ValueError):
    """This intent has no price, and `reason` says which kind of no.

    A ValueError on purpose: every door already turns a ValueError from
    check_render_choice into a 400 with the message, and a band refusal
    is the same event -- the card and the model have come apart."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class Estimate:
    """What the provider will charge. `frame` is the one field the spec's
    Quote does not list and the estimators cannot work without: Seedance
    and fal bill per resolution tier."""
    provider: str
    model: str
    seconds: int
    frame: str
    part: Optional[int]
    provider_usd_micros: int
    # a timed scene rendered as ONE clip with its cuts in the prompt
    # (timeline.renders_as_one), and how many of its photos go out with it
    one_clip: bool = False
    references: int = 0

    @property
    def usd(self) -> float:
        return self.provider_usd_micros / _MICROS


@dataclass(frozen=True)
class Quote:
    pricing_version: str
    account_id: Optional[int]
    shot_id: int
    part: Optional[int]
    provider: str
    model: str
    seconds: int
    frame: str
    provider_usd_micros: int
    credits: int
    content_hash: str
    line_items: tuple


# --------------------------------------------------------------------------
# money
# --------------------------------------------------------------------------

def usd_micros(usd) -> int:
    """A provider estimate (a float, from the adapter's own rate card) ->
    integer micro-dollars. Rounded to the NEAREST micro, via str(), for
    credits_for_usd's reason: this step exists to shed float noise, and
    the rounding that favours the house happens exactly once, in
    credits_for()."""
    if usd is None:
        raise PricingRefused("unpriced", "this renderer has no estimate to price")
    try:
        micros = (Decimal(str(usd)) * _MICROS).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise PricingRefused("unpriced", f"not a price: {usd!r}") from None
    if micros < 0:
        raise PricingRefused("unpriced", f"negative price: {usd!r}")
    return int(micros)


def credits_for(provider_usd_micros: int) -> int:
    """Micro-dollars of provider cost -> credits: marked up, rounded UP to
    the cent, never under the floor. Integer arithmetic throughout."""
    scaled = Fraction(int(provider_usd_micros)) * Fraction(str(MARKUP)) * CREDIT_CENTS
    cents = -((-scaled.numerator) // (scaled.denominator * _MICROS_PER_CENT))
    return max(int(cents), CREDIT_FLOOR)


# --------------------------------------------------------------------------
# the content hash -- one function, and it is timeline's
# --------------------------------------------------------------------------

def content_hash(shot: dict, part: Optional[int] = None) -> str:
    """What a price is ABOUT: the scene's prompt and its reference set.

    Computed LIVE from the shot through timeline.source_hash, never read
    off shot["timeline"]["source"]. The stored value is what the timeline
    was PLANNED from, and it is only refreshed when timeline.ensure next
    runs -- so between a prompt edit and the re-plan it still names the
    old prompt, and a quote compared against it would survive exactly the
    edit it exists to catch. When the timeline is current the two are the
    same string (timeline.is_current is this comparison).

    `part` is accepted and does not change the answer: a part's prompt
    and refs are derived from the scene's, so the scene's hash covers
    every part, and the part number rides beside it in the quote."""
    shot = shot or {}
    return timeline.source_hash(shot.get("prompt") or "", shot.get("refs") or [])


def signed_hash(shot: dict, part: Optional[int], *, account_id: Optional[int],
                shot_id) -> str:
    """The content hash a quote TOKEN carries: content_hash, plus the brand
    kit's hash when the scene's project picked one (src/brand_kits.py) --
    a kit's look is added at render time, so a kit switched or edited after
    the price would otherwise render something the person never priced.
    With no kit this IS content_hash, character for character, so every
    token issued before kits existed still verifies."""
    plain = content_hash(shot, part)
    from . import brand_kits
    kit = brand_kits.for_concept(shot_id, account_id=account_id)
    return f"{plain}+{kit['hash']}" if kit else plain


# --------------------------------------------------------------------------
# the estimate
# --------------------------------------------------------------------------

def _resolve(account_id: Optional[int], shot: dict,
             provider: Optional[str], model: Optional[str],
             ctx=None) -> tuple[str, Optional[str]]:
    """(provider, model-or-None). An explicit provider is the caller's
    choice and is kept as-is; nothing named means the card's own default,
    through the same call the card made."""
    planned = providers.platform_default((shot or {}).get("tool"))
    if provider:
        name = provider.strip().lower()
        if model is None:
            # a provider named with no model resolves as the card opened:
            # the model proposed for this scene first, then the planned tool's
            proposed = providers.proposed_default((shot or {}).get("render_model"))
            hint = proposed if proposed and name == proposed[0] else planned
            if hint and name == hint[0]:
                model = hint[1]
        return name, model
    default = providers.render_default((shot or {}).get("tool"), account_id, ctx,
                                       model=(shot or {}).get("render_model"))
    return default["provider"], model or default["model"]


def windows_to_render(shot: dict) -> Optional[list[dict]]:
    """[{"n", "seconds"}] for every timed shot an approve would render, or
    None when the scene renders whole. The card's own view of it
    (api._timeline_card): the planned parts still without a clip when the
    timeline is current, else the bare windows the prompt carries -- a
    stale or missing timeline is re-planned inside the render job, before
    the first clip, from those same windows."""
    shot = shot or {}
    if timeline.is_current(shot):
        return [{"n": p.get("n"), "seconds": p.get("seconds")}
                for p in timeline.pending_parts(shot)]
    windows = timeline.parse_windows(shot.get("prompt") or "")
    if not windows:
        return None
    return [{"n": i, "seconds": w["seconds"]} for i, w in enumerate(windows, start=1)]


def _part_window(shot: dict, part: int):
    if timeline.is_current(shot or {}):
        listed = shot["timeline"]["parts"]
    else:
        listed = windows_to_render(shot) or []
    for entry in listed:
        if entry.get("n") == part:
            return entry.get("seconds")
    raise PricingRefused("no_such_part", f"this scene has no shot {part}")


def _check_band(provider: str, model: str, seconds: int, tier: Optional[str],
                frame: Optional[str] = None) -> None:
    band = providers.band_for(provider, model, frame)
    # No tier refusal since 2026-10-20: every plan renders every model
    # (see "EVERY PLAN RENDERS EVERY MODEL" above). `tier` is accepted and
    # ignored here so callers need not change.
    del tier
    if band.max_seconds is not None and seconds > band.max_seconds:
        raise PricingRefused(
            "band_seconds", f"{model} is priced up to {band.max_seconds}s a render, "
                            f"not {seconds}s")


def estimate(*, account_id: Optional[int], shot: dict, part: Optional[int] = None,
             provider: Optional[str] = None, model: Optional[str] = None,
             seconds=None, frame=None, tier: Optional[str] = None,
             ctx=None) -> Estimate:
    """One render, resolved, checked and priced at the provider's rate.

    `seconds` None derives it: a PART renders at its own window fitted UP
    to what the model can make (timeline.fit_seconds -- a 3s window is a
    5s Runway clip); a whole scene renders at the model's default length,
    which is what the Queue card opens on. A length or a frame outside
    the model's legal set is REFUSED, not clamped (check_render_choice's
    rule). Raises ValueError / PricingRefused."""
    if tier is not None and tier not in providers.TIERS:
        raise PricingRefused("tier", f"unknown tier {tier!r} -- one of {list(providers.TIERS)}")
    if tier is None:
        tier = tier_for(account_id, ctx=ctx)
    name, wanted = _resolve(account_id, shot, provider, model, ctx)
    if part is not None and seconds is None:
        window = _part_window(shot, part)
        base = providers.check_render_choice(name, wanted, None, frame)
        axis = providers.model_options(base["provider"], base["model"])["duration"]
        seconds = timeline.fit_seconds(axis, window)
    choice = providers.check_render_choice(name, wanted, seconds, frame)
    _check_band(choice["provider"], choice["model"], int(choice["duration"]), tier,
                choice["frame"])
    return Estimate(provider=choice["provider"], model=choice["model"],
                    seconds=int(choice["duration"]), frame=str(choice["frame"]),
                    part=part, provider_usd_micros=usd_micros(choice["estimate_usd"]))


def one_clip_references(shot: dict, provider: str, model: str) -> int:
    """How many of the scene's photos a one-clip render sends: all of them
    up to the model's cap on its reference-to-video endpoint, none for a
    model that has no such endpoint (it is anchored on a still instead)."""
    if provider != "fal":
        return 0
    from . import fal
    return min(len(timeline.one_clip_refs(shot)), fal.ref_max(model))


def _one_clip(*, account_id, shot, provider, model, frame, tier, ctx) -> Optional[Estimate]:
    """The single estimate for a timed scene that renders as one clip, or
    None when it splits (timeline.renders_as_one). Its length is the
    scene's, fitted UP to the model; a model that holds the clip to
    references at only some resolutions (Grok: 480p and 720p) is REFUSED
    at any other, never quietly rendered without the photos."""
    name, wanted = _resolve(account_id, shot, provider, model, ctx)
    base = providers.check_render_choice(name, wanted, None, frame)
    axis = providers.model_options(base["provider"], base["model"])["duration"]
    if not timeline.renders_as_one(shot, axis):
        return None
    seconds = timeline.fit_seconds(axis, timeline.total_seconds(shot))
    choice = providers.check_render_choice(name, wanted, seconds, frame)
    _check_band(choice["provider"], choice["model"], int(choice["duration"]), tier,
                choice["frame"])
    refs = one_clip_references(shot, choice["provider"], choice["model"])
    if choice["provider"] == "fal":
        # every shot in one prompt must fit the model's own cap, else the
        # scene splits (2026-10-27: 1 in 23 real scenes was over Kling 3's
        # 3,072 before the kit was added)
        from . import fal
        pictures = timeline.one_clip_refs(shot)[:refs]
        target = timeline.one_clip_target(
            shot, dict(zip(pictures, fal.ref_tags(choice["model"], len(pictures)))))
        if target and len(target["prompt"]) > fal.prompt_max(choice["model"]):
            return None
    usd = float(choice["estimate_usd"])
    if refs:
        from . import fal
        spec = fal.ref_spec(choice["model"]) or {}
        allowed = spec.get("resolutions")
        if allowed and str(choice["frame"]) not in allowed:
            raise PricingRefused(
                "references_resolution",
                f"{choice['model']} renders with reference photos at "
                f"{' or '.join(allowed)} only, not {choice['frame']}")
        usd += float(spec.get("per_image_usd", 0)) * refs
    return Estimate(provider=choice["provider"], model=choice["model"],
                    seconds=int(choice["duration"]), frame=str(choice["frame"]),
                    part=None, provider_usd_micros=usd_micros(usd),
                    one_clip=True, references=refs)


def estimate_scene(*, account_id: Optional[int], shot: dict,
                   provider: Optional[str] = None, model: Optional[str] = None,
                   seconds=None, frame=None, tier: Optional[str] = None,
                   whole: bool = False, ctx=None) -> list[Estimate]:
    """What approving this scene would render, in order: one estimate per
    timed shot STILL WITHOUT A CLIP (windows_to_render -- approving again
    resumes, so it prices only what is left), or the single
    whole-scene render when the scene has no timeline. `seconds` applies
    to a whole-scene render only; a part's length is its window's.

    `whole` is the Director's Generate node: it renders the prompt it is
    handed as ONE clip whatever windows that prompt carries, so it is
    priced as one."""
    todo = None if whole else windows_to_render(shot)
    if todo is not None:
        if tier is None:
            tier = tier_for(account_id, ctx=ctx)
        one = _one_clip(account_id=account_id, shot=shot, provider=provider, model=model,
                        frame=frame, tier=tier, ctx=ctx)
        if one is not None:
            return [one]
        return [estimate(account_id=account_id, shot=shot, part=w["n"],
                         provider=provider, model=model, frame=frame, tier=tier,
                         ctx=ctx)
                for w in todo]
    return [estimate(account_id=account_id, shot=shot, provider=provider,
                     model=model, seconds=seconds, frame=frame, tier=tier, ctx=ctx)]


# --------------------------------------------------------------------------
# the quote
# --------------------------------------------------------------------------

def billable(account_id: Optional[int], provider: str) -> bool:
    """Would a render on this vendor be debited? Always, since BYOK was
    removed on 2026-09-26 -- the rule is still ledger.is_billable's, asked
    here with no lane marker because a Queue render never carries one."""
    return ledger.is_billable()


def quote(*, account_id: Optional[int], shot: dict, shot_id: int,
          part: Optional[int] = None, provider: Optional[str] = None,
          model: Optional[str] = None, seconds=None, frame=None,
          tier: Optional[str] = None) -> Optional[Quote]:
    """The price of one render in credits. (Optional because a caller
    that finds nothing billable -- none since BYOK went, 2026-09-26 -- got
    None.) `shot_id` is the concept's id: a scene is one row
    and its shot lives inside it, so that is the id a render is filed
    under everywhere else. Raises ValueError / PricingRefused."""
    priced = estimate(account_id=account_id, shot=shot, part=part, provider=provider,
                      model=model, seconds=seconds, frame=frame, tier=tier)
    # after the resolve, not before it: whose key it is can only be asked
    # of a vendor, and with no provider named there is not one yet
    if not billable(account_id, priced.provider):
        return None
    credits = credits_for(priced.provider_usd_micros)
    return Quote(pricing_version=PRICING_VERSION, account_id=account_id,
                 shot_id=int(shot_id), part=part, provider=priced.provider,
                 model=priced.model, seconds=priced.seconds, frame=priced.frame,
                 provider_usd_micros=priced.provider_usd_micros, credits=credits,
                 content_hash=signed_hash(shot, part, account_id=account_id,
                                          shot_id=shot_id),
                 line_items=_line_items(priced.model, priced.seconds, part, credits))


# --------------------------------------------------------------------------
# sign / verify -- so the thing that renders is provably the thing that
# was priced and approved
# --------------------------------------------------------------------------
# Wire shape: phq.<base64url(canonical json)>.<base64url(hmac-sha256)>,
# no padding. JWT-shaped without being a JWT -- no header, no algorithm
# field, so there is no `alg: none` to get wrong. The body uses short
# keys because it rides in request bodies and gets logged, and canonical
# JSON (sorted keys, no spaces, ascii) because the signature is over bytes.

def _secret() -> bytes:
    raw = (os.environ.get(SIGNING_ENV) or "").strip()
    if not raw:
        raise SigningUnconfigured()
    return raw.encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _canonical(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _line_items(model: str, seconds: int, part: Optional[int], credits: int) -> tuple:
    label = f"{model} · {seconds}s" + (f" · shot {part}" if part is not None else "")
    return ((label, credits, 1, "render"),)


def sign(q: Quote, *, now: Optional[int] = None, ttl: int = QUOTE_TTL) -> str:
    """The token for one quote. Raises SigningUnconfigured."""
    secret = _secret()
    iat = int(now if now is not None else time.time())
    body = {"v": TOKEN_VERSION, "pv": q.pricing_version, "acct": q.account_id,
            "shot": q.shot_id, "part": q.part, "prov": q.provider, "model": q.model,
            "frame": q.frame, "secs": q.seconds, "usd_micros": q.provider_usd_micros,
            "credits": q.credits, "chash": q.content_hash, "iat": iat, "exp": iat + int(ttl)}
    payload = _canonical(body)
    mac = hmac.new(secret, payload, hashlib.sha256).digest()
    return f"{TOKEN_PREFIX}.{_b64(payload)}.{_b64(mac)}"


def _refuse(reason: str, message: str) -> QuoteRefused:
    return QuoteRefused(reason, message)


def verify(token: str, *, account_id: Optional[int], shot: dict, shot_id: int,
           part: Optional[int] = None, now: Optional[int] = None) -> Quote:
    """The Quote a token stands for, or QuoteRefused. Never a bool.

    Checked in this order, and the order is the message: a token that
    was never ours is `bad_signature` before anything about it is read;
    then `retired_pricing`, `expired`, `wrong_account`, `wrong_render`
    (another shot, or another part of this one), and last
    `stale_content` -- the one that earns the design: edit the prompt or
    the references after quoting and the old price stops working.

    `wrong_account` should never happen through the UI; if it fires,
    somebody is replaying another tenant's quote, and the caller should
    log it loudly rather than answer a quiet 403.

    Raises SigningUnconfigured when there is no secret to check against."""
    secret = _secret()
    parts = (token or "").strip().split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price")
    try:
        payload, mac = _unb64(parts[1]), _unb64(parts[2])
    except (ValueError, TypeError):
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price") from None
    expected = hmac.new(secret, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price")
    try:
        body = json.loads(payload)
    except ValueError:
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price") from None
    if not isinstance(body, dict) or body.get("v") != TOKEN_VERSION \
            or _canonical(body) != payload:
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price")
    if body.get("pv") not in SUPPORTED_PRICING_VERSIONS:
        raise _refuse("retired_pricing", "prices changed -- re-quote")
    moment = int(now if now is not None else time.time())
    if not isinstance(body.get("exp"), int) or body["exp"] < moment:
        raise _refuse("expired", "this price is over an hour old -- re-quote")
    if body.get("acct") != account_id:
        raise _refuse("wrong_account", "this quote was not issued to this account")
    if "k" in body or body.get("shot") != int(shot_id) or body.get("part") != part:
        # "k" marks a studio token (below): same secret, never a shot's price
        raise _refuse("wrong_render", "this quote is for a different render")
    if body.get("chash") != signed_hash(shot, part, account_id=account_id, shot_id=shot_id):
        raise _refuse("stale_content", "the scene changed since this price -- re-quote")
    try:
        return Quote(pricing_version=body["pv"], account_id=body["acct"],
                     shot_id=int(body["shot"]), part=body["part"], provider=str(body["prov"]),
                     model=str(body["model"]), seconds=int(body["secs"]),
                     frame=str(body["frame"]), provider_usd_micros=int(body["usd_micros"]),
                     credits=int(body["credits"]), content_hash=str(body["chash"]),
                     line_items=_line_items(str(body["model"]), int(body["secs"]),
                                            body["part"], int(body["credits"])))
    except (KeyError, TypeError, ValueError):
        raise _refuse("bad_signature", "this quote isn't valid -- get a fresh price") from None


def configured() -> bool:
    """Whether quotes can be signed here at all -- the capability a card
    reads to know if a token will ride with its price."""
    return bool((os.environ.get(SIGNING_ENV) or "").strip())


# --------------------------------------------------------------------------
# the studio's signed quote -- a render no shot carries (2026-10-08)
# --------------------------------------------------------------------------
# The MCP studio surface renders images, clips, effects and element sheets
# that belong to no concept, so the shot token above has nothing to bind
# to. This is its sibling: the same secret, the same TTL, the same refusal
# codes, and a body that binds the TOOL and a hash of its exact normalized
# arguments (model, frame, length, prompt, reference ids, effect + options,
# element, project) -- change any of them after the yes and the token is
# `stale_content`. "k": "studio" keeps the two kinds apart: verify() above
# refuses a studio token as `wrong_render`, and verify_studio() a shot's.
#
# It carries a NONCE (`jti`), which the shot token deliberately does not:
# re-approving a shot is made harmless by the render loop's skip-parts-
# with-clips rule, and a free-standing render has no such rule -- the same
# yes would buy a second image. Single use is recorded by the caller in
# src/quote_redemptions.py; this module still writes nothing.

STUDIO_KIND = "studio"


@dataclass(frozen=True)
class StudioQuote:
    """A verified studio price. Duck-types as a Quote where src/charge.py
    reads one (`account_id`, `provider`, `credits`), so the hold is the
    number the person was shown."""
    pricing_version: str
    account_id: Optional[int]
    tool: str
    provider: str
    args_hash: str
    provider_usd_micros: int
    credits: int
    token_id: str
    issued_at: int
    expires_at: int


def args_hash(tool: str, args: dict) -> str:
    """What a studio price is ABOUT: the tool and its normalized arguments,
    as canonical JSON, hashed. The caller normalizes (defaults resolved,
    whitespace collapsed, ids deduplicated) so that two calls meaning the
    same render hash the same."""
    return hashlib.sha256(_canonical({"tool": tool, "args": args})).hexdigest()


def studio_quote(*, account_id: Optional[int], tool: str, provider: str, args: dict,
                 usd, now: Optional[int] = None, ttl: int = QUOTE_TTL) -> StudioQuote:
    """Price one studio render: the provider's USD -> credits through the
    one conversion every hold uses, bound to the tool and its arguments,
    with a fresh token id."""
    import secrets
    micros = usd_micros(usd)
    iat = int(now if now is not None else time.time())
    return StudioQuote(pricing_version=PRICING_VERSION, account_id=account_id, tool=tool,
                       provider=provider, args_hash=args_hash(tool, args),
                       provider_usd_micros=micros, credits=credits_for(micros),
                       token_id=secrets.token_urlsafe(12), issued_at=iat,
                       expires_at=iat + int(ttl))


def sign_studio(q: StudioQuote) -> str:
    """The token for one studio quote. Raises SigningUnconfigured."""
    secret = _secret()
    body = {"v": TOKEN_VERSION, "k": STUDIO_KIND, "pv": q.pricing_version,
            "acct": q.account_id, "tool": q.tool, "prov": q.provider,
            "ahash": q.args_hash, "usd_micros": q.provider_usd_micros,
            "credits": q.credits, "jti": q.token_id,
            "iat": q.issued_at, "exp": q.expires_at}
    payload = _canonical(body)
    mac = hmac.new(secret, payload, hashlib.sha256).digest()
    return f"{TOKEN_PREFIX}.{_b64(payload)}.{_b64(mac)}"


def verify_studio(token: str, *, account_id: Optional[int], tool: str, args: dict,
                  now: Optional[int] = None) -> StudioQuote:
    """The StudioQuote a token stands for, or QuoteRefused -- verify()'s
    order and codes: bad_signature, retired_pricing, expired,
    wrong_account, wrong_render (a shot's token, or another tool's), and
    stale_content (any argument changed since the price). Single use is
    NOT checked here (src/quote_redemptions.py). Raises
    SigningUnconfigured when there is no secret to check against."""
    secret = _secret()
    parts = (token or "").strip().split(".")
    bad = "this quote isn't valid -- get a fresh price"
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise _refuse("bad_signature", bad)
    try:
        payload, mac = _unb64(parts[1]), _unb64(parts[2])
    except (ValueError, TypeError):
        raise _refuse("bad_signature", bad) from None
    if not hmac.compare_digest(mac, hmac.new(secret, payload, hashlib.sha256).digest()):
        raise _refuse("bad_signature", bad)
    try:
        body = json.loads(payload)
    except ValueError:
        raise _refuse("bad_signature", bad) from None
    if not isinstance(body, dict) or body.get("v") != TOKEN_VERSION \
            or _canonical(body) != payload:
        raise _refuse("bad_signature", bad)
    if body.get("pv") not in SUPPORTED_PRICING_VERSIONS:
        raise _refuse("retired_pricing", "prices changed -- re-quote")
    moment = int(now if now is not None else time.time())
    if not isinstance(body.get("exp"), int) or body["exp"] < moment:
        raise _refuse("expired", "this price is over an hour old -- re-quote")
    if body.get("acct") != account_id:
        raise _refuse("wrong_account", "this quote was not issued to this account")
    if body.get("k") != STUDIO_KIND or body.get("tool") != tool:
        raise _refuse("wrong_render", "this quote is for a different render")
    if body.get("ahash") != args_hash(tool, args):
        raise _refuse("stale_content",
                      "the request changed since this price (a model, a length, a "
                      "frame, the prompt, a reference or an option) -- re-quote")
    try:
        return StudioQuote(pricing_version=body["pv"], account_id=body["acct"],
                           tool=str(body["tool"]), provider=str(body["prov"]),
                           args_hash=str(body["ahash"]),
                           provider_usd_micros=int(body["usd_micros"]),
                           credits=int(body["credits"]), token_id=str(body["jti"]),
                           issued_at=int(body["iat"]), expires_at=int(body["exp"]))
    except (KeyError, TypeError, ValueError):
        raise _refuse("bad_signature", bad) from None


# --------------------------------------------------------------------------
# the keyframes' signed quote -- a scene's stills, approved from a chat
# (2026-10-11)
# --------------------------------------------------------------------------
# The connector's `approve` drew a scene's keyframes on the scene id alone:
# a clip needed the quote's tokens and a still its single-use one, and the
# strip in between needed neither, so nothing tied that spend to a price
# anybody had been shown. This is the third token, for that door.
#
# It binds what a shot's token binds -- the account, the scene, the content
# hash -- plus WHICH stills (the timed shots still without one, by number;
# none for a scene that renders whole), the image model they are drawn on
# and the credits. Draw one of them, or edit the scene, and the old price
# stops working. "k": "keyframes" keeps it apart from the other two kinds:
# verify() refuses anything carrying a "k", verify_studio() anything that
# is not a studio token, and verify_keyframes() both of theirs.
#
# It carries a nonce like the studio token, for the studio token's reason:
# two approves racing each other both find every still undrawn, and without
# a record the same yes buys the strip twice. Single use is the caller's
# (src/quote_redemptions.py); this module still writes nothing.

KEYFRAMES_KIND = "keyframes"


@dataclass(frozen=True)
class KeyframeQuote:
    """A verified price for a scene's keyframe stills. `shots` is the timed
    shots it draws, by number -- empty for a scene that renders whole, whose
    one still belongs to no shot -- and `stills` how many that is."""
    pricing_version: str
    account_id: Optional[int]
    shot_id: int
    part: Optional[int]
    shots: tuple
    stills: int
    model: str
    credits: int
    content_hash: str
    token_id: str
    issued_at: int
    expires_at: int


def _shot_numbers(shots) -> list:
    return [int(n) for n in (shots or [])]


def keyframes_quote(*, account_id: Optional[int], shot: dict, shot_id: int,
                    shots, stills: int, model: str, credits: int,
                    part: Optional[int] = None, now: Optional[int] = None,
                    ttl: int = QUOTE_TTL) -> KeyframeQuote:
    """The quote for drawing `stills` keyframes of one scene, with a fresh
    token id. The caller says which stills and what they cost
    (scene_chain.keyframe_quote, the number every card prints); this binds
    them to the scene as it stands."""
    import secrets
    iat = int(now if now is not None else time.time())
    return KeyframeQuote(pricing_version=PRICING_VERSION, account_id=account_id,
                         shot_id=int(shot_id), part=part,
                         shots=tuple(_shot_numbers(shots)), stills=int(stills),
                         model=str(model), credits=int(credits),
                         content_hash=content_hash(shot),
                         token_id=secrets.token_urlsafe(12), issued_at=iat,
                         expires_at=iat + int(ttl))


def sign_keyframes(q: KeyframeQuote) -> str:
    """The token for one keyframe quote. Raises SigningUnconfigured."""
    secret = _secret()
    body = {"v": TOKEN_VERSION, "k": KEYFRAMES_KIND, "pv": q.pricing_version,
            "acct": q.account_id, "shot": q.shot_id, "part": q.part,
            "shots": list(q.shots), "stills": q.stills, "model": q.model,
            "credits": q.credits, "chash": q.content_hash, "jti": q.token_id,
            "iat": q.issued_at, "exp": q.expires_at}
    payload = _canonical(body)
    mac = hmac.new(secret, payload, hashlib.sha256).digest()
    return f"{TOKEN_PREFIX}.{_b64(payload)}.{_b64(mac)}"


def read_keyframes(token: str, *, account_id: Optional[int], shot_id: int,
                   part: Optional[int] = None,
                   now: Optional[int] = None) -> KeyframeQuote:
    """The KeyframeQuote a token carries, checked for everything that is
    true of the TOKEN: ours (bad_signature), on current prices
    (retired_pricing), under an hour old (expired), issued to this account
    (wrong_account), and a keyframe quote for this scene and this shot of
    it (wrong_render -- a clip's token, a studio token, another scene).

    Whether it still describes the scene is check_keyframes', deliberately
    apart: a caller looks a token up among the redeemed ones BETWEEN the
    two, because a strip that is halfway drawn makes its own token stale,
    and "you already used this, here is its job" is the answer a repeat
    wants -- "re-quote" would send it off to buy the rest a second time.
    Raises SigningUnconfigured when there is no secret to check against."""
    secret = _secret()
    parts = (token or "").strip().split(".")
    bad = "this quote isn't valid -- get a fresh price"
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise _refuse("bad_signature", bad)
    try:
        payload, mac = _unb64(parts[1]), _unb64(parts[2])
    except (ValueError, TypeError):
        raise _refuse("bad_signature", bad) from None
    if not hmac.compare_digest(mac, hmac.new(secret, payload, hashlib.sha256).digest()):
        raise _refuse("bad_signature", bad)
    try:
        body = json.loads(payload)
    except ValueError:
        raise _refuse("bad_signature", bad) from None
    if not isinstance(body, dict) or body.get("v") != TOKEN_VERSION \
            or _canonical(body) != payload:
        raise _refuse("bad_signature", bad)
    if body.get("pv") not in SUPPORTED_PRICING_VERSIONS:
        raise _refuse("retired_pricing", "prices changed -- re-quote")
    moment = int(now if now is not None else time.time())
    if not isinstance(body.get("exp"), int) or body["exp"] < moment:
        raise _refuse("expired", "this price is over an hour old -- re-quote")
    if body.get("acct") != account_id:
        raise _refuse("wrong_account", "this quote was not issued to this account")
    if body.get("k") != KEYFRAMES_KIND or body.get("shot") != int(shot_id) \
            or body.get("part") != part:
        raise _refuse("wrong_render", "this quote is for a different render")
    try:
        return KeyframeQuote(pricing_version=body["pv"], account_id=body["acct"],
                             shot_id=int(body["shot"]), part=body["part"],
                             shots=tuple(_shot_numbers(body["shots"])),
                             stills=int(body["stills"]), model=str(body["model"]),
                             credits=int(body["credits"]), content_hash=str(body["chash"]),
                             token_id=str(body["jti"]), issued_at=int(body["iat"]),
                             expires_at=int(body["exp"]))
    except (KeyError, TypeError, ValueError):
        raise _refuse("bad_signature", bad) from None


def check_keyframes(q: KeyframeQuote, *, shot: dict, shots, stills: int, model: str,
                    credits: int) -> None:
    """Whether a read KeyframeQuote still describes the scene: `shot` is
    the scene's shot as it stands, and `shots` / `stills` / `model` /
    `credits` the caller's LIVE answer for what a draw would make and
    cost. Raises QuoteRefused `stale_content` -- the scene was edited, or
    the stills to draw, the model or the price are no longer what was
    quoted (one of them has been drawn since, most often)."""
    if q.content_hash != content_hash(shot):
        raise _refuse("stale_content", "the scene changed since this price -- re-quote")
    if list(q.shots) != _shot_numbers(shots) or q.stills != int(stills) \
            or q.model != str(model) or q.credits != int(credits):
        raise _refuse("stale_content",
                      "the stills to draw, or their price, changed since this quote "
                      "-- re-quote")


def verify_keyframes(token: str, *, account_id: Optional[int], shot: dict, shot_id: int,
                     shots, stills: int, model: str, credits: int,
                     part: Optional[int] = None,
                     now: Optional[int] = None) -> KeyframeQuote:
    """read_keyframes then check_keyframes: the KeyframeQuote a token stands
    for, or QuoteRefused in verify()'s order -- bad_signature,
    retired_pricing, expired, wrong_account, wrong_render, stale_content.
    Single use is NOT checked here (src/quote_redemptions.py)."""
    q = read_keyframes(token, account_id=account_id, shot_id=shot_id, part=part, now=now)
    check_keyframes(q, shot=shot, shots=shots, stills=stills, model=model, credits=credits)
    return q


# --------------------------------------------------------------------------
# what a card shows
# --------------------------------------------------------------------------

def display(*, account_id: Optional[int], shot: dict, shot_id: int,
            provider: Optional[str] = None, model: Optional[str] = None,
            seconds=None, frame=None, tier: Optional[str] = None,
            whole: bool = False, ctx=None) -> dict:
    """The priced plan for one approve, as JSON a card can print without
    doing arithmetic: every render it would make, its length, the
    provider's estimate, and the credits it would cost.

    `estimate_usd` stays the PROVIDER's estimate -- the label the Queue
    has always shown -- so that while MARKUP is 1.0 no number on any
    screen moves. Raises ValueError / PricingRefused.

    `ctx` is a providers.RenderContext for this account -- a LISTING
    passes one so the per-account lookups happen once per request, not
    once per card. None (every other caller) is the behaviour before it
    existed. quote(), the path toward a hold, takes none and always asks."""
    parts = estimate_scene(account_id=account_id, shot=shot, provider=provider,
                           model=model, seconds=seconds, frame=frame, tier=tier,
                           whole=whole, ctx=ctx)
    if not parts:
        raise PricingRefused("nothing_to_render", "every shot of this scene has a clip")
    head = parts[0]
    # a listing's ctx already read this account's key rows; the question
    # and the rule are unchanged, only the read underneath is not repeated
    with providers.key_scope(ctx, account_id):
        charged = billable(account_id, head.provider)
    signed = charged and configured()
    renders = []
    for p in parts:
        credits = credits_for(p.provider_usd_micros) if charged else None
        token = None
        if signed:
            # one token per render, never one per scene: the render loop
            # holds per part as it reaches each, so a scene that fails on
            # shot 1 has nothing of shot 2's locked up
            token = sign(Quote(pricing_version=PRICING_VERSION, account_id=account_id,
                               shot_id=int(shot_id), part=p.part, provider=p.provider,
                               model=p.model, seconds=p.seconds, frame=p.frame,
                               provider_usd_micros=p.provider_usd_micros, credits=credits,
                               content_hash=signed_hash(shot, p.part,
                                                        account_id=account_id,
                                                        shot_id=shot_id),
                               line_items=_line_items(p.model, p.seconds, p.part, credits)))
        renders.append({"part": p.part, "seconds": p.seconds,
                        "estimate_usd": round(p.usd, 4), "credits": credits, "token": token})
    micros = sum(p.provider_usd_micros for p in parts)
    return {"pricing_version": PRICING_VERSION,
            "shot_id": int(shot_id),
            "provider": head.provider, "model": head.model, "frame": head.frame,
            "timed": head.part is not None,
            # a timed scene rendered as ONE clip, its cuts in the prompt:
            # `timed` is False (one render, one token) and the shots are
            # inside it; `references` is how many photos go with it
            "one_clip": head.one_clip,
            "references": head.references,
            "durations": [p.seconds for p in parts],
            "estimate_usd": round(micros / _MICROS, 4),
            # tokens ride only when there is something to charge AND a
            # secret to sign with; a client that finds none approves as
            # it always did, and the route falls to the same gate as before
            "signed": signed,
            "credits": sum(r["credits"] for r in renders) if charged else None,
            "content_hash": content_hash(shot),
            "renders": renders}


__all__ = ["PRICING_VERSION", "CREDIT_CENTS", "MARKUP", "CREDIT_FLOOR",
           "still_usd", "still_credits",
           "PricingRefused", "Estimate", "Quote",
           "usd_micros", "credits_for", "content_hash",
           "windows_to_render", "estimate", "estimate_scene", "billable", "quote", "display",
           "catalog_rows", "catalog_models",
           "SUPPORTED_PRICING_VERSIONS", "SIGNING_ENV", "SIGNING_COMMAND", "QUOTE_TTL",
           "SigningUnconfigured", "QuoteRefused", "sign", "verify", "configured",
           "StudioQuote", "args_hash", "studio_quote", "sign_studio", "verify_studio",
           "KeyframeQuote", "keyframes_quote", "sign_keyframes", "read_keyframes",
           "check_keyframes", "verify_keyframes"]


# --------------------------------------------------------------------------
# the public catalog -- what the site prints, generated here
# --------------------------------------------------------------------------

CATALOG_CLIP_SECONDS = 5
# The public-facing name for every renderable (provider, model). A model
# not listed here is still renderable and still priced; it just is not
# advertised. Keep this the honest subset: what a plan can actually buy.
CATALOG_MODELS: tuple[tuple[str, str, str, str], ...] = (
    # provider, model id, public name, one line -- all on fal since
    # 2026-09-26, the only video renderer
    ("fal", "ltx2.3", "LTX 2.3", "Fast, cheap, 1080p and up. The workhorse."),
    ("fal", "ltx2.5-fast", "LTX 2.5 Fast", "LTX's newest, with sound, up to 20 seconds, 720p to 4K."),
    ("fal", "ltx2.5", "LTX 2.5 Pro", "LTX 2.5 at full quality, with sound, 720p or 1080p."),
    ("fal", "wan3", "Wan 3.0", "Open-weight realism up to 1080p."),
    ("fal", "kling3-turbo-pro", "Kling 3 Turbo Pro", "Cinematic motion, strong on people."),
    ("fal", "seedance2-fast", "Seedance 2.0 Fast", "ByteDance's quick tier, up to 720p."),
    ("fal", "seedance2", "Seedance 2.0", "Seedance at full quality, up to 1080p."),
    ("fal", "seedance2.5", "Seedance 2.5", "ByteDance's newest, with sound, up to 30 seconds and 1080p."),
    ("fal", "veo3.1", "Veo 3.1", "Google's top model, with sound."),
    ("fal", "grok1.5", "Grok Imagine 1.5", "xAI's video model, with sound, 1 to 15 seconds, seven frame shapes."),
    ("fal", "grok1.5-lite", "Grok Imagine 1.5 Lite", "Grok's quick tier, with sound, up to 1080p."),
)


def catalog_rows() -> tuple[tuple[str, str, str, str], ...]:
    """CATALOG_MODELS plus a row for every parked slot that is READY
    (fal.SLOTS, 2026-10-22): a slot whose flag is off or whose price is
    None is not here, so the brain, the connector and the site never see
    it. Read live, never cached."""
    from . import fal
    extra = tuple(("fal", key, fal.SLOTS[key]["label"], fal.SLOTS[key]["blurb"])
                  for key in fal.ready_slots()
                  if key not in {m for _p, m, _n, _b in CATALOG_MODELS})
    return CATALOG_MODELS + extra


def catalog_models() -> list[dict]:
    """Every advertised model with its tier, legal lengths and the credits
    a CATALOG_CLIP_SECONDS render costs at the model's default frame --
    priced by the same estimators the Queue prices with, so the site
    cannot print a number the card would not."""
    out = []
    for provider, model, name, blurb in catalog_rows():
        band = providers.band_for(provider, model)
        try:
            choice = providers.check_render_choice(provider, model, CATALOG_CLIP_SECONDS, None)
            micros = usd_micros(choice["estimate_usd"])
            seconds = int(choice["duration"])
        except Exception:
            # a model whose legal lengths exclude the catalog clip: price
            # its default length and say so
            choice = providers.check_render_choice(provider, model, None, None)
            micros = usd_micros(choice["estimate_usd"])
            seconds = int(choice["duration"])
        out.append({"provider": provider, "model": model, "name": name, "blurb": blurb,
                    "tier": band.tier, "max_seconds": band.max_seconds,
                    "seconds": seconds, "credits": credits_for(micros),
                    "frame": str(choice["frame"])})
    return out


def public_catalog() -> dict:
    """The site's pricing data, in one JSON document: plans, the top-up,
    the tiers in order, every advertised model and its price per clip, the
    peg. web/src/content/pricing.json IS this, committed; the pages import
    it and tests/test_plans.py pins the two together."""
    return {
        "pricing_version": PRICING_VERSION,
        "credit_cents": CREDIT_CENTS,
        "markup": MARKUP,
        "credit_floor": CREDIT_FLOOR,
        "expiry_months": ledger.EXPIRY_MONTHS,
        "clip_seconds": CATALOG_CLIP_SECONDS,
        "tiers": list(providers.TIERS),
        "yearly_discount": YEARLY_DISCOUNT,
        "plans": [{"key": p.key, "name": p.name, "tier": p.tier,
                   "monthly_usd": p.monthly_usd, "yearly_usd": p.yearly_usd,
                   "yearly_monthly_usd": p.yearly_monthly_usd, "credits": p.credits,
                   "blurb": p.blurb, "popular": p.popular,
                   "storage_gb": p.storage_gb}
                  for p in PLANS.values()],
        "topup": {"key": TOPUP.key, "name": TOPUP.name, "usd": TOPUP.usd,
                  "credits": TOPUP.credits},
        # the free start (2026-10-11): what a new workspace is granted on its
        # first sign-in, no card. The default, not the live env -- the page is
        # built ahead of time, and PHANTRA_SIGNUP_CREDITS on a deployment
        # should match it.
        "trial": {"credits": _trial_credits(), "storage_gb": FREE_STORAGE_GB},
        "models": catalog_models(),
        # what the studio charges before a clip exists: a still (2026-09-28).
        # A Create is included in the plan (2026-09-29) -- 0 here, not absent,
        # so the site can say so rather than guess.
        "actions": {
            "create": 0,
            "still": {"standard": still_credits("gemini-2.5-flash-image"),
                      "pro": still_credits("gemini-3-pro-image-preview")},
            "talking_photo": talking_photo_catalog(),
        },
    }


def talking_photo_catalog() -> dict:
    """A talking photo's prices for the site (2026-10-20): credits for a
    10-second clip, the shortest and the per-plan longest voice, and the
    smallest voice preview -- off src/talking_photo.py's dated rows through
    the same credits_for every hold uses."""
    from . import talking_photo as tp  # lazy, as _trial_credits
    return {
        "per_10s": credits_for(usd_micros(tp.talk_usd(10))),
        "clips": [{"seconds": n, "credits": credits_for(usd_micros(tp.talk_usd(n)))}
                  for n in (10, *sorted(tp.PLAN_AUDIO_CAP.values()))],
        "min_seconds": int(tp.AUDIO_MIN_SECONDS),
        "max_seconds": dict(tp.PLAN_AUDIO_CAP),
        "voice_preview_from": credits_for(usd_micros(tp.voice_usd("x" * tp.SCRIPT_MIN_CHARS))),
    }


def _trial_credits() -> int:
    from . import accounts  # lazy: accounts is not on pricing's import path
    return accounts.DEFAULT_SIGNUP_CREDITS


CATALOG_PATH = "web/src/content/pricing.json"


def export_catalog(path: str = CATALOG_PATH) -> str:
    from pathlib import Path
    text = json.dumps(public_catalog(), indent=2, sort_keys=False) + "\n"
    Path(path).write_text(text)
    return text


if __name__ == "__main__":   # pragma: no cover
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export_catalog(sys.argv[2] if len(sys.argv) > 2 else CATALOG_PATH)
        print(f"wrote {sys.argv[2] if len(sys.argv) > 2 else CATALOG_PATH}")
    else:
        print(json.dumps(public_catalog(), indent=2))
