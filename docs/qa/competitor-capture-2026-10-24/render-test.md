# Render test: the competitors' clips on their sites and on Phantra (2026-10-24)

Mike: "make the briefs different cost efficient just enough so we can replicate not just the
chat but make sure the models are working with phantra. i want the on site higgsfield runway
clips".

## The question

The test asks two things:

1. **Does Phantra reproduce a competitor's result?** The same prompt, start frame, model and
   length is rendered on their site and on Phantra (through the studio connector, the same
   `fal.generate_from_prompt` / `generate_image_from_prompt` doors as `/studio/video` and
   `/studio/image`). Differences between the two are what our model plumbing adds or loses.
2. **Whose prompt is better?** Vesper's prompt for the same brief is rendered on Phantra, on
   the model Vesper picks (or, when Vesper picks none, on the brief's shared model), and
   judged blind against the other two.

## The briefs: three, each a different kind of work

| # | Brief (sent word for word) | Kind | What it exercises |
|---|---|---|---|
| A | a 10 second clip of a man walking home at night, in the style of Wong Kar-wai | named look, one character | text-to-video vs still-first; a named style |
| B | UGC ad: a girl checks her phone, finds a shift for today, grabs her bag and heads out the door | vertical ad, person + phone + action | 9:16, a phone screen, three beats in one clip |
| C | a jar of honey with a wooden dipper in morning light, then make it move | product still, then a clip | still -> image-to-video, product fidelity, slow motion |

Brief A was captured earlier (`higgsfield.md`, `runway.md`, `invideo.md`). B and C are
captured the same way: tap the first suggestion, else "you decide". invideo is left out of
B and C: it has 12.7 credits left and charges for chat.

## Settings, the same on both sides

- **5 seconds**, where the model takes 5 (else its shortest legal length).
- The lowest resolution both the site and Phantra offer for that model.
- The frame the tool chose.

Changing the length and resolution from a tool's default is recorded; the prompt and model
are never changed.

## Spend caps

| Where | Cap | Notes |
|---|---|---|
| Higgsfield | 300 credits | balance 551.02 at start |
| Runway | 600 credits | balance 3,568 at start |
| Phantra (live, account 1, through the connector and the studio's Video page) | ~4,000 credits (raised from 150: a Phantra credit is about $0.01, so one 15s Seedance clip is ~1,100) | each render quoted first |

Every spend is logged below as it happens. If a render would cross a cap, it is skipped and
its quote is recorded.

## Spend log

| Time (ET) | Where | What | Price | Balance after |
|---|---|---|---|---|
| 14:52 | Runway | B: two presenter stills, GPT Image 2, 9:16 | 40 | 3,528 |
| 14:53 | Higgsfield | B: presenter still, Higgsfield Soul 2.0 | 0.125 | — |
| 14:56 | Higgsfield | B: 8-slot storyboard sheet, GPT Image 2.5, 21:9 | 1.5 | — |
| 14:58 | Higgsfield | B: realism pass on the sheet, Seedream 5.0 Pro, 21:9 2K | 2.5 | — |
| 15:00 | Runway | B: 15s 9:16 Seedance 2, native audio. Asked for 720p instead of the card's 1080p (600 credits); the 1080p card was left unapproved | 450 | 3,078 |
| 14:57 | Phantra | B, Runway replay: Option A still, GPT Image 2, 9:16 (gen:226) | 11 | 5,590 |
| 15:04 | Higgsfield | B: 15s 9:16 Seedance 2.5, 3 references (sheet, character, app UI). Card said 1080p for 240; changed to 720p | 105 | 441.43 (all B steps + chat: 109.6) |
| 15:01 | Phantra | B, Runway replay: 15s Seedance 2, 720p, start frame gen:226, Runway's prompt word for word (connector job 2) | 1,093 | 4,497 |
| 15:03 | Phantra | B, Vesper: 10s Seedance 2, 720p, 9:16, text only, Vesper's prompt (studio Video page: the connector's `generate_video` has no aspect argument) | 729 | 3,768 |
| 15:04 | Higgsfield | C: honey still, GPT Image 2.5, 16:9 | 2.75 | — |
| 15:05 | Runway | C: honey still, GPT Image 2, 16:9 (Gygler kit left out on purpose) | 20 | — |
| 15:05 | Phantra | C, Runway replay: still, GPT Image 2, 16:9 (gen:228) | 11 | 3,757 |
| 15:06 | Phantra | C, Higgsfield replay: still, GPT Image 2.5 Flare, 16:9 (job 4) | 15 | 3,742 |
| 15:07 | Higgsfield | C: 5s 16:9 Seedance 2.5 from its still. Card said 1080p for 80; changed to 720p | 35 | — |
| 15:08 | Runway | C: 6s Seedance 2.5 from its still, native audio. Card said 1080p for 408; asked for 720p (the 1080p card left unapproved). Takes Runway to 690, past the 600 cap set here: Mike asked for the on-site clips | 180 | — |
| 15:08 | Phantra | C, Higgsfield replay: 5s Seedance 2.5, 720p, from gen:229 (job 5). **Higgsfield charged 35 for the same model, length and resolution** | 568 | 3,174 |
| 15:08 | Phantra | C, Runway replay: 6s Seedance 2.5, 720p, from gen:228 (job 6) | 682 | 2,492 |
| 15:09 | Phantra | C, Vesper: plan's image step, GPT Image 2, 16:9 (gen:231; Vesper named no model, so the brief's shared one) | 11 | 2,481 |
| 15:10 | Phantra | C, Vesper: plan's scene step, 5s Seedance 2.5, 720p, from gen:231 (job 8) | 568 | 1,913 |

