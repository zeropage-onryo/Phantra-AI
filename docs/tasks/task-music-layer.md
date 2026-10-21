# The music layer: a bed for a cut, and the kit's loudness

Status: **BUILT 2026-10-21**, on Mike's "build the music layer". Nothing real was generated: the
walk ran with fal stubbed at `effects.run`.

## What it is

The editor's Audio tab gets a **Make music** card. It makes an instrumental bed as long as the
cut, in the project's brand-kit direction plus the person's own words, on the model they pick, at
the price on the button.

- **Models** (`src/music.py`, read off each endpoint's OpenAPI schema and model page on
  2026-10-21; re-check before trusting a number):
  - **Stable Audio 2.5**, `fal-ai/stable-audio-25/text-to-audio`: $0.20 a track, 1-190 seconds
    (`seconds_total`). This is the default.
  - **ElevenLabs Music**, `fal-ai/elevenlabs/music`: $0.60 per output minute, rounded UP;
    3-600 seconds (`music_length_ms`), `force_instrumental: true`.
- **Direction.** `direction_from_kit` reads the kit's `sound.music` (genre, mood, BPM), which was
  stored and unread until now. The person's words are added after it. `prompts/music_prompt.txt`
  wraps both: always instrumental, made to sit under text and a voiceover.
- **Length and price.** The length is the cut's, in whole seconds rounded up. A length off a
  model's range is refused, never clamped. The price is `ledger.charge_credits(usd)`.
- **The spend.** It runs through `effects.run`, exactly like the talking photo's voice preview:
  the cap, the CREDIT HOLD before the submit, the generations row and settle. The bed is filed as
  an `asset:<id>` audio in the editor's media bin, the same handle an uploaded bed has.
- **Routes**, on the editor's router:
  - `GET /api/cut/projects/{id}/music`: the menu, each model priced for this cut.
  - `POST .../music/quote`
  - `POST .../music/run`: a job, held to `expect_credits` (409 `price_changed` when it moved, 400
    `missing_price` without it).
- **Placement** (`web/src/lib/cut/music.ts`, pure). These are the editor's ordinary ops, each an
  undoable version:
  1. a music track when the cut has none
  2. `overwrite` the bed from frame 0, cut to the cut's length
  3. a one-second `set_fade` out
  4. `duck` under the voice when there is voice on the cut
- **Loudness.** A kitted export is mastered to the kit's `sound.loudness` (`render.compile_args`
  `loudness=`, passed by `render.render` from the kit). Every other export stays at -14 LUFS (the
  no-kit goldens hold). The Audio tab's Loudness note says which.

## The walk

On a throwaway schema, with fal stubbed to return a real audio file and the Gygler kit (warm
acoustic pop, optimistic, 104 BPM, -16 LUFS):
1. The menu priced a 15s bed at 48 credits on Stable Audio and 144 on ElevenLabs.
2. Make music filed `music-stable-audio-25-15s.wav` and laid it on a new music track with its fade
   (version 4).
3. The MP4 export carried it and measured **-16.1 LUFS integrated**.

## Not built

- **A real generation.** It waits for Mike's word, because it is a real fal spend.
- **The kit's default voice:** a voiceover generated from it.
- **Reference tracks** (`music_ref`): stored, not sent to a model.
- **Snapping beats to the BPM.**
- **Music on the connector:** no MCP change.

## Music under the end card (2026-10-21, follow-up)

The card used to play over silence. Two parts fix it:
- **The bed is sized for cut plus card.** `_music_request` adds `brand.card_frames(kit, fps)`:
  the card's length less its crossfade, and 0 when the kit has no card.
- **The bed plays on under the card.** `brand.with_end_card(..., media=)` lengthens a music clip
  that ends where the cut ends, up to the new end, as far as its file has sound. Its fade-out moves
  with it. A bed that stops earlier, or a sped or reversed one, is left alone.

`tests/test_music.py` checks it in a real export: the sound is audible under the card. A cut with
no kit never reaches this, and the goldens hold.
