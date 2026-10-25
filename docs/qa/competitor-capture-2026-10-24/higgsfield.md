# Higgsfield Supercomputer — capture 2026-10-24

The agent at higgsfield.ai/supercomputer, on the plus plan. For brief 1 the model chip read
"GPT 6 Astra"; in later chats it read "Auto · Free". The mode was "Ask before generating", and
every approval was stopped, so nothing was rendered. Each brief ran in a new chat. Words are
Higgsfield's, copied from the page.

## Spend log (Higgsfield credits, read through the Higgsfield MCP `balance`)

| Point | Balance |
|---|---|
| Start | 557.16 |
| After briefs 1 + 2 (GPT 6 Astra turns) | 551.02 |
| After briefs 8, 9, 13 (Auto · Free) | 551.02 |

Total: **6.14 credits**. Every generate was stopped: 0.25 for brief 1's still, 2.75 for brief
2's still, 160 for brief 8's video.

## Brief 1: "a coffee cup on a rainy window"

- **No questions.** "Explored models, thought it through", then "Approve image?" on **GPT
  Image 2.5**, 0.25 credits.
- Card ("Approve image generation"):
  - the prompt;
  - a model chip with a menu;
  - a "Type something else..." field, to redirect instead of approving;
  - Always allow / Stop (Esc) / Approve · 0.25.
  - **No frame on the card.**

> A quiet, natural still-life photograph of a ceramic coffee cup resting on a wooden windowsill beside a rain-covered window. Fresh dark coffee, delicate steam rising from the cup. Focus on the cup and nearby raindrops streaking down the glass, with the rainy street outside softly blurred. Soft overcast daylight, warm cream ceramic and honey-colored wood against cool gray-blue outdoors. Close-up composition, eye-level perspective, realistic textures, peaceful cozy mood. No text or logos.

- About 480 characters. A plain still prompt, with no timing and no camera motion.

## Brief 2: "help me make an ad"

- "Happy to help. A few quick choices so I build the right thing:" Then **one question at a
  time**, numbered 1/3, 2/3, …, with numbered options. Each step has "No, and tell us what to
  do differently", Skip (Esc) and Continue.
  - 1/3 "What kind of ad deliverable do you want?":
    - Video ad (with or without voiceover): 9:16 or 16:9 spot, 5-30s, product or UGC style
    - Static ad creative / poster
    - Product photos / packshots
    - Ad copy only

    Picked: Video ad.
  - 2/3 "What are you advertising? Paste a product name/URL, or upload the product photo
    (best results with an actual image)." The answer area is an upload zone plus text.
    Typed: "a high-performance energy drink".

    Return sent it as a chat message, so question 3/3 was never shown.
- "Thought it through, viewed skill", then "Approve image?" on GPT Image 2.5, **2.75**
  credits. Video ad had been picked, but the first step is a **key visual still**:

> Vertical 9:16 premium energy-drink advertising key visual. A slim matte-black aluminium can with a brushed graphite top, standing dead center on wet black slate, ice cubes and electric-lime liquid splashing up around its base, tiny water droplets beaded on the metal. Can artwork: bold geometric lightning bolt in neon lime, the wordmark "VOLTAIC" printed vertically in heavy condensed white sans-serif with a thin lime underline, small lime type lines reading "ZERO SUGAR" and "200MG CAFFEINE". Hard cyan rim light from behind left, warm amber edge from right, deep charcoal background with a faint electric-lime haze and thin voltage-arc filigree. Top of frame: huge white condensed headline "CLEAN VOLTAGE." with a lime accent, smaller lime subline beneath it reading "ZERO CRASH." Bottom: small lime badge reading "ELECTRIC CITRUS". Photorealistic commercial product photography, razor-sharp focus, glossy reflections, cinematic contrast, high-end beverage campaign look, no extra text, no logos besides this one.

What it does:
- It invented a brand ("VOLTAIC"), product claims ("ZERO SUGAR", "200MG CAFFEINE") and the
  headlines, and never said so. invideo named the brand it invented and kept the claim
  "lifestyle only".
- Every piece of text that must appear is quoted, with its type and position.

## Brief 8: "a 10 second clip of a man walking home at night, in the style of Wong Kar-wai"

- **No questions.** "Thought it through, skill view failed, viewed skill", then "Approve
  video?" on **Seedance 2.5**. The card has chips **16:9 · 10s · 1080p · High** and Approve
  · **160**. It is text-to-video: no still first.
- Prompt, word for word:

> A tired man walks home through a rain-soaked Hong Kong night, and the city will not let him arrive.
>
> A narrow sloping street in Kowloon after midnight: wet asphalt holding every sign above it, tiled shopfronts with shutters half down, a noodle stall venting steam into the rain, plastic sheeting taped over a broken window and breathing in the wind, air-conditioners dripping onto a corrugated awning, a red lantern swaying on its hook. One thing moving in the background: a distant bus braking at the corner, its light dragging across the wet road.
>
> He is in his late thirties, white shirt gone translucent at the shoulders, dark tie pulled loose, suit jacket folded over one forearm, a plastic bag of takeaway hanging from two fingers and swinging against his thigh, hair stuck flat to his forehead. He keeps glancing back over his shoulder at nothing.
>
> 0.0–4.6s · MCU · handheld, just behind his right shoulder, tracking at 1.3 m/s. We see the back of his neck, his ear, the collar darkening with rain; the street's signage burns behind him as soft bokeh discs that slide and smear as he moves. He steps off the kerb into a standing puddle; the water breaks and reassembles his reflection around his shoe; passing shoppers erode into step-printed streaks at the frame edge. Outgoing: his shoulder fills the left third as he reaches the far pavement.
>
> Hard cut.
>
> 4.6–7.8s · MS · locked-off from across the street, low wall in the foreground, rain close enough to the lens to blur into moving glass. He stops under a leaking awning, tips his head up at the dripping edge, then drags the flat of his hand down his face and lets it fall. The bag swings once and settles against his knee. Neon from a closed pharmacy crawls green across his shirt. Outgoing: he pushes off the wall and walks on, frame right.
>
> Hard cut.
>
> 7.8–10.0s · MCU · low angle from inside a narrow stairwell doorway, looking out past him. He squeezes in past a curtain of plastic beads that clatter and swing back; a green fluorescent tube overhead stutters, dies, catches again. He pauses on the second step and turns his head toward the failing light. Outgoing: the tube holds green for one beat, then gutters, and the doorway sinks into shadow behind him.
>
> Camera law: 85mm and 50mm anamorphic glass, handheld for the street and locked for the doorway, lens height 1.5–1.6m throughout, 24fps with step-printed 12fps motion blur on all movement, 1.85:1 framing. Never level and centred — he sits on the right or left edge, or behind a foreground obstruction.
>
> Grade: neon-noir, jade green and sodium orange, blacks crushed with milky lifted shadows, halation blooming off every tube and sign, wet surfaces reflecting the whole street back up at itself. Audio: no music, no score, no bgm — diegetic only: rain drumming on the plastic awning, his shoes in puddles, distant traffic and a scooter horn, an air-conditioner drip, a roller shutter rattling, the electric buzz of the failing tube.
>
> Count of speaking characters: zero. Count of hard cuts: two. Count of on-screen subtitles: zero. Count of on-screen text legible in frame: zero. Screen direction stays left-to-right in both street shots. The same man, the same shirt, the same plastic bag in all three shots.

What this prompt does:
- **The director's name is gone, translated into craft**: step-printing, jade and sodium,
  anamorphic, off-centre framing, neon-noir halation. Vesper's Reasoning tier also dropped the
  name, but without putting the craft in its place.
- It is ONE prompt with timed shots (0.0–4.6s / 4.6–7.8s / 7.8–10.0s), shot sizes, "Hard cut."
  between shots and an "Outgoing:" frame for each cut. This is the shape of our `(0-3s)`
  windows, but with a shot size and an exit frame per shot.
- Fixed blocks follow the shots: "Camera law", "Grade", "Audio", and a closing list of **counts
  and continuity locks** (speakers, cuts, subtitles, legible text, screen direction, the same
  man, shirt and bag).
- "One thing moving in the background": the background action is rationed.
- It opens with a logline.
- Faults: the card frame is 16:9, but the prompt says "1.85:1 framing", so the prompt and the
  card disagree. And 160 credits was proposed with no question asked and no cheaper draft
  offered.

## Brief 9: "which model is best for a talking head?"

Answered in one turn ("Worked for 8s"), no make:

> Depends on whether you're generating the performance from scratch or syncing it to a voice you already have.
> Best single clip, most believable lip sync and audio: Google Veo 3.1 (veo-3-1-preview, quality high/ultra). Native dialogue plus the most natural mouth shapes; 16:9 or 9:16, and you can feed a start image so a photo or a Soul portrait becomes the presenter. Downside: short clips, so it suits one punchy take, not a long monologue.
> Best for longer takes and a repeatable face: Seedance 2.5. Audio on, up to 30s in one generation, and omni-reference keeps the same person across several clips — the practical pick for a creator doing multiple talking-head segments.
> Kling 3.0 is the third option if you want multi-shot with audio sync in one pass.
> If the voice must be exact (your own recording, a cloned voice, or a locked script read), don't fight the model: generate the performance, then run Sync Lipsync 3 with the source video plus your audio track. It has duration-mismatch modes (remap, cut_off, loop, silence), which is what makes a mismatched voiceover land cleanly instead of drifting.
> Rule of thumb: one short natural take → Veo 3.1; multi-clip creator series → Seedance 2.5; scripted voiceover or cloned voice → any clean clip + Sync Lipsync 3.
> Tell me the format (UGC ad, YouTube segment, avatar series), length, and whether you have a face/voice reference, and I'll set up the right pipeline and write the dialogue prompt.

Then "Suggest next steps" chips: Build UGC ad talking head pipeline / Set up YouTube avatar
series pipeline / Walk through Sync Lipsync 3 setup.

## Brief 13: "3am and the house is awake"

"That line lands like an opening image. Before I make something out of it, which direction do
you want?" One question, five numbered options:
1. Short story / scene
2. Cinematic video clip
3. Narrated monologue (~30-60s)
4. Moody still image
5. Just the writing

Then "No, and tell us what to do differently", Skip and Submit. Stopped here.

## Higgsfield patterns

1. **Ask only when the brief is open.** Briefs 1 and 8 got no questions. Briefs 2 and 13 got
   one question per step, numbered, with an upload where a product photo helps.
2. **The approval card is the prompt and the settings.** It shows the full prompt, then the
   model, frame, length, resolution and quality as chips, the price on Approve, and a "Type
   something else..." redirect.
3. **The model is picked per brief**, and the pick shows on the card: GPT Image 2.5 for
   stills, Seedance 2.5 for the 10 s clip.
4. **Video prompts are shot lists in one prompt**: timed, sized shots with exit frames, then
   camera, grade, audio, and a counts-and-locks block.
5. **Model questions are answered by what the person starts from**, with a rule of thumb and
   next-step chips.
6. Faults:
   - It invents brand names and product claims without saying so.
   - It proposed a 160-credit render with no draft and no question.
   - The frame in the prompt and on the card can disagree (1.85:1 vs 16:9).
