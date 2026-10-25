# Task: the still prompt the person approves is the prompt that runs

**From:** the Vesper output-quality audit, 2026-10-24 (`docs/qa/vesper-audit-2026-10-24.md`).
It was ranked first of six because it is the largest failure measured, and the only one in
every traced still.
**Branch:** `claude/vesper-approved-prompt-runs`. **No flag**: it fixes a broken promise, it
adds no feature.

## The failure, measured

A still from the Create box (`make_image`, a plan's image step, a typed prompt with Image
picked) goes through `POST /api/generate/run` (`app/api.py`, the `work` body). Between the
person's Approve and the model:

1. `_enhance_generate_prompt` rewrites it with `prompts/enhance_system.txt`, a **video**
   shot editor ("a photorealistic AI video pipeline"). It adds a `(0-5s)` window,
   "Motion:", "handheld camera drift", "smooth commercial camera movement" and
   "background music" to a still.
2. `brand_kits.dress` adds the kit's look. Then `fal.generate_image_from_prompt` adds it again
   from the concept (and `nano_banana.generate_from_prompt` from the project), so the block
   lands twice, with 8 to 12 hex codes.
3. The `aspect` form field (the settings line's frame) wins, while the prompt Vesper wrote says
   "9:16". The model is handed both. 5 of 6 traced stills asked for 9:16 and came out 4:5.
4. On Gemini, `as_still_frame` then wraps the video text back into a still brief.

Live, 6 of 6 Create stills traced (c436, c438-c440, c446, c447) show step 1. Prompts grew
from about 300 characters to 1,100-1,550. Reproduced fresh on 2026-10-24 with no spend. The
card says "the prompt you write is what they read above that Approve"
(`prompts/creative_guide_make.txt`), and today that is false.

## What to build

1. **A still from the Create box is sent as approved.** In `/api/generate/run`, when
   `output == "image"` and the prompt came from a step card (the composer sends the
   proposal's prompt), skip `_enhance_generate_prompt`. The prompt Vesper wrote and the person
   saw IS the brief. A still typed straight into the box with no brain turn behind it
   (Auto, a bare send) is also a prompt the person saw, so it is sent as typed too. This is
   the same rule as `/studio/image` (`docs/tasks/task-direct-generators.md`, "as typed: no
   enhance"). Keep the enhancer for video only. **Check first**: does a still still need the
   RAG `references` block the enhancer folded in? If yes, put it on the card where the person
   can see it, not into a hidden rewrite.
2. **Gemini stills: literal.** Pass `literal=True` (or a new `framing="still-brief"`) to
   `nano_banana.generate_from_prompt` for these stills. `as_still_frame` exists to un-video a
   video prompt, and this prompt is not one. Keep the reference captions (`REFERENCE_NOTE`):
   that part is about the pictures, not the words.
3. **The kit once.** Dress the prompt in exactly one place on this path: the route's
   `brand_kits.dress`, and pass `brand_kit=False` (or a `dressed=True`) to the renderer, or
   the other way round. Add a test that the words "BRAND LOOK" appear once in what a
   fal still and a Gemini still are sent, with a kit on the project AND named in the prompt.
4. **Show the kit's words on the card.** The kit block is what makes a branded still look
   on-brand, so it stays. The step card shows it under the prompt ("+ Gygler kit: look,
   palette, avoid list"), and the kit chip already turns it off. Nothing reaches the model
   that the card did not show.
5. **The frame from one place.** If Vesper's prompt names a shape ("9:16", "vertical",
   "square") and the settings line says another, the step card says so before Approve
   ("The prompt says 9:16; the frame is 4:5. Use 9:16?") with one tap to switch. Nothing is
   silently overridden. In `prompts/creative_guide_make.txt`: "pass the shape as `aspect`;
   never write a shape into the prompt". Vesper already has the `aspect` argument
   (thread 5 used it once). The card shows its frame, model and price as chips, the way
   invideo's and Runway's approval cards do (`docs/qa/competitor-capture-2026-10-24/`).
   Higgsfield's card and prompt disagreed on the frame (1.85:1 vs 16:9), which is the failure
   this step prevents.
6. **Record what the metric needs** on every Create generation, in `generations.params_json`
   and `generated_assets.metadata_json` (the provenance rule: no new columns):
   `door: "create"`, `output` (image|video), `autonomy` (ask|checkpoints|autopilot or null),
   `brain` (fast|reasoning), `model_picked_by` ("person" | "vesper" | "default"),
   `thread_id` and `turn_n` (the `assistant_projects` row and the turn index), and
   `sent_prompt_hash` beside the shown prompt's hash, so "sent as shown" can be checked on
   live rows. The composer already knows all of these when it posts.

## Not in this task

Ranked 2 to 5 in the audit and left for their own tasks: unsticking "help me make an ad" and
"which model…?" (they never reach a make); the timings and question-count conflicts between
`creative_guide.txt`, `_make.txt` and `assistant_brain.txt`; the scene writer dropping a typed
`AVOID:` line (c448); wiring `prompts/models/` into `list_models`.

## Success metric

On live use of the Create box, measured from the fields in step 6:

- **Sent as shown**: 100% of Create stills have `sent_prompt_hash == shown_prompt_hash`
  (kit words aside, which are shown as their own line). Today: 0 of 6.
- **Keep rate of Create stills** (any keep event, or reused as a reference): baseline
  **12%** on the default model (99 stills, 2026-09-04 to 10-23; the Vesper-era slice is too
  small to use alone). Target: double it within 4 weeks of live use, read per `model` and
  `model_picked_by`.
- **Re-rolls-to-keep**: baseline 0 in 27 of 28 kept chains, with 41 re-roll chains and 1
  kept on the second try. Target: the share of re-roll chains that end in a keep goes up
  (today 1 in 41), and fewer re-rolls per kept still.
- Report keep rate per `autonomy` and per `brain`. Today it can't be reported, which is
  step 6's reason to exist.

`src/outcomes.summary` (Stats on the dev console) should split by `door` once the field
exists.

## Verify by running it

- Start the API and the studio locally. Send "a coffee cup on a rainy window" with Image
  picked, approve the card, and read the generations row: the sent prompt equals the card's
  prompt, with no `(0-5s)`.
- With a kit project open, make a still. "BRAND LOOK" appears once in the sent prompt and the
  card shows the kit line.
- Ask for "a vertical poster…" with the frame set to 4:5. The card says the shapes differ
  before Approve.
- `venv/bin/python -m pytest tests/ -q -k "generate or composer or nano or brand_kit"`, then
  the full suite. A still costs credits, so the live check is one still on Mike's word.
