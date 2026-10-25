# Seedance (`seedance2-fast`, `seedance2`, `seedance2.5`): prompt dialect

- **Endpoints we use:**
  - Seedance 2.0 Fast: `bytedance/seedance-2.0/fast/{text,image}-to-video`.
  - Seedance 2.0: `bytedance/seedance-2.0/{text,image}-to-video`.
  - Seedance 2.5: `bytedance/seedance-2.5/{text,image}-to-video`.
- **Inputs we send:** `prompt`, `image_url` (i2v start frame), `duration` (a string), `resolution`, `aspect_ratio` (t2v).
- **Accepted by the endpoints, not wired:**
  - `end_image_url`, `generate_audio` (default true; fal says the cost is the same either way).
  - 2.5 only: `draft` (a 480p preview that can be finished at 1080p).
  - The reference-to-video endpoints [5].
- **Legal values (src/fal.py):**

  | Model | Durations | Resolutions |
  |---|---|---|
  | `seedance2-fast` | 4–15 s | 480p, 720p |
  | `seedance2` | 4–15 s | 480p, 720p, 1080p |
  | `seedance2.5` | 4–30 s | 480p, 720p, 1080p |

  Text-to-video frames for all three: 16:9, 9:16, 1:1, 4:3, 3:4, 21:9.
- **Version match:** BytePlus publishes a separate guide for each version: 2.0 (covers 2.0 and 2.0 Fast) [1], and 2.5 (updated 2026-10-16) [2]. Dreamina's 2.5 page is ByteDance's own consumer product (CapCut), cited as secondary-official [3].

## Rules

1. **2.0 formula:** precise subject + action details + scene/environment + lighting & colour tone + camera movement + visual style + image quality + constraints. Lock "who" is "doing what" first; style, quality and constraints come last. [1]
2. **2.5 one-sentence summary:** Subject + Location + Event + Genre/Style + Camera movement. Then write the detailed plot as a shot sequence or a timeline. Then add the elements that must stay constant throughout. [2]
3. **Seedance 2.0 does not follow timestamps.** "Seedance 2.0 does not respond to timestamps and only responds to shot numbers, while Seedance 2.5 supports integer-second timestamps." [2]
4. On 2.0, organise the clip as `Shot 1 / Shot 2 / Shot 3` and do not set per-shot durations. "The model's support for precise timing (such as 0–3 seconds) is unstable." [1]
5. On 2.5, use 1-second units ("0-3 seconds…3-7 seconds…" or "[1s-4s]…") with no gaps in the timeline.
   - Too little plot in a span lets the model improvise.
   - Too much causes "excessive cuts" or dropped plot.
   - Don't time high-frequency actions. [2]
6. Inside each 2.0 shot, write in this order: camera move or transition → subject action and expression → position or space → audio for the shot. [1]
7. Use **one camera movement per shot**: "Do not require push, pull, pan, and move at the same time, as this will increase image instability." [1]
8. On 2.0, prefer slow, gentle, continuous small movements. Avoid "sprinting, big jumps, and violent rolls". Quantify range, speed and force ("slowly raise a hand"). [1]
9. Show emotion through physical detail, never abstract words ("very sad" → "lowering the head, shoulders trembling slightly…"). [1]
10. On 2.5, strong emotional words can make pupils glow. Use neutral words ("amazed", not "fanatical"), and if needed add "normal human eyes; no glowing eyes" as the top negative. [2]
11. **Negatives:** "Use positive descriptions whenever possible." Negative constraints are supported for subtitles and audio: "No subtitles", "No BGM; generate only environmental sounds and action sounds", "No audio". [2]
12. 2.0 lists constraint templates for subtitles, logos and watermarks [1].
13. Dreamina: keep negatives "short, concrete, and grouped at the end". Don't write a long generic blacklist. [3]
14. **Dialogue:** the BytePlus examples write the speaker, then `says:`, then the line in braces: `Gao Yan says: {…}`. Voiceover is written as `(V.O.) says: {…}`. [1][2]
15. Dreamina writes the line in quotes with a speaker cue [3]. 2.5 generates speech in "more than 10 languages" [2].
16. Camera terms can be written directly: shot sizes; push in, pull out, pan, track, follow, orbit, tilt; handheld; one-shot/long take; dolly zoom; FPV.
    - For niche terms, write the term plus a plain description, for example "Rack focus: the focus shifts smoothly…".
    - For transitions, give both the timing and the method. [2]
17. **References:** number assets by upload order (Image 1 / Video 1 / Audio 1) and bind each one in the text with its purpose ("The knight in Image 1"). @-binding also works: "girl @Image 1". [1][2]
18. When a reference is accurate enough, just reference it; "avoid repeatedly describing the scene in detail". [2]
19. Upload subject references in their order of first appearance. A mismatch can swap characters. [2]
20. **First/last frame:** set the role via parameter. This locks the aspect ratio to the first image. [2]
21. Avoid conflicting instructions in one beat (a locked tripod plus aggressive handheld). Don't ask for detailed typography during motion. [3]

## NOT FOUND in primary sources

- A word-count sweet spot. Dreamina only says "the shortest prompt that fully specifies the production" [3].
- Whether fal's plain `prompt` field gives Seedance 2.5 the same timestamp behaviour as BytePlus' API. This is assumed, not documented.

## Conflicts with our pipeline

- **Time markers.** `scenes_prompt.txt` writes timed windows "(4-7s)", and `enhance_system.txt` keeps them ("the markers are how the prompt is split"). Any prompt that reaches Seedance 2.0 / 2.0 Fast with these markers still inside, such as a one-window scene or the direct page, asks 2.0 for something it "does not respond to"; BytePlus says to use `Shot N` instead [1][2].
- **Avoid list.** `scenes_prompt.txt` part 5's list ("no plastic AI sheen, no glossy CGI…, no cartoon reactions…") goes beyond what BytePlus documents negatives for (subtitles and audio) [2].
- **Cut words.** `shot_timeline_prompt.txt` puts "hard cut to" in a one-shot clip. Seedance treats stated transitions and too much plot per span as cut triggers [2].
- **Order.** `enhance_system.txt` puts "hard constraints and negatives first". Seedance's formula puts constraints last [1][3].

## Sources (all accessed 2026-10-24)

1. BytePlus ModelArk, "Dreamina Seedance 2.0 series prompt guide". https://docs.byteplus.com/en/docs/modelark/seedance-2-0-prompt-guide
2. BytePlus ModelArk, "Dreamina Seedance 2.5 prompt guide" (updated 2026-10-16). https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide
3. Dreamina by CapCut (ByteDance), "Seedance 2.5 Prompts Guide". https://dreamina.capcut.com/seedance/seedance-2-5-prompt
4. BytePlus ModelArk, Seedance 2.0 tutorial (model IDs, modes). https://docs.byteplus.com/en/docs/ModelArk/2291680
5. fal.ai queue OpenAPI schemas, `bytedance/seedance-2.0/image-to-video`, `bytedance/seedance-2.5/text-to-video`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=bytedance/seedance-2.5/image-to-video
