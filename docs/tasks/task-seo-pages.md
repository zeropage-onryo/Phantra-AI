# Task — get zeropage.studio found: fix the domain, then build the SEO pages

**From:** a claude.ai session, 2026-10-11, after the InVideo teardown (project
doc `claude/invideo_growth_teardown_2026-10-11.md`). InVideo's sitemap,
counted that day: ~1,015 FAQ pages, ~1,390 blog posts, 270 free-tool pages,
138 `/make/<use case>` pages, 48 per-model pages. **For:** Claude Code, in
`zeropage-onryo/video-pipeline` on Mike's Mac.
**Mike's call:** the connector ships first (`docs/tasks/task-ship-connector.md`);
SEO pages are next. Standing rules for the public site: build on top of the
existing `web/` app, never replace it; no landing-page change goes live
without his approval.
**Read first:** `web/src/landing-pages/README.md`, then
`docs/tasks/task-landing-pages-edit.md` (the per-page checklist and status),
then `web/src/landing-pages/pages.ts`.

## State right now (checked 2026-10-11)

- **The whole site tells Google its home is `zpf-web.vercel.app`, not
  `zeropage.studio`.** Live: `https://zeropage.studio/robots.txt` names
  `Sitemap: https://zpf-web.vercel.app/sitemap.xml`; the sitemap lists every
  URL on `zpf-web.vercel.app`; `/models/kling-video-generator` carries
  `<link rel="canonical" href="https://zpf-web.vercel.app/...">`. Cause:
  `NEXT_PUBLIC_SITE_URL` is unset on Vercel, and `web/src/app/layout.tsx`,
  `sitemap.ts` and `robots.ts` all fall back to the Vercel URL. Until this is
  fixed, every page built below ranks (if at all) for the wrong domain.
- Pages that exist: `/`, `/pricing`, `/models`, `/faq`, `/terms`, `/privacy`,
  ONE `/make` page (`ai-product-ad-generator`) and TEN `/models/<slug>` pages
  (ltx, wan, kling, seedance, veo, nano-banana, flux, seedream, gpt-image,
  ideogram). One template renders all of them from typed entries in
  `web/src/landing-pages/entries/`; adding an entry adds it to the sitemap.
- `task-landing-pages-edit.md` has 10 of 11 pages done; its open items:
  per-page OpenGraph cards, an image catalogue export, mobile Lighthouse at
  76–84 (six font families preloaded).
- `/connector` → 404. The directory listing needs a docs URL; today that is
  the plugin README.
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

### 0. Point the site at its real domain (do this first, it is one variable)
- [ ] **MIKE, ask first (production env change):** in Vercel → project `zpf-web` → Settings → Environment Variables, add `NEXT_PUBLIC_SITE_URL = https://zeropage.studio` for Production, then redeploy.
  - Done when: `curl -s https://zeropage.studio/robots.txt` ends `Sitemap: https://zeropage.studio/sitemap.xml`, the sitemap's `<loc>`s start `https://zeropage.studio`, and `curl -s https://zeropage.studio/models/kling-video-generator | grep -o '<link rel="canonical"[^>]*>'` shows `zeropage.studio`.
- [ ] Check `zpf-web.vercel.app` either redirects to `zeropage.studio` or keeps the canonical pointing there.
  - Done when: `curl -sI https://zpf-web.vercel.app/models` shows a 308 to `zeropage.studio`, or its canonical tag names `zeropage.studio`. If neither, tell Mike (Vercel → Domains can redirect it).
- [ ] Change the three fallbacks (`layout.tsx`, `sitemap.ts`, `robots.ts`) from `https://zpf-web.vercel.app` to `https://zeropage.studio`, so a missing variable can't silently undo this.
  - Done when: `grep -rn "zpf-web.vercel.app" web/src` returns nothing but comments.

### 1. Search Console
- [ ] **MIKE:** add `zeropage.studio` as a Domain property in Google Search Console (DNS TXT record at the registrar), then submit `https://zeropage.studio/sitemap.xml`.
  - Done when: Search Console shows the sitemap "Success" with the page count from step 0.
- [ ] **MIKE:** same in Bing Webmaster Tools (it can import from Search Console). Bing feeds ChatGPT search and Copilot.

### 2. A `/connector` page (the directory's docs URL, and an SEO page)
- [ ] Add `/connector`: what the Claude connector does (the ten tools in plain words), how to add it (the address, sign in once at zeropage.studio, approve), what it costs (reads and scene writing free; renders in credits after a quote and a yes), privacy link. Copy only, using the existing landing components.
  - Done when: `curl -s -o /dev/null -w "%{http_code}" https://zeropage.studio/connector` is 200 after deploy, and the page is in the sitemap.
- [ ] Once live, swap the directory docs URL to it (`docs/directory/SUBMISSION.md`), and tell Mike to update the portal field if the listing is already submitted.

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
- [ ] Per-page OpenGraph cards (each page names the root's card today).
- [ ] Mobile Lighthouse ≥ 90: stop preloading six font families on every public page (`app/layout.tsx`, shared with `/studio`).
  - Done when: Lighthouse mobile on `/make/ai-product-ad-generator` scores ≥ 90 performance.

### 6. Measure
- [ ] Two weeks after step 1, read Search Console (impressions, clicks, top queries per page) and write the numbers under "As built" here. That decides which kind of page gets made next.

## Done means

- `zeropage.studio` is the canonical domain everywhere a crawler looks, and Search Console has the sitemap.
- `/connector` is live and is the directory's docs URL.
- The approved `/make` pages are live, linked from `/`, and every model the studio offers has a page.
- First Search Console numbers are recorded here.
