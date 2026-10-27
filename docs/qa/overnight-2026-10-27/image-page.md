# Overnight QA 2026-10-27: the Image page and every still door

Scope: `/studio/image` (`web/src/components/studio/direct-generator.tsx`, `web/src/lib/direct.ts`),
`src/direct.py`, `/api/direct/image/*` (`app/api.py`), `fal.IMAGE_MODELS` + `fal.image_request` /
`image_usd` / `named_dims`, `src/nano_banana.py`, `model_menu.image_menu`, and the Create still
(`/api/generate/run`) where it shares this code. Audited at `f7d41665` (origin/main).

Method: read-only. Every endpoint's live queue OpenAPI schema fetched from
`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>` (14 endpoints, all 200), pricing
from `https://fal.ai/api/models?keywords=<id>` (`pricingInfoOverride` / `billingMessage`), the model
pages' `llms.txt` and, for the GPT models, the price table on the model page. Request bodies built
with `fal.image_request` for every model x every aspect, no call sent. No spend, no DB write.
`tests/test_direct.py tests/test_model_menu.py tests/test_fal.py`: 100 passed (one of them locks in
finding 1).

## Model table

| Model (id) | Endpoint(s) exist? | Fields we send legal? | Aspects really the labelled shape? | Price row matches fal? |
|---|---|---|---|---|
| FLUX 1.1 Pro (`flux-pro1.1`, the default) | yes `fal-ai/flux-pro/v1.1` (no edit) | **NO**: sends `width`/`height`, which the schema does not have (it takes `image_size`) | **NO**: fields ignored, every still comes back at fal's default `landscape_4_3` | yes, $0.04/MP rounded up ("$0.04 per megapixels", "billed by rounding up") |
| FLUX.2 Pro (`flux2-pro`) | yes, `fal-ai/flux-2-pro` + `/edit` | yes: `image_size` {w,h}, multiples of 16, within the x-fal bounds (256..2560, area <= 4,194,304); `image_urls` on edit | yes, all 10 | text draw yes ($0.03 first MP + $0.015/extra MP). References priced as 1 MP each, but fal bills real input MP (see 4) |
| Nano Banana Pro on fal (`nano-banana-pro`) | yes, + `/edit` | yes: `aspect_ratio` is in the enum for all 10 aspects; `resolution` not sent = 1K | yes | yes, $0.15/image (4K double, not offered) |
| Seedream 4.5 (`seedream4.5`) | yes, `.../v4.5/text-to-image` + `/edit` | yes: doubled frames all inside 2560x1440..4096x4096; `image_urls` max 10 matches "up to 10" | yes | yes, "$0.04 per images" |
| GPT Image 2 (`gpt-image-2`) | yes, `openai/gpt-image-2` + `/edit` | yes: `quality: medium` legal; `named_dims` {w,h} all multiples of 16, >= 655,360 px, edge <= 3840, ratio <= 3:1; `image_urls` maxItems 16 = ours | **yes, the 2026-10-24 fix holds for every aspect** (9:16 -> 944x1664 = 0.567, 21:9 -> 1920x816) | output yes (medium: 1024x1024 $0.053, 1024x1536 $0.042, 1920x1080 $0.040). Input image tokens on `/edit` not priced (see 5) |
| GPT Image 2.5 Flare | yes, `.../flare/text-to-image` + `/edit` | yes: `quality: high` legal, {w,h} legal, `image_urls` max 16 | yes | output yes (high 1024x1024 $0.05268, held at $0.06). Input image tokens not priced (see 5) |
| GPT Image 2.5 Sunburst | yes, same shape | yes | yes | same as Flare |
| Ideogram 4.5 (`ideogram4.5`) | yes, `ideogram/v4.5` | yes: `quality: medium`, named `image_size` | **NO for 5 of 10**: 4:5, 2:3 -> 3:4; 5:4, 3:2 -> 4:3; 21:9 -> 16:9 (see 2) | yes, medium $0.06 any size |
| Nano Banana via Gemini (`nano`) | n/a (Gemini API, `NANO_BANANA_MODEL`) | `image_config.aspect_ratio`: all 10 aspects are Gemini aspects | yes, unless the config is rejected (see 9) | yes: flash-image $0.039, 3-pro-image $0.134 (1K/2K) |

Prompt caps: the page holds every still to `direct.PROMPT_MAX = 4000`, under every model's own cap
(Ideogram 10,000; GPT 32,000; Nano Pro 50,000; FLUX none listed). One floor: Nano Banana Pro on fal
has `minLength: 3` (see 8). Nothing sends `seed`, `num_images` (default 1 everywhere, Seedream
`max_images` default 1) or `output_format` (see 7).

## Findings

### 1. FLUX 1.1 Pro ignores the frame: every still is 4:3 landscape (wrong output, the default model)
- `src/fal.py:685` (`"params": ("width", "height", ...)`), `src/fal.py:947-948` (the `width in params`
  branch), `src/fal.py:1626-1627` (generate_image does it again); the test locks it in at
  `tests/test_fal.py:779`.
