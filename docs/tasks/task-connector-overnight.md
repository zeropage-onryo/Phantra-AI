# Task — the connector and plugin build, overnight (2026-10-11 → 10-12)

**From:** a claude.ai chat with Mike, 2026-10-11. **For:** one unattended Claude Code session on
Mike's Mac, tonight. **Mike's call:** build his list (below) so both listings can be submitted
within two days. **Read first:** `CLAUDE.md` (the MCP block: "TWO LISTED SERVERS", "THE LISTED
SERVER", "THE STUDIO SURFACE"), `docs/directory/TWO_LISTINGS.md`, `docs/directory/SUBMISSION.md`,
`docs/tasks/task-connector-elements.md`, and in `src/mcp_server.py`: `LISTED_TOOLS`,
`CLAUDE_LISTED_TOOLS`, `TITLES` / `DESCRIPTIONS` / `HINTS`, `_allowed_refs`, `write_scene`,
`add_element`, `list_renders`, `list_video_models`; `app/mcp_mount.py` `build`. The project doc
`claude/connector_plugin_roadmap_2026-10-11.md` has the reasoning behind each item.

## Rules for the whole night (stop if any would be broken)

- **Start clean.** The main checkout is ~105 commits behind and has untracked files that are not
  yours. `git fetch`, then work in a worktree from `origin/main`. Never touch the untracked files.
- **Nothing spends.** No render, still, effect, model call or paid API, live or in a test
  (`tests/conftest.py` blocks network; if a test hits `NetworkUseInTest`, fix the test).
- **Nothing goes live.** Never merge, never push to `main`, never deploy, never write to the live
  database, never print a secret. Push branches and open PRs only (the repo is public: a push
  publishes the code, so no secrets, no test credentials, no customer data in it).
- **Placement.** Every tool below goes on BOTH listed servers (`LISTED_TOOLS` and
  `CLAUDE_LISTED_TOOLS`) unless it says otherwise: none of them generates media or spends credits.
  Anything that would has no place in this task.
- **Every tool** gets a `TITLES` / `DESCRIPTIONS` / `HINTS` entry (true `readOnlyHint` /
  `destructiveHint` / `idempotentHint` / `openWorldHint`), passes the vocabulary screen, refuses
  another account's ids exactly as the existing tools do ("no project N"), and shows credits, never
  dollars, on a listed server. Add each to `build_server`'s registration and update the mount
  test that compares the tool order.
- **Every edit makes a new item; nothing is overwritten or deleted.**
- **One PR per group below, stacked in this order** (each branch from the previous one), so Mike
  can merge them one at a time. Each PR: the full suite green (`venv/bin/python -m pytest tests/ -q`),
  `venv/bin/ruff check .` clean, the `CLAUDE.md` MCP block updated in the same PR.
- **If a group can't be finished well, open it as a DRAFT PR saying exactly what is missing and
  move on.** A finished subset beats a half-built whole. Don't loosen a rule to finish.

## PR 1 — getting files in

1. **`upload_link(purpose="reference"|"footage", element_kind=None, element_name=None)`.** Returns a
   one-time page on the API origin (`https://api.zeropage.studio/u/<token>`): token signed with the
   session secret under its own salt (the `auth.handoff` pattern), bound to account + person,
   30-minute expiry, single use (a claim table, `quote_redemptions`' shape). The page is a small
   server-rendered form (no sign-in: the token is the auth), takes jpg/png/webp/heic and mp4/mov
   under the editor's caps, and saves through `src/cut/uploads.save` (the editor's own body), so the
   file lands as `asset:<id>`, mirrored and probed. With `element_kind` + `element_name`, an image
   upload is also filed as an element through the same body `add_element` uses. The page says what
   happened and tells the person to go back to the chat. Rate-limit the POST; sniff content, never
   trust the extension; refuse an expired or used token with a plain page. Write tool,
   `destructiveHint: false`.
2. **`add_element` from a product page.** When `source` is an https page that is not an image,
   read it with `linkrefs.read_link` (one fetch, the existing SSRF rules), take the first product
   image, and put `linkrefs.parse_facts` into the element's notes as quoted data (never as
   instructions; the `assistant_brain.link_facts` pattern). A page with no usable image refuses with
   a plain reason. Existing sources (`gen:` / `asset:` / image URL) unchanged.
