# Per-model prompt dialects

What each model's own vendor says about writing prompts for it, one file per model family. These are craft notes for whoever writes or edits our prompts. Nothing in the code reads them yet.

## Ground rules

- **Primary sources only.** Every rule carries a citation: the vendor's own guide, docs or model card, or fal.ai's model page and queue schema for the exact endpoint we call. There are no blogs or third-party guides.
- **Gaps are marked, not guessed.** Where the vendor is silent, the file says **NOT FOUND in primary sources**.
- **Older guides are flagged.** Where a guide was written for an older version than the one we run, the file says so.
- **Conflicts are quoted.** Each file ends with "Conflicts with our pipeline", quoting lines in `scenes_prompt.txt`, `shot_timeline_prompt.txt`, `enhance_system.txt`, `creative_guide_make.txt` (or a skill) that the vendor advises against.
- **Endpoints, inputs, durations and resolutions** in each header are copied from `src/fal.py` (`VIDEO_MODELS`, `SLOTS`, `IMAGE_MODELS`, `T2V_ASPECTS`), checked against fal's queue OpenAPI schema on 2026-10-24.

## Index

| File | Our model keys | Kind |
|---|---|---|
| [veo.md](veo.md) | `veo3.1` | video + audio |
| [kling.md](kling.md) | `kling3-turbo-pro`, `kling4` | video (+ audio on 4.0) |
| [seedance.md](seedance.md) | `seedance2-fast`, `seedance2`, `seedance2.5` | video + audio |
| [ltx.md](ltx.md) | `ltx2.3`, `ltx2.5-fast`, `ltx2.5` | video + audio |
| [wan.md](wan.md) | `wan3` | video + audio |
| [grok-video.md](grok-video.md) | `grok1.5`, `grok1.5-lite` | video + audio |
| [flux.md](flux.md) | `flux-pro1.1`, `flux2-pro` | still |
| [nano-banana.md](nano-banana.md) | `nano-banana-pro` | still |
| [seedream.md](seedream.md) | `seedream4.5` | still |
| [gpt-image.md](gpt-image.md) | `gpt-image-2`, `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst` | still |
| [ideogram.md](ideogram.md) | `ideogram4.5` | still |

## Sources and dates

All accessed 2026-10-24.

| Model family | Primary source | Publisher date / version covered | Matches our version? |
|---|---|---|---|
| Veo 3.1 | Google Cloud blog "Ultimate prompting guide for Veo 3.1"; Vertex AI video prompt guide; DeepMind Veo prompt guide; fal Veo 3.1 pages | 2025-10-15; Veo 3.1 | Yes |
| Kling 4.0 | kling.ai "Kling 4.0 User Guide" | 2026-10-14 | Yes |
| Kling 3.0 Turbo Pro | kling.ai "Kling VIDEO 3.0 Model User Guide"; kling.ai blog prompt guide | 2026-08-07; Kling 3.0 (not Turbo-specific) | Partly |
| Seedance 2.0 / 2.0 Fast | BytePlus ModelArk "Seedance 2.0 series prompt guide" | 2.0 series | Yes |
| Seedance 2.5 | BytePlus ModelArk "Seedance 2.5 prompt guide"; Dreamina (CapCut, ByteDance) 2.5 page | updated 2026-10-16 | Yes |
| LTX-2.3 / 2.5 | Lightricks LTX-2 README; prompt-enhancer system prompts (gemma3 = 2.3, gemma4 = 2.5); LTX blog "Prompting guide for LTX-2"; HF LTX-2.3 card | blog 2025-12-11 (LTX-2); enhancers current | Yes (enhancers are per version). docs.ltx.video returned 403 and was not read |
| Wan 3.0 | Alibaba Cloud Model Studio "wan3.0 Video Generation Prompt Guide" + overview; Wan 2.2 extender (GitHub) | updated 2026-10-16; 2.2 is older | Yes (2.2 marked older) |
| Grok Imagine Video 1.5 | docs.x.ai video overview / generation / reference-to-video; xAI image prompting guide | current docs | Thin: there is no video prompting guide |
| FLUX1.1 [pro] / FLUX.2 [pro] | docs.bfl.ml FLUX.2 quick reference, FLUX1.1 model page, FLUX 3 guides | current docs are FLUX 3-centric | Partly: FLUX1.1 thin |
| Nano Banana Pro | ai.google.dev image generation; Google Blog "7 tips … Nano Banana Pro"; Google Developers Blog (2.5 Flash Image) | 2025-11-20; 2.5 post older | Yes (2.5 marked older) |
| Seedream 4.5 | BytePlus ModelArk "Seedream 4.0-4.5 prompt guide" | 4.0–4.5 | Yes |
| GPT Image 2 / 2.5 | OpenAI API "Image prompting"; OpenAI Cookbook image prompting guide (archived) | 2.5 + 2 | Yes |
| Ideogram 4.5 | docs.ideogram.ai Prompting Basics / Structure / Text / Fix Common Problems | 4.5, 4.0, 3.0 | Yes |
| All (inputs) | fal.ai queue OpenAPI schemas, `fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>` | fetched 2026-10-24 | n/a |

## Cross-cutting findings

1. **Negatives.** Most vendors advise positive description over "no …":
   - Veo says don't use "no"/"don't"; use the negative-prompt field as plain terms.
   - Kling 4.0 says only "no subtitles" and "no background music" are needed.
   - Seedance documents negatives only for subtitles and audio.
   - FLUX.2 has no negatives at all.
   - Ideogram and Gemini ask for semantic negatives.
   - xAI warns a long avoid list is ignored.

   The exceptions are **Wan 3.0**, which has a negative list *in the prompt*, and **GPT Image**, which says state exclusions explicitly. Our scene prompts put a "no …" AVOID list in every clip's positive prompt (`scenes_prompt.txt` part 5, kept by `enhance_system.txt`).
2. **Order.** Every vendor that states an order leads with subject, action or cinematography. Constraints come last (Seedance, Wan) or are discouraged up front (xAI). `enhance_system.txt` orders "hard constraints and negatives first … motion, camera and blocking last".
3. **Cut words in one-shot clips.** Kling 4.0 (multi-shot on by default), Wan, Seedance and LTX treat cut and transition words as instructions to cut. `shot_timeline_prompt.txt` puts "hard cut to" / "reverse on" into prompts that are each rendered as a single clip.
4. **Timestamps.** Seedance 2.0 "does not respond to timestamps"; 2.5, Wan, Veo and Kling 4.0 do.
5. **Prompt expansion.** Two endpoints rewrite our text unless we turn it off: Wan 3.0 (`enable_prompt_expansion` default true) and Ideogram 4.5 (same field, default true). Veo's `auto_fix` (default true) rewrites only prompts that fail policy or validation.
