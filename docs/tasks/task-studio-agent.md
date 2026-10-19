> Phantra was named Zero Page until 2026-10-13. This is a dated record and keeps the names of its day.

# Task: the chat box becomes a studio agent

Mike, 2026-10-10: "Evaluate the current ai production studio, specifically the chat box
portion. I want it to have the same capabilities as an expert llm and match that of higgsfield
or runway" -- crawl and create reference photos, element sheets, effects, winning prompts for
one scene and several, and a better chat and main page. Rules he set: no changes without his
approval, build on what exists, research the competitors first.

After the research (Runway Agent, Higgsfield Supercomputer, invideo Agent Two, and the rest of
the field) he chose the order: **"take some out of the runway and higgsfield playbook first"**,
then **"go"** on the batch below.

## Ground rules for the session doing this

- One PR per numbered item; **stop after each item and report** before starting the next.
- Read `CLAUDE.md` first. Build on existing code; nothing here is a rewrite.
- Mike's design-first rule (the creature work): a change to how the studio LOOKS goes on a
  design canvas for his pick before code. Item 1 added one chip and one menu group in existing
  styles. Item 2 he told to go ahead on 2026-10-10 ("merge it and go ahead with item 2"): build
  it out of the step card he already picked (`still-step.tsx`), and show him the result at the
  stop. A look that is NEW -- the effects gallery in item 3 -- goes on the canvas first.
- No live spend while building: stub the model in the server process (the recipe is in the
  memory note `worktree-browser-verification`). A live check is Mike's call.
- `venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`, and in `web/`:
  `npx tsc --noEmit`, `npx eslint src`, `node --test tests/<file>.test.mjs`.

## What the research found (short)

- The chat is a careful one-step assistant: up to six read calls, then the turn ENDS on the
  first write (`creative_guide._respond_with_tools`). Runway and Higgsfield plan several steps,
  price each, and run them on approval.
- Most of the missing abilities already exist in the repo, wired to the Claude Desktop connector
  and not to the in-app chat: `src/effects.py`, `prompt_craft`, prop and place sheets, and the
  studio MCP v2 tools (cancel, edit a clip, reframe, join clips).
- The competitors' "expertise" is a shelf of named recipes the agent reads on demand, not a
  bigger model.
- Zero Page is ahead on: Ask-first as the default, screened and attributed web references,
  per-project memory, free thinking.

## Progress

| item | state | PR / notes |
|---|---|---|
| 1. Skills | built 2026-10-10 | see "As built" below |
| 2. Plan with step cards | built 2026-10-10 | see "As built" below |
| 3. Effects in chat | built 2026-10-10 | see "As built" below |
| 4. "Continue" actions on results | built 2026-10-10 | see "As built" below |
| 5. Draft, then finish | built 2026-10-11 | see "As built" below |

The second batch -- invideo's playbook (Mike, 2026-10-11: "go ahead with the invideo playbook
next"), in the order it is being built:

| item | state | notes |
|---|---|---|
| 6. Out of credits, said with a way out | built 2026-10-11 | see "As built" below |
| 7. The plan card: total against the balance, every field editable, stills first | built 2026-10-11 | see "As built" below |
| 8. A role on every attached reference | built 2026-10-11 | see "As built" below |
| 9. Product facts from a pasted link | built 2026-10-11 | see "As built" below |
| 10. Research by name, saved to the project's look | built 2026-10-11 | see "As built" below |
| 11. A short number on every result, usable in a sentence | built 2026-10-11 | see "As built" below |
| 12. The brain proposes a model per step | built 2026-10-11 | see "As built" below |
| 13. An Explore / Make switch per project | built 2026-10-11 | see "As built" below |
| 14. Spend modes and a credit cap per project | not started | the largest; see the open decision |
| 15. A casting skill for invented characters | held for Mike | reverses a standing rule; see below |

## The batch

1. **Skills.** Named recipes the brain loads when needed, also listed under `/`. Runway's slash
   skills, Higgsfield's skill files.
