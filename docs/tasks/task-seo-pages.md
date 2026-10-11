# Task — get zeropage.studio found by Google

**From:** a claude.ai session, 2026-10-11, after the InVideo growth teardown (project doc
`claude/invideo_growth_teardown_2026-10-11.md`). InVideo's sitemap, counted that day: ~1,015 FAQ
pages, ~1,390 blog posts, 270 free-tool pages, 138 `/make/<use case>` pages, 48 per-model pages.
**For:** Claude Code, in `zeropage-onryo/video-pipeline` on Mike's Mac.
**Mike's call:** "Goal is to get google finding this studio." The connector ships first (PR #221 and
its `docs/tasks/task-directory-submission.md`); SEO pages come after. Standing rules for the public
site: build on top of the existing `web/` app, never replace it; no landing-page change goes live
without his approval.
**Read first:** PR #235's description, then `web/src/landing-pages/README.md`, then
`docs/tasks/task-landing-pages-edit.md` (the per-page checklist and status).

## State right now (checked 2026-10-11, ~13:55 ET)

- **Live, Google is still told the site lives at `zpf-web.vercel.app`.** `https://zeropage.studio/robots.txt`
  ends `Sitemap: https://zpf-web.vercel.app/sitemap.xml`; every sitemap URL and every `/make` and
  `/models` canonical names the Vercel host; `/`, `/pricing`, `/models`, `/faq` carry no canonical;
  the home page has no structured data; `zpf-web.vercel.app` serves the whole site a second time
  (200, no redirect); pages other than `/` name a share image `/og.jpg` that 404s.
- **PR #235 (`claude/seo-canonical-domain`) fixes all of that in code. OPEN, not merged.** Built and
  checked locally with `next build` + `next start` (robots, sitemap and seven canonicals on
  `zeropage.studio`; home JSON-LD parses; `Host: zpf-web.vercel.app` on a public page → 308, on
  `/studio` → 200). It also moves `DIRECTOR_FRONTEND_URL` in `fly.toml` off `zeropage-web.fly.dev`
  (scaled to zero) to `https://zeropage.studio/studio/flows`, so **merging it deploys Fly as well as
  Vercel.** CI was still running at the time of writing.
- PR #235 also carries an earlier, committed copy of this file at `docs/tasks/task-seo-pages.md`
  (and branch `claude/tasks-connector-seo` an older one). This uncommitted file replaces both; step 0
  removes the committed copy from #235.
- **Done:** Fly secret `STUDIO_URL` is `https://zeropage.studio` (Mike set it 2026-10-11; checked:
  `curl -s -o /dev/null -D - https://zeropage-studio.fly.dev/ui` → `location: /signin?next=https%3A%2F%2Fzeropage.studio%2Fstudio`).
- `https://www.zeropage.studio/` answers **307** (temporary) to the apex. A Vercel domain setting.
- `NEXT_PUBLIC_SITE_URL` on Vercel: **unknown from here** (the cloud session got 403 from the Vercel
  API on team `zero-page-ai`). PR #235's fallback is `https://zeropage.studio`, so unset is fine; set
  to the Vercel URL would override the fix.
- Pages that exist: `/`, `/pricing`, `/models`, `/faq`, `/terms`, `/privacy`, ONE `/make` page
  (`ai-product-ad-generator`), TEN `/models/<slug>` pages (ltx, wan, kling, seedance, veo,
  nano-banana, flux, seedream, gpt-image, ideogram). One template renders them from typed entries in
  `web/src/landing-pages/entries/`; adding an entry adds it to the sitemap.
- `/connector` → 404. PR #221's task (its step 6) asks for this page too; do it once, here.
  PR #221 also rewrites `llms.txt` (`app/seo.py`); leave that file to #221.
- Fonts were already fixed on main (`claude/site-fonts`, merged); line 71 of
  `task-landing-pages-edit.md` (Lighthouse 76–84) is stale.