**Totals:** Phantra 3,688 credits (about $37 at a cent a credit; balance 5,590 → 1,913). Higgsfield 147.35 (551.02 → about 404). Runway 690 (3,568 → 2,878). Brief A was not rendered: once B and C were done, the Phantra cap had no room left for A's replays. B (a person talking to camera, 9:16) and C (a product, still then clip) cover the two kinds of work.

## The clips

All nine are in the blind page, `judge/blind-dailies.html` (built by `judge/clips.py` + `judge/build.py`), published privately at https://claude.ai/artifact/Cxq2EtDCAGMffNSQqRwztK with the clips bundled. Takes are in a fixed shuffled order; "Reveal the slates" shows who, model, size and price. Phantra's are gen:230 (B, Runway replay), the Vesper B clip on the Video page, gen:232, gen:233, gen:234 (C), stills gen:226, 228, 229, 231.

## What the render test showed (before Mike's blind scores)

**The models work through Phantra.** The same prompt and start frame on the same model gave the same clip: Runway's 15s UGC take on Phantra reproduced Runway's own (same room, same script spoken word for word, same gestures and exit), and both honey replays move the way their prompts ask. Nothing in our model plumbing changed what the model did, with three exceptions, all about inputs:

1. **Our GPT Image 2 stills are not the shape they are labelled.** "9:16" comes back 1024×1536 (2:3) and "16:9" 1536×1024 (3:2). Runway's GPT Image 2 gives a true 1080×1920. Seedance then follows the start frame, so the Runway replay came out 3:4 and the honey clips 3:2. GPT Image 2.5 Flare's 16:9 was a true 1360×768. Fix: send GPT Image 2 the exact size (`image_size`) instead of the nearest preset, or crop to the label before the still is filed. Every image-to-video on Phantra inherits this. Fixed on this branch (`fal.named_dims`): 9:16 is sent as 944×1664, 16:9 as 1664×944, every aspect at no more pixels than its price row, so prices are unchanged.
2. **The studio connector's `generate_video` could only make 9:16 from text.** (Corrected 2026-10-24: an earlier draft said it came out in fal's default frame; fal's default here IS 9:16, `fal.DEFAULT_ASPECT`.) A 16:9 or square text clip had to go through the Video page. Fixed on this branch: `aspect` on the tool, checked against the model's legal shapes (refused, never clamped), bound into the quote token, and listed per model by `video_models`; a clip from a start frame takes the picture's shape and refuses an `aspect`.
3. **A competitor's best prompt does not fit our door.** Higgsfield's B (6,487 characters, 8 timed cuts, 3 references: a storyboard sheet, the character and the real Gygler app screens) cannot be replayed: `direct.PROMPT_MAX` is 4,000 and the Video door takes one start frame. Seedance 2.5 on fal takes several reference images; the door should too, and the prompt cap should be the model's, not a house number.

**Price.** For the same model, length and resolution, Higgsfield charged 35 of its credits for a 5s Seedance 2.5 clip at 720p; Phantra charges 568 (about $5.68, $2.37 of it fal's cost). Runway charged 180 for 6s. Higgsfield's 15s UGC clip with three references was 105. The competitors are selling video far below fal's list price (Higgsfield very far below it), so on price per clip Phantra loses every comparison here.

**What the competitor agents did that Vesper does not**, seen only by rendering:

- **Higgsfield checks its own render.** After the UGC clip landed it ran QC on the video, found that she says the brand as "Jiggler" and that the phone close-up shows scrambled text, and offered one re-render with the name spelled phonetically and the real app screen pinned. That is a review step after the spend, on the output, which neither Vesper nor the composer has.
- **Higgsfield pulled real app screens** (a web search) and used them as a reference, so its phone close-up shows Gygler's actual orange UI. Vesper's B shows invented gibberish on the phone. Higgsfield also invented facts the brief never gave ("Orlando, TODAY, nine to five thirty. Twenty-five an hour"), unlabelled.
- **Runway reasons about the kit**: on the honey brief it said the Gygler kit "has nothing to do with a honey jar still life, so I'm leaving it out".
- **Both proposed 1080p by default** and dropped to 720p only when asked (Runway made a second card each time and left the first one waiting; there is no Decline button).
- **Higgsfield's honey clip went out silent** (`generate_audio: false`) with no mention on the card, and its closing summary said "1080p" after the card had been changed to 720p.

**Vesper's own output, on the same models:** B is hands and feet only (its first-choice answer was hands-only), with a gibberish app screen and the person's clothes changing between beats: it reads as b-roll, not a UGC ad, and has no spoken line. C is a sound, simple product move (the dipper lifts, the ribbon falls), though the dipper looks to pass through the jar wall at about 2s. Vesper named no model for either step.

Waiting on: Mike's blind scores from the page.
