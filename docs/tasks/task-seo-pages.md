# Task — get zeropage.studio found: fix the domain, then build the SEO pages

**From:** a claude.ai session, 2026-10-11, after the InVideo teardown (project
doc `claude/invideo_growth_teardown_2026-10-11.md`). InVideo's sitemap,
counted that day: ~1,015 FAQ pages, ~1,390 blog posts, 270 free-tool pages,
138 `/make/<use case>` pages, 48 per-model pages. **For:** Claude Code, in
`zeropage-onryo/video-pipeline` on Mike's Mac.
**Mike's call:** the connector ships first (PR #221 and its
`docs/tasks/task-directory-submission.md`, on branch
`claude/directory-two-listings`); SEO pages are next. Standing rules for the public site: build on top of the
existing `web/` app, never replace it; no landing-page change goes live
without his approval.
**Read first:** `web/src/landing-pages/README.md`, then
`docs/tasks/task-landing-pages-edit.md` (the per-page checklist and status),
then `web/src/landing-pages/pages.ts`.

## State right now (checked 2026-10-11)

- **Before this branch, the whole site told Google its home was
  `zpf-web.vercel.app`, not `zeropage.studio`.** Live on 2026-10-11:
  `robots.txt` named `Sitemap: https://zpf-web.vercel.app/sitemap.xml`, every
  sitemap `<loc>` was on the Vercel host, `/make` and `/models` canonicals
  pointed there, `/`, `/pricing`, `/models` and `/faq` had NO canonical, the
  home page had no structured data, every page but `/` shared a missing
  `/og.jpg` (404), and `zpf-web.vercel.app` served the whole site as a second
  copy (200, no redirect). Branch `claude/seo-canonical-domain` fixes all of
  it in code (see "As built" at the bottom). **It is not live until that PR is
  merged.**
- `www.zeropage.studio` answers **307** (temporary) to the apex. Vercel's
  domain setting; it should be a 308. Not changeable from code.
- Pages that exist: `/`, `/pricing`, `/models`, `/faq`, `/terms`, `/privacy`,
  ONE `/make` page (`ai-product-ad-generator`) and TEN `/models/<slug>` pages
  (ltx, wan, kling, seedance, veo, nano-banana, flux, seedream, gpt-image,
  ideogram). One template renders all of them from typed entries in
  `web/src/landing-pages/entries/`; adding an entry adds it to the sitemap.
- `task-landing-pages-edit.md` has 10 of 11 pages done; its open items:
  per-page OpenGraph cards, an image catalogue export, mobile Lighthouse at
  76–84 (six font families preloaded).
- `/connector` → 404. PR #221's task (step 6) asks for a draft of this page
  in `web/`; step 2 below IS that draft, so do it once, here, and tick it in
  both files. PR #221 also rewrites `llms.txt` (served by the API, `app/seo.py`):
  leave that file to #221.
- Lighthouse fonts are already fixed on main (`claude/site-fonts`, merged:
  only Oswald preloads now); `task-landing-pages-edit.md` line 71 is stale.
- Checked 2026-10-11: no open PR touches `web/src/app/layout.tsx`,
  `sitemap.ts`, `robots.ts`, `web/src/landing-pages/` or `app/make` / `app/models`.
  The old SEO and landing branches (`claude/seo-metadata-robots-config-*`,
  `claude/landing-*`, `feat/make-landing-pages`, `claude/site-*`) are all
  merged (0 commits ahead of main).
- Unknown from here: whether Google Search Console is set up for
  `zeropage.studio`, and what Vercel Analytics shows.

## Rules for this task

- No renders, stills or any generation without Mike's yes in chat. Page media
  comes from renders that already exist (R2, `m/<account>/…` keys via
  `media.url_for`, or files already in `web/public/`); Mike picks which.
- Every claim on a page is something the studio does today (the entry's top
  comment says where it was checked). No earnings claims, no invented
  testimonials or customer logos.
- Branch for every change; a merge to `main` deploys Vercel. Mike approves a
  page before it merges.
- Gates before a commit (from `task-landing-pages-edit.md`): `cd web && npx tsc --noEmit`, `npx eslint src`, a look at 375 / 768 / 1440.

## Steps

