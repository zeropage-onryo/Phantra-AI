# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

It describes the product as it is. The reasoning behind most decisions, and everything that
has since been removed, is in **`docs/HISTORY.md`** (the full previous version of this file,
word for word, to 2026-10-14). Look there before re-adding something that sounds missing:
it was often removed on purpose.

## Overview

**Phantra** (phantra.ai) is an AI production studio. It generates AI images and AI video
from a person's idea and their own photos, and around that core it has effects (image edits,
template effects, camera moves, upscaling, sound, reframing, background removal), production
tools (projects, elements and reference sheets, a timeline editor, a library, draft-then-finish),
MCP servers (a connector for ChatGPT and for Claude, and a local studio server for Claude
Desktop) and plugins (a Claude plugin and a ChatGPT plugin of skills that drive the connector).
Work is paid for in credits, and nothing is spent without a priced approval. It was named
Zero Page until 2026-10-13 (`docs/tasks/task-rename-to-phantra.md`).

What a signed-in person has:

- **Create** (`/studio`): one chat box. The brain talks, proposes a plan, and makes a still or
  writes a scene only on an ask; every spend waits on a priced card.
- **Projects** (`/studio/projects`): a brief, a look, a memory and the scenes of one piece of
  work. A brand lives inside a project, never studio-wide.
- **A scene and its Render card**: timed shots, each rendered as its own clip on fal (Kling,
  Veo, Seedance, LTX, Wan). The priced button on the card is the only place a clip is paid for.
- **Elements** (`/studio/elements`): the characters, products and places a scene is held to,
  each with photos and a drawn reference sheet. A scene with no photographs does not render.
- **Library** (`/studio/assets`) and **Renders** (`/studio/renders`): everything made, with
  effects, download and draft-then-finish.
- **The editor** (`/studio/cut`): a timeline over the rendered clips, with an agent that
  proposes edits; export to MP4, audio, a still or OpenTimelineIO.
- **The connector**: an MCP server at `https://api.phantra.ai/mcp` (the ChatGPT listing; it
  renders) and `/mcp/claude` (the Claude listing; it writes and prices, renders happen in the
  studio), plus the stdio studio server Claude Desktop launches.
- **The plugins**: `phantra-claude-plugin` and `phantra-chatgpt-plugin`, public repos beside this
  one (`../phantra-claude-plugin`, `../phantra-chatgpt-plugin`): skills that drive the connector.
- **Credits and plans**: Stripe plans grant credits; every render and still takes a ledger hold
  before the provider call; model text is free on a plan.

**Where it runs.** The site and studio are Next.js (`web/`) on Vercel at phantra.ai; the API is
FastAPI (`app/` over the library in `src/`) on the Fly app `phantra-api`, at api.phantra.ai;
state is Postgres on Supabase, sign-in is Supabase Auth; media is the `phantra-media` R2
bucket at media.phantra.ai; video and most image models run on fal.ai, text and some stills on
Gemini. zeropage.studio 308-redirects to the same path on phantra.ai. Names that still carry the
old brand until their own step: the GitHub org `zeropage-onryo`, the Vercel project, the stopped
Fly app `zeropage-studio` and the old bucket `zeropageclips` (both awaiting deletion). Account 1's
slug is `phantra` ("Phantra AI") since 2026-10-15; the brand labels are gone
(`docs/tasks/task-remove-brand-labels.md`, done).

## Backlog and mods

Parked ideas, known bugs and next builds live in `docs/BACKLOG.md`. Read it before proposing new
work: several obvious-looking gaps are already recorded there with the reasoning. Task files
(`docs/tasks/task-*.md`) carry each build's "As built" notes; read the relevant one before
touching its area.

Three Claude Code mods (`/ship`, `/merge`, `/wrap`, `/handoff`, `/servers`, `/ci`, a spend guard,
a CI watcher) live under `.claude/skills/phantra-*`; `docs/CLAUDE_MODS.md` says how to load them.

## Commands

All Python runs through the project's venv. `src/` is an installed editable package: modules use
relative imports and run as `python -m src.<module>`.

