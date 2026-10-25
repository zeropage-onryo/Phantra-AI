# Wan 3.0 (`wan3`): prompt dialect

- **Endpoints we use:** `alibaba/wan-3.0/text-to-video`, `alibaba/wan-3.0/image-to-video` (start frame in `start_image_url`).
- **Inputs we send:** `prompt` (t2v max 20,000 characters), `start_image_url`, `duration` (an integer), `resolution`, `aspect_ratio` (t2v) [4].
- **Accepted by the endpoint, not wired:** `end_image_url`, `audio` (default true), `enable_thinking` (default false), and `enable_prompt_expansion` (default true).
- **Prompt expansion is on.** fal: "Disabling it can save roughly 20-60 seconds of latency but is likely to degrade generation quality." So **our prompt is rewritten by Wan's extender before it renders** [4].
- **Legal values (src/fal.py):** 2–10 s; 480p, 720p or 1080p (the endpoint defaults to 1080p, ours to 720p); t2v frames 16:9, 9:16, 1:1, 4:3, 3:4. Alibaba's own API allows 2–30 s [2].
- **Version match:** Alibaba's wan3.0 prompt guide (updated 2026-10-16) [1]. The open Wan 2.2 extender prompt shows an older model's rewrite format [3].

## Rules

1. Follow the full formula and skip any section you don't need:
   `[Overall description] + [Reference citation: Image N / Video N / Audio N] + [Shot N (start-end seconds): Subject + Scene + Motion + Aesthetic control] + [Dialogue: xx says: "xxxx"] + [Sound effect / BGM] + [Style / Mood] + [Negative prompt list]` [1]
2. "A single sentence is enough", but "the more complete and precise the description, the closer the result". [1]
3. **Multi-shot:** write an overall description, then the shot number, timestamp and content: `Shot 1 [0-3s] …` or `Shot 1 (00:00-00:03): …`.
   - Shots connect end-to-end, "2–5 seconds per segment".
   - Pick one bracket style and keep it.
   - Alibaba's overview gives 4–6 s per shot [2]. [1]
4. **Single take:** write "Generate single shot" or "One continuous shot" on the first line. [1]
5. **Transitions:** write "hard cut" or "dissolve" at the end of a segment, or start the next segment with "seamlessly continue from the last frame of the previous segment". [1]
6. **Camera:** use plain language (push in, pull out, orbit, handheld follow). A still camera is "Fixed shot, camera static, position unchanged". Lens and depth go in as "85mm telephoto, shallow depth of field". [1]
7. Avoid high-frequency actions the model can't control ("shaking head 3 times per second"). [1]
8. **Dialogue:** character + speaking verb + colon + quoted line: `she whispers: "content"`. With several speakers, write one line per speaker. Voiceover is `Voiceover: "…"`. Add `Lip sync` for lip sync. [1]
9. Write "No dialogue" explicitly when you want none. Otherwise "the model decides on its own whether to include dialogue." [1]
10. **Sound:** when the action, material and weather are clearly described, matching sound effects are filled in automatically. Specific SFX go in standalone sentences, optionally timed. [1]
11. **BGM:** write nothing (the model chooses), specify it ("cello enters very softly"), or turn it off ("No BGM, generate only ambient and action sounds" / "No background music."). [1]
12. Style, colour tone and mood can go at the beginning or the end. [1]
13. **Negative prompt list (in the prompt):** "Write only what you do not want to appear … Do not pad the list or repeat content already stated in the positive prompt."
    - Example: "No face distortion, No subtitles, No game-CG look, No slow motion".
    - Wan supports a negative list written into the prompt, unlike Veo. [1]
14. **References:** Image N, Video N and Audio N are numbered by upload order, each type counted separately. State each one's purpose, and what *not* to take from it ("Only reference the color tone and lighting of Image 2, not the characters"). [1]
15. The Wan 2.2 extender gives the older model's preferences [3]:
    - put any style first;
    - target 60–200 characters;
    - no literary mood prose;
    - describe how each motion unfolds;
    - default to a medium or wide shot.

## NOT FOUND in primary sources

- How `enable_prompt_expansion` treats an already long, structured prompt.
- Whether the in-prompt negative list survives expansion.

## Conflicts with our pipeline

- **Little conflict on negatives.** Wan explicitly supports an in-prompt negative list [1], so `scenes_prompt.txt` part 5 (AVOID) fits Wan's format, as long as it is not padded with items already stated positively [1].
- **Cut words.** Wan treats "hard cut" as a between-segment transition [1]. `shot_timeline_prompt.txt` puts "hard cut to" inside a one-window clip, which can produce a cut inside the clip. Wan's own fix is "Generate single shot" on the first line [1].
- **Expansion.** Expansion is left on (fal's default) [4], so Wan rewrites what the studio writes. That works against `enhance_system.txt`'s word-for-word locks ("must survive word for word").

## Sources (all accessed 2026-10-24)

1. Alibaba Cloud Model Studio, "wan3.0 Video Generation Prompt Guide" (updated 2026-10-16). https://www.alibabacloud.com/help/en/model-studio/wan3-video-generation-prompt-guide
2. Alibaba Cloud Model Studio, "wan3.0 video generation guide". https://www.alibabacloud.com/help/en/model-studio/wan3-video-generation-guide
3. Wan-Video, Wan 2.2 prompt-extender system prompts (`wan/utils/system_prompt.py`, older model). https://github.com/Wan-Video/Wan2.2/blob/main/wan/utils/system_prompt.py
4. fal.ai queue OpenAPI schemas, `alibaba/wan-3.0/text-to-video` and `/image-to-video`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=alibaba/wan-3.0/image-to-video
