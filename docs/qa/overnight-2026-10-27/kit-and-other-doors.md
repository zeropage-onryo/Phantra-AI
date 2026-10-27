# Brand kit and the other model doors: audit, overnight 2026-10-27

Scope: the brand kit pages and everything a kit adds to what is sent; effects
(`src/effects.py`, `/api/effects/*`); element sheets, keyframes, talking photo, clip
edit, Finish, quick edits, the editor's model calls, render QC. Read-only, against
`HEAD` = `f7d41665` (origin/main). No spend, no live database write.

How it was checked:
- every fal endpoint's **public** queue OpenAPI schema
  (`fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>`) and the `endpointBilling`
  record plus price text on its model page, fetched tonight (2026-10-26/27), compared
  field by field and enum by enum against the table rows by a script
  (`scratchpad/cmp.py`, not committed);
- request bodies and prompts built with `PYTHONPATH=<worktree>` snippets, nothing sent;
  the fal and watermark snippets were re-run on a `git archive HEAD` copy, because
  another session had uncommitted edits to `src/fal.py` / `app/api.py` in this
  worktree tonight (the results were the same);
- tests: `tests/test_effects.py test_effect_recipes.py test_effect_names.py
  test_talking_photo.py test_element_sheet.py test_render_qc.py test_kit_products_refs.py
  test_kit_changes.py test_drafts.py test_brand_kits.py test_watermark.py`: **177 passed**
  (58 s). None of the findings below is covered by a test.

Line numbers are for `HEAD`.

## Findings

Severity: **breaks** / **wrong output** / **wrong price** / **misleading** / **polish**.

### 1. An effect that is paid for and then fails to publish says "Nothing was charged" (misleading, and a paid output lost from the Library)
- `src/effects.py:959` settles the hold, then `:972` publishes (`fal._publish`, R2) and
  `:976` banks the row. Any exception after the settle (an R2 outage, a full disk) is
  caught by the outer `except` at `:983` and returned as `{"ok": False, "error": ...}`.
  `app/api.py:5969` turns that into `failures.plain(..., "The effect")`, which always
  ends in **"Nothing was charged."**
- Scenario: R2 is down for a minute. A person runs a 48-credit camera move. fal renders
  it, the credits are settled, the upload fails. The job says "The effect was not made:
  the effects service reported an error. Nothing was charged." The credits are gone, the
  file sits under `data/renders/fal/fx-...` with a generations row, and no Library tile.
- CONFIRMED by running: `effects.run(...)` with stubbed fal and a `publish` that raises
  gives events `['take', 'submitted', 'settle']`, `{'ok': False, 'error': 'r2 down'}`, and
  that plain text.
- Fix: wrap only the submit/download in the release `try`. After `settle`, a publish
  failure should return `ok: True` with the local path (or `/renders/...`) and a note, or
  at least an error that says it was charged. The same shape applies to talking photos
  and clip edits, which run through this function.

