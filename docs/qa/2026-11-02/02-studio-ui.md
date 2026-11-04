# 02 — Studio UI audit, signed in (Agent B), 2026-11-02

Branch `claude/qa-2026-11` (= `origin/main` `8ba89087`). Local stack, throwaway schema, headless
Playwright only. Mike's Chrome was not used; the live database and the R2 bucket were not touched.
No priced button was clicked anywhere.

## Summary

- **0 blocker, 6 major, 9 minor, 5 cosmetic** (T1–T20).
- Shipping as Mike decided: the price on the direct generators' one button (no prices in their
  model pickers), the owl + lettering on the phone's top bar, the chat clearing down to the final
  cut (code + node test), a visible focus ring on the Effects tiles (D6 fixed), the floating
  assistant docked in the rail (C2 fixed), the kit chip on a project's Create thread (C1 half fixed).
- Not shipping as decided: the Create chat's still card is **white on yellow in a red frame**
  (T1); the Render card and its Approve button name models by **raw id + platform**
  ("ltx2.3 (ltx)", T2); the Create composer's renderer menu **prints a price per model** (T3); the
  Library's provider filter still says **"Fal"** and **"Runway"** (T4 = C5, wider); `.elnew` is
  still **white on yellow** (T5 = D8); Elements still has **no phone layout** (T6 = D2).
- **Credits: 500 before (16:22Z), 500 after (16:55Z)**, `/api/billing/balance`, `outstanding: 0`,
  one `promo` lot, `remaining 500`. `generations` 0 rows, `fal_requests` 0 rows; the media guard
  logged 0 blocked provider calls.

## The stack (how this was run)

- **API** on `127.0.0.1:8021` through a scratch launcher (`launch_api.py`) with
  `PYTHONPATH=<worktree>:<scratch>/site` (the `sitecustomize.py` that drops the venv's editable
  finder). The launcher asserts `app.__file__` / `src.__file__` are inside the worktree and that
  `DATABASE_URL` names `qa1102b`, then `uvicorn.run("app.main:app")` in-process.
  `DATABASE_URL` and `RAG_DATABASE_URL` = local Postgres `phantra`, `options=-csearch_path=qa1102b`
  (the boot inits made 67 tables there; `/api/me` answered `qa1102b@example.com`, a user that
  exists only in that schema). Blanked on the command line: all `R2_*`, `STRIPE_*`, `SUPABASE_*`,
  `SUPABASE_RAG_DATABASE_URL`, `ELEVENLABS_API_KEY`, `SERPER_API_KEY`, `QUOTE_SIGNING_SECRET`,
  `HIGGSFIELD_*`, `IG_*`, `YOUTUBE_API_KEY`, `LANGSMITH_API_KEY`, `PHANTRA_MCP_TOKEN`,
  `ACCOUNT_KEYS_SECRET`, `GOOGLE_CSE_*`, `REDDIT_*`, `SOCIAL_TOKEN_SECRET`; set
  `PHANTRA_MEDIA=legacy`, `PHANTRA_FOLDER_ACCOUNT=`, `FAL_RECOVER=0`, `PHANTRA_WATERMARK=0`,
  `PHANTRA_RENDER_QC=0`, a local `SESSION_SECRET`. `FAL_KEY` was a FAKE non-key string so priced
  cards draw (the 10-02 recipe); `GEMINI_API_KEY` kept for text turns. Flags on:
  `PHANTRA_EFFECTS_TAB=1`, `PHANTRA_VOICE_TAB=1`, `PHANTRA_FREE_LOOKS=1` (off, `/studio/effects`
  and `/studio/voice` are a 404 by design); `vesper_v2` left at its default (off). Production's
  flag values were not read.
- **Media guard** (in the launcher): `nano_banana.generate_image / generate_from_prompt /
  _generate_content`, every fal submit/generate function, `talking_photo.run_voice / run_talk`,
  and `google.genai` `Models.generate_content` for any model whose name contains
  image/imagen/veo/nano (plus `generate_images/videos`) raise. The Playwright scripts also abort
  any non-GET to `/approve`, `/keyframes`, `/finish`, `/direct/*/run`, `/effects/run`,
  `/voice/*/run`, talking-photo, `/upscale`, `/sheet`, `/dub`, `/render` (not `/quote`).
  Guard hits in the API log: 0. The page guard aborted one `POST /api/scenes/run` on my first
  chat-video try (my pattern was too wide: that route only writes a scene, free); that try was
  discarded and re-run with the narrower pattern.