### 0. Point the site at its real domain
- [x] Code: one `SITE_URL` (`web/src/lib/site-url.ts`, fallback `https://zeropage.studio`) behind `layout.tsx`'s `metadataBase`, `sitemap.ts` and `robots.ts`; canonicals on `/`, `/pricing`, `/models`, `/faq`; home JSON-LD (Organization, WebSite, SoftwareApplication with the plans' price range off `pricing.json`); the root share image named `/opengraph-image` instead of the missing `/og.jpg`; `next.config.ts` 308s the PUBLIC pages on `zpf-web.vercel.app` to `zeropage.studio` (studio, sign-in, `/auth`, API proxy and media untouched). Branch `claude/seo-canonical-domain`, built and checked locally 2026-10-11 (see "As built").
- [ ] **MIKE:** merge the PR. A merge to `main` deploys Vercel.
- [ ] After the deploy, check live (verify by running):
  - `curl -s https://zeropage.studio/robots.txt | tail -1` → `Sitemap: https://zeropage.studio/sitemap.xml`
  - `curl -s https://zeropage.studio/sitemap.xml | grep -o '<loc>[^<]*' | head -3` → all `https://zeropage.studio…`
  - `for p in "" pricing models faq models/kling-video-generator; do curl -s https://zeropage.studio/$p | grep -o '<link rel="canonical"[^>]*>'; done` → five `zeropage.studio` canonicals
  - `curl -sI https://zpf-web.vercel.app/models/veo-video-generator | grep -i location` → `https://zeropage.studio/models/veo-video-generator`
  - `curl -sI https://zpf-web.vercel.app/studio | head -1` → still 200 (the studio is NOT redirected)
  - Done when: all five answer as above.
- [ ] If the canonical still names the Vercel host after deploy, `NEXT_PUBLIC_SITE_URL` is SET on Vercel to the old value and overrides the fallback. Check with `vercel env ls --scope zero-page-ai` in `web/` (names only; the cloud session got 403 from the Vercel API on this team). **MIKE, ask first:** delete it, or set it to `https://zeropage.studio`, then redeploy.
- [ ] **MIKE:** point the API's studio address at the real domain (it is `https://zpf-web.vercel.app`, read off the live redirects 2026-10-11: `/ui` sends to `zpf-web.vercel.app/studio`, and the API's landing page links there). In Terminal: `fly secrets set -a zeropage-studio STUDIO_URL=https://zeropage.studio`. It restarts the API (a render polling at that moment is picked up again by fal recovery).
  - Done when: `curl -s -o /dev/null -D - https://zeropage-studio.fly.dev/ui | grep -i location` names `zeropage.studio/studio`, and signing in at zeropage.studio lands on `https://zeropage.studio/studio`.
  - This PR also moves `DIRECTOR_FRONTEND_URL` in `fly.toml` from `zeropage-web.fly.dev` (scaled to zero) to `https://zeropage.studio/studio/flows`; it takes effect when the PR deploys.
- [ ] **MIKE:** Vercel → zpf-web → Settings → Domains → `www.zeropage.studio` → redirect to `zeropage.studio` with **308 Permanent** (it is 307 today).
  - Done when: `curl -sI https://www.zeropage.studio/ | head -1` shows 308.
- [ ] Once Search Console is set up (step 1), run its URL Inspection on `https://zeropage.studio/` and `https://zeropage.studio/models/veo-video-generator`, then **Request indexing** on both.
  - Done when: both show "URL is on Google" or "Indexing requested", and Google's chosen canonical is the `zeropage.studio` URL.

### 1. Search Console
- [ ] **MIKE:** add `zeropage.studio` as a Domain property in Google Search Console (DNS TXT record at the registrar), then submit `https://zeropage.studio/sitemap.xml`.
  - Done when: Search Console shows the sitemap "Success" with the page count from step 0.
- [ ] **MIKE:** same in Bing Webmaster Tools (it can import from Search Console). Bing feeds ChatGPT search and Copilot.

### 2. A `/connector` page (the directory's docs URL, and an SEO page)
- [ ] **After PR #221 is merged** (the page describes what it ships): add `/connector`. Two addresses: `https://api.zeropage.studio/mcp/claude` for Claude (writes and prices scenes; the render is approved in the studio through `approve_url`) and `https://api.zeropage.studio/mcp` for ChatGPT and hand-added clients (renders after a quote and a yes). How to add it (sign in once at zeropage.studio, then the consent page), privacy link. Copy only, existing landing components. Ask Mike before publishing.
  - Done when: `curl -s -o /dev/null -w "%{http_code}" https://zeropage.studio/connector` is 200 after deploy, and the page is in the sitemap.
- [ ] Once live, put it in `docs/directory/TWO_LISTINGS.md` as the docs URL for both listings, and tick step 6 of `task-directory-submission.md`.