### 2. A voice that was paid for but not filed is reported as "the image service reported an error. Nothing was charged." (misleading)
- `src/talking_photo.py:290` returns its own honest sentence ("the voice was made and
  paid for but could not be filed"). `app/api.py` `talking_photo_voice_run` passes it
  through `failures.plain(..., "The voice")`. `_OURS` (`src/failures.py:34`) does not
  match it, and `"The voice"` / `"The talking photo"` are missing from `_NOUNS` (`:55`).
  So the person reads the wrong service and a false "Nothing was charged".
- CONFIRMED by running `failures.plain('the voice was made and paid for but could not be
  filed (disk full)', 'The voice')`.
- Fix: add `paid for` (or a marker prefix) to `_OURS`, and add `The voice`, `The talking
  photo` and `The sheet` to `_NOUNS`.

### 3. Camera move (PixVerse 4.5) is priced at half of fal's price (wrong price)
- `src/effects.py:356` `PIXVERSE_5S_USD` (0.15 / 0.15 / 0.20 / 0.40) is used for both
  `pixverse-effect` (v5) and `camera-move` (`fal-ai/pixverse/v4.5/image-to-video`,
  `:487`). Tonight the v4.5 image-to-video model page says a 5 s clip costs **$0.30 at
  360p/540p, $0.40 at 720p, $0.80 at 1080p**. The v5 effects page still says
  0.15/0.20/0.40, so the v5 row is right.
- Scenario: a 720p camera move is quoted and held at 48 credits. fal bills $0.40, which
  is 96 credits at the house markup. The house absorbs half on every move, and
  `_pricing_note` tells the connector the old numbers.
- CONFIRMED against fal's page tonight (`credits_for`: $0.20 is 48 cr, $0.40 is 96 cr).
- Fix: give `camera-move` its own table, `{360p: .30, 540p: .30, 720p: .40, 1080p: .80}`,
  with a `checked` date, and update `_pricing_note`.

### 4. Seven Kling effect names in the table no longer exist on fal (breaks for those seven)
- `src/effects.py:63+` `KLING_EFFECTS` lists `day_to_night`, `skateskate`,
  `guardian_spirit`, `pet_moto_rider`, `3d_cartoon_2`, `pet_dance` and `surfsurf`.
  None of them is in tonight's `effect_scene` enum for
  `fal-ai/kling-video/v1.6/standard/effects`.
- Scenario: the gallery lists "surfsurf". `check_options` accepts it and the quote is
  shown. On Approve the hold is taken, fal answers 422, the hold is released, and the
  card says "the effects service reported an error". The effect can never succeed.
- CONFIRMED: `effects.check_options('kling-effect', {'effect_scene': 'surfsurf'})` passes,
  and the schema diff names all seven.
- Fix: remove the seven, or regenerate the tuple from the schema and re-date `CHECKED`.
  A test that diffs the table against a saved copy of the schema would catch the next
  drift.

### 5. Seedream 4 edit always comes back square (wrong output)
- `src/effects.py:441`: the row sends no `image_size`, and the schema's default is
  `{"width": 2048, "height": 2048}`. The row also exposes no aspect option, unlike
  `nano-banana-edit` and `flux-kontext-pro`.
- Scenario: a 9:16 product still is edited "make the background marble". It comes back
  as a 2048x2048 square: re-framed, the subject cropped or stretched.
- CONFIRMED by building the body: `{'num_images': 1, 'image_urls': [...], 'prompt': ...}`,
  with no size. The output shape is inferred from the schema default and was not
  rendered.
- Fix: put `"image_size": "auto_2K"` (an enum value on the schema that follows the input
  shape) in `fixed`, or add an aspect option mapped to the named sizes.

### 6. render_qc tells every shot of a kitted scene that "the product does not appear" (wrong output)
- `src/render_qc.py:218` hands the model **every** product the kit links, as "Products
  that should appear", for every shot. A shot that never names the product (a barista
  pouring, an establishing street) is checked against it.
- Scenario: a 4-shot Gygler scene where only shot 3 names the app. Shots 1, 2 and 4 come
  back with `product: missing`, printed under the Render card as "the product does not
  appear". A note that is wrong three times in four teaches people to ignore the check.
- CONFIRMED by building the prompt: for "A barista pours a latte at dawn", the prompt
  reads `Products that should appear: Gygler App`. The model's answer is inferred.
- Fix: `products = [e["name"] for e in brand_kits.named(kit, prompt, dsn) if e["kind"] ==
  "prop"]`, the same "named in its words" rule as `part_refs`.

### 7. The fal reference reader sends a free-trial render's WATERMARKED copy when the row stores a name (wrong output, narrow)
- `src/fal.py:1697` (`as_image_url`): a stored NAME with no file on this machine returns
  `media.bucket_url_for(value, account_id)` directly. That is the render's normal key,
  which for a trial account holds the marked copy. Only the `http(s)` branch (`:1681`)
  goes through `watermark.clean_url`. The Gemini reader does it right
  (`imagery.fetch_image_bytes` cleans every URL).
