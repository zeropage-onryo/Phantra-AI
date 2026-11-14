# 06 — Competitors: Phantra vs Higgsfield, Runway, LTX Studio, Krea, invideo AI, Magnific (Freepik)

2026-11-02. The merge of two agent files, which hold the detail, the per-competitor
"steal this / avoid this / Phantra has, they don't" pages, the measured page-weight and pricing
tables, and every source URL:

- [`06a-competitors-higgsfield-runway-ltx.md`](06a-competitors-higgsfield-runway-ltx.md) (Agent E)
- [`06b-competitors-krea-invideo-freepik.md`](06b-competitors-krea-invideo-freepik.md) (Agent F)

All competitor work was signed out, in headless Playwright: no account, no form, no generation,
no call to any competitor's MCP. Mike did not log in for us, so "clicks to first generation" for
the six is estimated from the public flow up to the auth wall plus docs and reviews. Freepik's AI
product is now **Magnific** (renamed 2026-04-28); every magnific.com / freepik.com page except
`/pricing` answers 403 to every reader we have, so three of its rows are n/m.

**Phantra's column is scored by the main session** from the agents' measurements of Phantra
(`01-public-ui.md`, `02-studio-ui.md`, `04-connector.md`) and from the product as `CLAUDE.md`
describes it. It is scored from the inside, signed in, while the six are scored from outside:
read it as a self-assessment against the same rubric, not as a neutral rank.

## Scorecard (1 = weak, 5 = best in class)

| Criterion | **Phantra** | Higgsfield | Runway | LTX Studio | Krea | invideo AI | Magnific |
|---|---|---|---|---|---|---|---|
| First-screen clarity | **3** — one headline, Vesper box, "Try for free"; but "Try Vesper free" / "Start creating" land on a signed-out studio shell with no sign-in prompt and 12+ 401s (01 P14) | 2 | 3 | 4 | 3 | 5 | n/m |
| Clicks to first generation | **4** — signed in: direct Video/Image 2 clicks, ~2.4 s to the priced button; chat still 7.3 s, chat video 25.8 s (02 timings); sign-up wall 1 click from the header (01 P14) | 4 | 3 | 2 | 4 | 3 | n/m |
| Model catalog breadth | **4** — 12 video models (`pricing.json`), ~11 image models, voice (ElevenLabs), talking photo (OmniHuman v2), sound (MMAudio); no music generation, no motion-control model | 5 | 5 | 3 | 5 | 5 | 5 |
| Effects & presets | **3** — dated effects table (edits, Kling/PixVerse templates, camera moves, upscale, sound, reframe, cut-out), free looks, the Effects tab; no one-click "apps" named by outcome | 5 | 3 | 2 | 5 | 3 | 4 |
| Asset library & pickers | **4** — Library (folders, stars, soft delete, picker), elements with drawn reference sheets; provider filter mislabels "Fal" / "Runway" (02 T4) | 4 | 4 | 4 | 4 | 4 | 5 |
| Editor / timeline | **4** — full timeline (keyframes, 58 transitions, mixer, grade, OTIO export) with an agent that proposes edits; no phone layout | 2 | 4 | 4 | 2 | 5 | 3 |
| Agent / chat assistance | **5** — Vesper plans, skills, look research, a priced card before every spend, Explore mode | 4 | 5 | 2 | 5 | 5 | 3 |
| Brand kit / ads tooling | **4** — brand kits (import from a site, kit screens), Ad Studio add-on; no ad-account data or variant-from-winner loop | 4 | 5 | 3 | 5 | 3 | 5 |
| Mobile web | **3** — public site: no overflow anywhere (01); studio: Elements 752 px wide at 390 (02 T6), Voice unreachable (T15), editor has no phone layout | 3 | 4 | 3 | 4 | 4 | n/m |
| Pricing clarity & credit model | **4** — credits on every spending button, per-model table on `/pricing`; trial is 100 credits once, credits expire after 2 months, the table hides 3 of 5 columns at 390 (01 P9, 06b F3/F4) | 2 | 4 | 3 | 3 | 3 | 4 |
| Speed / page weight (measured) | **4** — least JS of all seven (~0.46 MB home), pricing 0.65 MB; but home LCP 2.5 s at 390 and the Halloween page 28.9 MB on a phone (01 P1, P3) | 2 | 3 | 4 | 1 | 4 | 4 |
| API / MCP / integrations | **5** — three MCP servers (Claude, ChatGPT, stdio) with quote tokens, Claude + ChatGPT plugins, Premiere/Resolve panels; no `llms.txt` / `agents.md` (06b F2) | 5 | 5 | 4 | 5 | 5 | 5 |
| Social publishing | **5** — six providers (Instagram, Discord, Reddit, LinkedIn, X, YouTube), a calendar, posting times, a publish worker | 2 | 4 | 1 | 1 | 2 | 1 |
| **Total (of 65)** | **52** | **44** | **52** | **39** | **52** | **51** | **44 of 50** (10 scored) |

