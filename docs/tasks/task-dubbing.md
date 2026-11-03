# Dubbing: a clip in another language (backend built 2026-10-26)

Status: **backend, studio card and brain proposal built and tested; not yet run against fal; the card has not been looked at in a browser.**
Mike asked for "the code first, then we wire in the UI" (2026-10-26), after a gap check
of the studio's voice against Higgsfield (`dubbing`, `voice_change`, `create_voice`,
`generate_audio`) and Runway (`generate_speech`, `search_voices`, `localize_ad`). The
studio had one voice model (ElevenLabs v3, 21 fixed names) and nothing that re-speaks an
existing clip. Dubbing was first in the order proposed: it is the one both competitors
sell and it is one small spend.

## The model (read 2026-10-26 at fal.ai/models/fal-ai/elevenlabs/dubbing)
- Endpoint `fal-ai/elevenlabs/dubbing`. `video_url` or `audio_url` (video wins if both);
  `target_lang` required (ISO 639-1); `source_lang` optional (auto-detected);
  `num_speakers` 1-50 optional (auto-detected); `highest_resolution` default true.
- Output: `video` (when a video went in), `audio`, `target_lang`.
- Price: **$0.60 per minute of media, rounded up to the next whole minute.**
- The page lists **no** file-size, length or format limits, and names only six target
  languages as examples (es, fr, de, ja, pt, zh). It does not say whether the lips are
  re-synced to the new speech.

## What was built
- `src/dubbing.py`: the dated row, the checks, `request()` (checks + prices, spends
  nothing), `run()` (through `effects.run`: key, cap, credit hold before the submit,
  generations row, settle, the Library). Video in, video out. Not a row of
  `effects.EFFECTS`, for the reason `talking_photo` and `clip_edit` are not: `apply_effect`
  would run it in one call with no consent.
- Connector: `dub_clip` on the **studio** surface only (`STUDIO_TOOLS`), quote -> yes ->
  run through `approval_gate`; title, description, hints, `SPEND_PROVIDERS` and
  `mcp_shapes.SPEND_TOOLS` carry it. Never on the listed servers (ChatGPT, Claude).
- Studio routes: `GET /api/dubbing` (menu), `POST /api/dubbing/quote`,
  `POST /api/dubbing/run` (a job; `expect_credits` holds it to the price the card showed,
  409 otherwise), the same shape as `/api/talking-photo/*`.
- Tests: `tests/test_dubbing.py` (table, price, checks, the tool, and a real-ledger
  conversation with a real clip through ffprobe) and `tests/test_dubbing_studio.py`
  (the routes). Neither touches the network.

## Decisions made while building (not Mike's; change them freely)
1. **Consent is required**, same family as the talking photo's: the dub re-speaks the
   people on the clip in their own voices. Never pre-ticked, never set for the person.
2. **Six languages, no more**, because those are the only ones the page names. A language
   off `dubbing.LANGUAGES` is refused before a quote. Extending it is one line once a live
   run proves it. English as a *target* is not on the list and should be the first probe.
3. **Five minutes at most** (`MAX_SECONDS = 300`, $3.00 of fal, 720 credits). The page states
   no limit; this is the studio's own guard.
4. **A clip with no sound track is refused**, and so is one whose sound cannot be probed
   (ffprobe). Speech itself is not detected: a clip with music and no talking is accepted.
5. **Priced like fal bills it**: whole minutes, rounded up, never under one. A 9-second
   clip costs a minute (144 credits at the standard markup).

## Not verified
- No live call has been made. The wire body is read off the page, not off a run.
- Whether `highest_resolution: true` changes the output size or the price.
- Whether the dubbed video keeps the original picture untouched, and whether the lips move
  to the new speech. If they do not, a lip-sync pass (`fal-ai/sync-lipsync/v3`, $8/min, or
  `fal-ai/latentsync`, $0.20 per clip up to 40s) would be a second, optional spend.
- Public pricing page: `pricing.public_catalog()` has no dubbing entry yet.

## As built: the studio card (2026-10-26)
- `web/src/lib/dubbing.ts` (pure, import-free; `web/tests/dubbing.test.mjs`, 8 tests): `beginDub`,
  `clipChoices`, `dubMissing`, `dubRequest`, `dubPriceKey`, `speakerCount`. The card state is `Turn.dub`.
- `web/src/components/studio/dubbing-step.tsx` + its own `dubbing-step.css` (prefix `db-`): clip
  picker (the thread's clips only, by id), language select (the menu's six), optional spoken
  language and speaker count, the consent box (never pre-ticked), the server's price
  (`POST /api/dubbing/quote`, re-asked when the clip, language, spoken language or speakers change;
  not when consent changes), Render at `expect_credits`. Runs as an effect-shaped job, so a reload
  resumes it through `finishEffect`; the dubbed clip lands in the thread and the Library as `gen:<id>`.
- Wiring: `/dub` slash command (`composer.ts`), `startDub / patchDub / approveDub` in `page.tsx`,
  `getDubMenu / quoteDub / runDub` in `studio-api.ts`, `Turn.dub` in `assistant.ts`, the render in
  `turns.tsx`, and `assistant-thread.tsx` keeps a dub card when a thread is trimmed.
- Brain: `dub_clip` in `src/guide_tools.py` (`check_dub`: `on` held to a clip on the turn's list,
  `target_language` held to the six; `dub_line`), offered to the composer only, never run by the server,
  listed in `prompts/creative_guide_effects.txt`. Tests in `tests/test_dubbing_studio.py`.
- Checked in a clean copy: `npm run typecheck`, `npm run build`, eslint on the touched files (no new
  warnings), `node --test web/tests/*.test.mjs` (the only failures need `public/` and are environmental).

## Library entry (2026-10-26)
- The asset viewer shows a **Dub** button beside Effects on a clip that has a render id. It links to
  `/studio?dub=gen:<id>`; `page.tsx` opens the dub card on that clip once the thread has loaded and
  removes the param. Arriving spends nothing.

## Not done in the UI
- Not looked at in a browser (layout of the `db-row` fields and the viewer's two-button row are unseen).
- Public pricing catalog still has no dubbing entry.

## The rest of the voice gap (see the 2026-10-26 comparison)
Voice library (MiniMax Speech-02 HD, 300+ presets, same $0.10 per 1,000 characters as the
current model), cloning (`fal-ai/minimax/voice-clone`, $1.50 per clone; Qwen3-TTS;
Chatterbox) and multi-speaker dialogue (`fal-ai/vibevoice/7b`) are not started. Cloning
needs a consent and licensing decision from Mike first.
