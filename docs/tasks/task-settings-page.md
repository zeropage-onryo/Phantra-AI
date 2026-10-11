# Task: Settings, rebuilt (Runway / Higgsfield shape)

Mike, 2026-10-11: "build out the settings page for zeropage. Make it like
runways or higgsfield and revamp the ui to make it a bit more appealing."

## Where it stands

`web/src/app/studio/settings/page.tsx` (454 lines, 2026-10-03) is one
`max-w-3xl` column of four bordered cards: Profile (name), Password
(set/change with the current-password-or-emailed-code proof), Email
(change, confirmed by Supabase), Workspaces (list + Switch). A ghost
"Sign out of this device" at the bottom. It works; it looks like a form.
Reached only from the account menus.

What the server ALREADY answers that the page never shows:

| Data | Route | Today it lives in |
|---|---|---|
| balance, plan, lots, schedules, exempt, portal | `GET /api/billing/balance` | the header credit pill |
| checkout / Stripe portal | `POST /api/billing/checkout`, `/billing/portal` | the credit pill |
| Claude connector address + "connected" | `GET /api/me` (`mcp_url`), `GET /api/mcp/connection` | `connect-claude.tsx` modal |
| personal ChatGPT / Claude CLI logins | `/api/model-connections` (list, signin, disconnect) | composer brain pill |
| assistant persona (creature + name) | `GET/PUT /api/assistant` | the pill |
| ledger entries (holds, settles, grants) | `src/ledger.entries()` | **no route** |
| image models / default | `GET /api/image-models` | composer picker (default in localStorage) |

So most of this is a LAYOUT and SURFACING job, not new backend.

## The shape (what Runway and Higgsfield share)

A settings area, not a settings page: a left section nav, one section on
screen at a time, each section its own URL, the header row of each
section a title + one-line description, rows laid out "label and hint on
the left, control on the right", destructive things in a red-bordered
Danger zone at the bottom. Usage and billing get real visual weight (a
big balance number, a plan card, a history table) because on both
products that is the page people actually come to.

Routes (Next app router, nested layout):

```
/studio/settings                 -> redirect to /studio/settings/account
/studio/settings/account         profile, email, password, sessions, danger zone
/studio/settings/plan            plan card, credits, lots + expiry, top up, Stripe portal
/studio/settings/usage           credit history (ledger), filters, per-model totals
/studio/settings/workspace       workspaces, members (read), switch
/studio/settings/connections     Claude (MCP), ChatGPT / Claude logins
/studio/settings/preferences     assistant, generation defaults, notifications, keyboard
```

Phone (<640px): the nav becomes a horizontal scroll of pills above the
section, the section rows stack.

## Rules this must keep (from CLAUDE.md, do not relitigate)

- **Credits, never dollars**, anywhere in the studio
  (`tests/test_studio_shows_credits.py`). `monthly_usd` on a plan is a
  PRICE and is the one dollar figure allowed, on the plan card only, as
  the public `/pricing` page shows it.
- **Nothing on these pages spends.** Top up / change plan go to Stripe
  Checkout or the portal; Stripe is where money moves.
- **Colours from the palette on `:root`** (`studio.css`: `--signal`,
  `--void`..`--slate`, `--edge*`, `--text`, `--bone*`, `--dim*`, `--ok`,
  `--warn`). No hex in a rule. Tailwind `noir-*` / `bone*` map onto it.
- **Every password / email write re-proves the person** (current password
  or mailed code). Keep `ProofFields`' contract exactly; restyle only.
- **Undo through the toast** where the change is soft
  (`toast(text, kind, {action})`), held-then-sent where it is hard (the
  element-delete pattern).
- **Membership is granted by members, never by signing up.** Showing
  members is fine; an invite UI is BACKLOG #22 and is its own decision
  (task 9, optional).
- **Disconnecting Claude is claude.ai's**, not ours: the Connections
  section says where, it deletes nothing.
