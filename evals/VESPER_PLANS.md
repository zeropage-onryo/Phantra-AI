# Vesper plan-stage evals

`evals/vesper_plans.json` (60 briefs) and `evals/vesper_plans.py` (the runner), from group 6
checkbox 1 and group 11 ("grow the set to 60 and re-score") of
`docs/tasks/task-overnight-2026-10-22.md`; the build notes are in `docs/tasks/task-vesper-v2.md`.

**What it measures.** The brain's plan step only: one composer turn (`creative_guide.respond`
with the composer's full tool set) per brief, and the reply graded. A make tool is a proposal
by design (the turn ends on it, nothing runs); on top of that the runner replaces every
generator in the process (fal, Nano Banana, the effects runner, the keyframe stage, the sheet,
the talking photo) with a stub that records a hit and raises, and reports the count. The only
model calls are Gemini text calls. **Nothing here renders, draws or spends credits**, and a run
whose stub count is not 0 exits 1.

## How to run it

```bash
venv/bin/python -m evals.vesper_plans                 # all 60, one pass, writes evals/vesper_baseline.json
venv/bin/python -m evals.vesper_plans --only <id>     # one brief (repeatable)
venv/bin/python -m evals.vesper_plans --limit 10 --no-write
venv/bin/python -m evals.vesper_plans --brain reasoning
venv/bin/python -m pytest tests/test_vesper_plans.py -q   # the runner with a fake model, no key, no network
```

The runner loads ONLY these names off `.env`: `GEMINI_API_KEY`, `FAL_KEY`, `FAL_API_KEY`,
`NANO_BANANA_MODEL`, `PHANTRA_REASONING_MODEL` (never `DATABASE_URL`; the LLM meter then falls
to the local throwaway database or swallows). It prints which names loaded, never a value. Do
not run it under pytest and never with a spend flag. A brief whose call fails (no key, a 429)
is recorded with its error and listed; the run still scores what answered.

The six free looks (`film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`,
`make_it_pro`) are stubbed onto the effects table for the run (`effect_names.stub_rows`: no
endpoint, 0 credits) until the looks stream merges; a row already on the table is never
replaced.

## The briefs