- Scenario: Image page (or Create, or the MCP), FLUX 1.1 Pro, 9:16 -> body
  `{"prompt": ..., "width": 768, "height": 1360}`. fal's `FluxProV11Input` has no `width` / `height`
  property: its frame field is `image_size` (preset enum or {width, height}), `"default":
  "landscape_4_3"`. Extra fields are dropped, so the still comes back 1024x768 landscape whatever was
  picked, and every clip started from it is landscape too. FLUX 1.1 Pro is `DEFAULT_IMAGE_MODEL`.
- Evidence: CONFIRMED from the schema (field absent, default `landscape_4_3`) and the snippet (all 10
  aspects send keys `['height','prompt','width']`). The output shape is PLAUSIBLE: I made no live call;
  one 9:16 draw, roughly 10 credits, would confirm it.
- Fix: drop the width branch. Give the row `"params": ("image_size", "seed")` so it takes the
  `{width, height}` path the other FLUX row uses, and fix the test.

### 2. Ideogram 4.5 draws five of the ten offered frames in another shape (wrong output, and a clamp)
- `src/fal.py:827-831` (`IMAGE_SIZE_ENUM`), `src/direct.py:177-179` / `:199` (every model is offered
  every frame), `src/direct.py:211` (the only aspect check is against `IMAGE_SIZES`).
- Scenario: Ideogram 4.5, 4:5 -> `portrait_4_3` = 864x1152 (3:4). 2:3 -> 3:4. 5:4 and 3:2 -> 4:3.
  21:9 -> `landscape_16_9`. The page shows the 4:5 frame and charges for it, then a 3:4 picture
  arrives. That is the GPT Image 2 9:16 -> 2:3 bug again, on another model, and it breaks "refuse,
  never clamp".
- Evidence: CONFIRMED (snippet output above; the schema says the 4:3 presets are 1152x864 / 864x1152).
  The schema accepts these explicit sizes: `896x1120` (4:5), `1120x896` (5:4), `832x1248` (2:3),
  `1248x832` (3:2), `864x1152`, `1152x864`, `720x1280`, `1280x720`, `1024x1024`. There is no 21:9 size
  (the nearest are 2880x1440 = 2:1 and 3072x1280 = 2.4:1).
- Fix: send Ideogram an explicit `{width, height}` from that list for each aspect. Then have the menu
  carry per-model `aspects` and `image_quote` refuse a frame the model cannot draw (21:9 on Ideogram).

### 3. In Create, a FLUX.2 Pro still with references holds up to 3.6x the price on the card (wrong price)
- `web/src/app/studio/(create)/create-view.tsx:1565` and `:3058` (the card's and the send line's price
  is the menu's 1:1, no-reference figure), `app/api.py:6417-6600` (`/generate/run` takes no
  `expect_credits`), `src/fal.py:2379-2381` (the hold counts the references).
- Scenario: Create, image model FLUX.2 Pro, 8 pictures attached. The card says 10 credits
  (`charge_credits(0.03)`). The hold is `image_usd("flux2-pro", aspect, references=8)` = $0.15 =
  36 credits. CLAUDE.md promises a still is "never above the price the send button showed". The
  Image page is safe: its quote counts references and the run is held to `expect_credits` (409).
- Evidence: CONFIRMED by reading the code and computing it (`ledger.charge_credits(0.03)=10`,
  `(0.15)=36`). GPT Image 2 goes the other way (the card shows 13 for 1:1, a non-square still holds 11),
  so it is harmless.
- Fix: price the Create still with `direct.image_quote(model, aspect, references=n)` and have
  `/generate/run` take `expect_credits` for the still, like the direct route.

### 4. FLUX.2 Pro references are priced as 1 MP each, but fal bills their real size (wrong price, under-held)
- `src/fal.py:886-888` (`refs` counted as one megapixel each). `as_image_url`
  (`src/fal.py:1651+`) uploads photos as they are, with no downscale.
- Scenario: a 12 MP phone photo (4032x3024) as a reference. fal's rule is "$0.015 per extra megapixel
  of input and output, rounded up", so that one input is about $0.18. We hold $0.015. Eight such photos
  cost about $1.47 against a $0.15 hold. The person is never overcharged, but the hold and the settle
  are far below cost, and the `/costs` meter under-reads.
- Evidence: the pricing text is CONFIRMED (`pricingInfoOverride` on `fal-ai/flux-2-pro/edit`). That fal
  counts an input at its uploaded size is PLAUSIBLE: the docstring at `src/fal.py:675` already admits
  "real size is not known at pricing time".
- Fix: downscale references to <= 1 MP (1024x1024) before upload for this model, or price each
  reference by its real pixel count.

### 5. The GPT Image references cost tokens that are not priced (wrong price, under-held, PLAUSIBLE)
- `src/fal.py:747-756` (gpt-image-2 `usd_by_size`), `:770-797` (2.5 Flare/Sunburst `usd_per_image: 0.06`).
- Scenario: GPT Image 2 or 2.5 `/edit` with 16 references. fal bills "Image tokens (per 1M): $8.00
  input" on top of the output-image price. Our rows are the OUTPUT table only (the 2.5 page says
  outright "It does not include text input tokens"). Sixteen high-fidelity inputs are likely tens of
  thousands of input tokens, roughly $0.1-0.5, against a $0.042-0.06 hold.
