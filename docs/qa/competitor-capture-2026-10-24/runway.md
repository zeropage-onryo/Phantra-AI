# Runway Agent — capture 2026-10-24

app.runwayml.com Agent, on the Personal · Max plan, model "Sonnet 5.5", mode "Ask • Quality".
Each brief ran in a new chat, and nothing was approved. Words are Runway's, copied from the
page.

## Spend log (Runway credits)

Start 3,568; after all five briefs 3,568. **0 spent.** The chat turns cost nothing; spend
happens only on Approve. Every brief's chat showed the account's **Gygler brand kit**, which
the agent attached by itself ("BRAND KIT Gygler View").

## Brief 1: "a coffee cup on a rainy window"

- "Two quick questions above: a still, a video, or both, and the mood you want (cozy and warm,
  moody and cinematic, or soft and minimal). Pick whichever fits and I'll start."
- 1 of 2 "What should I make?": Still image / Short video clip / Both, image then animate it.
  Picked: Still image.
- 2 of 2 "What mood are you after?": Cozy, warm interior light / Moody, cool and cinematic /
  Soft, minimal and airy. Picked: Cozy.
- Card "Generate Image": the prompt, **Aspect Ratio 16:9 · Quality High · Model GPT Image 2 ·
  Credits 20**, then Approve.

> A ceramic coffee cup with a thin curl of steam, sitting on a wooden windowsill, in front of a large window streaked with rain. Raindrops run down the glass, and the grey street outside has dissolved into soft bokeh. A warm amber lamp glows from inside the room and lights the cup's rim and the steam. Cozy, intimate mood, shallow depth of field, 50mm lens at f/1.8, natural photographic look, warm highlights against cool blue-grey rain light.

- Under the card: "The image is ready to run once you approve it. It shows a steaming ceramic
  cup on a wooden sill, rain streaking the glass, and a warm lamp glowing behind it. I'm using
  the highest-quality setting at 16:9."
- The kit was attached but **not** put into this prompt: none of the kit's words are in it.

## Brief 2: "help me make an ad"

- "I've loaded your Gygler brand kit (orange palette, Urbanist type, the 60-second flat
  motion-graphics explainer style), so I'll build on that. A few quick choices will shape the
  ad:"
  - 1 of 3 "Who is this ad speaking to?": Businesses hiring talent / Talent looking for Gygs /
    Both, bridged together
  - 2 of 3 "How long should it be?": 15 seconds / 30 seconds / 60 seconds, full explainer
  - 3 of 3 "Where will it run?": YouTube / web (16:9) / Instagram / TikTok (9:16) / LinkedIn /
    feed (1:1)

  Picked the first of each.
- Card "**Motion Graphic skill**":
  - Sandbox
  - Goal: Gygler 15s ad
  - Model: Sonnet 5.5
  - **Pricing: 3 credits per action · Max Credits 150**
  - Approve

> I've set up your 15-second Gygler ad. It's waiting on your go-ahead before it starts building.
> 0–3s: The hook is white caps on full-bleed orange: "MANAGING TALENT SHOULDN'T FEEL LIKE THIS."
> 3–4.6s: "MEET" followed by the Gygler logo reveal.
> 4.6–12.4s: Three business-side beats on cream, each with a UI card animating on the right. They run "Find the right talent.", then "Book Gygs in seconds.", then "Build your Talent Pool."
> 12.4–15s: The end card with the logo, "Get a Gyg, stay for good." and Gygler.com.
> It's a 16:9, 1080p flat motion graphic in your orange and cream palette, set in Urbanist, using your logo files as supplied. The first version is silent. I can add a music bed and UI sounds afterward if you want them.

What it does:
- **"Help me make an ad" is answered from the brand kit.** It never asks what the product is.
  Its questions are about the brand's own audiences (businesses or talent, from the kit), the
  length and the platform.
- The ad is drawn **in code**, as a motion graphic in a sandbox, not by a video model. The
  card's price is a **budget**: credits per action and a maximum.
- A timed script is shown before Approve: the words on screen, the background, and the kit's
  real tagline and URL.

