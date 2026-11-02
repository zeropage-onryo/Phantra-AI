# Task: Every shape

Mike, 2026-11-02, after comparing the studio with Runway Ads' loop: the fastest volume win is
fanning one finished ad out into every placement's shape. Runway Ads resizes each variant for
every aspect ratio and channel on its own; here it is one click, free.

## What it does

From one finished clip or still (`gen:<id>`), **Every shape · free** makes **9:16, 1:1 and
16:9**, each a free reformat (`src/cut/quick.py`, the same body `reformat` and `/quick-edit`
use: ffmpeg on this server, no provider, no hold, `cost_usd` NULL), each its own item in the
Library with its own ad code.

- **Crop or pad, decided per shape** (`plan_every_shape`): crop when the frame keeps at least
  half the picture (`SHAPE_CROP_MAX = 0.25` per side: 9:16 <-> 1:1, 16:9 <-> 1:1), pad with bars
  when it would not (9:16 <-> 16:9, where a crop is a zoom on a sliver).
- **Nothing is made twice**: a shape the source already is (within 0.5%) is "this one"; a
  reformat of the same source to the same shape still on the wall (not deleted) is handed back
  as "made before".
- One shape that fails is a line with its reason; the others still come. A job where every
  shape that was to be made failed is a failed job ("Nothing was charged.").

## Doors

- `POST /api/every-shape {source, shapes?, project_id?}`: checked before the job starts (400
  `bad_edit` with the reason: a URL, an unknown shape, somebody else's item); the answer says
  what will be made; the job's result is `shapes: [{aspect, status: same|have|made|failed, fit,
  ref, asset_id, media_url}]`.
- The button (`components/studio/every-shape.tsx`, `lib/every-shape.ts`): under the in-chat Final
  cut beside Trim / hook / Edit the cut, and in the Library viewer's Details under the ad code.
  Each shape's line links to it in the Library.
- Vesper in the Ad Studio points to the button when asked for other placements
  (`prompts/studios/ads_turn.txt`) instead of writing new scenes.

## Ad results

A reformat carries no scene of its own, so `ad_results._owned_assets` follows its
`source_ref` (up to three hops) to the scene it came from: an ad that ran on the 1:1 cut of a
version counts toward that version's test (`docs/tasks/task-ad-results.md`).

## Verified

- `tests/test_every_shape.py` (9, real ffmpeg): the plan (same / crop / pad), refusals, the
  shapes made at their sizes with the source untouched and no ledger entry, a second click
  making nothing, a still staying a still, an ad on a shape counting toward its source's
  variant, the route and its job.
- `web/tests/every-shape.test.mjs` (4), typecheck, eslint.
- Clicked on a local API + `next dev`: a 720x1280 clip in the Library viewer, Every shape made
  1:1 (cropped) and 16:9 (with bars) and called 9:16 "this one"; a second click said both were
  made before. No sideways scroll at 390px.

## Not built

- A batch version (every shape of every version in a test at once).
- 4:5 is a known shape (`quick.SIZES`) but not in the default three.