```bash
venv/bin/pip install -r requirements.txt
venv/bin/pip install -e .

# The API (127.0.0.1:8000) and the studio (localhost:3000, proxies /api to the API)
venv/bin/uvicorn app.main:app --reload
cd web && npm install && npm run dev

# Checks (CI runs all of these on every pull request (not on plain pushes since 2026-10-15): .github/workflows/ci.yml)
venv/bin/python -m pytest tests/ -q          # 35-40 min on this Mac; ~13 in CI
venv/bin/ruff check .
cd web && node --test tests/*.test.mjs && npm run typecheck && npm run build

# MCP: the stdio studio server Claude Desktop launches (ops/connect-claude.md).
# ops/claude-desktop-mcp.json holds ONE entry, `phantra-ai`; the edit sticks only while
# Desktop is quit, so the register script waits for Cmd-Q, writes it and reopens Claude.
venv/bin/python -m src.mcp_server
open -a Terminal ops/register-claude-desktop.command

# Account flags. src.accounts NEVER loads .env: export DATABASE_URL first or the flag
# lands on the local throwaway database (the tell: "no account '<slug>'" with no list).
set -a && source .env && set +a && venv/bin/python -m src.accounts credits <slug> --on
venv/bin/python -m src.accounts operator <slug> --on        # the manual render lane
venv/bin/python -m src.accounts edits-teach <slug> --on     # hand edits teach the shelf
venv/bin/python -m src.accounts seed you@example.com        # bootstrap the auth tables

# fal recovery: a render whose worker died mid-poll is finished, not orphaned. The app
# runs this on boot (FAL_RECOVER=0 turns it off); by hand it is one sweep.
venv/bin/python -m src.fal_requests [--account N]

# The editor's index (what is IN each clip). Export DATABASE_URL first.
venv/bin/python -m src.cut.index backfill [--account <slug>] [--dry-run]

# Reference photos dropped into a folder BY HAND need pushing to R2 (the app's own
# uploads mirror as they save), then stored refs rewritten (report first, --write to act).
venv/bin/python ops/backfill_reference_photos_r2.py
venv/bin/python -m ops.canonicalize_shot_refs [--account <slug>] [--write]

# Supabase auth email (templates, SMTP, Site URL) through the Management API;
# needs SUPABASE_ACCESS_TOKEN. `report` is read-only.
venv/bin/python -m ops.supabase_auth_email report
venv/bin/python -m ops.supabase_auth_email apply --templates [--dry-run]

# Instagram tokens. `keep` is THE ONLY SCHEDULED JOB in the project: daily 10:00 ET on Fly
# (the image's one cron line); the Mac runs no LaunchAgent, by Mike's choice.
venv/bin/python -m ops.ig_tokens check [--probe]
venv/bin/python -m ops.ig_tokens refresh|publish|keep

# The manual render lane (operator only): a clip rendered anywhere, filed free.
python3 ops/render_queue.py --provider manual --account <slug> import \
    --concept N --shot 1 --file clip.mp4 --model "kling 3 web app" --duration 10

# The reference library (RAG, pgvector)
venv/bin/python -m src.rag ingest <files...>
venv/bin/python -m src.rag query "<text>" [--k 5]

# Pricing table for the public site (web/src/content/pricing.json)
venv/bin/python -m src.pricing export
```

**Tests block all network access** (`tests/conftest.py`). If a test fails with
`NetworkUseInTest`, it is patching a function the code under test no longer calls; the guard
exists because a billed API call once ran inside a passing test, four times. psycopg connects
below Python's socket module, so a stray Postgres connection is NOT caught: anything touching
the RAG store must patch `rag.connect` or above.

**The Create gate is never answered from the shared test schema.** `charge.create_refusal_code`
fails open on a read error; conftest raises `CreateGateInTest` instead. A route test that hits it
stubs the function its code path calls (`charge.create_refusal_code` for `app/api` and
`app/cut_routes`, `charge.create_refusal` for `src/mcp_server`) or seeds the account in `pg`.

The local test database is `phantra` on the Postgres.app server at :5432 (role and password
`phantra`); `TEST_DATABASE_URL` overrides it. `.env` needs `GEMINI_API_KEY`; `FAL_KEY`,
`QUOTE_SIGNING_SECRET`, `R2_*`, `STRIPE_*` and `SUPABASE_*` turn on their parts.
`.env.example` lists every setting; app settings are named `PHANTRA_*`.

## Sign-in

Supabase Auth does identity (`app/auth.py`, `src/accounts.py`): Google, Discord and email with a
password, server-side with no client library. OAuth goes to `{SUPABASE_URL}/auth/v1/authorize`
(PKCE), back to `/auth/callback`, the token is verified once with PyJWT, and the session is ONE
signed httpOnly cookie, `phantra_session` (itsdangerous, 30 days), carrying the Supabase user id.
No Supabase token is stored after sign-in.

