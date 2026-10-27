# Overnight 2026-10-27: every door that sends to a model

Mike's ask: "do a full test of it overnight, verify the issues, compare it to top studios and fix
the chat box, image page, video page, brand kit, and all other pages that involve sending to a
models endpoints."

No money was spent. Nothing was rendered live and nothing was written to the live database. Every
fal and Gemini media call was stubbed on a local studio (schema `ovn1027`). The stub logs the exact
body that would have gone out, so every model on the Image and Video pages was quoted, run and
checked against fal's live schema. The fal schemas and prices were read from fal's own pages.

The audit files beside this one hold the evidence, ranked within each area:
- [chat-box.md](chat-box.md): the Create composer and Vesper.
- [image-page.md](image-page.md): `/studio/image` and every place a still is drawn.
- [video-page.md](video-page.md): `/studio/video` and the scene renders.
- [kit-and-other-doors.md](kit-and-other-doors.md): brand kit, effects, talking photo, sheets, QC.
- [competitors.md](competitors.md): Runway, Higgsfield, Krea, Magnific, LTX Studio, invideo, fal.

Where an audit file and this page disagree, this page wins. One audit claim was checked and found
wrong: the PixVerse camera-move price matches fal's page ($0.15 / $0.15 / $0.20 / $0.40 for 5s).

## Fixed on this branch

### Image page and stills
- **FLUX 1.1 Pro, the default still, ignored the shape picked.** We sent `width`/`height`, which
  its schema does not have, so every still came back 4:3 landscape. It now sends `image_size`.
- **Ideogram 4.5 drew 5 of its 10 shapes wrong** (4:5 and 2:3 came out 3:4; 5:4 and 3:2 came out
  4:3; 21:9 came out 16:9). It now sends exact pixel sizes for 9 shapes and does not offer 21:9.
- **Each model offers only the shapes it can draw.** This applies on the page and in the quote,
  which refuses any other shape.
- **Nano Banana Pro on fal refuses prompts under 3 characters**, so the page refuses them first.
  Four models now ask for JPEG output.

### Video page and scene renders
- **Kling 4 ignored its start frame.** The picture went in `image_url`, but Kling 4 reads
  `start_image_url`.
- **Prices brought into line with fal:**
  - LTX 2.3 was under-charged at every resolution. The public table's row went from 87 to 116 cr.
  - Seedance 2 and Seedance 2 Fast gained their 480p price, so the cheaper draft is offered.
- **A scene prompt longer than the model takes is refused before the credit hold**, with a plain
  sentence. Before, the credits were held and fal then answered with a 422. One-clip pricing splits
  the scene when its combined prompt would be too long.
- **The chat's Frame pill is no longer dead.** Every scene used to render 9:16 whatever was picked.
  Now `shot["ratio"]` goes to the model on text and reference renders where the model takes that
  shape (`fal.shot_aspect`), and the keyframes are drawn at that shape too.
- **A start frame that cannot be read is refused.** Before, the clip rendered as text-to-video,
  was charged, and the row noted the dropped frame. This reverses a deliberate older choice
  (`tests/test_fal.py`). The person picked a picture to start from, so a clip without it is not
  what they were shown.

### Chat box (Create)
- **One-clip scenes (#515) broke three things, all fixed:**
  - Assemble and "Edit the cut" answered 409 `not_ready`. Now `clip_slots` uses the shot's one clip.
  - The in-chat Final cut is back for them, with the kit end card, the Library row and Trim.
  - "Add sound pass" and "Cut a vertical version" did nothing. They now run on the cut.
- **"Cut a vertical version" is no longer offered under a scene that is already 9:16.**
- **The Render card said "1 shot" for a 3-shot one-clip scene.** The approve button and the plan
  step now say "3 shots, one clip".
- **A refused price leaves the Render button disabled.**
- **An effect card no longer resets to a fresh Approve when only the wait was lost after the run
  started.** A second click would have paid again.
- **Vesper asks less:**
  - The dial now defaults to Checkpoints. Free steps run, and every credit still waits for a click.
  - The prompt asks a question only when the answer would change what gets made.
  - The "attach a photo" warning no longer fires when the words name a product or character the
    brand kit links, or point at a numbered result (`#3`).

### Brand kit, effects and other doors
- **Effects said "Nothing was charged" after the charge had settled**, when filing the result
  failed. Now the message says the effect was made and charged.
- **Voice, talking-photo, voiceover and music failures were blamed on "the image service".**
  Each now names its own service.
- **Seven Kling effect templates that fal no longer takes were removed** (`day_to_night`,
  `skateskate`, `guardian_spirit`, `pet_moto_rider`, `3d_cartoon_2`, `pet_dance`, `surfsurf`).
  Each would have failed at fal.
- **Seedream 4 edit no longer returns square images.** It sends `image_size: auto_2K`, which keeps
  the first picture's shape.
- **Render QC only expects the kit products that the shot's own words name.** Before, every shot
  was marked down for leaving out products it never mentioned.
- **A free-trial render read from the bucket now reaches the model as its clean original** (the
  `as_image_url` name fallback). The model never sees the watermark.

## Found, not fixed (ranked)

1. **The Create still is not held to the price its card showed.**
   - The card shows the model's base price, but `/api/generate/run` charges at the shape and
     picture count actually sent.
   - The run takes no `expect_credits`. On the Image page the same still is held to its quote.
   - It differs for FLUX.2 with pictures (each reference is an input megapixel), for per-megapixel
     models at wide shapes, and for size-priced models.
   - Fix: the card quotes through `/api/direct/image/quote` with the shape and picture count, and
     the run refuses a price that moved, as on the Image page.
2. **Keyframes are sold for a one-clip scene, but a reference-to-video render does not use them.**
   The person can pay for stills the clip never sees.
3. **Re-approving a rendered one-clip scene renders it again** (chat-box.md C11).
4. **Video page details:**
   - Resolutions are not narrowed when pictures are attached (`ref_resolutions`).
   - Extra pictures are dropped silently on start-frame-only models, and a dropped picture is not
     mentioned in the job's detail.
   - Line breaks in the prompt are folded into spaces.
   - Wan's legal lengths are 2-30s.
   - Grok's $0.01 start-frame charge is not priced.
5. **Image details:**
   - FLUX.2 references are priced at 1 MP each, but fal bills their real size.
   - GPT Image edit input tokens are not priced.
   - Gemini drops the shape when it retries with a smaller config.
   - Ideogram's prompt expansion is on.
   - FLUX.2's note says 9 references, but 8 are sent.
6. **Pricing:** element sheet resolution and price, and Topaz upscale price on vertical clips
   (kit-and-other-doors.md).

## Mike's calls
- **Price.** Credits sell at 2.4x fal's price. Runway's own API is under fal on Seedance 2.5
  (competitors.md §price). The markup is the largest gap with the other studios.
- **`PHANTRA_VESPER_V2=1` on Fly.** The v2 composer layout (the dial, next steps) is behind it.
  I could not read Fly's secrets to check.
- **One live test render** to confirm on real output: one-clip, Kling 4's start frame, and a 16:9
  Frame pick. About 100-300 cr on Seedance 720p. Not run, per "id rather not spend on it".
- **Features the other studios have** (competitors.md):
  - An end frame.
  - Kling `multi_prompt` for one-clip scenes.
  - Re-roll one shot.
  - An audio on/off toggle (Veo is half price without audio).
  - A still count of 1-4.
  - A default brand kit for the account.
  - A credit ceiling on "Approve all".
  - An editable prompt on the step card.
  - Decline with reasons.
