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
- **The kit's default voice:** BUILT 2026-10-21, see "The voiceover" below.
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

## The voiceover (2026-10-21, the kit's default voice)

The kit has stored `sound.voice` since it was built, and nothing read it. **Make a voiceover** sits
on the Audio tab under Make music (`web/src/components/cut/voiceover-card.tsx`, `src/voiceover.py`,
`/api/cut/projects/{id}/voiceover`, `/quote`, `/run`):
- **The voice.** The card starts on the kit's voice when its line names one of the 21 voices
  ElevenLabs v3 offers (`talking_photo.VOICES`), matched as a whole word in any case. It is marked
  "(kit)" in the picker. A line that names no voice ("warm, mid-30s") is shown beside the picker
  and never sent. Without either, the model's own default (Rachel) is used. Any other name is
  refused.
- **The price.** Same as the talking photo's voice preview: same endpoint, same body, per character
  (`talking_photo.voice_usd`), so most lines come to the 10-credit floor. It is held to
  `expect_credits` (409 `price_changed`) and runs through `effects.run` as `voiceover-eleven-v3`.
  There is no 50-character minimum here. That floor exists only because a talking clip refuses
  audio under 4s.
- **The placement** (`web/src/lib/cut/voiceover.ts`, pure, `tests/cut-voiceover.test.mjs`): adds
  a voice track if there is none, then overwrites the read at the playhead, whole. A line is never
  cut mid-word, so a read that runs past the picture lengthens the cut, and the toast says by how
  much. If the music isn't already ducking, it is set to duck under the voice. Each step is its
  own version and can be undone.
- **No MCP change.** The talking photo's `voice_preview` and its routes are untouched. The new
  module only calls their check, price and body functions.

Walked on a throwaway schema with fal stubbed. The kit line "George, low and calm" opened the card
on George, and a 47-character script was priced at 10 credits. fal received
`{"text": ..., "voice": "George"}`. Versions 5 to 7 were: add voice track, overwrite the read at
0.0s, duck A1 under voice. **No real voice was generated**, because that is a real fal spend.

## Drafting the script (2026-10-21, follow-up)

The card's **Draft** button writes the script for free, using one model call
(`voiceover.write_script`, stage `voiceover_script`,
`prompts/voiceover_script_prompt.txt`, `POST .../voiceover/script` as a job behind the Create
gate). The model gets:
- the kit's BRAND block, the same one the motion ad reads;
- the words on screen in time order: headlines, labels and caption cues (the big background
  words are left out), with an instruction to say the same idea in different words, not read
  the screen aloud;
- a word budget of 2.5 words a second of cut.

What comes back is checked, and each problem is a warning under the box, never a rejection:
- too long for the cut (over 1.3x the budget);
- a number that nothing above gives (`motion_ad.unsourced_numbers`);
- a word the kit says never to use.

The draft lands in the box for the person to edit. Editing it clears the warnings. Nothing is
read aloud or priced until they press Make voiceover.

Walked with the model stubbed: the prompt carried the kit's tone and banned word, the one
headline on screen, and "about 25 words" for 10 seconds. The draft filled the box and flagged
"hustle", and the button priced it at 10 credits. **No real model call was made.**
