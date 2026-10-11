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

> **Out of date since 15:07 ET the same day:** PR #235 is merged and live, and every "Live, Google
> is still told…" line below is fixed. What is true now is under "As built", steps 0 and 1. Still
> true below: the `www` 307, the unknown Search Console / Bing state, and `/connector` being a 404
> (its page is on PR #245).

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
- [x] **MIKE:** merge PR #235. *(Merged on his word, 2026-10-11 19:07 UTC, merge commit `5ba4c99`.)*

### 1. Verify live after the deploy
- [x] Run each check:
  - `curl -s https://zeropage.studio/robots.txt | tail -1` → `Sitemap: https://zeropage.studio/sitemap.xml`
  - `curl -s https://zeropage.studio/sitemap.xml | grep -o '<loc>[^<]*' | head -3` → all `https://zeropage.studio…`
  - `for p in "" pricing models faq models/kling-video-generator; do curl -s https://zeropage.studio/$p | grep -o '<link rel="canonical"[^>]*>'; done` → five `zeropage.studio` canonicals
  - `curl -s https://zeropage.studio/ | grep -c 'application/ld+json'` → 1
  - `curl -sI https://zpf-web.vercel.app/models/veo-video-generator | grep -i location` → `https://zeropage.studio/models/veo-video-generator`
  - `curl -sI https://zpf-web.vercel.app/studio | head -1` → still 200 (the studio is not redirected)
  - Done when: all six answer as above.
- [x] *(Not needed: the canonicals are right, so the variable is unset or already correct. It was not read.)* If the canonicals still name the Vercel host, `NEXT_PUBLIC_SITE_URL` is set on Vercel to the old value. In `web/`: `vercel env ls --scope zero-page-ai` (names only). **MIKE, ask first:** remove it, or set it to `https://zeropage.studio`, then redeploy.
  - Done when: the canonical check above passes.
- [x] *(Checked with the session already in Mike's Chrome; a fresh sign-in with credentials was not done, see "As built".)* Sign in at `https://zeropage.studio` with Mike's account (no spend), open a scene, press Open in Director from the classic `/ui` if he uses it.
  - Done when: sign-in lands on `https://zeropage.studio/studio`, and the Director link opens under `zeropage.studio/studio/...`.

### 2. Domain and search accounts (MIKE)
- [x] *(Done by the session on Mike's word, 2026-10-11: see "As built", step 2.)* **MIKE:** Vercel → project `zpf-web` → Settings → Domains → `www.zeropage.studio` → redirect to `zeropage.studio` as **308 Permanent**.
  - Done when: `curl -sI https://www.zeropage.studio/ | head -1` shows 308.
- [x] *(Property added and verified, sitemap submitted; Google's first status for it was "Couldn't fetch", so the "Success" line is still to be read: see "As built".)* **MIKE:** Google Search Console → add a **Domain** property for `zeropage.studio` (a DNS TXT record at the registrar), then Sitemaps → submit `https://zeropage.studio/sitemap.xml`.
  - Done when: the sitemap shows "Success" with the page count (17 today).
- [x] *(`/` is on Google with its own canonical; indexing requested for the Veo page.)* **MIKE:** URL Inspection on `https://zeropage.studio/` and `https://zeropage.studio/models/veo-video-generator` → Request indexing.
  - Done when: both show "Indexing requested" or "URL is on Google", with Google's chosen canonical on `zeropage.studio`.
- [ ] *(Still Mike's: Bing asks for a sign-in, which a session cannot do. With the Search Console property in place it is "Import from Google Search Console".)* **MIKE:** Bing Webmaster Tools → import the site from Search Console (Bing feeds ChatGPT search and Copilot).
  - Done when: Bing lists the sitemap.
- [x] *(Home: one valid Software App item. Model page: no item listed, and nothing to fix: see "As built".)* Rich Results Test (search.google.com/test/rich-results) on `https://zeropage.studio/` and one `/models` page.
  - Done when: both parse with no errors (Organization / SoftwareApplication on the home page, FAQPage on the model page).

### 3. A `/connector` page (after PR #221 is merged)
- [x] *(Live since PR #245 merged on Mike's word, 2026-10-11 19:35 UTC: 200, and the 18-URL sitemap lists it.)* Add `/connector` with the existing landing components, copy only: what the connector does; two addresses — `https://api.zeropage.studio/mcp/claude` for Claude (writes and prices scenes; the render is approved in the studio through `approve_url`) and `https://api.zeropage.studio/mcp` for ChatGPT and hand-added clients (renders after a quote and a yes); how to add it (sign in once at zeropage.studio, then the consent page); a privacy link. Add it to the sitemap's fixed list. Ask Mike before publishing.
  - Done when: after deploy, `curl -s -o /dev/null -w "%{http_code}" https://zeropage.studio/connector` is 200 and the sitemap lists it.
- [x] Put the URL in `docs/directory/TWO_LISTINGS.md` as the docs URL for both listings and tick step 6 of `task-directory-submission.md`.

### 4. `/make` pages: from 1 to 12 (Mike approves the list before any is built)
- [x] *("Go", 2026-10-11, with the two slugs below written the honest way.)* **MIKE:** approve, cut or add to this list. Each is a real search phrase the studio can serve today; the slug is the phrase.
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
- [x] *(Live since PR #252 merged on Mike's word, 2026-10-11 20:25 UTC, with text-only overviews. None has media yet: that is still to pick. See "As built", step 4.)* Per approved slug, one entry in `web/src/landing-pages/entries/`, following the checklist in `task-landing-pages-edit.md` (copy, media, signature, accent, related, check). One commit per page: `feat(web): /make/<slug> -- <what it says>`. Media: renders Mike picks; with none that fit, leave the gradient plates and list the page for him.
  - Done when: each page builds, passes the gates and appears in `/sitemap.xml`.
- [x] *(On the branch: the footer's Tools column and the header's Solutions panel list all twelve, one click from any page.)* Link them: footer and "More to make" reach every `/make` page within two clicks of `/`.
  - Done when: in the browser, every new page is reachable from `/` by links.

### 5. Model pages stay in step with the studio
- [x] Compare the ten `/models` pages with `fal.VIDEO_MODELS` / `fal.IMAGE_MODELS`. A model the studio offers with no page gets an entry; a page for a model it dropped gets its copy corrected, never silently removed. Write the table (model → page → status) under "As built" here.
- [x] Add to `web/src/landing-pages/README.md`: a new model in the studio gets its page the same week. *(On the branch, commit `dd2af7f`; it reaches main with that branch's PR.)*

### 6. Open items from the landing-page task
- [x] Per-page OpenGraph cards (`app/<section>/[slug]/opengraph-image.tsx`); every page names the root card today. *(On the branch, commit `dd2af7f`.)*
- [x] Re-measure mobile Lighthouse on `/make/ai-product-ad-generator`; update line 71 of `task-landing-pages-edit.md` with the number. *(79 / 81 / 73; the line is rewritten on the branch.)*

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

### Step 1, live after the merge (2026-10-11, ~15:10-15:25 ET)

PR #235 merged at 19:07:12 UTC as `5ba4c99`; its branch is deleted. The Vercel build was live about
two minutes later. `Fly Deploy` for `5ba4c99` finished with success, Fly shows release v267 complete,
and the deployed config reads `DIRECTOR_FRONTEND_URL = https://zeropage.studio/studio/flows`.

The six checks, as written above, all answer as expected:

| Check | Answer |
|---|---|
| `robots.txt` last line | `Sitemap: https://zeropage.studio/sitemap.xml` |
| sitemap | 17 URLs, all `https://zeropage.studio…`, none on another host |
| canonicals on `/`, `/pricing`, `/models`, `/faq`, `/models/kling-video-generator` | five, each the page's own URL on `zeropage.studio` |
| home `application/ld+json` (`grep -c`) | 1 |
| `zpf-web.vercel.app/models/veo-video-generator` | 308, `location: https://zeropage.studio/models/veo-video-generator` |
| `zpf-web.vercel.app/studio` | 200 |

Beside them:
- The home JSON-LD parses: Organization, WebSite, SoftwareApplication, every URL `https://zeropage.studio`,
  the offer `lowPrice` 15 / `highPrice` 95 / `offerCount` 3 off `pricing.json`. The logo it names answers 200.
- Share image: `/` names `/opengraph-image` (200, image/png). `/og.jpg` is still a 404 and no page names it.
- The Vercel host also sends `/`, `/pricing`, `/faq`, `/terms`, `/sitemap.xml`, `/robots.txt` and the
  ad page to the real domain (308 each). It does NOT redirect `/signin` (200), `/auth/handoff` or
  `/api/*` (401 with no session), which is what keeps sign-in working on either host.
- API after the deploy: `/healthz` 200 on both hosts, an unsigned POST to `/mcp/` is 401.

The signed-in check:
- With no session, "Sign in" on `zeropage.studio/studio` goes to
  `https://api.zeropage.studio/signin?next=https%3A%2F%2Fzeropage.studio%2Fstudio`, and `/ui` on the
  API answers 303 to the same address.
- With the session already in Mike's Chrome: that sign-in address lands on
  `https://zeropage.studio/studio`, signed in (`/api/me` 200, workspace `zeropage`).
- The classic shell (`https://api.zeropage.studio/ui?legacy=1`) carries
  `data-director-url="https://zeropage.studio/studio/flows"`. The address its Open in Director
  builds for scene 375 (`…/studio/flows?concept=375&shot=1`) lands on
  `https://zeropage.studio/studio/scene/375?shot=1` with the canvas drawn.
- **Not done:** a fresh sign-in typed with a password or through Google / Discord. A session
  cannot enter credentials. The handoff it ends in is the same one the already-signed-in path took.

Left for step 2: `https://www.zeropage.studio/` still answers 307 to the apex.

### Step 2, the domain and the search accounts (2026-10-11, ~15:20-15:40 ET)

Mike said to go ahead with these. What was done, and what is still his:

- **`www` is a 308 now.** `www.zeropage.studio` was not a domain on the Vercel project at all, which
  is why it answered with Vercel's default 307. It was added to project `zpf-web` as a redirect to
  `zeropage.studio` with status 308 (one API call through the signed-in Vercel CLI). Checked:
  `/`, `/pricing` and a model page with a query string each answer 308 to the same path on the
  apex. To undo it, remove the domain from the project.
- **Search Console.** The Google account in Mike's Chrome had no properties. `zeropage.studio` was
  added as a Domain property; Google's TXT record (`google-site-verification=…`) was added at the
  apex on Vercel DNS (`vercel dns add`, record `rec_495f24fb903c5a6400c0f49b`) and resolved
  publicly within seconds; "Ownership verified". **Leave that TXT record in place**: removing it
  un-verifies the property.
- **Sitemap.** `https://zeropage.studio/sitemap.xml` submitted, "Sitemap submitted successfully".
  The row's first status was **"Couldn't fetch"**, which is what Search Console usually shows
  until its first read. The sitemap answers 200 `application/xml` to a Googlebot user agent and
  `robots.txt` allows it. **To check tomorrow:** the row should read "Success" with 18 pages (29
  once the `/make` pages are live).
- **Indexing.** `https://zeropage.studio/` : "URL is on Google", last crawled 3:14 PM ET the same
  day (seven minutes after the merge), user-declared canonical `https://zeropage.studio/`,
  Google-selected canonical the same URL. `https://zeropage.studio/models/veo-video-generator`:
  "URL is unknown to Google", then **indexing requested**.
- **Rich Results Test.** Home: "1 valid item detected", Software Apps, "Zero Page Studio", with
  one non-critical note: `aggregateRating` is missing, which is on purpose (no ratings are
  printed). Veo page: "No items detected". Its FAQPage block is well-formed (nine questions, each
  with a name and an answer); Google lists FAQ results only for government and health sites, so
  there is nothing to fix. The block still serves other readers.
- **Bing: not done.** Bing Webmaster Tools asks for a sign-in, and a session cannot sign in or
  create an account. It is Mike's: sign in at bing.com/webmasters and choose "Import from Google
  Search Console".

### Step 3, live (2026-10-11, 19:35 UTC)

PR #245 merged on Mike's word as `348fd74`; its branch is deleted. PR #244 (the connector's
`add_element`, the still on `/mcp`, draft scenes) had merged eighteen minutes earlier, so the page
was reworded before the merge (commit `674b058`) and describes what Fly release v270 serves.
Live: `/connector` 200; the sitemap has 18 URLs and lists it; canonical and og:url are its own;
the Vercel host answers 308 for it; the footer links it. The share cards are live too: a model
page's og:image is its own card (200, image/png, about 500 KB) and an unknown slug's card is 404.
`docs/directory/TWO_LISTINGS.md` has the docs URL under "Listing materials", and the first two
boxes of step 6 in `task-directory-submission.md` are ticked.

### Step 4, live (2026-10-11, 20:25 UTC)

PR #252 merged on Mike's word as `6434fc5` after he asked for the overviews to be text only; its
branch is deleted. (Its first CI run failed on one test, `test_skills`, which was `main`'s own
failure from another change and was fixed on `main` meanwhile; the branch took `main` in and the
full suite passed on that exact commit.) Live: all twelve `/make` pages answer 200 with their own
canonical and one `h1`; the sitemap has 29 URLs; no page draws a media slot; a new page's share
card answers 200; the Vercel host answers 308 for them. Search Console was not told again: the
sitemap it already has lists them. **Still to do: pick media for the eleven** (README: "Since
2026-10-11 there are eleven more…" says what to change on an entry when a still is picked).

### Step 4, as it was built (2026-10-11, on `claude/seo-make-pages`)

One entry each on the existing template, one commit each, after a groundwork commit (`cda2808`).
Each entry's top comment lists what its sentences were checked against.

| Page | Says | Arrangement after the hero |
|---|---|---|
| `/make/ai-video-generator` | the whole studio: write, hold to photos, price, render, finish | overview, features (grid), models, how-to, FAQ |
| `/make/text-to-video` | words become a still first, then the shot | overview, how-to, features (list), models, FAQ |
| `/make/image-to-video` | a scene from your picture, or a camera move on it | overview, features (split), how-to, models, FAQ |
| `/make/ai-commercial-maker` | a brand's brief, a priced plan, one cut in three shapes | overview, features (grid), how-to, models, FAQ |
| `/make/ai-short-film-maker` | a film scene by scene, cut in the editor | overview, features (split), models, how-to, FAQ |
| `/make/ai-music-video-generator` | pictures for a song you bring | overview, how-to, features (grid), models, FAQ |
| `/make/ai-storyboard-generator` | timed shots and a still for each | overview, how-to, features (grid), FAQ, models |
| `/make/consistent-character-video` | a person saved once as an element | overview, features (list), how-to, FAQ, models |
| `/make/ai-instagram-reels-maker` | vertical scenes in one look | overview, features (split), how-to, models, FAQ |
| `/make/ai-tiktok-video-generator` | a cheap draft, a second take, effects on a still | overview, how-to, features (list), models, FAQ |
| `/make/ai-youtube-shorts-maker` | scenes up to 30 seconds, joined and captioned | overview, features (grid), models, how-to, FAQ |

**What Mike has to know before saying yes to any of them:**

- **None has media, and the overviews are text only** (Mike's call the same day, after seeing the
  first version: three or four empty coloured plates a page). `overview-section.tsx` now draws an
  overview with no media anywhere as numbered rows, the claim on the left and the sentences on the
  right; the model pages, whose blocks all have media, are unchanged. No still or clip was picked
  (his to pick), so no page draws a wall either. The README's rule that no two pages
  share a hero, signature and wall cannot be met yet: all eleven are a centred hero with no
  signature and no wall, told apart by copy, accent and the order above. The existing signatures
  are each tied to one model's media (the shot timeline says "its own Seedance 2.5 clip"), so none
  was reused. The second hero button goes to the steps, since there are no examples to see.
  Their share cards are the plate with the page's name and no still.
- **The two slugs that could not be written as worded** are written the honest way:
  `text-to-video` says the words become a still first and that a clip from words alone is not
  offered; `ai-music-video-generator` says the studio makes no music, finds no beat and has no
  lip sync, and is about pictures for a song you upload.
- **The three social pages** say one fact about each platform (it takes vertical video) and that
  the studio does not post, schedule or connect to an account. They differ by angle: Reels is the
  look, TikTok is speed and effects, Shorts is length and story. The Shorts FAQ tells the reader
  to check YouTube's own length limit, because the studio does not know it.
- **No storyboard export exists** (no PDF, no contact sheet) and the storyboard page says so.
- **Claims narrowed while writing**, each after reading the code: a single shot's still is drawn
  again by changing that shot's line (an already-drawn still is not redrawn on its own); a cut is
  opened from a render or a rendered scene, not from a multi-select in the Library; the "cheapest"
  sentence on the TikTok page quotes the catalog's least expensive row and is not called a floor.
- **The header changed for every public page:** the Solutions panel is two columns of names once
  there are more than four `/make` pages (twelve two-line rows were taller than a laptop screen).
- **Checked:** `npm run typecheck`, `eslint src` (0 errors), `node --test` (172 pass), `next build`
  (12 `/make` pages and 23 share cards prerendered); every page answers 200 with one `h1`, one
  JSON-LD block and a description of 160 characters or fewer; the sitemap has 29 URLs; no page
  scrolls sideways at 375 px (measured in a 375 px frame on all twelve); the three feature layouts
  and the Solutions panel looked at in Chrome.

### The privacy policy and the connector (2026-10-11, branch `claude/privacy-connector`)

Not a step of this task, but found by it: `/connector` linked to a policy that did not mention
the connector, and both directories ask for one that does. Mike said to write it. The policy
(both copies: `web/src/app/privacy/page.tsx` and `app/templates/privacy.html`) gains a section,
"Connecting a chat app", dated 11 Oct 2026: how a connection is made and that the token is
Supabase's and is not kept; what the chat app can read and do; that the connector's answers go to
the chat app's company (Anthropic for Claude, OpenAI for ChatGPT) and are under that company's
policy from there; what the Studio receives and that no tool takes the conversation; what is
recorded; and that a disconnect is made in the chat app and is never seen by the Studio. Each
sentence was checked against `src/mcp_server.py`, `app/mcp_auth.py`, `app/oauth_consent.py`,
`src/mcp_connections.py`, `app/mcp_mount.py` and `refbin.fetch_public_image`. The API copy also
said renders land "in your Queue"; it says Library now, like the site's copy. It is legal text:
it waits for Mike to read it (PR #258).

One thing the writing turned up: a clip and a still spent from a chat need the quote's signed
token, but a scene's keyframes do not (`approve` with `what="keyframes"` prices the strip itself
and checks only the balance). So the policy and `/connector` promise only that the chat app is
given a price and told to show it and wait, and say the Studio cannot see whether it did. Making
keyframes need a token is a separate change, flagged and not started.

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

### Steps 3, 5 and 6, built ahead of the merge (same session, 2026-10-11)

Step 0's heading says "before anything else". These were built anyway while PR #235 waited on Mike,
because none of them goes live without him: they sit on branch `claude/task-seo-pages-ef2826`, which
is `main` at `a2fe0c9` + PR #235's branch + this file + four commits. Its PR's diff is only these
commits once #235 is merged.

**`/connector` (step 3, commit `1ee549a`).** `web/src/app/connector/page.tsx`, copy on the inner
pages' own components (`PageIntro`, the card grid `/models` uses, `FaqList`). Six things the chat can
ask for; the two addresses; four steps; "What it will not do"; six questions with FAQPage JSON-LD.
In the sitemap's fixed list (18 URLs now), the footer's Studio column and the Vercel host's redirect
list. Checked that day:
- both addresses answered live: `/.well-known/oauth-protected-resource/mcp` and `.../mcp/claude` name
  their own `resource`, and an unsigned POST to `/mcp/claude/` is a 401 whose `WWW-Authenticate`
  names the `/mcp/claude` document (so PR #221 is deployed);
- each sentence against `src/mcp_server.py` (`LISTED_TOOLS`, `CLAUDE_LISTED_TOOLS`, the tools'
  descriptions) and `app/templates/oauth_consent.html`; the list is in the page's top comment;
- in the browser at 1440, 768 and a true 375 px (a 375 px frame, since headless Chrome will not
  go narrower than about 500): nothing overflows; the address breaks between host and path;
- on `next build` + `next start`: canonical and og:url are `https://zeropage.studio/connector`,
  `Host: zpf-web.vercel.app` on it answers 308 to the real domain.
- The page prints no price, plan or rating, and does not say the connector is in either directory.
- **Still to do after it is live:** the two boxes under step 3 (the 200 check; the URL into
  `docs/directory/TWO_LISTINGS.md` and step 6 of `task-directory-submission.md`).
- **For Mike to read before saying yes:** (1) the ChatGPT card says only "ChatGPT and other clients"
  and "add the second address the way that client adds a connector": nobody has added it in ChatGPT
  yet (TWO_LISTINGS step 6), so the page gives no ChatGPT menu path. (2) The contact printed is the
  address `/terms` and `/privacy` already print. (3) The privacy policy has no words about the
  connector (a chat app reaching the workspace over OAuth); the page links to the policy as it is.
  Both directories ask for a policy that covers the connector, so that section is worth writing.

- **PR #244 merged first (19:17 UTC), so the page was reworded before this one merged.** The
  connector now has `add_element` on both addresses (a picture becomes an element from the web
  address of an image, or from one of the person's renders), `image_models` and `generate_image`
  on `/mcp` only (a still, behind a quote and a yes), and a scene with no photos is saved as a
  draft. Changed to match: "Use your elements", "Write a scene", the ChatGPT card ("Write, price,
  draw and render."), step 1, the example in step 4, two of the limits, and four of the six
  answers. Fly release v270 carries #244, so the page describes what is deployed.

**The other fixed pages' share tags (commit `03b5784`, not in the task's list).** `/pricing`,
`/models`, `/faq`, `/terms` and `/privacy` set only a title and a description, so they inherited the
home page's whole `openGraph` object: each shared as "Zero Page — The AI content studio that creates
for you." with og:url pointing at `/`. `web/src/lib/page-meta.ts` gives each its own. Nothing a
visitor sees changes. Drop the commit if it is not wanted; `/connector` uses the helper too.

**Share cards (step 6, commit `dd2af7f`).** `web/src/landing-pages/og.tsx`: the home card's plate,
the page's name, a chip in its accent, one of its stills (the entry's new optional `card`, else its
first still; a clip's poster counts). All eleven are drawn at build time (12 cards in the prerender
manifest with the home one); an unknown slug's card is a 404. One thing learned by running it: an
image named in a page's `generateMetadata` is used INSTEAD of the file's card, so `route.tsx` names
none now. The cards share one alt text, because giving each its own (`generateImageMetadata`) stops
Next drawing them at build.

**Lighthouse (step 6).** 79, 81, 73 on the live ad page, mobile. The detail and what holds it down
(script, not fonts) are in `task-landing-pages-edit.md`.

### For step 4's list, before Mike approves it

Two slugs promise something the studio does not do as worded today. Checked in the code:

- `text-to-video`: a scene with no reference photo is refused at the render (`approve_render`
  answers `no_reference`). The honest version is two steps the studio does have: draw the first
  frame from the words (an image model, no photo needed), then render the shot from that frame.
  The page can say that, or the slug can be cut.
- `ai-music-video-generator`: the studio generates no music (nothing in `src/fal.py` or
  `src/effects.py` does). It can cut clips to a track you upload in the editor, and add sound
  effects to a clip. The page would have to be about pictures for your own song.

The three platform slugs (`ai-instagram-reels-maker`, `ai-tiktok-video-generator`,
`ai-youtube-shorts-maker`) can say vertical 9:16 clips and one exported MP4. They cannot say the
studio posts anywhere: nothing does.

### Seen on the way, not changed

- `/faq` still describes the idea board ("a scene with no references never reaches the board"),
  which left the product on 2026-10-11. Its other answers were not re-checked.
- The header's desktop nav wraps "How it works" onto two lines at 768 px, on every public page.
- `https://www.googleapis.com/pagespeedonline` answers 429 without a key (the shared daily quota),
  so the Lighthouse runs above are local ones.
