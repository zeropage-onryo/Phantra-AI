# The Agency plan, and the Ad Studio on every plan

2026-11-03. Mike asked whether the Ad Studio was an agency tier and what competitors do, then
"ok lets do that" to: drop the Ad Studio add-on, and sell an agency tier as seats, a project and
brand kit per client, and one shared credit pool.

## Why

Nobody sells ad tools as a paid gate. Higgsfield (Marketing Studio) and Runway include them in
normal plans and charge teams per seat (Higgsfield Teams $49/seat/mo yearly; Runway Team $55/seat/mo
yearly, 2-9 seats, one shared pool). Ad-only tools charge more for the whole product: Creatify
Business $195/mo for 10 seats and 10 brand spaces on a shared pool; Arcads $110 / $220. What agencies
pay for is seats, client separation and a pool. (Figures from third-party pages, many written by
Creatify; re-check the vendors' own pages before changing a price.)

## Mike's answers (2026-11-03)

- Agency: **$199 a month, 19,900 credits** (the plans' own 1c a credit), yearly $1,910.
- **5 seats.**
- **Solo below Agency**: Standard, Pro and Max keep one person.
- **Clients are a project + brand kit each**, inside one workspace and one credit pool (no
  workspace per client, no cross-workspace billing).

## As built

- `pricing.Plan` gains `seats` (default 1) and `yearly_usd_set` ($199 x 12 x 0.8 = $1,910.40 is not
  whole dollars). `PLANS["agency"]`: `STRIPE_PRICE_AGENCY` / `_YEAR`, 400 GB (ceiling 424),
  `BRAIN_USD` 8. Max's blurb no longer says "agencies". `public_catalog` plans carry `seats`.
- Billing: `balance` carries `buyable` / `buyable_yearly` per plan, and `checkout_configured` is
  "any plan can be bought", so an unset Agency Price no longer switches checkout off for the
  others. Settings shows an unpriced plan as "Not on sale yet".
- **Ad Studio included**: `prompts/studios/ads.json` names no add-on, so `studios.for_account`
  passes every pick and the page reads `entitled` / not `gated`. The add-on machinery
  (`src/addons.py`, `pricing.ADDONS`, the Stripe routing) stays for a future studio that names one.
- **Seats**: `accounts.seats_for`, `add_teammate` (an advisory lock per workspace so two invites
  cannot both take the last seat; a new address gets an unclaimed `users` row that its first sign-in
  claims, as `invite` always did), `remove_teammate` (never an owner). Routes:
  `POST /api/account/members {email}` (owner only; 402 `no_seats` below Agency, 409 `seats_full` /
  `already_member`, 400 `bad_email`), `DELETE /api/account/members/{user_id}` (owner only).
  `GET /api/account/members` adds `seats`, `used`, `can_invite`, and each member's `id` for an owner.
  Settings -> Workspace has the invite field and Remove. Nothing is emailed.
- **The tenant is the OPEN workspace** (`auth.current_account_id`, `_open_of`): the cookie's
  workspace when it names one of the person's memberships, else the oldest. Before, it was always
  the oldest, from the brand rows of 2026-09-02 (gone 2026-10-15); with seats, a teammate who
  already had a workspace would otherwise have rendered on their own credits after switching.
  Nobody who never switched sees anything move. `current_account` falls back to the oldest too
  (it was slug order), so the shell and the data agree.

## Mike's steps before it sells

1. `venv/bin/python -m ops.stripe_setup --live --fly` creates the Agency Product and its two
   Prices ($199/month, $1,910/year, read off `pricing.PLANS`), reuses the other seven and the
   webhook, and pushes `STRIPE_PRICE_AGENCY` / `_YEAR` to Fly. Until then Agency shows
   "Not on sale yet" and the other plans keep selling.
3. Check the live database for anybody who belongs to more than one workspace and has switched
   (the `phantra_account` cookie): after deploy their open workspace is where their work goes.

## Known gaps

- The connectors (`app/mcp_auth.py`, `app/oauth_consent.py`) still act on the OLDEST membership
  (no cookie there). A teammate with their own older workspace uses the connector on that one;
  the Connect to Claude panel reads that same account (`auth.oldest_account_id`).
- Seats are not taken back when a plan lapses: members stay, and nobody new can be invited.
- No email goes out with an invite; the owner tells the person to sign in with that address.
