# Nano Banana Pro (`nano-banana-pro`, Gemini 3 Pro Image via fal): prompt dialect

- **Endpoints we use:** `fal-ai/nano-banana-pro`; with references, `fal-ai/nano-banana-pro/edit`.
- **Inputs we send:** `prompt` (max 50,000 characters), `aspect_ratio`, `resolution` (1K/2K; 4K is not offered), and with references `image_urls`.
- **How many references:** we send up to 8, `image_max_refs`' default. fal's schema states a 14-reference total [4].
- **Accepted by the endpoint, not wired:** `system_prompt`, `enable_web_search`, `history`. Thinking is fixed at `high` [4].
- **Version match:** Google's API page covers `gemini-3-pro-image` (Nano Banana Pro) alongside newer Flash models [1]. Google's "7 tips" post is for Nano Banana Pro [2]. The Google Developers post is for Gemini 2.5 Flash Image, an older model [3].

## Rules

1. Include subject, composition, action, location and style. For professional results add aspect ratio, camera and lighting details, text specifics, and factual constraints for diagrams. [2]
2. "Describe the scene, don't just list keywords": a narrative paragraph beats disconnected words (2.5 Flash Image guidance). [3]
3. Be hyper-specific: "The more specific you are, the more control you have over the results." [1][3]
4. State context and intent, for example "Create a logo for a high-end, minimalist skincare brand" rather than "Create a logo". [3]
5. Photorealistic template: "A photorealistic [type of shot] of a [subject description] in a [setting description]", plus "Shot from a [camera angle] with a [lens type]" and the lighting. [1]
6. **Semantic negatives:** describe what you want instead of "no …". Write "an empty, deserted street with no signs of traffic" instead of "no cars". [3]
7. **Text:** "Be clear about the text, the font style (descriptively), and the overall design." Say exactly what text appears, where and in what style ("a bold, white, sans-serif headline at the top"). [1][2]
8. Small text and exact spellings "may not come out perfectly". [2]
9. Gemini 3 Pro Image is Google's pick "for professional asset production" and text-heavy work. [1]
10. **References:** give each uploaded image a role: "Use Image A for the character's pose, Image B for the art style, and Image C for the background environment." Up to 14 images can be blended. [2]
11. **Edits:** be direct about the change, and lock the rest: "Keep everything else in the image exactly the same, preserving the original style, lighting, and composition." [1]
12. Define a "mask" conversationally to edit one part and leave the rest untouched. [1]
13. With several inputs the model takes the aspect ratio of the last image. State "Do not change the input aspect ratio" if it drifts. This is 2.5 Flash Image behaviour, unconfirmed for Pro. [3]
14. For a background that will carry text later, describe "a vast, empty" area as negative space. [1]
15. Iterate in small conversational follow-ups rather than rewriting the whole prompt. [3]

## NOT FOUND in primary sources

- A prompt-length sweet spot.
- Per-type reference limits for Pro (characters vs objects); the API page's table did not parse cleanly in our fetch [1].
- Whether fal's `image_urls` order maps to "Image A/B/C" wording.

## Conflicts with our pipeline

- **Reference wording.** `prompts/skills/product-still.md` writes the lock as "the exact product from the reference photos". Google says give each image a role by name [2]. With several attached photos (product + person + place), an unnamed lock leaves the roles to the model.
- **The make_image brief agrees.** `creative_guide_make.txt` says "subject, setting, light, lens and distance, surface and texture, mood -- concrete nouns". That matches Google's photographic template [1][3].

## Sources (all accessed 2026-10-24)

1. Google AI for Developers, "Image generation" (Gemini API; Nano Banana models). https://ai.google.dev/gemini-api/docs/image-generation
2. Google Blog, "7 tips to get the most out of Nano Banana Pro" (2025-11-20). https://blog.google/products/gemini/prompting-tips-nano-banana-pro/
3. Google Developers Blog, "How to prompt Gemini 2.5 Flash Image Generation for the best results" (older model). https://developers.googleblog.com/en/how-to-prompt-gemini-2-5-flash-image-generation-for-the-best-results/
4. fal.ai queue OpenAPI schemas, `fal-ai/nano-banana-pro` and `/edit`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/nano-banana-pro