- No other open PR touches `web/src/app/layout.tsx`, `sitemap.ts`, `robots.ts`, `web/next.config.ts`,
  `web/src/landing-pages/`, `app/make` or `app/models` (checked against #142, #194, #221, #223, #225,
  #229–#233).
- Unknown: whether Google Search Console or Bing Webmaster Tools are set up for `zeropage.studio`.

## Rules for this task

- No renders, stills or any generation without Mike's yes in chat. Page media comes from renders that
  already exist (R2 `m/<account>/…` keys via `media.url_for`, or files already in `web/public/`);
  Mike picks which.
- Every claim on a page is something the studio does today. No earnings claims, no invented
  testimonials, ratings or customer logos.
- Never print a secret; names only. Vercel and Fly env changes: ask Mike first.
- Branch for every change; never commit to `main`. A merge to `main` deploys Vercel (and Fly when
  `fly.toml` or the API changes). Mike approves a page before it merges.
- Gates before a commit: `cd web && npx tsc --noEmit`, `npx eslint src`, a look at 375 / 768 / 1440.

## Steps

### 0. Get PR #235 merged (before anything else)
- [x] Check out `claude/seo-canonical-domain`, `git rm docs/tasks/task-seo-pages.md`, commit, push (this file is the live copy now).
  - Done when: `gh api repos/zeropage-onryo/video-pipeline/pulls/235/files --jq '.[].filename'` no longer lists `docs/tasks/task-seo-pages.md`.
- [x] Wait for CI on #235.
  - Done when: `gh api repos/zeropage-onryo/video-pipeline/commits/<head sha>/check-runs` shows `test` and `web` completed with `success`.
- [ ] **MIKE:** merge PR #235.

### 1. Verify live after the deploy
- [ ] Run each check:
  - `curl -s https://zeropage.studio/robots.txt | tail -1` → `Sitemap: https://zeropage.studio/sitemap.xml`
  - `curl -s https://zeropage.studio/sitemap.xml | grep -o '<loc>[^<]*' | head -3` → all `https://zeropage.studio…`
  - `for p in "" pricing models faq models/kling-video-generator; do curl -s https://zeropage.studio/$p | grep -o '<link rel="canonical"[^>]*>'; done` → five `zeropage.studio` canonicals
  - `curl -s https://zeropage.studio/ | grep -c 'application/ld+json'` → 1
  - `curl -sI https://zpf-web.vercel.app/models/veo-video-generator | grep -i location` → `https://zeropage.studio/models/veo-video-generator`
  - `curl -sI https://zpf-web.vercel.app/studio | head -1` → still 200 (the studio is not redirected)
  - Done when: all six answer as above.
- [ ] If the canonicals still name the Vercel host, `NEXT_PUBLIC_SITE_URL` is set on Vercel to the old value. In `web/`: `vercel env ls --scope zero-page-ai` (names only). **MIKE, ask first:** remove it, or set it to `https://zeropage.studio`, then redeploy.
  - Done when: the canonical check above passes.
- [ ] Sign in at `https://zeropage.studio` with Mike's account (no spend), open a scene, press Open in Director from the classic `/ui` if he uses it.
  - Done when: sign-in lands on `https://zeropage.studio/studio`, and the Director link opens under `zeropage.studio/studio/...`.

### 2. Domain and search accounts (MIKE)
- [ ] **MIKE:** Vercel → project `zpf-web` → Settings → Domains → `www.zeropage.studio` → redirect to `zeropage.studio` as **308 Permanent**.
  - Done when: `curl -sI https://www.zeropage.studio/ | head -1` shows 308.
- [ ] **MIKE:** Google Search Console → add a **Domain** property for `zeropage.studio` (a DNS TXT record at the registrar), then Sitemaps → submit `https://zeropage.studio/sitemap.xml`.
  - Done when: the sitemap shows "Success" with the page count (17 today).
- [ ] **MIKE:** URL Inspection on `https://zeropage.studio/` and `https://zeropage.studio/models/veo-video-generator` → Request indexing.
  - Done when: both show "Indexing requested" or "URL is on Google", with Google's chosen canonical on `zeropage.studio`.
- [ ] **MIKE:** Bing Webmaster Tools → import the site from Search Console (Bing feeds ChatGPT search and Copilot).
  - Done when: Bing lists the sitemap.
- [ ] Rich Results Test (search.google.com/test/rich-results) on `https://zeropage.studio/` and one `/models` page.
  - Done when: both parse with no errors (Organization / SoftwareApplication on the home page, FAQPage on the model page).

### 3. A `/connector` page (after PR #221 is merged)
- [ ] Add `/connector` with the existing landing components, copy only: what the connector does; two addresses — `https://api.zeropage.studio/mcp/claude` for Claude (writes and prices scenes; the render is approved in the studio through `approve_url`) and `https://api.zeropage.studio/mcp` for ChatGPT and hand-added clients (renders after a quote and a yes); how to add it (sign in once at zeropage.studio, then the consent page); a privacy link. Add it to the sitemap's fixed list. Ask Mike before publishing.
  - Done when: after deploy, `curl -s -o /dev/null -w "%{http_code}" https://zeropage.studio/connector` is 200 and the sitemap lists it.
- [ ] Put the URL in `docs/directory/TWO_LISTINGS.md` as the docs URL for both listings and tick step 6 of `task-directory-submission.md`.

### 4. `/make` pages: from 1 to 12 (Mike approves the list before any is built)
- [ ] **MIKE:** approve, cut or add to this list. Each is a real search phrase the studio can serve today; the slug is the phrase.
  1. `ai-video-generator`
  2. `text-to-video`
  3. `image-to-video`
  4. `ai-short-film-maker`
  5. `ai-music-video-generator`
  6. `ai-commercial-maker`
  7. `ai-instagram-reels-maker`
  8. `ai-tiktok-video-generator`
  9. `ai-youtube-shorts-maker`
  10. `consistent-character-video`
  11. `ai-storyboard-generator`
  - Done when: Mike has replied with the final list.
- [ ] Per approved slug, one entry in `web/src/landing-pages/entries/`, following the checklist in `task-landing-pages-edit.md` (copy, media, signature, accent, related, check). One commit per page: `feat(web): /make/<slug> -- <what it says>`. Media: renders Mike picks; with none that fit, leave the gradient plates and list the page for him.
  - Done when: each page builds, passes the gates and appears in `/sitemap.xml`.
- [ ] Link them: footer and "More to make" reach every `/make` page within two clicks of `/`.
  - Done when: in the browser, every new page is reachable from `/` by links.

### 5. Model pages stay in step with the studio
- [ ] Compare the ten `/models` pages with `fal.VIDEO_MODELS` / `fal.IMAGE_MODELS`. A model the studio offers with no page gets an entry; a page for a model it dropped gets its copy corrected, never silently removed. Write the table (model → page → status) under "As built" here.
- [ ] Add to `web/src/landing-pages/README.md`: a new model in the studio gets its page the same week.

### 6. Open items from the landing-page task
- [ ] Per-page OpenGraph cards (`app/<section>/[slug]/opengraph-image.tsx`); every page names the root card today.
- [ ] Re-measure mobile Lighthouse on `/make/ai-product-ad-generator`; update line 71 of `task-landing-pages-edit.md` with the number.

### 7. Measure
- [ ] Two weeks after step 2, read Search Console (impressions, clicks, top queries per page) and write the numbers under "As built". They decide which kind of page comes next.

## Done means

- `zeropage.studio` is the only home a crawler sees: robots, sitemap, canonicals, JSON-LD, and the Vercel host and `www` both redirect permanently.
- Search Console and Bing have the sitemap, and the home page is indexed under `zeropage.studio`.
- `/connector` is live and is the directory's docs URL.
- The approved `/make` pages are live and linked from `/`; every model the studio offers has a page.
- First Search Console numbers are recorded here.

## As built

### Where this file lives (2026-10-11)

The file was written uncommitted in the main checkout. A Claude Code session in a worktree cannot
write there (the worktree guard refuses the edit), so the copy with the ticks and these notes is on
branch `claude/task-seo-pages-ef2826`. The uncommitted copy in the main checkout is the same text
without them. Delete it there before that checkout pulls a `main` that contains this file, or the
pull stops on "untracked working tree files would be overwritten".

### Step 0 (2026-10-11, ~14:15 ET, a Claude Code session on the Mac)

- Commit `6af23c2` on `claude/seo-canonical-domain` removes the committed copy of this file from
  PR #235. The PR's file list is now eleven files, none under `docs/`.
- CI on `6af23c2`: `test` success (both runs, about ten minutes each), `web` success (both runs),
  Vercel preview success, `eval-gate` skipped. GitHub reports the PR `MERGEABLE` / `CLEAN`.
- The branch is 30 commits behind `main`. Both sides changed `fly.toml` (main moved
  `ZEROPAGE_MCP_RESOURCE` to `api.zeropage.studio`; the PR moves `DIRECTOR_FRONTEND_URL`); the two
  edits are on different lines and `git merge-tree` against `main` at `a2fe0c9` reports no conflict.
- Read the PR's code diff before handing it over. The two files its metadata points at exist on the
  branch (`web/public/brand/zp_black_favicon_512.png`, `web/src/app/opengraph-image.tsx`).
- **Waiting on Mike:** merge PR #235 (it deploys Vercel and Fly).

### Step 5, read ahead of time (same session; no page was changed)

Compared with `src/fal.py` on `main` at `a2fe0c9`. Every model the studio offers is on a page.

| Model in the studio | Table | Page | Status |
|---|---|---|---|
| `ltx2.5`, `ltx2.5-fast`, `ltx2.3` | video | `/models/ltx-video-generator` | all three in `modelIds` |
| `wan3` | video | `/models/wan-video-generator` | in `modelIds` |
| `kling3-turbo-pro` | video | `/models/kling-video-generator` | in `modelIds` |
| `seedance2.5`, `seedance2`, `seedance2-fast` | video | `/models/seedance-video-generator` | all three in `modelIds` |
| `veo3.1` | video | `/models/veo-video-generator` | in `modelIds` |
| Nano Banana (Gemini key) and `nano-banana-pro` (fal) | image | `/models/nano-banana-image-generator` | in `modelIds` |
| `flux2-pro` | image | `/models/flux-image-generator` | in `modelIds` |
| `flux-pro1.1` | image | `/models/flux-image-generator` | named in the page's FAQ and model cards, NOT in `modelIds` |
| `seedream4.5` | image | `/models/seedream-image-generator` | in `modelIds` |
| `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, `gpt-image-2` | image | `/models/gpt-image-generator` | all three in `modelIds` |
| `ideogram4.5` | image | `/models/ideogram-image-generator` | in `modelIds` |

No page sells a model the studio dropped. The one loose end is `flux-pro1.1`: the LTX and GPT pages
list their older family members in `modelIds` and the FLUX page does not. Nothing on the site links
by that id today (`/models` draws one image card per page, off the page's first id), so nothing is
broken; adding the id is a one-line change for consistency.
