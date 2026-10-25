# Vesper output quality audit, 2026-10-24

What Vesper (the Create box on `/studio`) does to the work between the person's words and
the model, measured on live data (read-only) and on fresh turns. Steps 0, 1, 2 and 6 of the
brief are done. Steps 3, 4 and 5 (competitor capture, benchmark renders, blind judging) were
NOT run: the spend cap in the brief was an unfilled placeholder, so the cap was treated as
zero and nothing was rendered. What they would cost is at the end.

Spend for this task: **0 credits, $0 on fal, 0 Higgsfield, 0 Runway.** Only Gemini text
(about 50 brain turns and 2 enhancer calls through the studio's own key).

## The answer in one paragraph

The biggest measured failure is not in Vesper's words. **A still made from the Create box is
not drawn from the prompt the person approved.** Between Approve and the image model, the
still goes through `prompts/enhance_system.txt`, a *video* shot editor, which adds a
`(0-5s)` time marker, "Motion:", "handheld camera drift" and "no background music". Then the
brand kit block is added twice, and the frame in the settings line silently beats the "9:16"
Vesper wrote into the prompt. That held for 6 of 6 Create stills traced on live (5 of 6 got
the brand block twice; 5 of 6 asked for 9:16 and came out 4:5). The prompt grows 3 to 6
times longer on the way. Fix that first: it breaks the product's own rule ("the prompt you
write is what they read above that Approve") and costs a still on every send.
Task file: `docs/tasks/task-vesper-approved-prompt-runs.md`.

## 1. Ground truth from our own data (read-only, live, 2026-10-24)

The data is small, and most of it is Mike's own: 225 Library rows, 108 `output_events`,
5 saved threads, 55 scenes. Only three outside accounts ever used the Create box. Two typed
a refused request (nudity). The third (account 11) wrote one bartender scene that was
archived with "no reference photos attached", then made one still and four LTX clips on a
second try (1 of 4 clips kept).

Keep = any `output_events` keep (cut_add, export, download, star, element_from, ref_reuse,
post) or the file reused as a reference in a later scene or thread.

| Door, model | n | kept | keep rate |
|---|---|---|---|
| Create still, Nano Banana (gemini-2.5-flash-image, the default) | 99 | 12 | 12% |
| Create still, Nano Banana Pro (gemini-3-pro-image) | 6 | 6 | 100% |
| Create still, FLUX 1.1 Pro | 3 | 3 | 100% |
| Connector still, Seedream 4.5 | 26 | 2 | 8% |
| Connector still, FLUX 1.1 Pro | 12 | 5 | 42% |
| Connector still, Nano Banana Pro | 5 | 3 | 60% |
| Render card clip, Kling 3 Turbo | 4 | 4 | 100% |
| Render card clip, Grok 1.5 Lite | 5 | 3 | 60% |
| Render card clip, LTX 2.3 / 2.5 | 10 | 3 | 30% |

Read with care:
- 85 of the 99 default-model stills are from 4 to 18 September, before Vesper existed in
  its current form. Since 2026-10-11 the Create box made about 20 stills. That is too few to
  rank models on.
- **Re-rolls-to-keep is 0 in 27 of 28 kept chains.** A still is kept on the first try or not
  at all. Re-rolls almost never end in a keep: 41 near-identical re-roll chains, 1 kept on
  the second try. So a re-roll is a sign the prompt was wrong, not that luck ran out.
- **Discards are almost never recorded.** There are 3 deletes and 1 regen in the whole table.
  People don't delete, they just ignore the result. "Not kept" means "ignored", which is the
  real signal.
- **Ask first / Auto, Fast / Reasoning and the Image | Video switch are recorded nowhere.**
  They are not in `generations.params_json` or in `generated_assets.metadata_json`. Nothing
  links a generation back to the chat turn that made it, apart from the thread itself, and a
  thread keeps only its newest turns. **Keep rate per setting cannot be measured until this
  is recorded.** That is part of the top task.

Discards by layer, from the 10 traces below: the clearest cause is the still chain (step 0b).
There are too few discarded clips to split by layer.

## 0a. The instructions, file by file

`src/creative_guide.py:instructions()` stacks these in order. A later file can contradict an
earlier one, and nothing tells the model which wins.

| File | Failure it prevents | Conflicts, repeats, stale |
|---|---|---|
| `creative_guide.txt` | A questionnaire; made-up assets, prices, renders | **Says to cut every scene into timed shots, 2+ by default. `_make` says "do not write shot lists or timings yourself unless they named a count".** Seen live: the Wong Kar-wai turn wrote `(0-4s)…(7-10s)` into make_video and passed `shots: 3`. Says "before Create", a button that no longer exists. Frames the job as video only, even in Image mode. |
| `_voice.txt` | Cute ferryman talk; joking about money | Says "lead with the useful thing, short sentences". But a make turn's `message` is the whole prompt pasted again (seen in every live make turn and in the fresh runs), so the person reads the prompt twice. |
| `_tools.txt` | Describing pictures that were never found; writes the person didn't ask for | Stale: "the Projects board is the studio's home", "Assets wall". The home is `/studio`, the wall is the Library. |
| `_make.txt` | Making on a question; forgetting attached references | Conflicts with the base file on timings (above). Its "THE PROMPT YOU HAND THE TOOL IS THE WORK" is then broken downstream, because the still prompt is rewritten (0b). |
| `_explore.txt` | Making in Explore | None found. |
| `_plan.txt` | Plans that make more than was asked | Plan steps put the full prompt in `message` too. |
| `_effects.txt` | Made-up effect names; stating prices | None found. |
| `_models.txt` | Proposing a model with no reference input | **Says to pick a text-capable model when "words must read in the picture". Live: Vesper chose FLUX 1.1 for an app screen ("superior for brand colors and text"), and in the fresh run Nano Banana for "UI text accurately".** The file gives categories but no facts per model, so the brain guesses. `prompts/models/` (step 2) is the missing fact sheet. |
| `_research.txt` | Copying a name ("like X") into the prompt | **Live: the Wong Kar-wai make prompt still says "in the style of Wong Kar-wai"**, and `research_look` was called twice for the same name, which the file forbids. |
| `_kit.txt`, `_screens.txt` | Kit edits by accident; video models drawing unreadable UI | `_screens` came after the 10-22 Gygler stills that asked FLUX to draw an app screen. Without a kit nothing offers a screen, so a new user's "UI on a tablet" goes to a still model. |
| `_questions.txt` | Typed questions that should be taps | **Three ways to ask in one turn:** `choices` (base), `questions` (assistant_brain, "at most three"), `ask_choice` (v2). The base file says ONE question; `assistant_brain.txt` says up to three. |
| `_results.txt`, `_skills.txt` | Pointing at the wrong result; working from memory | Skills are loaded again on almost every turn (`ad`, then `product-still`, …). That costs time but breaks nothing. |
| `assistant_brain.txt` | The pill losing the thread | **Says to ask up to 3 questions and put a timed scene in `brief`.** Both contradict the base and `_make`. Says directions "will be graded by an independent judge"; check that the judge still runs. "Press Create on direction B" is stale. |
| `prompts/skills/*.md` | Recipes for one kind of work | Not audited line by line. `ad` and `product-still` load on stills. |

## 0b. The chain, 10 real generations traced (live rows)

Still chain, from `app/api.py`'s Create job (the `work` body around line 6362):
Vesper's make_image prompt → `_enhance_generate_prompt` (**`enhance_system.txt`: "a
shot-prompt editor for a photorealistic AI video pipeline"**) → a scene row is saved (each
still writes a `shoot_concepts` row) → `brand_kits.dress` → on fal, `fal.generate_image`
dresses it again from the concept or project; on Gemini, `nano_banana.as_still_frame` wraps
the video text back into a still brief → the model.

