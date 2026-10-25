# Kling (`kling3-turbo-pro`, `kling4`): prompt dialect

## Endpoints and inputs

**Kling 3.0 Turbo Pro**
- Endpoints: `fal-ai/kling-video/v3/turbo/pro/text-to-video` and `.../image-to-video`.
- Inputs we send: `prompt`, `image_url` (i2v start frame), `duration`, `aspect_ratio` (t2v).
- The endpoint has no `negative_prompt` and no resolution field. fal's schema says "For best results keep the prompt under 2500 characters" [5].
- `multi_prompt` exists (1–6 shots, total ≤15 s) but is not wired [5].

**Kling 4.0** (a slot; on unless `PHANTRA_KLING_4=0`)
- Endpoints: `kling/v4/text-to-video` and `kling/v4/image-to-video`.
- Inputs we send: `prompt`, `start_image_url` (i2v), `duration`, `resolution`, `aspect_ratio` (t2v).
- The endpoint also takes `end_image_url` and `multi_prompt`; per-shot prompts are capped at 512 characters. Neither is wired [4].
- fal exposes no `negative_prompt`, no audio toggle and no reference images [4].

**Legal values (src/fal.py)**

| Model | Durations | Resolutions | t2v frames |
|---|---|---|---|
| `kling3-turbo-pro` | 3–15 s, sent as a string | 1080p only | 16:9, 9:16, 1:1 |
| `kling4` | 3–30 s, sent as an integer | 720p, 1080p | 16:9, 9:16, 1:1, 21:9 |

**Version match**
- Kling's 4.0 user guide (2026-10-14) covers `kling4` [1].
- For `kling3-turbo-pro` the closest primary source is the Kling VIDEO 3.0 guide [2], which is not Turbo-specific, plus Kling's prompt blog written for 3.0 [3].

## Rules

1. Describe concrete visuals, not abstract labels. Kling 4.0 lists "Premium look" and "Vintage feel" as not recommended; describe the visual details instead. [1]
2. Write a 4.0 prompt in this order [1]:
   - asset roles ("@Image1 defines ___; preserve its ___");
   - overall settings (scene and texture, visual style, camera tone);
   - the sequence of events in timestamped segments ("0–X s", "X–Y s", "Y s–end");
   - audio (dialogue or voiceover, ambience, music, SFX).
3. For 3.0, Kling's framework order is subject, action, scene, camera, lighting, mood: "clear scene direction rather than secret formulas." [3]
4. **Negatives (4.0):** "Only two types of negative instructions are truly necessary: no subtitles and no background music." Otherwise "describe what you want to see rather than what to avoid." [1]
5. The 3.0 guides do not mention negative prompts at all [2][3].
6. **Multi-shot:** 4.0 has "Multi-shot is enabled by default," and the model may split shots automatically. Write timing as "0–5s:" or "00:00–00:03 |" and label shots as "Shot 1 (5s):". You can ask for "hard cuts" and exclude fades or dissolves. [1]
7. In 3.0, shots are numbered in the text ("Shot 1, …. Shot 2, …"), each with its own framing and camera move. Write "one continuous long take without any cuts" when you want no cut. [2]
8. **Dialogue (3.0):** speaker label, delivery in parentheses, colon, then the line. Example: `Mom (softly, in a surprised tone): Wow, I didn't expect this plot at all.` [2]
9. **Dialogue (4.0):** "write the dialogue in that language inside quotation marks". For a specific voice, "describe the speaker's age, vocal tone, speaking speed, and emotion." [1]
10. Spoken languages [1][2]:
    - 3.0: Chinese, English, Japanese, Korean, Spanish. Other languages are translated into English.
    - 4.0 adds Portuguese, German, French and Hindi, with American, British and Indian accents.
11. Give every speaker a clear label and keep each speaker's name, line and delivery together. 3.0 handles three or more characters better than 2.6. [2][3]
12. Write camera moves in plain language: push-in, pull-out, pan, tracking, orbit; "The camera slowly pans to the right". Time a beat with "At the 4th second, …". [1][2]
13. Pair a non-photoreal style with an explicit exclusion of photorealism, so the styles do not mix. [1]
14. **References (4.0):**
    - Assets are numbered @Image1, @Video1, @Element1 in upload order.
    - Always state each asset's role: listing IDs alone is less predictable.
    - First frame: "Use @Image1 as the first frame, then describe what happens next."
    - First and last frame: "Use @Image1 as the first frame and @Image2 as the last frame, then describe the [process] in between." [1]
15. Text already in an input image (signs, logos) is preserved, and the camera can be told to hold on it ("The camera remains fixed on the word 'KLING.'"). [2]
16. Prompt length: up to 8,000 tokens on 4.0 [1]. On the fal 3.0 Turbo endpoint, stay under 2,500 characters [5].

## NOT FOUND in primary sources

- Whether the @Image tokens mean anything when the image arrives through fal's `start_image_url` field rather than Kling's own asset slots.
- A recommended prompt length (only maximums are given).
- Turbo-specific prompting differences from Kling 3.0.

## Conflicts with our pipeline

- **Avoid list.** `scenes_prompt.txt` part 5 ("AVOID: no plastic AI sheen, no glossy CGI…, no cartoon reactions…") and `enhance_system.txt` ("Every negative constraint … stays, in full, as an explicit negative") go beyond the two negatives Kling 4.0 calls necessary. Kling says describe what you want instead [1]. "No background music." (scenes_prompt part 4) is one of the two Kling endorses.
- **Cut words.** Kling 4.0 has multi-shot on by default [1]. `shot_timeline_prompt.txt` puts "hard cut to" / "reverse on" into a single shot's prompt, and Kling documents cut words as triggers for in-clip shots [1][2]. A window rendered as one clip can come back with a cut in it.
- **Order.** `enhance_system.txt` puts "hard constraints and negatives first". Kling leads with asset roles and the scene, and puts audio last [1].

## Sources (all accessed 2026-10-24)

1. Kling AI, "Kling 4.0 User Guide" (2026-10-14). https://kling.ai/quickstart/kling-4-model-user-guide
2. Kling AI, "Kling VIDEO 3.0 Model User Guide". https://kling.ai/quickstart/klingai-video-3-model-user-guide
3. Kling AI blog, "Kling AI Prompt Guide" (2026-08-07, written for Kling VIDEO 3.0). https://kling.ai/blog/kling-ai-prompt-guide
4. fal.ai queue OpenAPI schemas, `kling/v4/text-to-video` and `kling/v4/image-to-video`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=kling/v4/image-to-video
5. fal.ai queue OpenAPI schemas, Kling v3 turbo pro. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/kling-video/v3/turbo/pro/image-to-video
