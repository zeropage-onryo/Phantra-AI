# The Voice section (built 2026-10-26, restyled on main 2026-10-27)

Mike, 2026-10-26: "for all of this I want voice to have a separate ui section for all our voice
models." Status: **built and tested against a stand-in API; not run against fal; behind a flag
that is off.**

## What it is
- `/studio/voice`, a rail entry beside Effects (`AudioLines` icon), behind the `voice_tab`
  capability: `PHANTRA_VOICE_TAB=1` on the API turns it on. Off, the page is a 404 and the rail has
  no entry, exactly like the Effects tab.
- The model cards along the top are the server's list (`GET /api/voice`, `src/voice_studio.py`
  `models()`), so a new voice model is a row there plus a panel, not a new page. Each card says
  what the model does and how it is priced in words; no dollar or credit figure is on a card.
- **Text to speech** (ElevenLabs v3): script, voice (the 21 names), optional language, a live
  character count, the server's quote (`POST /api/voice/speak/quote`, re-asked as the words, voice
  or language change), and **Make the voice**, which runs at that number
  (`POST /api/voice/speak/run`, 409 if the price moved). Each read lands in a Reads list with a
  player and a download, and is filed in the editor's audio bin (the voiceover's body,
  `src/voiceover.py`, with no project kit). No 50-character floor: that floor belongs to the
  talking photo's 4-second clip.
- **Dub a clip** (ElevenLabs Dubbing): pick a clip from the Library or upload one, then the
  composer's own priced card (`dubbing-step.tsx`) with its consent box and Render. Dubs land in a
  list with a player and a download. `?model=dub&on=gen:<id>` opens it on a clip.

## Files
- API: `src/voice_studio.py` (new), `app/api.py` (`voice_tab` capability, `GET /api/voice`,
  `POST /api/voice/speak/{quote,run}`), `tests/test_voice_studio.py` (14 tests).
- Web: `web/src/app/studio/voice/page.tsx`, `web/src/components/studio/voice-tab.tsx` +
  `voice-tab.css` (prefix `vx-`), `web/src/lib/voice-tab.ts` (pure; `web/tests/voice-tab.test.mjs`,
  6 tests), helpers in `web/src/lib/studio-api.ts`, the rail entry in `shell.tsx`, and a fix in
  `dubbing-step.css` (its three fields now stack label-over-input, in the composer too).

## Checked
- pytest (the new 14 plus the dubbing and capability suites), ruff, `npm run typecheck`, eslint on
  the touched files, `node --test web/tests/*.test.mjs`, `npm run build`.
- The built page was opened in a browser against a stand-in API that serves the real menu and the
  real quote math: both panels, a read landing in the list, the Library picker, the dub card priced,
  and a 390px-wide phone layout.