| # | What | Model | Length | Added on the way | Lost |
|---|---|---|---|---|---|
| 1 | still c436 | Nano Banana | 326→1093 | `(0-5s)`, camera/motion words, 7 hex codes | – |
| 2 | still c438 | FLUX 1.1 | 314→1532 | `(0-5s)`, "handheld camera drift", brand block ×2, 12 hex | 9:16 asked, **4:5 drawn** |
| 3 | still c439 | FLUX 1.1 | 288→1239 | same | 9:16 → 4:5 |
| 4 | still c440 | FLUX 1.1 | 263→1548 | same | 9:16 → 4:5 |
| 5 | still c446 | Nano Banana | 396→1198 | same, 10 hex | 9:16 → 4:5 |
| 6 | still c447 | Nano Banana | 385→1328 | same | 9:16 → 4:5 |
| 7 | scene c437 | → keyframe | 392→726 | "Ultra-realistic grounded calm video"; the keyframe still was then sent "Steady, slow forward camera tracking" | – |
| 8 | scene c441 | scene writer | 678→895 | house avoid list | – |
| 9 | scene c442 | scene writer | 1139→1463 | house avoid list | – |
| 10 | scene c448 | scene → Grok | 884→998 | kit block on every shot, hex codes | **the person's whole AVOID line** (studio lighting, perfect skin, slow motion, cinematic depth of field, narrator voice) |