2. **Plan with step cards.** One message gets a numbered plan; each step shows model, prompt and
   credits and can be approved, edited or skipped; editing a step re-runs only that step, and
   stopping charges only finished steps. Runway's "Ask before generating", Higgsfield's plan and
   Approve. On the way it fixes two things seen on the live page on 2026-10-10: a failed draw
   that read "Done · Approved", and a raw provider error ("User is locked. Reason: Exhausted
   balance...") shown on a tile.
3. **Effects in chat.** `/effects` opens a gallery that never runs anything by browsing; a pick
   puts a priced card in the thread. Built on `src/effects.py`.
4. **"Continue" actions on every result.** Upscale, Edit, Variations, Make element, Turn into a
   shot, Download, and the price on the send button.
5. **Draft, then finish.** A cheap low-resolution clip first; full price only for the keeper.

## Decisions

Made:
- Runway and Higgsfield patterns first; invideo's after (Mike, 2026-10-10).
- No session list: a conversation is working memory and projects hold the history (Mike's
  2026-10-02 call; proposed by mistake in the first plan and withdrawn).
- Thinking stays free (Mike's 2026-10-08 call); invideo bills it and is disliked for it.

Open, for Mike:
- **Item 15, invented characters, is held.** It was on the invideo list he approved as a whole,
  but `prompts/stages/cast.md` says a face is always an Element from real photos, and building
  it reverses that. It is last in the batch and is not started without his yes.
- **Item 14's shape.** Recommended and assumed unless he says otherwise: three modes (always
  ask, ask before anything that makes a clip, always allow), Ask first staying the default, and
  a credit cap per project that no mode can pass.
- **Rendering a clip from the chat.** Should a plan's last step buy the clip, through the same
  approve body and signed quote the Queue and the claude.ai connector use? Until he says, a plan
  ends at "Send to Queue".
- **Auto mode.** invideo's three states (always allow / ask before video / always ask) with a
  credit cap per project, Ask-first staying the default -- recommended, not decided.
- **Invented characters.** `prompts/stages/cast.md` says a face is always an Element from real
  photos, never a generated stranger. Casting an invented person (invideo, Higgsfield) reverses
  that; not built.
- **Sheet layouts and styles.** The character sheet is the landing page's five-panel prompt
  "exactly as is" (Mike, 2026-10-09). Other layouts (expressions, outfits) would be options
  beside it, never a change to it; not built.

Later (invideo's list, and the small fixes): a role on every attached reference, research by
name saved to the project's look, product facts from a pasted link, a casting skill, a model
proposed per step, an explore / execute switch per project, a short number on every result
tile, a top-up link when a balance runs out mid-job, markdown in answers, Stop while thinking,
directions and questions drawn in the composer, stills made inside a project filed under it.

## Item 1 -- Skills: as built (2026-10-10)

`src/skills.py`, `prompts/skills/*.md`, `prompts/creative_guide_skills.txt`; the `CLAUDE.md`
entry "THE BRAIN HAS A SKILL SHELF" is the description of record.

- **Five skills,** in the studio's own words: `character-sheet`, `single-shot`, `multi-shot`,
  `product-still`, `mood-board`. Each uses only tools the brain already has; nothing new spends.
- **The brain loads one** with `load_skill`, a read tool published beside `find_references`;
  the shelf's index is in the instructions only when that tool is offered.
- **The person picks one** from `/` in the composer: a chip on the box, the Image | Video switch
  follows the skill, and that one send carries `skill=<name>` with the recipe already loaded.
- **The thread says which skill an answer used** ("used the Mood board skill"), whichever way it
  was loaded, and the person's own bubble carries the pick.
- What every composer and dock turn now carries: the shelf's index in the instructions (about
  1,400 characters) and one more tool. A turn that is offered no tools is what it was, and so is
  every turn when the shelf is empty.

Checked: `tests/test_skills.py` (shelf, tool, turn, routes) and `web/tests/skills.test.mjs`;
then in a browser against the real routes with the model stubbed in the server process -- the
menu, the chip, a picked send, a load the brain made on its own, the saved thread after a
reload, and 375px. No real model call was made, so **how well the live brain follows each
recipe has not been measured**; that is the first thing to watch on real turns.

Deliberately left out of item 1:
- Per-model prompt dialects (Kling / Veo / Seedance / LTX each read a prompt differently). The
  scene writer is not told which model will render, and the composer has no video model picker;
  this belongs with item 2, where each step names its model.
- A write tool for a project's LOOK. The mood-board skill writes the look into the brief and
  points at the LOOK box in the project's workspace.
- The dock's conversation does not offer the `/` menu; the brain can still load a skill there.

## Item 2 -- Plan with step cards: as built (2026-10-10)

`src/make_plan.py`, `prompts/creative_guide_plan.txt`, `web/src/lib/make-plan.ts`,
`web/src/components/studio/make-plan-card.tsx`, the `runPlan` block in
`web/src/app/studio/page.tsx`; the `CLAUDE.md` entry "THE BRAIN PROPOSES A PLAN" is the
description of record.

- **One answer, several makes.** `make_plan` takes two to eight steps: a still, a scene, a
  character sheet, keeping hunted references, a scene's keyframes, sending a scene to the
  Queue. Several scene steps in one plan is how a multi-scene piece is written from one message.
- **A checklist in the thread.** Each step says what it is, what it will do, why, and what it
  costs. Start runs it; a step that costs credits stops for its own Approve beside its price;
  "Approve all" covers the steps whose price is on the card. Keyframes are priced once their
  scene exists, so they always ask (with Ask first on).
- **Edit, skip, bring back.** Before a step runs, or after: editing a step that ran re-runs that
  step only. Skipping a scene takes its keyframes and Queue steps with it.
- **Stop and failure.** Stop ends the wait on the running make; a failed step stops the plan
  where it is, says why in plain words, and offers Try again.
- **Results are ordinary turns** under the card: the still's own step card and tile, the scene's
  shot tiles with every action they always had. A still a later step is "held to" rides along
  as a reference.
- **It never renders a clip.** A plan's last word on a scene is the Queue.
- **Fixed on the way** (both seen live on 2026-10-10): a still that failed at the provider no
  longer reads Done, and the provider's raw error no longer reaches the page (`src/failures.py`,
  `web/src/lib/made-state.ts`).

