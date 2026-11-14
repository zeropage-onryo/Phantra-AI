# 06a — Competitors: Higgsfield, Runway, LTX Studio (2026-11-02)

Agent E. Signed-out only: no account was created, no sign-up or email form was submitted, no
terms were accepted, nothing was generated, no priced button was clicked, and the Higgsfield MCP
connected in this session was **not called** (its public docs were read instead). Browser work was
headless Playwright (Chromium headless shell, desktop Chrome UA at 1440×900, iPhone UA at
390×844 @2x). Where a cookie banner had to be cleared, the most privacy-preserving button was used
(Higgsfield: "Reject Advertising Cookies"); elsewhere it was left on screen. None of the three
sites blocked headless Playwright.

Update to `docs/COMPETITIVE_LANDSCAPE.md` (7 Sep 2026), not a repeat of it. The two biggest
changes since September: **Runway now has an agent that shows a credit price and waits for
Approve**, and **Runway Ads publishes to Meta / Google / TikTok ad accounts** (GA 27 Oct 2026).
Phantra's "nothing spends without a price you saw" is no longer unique in the studio UI; it is
still unique on the MCP side (see §5).

Screenshots: `docs/qa/2026-11-02/screens/competitors/{higgsfield,runway,ltx,phantra-baseline}/`.
Raw crawl data (JSON + page text dumps) is in the session scratchpad, not committed.

---

## 1. Rubric (1 = weak, 5 = best in class)

"Clicks to first generation" is estimated from the public flow up to the auth wall plus public
docs and reviews, because no account was made. Everything marked *measured* was measured today.

