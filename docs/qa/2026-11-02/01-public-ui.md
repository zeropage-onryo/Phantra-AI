# 01 — Public site UI audit (signed out), 2026-11-02

Agent A. Everything here was read from https://phantra.ai signed out, in headless Chromium
(Playwright's own build, 156.0.8078.4) and with stdlib HTTP. No form was filled or submitted, no
priced button was clicked, nothing was generated, and Mike's Chrome was not touched. The sign-up
wall was reached by following links only and stopped at.

**Counts: 0 blocker, 5 major, 10 minor, 6 cosmetic (21 findings, P1–P21).** Re-check of the
10-22 items: S6 fixed, M2 not reproduced, the `/make` 404 is now a hub; S1–S5, W1–W4 and M1
still open (W2 and the new Halloween page worse; see P1).

## Method

| Step | How | Output |
|---|---|---|
| Crawl | `docs/qa/2026-11-02/crawl-2026-11-02.py crawl` (the 10-22 crawler, dated copy): every `<loc>` in `/sitemap.xml` (46), the 10-22 seeds, then every same-host link two levels deep. Model words now include Grok; visible-text price and "Zero Page" regexes added; declared weight for every page, not only `/` and `/make/*`. | 52 URLs fetched (16:20 UTC); 12 more internal links HEAD-checked; 36 external links checked |
| Browser pass | `crawl-2026-11-02.py browser`: per page and width, a fresh context; true bytes on the wire from CDP `Network.loadingFinished` / `dataReceived` by resource type (the page's own `transferSize` is 0 for the cross-origin `media.phantra.ai` clips, so it under-counts); LCP from a buffered `PerformanceObserver`; `documentElement.scrollWidth`; clipped text (`overflow:hidden`/ellipsis/line-clamp with `scrollWidth > clientWidth + 1`, 1-px sr-only labels excluded); elements past the right edge with no clipping ancestor; `img.naturalWidth === 0`; responses ≥ 400; console errors; axe-core **4.13.0** (from the main session's `web/node_modules/axe-core/axe.min.js`; tags wcag2a/2aa/21a/21aa/best-practice) on every top-level page and three `/make/*` pages at 1440 and 390; computed colour of every element whose text or fill is the yellow accent, against its blended background. Then the page is scrolled top to bottom once (lazy media) and measured again, and a full-page PNG is saved. | 88 page-loads, 0 errors (16:25–16:36 UTC) |
| Extras | `crawl-2026-11-02.py extras`: tap targets at 390 (outside the footer), a 30-Tab focus walk at 1440 on 4 pages, red fills, and the CTA click path to the sign-up wall. Plus one-off probes in the scratch dir (focus pixel contrast, the signed-out `/studio`, M2 first paint at 1/3/6 s). | — |

**Coverage.** 46 HTML pages (`/connector` 308s to `/mcp`, counted once). More than 40, so full
three-viewport screenshots (1440×900, 1280×800, 390×844) were taken for the 17 top-level pages
(`/`, `/pricing`, `/models`, `/faq`, `/mcp`, `/mcp/claude`, `/privacy`, `/terms`, `/make`,
`/support`, `/affiliates`, `/plugins`, `/whats-new`, `/download`, `/download/license`,
`/data-deletion`) and 5 representative pages (`/make/ai-video-generator`,
`/make/photo-to-talking-video`, `/make/ai-halloween-costume-try-on`,
`/models/kling-4-video-generator`, `/models/grok-imagine-video-generator`); the other 24
`/make/*` and `/models/*` pages at 390 only. `/v` and `/v/<anything>` are 404 without a real
share token (expected; no token was minted). `/studio` is robots-disallowed and out of scope
except as the CTA's destination (P14).

**Caveats.** The Mac's load average was 21 → 10 during the runs and the network was not
throttled: LCP numbers are relative, not field data. LCP is the first paint after `load` +
`networkidle`; on a phone network the video-heavy pages will be far slower than these numbers.
Screenshots in the repo are re-encoded to 256 colours (88 MB raw → 22 MB); the raw PNGs are in
the scratch dir. The 1440 full-page shot of `/` shows the hero's right half empty: a full-page
capture artifact (the reel is there and playing 4 clips at 8 s, `home-1440-fold.png`).

## Findings

| # | Severity | Where | Finding | Evidence |
|---|---|---|---|---|
| P1 | **major** | `/make/ai-halloween-costume-try-on` (new, 10-27) | **28.9 MB transferred on load on a phone** (30.3 MB at 1440, 28.1 MB at 1280): the "fan" hero loads all four spin-reveal MP4s at once, `spin-skeleton.mp4` 8.69 MB, `spin-pirate` 7.84, `spin-vampire` 7.17, `spin-witch` 5.79. The fan hero's `Media` renders `<ClipPlayer … eager />` for every card (`web/src/landing-pages/components/make-hero.tsx` line 76, `heroMedia` slice of 4 at line 255). The page is the heaviest on the site by 2.5×, now out of season but still in the footer of every page. Fix: re-encode the spins (they are ~1.2–1.7 MB/s), and load only the front card eagerly. | CDP bytes, `browser` run; HEAD sizes in the crawl; `screens/public/make-ai-halloween-costume-try-on-{1440,1280,390}.png` |
| P2 | **major** | `/make/photo-to-talking-video`, `/models/omnihuman-video-generator` | **W2 still open and measured:** 7.1 MB on load at 390 (10.8 MB at 1280), **18.6 MB after one scroll** at 390; `lena.mp4` is still 9.45 MB. The OmniHuman page shares the clips: 5.8 MB on load, **23.1 MB after a scroll** at 390 (`mechanic.mp4` 5.37 MB). | same; `screens/public/make-photo-to-talking-video-*.png`, `models-omnihuman-video-generator-390.png` |
| P3 | **major** | `/` | **W1 still open:** 12.82 MB declared (10-22: 12.78), **5.0 MB on load at 390** (3.2 MB of it video; the desktop reel holds 52 `<video>` elements), 6.9 MB after scrolling; LCP is a reel `VIDEO` at **2,544 ms at 390** (864 ms at 1440), the slowest LCP on the site. `/models` is the same shape at 1440 (5.6 MB on load). | `browser` run; `screens/public/home-*.png` |
| P4 | **major** (WCAG 2.4.7) | site header, every public page | **The header's focus indicator is invisible.** Nav items use `outline-none … focus-visible:bg-secondary focus-visible:text-foreground` (`web/src/components/site-header.tsx` line 66, and the menu items at lines 116–381): focused, the pill renders `#10100e` on the `#0b0a08` page, **1.04:1** (pixels read from the screenshot), and the label brightens `#c6c4c0` → `#fafafa`. A 30-Tab walk found 6–7 stops with no outline or box-shadow on `/`, `/pricing`, `/make/ai-video-generator`, and 14 on `/mcp`. | `screens/public/header-focus-pricing-1440.png` vs `header-nofocus-pricing-1440.png` (Pricing focused after 6 Tabs, `:focus-visible` true, `outline-style: none`); `extras` focus walk |
| P5 | **major** | `/` reel and "Made in Phantra" grid | **S1 still open:** a clip is labelled **"Runway Gen-4 Turbo"** (`web/src/content/hero-reel.ts` line 45), in the hero reel and on the "Made in Phantra" grid ("Neon city, rain on the lens"). Runway is not a renderer the studio offers and is named on no other page. | crawl text of `/`; `screens/public/home-1440.png` (grid, second column) |
| P6 | minor | `/` "Every top model, one place" strip | **S3 still open, and now staler:** `STRIP_MODELS` (`web/src/components/landing/vesper-content.ts` lines 220–231) says Kling 3, LTX 2.3, FLUX.2, GPT Image 2 and omits **Kling 4.0** and **Grok Imagine** (both added since 10-22) and OmniHuman v2 — on the same page whose banner reads "NEW Kling 4.0 is in the studio" and whose footer lists Kling 4.0, Kling 3 Turbo Pro, LTX 2.5 Pro, FLUX.2 Pro, GPT Image 2.5, Grok Imagine. | `screens/public/home-1440.png` (strip), crawl text |
| P7 | minor | `/` reel | **S2 still open:** "Seedance 2 Fast" (`hero-reel.ts` line 50) where `pricing.json`, `/pricing` and every other page say "Seedance 2.0 Fast". | crawl text of `/` |
| P8 | minor | `/make/ugc-ads`, `/make/ai-music-video-generator`, `/models/kling-4-video-generator` | **S4 partly open:** captions say "**Kling 3.0**" (ugc-ads 3 cards, `ugc-ads.ts` line 49 ff.; music video 3 cards, `ai-music-video-generator.ts` lines 99–101); the Kling 4.0 page's section and FAQ say "Kling 4.0 vs **Kling 3.0**" while its own comparison cards and the catalogue say "Kling 3 Turbo Pro". The Kling page itself is fixed (now titled "Kling 3 and Kling 4.0"). | crawl text |
| P9 | minor (WCAG 2.1.1 / M1) | `/pricing` and `/affiliates` tables, `/models` clip strip at 390 | axe **serious `scrollable-region-focusable`** ×1 on each: the horizontal scrollers are not focusable, so a keyboard user cannot scroll them. On `/pricing` the table is 640 px in a 342 px wrapper: **Standard, Pro and Max columns are off-screen with no cue** (M1 still open, `web/src/app/pricing/page.tsx` lines 67–68). | axe at 390; `wrapSW 640 / wrapCW 342`, no "swipe"/"scroll" text; `screens/public/pricing-390.png` |
| P10 | minor (WCAG 1.4.3) | `/mcp` tab row (Claude, Claude Code, Cursor & others, Claude plugin) | axe **serious `color-contrast` ×4** at both widths: `#82807d` on `#1a1917`, 14 px, **4.46:1** (needs 4.5). | axe; `screens/public/mcp-1440.png` |
| P11 | minor | `/models`, `/make/*`, `/mcp`, `/faq` at 390 | Tap targets under 24 px (WCAG 2.2 2.5.8; 2.1 AA has no size rule): `/models` "Try now" 69×20 and "Learn more" 70×20 ×10; `/make/ai-video-generator` "Start now" 308×20 ×7; `/make/ai-halloween…` "Try it" 308×20 ×7; `/mcp` filter "All" 18 px wide, "Open ChatGPT" 110×19. Under 44 px: 48 of 71 on `/models`, 54 of 80 on `/mcp`. | `extras` tap counts |
| P12 | minor | `/models/kling-4-video-generator` (the target of the home page's NEW banner) | Eleven days after launch the page has **no media at all** (0 images, 0 video) and two **"Comparison render on the way"** placeholders (entry comment: no Kling 4.0 render existed on 10-22). It is also the one new page not on Marigold: light tone, accent SIGNAL (lemon `#fee32d` text on a `#151514` button, 14.13:1, passes), while `landing-pages/theme.ts` line 243 makes Marigold "the brand's own accent for every NEW page" (the page predates that call by a day). | crawl text; contrast rows; `screens/public/models-kling-4-video-generator-*.png` |
| P13 | minor | every page | **W3 still open:** 378–467 KB of JS on the wire at 390 (12–29 chunks; 1.20–1.36 MB declared, uncompressed); `/whats-new` 654 KB and `/mcp/claude` 584 KB at 1440. The three largest chunks (102, 95, 73 KB compressed) load on every route. | `browser` run, CDP `Script` bytes |
| P14 | minor | CTA path: "Try Vesper free" (×3 on `/`), "Start creating" (`/models`, `/make`, footer) | These go to `/studio`, which signed out renders the **studio shell** ("What are we making?", the box, the rail) with **no sign-in prompt** after 8 s; the page fires 12+ `/api/*` calls that all answer 401, and the only "Sign in" is inside the account menu. The header's **Sign up** reaches the sign-up wall in **1 click** (`api.phantra.ai/signin?…&mode=signup`, "Sign up & get 100 free credits", Google / Discord / Email). The shell also still shows 10-22's **D8**: "NEW ELEMENT" `#f4f3f2` on `#fee32d`, 1.17:1. | `screens/public/studio-signed-out-{1440,390}.png`, `signup-wall-from-home-1440.png`; network log |
| P15 | minor (needs Mike) | `/download`, `/plugins` | The Resolve panel's installer is **live**: `media.phantra.ai/site/downloads/resolve/0.1.2/phantra-resolve-plugin-0.1.2.pkg` answers 200 (HEAD only, 44,181 bytes, not downloaded). CLAUDE.md says the panels are "offered later as downloads"; Premiere still reads "Download on the way" / "Coming soon". Confirm the link is meant to be public (and signed). | crawl external check; `curl -I` |
| P16 | cosmetic | `/affiliates` | Signed out, every load fires `GET /api/affiliates/me` → **401** and logs a console error (the only console error on the public site). | console log at all three widths |
| P17 | cosmetic | `/` Vesper demo | The demo's "Approve" is a **red fill** (`vh-btn-red`, `#e4002b`; white on it 4.64:1, passes), by `components/landing/vesper.css` line 37 ("red only on the one spend"); the brief for this QA says red is for errors only. One of the two rules should win; Mike's call. The same card shows "315 credits" under an "Example prices" tag (home is not a new page). | `extras` red scan; `screens/public/home-1440.png` |
| P18 | cosmetic | `/make` hub (new) and 5 `/make/*` pages | **W4 still open:** ai-commercial-maker, consistent-character-video, ai-instagram-reels-maker, ai-tiktok-video-generator, ai-youtube-shorts-maker carry 0 media; the new `/make` hub's 17 cards are text only, so the page that groups every tool shows none of their output. | crawl (0 images); `screens/public/make-1440.png` |
| P19 | cosmetic | `/make/photo-to-talking-video` | axe minor `image-redundant-alt` ×2 (`img[alt="A bike mechanic"]` next to the same caption). | axe |
| P20 | cosmetic | `/models/seedream-…`, `/models/ideogram-…` FAQs | **S5 unchanged** (by design): "What happened to Seedream 4.0?" / "Ideogram 3?" name retired models. | crawl text |
| P21 | cosmetic | `landing-pages/theme.ts` line 245 | The comment says Marigold on the warm black is 12.6:1; measured **12.24:1** (passes AAA either way). | computed below |

Nothing found in these classes: **horizontal overflow at 390: none** (every page's
`scrollWidth` is 390, no element past the right edge outside a clipping scroller); **clipped
text: none** measured on any page at any width; **broken images: none** (`naturalWidth 0` on 0
images; every declared asset HEADs 200); **internal broken links: none** (every same-host
`href` 200 or 308→200; `/legal` 404s but nothing links to it); **failed requests**: only
`net::ERR_ABORTED` on videos the player stops when they leave the viewport, and P16.
External: 26 `chatgpt.com` / `claude.ai` / `help.openai.com` links answer 403 to a script (bot
protection; unverified, as on 10-22); the other 10 answer 200.

## Per-page numbers

"Transfer on load" = bytes on the wire (CDP, all origins) after `load` + `networkidle` + 1.5 s,
before any scroll. "After full scroll" = the same counter after scrolling the page top to
bottom once. "Declared total" = HTML + every `<img>`/`<video>`/`<source>`/poster + script + CSS
named in the HTML, by `Content-Length` (the 10-22 measure; a ceiling). JS = `Script` bytes on the
wire (compressed). "–" = not measured at that width (390-only pages; axe only on top-level and
three `/make/*` pages). Status 200 for every row; `/legal`, `/v`, `/v/<bad token>` are 404.

| Page | Status | HTML bytes | Declared total (crawl) | Transfer on load 1440 / 390 (MB) | After full scroll 390 (MB) | JS on load 390 (KB) | LCP 1440 / 1280 / 390 (ms) | scrollWidth at 390 | Console errors | axe serious+critical 1440 / 390 |
|---|---|---|---|---|---|---|---|---|---|---|
| `/` | 200 | 178,802 | 12.82 MB | 5.41 / 5.00 | 6.88 | 414 | 864 / 1432 / 2544 | 390 | 0 | 0 / 0 |
| `/pricing` | 200 | 137,320 | 1.54 MB | 0.65 / 0.58 | 0.58 | 381 | 408 / 424 / 648 | 390 | 0 | 0 / 1 |
| `/models` | 200 | 205,274 | 6.16 MB | 5.61 / 1.06 | 3.99 | 436 | 544 / 652 / 356 | 390 | 0 | 0 / 1 |
| `/faq` | 200 | 112,522 | 1.50 MB | 0.64 / 0.58 | 0.73 | 378 | 388 / 404 / 396 | 390 | 0 | 0 / 0 |
| `/mcp` | 200 | 268,507 | 8.29 MB | 1.26 / 1.14 | 1.21 | 398 | 740 / 596 / 764 | 390 | 0 | 4 / 4 |
| `/mcp/claude` | 200 | 181,404 | 1.62 MB | 0.99 / 0.61 | 0.93 | 390 | 564 / 612 / 820 | 390 | 0 | 0 / 0 |
| `/privacy` | 200 | 123,613 | 1.51 MB | 0.65 / 0.60 | 0.60 | 388 | 556 / 568 / 496 | 390 | 0 | 0 / 0 |
| `/terms` | 200 | 110,817 | 1.50 MB | 0.65 / 0.59 | 0.60 | 378 | 448 / 1060 / 448 | 390 | 0 | 0 / 0 |
| `/make` | 200 | 134,691 | 1.53 MB | 0.75 / 0.64 | 0.73 | 421 | 496 / 456 / 348 | 390 | 0 | 0 / 0 |
| `/support` | 200 | 87,919 | 1.48 MB | 0.88 / 0.62 | 0.98 | 405 | 420 / 472 / 272 | 390 | 0 | 0 / 0 |
| `/affiliates` | 200 | 95,177 | 1.49 MB | 0.65 / 0.58 | 0.58 | 380 | 348 / 420 / 452 | 390 | 3 | 0 / 1 |
| `/plugins` | 200 | 105,812 | 1.65 MB | 0.66 / 0.59 | 0.59 | 378 | 348 / 440 / 304 | 390 | 0 | 0 / 0 |
| `/whats-new` | 200 | 86,663 | 1.48 MB | 1.35 / 0.72 | 0.90 | 467 | 440 / 544 / 344 | 390 | 0 | 0 / 0 |
| `/download` | 200 | 112,125 | 1.50 MB | 0.64 / 0.58 | 0.58 | 378 | 356 / 396 / 612 | 390 | 0 | 0 / 0 |
| `/download/license` | 200 | 91,378 | 1.48 MB | 0.65 / 0.58 | 0.71 | 378 | 476 / 440 / 372 | 390 | 0 | 0 / 0 |
| `/data-deletion` | 200 | 94,769 | 1.48 MB | 0.64 / 0.57 | 0.59 | 378 | 280 / 516 / 280 | 390 | 0 | 0 / 0 |
| `/make/ai-video-generator` | 200 | 197,315 | 3.19 MB | 1.73 / 1.67 | 7.62 | 414 | 644 / 684 / 704 | 390 | 0 | 0 / 0 |
| `/make/text-to-video` | 200 | 188,300 | 2.76 MB | – / 0.99 | 0.99 | 414 | – / – / 396 | 390 | 0 | – / – |
| `/make/image-to-video` | 200 | 180,668 | 5.56 MB | – / 4.27 | 4.27 | 414 | – / – / 616 | 390 | 0 | – / – |
| `/make/photo-to-talking-video` | 200 | 184,608 | 11.41 MB | 7.77 / 7.12 | 18.57 | 414 | 1108 / 648 / 612 | 390 | 0 | 0 / 0 |
| `/make/ai-halloween-costume-try-on` | 200 | 200,552 | 31.92 MB | 30.33 / 28.88 | 29.00 | 414 | 636 / 492 / 536 | 390 | 0 | 0 / 0 |
| `/make/ai-music-video-generator` | 200 | 170,549 | 2.47 MB | – / 0.84 | 4.67 | 414 | – / – / 600 | 390 | 0 | – / – |
| `/make/ai-product-ad-generator` | 200 | 187,661 | 2.13 MB | – / 0.68 | 0.68 | 414 | – / – / 416 | 390 | 0 | – / – |
| `/make/ugc-ads` | 200 | 183,940 | 5.55 MB | – / 2.20 | 4.02 | 414 | – / – / 640 | 390 | 0 | – / – |
| `/make/ai-storyboard-generator` | 200 | 197,990 | 3.01 MB | – / 0.82 | 0.85 | 414 | – / – / 636 | 390 | 0 | – / – |
| `/make/ai-movie-maker` | 200 | 180,778 | 2.31 MB | – / 1.14 | 2.57 | 414 | – / – / 516 | 390 | 0 | – / – |
| `/make/ai-short-film-maker` | 200 | 168,514 | 4.12 MB | – / 2.67 | 2.67 | 414 | – / – / 596 | 390 | 0 | – / – |
| `/make/ai-trailer-maker` | 200 | 169,775 | 3.48 MB | – / 1.81 | 1.81 | 414 | – / – / 372 | 390 | 0 | – / – |
| `/make/ai-commercial-maker` | 200 | 168,158 | 1.68 MB | – / 0.63 | 0.63 | 414 | – / – / 528 | 390 | 0 | – / – |
| `/make/consistent-character-video` | 200 | 163,833 | 1.67 MB | – / 0.63 | 0.63 | 414 | – / – / 608 | 390 | 0 | – / – |
| `/make/ai-instagram-reels-maker` | 200 | 164,643 | 1.67 MB | – / 0.63 | 0.63 | 414 | – / – / 396 | 390 | 0 | – / – |
| `/make/ai-tiktok-video-generator` | 200 | 164,669 | 1.67 MB | – / 0.63 | 0.63 | 414 | – / – / 376 | 390 | 0 | – / – |
| `/make/ai-youtube-shorts-maker` | 200 | 166,675 | 1.68 MB | – / 0.63 | 0.63 | 414 | – / – / 448 | 390 | 0 | – / – |
| `/models/ltx-video-generator` | 200 | 174,087 | 2.90 MB | – / 0.78 | 2.62 | 414 | – / – / 612 | 390 | 0 | – / – |
| `/models/wan-video-generator` | 200 | 167,998 | 2.55 MB | – / 0.80 | 5.11 | 414 | – / – / 632 | 390 | 0 | – / – |
| `/models/kling-4-video-generator` | 200 | 181,204 | 1.69 MB | 0.71 / 0.63 | 0.63 | 414 | 528 / 744 / 644 | 390 | 0 | – / – |
| `/models/kling-video-generator` | 200 | 170,804 | 3.09 MB | – / 1.86 | 3.54 | 414 | – / – / 644 | 390 | 0 | – / – |
| `/models/seedance-video-generator` | 200 | 213,362 | 1.93 MB | – / 0.69 | 2.98 | 414 | – / – / 684 | 390 | 0 | – / – |
| `/models/veo-video-generator` | 200 | 171,840 | 2.51 MB | – / 1.74 | 4.92 | 414 | – / – / 932 | 390 | 0 | – / – |
| `/models/grok-imagine-video-generator` | 200 | 142,577 | 3.47 MB | 2.28 / 0.75 | 0.79 | 414 | 608 / 512 / 500 | 390 | 0 | – / – |
| `/models/omnihuman-video-generator` | 200 | 162,160 | 7.21 MB | – / 5.79 | 23.07 | 414 | – / – / 572 | 390 | 0 | – / – |
| `/models/nano-banana-image-generator` | 200 | 208,592 | 2.84 MB | – / 0.81 | 0.99 | 414 | – / – / 592 | 390 | 0 | – / – |
| `/models/flux-image-generator` | 200 | 189,998 | 2.70 MB | – / 1.03 | 1.11 | 414 | – / – / 448 | 390 | 0 | – / – |
| `/models/seedream-image-generator` | 200 | 196,186 | 2.51 MB | – / 0.79 | 0.82 | 414 | – / – / 564 | 390 | 0 | – / – |
| `/models/gpt-image-generator` | 200 | 180,020 | 1.97 MB | – / 0.77 | 0.77 | 414 | – / – / 672 | 390 | 0 | – / – |
| `/models/ideogram-image-generator` | 200 | 194,759 | 2.20 MB | – / 0.78 | 0.78 | 414 | – / – / 1176 | 390 | 0 | – / – |

LCP: median 536 ms over 88 loads, worst `/` at 390 (2,544 ms, the reel video), then
`/models/ideogram-image-generator` at 390 (1,176 ms) and `/make/photo-to-talking-video` at
1440 (1,108 ms). axe serious/critical: **0 on 14 of 17 top-level pages and on all three
`/make/*` pages**; the hits are P9 (×1 each on `/pricing`, `/models`, `/affiliates` at 390) and
P10 (×4 on `/mcp`). No critical violation anywhere.

## Accessibility (WCAG 2.1 AA)

| Check | Result |
|---|---|
| axe-core 4.13.0, 20 pages × 2 widths | 0 critical; serious: `scrollable-region-focusable` ×3 (P9), `color-contrast` ×4 on `/mcp` (P10); minor: `image-redundant-alt` ×2 (P19). |
| Focus visible (2.4.7) | **Fails in the site header** (P4): 1.04:1 pill, no outline. Page CTAs and cards do carry a ring (the other 23–24 of 30 stops on `/`, `/pricing` and `/make/ai-video-generator`, 16 of 30 on `/mcp`, had an outline or box-shadow). |
| Keyboard reach (2.1.1) | Three horizontal scrollers cannot be scrolled by keyboard (P9). |
| Contrast (1.4.3) | Body and nav text pass (`#c6c4c0` 11.4:1, `#afafaf`/`#9d9a95` ≥ 7:1, `#82807d` 5.0:1 on `#0b0a08`); the one fail is `#82807d` on the `/mcp` tab pill (4.46:1, P10). |
| Target size (2.5.8, WCAG 2.2) | 20-px-tall text buttons on `/models` and `/make/*` (P11). |
| Names, labels, landmarks | No unnamed control, no unlabeled input, no `img` without `alt` reported by axe on any audited page. |

### The yellow accent ("Marigold") and the other accents, computed

| Where | Element | Foreground | Background | Size / weight | Ratio | AA |
|---|---|---|---|---|---|---|
| `/models/grok-imagine-video-generator`, `/make/ai-halloween-costume-try-on` (Marigold pages) | "Sign up" (header), "Make a Grok video", "Try on a costume", the slider's "drag" | `#0b0a08` | `#ffc21f` | 11–14 px / 500–600 | **12.24:1** | pass (AAA) |
| Marigold as text on the warm black (token pair, `theme.ts` PHANTRA) | — | `#ffc21f` | `#0b0a08` | — | 12.24:1 | pass |
| White on Marigold (the combination `theme.ts` forbids; not found on any page) | — | `#fafafa` | `#ffc21f` | — | 1.55:1 | would fail |
| `/models/kling-4-video-generator` (SIGNAL, lemon) | "Try Kling 4.0 free", header "Sign up" | `#fee32d` | `#151514` | 12.8–14 px / 500 | 14.13:1 | pass |
| `/studio` signed out (the CTA's landing, 10-22 D8) | "NEW ELEMENT" | `#f4f3f2` | `#fee32d` | 14 px | **1.17:1** | **fail** |
| `/` demo | "Approve" (`vh-btn-red`) | `#fafafa` | `#e4002b` | — | 4.64:1 | pass |
| `/mcp` tabs | "Claude", "Claude Code", … | `#82807d` | `#1a1917` | 14 px | 4.46:1 | fail (P10) |

Every element on the public site whose text or fill is yellow was scanned at 1440 and 390
(`CONTRAST_JS` in the crawler): **every yellow fill carries black text**, as Mike's rule says;
the only white-on-yellow is inside the studio (D8). Red appears on the public site only as the
home demo's Approve and two 6-px "live" dots (P17).

## Consistency

**Model names.** `web/src/content/pricing.json` lists twelve video models (LTX 2.3, LTX 2.5
Fast, LTX 2.5 Pro, Wan 3.0, Kling 3 Turbo Pro, Seedance 2.0 Fast, Seedance 2.0, Seedance 2.5,
Veo 3.1, Grok Imagine 1.5, Grok Imagine 1.5 Lite, Kling 4.0). The footer (every page) and the
`/models` chips list thirteen families: LTX 2.5 Pro, Wan 3.0, Kling 4.0, Kling 3 Turbo Pro,
Seedance 2.5, Veo 3.1, Grok Imagine, OmniHuman v2, Nano Banana Pro, FLUX.2 Pro, Seedream 4.5,
GPT Image 2.5, Ideogram 4.5 — consistent with each other and with `/pricing`'s table (which
carries the tiers). Names on public pages that match none of them:

| Name | Where | Catalogue name | Item |
|---|---|---|---|
| Runway Gen-4 Turbo | `/` reel + grid | (not offered) | P5 / S1 |
| Seedance 2 Fast | `/` reel | Seedance 2.0 Fast | P7 / S2 |
| Kling 3, LTX 2.3, FLUX.2, GPT Image 2 (and no Kling 4.0 / Grok / OmniHuman) | `/` model strip | Kling 3 Turbo Pro, LTX 2.5 Pro, FLUX.2 Pro, GPT Image 2.5 | P6 / S3 |
| Kling 3.0 | `/make/ugc-ads` ×3, `/make/ai-music-video-generator` ×3, `/models/kling-4-video-generator` headings | Kling 3 Turbo Pro | P8 / S4 |
| Seedream 4.0, Ideogram 3 | FAQs on their model pages | retired, named on purpose | P20 / S5 |
| GPT Image 2.5 Flare / Sunburst, FLUX 1.1 Pro, Nano Banana (1) | image model pages | variants and predecessors named in comparison copy | not a mismatch |

No public page prices a model differently from `/pricing`: the per-clip credit lines on
`/make/*` and `/models/*` (26, 75, 105, 116, 130, 173, 182, 228, 355, 360 credits) all match the
`/pricing` table today (e.g. LTX 2.3 116 / 6 s, Grok Imagine 1.5 Lite 26 / 5 s, Veo 3.1 360 / 6 s;
LTX 2.3 was 87 on 10-22, so the catalogue moved and the pages moved with it).

**Brand residue.** "Zero Page" / "zeropage" in visible text: **0 on all 46 pages** (also
checked on `innerText` after hydration). In HTML: 13 occurrences, all the allow-listed
`github.com/zeropage-onryo/phantra-claude-plugin` (`/mcp` 9 — 4 more than 10-22, because the
RSC payload repeats the link — and `/mcp/claude` 4).

**Prices on new pages** (routes added since 10-22: `git log --since=2026-10-22 --diff-filter=A
-- web/src/app` → `/make`, `/affiliates`, `/plugins`, `/whats-new`, `/download`,
`/download/license`, `/data-deletion`; new entries `/make/ai-halloween-costume-try-on`,
`/models/kling-4-video-generator`, `/models/grok-imagine-video-generator`): **no plan price and
no credit price on any of them**, in the server HTML or the hydrated text. `/affiliates` names
"1 credit = 1¢" and a "$50" payout threshold: terms of the programme, not a price. The Halloween
page's header tab is gone (season ended 11-01, `landing-pages/seasonal.ts`) and the page wears
Marigold today, as designed.

## Re-check of the 10-22 items

| Item (10-22) | Status 11-02 | Evidence |
|---|---|---|
| S1 "Runway Gen-4 Turbo" on `/` | **still open** (P5) | `web/src/content/hero-reel.ts` line 45; visible in the reel and the "Made in Phantra" grid |
| S2 "Seedance 2 Fast" | **still open** (P7) | `hero-reel.ts` line 50 |
| S3 `/` model strip vs footer | **still open, wider** (P6) | `components/landing/vesper-content.ts` lines 220–231; now also missing Kling 4.0 and Grok Imagine |
| S4 "Kling 3.0" captions | **still open** on ugc-ads and music video; **fixed** on `/models/kling-video-generator`; new instance on the Kling 4.0 page (P8) | `ugc-ads.ts` line 49 ff., `ai-music-video-generator.ts` lines 99–101, `kling-4-video-generator.ts` lines 158, 291 |
| S5 retired names in FAQs | unchanged, by design (P20) | `seedream-image-generator.ts` line 198, `ideogram-image-generator.ts` line 177 |
| S6 "… Image" chip suffix on `/mcp` | **fixed** | the type is now a separate pill on each card ("GPT Image 2.5" · "Image"): `screens/public/mcp-models-chips-1440.png` |
| W1 `/` weight | **still open** (P3) | 12.82 MB declared; 5.0 MB on load at 390, 6.9 MB after scroll |
| W2 `lena.mp4` 9.45 MB | **still open, measured worse** (P2) | 18.6 MB after scroll at 390 |
| W3 ~1.25 MB JS per page | **still open** (P13) | 1.20–1.36 MB declared, 378–654 KB on the wire |
| W4 text-only `/make` pages | **still open** (P18) | the same five pages, 0 media; plus the Kling 4.0 page (P12) |
| M1 pricing table swipe not signposted | **still open** (P9) | 640 px table in a 342 px wrapper, no cue, not keyboard-scrollable |
| M2 blank `/make/ai-video-generator` hero at 390 | **not reproduced** | at 1 s, 3 s and 6 s after navigation the `h1` has opacity 1 and the hero video `readyState` 4, playing: `screens/public/make-ai-video-generator-390-at-1s.png` |
| (10-22 note) `/make` 404 | **fixed** | `/make` is now the use-case hub (200) |

## Design critique

Structured on the `design:design-critique` frame (first impression, usability, hierarchy,
consistency, accessibility, what works, priorities), from the full-page screenshots at three
widths and the numbers above. Severity words as in the findings table.

### `/` (home)

- **First impression (2 s).** At 1440 the serif headline "The AI content studio that creates
  for you." and the Vesper box own the left half; the reel of real clips fills the right half
  and is the most persuasive thing on the page (`home-1440-fold.png`). What it is: clear. What
  to click: two white CTAs compete in the first screen — header "Sign up" and the box's "Try for
  free" — plus the "NEW Kling 4.0" pill; acceptable, since both lead to the same place.
- **Usability.** Header **Sign up → sign-up wall: 1 click** (`signup-wall-from-home-1440.png`,
  "Sign up & get 100 free credits"). The three "Try Vesper free" buttons further down go to
  `/studio`, which signed out shows an empty studio with no sign-in prompt (P14): a visitor who
  trusts the page's main CTA lands somewhere that does not say "sign in to continue". Make every
  marketing CTA use the header's sign-up target (or have `/studio` open the wall).
- **Hierarchy.** Good reading order (headline → box → reel → "Meet Vesper" → the agent demo →
  Start anywhere → Made in Phantra → models → closing CTA). Two dead bands of ~250 px of empty
  black (after the hero and after the demo's "Try Vesper free") break the scroll rhythm at 1440
  (`home-1440.png`). The demo card with "315 credits" and a red Approve is the busiest object on
  the page and the only red on the site (P17).
- **Consistency.** Three model vocabularies on one page: the reel's tags (incl. Runway, "Seedance
  2 Fast"), the "Every top model" strip (families from before Kling 4.0 and Grok), and the footer
  (current tiers) (P5–P7).
- **Mobile (390).** Clean: box, chips and "Try for free" in the first screen, the reel strip
  peeking below (`home-390.png`); no overflow. But it is the heaviest first view a phone gets
  outside the Halloween page (5.0 MB, LCP 2.5 s here unthrottled).
- **Works well.** The live Vesper box as the hero; the agent demo that shows "nothing renders
  until you say yes" in the product's own UI; real outputs everywhere.
- **Priorities.** (1) Cut the reel's weight (smaller phone renditions; load the columns in view
  only) — P3. (2) Fix the labels (P5–P7). (3) Point "Try Vesper free" at the sign-up wall — P14.

### `/pricing`

- **First impression.** "Pick your plan." with the one-credit-is-one-cent line, then four plan
  cards with the price, credits and a translation into clips ("≈ 134 × 5s on Grok Imagine 1.5
  Lite, or 9 on Veo 3.1") in the first screen at 1440 (`pricing-1440.png`). The strongest page on
  the site for clarity.
- **Usability.** Monthly/Yearly toggle obvious; Pro marked POPULAR and the only filled CTA. The
  per-model table hides three of its five columns at 390 with no cue and cannot be scrolled from
  the keyboard (P9/M1): stack it as one card per model on phones, or add a visible "swipe →"
  and `tabindex=0` + a label on the scroller.
- **Hierarchy / consistency.** Plan names, prices and model names match `pricing.json`; the
  credit FAQ closes the page. Fine.
- **Mobile.** Cards stack cleanly; the free card's "Sign up free" is first (`pricing-390.png`).

### `/models`

- **First impression.** "Every model you need, in one studio." with Start creating / See pricing
  and the 13 model chips, then a row of real clips (`models-1440.png`). Clear.
- **Usability.** The per-model cards' "Try now" / "Learn more" are 20-px-tall text buttons (P11);
  the clip strip at 390 is a swipe row that keyboard users cannot scroll (P9).
- **Weight.** 5.6 MB on load at 1440 (4.4 MB video) but 1.1 MB at 390 — the phone build is lazy
  where the desktop one is not.
- **Consistency.** Chips match the footer exactly. Good.

### `/mcp`

- **First impression.** "PHANTRA MCP — AI images and video inside your chat." with "Connect
  Phantra" and "How to connect?" and the endpoint printed under them (`mcp-1440.png`). Clear for
  someone who knows what MCP is; the tab row (ChatGPT / Claude / Claude Code / Cursor & others /
  Claude plugin) is the real navigation and its inactive labels are just under AA (P10).
- **Usability.** 80 interactive elements, 54 under 44 px at 390 (filter "All" 18 px wide). The
  model cards now carry the type as a separate pill (S6 fixed).
- **Weight.** 8.3 MB declared but 1.1–1.3 MB on load: the example videos are lazy. Good.
- **Length.** 11,700 px at 1440 and 18,600 px at 390 — the longest page on the site; the
  per-client instructions behind the tabs keep it navigable.

### `/make/ai-halloween-costume-try-on` (the new `/make` page)

- **First impression.** Strong: Marigold CTA "Try on a costume" with black text (12.24:1), a
  fanned hand of four portraits that spin into costumes, the face-kept promise in one line
  (`make-ai-halloween-costume-try-on-1440.png`). Out of season it correctly drops the header
  tab and wears Marigold.
- **Usability.** The CTA path is the same 1-click sign-up; "Try it" buttons further down are
  20 px tall (P11). No prices on the page, per Mike's rule.
- **The one problem is weight**: 28.9 MB on a phone before any scroll (P1). As a seasonal page
  that stays indexed all year, it should be the cheapest page to load, not the most expensive.

### Priority recommendations (site-wide)

1. **Video weight** (P1, P2, P3): re-encode the four Halloween spins, `lena.mp4` and
   `mechanic.mp4` to ≤ 1.5 MB each and stop eager-loading the back cards; serve phone renditions
   to the home reel. This is ~40 MB of avoidable transfer across three pages.
2. **Header focus ring** (P4): one `focus-visible:ring-2 ring-ring` (or an outline) on the nav
   classes in `site-header.tsx` line 66 and the menu items — the only WCAG AA failure that
   touches every page.
3. **One model vocabulary** (P5–P8): fix `hero-reel.ts` lines 45/50 and `STRIP_MODELS`, rename
   "Kling 3.0" captions; the footer is already the source of truth.

## Screenshots

All under `docs/qa/2026-11-02/screens/public/` (97 PNGs, 256-colour re-encodes):

- Full page, three widths (`<slug>-1440.png`, `-1280.png`, `-390.png`): `home`, `pricing`,
  `models`, `faq`, `mcp`, `mcp-claude`, `privacy`, `terms`, `make`,
  `support`, `affiliates`, `plugins`, `whats-new`, `download`, `download-license`,
  `data-deletion`, `make-ai-video-generator`, `make-photo-to-talking-video`,
  `make-ai-halloween-costume-try-on`, `models-kling-4-video-generator`,
  `models-grok-imagine-video-generator`.
- 390 only: the other 24 `make-*` and `models-*` pages.
- Probes: `home-1440-fold.png` (first screen at 8 s, reel playing), `header-focus-pricing-1440.png`
  / `header-nofocus-pricing-1440.png` (P4), `mcp-models-chips-1440.png` (S6),
  `make-ai-video-generator-390-at-1s.png` (M2), `signup-wall-from-home-1440.png` (the wall,
  reached by the header's Sign up), `studio-from-try-vesper-free-1440.png` (after clicking "Try Vesper free", 8 s) and
  `studio-signed-out-1440.png` / `-390.png` (P14).

## Not verified

- A real phone, Safari/iOS, a throttled network, and a screen reader (roles and names come from
  axe and the DOM).
- The hero box's "Try for free" (it is a form submit; not pressed) and anything past the
  sign-up wall.
- The 26 `chatgpt.com` / `claude.ai` links (403 to scripts), and the Resolve `.pkg` itself (HEAD
  only, not downloaded; its signature was not checked).
- `/v/<token>` share pages (no token minted).
