# Free-credit abuse check, 2026-10-22

Read-only, from the code on `main` at `1d7b7990` (group 7 of
`docs/tasks/task-overnight-2026-10-22.md`). Nothing was signed up, nothing was
run against Supabase or the live database. Where a guard lives in the Supabase
dashboard rather than in the repo, it is marked **unverified**: this session
cannot read the dashboard.

## The short answer

**One person can farm as many 100-credit trials as they have email addresses
or Discord accounts, at about five a minute per IP address, and the IP brake
can be rotated by a forged header.** The grant is per NEW WORKSPACE, one
workspace per Supabase user, one Supabase user per email; nothing ties two
sign-ups to the same person, device, card or phone. At the default grant that
is $1.00 of credits and up to $1.00 of Gemini text per throwaway identity; at
the Founding 500's 300 credits it is $3.00 of credits (about $1.25 of provider
money if every credit is spent) plus the same $1.00 of text.

A bounded, honest estimate of the farm rate today: 5 sign-ups a minute per IP
through `/auth/signup` or `/auth/email` (`RATE_LIMITS`), unbounded across IPs,
and the IP key is the first `X-Forwarded-For` entry, which the client controls
(see guard 2). Each sign-up needs a mailbox that receives a code when Supabase
confirmation is on (**unverified**, believed on: the code templates were
applied 2026-10-05), so the practical limit is mailboxes. Gmail plus-addressing
(`name+1@gmail.com`, `name+2@...`) gives one mailbox unlimited distinct
addresses, and the code normalises nothing but case and whitespace
(`app/auth.py:735`, `_valid_email`).

## How a sign-up turns into credits

| step | where | what it checks |
|---|---|---|
| a Supabase identity is made | `app/auth.py:793` (`/auth/signup`, email+password), `:740` (`/auth/email`, a one-time code with `create_user: True`), `:1140` (`_oauth_login`: Google, Discord, Apple) | a syntactically plausible email (`:735`), a password of 8+ (`MIN_PASSWORD_LEN`), the per-IP brake (`:510`) |
| the identity is claimed as a `users` row | `src/accounts.py:217` (`claim`) | an email must be present; an email already claimed by a different UUID is refused |
| a person with NO membership gets a workspace | `src/accounts.py:782` (`provision_personal`), called from `app/auth.py:682` (`_provision`) | `open_signup()` (`src/accounts.py:751`, on unless `PHANTRA_OPEN_SIGNUP=0`); one workspace per user id under an advisory lock |
| the workspace gets the trial | `src/accounts.py:852` (`grant_signup_credits`), `signup_credits()` at `:840`, default `DEFAULT_SIGNUP_CREDITS = 100` at `:837` | once per ACCOUNT: `ledger.grant(..., kind="promo", source_ref=f"signup:{account_id}")`, idempotent on the ref (`src/ledger.py:771`) |
| the trial may also think | `src/charge.py:305` (`create_refusal_code`), `src/pricing.py:143` (`TRIAL_THINKING_USD = 1.00`) | $1.00 of Gemini text ONCE per account that has never held non-trial credit (`ledger.beyond_trial`, `src/ledger.py:553`) |

So the unit of the grant is the account, the unit of an account is the
Supabase user, and the unit of a Supabase user is an email address (or an OAuth
identity). **Trial credits are per account, not per person**, and there is no
notion of "person" above the user id anywhere in `src/accounts.py`.

## The guards that exist

1. **One grant per workspace, by ledger ref.** `src/accounts.py:852-864` grants
   with `source_ref="signup:<account_id>"`; `src/ledger.py:771-806` reads for
   that ref inside the account's advisory lock and returns the existing lot. A
   retried sign-in, a double tab, a replayed callback cannot grant twice to one
   workspace. `tests/test_ledger.py::test_a_webhook_delivered_twice_grants_once`
   and the new `tests/test_ledger_safety.py` cover the mechanism.
2. **One workspace per user id.** `src/accounts.py:782-831` takes
   `pg_advisory_xact_lock(hashtext('zp-provision:' || user_id))`, then refuses
   when the user already has ANY membership. An invited member never gets a
   second studio; a user cannot re-provision by signing in again.
3. **A per-IP sliding-window brake on every sign-in door.** `app/auth.py:499-521`:
   `signup` 5/min, `otp` 5/min, `verify` 10/min, `login` 10/min, keyed on
   `request.client.host`. It is in-process memory (`_hits`), so it resets on
   every deploy and is per Fly machine, and -- the real gap -- the client host
   behind Fly's proxy comes from `X-Forwarded-For` with
   `--forwarded-allow-ips='*'` (`ops/fly/supervisord.conf:18`), which in uvicorn
   0.52 (`uvicorn/middleware/proxy_headers.py`, `always_trust` -> the FIRST
   listed host) is whatever the client put in the header before Fly appended
   its own entry. A script that sends `X-Forwarded-For: <random>` gets a fresh
   bucket per request.
4. **The trial's model text is capped once, not per day.** `src/charge.py:305-363`
   refuses 402 `trial_thinking_used` after $1.00 of metered Gemini
   (`spend.thinking_spent`). This bounds what a throwaway account can burn on
   the brain to $1.00, but a new account is a new $1.00.
5. **Every spend takes a hold before the provider call** (`src/charge.py`,
   `src/ledger.py:853`), so a trial can never spend past its 100 credits; and
   the per-account daily output cap (`src/fal.py:107`, `FAL_DAILY_CAP` = 200
   stills/effects a day, `GLOBAL_DAILY_CAP` at `:117` = 0, i.e. OFF) is a
   runaway guard, not an abuse guard.
