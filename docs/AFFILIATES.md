# Affiliate program — built 2026-10-26

Mike's call: "lets have this affiliate program up and ready by the morning", one
person, self-funded, so **no cash leaves the building until it is earned, held and
approved by hand**. The code is `src/affiliates.py` (rules, CLI), `app/affiliate_routes.py`
(three routes), `web/src/app/affiliates` (public page + apply form). Branch
`claude/affiliate-program`.

## The terms (Mike's numbers, in `src/affiliates.TIERS`)

| Tier | Earns | For | Reached at |
|---|---|---|---|
| Starter | 20% | first 3 months of a referral's payments | approval |
| Pro | 30% | first 6 months | 10 paying referrals *(build's assumption)* |
| Partner | 35% | first 12 months | 50 paying referrals |

- **Referred buyer:** 20% off their first *monthly* payment (a yearly plan already has 20% off).
- **Gating:** apply → Mike reads the channel → approves (`approve`). No link before approval.
- **Locked at first payment:** the tier is read when a referral first pays and stored on that
  referral. A partner who reaches Pro keeps Starter terms on people already referred.
- **Commission base:** what the customer paid, **before tax** (`invoice_net_cents`). Free
  invoices pay nothing; top-up packs never earn; only subscription invoices.
- **Yearly:** counted in months covered. A Starter partner's yearly referral earns 20% × 3/12
  of the payment, exactly what three monthly payments would have.
- **Hold:** 60 days from the payment (the refund window; also what absorbs chargebacks).
  A full refund inside the hold voids the commission, a partial one scales it. After the hold
  nothing is clawed back.
- **Payout:** **credits by default** — a `promo` lot on the partner's own account, 1 credit per
  cent, **12-month expiry** — because a credit costs about 42¢ on the dollar (pricing.MARKUP 2.4),
  so the top tier is ~14.6% of referred revenue in credits against 35% in cash. **Cash is a
  per-partner switch Mike flips** (`set-payout`), paid by hand in batches of $50 or more.
- **Attribution:** `?ref=<code>` link → `phantra_ref` cookie (60 days, domain `.phantra.ai`)
  → attributed at sign-up (`app/auth._provision`). Only a *new* account, only to an *approved*
  partner, first touch wins, never after the account has paid, never to yourself (same account
  *or* same person's other workspace).

## Assumptions to change if you disagree (each is one constant or line)

1. Pro unlocks at **10** paying referrals (`TIERS`). You only specified "at least 50" for Partner.
2. Credits are the default payout; cash is opt-in per partner.
3. 60-day hold (`HOLD_DAYS`), 60-day cookie (`COOKIE_DAYS`), $50 cash minimum (`MIN_CASH_PAYOUT_CENTS`).
4. Buyer discount is monthly plans' first payment only.
5. "Paying referrals" = referrals with a booked, not-voided commission.

## Launch checklist (the only things that need you)

1. **Stripe, once:** Dashboard → Product catalog → Coupons → new coupon, **20% off, duration "once"**.
   Copy its id.
2. **Env:** on Fly set `STRIPE_AFFILIATE_COUPON=<that id>` (unset = referred buyers simply get no
   discount; nothing breaks). Optional `AFFILIATE_LINK_BASE` (defaults to `https://phantra.ai`).
3. **Deploy** the branch (the three tables are created on boot; `db.OWNED_TABLES` lists them).
4. **Review desk** (export `DATABASE_URL` first — the CLI never loads `.env`):

   ```
   python -m src.affiliates report                 # applications waiting + every partner's numbers
   python -m src.affiliates approve <slug> [--code mycode]
   python -m src.affiliates reject <slug> --note "…"
   python -m src.affiliates suspend <slug>
   python -m src.affiliates set-payout <slug> cash # only after you trust them
   python -m src.affiliates release                # pays every commission whose hold ended
   python -m src.affiliates payouts                # cash owed (>= $50) — send it yourself
   python -m src.affiliates mark-paid <slug> <transfer-reference>
   python -m src.affiliates export                 # regenerate web/src/content/affiliate.json
   ```
5. **`release` daily** — like `python -m src.billing release`. Until it runs, held commissions
   just wait; running it late costs nothing.
6. The public page `/affiliates` is linked from the footer and the sitemap.

## What it can and cannot do (be honest about it)

- It never moves cash. The cash path is "Mike runs `payouts`, sends PayPal/bank, runs `mark-paid`."
- Referral clicks are not counted (only sign-ups and payments), so there is no click-through
  number. Add it only if a partner asks.
- The webhook hook is wrapped: if this module throws, the customer's credit still lands and the
  failure is logged (`[billing] affiliate commission FAILED …`).
- A refund event without an `invoice` field voids/scales the partner's *newest held* commission
  for that referral. Stripe's `charge.refunded` normally carries the invoice id.
- Dispute (chargeback) events are not handled separately; the hold is the protection.

## Tests

`tests/test_affiliates.py` (22), the tenancy audit in `tests/test_tenancy.py` (three owned
tables, four reasoned allowlist entries), `web/tests/affiliate.test.mjs`. A Python test fails if
`web/src/content/affiliate.json` disagrees with `public_terms()`.
