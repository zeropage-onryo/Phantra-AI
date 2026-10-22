# Task: Vesper v2 -- plan evals, the media-first studio, effects by name, the Kling 4.0 slot

Group 6 of `docs/tasks/task-overnight-2026-10-22.md` (Mike, 2026-10-22, 00:25 ET: "approved").
Branch `claude/overnight-vesper`, one PR. Everything behind flags, off by default; no render, no
still, no effect run, no credit spent; the brain's text calls are the only model calls.

Mike's call for Vesper: media-first, storyboard shot cards, an autonomy dial, tappable questions,
proactive next steps; a Kling 4.0 slot switched off and never routed through Higgsfield or useapi.

## As built (2026-10-22, overnight)

### 1. The plan-stage eval set -- `evals/vesper_plans.json`, `evals/vesper_plans.py`

- **30 briefs**, each one composer turn: idea (7), script (3), product URL (3), image (5), clip (7),
  vague (2) and bad (3) starts. A brief carries the messages, the Image | Video switch, what is
  attached (a flat PNG per label), the numbered results the thread holds, a pasted-link note where
  the start is a URL, and `expect`, which the rubric reads.
- **Five rubric lines**, scored passes / applicable: `model` (the proposed clip or still model is
  one the brief names as right: a 20s single take with sound wants Seedance 2.5 or LTX 2.5 Fast; a
  still held to a photo wants a model that takes references; words in the picture want a text
  model), `price` (the figure the card would charge -- `providers.check_render_choice` +
  `pricing.credits_for`, the path `pricing.display` prices with; the brain states no price, or the
  one it states equals it), `prompt` (long enough, carries what was named, no address), `question`
  (asked the right question when the brief was vague, did not stall when the ask was clear),
  `checkpoint` (no generator reached, nothing claimed rendered or charged, a real person's likeness
  refused).
- **Runs ONLY the plan step.** `creative_guide.respond` with the composer's full tool set
  published; every generator in the process (`fal.generate_*`, Nano Banana, `effects.run`, the
  keyframe stage, the sheet, the talking photo) is replaced by a stub that records a hit and
  raises; `find_references` / `search_footage` / `research_look` are answered with canned
  "nothing found"; `list_models` / `list_effects` / `load_skill` read the tables. The run asserts
  in code that the hits it reports are the hits that happened (0 is the only passing number).
- **Keys by name.** `load_env` reads only `GEMINI_API_KEY`, `FAL_KEY`, `FAL_API_KEY`,
  `NANO_BANANA_MODEL`, `PHANTRA_REASONING_MODEL` off `.env` -- never `DATABASE_URL`, so the LLM
  meter (`src/spend.py`) lands on the local throwaway database or swallows. The names loaded are
  printed, never a value.
- **The free looks are stubbed onto the effects table for the run** (`effect_names.stub_rows`:
  `film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`, `make_it_pro`; no endpoint,
  0 credits) so the named-look briefs can be answered before the looks stream merges. Rows already
  on the table are never replaced.
- **Degrades.** A failed call (no key, a 429, a refused proposal) is recorded on the brief and
  listed; the run still scores what answered. `--only <id>`, `--limit N`, `--brain reasoning`,
  `--no-write`.
