# Motion control: a still performs a clip's movement

Asked for 2026-11-14 (Mike: "lets do the build"). Kling's motion control on
fal takes a STILL of a character and a DRIVING CLIP and renders the still's
character doing the clip's movement, camera and timing. It is the first
effect that takes two kinds of source, so it is built into the effects
table as a new input shape rather than as a module of its own.

## As built (2026-11-14)

- **Two rows in `src/effects.py`**, category `motion` ("Copy a movement"):
  - `motion-control`: `fal-ai/kling-video/v3/standard/motion-control`, $0.126/s
  - `motion-control-pro`: `fal-ai/kling-video/v3/pro/motion-control`, $0.168/s
  Read off each model page and its llms.txt on 2026-11-14 (`CHECKED_MOTION`).
  Billed per second of the output, which is the driving clip's length, so the
  row is priced off the probed clip (`probe: True`).
- **The input shape `takes: "image+video"`** (`effects.MIXED`), sources
  `(2, 2)`, ORDERED: the still first, the driving clip second.
  `effects.is_mixed(row)` and `effects.split_mixed(named)` are the only
  readers of that order. `check_sources` refuses anything but two with a
  sentence that says the order. `build_body` writes `image_url` and
  `video_url`.
- **Options** (refused off the legal set, never clamped):
  `character_orientation` `image` (default; the still's framing, driving clip
  up to 10s) or `video` (the clip's framing, up to 30s), and
  `keep_original_sound` (default **false**: a driving clip is usually someone
  else's footage and its sound is not wanted). The prompt is optional.
- **The length cap depends on the option**: `row["max_seconds_for"](options)`,
  checked in `quote_usd` with the same half-second slack as the reframe. A
  clip over the cap is refused before it is priced, and the refusal says to
  trim it or switch to the clip's orientation.
- **Both doors read each half by its own reader.** The connector
  (`mcp_server.run_effect`): the still through `resolve_references`, the clip
  through `_video_sources` (a `gen:<id>` render or an `asset:<id>` import).
  The studio (`api._effect_request` / `_effect_urls`): probes `named[-1]`,
  the clip, and makes the still fetchable exactly as an image effect's.
- **The studio card** (`web/src/lib/effects.ts`): `pairFor` binds the still
  (attached first, else the newest) and the newest clip; `unavailable` and
  `missing` say which half is absent; an action taken on a result fills its
  own half and keeps the other. On the **Effects tab** either half can be
  dropped first and the next drop fills the other half (`fits` accepts both
  kinds for a mixed row; `load` keeps the half already on the card). That is
  the door for a clip that was not made in the studio: a dropped clip is
  uploaded as an `asset:<id>`.
- Tests: `tests/test_motion_control.py`, `web/tests/effects.test.mjs`,
  `web/tests/effects-tab.test.mjs`; the table's invariant test now allows the
  mixed shape.

## Added the same evening: face lock and clips in Create

- **Face lock** (Kling's `elements`). Optional sources AFTER the clip:
  `[still, clip, face, *more angles]`, up to 4 photos (`MOTION_FACES`), so a
  row's sources are `(2, 6)`. `build_body` sends ONE element: the first face
  photo is `frontal_image_url`, the rest are `reference_image_urls`, and with
  a single face photo the still is used as the second angle (the page says
  at least one reference image is required). The prompt gets `@Element1` put
  in front unless it already names it, because the element only binds where
  the prompt names it. Kling binds an element only with
  `character_orientation: video`, so `check_sources` REFUSES face photos with
  `image`, and the card switches to video the moment a face photo is on it
  (`begin`, and the Effects tab's `load`). Price unchanged: the model page
  lists no charge for an element. Treat that as unverified until the first
  real render's bill.
- **Clips in Create.** The composer's file picker, drop and paste now take
  mp4 / mov / webm. A clip is uploaded to the editor's media bin
  (`cutUploadMedia`, the Effects tab's upload) and sits on the box as a CLIP
  chip, named `asset:<id>`. `candidates()` takes it as an attached clip,
  ahead of the thread's clips, so it is what a clip effect binds first:
  motion control's driving clip, or an upscale's source. The chips are this
  page's state, not the saved draft: New session and Clear drop them, and a
  reload loses them (the upload itself stays in the media bin). The brain is
  not told about an attached clip; it is for effects.
- In Create, motion control binds: the first attached image (else the newest
  still) as the still, the attached clip (else the newest) as the clip, and
  the OTHER attached images as face photos (`pairFor`). On the Effects tab
  each drop takes its place by `addToPair`: a clip replaces the clip, an
  image is the still if there is none, else a face photo.

## Left out, with the reason

- **v2.6 tiers** ($0.07/s standard, $0.112/s pro): cheaper and older. Add a
  row if a budget tier is wanted; the shape is the same.
- **A listed tool** for the ChatGPT render listing (`LISTED_EFFECT_TOOLS`):
  not added, on purpose. The listing's tool list is the one submitted to the
  ChatGPT directory (pinned in `tests/test_mcp_server.py`, mirrored on
  `/mcp` and in `docs/directory/TWO_LISTINGS.md`), so a new tool there is a
  change to the submitted app: Mike's call. `test_mcp_add_element` names the
  two rows as studio-only. The studio surface's `apply_effect` reaches them.
- **A clip attached in Create is not saved with the draft.** The draft type
  (`ComposerDraft`) is stored by the server; adding a field to it is its own
  change, done if losing the chip on reload turns out to matter.
