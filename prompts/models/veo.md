# Veo 3.1 (`veo3.1`): prompt dialect

- **Endpoints we use:** `fal-ai/veo3.1` (text-to-video), `fal-ai/veo3.1/image-to-video` (start frame).
- **Inputs we send:** `prompt`, `image_url` (i2v start frame), `duration`, `resolution`, `aspect_ratio` (t2v only), and `negative_prompt`. Our whitelist allows `negative_prompt`, but it is filled only when `PHANTRA_PROMPT_DIALECTS=1` (`src/prompts_for.py`).
- **The endpoint also accepts, not wired:** `generate_audio` (default true, the rate we price), `auto_fix` (default true: fal rewrites a prompt that fails policy or validation), and `seed`. The prompt holds up to 20,000 characters [6].
- **Legal values (src/fal.py):** duration 4, 6 or 8 s, sent as `"4s"`/`"6s"`/`"8s"`; 720p or 1080p (4k exists, not offered); t2v frames 16:9 and 9:16.
- **Inputs not on our fal endpoints:** end frame and reference images ("ingredients"). Google documents both for Veo 3.1 [1].
- **Version match:** Google's guides are written for Veo 3.1 [1][2].

## Rules

1. Order the prompt as **[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]**. Google calls cinematography "the most powerful tool for conveying tone and emotion." [1]
2. Open with the kind of video you want: "Start your prompt by defining the sort of video you want to create." [3]
3. Name camera movement and framing in standard film terms. Movement: dolly, tracking, crane, aerial, slow pan, POV. Framing: wide, close-up, extreme close-up, low angle, two-shot. Lens: shallow depth of field, wide-angle, macro, deep focus. [1][2]
4. Keep zoom and dolly apart: a zoom "is different from a dolly, as the camera itself doesn't move." Google also says "Some advanced camera angles are not officially supported." [2]
5. Write audio in separate sentences, and say when you want it ("Clearly specify if you want audio"). [2]
6. Audio syntax:
   - Put dialogue in quotation marks: `A woman says, "We have to leave now."`
   - Prefix sound effects with `SFX:`: `SFX: thunder cracks in the distance`.
   - Prefix background sound with `Ambient noise:`. [1]
7. Delivery cues go in the scene text, for example "says in a weary voice". The timestamp example also uses an `Emotion:` line. [1]
8. Keep spoken lines short: "write conversational lines that fit within an 8-second reading window." This is fal's tip, not Google's. [4]
9. State the soundtrack outright: "don't rely on Veo to infer it; state whether you want ambient sound, music, dialogue, or silence." (fal) [4]
10. **Negatives:** "using instructive language or words such as 'no' or 'don't'" is not recommended. Describe what you don't want to see, as comma-separated terms in the negative prompt (example: "wall, frame"). [2]
11. In the main prompt, write an exclusion as a positive scene: "a desolate landscape with no buildings or roads" instead of "no man-made structures". [1]
12. **Multi-shot in one clip:** use `[00:00-00:02]`-style timestamp lines, each carrying its own shot, SFX and Emotion cues, inside the 8 s clip. [1]
13. **Image-to-video:** "The prompt should describe how to animate the input image": action, style, and optionally camera motion and ambiance. (fal) [5]
14. Supply a start image at 720p or higher, in 16:9 or 9:16. Other shapes are cropped. (fal) [5]
15. For long or complex action, "Try mapping out exact play-by-plays", and give a narrative a beginning, middle and end. [3]
16. Long and short prompts both work. Google sets no length sweet spot; its examples are one dense paragraph per 8 s clip. [3][2]
17. Across a sequence of clips, repeat the same character description and the same lighting in every prompt. (fal) [4]
18. **References (ingredients):** say what each image is for: "Using the provided images for the detective, the woman, and the office setting, create…". Our endpoints do not send references. [1]
19. **First and last frame:** describe the transition and the audio between the two images. Not wired. [1]

## NOT FOUND in primary sources

- A word or character count sweet spot. Google only says "long and short" prompts both work.
- Whether `negative_prompt` affects the generated audio.
- How Veo treats a "No background music." sentence. The negative-wording rule (#10) suggests putting "background music" in the negative prompt instead, but Google does not document this.

## Conflicts with our pipeline

- `scenes_prompt.txt` part 5 writes the avoid list into the positive prompt as "no" phrases: "AVOID: no plastic AI sheen, no glossy CGI…". `enhance_system.txt` insists "Every negative constraint … stays, in full, as an explicit negative." Google advises against "no"/"don't" in prompts and says to describe exclusions [1][2]. With dialects off, Veo receives these lines as written.
- `scenes_prompt.txt` part 4 has every scene's sound block "begin 'No background music.'" That is an instructive negative, the same issue as above [2].
- `enhance_system.txt` asks for "hard constraints and negatives first … motion, camera and blocking last". Google's formula leads with cinematography, then subject and action [1].
- `shot_timeline_prompt.txt` keeps voiceover lines "If it cannot be said in the window's seconds, keep it anyway". fal advises dialogue that fits an 8 s reading window [4].
- `shot_timeline_prompt.txt` asks each shot to say "hard cut to" / "reverse on" relative to the previous one. On Veo each window is its own clip. Google's documented multi-shot syntax is the in-clip timestamp form [1], so a cut word in a single-shot prompt may produce a cut inside the clip. This is an inference; Google does not say it.

## Sources (all accessed 2026-10-24)

1. Google Cloud blog, "The ultimate prompting guide for Veo 3.1" (2025-10-15). https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
2. Google Cloud, Vertex AI "Video generation prompt guide" (Veo 3.1). https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide
3. Google DeepMind, "Veo prompt guide". https://deepmind.google/models/veo/prompt-guide/
4. fal.ai, Veo 3.1 model page (prompting tips). https://fal.ai/models/fal-ai/veo3.1
5. fal.ai, Veo 3.1 image-to-video API page. https://fal.ai/models/fal-ai/veo3.1/image-to-video/api
6. fal.ai queue OpenAPI schema, `fal-ai/veo3.1`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/veo3.1
