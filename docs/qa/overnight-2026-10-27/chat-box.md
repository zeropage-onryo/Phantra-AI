# Overnight audit 2026-10-27: the Create chat box (composer + Vesper)

Read-only audit of `origin/main` at f7d41665 (after #515 one-clip render and #517). No render,
no model call, no database write. Checks run: `tests/test_one_clip.py` (7 pass),
`web/tests/render-choice.test.mjs` and `final-cut.test.mjs` / `make-plan.test.mjs` (36 pass),
plus the scratch scripts named under each finding (pure functions only, run from the worktree
with `PYTHONPATH=$PWD`). Scratch files live in the session scratchpad, not the repo.

Ranked most severe first.

---

## 1. BREAKS: a one-clip scene cannot be assembled or opened in the editor; the in-chat Final cut, its kit end card, Trim and Library filing are gone for timed scenes

- `src/cut/assemble.py:50-67` (`clip_slots`), `app/cut_routes.py:470` (`not_ready`),
  `web/src/lib/final-cut.ts:58-71` (`joinable`/`shouldJoin`),
  `web/src/components/studio/composer/turns.tsx:599-601`.
- Since #515 a timed scene that fits the model renders as ONE clip on `shots[0].media_url`; its
  timeline parts keep `media_url = None`. `clip_slots` reads the parts whenever they exist, so
  every slot is empty and `POST /api/cut/assemble` answers 409 `not_ready` ("shot 1 part 1 has no
  clip yet; ..."). That is the door behind the Renders page's "Ready to cut" / Assemble and the
  scene's editor cut.
- In the chat, `joinable(m.parts)` is false, so no join runs (by design per the task file), but
  the join was also what:
  - ended the clip on the brand kit's end card (`cut_routes.py:485`, CLAUDE.md "The in-chat Final
    cut ends on the kit's end card"): a Gygler scene rendered in chat now has no end card;
  - filed a "Final cut" row in the Library and offered Trim / See it in the Library / Edit the cut
    (`FinalCutView`). The one-clip tile (`turns.tsx:541-552`) has none of these, and the turn's
    Continue row offers nothing for the clip either (the scene's `Made` has no `clip`/`asset`).
- Verified: CONFIRMED with a pure call: `assemble.clip_slots({'shots':[{'n':1,'media_url':'m/1/renders/x.mp4','timeline':{'parts':[{'n':1},{'n':2},{'n':3}]}}]})`
  returns three slots, all `media_url: None`.
- Fix: in `clip_slots`, when no part has a clip and the shot has `media_url`, emit one slot for
  the shot's clip. Then run the in-chat join for a one-clip scene too (a "join" of one clip
  through Assemble gives the end card, the Library row and Trim back for free).

## 2. BREAKS (v2 only): "Add Sound Pass" and "Cut a vertical version" under a rendered scene do nothing

- `web/src/app/studio/(create)/create-view.tsx:2540-2547` (`takeNextStep`) ->
  `continueOn` `:2572-2579` -> `web/src/lib/effects.ts:98-101` (`candidateOf`).
- `nextStepsFor` offers both effects under every rendered scene (`next-steps.ts:39-50`). The click
  calls `continueOn(t, {kind:"effect"})`, which builds its source with
  `candidateOf({clip: m.clip, asset: m.asset})`. A scene's `Made` never gets `clip` or `asset`
  (only `parts` / `sceneClip` / `finalCut`), so `candidateOf` returns null and `continueOn`
  returns silently: no card, no toast. Pre-dates #515, but the one-clip scene is now the common
  case. Also "Cut a vertical version" promises "A 9:16 version" of a scene that already renders
  9:16 (`render-choice.ts:318`).
- Verified: PLAUSIBLE by reading the whole path (behind `PHANTRA_VESPER_V2=1`; not clicked).
- Fix: give the scene's turn the clip's Library id (`gen:<id>`, from the render job or the scene
  read) and pass it as the candidate; drop the vertical step for a 9:16 scene.

## 3. WRONG OUTPUT: the Video line's Frame pill is a dead control; every scene renders 9:16

- `create-view.tsx:3624-3626` (the pill), `:1362` (`form.append("ratio", ratio)`),
  `app/api.py:3468-3471` (validated), `src/shootgen.py:1459` (stored on the shot);
  `src/fal.py:1515` (`aspect_ratio=DEFAULT_ASPECT`, "9:16"), `generate_for_shot` passes no aspect.
- The settings line offers 16:9, 9:16, 4:3, 3:4, 1:1 and 33:14 (`render_specs.FRAME_SIZES`) for
  Video and remembers the pick in localStorage. The pick is sent, validated, written onto the
  shot and then read by nothing except the retired manual lane (`app/api.py:4499`). A person who
  picks 16:9 gets a 9:16 clip. The in-chat button does say "· 9:16 ·" (`render-card.tsx:300`)
  and `shapeAsked` warns only when the PROMPT names a shape, never when the PILL did.
- Verified: CONFIRMED by grep: `shot.get("ratio")` has one reader in `src/` and `app/`, the
  manual lane.
- Fix: either hide the Frame pill for Video (and tell Vesper, as `locked` already says "a scene is
  always rendered 9:16"), or carry `shot["ratio"]` into the quote and `build_body(aspect_ratio=)`
  for the models whose `T2V_ASPECTS` take it.

## 4. WRONG OUTPUT / MISLEADING: keyframes are still sold for a one-clip scene and mostly not sent

- `web/src/components/studio/render-card.tsx:298, 323-338` (the APPROVE N KEYFRAMES button in
  the chat), `src/fal.py` `generate_for_shot` (#515 hunk: `image_url = None if ref_urls else
  as_image_url(target["reference_image"])`), `src/timeline.py` `one_clip_target` (anchor = the
  FIRST shot's still only).
- In the chat's approve-only card, a scene with no stills shows "APPROVE 3 KEYFRAMES · N CR"
  above the render button. Rendered as one clip:
  - on a model with a reference endpoint (Seedance, Kling 4, Grok 1.5) the keyframes are never
    sent: the photos go as references and the start frame is dropped;
  - on any other model only shot 1's still is sent.
  Before #515 every shot was anchored on its own still. Nothing on the card says the stills will
  not steer the clip, and `keyframeNote` (which used to explain the anchoring) is replaced only in
  the full card.
- Verified: CONFIRMED by reading the adapter and the card. The keyframe quote is unchanged by #515.
- Fix: when the quote is `one_clip`, hide the keyframes button in the approve-only card (or label
  it "preview stills, not sent to the clip"), and have `stills_to_draw` price only shot 1 for a
  model with no reference endpoint.

## 5. MISLEADING: the chat's Approve button says "1 shot" for a one-clip scene of 3 shots; the plan's render step too

- `render-card.tsx:300` builds its own label from `plan.n` instead of `approveText` /
  `shotsText`, and `planFor` sets `n: 1` for `one_clip` (`render-choice.ts:175-178`).
- `create-view.tsx:1677, 1781` (plan render step: `shots: q.renders.length || 1`) and
  `:1606-1608` (`"1 shot · N credits"`).
- `render-card.tsx:345` still says "the shots join into one video when the last one lands" while
  a one-clip render is running.
- Verified: CONFIRMED by running the label's own expression on `planFor(...)` with a one-clip
  quote (scratch `label.mjs`): `Approve · Kling · 9:16 · 1 shot · 288 cr`. The full card's
  `renderText` correctly reads "3 shots, one clip". The price itself matches the server.
- Fix: use `shotsText(plan)` in the approve-only label; in `priceRender` /
  `runPlanStep`, take `q.one_clip ? parts : renders.length` and say "N shots, one clip"; key the
  running note on `plan.oneClip`.

## 6. BREAKS (some scenes): the one-clip prompt is never checked against the model's prompt cap

- `src/fal.py:1940-1960` (`generate_for_shot`, the one-clip target), `src/fal.py:563-572`
  (`PROMPT_MAX`); the cap is enforced only in `direct.clean_prompt` (the Video page).
- The one-clip prompt is the header, the continuity, PICTURES (one line per photo), THE WHOLE
  SCENE and every shot's prompt, then `for_render` / `prompts_for` / the kit's `dress`.
  `kling3-turbo-pro` takes up to 15 s with a 3,072-character cap. Grok 1.5 and Grok 1.5 Lite take
  4,096. Nothing refuses a longer prompt before the hold and the submit, so fal's own validation
  error ends the job after the person approved (the hold is released, the render fails).
- Verified: PLAUSIBLE, measured on the real corpus (main checkout
  `data/backups/wipe-concepts-1-20261007T183008Z.json`, 23 timed scenes, all 10 s, 2-3 shots):
  `one_clip_target` gives 1,463-3,219 characters before pictures and the kit, and 1 of 23 is
  already over 3,072. Overhead averages about 1,460 characters and each shot about 240, so a
  15 s, 5-shot scene with a kit is near or over 4,096.
- Fix: in `pricing._one_clip`, refuse when `len(one_clip_target(...)["prompt"]) > fal.prompt_max(model)`
  (`PricingRefused("prompt_too_long")`), or fall back to the split.

## 7. MISLEADING: a refused one-clip quote leaves the chat's button live, reading "refused" with no reason

- `render-card.tsx:226` (`disabled` has no `plan.refused`), `:300` (the label), `render-choice.ts:179-181`.
- Example: Grok 1.5 at 1080p with photos is refused (`references_resolution`). `planFor` then
  falls to the timed branch and returns `{n: 3, refused: "<reason>"}`. The approve-only button
  reads "Approve · Grok 1.5 · 9:16 · 3 shots · refused" and is still clickable. The reason is
  printed only in the full card's chip (`:528`). Clicking re-quotes, gets no tokens and approves
  anyway; the server refuses, and the person sees a toast. It does not hang.
- Verified: CONFIRMED by reading, plus `planFor` with an error quote (scratch `label.mjs`).
- Fix: add `!!plan?.refused` to `disabled` and print `plan.refused` as the note in the
  approve-only card.

## 8. WRONG OUTPUT (double-spend risk): the effect card goes back to "Approve" when only the WAIT failed

- `create-view.tsx:1960-1973` (`approveEffect`).
- The catch around `runEffect` + `waitForJob` treats every throw as "refused before anything
  ran" and resets the card (made and paid cleared). `followJob` (`studio-api.ts:923-930`) throws
  on any failed `getJob`: a network blip, a 502 during a deploy, or a 404 once a restart has
  emptied the job registry. In those cases the effect is still running, or the fal boot sweep
  finishes it, and it is charged, while the card invites a second Approve at the same price.
- Verified: PLAUSIBLE by reading (not reproduced).
- Fix: reset the card only when `runEffect` itself throws. After a `job_id` exists, mark the turn
  "lost: check the Library before running it again", as `followCut` already does.

## 9. "ASKS TOO MUCH": where the questions come from

- The default dial is the most asking setting. `lib/autonomy.ts:38-44` `loadAutonomy()` returns
  `"ask"` (Ask me everything), and `create-view.tsx:602` starts there. Under v2 that sends
  `AUTONOMY_NOTES["ask"]` (`src/creative_guide.py:203-205`: "before you make, ask the one
  question that matters most when anything is open") and stops plans at FREE steps too
  (`stopsAt`). `generateModeFor` forces "ask" for every setting, so with v2 on even a still never
  draws on the send.
- The base prompt asks a question on every turn. `prompts/creative_guide.txt:3`: "give a concrete
  creative observation, then ask ONE focused question", and `:5` walks intent, audience, subject,
  turn, visual direction, pacing, sound and references. `creative_guide_make.txt:3` makes only a
  bare description or a clear "make it"; anything "close" becomes an offer instead.
- A forced question before every Video make with no attached photo: `NO_PHOTO_NOTE`
  (`creative_guide.py:152-168`, "Before make_video, ask them to attach a photo"). `photo_note`
  looks only at the box's attachments and the grounding's cast and locations. Two cases where the
  scene WOULD render but Vesper is still told to ask first (PLAUSIBLE by reading;
  `tests/test_guide_tools.py:328` covers neither):
  - **(a) a brand kit is in play** whose linked product the idea names. The kit's photos are
    added at write time by `api._kit_refs` (`app/api.py:3311`); `photo_note` is called without
    the kit (`creative_guide.py:428`). This is the Gygler ad case, Mike's main use.
  - **(b) the person points at a still made in this chat** ("animate #3"). The number rides as
    `args.results` and only becomes a ref in `make()`; the guide request's `image_refs` are the
    box's alone (`create-view.tsx:2311`).
- Fixes:
  - Default the dial to Checkpoints. Pricing still stops every spend.
  - Make the base prompt's question conditional ("ask only when the next make would be a guess").
  - Pass the kit's linked-photo count and the named results into `photo_note`, and suppress the
    note when either would hold the scene.

## 10. "LOOKS LIKE THE OLD BOX": the new layout is behind an env flag that defaults off

- `app/api.py:326-328`: `vesper_v2` is on only with `PHANTRA_VESPER_V2=1`. The corner sheet, the
  storyboard, the dial, the tappable questions and the next steps all gate on it
  (`create-view.tsx:592, 594`). `create_v2` (the front page) defaults ON.
- The 2026-10-22 run left `fly secrets set PHANTRA_VESPER_V2=1` for Mike to run. I could not read
  production (`/api/capabilities` needs a session). If the secret is unset, Mike is seeing the
  pre-v2 chat.
- Verified: PLAUSIBLE. Check with `fly secrets list -a phantra-api` (Mike).

## 11. POLISH

- The plan render step's note "clip rendered · it is in the Library" is right. But a plan's
  scene (`m.planned`) never gets its clip drawn on its tiles. `sceneRead` runs only from the
  in-turn Render card, which a planned scene does not draw (`turns.tsx:602`), so the scene's
  tiles stay stills after its plan renders it. PLAUSIBLE by reading.
- `approve_render` has no "already rendered" guard for a one-clip scene. Its parts still have no
  clip, so `renders_as_one` stays true and a second approve renders it again at full price. The
  studio guards on `media_url` (`renderedOf`, the plan's `card.media_url`), but the connector's
  `quote` / `approve` do not. Out of this area; noted for the connector audit.

---

## Checked and fine

- **The in-chat render after #515.**
  - `sceneRead` (`create-view.tsx:2607-2626`) treats the shot's own clip as `whole` only when no
    part has a clip, and clears the chat down to the turn on landing.
  - `sceneRendered` / `rendered` take `sceneClip` first, so the Render card goes away and the
    v2 next steps appear.
  - `shouldJoin` correctly does not fire for a one-clip scene.
  - No double-file: nothing is joined, and the clip's own Library row comes from the render.
- **The one-clip price.**
  - The full card's "Render · 3 shots, one clip · N cr" matches `pricing.display`: one estimate,
    one token, `durations=[fit_seconds(total)]`, per-picture USD included.
  - `served()` skips the duration match for `one_clip`.
  - The plan step's approve sends `duration: q.durations[0]` (`timed` False); the server ignores
    it for a timed scene, and the token's content hash is checked before `timeline.ensure`
    re-plans inside the job.
- **Stills.** The step card's prompt is the prompt sent: `/generate/run` sends the approved
  prompt as is (`app/api.py:6505-6513`), plus only a picked camera line, the kit `dress` the card
  names, and the ref-role note. The model and frame on the card are the ones posted
  (`stillModelOf` / `stillFrameOf` -> `image_model` / `aspect`). Auto draws only when
  `autoCovers` says the proposed model is not dearer than the send button's.
- **No clip spend under Auto or Approve all.** `alwaysAsks(render)`, `approveAll` excludes it,
  `approveStep` needs a price, and `runPlanStep` re-prices at the click and stops on a moved
  price. Effects send `expect_credits` (409 on a moved price, shown as a toast). The talking
  photo's Render and the ad's build are their own clicks.
- **No URL to the model.** The guide's tools take numbers and ids (`check_args`); refs travel
  client -> server as form fields and reach fal through `as_image_url` / `clean_url`.
- **Error paths that do not hang.** A guide turn that fails marks its bubble failed with the
  words handed back; `needsCredits` gives the add-credits path. Render-card approve errors toast
  and reload. A locked scene (no photos) says why and links to its canvas.
- **Length.** The settings line's seconds and the brain's `seconds` reach `/scenes/run`
  (clamped by `scene_seconds`, by design) and become the windows the one-clip price fits up.
