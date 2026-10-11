# Task — submit the Zero Page connector and plugin to the Claude directory today

**From:** a claude.ai session, 2026-10-11, after the InVideo growth teardown
(project doc `claude/invideo_growth_teardown_2026-10-11.md`: InVideo is already
advertising "ChatGPT can edit your videos now… using MCP"). **For:** Claude
Code, in `zeropage-onryo/video-pipeline` on Mike's Mac.
**Mike's call:** ship the connector today and finish it; SEO pages come next
(`docs/tasks/task-seo-pages.md`). Earlier calls still stand: render path B
(`write_scene` → `quote` → `approve` on the listed server), one web sign-in
before connecting, MIT licence, support = GitHub issues on the plugin repo,
the idea board is gone from every door (2026-10-11).
**Read first:** `docs/directory/SUBMISSION.md` (the portal fields and the
by-hand list), then `docs/directory/OAUTH_TEST.md` § "The live script", then
the CLAUDE.md paragraph "THE LISTED SERVER (2026-10-07…)".

This file is the finish line for `docs/tasks/task-directory-listing.md`
(Phases 0–6, done). It does not repeat that work.

## State right now (checked 2026-10-11, ~12:50 ET)

- `origin/main` tip is `3ecf3f2` (PR #228). PR #226 (higgsfield-shape steps
  0–3) is merged: `mcp_server.LISTED_TOOLS` is the ten tools `projects,
  project, project_chat, create_project, save_chat, elements, write_scene,
  quote, approve, job`.
- Live, unauthenticated: `POST https://zeropage-studio.fly.dev/mcp/` answers
  **401** with `WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource/mcp"`;
  `/.well-known/oauth-protected-resource` answers with the Supabase auth
  server. `POST /mcp` (no slash) is a 307 to `/mcp/`.
- **Unknown from here:** which commit Fly is running (so whether the live
  listed server already has the ten tools), and whether anything was already
  submitted in the directory portal.
- The 403 for a sign-in with no workspace already tells the person to sign
  in once at `ZEROPAGE_SIGNUP_URL` (default `https://zeropage.studio`) —
  `app/mcp_mount.py` ~line 232. Nothing to change.
- `https://zeropage.studio/privacy` and `/terms` → 200. `/connector` → 404.
- **The public plugin repo is stale.**
  `github.com/zeropage-onryo/zeropage-studio-plugin` (last commit 2026-10-08)
  still has a `skills/concept-board` skill, and its README names `board`,
  `pick`, `capture`, `archive` — tools no door serves any more. Its skills:
  `concept-board, credits-and-limits, look-matching, render-and-status,
  write-scene`.
- The live walk in `OAUTH_TEST.md` (2026-10-08) was made on the OLD tool set.
  `SUBMISSION.md` says it has to be made again.
- Test account `zp-billing-test` (account 5), member
  `deals4michael@gmail.com`, 501 credits (lot expires 2026-12-08), project
  "Spring product spots", scene #400 written. That user has **no password**.
- Icon: `web/public/brand/zp_black_favicon_512.png` exists (512×512, the
  red/white ZP on black Mike picked 2026-09-26). No new image is needed.

## Rules for this task

- No renders, stills or any generation without Mike's yes in chat. In this
  task `approve` is the only tool that spends, and only on the test account,
  only after he says go.
- Never print a secret, token or password; names only. The test account's
  password goes in the portal field and nowhere else.
- Code changes on a branch, never on `main`. A merge to `main` deploys Fly.
- The plugin repo is PUBLIC: read every changed file as a stranger before
  pushing (no Mac paths, account slugs, concept ids, internal notes).
- Tests and lint as CI runs them: `venv/bin/python -m pytest tests/ -q`,
  `venv/bin/ruff check .`.

## Steps

### 0. Confirm what is live (before anything else)
- [ ] Read which commit Fly runs (read-only).
  - `fly releases --app zeropage-studio | head -5` and compare the image to `git rev-parse origin/main`
  - Done when: the live release is at or after the merge of PR #226. If not, stop and tell Mike a deploy is needed (he merges/deploys).
- [ ] **MIKE:** open https://claude.ai/directory/manage and say whether a connector or plugin submission already exists.
  - Done when: Mike answers "nothing submitted" or names the open submission. If one exists, step 6 becomes "tell the reviewers the tools changed" (`SUBMISSION.md`, top note).

### 1. Plugin repo matches the ten tools
- [ ] Clone `zeropage-onryo/zeropage-studio-plugin` next to the main checkout and branch (`claude/ten-tools`).
- [ ] Replace `skills/concept-board` with a `skills/projects` skill: open a project (`projects`, `project`), read its chat (`project_chat`), start one (`create_project`), keep the conversation (`save_chat`). Under 100 lines, frontmatter `name` + `description` with a "NOT for" line.
  - Done when: `grep -rE "\b(board|pick|capture|archive|shoot|idea|search|stats)\b" skills README.md` returns only ordinary English, never a tool name.
