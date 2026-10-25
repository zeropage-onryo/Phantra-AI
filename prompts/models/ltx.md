# LTX (`ltx2.3`, `ltx2.5-fast`, `ltx2.5`): prompt dialect

- **Endpoints we use:**
  - LTX-2.3: `fal-ai/ltx-2.3/text-to-video`, `fal-ai/ltx-2.3/image-to-video`.
  - LTX-2.5 Fast: `lightricks/ltx-2.5/{text,image}-to-video/fast`.
  - LTX-2.5 Pro: `lightricks/ltx-2.5/{text,image}-to-video/pro`.
- **Inputs we send:** `prompt` (5,000 characters max), `image_url` (i2v start frame), `duration` (an integer), `resolution`, `aspect_ratio` (t2v).
- **Accepted by the endpoints, not wired:** `end_image_url`, `generate_audio` (default true), `fps`, and, on 2.5 only, `camera_motion` (`dolly_in`, `dolly_out`, `dolly_left`, `dolly_right`, `jib_up`, `jib_down`, `static`, `focus_shift`) [7].
- **Legal values (src/fal.py):**

  | Model | Durations (s) | Resolutions |
  |---|---|---|
  | `ltx2.3` | 6, 8, 10 | 1080p, 1440p, 2160p |
  | `ltx2.5-fast` | 6–20 in even steps | 720p, 1080p, 1440p, 2160p |
  | `ltx2.5` | 6, 8, 10 | 720p, 1080p |

  Every model takes 16:9 or 9:16 on text-to-video.
- **Version match:**
  - Lightricks' prompting text names LTX-2 [1][5].
  - The prompt-enhancer system prompts in the LTX-2 repo are versioned by text encoder: `gemma3_*` serves LTX-2.3, which uses a Gemma 3 encoder, and `gemma4_*` serves LTX-2.5, which uses Gemma 4 [1][2][3][4].
  - The `gemma4` files say outright that they write captions "in the EXACT style of the training captions used for this video model" [2][3].
  - The official docs page (docs.ltx.video prompting guide) returned 403 to our fetch, so it was not read.

## Training caption style (stated by the vendor)

LTX-2.5 was trained on single-paragraph, objective, chronological audio-visual captions of about 150–220 words. Each caption begins immediately with the action, weaves shot size, camera motion and camera viewpoint into prose, and quotes dialogue exactly [2][3].

## Rules

1. Write ONE continuous paragraph. Use no bullets, headers or labels: "No bullet points, no section headers, no labels like 'Audio:' or 'Visual:'." [2]
2. Begin with the action or a visual detail. Never write "The scene opens…", "We see…" or "There is…". [2][4]
3. Length:
   - LTX-2.5: about 150–220 words [2].
   - The README says "Keep within 200 words" [1].
   - The blog suggests 4 to 8 descriptive sentences [5].
4. Keep strict chronological, real-time order, with connectors such as "Initially…", "A moment later…", "Simultaneously…" (2.5) [2], or "as", "then", "while" (2.3) [4].
5. Use present tense or present-progressive verbs [4][5].
6. For every shot on 2.5, state:
   - exactly one shot size (extreme wide / wide / medium / medium close-up / close-up / extreme close-up);
   - the camera motion ("if none, explicitly say the camera remains static");
   - the viewpoint (front / back / side / over-the-shoulder / top-down / low / high).

   Write all three as prose, never as tags ("Never as 'medium shot, static camera —'") [2].
7. Describe camera movement by its relationship to the subject. Say how subjects appear after the move, "to give the model a better idea of how to finish the motion" [5].
8. Describe only what is observable. Write "his eyebrows angle downward…", not "he looks sad" [2]. The blog likewise says avoid labels like "sad" or "confused" without visual cues [5].
9. Dialogue:
   - Quote it exactly, in its own language [2][5].
   - Give voice characteristics, for example "The man says in an excited voice: '…'" [4].
   - Name the language and accent when it matters [5].
