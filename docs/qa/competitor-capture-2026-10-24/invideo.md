# invideo Agent Two (Lite) — capture 2026-10-24

Project "Phantra capture 2026-10-24", agent "Scout", Agent Two **Lite**. Approval mode was
"Always allow" (the default) for brief 1, then "Always ask before generating". Words are
invideo's, copied from the page. The rule was to answer with the first suggestion, or "you
decide" when there was none, and to stop at the first generate.

## Spend log (invideo credits, start 50)

| Step | Balance after | Spent |
|---|---|---|
| Brief 1, greeting turn | 49.9 | 0.1 |
| Brief 1, questions form | 49.1 | 0.8 |
| Brief 1, brief + skill read | ~47 | ~2 |
| Brief 1, auto still (Nano Banana Pro, "Always allow"; Stop did not cancel it) | ~43 | ~4 |
| Brief 2, first turn (archived brief 1, opened the form) | 39.5 | ~1.6 |
| Brief 2, answers turn | 37 | 2.5 |
| Brief 2, "you decide" turn: brief update + script + approval form | 27.9 | 9.1 |

## Brief 1: "a coffee cup on a rainy window"

- Turn 1: a greeting only. The brief was sent again in the chat.
- "Rain on glass, coffee steam — that's a mood piece. A few calls so I aim it right."
- Form "Coffee & rain", 4 questions (chips + "Other…"). Picked: Short atmospheric loop (no
  words) / 5–8s loop / 16:9 (YouTube / web) / Quiet melancholy.
- Steps shown: "Locking the hero frame first", "Creating brief Coffee & rain loop", "Reading 1
  skill". Then it generated a still on **Nano Banana Pro** without asking, because the mode was
  "Always allow".
- Prompt sent:

> Photoreal cinematic still, 16:9, motion-safe for video handoff. Extreme close-up to medium close-up: a ceramic coffee cup sits on a wooden windowsill in the lower-left third of frame, steam faintly rising. Beyond the glass, a cool grey rainy day; raindrops and long vertical streaks cling to the window pane, city or soft trees blurred beyond. Soft warm interior spill from frame-left kisses the cup rim and saucer; cool overcast light from outside. Shallow depth of field, 50mm feel, natural skin of ceramic glaze and wood grain, subtle film grain, muted desaturated palette with cool blues and soft amber. Quiet melancholy, empty room feel, no people, no text, no logos, no signage. Foreground cup sharp, midground rain glass readable, background soft. Rule-of-thirds, negative space upper right through the wet glass.

What the still prompt does:
- A still: no timings and no camera motion. "Motion-safe for video handoff" is said once, as
  intent.
- The shape is written into the prompt, and it matches the answer the person gave.
- It adds: lens, light sources by side, depth layers, palette, negatives (no text, logos or
  people) and composition.
- About 1,000 characters, written once. No second rewrite runs after the prompt is shown.

## Brief 2: "help me make an ad" (same thread)