- Evidence: the pricing text is CONFIRMED (`pricingInfoOverride` on all three). The per-reference token
  counts are PLAUSIBLE; one real `/edit` call's fal invoice line would settle it.
- Fix: add a per-reference input charge (`per_ref_usd`) to these rows in `image_usd`, or cap the
  references these models get on the Image page.

### 6. A text-only model is quoted with references "attached" and the result never says they were dropped (misleading)
- `src/direct.py:225` (silently `used = 0`), `app/api.py:6849` and `:6869`.
- Scenario: FLUX 1.1 Pro or Ideogram with 3 pictures attached. The page does warn before the click
  ("draws from the prompt only", `referencesLine`). But the server accepts, and because
  `refs = image_refs[:0]` is empty, the job's "takes no reference images" note
  (`if refs and not nano ...`) can never fire. The same holds for the MCP or any other client that
  skips the warning.
- Evidence: CONFIRMED (code path).
- Fix: either refuse (400 "FLUX 1.1 Pro takes no pictures") when `references > 0` on a 0-cap model, or
  test `image_refs` instead of `refs` at `app/api.py:6869`.

### 7. PNG bytes are stored as `.jpg` and served as `image/jpeg` (polish)
- `src/fal.py:2378` (`.jpg` name), `:2425` (`_publish(..., "image/jpeg")`), `:1356` (`_download`
  writes the bytes as they come).
- Scenario: Nano Banana Pro (fal), GPT Image 2, 2.5 Flare and 2.5 Sunburst all default to
  `output_format: "png"`. The file is a PNG with a `.jpg` name and a JPEG content type: about 3-5x
  larger, and any tool that trusts the extension is misled.
- Evidence: CONFIRMED from the schema (`"default": "png"`). That the bytes are PNG follows from it
  (PLAUSIBLE without a live call).
- Fix: send `"output_format": "jpeg"` on every row whose schema has it (FLUX already defaults to jpeg).

### 8. Nano Banana Pro on fal refuses prompts under 3 characters after the hold (polish)
- `src/direct.py:50-64` (no floor) vs the fal schema `prompt: {minLength: 3}` on `fal-ai/nano-banana-pro`
  and its `/edit`.
- Scenario: prompt "ad" on Nano Banana Pro (fal). The hold is taken, then fal answers 422, the hold is
  released, and the page shows a generic failure. Nothing is lost, but it is a wasted round trip.
- Fix: a per-model minimum in `clean_prompt`, or reject prompts under 3 characters for every still.

### 9. Gemini Nano drops the aspect without saying so when the config is refused (misleading, PLAUSIBLE)
- `src/nano_banana.py:321-327`.
- Scenario: an `INVALID_ARGUMENT` that names `aspect_ratio` or `image_size` (for example
  `NANO_IMAGE_SIZE` set to a size the model lacks) retries with NO config. The still comes back in
  whatever shape the model infers (the docstring's own 3:4-for-9:16 case), and no warning reaches the
  result.
- Fix: on the retry keep `aspect_ratio` and drop only `image_size`, and add a note to the result when
  anything was dropped.

### 10. Ideogram rewrites the prompt although the page promises "sent as typed" (polish)
- `src/fal.py:795-800` (left on by choice). The schema has `enable_prompt_expansion` default `true`.
- Fix: send `enable_prompt_expansion: false` from the direct page, or say "Ideogram expands your prompt"
  on its menu note.

### 11. Small notes (polish)
- FLUX.2 Pro's note says "takes up to 9 reference images", but the row has no `max_references`, so 8
  are sent (`image_max_refs` default). Fal's schema has no maxItems. Make the note and the cap agree.
- On the direct page the quote counts the pictures before `as_image_url`. If one cannot be made public
  it is dropped from the request: on FLUX.2 the hold is then lower than the button (harmless), but the
  person was told N references reach the model and fewer did, with no note (the note only fires at 0).
- `IMAGE_SIZES["16:9"] = 1360x768` is 1.771, not 1.778 (an 8 px difference). That is within tolerance,
  and fine for stills.

## What holds
- Every endpoint id exists, and every field sent (apart from finding 1) is in its schema with a legal
  value.
- GPT Image 2's `named_dims` keeps the true shape for all ten aspects, inside fal's pixel and ratio
  bounds. The 2026-10-24 fix holds, and the other {w,h} models (FLUX.2, Seedream, GPT 2.5) send the
  exact frame.
- The Image page's button price equals the hold: `image_quote` and the hold share `fal.image_usd` with
  the same reference count, and `ledger.charge_credits` is the one converter. The run is refused (409)
  if the price moved.
- The reference caps match the schemas (Seedream 10, GPT 16), and references reach the `/edit`
  endpoints as `image_urls`.
- Failure text goes through `failures.plain` ("Nothing was charged.").