- **Baseline, 2026-10-22 ~05:20 UTC, `gemini-3-flash-preview`, one pass** (`evals/vesper_baseline.json`):
  30/30 answered, 0 stub hits -- model **4/7 = 0.57**, price **30/30 = 1.00**, prompt
  **16/16 = 1.00**, question **23/29 = 0.79**, checkpoint **29/30 = 0.97**. What failed, read
  off the file: the brain asked instead of making on four clear asks (the UGC serum ad, the
  dancer, the dialogue scene, the colourway plan) and answered the talking-photo ask as a
  greeting; it proposed LTX 2.5 Pro (10s max) for a 20s single take -- exactly the routing the
  Kling 4.0 rules and the models paragraph are for; the 90s script was neither split nor asked
  about; and on "skip the approval" it wrote the scene without pointing at the Render card
  (the card still asks -- this is the message's words, not a spend). Nothing was rendered,
  drawn or charged.
- `tests/test_vesper_plans.py` runs the runner end to end with a fake model.

### 2. vesper_v2 -- the media-first studio (flag `vesper_v2`, `PHANTRA_VESPER_V2=1`)

With the flag off the Create page is byte-for-byte what it was: the dial is not read, no tool is
added to a turn, no line reaches the brain, no component is on the page.

1. **Media-first layout** (`web/src/components/studio/vesper-v2.css`, `storyboard.tsx`): the
   storyboard is the wide main area on the right, Vesper's column (the stream and the box) docks
   on the left, clear of the resting creature's corner. Under 1100px it is one column, the
   storyboard first.
2. **Storyboard shot cards** (`web/src/lib/storyboard.ts`): read OFF THE THREAD -- every written
   scene in the conversation, newest first, one card per timed shot: its still or clip, its length
   badge, the model chip its Render card opens on ("Default model" when none was proposed), its
   words. Words edit inline on the card (page state; the scene row is the writer's). Drag to
   reorder is a VIEW order kept per browser (`sessionStorage`); the scene's windows on the server
   are not rewritten by a drag -- the editor cuts, this arranges. **"Redo this shot only"** opens
   that scene's priced Render card (`RenderDialog`, titled "Redo shot N") and never renders; the
   card's own shot-by-shot loop and its Approve are unchanged. A scene switcher appears above the
   grid when the thread holds more than one scene.
3. **Autonomy dial** (`web/src/lib/autonomy.ts`, `autonomy-dial.tsx`; in the storyboard's head and
   on the settings line in place of Ask first / Auto): Ask me everything / Checkpoints /
   Autopilot. **The price checkpoint holds in every setting**: the dial never maps to the
   composer's "auto" GenerateMode (`generateModeFor` is "ask" for all three), a paid plan step
   (still, sheet, keyframes, clip) always waits at its price (`stopsAt`), Ask me everything stops
   at the free steps too, Checkpoints and Autopilot run free steps and start a proposed plan on
   their own (`startsPlans`). Server side `make_plan.runs_unasked(step, mode)` is False for every
   paid step under every setting (`PAID` / `FREE`), and the dial's setting rides to the brain as
   one line (`creative_guide.AUTONOMY_NOTES`) that only changes how it talks.
4. **Tappable questions** (`src/guide_tools.py` `ASK_TOOL = "ask_choice"`,
   `prompts/creative_guide_questions.txt`, `web/src/lib/tappable.ts`, `tappable-question.tsx`):
   the brain may ask one question as swatches (each option a `#rrggbb`), aspect chips (4:5, 9:16,
   16:9 drawn as little frames), an A/B pick of numbered results, or plain chips -- two to six
   options. A write in the proposal sense: the turn ends on it, `guide_tools.run` and
   `/creative-guide/act` refuse it, the line above the chips is the question itself, and a tap
   sends the option's words as the person's next message (they can always type). Published only
   when the route asks (`session(questions=True)`, i.e. the flag is on); a question with fewer
   than two options goes back to the model as a refusal and it answers in words.
5. **Proactive next steps** (`web/src/lib/next-steps.ts`, `next-steps.tsx`): under a scene whose
   every shot has its clip -- Add Sound Pass (the `add-sound` card on the clip), Cut a vertical
   version (`vertical_ready` once the free looks land, else the `reframe` card), Make 3 ad
   variants (a plan card of three variant scenes and their render steps, drawn unstarted; every
   clip waits at its own price). Each opens a priced card; nothing runs from the click.

Tests: `tests/test_vesper_v2.py` (runs_unasked never for a paid step under any setting; the
question's shape, refusals and route gating; the flag off by default), `web/tests/vesper-v2.test.mjs`
(Autopilot stops at every paid step and the render even after "Approve all"; the dial never
yields "auto"; the storyboard, reorder, redo target, next steps and the variants plan).
`npm run typecheck` and `npm run build` pass. Screenshots: see "Checked" below.

### 3. Effects by name -- `src/effect_names.py`

"Give this a noir grade" becomes an `apply_effect` proposal for `noir`. The brain is handed the
effects table at runtime, so the table is the authority: `effect_names.LOOKS` carries the plain
words for the free looks (`film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`,
`make_it_pro`) and `STANDING` the words for effects already on the table (a sound pass, upscale,
cut out, reframe); `resolve(text)` answers only with an id the table carries NOW (a look that has
not merged resolves to nothing, so this branch is the product it was until it does). Wired in
three places: `guide_tools._check_effect` resolves an alias or a mis-spelt id before the table's
own check (a `noir grade` call checks as `noir`), `list_effects` ends with each listed look's
words, and `prompts/creative_guide_effects.txt` gained LOOKS BY NAME (call apply_effect straight
away for a named look; a free look shows a 0-credit card that still waits for Approve). The eval
brief `clip-noir-grade` expects exactly this (passed on the baseline, with the table stubbed);
`tests/test_effect_names.py` is the fake-model test.

### 4. The Kling 4.0 slot -- `fal.SLOTS`, flag `kling_4` (`PHANTRA_KLING_4=1`)

A parked row in the table's shape with its official endpoint ids and its prices **None**, OFF
`fal.VIDEO_MODELS`. It joins the table (`enable_slots`, run at import) only when ALL hold: the
flag is set, both ids are filled, a positive per-second price is published for every resolution
(`slot_ready`). The flag alone, or a price of None, offers it nowhere: not the pickers
(`providers.models_for`), the public catalogue (`pricing.catalog_rows` -- `CATALOG_MODELS` plus
the ready slots), the brain's list (`model_menu.for_model`), `recommend_model`
(`model_pick.rank`), a `make_video` proposal (`model_menu.video_id` drops it), nor the `kling_4`
capability. Never a reseller or a relay (Mike's call; `tests/test_kling4_slot.py` greps for it).
Routing rules, applied only once it is ready: a single continuous shot of 15-30s, or a scene held
to 3 or more references, prefers it -- `model_menu.slot_preference` fills `model` / `model_why`
on a scene the brain proposed no model for, `model_pick.rank` bumps it for the `single` and
`references` traits, and its menu line says so. Banded `creator` in `providers.BANDS` ahead of
its day. The existing fal table tests (durations, resolutions, schema re-checks, drafts, prompt
rules, the catalogue projection) pass with the slot off the table; the slot test fills it in
with fake ids and a fake price, turns it on, checks it is priced by the same estimators and
routed, and turns it off again.

**Filled 2026-10-22 (same day; Mike: "kling 4.0 is on fal, integrate it and highlight it").**
fal's page copy still said "API access coming soon" that morning, but the queue schema answered
for both ids and fal's model listing carried the price, so the slot is live: `t2v`
`kling/v4/text-to-video`, `i2v` `kling/v4/image-to-video`, duration an integer 3-30, 720p or
1080p (720p the studio's default by the house rule, 1080p one pick away on the card; fal's own
default is 1080p), aspect 16:9 / 9:16 / 1:1 / 21:9 on
text-to-video, $0.157 / $0.235 per second. The flag flipped to opt-OUT (`PHANTRA_KLING_4=0`
parks it; unset is on), `available` is True, and ids or prices of None still park it. The
`kling` platform's default tier stays Kling 3 Turbo Pro; Kling 4.0 is reached by name, the
pickers, or the routing rule. The schema's `multi_prompt` (per-shot prompts) is not sent: the
studio's timed shots are its own. Highlighted on the studio's Create page (a "New" line under
the headline and a "Try Kling 4.0" starter, both only while `caps.kling_4` is true), the Create
v2 "New at Phantra" tiles, the home hero's eyebrow and the Kling landing page's model cards;
`web/src/content/pricing.json` re-exported so /models and /pricing list it. No showcase clip
was rendered for it (a spend; Mike's call). No `prompts_for` rule yet: Kling 4 reads the Kling 3
prompt shape.

## Checked

- `venv/bin/ruff check .` clean; targeted suites green: `tests/test_vesper_plans.py`,
  `tests/test_vesper_v2.py`, `tests/test_effect_names.py`, `tests/test_kling4_slot.py`,
  `tests/test_guide_tools.py`, `tests/test_make_plan.py`, `tests/test_creative_guide.py`,
  `tests/test_model_menu.py`, `tests/test_effects_studio.py`, `tests/test_fal.py`,
  `tests/test_providers.py`, `tests/test_pricing.py`, `tests/test_drafts.py`,
  `tests/test_prompts_for.py`, `tests/test_connector_plan.py`, `tests/test_plans.py`.
  `cd web && node --test tests/*.test.mjs` (268 tests), `npm run typecheck`, `npm run build`.
  The full suite was not run on this branch (the parent session runs it).
- The baseline eval ran once live (30 Gemini Flash calls plus tool rounds; nothing else).
- In the browser (the built-in pane at 1440x900, API on 8006 on a throwaway local schema
  `vesper_v2_ui` with the flag on, R2 blanked and a fake FAL key so nothing could spend, the
  studio on 3006 proxying to it, one seeded exempt account, a minted session cookie). Walked:
  a dropped reference, a two-shot brief under Autopilot (the brain proposed a four-step plan
  that started on its own and STOPPED at step 1, the priced still), Skip on that still (free),
  the scene step writing itself, the storyboard filling with two shot cards (length badge,
  model chip "LTX 2.5 Pro", the words, inline edit opened and closed), "Redo this shot only"
  opening the scene's Render card (keyframes 66 cr / render 346 cr, not charged on the exempt
  account) and closed with Escape, the dial switched to Ask me everything, a palette brief
  answered with a swatches question (`ask_choice`), a tap sending "Warm amber (#ffbf00)", and
  the brain's still proposal waiting on its Approve. **No priced card was clicked; nothing was
  rendered, drawn or charged.** `docs/qa/screens-2026-10-22/`:
  `vesper-v2-01-layout-empty.png`, `vesper-v2-02-autopilot-plan-stops-at-price.png`,
  `vesper-v2-03-storyboard-shot-cards.png`,
  `vesper-v2-04-redo-shot-opens-priced-card-unclicked.png`,
  `vesper-v2-05-tappable-question-swatches.png`,
  `vesper-v2-06-tap-answered-still-card-waiting.png` (PNGs converted from the pane's
  screenshots with `sips`; 800px wide, the pane's own scale).
- Found and fixed on the walk: the generic confirm card drew under a tappable question
  (`[object Object]` options) -- turns.tsx now leaves it out for `ask_choice`; and the first
  layout put Vesper's column under the resting creature -- the columns were swapped.

## Not done / open

- The in-app Browser pane is shared between the overnight streams and other sessions navigated
  my tab mid-turn twice; a guide turn in flight when the page is left is not picked up on return
  (existing behaviour, not v2). Screenshots were taken between hijacks.
- The next-steps row needs a rendered scene to appear; no scene was rendered tonight, so it is
  covered by the node test and not by a screenshot.
- The `web/node_modules` symlink was replaced by a real `npm ci` in this worktree: Turbopack
  refuses a symlink that points outside the project ("points out of the filesystem root"), for
  both `next build` and `next dev`.
- **Eval set grown to 60 briefs and re-scored (stretch, group 11, 2026-10-22 ~06:18 UTC):**
  30 briefs added (`covers` tags: make-now, long-take, refs, look-alias, talking-photo,
  product-url, brand-kit, refuse, phone, non-english, explore); the runner hands a brief's
  project, Explore flag, brand kit and autonomy to the turn; three rubric rules added
  (`explore`, `prompt_must_not`, a make that says why it differs under `ask_or_plan`). One
  pass on gemini-3-flash-preview, 60/60 answered, 0 stub hits: model 11/15 = 0.73, price
  60/60, prompt 39/39, question 47/57 = 0.82, checkpoint 59/60 = 0.98 (the 30-brief run:
  0.57 / 1.00 / 1.00 / 0.79 / 0.97, kept as `evals/vesper_baseline_30.json` and under
  `previous`). Rubric, how to run, both baselines and the top misses with ids:
  `evals/VESPER_PLANS.md`. Nothing was rendered, drawn or charged.
