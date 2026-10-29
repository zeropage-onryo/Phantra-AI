# GPT Image (`gpt-image-2`, `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`): prompt dialect

**Endpoints we use**

| Model | Text-to-image | Edit (with references) |
|---|---|---|
| GPT Image 2 | `openai/gpt-image-2` | `openai/gpt-image-2/edit` |
| GPT Image 2.5 Flare | `openai/gpt-image-2.5/flare/text-to-image` | `.../flare/edit` |
| GPT Image 2.5 Sunburst | `openai/gpt-image-2.5/sunburst/text-to-image` | `.../sunburst/edit` |

**Inputs we send**
- `prompt` (max 32,000 characters), `image_size` and `quality`: `medium` on 2, `high` on 2.5.
- With references: `image_urls`, up to 16 [3].

**Accepted by the endpoints, not wired**
- `background` (`transparent` / `opaque` / `auto`), `mask_url` (white = edit, black = keep), and `image_passthrough` [3].
- Quality levels: 2.5 takes `auto`, `low`, `medium`, `high`, `xhigh`, `max`; GPT Image 2 takes `low`, `medium`, `high`, `auto` [1][3].

**Version match**
- OpenAI's image-prompting guide covers GPT Image 2.5 (Flare = small, speed-optimised, quality comparable to GPT Image 2; Sunburst = base, quality above GPT Image 2) and keeps GPT Image 2 notes [1].
- The cookbook guide covers GPT Image 2 and is marked archived [2].

## Rules

1. Define the result first: subject, intended use, composition, aspect ratio and placement constraints. "For complex requests, organize the prompt as scene, subject, details, and constraints, using labeled sections." [1]
2. Use a consistent order: "background/scene → subject → key details → constraints". State the intended use (ad, UI mock, infographic). [2]
3. Any format can work: prose, JSON-like, instructions, tags. For production, "prioritize a skimmable template over clever prompt syntax". [1][2]
4. Name materials, lighting, colours and the medium. When photorealism is the goal, ask for "photorealistic" or "real photograph". [1][2]
5. Treat camera specs as "cues for appearance, not a guarantee of exact physical simulation". [1]
6. For people, describe framing, scale, gaze and interaction with objects. [1][2]
7. **Text:** put required wording in quotes (or ALL CAPS) and give its position and typography. "Spell unusual words or brand names letter by letter when needed." Use medium or high quality for small or dense text. [1][2]
8. **Constraints are stated explicitly.** "State exclusions and invariants explicitly," such as no watermark, no extra text, or no logos. "Ask for no extra text, then check spelling." [1][2]
9. **Multiple inputs:** "Identify each input by number and purpose: subject, style, clothing, or background." Explain how they combine, which elements move where. [1][2]
10. **Edits:** write "change only X", then list what must stay (identity, layout, lighting, labels).
    - For surgical edits also lock saturation, contrast, camera angle and surrounding objects.
    - Repeat the preserve list on every iteration. [1][2]
11. "Repeated edits can still change details you intended to preserve." Composite the result when pixels must stay identical. [1]
12. **Transparency:** set `background="transparent"` with PNG or WebP. "A drawn checkerboard is not transparency." Transparency is in preview on GPT Image 2. [1]
13. Raise quality only when the output falls short. "A higher setting doesn't guarantee a better result for every prompt", and the same label differs across models. [1]
14. Known failure points: misspelled or extra text, drift across edits, period details, diagram labels, fake transparency. [1]

## NOT FOUND in primary sources

- A prompt-length sweet spot. OpenAI says "Long prompts can work, but a clean base prompt is easier to debug" [2].

## Conflicts with our pipeline

- **Negatives: none.** OpenAI is the one image vendor that *endorses* explicit exclusions ("no watermark, no extra text") [1][2], so negative lines are not a conflict here.
- **Reference wording.** `prompts/skills/product-still.md`'s "the exact product from the reference photos" names no input. OpenAI says identify each input by number and purpose [1].

## Sources (all accessed 2026-10-24)

1. OpenAI API docs, "Image prompting" (GPT Image 2.5 Flare/Sunburst; GPT Image 2 notes). https://developers.openai.com/api/docs/guides/image-prompting
2. OpenAI Cookbook, "GPT Image Generation Models Prompting Guide" (gpt-image-2; archived). https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
3. fal.ai queue OpenAPI schemas, `openai/gpt-image-2`, `/edit`, `openai/gpt-image-2.5/flare/text-to-image`, `.../sunburst/edit`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=openai/gpt-image-2.5/sunburst/edit
