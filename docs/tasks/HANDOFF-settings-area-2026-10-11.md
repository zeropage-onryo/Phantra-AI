# Handoff — the settings area: what is left after PR #227

**From:** a Claude Code session, 2026-10-11. **For:** the next Claude Code session, in this repo on Mike's Mac.
**Read first:** `docs/tasks/task-settings-page.md` (the task, with an "As built" note under each of tasks 1 to 8) and CLAUDE.md, "Settings is an area of six sections".
**Mike's standing rule:** one item, one branch, one PR; stop and report after each; merge only on his word.

## State right now

- Tasks 1 to 8 are DONE and merged: PR #227, merge commit `d7cec3c` (2026-10-11). Task 9 (the optional items) is NOT started.
- `/studio/settings` is six sections, each its own URL: `account`, `plan`, `usage`, `workspace`, `connections`, `preferences`. Two routes are new: `GET /api/billing/history` (`src/credit_history.py`) and `GET /api/account/members` (`app/api.py`). `POST /brand/<slug>` now accepts any workspace the signed-in person belongs to.
- Deployed. When this was written `main` was `a92d31b`, its Fly Deploy had succeeded and Vercel had finished `d7cec3c`. Asked without a session: `/studio/settings` answers 307 to `/studio/settings/account`, `/studio/settings/plan` 200, both new API routes 401 (a route that was not deployed would be 404), `/mcp/` 401.
- **Nobody has looked at the live pages signed in.** That is item 1.
- Nothing is uncommitted. The branch `claude/task-settings-page-d96450` is deleted on the remote. This file is on `claude/settings-area-handoff`.
- Other sessions are merging into `main` the same day (the studio agent, the "no idea board" work). One has already changed a sentence in `settings/plan.tsx`. `shell.tsx`, `app/studio/page.tsx` and `lib/studio-api.ts` are busy files: fetch and read `git log HEAD..origin/main` before branching and before pushing.

### Kept outside git, on Mike's Mac only

`data/_scratch_settings/` in the MAIN checkout (git-ignored, beside `_scratch_mascot`):

- `dev_api.py`, `dev_seed.py`: a throwaway API for checking settings in a browser (below).
- `shots.mjs`: twelve full-page screenshots from a headless Chrome.
- `screenshots/`: the twelve taken on 2026-10-11 (six sections at 1440 and at 390, seeded data).

The screenshots are not in the repo and not on PR #227. `.gitignore` keeps `*.jpg`, `*.png` and `*.mp4` under `docs/reference-look/` out of git, and `git add <folder>` skips ignored files without a word: commit `0f51576` is titled "with screenshots" and carries none.

### Traps

- `tests/conftest.py` overrides `auth.current_account_id` to `None` for every test. A test that is about WHO the caller is must pop it first (`app.dependency_overrides.pop(auth.current_account_id, None)`), as `tests/test_account_members.py` does.
- `GET /api/model-connections` starts the real Codex and Claude Code programs when they are installed. They are on this Mac. Stub `src.personal_models` before loading Connections locally (`dev_api.py` does).
- A dollar may appear in settings in exactly one way: a plan's price, in `settings/plan.tsx`, through `lib/catalog`'s `usd()`. `tests/test_studio_shows_credits.py` fails on anything else in the settings folders, including a typed `$10`.
- The ledger writes one entry per LOT for a hold or a give-back. Anything shown to a customer groups by (kind, ref), as `credit_history.movements` does.
- The palette's hairlines (`--edge*`) are about 1.2:1 against a card: right for a divider, too faint for a field. Fields in settings use `--zset-field-edge` (3.3:1).

## What was verified

- `pytest tests/ -q` on the merged tree: 3674 passed, 8 xfailed. `ruff check .` clean. Web: `npm run lint` 0 errors, `npm run typecheck`, `npm run build` (seven settings routes), 150 node tests.
- New tests: `tests/test_credit_history.py` (18), `tests/test_account_members.py` (10), two more in `tests/test_studio_shows_credits.py`; node: `settings-sections`, `credits`, `credit-history`, `preferences`, and one more case in `legacy-routes`.
- Every section walked in a browser against the throwaway API, at 1440 and 390: first password with an emailed code, change with the current password, an email change, each refused without its proof; four billing states (monthly plan, trial only, operator, yearly) with and without Stripe; plan choice and top-up reaching checkout, an existing plan reaching the portal; the history's chart, filters and Load more; the workspace switch both ways; a ChatGPT sign-in to connected and back; the connector on, connected and off; a persona saved and undone; defaults carried to Create; the notification switch and the tray following each other.
- The history reader run against the LIVE ledger with SELECTs only: entry 7 read "LTX 2.3 clip, 6s" on scene 194, entries 4 and 5 the released 422 hold, entry 1 the grant, and the newest line's balance equalled `ledger.available(1)` (11,529 that day).
- Contrast computed for every text, edge and mark; a DOM audit of all six sections found nothing unlabelled.

Not verified: the live pages signed in; a real Stripe checkout or portal opened from Settings; a real password or email change through the new forms; the real model-login programs; Safari; the assistant parked on the left.

## What is next

Rules for the run: no renders, no generations, no paid calls; nothing pressed on live Stripe; no password or email write on a live account. One item is one branch from a fresh `origin/main` and one PR. Before every push: `PYTHONPATH="$PWD" venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`, and in `web/`: `npm run lint && npm run -s typecheck && npm run build && node --test tests/*.test.mjs`. A NEW look goes to Mike before code. Stop processes by PID only. Never `git add -A`.

