# Task: a markup per video model (2026-10-27)

Mike, 2026-10-26: "for video models it's way too expensive at the current rates", wanting
them "at least somewhat competitive" with Higgsfield. The evidence and the margin model are
in `Claude outputs/Phantra_video_pricing_2026-10-27.xlsx` (Mike's checkout) and the project doc
`claude/video_pricing_decision_2026-10-27.md`. **Nothing here is live until Mike merges and
deploys.**

## What a 5s clip cost, against Higgsfield (2026-10-27)

Higgsfield's prices were read off its Generate button in Mike's Chrome. They agree with his
Higgsfield transaction log (Seedance 2.5 at 720p: 35 credits for 5s, 105 for 15s). Higgsfield
credits are valued at $0.039 each (Plus annual, $39 for 1,000).

| Model | Before (credits) | Now (credits) | Before vs Higgsfield | Now vs Higgsfield |
|---|---|---|---|---|
| Seedance 2.5, 720p | 568 | 355 | 4.2x | 2.6x |
| Seedance 2.0 Fast, 720p | 291 | 182 | (not on Higgsfield's web) | |
| Seedance 2.0, 720p | 365 | 228 | 3.1x | 1.9x |
| Kling 3 Turbo Pro | 168 | 105 | 4.3x | 2.7x |
| Kling 4.0, 720p | 189 | 118 | 3.5x | 2.2x (list price) |
| Veo 3.1, 720p, 6s | 576 | 360 | 2.5x | 1.5x |
| Wan 3.0, 720p | 120 | 75 | 2.4x | 1.5x |
| Grok 1.5, 720p | 168 | 115 | 1.9x | 1.3x |
| Grok 1.5 Lite, 720p | 36 | 26 | 1.85x | 1.3x |
| LTX 2.3, 1080p, 6s | 116 | 116 | not on Higgsfield | unchanged |

The rule each number came from: at most 1.3x Higgsfield's list price, never under
`MIN_MARKUP` (1.5x) over fal's rate card, never over `MARKUP` (2.4x). On fal alone, Seedance and
Kling cannot get closer than this without going under 1.5x. A cheaper host is the next step (see
Open, below).

## As built

- `pricing.MARKUP_BY_MODEL` gives each video model its own markup, as a string read through
  `Fraction`, like `MARKUP`. `pricing.markup_for(model)` falls back to `MARKUP` for any model
  not in the table. `MIN_MARKUP = "1.5"` is the floor.
- `pricing.credits_for(micros, model=None)` and `ledger.charge_credits(usd, model=None)` take
  the model. With no model the price is `MARKUP`, so stills, effects, sheets, talking photos and
  every other caller are unchanged.
- **The card and the hold are still one number.** Every door that prices a clip now passes its
  model:
  - `pricing.quote`, `pricing.display` (through the scene's parts) and `pricing.catalog_models`
    (so the site, `pricing.json` and `/models`)
  - `pricing.studio_quote` and `mcp_server.approval_gate` (for `generate_video`), plus
    `video_models` and `recommend_model` on the connector
  - `direct.py` (the Video page), and `app/api.py`'s renderer pick
  - `charge.Charge(model=)` at the four video `Charge` sites in `fal.py`, so a hold with no
    quote (the graph, the CLI) holds the model's price
  - the reaper (`ledger.reap`), which reads the model off the `generations` row it settles
- `PRICING_VERSION` is `2026-10-27-fal-v4`, and v3 is retired. Every open card re-quotes once
  (`retired_pricing`), as at v3.
- `public_catalog()` adds `markup_by_model`, and `web/src/lib/catalog.ts` types it.
  `pricing.json` was regenerated with `python -m src.pricing export`.
- Tests: `tests/test_pricing.py` covers the table (real models, floor to cap), "no model means
  MARKUP", and an unquoted `Charge` holding its model's price. `tests/test_ledger.py` covers the
  reaper at a model's markup. Pins that were 2.4x video prices now read the new numbers.

## Not changed, on purpose

- **The rate card.** `main` had already moved LTX 2.3 to $0.08 and Seedance 2.0 at 480p to the
  token price. Seedance 2.5 at 1080p ($1.164 on fal's page against about $1.04 from the token
  price) was left alone: fal's own rate card is the higher number, and a quote under the
  invoice is the worse error.
- **Storage quotas.** `storage_ceiling_gb` is still sized at `MARKUP`. At 1.5x, a yearly
  subscriber who spends every credit on video leaves room for about 4 / 12 / 42 GB under its
  10% rule, against the 25 / 70 / 200 GB the plans give. The money is at most about $1 a month
  a user at R2's price, so the quotas stay. That's Mike's call.
- **`ops/cost_table.py`** still reports at `MARKUP`. It's a report, not a price.

## Open

- **A cheaper host for Seedance**, BytePlus ModelArk, which is about half of fal's per-token
  price. BytePlus refuses realistic faces in references unless the person passes a liveness
  check, so the router would send shots with a `subject` reference to fal and the rest to
  BytePlus. Phantra needs its own prompt and image screening before any second host
  (`claude/screening_and_host_routing_spec_2026-10-27.md` in the project). At the same 1.5x
  floor, Seedance 2.5 at 720p would be about 179 credits, about 1.3x Higgsfield. (The workbook's
fal-only figure was 347, from fal's per-token price; the shipped table prices off fal's
published rate card, $0.473/s, so it reads 355.)
- **fal invoices.** Checking that real cost matches the rate card needs a fal key with
  `billing:usage:read`; the current key was refused.
