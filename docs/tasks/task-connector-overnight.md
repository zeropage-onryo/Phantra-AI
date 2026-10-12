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