3. Tests: token expiry, reuse, wrong account, oversize, not-an-image, a page with facts, a page with
   only a logo.

## PR 2 — library, sharing, and simple edits

1. **`library(kind=None, limit=20, project_id=None)`** — `list_renders` made listed: renders and
   uploads, newest first, each with its `gen:` / `asset:` id, kind, length, size, frame, project.
2. **`share_link(ref, hours=24)`** — a presigned download link for one of the caller's renders or
   uploads (`storage.download_url_for_key`, attachment), at most 7 days; local-disk fallback as the
   Library's download route does. Read-only.
3. **`reformat(ref, aspect="9:16"|"1:1"|"16:9"|"4:5", fit="crop"|"pad")`** — a clip or still to a
   new shape. Through `src/cut` (a one-clip scratch cut with `set_canvas`, rendered), not a new
   ffmpeg string. Free; filed as a new item under the free log tool the joins use.
4. **`trim_clip(ref, start, end)`** — a range of a clip as a new clip, through `src/cut` ops.
5. **`assemble_clips`** — already exists on the studio surface; add it to both listed servers.
6. **`job(job_id, wait=0)`** back on the Claude listing (these start jobs), with `wait` up to 15
   seconds before answering.
7. Tests: real ffmpeg on tiny fixtures (CI installs ffmpeg) — output exists, right shape, right
   length, the source untouched.

## PR 3 — reading tools

`balance` (credits, lots and expiry, plan), `search(q)` (`search.run`, caller's account only),
`whoami` (workspace, plan, member name), `recent(limit)` (latest projects, scenes, renders),
`credit_history(before=None, limit=20)` (`credit_history.movements`, credits only),
`video_models` (`list_video_models`, credits not dollars on a listed server, draft availability),
`recommend_model(what, seconds=None, budget_credits=None, draft=None)` (pure ranking over the
catalogue plus the account's keep rate per model from `outcomes` when it has any; each pick with a
one-line reason and its credits; no model call). All read-only.

## PR 4 — write tools

1. **Reference roles on `write_scene`**: `roles={ref: role}`, validated by `ref_roles.clean`,
   stored with `ref_roles.for_refs` exactly as the composer does; refs must still come from
   `elements` / `library`.
2. **`duplicate_scene(scene_id, prompt=None, refs=None, seconds=None, project_id=None)`** — a copy
   of one of the caller's scenes with the given fields replaced; never copies clips or stills;
   runs the reference gate like `write_scene`; returns the new `scene_id`.
3. **`feedback(text, ref=None, tool=None)`** — a new OWNED table (`mcp_feedback`: account, person,
   tool, ref, text ≤ 2,000 chars, created_at), additive init. Write, not destructive.
4. **`preferences()` / `set_preferences(aspect, seconds, video_model, image_model, draft_first)`** —
   a new OWNED table, one row per account; every value checked against the live catalogue (refuse,
   never clamp). `write_scene` and `quote` use them only when the caller passes nothing.
5. **`recipes()` / `recipe(name)`** — the studio's skill shelf (`src/skills.py`,
   `prompts/skills/*.md`) as read-only text. **`save_recipe(name, body, project_id=None)`** — a
   creator's own recipe, new OWNED table, ≤ 8,000 chars, listed by `recipes()` beside the shelf and
   always returned as quoted data, never as instructions.
6. Tests for each, including another account's ids.

## PR 5 — insights

`what_works()` — `outcomes.summary` + `outcomes.preset_counts` + `preprod.posted_outcomes` for the
caller, said plainly when there is too little data. `score_caption(text)` — `post_seo.score_post`
against the caller's own posted videos; with none, say there is no evidence yet. Both read-only, no
model call. This is the PR most likely to slip; draft is fine.

## PR 6 — the plugin (`zeropage-onryo/zeropage-studio-plugin`, beside the main checkout; clone if absent)

