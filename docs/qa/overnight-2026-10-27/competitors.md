# How the top AI studios handle Phantra's surfaces (late October 2026)

Research done 2026-10-26 from public pages only: help centres, docs, model pages, pricing
pages and reviews. Nothing was signed into and nothing was generated. It builds on the hands-on
capture of 2026-10-24 (`docs/qa/competitor-capture-2026-10-24/`: `comparison.md`,
`higgsfield.md`, `runway.md`, `invideo.md`, `ltx.md`, `render-test.md`). Where a claim comes from
that capture, it is cited as **[cap]** with the file name.

How to read the markers:
- **(unverified)**: the claim comes from a secondary source, a search snippet, or a page that
  refused the fetch (HTTP 403: help.runwayml.com, magnific.com).
- **(conflict)**: sources disagree; both sides are given.

Studios covered: Runway, Higgsfield, Krea, Magnific (Freepik's AI suite, renamed April 2026),
LTX Studio and invideo, with fal's playground as the raw baseline. I left out Pika and Hailuo.
Neither has a chat agent or a brand kit I could document. Their public pricing comes only
from aggregators that disagree with each other ([krater](https://krater.ai/pricing/hailuo),
[costbench](https://costbench.com/compare/hailuo-ai-vs-pika/)), and Runway already resells
Hailuo 3 and MiniMax H3 through its API (below).

---

## 1. The chat agent

| | Runway Agent | Higgsfield Supercomputer | invideo Agent One | Krea Agent | Magnific Assistant | LTX Studio |
|---|---|---|---|---|---|---|
| Approval setting | "Generation mode": **Ask before generating media** / **Automatically generate**. The help article says Automatically generate is the default ([help](https://help.runwayml.com/hc/en-us/articles/51601639579667-Creating-with-Runway-Agent), snippet, unverified). Our account showed "Ask • Quality" **[cap] runway.md**, possibly a saved choice. | A card says "Approve · N" and offers **Always allow** / Stop / Approve, plus a "Type something else..." redirect **[cap] higgsfield.md**. The guide says the cost is shown and you click Approve before anything is spent ([guide](https://higgsfield.ai/blog/higgsfield-supercomputer-guide), via search). The default is not documented (unverified). | **Always allow is the default.** You can switch to "Ask before generating videos" or "Always ask before generating" ([help](https://help.invideo.io/en/articles/14718313-how-are-credits-charged-in-agent-one)). | Asks for approval "before an expensive step"; there is no documented toggle ([docs](https://www.krea.ai/docs/user-guide/agent/overview)). Integrations have an allow-or-ask setting. | An image-only chat; every message builds on the last ([docs](https://www.magnific.com/ai/docs/ai-assistant), via search). | No agent. Storyboard Builder is paid-only **[cap] ltx.md**. |
| What the card shows | Each step's model, prompt and estimated credits ([workflows help](https://help.runwayml.com/hc/en-us/articles/53645211363475-Building-and-running-Workflows-with-Agent), via search). Ours showed Aspect · Quality · Model · Credits. An agent skill's card shows "3 credits per action · Max Credits 150" **[cap] runway.md**. | The prompt, a model chip, and frame · length · resolution · quality on video. A still shows no frame **[cap]**. | The prompt, model, duration and aspect, **editable before you approve** ([help](https://help.invideo.io/en/articles/14718313-how-are-credits-charged-in-agent-one)). Deny offers six reason chips **[cap] invideo.md**. | Not documented. A "free credits left" pill; a Generations panel shows what a session spent ([credits](https://www.krea.ai/docs/user-guide/agent/plans-and-credits)). | Not documented. | n/a |
| Questions before making | Up to 3, one at a time ("1 of 3"), only on an open brief. None on a specific one **[cap]**. | The same shape (numbered, Skip). A product photo is asked for as an optional upload **[cap]**. | One form with every question **[cap]**. | Reads attached references, links and PDFs before planning ([docs](https://www.krea.ai/docs/user-guide/agent/overview)). | n/a | n/a |
| Model choice | Preference: **Speed / Cost / Quality / Custom**. The default is Quality on desktop and Speed on mobile. It is a weighting, not a rule (help snippet, unverified). | Auto-routes each step. The chat LLM is pickable ([help](https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-supercomputer)). | Lite / Pro / Ultra modes ([help](https://help.invideo.io/en/articles/14718313-how-are-credits-charged-in-agent-one)). | **Effort: Instant / Medium / High / Extra High**, default Auto. Higher effort means more self-review and retries ([docs](https://www.krea.ai/docs/user-guide/agent/overview)). | n/a | n/a |
| Cost of chat turns | Free **[cap]** | Auto turns free; a pinned flagship model charged **[cap]** | Charged: up to 9.1 credits a turn **[cap]**. A per-project credit limit is available ([help](https://help.invideo.io/en/articles/14718313-how-are-credits-charged-in-agent-one)). | Free tier pays 5% of token price; included on paid plans except Opus at Extra High ([credits](https://www.krea.ai/docs/user-guide/agent/plans-and-credits)). | | |
| Checks after the render | n/a | QC on the landed clip (the brand name misspoken, scrambled phone text) and an offer to re-render once **[cap] render-test.md** | | Extra High "checks and retries its own output" ([docs](https://www.krea.ai/docs/user-guide/agent/overview)) | | |

**What Phantra should take**

- **Keep Ask as the default; it is now the cautious outlier.** Runway (per its help article)
  and invideo default to generating automatically. Phantra's `GenerateMode` defaults to `"ask"`
  (`web/src/lib/composer.ts` `loadGenerateMode`), and a clip render always waits. That is the
  right call for a paid studio. The thing to fix is the setting's reach: it is remembered
  **per browser** (localStorage). Move it to the account (`src/assistant_store.py` or
  preferences) so the connector and a second device agree.
- **Add a budget card for multi-step work.** Runway prices an agent skill as "per action · Max
  N" **[cap]**, and invideo has a per-project credit limit. Phantra's `make_plan` "Approve all"
  (`lib/make-plan.ts`) should show the plan's **total ceiling** on the button and refuse a step
  that would pass it. An optional per-project credit cap fits beside it (`src/projects.py`).
- **Make the card editable before Approve.** invideo lets you change the prompt, model,
  duration and aspect on the popup. Phantra's step card (`components/studio/composer/`) should
  allow an inline prompt edit that re-quotes through the same `expect_credits` 409 path as
  `direct-generator.tsx`. A prompt edit is already an "edited" outcome (`src/outcomes.py`).
- **Take the redirect field and the Deny reasons.** Higgsfield's "Type something else..." and
  invideo's six Deny chips **[cap]** should go on Phantra's step card and Render card as a
  Decline with reasons, recorded through `outcomes.record("discard", reason=...)`. Live data has
  only 4 discard events (comparison.md).
- **Model preference as Speed / Cost / Quality.** Runway weights model picks by a stated
  preference. Phantra's "Which model renders" is Auto or one model. Add the preference to the
  Video line (`create-view.tsx`) and pass it to `src/model_menu.py` and the brain as
  `clip_model_pref`. Runway's talking-head answer was tied to it ("Since you've prioritized
  quality") **[cap]**.
- **Check renders after they land.** Higgsfield's QC and Krea's Extra High self-review match
  what `src/render_qc.py` already does (2026-10-25). The missing step is Higgsfield's: offer
  **one** priced re-render with the fix named (a phonetic brand name, a pinned screen), never
  automatically. That offer belongs on the Render card under the QC notes.

---

## 2. The image generator page

| | Model picker | Aspect / size | References / edit | Outputs per run | Price before Generate |
|---|---|---|---|---|---|
| Krea | Opens from the model name. Each entry shows a description, speed (bolts), quality (diamonds) and **approximate compute per generation**, with an **Auto** entry at the top ([docs](https://www.krea.ai/docs/user-guide/features/krea-image)) | Square / portrait / landscape presets; custom on some models | Image prompt: 2 (Krea 1) to 15 (Nano Banana) uploads; style transfer has a strength drag; an Edit hover sends a result to the editor | **Fixed by model: 2 or 4**, shown in the picker | In the picker (units per generation: 2 up to 569) |
| Higgsfield | Model pages per model | 14 aspects on Nano Banana 2 Lite ([page](https://higgsfield.ai/nano-banana-2-lite)) | | **Batch 1-4**, each charged; total shown on Generate ([help](https://higgsfield.ai/creator-hub/help-center/credits/what-uses-my-credits), via search) | "The exact cost is shown on the Generate button before you confirm" ([help](https://higgsfield.ai/creator-hub/help-center/credits-and-usage/how-credits-work)) |
| LTX Gen Space | Chip row: Image · Nano Banana Pro · 1K · 16:9 · **3** **[cap] ltx.md** | Chip | `@Element` in the prompt | Chip (3) | |
| Magnific | Many models; "Custom Styles" (LoRA) for consistency ([custom styles](https://www.magnific.com/ai/custom-styles), via search) | | Brand Kit applies with Magnific One (section 4) | (unverified) | Credits per model, changing often (unverified) |
| fal playground | One model per page | Per-model enum | Per-model fields | `num_images` where the model has it | "Pricing details" line beside Run, in dollars ([e.g.](https://fal.ai/models/bytedance/seedance-2.5/reference-to-video)) |
| **Phantra** `/studio/image` | One menu with a label (`direct-generator.tsx`) | Shape radio per model | Up to the model's `max_refs`; a line says when refs are not sent | **One** | The priced Generate button, re-quoted on every change, 409 if the price moved |

**What Phantra should take**

- **Speed, quality and price in the model menu.** Krea's picker carries bolts, diamonds and an
  approximate cost per entry. Phantra's menu items have `note` and `right` slots
  (`direct-generator.tsx`, the `items` maps). Fill `right` with the model's credits at the
  current pick, and add a speed/quality mark from `src/model_menu.py`. People then choose with
  the price in view, not after picking.
- **A 1-4 count on stills.** Every competitor returns several stills per run (Krea 2-4,
  Higgsfield 1-4, LTX 3), and selection is Phantra's stated bottleneck. Add a count to the image
  pick: N holds, or one hold for N × price. The Generate button shows the total, as on
  Higgsfield. It runs through `src/direct.py` `image_quote` and the `fal.IMAGE_MODELS`
  `num_images` field where the model has one, else N calls. A failed one releases only its
  share.
- **An Auto entry in the image menu**, labelled with what it picked and why. Krea's picker has
  one. The brain already proposes from `src/model_menu.py`; the direct page should show the
  same pick as a default, never hidden.
- **The shape bug stays fixed.** The render test found GPT Image 2 "9:16" coming back 2:3
  **[cap] render-test.md**, fixed in `fal.named_dims`. Keep a test that checks every image
  model's output dimensions against the label, because every image-to-video inherits them.

---

## 3. The video generator page

| | Start / end frame | References and tags | Duration / resolution / audio | Multi-shot in one clip | Price shown |
|---|---|---|---|---|---|
| fal (raw) | Seedance 2.5 i2v: `image_url` plus an optional **`end_image_url`**. Kling 3 Pro: `end_image_url` ([seedance](https://fal.ai/learn/tools/seedance-2-5-workflows), [kling](https://fal.ai/learn/tools/how-to-use-kling-3-0-pro)) | Seedance 2.5 r2v: up to 50 files (30 images, 10 videos, 10 audio), named **`@Image1` / `@Video1` / `@Audio1`** by position. Image and audio refs are free; video refs are billed. Kling 3: `@Element1` with frontal and extra angles, at a higher rate | Seedance 2.5: 4-30 s or `auto`, 480p/720p (the r2v page), `generate_audio` on by default. Kling 4: 720p/1080p, the form defaulting to 1080p and 16:9 ([kling4](https://fal.ai/models/kling/v4/text-to-video)) | **Kling 3 `multi_prompt`**: per-shot prompt and duration (1-15 s each) in one call, one continuous video. **Kling 4 has a "Multi Prompt" add-item field.** Seedance 2.5 has no mode; timed ranges in the prompt "set proportion and pacing, not frame-exact cuts" | "Your request will cost $X per …" beside Run |
| Runway | Seedance 2.5 Keyframe mode: first and last frame alongside references ([help](https://help.runwayml.com/hc/en-us/articles/53542207042323-Creating-with-Seedance-2-5), snippet) | Up to 30 images, 10 videos, 10 audio (same help) | | | Credits on the card **[cap]** |
| Higgsfield | Cinema Studio "Hero Frame First": start and end frames ([help](https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-cinema-studio), via search) | Up to 50, tagged "@Image 1" in the prompt ([blog](https://higgsfield.ai/blog/seedance-2-5-on-higgsfield-2026)) | 480p/720p/1080p, 9:16 to 21:9, audio in the same pass; selectors for era, genre, hex palette lock, lighting, lens, emotion, physics | **"Montage cuts and pacing"**: set the number of shots and the cut speed; **"Shot re-generate" re-rolls one shot in a sequence** (same blog) | On the Generate button |
| Magnific (Kling 3.0) | First and end frame (API docs, via search) | Up to 3 character, product or image refs; O1 up to 7 (unverified, 403) | 3-15 s | Up to 6 scenes (unverified) | Credits per second: 70 / 90, or 105 / 140 with audio (unverified) |
| LTX | | `@Element` names reusable characters, products, logos and fonts; a storyboard pulls in matching Elements automatically ([help](https://help.ltx.io/hc/en-us/articles/33578393195922-Introduction-to-Elements)) | | Storyboard = script → scenes → shots ([blog](https://ltx.studio/blog/top-ltx-studio-features), via search) | |
| **Phantra** `/studio/video` | **Start frame only.** `end_image_url` is not wired (`src/fal.py` comment on `seedance2.5`) | `fal.REF2V`: Seedance 2.5 up to 30, Seedance 2 up to 9, Kling 4 up to 10, Grok up to 7, with per-model tags (`@Image{n}`, `<IMAGE_{n}>`) | Length, resolution, frame. **No audio toggle.** Veo is always priced at the audio rate ($0.40/s; $0.20/s without, per the `veo3.1` row) | A scene's timed shots go into ONE clip when they fit (`timeline.one_clip_prompt`). **Kling 4 `multi_prompt` is "not sent"** (the `SLOTS["kling4"]` comment) | The priced Generate button |

**What Phantra should take**

- **Wire `end_image_url` (first and last frame).** Runway, Higgsfield, Magnific and fal all
  offer it, and Phantra's Seedance 2.5 row says outright it is not wired. Add an "End frame"
  slot in `direct-generator.tsx` for models that take it (a new `end_image_field` on the
  `fal.VIDEO_MODELS` row), bound into the quote. On a scene, it lets shot N's still end shot
  N-1 (`scene_chain`).
- **Send Kling's `multi_prompt` for one-clip scenes on Kling.** `timeline.renders_as_one`
  already plans per-shot windows. On Kling 4 and 3, send them as `multi_prompt` (prompt plus
  duration per shot) instead of one long cut-list prompt. That is the model's own frame-exact
  cut, and fal says Seedance's timed text only sets proportion. Keep the cut-list prompt for
  Seedance. Check fal's Kling 4 schema for field names and bounds first; the shot-count limit
  is unverified.
- **Re-roll one shot of a one-clip scene.** Higgsfield's "Shot re-generate" re-rolls a single
  shot inside a sequence. Phantra's one-clip render puts the whole cut on one shot, so a bad
  beat means re-rendering everything. Offer "Re-render shot 2 only" on the Render card: a split
  render of that window, priced, cut into the joined file by `cut/render.py`. The splitter
  already exists for long scenes.
- **An audio switch, priced both ways.** fal's Kling 3 drops a third of the price without audio
  ($0.112 vs $0.168/s), and Veo halves ($0.20 vs $0.40). Runway's API lists both rates
  ([pricing](https://docs.dev.runwayml.com/guides/pricing)). Phantra always prices and sends
  audio. Add "Sound: on/off" to the video pick where the row has a no-audio price. The
  render-test found Higgsfield turning audio off without saying so **[cap]**, so the card must
  show the state.
- **A draft tier wherever one exists.** Runway's API sells `seedance2_mini` (720p, 15 cr/s) and
  `seedance2_fast`; invideo lists "Seedance 2.5 Draft" ([invideo](https://invideo.io/help/billing/video-model-pricing/)).
  Phantra has `drafts.py`. Point the draft at the cheapest row of the same family (Seedance 2.5
  480p today) and show it on the card as "Draft · N credits" next to the full price.
- **Raise the prompt cap to the model's.** It is now per model (`fal.PROMPT_MAX`, as the render
  test asked). Make sure Seedance 2.5's cap fits a Higgsfield-length shot list (6,487
  characters **[cap] render-test.md**).

---

## 4. Brand kit / brand context

| | What a kit holds | How it is built | How it reaches a generation | Check against the kit |
|---|---|---|---|---|
| Runway | Logos, colours, fonts, backgrounds ([help](https://help.runwayml.com/hc/en-us/articles/47057921993491-Brand-Kits-for-Enterprises), snippet, unverified) | | Toggled on in a **Brand tab below the composer**, then guides every generation in the session; also in Apps and Tool Mode (same). The agent attaches the account kit by itself and leaves it out when unrelated ("nothing to do with a honey jar") **[cap] runway.md, render-test.md** | |
| Magnific | Colour palette, imagery style, tone of voice, typography rules ([docs](https://www.magnific.com/ai/docs/brand-kit), via search; 403) | **Reads your sources and proposes the kit**; test images and your feedback become part of it | Library → Brand kit → pick where it applies: a Space, the Image Generator (with Magnific One), Design, or the agent | A post-check for style, colour, type and logo use in Final mode (secondary source, unverified) |
| Krea | Logo, palette, type references, packaging, product photos, approved images, rules for the wordmark and tone, the audience and placement ([branding](https://www.krea.ai/krea-agent/branding)) | Upload, **or point at a website and it writes a brand brief** | Carried from step to step; stored in a shared Workspace Context for the team | Left to the user ("check logos, type, and colors against the originals") |
| LTX | Logos, typography, characters, products, styles as Elements ([blog](https://ltx.studio/blog/introducing-brand-kit-in-ltx-studio), via search) | Admin-managed, Enterprise only | `@` names in prompts; the storyboard pulls them in automatically | |
| **Phantra** | Palette, fonts, logo, linked products and characters with aliases and photos (`src/brand_kits.py`) | Kit import (Gygler kit 1) | Through a project's pick, or "Kit: none ▾" on a no-project chat; a named product becomes a reference (`api._kit_refs`, `brand_kits.part_refs`); `make_screen` draws UI in code | `render_qc` checks the brand said, readable words and product shape |

**What Phantra should take**

- **An account default kit.** Runway attaches the account kit to every chat and lets the agent
  judge its relevance. Its "help me make an ad" was answered from the kit **[cap]**, which beat
  every other tool. Phantra's kit needs a project or a manual pick. Add "default kit" on the
  account (`src/brand_kits.py`); the no-project picker (`create-view.tsx`) starts on it. Tell
  Vesper in `prompts/creative_guide_kit.txt` to say aloud when it leaves the kit out (Runway's
  honey line).
- **Build a kit from a URL.** Krea and Magnific both turn a website into a kit or brief.
  Phantra already fetches pages (`src/linkrefs.py`, product facts as quoted data). Add a "Make a
  kit from this site" door that proposes palette, fonts, logo and tagline as a **kit-change
  card** (`src/kit_changes.py`'s Apply), never written without the click.
- **Tone and claims rules in the kit.** Magnific's kit holds tone of voice; Krea's holds
  wordmark and tone rules. Add `voice` and `never_say` fields (claims that must not appear) to
  the kit and feed them to the scene writer and `render_qc`. That guards against Higgsfield's
  invented "200MG CAFFEINE" **[cap] higgsfield.md**.
- **Name the kit check on the card.** `render_qc` already does what Magnific markets as a
  post-check. Say so on the Render card ("Checked against Gygler kit: 1 note") so the check is
  visible as a feature.

---

## 5. Price per clip

Phantra: a credit is 1¢ on a plan (`docs/BILLING.md`: "1 credit = 1¢ of charge on a plan; a
render = provider estimate × 2.4, rounded up, floor 10"). `src/pricing.py`: `MARKUP = "2.4"`,
`CREDIT_FLOOR = 10`. Top-ups are dearer, at 1.33¢ a credit (BILLING.md). Phantra prices below
are computed from `fal.VIDEO_MODELS` as ceil(USD × 2.4 × 100). Veo has no 5 s length (4/6/8)
and LTX 2.3's shortest is 6 s, so those fit up.

The dollar value of a competitor credit depends on the plan:
- Runway web: Standard $15 / 625 = 2.4¢; Pro $35 / 2,250 = 1.56¢; Max $95 / 9,500 = 1.0¢
  ([pricing](https://runway.com/pricing)). Runway API: 1¢ ([docs](https://docs.dev.runwayml.com/guides/pricing)).
- Higgsfield: 3.3¢-7.0¢ ([Krea's analysis](https://www.krea.ai/blog/higgsfield-pricing-explained-2026-unlimited-credits-and-real-monthly-costs), plans captured 2026-08-31).

**Seedance 2.5, 720p, 10 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $0.473/s ([fal](https://fal.ai/learn/tools/seedance-2-5-workflows)) | **$4.73** |
| Runway API | 30 cr/s, 80-credit minimum ([docs](https://docs.dev.runwayml.com/guides/pricing)) | **$3.00** |
| Runway web | 30 cr/s (180 charged for 6 s **[cap]**) | $3.00 (Max) to $7.20 (Standard) |
| Higgsfield | 70 credits ([blog](https://higgsfield.ai/blog/seedance-2-5-on-higgsfield-2026)) (conflict: another Higgsfield post says 56 for 8 s, [pricing blog](https://higgsfield.ai/blog/seedance-2-5-pricing-2026); we were charged 35 for 5 s **[cap]**) | $2.31-$4.93 |
| invideo | 6.10-1,962 credits across 4-30 s and 480p-4k; no per-point price published ([invideo](https://invideo.io/help/billing/video-model-pricing/)) | unknown |
| **Phantra** | 1,136 credits | **$11.36** |

**Seedance 2.5, 1080p, 10 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $1.164/s | $11.64 |
| Runway API | 68 cr/s | $6.80 |
| Higgsfield | 120 credits (blog) (conflict: 128 for 8 s, pricing blog) | $3.96-$8.45 |
| **Phantra** | 2,794 credits | **$27.94** |

**Seedance 2.0, 720p, 10 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $0.3034/s | $3.03 |
| Runway API | 30 cr/s | $3.00 |
| Higgsfield | ~45 for 5 s (Krea's analysis) | ~$3-6 |
| **Phantra** | 729 credits | **$7.29** |

**Kling 4.0, 720p, 10 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $0.157/s ([fal](https://fal.ai/models/kling/v4/text-to-video)) | $1.57 |
| Runway API | 15.7 cr/s list, **12.56 cr/s** at 20% off to Nov 30 | $1.26 |
| invideo | 22.61 credits for 3 s at the cheapest point | unknown |
| **Phantra** | 377 credits | **$3.77** |

**Kling 4.0, 1080p, 5 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $0.235/s | $1.18 |
| Runway API | 18.8 cr/s promo (23.5 list) | $0.94 |
| Runway web | 118 credits per 5 s (89 with the promo) ([pricing](https://runway.com/pricing)) | $1.18-$2.83 |
| **Phantra** | 282 credits | **$2.82** |

**Kling 3.0 (Phantra's row is Turbo Pro), 10 s**

| Where | Price | In dollars |
|---|---|---|
| fal Kling 3 Pro | $0.168/s with audio, $0.112 without ([fal](https://fal.ai/learn/tools/how-to-use-kling-3-0-pro)); Phantra's row is v3 turbo pro at $0.14 | $1.40-$1.68 |
| Runway API | `kling3.0_pro` 17 cr/s with audio, 12 without | $1.20-$1.70 |
| Higgsfield | 20 credits at 720p, 25 at 1080p (Krea's analysis); "unlimited" for 7 days on Plus | ~$0.66-$1.76 |
| Magnific | 105-140 cr/s with audio (unverified) | ~$1.05-$1.40 at about 0.1¢ a credit (unverified) |
| **Phantra** (turbo pro, 1080p) | 336 credits | **$3.36** |

**Veo 3.1 with audio, 8 s**

| Where | Price | In dollars |
|---|---|---|
| fal list | $0.40/s | $3.20 |
| Runway API | 40 cr/s (20 without audio) | $3.20 |
| invideo | 32-192 credits | unknown |
| **Phantra** | 768 credits | **$7.68** |

**What the numbers say**

- **Runway's API sells several models below fal's list price.** Seedance 2.5 720p costs $0.30/s
  against fal's $0.473, and 1080p $0.68 against $1.164. Kling 4 is 20% under fal until Nov 30.
  Veo and Wan match fal exactly. Higgsfield's consumer prices sit at or below fal's for most
  plans. Phantra, at 2.4 × fal, is **2-4× the competitor price** on every comparable row. The
  render test reached the same verdict **[cap]**.
- **What Phantra should take:**
  - **(a) Price check.** Add Runway's API as a second source for the models it undercuts. It
    sells at 1¢ a credit with no plan; this is the one finding that changes the margin. It
    breaks "fal is the only video renderer" (`providers.VIDEO_PROVIDERS`), so it is **Mike's
    call**. It would need its own receipt and recovery like `src/fal_requests.py`.
  - **(b) Without a new provider**, lower `MARKUP` on video only, or by band
    (`providers.BANDS`), and keep 2.4 on stills and effects, where the absolute numbers are
    small.
  - **(c) Show the cost as competitors do: on the button, per clip.** Phantra already does.
    The gap is price, not display.
- **Minimums.** Runway sets per-model floors (an 80-credit minimum on Seedance 2.5). Phantra's
  flat `CREDIT_FLOOR = 10` is fine.

---

## 6. Failures and refusals

| | What happens |
|---|---|
| Higgsfield | A failed generation is refunded automatically "within a few minutes", **but "specific models might not refund"**. A "Refunded" entry appears under Manage Account → Usage ([help](https://higgsfield.ai/creator-hub/help-center/credits-and-usage/how-credits-work)). An NSFW block is refunded in most cases; the advice is to rephrase, swap the reference or try another model ([help](https://higgsfield.ai/creator-hub/help-center/troubleshooting/content-flagged-as-nsfw), via search). |
| Runway | An error returns credits automatically; a completed but bad output is billable; cancelling a stuck job reportedly does not refund (third-party, [seedance.tv](https://www.seedance.tv/blog/runway-failed-generation-credits-refund), unverified). |
| Krea | Most failures are retried automatically. When compute runs out, the agent halts before the next billable turn and keeps the draft ([credits](https://www.krea.ai/docs/user-guide/agent/plans-and-credits)). |
| Phantra | The hold is taken before submit and released on any failure; fal's own "no" releases; a cancel lets fal's answer decide (`src/charge.py`, `src/fal_requests.py`). Failures are said in plain words, "Nothing was charged." (`src/failures.py`). |

**What Phantra should take**

- **Already ahead on the rule.** Show it the way Higgsfield does: a "Released" line in Settings →
  Usage and in the connector's `credit_history`, against the job, so a person can see the hold
  came back.
- **On a provider safety refusal, say which of three fixes applies** (rephrase / swap the
  reference / try another model) and offer the model switch as a button in `src/failures.py`
  copy. Higgsfield gives the same three, but only in a help article.

---

## Sources not reached

help.runwayml.com and magnific.com answered 403 to the fetch. Their claims above come from
search snippets and are marked. The Runway "Automatically generate is the default" claim
contradicts what our account showed (Ask), which may have been a saved choice. Recheck it in
the app before acting on it.
