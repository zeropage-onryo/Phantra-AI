#!/usr/bin/env python3
"""
The cost table: provider USD against credits charged, per effect row and
per video / image model row, plus the Founding 500 free-grant arithmetic
(docs/tasks/task-overnight-2026-10-22.md, group 7, 2026-10-22).

REPORT ONLY. Reads the dated tables (src/effects.py, fal.VIDEO_MODELS,
fal.IMAGE_MODELS, spend.DEFAULT_PRICES, src/talking_photo.py) and prices
every row with the SAME functions a card and a hold use (effects.quote_usd,
providers.check_render_choice, fal.image_usd, pricing.still_usd,
pricing.credits_for over pricing.usd_micros -- the pair ledger.charge_credits
delegates to), so a number here is a number the studio would charge. No
database, no network, no key: it can be re-run any day.

    venv/bin/python -m ops.cost_table                 # prints the markdown
    venv/bin/python -m ops.cost_table --write [PATH]  # writes it (default: docs/stats/cost-per-effect-<today>.md)

Representative option set per row: a model's DEFAULT duration and
resolution (check_render_choice with nothing picked); an effect's default
options, a required option with no default at its first value; a clip
effect priced off a REPRESENTATIVE source (PROBE below: 5 s, 1080p, 30 fps),
because those rows are priced off the clip they are given and have no
"from" price otherwise.

A row is FLAGGED when the credits charged, at retail parity (one credit =
one cent), are under the provider's USD -- i.e. the studio would lose money
on it -- and NOTED when the CREDIT_FLOOR, not MARKUP, set the price.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Optional

from src import accounts, effects, fal, ledger, pricing, providers, talking_photo

# One credit's retail value in USD: what every plan sells it at
# ($15/1500, $35/3500, $95/9500 -- all one cent; the $10/750 top-up is 1.33c).
CREDIT_USD = Fraction(pricing.CREDIT_CENTS, 100)
MARKUP = Fraction(pricing.MARKUP)

# the representative source clip for effects priced off the clip
PROBE = {"seconds": 5.0, "width": 1920, "height": 1080, "fps": 30.0}

# --- the Founding 500 (the sprint doc, as summarised in the task file) ------
FOUNDING_MEMBERS = 500
FOUNDING_SIGNUP_CREDITS = 300          # the doc's grant per member
FOUNDING_SHARE_BONUS_MAX = 300         # per member per month, at most
FOUNDING_WEEKLY_PRIZES = 4
FOUNDING_PRIZE_CREDITS = 2_500
FOUNDING_CEILING_USD = 3_100           # the doc's month-one ceiling, at retail


def credits(usd: float) -> int:
    """The charge for a provider price, exactly as a hold takes it."""
    return pricing.credits_for(pricing.usd_micros(usd))


def credits_unfloored(usd: float) -> int:
    """What MARKUP alone would charge, before CREDIT_FLOOR."""
    micros = pricing.usd_micros(usd)
    scaled = Fraction(micros) * MARKUP * pricing.CREDIT_CENTS
    return -((-scaled.numerator) // (scaled.denominator * 10_000))


def implied_markup(usd: float, charged: int) -> Optional[Fraction]:
    if not usd:
        return None
    return Fraction(charged) * CREDIT_USD / Fraction(str(usd))


def _fmt_markup(m: Optional[Fraction]) -> str:
    return "n/a" if m is None else f"{float(m):.2f}x"


def _flags(usd: float, charged: int) -> str:
    out = []
    if Fraction(charged) * CREDIT_USD < Fraction(str(usd)):
        out.append("**BELOW COST**")
    if usd and charged == pricing.CREDIT_FLOOR and credits_unfloored(usd) < pricing.CREDIT_FLOOR:
        out.append("floor")
    return ", ".join(out)


# --------------------------------------------------------------------------
# the rows
# --------------------------------------------------------------------------

def _default_options(effect: str) -> dict:
    row = effects.spec(effect)
    chosen = {k: (o.get("default") if o.get("default") is not None else list(o["values"])[0])
              for k, o in row["options"].items()
              if o.get("required") or o.get("default") is not None}
    return effects.check_options(effect, chosen)


def effect_rows() -> list[dict]:
    rows = []
    for name, row in effects.EFFECTS.items():
        opts = _default_options(name)
        probe = PROBE if row.get("probe") else None
        usd = effects.quote_usd(name, opts, probe)
        charged = credits(usd)
        shown = ", ".join(f"{k}={v}" for k, v in opts.items()) or "-"
        if probe:
            shown = (shown + "; " if shown != "-" else "") + "source 5s 1080p 30fps"
        rows.append({"id": name, "label": row["label"], "category": row["category"],
                     "options": shown, "usd": usd, "credits": charged,
                     "markup": implied_markup(usd, charged), "flags": _flags(usd, charged),
                     "checked": row.get("checked", effects.CHECKED)})
    return rows


def video_rows() -> list[dict]:
    rows = []
    for model, spec in fal.VIDEO_MODELS.items():
        choice = providers.check_render_choice("fal", model, None, None)
        usd = float(choice["estimate_usd"])
        charged = credits(usd)
        rows.append({"id": model, "seconds": int(choice["duration"]),
                     "frame": str(choice["frame"]),
                     "per_second": fal.price_per_second(model, str(choice["frame"])),
                     "usd": usd, "credits": charged,
                     "markup": implied_markup(usd, charged), "flags": _flags(usd, charged),
                     "checked": spec.get("checked", "?")})
    return rows


def video_resolution_rows() -> list[dict]:
    rows = []
    for model, spec in fal.VIDEO_MODELS.items():
        default = providers.check_render_choice("fal", model, None, None)
        seconds = int(default["duration"])
        for res in spec["resolutions"]:
            usd = round(fal.price_per_second(model, res) * seconds, 4)
            charged = credits(usd)
            rows.append({"id": model, "seconds": seconds, "frame": res,
                         "per_second": fal.price_per_second(model, res),
                         "usd": usd, "credits": charged,
                         "markup": implied_markup(usd, charged),
                         "flags": _flags(usd, charged)})
    return rows


def image_rows() -> list[dict]:
    rows = []
    for model, spec in fal.IMAGE_MODELS.items():
        usd = fal.image_usd(model, fal.DEFAULT_IMAGE_ASPECT)
        charged = credits(usd)
        rows.append({"id": model, "label": spec["label"], "provider": "fal",
                     "usd": usd, "credits": charged,
                     "markup": implied_markup(usd, charged), "flags": _flags(usd, charged),
                     "checked": str(spec.get("checked", "?")).split(" ")[0]})
    for model in ("gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-3-pro-image"):
        usd = pricing.still_usd(model)
        charged = pricing.still_credits(model)
        rows.append({"id": model, "label": "Nano Banana" if "2.5" in model else "Nano Banana Pro",
                     "provider": "gemini", "usd": usd, "credits": charged,
                     "markup": implied_markup(usd, charged), "flags": _flags(usd, charged),
                     "checked": "2026-09-04 (spend.DEFAULT_PRICES)"})
    return rows


def talking_rows() -> list[dict]:
    rows = []
    for seconds in (10, *sorted(talking_photo.PLAN_AUDIO_CAP.values())):
        usd = talking_photo.talk_usd(seconds)
        charged = credits(usd)
        rows.append({"id": f"talking photo ({talking_photo.TALK['id']}) {seconds}s",
                     "usd": usd, "credits": charged, "markup": implied_markup(usd, charged),
                     "flags": _flags(usd, charged)})
    for chars in (talking_photo.SCRIPT_MIN_CHARS, 500, talking_photo.SCRIPT_MAX_CHARS):
        usd = talking_photo.voice_usd("x" * chars)
        charged = credits(usd)
        rows.append({"id": f"voice preview ({talking_photo.VOICE['id']}) {chars} chars",
                     "usd": usd, "credits": charged, "markup": implied_markup(usd, charged),
                     "flags": _flags(usd, charged)})
    return rows


# --------------------------------------------------------------------------
# the free-grant arithmetic
# --------------------------------------------------------------------------

def _fixed_credits() -> int:
    """The month-one credits that do not depend on the signup grant: every
    member's full share bonus and every weekly prize."""
    return (FOUNDING_MEMBERS * FOUNDING_SHARE_BONUS_MAX
            + FOUNDING_WEEKLY_PRIZES * FOUNDING_PRIZE_CREDITS)