Reproduced fresh (no spend, enhancer only). Vesper wrote: "A close-up of a steaming ceramic
coffee cup on a wooden windowsill… Macro lens, sharp focus on the water droplets". The still
model would receive: `(0-5s) Avoid: … smooth commercial camera movement, … background music.
… Motion: Rising wisps of steam … Static shot with slight organic handheld drift.`

Where the damage happens: **the enhancer (stills), the kit dressing (twice), the frame
override, and the scene writer dropping a person's avoid list.** Vesper's own still prompts
are good: photographer's nouns, light, lens, no "cinematic". The layers after it make them
worse.

## 0c. Five briefs as a new user (Gemini 3 Flash, "Fast"; empty workspace; text only)

Run through the real `creative_guide.respond` with the composer's tools (not the browser;
see the note below). Full transcripts: `docs/qa/vesper-audit-2026-10-24/briefs_fast.json`.

| Brief | Turns to a make | What Vesper did | Where a person stalls |
|---|---|---|---|
| "a coffee cup on a rainy window" (Image) | 1 | Good photographer's prompt; proposed Nano Banana, "a sharp first look" | The message is the whole prompt again; the image model gets a different prompt (0b) |
| "help me make an ad" (Video) | **never (4 turns)** | Asked for a product photo **four turns in a row**; the choices loop ("I have a photo" → asks again) | No way forward without a photo: it never offers to draw a hero still first or to hunt references |
| attached photo + "make an ad with this" (Image) | 2 | One good question (three settings), then a make | Proposed Nano Banana for "UI text accurately": the wrong model for readable UI |
| "…in the style of Wong Kar-wai" (Video) | 2 | Researched the look (twice), drafted 3 timed shots | "In the style of Wong Kar-wai" stays in the prompt; timings written despite `_make` |
| "which model is best for a talking head?" | **never (4 turns)** | Called `list_models` 3 times, **never named a model**, named the internal tool `talking_photo` in backticks, asked for the photo again each turn | The question is never answered |

**The same five on "Reasoning"** (`briefs_reasoning.json`) do better on three:

| Brief | Fast | Reasoning |
|---|---|---|
| bare | 1 turn, 19 s | 1 turn, 6 s, no model proposed |
| "help me make an ad" | never (4 turns) | **never (4 turns)**: asks for the can's photo every turn |
| photo | 2 turns | 2 turns; a poster with invented on-image copy |
| named look | 2 turns; name left in, timings written | **1 turn; name gone, look in craft words, no timings** |
| talking-head question | never (4 turns) | **2 turns: answers, then opens the talking-photo card** |