- Scenario: a trial account's Library still is put on a scene as a reference. From the
  `tenant` rung up, the shot stores it as the name `/renders/fal/x-<hex>.png`. On a
  machine without that file (another Fly machine, a lost volume, the Mac rendering a Fly
  scene), the clip's start frame or REF2V reference reaches fal with the "Phantra" mark
  burned in, and the model reproduces it. The same applies to `mcp_server._fetchable`,
  which tries the raw name first. The Fly volume makes this rare today.
- CONFIRMED by running `as_image_url` with stubs: the name gives the marked URL, the URL
  gives `CLEAN:...`.
- Fix: `return watermark.clean_url(media.bucket_url_for(value, account_id))` on that line.

### 8. Element sheet: underpriced on GPT Image 2.5 Sunburst, and drawn at 1360x768 (wrong price, and probably wrong output)
- `src/element_sheet.py:168` prices a sheet at `fal.image_usd(SHEET_MODEL, "16:9")` =
  the flat **$0.06** (15 credits). Sunburst is billed by tokens. fal's table puts a high
  quality 1360x768 output at about $0.04, and **each reference image adds about
  $0.008-$0.012**. A sheet sends up to 6 photos (`MAX_REFERENCES`), so it costs about
  $0.09-$0.11 against the $0.06 held.
- The frame is `image_dims("16:9")` = **1360x768** for five panels, about 270 px per
  body. The Gemini lane drew at 2K (`SHEET_SIZE`, Gemini only). The sheet becomes
  `refs[0]` for every later shot (`element_refs`), so a low-resolution sheet lowers the
  likeness of every clip.
- PLAUSIBLE: the price is from fal's published table, not billed. The resolution is
  CONFIRMED by building the request: `image_size {'width': 1360, 'height': 768}`.
- Fix: price Sunburst as output-by-size plus `refs × ~$0.012`, and pass `references` to
  `image_usd`. Draw the sheet at a 2K frame, for example 2560x1440 (about $0.055 output),
  through an explicit size.