1. **Look at the live pages signed in. No branch, read only.** Through Mike's own Chrome session (Claude in Chrome), open each of the six URLs on `https://zeropage.studio/studio/settings/`. What should be true: the Plan number equals the header's credit pill; the newest Usage line's "balance after" equals it too; the oldest Usage lines include "LTX 2.3 clip, 6s" linked to "Aisle Four Flicker"; Workspace shows one workspace and its members; Connections shows the address `https://zeropage-studio.fly.dev/mcp`; Preferences shows the saved assistant. Press nothing that leaves for Stripe, starts a sign-in, or saves a password or email. Report what differs.
2. **The header keeps the old name after a rename.** `AccountSection` holds the renamed `Me` locally; the shell's copy is read once. Add a `refreshMe` to the shell's context (`web/src/components/studio/shell.tsx` already has `loadMe`) and call it after `updateMe` in `settings/account.tsx`. The workspace switch can then use it in place of `window.location.reload()` (`settings/workspace.tsx`). Check in a browser: rename, and the rail and the avatar change without a reload.
3. **Say whose credits the Plan and Usage pages are counting.** They count the caller's FIRST workspace whichever is open (`auth.current_account_id`). Add `account: {id, label}` to what `billing_balance` and `billing_history` answer (`app/billing.py`; a test in `tests/test_billing.py` and `tests/test_credit_history.py`), and name it under the hero and the chart when it is not the open workspace (`settings/plan.tsx`, `settings/usage.tsx`). Only somebody in two workspaces ever sees the line.
4. **Whatever Mike picks from "Mike's calls" below**, one PR each. Files for each are named there.

## Mike's calls

1. **Model logins.** The card in Connections signs a person in to their own ChatGPT or Claude plan, and the React studio never uses that login (it always sends `guide_provider=gemini`; only the classic `/ui` Guide reads it). Options: (a) hide Sign in and keep the card as status plus Disconnect, a few lines in `settings/connections.tsx`; (b) wire the composer's brain to a connected login, which is a feature (`web/src/app/studio/page.tsx`, `assistant-pill.tsx`, and a personal login has no tools, so it can talk but not make); (c) leave it as it is, with its one line of explanation.
2. **The top-up's price.** Settings says "Add 750 credits" and Checkout shows the price, because the rule allowed one dollar figure, a plan's. Options: (a) leave it; (b) print it, which is `TOPUP.usd` in `settings/plan.tsx` plus one more allowed case in `tests/test_studio_shows_credits.py`.
3. **Where Stripe sends people back.** A checkout started in Settings returns to the public `/pricing?checkout=success`. Options: (a) leave it; (b) return to `/studio/settings/plan`: a `return_to` on `billing.checkout_url` that accepts only fixed names, `CheckoutBody` in `app/billing.py`, `startCheckout` in `web/src/lib/site-billing.ts`, and the Plan section reading `?checkout=` to say so and re-read the balance. It changes a URL on the money path, so it wants a test in `tests/test_billing.py` and his yes.
4. **Two workspaces.** Switching changes what the studio shows; the credits, scenes and elements stay with the first workspace a person joined. The Workspace section now says that. Options: (a) leave it, since nobody live has two; (b) make data follow the switch, which is the tenancy split CLAUDE.md describes under `current_account_id` and its own design task.
5. **Task 9 and BACKLOG #22, which and in what order:** invite a member by email (owner-only route over `src.accounts invite`); sign out everywhere (a `users.sessions_valid_from` column that `auth.current_user` checks); an avatar upload (`media.mirror`, tenant-fenced); generation defaults kept on the account instead of the browser; listing linked sign-in providers; renaming a workspace or its accent; deleting an account. The last one is irreversible and touches Supabase, owned rows and R2: ask before building it.
6. **The floating assistant on settings.** From 1280px up the settings column moves aside for it; below that it sits over the right edge and the page scrolls clear. Options: (a) leave it; (b) start it small on settings, the way it starts on Create (`restingPark` in `web/src/lib/creature.ts`).

## Checking settings in a browser

From a worktree under `.claude/worktrees/` (the script finds the main `.env` three folders up, to blank every name in it):

```bash
ln -s ../../../venv venv && (cd web && npm ci)
D="/Users/iphone/Documents/PRODUCTION PIPLINE .GIT/data/_scratch_settings"
PYTHONPATH="$PWD" venv/bin/python "$D/dev_api.py" 8041 reset stripe      # in the background
(cd web && API_UPSTREAM=http://127.0.0.1:8041 NEXT_PUBLIC_API_URL= NEXT_PUBLIC_AUTH_ORIGIN= npx next dev --port 3141)
node "$D/shots.mjs" <out dir> "$D/cookies.json" mara                     # twelve screenshots
```

- Flags after the port: `reset` drops and recreates the schema `zp_settings_dev` on the local test Postgres; `stripe` makes checkout "configured" and sends checkout and the portal to local addresses; `nomcp` turns the Claude connector off; `nologins` makes the model-login programs look uninstalled.
- It writes `cookies.json` beside itself: `mara` (Creator, monthly, three weeks of history, two more workspaces), `trial`, `ops` (exempt), `yearly`. In the browser open `http://zpset.localhost:3141/studio/settings` and set `document.cookie = "zp_session=<value>; path=/"`. Pick another host name if another session is using that one.
- The stubbed proofs: the current password is `current-pass-1`, the emailed code is `123456`.
- Afterwards: stop both servers by PID, `git checkout -- web/next-env.d.ts`, and drop the schema.

## Don't

- Don't press Choose, Add credits or Manage billing on the live site: they open live Stripe.
- Don't start a second checkout for a workspace that has a plan. It would be a second subscription. That is why "Switch to ..." opens the portal.
- Don't put a hex in `settings.css`, or a dollar anywhere in settings but a plan's price.
- Don't change the assistant's size or where it rests without Mike's pick; that rule is his.
- Don't force screenshots into git past the ignore rule. Hand them over, or ask.
