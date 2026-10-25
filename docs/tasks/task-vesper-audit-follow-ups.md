# Task: the six follow-ups from the Vesper audit and the render test

Mike's "do 1-6", 2026-10-25. The six came out of two write-ups from 2026-10-24:
`docs/qa/vesper-audit-2026-10-24.md` (section 6, the ranked changes) and
`docs/qa/competitor-capture-2026-10-24/render-test.md` ("What the render test showed"). Rank 1 of
the audit, the approved still prompt is the prompt that runs, is its own task
(`task-vesper-approved-prompt-runs.md`, PR #488). Each follow-up went on its own branch and PR,
all merged and deployed on 2026-10-25.

| # | What | PR | Audit rank |
|---|---|---|---|
| 1 | Video page: several pictures as references, each model's own prompt cap | #491 | render test 3 |
| 2 | Vesper answers "which model", decides on "you decide", offers the lone kit | #492 | 3, 4, 6 |
| 3 | The guide's prompt files stop contradicting each other | #490 | 7, part of 2 and 4 |
| 4 | The scene writer keeps the person's typed AVOID line | #489 | 8 |
| 5 | A kit link holds a shot to an app's real screenshots | #493 | render test |
| 6 | Gemini watches every landed clip once; notes on the Render card | #494 | render test |

## As built (2026-10-25)

### 1. References on the Video page (#491)
- `fal.REF2V`: the reference-to-video endpoint, image field, picture limit and prompt tag per
  model, read off fal's queue schemas on 2026-10-25:
  - Seedance 2.5: 30 pictures; Seedance 2.0 and 2.0 Fast: 9; tag `@Image{n}`.
  - Kling 4: 10 pictures, `@Image{n}`, only while its slot is on.
  - Grok 1.5: 7 pictures, `<IMAGE_{n}>` counted from 0, +$0.01 per picture, 480p or 720p only.
  - `fal.ref_spec` / `ref_max` / `ref_tags` read it. Images only; no video or audio references.
- `reference_urls` runs through `build_body`, `generate_video`, `generate_from_prompt`
  (`references=`) and `estimate_cost(references=)`, so the quote prices the pictures.
- Refused, never clamped (`fal.build_body`): a model with no reference endpoint, a start frame
  together with references, more pictures than the model takes. Grok's 480p/720p limit with
  references is listed to the page (`ref_resolutions`); the server does not check it.
- `fal.PROMPT_MAX` is each model's own prompt `maxLength`; a model whose schema sets none
  (Seedance) gets `PROMPT_MAX_UNSET` = 10,000. `direct.clean_prompt(raw, video_model)` refuses
  past the cap. Stills keep `direct.PROMPT_MAX` = 4,000.
- Routes: `/api/direct/video/quote` and `/run` take `references` and `ref_mode=references`.
  `direct.video_menu` items carry `prompt_max`, `max_refs`, `ref_tag`, `ref_resolutions`.
- The page (`direct-generator.tsx`, `lib/direct.ts` `videoRefMode` / `videoRefTags`): one picture
  is a start frame unless the person flips it to a reference; two or more are references. The
  hint lists the tags to write, and the box's limit is the model's.

### 2. Vesper stops stalling (#492)
- `prompts/model_picks.txt`: which model, by what the person starts from (a speaker's photo →
  the talking-photo card, none → Veo; several pictures → Seedance 2.5 or Grok 1.5; Kling 4 on a
  line of its own; long takes, readable words, a cheap first look, a kept face or product).
  `list_models` ends with it. `model_menu.picks_block` drops any line naming a model the
  account is not listed for (a parked slot, a missing key), and a test checks every model the
  guide names against `fal`'s tables (`model_menu.models_named`).
- `creative_guide_models.txt`: a model question is answered in the same turn, one model and why,
  `list_models` called once, no tool names in the answer.
- Deferring ("you decide"): `creative_guide_make.txt`'s WHEN THEY DEFER, DECIDE rule, plus a
  `locked` argument on `make_image` / `make_video` (`guide_tools.LOCKED_PROPERTY`,
  `MAX_LOCKED` = 200 characters). The make's message opens on that line, saying what was locked
  and naming anything invented. A scene is never locked to a shape other than 9:16.
- The lone kit: with no kit in play and no project, an account with exactly one brand kit has
  it offered for an ad that names no product (`api._lone_kit`,
  `creative_guide.lone_kit_instructions`, `prompts/creative_guide_lone_kit.txt`). The first
  choice reads "Yes, an ad for <kit>"; picking it names the kit, which brings it in the way a
  named kit always did.
- Re-run on the real brain (Gemini 3 Flash "Fast", local throwaway database, text only): the
  model question is answered in turn 1; "you decide" makes in turn 1 with a "Locking it
  myself…" line (2 of 2 runs); "help me make an ad" opens on "An ad for Gygler?".

### 3. The prompt files agree (#490)
- Timings: `creative_guide.txt` and `assistant_brain.txt` no longer ask the brain for timed
  shots; the scene writer cuts them. A count the person names goes on in words ("in 2 shots"),
  a single take as "one continuous shot". `tests/test_shot_count.py` pins it.
- One question everywhere (`questions` is a list of one); `assistant_brain.txt` had said three.
- `_voice`: never paste the prompt into `message`; the card shows it.
- The photo reminder: say once what a reference would add, never ask again.
- The base file covers stills as well as videos; stale names fixed (the Create box, Library,
  Approve / Render). The story-judge line stays (`story_judge` still runs).

### 4. The typed avoid list survives (#489)
- `scenes_prompt.txt`, `scene_brief_prompt.txt`: part 5 starts with the person's own items, word
  for word and in order, then the house list.
- `creative_guide_make.txt`: a typed avoid list goes into `make_video`'s prompt as its own
  `AVOID:` line.
- `shootgen.typed_avoids(idea)` / `avoid_warnings(prompt, idea)`: an item the writer still drops
  is a warning on the saved scene ("your avoid list lost: …").
- Follow-up fix: the no-kit goldens (`tests/goldens/no_brand_kit.json`) went stale with the
  prompt change and failed CI; regenerated with `PHANTRA_UPDATE_GOLDENS=1` (d0ccf476).

### 5. A kit link holds a shot to real screenshots (#493)
- A product or character link takes `photos` (1 to `brand_kits.LINK_PHOTOS_MAX` = 4). At 1 the
  key is left out, so every existing kit hashes and writes as before; off the range is refused.
- `element_sheet.element_photos(photos, n)`: n > 1 puts the person's own uploads first and a
  drawn sheet last (a drawn sheet cannot carry readable UI). `api._kit_refs` uses it; a timed
  part naming the product gets all n (`brand_kits.part_refs` unchanged).
- The kit page has a "Hold a shot that names it to N photos" picker on each linked product
  (`web/src/app/studio/brand/[id]/page.tsx`, `lib/brand-kit.ts`). The brain's kit block says "a
  shot that names it is held to N of its real photos" only where N > 1.
- `creative_guide_screens.txt`: draw a kit screen only for a screen the real screenshots lack.
- Live, on Mike's word (2026-10-25): kit 1's link to prop 13 is `photos: 3`. Prop 13 holds
  `gygler-app-1-phone-jobs.jpg`, `-2-talent-pool.jpg`, `-3-live-tracking.jpg` (gygler.com's own
  images, flattened onto the kit's cream, uploaded through `media.mirror`) and was re-described.
  The old laptop mockup `gygler-app-interface.jpg` stays, sorting last: scenes 440 and 442-450
  reference it by name. Photos list by filename, so a new screen needs a name that sorts before
  it. Backups: main checkout `data/backups/kit1-photos-2026-10-25/`,
  `prop13-screens-2026-10-25/`.

### 6. The clip check (#494)
- `src/render_qc.py`: inside the render job, after each shot's clip lands
  (`app.api._check_clip`), Gemini (`FAST_MODEL`) watches it once against the shot's prompt and
  the scene's kit: its name, its linked products, any words the prompt quotes
  (`render_qc.quoted_words`). Prompt in `prompts/render_qc.txt`.
- Four facts (brand said / misspoken / not said; words readable / garbled; product present /
  missing / wrong shape; hands and faces fine / distorted) and up to three timed notes.
- Free to the person, metered as stage `render_qc`. Advice only: never raises, never fails a
  render. `PHANTRA_RENDER_QC=0` turns it off; on by default.
- OWNED table `render_qc` (`ensure(dsn)`, inited at app start, in `db.OWNED_TABLES` and the
  tenancy test's init lists). Created on live by the 2026-10-25 deploy.
- `GET /api/scenes/{id}/render` returns `scene.checks` by shot; a re-rendered shot shows its new
  clip's check. The Render card prints them under the planner's warnings
  (`lib/render-checks.ts` `checkLines`): "Shot 2: The brand name is said wrong".
- On the render test's own Gygler clip (`b_vesper.mp4`) it reported the brand never said,
  illegible screen text at 0s and warped hands at 4s, as the render test found by eye.

## Checked
- All six PRs merged, Fly deploys green, `/healthz` 200, `/api/direct/video` and `/mcp` 401
  signed out, the live `render_qc` table present (read-only SQL).

## Not done
- A live render on a reference endpoint (#491) and a live render with the check on (#494): both
  spend, so they wait on Mike's yes. One Create scene that names the Gygler app with kit 1 covers
  #493 and #494 together.
- Browser walks of the Video page's reference mode and the Render card's notes.
- A server-side refusal of a resolution the reference endpoint lacks (Grok 1080p with
  references): only the page knows the limit today.
- Audit rank 2 (no photo → a hero still first) is Mike's call; rank 5 (No asks why) is not built.
- Elements are still not offered as references on the Video page (uploads and Library stills are).