10. Describe the complete soundscape in the same paragraph: dialogue, tone of voice, music (type, mood, volume changes) and specific environmental sounds ("soft footsteps on tile", not "ambient sound is present") [2][4]. Lightricks' model card notes that "Audio generated without speech may be of lower quality." [6]
11. **Image-to-video:** the opening must match the first frame exactly (same subject, clothing, setting, light, composition), then narrate what happens from that frame. "Single continuous take — no hard cuts." [3]
12. Keep 2.3's language restrained: plain colours ("red dress", not "vibrant blue"), neutral light ("soft overhead light", not "blinding light") [4].
13. Expect no readable text. "LTX-2 does not currently generate readable or consistent text. Avoid signage, brand names, or printed material." [5]
14. Avoid complex physics: "Non-linear or fast-twisting motion (e.g., jumping, juggling) can lead to artifacts". Dancing can work [5].
15. Keep the scene simple. "Too many characters, layered actions, or excessive objects reduce clarity." The more actions you add, "the higher the chance some of them won't be seen" [5].
16. Don't mix conflicting light sources ("a warm sunset with cold fluorescent glow") unless the mix is motivated [5].
17. Match detail to shot scale: "Closeups need more precise detail than wide shots." [5]
18. Name stylized looks early in the prompt. On 2.3 a leading "Style: <style>, …" is the enhancer's format [4][5].
19. Write no timestamps or cuts unless a cut is asked for (2.3: "DO NOT use timestamps or describe scene cuts unless explicitly requested") [4].
20. Lightricks warns: "Prompt following is heavily influenced by the prompting-style." [6]

## NOT FOUND in primary sources

- Any negative-prompt mechanism. The fal LTX endpoints have no `negative_prompt` field [7], and Lightricks gives no guidance on negative phrasing.
- Whether "No background music." is obeyed.

## Conflicts with our pipeline

- **Opening line.** `scenes_prompt.txt` part 1 opens every prompt with "Ultra-realistic grounded [tone] video in 9:16," plus reference-lock clauses. LTX-2.5's caption style says begin immediately with action or visual detail [2]. LTX-2.3 tolerates a leading style clause [4].
- **Order.** `enhance_system.txt` says "hard constraints and negatives first … motion, camera and blocking last." LTX wants the main action first [1][2].
- **Labelled blocks.** Our five-part structure (STYLE / BEATS / SOUND / AVOID) and the gold standard's separate "Avoid:" paragraph contradict "One single continuous paragraph … no labels like 'Audio:'" [2].
- **Cuts.** `shot_timeline_prompt.txt` asks each shot prompt to say "hard cut to" / "reverse on". The i2v caption style is "Single continuous take — no hard cuts" [3], and 2.3 says don't describe scene cuts unless requested [4].
- **Length.** The continuity block (prepended by code), the shot prompt, the scene's tail (sound, avoid list, look) and the voiceover often add up to well over the 150–220-word caption length [2]. `enhance_system.txt` says "LENGTH IS NOT A GOAL".
- **Quality words.** `enhance_system.txt` bans "cinematic". LTX-2.5's own enhancer weaves in "warm cinematic lighting", "film-grade color" [2]. The two pull in opposite directions.
- **Brand text.** `creative_guide_make.txt` says to "Carry the person's exact words for anything named (a product, a brand…)". LTX says avoid brand names and printed material, because it cannot render text [5].

## Sources (all accessed 2026-10-24)

1. Lightricks, LTX-2 GitHub README, "Prompting for LTX-2". https://github.com/Lightricks/LTX-2
2. Lightricks, LTX-2.5 t2v enhancer system prompt (`gemma4_t2v_system_prompt.txt`). https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-core/src/ltx_core/text_encoders/gemma/encoders/prompts/gemma4_t2v_system_prompt.txt
3. Lightricks, LTX-2.5 i2v enhancer system prompt (`gemma4_i2v_system_prompt.txt`). https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-core/src/ltx_core/text_encoders/gemma/encoders/prompts/gemma4_i2v_system_prompt.txt
4. Lightricks, LTX-2.3 t2v enhancer system prompt (`gemma3_t2v_system_prompt.txt`). https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-core/src/ltx_core/text_encoders/gemma/encoders/prompts/gemma3_t2v_system_prompt.txt
5. LTX Team blog, "Prompting guide for LTX-2" (2025-12-11). https://ltx.io/blog/prompting-guide-for-ltx-2
6. Lightricks, LTX-2.3 model card (Hugging Face). https://huggingface.co/Lightricks/LTX-2.3
7. fal.ai queue OpenAPI schemas. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=lightricks/ltx-2.5/image-to-video/pro (also `fal-ai/ltx-2.3/image-to-video`, `lightricks/ltx-2.5/text-to-video/fast`)