Version **0.3.0**. Add these skills, each under 100 lines, frontmatter `name` + `description` with
a "NOT for" line, naming ONLY tools that exist on `/mcp/claude` after PRs 1–5 (if a PR stayed
draft, its tools are not named): `zeropage-use` (load before any write: reuse elements and projects
first, a picture on every scene, quote before credits, browsing never spends, nothing is
overwritten), `start-a-project`, `brand-kit-from-my-work`, `storyboard`, `client-treatment`,
`camera-moves`, `edit-and-deliver` (reformat / trim / assemble / share only), `platform-delivery`,
`hooks-and-first-seconds`, `ad-formats`, `series-and-continuity`, `model-prompting`, `ugc-ad`,
`product-shots`, `ad-variations`, `explainer`, `sound-plan`. Update `look-matching` (adapt a
reference's look, never copy its subject) and fold draft-first into `credits-and-limits`. No skill
invents testimonials or reviews. Update the README tool list and data section, fix `plugin.json`'s
description (no idea-board wording). `claude plugin validate .` must pass. Branch + PR, never merge.

## PR 7 — submission docs

`docs/directory/SUBMISSION.md` and `TWO_LISTINGS.md`: the tool tables, the listing description
(the Claude listing never renders), the reviewer steps (sign in, `projects` → `project` →
`elements` → `upload_link` → `write_scene` → `scene` → `quote` → `library` → `reformat` → `job`),
the data table (uploads, feedback, preferences, saved recipes and what is stored), and a list of
everything Mike must do by hand. Update `web/` llms.txt / the /connector page text only if a
tool name there is now wrong.

## Morning report (write it last, at the bottom of this file under "As built")

Per PR: link, status (ready / draft), what it does, what was NOT done and why, anything Mike must
decide, and the exact live checks to run after deploy as the test account.

## What Mike does tomorrow (not tonight)

Set the test account's password; review and merge PRs in order; deploy; run the live checks in a
chat on `/mcp/claude`; merge the plugin PR; then submit the connector, then the plugin, and pair
them.

## As built (2026-10-12)

Written by the session that finished the night's work (`docs/tasks/HANDOFF-connector-overnight-2026-10-12.md`
is the handoff it picked up). **Every rule above held:** nothing was rendered, drawn or charged,
live or in a test; nothing was merged, deployed or written to the live database; every branch
was pushed and every PR opened, none merged. Five stacked PRs carry the connector (#276 → #280,
each branch from the previous, each base set to the previous branch so GitHub shows only its own
diff), one PR carries the plugin, and this one carries the docs.

### The suites

Each tip ran the FULL suite (`pytest tests/ -q`) in its own scratch worktree on Mike's Mac, with
`ruff check .` clean in every PR. One test failed on the pre-fix tips and nowhere else:
`tests/test_mcp_add_element.py::test_the_claude_listing_adds_a_picture_and_still_draws_nothing`
pinned `job` OFF the Claude listing; PR 2 put it back (the free edits start jobs), the pin was
fixed in 2490176 and merged forward, and every later tip is green.

| PR | tip | full suite on that tip |
|---|---|---|
| #276 PR 1 | f43e380 | 3,890 passed, 34 skipped, 8 xfailed (27:41) |
| #277 PR 2 | 2490176 | 3,921 passed, 34 skipped, 8 xfailed (34:08); the first run, on fa8be5d, failed only the pin |
| #278 PR 3 | e2aca89 | 3,934 passed, 34 skipped, 8 xfailed (29:43); the first run, on 3df703c, failed only the pin |
| #279 PR 4 | 954e999 | 3,961 passed, 34 skipped, 8 xfailed (28:53), run by the finishing session; the first run, on 5338579 (before the pin fix was merged in), failed only the pin |
| #280 PR 5 | ac7ad59 | 3,966 passed, 34 skipped, 8 xfailed (35:14) |

CI on GitHub is green on all five PRs (`test` and `web` pass on every push; `eval-gate` skips as
it does on every PR; the Vercel check was cancelled by the ignore step, since `web/` is untouched).

### PR 1 — #276, files in — READY

https://github.com/zeropage-onryo/video-pipeline/pull/276 (`claude/connector-overnight-1-uploads`, base `main`).