- **Studio**: `next dev --port 3021` (Turbopack, default `.next`),
  `API_UPSTREAM=http://127.0.0.1:8021`, host `http://qa1102b.localhost:3021`. Sign-in: a
  2-minute token from `app.auth._handoff_serializer` under the local secret, opened at
  `/auth/handoff?t=…&next=/studio` through the studio's proxy, so `phantra_session` lands on the
  studio origin first-party, exactly as in 10-22.
- **Seeded on `qa1102b`**: `accounts.seed` (account 1, slug `phantra`, so this account is the
  "house" account, see T7), a 500-credit `promo` lot, brand kit "QA Kit Acme" (orange/brown
  palette, Pillow logo), project 1 "QA 1102 Mug launch" with that kit picked, character "Maya QA"
  (a 768×1024 Pillow JPEG through the real `POST /api/assets/characters`), a timed 10 s scene
  (3 shots) held to that photo via `mcp_server.write_scene`, an empty 9:16 cut project; later
  seven `generated_assets` rows (Pillow PNGs; tools fal/runway/kling/ltx/nano) to exercise the
  Library filter (T4). Chat turns wrote two more scenes (free, text only).
- **Deviation**: the element POST did not send `sheet=0`, and the API draws a sheet when the field
  is absent (`app/api.py:2585 _sheet_wanted`), so sheet job 1 started. It failed before any
  provider call ("the photos could not be sent to the image model (is the media bucket
  configured?); nothing was charged"); 0 generations, balance unchanged. Recorded as T10.
- Model text spent: 30 `llm_calls` rows (five Create turns, the element's vision description,
  the scene writer), Gemini text models only.