- One-file-per-concern: section components under
  `web/src/components/studio/settings/`, the page files thin.

## Tasks

Do them in order; each is a PR-sized commit with its own verification.
Check the box in this file as each lands.

### 1. Settings shell and routing  [x]
- `web/src/app/studio/settings/layout.tsx`: left nav (icon + label, active
  = `--signal` rule on the left edge + `--text` label, inactive `--dim`),
  sticky; content column `max-w-[760px]`; mobile pill row.
- `settings/page.tsx` -> `redirect("/studio/settings/account")`.
- Shared primitives in `components/studio/settings/ui.tsx`:
  `SectionHeader {title, description}`, `SettingsCard`, `Row {label,
  hint, control}` (two-column >=640px, stacked below), `Divider`,
  `DangerZone`, `Badge`, `Stat {value, label}`. Replace the page's
  `CARD/BTN/PRI/GHOST/FIELD` string constants with these.
- Account menus (`shell.tsx` `MenuTail`): "Settings" -> `/account`, add
  "Plan & credits" -> `/plan`. The ⌘K palette (`lib/palette.ts`) gets one
  command per section.
- Old URL `/studio/settings` keeps working (redirect); add it to
  `legacy-routes.ts` tests if that file covers studio routes.
- **Verify:** every section URL loads directly and from the nav; reload
  keeps the section; 390px has no horizontal scroll.

### 2. Account section (restyle of what exists)  [x]
- Profile card: avatar circle (initials on an account-accent ring; no
  upload in this task), name inline-edit with Save appearing only when
  dirty, email shown read-only with "Change" opening the email form in
  place.
- Password and Email: same logic, moved into `Row`s; the proof block as a
  segmented control ("Current password" | "Email me a code") instead of
  radios; "Sign-in methods" row listing what the account has (password set
  or not, from `/me/security`; Google/Discord if the identity says so --
  add `providers` to `/me/security` only if it is one read off the
  identity, else skip it).
- Sessions row: "Sign out of this device" (exists). "Sign out everywhere"
  is BACKLOG #22 -- show it disabled with "coming soon" ONLY if Mike wants
  it visible; default is to leave it off.
- Danger zone: "Delete account" is NOT built. Leave the zone with
  "Leave workspace" only if task 5 builds it; otherwise omit the zone.
  **Ask Mike before building any account deletion** (it is irreversible,
  touches Supabase auth, owned rows and R2 media).
- **Verify:** set a first password on a code-only account, change it, change
  email -- each still requires the proof and still toasts.

### 3. Plan & credits section  [x]
The Runway/Higgsfield centrepiece.
- Hero: large available-credit number (`available`), smaller
  `outstanding` ("held by renders in progress"), plan name + tier badge,
  next release date for yearly schedules ("312 credits on Nov 3").
  `exempt` accounts: replace the number with "Not charged -- operator
  account" (the pill's wording).
- Plan card: current plan, credits/month, price (`monthly_usd`, the one
  allowed dollar figure), "Change plan" -> the existing checkout flow,
  "Manage billing" -> `/billing/portal` when `portal`, hidden otherwise.
  When `!checkout_configured`, say so plainly (as the pill does).
- Plan comparison: the three `src/pricing.PLANS` side by side, read from
  `web/src/content/pricing.json` (the same file `/pricing` renders), the
  current one marked. No new pricing source.
- Lots table: kind, granted, remaining / total as a bar, expires (relative
  + "expires soon" `--warn` under 7 days).
- "What things cost" strip: a still (`prices.still`), and a link to the
  public `/models` page for clips. Credits only.