Checked: `tests/test_make_plan.py`, `tests/test_failures.py`, a new case in
`tests/test_pipeline_tabs.py`, `web/tests/make-plan.test.mjs`, `web/tests/made-state.test.mjs`;
then in a browser against the real routes, jobs, concept rows and keyframe approve with every
model stubbed in the server process: Ask first (Start, per-step Approve, Approve all), a draw
that failed with the live 403 text and its Try again, Edit and Skip, a reload mid-plan, 375px,
and Auto with Stop and Resume. **No real model call was made**: whether the live brain proposes
plans when it should, and writes steps that stand on their own, is the first thing to watch.

Known limits:
- The loop runs in the page. A plan left mid-step is picked up on return (each step follows the
  turn its result went into) but does not carry on by itself; the card offers Resume.
- With Auto on, a plan spends through every step without a click, as a single make does. The
  open decision on a per-project credit cap (above) matters more now.
- `uses` holds a step to an earlier STILL only. A sheet step's character reaches a later scene by
  being named in it, the way any Element does.
- Plain failure wording is applied to the still route. Keyframes, sheets and Queue renders still
  show their adapters' own text.
- The dock shows a plan's summary line and nothing else; a plan is run from the composer.

## Item 3 -- Effects in chat: as built (2026-10-10)

`app/api.py` (`/api/effects`, `/effects/quote`, `/effects/run`), `guide_tools.EFFECT_SPECS`,
`prompts/creative_guide_effects.txt`, `web/src/lib/effects.ts`,
`web/src/components/studio/effect-gallery.tsx` and `effect-step.tsx`; the `CLAUDE.md` entry
"EFFECTS IN THE CHAT" is the description of record.

- **Thirteen effects, four tabs,** all from `src/effects.py`, the table the Claude Desktop
  connector already used: edit an image by instruction (three models) or cut out its
  background; animate a still with a Kling or PixVerse template (98 and 154 looks) or a named
  camera move (20); and finish a clip -- upscale or smooth it, add sound, give it a new shape,
  remove its background.
- **`/effects` opens a gallery above the box.** Browsing runs nothing. Each row says what it
  takes, what it gives and what it costs from; a row with nothing to act on yet is greyed
  with the reason.
- **A pick puts a card in the thread.** It shows what it will act on (what is attached to the
  box, else the newest result that fits), its choices, its words, and Approve beside the
  price. The price is asked from the server whenever a choice changes, and Approve sends that
  number back: the effect runs at the price shown or is refused.