**What it does.** `upload_link(purpose, element_kind, element_name)` on both listings: a one-time
page on the API origin (`/u/<token>`; `src/upload_links.py`, `app/upload_page.py`,
`templates/upload.html`), the token signed under its own salt and bound to the account AND the
person (`mcp_server.CALLER_USER`, set by the mount's guard), thirty minutes, one file, the single
use kept in the OWNED `upload_claims` table. The page types a file by its first bytes (jpg / png /
webp / heic, mp4 / mov), caps it at the editor's sizes before and while reading, normalises a
picture to an upright JPEG, files it through `src/cut/uploads.save` as an `asset:<id>`, and with
`element_kind` + `element_name` adds it to that element through the same create body
`add_element` uses. The POST is rate-limited by address. **`add_element` takes a product page:**
the first usable picture (never a logo) and `linkrefs.parse_facts` in the notes as quoted data.
38 tests in `tests/test_upload_link.py`.

**Not done / to decide.**
- `web/` untouched: the `/connector` page's Limits sentence ("a picture reaches it as the web
  address of an image you give the chat, or as one of your own renders") is incomplete once this
  deploys -- a picture also reaches it through the upload page. One sentence; Mike's call
  (SUBMISSION.md by-hand item 18).
- `ZEROPAGE_UPLOAD_ORIGIN` is optional; the page's origin falls back to the origin of
  `ZEROPAGE_MCP_RESOURCE` (`https://api.zeropage.studio` on Fly).

**Live check after deploy** (as the test account, in a chat on `/mcp/claude`):
1. `upload_link` with `element_kind="prop"`, `element_name="Live check"` → a
   `https://api.zeropage.studio/u/…` link, `credits: 0`.
2. Open it on a phone, pick a photo → the page says *Saved*, names an `asset:<id>` and "Added to
   Live check (prop)".
3. `elements` → the prop lists the new photo's `ref`.
4. Open the link again → "already used"; ask for a second link → a new address.
5. `add_element` with a Shopify product page's address → `page.facts` in the answer and the
   notes; with a logo-only page → refused in plain words.

### PR 2 — #277, library, sharing and the free edits — READY

https://github.com/zeropage-onryo/video-pipeline/pull/277 (`claude/connector-overnight-2-library`, base PR 1's branch).

**What it does.** Five tools on both listings, none spends: `library(kind, limit, project_id)`
(`renders` made listed: `gen:<id>` and `asset:<id>` with kind, length, size, frame, aspect,
project); `share_link(ref, hours=24)` (a presigned attachment download for 1-168 hours, refused
past seven days, this server's own address with no bucket; a render's download is an outcome);
`reformat(ref, aspect, fit)` and `trim_clip(ref, start, end)` (new `src/cut/quick.py`: one-clip
scratch cuts through the editor's own ops, rendered, filed free under the `cut` log tool; `SIZES`
gained 4:5); `assemble_clips` registered on all three servers; `job(job_id, wait)` back on the
Claude listing with `wait` 0-15 s. 26 tests in `tests/test_connector_library.py`, real ffmpeg
for the shapes and lengths.

**Not done / to decide.**
- `reformat` on a still exports the frame as a PNG through the editor's still export; the editor
  lists that cut project only as a one-clip scratch cut.
- No `share_link` for a file this server neither holds nor has in the bucket: said plainly.

**Live check after deploy** (`/mcp/claude`, test account):
1. `library` → the renders and uploads with ids; `library kind=upload` → only uploads.
2. `reformat` the one rendered clip to `1:1` with `fit=crop` → a job id; `job` with `wait=15` →
   `done`, a new `gen:<id>`, `credits: 0`; it appears in `library` and the Library page.
3. `trim_clip` the same clip `0`-`1` → a ~1 s clip; `assemble_clips` the two → one joined clip.
4. `share_link` the joined clip → an `https://…r2…` address that downloads; `hours=200` → refused.
5. The balance is unchanged throughout.

### PR 3 — #278, reading tools — READY

https://github.com/zeropage-onryo/video-pipeline/pull/278 (`claude/connector-overnight-3-reading`, base PR 2's branch).

**What it does.** Seven read-only tools on both listings, every answer in credits only (a test
walks each listed answer for a dollar key or sign): `balance` (`billing.balance`: available, held,
plan, lots, a yearly plan's months to come; the ledger alone as fallback), `search(q, limit)`
(`search.run`, the ⌘K route), `whoami` (workspace, plan, the signed-in member's name and role),
`recent(limit)`, `credit_history(before, limit)` (Settings → Usage's lines), `video_models` (on a
listed server each frame priced in credits for a short clip, the draft frame where a model has
one; the studio surface keeps its dollars), `recommend_model(what, seconds, budget_credits,
draft)` (new `src/model_pick.py`: a pure ranking over the catalogue with six traits read off the
words, a length or budget a model cannot meet skipped with the reason, the account's keep counts
from `outcomes`; no model call). 13 tests in `tests/test_connector_reading.py`.

**Not done / to decide.**
- `recommend_model`'s traits are a short keyword table, not a model; it reports what it matched
  (`asked`). Nothing measures whether the picks are good.
- `search` returns element hits by kind and name only; `elements` is where refs come from.

**Live check after deploy** (`/mcp/claude`, test account):
1. `whoami` → the test workspace, no plan, the member's name and `owner`.
2. `balance` → `available` = the lot's remaining credits, one lot with its expiry, nothing in dollars.
3. `search q="headphones"` → the Tonal One prop and the written scene with its `scene_id`;
   `search q=""` → the project and open scenes.
4. `credit_history` → the grant line(s) with `balance_after`.
5. `video_models` → credits per frame, `wan3` with `draft: "480p"`; `recommend_model what="a cheap
   test"` → LTX 2.3 first with its credits; `seconds=25` → Seedance 2.5 only.

### PR 4 — #279, write tools — READY

https://github.com/zeropage-onryo/video-pipeline/pull/279 (`claude/connector-overnight-4-writes`, base PR 3's branch).

**What it does.** Seven write tools on both listings; every one makes a NEW row. Reference
`roles` on `write_scene` (`ref_roles.clean`'s vocabulary, stored as the composer stores them, a
look-only photo never first; `scene` answers them); `write_scene`'s `seconds` defaults to the
workspace's preference, else 10. `duplicate_scene(scene_id, prompt, refs, seconds, project_id,
roles)` (a copy carrying words, photos, roles and project, never a still, clip or timeline; the
reference gate as `write_scene`; answers `copied_from`; `project_id=0` files it on its own).
`feedback(text, ref, tool)` (OWNED `mcp_feedback`, insert-only, 2,000 characters). `preferences` /
`set_preferences(aspect, seconds, video_model, image_model, draft_first)` (OWNED
`mcp_preferences`, insert-only, newest row wins; every value checked against the live catalogue,
refused never clamped; read only where a caller passed nothing: `write_scene`'s length, `quote`'s
model and draft frame, a listed still's model and frame on `/mcp`). `recipes` / `recipe(name)` /
`save_recipe(name, body, project_id)` (the skill shelf beside the caller's own, OWNED
`mcp_recipes`, 8,000 characters, every save version n+1, read back as quoted data). 27 tests in
`tests/test_connector_writes.py`.

**Not done / to decide.**
- On the Claude listing a quote that applied a preferred model says so (`preference`), but the
  Render card opens on its own default and the person picks the renderer there. On `/mcp`,
  `approve` must be given the same model/frame the quote applied.
- `aspect` is used by a listed still only; a scene's frame is fixed by its prompt.
- `preferences` history is kept but no tool lists it.

**Live check after deploy** (`/mcp/claude`, test account):
1. `preferences` → every field null, the choices listed. `set_preferences seconds=12
   video_model=wan3 draft_first=true`; `set_preferences video_model=sora` → refused with the list.
2. `write_scene` a one-window prompt with `refs` from `elements` and `roles={<second ref>:
   "light"}` → `roles` on the answer, the light photo not first; `scene` shows `seconds: 12`.
3. `quote` that scene → `preference: {model: wan3, frame: 480p}`; `quote … model=ltx2.3` → no `preference`.
4. `duplicate_scene` the test account's rendered scene → a new `scene_id`, `rendered: false`, no
   clips; `duplicate_scene` with `refs=[]` → `needs_reference`.
5. `feedback text="live check"` → saved; `save_recipe name="live-check" body="…"` twice →
   versions 1 and 2; `recipe name="live-check"` → the note that it is quoted data; `recipe
   name="single-shot"` → the shelf's.

### PR 5 — #280, insights — READY

https://github.com/zeropage-onryo/video-pipeline/pull/280 (`claude/connector-overnight-5-insights`, base PR 4's branch).

**What it does.** Two read-only tools on both listings, no model call, credits only
(`_credits_only` drops any dollar key): `what_works()` (`outcomes.summary` +
`outcomes.preset_counts` + `preprod.posted_outcomes` for the caller, said plainly in `lines`;
`enough_data: false` under five outputs; "no audience signal" with nothing posted) and
`score_caption(text)` (`post_seo.score_post` against the caller's own posted videos split at
their median; neutral and saying so under four posted videos with numbers; 2,200 characters).
5 tests in `tests/test_connector_insights.py`.

**Not done / to decide.**
- `what_works` reports; it does not rank or recommend (its keep counts feed `recommend_model`).
- `score_caption` scores words, topics and hook types as the publish queue's caption builder does;
  not length or hashtags.
- Both depend on data the test account barely has; the live check mostly proves the "too little"
  paths.

**Live check after deploy** (`/mcp/claude`):
1. As the test account: `what_works` → `enough_data: false` with the "too little to say" line and
   "nothing posted"; `lines` readable as sentences; no dollar anywhere.
2. `score_caption text="Spring product spots, shot on the headphones"` → score 0.5, the "no
   performance data" reason, `enough_data: false`.
3. As Mike's own workspace: `what_works` → real keep counts per model and the posted reel's views.

### PR 6 — the plugin, v0.3.0 — READY, merge AFTER the connector is live

https://github.com/zeropage-onryo/zeropage-studio-plugin/pull/4 (`zeropage-onryo/zeropage-studio-plugin`, branch `claude/v0.3.0-skills`, base `main`).

**What it does.** Seventeen new skills (`zeropage-use`, `start-a-project`, `brand-kit-from-my-work`,
`storyboard`, `client-treatment`, `camera-moves`, `edit-and-deliver`, `platform-delivery`,
`hooks-and-first-seconds`, `ad-formats`, `series-and-continuity`, `model-prompting`, `ugc-ad`,
`product-shots`, `ad-variations`, `explainer`, `sound-plan`), two updated (`look-matching`:
roles, adapt a look never copy its subject, `upload_link`; `credits-and-limits`: draft-first,
`balance`, `credit_history`), the README (the 32-tool table, the 22 skills, the demo, the data
section), `plugin.json` 0.3.0 with the idea-board wording gone. Twenty-two skills in all. Each new
skill is under 100 lines with `name` + a "NOT for" description and names only tools on
`/mcp/claude` after PRs 1-5; no skill invents testimonials, reviews, numbers or awards.

**How it was checked.** Every skill was written from one brief (the hard rules and the studio
facts) and read back three ways: the night's own script (line count, frontmatter, tool names
against the listing, operator vocabulary, money figures: 22 skills, the only "problem" the
pre-existing `write-scene` at 111 lines); `claude plugin validate .` (passed, Claude Code 2.1.285);
and, by the finishing session, one independent verifier per changed file reading it against the
tool dump AND the code at ac7ad59 (argument names, answer fields, every limit and number), each
reported problem then challenged by a second agent before it was acted on. That pass found 57 wrong statements across 17 files -- the
recurring ones: `scene` lists clips as addresses, not ids, and gives only a photo count; the
`aspect` preference is for stills and nothing on the listing sets a scene's render shape;
`draft_first` prices a draft only with a `video_model` preference, on Wan 3.0 or Seedance 2.5,
when `quote` names no renderer; a `write_scene` rewrite keeps nothing it is not handed and
never renames; `library` carries 80 characters of a prompt and no kept flag, `project` 400,
the full prompt is on `scene`; `recommend_model` reads six job traits, not camera moves, and
a timed scene's windows are fitted UP, not refused; one keyframe is quoted PER SHOT -- each
confirmed against the code and corrected before the commit (629c93c). The PR body lists them.

**Not done / to decide.**
- No skill for `/mcp` only (a still through `generate_image`, `approve`): this plugin's connector
  is the Claude listing.
- Two pre-existing files are left as they were: `write-scene` is 111 lines (since v0.2.0), and
  `ideas-and-projects` says "there is no idea board" (true, and in the negative). Mike's call
  whether to trim the first.
- The skills name the new tools, so the plugin PR merges only once PRs 1-5 are live.

### PR 7 — this PR, the submission pack — READY

`claude/connector-overnight-7-docs` (base PR 5's branch): `docs/directory/SUBMISSION.md` and
`TWO_LISTINGS.md` rewritten for the 32/34-tool set (the tool tables, the listing description --
the Claude listing never renders -- the reviewer steps through `upload_link` → `write_scene` →
`quote` → `library` → `reformat` → `job`, the data table with the four new tables, and the
by-hand list), the handoff doc, and this report. `web/` is untouched on purpose: no tool name
there is wrong; the one Limits sentence is by-hand item 18.

### What Mike does by hand, in order

SUBMISSION.md's "Added by the overnight build" items 13-19, repeated here so this page stands alone:

1. **Set the test account's password** (`zp-billing-test`, member `deals4michael@gmail.com`):
   sign in as it and set one in /studio/settings; put the email + password in the portal field only.
2. **Merge PRs #276 → #280 one at a time, in order** (each is stacked on the previous: merge
   #276 into `main` and delete its branch, then #277, and so on -- GitHub re-targets the next
   PR to `main` when the branch it was based on is deleted; if the branch is kept, set the next
   PR's base to `main` by hand first), reading each PR's "Live check after deploy" first. A
   push to `main` deploys Fly. Then merge this docs PR the same way.
3. **Deploy** (the push does it); `fly releases --app zeropage-studio` to confirm the live commit.
   Optional: `ZEROPAGE_UPLOAD_ORIGIN` only if the upload page should live off the API origin.
4. **Walk the reviewer steps as the test account on `/mcp/claude`** (SUBMISSION.md "Test &
   launch" step 2, plus each PR's live check above): the `upload_link` page on a phone,
   `library`, `reformat`, `job`. Nothing in that walk spends. Once on `/mcp` for the still and the
   approve (one small still, one small clip).
5. **Merge the plugin PR** (PR 6) after the connector is live; its skills name the new tools.
6. **One sentence on `/connector`** (web/), Mike's call: a picture also reaches the connector
   through the one-time upload page.
7. **Submit** the connector on both portals, then the plugin, then **pair** them.

### Open decisions, collected

- The `/connector` Limits sentence (PR 1).
- `write-scene` at 111 lines in the plugin (pre-existing); trim or leave.
- `recommend_model`'s keyword traits and `what_works` / `score_caption`'s thin data on the test
  account: both are reported honestly by the tools; whether to invest in a better ranking is a
  later call.
- On `/mcp`, `approve` must be handed the quote's `preference` model/frame (PR 4); the Claude
  listing's Render card opens on its own default.

## Live checks run

Filled by `docs/tasks/task-connector-submission.md` (the run of 2026-10-12 → 10-13). Each PR's
"Live check after deploy" above is the list that was walked.

### 2026-10-12, as Mike's own workspace (account 1) -- PASS in full

From a claude.ai chat on `/mcp/claude` ("ZeroPage connector live check" in his history), with
the connector reconnected at the new address and its tool list refreshed to 32: all 16 reads, all
23 writes and free edits (`reformat` → gen:101, `trim_clip` → gen:102, `assemble_clips` →
gen:103, a `share_link` download, the 200-hour link refused, `project 1` → "no project 1",
`scene 1` → "no scene 1"), and the upload page (a PNG → asset:2 onto a new prop; the link then
"already used"; a second link a different address). Balance 11,486 before and after. Left on
account 1, labelled "Live check": scenes 405/406/407, the prop "Live check 2026-10-12", recipe
`live-check` v1–v2, one feedback row, preferences `seconds=10 / ltx2.3 / draft_first=false`
(the studio's own defaults).

### 2026-10-13, as the test account (`zp-billing-test`, account 5)

- **`/mcp/claude`, the reviewer list** (`ops/connector_walk.py walk claude`):
  `docs/directory/walk-2026-10-13-claude.md` -- TO FILL (step 5).
- **`/mcp`, the spending half** (one still, the scene's keyframes, one LTX 2.3 shot; capped at
  130 credits): `docs/directory/walk-2026-10-13-render.md` -- TO FILL (step 5), with the credits
  each spend held and settled.
- **The MCP Inspector**, both doors: `docs/directory/screens/inspector-claude.json` (32 tools)
  and `inspector-render.json` (34) -- TO FILL (step 5).
- **What the walk added to the test account** -- TO FILL (step 7b): the prop "Reviewer check"
  with the icon as its photo, the written scene and its copies, the recipe, the preferences set
  back to the defaults.
