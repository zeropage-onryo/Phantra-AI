# CLAUDE.md

> **PROPOSED slim replacement (drafted 2026-10-22, not in force).** The full previous text is in
> `docs/CLAUDE_HISTORY.md`, moved there verbatim section by section; the links below point into it.
> Swapping this in means copying it over `CLAUDE.md` (and, if wanted, `AGENTS.md`, which is a copy
> of the old file) -- a decision for Mike, not for a session.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
It loads into every session, so it holds only what a session needs to work safely today. **Keep it
that way:** a new decision gets a line or two here and its full write-up in a task doc
(`docs/tasks/`) or the history file, never a new essay in this file. The history is where the WHY
lives; read the linked section before changing a subsystem it covers.

## Overview

Phantra (phantra.ai; formerly Zero Page / Zeropage Studio -- the account slug `zeropage`, the Fly app
names and some identifiers still carry the old name) is a multi-user AI studio for creators,
filmmakers and agencies. A person signs in (Supabase Auth), works inside **projects** (one brief and
one memory per piece of work), holds scenes to their own **elements** (characters, props and places,
each a set of photos), and makes stills and video clips from the **composer**, where every send is a
brain (Guide) turn that either talks or proposes a priced make. Video renders only on **fal**
(`src/fal.py`) on the operator's key; every spend is quoted in **credits**, approved by the person
against a **signed quote**, and **held on the prepaid ledger before the provider is called**.
Results land in their project or on the Assets wall, `src/cut/` assembles clips into an edit, and
what a person does with an output (kept, discarded, edited) is the eval signal. The same studio is
reachable from Claude and ChatGPT through MCP (`src/mcp_server.py`). Stack: a FastAPI API (`app/`,
on Fly) over the library modules in `src/`, Postgres on Supabase, media on Cloudflare R2, and the
Next.js front end in `web/` (on Vercel, proxying `/api`, `/auth` and media to the API so the session
cookie stays first-party). Last measured state: [Where the project stands](docs/CLAUDE_HISTORY.md#verified-data-2026-09-18).

**Gone -- do not rebuild it, and do not "fix" code to match a history section that describes it:**
the nightly walk and every scheduled job except the Fly IG-token keeper; the Runway, Veo and
Higgsfield adapters and BYOK (`account_keys`); the idea board, the pick and the Queue as the place a
render is approved; the Dev Studio's Grade and Teach tabs; the prompt gate's LLM rubric and the
`PHANTRA_GATES` advisory / hard modes; post-production (ingest / pitch / editgen); the MCP board
surface and the Guide's MCP bridge (`guide_tools.TOOLS == ()`); the vanilla Gen Space;
`NANO_DAILY_CAP`. Whenever older text says a scene is picked on a board, waits in the Queue, is
approved there, or renders on Runway, it is history: today a scene is rendered from the scene, on fal.

## Backlog

Parked ideas, known bugs and next builds live in `docs/BACKLOG.md`.
Read it before proposing new work — several obvious-looking gaps are
already recorded there with the reasoning, and some already have a
script (e.g. `ops/ingest-saved-images.py` is the local-file route into
the reference bin that `bank_reference`'s URL-only signature implies is
missing).

## Claude Code mods

Three mods for how this repo is actually driven (`/ship`, `/merge`, `/wrap`,
`/handoff`, `/servers`, `/ci`, a spend guard, a CI watcher) live under
`.claude/skills/zp-*`; `docs/CLAUDE_MODS.md` says what each does, how to load
them, and what else the session logs suggested.


## Commands

All Python commands run through the project's venv, not system Python. The lines below are the
ones still current; the full original block, with the reasoning in its comments, is
[here](docs/CLAUDE_HISTORY.md#commands-original).

```bash
venv/bin/pip install -r requirements.txt
venv/bin/pip install -e .

# Web app. The product is web/ (see web/README.md); 127.0.0.1:8000/studio is the Dev Studio
# (dev posture only, no sign-in; its Grade/Teach tabs are gone), 127.0.0.1:8000 the landing.
venv/bin/uvicorn app.main:app --reload
venv/bin/python -m src.accounts seed you@example.com   # identity is Supabase Auth's

# ACCOUNT FLAGS: EXPORT DATABASE_URL FIRST. src.accounts never loads .env; with nothing exported
# it writes the LOCAL throwaway Postgres and answers "no account '<slug>'" with no list of slugs.
set -a && source .env && set +a && venv/bin/python -m src.accounts credits <slug> --on
venv/bin/python -m src.accounts operator <slug> --on   # --off to revoke
# (same shape: `edits-teach <slug> --on` -- hand edits of prompts teach the shared shelf)

# MCP: stdio, the STUDIO surface. Register with Claude Desktop only while the app is QUIT:
venv/bin/python -m src.mcp_server   # stdio; Claude Desktop launches this itself
# `open -a Terminal ops/register-claude-desktop.command`

# fal receipts / recovery of a render whose worker died (the app also sweeps on boot)
venv/bin/python -m src.fal_requests [--account N]

# The cut's index (Gemini shot log + Whisper; metered). Export DATABASE_URL first.
venv/bin/python -m src.cut.index backfill [--account <slug>] [--dry-run]
venv/bin/python -m src.cut.index one gen:85 [--force]

# Reference photos added to a folder BY HAND -> R2; then rewrite stored refs (report first)
venv/bin/python ops/backfill_reference_photos_r2.py
venv/bin/python -m ops.canonicalize_shot_refs [--account <slug>] [--write]

# The manual render lane (operator-only; a clip rendered elsewhere, filed free)
python3 ops/render_queue.py --account <slug> [--provider manual] list
python3 ops/render_queue.py --provider manual --account <slug> import \
    --concept N --shot 1 --file clip.mp4 --model "kling 3 web app" --duration 10

# The scene writer and a graph run, BY HAND -- nothing schedules either (`antihero` is no
# longer an account; `--brand zeropage` or a project's brief)
venv/bin/python -m src.shootgen [--brand antihero|zeropage] [--client ...] [--spark ...] [--count 8]
venv/bin/python -m src.shootgen --scene <concept_id>   # write THAT idea's scene prompt
venv/bin/python -c "from src import orchestrator; print(orchestrator.run('gearing up ritual'))"
venv/bin/python -m src.trigger [--spark ...] [--channel zeropage] [--scout]

# Research / scout and the metrics sweep: by hand only (their fate is step 9 of
# docs/tasks/task-higgsfield-shape.md, Mike's call)
venv/bin/python -m src.scout run  [--brand ...] [--count 4] [--lanes web,shorts,feeds,creators]
venv/bin/python -m src.scout list [--brand ...] [--unused]
venv/bin/python -m src.scout next --brand zeropage       # the servable spark, or exit 1

# Instagram tokens (`keep` is the ONE scheduled job: Fly cron, daily 10:00 ET)
venv/bin/python -m ops.ig_tokens check [--probe]
venv/bin/python -m ops.ig_tokens refresh|publish
venv/bin/python -m ops.ig_tokens keep [--days 30]
venv/bin/python -m ops.ig_tokens research --app-id <research app id>

# RAG library (pgvector)
venv/bin/python -m src.rag ingest <files...>        # (re-)build the pgvector library
venv/bin/python -m src.rag query "<text>" [--k 5]
venv/bin/python -m src.rag_eval <cases.json> [--k 5]   # hit@k + MRR over labeled cases

# Supabase auth email config (needs SUPABASE_ACCESS_TOKEN; `report` is read-only)
venv/bin/python -m ops.supabase_auth_email report
venv/bin/python -m ops.supabase_auth_email apply --templates [--smtp-host ...] [--dry-run]

# Dormant L2-L4 loop: exists, gated, off by default
venv/bin/python -m src.promote_winners propose|approve|reject|run     # winners -> proven_results shelf
venv/bin/python -m src.rework [--count 6] [--brand ...]               # evidence-grounded next slate
venv/bin/python -m src.autopilot plan|run|kill
venv/bin/python -m src.scheduling list
venv/bin/python -m src.scheduling run [--approve] [--live]
```

Billing has two more: `python -m src.pricing export` regenerates `web/src/content/pricing.json` (the
public `/pricing`, `/models`, `/faq` are built from it) and `python -m src.billing release` releases
due yearly-schedule credits. Account flags need `DATABASE_URL` exported, as above.

`src/` is an installed editable package (`pyproject.toml`) — modules use relative imports and run
via `python -m src.<module>`, not `python src/<module>.py`.

Tests run with `venv/bin/python -m pytest tests/ -q`; lint with `venv/bin/ruff check .`. Both run
in CI on every push and PR (`.github/workflows/ci.yml`).

**`tests/conftest.py` blocks all network access during tests.** This exists because the same bug
landed four times: a test monkeypatches one generator function, the route is changed to call a
different one, the patch silently misses, and a real billed API call happens while the test still
passes — the only symptom being a slower suite. If a test fails with `NetworkUseInTest`, it is
patching something the code under test no longer calls.

**The Create gate is never answered from the shared test schema (2026-10-11).**
`charge.create_refusal_code` fails open on a read error, and the routes call it with no dsn, so a
route test acting as a real account id used to get whatever the throwaway's PUBLIC schema held:
allowed on a fresh CI Postgres (no ledger tables), 402 on a machine that had run the suite before.
conftest's `create_gate_reads_its_own_schema` raises `CreateGateInTest` there instead, the same on
both. A test that hits it either stubs the function its code path calls
(`charge.create_refusal_code` for `app/api` and `app/cut_routes`; the wrapper
`charge.create_refusal` for `src/mcp_server`) or seeds the account in `pg` and sets
`DATABASE_URL` to it, where the real gate answers. `tests/test_create_gate_guard.py` holds it.

Requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) for every model-text step. Video and image renders
need `FAL_KEY`; approvals need `QUOTE_SIGNING_SECRET` (see below); sign-in needs `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `SESSION_SECRET`; R2 needs its keys (`R2_PUBLIC_BASE_URL` and the rest); Stripe's
`STRIPE_*` are optional (unset = the plan buttons say so). `.env.example` is the list. Env names were
renamed to `PHANTRA_*` on 2026-10-16 (`src/legacy_env.py` copies an old name onto its new one until the old names are gone).

## Hard invariants

Break one of these and real money, someone else's data, or a working render path is at risk. Each
links to the section that explains it.

### 1. Spending: one yes, against a price, in credits, with a signed quote

- **Nothing spends without a person's yes against a price they were shown.** Routes a person drives
  pass `approved=True` into the adapter's spend check (`spend_approved`); unattended code
  (`orchestrator.py`, `autopilot.py`) passes nothing, so it would need `*_SPEND_OK` armed on purpose
  on top of `PHANTRA_RENDER=1` and the L4 gate. Never let an unattended or remote path be what
  trips a spend, and never add a setting that leaves approval switched on.
  [Why](docs/CLAUDE_HISTORY.md#spend-gate-history)
- **`src/pricing.py` is the only code that turns a render intent into a price.** `estimate()` is the
  provider's USD, `quote()` is credits, `display()` is the JSON every card reads -- there is no JS
  price twin, and the Render card (`web/src/components/studio/render-card.tsx`) computes none.
  `MARKUP = "2.4"` is a STRING read through `Fraction` (a float there is a latent off-by-one);
  `CREDIT_FLOOR = 10`. [Why](docs/CLAUDE_HISTORY.md#src-pricing-py)
- **Signed quotes.** `pricing.sign()` / `verify()` mint `phantraq.<body>.<mac>` (HMAC, 1-hour TTL)
  under `QUOTE_SIGNING_SECRET` -- its own secret, never `SESSION_SECRET`, a different value on Fly.
  When the server can sign and the render is billable, an approve without its token is 400
  `missing_quote`. Six refusals, in order: `bad_signature / retired_pricing / expired /
  wrong_account / wrong_render / stale_content`. The content hash is `pricing.content_hash` computed
  on the LIVE shot -- never write a second one. The MCP studio tools use `pricing.sign_studio`
  (bound to the tool and a hash of its normalized arguments, single-use via `quote_redemptions`):
  a call with no `quote_token` returns the quote and spends nothing.
  [Studio surface](docs/CLAUDE_HISTORY.md#mcp-studio-surface)
- **A door that shows no price never runs a billable render**; it sends the person to the Render
  card. A plan's render step always stops for its own button -- "Approve all" and Auto never cover a
  clip (`web/src/lib/make-plan.ts` `alwaysAsks`). [Why](docs/CLAUDE_HISTORY.md#no-idea-board)
- **Model text is gated too.** A Create costs 0 credits but `charge.create_refusal` refuses it (402
  `subscribe_or_top_up`) for an account with no plan and no balance, and every route that spends
  model text asks the same thing (`api._create_gate`) -- a new one must too. The trial's thinking is
  capped once (`pricing.trial_thinking_usd()`, then 402 `trial_thinking_used`). There is no daily
  cap on model text, by Mike's call. Stills cost credits (10 Flash / 33 Pro).
  [Billing state](docs/CLAUDE_HISTORY.md#billing-state)

### 2. The ledger hold comes before the submit

- Every adapter's `generate_*` takes the hold (`src/charge.py`, `ledger.hold_for_render`) AFTER the
  spend gate and BEFORE the provider's HTTP call: `InsufficientCredit` there means no call is ever
  made; `submitted()` is the last line before the provider call; any raise after the take releases;
  the caller settles against the `generations` row. The hold sits behind the approval, not instead
  of it. Zero credits refuses even for the operator: `accounts.credit_exempt` is FALSE on every
  account (read live 2026-10-11), so `zeropage` needs a balance. The only exemptions are that
  column and the manual lane's `source` marker. [Why](docs/CLAUDE_HISTORY.md#src-pricing-py)
- **No schema init on a request path.** Ask `ledger.ensure(dsn)` (once per process and database,
  through `db.run_init`), never `ledger.init` -- two inits at once deadlock. The same goes for
  `billing._ensure`. A new process entry point wraps its inits in `db.run_init(steps, dsn)`.
  [Why](docs/CLAUDE_HISTORY.md#mcp-two-starts-init-race)
- **fal's receipt is persisted at submit** (`src/fal_requests.py`) so a restart reattaches rather
  than orphaning the hold. A render is released only on fal's own "no" (error payload, 404/410/422,
  no output, queued past the give-up time) -- never on no answer (network, 5xx, 429, no key).
  Nothing writes the ledger after the submit except settle and release.
  [Why](docs/CLAUDE_HISTORY.md#src-fal-py)

### 3. Credits, never dollars, wherever a customer looks

The studio shows credits only (`tests/test_studio_shows_credits.py` guards it). The listed MCP
servers answer in credits only (`_listed_clip`, `_listed_spend`, `_credits_only` drop dollar keys).
Provider USD appears only as detail on the operator's studio surface and in the cost tracker.
New sign-ups get a one-time trial grant (`PHANTRA_SIGNUP_CREDITS`; the code default is 100).

### 4. fal is the only video renderer

`providers.VIDEO_PROVIDERS == {"fal": fal}`. `runway.py`, `veo.py`, `higgsfield.py` and
`account_keys` are deleted -- do not bring them back; Veo lives on as the fal model `veo3.1`. A shot
still carrying `RUNWAY` / `HIGGSFIELD` as its tool is read as the fal default at render time
(`providers.platform_default`, `RETIRED_PLATFORMS`) and never rewritten. A row is logged under the
PLATFORM that rendered it (kling / ltx / wan / seedance), never "fal". fal documents no FAILED
status: a dead job answers `COMPLETED` with `error` fields, so detect failure by the fields and the
deadline. Model ids and prices in `fal.VIDEO_MODELS` are dated -- re-check before trusting one;
`fal.fit_duration` fits a length UP to a model's enum and `providers.check_render_choice` refuses an
illegal length or frame rather than clamping. Much older prose still names Runway as the renderer;
fal is what happens. [Why](docs/CLAUDE_HISTORY.md#fal-only-renderer)

### 5. No photographs, no render (the reference gate)

A scene whose shot carries no `shot["refs"]` never renders, from any door.
`preprod.reference_gate(concept)` is the single predicate; it reads `refs` and NOT
`reference_image` (a still this pipeline drew is not evidence anything grounded it), and it is
asked again at the quote and inside both approve bodies (`app.api.approve_keyframes` /
`approve_render`, which the routes and the MCP `approve` share) and by `ops/render_queue.py`. The
MCP `write_scene` may save a photo-less DRAFT (`needs_reference`); only the write loosened.
`NO_REFERENCE` is a machine reason, excluded from the rates. This is the ONE check that rejects:
everywhere else model output is checked and mismatches surface as warnings ("prompts request, code
advises"), and anything that calls a model degrades instead of raising.
[Why](docs/CLAUDE_HISTORY.md#conv-grounded-in-what-exists-and-since-2026-09-08-no),
[conventions](docs/CLAUDE_HISTORY.md#conv-prompts-request-code-advises)

### 6. Tenancy: every row has an owner or a reason to be shared

- **Every table is in `db.OWNED_TABLES` or in `db.SHARED_TABLES` with the reason it is global.**
  `tests/test_tenancy.py` fails on a table in neither list and on any `/api` route that does not
  declare `auth.current_account_id`. A new owned table gets `init` + `ensure` and goes in
  `db.OWNED_TABLES`, the app's `init_tables`, the stdio `main()` and `tests/test_tenancy.py`.
- **Routes take the tenant from the dependency**: `account_id: int =
  Depends(auth.current_account_id)`. Written as `Optional[int] = None` FastAPI reads it as a query
  parameter, every call arrives as None and matches no owned row. Pass the tenant on to every
  helper that accepts `account_id` (None there means the unowned pool). The tenant is the user's
  OLDEST membership (`min(id)`); the brand cookie is a preference, never an owner. Apply a SQL
  `LIMIT` after every filter over the same list. `conftest.account_scope` overrides the dependency,
  so a green test is not evidence of scoping -- an ownership test seeds an account.
- **The learning shelves are shared ON PURPOSE** (`winning_prompts`, the reference bin, the
  `scout_*` tables): do not "finish the migration" by scoping them; check `db.SHARED_TABLES` first.
- **MCP callers resolve to one account by the same rule.** `mcp_server._account` reads explicit
  `account_id` -> `CALLER_ACCOUNT` (the ContextVar the ASGI guard sets for a signed-in caller) ->
  bootstrap (the operator's static `PHANTRA_MCP_TOKEN` only). A verified token with no membership
  is 403, never a fall-through to Mike's account. [Why](docs/CLAUDE_HISTORY.md#mcp-two-doors-auth),
  [tenancy test](docs/CLAUDE_HISTORY.md#src-autonomy-py)

### 7. Media: store names, not URLs; never a flat R2 key

- **What goes ON a row is `asset_shelf.storable_ref(...)` -- a logical name, not a URL**; the
  fetchable string is minted on READ by `media.url_for`. Every reference bug this repo paid for came
  from storing a URL (a local route true on one machine; a signed URL true for an hour).
  `asset_shelf.parse_ref` is THE parser for a stored ref (never `split("/")` it yourself);
  `src/media.py` owns the key scheme; `storage.py` is the boto3 layer.
- **`PHANTRA_MEDIA` is a ladder**: `legacy` (flat keys) -> `tenant` (`m/<account>/<tail>`, `t/...`
  for the 480px derivative) -> `signed` (presigned, private bucket); an unknown value reads as
  `legacy`. **Never write a new flat-key URL** -- the flat keys left the bucket (seen 2026-10-07);
  ask `media.url_for` or use the `m/<account>/` key. The bin (`refs/`) is shared by decision
  (`m/shared/refs/...`); characters, props, locations and renders are fenced per account, and with
  no account a fenced read is None / 404, never the flat key and never another account's.
- **A reader that hands bytes to a model passes the caller's `account_id`** (`_photo_bytes` ->
  `media.bucket_url_for`; `tests/test_photo_bytes_bucket.py`). Writers mirror through
  `media.mirror` (one mirror; it writes the thumbnail). `refs` and `photo_thumbs` are deliberately
  separate lists: `refs` order anchors the render. Migrations COPY, never move.
  [Why](docs/CLAUDE_HISTORY.md#media-multi-tenant),
  [public URLs](docs/CLAUDE_HISTORY.md#reference-url-public),
  [listing](docs/CLAUDE_HISTORY.md#listing-bucket-fallback)

### 8. Layering and the database

- **`src/` never imports `app/`.** Web-side callables (the job registry, the approve and
  element-create bodies) are injected; `mcp_server.main()` is the one deliberate exception, as a
  process entry point. [Why](docs/CLAUDE_HISTORY.md#mcp-two-layers-transports)
- **State is Postgres** (`DATABASE_URL`, Supabase). `data/pipeline.db` is a leftover of the SQLite
  era -- do not write to it. CLIs, `src.accounts` above all, read whatever `DATABASE_URL` is
  EXPORTED and do not load `.env`.
- **Render provenance lives in `generated_assets` and `params_json`, never in new columns on
  `generations`** (the attempt log). [Why](docs/CLAUDE_HISTORY.md#conv-render-provenance-lives-in-generated-assets-and)
- **Prompts and the brand brief are plain text in `prompts/`**, not hardcoded strings.
- A new door that makes, keeps or discards an output calls `outcomes.record` (the one writer of the
  OWNED `output_events`; it never raises). [Why](docs/CLAUDE_HISTORY.md#outcomes-eval-signal)

### 9. MCP: what each surface may do

Three servers, one tool registry (`src/mcp_server.py`, mounted by `app/mcp_mount.py` when
`PHANTRA_MCP=1` and `PHANTRA_MCP_TOKEN` is set -- no token means refused, never served open):

- **STUDIO** (`STUDIO_TOOLS`; stdio, the default Claude Desktop launches, and the operator's key
  over HTTP, there without `import_file`): makes things WITH Claude -- `generate_image`,
  `generate_video`, `apply_effect`, `element_sheet`, `edit_clip`, each quoted first in credits and
  run only on that quote's signed single-use token; plus `cancel_job`, `assemble_clips`,
  `import_file` (stdio only), the model / effect / element / render readers and the project tools.
  Never board tools.
- **LISTED `/mcp`** (`LISTED_TOOLS`, a signed-in person; the ChatGPT listing): the person's own
  projects, `elements`, `add_element`, `write_scene` / `quote` / `approve` / `job`, `image_models` /
  `generate_image`, the reading, write and insight tools. Credits only, no server paths, never the
  engine tools, never the shared spark bank or its counts.
- **LISTED `/mcp/claude`** (`CLAUDE_LISTED_TOOLS`): the same minus `approve`, `job`, `image_models`
  and `generate_image` -- Anthropic's directory refuses AI media generation, so its `quote` returns
  an `approve_url` into the studio's Render card instead. No other spending door is listed.
- Neither listing has `save_chat`. A caller error is raised as a `ToolError` with a message (the SDK
  hides any other exception, and an agent that cannot tell a bad id from a broken server retries the
  identical call). Tool titles and descriptions are constants
  screened by a test. [Listed](docs/CLAUDE_HISTORY.md#mcp-two-listed-servers),
  [studio](docs/CLAUDE_HISTORY.md#mcp-studio-surface),
  [auth](docs/CLAUDE_HISTORY.md#mcp-listed-server),
  [registering](docs/CLAUDE_HISTORY.md#commands-original)

### 10. Verify by running it

Every real bug here passed review and its own tests; each was found by starting the server,
clicking the thing, or noticing the suite got slower. Verify against the running app (and the live
database where it matters), not by reading. [Why](docs/CLAUDE_HISTORY.md#conv-verify-by-running-it-not-by-reading-it)

## Module map

One line each; the history has the detail.

**Web (`app/`)**
- `app/main.py` -- the FastAPI app, lifespan inits (`init_tables` via `db.run_init`), photo routes and their R2 fallback, the Dev Studio. [History](docs/CLAUDE_HISTORY.md#app-main-py)
- `app/api.py` -- the JSON API the React studio calls: composer, scenes, render/quote/approve, elements, media, the create gate. [History](docs/CLAUDE_HISTORY.md#app-api-py-ui)
- `app/auth.py` -- Supabase Auth sign-in, the `zp_session` cookie, `current_account_id`, the cross-site handoff. [History](docs/CLAUDE_HISTORY.md#sign-in)
- `app/billing.py` -- Stripe's HTTP half (`/billing/webhook`); `app/cut_routes.py` -- `/api/cut`; `app/publish_routes.py` -- the publish review page.
- `app/mcp_mount.py` + `app/mcp_auth.py` + `app/oauth_consent.py` -- the MCP mount, its two doors, and the OAuth consent page.
- `app/jobs.py` -- the in-process job registry (stdlib only; injected into `src/`); `app/seo.py` -- robots, llms.txt, sitemap, JSON-LD; `app/upload_page.py` -- the one-time upload page.

**Making things (`src/`)**
- `shootgen.py` -- the scene writer over the active project's brief. [History](docs/CLAUDE_HISTORY.md#src-shootgen-py)
- `scene_chain.py` -- a scene's stages as functions (attach refs, plan timeline, keyframes, render). [History](docs/CLAUDE_HISTORY.md#parked-marker-imagery)
- `timeline.py` -- a scene's timed windows as separately rendered shots. [History](docs/CLAUDE_HISTORY.md#timed-shots)
- `preprod.py` -- `shoot_concepts` (a concept is ONE scene, ONE prompt), `reference_gate`, archive. [History](docs/CLAUDE_HISTORY.md#one-scene-one-prompt)
- `orchestrator.py` -- the LangGraph content graph, run by hand (`src.trigger`); `autonomy.py` -- hold queue, kill switch. [History](docs/CLAUDE_HISTORY.md#src-orchestrator-py)
- `fal.py` / `fal_requests.py` / `providers.py` -- the one renderer, its persisted receipts, the one-entry registry. [History](docs/CLAUDE_HISTORY.md#src-fal-py)
- `nano_banana.py` / `midjourney.py` / `refgen.py` -- stills and generated references. `effects.py` -- fal edits, template effects, camera moves, upscale, sound. `clip_edit.py` -- a clip changed by instruction, one frame first.
- `imagery.py` -- stored reference -> bytes a model can see. `prompts_for.py` -- per-model prompt shaping (off unless `PHANTRA_PROMPT_DIALECTS=1`). `shot.py` / `promptgen.py` / `genlog.py` / `generative.py` -- the shot dataclass, prompt renderers, generation attempts.
- `render_assets.py` -- the Assets wall's records; `outcomes.py` -- output events, the eval signal. [History](docs/CLAUDE_HISTORY.md#outcomes-eval-signal)
- `cut/` -- the editor: OTIO-shaped timeline doc, pure edits, validation, render, index, the editing agent. [History](docs/CLAUDE_HISTORY.md#src-cut)

**The brain and the studio**
- `assistant_brain.py` / `guide_tools.py` / `skills.py` / `make_plan.py` / `drafts.py` -- the composer's brain, its tools, skill shelf, step-by-step plans, draft-then-finish. [History](docs/CLAUDE_HISTORY.md#the-brain-is-the-composer-and-it-makes)
- `projects.py` / `project_context.py` / `creative_projects.py` -- projects, their brief and memory. [History](docs/CLAUDE_HISTORY.md#src-projects-py)
- `looks.py` / `look_research.py` / `ref_roles.py` / `result_refs.py` / `model_menu.py` / `failures.py` -- looks, reference roles, numbered results, model proposals, render failures in a customer's words.
- `search.py` -- the ⌘K global search; `credit_history.py` -- the ledger as lines a person reads.

**References and media**
- `asset_shelf.py` -- elements as retrievable text, `parse_ref`, `storable_ref`, bucket listings. `media.py` -- the key scheme and read-time mint. `storage.py` -- R2 (boto3). [History](docs/CLAUDE_HISTORY.md#media-multi-tenant)
- `refbin.py` -- `data/refs`, content-addressed names, JPEG normalisation, safe fetch. [History](docs/CLAUDE_HISTORY.md#src-refbin-py)
- `linkrefs.py` -- a pasted link becomes a reference frame. [History](docs/CLAUDE_HISTORY.md#src-linkrefs-py)
- `element_sheet.py` / `entities.py` / `locations.py` -- element reference sheets, characters and props, described rooms (optional material).

**Money**
- `pricing.py` -- the only price, the signed quote, the plans. `charge.py` -- one render's hold. `ledger.py` -- the prepaid ledger. `billing.py` -- Stripe in front of the ledger, yearly schedules. `quote_redemptions.py` -- single-use studio quotes. [History](docs/CLAUDE_HISTORY.md#src-pricing-py)
- `spend.py` / `costs.py` -- the LLM meter (never raises; unpriced is NULL, not $0) and `/costs`. [History](docs/CLAUDE_HISTORY.md#src-spend-py)

**Accounts, MCP, data**
- `accounts.py` -- users, accounts, membership, the account-flag CLI. `edit_teach.py` / `manual_lane.py` -- per-account column gates that fail closed.
- `mcp_server.py` (+ `mcp_shapes.py`, `mcp_recipes.py`, `mcp_preferences.py`, `mcp_feedback.py`, `mcp_connections.py`, `upload_links.py`, `model_pick.py`) -- the MCP surface. [History](docs/CLAUDE_HISTORY.md#src-mcp-server-py)
- `db.py` -- the schema spine, `OWNED_TABLES` / `SHARED_TABLES`, `run_init`.
- `rag.py` / `rag_eval.py` / `crag.py` / `winners.py` -- the pgvector library, its eval, retrieval grading, the prompt shelves. [History](docs/CLAUDE_HISTORY.md#src-rag-py)
- `scout.py` / `research_agent.py` / `story_judge.py` -- research, by hand only, fate pending. [History](docs/CLAUDE_HISTORY.md#src-scout-py)
- `instagram.py` / `tiktok.py` / `youtube.py` / `scheduling.py` / `publish_review.py` / `post_seo.py` / `refresh_metrics.py` -- distribution and its metrics. `promote_winners.py` / `rework.py` / `autopilot.py` -- the L2-L4 loop (dormant, off).
- `gemini_utils.py` -- `generate_with_retry` with model fallback (where the meter lives).

`web/` is the Next.js studio and landing page (React Flow canvas, Render card, Elements, Assets,
Renders, Settings); `web/README.md` has the deploy recipe. `ops/` holds one-off and repair scripts
(report first, `--write` to act). `docs/BACKLOG.md`, `docs/BILLING.md`, `docs/RUNBOOK.md`,
`docs/CUT_EDITOR.md` and `docs/tasks/*.md` (read a task doc's "As built" before touching its code)
are the deeper references.

## For the history of ...

All in `docs/CLAUDE_HISTORY.md`:
- the original overview -> [#overview-original](docs/CLAUDE_HISTORY.md#overview-original)
- sign-in, passwords, the session handoff -> [#sign-in](docs/CLAUDE_HISTORY.md#sign-in)
- why there is no board and no pick -> [#no-idea-board](docs/CLAUDE_HISTORY.md#no-idea-board); Grade/Teach removal -> [#grade-teach-gone](docs/CLAUDE_HISTORY.md#grade-teach-gone); the rubric -> [#prompt-gate-rubric-gone](docs/CLAUDE_HISTORY.md#prompt-gate-rubric-gone), [#gates-inverted](docs/CLAUDE_HISTORY.md#gates-inverted)
- prompts that learn, presets, dialects -> [#prompts-that-learn](docs/CLAUDE_HISTORY.md#prompts-that-learn); hand edits teaching -> [#hand-edit-teaches](docs/CLAUDE_HISTORY.md#hand-edit-teaches)
- the nightly walk and the night -> [#the-night](docs/CLAUDE_HISTORY.md#the-night), [#night-no-longer-draws](docs/CLAUDE_HISTORY.md#night-no-longer-draws)
- the old Queue and the click-is-the-approval decision -> [#spend-gate-history](docs/CLAUDE_HISTORY.md#spend-gate-history)
- the deleted Veo adapter -> [#src-veo-py](docs/CLAUDE_HISTORY.md#src-veo-py)
- references being attached at all -> [#references-attached](docs/CLAUDE_HISTORY.md#references-attached); `.heic` -> [#heic](docs/CLAUDE_HISTORY.md#heic)
- the Director canvas and its saved state -> [#the-director-canvas-is-the-gen-space](docs/CLAUDE_HISTORY.md#the-director-canvas-is-the-gen-space), [#canvas-outlives-visit](docs/CLAUDE_HISTORY.md#canvas-outlives-visit)
- `web/` vs `frontend/`, Vercel -> [#web-is-the-react-front-end-frontend-is-its](docs/CLAUDE_HISTORY.md#web-is-the-react-front-end-frontend-is-its)
- Assets vs Elements -> [#assets-and-elements-are-two-things-not-four](docs/CLAUDE_HISTORY.md#assets-and-elements-are-two-things-not-four); the projects board -> [#one-projects-board](docs/CLAUDE_HISTORY.md#one-projects-board); Settings -> [#settings-is-an-area-of-six-sections](docs/CLAUDE_HISTORY.md#settings-is-an-area-of-six-sections)
- the MCP desktop double-launch and init deadlock -> [#mcp-two-starts-init-race](docs/CLAUDE_HISTORY.md#mcp-two-starts-init-race); add_element, uploads, the library -> [#mcp-add-element](docs/CLAUDE_HISTORY.md#mcp-add-element), [#mcp-upload-page](docs/CLAUDE_HISTORY.md#mcp-upload-page), [#mcp-library-free-edits](docs/CLAUDE_HISTORY.md#mcp-library-free-edits)
- the composer and the brain's features (plans, effects, drafts, looks, numbered results, explore mode, one conversation) -> [#the-composer-is-drawn-to-the-phantra-composer](docs/CLAUDE_HISTORY.md#the-composer-is-drawn-to-the-phantra-composer) and the sections after it in the contents
- the feedback loop, auto-posting, Instagram research lane -> [#the-feedback-loop-and-where-it-was-broken](docs/CLAUDE_HISTORY.md#the-feedback-loop-and-where-it-was-broken), [#nothing-auto-posts-right-now](docs/CLAUDE_HISTORY.md#nothing-auto-posts-right-now), [#the-instagram-research-lane](docs/CLAUDE_HISTORY.md#the-instagram-research-lane)
- the first closed loop and first billed renders -> [#loop-closed-first-renders](docs/CLAUDE_HISTORY.md#loop-closed-first-renders); known gaps (incl. the local Homebrew Postgres for RAG) -> [#known-gaps](docs/CLAUDE_HISTORY.md#known-gaps)
