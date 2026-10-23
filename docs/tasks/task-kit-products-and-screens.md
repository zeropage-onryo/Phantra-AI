# Kit products, kit-drawn screens, and the three scene-442 leaks

Status: **SPEC, waiting on Mike's approval to build** (written 2026-10-22 from a Claude chat
that diagnosed the Gygler ad, scene 442 / final cut gen:208). Nothing has been built,
rendered or spent. **Do not render, quote-and-approve, or spend anything while building or
testing this; verify with free paths and stubs only.**

Save this file in the repo as `docs/tasks/task-kit-products-and-screens.md`.

## 0. What happened (the evidence)

Mike wrote a 10 s Gygler ad (three timed shots, voiceover in shot 3, photos #3 dish,
#4 chef, #5 tablet/app). The final cut had no voiceover, no pasta, a stranger for a chef, and
an unreadable app screen. Read off the live DB (Supabase project `ewkbrenbjsiggufegrnd`):

- Scene **441** (single take) was held to 3 refs: the three FLUX stills
  `flux-pro1.1-c438/c439/c440-...jpg` (dish, chef, tablet), all `renders/fal/...` URLs.
- Scene **442** (the timed rewrite that rendered) has ONE ref:
  `/props/gygler-app-interface/photo/gygler-app-interface.jpg`. The Library stills were
  dropped on the rewrite. `shot["timeline"]["parts"][*].refs` = `[[], [that prop], []]`.
- No part has a `still` (no keyframes were drawn); clips are `kling3-turbo-pro` (gen:205-207).
- Part prompts as planned:
  1. "Close-up. Chef's hands placing micro-herb garnish on ceramic plate. ..." (no dish/food)
  2. "Medium shot. Hand taps tablet displaying orange Gygler [1] interface ..."
  3. "Close-up. Head chef smiling at lens. ... Sound: low ambient kitchen hum." (the scene's
     `Voiceover: '...'` line is gone)
- Scene 442 has `brand_kit_id = 1` (Gygler). The kit's look line rides on clips
  (`fal.py` ~1761 `brand_kits.dress`), but its reference images only go to stills/keyframes
  (`scene_chain.py` ~505/615) and there were none. Kit `spec.products` and `spec.characters`
  are empty; the existing `gygler-app-interface` prop is not linked to the kit.
- Final cut is 10.1 s and ends on the chef: no kit end card (kit has `end_card.on = true`,
  2.5 s). The in-chat Assemble (`src/cut/assemble.py` `file_on_wall`) seems not to apply
  `src/cut/brand.py`; confirm.

## Part A: the three leaks (bugs; fix first)

### A1. A rewrite drops Library refs
When the brain rewrites a scene (441 -> 442, single take -> timed shots via `make_video`),
`gen:<id>` / `renders/...` refs were not carried; only the Element photo survived.
- Find where 442 got its refs (`src/guide_tools.py` `make_video` path ~137/939,
  `src/creative_guide.py`, `shootgen.generate_scene_concept`). Likely the brain re-picked
  refs from Elements only, or `asset_shelf.storable_ref` / `parse_ref` rejected render URLs.
- Fix: a rewrite of a scene in the same thread keeps that scene's refs (and the thread's
  attached Library items) unless the person removed them. Note the 441 refs are stored as full
  `https://media.phantra.ai/...` URLs, which breaks "store names, mint addresses"; check
  how they were written and store them as `gen:<id>` names instead.
- Test: a thread attaching 3 Library stills, rewritten into timed shots, keeps all 3.

### A2. The timeline planner drops a voiceover
`src/timeline.py` `plan()` + `prompts/shot_timeline_prompt.txt`: the scene's
`Voiceover: '...'` line vanished from part 3 and was replaced by ambient sound.
- Check `_scan` / `_TAIL` (~line 209): the VO likely sits in the scene's SOUND tail and is
  classed as tail, then the planner rewrites part 3's sound. Also check whether
  `render_prompt` (~627) ever re-appends the tail (sound, avoid list, look lines); CLAUDE.md
  says the tail belongs to every shot.
- Fix: a quoted voiceover/dialogue line is never dropped. It is kept verbatim on the shot it
  was written under, or attached to the scene as a VO line.
- Add a **visible warning** (code advises, never rejects) when the spoken line can't fit its
  window: ~2.5 words/s, so a 20-word line needs ~8 s and won't fit a 3 s shot.
  E.g. "shot 3: the voiceover is ~8s of speech in a 3s shot; it will be cut or rushed.
  Lay it as its own track in the editor."
