# Grok Imagine Video 1.5 (`grok1.5`, `grok1.5-lite`): prompt dialect

- **Endpoints we use:**
  - 1.5: `xai/grok-imagine-video/v1.5/text-to-video` and `/image-to-video`.
  - Lite: `xai/grok-imagine-video/v1.5/lite/text-to-video` and `/image-to-video`.
- **Inputs we send:** `prompt` (max 4,096 characters), `image_url` (i2v start frame), `duration` (an integer), `resolution`, `aspect_ratio` (t2v only) [5].
- **Not wired:** fal's reference-to-video endpoints. xAI's own API also has `last_frame`, up to 4 `keyframes`, up to 14 reference images and up to 3 preset voices, on 1.5 only [1][2].
- **Legal values (src/fal.py):** 1–15 s; 480p, 720p or 1080p; t2v frames 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3.
- **Sound** is generated with the picture, with lip-synced speech on both 1.5 and Lite [2].
- **Version match:** xAI's docs cover `grok-imagine-video-1.5` and `-1.5-lite`. **Primary prompting guidance for video is thin.** xAI publishes a full prompting guide only for its *image* model [4].

## Rules

1. **Text-to-video is image-first.** "On `grok-imagine-video-1.5` and `grok-imagine-video-1.5-lite`, text-to-video uses text-to-image then image-to-video under the hood: the model generates a first frame from your prompt, then animates it." [2]
2. For text-to-video, "Describe the shot, including camera movement, lighting, and sound." [1]
3. For image-to-video, "The still you pass as `image` becomes the first frame, and the prompt describes what happens next."
   - "The output always matches the still's aspect ratio; `aspect_ratio` is ignored."
   - Write the motion, not the picture. [1]
4. **References** (xAI API; not on our fal endpoints):
   - Name images by position: `<IMAGE_0>`, `<IMAGE_1>`, ….
   - If `image` pins the first frame, it takes `<IMAGE_0>` and the references start at `<IMAGE_1>`.
   - Name voices as `<AUDIO_0>`, … [3]
5. Reference images "supply the characters, products, and locations without fixing the first frame." [1]
6. Because text-to-video first draws a still (rule 1), xAI's image guide applies to the opening frame. This is our inference from [2] and [4]: xAI does not say it for video.
   - "Open with one sentence that names the subject, the state or form it is in, what holds or supports it, and the setting."
   - "A prompt that leads with mood, film stock, or a list of things to avoid produces a styled scene whose subject is a stand-in." [4]
7. From the image guide: "A long avoid list is easy to ignore, and it spends the prompt on objects that then show up anyway." Keep a constraint only when it is a count or a specific object, and pair it with what you want. [4]
8. From the image guide: describe materials positively ("Brushed steel with fine horizontal grain", not "not shiny"). [4]
9. From the image guide: ask for light that keeps the subject readable. "Slightly underexposed" and "crushed shadows" pull the image dark. Leave out chromatic fringing, dust and scratches, which "the model draws … as defects." [4]

## NOT FOUND in primary sources

- Dialogue syntax (quotes, speaker labels).
- Camera vocabulary.
- Multi-shot or timestamp syntax.
- Negative prompts for video.
- Length sweet spot.
- Any difference between 1.5 and Lite in prompting.

## Conflicts with our pipeline

- **Order.** `enhance_system.txt` says "hard constraints and negatives first, then the style and texture declaration, then motion". xAI's image guide warns that leading with mood, film stock or an avoid list makes the subject "a stand-in" [4]. Since text-to-video draws its first frame from the prompt [2], this likely carries over. That last step is our inference.
- **Avoid list and film-stock words.** `scenes_prompt.txt` part 5 (the AVOID list) and `enhance_system.txt` ("a named film stock or grain character") match what xAI's image guide calls easy to ignore or defect-inducing [4].

## Sources (all accessed 2026-10-24)

1. xAI docs, "Imagine — Video Overview". https://docs.x.ai/developers/model-capabilities/video/overview
2. xAI docs, "Imagine — Video Generation". https://docs.x.ai/developers/model-capabilities/video/generation
3. xAI docs, "Imagine — Reference-to-Video". https://docs.x.ai/developers/model-capabilities/video/reference-to-video
4. xAI docs, "Imagine — Image Prompting Guide" (for `grok-imagine-image-2.0`). https://docs.x.ai/developers/model-capabilities/images/prompting-guide
5. fal.ai queue OpenAPI schemas, `xai/grok-imagine-video/v1.5/*`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=xai/grok-imagine-video/v1.5/text-to-video
