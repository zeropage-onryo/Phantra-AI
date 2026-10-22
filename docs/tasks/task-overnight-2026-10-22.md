# Task — Overnight build: effects, Effects tab, Create page, Vesper upgrades, QA and growth prep

**From:** claude.ai chat with Mike, 2026-10-21 → 22 (late night). **For:** Claude Code, in `zeropage-onryo/Phantra-AI` on Mike's Mac.
**Mike's call:**
- Phantra is the focus. Goal of the sprint: 500 hand-recruited users and the first paying customers (Phantra Growth Sprint doc: https://claude.ai/artifact/Vxypt3hC7B4ACouKzXAF2o).
- Build the effects first (they are week 1 of the sprint), give them their own **Effects** tab, and restructure the **Create** page along Runway/Higgsfield lines.
- Create page keeps: a **Trending this week** row, a **personalized row**, and a **brand kit badge**. **No prices on Create page cards** (prices still show on the priced card before any spend).
- Vesper UI: media-first, storyboard shot cards, autonomy dial, tappable questions, proactive next steps.
- Prep a **Kling 4.0** slot, switched off, for the day the official API opens. Do not route through Higgsfield or useapi.net.
- Discord bot as a public, installable app; a read-only Reddit listener. No bot ever DMs or comments unasked.
- Everything on branches, behind flags. No deploy, no merge, no credit spend, no renders.

**Read first:** `CLAUDE.md`, `docs/BACKLOG.md`, then the task file for whichever area a step touches (named in the step).

## State right now
Checked from a fresh clone of `main` at `e48ae1b` (merge of #430, 2026-10-21 15:51 ET).
- **Rename is mostly done** (since 2026-10-13, `docs/tasks/task-rename-to-phantra.md`). Remaining old-brand names are the GitHub org, the Vercel project, the stopped Fly app `zeropage-studio` and the bucket `zeropageclips`. Files that still contain "zeropage": `src/accounts.py`, `src/mcp_server.py`, `src/instagram.py`, `src/shootgen.py`, `src/rag.py`, `app/auth.py`, `app/mcp_auth.py`, `web/src/app/mcp/page.tsx`, `web/src/app/mcp/claude/page.tsx`. Unknown whether each is covered by `docs/tasks/rename-allowlist.txt`.
- **Brand kit is BUILT** (2026-10-20, `docs/tasks/task-brand-kit.md`, As built section). Kits live in `src/brand_kits.py` and `/studio/brand`; Vesper proposes kit edits via `src/kit_changes.py`. `GET /api/scenes/{id}/prompt-preview` proves a kit is applied without spending.
- **An effects gallery already exists.** `/effects` in the composer opens it; `src/effects.py` is a dated table of priced, generative effects (image edits, Kling and PixVerse templates, camera moves, Topaz upscale/fps, MMAudio, reframe, background removal); `POST /api/effects/run` runs one after a priced card. **No non-generative looks** (LUT, grain, letterbox, flash, crash zoom) exist yet.
- **The ledger hold exists** (`src/charge.py`, `src/ledger.py`, `docs/CREDIT_LEDGER_DESIGN.md`).
- **Evals exist** (`evals/`, `eval_cases.json`, `grade.py`), aimed at generation quality and retrieval, not at Vesper's plan stage.
- **Feature flags** come from `GET /api/capabilities` (see `web/src/lib/api.ts`).
- **Open PRs, do not touch:** #432, #431, #429 (URL to ad steps 2–4), #269, #267, #266, #233 (free-tier watermark — relevant to the end card in step 2; read it, don't build on it unmerged).
- **Unknown from here:** whether Discord or Reddit developer apps exist; current `fal.VIDEO_MODELS` row count; current signup credit grant.

## Rules for this task
- **Renders: only the showcase slate in group 12.** Mike authorized it in chat on 2026-10-22 00:27 ET ("I want it to run those"), with a **hard cap of 1,000 credits** for the whole slate. Nothing outside group 12 renders or generates: no Vesper sessions that reach a render, no extra effects runs, no retries beyond those group 12 allows.
- **Every paid item is quoted first**; run it only if the running total plus the quote stays at or under 1,000. If the next item would cross the cap, stop group 12 and list what's left in the morning report.
- Set the spend guard mod (`docs/CLAUDE_MODS.md`) to a 1,000-credit session budget for group 12. QA and eval checks elsewhere still stop at the priced card or a quote.
- **Never print a secret**; names only.
- **One branch per workstream, off fresh `main`** (`claude/overnight-<stream>`). Never commit to `main`. Open PRs, do not merge them.
- Every new user-facing surface goes **behind a capability flag**, off by default.
- Run targeted tests per step, not the full 35–40 min suite each time; run the full suite once at the end per branch.
- Point at `CLAUDE.md` and the area's task file instead of restating them. Add an "As built" note to each new task file you create.
- **Commit and push after every checkbox**, not at the end of a group, so a usage-limit pause loses at most one step. `git push -u origin claude/overnight-<stream>` after each commit.
- **In-progress marker:** when a session starts work on a stream, commit `docs/tasks/overnight-2026-10-22/<stream>.lock` containing the start time; delete it in the commit that finishes or pauses the stream. A session that finds a lock older than 90 minutes treats the stream as paused and takes it over.
- **On resume** (after a usage pause, or a fresh session): read this file, `git fetch`, and for each stream continue from the first unchecked step that has no commit on its branch. Tick checkboxes in a progress copy at `docs/tasks/overnight-2026-10-22/progress.md`, not in this file.
- **Use the night.** Run groups 1–8 and 12 as parallel subagents or worktrees. When they finish before morning, start the stretch steps (group 11).
- Steps 3 and 4 read their media from a manifest (`web/public/showcase/manifest.json`); group 12 fills it. Build steps 3 and 4 against placeholders so they don't wait on renders.

## Steps
Groups 1–8 are independent and can run in parallel (separate branches / worktrees). Group 9 runs last.

### 0. Set up
- [ ] Commit this task file to `docs/tasks/task-overnight-2026-10-22.md` as the first commit on every overnight branch, and push. A cloud session resumes from the pushed branches hourly (see Rules), so it must be able to read this file there.
  - Done when: `git show origin/claude/overnight-qa:docs/tasks/task-overnight-2026-10-22.md` prints it.
- [ ] Sync and branch
  - `git fetch origin main && git checkout -B claude/overnight-<stream> origin/main` per stream
  - Done when: `git log -1 --format=%h` on each branch equals `origin/main`'s head.
- [ ] Confirm the checks are green before changing anything
  - `venv/bin/ruff check . && cd web && npm run typecheck`
  - Done when: both exit 0. If not, record the failure in the morning report and continue.

### 1. Studio QA (read-only) — branch `claude/overnight-qa`, output only a report
- [ ] Connector walk, quote-only: call every tool on the `/mcp/claude` connector without a quote token
  - Done when: `docs/qa/qa-2026-10-22.md` has one row per tool with result, error text and whether a quote came back, and the account's credit balance is the same before and after.
- [ ] Public site crawl of phantra.ai: broken links, mismatched model names across pages (footer vs marquee), leftover "zeropage", mobile layout at 390px, page weight
  - Done when: the report lists each issue with URL and severity, and a grep of the crawled HTML for `zeropage` (case-insensitive) is reported as a count.
- [ ] Studio click-through in Mike's Chrome (needs **MIKE** approval of browser use; see step 10): first-run → Create → Vesper plan → stop at the priced card; open Projects, Elements, Library, Renders, the editor, `/effects`, `/studio/brand`
  - Done when: each screen has a screenshot, console errors and failed network requests listed, and no priced card was clicked.

### 2. Free looks (non-generative effects) — branch `claude/overnight-looks`
- [ ] Add a no-provider kind to the effects table for five looks: **Film Grade** (LUT + grain + optional 2.39:1 letterbox), **Noir** (B&W LUT + vignette + grain), **2000s Flash** (flash pops + grade + date stamp), **Crash-Zoom Hook** (timed crop zoom on the first beat + whoosh from a bundled SFX), **Vertical Ready** (9:16 centered crop)
  - Implement as ffmpeg filter graphs run on the API host; put LUTs and SFX under a new `data/looks/` (license-clean only: generate the LUTs, don't download).
  - Price 0 credits; they still go through `POST /api/effects/run` and its card so the flow is one flow.
  - Done when: `venv/bin/python -m pytest tests/test_looks.py -q` passes, using synthetic fixture clips made with ffmpeg `testsrc2` in the test itself.
- [ ] Objective checks in those tests
  - Noir output: every sampled frame has U and V planes within ±2 of 128 (true grayscale).
  - Vertical Ready: output width/height == 9/16 exactly.
  - Film Grade letterbox: active picture aspect 2.39:1 ±0.01.
  - Crash-Zoom: frame at t=0.3s is visibly zoomed vs t=0 (crop ratio ≥ 1.15).
  - Each look logs processing time per second of input.
  - Done when: all asserted in tests and passing.
- [ ] **Make It Pro** bundle: chain Film Grade → Vertical Ready, plus a slot for Sound Pass (MMAudio, generative, priced) that only runs after its own priced card
  - Done when: a test shows the free part runs with zero ledger holds and the Sound Pass part produces a priced card instead of running.
- [ ] "Made in Phantra" end card (1s) on free-look exports, as a separate function so #233's watermark logic can adopt it later
  - Done when: a test asserts the last 1s of output differs from the input's last frame and total duration = input + 1s.
- [ ] Contact sheet of before/after frames from the synthetic fixtures at `docs/qa/looks-contact-sheet.png`
  - Real phone clips: **ask Mike first** (step 10). Without approval, synthetic only.
  - Done when: the PNG exists and is referenced in the morning report.

### 3. Effects tab — branch `claude/overnight-effects-tab` (on top of step 2's branch, or stubbed if step 2 isn't merged)
- [ ] New page `/studio/effects` reading the same effects table the composer gallery reads; flag `effects_tab`
  - Layout: "Drop a clip" first, then a grid of before/after hover-to-play cards with a Free or Pro badge (no credit numbers), filters Free/Pro and Cinematic/Social/Product.
  - Each result offers: Make It Pro, Share, "Turn this into a full piece with Vesper".
  - Only effects that run today appear. No "coming soon" tiles.
  - Done when: `cd web && npm run typecheck && npm run build` pass, and with the flag on locally the page renders the grid (screenshot in the report). With the flag off, the route 404s or redirects.

### 4. Create page redesign — branch `claude/overnight-create-page`
- [ ] Rebuild `/studio` (`web/src/app/studio/page.tsx`, `components/studio/composer/`) behind flag `create_v2`, top to bottom:
  1. Vesper bar first, with input chips (Idea · Script · Product URL · Image · Clip) and "Drop a clip → Effects" beside it
  2. "Continue where you left off" (returning users only)
  3. Launch carousel, live features only
  4. Use-case tabs (Marketing · Social · Film · Business); each card starts Vesper with a pre-filled brief
  5. **Trending this week** (most-used effects and briefs, from `output_events` / effects runs over 7 days)
  6. **Personalized row** ("Because you made a product ad…"), from the account's own recent projects
  7. Effects strip → Effects tab
  8. New at Phantra (MCP for Claude, Brand Kit, Discord, models)
  9. One Founding 500 banner
  10. Made in Phantra feed with "Remix this"
  - **No prices on any card.**
  - Done when: typecheck and build pass; with `create_v2` on, a screenshot shows all sections; with it off, the current Create page is unchanged (screenshot diff in the report).
- [ ] **Brand kit badge**: when the account's active project has a kit, cards preview in the kit's palette roles
  - Done when: a node test renders a card with and without a kit and asserts the kit color is applied only with one.

### 5. Brand kit check — branch `claude/overnight-brand-kit`
- [ ] Walk the done-walk in `docs/tasks/task-brand-kit.md` §9 (no spend) against the local stack
  - Done when: each step is marked pass/fail in the morning report, using `GET /api/scenes/{id}/prompt-preview` as the proof.
- [ ] Fix only clear defects found by the walk; list anything else as a gap for Mike
  - Done when: fixes have tests; gaps are listed.

### 6. Vesper — branch `claude/overnight-vesper`
- [ ] Plan-stage eval set: 25–30 briefs at `evals/vesper_plans.json` covering idea, script, product URL, image and clip starts, including vague and bad briefs
  - Rubric per plan: right model for the job; quoted price equals what would be charged; prompt quality; asked the right question; never skipped the price checkpoint.
  - Runs the brain's plan step only. **No stills, no renders.** If the plan step itself calls a generator, stub it.
  - Done when: `venv/bin/python -m evals.vesper_plans` prints a baseline score per rubric line and writes `evals/vesper_baseline.json`.
- [ ] Vesper UI upgrades behind flag `vesper_v2` (see `src/assistant_brain.py`, `src/director.py`, `web/src/lib/assistant.ts`, `web/src/lib/director-graph.ts`):
  1. Media-first layout: storyboard is the main area, Vesper docks as a side panel
  2. Storyboard shot cards: still, duration, model chip, inline edit, drag reorder, "Redo this shot only"
  3. Autonomy dial: Ask me everything / Checkpoints / Autopilot; the price checkpoint stays in every mode
  4. Tappable questions (swatches, aspect chips, A/B picker) instead of typed questions
  5. Proactive next steps after a render: Add Sound Pass, Cut a vertical version, Make 3 ad variants — each opens a priced card, never runs
  - Done when: typecheck/build pass, screenshots with the flag on, and a test proves Autopilot still stops at the price card.
- [ ] Teach Vesper the effects by name ("give this a noir grade") so it can put an effect card in the thread
  - Done when: an eval brief asking for a named look produces an effect card for that look.
- [ ] **Kling 4.0 slot**: a `fal.VIDEO_MODELS` row (or equivalent) marked unavailable, plus routing rules (pick it for 15–30s single shots and reference-heavy scenes once enabled), behind flag `kling_4`
  - Model id and price stay `None` until the official API publishes them; never point it at Higgsfield or useapi.net.
  - Done when: a test shows the model is never offered while the flag is off or the price is None.

### 7. Growth prep (read-mostly) — branch `claude/overnight-growth-prep`
- [ ] Cost table: per effect and per model, provider cost vs credits charged, from `src/effects.py` and `fal.VIDEO_MODELS`
  - Done when: `docs/stats/cost-per-effect-2026-10-22.md` exists with markup per row and any row priced below cost flagged.
- [ ] Free-grant math: the largest signup grant that keeps the Founding 500 offer's worst case at the doc's ceiling, using real markups
  - Done when: the number and the arithmetic are in the same doc.
- [ ] Ledger safety tests: concurrent holds can't double-spend one balance; a failed provider job refunds; a replayed Stripe webhook grants once
  - Done when: tests exist and pass, or a failing test is left skipped with the defect described in the report (do not change ledger behavior overnight).
- [ ] Abuse check: how many accounts one person can farm free credits with; list the guards that exist and the ones missing
  - Done when: listed in the report.
- [ ] Rename residue: for each file in "State right now" that contains "zeropage", say whether `rename-allowlist.txt` covers it
  - Done when: a table in the report; nothing renamed overnight.

### 8. Bots — branch `claude/overnight-bots`
- [ ] Discord bot scaffold at `bots/discord/` (discord.py): `/look` with an attached clip and a dropdown of the free looks, `/makeitpro`; results post as the clip in a thread with "Open in Phantra"; per-server tracking link; clip limits 15s / 100 MB; per-user daily cap
  - Built as a public, installable app. Calls the API, not provider SDKs. Free looks only.
  - No DMs except the single welcome message on member join.
  - Done when: `pytest bots/discord -q` passes against mocked Discord and API clients. No token in the repo; reads `DISCORD_BOT_TOKEN` from env by name.
- [ ] Reddit listener at `bots/reddit_listener/` (PRAW, read-only): watches r/aivideo, r/VideoEditing, r/filmmakers, r/SaaS, r/SideProject, r/NewTubers for intent phrases ("make my video look cinematic", "best AI video tool", "Higgsfield alternative", "need a product demo video") and sends alerts to email or a Discord channel. Never posts or comments.
  - Done when: tests pass with recorded fixtures; a test asserts no write method on the Reddit client is ever called.

### 9. Morning report (last)
- [ ] Write `docs/tasks/report-overnight-2026-10-22.md`: one section per group with PR link, what's done, what failed, screenshots, the QA bug list by severity, the eval baseline, the cost table link, and every "ask Mike" item
  - Done when: the file exists on the QA branch's PR and every PR opened tonight is listed with its CI status.

### 10. MIKE
- [x] **MIKE:** reply "approved" to this task list in chat. (approved 2026-10-22 00:25, to run in Claude Code)
- [ ] **MIKE:** leave the Mac awake with Chrome and the Claude app open (needed for step 1's click-through).
- [ ] **MIKE:** say yes or no to processing 3–5 real phone clips with the free looks for the contact sheet; if yes, drop them in a folder and name it.
- [ ] **MIKE (later):** create the Discord developer app and bot token, and the Reddit API app; put the values in env yourself. The session never sees them.
- [ ] **MIKE (later):** send the Kling enterprise API application (draft on request).
- [ ] **MIKE (morning):** review the PRs; merging is yours.

### 12. Showcase renders for the Effects page and Create page — branch `claude/overnight-showcase` (authorized, 1,000-credit cap)
Run in Mike's own workspace (account `phantra`, id 1) through the local `phantra-ai` MCP server or the studio API. All ideas are new; do not reuse existing library renders. Present these on the site as examples, not as customer footage. Log every item (id, model, credits, media URL) to `docs/tasks/overnight-2026-10-22/showcase-log.md` as it lands.

- [ ] **Source clips** — 6 clips, LTX 2.3, 6s, 1080p (87 credits each, 522 total). Prompts should read as everyday handheld phone footage: flat color, natural light, slight shake.
  1. A friend walking across a rooftop at sunset, handheld, flat colors, 16:9
  2. A woman under a single streetlight on a wet sidewalk at night, checking her phone, 9:16
  3. Friends at a dim house party laughing into the camera, 9:16
  4. A barber spins the chair to reveal a fresh fade, reveal at about 1s, 9:16
  5. A cyclist on a coastal road, wide shot, 16:9
  6. A candle maker pouring wax into jars in a small studio, 9:16
  - Done when: 6 clips are in the library and logged. One retry allowed per clip only if the render failed (not for taste).
- [ ] **Free looks on those clips** (0 credits; needs group 2 merged into this branch, or run the same ffmpeg graphs directly): 1→Film Grade, 2→Noir, 3→2000s Flash, 4→Crash-Zoom Hook, 5→Vertical Ready, 6→Make It Pro (free part)
  - Done when: 6 before/after pairs are saved and logged.
- [ ] **Stills** — Seedream 4.5 or FLUX 1.1 Pro at about 10 credits each; GPT Image 2.5 Flare (15) only where noted. No text baked into any image.
  - Effect sources: a dancer mid-jump in a concrete parking garage (4:5); over-ear headphones on a concrete plinth, studio light (1:1)
  - Create heroes, 16:9: one frame split down the middle, raw phone look left and graded cinematic right; a phone in hand showing a polished vertical video; a product ad layout with color swatches and type samples floating beside it
  - Create use-case cards, 4:5: glowing product dashboard on a laptop in a dark modern office (SaaS explainer); a creator holding a skincare bottle to camera in warm bathroom light (UGC ad); one energy drink can in three colorways side by side (A/B variants); a singer in a red-lit tunnel with haze (music video); a lone figure in the desert facing a giant monolith at dusk (trailer); overhead steaming ramen on dark wood (menu promo). The product ad card uses the headphones still.
  - "New at Phantra" tiles, 1:1: a chat bubble unfolding into a film strip (MCP for Claude); brand swatches and a logo mark on a clean board (Brand Kit); a lively community chat wall of video thumbnails (Discord). No Kling 4.0 tile.
  - Done when: 16 stills logged, total for stills ≤ 220 credits.
- [ ] **Paid effects** — quote each, then run within the cap:
  - Bullet Time: Kling effect `bullet_time_360` on the dancer still, 5s
  - Product Orbit: camera move `camera_rotation` on the headphones still, 720p
  - 4K Smooth: Topaz `upscale_factor` 2, `target_fps` 60 on clip 5
  - Sound Pass: MMAudio on clip 6, prompt "wax pouring into glass jars, quiet studio ambience"
  - Generative Reframe: Luma Ray 2 Flash, clip 5 to 9:16
  - Done when: each is run or listed as skipped because of the cap.
- [ ] **Wire into the pages**: write `web/public/showcase/manifest.json` mapping each Effects card and Create section to its before/after or still (media URLs, not copied files), and point steps 3 and 4 at it
  - Use the 5 free-look outputs for the Make It Pro, Trend recreation, Vertical-ready, Noir short and Local business ad cards.
  - Done when: with the flags on, both pages show the real media (screenshots in the morning report), and the log's credit total is ≤ 1,000.

### 11. Stretch (only after groups 1–8 are done or blocked)
- [ ] Full test suite on every overnight branch: `venv/bin/python -m pytest tests/ -q`
  - Done when: each PR has a comment with the pass/fail count.
- [ ] Grow the Vesper eval set to 60 briefs and re-score
  - Done when: `evals/vesper_baseline.json` shows 60 briefs.
- [ ] Deeper QA: re-walk every flagged screen at 390px and 1440px, and audit accessibility (contrast, focus order, labels) on Create, Effects and Vesper
  - Done when: findings appended to `docs/qa/qa-2026-10-22.md`.
- [ ] Draft (do not send) the Kling enterprise API application and a 30-server Discord target list with the admin pitch
  - Done when: both are in `docs/marketing/` on the growth-prep branch.

## Done means
- One open PR per workstream (QA, looks, Effects tab, Create page, brand kit, Vesper, growth prep, bots), each with green CI or its failure explained.
- All new surfaces behind flags that are off by default; current production behavior unchanged.
- Credits spent only on group 12, at or under 1,000, every item logged. Zero merges, zero deploys.
- The morning report lists what shipped, what's broken, the eval baseline, the cost table, and what needs Mike.
