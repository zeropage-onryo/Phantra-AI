# Task: competitive Seedance and Veo prices, and monthly plan credit (2026-11-02)

Mike, 2026-11-02: make "the costs of seedance and veo more competitive", and "change credits to
expiring monthly". The evidence (competitor prices read that day, wholesale rates, the margin
model) is in the project doc **Phantra Pricing vs Competitors — Cost-Cutting Plan** (Claude
Docs). This is Phase 1 of that plan: pricing only, still on fal. **Nothing here is live until
Mike merges and deploys.**

## What a clip costs (credits; 1 credit = 1¢ on a monthly plan)

| Model | Clip | v4 (2026-10-27) | v5 (this) | Markup | Competitors $/s (2026-11-02) |
|---|---|---|---|---|---|
| Seedance 2.5, 720p | 5s | 355 | **332** | 1.5x -> 1.4x | Higgsfield ~$0.34, Pika $0.27, Dreamina $0.35 |
| Seedance 2.0, 720p | 5s | 228 | **213** | 1.5x -> 1.4x | $0.16-0.29 |
| Seedance 2.0 Fast, 720p | 5s | 182 | **170** | 1.5x -> 1.4x | ~$0.17 |
| Veo 3.1, 720p, audio | 6s | 360 | **276** | 1.5x -> 1.15x | Higgsfield ~$0.39 |
| Veo 3.1 Fast, 720p, audio | 6s | (new) | **135** | 1.5x | Higgsfield ~$0.16, Krea ~$0.10 |
| LTX 2.3, 1080p | 6s | 116 | **96** | 2.4x -> 2.0x | not on Higgsfield |
| LTX 2.5 Fast / Pro, 720p | 6s | 130 / 173 | **108 / 144** | 2.4x -> 2.0x | |
| Kling, Wan, Grok | | unchanged | unchanged | 1.5x / 1.64x / 1.73x | |

Seedance on fal is still about 2x Higgsfield: fal charges exactly twice ByteDance's own per-token
price (fal $21.40 / BytePlus $10.70 per million tokens for 2.5). Closing that gap is Phase 2, a
second host (BytePlus ModelArk or Replicate, same price), gated on the real-person check BytePlus
runs on reference photos (see `task-video-markup.md`, Open). At 1.4x on BytePlus, Seedance 2.5 at
720p would be about 162 credits, just under Higgsfield's monthly price.

## As built

- `pricing.MARKUP_BY_MODEL`: Seedance 1.4, Veo 3.1 1.15, Veo 3.1 Fast 1.5, LTX (all three) 2.0;
  Kling, Wan, Grok unchanged. `MIN_MARKUP` 1.5 -> 1.15 (Mike's call): a yearly subscriber who
  spends every credit on Seedance and Veo is now about break-even; the margin is carried by the
  cheaper models, credit that expires unspent, and plan revenue.
- `PRICING_VERSION` `2026-11-02-fal-v5`; v4 retired, so every open card re-quotes once
  (`retired_pricing`), as at v4.
- **Veo 3.1 Fast** (`veo3.1-fast`): a `fal.VIDEO_MODELS` row read off both endpoints' queue
  schemas and fal's pricing API on 2026-11-02 (`fal-ai/veo3.1/fast`, `.../image-to-video`; same
  inputs as Veo 3.1; $0.15/s with audio at 720p and 1080p, 4k left out). Also in `T2V_ASPECTS`,
  `PROMPT_MAX`, `providers.BANDS` (standard, 8s max), `pricing.CATALOG_MODELS`,
  `prompts/model_picks.txt` (the cheap first pass of a Veo clip) and `prompts/models/README.md`.
  Not added to `whats_new` (an announcement is Mike's call).
- **Plan credit lives one month.** `ledger.EXPIRY_MONTHS_BY_KIND = {"subscription": 1}` and
  `ledger.expiry_months(kind)`; `grant()` defaults to it. Top-ups (`purchase`), the trial and
  promos keep `EXPIRY_MONTHS = 2` on purpose: expiring cash-bought credit is LAPSE_POLICY's
  question (chargebacks, gift-card law), not this change. Lots already granted keep their
  `expires_at`. The yearly schedule needs nothing else: each month is already its own lot.
- `public_catalog()` now carries `expiry_months` (plan credit: 1), `topup_expiry_months` and
  `trial_expiry_months` (2); the plan cards, Settings -> Plan, /pricing, /faq and /terms say
  "a month" / "2 months" through `monthsLabel` (`web/src/lib/catalog.ts`).
- Fal's live pricing API was re-read 2026-11-02 for every video endpoint: no rate moved since
  2026-10-27, so the rate card is unchanged.

## Watch after it ships

- **A renewal gap.** A monthly lot now expires about when the next invoice lands. If Stripe's
  `invoice.paid` arrives after the old lot's `expires_at`, the account has no plan credit for
  that window (minutes to an hour; days if a card retry runs). Nothing refuses wrongly (the
  balance is just the balance), but a short grace on subscription lots is the fix if it shows.
- **A yearly month released late lands already expired** if it is more than a month late (the
  lazy release before every hold makes that rare for anyone who renders). That is the rule
  working: the month would have expired unused anyway.
- Tell current subscribers about the change before it ships; Runway, DomoAI and Invideo already
  reset monthly.