### 9. A brand kit can push a scene prompt past the model's prompt limit, and no scene door checks the limit (breaks, plausible)
- `fal.PROMPT_MAX` (`src/fal.py:563`: kling3-turbo-pro 3072, grok1.5 4096, ltx 5000) is
  enforced only by `src/direct.py`. `generate_for_shot` dresses the prompt with the kit
  (`src/fal.py:1992`, `brand_kits.dress`) after `prompts_for` and never measures it. A
  kit's `look_suffix` can reach **3,506 characters** (style 1500, 30 banned items, 8
  aesthetics; measured with `clean_spec`). A one-clip scene (`timeline.one_clip_prompt`:
  continuity, every shot's window, style, sound, avoid) is long before the kit is added.
- Scenario: a 15 s, 5-shot Gygler scene on Grok 1.5 one-clip, with a 1,200-character kit
  look. The prompt passes 4096, fal answers 422 after the hold, the hold is released,
  and the card says "the video service reported an error". It fails the same way on
  every retry.
- PLAUSIBLE: the code path was read; no real scene was measured.
- Fix: in `generate_for_shot`, refuse before the hold when
  `len(prompt) > fal.prompt_max(model)`, in words ("this scene plus its brand look is N
  characters; <model> takes M"). Better, have the quote measure the dressed prompt.

### 10. Topaz (upscale, and so Finish) prices a vertical clip by its LONG side (wrong price, plausible overcharge)
- `src/effects.py:362` `_topaz_usd` takes `out_h = height × factor`. fal's tiers ("up to
  720p, 720p to 1080p, above 1080p output") are conventionally the short side. The house
  format is 9:16, so the height is the long side.
- Scenario: Finish on a 540x960 draft (x2 gives 1080x1920) is priced at $0.08/s, the
  above-1080p tier. If fal reads it as 1080p, it bills $0.02/s, so the person is charged
  4x. A 720x1280 smooth-only pass (factor 1) is priced $0.02/s instead of $0.01/s.
- PLAUSIBLE: fal's rule is ambiguous. One cheap billed run would settle it.
- Fix: use `min(width, height) × factor` once fal's unit is confirmed. Until then the
  rule overcharges, which is the safe direction, but say so in `_pricing_note`.

### 11. No prompt length cap on the effects that have one (polish)
- `src/effects.py:745` `check_prompt` caps only recipes. `camera-move` (PixVerse 4.5)
  takes at most **2048 UTF-8 bytes** (schema text). Kling O1 edit takes 2500 (clip edit
  stays under it: 1500 plus about 110). Luma reframe takes 5000.
- Scenario: a 3,000-character camera-move prompt is accepted, held, refused by fal, and
  released as "reported an error".
- CONFIRMED: `check_prompt('camera-move', 'x'*3000)` passes.
- Fix: a `prompt_max` (and a `bytes` flag for PixVerse) on each row, refused in
  `check_prompt`.

### 12. Keyframes: a kit look reference can become a timed shot's FIRST reference (polish)
- `src/scene_chain.py:641` / `:672`: in `_keyframe_timeline`, `references =
  references + kit_refs`. For shot 1 of a part with no refs of its own (the planner's
  "a shot with no photos" warning case), there is no continuity still either, so the
  kit's look reference is `references[0]`. That breaks the module's own rule that a look
  reference is never first.
- PLAUSIBLE by reading.
- Fix: when `references` is empty, skip the kit refs (or prepend the scene's first ref).

### 13. Smaller notes (polish)
- **Nano Banana edit** is $0.039 in the table and **$0.0398** on fal tonight
  (`src/effects.py:427`). It is still 10 credits, because the floor covers it, so only
  the dated number is stale. This is also `clip_edit`'s frame stage.
- **Recipe effects** do not check the source photo against Kling 3 Turbo's
  `image_url` limits (300 px minimum, aspect 0.4-2.5; schema `x-fal`), so a long panorama
  is held and then refused. The talking photo checks the same limits; the recipe rows
  could too.
- **Imported clips** (`asset:<id>`, stored as `/renders/cut/media/<sha>.mp4`):
  `effects.fetchable_video` (`src/effects.py:824`) has no bucket fallback, unlike
  `talking_photo.fetchable_audio`, and `probe_video` is handed the bare name. On a
  machine without the file, an imported clip cannot be effected ("could not measure the
  source clip"). The Fly volume hides this today.
- **The editor's index** sends speech to `fal-ai/whisper` (`src/cut/index.py:329`) with
  `diarize: true`. It is unbilled to the person and carries no daily cap, so it is house
  spend proportional to uploads. That is by design, but nothing bounds it.
- **The prop and location sheet prompts** ask for panels "labelled in small capitals",
  and the sheet becomes `refs[0]` of every clip, so labels can leak into frames. The
  character sheet already says no text.
- The kit page (`web/src/app/studio/brand/**`) calls **no spending door**: create, edit,
  duplicate, files, end-card PNG, screens preview and keep are all free and unpriced, as
  they should be. Import runs one Gemini sort, behind the Create gate
  (`app/brand_routes.py:301`), and is rate-limited to 10 an hour. Nothing found there.
- Kit text is added **once** on every path read: stills (`app/api.py:6571`, with
  `dressed_kit` so the renderer does not add it again), keyframes (`scene_chain` 520 /
  670), clips (`fal.py:1992`), and connector clips (`for_project_id`). Element sheets
  pass `brand_kit=False`, and effects take no kit. No duplication found.
  `pricing.signed_hash` binds the kit's hash into the clip quote, so a kit edited after
  the price is caught as `stale_content`.

## Every door

"Endpoint" is whether the id exists on fal tonight. "Fields" means the body we send is
legal against the schema, with enums diffed. "Price" means the row against
`endpointBilling` and the page's price text.

| Door | Endpoint | Endpoint OK | Fields OK | Price OK |
|---|---|---|---|---|
| Effect `nano-banana-edit` | fal-ai/nano-banana/edit | yes | yes (aspect enum exact) | ~ ($0.039 vs $0.0398; same credits) |
| Effect `flux-kontext-pro` | fal-ai/flux-pro/kontext | yes | yes | yes ($0.04) |
| Effect `seedream-edit` | fal-ai/bytedance/seedream/v4/edit | yes | **no size sent: square output (#5)** | yes ($0.03) |
| Effect `remove-background` | fal-ai/bria/background/remove | yes | yes | yes ($0.018) |
| Effect `kling-effect` | fal-ai/kling-video/v1.6/standard/effects | yes | **7 dead `effect_scene` values (#4)** | yes ($0.056/s) |
| Effect `pixverse-effect` | fal-ai/pixverse/v5/effects | yes | yes (8 s exists, not offered) | yes (0.15/0.20/0.40) |
| Effect `camera-move` | fal-ai/pixverse/v4.5/image-to-video | yes | yes; no 2048-byte prompt cap (#11) | **no: half price (#3)** |
| Effect `upscale` / Finish | fal-ai/topaz/upscale/video | yes | yes (default model Proteus) | ~ long-side tier (#10) |
| Effect `add-sound` | fal-ai/mmaudio-v2 | yes | yes (duration 1-30) | yes ($0.001/s) |
| Effect `reframe` | fal-ai/luma-dream-machine/ray-2-flash/reframe | yes | yes | yes ($0.06/s) |
| Effect `reframe-hq` | fal-ai/luma-dream-machine/ray-2/reframe | yes | yes | yes ($0.20/s) |
| Effect `remove-video-background` | veed/video-background-removal | yes | yes | yes ($0.0225 / $0.015 per 30 frames) |
| Effect `remove-video-background-pro` | bria/video/background-removal | yes | yes | yes ($0.14/s) |
| Recipe effects (10) | fal-ai/kling-video/v3/turbo/pro/image-to-video | yes | yes (prompts 361-701 chars, under 3072) | yes ($0.14/s) |
| Free looks | local ffmpeg | n/a | n/a | free |
| Talking photo clip | bytedance/omnihuman/v2 | yes | yes (image_url, audio_url, prompt) | yes ($0.105/s, whole seconds up) |
| Voice preview | fal-ai/elevenlabs/tts/eleven-v3 | yes | yes (text ≤5000, voice, language_code) | yes ($0.10 / 1k chars) |
| Clip edit, frame | (nano-banana-edit) | yes | yes | ~ as above |
| Clip edit `kling-o1` | fal-ai/kling-video/o1/standard/video-to-video/edit | yes | yes (limits match x-fal; prompt ≤2500) | yes ($0.126/s) |
| Clip edit `kling-o1-pro` | fal-ai/kling-video/o1/video-to-video/edit | yes | yes | yes ($0.168/s) |
| Clip edit `flux-3` | blackforestlabs/flux-3/edit-video | yes | yes (prompt ≤4096) | yes ($0.03/s) |
| Element sheet (fal lane) | openai/gpt-image-2.5/sunburst/edit | yes | yes (1360x768, quality high) | **no: flat $0.06 vs ~$0.09-0.11 token-billed (#8)** |
| Keyframes | Gemini (nano_banana) | n/a (Gemini) | kit look added once; kit refs may lead (#12) | per still, capped by `limit` (not re-audited) |
| render_qc | Gemini FAST_MODEL, video inline ≤18 MB | n/a | **all kit products for every shot (#6)** | free (metered) |
| Brand import sort | Gemini fast brain | n/a | yes | free, behind the Create gate |
| Editor index transcript | fal-ai/whisper | yes | yes (transcribe, word, diarize) | unbilled to the person, no cap |
| Editor agent, shot logs, motion ad | Gemini | n/a | proposals only | free (metered) |
| Quick edit / trim / reformat / assemble / end card / kit screens | local ffmpeg / Pillow | n/a | n/a | free |
