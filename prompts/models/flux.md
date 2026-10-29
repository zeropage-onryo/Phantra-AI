# FLUX (`flux-pro1.1`, `flux2-pro`): prompt dialect

**Endpoints we use**

| Model | Endpoint | References |
|---|---|---|
| FLUX1.1 [pro] | `fal-ai/flux-pro/v1.1` | none (text only) |
| FLUX.2 [pro] | `fal-ai/flux-2-pro` | the edit endpoint `fal-ai/flux-2-pro/edit` takes `image_urls`; we send up to 8 (`image_max_refs`' default) |

**Inputs we send**
- `prompt`, `image_size` (from the aspect), `seed`.
- FLUX1.1 also has `enhance_prompt` (default **false**); we never send it [7].
- BFL's own API calls the same switch `prompt_upsampling` (default false) [1].
- FLUX.2 [pro] on BFL's API takes up to 8 references, capped by a 9 MP total for input plus output (at 1 MP output, 8 references) [2].

**Version match**
- BFL's current prompting guides are written for FLUX 3 Image [4][5][6].
- BFL keeps a FLUX.2 quick-reference box [2] and a FLUX1.1 [pro] model page [1].
- **There is no FLUX1.1-specific prompting guide in BFL's current docs. Thin.**
- Rules marked (FLUX 3) come from the newer model's guide and are not confirmed for ours.

## Rules

1. **FLUX.2 [pro]:** "No negative prompts supported." [2]
2. Write the scene you want instead of a negation: "an empty promenade" instead of "no crowds"; "clean surfaces", "unmarked" instead of "no text". (FLUX 3) [5]
3. For text in the image, use quotation marks for exact text (FLUX.2) [2]. "Front-load text descriptions" and "Keep text short." [2]
4. Say where the text goes and how it looks, for example `Below the scene, bold serif typography reads "…"`. (FLUX 3) [4]
5. Hex colour codes work in FLUX.2 text-to-image prompts for brand colours: *"The logo text 'ACME' in color #FF5733"*. [2]
6. FLUX.2 supports JSON-structured prompts "for production workflows". [2]
7. FLUX.2 can be prompted in other languages, but "English prompts tend to produce the most precise results". [2]
8. Naming a specific camera model gives an authentic photorealistic look (FLUX.2) [2]. BFL's cheat sheet maps lens and aperture terms to effects: "85mm" for portraits, "f/1.4 – f/2.8" for a blurred background [2].
9. Use natural sentences that explain relationships: "who holds what, what stands behind what, and where the light comes from". (FLUX 3) [4]
10. Starting template, not a strict formula: `[Subject], [location], [style], [camera settings], [lighting], [colors], [effect], [additional elements]`. (FLUX 3) [4]
11. Name only what is visible: no "beautiful", "iconic" or "masterpiece"; "Every phrase names something you could point to in the frame." (FLUX 3) [4]
12. **Multi-reference (FLUX.2 edit):** BFL's FLUX.2 page gives only "<What you want to edit on the image>" [3]. BFL's FLUX 3 multi-reference rules, unconfirmed for FLUX.2 [6]:
    - Refer to each image by position ("image 1", "image 2").
    - Say what each one supplies.
    - Say how the pieces relate.
    - Put the base image first, because it sets the aspect ratio.
13. For edits (FLUX.1 Kontext guidance), say what should change and be explicit about what stays: *"while maintaining the same facial features and hairstyle"*. [2]

## NOT FOUND in primary sources

- Prompt length for FLUX1.1 or FLUX.2.
- Any FLUX1.1-specific prompting advice beyond "strong prompt adherence" [1].
- Whether FLUX.2 [pro] reads "image 1" phrasing the way FLUX 3 does.

## Conflicts with our pipeline

- **Reference wording.** `prompts/skills/product-still.md` locks the product as "the exact product from the reference photos". With several references on FLUX.2 edit, BFL's guidance (FLUX 3) is to name each image by position and role [6]. The lock does not name an image.
- **Negative phrasing.** Any still prompt carrying a "no …" list has no negative channel on FLUX.2 [2], so the phrasing should be positive [5]. `creative_guide_make.txt`'s photographer brief ("concrete nouns, no 'cinematic'") is consistent with rule 11.

## Sources (all accessed 2026-10-24)

1. Black Forest Labs docs, "FLUX1.1 [pro] Image Generation". https://docs.bfl.ml/flux_models/flux_1_1_pro.md
2. Black Forest Labs docs, "Prompt Reference" (includes the FLUX.2 [pro]/[max] quick reference). https://docs.bfl.ml/guides/prompting_unified_reference.md
3. Black Forest Labs docs, "FLUX.2 Image Editing". https://docs.bfl.ml/flux_2/flux2_image_editing.md
4. Black Forest Labs docs, "Prompting Basics" (FLUX 3). https://docs.bfl.ml/guides/prompting_unified_basics.md
5. Black Forest Labs docs, "Technical Parameters: working without negative prompts" (FLUX 3). https://docs.bfl.ml/guides/prompting_unified_technical.md
6. Black Forest Labs docs, "Multi-Reference Editing" (FLUX 3). https://docs.bfl.ml/guides/prompting_editing_multi_reference.md
7. fal.ai queue OpenAPI schemas, `fal-ai/flux-pro/v1.1`, `fal-ai/flux-2-pro`, `fal-ai/flux-2-pro/edit`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2-pro/edit
