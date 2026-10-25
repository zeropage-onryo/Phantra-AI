# Seedream 4.5 (`seedream4.5`): prompt dialect

- **Endpoints we use:** `fal-ai/bytedance/seedream/v4.5/text-to-image`; with references, `fal-ai/bytedance/seedream/v4.5/edit`.
- **Inputs we send:** `prompt`, `image_size` (between 2560×1440 and 4096×4096 total pixels; we scale ×2), `seed`, and `image_urls` (up to 10, our `max_references`).
- **Over 10 references:** fal says "If over 10 images are sent, only the last 10 will be used." [2]
- **Version match:** BytePlus' guide covers Seedream 4.0 and 4.5 together [1].

## Rules

1. Describe the scene in coherent natural language: **subject + action + environment**. Add style, colour, lighting or composition when aesthetics matter.
   - Recommended: "A girl in a lavish dress walking under a parasol along a tree-lined path, in the style of a Monet oil painting."
   - Avoid: "Girl, umbrella, tree-lined street, oil painting texture." [1]
2. Be concise. 4.5 and 4.0 "generate the expected images with less description". Concise, precise prompts usually beat "repeatedly stacking" ornate words. [1]
3. State the purpose and type of image: "Design a logo for a gaming company…", not "An abstract image of a dog…". [1]
4. Use precise style keywords ("children's book illustration style") or a style reference image. [1]
5. Put text that must appear in **double quotation marks**: `Generate a poster with the title "Seedream 4.5".` [1]
6. For knowledge-dense images (formulas, diagrams, infographics), use precise technical terms. [1]
7. **Edits:** give concise, unambiguous instructions with no vague pronouns, and say what stays unchanged. Write "Dress the tallest panda in pink Peking Opera costume…, keeping its pose unchanged", not "Put that one in pink clothes". [1]
8. Edit verbs are add, remove, replace and modify. When text alone can't pin the region, arrows, bounding boxes or doodles drawn on the input mark it ("where the red area is marked"). [1]
9. **References:** state the reference target (what to keep, such as character design or product material) and then the generated scene in detail. [1]
10. **Multi-image input:** say what to take from each image by number: "replace the character in Image 2 with the character from Image 1, … in the style of Image 3". [1]
11. **Series output:** "a series", "a set" or a number of images triggers multi-image output with consistent characters. Our pipeline asks for one image. [1]
12. For sketches and wireframes, say "Generate based on the text in the image" when the input carries annotations, and name what must match the layout. [1]

## NOT FOUND in primary sources

- Negative prompts: the guide has no negative field and no advice on negation. fal's schema has no `negative_prompt` field [2].
- Prompt-length limits.
- Whether fal's `image_urls` order is "Image 1, Image 2…" exactly as BytePlus numbers uploads. This is likely but unstated.

## Conflicts with our pipeline

- **Reference wording.** `prompts/skills/product-still.md` writes "the exact product from the reference photos". With several images, BytePlus says name each one by number and role [1].
- **Silent drop past 10.** fal keeps the *last* 10 references when more are sent [2]. Our `image_request` trims to the *first* `max_references` (10) before sending, so nothing is dropped silently. This is a note, not a conflict.

## Sources (all accessed 2026-10-24)

1. BytePlus ModelArk, "Seedream 4.0-4.5 prompt guide". https://docs.byteplus.com/en/docs/modelark/seedream-4-0-5-0-prompt-guide
2. fal.ai queue OpenAPI schemas, `fal-ai/bytedance/seedream/v4.5/text-to-image` and `/edit`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/bytedance/seedream/v4.5/edit