## What the six say about Phantra

**Where Phantra leads, and should say so louder**
- **A price and an approval before every spend, on every door.** Not one of the six requires it
  everywhere: Runway's agent shows an Approve card in the UI (one reviewer, an image job), but
  neither Runway's nor Higgsfield's MCP documents a quote step; Krea's agent describes none;
  invideo's dry run is advice and budgets are Enterprise-only; Magnific's `simulate_cost` is
  optional (06a §5, 06b §5). This is the line for the connector listings and `/mcp`.
- **Organic social publishing with a calendar.** None of the six has it on today's evidence
  (Runway publishes *paid* ads). It is not on Phantra's home page.
- **Elements with reference sheets and the reference gate.**
- **A light site.** Least JavaScript of the seven; pricing 0.65 MB vs 1.8–13.2 MB (06a §3, 06b §3).
- **Trust.** All three scored on Trustpilot (Higgsfield 4.0, Runway 1.1, LTX 1.6) collect the same
  complaints: refunds, charges after cancelling, credit burn (06a §5). Priced approval is the
  answer to exactly that.

**Where Phantra trails**
- **Price per clip** (06b F1, major): Seedance 2.5 is ~$3.55 per 5 s clip on Phantra (355 credits
  at 1 cent), ~$1.6–2.0 on invideo and Magnific, ~$0.54 on Krea (resolution unstated). Phantra
  Pro ($35) buys ~9 such clips, Krea Pro ~65. Caveat from the main session: `pricing.json`
  already marks Seedance up 1.5× (not the house 2.4×), so the fal cost is ~$2.37; the cheaper
  rivals are likely quoting 720p or a shorter take, or selling below fal's list. A rough guide,
  not a like-for-like price.
- **Trial and expiry** (06b F3/F4): 100 credits once vs Krea's 100 units every day; credits expire
  in 2 months (Magnific's annual credits last a year).
- **Outcome-named apps** (Higgsfield `/apps`, Krea `/apps`): "Click to Ad", "9 shots from one
  image", Relight, product spin.
- **Ads with performance data in** (Runway Ads, GA 2026-10-27): ad accounts in → variants of
  winners → approved publish.
- **Signed-out try-before-sign-up** (Runway's guest workspace, Krea's tool pages).
- **Agent-readable site**: `invideo.io/agents.md`, `llms.txt` on Krea and invideo; phantra.ai 404s
  both.

## Top "steal this" across all six (main session's merge of 06a and 06b)

1. **Signed-out composer up to the Generate button** (Runway guest app, Krea tool pages); ask for
   an account on Send. Fixes P14's dead-end CTA too.
2. **Ad loop on Ad Studio**: ad-account data in, variants of winners, approve, publish (Runway Ads),
   on Phantra's existing Ad Studio + brand kits + `outcomes` + publish worker.
3. **Outcome-named apps gallery** (Higgsfield, Krea).
4. **Credits translated into outputs on each plan card + a plan finder** (Runway, Higgsfield,
   invideo).
5. **The MCP page as a recipe library + `/agents.md` + `llms.txt`** (Runway's 19 copyable prompts,
   invideo's agents.md, Krea's "Generate in Claude" button on Ad Studio).
6. **A small daily free allowance** instead of 100 credits once (Krea).

## Avoid (seen on the six)

Higgsfield's 7-day "Unlimited" that excludes MCP, discount banners on every page and a 27-link nav;
Runway's implied marketing consent with no cookie banner and a free plan that cannot make video
(reviews); LTX's 4-step quiz before sign-in, opt-out marketing and refunds capped at 1,200
credits; invideo's "we may change credit costs without notice"; Krea's 16–32 MB home page and
token-billed agent reasoning on Free (06a §2, 06b §2).