def grant_math(signup: int = FOUNDING_SIGNUP_CREDITS) -> dict:
    """Month one of the Founding 500, worst case: every member gets the
    signup grant, every member earns the full share bonus, every prize is
    paid, and EVERY credit is spent (so provider cost = retail / MARKUP --
    the floor and the ceil() both move the real provider cost DOWN from
    this, never up)."""
    bonus = FOUNDING_MEMBERS * FOUNDING_SHARE_BONUS_MAX
    prizes = FOUNDING_WEEKLY_PRIZES * FOUNDING_PRIZE_CREDITS
    signup_total = FOUNDING_MEMBERS * signup
    total = signup_total + bonus + prizes
    retail = Fraction(total) * CREDIT_USD
    provider = retail / MARKUP
    return {"signup": signup, "signup_total": signup_total, "bonus": bonus, "prizes": prizes,
            "total": total, "retail_usd": retail, "provider_usd": provider}


def largest_signup_at_retail_ceiling() -> int:
    """The biggest per-member signup grant whose worst month stays at or
    under FOUNDING_CEILING_USD counted at RETAIL (one credit = one cent)."""
    ceiling_credits = int(Fraction(FOUNDING_CEILING_USD) / CREDIT_USD)
    return max(0, (ceiling_credits - _fixed_credits()) // FOUNDING_MEMBERS)


def largest_signup_at_provider_ceiling() -> int:
    """The same, with the ceiling read as PROVIDER money: a credit costs
    the studio retail / MARKUP, so $3,100 of real money is MARKUP x more
    credits."""
    ceiling_credits = int(Fraction(FOUNDING_CEILING_USD) * MARKUP / CREDIT_USD)
    return max(0, (ceiling_credits - _fixed_credits()) // FOUNDING_MEMBERS)


# --------------------------------------------------------------------------
# the markdown
# --------------------------------------------------------------------------

def _usd(x: float) -> str:
    return f"${float(x):.4f}".rstrip("0").rstrip(".") if x else "$0"


def _money(x: Fraction) -> str:
    return f"${float(x):,.2f}"


def render(today: Optional[str] = None) -> str:
    today = today or date.today().isoformat()
    out: list[str] = []
    w = out.append
    w(f"# Cost per effect and per model, {today}")
    w("")
    w("Generated by `venv/bin/python -m ops.cost_table --write` (report-only, re-runnable). "
      "Every USD is the provider's price off the dated table in the code, and every credit "
      "figure is what a hold takes for it (`pricing.credits_for(pricing.usd_micros(usd))`, "
      "the pair `ledger.charge_credits` delegates to). Nothing here was run; no credit was spent.")
    w("")
    w(f"- `pricing.MARKUP` = **{pricing.MARKUP}** (credits = provider USD x 100 x markup, rounded up)")
    w(f"- `pricing.CREDIT_FLOOR` = **{pricing.CREDIT_FLOOR}** credits per billable render, still or effect")
    w(f"- one credit = **{pricing.CREDIT_CENTS} cent** at retail on every plan "
      f"({', '.join(f'{p.name} ${p.monthly_usd}/{p.credits}' for p in pricing.PLANS.values())}); "
      f"the top-up is ${pricing.TOPUP.usd}/{pricing.TOPUP.credits} (1.33c)")
    w("- \"implied markup\" = credits x $0.01 / provider USD. Above 2.4x means the floor or the "
      "round-up set the price; **BELOW COST** would mean the credits are worth less than the "
      "provider's invoice at retail parity.")
    w("")

    # effects
    w("## Effects (`src/effects.py`)")
    w("")
    w("Representative option set: the row's defaults, a required option at its first value; "
      "clip effects priced off a 5 s, 1080p, 30 fps source (those rows have no \"from\" "
      "price -- `effects.default_usd` returns None -- so a real quote moves with the clip).")
    w("")
    w("| effect | category | options priced | provider USD | credits | implied markup | flags | checked |")
    w("|---|---|---|---:|---:|---:|---|---|")
    for r in effect_rows():
        w(f"| `{r['id']}` ({r['label']}) | {r['category']} | {r['options']} | {_usd(r['usd'])} "
          f"| {r['credits']} | {_fmt_markup(r['markup'])} | {r['flags']} | {r['checked']} |")
    w("")
    w("Clip effects scale with the source: `upscale` is $0.02/s at 1080p out (x2 above 30 fps), "
      "`add-sound` $0.001/s (capped at 30 s), `reframe` $0.06/s and `reframe-hq` $0.20/s "
      "(clips to 10 s), `remove-video-background` $0.0225 per started 30 frames, and the Bria "
      "variant $0.14/s. The markup holds at every length; only the floor changes the ratio.")
    w("")

    # video models
    w("## Video models (`fal.VIDEO_MODELS`), at the model's default length and resolution")
    w("")
    w("| model | seconds | resolution | USD/s | provider USD | credits | implied markup | flags | checked |")
    w("|---|---:|---|---:|---:|---:|---:|---|---|")
    for r in video_rows():
        w(f"| `{r['id']}` | {r['seconds']} | {r['frame']} | {_usd(r['per_second'])} | {_usd(r['usd'])} "
          f"| {r['credits']} | {_fmt_markup(r['markup'])} | {r['flags']} | {r['checked']} |")
    w("")
    w("Every resolution the table allows, at the same default length:")
    w("")
    w("| model | seconds | resolution | USD/s | provider USD | credits | implied markup | flags |")
    w("|---|---:|---|---:|---:|---:|---:|---|")
    for r in video_resolution_rows():
        w(f"| `{r['id']}` | {r['seconds']} | {r['frame']} | {_usd(r['per_second'])} | {_usd(r['usd'])} "
          f"| {r['credits']} | {_fmt_markup(r['markup'])} | {r['flags']} |")
    w("")

    # image models
    w("## Image models (`fal.IMAGE_MODELS` and the Gemini stills), one still at the default frame")
    w("")
    w("| model | provider | provider USD | credits | implied markup | flags | checked |")
    w("|---|---|---:|---:|---:|---|---|")
    for r in image_rows():
        w(f"| `{r['id']}` ({r['label']}) | {r['provider']} | {_usd(r['usd'])} | {r['credits']} "
          f"| {_fmt_markup(r['markup'])} | {r['flags']} | {r['checked']} |")
    w("")
    w("FLUX.2 Pro and FLUX 1.1 Pro bill per megapixel (a 1 MP frame here); a reference-image "
      "edit on FLUX.2 Pro adds $0.015 per reference. GPT Image 2.5 is token-billed by size and "
      "held at a rounded-up $0.06.")
    w("")

    # talking photo
    w("## Talking photo and voice (`src/talking_photo.py`)")
    w("")
    w("| item | provider USD | credits | implied markup | flags |")
    w("|---|---:|---:|---:|---|")
    for r in talking_rows():
        w(f"| {r['id']} | {_usd(r['usd'])} | {r['credits']} | {_fmt_markup(r['markup'])} | {r['flags']} |")
    w("")

    # below-cost summary
    all_rows = (effect_rows(), video_rows(), video_resolution_rows(), image_rows(), talking_rows())
    flagged = [r["id"] for rows in all_rows for r in rows if "BELOW COST" in r["flags"]]
    floored = sorted({r["id"] for rows in all_rows for r in rows if "floor" in r["flags"]})
    w("## Rows priced below cost")
    w("")
    if flagged:
        w("**" + ", ".join(f"`{f}`" for f in flagged) + "**")
    else:
        w("**None.** With `MARKUP` at 2.4 and the round-up in `credits_for`, every row charges at "
          "least 2.4x the provider's price; the only way a row goes below cost is a provider "
          "price that rose after its `checked` date without the table moving, which this "
          "script cannot see. Re-check the dated rows before a price-sensitive launch.")
    w("")
    w(f"Rows where the {pricing.CREDIT_FLOOR}-credit floor, not the markup, set the price "
      f"(the implied markup is above 2.4x): " + (", ".join(f"`{f}`" for f in floored) or "none") + ".")
    w("")
    w("What the credits do NOT cover: the brain's model text (free on a plan, carried by the "
      "markup; the trial gets `pricing.trial_thinking_usd()` = "
      f"${pricing.trial_thinking_usd():.2f} of Gemini text once), storage on R2, and Stripe's cut.")
    w("")

    # grant math
    w("## Free-grant math: the Founding 500")
    w("")
    w(f"The sprint doc's offer, month one, worst case: **{FOUNDING_MEMBERS} members** x "
      f"**{FOUNDING_SIGNUP_CREDITS} signup credits**, share bonuses of up to "
      f"**{FOUNDING_SHARE_BONUS_MAX} credits per member per month**, "
      f"**{FOUNDING_WEEKLY_PRIZES} weekly prizes of {FOUNDING_PRIZE_CREDITS:,} credits**, "
      f"against a **${FOUNDING_CEILING_USD:,} retail ceiling** (one credit = one cent).")
    w("")
    w("Two ways to read a credit given away:")
    w("")
    w("- **Retail value**: credits x $0.01 -- what the same credits would have sold for.")
    w(f"- **Provider cost**: credits x $0.01 / {pricing.MARKUP} -- what fal or Gemini bills the "
      "studio when every one of them is spent (the hold is provider USD x 2.4 rounded up, so "
      "the real cost is at most this; the floor and the ceil() only lower it).")
    w("")
    doc = grant_math(FOUNDING_SIGNUP_CREDITS)
    default = grant_math(accounts.DEFAULT_SIGNUP_CREDITS)
    w("| scenario | signup credits | bonuses | prizes | total credits | retail value | provider cost |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for label, g in ((f"the doc's grant ({FOUNDING_SIGNUP_CREDITS}/member)", doc),
                     (f"today's default `PHANTRA_SIGNUP_CREDITS` ({accounts.DEFAULT_SIGNUP_CREDITS}/member)", default)):
        w(f"| {label} | {g['signup_total']:,} | {g['bonus']:,} | {g['prizes']:,} | {g['total']:,} "
          f"| {_money(g['retail_usd'])} | {_money(g['provider_usd'])} |")
    w("")
    w("Arithmetic, the doc's grant: "
      f"{FOUNDING_MEMBERS} x {FOUNDING_SIGNUP_CREDITS} = {doc['signup_total']:,}; "
      f"+ {FOUNDING_MEMBERS} x {FOUNDING_SHARE_BONUS_MAX} = {doc['bonus']:,}; "
      f"+ {FOUNDING_WEEKLY_PRIZES} x {FOUNDING_PRIZE_CREDITS:,} = {doc['prizes']:,}; "
      f"= {doc['total']:,} credits = {_money(doc['retail_usd'])} retail "
      f"= {_money(doc['provider_usd'])} at the provider.")
    w("")
    at_retail = largest_signup_at_retail_ceiling()
    at_provider = largest_signup_at_provider_ceiling()
    w(f"**The largest signup grant that keeps the worst case at the ${FOUNDING_CEILING_USD:,} ceiling:**")
    w("")
    w(f"- ceiling counted at **retail** (the doc's own framing): "
      f"({FOUNDING_CEILING_USD:,} x 100 - {doc['bonus']:,} - {doc['prizes']:,}) / {FOUNDING_MEMBERS} "
      f"= **{at_retail} credits per member** -- exactly the doc's number; "
      f"the offer is already sized to the ceiling, with no room above it.")
    w(f"- ceiling counted as **provider money** (${FOUNDING_CEILING_USD:,} of real invoices at the "
      f"real {pricing.MARKUP}x markup): ({FOUNDING_CEILING_USD:,} x {pricing.MARKUP} x 100 "
      f"- {doc['bonus']:,} - {doc['prizes']:,}) / {FOUNDING_MEMBERS} "
      f"= **{at_provider} credits per member**.")
    w("")
    w("Two things sit outside the credit arithmetic:")
    w("")
    w(f"- the trial's included model text, ${pricing.trial_thinking_usd():.2f} of Gemini per "
      f"account once (`PHANTRA_TRIAL_THINKING_USD`): real money, up to "
      f"${FOUNDING_MEMBERS * pricing.trial_thinking_usd():,.0f} across {FOUNDING_MEMBERS} members;")
    w(f"- a `promo` lot expires after `ledger.EXPIRY_MONTHS` = {ledger.EXPIRY_MONTHS} months "
      "(unspent credit costs nothing), so the worst case above assumes every credit is spent "
      "inside its window.")
    w("")
    w("Neither the share bonus nor the weekly prize exists in code today: both would be hand "
      "grants (`ledger.grant(..., kind='promo')`). Grant them as `promo`, not `adjustment`: an "
      "`adjustment` lot counts as beyond the trial (`ledger.BEYOND_TRIAL_KINDS`) and lifts the "
      "once-only cap on the trial's model text.")
    w("")
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", nargs="?", const="", metavar="PATH",
                        help="write the markdown (default docs/stats/cost-per-effect-<today>.md)")
    args = parser.parse_args(argv)
    text = render()
    if args.write is None:
        print(text)
        return 0
    path = Path(args.write or f"docs/stats/cost-per-effect-{date.today().isoformat()}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
