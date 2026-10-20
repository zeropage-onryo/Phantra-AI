# OmniHuman v2 on Phantra: talking-photo feature + landing page (plan, 2026-10-20)

Status: **approved by Mike 2026-10-20**; built the same day (see "As built" at the end).

## The model (read 2026-10-20 at fal.ai/models/bytedance/omnihuman/v2 and /api)
- Endpoint: `bytedance/omnihuman/v2`. Turns a photo of a person plus an audio clip into a talking or singing video. Motion and expression follow the audio.
- Inputs:
  - `image_url` (required): jpeg/png/webp/bmp/tiff/gif/heic, up to 30 MB, 300–6000 px, aspect ratio 0.4–2.5.
  - `audio_url` (required): wav/mp3, up to 15 MB, **4–300 s**.
  - `prompt` (optional): scene, movement and camera.
- Output: `video` (File) and `duration` (float). Billing is on `duration`.
- Price: $0.105/s, from the model page (the API page doesn't list it).

## Text-to-speech (read 2026-10-20 on fal model pages)
| Endpoint | Price | Notes |
|---|---|---|
| `fal-ai/elevenlabs/tts/eleven-v3` | $0.10 / 1k chars | **Default.** Fields: `text` (supports audio tags like [laughs] and [whispers]), `voice` (default Rachel), `stability`, `similarity_boost`, `speed`, `language_code`, `apply_text_normalization`, `seed`, `timestamps`, `output_format` (default mp3_44100_128). 70+ languages. |
| `fal-ai/elevenlabs/tts/turbo-v2.5` | $0.05 / 1k chars | Cheap or fast fallback. |
| `fal-ai/gemini-3.1-flash-tts` | $0.05 / 1k chars | Voice default Kore. Possible alternative. |
| `fal-ai/minimax/speech-2.8-hd` | $0.10 / 1k chars | Not chosen. |
- Max text length isn't stated on the pages. The code agent checks the OpenAPI schema.
- TTS costs very little next to the video: 30 s of speech is about 450 chars, roughly $0.05.

## Decisions (Mike, 2026-10-20)
- **Audio cap per plan:** 30 / 60 / 120 s for Starter / Creator / Studio. Worst-case clip: $3.15 / $6.30 / $12.60.
- **v1 audio:** both upload and text-to-speech.
- **Page keyword:** "photo to talking video". Picked without Semrush (subscription expired); refine from Search Console after launch.
- **Credits:** use the existing `pricing.credits_for(usd_micros(...))` conversion. The code agent confirms it carries the standard markup, and adds no new rule.

## Flow
1. The user picks a photo: their own element or upload, with a consent checkbox.
2. Audio comes from one of two sources:
   - **Upload:** wav or mp3. Measure the duration.
   - **Script:** text plus a voice. Run a **voice preview** with TTS (about 1 credit, quoted and approved like any spend). The user hears it, and the exact duration is now known.
3. Check the audio is between 4 s and the plan cap. Pad audio under 4 s with silence, or refuse it: the code agent picks one and documents it.
4. Quote = `ceil(audio_seconds) × credits_per_second`. The user approves, it renders, and the clip lands on the Assets wall.
- MCP: an `effects` row plus a `talking_photo` tool, both quote → approve. The TTS preview is its own quoted step.

## Stack (existing, no new services)
- `src/fal.py`: rows for omnihuman-v2 and eleven-v3, each with id, price, source URL and date.
- `src/effects.py`: rows for `omnihuman-v2` (photo + audio -> clip) and `tts-preview` (text + voice -> audio). Same approval_gate, credit hold, settle and generations path as the other effects.
- `src/mcp_server.py` (studio surface), studio UI, Supabase, R2.
- Web: Next.js on Vercel. Entry `web/src/landing-pages/entries/photo-to-talking-video.ts` registered in `pages.ts`, built with the phantra-ai-landing-page skill.

## Where competitors put talking-photo pages (checked 2026-10-20)
- **Feature or tool page** (the main pattern):
  - invideo.io/make/talking-photo and invideo.io/tools/talking-avatar
  - heygen.com/talking-photo and heygen.com/tool/face-talking-tool
  - creatify.ai/features/talking-photo
  - magichour.ai/products/talking-photo
  - capcut.com/resource/talking-photo-ai
- **Model page:**
  - hedra.com/models/video/kling/ai-avatar-v2-pro and hedra.com/models/video/hedra/omnia
  - dreamina.capcut.com/resource/omnihuman-ai
  - fal.ai/models/bytedance/omnihuman/v2 (developer page)
- **Blog guide:**
  - higgsfield.ai/blog (Lipsync Studio post; How to Create a Realistic AI Talking Avatar)
  - heygen.com/blog/create-ai-avatar-from-photo
  - info.invideo.io/blog/ai-avatar-video-creation-from-single-photo
- Bigger sites run all three: a feature page for the job ("talking photo"), a model page for the model name, and a blog guide linking to the feature page.
- **Recommendation for Phantra:**
  - v1: the feature page `photo-to-talking-video`. List it under a Tools/Features menu, not Models.
  - Week 2: a model page `omnihuman` that links to the feature page.
  - Later: one how-to guide.

## Live-site placement (checked on phantra.ai 2026-10-20)
- Use-case pages live at `phantra.ai/make/<slug>`, from the sitemap. Model pages live at `phantra.ai/models/<model>-video-generator`.
- **The new page is `phantra.ai/make/photo-to-talking-video`.**
- Model page later: `phantra.ai/models/omnihuman-video-generator`.
- Links to add:
  - Product menu, "Use cases" group: right after Image to Video.
  - Footer: Tools column.
  - "More to make" tiles: Image to Video and Consistent Character Video link to it.
- Mockup: the live /make/image-to-video page, re-rendered with the talking-photo copy and grey placeholders where renders go. Shared with Mike 2026-10-20.
- Mockup copy carried into the entry:
  - H1 "Photo to Talking Video"; CTA "Make a photo talk".
  - Sections: "Type it, or upload it" / "The photo speaks" / "Then finish the clip".
  - 9 feature tiles, 3 steps.
  - "The models behind it": OmniHuman v2, ElevenLabs v3, any video model.
  - FAQ: what is it; how; typed scripts; languages and voices; someone else's photo; which model; length; commercial use.
- Still open: credit numbers on the page (come from `credits_for`), FAQ answers, and real example renders (after Mike's OK).

## Build (next session with repo access)
- **Agent B, code** (worktree, branch `claude/omnihuman-talking-photo`):
  - the table rows, validation (image px, ratio and size; audio length; plan cap), the TTS preview, the quote, and the MCP tool;
  - tests with a mocked fal client, then a PR.
  - No live render.
- **Agent C, page:**
  - CTA (150 trial credits), spec table, credits per 10 s, FAQ with JSON-LD, Vesper pitch, consent line;
  - a Vercel preview.
- Claude checks the page facts against this doc.
- **Mike's gates:** approve the first real render (one 10 s clip, about $1.05 plus TTS), the preview, and the merge.

## As built (2026-10-20, branch `claude/omnihuman-v2-talking-photo-bcf1f4`)

Built in one session on the Mac (code and page together), not the two agents above.

- **`src/talking_photo.py`**: the dated rows (OmniHuman v2 and ElevenLabs v3, re-read
  that day off each OpenAPI schema and the model page's `endpointBilling`: $0.105/s
  billed on `duration`; $0.10 / 1k characters), the plan caps, and every check.
  The rows live here, **not** in `fal.py` or `effects.EFFECTS` as the plan said: an
  `EFFECTS` row takes one kind of source and `apply_effect` runs whatever the menu lists,
  so a row there would be listed and then refused. It follows `clip_edit`: own table,
  `effects.run(row=, endpoint_body=)` for the cap, hold, generations row and settle.
- **`effects.run`** takes `row["output"] == "audio"`: downloaded, recorded and settled
  as before, returned by path with no Assets tile.
- **Two studio tools** (`STUDIO_TOOLS`, Claude Desktop; not the listed servers):
  `voice_preview(script, voice, language)` -> an `asset:<id>` in the editor's media bin
  with its measured `seconds`; `talking_photo(photo, audio, prompt, consent)` -> a
  `gen:<id>` clip. Both quote -> yes -> run through `approval_gate`. `import_file`
  now takes .mp3 / .wav too.
- **Decisions the plan left to the build:**
  - Under 4 s is **refused**, not padded. A preview script under 50 characters is
    refused before it is paid for (speech runs ~14-16 chars/s), so a preview cannot
    come back too short to use. The measured length still decides at the clip.
  - The quote is `ceil(seconds) * $0.105` through `ledger.charge_credits`
    (= `pricing.credits_for(usd_micros(...))`, the standard 2.4x markup and the
    10-credit floor). 10 s = 252 credits. No new rule.
  - An account with no plan (the trial) gets Starter's 30 s cap.
  - `consent` is a required `true`, signed into the quote token.
  - Voices are the 21 names the schema's examples list (Rachel default); anything else
    is refused. The v3 schema has `stability`, `language_code`,
    `apply_text_normalization`, `timestamps`, but NOT `speed` / `similarity_boost`
    (the plan's list was from another ElevenLabs endpoint); only voice and language are
    exposed. `text` maxLength is 5000.
  - A voice preview is 10 credits at the floor, not "about 1 credit": 450 characters
    (30 s) is $0.045 -> 11 credits.
- **Prices on the site** come from `pricing.json` `actions.talking_photo`
  (`pricing.talking_photo_catalog`, regenerated by `python -m src.pricing export`).
- **The page**: `/make/photo-to-talking-video`, accent SKY (new), center hero, no
  signature, NO_WALL until renders exist, features grid, its own pricing table. In the
  Product menu after Image to Video, in the footer's Tools column, and in the related
  links of Image to Video and Consistent Character Video. The trial line reads the
  catalog's trial (100 credits today; the plan said 150).
- **Not built: a studio (web) door.** The web composer has no talking-photo card, so
  today the feature is reachable only from Claude Desktop's studio connector. The page's
  CTA opens the composer, so the page should not go live before that door exists
  (see BACKLOG / the follow-up session).
- No live render was made. Mike's gates stand: the first real render (one 10 s clip,
  ~$1.05 + TTS), the preview, the merge.