- [ ] Update `write-scene` and `render-and-status` for the new flow: `write_scene` returns a `scene_id`; `quote` and `approve` take that `scene_id`; nothing is picked first.
- [ ] Rewrite the README tool list to the ten tools, in `LISTED_TOOLS` order, with the read/write split from `SUBMISSION.md` ("Tools").
- [ ] Bump `.claude-plugin/plugin.json` version to `0.2.0`.
- [ ] Validate: `claude plugin validate .`
  - Done when: `✔ Validation passed`.
- [ ] **MIKE:** merge the plugin PR (public repo).
  - Done when: `main` on GitHub shows no `concept-board` folder.

### 2. Test account ready for reviewers
- [ ] **MIKE:** sign in at https://zeropage.studio as `deals4michael@gmail.com` (emailed code), open `/studio/settings`, set a password. Keep it for the portal field only.
  - Done when: a fresh private window signs in with email + password.
- [ ] Check the account through the studio (free, nothing spends): project "Spring product spots" lists scene #400 and the four product elements.
  - Done when: the Projects page shows them for that user.

### 3. The live walk on the ten tools
- [ ] **MIKE:** on claude.ai, signed in as the test user, add the custom connector `https://zeropage-studio.fly.dev/mcp`, approve the consent page.
  - Done when: the connector shows as connected with ten tools and their titles.
- [ ] In that chat, call the free tools in order and note each result in `OAUTH_TEST.md` under a new "Live results, 2026-10-11" heading: `projects`, `project` (Spring product spots), `project_chat`, `elements`, `create_project`, `save_chat`, `write_scene` (timed shots, `refs` from `elements`, the new project's id), `quote` (the returned `scene_id`), `job` on a bad id.
  - Done when: every call answers without a generic error, and `quote` shows credits beside the 501 balance.
- [ ] Cross-tenant check: from the test account, `project` with one of Mike's project ids and `quote` with one of his scene ids.
  - Done when: both answer "no project N" / "no scene N".
- [ ] **MIKE, ask first — this spends test-account credits:** `approve` keyframes, then the clip, on the cheapest model the quote offers, for the scene written above.
  - Done when: `job` reports done, the clip is on that account's Assets wall, and the ledger shows a hold then a settle (or a release if it failed).
- [ ] Take the screenshots `SUBMISSION.md` lists that still make sense: `consent-page.png`, `tool-list.png`, `cross-tenant-refused.png` (now a project/scene id, not `idea 375`). Drop `empty-board.png` and `shared-sparks.png`.

### 4. MCP Inspector (item C26)
- [ ] Run `npx @modelcontextprotocol/inspector`, connect with Streamable HTTP to `https://zeropage-studio.fly.dev/mcp`, sign in through the OAuth flow as the test user.
  - Done when: Inspector lists the ten tools with titles and annotations, and `projects` returns the test account's projects. Record the result in `SUBMISSION.md` C26.

### 5. Bring `SUBMISSION.md` up to date
- [ ] Update the status table: C26 PASS (if step 4 passed), C27 icon = `web/public/brand/zp_black_favicon_512.png`, C28 READY (password set), C29 docs URL = the plugin README.
- [ ] Replace the screenshot list and reviewer step 1 with what step 3 actually used.
- [ ] Commit on a branch (`claude/ship-connector`), push, open a PR.
  - Done when: the PR is open and CI is green.

### 6. Submit (all MIKE, in this order)
- [ ] **MIKE — decision:** the compliance acknowledgement on AI image/video generation (C12). The checklist says connectors that generate media "aren't accepted". Options: (a) submit as is and answer truthfully; (b) take `approve` out of `LISTED_TOOLS` (one line in `src/mcp_server.py`, one test) so the listed connector writes and prices scenes and the render is approved in the studio's Queue. The session makes (b) only if he picks it, on a branch, before submitting.
- [ ] **MIKE:** claude.ai/directory/manage → Submit new → MCP connector. Copy every field from `SUBMISSION.md` § "The portal fields (MCP connector)": URL, listing text, categories, docs URL (plugin README), privacy, terms, support (plugin issues), icon (the 512 PNG), test account email + password, reviewer steps, compliance.
  - Done when: the portal shows the connector "In review".
- [ ] **MIKE:** Submit new → Plugin bundle → `zeropage-onryo/zeropage-studio-plugin`, `main`, root → Validate → data handling (from `SUBMISSION.md`) → compliance → submit. Set up the push webhook it offers.
  - Done when: the plugin shows "In review".
- [ ] **MIKE:** pair the two listings in the portal.

### 7. After submitting
- [ ] Write the date, the two submission states and any reviewer email into `SUBMISSION.md` (top), commit on the same branch.
- [ ] Watch mikemassaad@gmail.com for `directory@anthropic.com` / `mcp-review@anthropic.com`. If a reviewer refuses on C12, the fallback is option (b) above.

## Done means

- The public plugin repo describes exactly the ten tools the listed server serves, and validates.
- The live walk on the ten tools is recorded in `OAUTH_TEST.md`, including the cross-tenant refusal and (if Mike approved it) one paid render on the test account.
- `SUBMISSION.md` matches what was submitted.
- The connector and the plugin both show "In review" in the directory portal, and are paired.