- "Different job — an ad. Parking the rain loop and starting fresh." BRIEF-1 was archived.
- Form "Ad basics", 5 questions:
  - What are we advertising? (free text; typed "a high-performance energy drink", the product
    Vesper's run used)
  - Where does it run? -> Meta / IG / FB (feed + stories)
  - Runtime? -> 6s bumper
  - Feel / format? -> UGC / founder talking to camera
  - Anything locked already? (offer, CTA, logo, product shots, must-say lines) -> left blank
- "Six-second UGC bumper — one line, one claim, product in frame. A few locks before I write
  it." It created brief "Energy drink 6s bumper", then **stopped without asking anything**. We
  sent "you decide".
- "Locking it myself: brand is RISE, one confession line, clean-focus/no-crash claim, 9:16 for
  Meta stories and feed. Writing the six-second script now."
- Steps: "Updating brief BRIEF-2", "Writing 6s AV script + ranked hooks".
- "Here's the six-second lock. Primary is nine words — room to breathe on camera."

PRIMARY (9:16 UGC)

| Time | Visual | Audio |
|---|---|---|
| 0–2s | Phone selfie, handheld. Founder to camera; can just out of frame. | I quit the crash cans. |
| 2–4s | Can comes into frame — matte black, lime RISE wordmark. | Clean focus. No crash. |
| 4–6s | Can close to lens, wordmark sharp. Captions on. | Try RISE. |

> Brand I'm running with: RISE — matte black slim can, electric lime wordmark. Claim is lifestyle only (no medical).
> Top alt hooks if you want a different open: "I was done with the afternoon crash." / "Big can. Bigger crash." / "Still crashing after your energy drink?"

- Approval form "Scout is waiting / Script go?": "Approve this and I lock the founder + can and
  shoot the bumper."
  - Primary script? Go — shoot this / Swap hook / Rewrite — I'll note what
  - If swapping the hook, which open? (the 4 hooks / Skip)
  - Founder vibe on camera? Athletic guy, mid-20s, casual / Athletic woman, mid-20s, casual /
    Either — you cast / I'll describe
  - Anything to change before we shoot? (optional free text: brand name, claim, can color,
    line tweaks)
- **Stopped here.** Answering "Go" would start the casting stills and then the clip.

What the ad flow does:
- "Help me make an ad" is never a dead end. It asks one form of 5 questions, and when the
  person defers it **decides for itself and says so** ("Locking it myself").
- Before any spend, the script is shown as a timed table: time, visual and audio, plus ranked
  alternative hooks.
- The claim is kept safe on purpose ("lifestyle only (no medical)").
- The approval is one form that carries the remaining choices: hook, casting and changes.
- Faults:
  - It invented a brand name instead of asking for one.
  - The person said feed + stories; it picked 9:16 without saying that this crops for feed.
  - The text-only turn cost 9.1 credits.

| Brief 8, brief + skills + still card (Deny) | 21 | 3.6 |
| Brief 9, model search + answer | 12.9 | 8.1 |
| Brief 13, questions form | 12.7 | 0.2 |

Total: 37.3 of 50 invideo credits. No video was rendered. One still was drawn (brief 1, under
"Always allow").

## Brief 8: "a 10 second clip of a man walking home at night, in the style of Wong Kar-wai"

- **No questions.** "Parking the RISE bumper. Ten seconds, man walking home at night, Wong
  Kar-wai — neon rain, slow longing, step-print feel. Locking the still the clip breathes from."
- Steps: "Unloading brief BRIEF-2", "Creating brief WKW night walk", "Reading 2 skills".
- "One continuous night walk — neon, wet asphalt, that slow WKW ache. Building the still the
  camera will follow from." Then "Updating brief BRIEF-3", "Generating Hero still: man walking
  home at night".
- **The approval card** ("Generate Image / WKW night walk"):
  - The whole prompt, in an editable box.
  - "Images 0/8" (reference slots).
  - The frame "Horizontal (16:9)" and the model "Nano Banana Pro · Ingredients", each a chip.
  - Buttons: Deny / **Approve · 2.50 credits** / Always allow.
- Prompt shown:

> Photoreal cinematic motion-safe still for I2V handoff, 16:9. Wong Kar-wai night grammar (In the Mood for Love / Chungking Express): a lone East Asian man in his early 30s walks home along a narrow rain-slick Hong Kong side street at night, mid-stride, weight on his front foot, hands in the pockets of a slightly rumpled dark suit jacket over a white shirt, no tie, hair a little damp. He is placed on the left third of frame walking toward frame-right, leaving leading space ahead of him. Foreground: wet asphalt with sharp neon reflections (magenta, deep red, cool green). Midground: the man, medium-wide, face quiet and tired, gaze slightly down. Background: stacked shopfronts and a distant busier cross-street soft in rain haze, practical neon signs as colored glow only — abstract light shapes, no readable lettering. Lighting: mixed neon practicals and warm tungsten spill from a doorway frame-left, soft rain mist, shallow depth of field, 35mm spherical feel, subtle film grain, crushed blacks, saturated practical colors against muted skin. Pose ready to continue walking. Camera intent: slow lateral track beside him. No text, no logos, no signage lettering, no other people in focus.

- **Deny opens a reason form:** "Tell Scout what should change so it can take the right next
  step". The chips:
  - Prompt needs a clearer direction
  - Add or change the references first
  - Use a more suitable model for this
  - Adjust the settings before generating
  - This is not aligned with the brief
  - I want to revise it before generating

  Plus a note box, and Skip / Submit. We pressed Skip.

What it does:
- **A video is always made still-first**: a hero still, then image-to-video. The still prompt is
  a still, with the intended camera move as one line ("Camera intent: slow lateral track").
- The director's name stays in the prompt, with the films it means named beside it.
- "Mid-stride, weight on his front foot" is a mid-motion start, so the clip begins moving.
- Faults:
  - It asked nothing, though brief 1 got four questions.
  - It cast an ethnicity and a costume and never said that it had chosen them.

## Brief 9: "which model is best for a talking head?"

- "Pulling the current lineup so I give you the real answer, not a stale one." Step: "Searching
  models for talking head avatar lipsync photo avatar dialogue on camera". Then:

> Depends on the source:
> Portrait photo + script: P-Video Avatar. Best for a quick presenter-style talking head.
> Existing video + replacement audio: Kling Lipsync. Best when you already have the performance.
> Generate a filmed-looking person speaking in a scene: Seedance 2.5 or MiniMax H3, with native dialogue and lip-sync.
> For a founder UGC, I'd use Seedance or MiniMax if we're generating the whole clip; P-Video Avatar if you have a portrait to animate.

- It answered in one turn, from a live lookup of its models, split by **what the person
  starts from**. It added a pick for the work already in the thread (the founder UGC). No form
  and no make.

## Brief 13: "3am and the house is awake"

- "That's a strong opening. Is it a new piece, or a turn in the night-walk idea?" Then a form,
  "3 a.m. idea / One quick direction check before I build on it":
  - What are you picturing? A new short film / A scene in the night-walk piece / Just
    developing the idea for now
  - If it's a film, what form and length? Wordless mood piece, 10–15s / Short narrative,
    about 60s / Longer short / Not sure — shape it with me
  - What does "the house is awake" mean? (free text; the hint lists "People moving through the
    dark, strange noises, a baby, something uncanny, or your own take")
- Stopped here; the cap was near (12.7 credits left).

## invideo patterns, across the five briefs

1. **A form, not a chat question.** Its questions come as one dialog of 3-5 questions, chips
   plus free text, answered in one submit. "Continue chatting" sets it aside. It asks only when
   the brief is open: briefs 1, 2 and 13. A clear brief (8) gets none.
2. **When the person defers, it decides and says what it locked** ("Locking it myself: brand is
   RISE … 9:16 …"). It never dead-ends.
3. **Briefs are objects.** Each request creates or updates a BRIEF-n. A new topic parks the
   old one ("Parking the RISE bumper"), and the parked brief comes back as context (brief 13
   asks whether it belongs to the night walk).
4. **Skills are read per brief**, and the step is shown ("Reading 2 skills").
5. **Video is still-first.** A hero still is drawn on Nano Banana Pro with "motion-safe for
   I2V handoff", then the clip.
6. **The approval card is the prompt.** It shows the full prompt, editable, with the frame and
   the model as chips and the price on the Approve button, plus a session-wide "Always allow".
   The prompt on the card is the prompt sent: the brief 1 still came back matching it.
7. **Deny asks why**, with six reasons that map to fixes (prompt, references, model, settings,
   brief, revise). That is a labelled discard signal.
8. **A script before any video spend** for an ad: a timed table of visual and audio, with a
   word count and read time ("9 words. Estimated read: 4 seconds") and ranked alternative
   hooks.
9. **Model questions are answered from a live list**, split by what the person starts from.
10. The cost of thinking is visible and high on Lite: 8-9 credits for some text-only turns.
