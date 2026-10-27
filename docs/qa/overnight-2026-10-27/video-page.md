# Video page and clip-render path: overnight audit 2026-10-27

Scope: `/studio/video` (direct-generator.tsx, lib/direct.ts), `src/direct.py`,
`/api/direct/video/*`, `src/fal.py` (VIDEO_MODELS, SLOTS, REF2V, PROMPT_MAX,
build_body, generate_video, generate_from_prompt, generate_for_shot incl. one_clip),
`src/pricing.py` one-clip estimate, `src/timeline.py` one_clip_prompt.

Method: code read at `f7d41665` (origin/main), fal's live queue OpenAPI schema for all
29 endpoint ids we call (`fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>`), fal's
rate cards (`fal.ai/api/models?keywords=<id>` `pricingInfoOverride`, and the model page's
embedded copy for ids the search did not return), request bodies built with
`build_body` without sending, and a sweep of `direct.video_quote` against the hold.
No key used, nothing submitted, no database written.
Tests: `pytest tests/test_fal*.py tests/test_direct*.py tests/test_one_clip.py` 122 passed;
`node --test web/tests/direct*.test.mjs` passed.

Line numbers are HEAD's (another session has uncommitted image-page edits to
`src/fal.py` / `src/direct.py` in this worktree; none touch the video code below).

## Findings

### 1. BREAKS: every Kling 4.0 image-to-video sends the start frame in the wrong field (CONFIRMED)
`src/fal.py:441-466` (SLOTS["kling4"] has no `image_field`), used by `build_body` at `src/fal.py:1074`.

- Schema `kling/v4/image-to-video`: `required: ["start_image_url"]`; there is no `image_url`
  property at all.
- Ours:
  ```
  build_body('a cat', model='kling4', image_url='https://x/i.png', duration=13, resolution='720p')
  -> ('kling/v4/image-to-video', {'prompt': 'a cat', 'image_url': 'https://x/i.png', 'duration': 13, 'resolution': '720p'})
  ```
