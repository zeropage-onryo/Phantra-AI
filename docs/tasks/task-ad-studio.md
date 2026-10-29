# Task: the Ad Studio

Mike, 2026-10-26: "can you also give it its own UI and title 'Ad Studio' in the Phantra studio.
Combine what we already have and build this." Decided the same night: Phantra gets three studios
(Ad, Film, Fashion), Ad first; studios are a **priced tier**, shaped as a **flat add-on** on any
plan. Spec: the project doc `claude/ads_studio_spec_2026-10-26.md`.

## What it is

A studio is **not a second app**. It is a config over the one engine:

- `prompts/studios/ads.json`: the formats (product showcase, UGC review, unboxing, TV spot,
  motion ad, product still, social cut-down), each riding on a skill that already existed
  (`ad`, `ugc`, `motion-ad`, `product-still`, `social-cutdown`), with its shapes, its length
  window, what it needs (a product, a kit, a clip) and a prompt note; and a four-question
  intake (platform, audience, offer, tone).
- `prompts/studios/ads_turn.txt`: what a brain turn is told while the conversation follows the
  brief.
- `src/studios.py`: the loader (never raises), `clean_pick` (the one cleaner of a pick),
  `for_account` (the pick only for a workspace with the add-on), `turn_note`, `public` (the
  page's JSON, without the prompt notes) and `problems` (the config's own test).

## The page: `/studio/ads`

`web/src/app/studio/ads/page.tsx` -> `components/studio/ads/ad-studio.tsx` (+ `ad-studio.css`,
prefix `as-`), logic in `lib/ad-studio.ts` (pure, `web/tests/ad-studio.test.mjs`).

Four steps and a card: **Format**, **Product** (the account's prop elements; "Add a product"
goes to Elements), **Brief** (the intake, the shape and the length), **Brand kit** (the
account's kits, plus the Brand page's website reader inline). The card shows the frame at the
chosen shape, the sentence Vesper will be handed, and the one action.

**Start in Create** is a LINK (`handoffHref`): `/studio?spark=<the sentence>&kind=&frame=&skill=
&seconds=&studio=<pick JSON>&kit=&attach=<product>`. The composer already read spark, kind,
frame, kit and attach; it now also reads `studio` (onto the conversation's draft), `skill` (the
format's recipe picked for the first send) and `seconds` (the length, if the slider allows it).
Nothing is sent until the person presses Send, and every still and clip still waits on its
priced card.

In Create the settings line carries an **"Ad Studio · <format>"** chip (a link back to the
studio, and an x that stops following the brief). The pick lives on the draft
(`ComposerDraft.studio`, `assistant_store._clean_draft`), survives a written scene like the kit
does, and New session clears it. Every guide turn sends it as the `studio` form field;
`POST /api/creative-guide` cleans it and passes it to `creative_guide.respond` /
`respond_personal` only for a workspace with the add-on (otherwise the turn is the plain
composer's, never a refusal). The job result names the pick it ran with (`studio`).

Entries: the rail (Megaphone, after Video), the phone menu, the palette ("Ad Studio").

## The add-on

- `src/addons.py`, OWNED table `account_addons` (one row per account and add-on; `ensure(dsn)`;
  init in the lifespan and `test_tenancy._init_everything`). `active()` is the one reader and
  never raises. `PHANTRA_STUDIOS_GATE=0` opens the studios to everyone.
- `pricing.ADDONS["studios"]` (`Addon`: no credits, not a `Plan`, never `accounts.plan`),
  `STRIPE_PRICE_STUDIOS`, monthly only. `monthly_usd` is **None** until Mike sets the price, so
  no page shows a made-up number.
- Checkout (`billing.checkout_url`): an add-on needs a plan (`plan_required`, like a top-up),
  is a `subscription`, refuses a yearly interval and a second purchase, and comes back to
  `/studio/ads?checkout=success`.
- **The webhook bug this closes.** Before, a second subscription's `customer.subscription.deleted`
  fell into the plan's lapse: it expired the plan's credits, cancelled its schedule and cleared
  `accounts.plan`. Now `billing._addon_of` reads the event's Price (then the checkout's metadata)
  and `_handle_addon` keeps the add-on's row current and returns before any plan branch. A
  payment-mode checkout naming an add-on grants nothing.
- `GET /api/billing/balance` carries `addons: {"studios": bool}` (the row's own status).
- By hand: `python -m src.accounts studios <slug> --on|--off` (reports the before; refuses to
  turn off a Stripe-paid add-on -- cancel it in Stripe).

## Routes

- `GET /api/studios/{id}`: the page (open to every account; 404 for an unknown studio).
- `POST /api/creative-guide`: new optional `studio` field.
- `POST /api/billing/checkout {"item": "studios"}`.

## Fixed on the way

- The composer's kit (`?kit=`) and the new studio pick waited on a REF for the spark; with
  `?attach=` holding the spark back past their last run they never applied. They now also
  depend on `sparkApplied` (state).
- A hand-off (`?spark=&kind=`) cleared the draft AFTER `?attach=` had added its photos, so a
  link's own attachment was dropped. The hand-off's clean draft now keeps the link's photos.

## Verified

- `tests/test_studios.py` (25): the config, the pick, the gate, the page, the turn, the webhook
  routing (including "cancelling the add-on never touches the plan"), checkout, balance, CLI.
- `web/tests/ad-studio.test.mjs` (10), `npm run typecheck`, `npm run build`.
- Clicked through on a local API + `next start`: the locked page (Preview, "Ad Studio opens
  soon"), the granted page, Start in Create landing with the sentence in the box, the UGC
  skill chip, the product photo attached, 9:16 and 15s set, Kit: Halo, and the
  "Ad Studio · UGC review" chip; the saved draft carried the pick. Phone width has no
  horizontal scroll.

## Open (Mike)

- The add-on's price, and one price for all three studios or one each.
- Create the Stripe Price and set `STRIPE_PRICE_STUDIOS`; until then grant by hand.
- Next in the spec: `schedule_post` / `what_worked` for Vesper, ad QC on the card. Variants as
  one plan and ad results were built 2026-10-29 (`docs/tasks/task-ad-results.md`). Film and Fashion wait on usage.