So two of Fast's failures (rules ignored, the question not answered) belong to the default
tier. The photo dead end happens on both tiers. Fast is the default (`gemini_utils.DEFAULT_BRAIN`).
Whether Create should default to Reasoning is a cost and latency call for Mike. The five
briefs are not enough to settle it, but they point that way.

Settings line: with nothing picked, Vesper proposed a still model on every image make, and
the reason it gave was a guess (above). Length and frame were never explained. Frame is
silently overridden at draw time (0b). The prompt above Approve is readable, but it is not
what runs.

Note on method: the brief asked for a browser walk of `/studio`. I didn't run it on the
live site: "New session" there would replace Mike's saved working thread (the Gygler work),
and a fresh account needs a sign-up I can't do. The harness calls the same brain turn the
page calls. The UI half (the step card, how it can be edited) is judged from the code and the
saved live threads.

## 2. Model dialects

`prompts/models/*.md`: 11 craft notes plus `README.md`, each rule cited to the vendor or fal
(accessed 2026-10-24), each with a "NOT FOUND in primary sources" section. Primary sources
were thin for Grok video (xAI has no video guide), FLUX 1.1 and Kling 3 Turbo (the 3.0 guide
stands in). Nothing reads these notes yet. Where our pipeline goes against the vendors:

1. **Avoid lists written as "no …" in the positive prompt** (`scenes_prompt.txt` part 5,
   `enhance_system.txt` "stays … as an explicit negative"). Veo, Kling 4, Seedance, FLUX.2,
   Ideogram, Gemini and xAI all advise against this; only Wan and GPT Image fit it. Veo has a
   `negative_prompt` field we fill only when `PHANTRA_PROMPT_DIALECTS=1`, which is off on Fly.
2. **Constraints first.** `enhance_system.txt` orders negatives first and camera last. Every
   vendor that states an order leads with the subject, action or camera.
3. **Cut words inside one-clip prompts** ("hard cut to", in `shot_timeline_prompt.txt`).
   Kling 4 is multi-shot by default, and LTX image-to-video wants one continuous take.
4. **LTX** was trained on one objective, chronological paragraph of 150-220 words. Ours is
   labelled blocks that open "Ultra-realistic grounded … video". LTX also can't render brand
   text, yet `_make` says to carry brand names word for word.
5. **Wan 3.0 and Ideogram 4.5 rewrite our prompt** (fal's prompt expansion is on by default
   and we never turn it off).
6. Hex colour codes are fine on FLUX (BFL documents them). The damage in 0b is the kit block
   repeated, not the hex codes as such.

## 6. Ranked changes (re-ranked after the competitor capture, `competitor-capture-2026-10-24/comparison.md`)

The capture changed the order below rank 1, and added two changes. Rank 1 stands: every
competitor's approval card sends the prompt it shows, and ours is the only one that doesn't.

1. **The approved still prompt is the prompt that runs**, plus a record of the settings and
   the turn on every Create generation.
   - For stills: no video enhancer, the kit added once, and the frame from the prompt or a
     visible conflict.
   - It closes the defect in 6 of 6 traced stills, and it makes the success metric
     measurable.
   - The capture adds one thing: the card shows its frame, model and price as chips, the way
     invideo's and Runway's cards do.
   - → `docs/tasks/task-vesper-approved-prompt-runs.md`
