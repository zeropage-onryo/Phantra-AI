# Task: the direct generators (`/studio/image`, `/studio/video`) and the Video line's model

**From:** Mike, 2026-10-22: "in studio, we have all the image model options, can we do the same for
video?", then, on separate pages where you just pick a model: "Yes and make it for image too" —
with text-to-video allowed (no photograph required) on the direct Video page.
**Branch:** `claude/direct-generators`. **No flag**: Mike asked for the pages, so they are live on merge.

## What it is

Two doors beside Create's chat, for someone who already knows the model they want:

1. **`/studio/image`**: every image model the composer's picker lists (`model_menu.image_menu`:
   Nano Banana on Gemini, plus every `fal.IMAGE_MODELS` row), a prompt box, the shape (every
   `fal.IMAGE_SIZES` frame), up to 12 references (each model takes its own number; the page says
   before the click when a picture will not reach the one picked), one priced Generate button.
2. **`/studio/video`**: every advertised clip model (`pricing.catalog_rows`, so a ready slot like
   Kling 4.0 is in it the day it is), a prompt box, an optional **start frame**, and exactly the
   settings the picked model takes: its legal lengths, its resolutions, and its text-to-video
   frames (`fal.T2V_ASPECTS`, read off fal's schema per endpoint the same day). With a start frame
   the frame control says "follows the start frame", and no aspect is quoted or sent.
3. **The pick is final there.** Nothing proposes a model. The prompt goes to the model **as typed**:
   no enhance, no brain turn, no rewrite, no scene written. Moving to another model KEEPS what it
   takes (10s, 9:16) and resets each part it does not take to that model's opening value — never a
   nearest — and says so in one line.
4. **Text-to-video needs no photograph.** The reference gate (`preprod.reference_gate`) still guards
   every SCENE: consistency across shots is what it protects, and one free-standing clip writes no
   scene. This is the one door that renders a clip with no reference, on purpose.
5. **The composer's Video line gets a model picker**: "Auto" (the default; the brain may propose one
   per scene and the Render card opens on it, as before) or one model, which is then the person's.
   A pinned model is sent as the scene's `render_model` on every scene written (outranking any
   proposal) and told to the brain (`clip_model` → `creative_guide.clip_model_note`: propose no other
   model). The Render card is still the one place a clip from a scene is paid for.

## Money

- **The menus and quotes spend nothing.** `GET /api/direct/{image,video}`,
  `POST /api/direct/{image,video}/quote` are projections: `providers.check_render_choice` /
  `fal.image_usd` / `pricing.still_usd` at exactly the pick, converted by `ledger.charge_credits`
  (the number a hold takes). Credits only: `direct.public` strips the USD before the studio sees it.
- **A run is the click.** `POST /api/direct/{image,video}/run` (multipart, the composer's
  `files` / `asset_photos` reference fields) re-prices the pick and refuses with 409 `price_changed`
  if it is not the `expect_credits` the button showed, 400 `missing_price` without one, 400
  `bad_choice` for a pick off the model's legal set (refused, never clamped). Then one job
  (`kind: "make"`, which the activity tray links to the Library): `fal.generate_from_prompt`
  (`approved=True`, `bank=True`, `source="direct"`; cancellable, the fal receipt and the hold are
  that function's) or `fal.generate_image_from_prompt` / `nano_banana.generate_from_prompt`
  (`literal=True`, so the still-frame wrapper is not put round a typed prompt). No brand kit, no
  project: these are bare makes. The trial watermark and the daily caps apply as they do everywhere.

## Where things are

- `src/direct.py`: the menus, the quotes, `clean_prompt`, `public`.
- `src/fal.py`: `T2V_ASPECTS` + `t2v_aspects` (the frames each model takes on text-to-video; a
  model added without its row fails `tests/test_direct.py`).
- `app/api.py`: the six `/api/direct/*` routes after `/generate/run`; `clip_model` on
  `/api/creative-guide`.
- `src/creative_guide.py`: `clip_model_note`, `respond(clip_model=)`.
- `web/src/lib/direct.ts` (pure, `tests/direct.test.mjs`), `components/studio/direct-generator.tsx` +
  `.css` (prefix `dg-`, studio tokens only), `app/studio/{image,video}/page.tsx`.
- `web/src/components/studio/shell.tsx`: Image and Video on the rail after Create (not on the
  phone's bottom bar, which has no room; the Create home's two new tool tiles reach both there).
- `web/src/lib/create-v2.ts`: the `image_gen` / `video_gen` tool tiles.
- `web/src/app/studio/(create)/create-view.tsx`: the Video line's "Which model renders" menu
  (`lib/composer.ts` `loadVideoModel` / `saveVideoModel`).
- `src/pricing.py`: the catalogue blurbs no longer say "Premium only" / "1080p is premium" (no plan
  tier has refused a model since 2026-10-20); `web/src/content/pricing.json` regenerated.

## Links into the pages

`?model=<id>` opens a page on that model, `?prompt=` fills the box, and on Video `?start=<picture
address>` puts a start frame on (a still's **Animate** button on the Image page uses it).

## Not done (next)

- The public `/models` page's "Try now" still opens Create's chat; pointing each model's button at
  `/studio/video?model=<id>` (or `/studio/image?model=<id>`) is a one-line change per section, held
  back because it changes what a signed-out visitor lands on.
- Elements are not offered as references on the direct pages (uploads and Library stills are);
  Create's `@` is where a scene is held to an element.

## As built later: several pictures as references (2026-10-25, PR #491)

The Video page takes up to the model's own number of pictures as references (`fal.REF2V`:
Seedance 2.5, Seedance 2.0 / Fast, Kling 4 while its slot is on, Grok 1.5), and each model's own
prompt cap (`fal.PROMPT_MAX`, 10,000 where the schema sets none). One picture is still a start
frame unless flipped. Details in `task-vesper-audit-follow-ups.md`, item 1.