- **The brain can propose one** from a plain sentence ("remove the background", "give it a
  slow camera move"). It looks the exact template and camera names up first, and its options
  and words land on the same card, still editable. It never picks what the effect acts on.
- **Results chain.** A still, and what an effect made, each carry their render id, so the
  next effect can act on them: still -> template clip -> sound on that clip was walked.
- **Effects always ask.** The Auto pill does not cover them.
- **Failure** reads as one plain sentence with "Nothing was charged", and the card offers
  Approve again.
- Found and fixed on the way: a clip an effect made read "Not made" (the rule that a still
  with no image is a failure did not know about clips); the effect job's result wrote over
  the job's own `kind`; a finished card said "Pricing..." after a reload.

Checked: `tests/test_effects_studio.py`, a new case in `tests/test_pipeline_tabs.py`,
`web/tests/effects.test.mjs` and new cases in `made-state`, `job-feed` and `skills`; then in a
browser against the real routes, checks, quote, job registry and Assets rows with the
provider and the model stubbed in the server process: the gallery and its tabs, a Kling
template on a still, sound on the clip that made (priced from the clip's measured length), a
failed run and its Approve again, the brain's two paths, a reload, and 375px. **No real model
or provider call was made.** Unmeasured: whether the live brain reaches for an effect only
when asked, and every effect's real output.

The look: the design-first rule says a new look goes on a canvas before code. The gallery was
built out of parts Mike already picked -- the slash menu's panel and the still step card --
and is shown to him at this stop. If he wants a different look, it changes before merge.

Known limits:
- No preview per template: 252 template names are words in a list with a search box.
  Higgsfield and Runway show a thumbnail or a loop for each; that needs media made per template.
- An effect is not a plan step, and the dock does not offer effects.
- **What an effect can act on is what this conversation holds:** images attached to the box,
  and results in the thread. A clip rendered from the Queue is on the Assets wall but the
  composer cannot pick it yet, so "Finish a clip" works today only on a clip an effect made
  here. Item 4's actions on the Assets wall are where that closes.
- Each row is called by the effects table's own label, which names the model
  ("Add sound (MMAudio)").
- Lip sync, relight and frame interpolation by RIFE / FILM are still out of the table, for the
  reason `src/effects.py` gives: a price or an input could not be verified.

## Item 4 -- "Continue" actions on every result: as built (2026-10-10)

`web/src/lib/continue.ts`, `ContinueRow` in `web/src/components/studio/composer/turns.tsx`,
`continueOn` / `variation` in `web/src/app/studio/page.tsx`, two routes in `app/api.py`
(`GET /api/assets/generated/{id}` and `.../download`), `storage.download_url_for_key`; the
`CLAUDE.md` entry "EVERY RESULT SAYS WHAT IT CAN BE CARRIED ON TO" is the description of record.

- **One row under every finished result, and a More menu.** A still: Edit image, Variation,
  Animate, Turn into a shot; under More: Remove background, Camera move, Use as reference,
  Make element, Download, See it in the Library, Open the canvas, Reuse prompt. A clip:
  Upscale, Add sound, Reframe; under More: Remove background, Open in the editor, Download,
  the Library. A written scene keeps the three it had.
- **Nothing in the row spends.** An effect opens item 3's priced card; a Variation is a still's
  step card. Their Approve is the click.
- **The action is on that result.** "Edit image" under an older still edits that still, not
  the newest one.
- **Variation** draws the same prompt, shape and references again, on the model the picker
  shows now.
- **Download saves the file.** The old button opened it in a tab.
- **The Library can send a render to effects.** Its Effects button opens the composer's
  gallery on that render. This closes item 3's limit: a clip rendered from the Queue can now
  be upscaled, reframed or given sound.
- **The send button says what a send can spend:** nothing, except a still with Auto on, and
  then the credits are beside the button.
- Fixed on the way: a still that only exists on this machine's disk could not be a reference
  or an element's photo; a failed photo description put the model's raw error on the page.

Checked: `tests/test_continue_actions.py`, updated cases in `tests/test_api.py` and
`tests/test_effects_studio.py`, `web/tests/continue.test.mjs` and a new case in
`effects.test.mjs`; then in a browser against the real routes with the provider and model
stubbed in the server process: the row and menu on a still and on a clip, Edit image bound to
its still, a Variation approved and drawn, Animate opening the gallery on the still, Make
element saving from a still, the download answering as an attachment through the proxy, the
Library's Effects round trip ending in a finished clip, the price beside send with Auto on,
and 375px. **No real model or provider call was made.** Download's signed link was checked against the
real bucket from this machine (a 16-byte read: the bucket answered 206 with
`Content-Disposition: attachment`); the route end to end on the live site, through the proxy,
is the remaining check.

The look: built from the action buttons and the option menus the composer already has; shown
to Mike at this stop.

Known limits:
- A scene has no new actions. Its keyframes are the Queue's priced button and a plan's step.
- No image upscale: the effects table has none (its upscale is for clips).
- A Variation is one more take, not four, and uses the model picked now rather than the one
  that drew the first.
- Results on the dock and in a project's workspace do not have the row; it is the composer's.
- "Price on the send button" is only ever a still's price. A scene is free to write, and a
  clip is bought in the Queue.

## Item 5 -- Draft, then finish: as built (2026-10-11)

`src/drafts.py`, `fal.draft_resolution`, the `finish` flag on the effects routes in
`app/api.py`, `GET /api/cut/ready`'s `drafts`, the Draft toggle and Finish buttons in
`web/src/app/studio/queue/page.tsx`; the `CLAUDE.md` entry "DRAFT, THEN FINISH" is the
description of record.

**Moved the same day (2026-10-11, `docs/tasks/task-higgsfield-shape.md`):** the Queue page
is gone. The Draft toggle is on the scene's Render card
(`web/src/components/studio/render-card.tsx`) and the Finish buttons are on the Renders
page's "Ready to cut" cards (`web/src/app/studio/renders/page.tsx`). Where the notes below
say "the Queue", read those two places. Nothing about the prices or the routes changed.

The precondition, done first: fal's rate cards were read again on 2026-10-11. Wan 3.0 is
$0.05 / $0.10 / $0.20 per second at 480p / 720p / 1080p and Seedance 2.5 is $0.2205 / $0.4730 /
$1.164, both as the table already had them. Seedance 2.5's schema takes 1080p and has no seed.

- **Draft is the Queue's own approve at the model's cheapest resolution.** The card shows
  "Draft first · 480p · cheaper" under the renderer; turning it on changes the price on the
  one Approve button, which then reads "Draft · 3 shots · 636 credits". Nothing else spends.
- **Offered only where it is really cheaper.** Today: Wan 3.0 and Seedance 2.5. The other
  seven models have no lower-priced tier than the one they render at by default, so their
  cards show no Draft.
- **Finish keeps the take.** A drafted scene lands in "Ready to cut" marked "all drafts ·
  480p" with a Finish button per shot. The first click shows the price; the second upscales
  that clip (2x) and puts it on its shot in the draft's place. The draft stays in the Library.
- **Finish is the upscale effect from item 3 with a target**, not a new way to spend: the same
  quote, the same "runs at the price shown or not at all", the same hold.
- The Library says when a clip is a draft and points at the Queue.

What it costs, measured on the stub with the real price code (five-second shots):

| | draft | finish | draft + finish | 720p outright | 1080p outright |
|---|---|---|---|---|---|
| Wan 3.0 | 60 | 96 | 156 | 120 | 240 |
| Seedance 2.5 | 265 | 96 | 361 | 568 | 1,397 |

So on Wan 3.0, drafting saves credits only when some takes are thrown away, or when 1080p was
the aim. On Seedance 2.5 it saves on every shot. A finished clip is 960x1708, between 720p and
1080p, not native 1080p.

Checked: `tests/test_drafts.py`, a new case in `web/tests/render-choice.test.mjs`; then in a
browser against the real Queue approve path (spend gate, cap, generations rows, clips attached
to their parts, Assets rows) with only the provider's HTTP call replaced by a local test
clip: the toggle and its price on Wan 3.0 (240 -> 120) and Seedance 2.5 (1,365 -> 636), no
toggle on a model without a draft, a draft approved and rendered, the scene listed with its
drafts, a Finish priced (96) then run, the finished clip on its shot and filed under the
scene, and the Library's label. **No real render or upscale was made.**

Known limits:
- **The upscale's price is read the dear way.** fal prices Topaz by output size in three
  tiers and does not say which dimension it measures. A portrait 480p draft doubles to
  960x1708; the table treats that as "above 1080p" ($0.08 a second). If fal bills it as
  "720p to 1080p" the real cost is a quarter of that, and the customer is still charged the
  96. The first real finish is the check: compare fal's invoice line with the quote.
- Two models have a draft. Cheaper sibling models (Veo Fast, a Kling standard tier) would
  widen that, and each needs its table row checked first.
- There is no "render this one shot again at full resolution". Finish is the upscale only.
- Finish is on the Queue page. The composer and the claude.ai connector cannot finish a
  draft, though the connector can already approve at the draft resolution.
- A cut already made in the editor keeps the draft clips it was built from. Export again, or
  swap the clip in the editor.

## Item 6 -- Out of credits, said with a way out: as built (2026-10-11)

`web/src/lib/out-of-credits.ts`, `web/src/components/studio/top-up-link.tsx`, the toast in
`shell.tsx`; `tests/test_out_of_credits.py` ties the page's detection to the server's own
sentences. The `CLAUDE.md` entry "AN EMPTY BALANCE IS SAID WITH A WAY OUT" is the description
of record.

invideo's loudest complaint is the agent going quiet at zero. Here the server already said so
in a sentence of its own; the page showed it as one more red line with nothing to press.

- A send refused for an empty balance marks its own bubble "Not sent: you are out of credits"
  with the door beside it, and the words go back in the box.
- A still, an effect, a sheet or a plan step refused mid-job shows the same door beside its
  failure line, and its card still offers Approve again for after the top-up.
- Any page's error toast about the balance carries the door as its action.
- The door is named as the credit pill names it ("Buy credits", or "Choose a plan" for an
  account with none) and goes where the pill goes.

Checked: `tests/test_out_of_credits.py`, `web/tests/out-of-credits.test.mjs`; then in a
browser on a stub server with a real, non-exempt test account: a send at zero balance (the
real 402), and a still refused in the server's own words.

Known limits: the page still prints the server's sentence as written ("-- top up to
continue"); a plain rewording of it is a server change that touches every test that quotes it.
The dock does not show the door.

## Item 7 -- The plan card: as built (2026-10-11)

`web/src/lib/make-plan.ts` (`budget`, `fieldsOf`, `cleanEdit`), `make-plan-card.tsx`,
`prompts/creative_guide_plan.txt`.

- **The plan is held against the balance before Start.** The card's last line reads "Still to
  spend: 10 credits · you have 25", and when it does not fit, "you have 4, 6 short" with the
  way to add credits beside it. Start stays available: the free steps can still run.
- **Every field of a step can be changed,** not only its words: a still's shape, a scene's
  length, a sheet's name and outfit. Changing one on a step that already ran sends that step
  back, like editing its words does. Each step already had Skip.
- **Stills before clips.** The brain is told to settle a look on a still before a scene is
  written to it, and to add no still when a look already exists.

Checked: new cases in `web/tests/make-plan.test.mjs` and `tests/test_make_plan.py`; then in a
browser on a stub server with a 25-credit test account: the line against the balance, a
scene's length changed to 14s and a still's shape to 9:16, both marked edited.

Known limits: the still-first rule is an instruction to the brain, so whether it follows it is
only measurable on real turns. A scene's shot count is still set by its words, not a field.
The model that draws a still is the one picked in the box, not a field on the step (item 12).

## Item 8 -- A role on every attached reference: as built (2026-10-11)

`src/ref_roles.py`, `web/src/lib/ref-roles.ts`, `composer/ref-role.tsx`; the `CLAUDE.md` entry
"EACH ATTACHED REFERENCE SAYS WHAT IT IS FOR" is the description of record.

- **Each reference in the box has a "for…" control**: Subject, Product, Place (what the picture
  is of) or Light, Palette, Framing, Style (only that is taken from it). No role means it reads
  as it always did.
- **The role is the caption the model reads before that picture**, written in code: "use ONLY
  its lighting... Do not copy its subject, its place or its framing".
- **A picture that only lends its look is never first.** The first reference is what a
  keyframe and a clip anchor on; a light reference there becomes the subject.
- Roles are saved with the box, sent with every request (the brain, a still, a scene), and
  stored on a scene's shot beside its references, so its keyframes read them too.
- **Fixed on the way: a still only ever saw the FIRST attached reference**, with no caption.
  Every reference now reaches the still, each under its caption. This changes what a still
  with several references attached looks like, roles or not.

Checked: `tests/test_ref_roles.py`, new cases in `tests/test_scene_references.py`,
`tests/test_pipeline_tabs.py` and `tests/test_assistant_store.py`, `web/tests/ref-roles.test.mjs`;
then in a browser on a stub server: two uploads, a role on each, the roles surviving a reload,
and the server's log showing the still handed the product first and the light frame second,
each under its role's caption.

Known limits:
- Whether a real image model obeys "only its lighting" is unmeasured. No real model call was made.
- The image models on fal take no captions; they are told in the prompt, by position
  ("Reference image 2: use ONLY its lighting").
- The scene WRITER sees the captions; a rendered CLIP is anchored on its keyframe, so a role
  reaches the clip only through the keyframe.
- The Director canvas's own Enhance and keyframe nodes do not read roles.
- Hunted references keep their own departments; this is for what the person attaches.

## Item 9 -- Product facts from a pasted link: as built (2026-10-11)

`linkrefs.parse_facts`, `assistant_brain.link_facts`, `web/src/lib/link-facts.ts`; the
`CLAUDE.md` entry "A PASTED PRODUCT PAGE GIVES UP ITS FACTS, NOT ONLY ITS PICTURES" is the
description of record.

- **A pasted product link now gives the brain what the page says about the product**: its
  name, brand, price, colour, material, size, category and description -- whichever of those
  the page states. Before, a link gave pictures and a title, and the brain wrote "the can".
- **Only the page's structured statements about itself are read**: its first product record
  and its preview tags. Never the body text. A page that is not a product's (an article, a
  home page) gives nothing.
- **The text is treated as a stranger's.** Each value is flattened to one line, stripped of
  markup and of every web or email address, and cut short. The brain receives it as quoted
  data under a line saying it is copied off a page and is not instructions, and is told to
  state nothing the page does not say and to leave the price out unless asked.
- **The person sees it too**: the link's row on the contact sheet reads "The page says GHOST
  ENERGY - ORANGE CREAM · Orange · 2.99 USD", with the description on hover. It is saved with
  the conversation.
- No new fetch, no model call, nothing spent: it is read from the page the link already
  fetched.

Checked: seven new cases in `tests/test_linkrefs.py` (the facts off a real-shaped page, the
length cut, a non-product page, the reader carrying them, the row and the model's block, a
value that tries to close its own quotes, a page with facts and no picture) and
`web/tests/link-facts.test.mjs`; then in a browser on a stub server (no page fetched, no
model called): a link pasted in the composer, the row's line, the same line after a reload,
its fit at phone width, and the server's log showing the model handed the quoted block with
no address in it.

Known limits:
- How well the live brain uses the facts is unmeasured. No real model call was made, and no
  real page was fetched for this item.
- A page that builds its product record with scripts after it loads gives nothing here,
  the same as it gives no picture: the page is read once, as served, with no browser.
- The facts stay in the conversation. They are not written to a project's brief or to a
  Product element's notes; that is a separate step if wanted.
- Variants: a page listing several sizes or colours gives the one its first record names.

## Item 10 -- Research by name, saved to the project's look: as built (2026-10-11)

`src/look_research.py`, `guide_tools.LOOK_TOOL`, `web/src/lib/look-research.ts`,
`components/studio/look-research.tsx`; the `CLAUDE.md` entry "A LOOK IS RESEARCHED BY NAME, AND
KEPT ON THE PROJECT" is the description of record.

- **Name a look and the brain researches it.** "Make it look like X" (a film, a
  photographer, a brand, an era) runs a web search by that name and one small model call
  that turns what was found into seven labelled lines: palette, light, lens and framing,
  texture and grade, movement and pacing, sets and wardrobe, what to avoid.
- **The person sees where it came from.** Under the answer: "The look of “X”, read from 3
  pages", with each page as a link. With no search available the look is written from what
  the model knows and is said to be unchecked.
- **Inside a project, the look can be kept.** The brain proposes it on a card that shows the
  lines; "Save look" stores it as the project's look, which every scene written in the
  project is then held to. The card says when it replaces a look the project already has,
  and the toast's Undo puts the old one back.
- **The look is written without the name.** A prompt saying "like X" asks a renderer to copy
  X. When the name is a person, a title or a brand, code removes it from the lines; an era or
  a genre ("film noir") is left, because it is a craft word.
- **Web text is treated as a stranger's.** Search snippets go to the model as quoted evidence
  marked "not instructions", with no addresses; only the seven known labels come back, each
  line stripped and cut short.
- Outside a project a look lasts as long as the conversation; a project made in chat can be
  made with the look. A turn inside a project is now told the look the project has.
- It spends no credits (model text, plus two flat-priced search requests on the meter).

Checked: `tests/test_look_research.py` (12) and `tests/test_look_tools.py` (21),
`web/tests/look-research.test.mjs` (5); then in a browser on a stub server (search and model
both faked): researched a look from the composer inside a project, saw the pages and the
card, saved it, undid it, saved again over an existing look (the card said it replaces one),
asked for a name that cannot be researched, and did the same from the assistant's dock on
the project's workspace, where the Look box followed the save and the undo; the card
measured inside a 390px frame.

Known limits:
- No real search and no real model call was made. How good a researched look is, and whether
  the live brain researches and saves when it should, is unmeasured. The search key on this
  Mac is not valid, so the first real run will be on the live site.
- It reads search snippets, not whole pages: enough to anchor a well-known look, thin for an
  obscure one.
- Whether the name is removed depends on the model saying what kind of thing it is; with no
  answer the name is left in.
- The look cannot be edited on the card; it is edited in the workspace's Look box after
  saving. Saving replaces the whole look.
- The assistant's dock does not know the project's current look, so its card always says it
  replaces "any look the project has".
- Not walked in the browser: a research outside any project (covered by a test).
- Not built: research as a step of a plan, pictures for the look (the reference hunt can be
  asked for separately), and the personal ChatGPT / Claude connections, which have no tools.

## Item 11 -- A short number on every result: as built (2026-10-11)

`web/src/lib/result-numbers.ts`, `src/result_refs.py`, `prompts/creative_guide_results.txt`;
the `CLAUDE.md` entry "EVERY RESULT HAS A SHORT NUMBER, AND A SENTENCE CAN POINT AT IT" is the
description of record.

- **Every still, clip and scene in the conversation has a number**, shown as `#3` at the head
  of its line. It is given once and never changes; a new conversation starts at 1.
- **A sentence can point at one**: "make 1 warmer", "like 2 but at night", "turn #5 into a
  shot". The brain is told the numbered list with each message and passes the number back
  with what it proposes.
- **The studio binds the number to the actual picture.** An effect's card reads "On #1"; a
  still's card reads "Held to #2"; a scene is written with the named stills as references.
- **A number that cannot be used is refused, in words.** "upscale 2" when 2 is a still is
  answered "#2 is a still and this effect takes a clip", and no card appears. A number that
  does not exist is answered the same way.
- **Clicking a number puts it in the box** as `#3`.
- **Fixed on the way:** an earlier picture attached as a reference reached the image model
  with no caption at all. It now says what it is: keep its subject and look, except where the
  prompt asks for a change.

Checked: `tests/test_result_refs.py` (14) and `web/tests/result-numbers.test.mjs` (7); then in
a browser on a stub server (brain scripted, no model or provider called): two stills numbered
1 and 2, "make 1 warmer" (the card bound to #1 though #2 was newer), its result numbered 3,
"upscale 2" refused in words, "like 2 but at night" (card "Held to #2"), "like 1 but at dawn"
(the server log showed the still handed over under its caption), "turn #5 into a shot" (the
scene written with one reference and numbered 6), a click on #1, the numbers after a reload,
and the layout inside a 390px frame.

Known limits:
- No real model was called, so how reliably the live brain reads "3" as a result and not as
  "3 seconds" is unmeasured. The paragraph tells it to go by what is plainly pointed at and to
  ask when it could be either.
- The floating assistant does not show the numbers or send the list; this is the composer's.
- A scene has a number but no tool takes one: the brain can talk about it or write a new scene
  from its prompt, and rendering is still the scene's own Render card.
- A plan's steps do not take result numbers.
- In a long conversation only the newest 40 results are listed to the brain.

## Item 12 -- The brain proposes a model per step: as built (2026-10-11)

`src/model_menu.py`, `prompts/creative_guide_models.txt`, `web/src/lib/step-model.ts`; the
`CLAUDE.md` entry "THE BRAIN PROPOSES THE MODEL A STEP IS MADE ON" is the description of record.

- **The brain can read the studio's own model list** (a new read tool): every still model and
  clip model, each with the line the studio already keeps about it and what it costs. It is
  the same list the picker and the public catalogue draw from; nothing new was written about
  any model.
- **A still's card shows the model it will be drawn on**, with the brain's reason when it
  proposed one ("Ideogram 4.5 proposed: the words must read"). The person can change it on the
  card, and the price beside Approve follows.
- **A model that takes no references says so** on the card when pictures are attached.
- **Auto never spends more than the send button said.** A proposed model that costs more than
  the picked one waits for Approve; one that costs the same or less draws at once.
- **A plan prices each still by its own model**, and the model is one of the step's editable
  fields.
- **A scene's proposed model is where its Render card opens.** The card says it was proposed
  and why; the person still chooses the renderer and presses the priced button.
- **In a plan, the render step is priced on the proposed model.** It still waits for the
  person's own click beside that price, and says which model it is and where to pick another.

Checked: `tests/test_model_menu.py` (15), `web/tests/step-model.test.mjs` (6) and two new plan
cases; 726 server tests around the Guide, pricing, providers and scenes; then in a browser on
a stub server with a charged test account (brain scripted, the fal still draw faked):
- a poster proposed for Ideogram at 15 credits while the picker held Nano Banana at 10; the
  model changed on the card and the price followed; the still drawn on the model chosen;
- a scene proposed for Kling: the server stored it, and its quote was on Kling though the
  scene was written for LTX;
- a plan with a model on each step, a step's model changed in its Edit form, the total
  following, the stills drawn on the right models, and the render step priced on the proposed
  Veo with the Render card opening on it and saying so;
- Auto on: a dearer proposal waited, a same-price one drew at once;
- the no-references warning with a picture attached; the layout inside a 390px frame.

Known limits:
- No real model was called. Whether the live brain proposes sensibly, or too often, is
  unmeasured; the studio's one-line notes are all it has to go on.
- A plan's render step cannot change its model in place; the scene's own Render card can.
- The floating assistant does not propose models.
- Keyframes and the character sheet are drawn on fixed models; nothing is proposed for them.

Seen on the way, not part of this item: two balance reads at the same moment deadlocked in the
database once on the stub server (`billing.balance` creates its tables on every read). The page
recovered on its next read.

## Item 13 -- An Explore / Make switch per project: as built (2026-10-11)

`src/guide_tools.py` (`SWITCH_TOOL`, `session(explore=)`), `prompts/creative_guide_explore.txt`,
`web/src/lib/explore.ts`, `web/src/components/studio/explore-switch.tsx`; the `CLAUDE.md` entry
"A PROJECT CAN BE SWITCHED TO EXPLORE, WHERE A SEND ONLY TALKS" is the description of record.

Mike picked option A off the design canvas ("Explore / Make Switch"): the switch on the project
row above the box. He was asked whether new projects should start in Make and whether the
exploring talk should be saved to the project's history and answered neither, so the
recommended defaults stand: a new project starts in Make, and history is as it was.

- **A project has two states, Explore and Make.** The switch sits on the project row above the
  box, and in the workspace's project panel. It is the project's own setting: it follows the
  project to any browser. Every project that existed before is in Make.
- **While a project explores, a send only talks.** The server reads the project and hands the
  brain nothing that makes: no still, scene, sheet, effect or plan. Finding and keeping
  references, researching a look and saving it to the project still work. The settings line
  folds to one caption; which model thinks is still the person's choice.
- **Asked to make while exploring, the brain says what it would make and nothing is made.**
  Under its words a card offers "Switch to Make" or "Keep exploring".
- **"Switch to Make" never spends.** It flips the project and sends the same ask again; a still
  then waits on its usual card for Approve beside its price, even with Auto on. A scene is
  written (writing costs nothing). The person's message is not shown or stored twice.
- **The floating assistant inside a project follows the same switch**, with the same card.
- **Outside a project nothing changes**, and the buttons under earlier results (Upscale,
  Variation and the rest) still open their priced cards.

Fixed on the way: under a long conversation the docked box slid over the project row, which
made the row unreachable. The row now docks with the box.

Checked: `tests/test_explore_switch.py` (19) and `web/tests/explore.test.mjs` (10); the Guide,
projects, tenancy and connector suites around them; then in a browser on a stub server with a
CHARGED test account (400 credits; the brain scripted, no provider called):
- the switch on the project row, flipped by a real click, saved on the project;
- talk while exploring: an answer with choices and a brief, no Make button on the brief;
- "draw the hero still" while exploring: the card, and the server log showing the turn was
  handed the switch and no make tool;
- "Switch to Make" with Auto ON: the project flipped, the card gave way to the still's step
  card waiting for Approve at 10 credits, the balance still 400 with nothing held, no still
  drawn, the person's bubble not repeated;
- a scene asked for: its own card wording, and the ask sent again as Video;
- "Keep exploring": the card reads "Still exploring" and the project stays as it was;
- a 375px phone width (the row stacks; no sideways scroll);
- the workspace: the switch in the project panel, the assistant's card, the panel following
  the switch from the card, and the project's history holding the message once.
- outside any project: no row and no switch, and the docked box sits exactly where it did
  (measured with and without the new wrapper around it).

Known limits:
- No real model was called. Whether the live brain offers the switch when it should, or too
  often, is unmeasured.
- The switch governs what a send does. The routes that make (a scene, a still, an effect) do
  not read it: they are reached by the person's own buttons, each with its own price.
- A skill picked from the slash menu does not ride on a send while exploring, and the slash
  menu there offers only "attach a reference" and "reference an element".
- The connector's project tool does not show the switch.
- In the assistant's dock the card's main button is the dock's usual red; on the composer it
  is not red, because nothing there spends.