- `users` mirrors `auth.users` by UUID; `accounts` (workspaces) and `account_members` are ours.
  A new sign-up gets its own workspace and a one-time 100-credit trial
  (`PHANTRA_SIGNUP_CREDITS`); `PHANTRA_OPEN_SIGNUP=0` restores the invite-only gate, where a
  sign-in with no membership sees "no account access yet" until a member invites them.
- **The tenant** of every `/api` route is `auth.current_account_id`: the caller's OLDEST
  membership. The `phantra_account` cookie (set by `POST /account/{slug}`) only chooses among
  workspaces the person belongs to.
- **The studio gets its session by handoff, never cross-site.** The studio's fetches go to its
  own origin and Next proxies `/api`, `/auth`, `/signin`, `/account` and the photo routes to
  `API_UPSTREAM`; sign-in navigates to the API origin (`NEXT_PUBLIC_AUTH_ORIGIN`), and a trusted
  `next` ends in a 303 to `{front end}/auth/handoff?t=<2-minute token>` so the cookie lands on
  the front end's origin first-party. `STUDIO_URL` is the studio's ORIGIN only
  (`https://phantra.ai`); with `/studio` on it a sign-in lands on `/studio/studio`.
- Passwords and email changes: "Create a password", "Forgot your password?" (code or link),
  `/studio/settings`. Every password or email write re-proves the person first (current password
  or a mailed code), because GoTrue takes `PUT /user` only as the person. Emailed links use
  `GET /auth/confirm?token_hash=&type=` (no verifier cookie, any browser).
- The OAuth consent page for the connector is ours (`app/oauth_consent.py`): Supabase's OAuth
  server sends the person to `<Site URL>/oauth/consent`, the page signs them in and answers as
  them.

## Architecture

### Layout

- `src/` is the library: no web imports. Where it needs an app-layer capability (the job
  registry, an approve body, a photo resolver) the caller INJECTS a callable. The one exception
  is a process entry point (`mcp_server.main`), which may import `app/` to inject them.
- `app/` is FastAPI: `main.py` (app, photo routes, the dev console), `api.py` (the `/api` JSON
  routes), `auth.py`, `billing.py`, `cut_routes.py`, `mcp_mount.py` / `mcp_auth.py`, `jobs.py`
  (an in-process, deliberately non-persistent job registry with one SSE feed,
  `/api/jobs/stream`). uvicorn runs with `--timeout-graceful-shutdown 3` because the SSE socket
  otherwise wedges every reload and deploy.
- `web/` is the Next.js site and studio; `prompts/` holds every prompt as plain text; `ops/` holds
  scripts (report first, `--write` to act, re-runnable); `docs/` holds task files, the backlog,
  the billing design and the runbook.
- Every table is OWNED (has `account_id`, listed in `db.OWNED_TABLES`) or named in
  `db.SHARED_TABLES` with the reason it is global; `tests/test_tenancy.py` fails on one that is
  neither, and on any `/api` route that does not declare `auth.current_account_id`.
- **Schema inits never run per request.** An init is not safe beside a copy of itself: two at
  once deadlock. Process starts run inits under `db.run_init` (an advisory lock, retried on a
  deadlock); a module written to from a request exposes `ensure(dsn)`, which inits once per
  process and database (`generative`, `render_assets`, `fal_requests`, `ledger`, `billing`).
  A new module that owns a table follows that shape.

### Create: the composer and the brain

`web/src/app/studio/page.tsx` + `components/studio/composer/` + `lib/composer.ts`. One box under
"What are we making?", an Image | Video switch, a settings line (frame, length, model, Ask first /
Auto, Fast / Reasoning), `/` for commands, drop to attach.

- **Every send is a brain turn** (`POST /api/creative-guide`, `src/creative_guide.py`,
  `src/guide_tools.py`). The model decides between talking and making. Make tools are published
  only to a maker turn; a turn ENDS on any write as a proposal and the studio runs it:
  `make_video` writes a scene at once (free) and its priced Render card is drawn IN that turn under the shots, so a clip is approved and rendered from the chat with no dialog, and when the last shot lands the shots are joined into ONE MP4 in the same turn by the editor's Assemble, free, and filed in the Library as "Final cut" under the scene (`assemble.file_on_wall`, its clips named as sources), with Trim (a new free clip through `/api/quick-edit`) and Edit the cut under it (`lib/final-cut.ts`; Runway's Final Cut) (2026-10-20; a plan's scene keeps Render…, its plan's render step approves it), `make_image` becomes a **step card** with the
  model and its price, drawn on Approve (or at once with Auto, never above the price the send
  button showed). The rule the brain follows is `prompts/creative_guide_make.txt`: make only on
  an ask in this turn or a confirmed offer.