| Criterion | Higgsfield | Runway | LTX Studio |
|---|---|---|---|
| First-screen clarity | **2** — 27 top-nav links (Explore, Image, Video, Audio, MCP, API, Genjutsu, Content Factory, Playable, AI Influencer, Academy, Katana, …); hero is three promo tiles, no one-line value proposition; the cookie sheet covers the right third (`higgsfield/home-1440.png`). Mobile redirects `/` to the `/explore` feed (`home-390.png`). | **3** — marketing home says "Intelligent tools for scaling content and teams" (vague, enterprise-first), but "Try Runway" lands in the real app with a prompt box (`runway/home-1440.png`, `guest-app-1440.png`). | **4** — one headline ("Video creation for filmmakers, advertisers, and creative teams"), one START NOW (`ltx/home-1440.png`). |
| Clicks to first generation (est.) | **4** — "Sign up" (1 click) opens a modal: Google / Apple / Microsoft / email (`higgsfield/signup-wall-1440.png`). The generator pages are browsable signed out with a model preselected (`models-video-1440.png`, `effects-1440.png` shows "Use free gen"). Est. 4–5 clicks after OAuth. | **3** — best pre-auth experience (guest workspace, 1 click), auth wall at click 2 (`runway/signup-wall-1440.png`: email, Google, Apple, SSO). After sign-up a reviewer hit 3 sign-up questions, an Upgrade-to-Pro wall, then a non-dismissable "What best describes you?" modal; the free plan made an image but refused video ([marcandrews, free plan](https://marcandrews.com/runway-free-plan-2026-what-it-actually-makes/)). | **2** — START NOW goes to a 4-step onboarding quiz ("What's your inference stack?" → inference → hardware → access) **before** any auth (`ltx/onboarding-quiz-1440.png`); "Login" reaches the wall in 1 click (`ltx/login-wall-1440.png`). |
| Model catalog breadth | **5** — video: Seedance 2.5/2.0/1.5, Kling 4.0/3.0/2.x + Motion Control, Veo 3.1/3, Wan 2.x/3.0, Hailuo, Sora 2, Grok, own DoP; image: Nano Banana Pro/2, GPT Image 2.5, Seedream 5, FLUX.2, Ideogram 4.5, own Soul; audio, lipsync studio, voice clone/dubbing via MCP ([pricing table](https://higgsfield.ai/pricing), [MCP help](https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent)). | **5** — Dev catalog lists 24 image→video, 23 text→video, 12 video→video, 22 text→image, 4 TTS, music, 3 sound-effect, dubbing, speech→speech, upscale, SDR→HDR (`runway/models-1440.png`, [dev.runwayml.com/models](https://dev.runwayml.com/models)); own Gen-4.5, Aleph 2.0, Act-Two. | **3** — LTX-2.5/2.3, Veo 3.1, Kling 2.6/3.0, Seedance 2.0, Nano Banana Pro/2, FLUX.2 Pro, GPT Images 2.0, Z-Image; audio-to-video; dubbing on the compare table; no music or voice line found ([pricing](https://ltx.io/studio/pricing)). |
| Effects & presets | **5** — `/apps`: ~40 one-click apps in 8 groups (Professional, Enhance & Style, Face & Identity, Video Editing, Ads & Products, Games, Extras, Trending) incl. Virality Predictor, Angles 2.0, "Shots: 9 unique shots from one image", Relight, Click to Ad, Bullet Time product spin (`higgsfield/apps-1440.png`); `/effects/use` effect page takes Character / Location / Products slots. | **3** — Apps (Product Reshoot, Ad Localization, Product Shot Video Builder, Multi-Shot Video, Slide Maker, Edit Studio) and Workflow templates (`runway/guest-app-1440.png`, `workflows-1440.png`). | **2** — preset visual styles, IC-LoRAs (relight, clean plate) promoted from the community; no effects gallery found ([ltx.io/studio](https://ltx.io/studio)). |
| Asset library & pickers | **4** (docs) — Assets, Soul characters, named reference Elements usable several per prompt; MCP results land in Assets tagged by source ([MCP help](https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent)). | **4** (docs) — Projects "organize Sessions, Workflows and Assets"; Characters; Brand Kits; projects capped 3 / 5 / 10 by plan ([pricing](https://runway.com/pricing)). | **4** (docs) — Elements for characters, objects, locations; logos and fonts saved as Elements ([release notes via search](https://ltx.studio/release-notes)). |
| Editor / timeline | **2** — "Edit" is layer/inpaint image editing; Canvas; an After Effects plugin; no NLE timeline found. | **4** — "Edit in Timeline" chip under the prompt box (`guest-app-1440.png`); Aleph 2.0 edits by keyframe; plugins for Premiere Pro, After Effects, Resolve. | **4** — Dynamic Storyboard → Timeline Editor → Sound Design on the studio page; "Video Editor Upgrades" in the 15 Apr 2026 release notes. |
| Agent / chat assistance | **4** — "Supercomputer" agent (GPT-6 Astra); on mobile `/ai/video` redirects to `/start/agent` (`models-video-390.png`); MCP skills (Ad Strategist, Hook Multiplier, Product Review UGC). | **5** — Runway Agent: "Review the plan, then approve or edit it… before anything generates", Brand Kits, Workflows, team Skills, diagnose under-performing creative ([runway.com/product/agent](https://runway.com/product/agent)); a reviewer saw a credit-cost card with Approve (20 credits) and the balance drop by exactly that ([marcandrews, credits](https://marcandrews.com/runway-credits-explained/)). | **2** — script / concept / image / video "starting points" generate a storyboard; no conversational agent found. |
| Brand kit / ads tooling | **4** — Ads Studio, Marketing Studio, Click to Ad from a product link, Virality Predictor, Hook Multiplier; brand kit not shown signed out. | **5** — 1 Brand Kit (Pro) / 3 (Max); Runway Ads: connect ad accounts, rank ads against a goal, make on-brand variants of winners, team approval, publish ([Runway Ads GA, 27 Oct 2026](https://runway.com/news/company-news/runway-ads)). | **3** — Ad Generator, Pitch Decks; Brand Kit is Enterprise-only ([pricing](https://ltx.io/studio/pricing)). |
| Mobile web (390×844) | **3** — no horizontal scroll (scrollWidth 390), app-shell feed, but the cookie sheet covers ~55% of the first screen and the home makes **776 requests / 15.6 MB** (`higgsfield/home-390.png`). | **4** — no horizontal scroll, 3.1 MB home, smart banner to native iOS/Android apps (`runway/home-390.png`, `pricing-390.png`). | **3** — no horizontal scroll; header CTA on mobile is BOOK A DEMO, cookie bar has only "OK" (`ltx/pricing-390.png`); 12.4 MB home. |
| Pricing clarity & credit model | **2** — "Unlimited" headline means 7-day unlimited on Plus/Ultra and is excluded from MCP/CLI, Canvas and Supercomputer (page footnote); the first load showed annual prices ("/mo billed yearly"); per-model table uses "~" estimates; a plan-finder quiz helps (`pricing-1440.png`, `pricing-monthly-1440.png`). | **4** — each plan translates credits into outputs ("625 credits = 52s of Gen-4.5"), per-model credit table, FAQ on rollover and top-ups (min 1,000, never expire) (`runway/pricing-1440.png`). | **3** — plain tiers, but no per-model credit cost on the pricing page; refunds only within 14 days and under 1,200 credits; reviewer: 6-shot storyboard used 2,610 credits "with no usage breakdown" ([Trustpilot](https://www.trustpilot.com/review/ltx.studio)). |
| Speed / page weight (*measured*, §3) | **2** — heaviest JS (3.8–4.2 MB desktop), 455–801 requests, pricing LCP 3.6 s desktop / 4.2 s mobile. | **3** — fast LCP (0.43–0.64 s) but 21.4 MB desktop home, 13.2 MB pricing (10 MB of images). | **4** — 3.6 MB pricing, LCP ≤0.78 s everywhere; `load` 3–4 s from third-party tags. |
| API / MCP / integrations | **5** — MCP for Claude, ChatGPT (plugin), Cursor; CLI + `npx skills add` for Claude Code; API console; AE plugin; Chrome reference extension; Telegram tab (`higgsfield.ai/mcp`). Paid plan required. | **5** — MCP for Claude, ChatGPT (plugin), Grok, Cursor, Replit with 19 copyable example prompts ([runway.com/mcp](https://runway.com/mcp)); Dev API + model router; Premiere/AE/Resolve plugins; iOS/Android. | **4** — API, open weights (HF, GitHub), ComfyUI, LTX Desktop, LoRA trainer; no MCP found. |
| Social publishing | **2** — no organic publishing documented publicly. (Its MCP's tool list, as surfaced by name in this session and not called, includes `tiktok_connect` / `tiktok_prepare_publish`; unverified.) | **4** — Runway Ads publishes **paid** ads to Meta, Google, TikTok after a team approval; no organic posting/calendar found. | **1** — none found. |
| **Total (of 65)** | **44** | **52** | **39** |

Phantra for reference (not scored by this agent; measured only): home 5.4 MB / 64 requests /
0.46 MB JS, pricing 0.65 MB / 31 requests (§3).

---

## 2. Per-competitor pages

### Higgsfield (higgsfield.ai)

Trustpilot 4.0 on 5,262 reviews, 19% one-star; Oct 16 – Nov 2 complaints: refunds refused
(7-day window), charges after cancel, credits draining, "unlimited" free gens queued 4–5 h, upgrade
pop-ups ([Trustpilot](https://www.trustpilot.com/review/higgsfield.ai)).

**Steal this**
1. **An apps gallery named by outcome, not by model.** `/apps` sells "9 unique shots from one
   image", "Relight", "Click to Ad: product link → UGC ad", "Bullet Time" product spin, "Virality
   Predictor" (`higgsfield/apps-1440.png`). Phantra's `/effects` gallery is the same capability
   (`src/effects.py` rows) grouped by engine; regroup the gallery by job (Ads & products, Fix a
   photo, Camera, Sound) and name tiles by result.
2. **Plan finder on the pricing page.** "Not sure which plan?" asks what you make (product photos,
   cinematic, UGC, MCP…) and how many per month, then recommends a tier with "820 of 1,200
   credits" expected use (`pricing-monthly-1440.png`). Cheap to add from `pricing.json`.
3. **Credits translated into outputs on every plan card** ("1,200 credits = 600 Nano Banana Pro /
   80 Seedance 2.5 videos"). Phantra's cards show credits only.
4. **One MCP page with a tab per client** (ChatGPT, Claude, Claude Code, Telegram, CLI) and a
   copy-prompt card per skill ("Hook Multiplier", "Ad Recreator", "Product review UGC")
   ([higgsfield.ai/mcp](https://higgsfield.ai/mcp)). Phantra's `/connector` explains setup;
   recipe cards with "Copy prompt" would sell the plugins' skills.
5. **CLI + skills for coding agents**: Claude Code sets itself up with `npm i -g @higgsfield/cli`
   and `npx skills add higgsfield-ai/skills` ([help](https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent)).
   Phantra's stdio server needs `ops/register-claude-desktop.command`; a one-line installer for
   Claude Code would match.

**Avoid this**
- **"Unlimited" that is 7 days and web-only.** The pricing page footnote excludes unlimited and
  free gens from MCP/CLI, Canvas and Supercomputer; the plan cards say "Unlimited models for 7
  days". This is the top Trustpilot theme.
- **Discount pressure on every page**: "Pricing 30% OFF" badge in the nav, "Sign up and get your
  extra discount" hero on home, pricing and the video tool (`home-1440.png`, `pricing-1440.png`).
- **Pricing loaded in the annual view** on first visit (text dump: "/mo billed yearly"); the monthly
  price is one toggle away.
- **27 top-level nav items** and a 25.6 MB / 472-request home.
- **No spend gate on MCP.** The help page tells the user to say "Before generating anything, tell
  me the credit cost and wait for my confirmation" — the gate is a prompt, not the product.

**Phantra has, they don't (on public pages)**
- A priced quote and single-use token before **every** MCP spend (`quote` → `approve`), and a
  Claude listing that never spends; Higgsfield's MCP deducts credits on any call.
- Projects with a brief, look and memory; scenes held to reference photos (the reference gate).
- A timeline editor with an agent whose edits are proposals; OTIO export.
- Organic publishing + calendar (Instagram, Discord, Reddit, LinkedIn, X, YouTube).
- A free trial whose watermark is lifted from everything already made on payment.

### Runway (runway.com, app.runwayml.com)

Trustpilot 1.1 on 382 reviews (unclaimed profile), 93% one-star; late-Oct complaints: credit
cost, prompts not followed, a "unlimited" Topaz upscale charged 30 credits, moderation false
flags ([Trustpilot](https://www.trustpilot.com/review/runwayml.com)).

**Steal this**
1. **A signed-out guest workspace.** "Try Runway" opens `app.runwayml.com/.../teams/guest/...`:
   the real composer ("What will you create today?"), Reference / Sketch slots, model chips,
   "Edit in Timeline", "Try MCP", use-case tiles (Make video ad, Reshoot your product, A/B
   variants), apps list. Sign-up is asked for only at the second click
   (`runway/guest-app-1440.png` → `signup-wall-1440.png`). Phantra's composer + front page could
   render signed out the same way and ask for sign-in on Send.
2. **Ads loop from real performance**: "Making an ad? Connect your ad accounts to build on what's
   winning" sits above the prompt box; Runway Ads ranks ads against a workspace goal, makes
   on-brand variants of winners and publishes after a teammate approves
   ([Runway Ads](https://runway.com/news/company-news/runway-ads)). Phantra has the parts (Ad
   Studio, brand kits, `outcomes.record`, the publish worker); it lacks ad-account metrics in.
3. **"Nothing runs without you" as the headline of the agent page**
   ([product/agent](https://runway.com/product/agent)). Phantra built this first (priced cards,
   quote tokens) and does not lead with it; Runway now does.
4. **Plan card says what the credits buy** ("625 credits = 52s of Gen-4.5, 104s of Gen-4 Turbo,
   or 78 Gen-4 Images") plus a per-model table and a rollover FAQ (`runway/pricing-1440.png`).
5. **Example-prompt library on the MCP page** (19 examples, filter by Product ads / Animated
   stories / UGC / From a link, "Try in ChatGPT" + "Copy prompt") ([runway.com/mcp](https://runway.com/mcp)).

**Avoid this**
- **Implied cookie consent.** After "Try Runway" the app URL carried
  `CookieConsent={…marketing:true,method:'implied'…}`; no banner was shown in the US session
  (`runway/home-1440.png`). Phantra should keep explicit consent.
- **Onboarding walls after sign-up**: three questions, an Upgrade-to-Pro wall, then a blocking
  "What best describes you?" modal ([marcandrews](https://marcandrews.com/runway-free-plan-2026-what-it-actually-makes/)).
- **A free plan that cannot make video** while the site sells video; it showed 500 credits at
  sign-up vs 125 on the pricing page in the same review.
- **Hard project caps per plan** (3 / 5 / 10 projects). Phantra's plan table (`pricing.json`) has no project cap; keep it that way.
- **Heavy marketing pages**: 21.4 MB home and 13.2 MB pricing on desktop, ~10 MB of each is images.

**Phantra has, they don't (on public pages)**
- A quote before every spend on the MCP door too; Runway's MCP bills credits "just as the app
  does" with no documented approval step ([help center](https://help.runwayml.com/hc/en-us/articles/51931843164691-Connecting-to-Runway-MCP)).
- A Claude listing that writes and prices but never generates.
- The reference gate and element reference sheets (five-panel character sheet).
- **Organic** social publishing and a calendar; Runway Ads is paid placements only.
- Per-clip render QC notes under the Render card.
- Projects with brief / look / memory and no per-plan project cap in `pricing.json`.

### LTX Studio (ltx.io/studio, app.ltx.studio)

Trustpilot 1.6 on 82 reviews, 87% one-star; Aug–Oct complaints: charges after cancel, refunds
refused under the 1,200-credit rule, characters drifting mid-story, no credit breakdown
([Trustpilot](https://www.trustpilot.com/review/ltx.studio)).

**Steal this**
1. **"Choose your starting point" on the home page**: From a Script / With a Concept / From an
   Image / From a Video, each one line ([ltx.io/studio](https://ltx.io/studio)). Phantra's front
   page tiles fill the box; four entry doors would explain the product in one row.
2. **Storyboard → timeline → sound as one named pipeline** ("From concept to final cut").
   Phantra has every step (scene, keyframes, Render card, Final cut, editor); it is not drawn as
   a pipeline anywhere a visitor sees.
3. **Logos and fonts as Elements** (release notes, Jan 2026): brand assets live in the same picker
   as characters and products. Phantra keeps the kit separate from elements.
4. **Lightest competitor pages**: 3.6 MB pricing, LCP ≤0.78 s.

**Avoid this**
- **A quiz before auth.** START NOW opens a 4-step "set up your account" quiz about inference
  stacks before any sign-in (`ltx/onboarding-quiz-1440.png`).
- **Marketing consent bundled into sign-up**: the login wall says signing up agrees to Terms,
  Privacy and "to receive offers and updates from Lightricks" (`ltx/login-wall-1440.png`).
- **Cookie bar with only "OK"** (`ltx/pricing-390.png`).
- **Refund rule tied to credits used** (14 days and ≤1,200 credits), the most-cited Trustpilot
  complaint.
- **No per-model price on the pricing page**; "28,000 credits/month" with no translation.
- **Brand Kit and custom training Enterprise-only.**

**Phantra has, they don't (on public pages)**
- A conversational brain that proposes priced plans; an MCP connector and Claude/ChatGPT plugins.
- Priced approval for every spend; the keyframe price is a ceiling.
- Brand kits picked per project or per conversation (LTX gates Brand Kit to Enterprise).
- Organic publishing + calendar; talking photo.

---

## 3. Page weight (measured 2026-11-02 ~16:20 UTC)

Method: headless Chromium, CDP `Network.loadingFinished.encodedDataLength` summed (transfer
bytes, after compression), JS = resourceType Script, LCP = last
`largest-contentful-paint` entry (PerformanceObserver, buffered) read after `load` +
networkidle (15 s cap) + 3 s. One cold run each; treat ±20% as noise. "Media" = images + video.

| Site | Page | Width | Transfer MB | JS MB | Media MB | Requests | LCP | `load` | Final URL |
|---|---|---|---|---|---|---|---|---|---|
| Higgsfield | home | 1440 | 25.6 | 3.8 | 18.0 | 472 | 0.84 s (IMG) | 2.71 s | higgsfield.ai/ |
| Higgsfield | home | 390 | 15.6 | 2.1 | 11.3 | 776 | 1.11 s (IMG) | 1.41 s | higgsfield.ai/explore |
| Higgsfield | pricing | 1440 | 7.8 | 4.2 | 0.1 | 455 | **3.63 s** (DIV) | 2.27 s | higgsfield.ai/pricing |
| Higgsfield | pricing | 390 | 5.0 | 2.8 | 0.3 | 801 | **4.17 s** (IMG) | 1.39 s | higgsfield.ai/pricing |
| Runway | home | 1440 | 21.4 | 2.6 | 10.0 | 146 | 0.64 s (IMG) | 0.63 s | runway.com/ |
| Runway | home | 390 | 3.1 | 2.2 | 0.4 | 117 | 0.43 s (IMG) | 0.61 s | runway.com/ |
| Runway | pricing | 1440 | 13.2 | 2.4 | 10.0 | 127 | 0.47 s (IMG) | 0.48 s | runway.com/pricing |
| Runway | pricing | 390 | 2.7 | 2.0 | 0.1 | 101 | 0.43 s (H1) | 0.57 s | runway.com/pricing |
| LTX | home | 1440 | 10.2 | 1.9 | 0.8 | 228 | 0.70 s (IMG) | 3.36 s | ltx.io/studio |
| LTX | home | 390 | 12.4 | 1.8 | 3.1 | 221 | 0.78 s (IMG) | 4.01 s | ltx.io/studio |
| LTX | pricing | 1440 | 3.6 | 1.8 | 0.1 | 159 | 0.61 s (P) | 3.07 s | ltx.io/studio/pricing |
| LTX | pricing | 390 | 3.7 | 1.8 | 0.1 | 159 | 0.48 s (P) | 3.39 s | ltx.io/studio/pricing |
| *Phantra* | home | 1440 | 5.4 | 0.5 | 4.7 | 64 | 1.41 s (VIDEO) | 0.86 s | phantra.ai/ |
| *Phantra* | home | 390 | 5.0 | 0.4 | 4.3 | 52 | **2.50 s** (VIDEO) | 0.51 s | phantra.ai/ |
| *Phantra* | pricing | 1440 | 0.6 | 0.4 | 0.0 | 31 | 0.32 s (P) | 0.44 s | phantra.ai/pricing |
| *Phantra* | pricing | 390 | 0.6 | 0.4 | 0.0 | 22 | 0.53 s (P) | 0.59 s | phantra.ai/pricing |

Other pages (1440): Higgsfield `/ai/video` 32.9 MB / 639 req (mobile redirects to
`/start/agent`), `/effects/use` 8.9 MB / 411 req; Runway `dev.runwayml.com/models` 10.9 MB / 41
req (mobile LCP 5.2 s), `/workflows` 22.2 MB (19.1 MB images); LTX `/model` 43.0 MB (32.4 MB
video). All 390 px pages had `scrollWidth` = 390 (no horizontal scroll).

Read: Phantra ships 5–10× less JS than all three and the lightest pricing page by far. One
Phantra finding from the baseline row: **minor** — the mobile home's LCP is a poster `VIDEO`
element at 2.50 s, the slowest mobile-home LCP of the four (`phantra-baseline/home-390.png`);
competitors put a static image first and measure 0.43–1.11 s.

---

## 4. Pricing (read from each pricing page today, 2026-11-02, USD, signed out, US)

| | Free | Entry | Mid | Top individual | Team / Enterprise | Notes |
|---|---|---|---|---|---|---|
| **Higgsfield** | "Limited use" (compare table) | Starter **$19/mo**, 270 cr | Plus **$59/mo** ($47 annual), 1,200 cr | Ultra **$129/mo** ($99 annual), 3,000 cr; slider to 6K / 9K | Teams from **$65/seat/mo**, 2–15 seats, up to 37,500 cr pooled | ~14 cr per video, ~2 cr per image (page's own estimate); "Unlimited" = 7 days on Plus/Ultra, web only; 30% off annual banner (`pricing-monthly-1440.png`) |
| **Runway** | **$0**, 125 cr one-time, 5 GB | Standard **$15/mo** ($12 annual), 625 cr | Pro **$35** ($28), 2,250 cr, 1 Brand Kit, 1 voice clone, MCP | Max **$95** ($76), 9,500 cr, 3 Brand Kits, HDR/ProRes, 1-month rollover | Team & Enterprise tab; "up to 2 months free" if signed by 12/31 | Gen-4.5 60 cr / 5 s; Kling 4.0 1080p 118 → 89 cr / 5 s (25% off to Nov 30); top-ups min 1,000, never expire |
| **LTX Studio** | **$0**, 800 cr one-time, personal-use licence | Lite **$15** ($12), 8,000 cr | Standard **$35** ($28), 28,000 cr, Elements, AI Storyboards, Pitch Decks, commercial licence | Pro **$125** ($100), 110,000 cr, Veo 3.1, 3 collaborators | Enterprise custom: LTX-2.3 training, Brand management, SSO | No per-model costs on the page; refunds ≤14 days and ≤1,200 cr |
| *Phantra* (`web/src/content/pricing.json`) | 100-credit trial, watermarked | Standard **$15** ($12), 1,500 cr | Pro **$35** ($28), 3,500 cr | Max **$95** ($76), 9,500 cr | — | Every spend priced before it runs |

Changes since the 7 Sep landscape doc: Higgsfield Starter is now $19 / 270 credits (was ~$15 /
200, secondary); Runway and LTX tiers unchanged; LTX added Seedance 2.0, Kling 3.0 Pro and
ChatGPT Images 2.0 to Standard. Phantra's three prices sit exactly on Runway's ($15 / $35 / $95).

---

## 5. Cross-cutting read

- **The spend gate is now table stakes in the UI, not on MCP.** Runway's agent shows a credit
  card with Approve (one reviewer, image job, Aug 2026). Neither Runway's nor Higgsfield's MCP
  documents a quote step; Higgsfield tells users to ask the agent for the cost. Phantra's
  quote-token MCP is the differentiator to lead with in the directory listings and on
  `/connector`.
- **Ads with performance data in** is where Runway went in October (Runway Ads GA, 27 Oct).
  Higgsfield sells the same buyer through Ads Studio, Click to Ad, Hook Multiplier and a
  Virality Predictor. Phantra's Ad Studio has no ad-account data and no variant-from-winner step.
- **Nobody of the three does organic multi-platform posting with a calendar.** Phantra does
  (six providers). It is not on Phantra's home page.
- **Trust is the weak flank for all three**: Trustpilot 4.0 (Higgsfield, 19% one-star), 1.1
  (Runway), 1.6 (LTX), with refunds, charges after cancel and credit burn as the shared themes.

### Top 5 "steal this" across the three
1. **Signed-out guest composer** (Runway): the real prompt box and use-case tiles before sign-up;
   sign-in on Send. `runway/guest-app-1440.png`.
2. **Ad accounts in → variants of winners → approved publish** (Runway Ads), on Phantra's
   existing Ad Studio + brand kit + `outcomes` + publish worker.
3. **Outcome-named apps gallery** (Higgsfield `/apps`): Click to Ad, 9 shots from one image,
   Relight, product spin, hook score. `higgsfield/apps-1440.png`.
4. **Pricing that translates credits into outputs + a plan finder** (Runway plan cards, Higgsfield
   "Not sure which plan?"). `runway/pricing-1440.png`, `higgsfield/pricing-monthly-1440.png`.
5. **MCP page as a recipe library**: per-client tabs and copy-prompt cards (Runway 19 examples,
   Higgsfield skills), plus a one-line CLI/skills install for Claude Code.

---

## 6. Sources (all read 2026-11-02 unless noted)

Vendor pages (crawled with Playwright; screenshots named above):
- https://higgsfield.ai/ · https://higgsfield.ai/pricing · https://higgsfield.ai/ai/video ·
  https://higgsfield.ai/effects/use · https://higgsfield.ai/apps · https://higgsfield.ai/mcp
- https://higgsfield.ai/creator-hub/help-center/integrations/how-do-i-connect-higgsfield-to-ai-agent (dated 1 Aug 2026)
- https://runway.com/ · https://runway.com/pricing · https://runway.com/workflows ·
  https://runway.com/mcp · https://runway.com/product/agent · https://dev.runwayml.com/models ·
  https://app.runwayml.com/ (guest workspace) · https://auth.runwayml.com/ (register wall)
- https://runway.com/news/company-news/runway-ads (GA post, 27 Oct 2026)
- https://help.runwayml.com/hc/en-us/articles/51931843164691-Connecting-to-Runway-MCP
- https://ltx.io/studio · https://ltx.io/studio/pricing · https://ltx.io/model ·
  https://ltx.io/forms/onboarding?placement=studiohero ·
  https://ltx.studio/purchase/v1/ltx_studio/default/login · https://ltx.studio/release-notes (via search summary; the page rendered empty headless)

Reviews and secondary:
- https://www.trustpilot.com/review/higgsfield.ai
- https://www.trustpilot.com/review/runwayml.com
- https://www.trustpilot.com/review/ltx.studio
- https://marcandrews.com/runway-credits-explained/ (Aug 2026 test; header says updated Nov 2026)
- https://marcandrews.com/runway-free-plan-2026-what-it-actually-makes/
- https://fluxnote.io/guides/higgsfield-ai-review (secondary, search result)
- https://creatify.ai/blog/higgsfield-ai-review-(2026)-is-it-worth-it (competitor-authored, search result only)
- Baseline: `docs/COMPETITIVE_LANDSCAPE.md` (7 Sep 2026)
