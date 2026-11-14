# 06b — Competitors: Krea, invideo AI, Freepik (now Magnific)

Agent F, 2026-11-02. Signed out only: no account was made, no form submitted, no terms accepted,
nothing generated anywhere. No Phantra spend or quote call was made by this agent, so Phantra
credits were not touched (before = after, see `00-baseline.md`). Cookie banners: Magnific's
OneTrust banner was answered "Reject All" (the only banner met). Sibling file `06a-…md` covers
Higgsfield, Runway and LTX Studio.

**Read this first: Freepik is now Magnific.** Freepik renamed itself Magnific on 2026-04-28
(stock, generators and the upscaler under one brand, magnific.com; `freepik.com/pricing` 301s to
`magnific.com/pricing`; the pricing page title reads "Magnific (formerly Freepik)"). Sources [M1]
[M2]. Below, "Magnific" means the product the task calls Freepik AI.

**Method.** Headless Chromium (Playwright, the venv's headless shell), desktop 1440×900 and
mobile 390×844 (iPhone UA, touch, DPR 2), cold cache, from this Mac at ~16:20 UTC. Page weight is
the sum of CDP `encodedDataLength` over every response from navigation to `load` + 7 s idle (so
autoplaying hero video and lazy images that start in that window count). LCP is the last
`largest-contentful-paint` entry read with a buffered PerformanceObserver. Scripts and raw JSON:
`/private/tmp/claude-501/-Users-iphone-Documents-PRODUCTION-PIPLINE--GIT--claude-worktrees-phantra-qa-competitive-8903e3/8e124c54-1b2c-426d-a936-2335f6112e5e/scratchpad/agentF/`
(`crawl.py`, `signup.py`, `crawl-*.json`). Screenshots: `screens/competitors/{krea,invideo,freepik}/`.

**Magnific blocks automated readers.** Every magnific.com / freepik.com page except `/pricing`
answered **HTTP 403** ("Our security filter flagged something") to headless Chromium, to plain
`curl` with a desktop UA, and to Anthropic's WebFetch: `/`, `/ai`, `/ai/video-generator`,
`/ai/video-editor`, `/ai/image-generator`, `/spaces`, `/mcp`, `/agents`, `/sign-up`, the help
docs (`/ai/docs/*`). Per the task rules nothing was done to get past it; Magnific is scored from
its pricing page, its developer docs on `docs.magnific.com` (which answered) and third-party
reviews, and every such score says so. Evidence: `freepik/home-1440.png`, `home-390.png`,
`signup-signup-1440.png` (the 403 page prints the visitor's IP address; it is redacted in the
committed screenshots).

---

## 1. Rubric (1 = weak, 5 = best in class)

| Criterion | Krea | invideo AI | Magnific (Freepik) |
|---|---|---|---|
| First-screen clarity | **3** — desktop opens straight into the app shell: a sidebar of 14 tools, an "Introducing Ad Studio" carousel and a prompt bar; no headline says what Krea is. Mobile is clearer ("Sign up and start creating free · Free daily credits · 90+ models"). `krea/home-1440.png`, `home-390.png` | **5** — one headline ("The agentic video editor for serious creatives"), one CTA ("Start Creating"), a second line for agents ("Or start with your Cowork & Codex agents"), the editor shown below the fold. A yellow discount bar sits above it. `invideo/home-1440.png` | **n/m** — home is a 403 to every reader we have. Pricing's first screen is clear (Magnific One + Brand Kit banner, three plans). `freepik/pricing-1440.png` |
| Clicks to first generation (inferred: we cannot sign in) | **4** — tool pages open signed out with the full composer (model, start/end frame, 720p, 6 s, 16:9) — `krea/signup-tool-video-1440.png`; "Sign in" is 1 click to a modal with Google / Apple / SSO / email, "Free to start · No credit card required" — `krea/signup-signin-1440.png`. Free plan = 100 units/day [K1]. Estimate ~4 clicks from home to a first image after OAuth. | **3** — no tool is reachable signed out: "Start Creating" and "Sign up" are both 1 click to `/signup` (email / Google / Apple / SSO, Cloudflare Turnstile iframe) — `invideo/signup-start-creating-1440.png`. The free plan is not on the pricing page; third parties disagree on what it gives [I4][I5]. | **n/m** — `/sign-up` is a 403 here (1 click from pricing, `freepik/signup-signup-1440.png`); no free plan is listed on pricing; third parties disagree whether one exists [M3][M5]. |
| Model catalog breadth | **5** — `/models`: 39 image, 35 video, 5 motion transfer, 2 lipsync, 3 audio, 1 video restyle, plus 3D, LoRA training and in-house Krea 1/2/3. `krea/models-1440-full.png` | **5** — `/ai-models/` lists 91 video, 86 image, 11 audio and 9 music models (counted from the page), incl. motion control (Kling 3.0 MC, Wan Animate), lipsync (HeyGen, Veed, Kling, Pixverse), avatars, upscalers. `invideo/models-1440-full.png` | **5** — pricing table names Kling 4.0 / 3.0 / 2.5, Seedance 2.5 / 2.0, Veo 3.1, Gemini Omni, MiniMax, in-house Magnific One, Nano Banana family, GPT 2.5, Flux.2, Recraft, Ideogram, Grok; audio (Lyria 3, ElevenLabs music, SFX, TTS, voice clone), 3D, lipsync ("Speak"), character training. MCP exposes 236 tools [M4]. `freepik/pricing-1440-full.png` |
| Effects & presets | **5** — `/apps`: "hundreds" of one-click apps built on node workflows in 6 categories (Camera & Motion, Enhance & Style, Face & Identity, Video Editing, Ads & Products, Games & Characters) + Agent templates deep-linked (`/agent?template=game-cutscene`). `krea/apps-1440-full.png` | **3** — `/ideas/` is a gallery of finished videos each with a "Generate" (recreate) button (Trending, Movies, Million Dollar Ads, UGC & Avatars, Music Videos); Agent Two has 9 "Workflows" [I2]; Kling Effects as a model. `invideo/ideas-1440-full.png` | **4** (menu only) — Relight, Change Camera, Image Extender, Video Relight, 3D 360, upscalers, background remover in the Creative Suite menu (read from the pricing page's nav). Pages themselves 403. |
| Asset library & pickers | **4** — Assets, Moodboards, LoRA "Train", the composer takes `@` references to "images, videos, audio, or elements". `krea/signup-tool-video-1440.png` | **4** — 200 GB–2 TB storage and 100–500 premium stock clips per plan; Agent Two keeps project memory and reads uploads, scripts, PDFs, links [I2]. `invideo/pricing-1440-full.png` | **5** — 250M+ stock assets on every paid plan, a library and brand kits as first-class objects (MCP groups "Library and brand kits", "Organize and share") [M4]. |
| Editor / timeline | **2** — a Node Editor and Video Restyle/Edit; no timeline editor found in the nav or pricing features. | **5** — a full NLE in the browser: multiplayer, colour, audio, 3D, branches and edit history, agents edit the same timeline under their own cursor [I1][I3]. `invideo/mcp-1440.png` | **3** — "Video Project Editor" and "Clip Editor" exist in the nav; depth unverified (403). |
| Agent / chat assistance | **5** — Krea Agent on every plan since 2026-09-10: plans, generates and iterates across models, researches a brand, builds a context library, templates; Slack agent; routines and custom agents on Enterprise [K2][K3]. `krea/agent-1440.png` | **5** — Agent Two: project memory, Playbooks (standing rules), Notebooks, Workflows, Lite / Pro / Ultra tiers that set cost per task [I2]. | **3** — "AI Assistant" (`/app/assistant`) and "Agents" pages exist; content 403, so unscored beyond existence. |
| Brand kit / ads tooling | **5** — Ad Studio: "Turn your website into a brand kit and ads", logo / colours / type pulled in "a minute or two", 16 example ads by placement (Display 16:9, Stories 9:16, Feed 4:5, Paid social 1:1), and a **"Generate in Claude"** button beside "Generate in Krea". `krea/ad-studio-1440.png` | **3** — UGC Ads and AI Ad Generator landing pages; a brand kit is described only by third parties [I6]. | **5** — "Magnific One, with Brand Kit … Included in all paid plans" on the pricing hero; MCP has `brand_kit_scrape_url` and `brand_kit_create_template` [M4]. `freepik/pricing-1440.png` |
| Mobile web | **4** — a separate app-like layout at 390 (category pills, tool icons, "Get started" recipe tiles, a bottom "Describe what you want to make" bar) and an iPhone app; but the home moved **31.7 MB** at 390. `krea/home-390.png` | **4** — clean responsive page, no horizontal scroll, 2.8 MB, LCP 2.8 s at 390; iOS and Android apps in the footer. `invideo/home-390.png` | **n/m** — only pricing renders: 2.2 MB, LCP 0.7 s, no horizontal scroll (`freepik/pricing-390.png`); a mobile app is linked. |
| Pricing clarity & credit model | **3** — each plan says what it buys ("~112 Nano Banana 2 generations, ~15 Seedance 2.0 Fast videos") and the free tier is daily; but "units" vary per model, the Agent's own reasoning is billed in tokens on Free [K3], packs expire in 90 days [K4], and reviews call usage hard to predict [K5]. | **3** — per-model credit costs, a plan finder that asks what you make and how much, seats; but a "50% OFF" badge on every page, "We reserve the right to update credit costs at any time, without prior notice", no rollover, Starter has no Seedance 2.5. `invideo/pricing-1440-full.png` | **4** — the longest per-model table of the three (credits per clip and clips per plan per year), credits valid a year with no monthly reset; but the annual price is the default with the monthly struck through, "UNLIMITED" applies to a list of models, and no free plan is shown. |
| Speed / page weight (measured, §3) | **1** — home: 16.2 MB, 1,021 requests (768 of them JS), LCP 6.7 s desktop; pricing 5.6 MB, 604 JS requests. | **4** — home 2.8 MB / 113 req / LCP 1.5 s; pricing 1.8 MB, but TTFB 1.4 s. The `/ai-models/` page moved 47.2 MB of images. | **4** (pricing only) — 2.1 MB / 100 req / LCP 1.3 s. |
| API / MCP / integrations | **5** — hosted MCP for Claude, ChatGPT, Claude Code, Cursor, Grok bot, Hermes, OpenClaw; a CLI; API; ChatGPT plugin; plugins (After Effects and others); Slack agent; `llms.txt` (24.9 KB). `krea/mcp-1440.png` | **5** — MCP at `mcp.invideo.io/mcp` (Claude, ChatGPT, Codex, Cursor), a CLI, and a public **`/agents.md`** (9.9 KB) written to the agent ("run the setup below yourself … ask once"); `generate` takes a dry run first [I1]; `llms.txt` (18.0 KB). `invideo/remote-agents-1440.png` | **5** — MCP with 236 tools (OAuth, no key), a free `simulate_cost` / `account_balance`, API, Photoshop and Figma plugins, ComfyUI, desktop app [M4]. |
| Social publishing | **1** — "Download it for your ad platforms" (Agent page); no connection or scheduling found. | **2** — third parties say exports can go straight to YouTube / Instagram / TikTok [I6]; nothing on today's site confirms it. | **1** — none found (MCP has share/projects tools, no platform posting) [M4]. |

n/m = not measurable from here (403). Scores dated 2026-11-02.

---

## 2. Per competitor

### Krea (krea.ai)

**What it is now.** No longer "the realtime image tool": an app shell with Krea Agent at the top,
Ad Studio, Seedance Studio, Node Editor, LoRA training, Realtime, Enhancer, Audio, 3D, an MCP
server, a ChatGPT plugin, a Slack agent and an in-house model family (Krea 3). It overlaps
Phantra's Create chat, Ad Studio, brand kits and connector almost one for one.

**Steal this**
1. **"Generate in Claude" next to "Generate in Krea" on the Ad Studio page** (`krea/ad-studio-1440.png`). The connector stops being a settings page and becomes a door on the feature itself. Phantra's Ad Studio could carry the same second button ("Open in Claude" / "Open in ChatGPT") that drops the format + kit + brief into the connector.
2. **Deep-linked agent templates** (`/agent?template=metro-fashion-oner`, `?template=swap-the-car`, ten on the home page, each "Recreate"): a public, shareable URL that opens the agent with a recipe loaded. Phantra has skills and front-page tiles; giving each a public `/studio?skill=<name>` link that survives sign-up would make them shareable and SEO-able.
3. **Free units every day, not once** (pricing: Free "100 units / day", no card). Phantra's trial is 100 credits once, expiring after two months. A small daily allowance gives a reason to come back; it can be watermarked and limited to cheap models.
4. **Tool pages work signed out up to the Generate button** (`krea/signup-tool-video-1440.png`): the visitor sets model, frames, resolution, length and ratio before any wall. The wall appears only on Generate.
5. **"Ask ChatGPT about Krea" / "Ask Claude about Krea" footer links** (prefilled `chatgpt.com/?prompt=` and `claude.ai/new?q=`) plus a 25 KB `llms.txt`. Cheap AI-search plumbing; phantra.ai has neither (`/llms.txt` → 404).

**Avoid this**
- **Page weight.** Home: 16.2 MB, 1,021 requests, 768 JS requests, LCP **6.7 s** on desktop; 31.7 MB on the phone; the MCP page 19.7 MB (14.4 MB video). Phantra's home is 6.3 MB / 64 requests / LCP 1.4 s.
- **The agent spends with no price in front of it.** Krea's own Agent docs describe no cost preview or confirmation; the only stop is running out, and on Free the orchestrator's reasoning is billed at 5% of token price [K3]. The video composer's Generate button carries no price (`krea/signup-tool-video-1440.png`).
- **Unpredictable units.** Trustpilot reviewers (3.5/5 on one regional page, 2/5 on another) report units draining faster than expected and a cancelled plan over a withdrawn "unlimited Seedance 2.0" [K5][K6]; packs expire in 90 days [K4].

**Phantra has, they don't**
- A price on every spending button and an approval before any spend, including the agent's (Krea: none described).
- A timeline editor with an agent that proposes edits (Krea: nodes, no timeline).
- Elements with drawn reference sheets and the reference gate; timed multi-shot scenes rendered as one clip.
- Social connections, a publish worker and a calendar (Krea: download only).
- Render QC notes under each clip.

### invideo AI (invideo.io)

**What it is now.** Repositioned from "text to video" to **"the agentic video editor"**: a
browser NLE (multiplayer, colour, audio, 3D, branches) with Agent Two inside it and the same
editor exposed to outside agents over MCP. This is the closest match to Phantra's editor + agent
+ connector story, and it is ahead on the editor.

**Steal this**
1. **`/agents.md`** (`https://invideo.io/agents.md`, 9.9 KB): a setup guide written *to the agent*: server URL, transport, auth, a section per client (Claude Code, Codex, …), what to ask the user once, and the dry-run rule. The home hero links to it ("Or start with your Cowork & Codex agents"). Phantra has the connector and the plugins but `phantra.ai/agents.md` is a 404; one page would let any agent install Phantra by itself.
2. **The plan finder on pricing** ("Not sure? Work it out": what you make → how many clips and images a month → seats → a recommended plan with the credits it covers). `invideo/pricing-1440-full.png`. Phantra's "What a month buys" table answers the reverse question; a three-question finder would answer "which plan".
3. **Agents edit the same timeline, live, under their own cursor, with branches** (`invideo/mcp-1440.png`, [I3]). Phantra's editor agent proposes ops the person keeps or undoes; showing the connector's edits land in `/studio/cut` while the person watches is the demo invideo leads with.
4. **Playbooks**: standing rules per project ("process, language, generation options") the agent always follows [I2]. Phantra's project memory is learned; an explicit, editable rule list is the missing half.
5. **A second hero line for agents** under the main CTA. Phantra's home sells Vesper; one line to the connector costs nothing.

**Avoid this**
- **Discount pressure on every surface**: a yellow "Get an additional discount … after signing up" bar, "50% OFF" on the Pricing nav item, "Unlimited for 30 days" offers (`invideo/home-1440.png`).
- **"We reserve the right to update credit costs at any time, without prior notice"** (pricing FAQ) and "Unused credits don't roll over". Phantra's quote-then-approve is the opposite promise; say it as plainly.
- **Everything behind sign-up**: no tool is reachable signed out; both hero CTAs go to `/signup`.
- **Refund friction** is the most repeated Trustpilot complaint (credits used, refund refused) [I4]; a 2026 comparison notes no per-agent spending cap on the MCP [I7].
- **Unoptimised media**: `/ai-models/` moved 47.2 MB of images on desktop (17.4 MB at 390).

**Phantra has, they don't**
- A priced approval on every spend in the studio and a signed, single-use quote token on the connector (invideo: a dry run the agent is told to do; budgets per project only on Enterprise [I2]).
- Elements and reference sheets that every shot is held to.
- Social publishing with a calendar and posting times (invideo: only third-party claims).
- A Claude plugin and a ChatGPT plugin of skills on top of the connector.
- Projects with a look and a brief that feed scene writing (invideo has memory and playbooks; no "look").

### Magnific, formerly Freepik (magnific.com)

**What it is now.** Since 2026-04-28 one brand over stock (250M+ assets), generators, the
Magnific upscaler, Spaces (a shared canvas for workflows), an Assistant, a video project editor,
Designer, 3D, plugins and an MCP. Third parties put it at €230M ARR and 1M+ paying subscribers,
bootstrapped [M1][M2]. Only `/pricing` and `docs.magnific.com` could be read.

**Steal this**
1. **Brand kit sold as part of the model, on the pricing hero**: "Meet Magnific One, with Brand Kit — Art direction, built in … Included in all paid plans." (`freepik/pricing-1440.png`). Phantra's brand kits and Ad Studio are an add-on and a settings page; the pitch should be "your kit is in every render".
2. **A free cost tool on the MCP**: `simulate_cost` / `simulate_spaces` / `simulate_flows` and `account_balance`, free, documented as "check before paid generations" [M4]. Phantra's `quote` already does this; Magnific shows the value of naming it plainly in the docs page agents read.
3. **Credits that last the year** on annual plans ("Credits valid for 1 year, no monthly resets"). Phantra's credits expire two months after they land; for an annual buyer that is the credit-anxiety Krea and invideo reviews complain about.
4. **A per-model "what your plan buys" table that covers audio too** (Lyria songs, ElevenLabs music per 30 s, SFX per 3 s, character training at 3,000 credits each). Phantra's table is video-only.
5. **Character training as a priced line** ("Train AI characters 3,000 credits/character"). Phantra holds characters with photos and sheets; a trained identity is the next step reviewers compare on.

**Avoid this**
- **A bot wall in front of the whole marketing site.** Normal headless Chromium, plain curl and an AI fetcher all get a 403 on every page but pricing; the 403 page prints the visitor's IP. Anything that blocks AI readers also blocks AI search answers about the product.
- **"Unlimited" with an asterisk**: Premium+ is "UNLIMITED generations" for a named list (Nano Banana 2 1K, Kling 2.5 720p, MiniMax Hailuo 2.3 Fast, Flux.2 Pro 1K …), everything else spends credits.
- **Annual-first pricing**: the toggle defaults to Annual with the monthly price struck through ($20 → $14.50).
- **Reviews**: credits gone fast, a 3,000-credit balance lost at a forced renewal, refund disputes; magnific.ai 1.7/5 (73 reviews) vs magnific.com 3.8/5 (2,992) on Trustpilot snapshots; G2 4.7/5 with price/limits the main complaint [M5][M6].

**Phantra has, they don't**
- The approval is the product: every spend is priced and approved by the person; Magnific's MCP lets an agent call `simulate_cost` but does not require it [M4].
- Timed scenes, keyframes and one-clip multi-shot renders from a plan the chat writes.
- An editor with an agent that proposes edits; social publishing and a calendar (none found at Magnific).
- A connector that is listed for Claude and ChatGPT with plugins (Magnific: "isn't in Claude's connector directory yet, so it must be added as a custom connector" [M4]).

---

## 3. Page weight (measured 2026-11-02, cold cache, load + 7 s)

| Site | Page | Width | HTTP | Requests | Transfer | JS (requests) | Images | Video | TTFB | LCP | load |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Krea | home | 1440 | 200 | 1021 | 16.23 MB | 5.21 MB (768) | 7.67 MB | 2.94 MB | 463 ms | **6676 ms** | 7.1 s |
| Krea | home | 390 | 200 | 817 | **31.68 MB** | 5.02 MB (678) | 21.34 MB | 5.00 MB | 436 ms | 828 ms | 4.2 s |
| Krea | pricing | 1440 | 200 | 685 | 5.62 MB | 4.68 MB (604) | 0.54 MB | 0 | 481 ms | 1436 ms | 9.8 s |
| Krea | pricing | 390 | 200 | 676 | 5.77 MB | 4.68 MB (604) | 0.70 MB | 0 | 485 ms | 1308 ms | 6.8 s |
| Krea | models | 1440 | 200 | 234 | 2.59 MB | 2.10 MB (194) | 0.13 MB | 0 | 696 ms | 1092 ms | 4.1 s |
| Krea | apps | 1440 | 200 | 640 | 6.88 MB | 2.85 MB (549) | 3.69 MB | 0 | 324 ms | 912 ms | 3.6 s |
| Krea | ad-studio | 1440 | 200 | 917 | 9.66 MB | 5.88 MB (788) | 3.40 MB | 0 | 272 ms | 7652 ms | 5.0 s |
| Krea | mcp | 1440 | 200 | 336 | 19.75 MB | 3.92 MB (244) | 1.05 MB | 14.37 MB | 901 ms | 1680 ms | 7.7 s |
| invideo | home | 1440 | 200 | 113 | 2.79 MB | 1.36 MB (51) | 0.82 MB | 0 | 136 ms | 1528 ms | 1.1 s |
| invideo | home | 390 | 200 | 107 | 2.78 MB | 1.36 MB (51) | 0.80 MB | 0 | 349 ms | 2832 ms | 1.6 s |
| invideo | pricing | 1440 | 200 | 102 | 1.84 MB | 1.32 MB (47) | 0.06 MB | 0 | 1449 ms | 1836 ms | 1.9 s |
| invideo | pricing | 390 | 200 | 89 | 1.80 MB | 1.32 MB (47) | 0.03 MB | 0 | 1246 ms | 1964 ms | 2.0 s |
| invideo | ai-models | 1440 | 200 | 134 | **47.23 MB** | 1.21 MB (43) | 45.84 MB | 0 | 592 ms | 1168 ms | 0.9 s |
| invideo | ideas | 1440 | 200 | 121 | 18.04 MB | 1.21 MB (43) | 0.44 MB | 16.19 MB | 235 ms | 668 ms | 0.4 s |
| Magnific | home (`freepik.com/ai`) | 1440 | **403** | 5 | 0.48 MB | 0 | 0.32 MB | 0 | 399 ms | — | — |
| Magnific | pricing | 1440 | 200 | 100 | 2.09 MB | 1.35 MB (57) | 0.12 MB | 0 | 976 ms | 1292 ms | 1.5 s |
| Magnific | pricing | 390 | 200 | 103 | 2.22 MB | 1.35 MB (57) | 0.13 MB | 0 | 445 ms | 720 ms | 0.9 s |
| *Phantra (baseline)* | home | 1440 | 200 | 64 | 6.28 MB | 0.46 MB (17) | 1.13 MB | 4.41 MB | 336 ms | 1440 ms | 1.6 s |
| *Phantra (baseline)* | home | 390 | 200 | 53 | 6.56 MB | 0.41 MB (13) | 1.13 MB | 4.76 MB | 152 ms | 2488 ms | 0.7 s |
| *Phantra (baseline)* | pricing | 1440 | 200 | 31 | 0.65 MB | 0.41 MB (15) | 0 | 0 | 218 ms | 552 ms | 0.8 s |
| *Phantra (baseline)* | pricing | 390 | 200 | 22 | 0.58 MB | 0.38 MB (12) | 0 | 0 | 232 ms | 428 ms | 0.6 s |

Read: Phantra ships the least JavaScript of the four by 3–11× (0.46 MB vs 1.36 MB invideo and
5.21 MB Krea on the home). Phantra's home weight is its hero video (4.4–4.8 MB), which also puts
its 390 LCP at 2.5 s against 0.4 s on its own pricing page (minor; see §5).

---

## 4. Pricing, 2026-11-02 (USD, read from each pricing page today)

| | Free | Tier 1 | Tier 2 | Tier 3 | Team / top | Credit rules |
|---|---|---|---|---|---|---|
| **Krea** (units) | $0, **100 units/day**, no card | Basic **$9/mo** ($5.25 yearly), 5,000 units: ~112 Nano Banana 2 or ~15 Seedance 2.0 Fast; selected video models | Pro **$35/mo** ($21 yearly), 20,000 units: 450 Nano Banana 2 or ~65 Seedance 2.5; all video models | Max **$105/mo** ($63 yearly), 60,000 units (slider to 100k); unlimited LoRA training | Business **$200/mo** ($160 yearly), 80k units (to 1.5M) | Yearly = "40% off". Individual units don't roll over; packs expire in 90 days [K4]. "Unlimited relaxed" in-house image models after units run out. |
| **invideo AI** (credits, per seat) | Not on the pricing page (third parties: watermarked 720p exports, limits disputed [I4][I5]) | Starter **$20/mo** ($10 yearly, "50% off"), 400 credits; no Seedance 2.5 / 2.0; Agent Two Lite only | Plus **$60/mo** ($30 yearly), 2,000 or 5,000 credits; all models; +10 guest seats | Max **$250/mo** (same yearly), 8,000 / 10,000 / 15,000 credits; "lowest cost per credit" | Team and Business tabs | "All models are available at their original API pricing"; no rollover; costs may change "without prior notice". Examples: Seedance 2.5 720p ~56 credits / 5 s, Nano Banana Pro ~2.5 credits. |
| **Magnific** (credits, per year) | None shown on pricing (G2 lists a limited €0 plan [M5]) | Premium **$20/mo** ($14.50 yearly), 240K credits/yr | Premium+ **$45/mo** ($33.75 yearly), 600K credits/yr + "unlimited" on listed models | Pro Starter **$110/mo** ($82.50 yearly), 1.5M credits/yr (or 4M with Nano Banana Pro) | Teams tab; Enterprise | "Credits valid for 1 year, no monthly resets"; 30-day refund guarantee; Seedance 2.5 720p 1,760 credits / 4 s; Kling 4.0 1080p 840 / 3 s. |
| *Phantra (for reference)* | 100 credits once, 2-month expiry, watermarked | Standard $15/mo, 1,500 cr | Pro $35/mo, 3,500 cr | Max $95/mo, 9,500 cr | Top-up 750 cr / $10 | 1 credit = 1 cent; the Render card's number is the charge; credits expire 2 months after landing. |

**Same clip, four prices (Seedance 2.5, ~5 s, cheapest monthly plan that includes it).** Phantra:
355 credits = **$3.55** (Pro table, 5 s). invideo Plus monthly: 56 credits × $0.03 = **~$1.68**
(720p, 5 s). Magnific Premium+ monthly: 1,760 credits per 4 s × ($45 / 50,000) = **~$1.58 per
4 s, ~$1.98 per 5 s**. Krea Pro monthly: $35 / ~65 clips = **~$0.54**, length and resolution not
stated on the card (the composer defaults to 6 s 720p). Different resolutions and lengths make
this approximate, but Phantra is roughly 2× invideo and Magnific on the flagship video model and
several times Krea. That is the `MARKUP = "2.4"` showing up next to resellers who price near API
cost (invideo says so outright).

---

## 5. Findings for Phantra (severity as on 10-22)

| # | Severity | Finding | Evidence |
|---|---|---|---|
| F1 | **major** | Seedance 2.5 costs ~$3.55 per 5 s clip on Phantra vs ~$1.6–2.0 on invideo and Magnific and ~$0.54 (unstated res) on Krea; invideo states it resells "at original API pricing". A comparison shopper sees 9 Seedance 2.5 clips a month on Phantra Pro vs ~65 on Krea Pro at the same $35. | §4; `phantra.ai/pricing` table; `krea/pricing-1440-full.png`; `invideo/pricing-1440-full.png`; `freepik/pricing-1440-full.png` |
| F2 | minor | No `/agents.md` and no `/llms.txt` on phantra.ai (both 404), while invideo (agents.md 9.9 KB, llms.txt 18.0 KB) and Krea (llms.txt 24.9 KB) publish them. | `curl` 2026-11-02: phantra 404 / 404; invideo 200 / 200; krea 200 (llms.txt) |
| F3 | minor | The trial is 100 credits once; Krea gives 100 units every day with no card. | Krea pricing "Free 100 units / day"; phantra pricing "100 credits once, on sign-up" |
| F4 | minor | Credits expire two months after they land, also on yearly; Magnific's annual credits last a year with no monthly reset. Expiry is the shape of the credit-burn complaints all three competitors collect. | `freepik/pricing-1440.png`; phantra pricing "Credits expire 2 months after they land" |
| F5 | minor | Phantra's home LCP at 390 is 2.5 s, driven by 4.8 MB of hero video in the first 7 s (pricing: 0.4 s). Still far lighter than Krea; invideo's home is 2.8 MB total. | §3 |
| F6 | cosmetic | Ad Studio has no "open in Claude / ChatGPT" door; Krea's Ad Studio puts "Generate in Claude" beside its own button. | `krea/ad-studio-1440.png` |

Where Phantra leads all three (keep saying it): a price on every spending button and an approval
before any spend, including the agent's and the connector's (none of the three requires one:
Krea Agent describes none [K3], invideo's dry run is advice to the agent and budgets are
Enterprise-only [I1][I2], Magnific's `simulate_cost` is optional [M4]); elements with reference
sheets and the reference gate; social publishing with a calendar (none of the three, on today's
evidence); a much lighter site (§3).

---

## 6. Screenshots

`screens/competitors/krea/`: `home-1440.png`, `home-390.png`, `pricing-1440.png`,
`pricing-1440-full.png`, `pricing-390.png`, `models-1440.png`, `models-1440-full.png`,
`models-390.png`, `apps-1440.png`, `apps-1440-full.png`, `apps-390.png`, `agent-1440.png`,
`ad-studio-1440.png`, `mcp-1440.png`, `signup-signin-1440.png` (the auth modal, 1 click),
`signup-tool-image-1440.png`, `signup-tool-video-1440.png`, `signup-tool-agent-1440.png`
(signed-out tool pages).

`screens/competitors/invideo/`: `home-1440.png`, `home-390.png`, `pricing-1440.png`,
`pricing-1440-full.png`, `pricing-390.png`, `models-1440.png`, `models-1440-full.png`,
`models-390.png`, `ideas-1440.png`, `ideas-1440-full.png`, `ideas-390.png`, `mcp-1440.png`,
`remote-agents-1440.png`, `signup-signup-1440.png`, `signup-start-creating-1440.png` (both 1 click
to `/signup`).

`screens/competitors/freepik/` (Magnific): `home-1440.png`, `home-390.png` (403, IP redacted),
`pricing-1440.png`, `pricing-1440-full.png`, `pricing-390.png`, `signup-signup-1440.png` (403,
IP redacted).

Clicks from home to the email/OAuth wall: Krea **1** ("Sign in" → modal); invideo **1** ("Sign
up" or "Start Creating" → `/signup`); Magnific **n/m** (home 403; from pricing, "Sign up" is 1
click to a 403).

---

## 7. Sources (read 2026-11-02)

Krea
- [K1] Krea pricing — https://www.krea.ai/pricing (crawled; `krea/pricing-1440-full.png`)
- [K2] Krea Agent overview — https://www.krea.ai/docs/user-guide/agent/overview ; landing https://www.krea.ai/krea-agent ; blog https://www.krea.ai/blog/what-is-krea-agent
- [K3] Krea Agent plans and credits — https://www.krea.ai/docs/user-guide/agent/plans-and-credits
- [K4] Krea compute units — https://www.krea.ai/docs/user-guide/help-and-support/compute-units
- [K5] Trustpilot, Krea — https://nz.trustpilot.com/review/krea.ai?page=2 , https://no.trustpilot.com/review/krea.ai , https://www.trustpilot.com/review/www.krea.ai
- [K6] Krea cost analyses — https://www.costbench.com/software/ai-image-generators/krea/hidden-costs/ , https://academy.techpresso.co/reviews/is-krea-worth-it
- Krea MCP coverage — https://hermes-ai.net/news/krea-opens-60-plus-ai-image-and-video-models-to-coding-agents/ ; pages crawled: https://www.krea.ai/ , /models , /apps , /ad-studio , /mcp , /image , /video , /agent , https://www.krea.ai/llms.txt

invideo AI
- [I1] invideo MCP / agents guide — https://invideo.io/agents.md , https://invideo.io/mcp/ , https://invideo.io/news/introducing-invideo-mcp/
- [I2] Agent Two — https://invideo.io/agent-two/
- [I3] Remote agents — https://invideo.io/remote-agents/
- [I4] Trustpilot, invideo — https://au.trustpilot.com/review/ai.invideo.io?page=3 , https://ca.trustpilot.com/review/ai.invideo.io?page=4
- [I5] Free plan (third party, dated 2026-06, pre-credit plans) — https://www.fast.io/resources/invideo-ai-review-2026.md , https://marcandrews.com/invideo-ai-credits-explained/
- [I6] Publishing / brand kit (third party, unverified) — https://creatify.ai/review/invideo-ai , https://flowith.io/blog/invideo-ai-automated-script-to-screen-essential-brand-content
- [I7] MCP comparison (spending cap) — https://aitoolsrecap.com/Comparisons/invideo-remote-agents-vs-descript-mcp
- Pages crawled: https://invideo.io/ , /pricing/ , /ai-models/ , /ideas/ , /signup , https://invideo.io/llms.txt

Magnific (Freepik)
- [M1] Rebrand — https://en.wikipedia.org/wiki/Magnific , https://alternativeto.net/news/2026/5/freepik-rebrands-as-magnific-expands-into-full-ai-creative-platform/
- [M2] Rebrand detail — https://dev.to/raxxostudios/freepik-just-rebranded-as-magnific-what-changes-for-solo-creators-1jac
- [M3] Free plan, conflicting — https://toolquestor.com/tool/magnific , https://www.g2.com/products/magnific/pricing
- [M4] Magnific MCP docs — https://docs.magnific.com/modelcontextprotocol
- [M5] Reviews — https://www.g2.com/products/magnific/reviews , https://ca.trustpilot.com/review/magnific.ai?page=2 , https://uk.trustpilot.com/review/magnific.ai?page=4 , https://nz.trustpilot.com/review/www.magnific.com?page=10
- [M6] Rating snapshot — https://tools.malwaretips.com/url-scan/magnific.com
- Pages crawled: https://www.magnific.com/pricing (200); https://www.freepik.com/ai , https://www.magnific.com/ , /ai , /ai/video-generator , /ai/video-editor , /ai/image-generator , /spaces , /mcp , /agents , /sign-up , /ai/docs/ai-credits-and-limits (all 403)

Phantra baseline: https://phantra.ai/ , https://phantra.ai/pricing (crawled with the same script).