- **Plans** (`src/make_plan.py`, `lib/make-plan.ts`): one `make_plan` write lists 2-8 steps
  (image / scene / sheet / keep / keyframes / render); the composer runs them through the doors
  each step already has, priced on the card, each costing step stopping for its own Approve
  unless covered by "Approve all"; a clip render ALWAYS waits for its own button.
- **Effects in chat**: `/effects` opens a gallery (browsing is free); the brain's
  `apply_effect` or a pick puts a priced card in the thread; `POST /api/effects/run` takes the
  credits the card showed and refuses (409) if the price moved. A **talking photo** is the same
  shape (`components/studio/talking-photo-step.tsx`, `lib/talking-photo.ts`): `/talking-photo` or
  the brain's `talking_photo` proposal opens a card (photo, a consent box never pre-ticked, an
  .mp3/.wav or a script with a priced Preview), and its Render is the one click that spends.
- **Skills** (`src/skills.py`, `prompts/skills/*.md`): recipes for one kind of work, loaded by
  the brain (`load_skill`) or picked from `/`.
- **The brain proposes models** from `src/model_menu.py` (the same list the pickers read); a
  proposal is only where a card opens, never a choice made for the person.
- **References say what they are for** (`src/ref_roles.py`): subject / product / place, or
  light / palette / framing / style (look-only, never first, since the first anchors).
- **Pasted links** (`src/linkrefs.py`): one fetch of the page the person chose, its preview
  images onto the contact sheet, its product facts handed to the model as quoted data. The model
  never handles a URL (`guide_tools.check_args` refuses one in any argument).
- **Look research** (`src/look_research.py`): `research_look` searches a named look and returns
  seven labelled craft lines; `set_project_look` saves it on the project on the person's click.
- **Results are numbered** (`#3`, `lib/result-numbers.ts`) so a sentence can point at one;
  tools take numbers from a closed list.
- **Explore**: a project switched to Explore only talks (no make tools at all) until the person
  switches it back.
- **Failures are said in plain words** (`src/failures.py`: "Nothing was charged.") and an empty
  balance always offers the way to add credits (`lib/out-of-credits.ts`).
- **One conversation, saved** (`assistant-thread.tsx`, `src/assistant_store.py`): the composer and
  the floating assistant are two views of one thread, kept as working memory until a scene is
  written or the person starts a new session; never archived.

### Projects

`src/projects.py`, `src/project_context.py`. `/studio/projects` is the home: one card per project.
A project holds a brief, a LOOK (`projects.look`; the studio has no house style), a memory of what
it learned, its scenes and its chat history (`project_messages`). The writer reads the brief,
look and memory through a ContextVar (`shootgen.project_brief`, `looks.look_block`). Projects are made
only through the brain (`create_project`, `save_as_project`), never a form. Deleting a project
DETACHES its scenes (never deletes them) so a rendered clip stays in the Library. A scene outside
any project opens on its own canvas at `/studio/scene/<id>`. The workspace
(`/studio/projects/<id>`) is the scene list, the Director canvas (React Flow, `FlowWorkspace`) and
the brief / look / memory panel.
A project may pick one brand kit (`src/brand_kits.py`, `/studio/brand`); in its Create thread the
settings line shows a "Kit: <name>" chip that leaves the kit off for the next still only, and
Vesper can propose kit edits (`propose_kit_change`, `src/kit_changes.py`) that change nothing
until the card's Apply.

### Scenes: writing, shots and references

- **A scene is ONE `shoot_concepts` row with ONE prompt** (`shots` is a one-element JSON list).
  `shootgen.generate_scene_concept(s)` writes it from the idea, the project, the references and
  the RAG library (`prompts/scene_brief_prompt.txt`, `scenes_prompt.txt`). The `spark` column is
  the direction only; steering text rides separately.
