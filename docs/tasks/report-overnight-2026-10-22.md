# Overnight 2026-10-22 — morning report

**Task:** `docs/tasks/task-overnight-2026-10-22.md` (Mike pasted it at 00:50 ET; it was never in the repo before, so it is the first commit on every overnight branch). **Base:** `main` at `e48ae1b3`. **Run:** 00:55 to 04:00 ET, nine streams in parallel as subagents, each in its own worktree and branch, then the group 11 stretch steps.

## The short version

- **Nine PRs open, none merged, nothing deployed.** #434 bots, #435 growth prep, #436 Effects tab, #437 brand kit, #438 QA, #439 free looks, #440 Create v2, #441 showcase, #442 Vesper.
- **Every new surface is behind a flag, off by default:** `free_looks` (`PHANTRA_FREE_LOOKS`), `effects_tab` (`PHANTRA_EFFECTS_TAB`), `create_v2` (`PHANTRA_CREATE_V2`), `vesper_v2` (`PHANTRA_VESPER_V2`), `kling_4` (`PHANTRA_KLING_4`).
- **Credits: 542 of the 1,000 cap spent, all in group 12.** Balance 7,527 → 6,985, equal to the log's charged column, no dangling holds. Six source clips rendered; every still and paid effect was refused by a daily cap on the Desktop-launched MCP server (see group 12) and is waiting on you.
- **GitHub CI is red on every PR for a billing reason, not the code.** Every `test` and `web` job since 2026-10-21 19:30 UTC fails at start with "The job was not started because recent account payments have failed or your spending limit needs to be increased" (the job has zero steps and no log; PR #432 from yesterday shows the same). The local full suite stands in and is green on all nine branches (table at the end; each PR has the count as a comment).
- **Mike's calls** are collected in the last section: 30 items, grouped.

## What each stream did

### Group 1 — Studio QA (read-only) — [PR #438](https://github.com/zeropage-onryo/Phantra-AI/pull/438)
Report: `docs/qa/qa-2026-10-22.md` (+ the stretch section), crawler `docs/qa/crawl-2026-10-22.py`, screenshots `docs/qa/screens-2026-10-22/` (6 site at 390 px, 14 studio, 24 stretch).
- **Connector walk, quote only:** all 33 `/mcp/claude` tools called, `quote` without a token. Balance 343 → 343. Finding: the connector in this Claude Code session acts in **workspace 5 "Phantra Review"** (zp-billing-test), not `phantra`; the test rows it wrote there are listed for deletion (project 3, scenes 433/434, prop "QA 2026-10-22 test prop (delete me)", gen:159 + cut `fcd7ca15-…`, recipe `qa-2026-10-22-test`, feedback 7). Bugs: a 16-call burst trips rate limiting with a transport-level error; `quote` prices a soft-deleted scene; a 4 s scene is priced at 6 s with no fit-up note.
- **Site crawl:** 45 pages, 0 broken internal links; 24 of 26 external links answer 403 to scripts (bot protection; hand-check). "zeropage" in HTML: 13, all the GitHub org URL, 0 in visible text. Model-name mismatches: the hero reel labels a clip "Runway Gen-4 Turbo" (`web/src/content/hero-reel.ts:45`) and "Seedance 2 Fast"; the home strip, `/make/ugc-ads` and `/make/music-video` say "Kling 3", "Kling 3.0", "FLUX.2", "GPT Image 2" against the footer's tier names. Weight: home declares 12.8 MB of media (29 files); `/make/photo-to-talking-video` 11.4 MB (one 9.45 MB MP4). No horizontal overflow at 390 px on home, pricing, models, a make page, connector.
- **Click-through** on a local stack (live database, minted handoff token, **Mike's Chrome not used**): Create → `/effects` → one Vesper brief → stopped at "Start / Approve all · 33 credits" → Projects, Elements, Library, Renders, editor, Brand. No priced card clicked; balance 6,985 → 6,985. Findings: Vesper applied the Gygler kit to a "plain white mug" brief without saying so; the floating assistant and its pending "2 frames picked" card cover content on every page at 1280×800; two kit-asset 404s on kits the brand-kit stream made (files on this Mac only). One turn was appended to account 1's live Create thread.
- **Deeper QA (stretch):** local merge of looks + Effects tab + Create v2 + Vesper v2, all flags on, throwaway schema, keys blank. **23 findings: 0 blocker, 8 major, 9 minor, 6 cosmetic.** Top: `/showcase/manifest.json` 404s on every Create v2 / Effects load because the root `.gitignore` ignores `manifest.json` (#441 adds the exception: merge it with or before #440 and #436); Elements at 390 px forces a 752 px viewport (`.elcover` grid, on main); on a phone Create v2 + Vesper v2 opens on the storyboard with the box ~1,700 px down, and the creature + chips cover content; no visible focus indicator on the Effects cards (#436) and the composer textarea (main); white-on-yellow at 1.16:1 on `.elnew` (main) and the Founding CTA (#440); `role=list` with non-listitem children (axe critical); Effects card by keyboard keeps focus on the grid and Escape does not close; the autonomy dial has no arrow keys; drag-only reorder; hover-to-play ignores reduced motion; small-text contrast 2.5–2.7:1 (main); no `<main>`/h1.
- Not verified: deep links by hand, Director canvas, scene pages, Settings, talking-photo card, screen reader/Safari/real phone, production.

### Group 2 — Free looks — [PR #439](https://github.com/zeropage-onryo/Phantra-AI/pull/439)
`src/free_looks.py` (+ `src/looks_assets.py`; **not** `src/looks.py`, which is the existing project-look module and was restored byte-for-byte after an early overwrite). Rows in `effects.EFFECTS`: `film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`, bundle `make_it_pro`; provider `local`, `free: True`, 0 credits, category `look`, tags Cinematic/Social/Product. One flow: the gallery, `/api/effects/quote|run` (0 credits, 409 at any other price), the connector's `apply_effect` quotes 0. `tests/test_looks.py`: noir U/V 128±2, 9/16 exact, letterbox 2.39±0.01, zoom ≥1.15 (from params and measured), timing per input second logged. `make_it_pro`: the free part takes zero holds (hold/fal patched to fail), Sound Pass comes back as a priced `add-sound` card in the job result's `next`. End card: `append_end_card`, +1 s, last second differs. Contact sheet `docs/qa/looks-contact-sheet.png` (synthetic only; `ops/looks_contact_sheet.py --clip` for real clips once you say yes). Degraded: the Mac's ffmpeg has no `drawtext`, so the date stamp and end-card words are Pillow PNG overlays; `data/looks/` assets are regenerated on first use. As built: `docs/tasks/task-free-looks.md`.

### Group 3 — Effects tab — [PR #436](https://github.com/zeropage-onryo/Phantra-AI/pull/436)
`/studio/effects` behind `effects_tab`: server page 404s with the flag off or no session; rail entry only with it on. Drop zone (clip → `/api/cut/media`, still → `/api/refs/upload`, or a Library pick), before/after hover-to-play cards with Free/Pro badge and no credit numbers, Free/Pro + Cinematic/Social/Product filters, a click opens the composer's own EffectStep card (price there, Approve is the only spend), results offer Make It Pro / Share+Download / "Turn this into a full piece with Vesper". `GET /api/effects` now carries `free` and `tags`. Showcase contract: `web/public/showcase/manifest.json` v1 + `web/src/lib/showcase.ts`. Verified: typecheck, build, 263 node tests, local run on a throwaway schema with screenshots (`effects-tab*.png`), flag-off 404 by curl. Not done: ⌘K row; the Vesper hand-off attaches a still only; signed-out visitor gets a 404 rather than the sign-in shell. As built: `docs/tasks/task-effects-tab.md`.

### Group 4 — Create page v2 — [PR #440](https://github.com/zeropage-onryo/Phantra-AI/pull/440)
`/studio` behind `create_v2`: one `caps.create_v2 ? <CreateV2/> : null` branch; flag off = current page, no v2 node in the DOM (`create-v1.png`). Ten sections in order; a node test renders every card with a priced effect and asserts no price text (the Founding banner's grant number is the one allowed "credits"). `GET /api/trending` + `src/trending.py` is **per-account only** (the tenancy SQL audit forbids a cross-account read). Kit badge: card-scoped CSS vars + "Kit: <name>" only when the composer's project has a kit, tested with and without. Verified by Playwright on a throwaway schema: zero POSTs to any run/approve route; two defects found by running it and fixed (2,570 px-wide grid at 390 px; invisible Remix button on kit cards). Screens `create-v2.png`, `create-v2-nokit.png`, `create-v2-390.png`. Placeholders: `FOUNDING_500` numbers in `web/src/lib/create-v2.ts`, `DISCORD_INVITE_URL` empty. **Deviation:** the agent unpacked `react-resizable-panels@4.14.1` (lockfile-checked tarball) into the **main checkout's** `web/node_modules` as one new directory before my note reached it; additive, remove if you like. As built: `docs/tasks/task-create-page-v2.md`.

### Group 5 — Brand kit walk — [PR #437](https://github.com/zeropage-onryo/Phantra-AI/pull/437)
§9 of `task-brand-kit.md`: **all five steps pass** (API on the live database with provider keys and R2 blanked; proof by `prompt-preview` on scene 435 with kit A, kit B, none, plus three local exports with kit cards). One defect fixed: the kit page's caption preview said "Book Gygs in seconds." on every kit (`captionSample()` in `web/src/lib/brand-kit.ts`, tested). 139 brand/kit tests pass. Walk table: `docs/qa/brand-kit-walk-2026-10-22.md`, 15 screenshots. Gaps for you: two live kits both named "Gygler" (ids 1 and 2) are indistinguishable in the picker; the floating creature covers the Kit chip and the kit select below ~1,000 px. QA rows to delete in workspace `phantra`: kits 4 and 5, project 5, scene 435, cut `44320fc0-ad3f-45a3-a7f2-7fa2e119962d`, bin `asset:33`, three exports (their files exist only on this Mac, so production shows two QA kits with missing thumbnails until then).

### Group 6 — Vesper — [PR #442](https://github.com/zeropage-onryo/Phantra-AI/pull/442)
- **Plan-stage evals:** `evals/vesper_plans.json` (now **60 briefs**, stretch step), `evals/vesper_plans.py` (plan step only, every generator stubbed with hit recording), `evals/VESPER_PLANS.md`. Baselines (one pass each, gemini-3-flash-preview, 0 stub hits, nothing rendered):

  | rubric line | 30 briefs | 60 briefs |
  |---|---|---|
  | right model | 0.57 (4/7) | 0.73 (11/15) |
  | quoted price = charge | 1.00 | 1.00 |
  | prompt quality | 1.00 | 1.00 |
  | asked the right question | 0.79 (23/29) | 0.82 (47/57) |
  | never skipped the price checkpoint | 0.97 (29/30) | 0.98 (59/60) |

  Top misses: asks instead of making on 8 of 10 question misses (phone-typed and bare "make N say…" asks); people/reference routing (3 characters → LTX 2.5 Pro; a 20 s single take left on the 10 s LTX 2.3 default); the poster-with-words brief picked GPT Image 2.5 Sunburst; says nothing about what it changed (off-table model swapped silently, no "needs a photo" line, no Render-card pointer); talking photo by number ("I don't see a first image").
- **`vesper_v2` UI:** media-first layout, storyboard shot cards (inline edit, view-only drag reorder, "Redo this shot only" opens the priced Render card), autonomy dial (never maps to Auto; paid steps always stop; `make_plan.runs_unasked` is False for every paid step), tappable questions (`ask_choice` tool, `prompts/creative_guide_questions.txt`), next steps after a render as priced cards. Screens `vesper-v2-01..06`. The next-steps row is node-tested only (needs a rendered scene).
- **Effects by name:** `src/effect_names.py` aliases resolved in `guide_tools._check_effect`; the eval brief "noir grade" produced the `noir` card live.
- **Kling 4.0 slot:** `fal.SLOTS["kling4"]` with ids and prices `None`, joins the table only with `PHANTRA_KLING_4=1` **and** ids **and** prices; routing rules (15–30 s single shot, 3+ refs) in `model_menu`, `guide_tools`, `model_pick`; a grep test asserts no reseller. As built: `docs/tasks/task-vesper-v2.md`.
- Hygiene: the pre-existing local-only failure `tests/test_mcp_server.py::test_main_serves_the_studio_whatever_an_old_config_asks` prints `os.environ` including a signing secret when it fails.

### Group 7 — Growth prep — [PR #435](https://github.com/zeropage-onryo/Phantra-AI/pull/435)
- **Cost table** `docs/stats/cost-per-effect-2026-10-22.md` (regenerate with `venv/bin/python -m ops.cost_table --write`): every effect, video model (per resolution), image model, Gemini still, talking photo. No row below cost; five sit on the 10-credit floor (add-sound, remove-background, seedream-edit, flux2-pro, a 50-character voice preview).
- **Free-grant math** (same doc): Founding 500 worst month = 310,000 credits = $3,100 retail / $1,291.67 provider at `MARKUP` 2.4. Largest signup grant at the $3,100 ceiling: **300 credits if the ceiling is retail** (the doc's number, zero headroom) or **1,168 if it is provider money**; the default `PHANTRA_SIGNUP_CREDITS=100` gives $2,100 / $875. Outside the arithmetic: ~$1 of Gemini text per trial account (up to $500), and share bonuses and prizes are not in code.
- **Ledger safety tests** `tests/test_ledger_safety.py`: 9 pass (four concurrent holds, one wins and the balance never goes negative; a failed fal submit restores the balance; a replayed Stripe webhook, racing deliveries and a re-sent event id all grant once). No defect found, nothing skipped, no behaviour changed.
- **Abuse check** `docs/stats/free-credit-abuse-2026-10-22.md`: one person can farm as many trials as they have emails or Discord accounts, about five a minute per IP; 9 guards cited by file and line, 10 missing with one-line fixes. The per-IP brake keys on a forgeable `X-Forwarded-For` (uvicorn runs with `--forwarded-allow-ips='*'`, `ops/fly/supervisord.conf:18`); no email normalisation (gmail dots and plus tags); no disposable-domain block. Supabase dashboard posture (email confirmation, captcha) not verified.
- **Rename residue** `docs/stats/rename-residue-2026-10-22.md`: 18 lines in the nine files; 9 allowlisted, 9 still printed by `brand-grep.sh`, 3 with lapsed reasons. Nothing renamed.
- **Stretch drafts** (not sent): `docs/marketing/kling-enterprise-api-application-2026-10-22.md` (Kling's own October post lists the 4.0 API for enterprise as "coming soon"; the portal is JS-rendered so its real fields could not be read; `[MIKE: …]` marks every field to fill) and `docs/marketing/discord-target-servers-2026-10-22.md` (30 servers ranked by fit, 17 with verified invite URLs, 9 bot-list pages unverified, a "looked for, not found" list, and a sub-150-word admin pitch).

### Group 8 — Bots — [PR #434](https://github.com/zeropage-onryo/Phantra-AI/pull/434)
`bots/discord/` (discord.py, imported lazily): `/look` with a clip attachment and an autocomplete of the free looks (read from `GET /api/effects` at runtime, kept only when free and on the allowlist), `/makeitpro`; the flow checks the daily cap, 100 MB, 15 s by ffprobe, uploads through `/api/cut/media`, quotes through `/api/effects/quote` (anything above 0 is refused, never run), runs, polls `/api/jobs/<id>`, posts the clip in a thread with "Open in Phantra" carrying `?src=discord&server=<guild id>&look=<id>`. Per-user daily cap in SQLite; the only DM is one welcome on member join, flagged. Public installable app (README has scopes, intents, install URL shape). `bots/reddit_listener/` (PRAW behind a sealed read-only facade; six subreddits; de-dup; alerts to a webhook, SMTP or stdout); a test runs a full cycle over a mock and asserts no write method (40 names) was ever called. `pytest bots -q`: 111 passed, 1 skipped (discord.py not in the venv; `bots/requirements.txt` pins it; nothing was installed into the shared venv). Not verified: neither bot ran against Discord, Reddit or the live API. As built: `docs/tasks/task-bots.md`. **Design gap:** `/api` is gated by the `phantra_session` cookie only, so the bot's `PHANTRA_BOT_API_KEY` must today be a minted session value for a bot workspace; the right fix is a service-key bearer door on `/api`, not built overnight.

### Group 12 — Showcase renders (the only spend) — [PR #441](https://github.com/zeropage-onryo/Phantra-AI/pull/441)
Log: `docs/tasks/overnight-2026-10-22/showcase-log.md`, every item quoted first. Project "Showcase 2026-10-22" (id 4) in workspace `phantra`.

| item | credits | result |
|---|---|---|
| 6 source clips, LTX 2.3, 6 s, 1080p | 522 | gen:162 rooftop 16:9, gen:161 streetlight, gen:163 party, gen:165 barber, gen:167 cyclist 16:9, gen:166 candle maker (all 6.12 s, verified by ffprobe) |
| 2 FLUX 16:9 start frames | 20 | gen:160, gen:164. Needed because the studio MCP's text-to-video is always 9:16 (`fal.DEFAULT_ASPECT`; `run_video` passes no aspect), so the 16:9 clips had to be image-to-video. Not a listed item; flagged in the log. |
| 13 stills (quoted 10 each) | 0 | **refused:** "daily cap: 6/6 images generated today" |
| Bullet Time (68), Product Orbit (48) | 0 | not runnable, their source stills were never drawn |
| 4K Smooth (236) | 0 | held: fits the cap but would have starved the stills |
| Sound Pass (10) | 0 | failed before any fal call on the Supabase pooler ("max clients reached", pool 15); not retried |
| Generative Reframe (89) | 0 | refused by the same daily cap |
| **Total** | **542** | balance 7,527 → 6,985, no dangling holds, 458 unspent |

Why the cap: the `phantra-ai` MCP server this session launches runs from the **main checkout, which is on `claude/element-sheet-is-the-element` at `6a9d8d57`**, whose older `src/fal.py` defaults `FAL_DAILY_CAP` to 6 (main: 200), and the image and effect doors read the same counter. I did not open a second door around it (the auto-mode classifier refused that twice, and it is your call anyway). **Free looks** ran with the real module on the six clips (no provider call): `asset:46-51` (7.12 s with the end card), posters `asset:52-57`; an earlier ffmpeg fallback pass (`asset:34-45`) sits unused in the library. Manifest `web/public/showcase/manifest.json` v2: six `look.*` items, the `cards` mapping, `sources`, and `pending` naming the 20 effect/still keys with no media (the pages draw placeholders). `/studio/effects` with the flags on shows "Free · 6" and the Film Grade clip (`showcase-effects.png`, `showcase-effects-grid.png`).

## Test results

GitHub CI cannot run (billing, see the short version). Local full suite, `venv/bin/python -m pytest tests/ -q`, one branch at a time on this Mac while other sessions tested:

| PR | branch | local full suite | CI (GitHub) |
|---|---|---|---|
| #434 | overnight-bots | **4320 passed, 5 xfailed** (28 m 55 s); `pytest bots` 111 passed, 1 skipped | blocked by billing |
| #435 | overnight-growth-prep | **4329 passed, 5 xfailed** (30 m 19 s) | blocked by billing |
| #436 | overnight-effects-tab | **4316 passed, 5 xfailed**, 6 failed, then **6 passed** re-run without the linked env file (environmental: R2 keys + `PHANTRA_MCP_ENGINE` from `.env`) | blocked by billing |
| #437 | overnight-brand-kit | **4314 passed, 5 xfailed**, 6 failed, then **6 passed** re-run without the linked env file (environmental: R2 keys + `PHANTRA_MCP_ENGINE` from `.env`) | blocked by billing |
| #438 | overnight-qa | **4320 passed, 5 xfailed** (27 m 37 s; no product code, so this is main's count) | blocked by billing |
| #439 | overnight-looks | **4342 passed, 5 xfailed** (31 m 59 s) | blocked by billing |
| #440 | overnight-create-page | **4324 passed, 5 xfailed** (29 m 36 s) | blocked by billing |
| #441 | overnight-showcase | **4342 passed, 5 xfailed** (29 m 29 s) | blocked by billing |
| #442 | overnight-vesper | **4404 passed, 5 xfailed**, 6 failed, then **6 passed** re-run without the linked env file (environmental: R2 keys + `PHANTRA_MCP_ENGINE` from `.env`) | blocked by billing |

Per-stream targeted checks (ruff, the touched test files, node tests, typecheck, build) passed on every branch before its PR opened; each PR body says which.

## Merge notes
- `app/api.py` conflicts three ways between #439 (looks), #436 (Effects tab) and #440/#442: the capabilities dict (keep all five keys), `EFFECT_CATEGORY_LABELS` ("look") vs `EFFECT_TAGS`, `_effect_view`'s `free`/`tags` (row, else spec, else fallback), and the listing's return line. #440 and #442 conflict only on the capabilities dict. The QA stretch and the showcase stream both resolved it locally the same way.
- Merge #441 with or before #440 and #436: it carries the `.gitignore` exception for `web/public/showcase/manifest.json`, without which the page fetch 404s.
- `web/src/lib/showcase.ts` and the placeholder SVG are byte-identical on #436 and #440.
- Worktree hygiene found tonight: Turbopack refuses a symlinked `web/node_modules` (dev and build), so worktrees need their own `npm ci` or `--webpack`; `next build` with `NEXT_BUILD_DIR` edits `web/tsconfig.json` and `next-env.d.ts`; the Browser pane is one tab shared by every session on this Mac; the Supabase session pooler's 15-client cap was saturated for ~15 minutes with nine local APIs up.
- The task's spend-guard mod folder (`.claude/skills/phantra-spend-guard`) does not exist, but a `zp-spend-guard` hook is live and did refuse. Group 11's "full suite" and the per-stream progress files are per stream (`docs/tasks/overnight-2026-10-22/progress-<stream>.md`), not the single `progress.md` the task names, to avoid a nine-way conflict.

## Needs Mike

**Money and accounts**
1. GitHub: fix Billing & plans (payments failed or spending limit) so CI runs again.
2. Showcase: raise `FAL_DAILY_CAP` for the Desktop-launched MCP server, or run the 13 stills + 5 paid effects (quoted 130 + 68 + 48 + 236 + 10 + 89 = 581, within the 458 left only if 4K Smooth is dropped) from a server on current main; the log lists each.
3. Founding 500 grant sizing: 300 credits at retail (zero headroom) vs ~1,168 at provider cost, plus ~$1 of Gemini text per trial; bonuses and prizes should be `promo` lots, not `adjustment` (which lifts the trial thinking cap).
4. Abuse guards: key the per-IP sign-up brake on `Fly-Client-IP` (the forwarded header is forgeable); add email normalisation and a disposable-domain block.

**Data to clean up**
5. Workspace 5 (Phantra Review): the QA connector rows listed in group 1.
6. Workspace `phantra`: kits 4 and 5, project 5, scene 435, cut `44320fc0-…`, bin `asset:33`, three exports (brand-kit walk); the unused ffmpeg fallback assets `asset:34-45` (showcase); one appended turn on the live Create thread.
7. The main checkout's `web/node_modules` gained one directory (`react-resizable-panels`), additive.

**Product calls**
8. Two live kits named "Gygler" (ids 1 and 2): refuse duplicates or show swatches/ids.
9. The floating creature + chips cover the Kit chip, the kit select and page content below ~1,000 px, and the storyboard edge at 1,440.
10. Vesper applies a project's kit silently; the "white mug" brief got the Gygler kit with no line saying so.
11. Trending stays per account unless you want it studio-wide (tenancy forbids the read today).
12. `FOUNDING_500` numbers and `DISCORD_INVITE_URL` placeholders in `web/src/lib/create-v2.ts`.
13. Effects tab: signed-out visitors get a 404, not the sign-in shell; no ⌘K row; the Vesper hand-off has nothing to attach for a clip.
14. Real phone clips for the looks contact sheet (yes/no, and the folder).
15. `PHANTRA_FREE_LOOKS=1` on Fly when the Effects tab ships.
16. Kling 4.0: fill `fal.SLOTS["kling4"]` ids and prices and set the flag when the official API opens; the application draft's `[MIKE: …]` fields; send it yourself.
17. Bots: create the Discord app and token and the Reddit script app (values in env, never in the repo); hosts for the two processes; the welcome-DM default; whether to approach vendor servers or community-run ones first; a service-key bearer door on `/api` for the bot (not built).

**QA findings to triage** (`docs/qa/qa-2026-10-22.md`, 8 major): the manifest 404 (merge order), Elements at 390 px, Create v2 + Vesper v2 on a phone, missing focus indicators, white-on-yellow CTAs, the `role=list` axe critical, keyboard handling of Effects cards and the dial; plus the site's hero-reel "Runway Gen-4 Turbo" label, the model-name mismatches across pages, the 12.8 MB home page, the connector burst limit, and the quote on a soft-deleted scene.

**Hygiene**
18. `tests/test_mcp_server.py` prints `os.environ` (including a signing secret) when its old-config assertion fails.
19. The main checkout sits on `claude/element-sheet-is-the-element` at `6a9d8d57`; the Desktop MCP server runs from there, so it is 20+ commits behind main.