- Reuse `getBalance()` and re-read on `BALANCE_EVENT`.
- **As built, one departure:** "Change plan" starts a checkout only for a
  workspace with NO plan. One that already has a plan switches in Stripe's
  portal ("Switch to Studio" opens it): `billing.checkout_url` does not look
  for an existing subscription, so a second checkout would start a second
  subscription beside the first and Stripe would bill both. The top-up's
  price is not printed (only a plan's price may be); Checkout shows it.
- **Verify:** an exempt account, an account with a plan, an account with
  only the 100-credit trial, and a server with no `STRIPE_*` all render
  sensibly; no `$` anywhere except the plan price (extend
  `test_studio_shows_credits.py` to cover the new files).

### 4. Usage section  [x]
- New route `GET /api/billing/history?before=&limit=50` in
  `app/billing.py`'s `API_ROUTES`, guarded by `auth.current_account_id`,
  over `ledger.entries(account_id)`: `{id, at, kind (grant|hold|settle|
  release|expire), credits (signed), what (human line: "Kling 3 clip,
  10s", "Still · Nano Banana", "Monthly credits"), ref (concept/gen id),
  balance_after}`. Never `cost_usd`. Paged by id.
- A test in `tests/` that the route is tenant-scoped (the
  `test_tenancy.py` route rule will fail it otherwise) and dollar-free.
- Page: 30-day bar chart of credits spent per day (follow the `dataviz`
  skill; one series, palette tokens), totals by model/kind beside it,
  then the history table with filter chips (All / Renders / Stills /
  Grants) and "Load more". A row with a `ref` links to the scene or the
  Assets item (`sceneHref`, `/studio/assets?open=`).
- **Verify:** against the live account 1 ledger (entries 1-9 from the
  2026-09-26 fal test exist): the LTX settle, the released 422 hold and
  the grant all read correctly.
- **As built:** the reader is `src/credit_history.py` (the route is a few
  lines over it). One row per MOVEMENT, not per entry: a hold that drew on
  two lots is one line. Each row also carries `group` (render | still |
  effect | grant) and `label` (the model) for the chips and the totals, and
  `ref` is `{kind: "scene", id, title}` or `{kind: "render", id}`. The first
  page carries `summary` (30 days of spend per day and by model, a render
  counted once at what it NET cost on the day it was held), so the chart
  never depends on how many pages are loaded. Read against the live ledger
  (SELECT only) on 2026-10-11: entry 7 reads "LTX 2.3 clip, 6s" on scene
  194, entries 4/5 are the released 422 hold with the same line, entry 1
  the grant, and the newest line's balance equalled `ledger.available`.

### 5. Workspace section  [x]
- Workspace cards: accent dot, name, role, "Active" badge, Switch
  (existing `switchAccount` + reload).
- Members list (READ ONLY): new `GET /api/account/members` returning
  name/email/role/claimed for the ACTIVE account; owners see emails,
  members see names only. Skip this route if Mike says single-user for
  now.
- **Verify:** switch round-trips; a member account cannot read another
  account's members.
- **As built, and one bug found on the way:** the switch did NOT
  round-trip. `POST /brand/<slug>` stored only the two legacy brand names
  in the cookie, so asking for any other workspace stored the default
  brand and `auth.current_account` fell back to the caller's FIRST
  membership, whichever was clicked (the account menus had the same bug).
  The route now accepts a slug the signed-in person is a member of
  (`app/main.py set_brand`); anything else is still the default.
  The members list is the ACTIVE workspace's (`auth.current_account`,
  backed by real membership; no id is taken from the request). The answer
  also carries `home`: the workspace every data route acts on, which is
  the caller's FIRST one whichever is open (`auth.current_account_id`).
  Somebody in two workspaces is told so on the page, because switching
  does not move their credits or scenes -- that is how tenancy works
  today, and changing it is its own task.

### 6. Connections section  [x]
- Claude card: lift the body of `connect-claude.tsx` into a component the
  modal and this section both render (one source; the modal stays for
  the menu). Status from `/api/mcp/connection`: connected client name +
  "last used 3h ago", or the copy-the-address steps. Removal text points
  to claude.ai, deletes nothing.