## Added 2026-10-27: the voice library and dialogue
Mike: "Go ahead with this" (the next voice models). Cloning was left out: it needs his consent and
licensing decision first.
- **Voice library** (MiniMax Speech-02 HD, `fal-ai/minimax/speech-02-hd`, $0.10 per 1,000
  characters): 83 voices in 8 languages (the 45 English system voices plus fal's default
  `Wise_Woman`, and the first ids MiniMax's voice list gives for Spanish, French, Portuguese,
  German, Japanese, Korean and Mandarin), emotion (7), speed 0.5-2.0, pitch -12..12. Language chips,
  then the language's voices as pills. Body: `text`, `voice_setting` {voice_id, speed, pitch?,
  emotion?}, `language_boost` (the voice's language), `output_format: "url"`.
- **Dialogue** (VibeVoice 7B, `fal-ai/vibevoice/7b`, $0.04 per minute of speech in 15-second
  steps): up to 4 speakers, each one of the model's 8 presets, and lines that each name a speaker.
  The studio writes the `Speaker N:` labels (N from 0, `speakers[N]`) and refuses a line that
  carries its own. **The quote is an upper bound**: the words at a slow 10 characters a second,
  rounded up to 15 seconds. The person pays the quote; fal bills the real length, which should be
  less.
- Code: `src/voice_models.py` (tables, checks, bodies, runs, `file_audio` shared filing),
  `src/voice_studio.py` (two more model rows and menu sections), `app/api.py`
  (`POST /api/voice/library/{quote,run}`, `POST /api/voice/dialogue/{quote,run}`), the
  `LibraryPanel` / `DialoguePanel` in `voice-tab.tsx`, and their helpers in `lib/voice-tab.ts`.
- Tests: `tests/test_voice_models.py` (31), `tests/test_voice_studio.py` (14),
  `web/tests/voice-tab.test.mjs` (13). Screenshot-checked against the stand-in API, desktop and phone.

## Not verified (library and dialogue)
- Whether fal's MiniMax endpoint takes every MiniMax platform voice id. fal's page names only
  `Wise_Woman` (the default here). The first live read with another voice settles it; a refused
  id fails before fal bills, and the hold is released.
- VibeVoice's real script limit and pace. If real speech ever comes out slower than 10 characters
  a second, fal would bill a little more than the quote (cents at most at 5,000 characters).

## Added 2026-10-27: cloning your own voice
Mike's rules (2026-10-27): **only the person's own voice**, and they prove it by **reading a
consent line**. Model: MiniMax Voice Clone (`fal-ai/minimax/voice-clone`, "$1.5 per clone, with
preview inputs costing $0.3 per 1000 characters").
- The sample (mp3, wav, m4a, ogg or aac, 10 s to 5 min, uploaded to the editor's bin) must START
  with: *"This is my own voice, and I agree to Phantra making a copy of it."* The run transcribes it
  first (fal Whisper, an operator cost on the `transcribe` stage) and needs 80% of the line's words,
  in order, within its first words (`voice_clone.consent_score`). Not heard: the job fails, no hold
  is taken and nothing is charged. Heard: the clone runs through `effects.run` at the quoted price
  (the clone plus a short preview read), and `effects.run` now returns the model's `result` on an
  audio row so the `custom_voice_id` is kept.
- Kept per account in a new owned table, `voice_clones` (registered in `db.OWNED_TABLES`, created
  in the app lifespan and in tests/test_tenancy.py): the voice id, its name, the sample, what was
  heard and its score, the preview, `last_used_at` and `removed_at`. At most 10 voices per account.
- Clones lead the voice library as **Your voices** (language left to the model, "auto"). A read
  in a clone sets `last_used_at`. MiniMax deletes a voice that is not read in within 7 days, so an
  unused clone shows how many days it has, and drops off the list once its week is up.
- Routes: `POST /api/voice/clone/{quote,run}`, `DELETE /api/voice/clones/{voice_id}` (off the
  list; nothing charged). Panel: the consent steps, the upload, a name, the price, **Clone my
  voice**, and Your voices (preview, Read a script in it, Remove).
- Tests: `tests/test_voice_clone.py` (26), plus the tenancy suite with pgvector.

## Not verified (cloning)
- No live clone has been made. Whether the clone's own preview counts as the "use within 7
  days" is not stated, so the studio counts a clone as unused until its first library read.
- Whisper's exact output shape for `task: transcribe` without chunks is read as `text`, else the
  chunks' text joined. The first live clone confirms it.
- Recording in the browser is not built: people upload a recording (a phone's voice memo works).

## Restyled to match the studio (2026-10-27)
Mike: "design the UI to match that of what we have". The first build sat on an old local
branch (claude/sheet-gpt-image-25) and used its own cards; this pass carries every voice and dub
change onto origin/main (3eaebf43) and redraws the page in the direct generators' layout
(components/studio/direct-generator.tsx, the Image page):
- **Panel (left):** a Model menu (the same `ModelMenu` the Image page uses, now exported) listing
  the five models, the picked model's fields in the generators' field style (mono labels, the
  prompt box as the script, pill rows for languages / emotions / dub targets, a Voice menu,
  sliders), and the yellow pill that spends with its price ("Make the voice · 10 credits",
  "Dub it · 144 credits"), pinned to the panel's foot while a long panel scrolls.
- **Stage (middle):** the Anton headline and script starters when empty ("What you say plays
  here"); a read as its voice's name, a drawn waveform and the player, with chips (voice, length,
  credits) and Reuse script / Open in Library / Download; a dub plays as a video; the clone model's
  empty stage is "Your voices" with each kept voice's preview, its 7-day line, Read a script in it
  and Remove.
- **History (right):** this visit's makes as small waveforms.
- The dub is no longer the chat's card on this page: its clip, language, spoken language, people
  and consent box are panel fields, priced by the same `/api/dubbing/quote`.
- Voice is in main's rail (behind `voice_tab`), between Effects and Assets.
- Merged onto main by three-way merge against the snapshots the work started from; the conflicts
  were all "both sides added beside each other" (main's ad card, watermark, posts, screens).

## Not done
- No live run of any of the five models from this page.
- (Done 2026-10-27) The Library viewer's Dub button opens this page on the clip when `voice_tab` is
  on (`/studio/voice?model=dub&on=gen:<id>`), and the composer's card when it is off.