- Test: the exact 442 scene prompt (read it with the `scene` tool or from `shoot_concepts`)
  plans with the VO text present in part 3, or on the scene, plus the warning.

### A3. Shots with no photos render with no warning
`preprod.reference_gate` passes a scene if ANY shot has a ref; parts 1 and 3 had none.
- Do NOT add a second rejection (conventions: the reference gate is the one rejection).
  Add a warning per part with empty `refs` when the scene has refs that part could use
  ("shot 1 has no photo; it will be drawn from text"), shown on the Render card before the
  priced button.
- Consider: when a part has no refs, the planner should consider the scene's refs by role
  (subject -> any shot naming that subject). Check `timeline.plan` ref picking.

### A4. In-chat Final cut skips the kit end card (confirm, then fix)
If `assemble.file_on_wall` doesn't apply `cut/brand.py` (`end_card_png`) when the scene has
a kit, add it (the kit's `end_card.on`), free, same as the editor's export.

## Part B: kit products become real references

Today `spec.products` links to prop Elements but `brief_lines` (~848) passes only the name and
claims to the writer. The photo never reaches a shot.

- When a scene has a kit and a shot's text names a kit product (its Element name or aliases;
  a new optional `aliases` list on the product link, e.g. "Gygler app", "the app", "tablet
  screen"), attach that Element's photos to the shot as **subject/product** refs, ordered per
  the existing rule (character, prop, location), NOT as look-only refs. Same for
  `spec.characters`.
- Where: the scene writer's ref assembly and/or `timeline.plan` part refs. Keep opt-in
  byte-for-byte: no kit, or no named product, means identical prompts and quote hash
  (`tests/test_brand_kit_no_kit.py` goldens must still pass).
- The quote's content hash already folds `hash_of(kit)`; make sure an auto-attached ref
  changes the live shot's hash so a re-price happens.
- Brand kit page (`/studio/brand`): the Products section links Elements (exists?) and shows
  "attached to any shot that mentions it".
- Then link the existing `gygler-app-interface` prop to kit 1 only **after asking Mike**
  (live data rule: report first, back up, write on his word).

## Part C: the kit draws app screens (free, in code)

Video and image models can't draw readable UI. The kit already holds what a screen needs:
Urbanist heading/body fonts, palette (#FF880B, #371901, #FAF0E4, #151515, #FFFFFF), logos.

- New `src/kit_screens.py`: render a branded UI screen to PNG from a small spec, using the
  kit's fonts/palette/logo (Pillow, or HTML -> headless Chromium if layout needs it; the Fly
  image must support whichever is chosen). Sizes: phone 1170x2532, tablet 2048x1536 / 1536x2048.
- Templates (start with 3): `schedule` (e.g. a "Staffed" shift list: rows with name, role,
  time, status pill), `list_cards` (profiles / Gygs), `hero_cta` (headline + button in the
  kit's CTA style, e.g. "I Need Talent"). Spec is plain data, e.g.
  `{"template":"schedule","title":"Staffed","rows":[...]}`; text checked against the kit's
  `voice.avoid` and `never_claim`.
- It costs nothing: no hold, no provider call. File the PNG in the Library (`generated_assets`,
  model `"kit screen"`), so it can be used as a shot ref or made into an Element.
- Brain tool: `make_screen` (proposal -> card with the drawn PNG, free, kept on click), only
  published when a kit is active. Prompt rule in `prompts/`: when a shot shows an app or
  screen for a kit brand, propose a kit screen and use it as that shot's first ref.
- Tests: render each template under kit 1's spec with a stub font; no network.

## Part D (later, BACKLOG only): screen replacement
Track the device screen in a rendered clip and composite the kit screen onto it in the Cut.
Needs a second video track (`src/cut/render.py` refuses one today, ~256). Record it in
`docs/BACKLOG.md`, don't build it here.

## Order and done-when
1. A1-A4 (bugs). Done when the 442 prompt + 3 Library stills re-plan with refs on every
   part, VO kept and warned, empty-ref parts warned, and Final cut gets the end card. Verified by
   running the server and clicking through Create **without approving a render**.
2. B. Done when a kit-linked product named in a shot lands in that part's refs, and no-kit
   goldens are unchanged.
3. C. Done when "a Staffed schedule screen for Gygler" in Create yields a crisp PNG card in the
   kit's fonts/colours, free, usable as a ref.
4. Add "As built" notes here; update CLAUDE.md's brand-kit and timeline lines.

Checks: `venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`,
`cd web && node --test tests/*.test.mjs && npm run typecheck && npm run build`.
