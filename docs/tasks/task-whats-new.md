# Task: What's new — the Create wall fills itself (2026-10-25)

**Mike's call (2026-10-25):** the Create wall is a sitewide channel that tells every user about
new models, new effects and new features. Adding one in code makes its tile; Mike approves ONE
showcase render on the house account, keeps it, and it goes live for everyone. Nothing renders
without his Approve. Written against `main` as of 18ed64ea (the news wall, `src/content/news.json`,
`lib/front-page.ts`, `docs/tasks/task-create-front-page.md`).

The problem it fixes: Grok Imagine 1.5 / 1.5 Lite went live in `src/fal.py` on 2026-10-23
(PR #474) and is still not on the wall, because the wall is a hand-edited JSON file plus a
hand-filled showcase manifest, both shipped with a deploy.

## Decisions (Mike, 2026-10-25)

1. **A tile is hidden until Mike keeps its render.** No placeholder cards for users.
2. **The "New" badge and a public What's new page ship in this build.**
3. **Sitewide trending is a later step** (counts only, a minimum before anything shows, never
   another account's renders or prompts). Trending entries stay hand-picked until then.
4. **One render per announcement, on the house account (`phantra`)**, shown to every user. Users
   never pay for or see a price on a showcase; they pay only for their own render after a click.
5. **Approve each render**, no standing budget. Keep / Redo before anything goes live.
6. **Coming soon tiles are in** (overrides the wall's "live features only" rule).
7. **Deals are Phantra's own discounts only**, none today. No social-platform tiles, no tiles
   for fal's price changes.

## Sources (Mike, 2026-10-25)

| Kind (tag) | Where it comes from | How it gets in |
| --- | --- | --- |
| New model (`NEW MODEL`) | `fal.VIDEO_MODELS`, ready `fal.SLOTS`, `fal.IMAGE_MODELS` | Automatic: a key the feed has never seen |
| New effect (`NEW EFFECT`) | `src/effects.py` table, incl. camera moves | Automatic |
| New look (`NEW LOOK`) | `src/free_looks.py` | Automatic |
| New skill (`NEW SKILL`) | `prompts/skills/*.md` via `src/skills.py` | Automatic; the tile opens `/` with the skill loaded |
| Editor update (`UPDATE`) | the editor's transition list and other tables in `src/cut/` | Automatic, batched: "N new transitions" as one tile |
| Plugin release (`UPDATE`) | the plugin versions `/download` reads (Resolve, Premiere) | Automatic on a version bump; the tile links to `/download` |
| Connector (`UPDATE`) | the MCP tool lists in `src/mcp_server.py` (`LISTED_TOOLS`, `CLAUDE_LISTED_TOOLS`) and directory listings | Automatic for new tools; a listing going live is a feature entry |
| Model page (`NEW PAGE`) | `web/src/landing-pages/entries/` | Automatic on a new entry; the tile links to the page |
| Feature (`UPDATE`) | `FEATURES` in `src/whats_new.py` | Hand-written in the PR, or created from a merged PR labelled `whats-new` (pending, title from the PR, Mike edits and keeps) |
| Coming soon (`COMING SOON`) | `COMING_SOON` in `src/whats_new.py` | Hand-written; see below |
| Deal (`DEAL`) | `DEALS` in `src/whats_new.py` | Hand-written; empty today; see below |

**Out, by Mike's call:** social platforms (a new place to post is not announced on the wall), and
fal's own price changes (the price table moving is not news; only Phantra's deals are).

**Later:** Made in Phantra spotlights (needs a "feature this" opt-in on the person's own render,
never shown without it) and sitewide trending (counts only, a minimum before anything shows).

Each model / effect / look / skill row may carry an optional `showcase` block; without one, the
prompt is built from the row's `label` and `blurb`/`note`:

```python
"showcase": {"prompt": "...", "aspect": "16:9", "kind": "clip", "seconds": 6,
             "resolution": "720p", "title": "Grok Imagine is here", "line": "...",
             "action": {"fill": "One 6-second take on Grok Imagine: "}}
```

A hand-written entry (feature, coming soon, deal) carries the same fields plus `id`, `date`,
`requires` (a capability) and its own media: a new render, a still Mike uploads, an existing
Library item (`gen:<id>`), or `kind: "none"` (a type-only tile).

### Coming soon

Mike's call (2026-10-25), replacing the wall's earlier "live features only" rule: a tile may
announce something not yet usable.

- Tag `COMING SOON`, an optional `eta` line ("This month", "November") and never a fake date.
- **No action that makes anything**: it can't fill the box or open a model that isn't there. The
  click is **Notify me** (a per-user row in `announcement_seen` with `notify=true`) or a link to
  a page about it.
- Its picture can't come from the unreleased model. It is a still Mike uploads, a render from a
  live model he approves, or a type-only tile.
- **When the thing ships**, the coming-soon entry names the model / effect / feature key it
  becomes (`becomes: "model:grok2"`). The new live tile replaces it, and everyone who pressed
  Notify me gets the New badge on that tile first (an email later is optional, not in this build).
- An entry past its `eta` with nothing shipped stays up, but the wall shows no eta line; Mike can
  retire it from the Showcase list.

### Deals

Phantra's own discounts and offers only (a plan discount, a credit bonus, a founding offer).
None are live today, so `DEALS` ships empty.

- Tag `DEAL`, a `starts` and `ends` date; the tile shows only inside that window and retires itself
  after `ends`.
- This is the one tile allowed to name money or credits, because the offer IS the news ("20% off
  yearly", "+200 credits on a top-up"). The no-price rule still holds for every other tile, and
  the test that checks it exempts `DEAL` alone.
- `requires` can limit a deal to who it applies to (a plan, a new account).
- The click goes to the plan or top-up page with the deal applied there. The deal is enforced in
  billing, never by the tile.

## Data

- **`showcase_items`** (SHARED; reason: "site announcements; house renders only, no account's
  data"): `id` (e.g. `model:grok1.5`, `effect:bullet_time`, `feature:final_cut`), `kind`,
  `source` (`model|effect|feature|manual`), `title`, `line`, `accent`, `size`, `prompt`,
  `model`, `params_json`, `action_json`, `requires`, `status`
  (`pending → rendering → review → live`, plus `skipped`, `retired`), `starts`, `ends`, `eta`,
  `becomes` (coming soon / deals), `media` (a stored NAME,
  never a URL; `media.url_for` mints it), `poster`, `credits_spent`, `gen_id`, `first_seen_at`,
  `live_at`, `retired_at`. Listed in `db.SHARED_TABLES`.
- **`announcement_seen`** (OWNED, by user and account): `user_id`, `account_id`, `item_id`,
  `seen_at`, `dismissed_at`, `notify` (Coming soon's Notify me). Listed in `db.OWNED_TABLES`; drives the badge and the unread count.
- `src/whats_new.py` owns both tables and exposes `ensure(dsn)` (inits once per process; never
  per request).
- `news.json` stays for the hand-made tiles (use-case renders, the Claude card). The wall merges
  `live` rows from `/api/whats-new` with `news.json`, newest first; on an id clash the database wins.

## The flow

1. **Sync on boot.** `whats_new.sync()` runs at process start under `db.run_init` (same shape as
   the fal recovery sweep; `PHANTRA_WHATS_NEW_SYNC=0` turns it off). It diffs the three sources
   against `showcase_items` and inserts a `pending` row for anything new. It spends nothing.
   First run seeds every EXISTING model/effect as `skipped` so the wall isn't flooded; only keys
   added after that become `pending`.
2. **Operator list.** `/studio/renders` gains a Showcase section (operator only,
   `accounts.operator`): each pending row with its prompt (editable), model, length and a priced
   **Approve render** button. Price through `pricing.quote` / `display`, credits on the card.
3. **Render.** Approve takes the normal quote token and ledger hold on the house account and
   renders on fal through the existing adapter (a still through `fal.IMAGE_MODELS` / Gemini). The
   file is mirrored to R2 under `site/showcase/<id>-<32hex>.<ext>`, plus a poster frame. Row →
   `review`. A failure releases the hold and says so in plain words.
4. **Keep / Redo.** Keep → `live`, `live_at` set. Redo → back to `pending` with the old take
   kept (soft; a paid output is never thrown away). Skip → `skipped` (never shown).
5. **Show.** `GET /api/whats-new` returns the `live` rows the caller can use: a model must still
   be in its table and ready (`slot_ready`), and `requires` must be true for the caller. A model
   removed from its table → its tile disappears and the row is `retired`.
6. **Age out.** A tile sits in the New position for 21 days from `live_at`, then drops into the
   normal wall order; it leaves the wall when the source row leaves its table.

## What a user sees

- A **New dot** on the Create rail with an unread count (`live` items with no `announcement_seen`
  row for this user). Opening Create marks the visible ones seen; a tile's X marks it dismissed.
- The tile on the wall, autoplaying muted, tag `NEW MODEL` / `NEW EFFECT` / `UPDATE`. Clicking it
  runs its `action` (fill the box with the prompt and pick the model, open the effect, a page).
  Never sends, never shows a price.
- **`/whats-new`**, a public page (no sign-in), the same `live` rows newest first, each with its
  clip, date and a link into the studio. Server-rendered for search, with `Article` JSON-LD per
  item and an RSS feed at `/whats-new/rss.xml` (later: feeds the Discord bot and socials).

## Build steps

- [x] `src/whats_new.py`: tables, `ensure`, `sync` (with the first-run seed), `feed(account, user)`,
      `mark_seen`, `dismiss`. `FEATURES` list with the existing features back-filled as `skipped`.
- [ ] Sync readers for each source in the table above (models, effects, looks, skills, editor,
      plugins, connectors, model pages); `FEATURES`, `COMING_SOON` and `DEALS` lists (DEALS empty).
- [x] `showcase` blocks on `grok1.5` and `grok1.5-lite` (the first real pending rows).
- [ ] GitHub: a merged PR labelled `whats-new` creates a pending feature row (a small webhook
      route or a CI step that calls it; the operator edits the copy before Keep).
- [x] Boot hook in `app/main.py` beside the fal recovery sweep.
- [ ] Routes: `GET /api/whats-new`, `POST /api/whats-new/{id}/seen`, `.../dismiss`; operator:
      `GET /api/showcase`, `POST /api/showcase/{id}/quote`, `/approve`, `/keep`, `/redo`, `/skip`.
- [ ] Studio: wall merges the feed (`lib/front-page.ts` reads both); New dot on the rail;
      Showcase section on Renders.
- [ ] Public `/whats-new` page + RSS.
- [ ] `/ship` mod: warn when a PR adds a model or effect row with no `showcase` block, or touches
      a user-facing feature with no `FEATURES` entry (a reminder, not a block).

## Tests

- `tests/test_whats_new.py`: sync inserts pending for a new key and skips on first run; never
  spends; a removed model retires its row; `feed` hides non-live rows, unready slots and failed
  `requires`; seen/dismiss are per user.
- Tenancy: `showcase_items` in SHARED with its reason; `announcement_seen` owned; every new
  `/api` route declares `auth.current_account_id`; operator routes refuse a non-operator.
- Spend: approve without a quote token is 400 `missing_quote`; the hold is on the house account;
  a failed render releases.
- `web/tests/front-page.test.mjs`: the merge (db wins on clash), no price or "credits" on any
  tile except `DEAL`, a tile with no media never renders unless it is type-only, a coming-soon
  tile never fills the box, a deal outside its window never shows.
- `tests/test_whats_new.py` also: a coming-soon entry is replaced by the tile it `becomes`, and
  its Notify me users see that tile as unread; social platforms and fal price changes never
  create rows.
- Verify by running it: boot the API, add a fake model row, see the pending row, approve a cheap
  still on a test key, keep it, see it on the wall and on `/whats-new`, see the dot clear.

## Later

- Sitewide trending: a nightly count-only aggregate, a minimum count before an item shows,
  listed in the tenancy test's exempt list with its rule. Trending tiles use the house showcase
  clip for that effect, never a user's render.
- Made in Phantra spotlights, with an opt-in on the person's own render.
- Email for Notify me. Showcase variants (2–3 takes, Mike picks one). Plan-gated "On Pro" labels
  instead of hiding.

## As built

### Step 1 (2026-10-25, branch `claude/whats-new`): the backend, nothing spends

- `src/whats_new.py`: `showcase_items` (SHARED, reason in `db.SHARED_TABLES`) and
  `announcement_seen` (OWNED, `db.OWNED_TABLES`, unique on account + user + item), `init` /
  `ensure(dsn)`; `sync()` reads four automatic sources (fal's video and image tables, the effects
  table split into effects and looks by `category == "look"`, the skills shelf) and the three
  hand lists (`FEATURES`, `COMING_SOON`, `DEALS`, all empty); `feed()`, `mark()` (seen /
  dismissed / notify), `queue()` (what waits on Mike).
- The showcase copy for an automatic source lives in `whats_new.SHOWCASE` by id, NOT as a
  `showcase` key on the fal / effects rows: those rows are read field by field by the adapters
  and the pricing export, and a stray key there is a risk for no gain. Without an entry, copy is
  built from the catalogue name and blurb (video), `label` / `note` (images, effects), the skill's
  title and `for` line. Grok 1.5 and 1.5 Lite have entries and are `SEED_PENDING`.
- First run on an empty table: every automatic entry already in the tables is `skipped` (old
  news); hand entries and `SEED_PENDING` are `pending`. Checked against a blank database by
  starting the app: 2 pending (both Grok), 48 skipped (20 models, 13 effects, 6 looks and 11
  skills, less the two Grok rows); a second sync changed nothing.
- A source whose reader raises retires nothing that run. A model taken out retires its row; put
  back, it is `live` again if it had been kept, else `pending`. A deal past `ends` and a
  coming-soon item whose `becomes` is live retire on the next sync.
- The feed hides a live tile whose model / effect / skill is no longer offered, even before the
  next sync. A coming-soon tile's action is cut to `href` only (never fills the box); a person's
  Notify me puts `you_asked` on the tile it becomes. No item carries a price.
- `app/whats_new_routes.py` under `/api`: `GET /api/whats-new`, `POST /seen`, `/{id}/dismiss`,
  `/{id}/notify` (404 `not_coming_soon` for anything else). Capabilities for `requires` are
  `api.compute_capabilities(account_id)`.
- Boot: `whats_new.init()` in `init_tables`; `whats_new.start_sync()` in the lifespan after the
  fal sweep, under `db.run_init`, off with `PHANTRA_WHATS_NEW_SYNC=0`.
- Tests: `tests/test_whats_new.py` (17), and `tests/test_tenancy.py` inits the new module.

### Step 2 (2026-10-25, same branch): the operator's Showcase list

- **Who:** the OWNERS of the house account (`whats_new.house_account_id`: the slug in
  `PHANTRA_SHOWCASE_ACCOUNT`, default `phantra`), resolved from the tenant the session already
  proves, never a parameter. A member who is not an owner, and anyone in any other workspace,
  get a plain 404 `not_found` from every `/api/whats-new/showcase*` route, and the section on
  Renders draws nothing. (The retired `manual_lane_operator` flag is not reused.)
- **The moves** (`src/whats_new.py`, each one guarded UPDATE so two clicks can't both render):
  pending -> rendering -> review on Approve; pending/review -> review on Pick (a house Library
  item by `gen:<id>`, for effects, looks and features that have nothing to render alone);
  review -> live on Keep (pending -> live for a words-only tile); review/live -> pending on Redo
  (the take stays in the Library, its id kept in `params.takes`); pending/review -> skipped,
  skipped -> pending on Restore. Words, prompt, seconds / resolution / aspect edit only before
  live (Redo first), so a tile people saw never changes under them.
- **The spend:** `POST .../approve {expect_credits}`. The price is `direct.video_quote` /
  `direct.image_quote` on the house account (the Video and Image pages' own quote, the number
  the hold takes); a different number is 409 `price_changed`; the render is
  `fal.generate_from_prompt` / `generate_image_from_prompt` with `approved=True`,
  `source="showcase"`, `bank=True`, so it takes the house account's ledger hold, files in its
  Library, and a failure releases (the adapter's rule) and puts the row back to pending with
  the reason in `note`. The row stores the Library row's NAME (`media_url`), its account and
  `gen:<id>`; the feed mints the address (and a clip's 480px poster) on read.
- **A deploy mid-render:** a row still `rendering` 30 minutes after its last change goes back to
  pending on the next sync, with a note to pick the take from the Library (the fal sweep files
  it there).
- **Columns added in step 2** (`media_type`, `media_account`, `note`) are also ALTERed onto an
  older table at init: starting the app on the step-1 database found that `CREATE TABLE IF NOT
  EXISTS` alone left them missing.
- **Studio:** `components/studio/showcase/showcase-list.tsx` on `/studio/renders` above the
  jobs, `web/src/lib/whats-new.ts` (types, fetchers for the feed and the list). Each waiting row:
  the take (or an empty frame), tag, title, line, model / seconds / resolution, an editable
  prompt with Save, the priced **Render · N credits** button, Use this Library item, Keep, Redo,
  Skip; live and skipped fold under one line. Checked in a browser against `next dev` and the
  API on a local database with a signed session cookie: both Grok rows waiting, 202 credits
  (1.5, 6s 720p) and 44 (Lite); no click on Render was made (it spends).
- Tests: 25 in `tests/test_whats_new.py` (the gate, the price check, one render only, a failed
  render, redo / skip / restore, pick, words-only keep, edits re-price, the interrupted render,
  the column upgrade).
- The house account's renders are watermarked if it has no plan (`src/watermark.py`); give
  `phantra` a plan or set it credit-exempt before approving the first showcase.

Not in step 2, still to build: the editor / plugin / connector / model-page readers, the wall
reading the feed, the New dot, `/whats-new` + RSS, the `whats-new` PR label, the `/ship` reminder.