- **Cleanup**: both servers stopped by PID (ports 3021 / 8021 free), schema `qa1102b` dropped,
  `characters/`, `data/brandkits/`, `data/thumbs/`, `data/renders/qa1102b/`, `web/.next` and the
  worktree's `app/`/`src/` `__pycache__` removed, `web/next-env.d.ts` restored; `git status
  --ignored` matches the pre-run snapshot except `docs/qa/2026-11-02/__pycache__/` (another
  agent's crawl script). Nothing committed. Scripts and JSON logs:
  `<scratch>/agentB/{launch_api,seed,sweep,flows,flows2,flows3,apidown,lib}.py`,
  `sweep-all.json`, `flows-*.json`, `flows2.json`, `flows3.json`, `apidown.json`.

## Findings

| # | Severity | Where | What | Evidence |
|---|---|---|---|---|
| T1 | **major** | Create chat, a still's step card (`web/src/components/studio/still-step.css`) | The one button that spends in the chat's still card is **white on yellow** (`.ss-go button { background: var(--signal); color: #fff }`, lines 138-145, about 1.2:1, WCAG 1.4.3 fail), and a card waiting for approval is framed in **red** (`.ss[data-state="waiting"] { border-color: rgb(228 0 43 / .45) }` line 17; "WAITING FOR APPROVAL" in `#ff4d6a`, line 43; the disabled button is dark red `#6e1a1f`, line 156). Waiting is not an error. Breaks two of Mike's rules at once (black text on yellow fills; red only for errors). The price sits under the button ("Nano Banana · 10 credits"), not on it. | `screens/studio/flow-chat-still-1440.png`; CSS lines above |
| T2 | **major** | Render card (project canvas and the chat's) | Renderers are named by **raw id + platform**: the card's model menu lists `grok1.5 (grok)`, `kling3-turbo-pro (kling)`, `kling4 (kling)`, `ltx2.3 (ltx)` … `wan3 (wan)`, the closed picker reads "LTX2.3 (LTX) · 3 SHOTS · 10S · 1080P", and the chat's priced button reads **"Approve · kling3-turbo-pro (kling) · 9:16 · 1 shot · 105 cr"** while the line above it says "Kling 3 Turbo Pro". Source: `src/providers.py:172` `"label": f"{name} ({spec['platform']})"`, served as `renderer.models[].label` by `GET /api/scenes/{id}/render`. The public names already exist (`model_menu.label_for`). | `flow-chat-video-card-1440.png`, `flow-project-render-card-1440.png`, `flow-render-card-model-menu-1440.png` |
| T3 | **major** | Create composer, Video line, "Which model renders" menu | Every model in the menu carries a price: "LTX 2.3 … · 116 credits a clip", "Veo 3.1 … · 360 credits a clip" (12 rows). Mike's rule: no prices in model pickers, the price only on the button. The direct generators' pickers comply (no credits in either menu); this one does not. Source: `web/src/app/studio/(create)/create-view.tsx:4073`. | `flow-create-clip-model-menu-open-1440.png`; menu text in `flows-direct-pickers.json` |
| T4 | **major** (C5, still open, wider) | Library provider filter | With one row per tool seeded, `/api/media` returns `providers: {Fal: 3, Kling: 1, LTX 2.3: 1, Nano Banana: 1, Runway: 1}` and the `<select aria-label="Provider">` shows "Fal · 3" (FLUX.2 Pro, Seedream 4.5 and the Remove-background effect), "Kling" for Kling 4.0, and "Runway". Cause: `src/render_assets.py:116-137 _label` maps `tool == "runway"` to "Runway", looks names up in `pricing.CATALOG_MODELS` (video only, no parked slots such as `kling4`), and otherwise title-cases the tool, so every fal still and every effect (`fal.IMAGE_LOG_TOOL = "fal"`, `effects.LOG_TOOL`) reads "Fal". The viewer's own title is right (`model_label`: "FLUX.2 Pro", "Kling 4.0"). 10-22 counted 18 "Fal" rows in production. | `c5-library-provider-filter-1280.png`, `library-viewer-open-1280.png` |
| T5 | **major** (D8, still open) | `/studio/elements` "New element" | Computed `color: rgb(244,243,242)` on `rgb(254,227,45)`: white on yellow; axe `color-contrast` serious at all three widths. `.elnew` now sets `color: var(--on-signal)`, but `.zps button { color: inherit }` (`studio.css` 121-127, specificity 0,1,1) beats `.elnew` (0,1,0). D8's other half (`.cv2-cta`) no longer exists. | `elements-1440.png`, `elements-390.png`; sweep axe |
| T6 | **major** (D2, still open) | `/studio/elements` at 390 | `innerWidth` and `scrollWidth` both **752** at a 390 viewport (the only one of 33 routes that does this); the element card is off the right edge. | `elements-390.png`; `sweep-all.json` |
| T7 | minor | `/studio/renders` (and `/studio/queue` → renders) at 390 | `scrollWidth` **407**. The "SHOWCASE · 2 — what the Create wall is waiting on · house account only" block squeezes its prompt textareas to ~50 px ("A / rain"), wraps "USE THIS LIBRARY ITEM" into a four-line circle, beside "Render · 138 credits" buttons. Only account 1 sees it (here the seeded account; in production Mike). | `renders-390.png` |
| T8 | minor (D7, still open) | Composer textarea | Keyboard focus (Tab 30 on `/studio/new`): the textarea's `outline-style` is `none`, no shadow; the `.zc-box` border goes from `rgb(38,37,34)` to `rgb(43,42,39)`, which is not a visible indicator. | `d7-composer-focused-1440.png` |
| T9 | minor (C1, half fixed) | Create on `/studio?project=1` with a kit picked | Fixed: the settings line now shows **"Kit: QA Kit A…"**. Still open: asked for "a plain white ceramic mug … propose the plan first; do not make anything yet", the brain offered "Add the Acme logo to the mug?" as a question, but its editable brief already says "SUBJECT: A plain white ceramic mug **with the Acme logo**" and "accents of **Acme orange**", and the plan's still prompt adds "Acme orange #FF880B in a simple cloth napkin". The reply also said "I've started with a still" though no still card was drawn. | `flow-chat-project-kit-1440.png`, `flow-chat-plan-card-1440.png`; reply text in `flows-plan.json` |
| T10 | minor | Elements "Add element" modal; `POST /api/assets/characters` | "Draw a reference sheet … — 15 credits" is **pre-ticked** and the "Add" button that then spends 15 credits carries no price. The API also draws a sheet whenever the form omits `sheet` (`_sheet_wanted`, `app/api.py:2585`), which any caller other than the modal trips over (this QA seed did). | `flow-elements-new-modal-1440.png`; seed log (sheet job 1, failed before the provider, nothing charged) |
| T11 | minor | Every page with the API down | API stopped mid-session: Projects shows an empty board and "— — no account" in the account chip; Create shows "NO ELEMENTS YET — Create a character…"; Assets prints the raw text "INTERNAL SERVER ERROR"; the Video generator's button stays on "Generate · pricing…". Console: 500s from the proxy. Nothing says the studio cannot reach its server, and two pages present an outage as an empty account. | `error-api-down-{projects,create,assets,video}-1440.png`; `apidown.json` |
| T12 | minor | The small creature in the chat (C2 / D5 residue) | C2 is fixed: the assistant is `zpa-corner in-rail`, 44×44 at the rail's top, and no overlap was found on any of the 99 route loads. In the chat the small creature still sits on controls: at 1440 its bubble "That one came out. Another take, or join it into a cut?" covers "Open the canvas" under the Render card (and the bubble is wrong: nothing had rendered, a scene was only written); it covers the "Project · Q…" chip; at 390 it sits on the plan card's last line. | `flow-chat-video-card-1440.png`, `flow-chat-project-kit-1440.png`, `mobile-chat-390.png` |
| T13 | minor | Composer settings line | With a project and a kit set, the line (Image/Video · 9:16 · 10s · Auto · Gemini 3 Flash · Kit · Ask first) no longer fits at 1440 and the send button drops to a second row at the box's bottom-left. | `flow-chat-project-kit-1440.png` |
| T14 | minor | New and redesigned pages (axe, serious) | `/studio/image` color-contrast 9 (`.dg-lab` labels) + link-in-text-block 1; `/studio/video` 3 (`.dg-count`, `small`); `/studio/voice` 8 (`.dg-lab`); `/studio/ads` 13 (format blurbs, `#as-format > span`); `/studio/brand/1` 13 (`.bk-lab`); `/studio/brand` nested-interactive 1 (`article`); `/studio/calendar` and the editor: scrollable-region-focusable 1 + contrast 1; `/studio/plugins` "Download for Mac"; project canvas `.save-indicator`. Same counts at all three widths. | `sweep-all.json`; grid below |
| T15 | minor | Phone navigation | Voice cannot be reached on a phone: not in the bottom bar (Home · Assets · Create · Effects · Profile) and not in the menu (Projects, Video, Image, Ad Studio, Elements, Brand kits, Calendar, Plugins, Settings). | `mobile-menu-open-390.png` |
| T16 | cosmetic | `/studio/image` model picker | One row names the host: "Nano Banana Pro (fal)". Badges disagree with blurbs: FLUX.2 Pro "up to 9 reference images" vs badge "8 refs"; GPT Image 2 / 2.5 "up to 16 references" vs "12 refs". The footer says "The price is for one still at this shape." in a menu that (correctly) shows no price. | `flow-image-model-picker-open-1440.png` |
| T17 | cosmetic | Operator words on screen | Add-element modal: "becomes a searchable chunk on the RAG assets shelf", "Saves the character + teaches the RAG assets shelf"; Ad Studio: "too little to say yet: 0 outputs made (this fills in from 5)…" (`src/mcp_server.py:3538`); editor bin: "Render a scene in the Queue" (the Queue is gone; `web/src/components/cut/left-panel.tsx:244`); a missing scene says "no such concept" and offers **Sign in** to a signed-in person. | `flow-elements-new-modal-1440.png`, `ads-1440.png`, `cut-project-1440.png`, `error-missing-scene-1440.png` |
| T18 | cosmetic | Rail at 1280×800 | The account avatar (`.ravatar`, y=793, 36 px tall) is cut by the window's bottom edge. | `projects-1280.png`; DOM box from `lib.py` |
| T19 | cosmetic | Profile (`/studio/me`) | "Log out" is red text in a red-outlined pill; red is meant for errors only. | `me-390.png` |
| T20 | cosmetic | Create on a phone (`/studio/new`) | Two creatures on one screen (the large one over the heading, a small one by the box); the placeholder truncates ("…describe the next sho"). | `mobile-tab-create-390.png`, `mobile-chat-390.png` |

Checked and fine (not findings): the direct generators carry the price on their one button; the
Render card inside the project (two clicks from Projects) shows "Draw 3 keyframes first · 30
credits", three per-shot keyframe buttons at 10 cr and "Render · 3 shots, one clip · 192 cr",
none pressed; the plan card ("Start", "Approve all · 10 credits", "keyframes and the clip are
priced once the scene is written · each paid step asks first"); the Voice button prices itself
once a script is typed ("Make the voice · 10 credits", `POST /api/voice/speak/quote` only); the
Library drawer (Library / Elements tabs, lists the seeded stills, "Each is sent by its address;
nothing is uploaded again"); the Effects upload panel ("Drop it here, choose a file or use your
Library") and its Library picker; the editor opens an empty 9:16 cut with V1 / A1 / A2 and Export
disabled; Settings → Plan says "Checkout isn't set up on this server yet" (no Stripe here, as
intended); missing ids give a stated error (project, cut, brand kit, publish). No console error
and no request ≥ 400 on any route at any width except the deliberately missing
`/studio/publish/1`. Dev-only, not a finding: the Next dev badge sits on the phone's Home tab and
intercepts its tap.

## Route × viewport grid

Every route under `web/src/app/studio/` (33 addresses, 99 loads), signed in, 3.5 s after `load`.
"ok" = no finding at that width; ids refer to the table above. `sw` = `scrollWidth` when it is
wider than the viewport. Screenshots: `docs/qa/2026-11-02/screens/studio/<stem>`, one per width.
Every route loaded with HTTP 200; redirects are shown as "→". Routes are relative to `/studio`. T18 (the rail avatar cut off) holds at 1280×800 on every route with the rail and is not repeated per row.

| Route (lands on) | 1440×900 | 1280×800 | 390×844 | Console errors / requests ≥400 | axe serious+critical (nodes) | Screenshot stem |
|---|---|---|---|---|---|---|
| `/` | ok | ok | ok | 0 / 0 | 0 | `create-home-{1440,1280,390}.png` |
| `/chat` → `/` | ok | ok | ok | 0 / 0 | 0 | `chat-{1440,1280,390}.png` |
| `/new` | ok | ok | ok | 0 / 0 | 0 | `new-{1440,1280,390}.png` |
| `/image` | T14, T16 | T14, T16 | T14, T16 | 0 / 0 | color-contrast 9, link-in-text-block 1 | `image-{1440,1280,390}.png` |
| `/video` | T14 | T14 | T14 | 0 / 0 | color-contrast 3 | `video-{1440,1280,390}.png` |
| `/ads` | T14, T17 | T14, T17 | T14, T17 | 0 / 0 | color-contrast 13 | `ads-{1440,1280,390}.png` |
| `/assets` | ok | ok | ok | 0 / 0 | 0 | `assets-{1440,1280,390}.png` |
| `/brand` | T14 | T14 | T14 | 0 / 0 | nested-interactive 1 | `brand-{1440,1280,390}.png` |
| `/brand/1` | T14 | T14 | T14 | 0 / 0 | color-contrast 13 | `brand-1-{1440,1280,390}.png` |
| `/calendar` | T14 | T14 | T14 | 0 / 0 | color-contrast 1, scrollable-region-focusable 1 | `calendar-{1440,1280,390}.png` |
| `/cut` | ok | ok | ok | 0 / 0 | 0 | `cut-{1440,1280,390}.png` |
| `/cut/<cut-id>` | T14, T17 | T14, T17 | T14, T17 | 0 / 0 | color-contrast 1, scrollable-region-focusable 1 | `cut-project-{1440,1280,390}.png` |
| `/effects` | ok | ok | ok | 0 / 0 | 0 | `effects-{1440,1280,390}.png` |
| `/elements` | T5 | T5 | T5, T6, sw 752 | 0 / 0 | color-contrast 1 | `elements-{1440,1280,390}.png` |
| `/flows` → `/projects` | ok | ok | ok | 0 / 0 | 0 | `flows-{1440,1280,390}.png` |
| `/link` | ok | ok | ok | 0 / 0 | 0 | `link-{1440,1280,390}.png` |
| `/me` | ok | ok | ok | 0 / 0 | 0 | `me-{1440,1280,390}.png` |
| `/pipeline` → `/projects` | ok | ok | ok | 0 / 0 | 0 | `pipeline-{1440,1280,390}.png` |
| `/plugins` | T14 | T14 | T14 | 0 / 0 | color-contrast 1 | `plugins-{1440,1280,390}.png` |
| `/projects` | ok | ok | ok | 0 / 0 | 0 | `projects-{1440,1280,390}.png` |
| `/projects/1` | T2, T14 | T2, T14 | T2, T14 | 0 / 0 | color-contrast 1 | `projects-1-{1440,1280,390}.png` |
| `/publish/1` | ok | ok | ok | 404 GET /api/publish/1 ×2 (expected: no post 1; page says "no such post on this account -- prepare it again") | 0 | `publish-1-{1440,1280,390}.png` |
| `/queue` → `/renders` | ok | ok | T7, sw 407 | 0 / 0 | color-contrast 1 | `queue-{1440,1280,390}.png` |
| `/renders` | ok | ok | T7, sw 407 | 0 / 0 | color-contrast 1 | `renders-{1440,1280,390}.png` |
| `/scene/1` → `/projects/1?scene=1` | T2, T14 | T2, T14 | T2, T14 | 0 / 0 | color-contrast 1 | `scene-1-{1440,1280,390}.png` |
| `/settings` → `/settings/account` | ok | ok | ok | 0 / 0 | 0 | `settings-{1440,1280,390}.png` |
| `/settings/account` | ok | ok | ok | 0 / 0 | 0 | `settings-account-{1440,1280,390}.png` |
| `/settings/plan` | ok | ok | ok | 0 / 0 | 0 | `settings-plan-{1440,1280,390}.png` |
| `/settings/usage` | ok | ok | ok | 0 / 0 | 0 | `settings-usage-{1440,1280,390}.png` |
| `/settings/workspace` | ok | ok | ok | 0 / 0 | 0 | `settings-workspace-{1440,1280,390}.png` |
| `/settings/connections` | ok | ok | ok | 0 / 0 | 0 | `settings-connections-{1440,1280,390}.png` |
| `/settings/preferences` | ok | ok | ok | 0 / 0 | 0 | `settings-preferences-{1440,1280,390}.png` |
| `/voice` | T14 | T14 | T14, T15 | 0 / 0 | color-contrast 8 | `voice-{1440,1280,390}.png` |

States beyond "loaded" (screenshots in the same folder): empty (fresh account: `assets-*`,
`renders-*`, `cut-*`, `calendar-*`), modal / picker open (`flow-elements-new-modal-1440`,
`flow-video-library-drawer-1440`, `flow-image-library-drawer-items-1280`,
`flow-effects-library-picker-1440`, `flow-image-model-picker-open-1440`,
`flow-video-model-picker-open-1440`, `flow-create-clip-model-menu-open-1440`,
`flow-create-model-menu-open-1440`, `flow-render-card-model-menu-1440`, `mobile-menu-open-390`,
`library-viewer-open-1280`), error (`error-missing-{scene,project,cut,brand-kit,publish}-1440`,
`error-api-down-{projects,create,assets,video}-1440`).

## Flow timings (clicks and seconds)

Measured by the Playwright scripts from `/studio` already loaded (dev server, routes warmed),
counting clicks only (typing and Enter not counted). Seconds are wall time from the first click
to the priced element appearing in the DOM (polled every 250 ms for the generators, 1 s for chat).

| Goal | Path | Clicks | Seconds | Priced element reached (never pressed) |
|---|---|---|---|---|
| Priced card for a **video** | Direct: rail **Video** | **1** | **1.1** | "Generate · 116 credits" (LTX 2.3, 6 s, 1080p, 9:16), disabled until a prompt is typed |
| | Direct, ready to spend: Video → click the prompt, type | 2 | 2.4 (incl. scripted typing) | "Generate · 116 credits", enabled |
| | Create chat: Video toggle → box → type → Enter | **2** | **25.8** | Render card in the turn: "Approve up to 2 keyframes · up to 20 credits" and "Approve · kling3-turbo-pro (kling) · 9:16 · 1 shot · 105 cr" (T2) |
| | Project: Projects → project card → "Render…" | 2 (from `/studio/projects`; 3 from `/studio`) | 8.6 (includes 8 s of fixed waits in the script) | "Render · 3 shots, one clip · 192 cr", "Draw 3 keyframes first · 30 credits" |
| Priced card for a **still** | Direct: rail **Image** | **1** | **1.0** | "Generate · 10 credits" (Nano Banana, 1:1), disabled until a prompt |
| | Direct, ready to spend | 2 | 2.3 (incl. typing) | "Generate · 10 credits", enabled |
| | Create chat: Image toggle → box → type → Enter | **2** | **7.3** | step card "Approve" + "Nano Banana · 10 credits" (T1) |
| Plan with a priced card | Create in the project: box → type → Enter (after one talk turn) | 1 | 20.7 | PLAN · 3 STEPS: "Start", "Approve all · 10 credits" |

## Decision compliance

| Decision (Mike) | Ships? | Evidence |
|---|---|---|
| No prices in model pickers; the price only on the button | **Partly.** Image and Video generators: yes (no credits in either picker; the price is on "Generate · N credits"). Create composer's "Which model renders" menu: **no** (T3). Create chat still card: price under "Approve", not on it (T1). Render card picker: no prices, but raw ids (T2). Elements' Add: the 15-credit sheet is priced in the checkbox, not the button (T10). | `flow-*-model-picker-open-1440.png`, `flow-create-clip-model-menu-open-1440.png` |
| Renders named by model, never "fal" | **No.** Library filter "Fal · 3" / "Runway" / "Kling" (T4); Render card "ltx2.3 (ltx)" (T2); image picker "Nano Banana Pro (fal)" (T16). The Library viewer and the direct pickers use public names. | T2, T4, T16 |
| Yellow accent, black text on fills; red only for errors | **Partly.** Black on yellow: direct Generate, plan "Start", the Render card's Approve / Render, Effects "Step inside", Projects "New project", Profile "Add credits". White on yellow: chat still card's Approve (T1) and Elements "New element" (T5). Red on non-errors: the still card's waiting frame and label (T1), Profile "Log out" (T19). | T1, T5, T19 |
| Chat clears to the final video after a render | **Yes, from code and test (not produced: it needs a render).** `keepOnlyCut` in `web/src/lib/final-cut.ts` keeps only the turn carrying the final cut; called from `create-view.tsx:2970` (a one-clip scene's clip lands) and `:3012` (the joined cut is ready). `node --test tests/final-cut.test.mjs`: 7/7 pass, including `keepOnlyCut` (lines 45-53). | test run, 2026-11-02 |
| Phone top bar uses the owl + Phantra lettering | **Yes.** `PhoneTop` renders `OwlLockup` (menu button left, lockup right, `phone-chrome.tsx`); seen on every 390 screenshot. The bottom bar is Home · Assets · Create (a yellow star, `aria-label="Create"`, no text label) · Effects · Profile, each 48 px tall. | `create-home-390.png`, `me-390.png` |

## Re-checks from 2026-10-22

| Id | Then | Now | Evidence |
|---|---|---|---|
| C1 | Kit applied to a "plain white mug" brief, no cue, no chip on `/studio` | **Half fixed.** Chip "Kit: QA Kit A…" is on the settings line of the project's thread; the brain asks before adding the logo, but its brief and the plan's still prompt already carry the logo / Acme orange (T9). | `flow-chat-project-kit-1440.png`, `flow-chat-plan-card-1440.png` |
| C2 | Floating assistant covering content at 1280×800 | **Fixed.** Docked as a 44×44 `zpa-corner in-rail`; no overlap on any route at 1280 or 1440. Residue in the chat only (T12). | `projects-1280.png`, `elements-1280.png` |
| C3 | Brand kit asset 404s | **Not reproduced** here: `/studio/brand` and `/studio/brand/1` made 0 failed requests, the seeded kit's logo answered 200. The kit was made on this stack, so production's two rows were not tested. | sweep |
| C5 | Library filter "Runway" | **Still open, wider**: "Runway", "Fal" for every fal still and effect, "Kling" for Kling 4.0 (T4). | `c5-library-provider-filter-1280.png` |
| D2 | Elements 752 px wide at 390 | **Still open** (T6). | `elements-390.png` |
| D5 | Creature covers content on every page at 390 | **Mostly fixed**: no creature on the 390 route sweep (none found in the DOM boxes); a small one remains by the chat composer (T12, T20). | `mobile-tab-*-390.png`, `mobile-chat-390.png` |
| D6 | Effects cards: no focus ring | **Fixed** (the page is redesigned): `.fxw-tile` focused by Tab (56 tabs in) is `:focus-visible` with `outline: solid 1px rgb(254,227,45)`. | `d6-effects-tile-focused-1440.png` |
| D7 | Composer textarea: no focus ring | **Still open** (T8). | `d7-composer-focused-1440.png` |
| D8 | White on yellow (`.elnew`, `.cv2-cta`) | **`.elnew` still open** (T5); `.cv2-cta` is gone with the old Create page. New instance: the chat still card's Approve (T1). | `elements-1440.png`, `flow-chat-still-1440.png` |

## Not verified

- Anything that needs a render: the final cut clearing the chat (code + test only), the Render
  card after a clip lands, render QC notes, Finish / draft, the watermark.
- Production: flag values (`effects_tab`, `voice_tab`, `free_looks`, `vesper_v2` were set by
  hand here), C3 on production's kits, real R2 media, Stripe checkout (not configured locally),
  real phones / Safari / a screen reader.
- `vesper_v2` on (storyboard, dial, next steps): not walked this time.
- The talking-photo card, dubbing, clip edits, the calendar's drawer and posting (no social
  connection seeded), Ad Studio past its page (add-on not on sale: "Ad Studio opens soon").
- A real element photo or a real Library video; Library at 390 with many items; the editor with
  clips on the timeline (the bin was empty when it was opened).
- First-run `/studio` with no saved thread at 390 was seen (`create-home-390.png`); the mid-render
  states were not.
- Timings are on a dev server with warmed routes on this Mac; production paint times will differ.

## Screenshots

`docs/qa/2026-11-02/screens/studio/` (143 PNGs, 32 MB):
- Route sweep: `<stem>-{1440,1280,390}.png` for the 33 routes in the grid (99 files).
- Flows: `flow-direct-{video,image}-priced-1440`, `flow-{image,video}-model-picker-open-1440`,
  `flow-create-{model,clip-model}-menu-open-1440`, `flow-chat-still[-card]-1440`,
  `flow-chat-video[-card]-1440`, `flow-chat-project-kit[-card]-1440`, `flow-chat-plan[-card]-1440`,
  `flow-project-render-card-1440`, `flow-render-card-model-menu-1440`,
  `flow-elements-{new-modal,see-all,view}-1440`, `flow-video-library-drawer-1440`,
  `flow-image-library-drawer-items-1280`, `flow-effects-library-picker-1440`,
  `flow-voice-script-typed-1440`, `library-viewer-open-1280`, `c5-library-provider-filter-1280`.
- Focus: `d6-effects-tile-focused-1440`, `d7-composer-focused-1440`,
  `d7-composer-focused-programmatic-1440`.
- Errors: `error-missing-{scene,project,cut,brand-kit,publish}-1440`,
  `error-api-down-{projects,create,assets,video}-1440`.
- Phone: `mobile-tab-{home,assets,create,effects,profile}-390`, `mobile-menu-open-390`,
  `mobile-chat-390`.
