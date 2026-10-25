# Ideogram 4.5 (`ideogram4.5`): prompt dialect

- **Endpoint we use:** `ideogram/v4.5`. It is text-only: there is no edit endpoint in our table.
- **Inputs we send:** `prompt` (max 10,000 characters), `image_size` (enum presets), `quality` (`medium`).
- **Prompt expansion is on.** The endpoint takes `enable_prompt_expansion` with **default true** ("partner prompt expansion", Ideogram's Magic Prompt). We never send it, **so our prompt is rewritten before it renders** [1][5].
- **Version match:** Ideogram's prompting guide covers Ideogram 4.5, 4.0 and 3.0 [1].

## Rules

1. Write in sentences. Tag lists can work, but sentences tell the model "how things relate: who holds what, what sits behind what." [1]
2. "Put the main idea first. Words near the start of the prompt tend to carry more weight." [1]
3. Use the template `[image type] of [main subject], [action or placement], [setting], [lighting], [style]`, with `text that reads "[exact words]"` when lettering is needed. [2]
4. The full order is: summary → subject details → pose/action → secondary elements → setting → lighting and atmosphere → framing → finish. [2]
5. Open with a one-sentence image summary: the kind of image, the main subject and the tone. "If you write only one sentence, make it this one." [2]
6. **Say what you want, not what you don't.**
   - "Image models don't handle 'no', 'without' or 'not' well. They latch onto the word that follows."
   - Write "an empty room with chairs neatly arranged", not "no people in the room".
   - 4.5 has no negative prompt field. [1][4]
7. There is no hidden syntax: weights (`::1`, `(important)`) and flags (`--ar`) are read as words. Aspect ratio and quality belong in settings. Writing "16:9" in the prompt does not replace the setting. [1]
8. **Text:**
   - Quote the exact words.
   - Mention the text early.
   - Say where it appears.
   - Keep it short.
   - Keep the scene simple. [3]
9. With several text blocks, give each its own words, style and place, in reading order from top to bottom. [3]
10. Describe lettering by weight, shape and mood rather than a font name. [3]
11. Text is most accurate in English. Keep non-Latin text to a word or two. Long passages belong in a design tool. [3][4]
12. Vague style words ("beautiful", "cool", "artistic", "modern") "don't point to anything Ideogram can draw". Name a medium, technique or movement instead. [4]
13. Tie abstract ideas to something visible: "a single flower blooming through a crack in the concrete", not "a symbol of hope". [4]
14. Avoid contradictions ("a clean, empty room cluttered with artifacts"): choose one direction. [4]
15. Faces and hands distort when the person is small in frame. Use "close-up" or "portrait" when people matter. [4]
16. Length: 4.5 takes up to 10,000 characters, "but a focused prompt is still easier to control". Too many unrelated ideas confuse it. [2]
17. A detail that comes late in a long prompt gets little weight. Move it earlier or repeat it. [4]
18. 4.5 accepts plain language or a structured JSON prompt with text, colour palette and bounding-box fields. JSON guides composition but "doesn't turn image generation into a fixed layout engine". [1]

## NOT FOUND in primary sources

- How fal's "partner prompt expansion" maps to Ideogram's Magic Prompt settings, beyond the name.

## Conflicts with our pipeline

- **Expansion.** Expansion is on by fal default [5]. Ideogram says turn Magic Prompt off "when you want to evaluate your own wording" and when it keeps adding unwanted things [1][4]. Every still the studio writes for Ideogram is rewritten first, and the studio does not see the rewritten text.
- **"No" lines.** A still prompt with "no …" phrasing (for example an avoid list carried over from a scene) gets the effect Ideogram warns about: the model "latch[es] onto the word that follows" [4].

## Sources (all accessed 2026-10-24)

1. Ideogram docs, "Prompting Basics". https://docs.ideogram.ai/prompting/prompting.md
2. Ideogram docs, "Prompt Structure". https://docs.ideogram.ai/prompting/prompt-structure.md
3. Ideogram docs, "Text in Images". https://docs.ideogram.ai/prompting/text-in-images.md
4. Ideogram docs, "Fix Common Problems" (covers negative prompts). https://docs.ideogram.ai/prompting/fix-common-problems.md
5. fal.ai queue OpenAPI schema, `ideogram/v4.5`. https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=ideogram/v4.5