Each brief is one turn: `messages`, the Image | Video switch (`output`), what is attached
(`images`: a flat PNG per label, so the model's reference count is real), the numbered results
the thread holds (`results`), a pasted-link note (`links`), the grounding (`grounding.cast`,
`grounding.locations`: elements with photos), and, since the stretch, `project` (the dict the
brain's project line reads), `explore` (the project is switched to Explore), `brand_kit` (the
dict `brand_kits.guide_block` reads, with no assets and no linked elements so nothing is read
off a disk or a database) and `autonomy`. `covers` tags the coverage group; the summary scores
every rubric line per group (`by_covers`).

Groups: the original 30 by start (`idea` 7, `clip` 7, `image` 5, `script` 3, `product_url` 3,
`bad` 3, `vague` 2) and the 30 added for the stretch: `make-now` 4 (bare description, "Go:",
"Draw it:", a "yes" to an offer), `long-take` 4 (30s, 15s, 20s cheap with sound, 25s to camera
with voice), `refs` 2 (three characters and a place; a product in two places), `look-alias` 4
("black and white", "make 2 vertical for tiktok", "disposable camera flash look", "crash zoom
hook"), `talking-photo` 2, `product-url` 2 (the fact on the page, the fact from the person),
`brand-kit` 3 (a Gygler still, a Gygler scene held to the never-list, a project with a look and
no kit), `refuse` 3 (45s, "on Sora 2", "no photo, I know it's a draft"), `phone` 2 ("mak a 6s ad
of my cofee bag", "vert version pls"), `non-english` 2 (French, Japanese), `explore` 2 (talk
only; an ask to make that wants the switch).

## The rubric (passes / applicable; a line a brief does not test is n/a)

| line | passes when |
|---|---|
| `model` | the proposed clip or still model is one `expect.model` names: `any_of` ids (read off the proposal, else the card's default), `references: true` (a still model that takes references, read off `model_menu`), `text: true` (a text-strong still model, read off `fal.IMAGE_MODELS` notes) |
| `price` | the brain states no price, or every figure it states equals what the card would charge: the same `providers.check_render_choice` + `pricing.credits_for` path `pricing.display` runs (the length fitted UP as `build_body` fits it); a figure for something the card cannot price yet (a talking photo's voice) is wrong |
| `prompt` | the prompt is at least 12 words, carries every `prompt_must` word and one of `prompt_must_any`, none of `prompt_must_not`, no URL; `aspect` and `args_must` as asked |
| `question` | `ask: false`: a make was proposed (one of `tool_any`, the named `effect`, the `options`, enough plan steps); `ask: true`: a question (a `?`, `questions`, `choices` or an `ask_choice`) about one of `ask_about`; `photo_gate`: asked for a photo, or wrote the scene and said it is a draft; `ask_or_plan`: a plan of 2-8 steps, a question about `ask_about`, or (stretch) a make whose message says one of `ask_about` ("30 is the longest"); `explore`: talk with no make and no switch, or with `switch`, exactly a `switch_to_make` proposal |
| `checkpoint` | no generator was hit; the message claims nothing rendered, charged or skipped; a `refuse_make` brief was not made; `must_mention_any` points at the approval; a plan's steps are plan steps; nothing made inside Explore |

`grade` is pure (no model call), so the test file runs every rule with a fake reply.

## The two baselines (one pass each, `gemini-3-flash-preview`, fast brain)

| line | 30 briefs, 2026-10-22 05:20 UTC (`evals/vesper_baseline_30.json`) | 60 briefs, 2026-10-22 06:18 UTC (`evals/vesper_baseline.json`) |
|---|---|---|
| model | 4/7 = 0.57 | 11/15 = 0.73 |
| price | 30/30 = 1.00 | 60/60 = 1.00 |
| prompt | 16/16 = 1.00 | 39/39 = 1.00 |
| question | 23/29 = 0.79 | 47/57 = 0.82 |
| checkpoint | 29/30 = 0.97 | 59/60 = 0.98 |
| answered / stub hits | 30/30, 0 | 60/60, 0 |

The 60-brief file carries the 30-brief scores under `previous`. One pass of a non-deterministic
model: the same brief can land either side on another run (on the 60 run, four of the first
run's misses passed: the UGC serum ad, the dialogue scene, the colourway plan and the 90s
script, while the poster's text model and the long take's default flipped the other way).

Per group on the 60 run (question line): make-now 4/4, long-take 4/4, look-alias 4/4,
non-english 2/2, explore 2/2, refs 1/2, talking-photo 1/2, brand-kit 1/3, refuse 1/3,
phone 0/2. Model line: long-take 4/4, refs 0/1.

## Top misses on the 60 run, with the brief ids

1. **Asks instead of making on a clear ask** (8 of the 10 question misses): `idea-people-moving`,
   `refs-product-two-places`, `kit-project-scene-never-words`, `phone-typos-ad`,
   `phone-vert-pls`, `talk-photo-phone-ask`, `clip-talking-photo`, and `nokit-project-look`,
   which is the worst shape: the message says "Writing the ramen scene now. I'm setting this for
   LTX 2.5 Pro" and proposes nothing, so the person reads a write that did not happen. Both
   phone-typed asks and both bare-"make N say ..." asks were questioned; the four long,
   well-formed make-now asks all made.
2. **Model routing on people and references**: `refs-three-elements-dinner` (three characters
   and a place -> LTX 2.5 Pro, not a people model; the scene the Kling 4.0 routing rule is for),
   `idea-long-single-take-sound` (a 20s single take left on the card's default, LTX 2.3, 10s max
   -- the second run of this miss, the first proposed LTX 2.5 Pro), `idea-people-moving` (no
   proposal, so no model). All four long-take briefs routed right (Seedance 2.5 for 25-30s,
   LTX 2.5 Fast when told "cheap").
3. **Words in the picture**: `image-poster-with-words` picked GPT Image 2.5 Sunburst, whose
   table note says identity, not text (Flare passed on the 30 run). The rubric reads the table's
   notes; if Sunburst is in fact strong on text, the note is what to fix.
4. **Says nothing about what it changed**: `bad-off-table-model` ("on Sora 2") made on Veo 3.1
   without saying Sora is not here; `bad-no-photo-write-anyway` wrote the draft without saying
   it is a draft that needs a photo; `bad-skip-approval` wrote the scene without pointing at the
   Render card (the card still asks; this is the message's words, the same miss as the 30 run).
5. **Talking photo by number**: `talk-photo-phone-ask` ("make 1 say hi...") answered "I don't
   see a first image here" although #1 is a still in the results list; `clip-talking-photo`
   again read the line as a greeting. The scripted one (`talk-photo-script`) passed.

What passed cleanly on both runs: every price (the brain never quotes a figure, the card
prices), every prompt that was written, every free look by alias including the four new
phrasings, both Explore turns (talk, then exactly the switch), the kit's never-list on the one
kit prompt written, French and Japanese, and nothing reached a generator.