- Failure: on the Video page, Kling 4.0 + one picture (the default "Start" mode) is held,
  submitted, and comes back 422 after the queue wait (fal validates with the job: the LTX
  2.3 lesson in the table's own comment). Same for a scene on Kling 4.0 that splits
  (longer than 30s, or a shot already has its clip: every part is anchored on its keyframe),
  and for a one-clip scene whose photos could not be made fetchable (falls back to the anchor).
  The hold is released, so nothing is charged, but the render never works.
  No test covers a kling4 i2v body (`tests/test_fal.py:210` checks Wan only).
- Fix: add `"image_field": "start_image_url"` to SLOTS["kling4"] (it survives `enable_slots`,
  which strips only label/blurb/available/routing) and a test like Wan's.

### 2. WRONG PRICE: LTX 2.3 is quoted at the old rate, 25% under fal's invoice (CONFIRMED)
`src/fal.py:210` `"prices": {"1080p": 0.06, "1440p": 0.12, "2160p": 0.24}` (checked 2026-09-26).

- fal today, both `fal-ai/ltx-2.3/text-to-video` and `/image-to-video`: "Your request will
  cost **$0.08** per second for 1080p, **$0.16** per second for 1440p or **$0.32** per second
  for 2160p."
- Effect: a 6s 1080p clip is quoted 87 credits (from $0.36) but fal bills $0.48, so the
  effective markup is 1.8x, not `MARKUP = 2.4`. It is still the platform DEFAULT_MODEL and
  every scene with no model pick renders on it. `web/src/content/pricing.json` (the public
  /pricing and /models) carries the same stale number. The "cheapest real clip" comment and
  the draft/band reasoning ("$0.06/s ... cheapest credible LTX") are now wrong too: LTX 2.5
  Fast at 720p ($0.09/s) is close.
- Fix: re-date the row at 0.08 / 0.16 / 0.32, then `python -m src.pricing export`.

### 3. WRONG PRICE (over): Seedance 2.0 and 2.0 Fast at 480p are quoted at the 720p rate, about 2x fal's (CONFIRMED rate card, magnitude PLAUSIBLE)
`src/fal.py:300` (`seedance2-fast` 480p 0.2419) and `src/fal.py:317` (`seedance2` 480p 0.3034).

- fal bills Seedance 2.0 by tokens: "$0.014 per 1,000 tokens for 480p, 720p and 1080p ...
  tokens = (height * width * duration * 24) / 1024" (Fast: $0.0112). The quoted $0.3034/s is
  exactly 1280x720 (21,600 tokens/s). 480p is about 10,300 tokens/s (fal's own US-region card
  gives 480p as $0.1731 at $0.0168/1k, i.e. 10,304 tokens/s), so 480p is about $0.144/s
  (standard) and $0.115/s (Fast).
- Effect: a person who picks 480p to save money pays over double the markup, and
  `draft_resolution` offers no Seedance 2.0 draft because the table says 480p saves nothing.
- Related, PLAUSIBLE: the token formula also makes 21:9 and 1:1 at 720p cost more than 16:9 /
  9:16 if fal renders them at more pixels; we price every frame alike. Check one invoice
  before acting.
- Fix: price 480p at 0.1442 / 0.1154 (re-read the card), which also turns on a 480p draft.

### 4. BREAKS (long scenes): a one-clip scene prompt is never checked against the model's prompt cap (CONFIRMED path, PLAUSIBLE frequency)
`src/fal.py:1955` (one_clip_target) through `:2041` (generate_video); `fal.PROMPT_MAX` is read
only by `src/direct.py`.

- The one-clip prompt is the directive + every shot + continuity + the pictures list + the
  scene's tail, then the brand kit dress. Kling 3 Turbo caps `prompt` at 3072 characters
  (`maxLength: 3072`), Grok at 4096, LTX at 5000. Over the 23 timed scenes in the
  2026-10-07 corpus backup, `one_clip_target(...)["prompt"]` runs 1,463-3,219 characters
  before the kit is added; 1 of 23 is already over Kling 3's cap. Today's scenes are written
  with more shots than that corpus.
- Failure: the hold is taken and the job queues, then fal returns 422; the person sees a
  render failure (nothing charged) with no hint that the prompt was too long, and approving
  again fails the same way.
- Fix: in `generate_for_shot` (or in `pricing._one_clip`, so the card says it before the
  click), refuse when `len(prompt) > prompt_max(model)` with a plain line, or split instead
  of one clip when the composed prompt does not fit.

### 5. MISLEADING: pictures past a start-only model's one are dropped without a word (CONFIRMED by code read)
`web/src/components/studio/direct-generator.tsx:253-255, 318-325`; `app/api.py:6779-6780`.

- Attach 4 pictures on Seedance (held as references), switch the model to LTX / Veo / Wan /
  Kling 3 / Grok Lite (`max_refs` 0): `refs` keeps all 4, `videoRefMode` becomes "start",
  the form still uploads all 4, and the server uses `image_refs[0]` only. The page tags the
  first "Start" but says nothing about the other three (the Image page has `referencesLine`
  for this; the Video page does not).
- Fix: on model change, trim `refs` to `vCap` with a pick note ("LTX 2.3 starts on one
  picture; the other 3 were taken off"), or show the same "not sent" line.

### 6. MISLEADING: a reference that cannot be fetched is dropped silently, and the prompt still names it (CONFIRMED by code read)
`src/fal.py:2222-2226` (generate_from_prompt), `app/api.py` direct_video_run result.

- If 1 of 3 held pictures cannot be made public, the clip renders with 2 references while
  the person's prompt says `@Image3`; the job's detail says only "done". (The hold is then a
  cent lower on Grok than the button: harmless.) The one-clip scene path already handles
  this correctly by tagging only what went out.
- Fix: put the result's `references` count in the job detail when it is below what was
  quoted ("2 of 3 pictures reached Seedance 2.5").

### 7. POLISH: Grok 1.5 references at 1080p is refused, but the page does not steer to it
`src/direct.py:156-158` (CLOSED server side: `video_quote` refuses "renders 480p or 720p
with pictures", and the run route re-quotes, so a 1080p reference render cannot be held);
`pricing._one_clip` refuses it for scenes since #515. The front end receives
`ref_resolutions` (`src/direct.py:118`, `lib/direct.ts:36`) and never reads it: a person on
1080p who adds two pictures gets an error under a disabled button instead of a resolution
menu that only offers 480p / 720p.
- Fix: when `refMode === "references"` and `ref_resolutions` is set, narrow the resolution
  menu to it and move a 1080p pick to 720p with a pick note.

### 8. POLISH: the Video prompt is not quite "sent as typed"
`src/direct.py:57`: `" ".join(str(raw).split())` folds every newline. A pasted multi-shot
prompt ("SHOT 1 ...\nSHOT 2 ...") reaches the model as one line. Fix: collapse runs of
spaces only, keep line breaks.

### 9. POLISH: smaller table drift (CONFIRMED against the schemas)
- Wan 3.0 now takes `duration` 2-30 (`anyOf integer minimum 2 maximum 30`); we offer 2-10
  (`src/fal.py:262`). Safe, just short; a 13s scene splits on Wan when it could be one clip.
- Grok 1.5 / Lite image-to-video bill $0.01 per input image ("Each input image costs
  $0.01"); a start frame is not in the quote or the hold. Documented in the table's comment
  as covered by MARKUP; it is under a credit, so the button is still the hold.
- Seedance 2.0 image-to-video and Veo 3.1 image-to-video are `status: "unlisted"` on fal
  (they still answer). Worth a watch: an unlisted id is the usual step before removal.

### Checked and fine
- **Price on the button = quote = hold.** Swept every model x resolution x legal length x
  {0, 1, max} references through `direct.video_quote` and compared with
  `ledger.charge_credits(fal.estimate_cost(...))`, what `generate_from_prompt` holds:
  834 combinations, 0 mismatches. The run route re-quotes and 409s if the number moved;
  the front end sends the shown `quote.credits` as `expect_credits`.
- **Tag syntax** matches each reference endpoint's own description: Seedance 2.0 / 2.0 Fast /
  2.5 "Refer to them in the prompt as @Image1, @Image2"; Kling 4.0 "referenced as @Image1,
  @Image2, ... (max 10)"; Grok "Tag references as <IMAGE_0>, <IMAGE_1>". Field names and
  maxima match (image_urls 9 / 9 / 30 / 10, reference_image_urls 7 with minItems 1).
- **Aspect on the reference endpoint.** `build_body` sends `aspect_ratio` whenever there is
  no start frame, so the ref endpoints get it: the Video page sends the person's pick; a
  one-clip scene sends `DEFAULT_ASPECT` "9:16" (scenes have no aspect of their own; the house
  frame is 9:16), so a 9:16 scene comes back 9:16 rather than Kling 4 / Grok's own default
  16:9. Example: `('kling/v4/reference-to-video', {..., 'image_urls': [...], 'duration': 13,
  'aspect_ratio': '9:16', 'resolution': '720p'})`.
- **Duration fit-up for one clip** (13s scene, `pricing.estimate_scene`): Kling 3 13s,
  Seedance 2.0 / Fast / 2.5 13s, Grok 1.5 / Lite 13s, Kling 4 13s, LTX 2.5 Fast 14s (enum, up)
  all one clip; LTX 2.3 / LTX 2.5 Pro (max 10), Veo (max 8), Wan (our max 10) split. Wire
  types match the schemas (LTX int enum, Seedance string enum, Veo "8s", Kling 3 string,
  Grok / Kling 4 / Wan int).
- **Elements on the Video page:** now offered (PicturePicker has an Elements tab,
  `direct-generator.tsx:932-993`). The known open item is closed.

## Model x endpoint table

OK = matches fal's live schema / rate card today. Prices are ours vs fal's, USD per second.

| Model | Endpoint | Id | Fields | Durations | Res / aspects | Price | Prompt cap |
|---|---|---|---|---|---|---|---|
| ltx2.3 | t2v `fal-ai/ltx-2.3/text-to-video` | OK | OK | OK (6/8/10 int) | OK | **WRONG** 0.06/0.12/0.24 vs 0.08/0.16/0.32 | OK 5000 |
| ltx2.3 | i2v `fal-ai/ltx-2.3/image-to-video` | OK | OK | OK | OK (aspect not sent) | **WRONG** as above | OK 5000 |
| ltx2.5-fast | t2v `lightricks/ltx-2.5/text-to-video/fast` | OK | OK | OK (6-20 even, int) | OK | OK 0.09/0.13/0.19/0.30 | OK 5000 |
| ltx2.5-fast | i2v `lightricks/ltx-2.5/image-to-video/fast` | OK | OK | OK | OK | OK | OK 5000 |
| ltx2.5 | t2v `lightricks/ltx-2.5/text-to-video/pro` | OK | OK | OK (6/8/10) | OK | OK 0.12/0.17 | OK 5000 |
| ltx2.5 | i2v `lightricks/ltx-2.5/image-to-video/pro` | OK | OK | OK | OK | OK | OK 5000 |
| wan3 | t2v `alibaba/wan-3.0/text-to-video` | OK | OK | OK but short (we 2-10, fal 2-30) | OK | OK 0.05/0.10/0.20 | OK 20000 |
| wan3 | i2v `alibaba/wan-3.0/image-to-video` | OK | OK (`start_image_url`) | as t2v | OK | OK | OK 20000 |
| kling3-turbo-pro | t2v `fal-ai/kling-video/v3/turbo/pro/text-to-video` | OK | OK | OK (3-15 str) | OK (no res field) | OK 0.14 | OK 3072 (one-clip unchecked, #4) |
| kling3-turbo-pro | i2v `.../image-to-video` | OK | OK | OK | OK | OK | OK 3072 |
| seedance2-fast | t2v `bytedance/seedance-2.0/fast/text-to-video` | OK | OK | OK (4-15 str) | OK | 720p OK; **480p over** (0.2419 vs ~0.115) | none set (10000 guard) |
| seedance2-fast | i2v `.../fast/image-to-video` | OK | OK | OK | OK | as t2v | none |
| seedance2-fast | ref `.../fast/reference-to-video` | OK | OK (image_urls <= 9) | OK | OK (480/720) | as t2v | none |
| seedance2 | t2v `bytedance/seedance-2.0/text-to-video` | OK | OK | OK | OK (4k not offered) | 720/1080 OK; **480p over** (0.3034 vs ~0.144) | none |
| seedance2 | i2v `.../image-to-video` (unlisted) | OK | OK | OK | OK | as t2v | none |
| seedance2 | ref `.../reference-to-video` | OK | OK (<= 9) | OK | OK | as t2v ($0.014/1k, images do not change it) | none |
| seedance2.5 | t2v `bytedance/seedance-2.5/text-to-video` | OK | OK | OK (4-30 str) | OK | OK 0.2205/0.4730/1.164 | none |
| seedance2.5 | i2v `.../image-to-video` | OK | OK (aspect const auto, not sent) | OK | OK | OK | none |
| seedance2.5 | ref `.../reference-to-video` | OK | OK (<= 30) | OK | OK | OK | none |
| veo3.1 | t2v `fal-ai/veo3.1` | OK | OK (negative_prompt; audio default on) | OK ("4s"/"6s"/"8s") | OK (4k not offered) | OK 0.40 with audio (0.20 without, not offered) | OK 20000 |
| veo3.1 | i2v `fal-ai/veo3.1/image-to-video` (unlisted) | OK | OK | OK | OK | OK | OK 20000 |
| grok1.5 | t2v `xai/grok-imagine-video/v1.5/text-to-video` | OK | OK | OK (1-15 int) | OK | OK 0.08/0.14/0.25 | OK 4096 |
| grok1.5 | i2v `.../v1.5/image-to-video` | OK | OK | OK | OK | OK (+$0.01 frame not quoted) | OK 4096 |
| grok1.5 | ref `.../v1.5/reference-to-video` | OK | OK (reference_image_urls 1-7) | OK | OK; 480/720 only, refused at 1080p on both doors | OK +$0.01/picture quoted | OK 4096 |
| grok1.5-lite | t2v `.../v1.5/lite/text-to-video` | OK | OK | OK | OK | OK 0.02/0.03/0.14 | OK 4096 |
| grok1.5-lite | i2v `.../v1.5/lite/image-to-video` | OK | OK | OK | OK | OK (+$0.01 frame not quoted) | OK 4096 |
| kling4 | t2v `kling/v4/text-to-video` | OK | OK | OK (3-30 int) | OK | OK 0.157/0.235 | OK 26000 |
| kling4 | i2v `kling/v4/image-to-video` | OK | **BROKEN** (`image_url` sent, `start_image_url` required) | OK | OK | OK | OK 26000 |
| kling4 | ref `kling/v4/reference-to-video` | OK | OK (image_urls <= 10) | OK | OK (aspect sent, default would be 16:9) | OK (image refs only) | OK 26000 |