2. **No photo → a hero still first, never "drop a photo" again.** All three competitors make
   something without a photo; invideo and Runway draw a start frame and animate it ("the
   subject isn't pinned down, so I'll lock the look with a start frame first").
   - Vesper asked for a photo on every turn of "help me make an ad", on both tiers. That
     brief never reached a make, and Wong Kar-wai on Fast stalled the same way.
   - The change: when a video idea has no reference, Vesper proposes a priced hero still. On
     a keep, that still becomes the scene's `refs[0]`. The reference gate itself is unchanged
     (a Library render is already a legal reference, `timeline.caption`).
   - This is a change to how the product behaves when nothing is uploaded, so it is **Mike's
     call**.
   - Prompt edits: `creative_guide.txt` (the photo reminder) and `_make.txt`, plus the step
     card's still -> scene hand-off.
3. **Answer a model question in one turn, by what the person starts from** (photo / clip /
   nothing; one take vs a series; a fixed voice). All three competitors do this. Vesper Fast
   went 3 turns and never named a model.
   - Fold `prompts/models/` into `list_models`' answer, so each pick carries a cited reason
     and a draft model.
   - Then turn on the per-model clip rules (`PHANTRA_PROMPT_DIALECTS`) one model at a time,
     behind the benchmark.
4. **When the person defers, decide and say what was locked** (invideo: "Locking it myself:
   brand is RISE … 9:16"), and name anything invented (a brand, a claim) as invented. One rule
   in `_make.txt` and `assistant_brain.txt`, together with resolving the question-count
   conflict (base vs `assistant_brain`). Closes "you decide" -> another question.
5. **Deny asks why** (new, from invideo): the step card's No opens six reason chips (prompt,
   references, model, settings, not the brief, revise first), recorded through
   `outcomes.record("discard", reason=…)`.
   - Live data has 4 discard events in total, so the keep-rate metric has almost no
     denominator signal.
   - Cheap, and it rides on task 1's recording fields.
6. **The account's brand kit as default context for an ad with no product named** (new, from
   Runway). With exactly one kit on the account, "help me make an ad" offers it ("An ad for
   Gygler?") instead of asking what is being sold.
   - Never put into an unrelated still.
   - Extends the existing "Kit: none ▾" pick; it does not replace it.
7. **The rest of the instruction conflicts**: timings (base vs `_make`), the message repeating
   the prompt, the stale names. Small edits.
8. **Keep the person's avoid list through the scene writer** (`scenes_prompt.txt`), with a
   check in `validate_concept` that warns when a typed `AVOID:` item is missing. 1 of 4 traced
   scenes.
9. **Not ranked, worth a test later:**
   - an ad's script table with a read time before any clip spend (invideo, Runway);
   - a continuity-locks block at the end of a timed clip prompt (Higgsfield: counts of cuts,
     speakers and legible text; "the same man, the same shirt");
   - an editable prompt on the card.

   None of them answers a measured failure yet.

## Not done, and what it would cost

- **Step 3, partly done (2026-10-24)**: briefs 1, 2, 8, 9 and 13 went through invideo Agent
  Two (Lite), Higgsfield Supercomputer and Runway Agent, word for word
  (`docs/qa/competitor-capture-2026-10-24/`). Nothing was rendered.
  - Spent: invideo 37.3 of its 50 credits, Higgsfield 6.14, Runway 0.
  - LTX Studio has no chat agent on the free plan (its Storyboard Builder needs an upgrade).
  - The other 15 briefs: Runway is free to chat and Higgsfield nearly free on Auto, so about
    2 hours of browser driving. invideo would need more credits (about 5-9 per brief on
    Lite).
- **Step 4** (20 briefs, Vesper's side on fal, Assist's on Higgsfield). From
  `src/fal.py`'s rows: 20 stills on Nano Banana Pro ($0.15) = $3.00. Then 20 clips:
  Grok 1.5 Lite at 480p, 5 s ($0.02/s) = $2.00; LTX 2.3 at its smallest legal pick, 6 s at
  1080p ($0.06/s) = $7.20; Kling 3 Turbo, 5 s ($0.14/s) = $14.00. **Vesper's side: $5 to $17
  on fal, before the 2.4× credit markup if run through the studio.** Higgsfield's side:
  20 stills + 20 clips; its credit prices vary by model, so price it in Assist before
  starting.
- **Step 5** needs people to judge blind. A judging kit (pairs shuffled, tool names hidden)
  can be built once step 4 exists.

Recommendation: ship rank 1 before the benchmark. A benchmark run today would mostly measure
the enhancer's damage to our stills, not Vesper.