- **Timed shots** (`src/timeline.py`): the prompt's beats are timed windows, `(0-3s)` etc.,
  filling the scene's length (4-30s). As many shots as the idea needs; ONE only when the person
  asked for a single take. The timeline planner turns windows into `shot["timeline"]["parts"]`,
  each with its own prompt, refs (picked by number from the scene's own refs) and still/clip;
  continuity is prepended in code; staleness is checked on read (`source` hash), and a re-plan
  carries over unchanged shots' stills and clips. The scene's tail (sound, avoid list, look
  lines) belongs to every shot, not the last one.
- **References live on the shot** (`shot["refs"]`, with `ref_roles` and `ref_sources` beside it).
  Order is load-bearing: character, then prop, then location last, then first mention, because
  `refs[0]` anchors a keyframe and a clip.
- **No photographs, no render.** `preprod.reference_gate` is the one predicate: a scene written
  with no refs is a draft (the connector says `needs_reference`) and every quote and approve
  refuses it. This is the ONE place output is rejected rather than warned about.
- **Keyframes**: one still per shot (`scene_chain.keyframe_scene`), each shot's first frame, the
  previous shot's still alongside for continuity only. Drawn only on a priced approve, the whole
  strip or one shot (`POST /api/scenes/{id}/keyframes {"part": n}`).
- **Model output is advised, never rejected.** `validate_concept` and
  `timeline.shot_count_warnings` add visible warnings to a saved scene.

### Rendering, pricing and the spend gate

- **fal is the only video renderer** (`src/fal.py`, `providers.VIDEO_PROVIDERS = {"fal": fal}`):
  Kling, Veo, Seedance, LTX, Wan from one dated table (`fal.VIDEO_MODELS`: id, legal durations
  and resolutions, price per second per resolution, each re-checked against the model's schema).
  A length is fitted UP to the model's enum; an illegal choice is REFUSED, never clamped. A row
  is logged under the model that rendered it, never "fal".
- **The Render card** (`render-card.tsx`) is the only place a clip is paid for:
  `GET /api/scenes/{id}/render` is its whole state, `/quote` re-prices a changed pick, `/approve`
  renders (`app.api.approve_render`, the same body the connector's `approve` calls). Approving
  stamps `picked_at` ("rendered on purpose"). A timed scene renders shot by shot, skipping shots
  that have a clip and stopping at the first failure, so approving again resumes.
- **Draft then finish** (`src/drafts.py`): where a model's cheapest resolution is strictly cheaper,
  the card offers a draft; Finish upscales the liked take (Topaz) rather than re-rendering it.
- **Pricing** (`src/pricing.py`): `estimate()` is the provider's USD, `quote()` is credits
  (`MARKUP = "2.4"`, read through `Fraction`; `CREDIT_FLOOR = 10`), `display()` is what every card
  reads. When `QUOTE_SIGNING_SECRET` is set, a quote carries a signed token (`phq.<body>.<mac>`,
  one hour) and a billable approve without it is 400 `missing_quote`. Six refusals, in order:
  bad_signature, retired_pricing, expired, wrong_account, wrong_render, stale_content (the content
  hash is `pricing.content_hash` over the LIVE shot).
- **The ledger hold** (`src/charge.py`, `src/ledger.py`): every adapter takes the hold after the
  approval and BEFORE the submit (no credit, no HTTP call), marks `submitted()` as the last line
  before the provider call, releases on any failure, and the caller settles against the
  generations row. `accounts.credit_exempt` skips the hold (off for every account today).
- **fal's receipt is persisted at submit** (`src/fal_requests.py`), so a deploy that kills a
  polling worker leaves a render the boot sweep finishes, never an orphaned hold. fal's own "no"
  releases; no answer from fal is never a release. `cancel_job` asks fal and lets fal's answer
  decide what is charged.
- **Stills** come from Gemini (`src/nano_banana.py`) or fal's image table (`fal.IMAGE_MODELS`:
  FLUX, Seedream, GPT Image, Ideogram and others, dated, priced per still), both through the same
  hold. **Effects** are a dated table (`src/effects.py`: image edits, Kling and PixVerse template
  effects, camera moves, Topaz upscale and frame rate, MMAudio sound, reframe, background removal),
  each row's options checked and anything off-table refused. **Clip edits** by instruction
  (`src/clip_edit.py`) are two spends: one frame as a still first, then the clip.
  A **talking photo** (`src/talking_photo.py`, 2026-10-20) is two too: an optional voice
  preview (ElevenLabs v3, filed as an `asset:<id>` audio) and the clip (OmniHuman v2 on a
  photo + that voice, priced per whole second, capped per plan 30/60/120s), one body for both
  doors (`talking_photo.voice_request` / `run_voice` / `talk_request` / `run_talk`): the studio
  connector (`voice_preview`, `talking_photo`) and the composer's card (`/api/talking-photo/*`),
  page `/make/photo-to-talking-video` (its CTA opens `/studio?open=talking-photo`).
- Render provenance lives in `generated_assets` (the Library's rows) and `generations.params_json`
  (the attempt log), never in new columns on `generations`.

### Elements and media

- **Elements** (`/api/assets?scope=elements`): characters, props/products, places, each with
  photos and a vision description; creating one can draw a **reference sheet**
  (`src/element_sheet.py`, `prompts/element_sheet_*.txt`, five panels for a character) on a quoted
  still. The sheet sorts LAST: it is a derivative of the face, never evidence of it.
  `element_sheet.photo_files` is the one reader of an element's photos (disk, else the bucket).
- **Media keys are per account** (`src/media.py`, the one owner of the key scheme). The
  `PHANTRA_MEDIA` ladder is `legacy` -> `tenant` (`m/<account>/<tail>`, live) -> `signed`
  (presigned URLs, private bucket); an unknown value reads as `legacy`. Masters are under `m/`, the
  480px derivatives under `t/`, shared bin images under `m/shared/refs/`, site media under `site/`.
- **What goes on a row is a NAME, never a fetchable URL** (`asset_shelf.storable_ref`);
  `media.url_for` mints the address on read. A reader that hands bytes to a model asks
  `media.bucket_url_for(url, account_id)` and must pass the caller's account (enforced by
  `tests/test_photo_bytes_bucket.py`). `asset_shelf.parse_ref` is THE parser for a ref.
- **Known gap**: readers handed `resolve_photo` (the keyframe stage, the timeline planner, the
  writer's image refs, `fal.as_image_url`) read only this machine's disk, so on Fly a scene held
  to an element photo is drawn from its prompt alone until that is fixed.
- **Fetching an address nobody here vouched for** goes through `refbin.public_bytes`: redirects
  followed by hand, every hop a public host, no credentials in the URL, pages refused, a size cap.
- **Render names are unguessable, and `/renders` is no longer open** (2026-10-15, security
  review; `src/render_names.py`). Every writer of a file under `data/renders/` (fal clips and
  stills, Gemini stills, effects, cut exports and OTIO/SRT, the manual lane's import) appends
  `-<32 hex>` (128 random bits) to the readable stem it always wrote. The `/renders` route serves
  such a name, or a content-addressed cut file (`cut/media|audio/<sha24>`,
  `cut/preview/<sha24>/`), to whoever holds the address (a capability URL, so share_link's
  no-bucket fallback and a publisher's fetch keep working); any older, guessable name only to the
  signed-in account a `generated_assets` / `generations` / `cut_media` / `timelines` row says
  owns it, and a plain 404 to everyone else. Nothing was renamed and no row was rewritten. The
  same old guessable names still sit in R2 under `m/<account>/renders/...`: while the bucket is
  public (`tenant` rung) they stay enumerable, and closing that is Mike's call, either the
  `signed` rung (private bucket) or a migration that copies them to tokened keys and rewrites
  the rows.
- The element folders (`characters/`, `props/`, `locations/`) are shared by NAME across accounts on
  one machine; where the bucket is the store the connector never reads them
  (`asset_shelf.bucket_is_store`). BACKLOG #25 has the rest.

### Library and Renders

The Library (`/studio/assets`, `/api/media?scope=generated`) is generated content only: folders,
stars, provider filter, a clip's tile is its poster. Delete is SOFT (`deleted_at`): the row and
the file stay, so a scene using the clip keeps it, and Undo restores it. Download is a five-minute
presigned URL with an attachment disposition. "Make element" turns a still into an element;
"Effects" opens the composer's gallery on it. Renders (`/studio/renders`) lists jobs, unfinished
scenes, ready-to-cut scenes with their Finish buttons, and the operator's manual lane. It has
no rail entry since 2026-10-20 (its address, ⌘K and the Finish links reach it), and the phone's
bottom bar has no Edit (the editor has no phone layout).

**What a person does with an output is the eval signal** (`src/outcomes.py`, `output_events`):
kept (cut, export, element, reuse, continue, download, star, post), discarded (delete, regen),
edited (prompt edit). Nobody is asked to grade; `generations.kept` is derived. A new door that
makes, keeps or discards an output calls `outcomes.record`. Stats on the dev console reads
`outcomes.summary`.

### The editor (`src/cut/`, `web/src/app/studio/cut/`)

- The timeline is an OTIO-shaped document in INTEGER FRAMES (`doc.py`), media named by handles
  (`gen:<generated_assets.id>`, `asset:<cut_media.id>`), never URLs. `ops.py` holds the pure
  doc -> doc edits (a clip and its linked sound move as one); `validate.py` is the rail every doc
  passes; `render.py` compiles one ffmpeg `filter_complex` (-14 LUFS).
- Projects are versioned (`store.py`: insert-only versions, a head pointer, undo/redo); every
  edit is `POST /api/cut/projects/{id}/ops {base_id, op, args}` and is refused (409 `stale`) unless
  `base_id` is still the head. Media is probed once and cached (`cut_media_cache`).
- Features: Source viewer with In/Out and insert / overwrite / append; keyframed zoom / position
  / rotation, crop and opacity; speed and reverse; 58 xfade transition styles; a mixer (track
  gain and pan, clip fades, a volume lane); a basic grade (Color page); markers; export to MP4,
  audio, a still or OTIO + SRT.
- **The agent never edits**: every change is a proposal the person keeps or undoes, checked by
  `projects.check_ops` before it is shown. Clean-up (silences, filler words) and auto-captions
  work off the index's word timings (`src/cut/index.py`: shot logs on Gemini, Whisper only when
  speech was heard; searchable through `index.find`).
- Homebrew's ffmpeg has no libass, so the Mac does not burn captions; the Fly image's does.

### The connector and MCP servers (`src/mcp_server.py`, `app/mcp_mount.py`, `app/mcp_auth.py`)

- **Three servers.** The stdio STUDIO surface (`python -m src.mcp_server`, what Claude Desktop
  launches; `STUDIO_TOOLS`); `/mcp` for a signed-in person (`LISTED_TOOLS`, the ChatGPT listing,
  which can render: `approve`, `generate_image`, `apply_effect`); `/mcp/claude`
  (`CLAUDE_LISTED_TOOLS`, the Claude listing, which never generates media: its `quote` returns
  the studio link where the render is approved). The operator's static key
  (`PHANTRA_MCP_TOKEN`) reaches the full server as the bootstrap account.
- **Who is calling**: a Supabase OAuth access token (Supabase is the authorization server; this
  app is the resource server, `/.well-known/oauth-protected-resource`, audience
  `PHANTRA_MCP_RESOURCE` = `https://api.phantra.ai/mcp`; Supabase actually mints connector
  tokens with `aud: authenticated`, so that audience passes only with a `client_id` claim, and
  a plain studio session token is refused at /mcp). The caller reaches a tool through the
  `CALLER_ACCOUNT` / `CALLER_USER` ContextVars; the mount is stateless.
- **Every spend is two calls**: a quote with no token spends nothing; only that quote's signed,
  single-use token (`quote_redemptions`) runs it. Listed servers answer in credits only. A short
  balance is a structured refusal, never a tool error.
- **References are ids, never URLs**: `gen:<id>`, `asset:<id>`, a photo ref exactly as
  `elements` lists it. The one tool that takes a URL is `add_element` (an image or a product
  page); `upload_link` mints a one-time page for a file from a phone.
- Tools beyond making: projects and their chats, `library`, `share_link`, `reformat`,
  `trim_clip`, `assemble_clips` (free edits on a scratch cut), reading tools (`balance`,
  `search`, `whoami`, `recent`, `credit_history`, `video_models`, `recommend_model`), write tools
  (`write_scene`, `duplicate_scene`, `feedback`, `preferences`, recipes) and insights
  (`what_works`, `score_caption`). Every tool's title, description and hints are constants
  screened by a test for operator vocabulary.
- Starts: Desktop launches a stdio server twice; the dropped copy leaves without touching the
  database (`stdin_dropped`), and inits run under `db.run_init`.
- "Connect to Claude" in the account menu shows the address to paste; nothing on our side
  connects anybody. `mcp_connections` records consent and use.

### Billing and credits (`docs/BILLING.md`)

Three plans (`pricing.PLANS`), monthly and yearly (yearly is a schedule released monthly, never a
twelve-month lot), top-ups, Stripe Checkout and portal (`app/billing.py`, `src/billing.py`), grants
through `/billing/webhook` (at `https://api.phantra.ai/billing/webhook`). Renders and stills cost
credits; writing scenes and the brain's text cost none on a plan, but `charge.create_refusal`
refuses model-text routes (402 `subscribe_or_top_up`) for an account with no plan and no balance,
and a trial's model text is capped once (`pricing.trial_thinking_usd`, 402
`trial_thinking_used`). The studio shows credits, never dollars, except a plan's price
(`tests/test_studio_shows_credits.py`). `src/spend.py` meters every model call into `llm_calls`
(estimated cost; never raises); `/costs` reads it. The public `/pricing`, `/models` and `/faq` are
generated from `web/src/content/pricing.json`.

### The studio's chrome

Settings is six sections (`/studio/settings/{account,plan,usage,workspace,connections,
preferences}`, one list in `web/src/lib/settings-sections.ts`); the shell holds the one copy of
`/api/me` (`refreshMe`). ⌘K opens a palette over `GET /api/search` (projects, scenes, elements,
renders, cuts; nothing in it spends). One SSE feed drives every job wait and the activity tray,
falling back to polling. One colour palette on `:root` in `studio.css`; a new colour goes there.
Toasts carry Undo where the change is soft. Keyboard verdicts on scene lists never spend on one
keystroke.

### Still in the code, not in the product

- `src/orchestrator.py` (the LangGraph content graph, `langgraph.json` graph `orchestrator`), run
  only by hand through `python -m src.trigger`; its render step is dry unless `PHANTRA_RENDER=1`.
- Removed on purpose (2026-10-13 to 10-15, see `docs/tasks/task-remove-brand-labels.md` and step
  9 of `docs/tasks/task-higgsfield-shape.md`): the research scout, the research agent and the
  spark bank; the hold queue (a graph run returns why it stopped and writes no row); the
  per-brand channels, the uncanny judge and the inspiration feature; the Pinterest board. Their
  live tables are dropped. Do not re-add one without reading why it went.
- `src/autopilot.py`, `src/scheduling.py`, `src/instagram.py`: gated posting, off by default;
  nothing auto-posts. Instagram metrics refresh and the token keeper are live.
- The RAG library (`src/rag.py`, pgvector in the main database; `project` is the tenant slug,
  preferred, not filtered) and `post_seo` / `promote_winners` / `rework`.
- The dev console at `/studio` on the API (only with `DEV_TOOLS=1`) and the classic `/ui` shell
  (`app/templates/studio.html`, `app/static/studio/`), which hands the person to the React studio
  when `STUDIO_URL` is set.

## Conventions to preserve

- **Prompts are plain text in `prompts/`**, never strings in code. Treat `{brief}`, `{cast}`,
  `{look}`, `{spark}`, `{references}`, `{seconds}` and the other `{...}` names as the templating
  slots.
- **Prompts request, code advises.** Model output is checked against reality and every mismatch is
  a visible warning on the saved result. The reference gate is the one exception that rejects; a
  second one is almost certainly a warning instead.
- **Anything that calls a model degrades instead of breaking**: a missing key or a failed call is
  a result the caller can report, not an exception that takes down the page. A crawl or a lane
  that finds nothing says so in a line.
- **Refuse, never clamp**, a choice off a model's legal set; the person sees why.
- **Nothing spends without a price the person saw.** Every spending door shows credits and takes
  an approval; a keystroke, a plan's "Approve all" and Auto never cover a clip render.
- **A reference is traceable** to where it came from (`source_url` on bin rows, `ref_sources` on a
  shot); only http(s) is ever linked.
- **Store names, mint addresses.** Never write a fetchable URL onto a row and never hard-code a
  flat media key; ask `media.url_for` or use the `m/<account>/` key.
- **A paid output is never thrown away**: deletes are soft, project deletes detach.
- **Verify by running it.** Every real bug in this project passed review and its own tests and
  was found by starting the server, clicking the thing, or noticing the suite got slower.
- **Live data**: report first, back up, then write, and only on Mike's word. `ops/` scripts follow
  that shape.

## Where the project stands

- The rename to Phantra (2026-10-13) is done for everything a visitor, a signed-in person, an
  email and the connectors see; the remaining steps are in `docs/tasks/task-rename-to-phantra.md`
  (old app and bucket deletion, the GitHub org and Vercel project names).
  `scripts/brand-grep.sh` counts what is left; `docs/tasks/rename-allowlist.txt` lists what is
  kept on purpose, with reasons.
- The brand labels and the old brand-era data are gone (2026-10-15,
  `docs/tasks/task-remove-brand-labels.md`): no brand column, constant, cookie or route is
  left, account 1 is `phantra`, and `docs/tasks/brand-allowlist.txt` lists every mention of the
  old names kept on purpose. Backups of everything cleared or dropped are in the main checkout's
  `data/backups/brand-removal-2026-10-1{3,4,5}/` and `slug-rename-2026-10-15/`.
- Billing is live on Stripe; billed renders and the ledger hold were verified with real money on
  fal (2026-09-26). No account is credit-exempt.
- The connector is built for both directories; submissions wait on the rename and a Phantra icon
  (`docs/directory/`).
- Selection, not generation, is the bottleneck: one concept has gone all the way to a posted,
  measured video (#375). The most valuable next step is real repeated use.
- The user's real data is the live database and the R2 bucket; `data/` and the element folders
  on the Mac are gitignored. Never overwrite either without asking.