## Brief 8: "a 10 second clip of a man walking home at night, in the style of Wong Kar-wai"

- No questions. "The central subject (the man) isn't pinned down, so I'll lock the look with a
  start frame first."
- Card "Generate Image": 16:9 · High · GPT Image 2 · 20 credits.

> A lone man in his early 40s, lean, slightly tired eyes, short dark hair, wearing a rumpled charcoal suit jacket over an open-collar white shirt, loosened tie, carrying a briefcase, walking along a narrow rain-slick city side street at night, seen from a low three-quarter front angle through foreground neon haze. Saturated emerald and crimson neon signs reflect on wet asphalt, sodium-orange streetlamps cast pools of light, steam rises from a grate, shallow depth of field, anamorphic lens flares, heavy film grain, smeared practical lights in the foreground, melancholic and intimate, 35mm film look with rich saturated color.

> The opening frame is waiting on your go-ahead.
> The plan: one continuous 10-second take, 16:9. A lean man in a rumpled charcoal suit walks home down a rain-wet side street, drifting through neon haze. The look is step-printed, smeared motion with saturated emerald and crimson against sodium-orange light, grainy 35mm, with only street sound (footsteps, rain, distant traffic).
> Once the frame is approved, I'll show it to you. If you like it, I'll animate it. I'll leave music off the clip unless you want a separate track.

What it does:
- It goes **still-first, and says why**: the subject isn't pinned down.
- The director's name is gone from the still prompt, translated into craft (emerald and
  crimson neon, sodium orange, smeared practicals, 35mm). The step-printing goes into the plan
  for the clip.
- It says the plan for the clip ahead of time: one take, 16:9, sound but no music, and the
  clip only after the person likes the frame.

## Brief 9: "which model is best for a talking head?"

> That brand kit lookup wasn't needed for your question, so ignore it. Here is the answer.
> Best overall for a talking head: Seedance 2.5. Since you've prioritized quality, this is my pick. It handles lip-sync and quoted dialogue with native audio, and it accepts an image reference to lock the speaker's look. It also runs up to 30 seconds in a single take, so longer monologues don't need stitching.
> Alternatives — Kling 3.0 Pro: strong native audio and lip-sync, and good when you want cuts inside one generation (up to 15s). Kling 3.0 Omni Pro: best if you need to lock in a specific person using up to 7 reference images or a first and last frame. Seedance 2.0 Fast or Mini: cheap, quick drafts to test the script and framing before committing to a final. Kling 3.0 Motion Control: if you already have a clip of someone performing the speech and want a different character image to deliver it with the same movement.
> Voice options — For the best-sounding delivery, you can generate the voiceover separately with Eleven v4. I'd only do this if you need precise control over the voice, since it adds a sync step.
> If you want me to make one, tell me: who the speaker is (or attach a photo), what they say, how long it should be and the aspect ratio.

What it does:
- A direct pick, tied to the person's own setting ("Since you've prioritized quality"), then
  alternatives by situation, a cheap model for drafts, and what it needs to make one.

## Brief 13: "3am and the house is awake"

"Once you pick, I'll get started." 1 of 3 "What should I make from "3am and the house is
awake"?":
1. Short atmospheric video clip
2. Still image / poster
3. Narrative short with a story
4. Music or sound piece
5. Gygler on-brand piece

Stopped here.

## Runway patterns

1. **Up to three questions, one at a time** ("1 of 3", numbered chips, Skip or "Skip &
   send"), only when the brief is open. Brief 8 got none; briefs 1, 2 and 13 got 2-3.
2. **The account's brand kit is context on every turn.** It answers "help me make an ad" with
   the kit's product, audiences, palette, type and tagline, and it offers "Gygler on-brand
   piece" as an option for an open brief. It is not put into prompts that aren't for the
   brand (brief 1).
3. **The approval card is the prompt plus every setting**: aspect ratio, quality, model and
   credits. For an agent skill, the card shows a per-action price and a maximum.
4. **Still-first for video when the subject is not pinned down**, and the reason is said.
5. **Model answers depend on the person's settings** (Quality), with a draft model named.
6. Chat is free; only Approve spends.