### 3. `/make` pages: from 1 to 12 (Mike approves the list before any is built)
- [ ] **MIKE:** approve, cut or add to this list. Each is a real search phrase the studio can actually serve today; the slug is the phrase.
  1. `ai-video-generator` (the head term)
  2. `text-to-video`
  3. `image-to-video` (animate a still)
  4. `ai-short-film-maker`
  5. `ai-music-video-generator`
  6. `ai-commercial-maker` (broader than the product ad page)
  7. `ai-instagram-reels-maker`
  8. `ai-tiktok-video-generator`
  9. `ai-youtube-shorts-maker`
  10. `consistent-character-video` (elements + reference sheets)
  11. `ai-storyboard-generator` (timed shots + keyframes)
  - Done when: Mike has replied with the final list.
- [ ] For each approved slug, one entry in `web/src/landing-pages/entries/` following the per-page checklist in `task-landing-pages-edit.md` (copy, media, signature, accent, related, check). One commit per page: `feat(web): /make/<slug> -- <what it says>`.
  - Media: Mike picks existing renders per page; if a page has none that fit, leave gradient plates and list it for him. No new generation.
  - Done when: each page builds, passes the gates, and is in the sitemap.
- [ ] Link them: the footer and the "More to make" sections reach every `/make` page within two clicks of `/`.
  - Done when: from `/`, every new page is reachable through links (check in the browser, not by reading code).

### 4. Model pages stay in step with what the studio offers
- [ ] Compare the ten `/models` pages against `fal.VIDEO_MODELS` / `fal.IMAGE_MODELS` (the live tables). A model the studio offers with no page gets an entry; a page for a model the studio dropped gets its copy corrected, never silently removed.
  - Done when: a short table of model → page → status is in this file under "As built".
- [ ] When a new model lands in the studio, its page ships the same week (InVideo's per-model pages are how they ride every launch). Add that line to `web/src/landing-pages/README.md`.

### 5. The open items from the landing-page task
- Note: PR #233 (`claude/free-tier-watermark`) adds a watermark on free-trial renders, InVideo's other growth lever. It touches no site file; nothing here depends on it.
- [ ] Per-page OpenGraph cards (each page names the root's card today).
- [ ] Run Google's Rich Results Test on `https://zeropage.studio/` (home JSON-LD) and one `/models` page (FAQPage) after deploy.
  - Done when: both parse with no errors.
- [ ] Re-measure mobile Lighthouse on `/make/ai-product-ad-generator` (fonts were fixed on main since the 76–84 reading) and update line 71 of `task-landing-pages-edit.md` with the new number.

### 6. Measure
- [ ] Two weeks after step 1, read Search Console (impressions, clicks, top queries per page) and write the numbers under "As built" here. That decides which kind of page gets made next.

## Done means

- `zeropage.studio` is the canonical domain everywhere a crawler looks, and Search Console has the sitemap.
- `/connector` is live and is the directory's docs URL.
- The approved `/make` pages are live, linked from `/`, and every model the studio offers has a page.
- First Search Console numbers are recorded here.

## As built

### 2026-10-11 — branch `claude/seo-canonical-domain` (step 0, code half)
- `web/src/lib/site-url.ts`: `SITE_URL` (env or `https://zeropage.studio`, trailing slash stripped) and `VERCEL_HOST`. `layout.tsx`, `sitemap.ts`, `robots.ts` import it; `grep -rn "zpf-web.vercel.app" web/src` now finds only `site-url.ts`.
- Canonicals added: `/` (in `app/page.tsx`), `/pricing`, `/models`, `/faq`. `/make`, `/models/<slug>`, `/terms`, `/privacy` already had theirs.
- Home JSON-LD in `app/page.tsx`: Organization (logo = the 512 favicon), WebSite, SoftwareApplication with an AggregateOffer built from `PLANS` (15–95 USD, 3 offers today). No ratings, no reviews.
- Root OpenGraph image: `/opengraph-image` (the generated card). `/og.jpg` never existed.
- `next.config.ts` `redirects()`: host `zpf-web.vercel.app` + the sitemap's public paths (and `/sitemap.xml`, `/robots.txt`) → `https://zeropage.studio<path>`, 308.
- Checked against `next build` + `next start` locally: robots and sitemap name `zeropage.studio`; all seven public pages tested carry a `zeropage.studio` canonical and the generated share image; the home JSON-LD parses; `Host: zpf-web.vercel.app` on `/models/veo-video-generator` → 308 to `zeropage.studio`, on `/studio` → 200; `Host: zeropage.studio` → 200. `tsc` via the build and `eslint` on the changed files are clean.