- ChatGPT / Claude logins: list `/api/model-connections`, Sign in /
  Disconnect per provider, the same calls the brain pill makes.
- **Verify:** with the mount off (`mcp_url` null) the card says the
  connector is off rather than showing a dead address.
- **As built, and one thing this task's table had wrong:** the React
  studio never uses a personal model login. Its composer and assistant
  always post `guide_provider=gemini`; only the classic studio's Guide
  (`/ui?legacy=1`, `app/static/zpf/model-connections.js`) can answer with
  one. So the logins card is built as asked -- list, sign in, disconnect,
  the same calls -- and SAYS that on the card, rather than letting a
  customer sign in to something these pages do not use. Whether to wire
  the composer's brain to a connected login, or to hide sign-in here, is
  Mike's call.

### 7. Preferences section  [x]
- Assistant: the persona (creature + name) with a live preview of the
  avatar (`assistant-avatar.tsx`), saved through `PUT /api/assistant`.
- Generation defaults: default image model (`/api/image-models`), Ask
  first / Auto (`GENERATE_MODES`), default frame and scene length. These
  live in localStorage today; keep localStorage (per browser) in this
  task and label the card "on this browser". Moving them server-side is
  a follow-up, only if Mike wants them to follow him across devices.
- Notifications: the job-finished browser notification toggle the
  activity tray already has (`activity-tray.tsx`), read/written from the
  same place so the two cannot disagree.
- Keyboard: a read-only list of the shortcuts that exist (⌘K, A/X/arrows
  on Queue and workspace, editor I/O/F9/F10).
- **Verify:** change the default model here, open the composer: the picker
  shows it; toggle notifications here, the tray agrees.
- **As built:** the persona is `PUT /api/assistant/persona` (not
  `/api/assistant`), with the creature / look / colour / tone options of
  `lib/mascot.ts`; saving fires `PERSONA_EVENT` so the floating assistant
  changes on the spot, and the toast carries Undo. The image model and
  Ask / Auto were already in localStorage, so this section and the
  composer's own pickers are one value. The frame and the scene length
  were NOT stored anywhere (the composer always started from the server's
  default), so they are new: `lib/scene-defaults.ts` holds a default a new
  scene STARTS from, the composer reads it on load, and changing either on
  Create stays for that scene only. Notifications moved into
  `lib/notify-pref.ts`, which the tray and this section both use.

### 8. Visual pass across the section  [ ]
- Typography: section titles in the studio display face at ~20px, row
  labels 13px `--text`, hints 12px `--dim`; generous vertical rhythm
  (24px between rows, 40px between cards).
- Cards: `--slate` surface, `--edge-lo` border, 14px radius; hover lifts
  to `--edge`; focus rings in `--signal-soft`.
- Primary button white-on-black as today; destructive in `--signal`.
- Motion: section switch cross-fades (motion/react, 120ms), skeleton rows
  while loading instead of "Loading…".
- Empty states written, not blank (no history yet, no connections).
- Run the `design:accessibility-review` checks: contrast on `--dim`
  hints, labels bound to inputs, the nav is a `<nav>` with
  `aria-current`.
- **Verify:** screenshots at 1440 and 390 of every section, light of the
  real data, in Chrome against the running dev server; attach them to
  the PR.

### 9. Optional, only on Mike's yes
- Invite members by email (BACKLOG #22) -- `src.accounts invite` behind a
  route, owner-only.
- Sign out everywhere (BACKLOG #22).
- Avatar upload (R2 via `media.mirror`, tenant-fenced).
- Server-side generation defaults (a `prefs_json` on the user row).
- Delete account / delete workspace.

## Done means
- `venv/bin/python -m pytest tests/ -q` and `venv/bin/ruff check .` green;
  `cd web && npm run lint && npm run build` green.
- Every section verified in a browser as written above.
- CLAUDE.md gains a short "Settings" bullet under Architecture naming the
  routes and the new `/api/billing/history` + `/api/account/members`.