6. **Credits are not transferable.** There is no route that moves credit between
   accounts, no referral grant, no "gift"; a farmed trial can only be spent in
   its own workspace. Outputs, though, are downloadable (`/api/media` download
   URLs), so the farmed value is the renders themselves.
7. **The connector grants nothing.** `/mcp`, `/mcp/claude` and the stdio server
   spend an existing workspace's credits and never create one
   (`app/mcp_auth.py`, `src/mcp_server.py`: no `provision_personal` call); the
   OAuth consent page (`app/oauth_consent.py:30`) DOES run `_provision` for a
   first-time sign-in, so a connector install is also a sign-up door, with the
   same trial.
8. **`PHANTRA_OPEN_SIGNUP=0` closes every door** (`src/accounts.py:751`): a
   fresh sign-in gets a mirror row and no workspace, so no grant. This is the
   one switch that stops a farm cold, at the price of stopping sign-ups.
9. **Supabase-side (unverified from here):** email confirmation on (a code must
   be typed, so a mailbox is needed per identity); Supabase's own OTP and
   sign-up rate limits; `rate_limit_email_sent` per hour on the SMTP sender
   (`ops/supabase_auth_email.py:153` reports it; the apply example sets 100).
   Supabase also offers CAPTCHA (hCaptcha / Turnstile) on sign-up -- nothing in
   `app/auth.py` sends a captcha token, so it is **off** unless the dashboard
   enforces it, and if the dashboard enforced it every sign-up here would fail.

## The guards that are missing

| gap | why it matters | one-line recommendation |
|---|---|---|
| No email normalisation | `a+1@gmail.com` ... `a+999@gmail.com` and `a.b@gmail.com` are one inbox and 1,000 trials | Normalise before `claim` and before the grant: lower-case, strip `+tag`, and for gmail.com/googlemail.com drop dots; grant once per normalised address (a `signup_emails` table, or a unique index on a normalised column). |
| No disposable-domain block | mailinator, guerrillamail, temp-mail and co. give unlimited confirmed mailboxes for free | Refuse sign-up (or grant 0 trial credits) for a maintained disposable-domain list; keep the list in `data/` and the check in `app/auth.py:_valid_email`. |
| The IP brake trusts a client header | guard 3: `--forwarded-allow-ips='*'` + Fly appending means the limiter keys on a client-chosen value | Key `_rate_limited` on `Fly-Client-IP` (Fly sets it and it cannot be forged through the proxy), or set `--forwarded-allow-ips` to Fly's proxy ranges; make the brake per-process-wide or Postgres-backed so a deploy does not reset it. |
| No per-IP / per-day sign-up count | the brake is per MINUTE; 5/min is 7,200 trials a day from one address, and the brake forgets on deploy | A persisted count of workspaces provisioned per client IP per 24 h (a column on `accounts` or a small table), refusing or granting 0 past N (say 3). |
| No device or browser signal | one laptop can sign up a hundred Discord accounts | Cheapest honest option: a first-party cookie set at the first sign-up and read at provisioning; a workspace that arrives with one already set gets 0 trial credits (same person, not a new person). Fingerprinting proper is a product and a privacy call for Mike. |
| OAuth identities are free | Discord accounts cost nothing and need no phone; Google and Apple are harder but not hard | Treat OAuth like email: normalise the provider email, apply the same per-address grant guard; consider granting the trial only after email confirmation for Discord (Discord emails CAN be unverified -- `claim` refuses a missing email, `src/accounts.py:258`, but not an unverified one). |
| No phone or card step for the trial | every other guard is a speed bump; a phone number or a $0 card hold is the one that makes a farm cost money | Keep the trial card-free (Mike's InVideo shape) but gate the SECOND half of it: e.g. 50 credits at sign-up, 50 more after a phone number or a connected Instagram/Discord that is older than N days. |
| The trial text cap is per account | $1.00 of Gemini per throwaway is real money the credits never see | Lower `PHANTRA_TRIAL_THINKING_USD` for accounts whose email domain or IP has signed up before; or make the first Create free and the rest wait on a render (one spend proves a person). |
| Outputs leave the trial freely | a farmed trial's value is 100 credits of downloadable renders | PR #233 (free-tier watermark, OPEN) is the answer: watermark trial renders and un-mark on the first payment; it makes a farmed render worth less without touching sign-up. |
| Share bonuses and prizes are not built | the Founding 500 doc gives up to 300 credits/member/month for sharing and 2,500-credit prizes; today those would be hand grants with no fraud check at all | When they are built: grant on a VERIFIED share (a link with a signed token that was actually opened N times from N distinct `Fly-Client-IP`s), cap per account per month in code, and grant as `promo` (not `adjustment`, which lifts the thinking cap). |
| No alerting | nobody is told when 50 workspaces appear in an hour | A line on the dev console (`/costs` already reads `llm_calls`) or a daily stderr count of `promo` lots granted, with the IP and domain histogram. |

## What to do first (cheapest to most)

1. Key the brake on `Fly-Client-IP` and persist a per-IP, per-day provisioning
   count (two small changes in `app/auth.py`, one column). Closes the forged
   header and the 7,200-a-day arithmetic.
2. Normalise emails (plus-tags, gmail dots) before the grant, and block a
   disposable-domain list. Closes the one-inbox-many-trials path.
3. Merge or adopt PR #233's watermark for trial renders. Makes the prize of a
   farm smaller.
4. For the Founding 500 specifically: grant the 300 credits as 100 at sign-up
   and 200 on the first thing a person does that a bot does not (a photo
   uploaded as an element, an Instagram or Discord connected). Same retail
   ceiling, a quarter of the farmable value.

Every one of these is a product call and is listed here for Mike; none was
built overnight.
