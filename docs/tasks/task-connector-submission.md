# Task — overnight: finish everything before the directory submissions, unattended

**From:** the Claude Code session that finished the overnight connector build and ran the live
walk as Mike's own workspace, 2026-10-12 (the night's handoff was
`docs/tasks/HANDOFF-connector-overnight-2026-10-12.md`; its "As built" is at the bottom of
`docs/tasks/task-connector-overnight.md`). **For:** one unattended Claude Code session in
`zeropage-onryo/video-pipeline` on Mike's Mac, started before he sleeps.
**Mike's call (2026-10-12, in chat):** "do everything needed except adding this to the directories
for approval, that last step is for me to do" -- run overnight, do not wait for approval at each
step. That covers the merges and deploys of the PRs named below, the test-account walk, the capped
spend on the test account for the `/mcp` half, and the docs. The portal submissions, the pairing,
and anything after publishing stay his.
**Read first:** `docs/tasks/task-connector-overnight.md` ("As built"), then
`docs/directory/OAUTH_TEST.md` ("The live script", which is the OAuth flow the client in step 1
copies), then `docs/directory/SUBMISSION.md` ("The portal fields", "Test & launch",
"Everything Mike must do by hand").

## State right now (checked 2026-10-12 ~06:00 UTC)

- **Live.** PRs #276–#280 merged 2026-10-12 03:11–03:13 UTC; Fly `zeropage-studio` v291 is that
  code. `https://api.zeropage.studio/mcp/claude` answers 401 with its OAuth metadata and lists 32
  tools to a signed-in person; `/mcp` lists 34. The bare `/mcp` (no slash) answers `307 → /mcp/`
  until #283 deploys; claude.ai's "Add custom connector" check reads that as "Not found".
- **Open, none merged, all base `main`, all MERGEABLE:** #281 (`claude/connector-overnight-7-docs`,
  docs: SUBMISSION.md, TWO_LISTINGS.md, the handoff, the As built), #282
  (`claude/connector-page-upload-page`, three sentences on `web/src/app/connector/page.tsx`; a
  merge deploys the site through Vercel), #283 (`claude/mcp-bare-path`, the bare-`/mcp` fix; CI
  green), #284 (`claude/upload-page-still-length`, the upload page printed "Length 600.0s" for a
  picture; `test` was still pending at 05:40 UTC), and the plugin's pull 4
  (`zeropage-onryo/phantra-claude-plugin`, `claude/v0.3.0-skills`, 629c93c).
- **Already done, not in the steps:** the OAuth and tenancy script walked live 2026-10-08 with the
  OLD tool set through a local OAuth client (OAUTH_TEST.md "Live results": every step PASS, the 429
  with `Retry-After: 18` included); the test account populated 2026-10-08 and its password set by
  Mike 2026-10-12; the plugin repo public; Mike's own `ZeroPage` connector moved to `/mcp/claude`
  (its tool list refreshed to 32 on 2026-10-12); the Supabase OAuth authorization path set; the
  icon drawn: `docs/directory/icon/zeropage-studio-icon-512.png` and `-1024.png` on `main`
  (SUBMISSION.md's "Icon: none prepared" and by-hand item 8 are stale).
- **The 2026-10-12 walk as Mike's own workspace (account 1) PASSED in full** from a claude.ai chat
  ("ZeroPage connector live check" in his history): all 16 reads, all 23 writes and free edits
  (reformat → gen:101, trim → gen:102, join → gen:103, a download link, the 200-hour link refused,
  "no project 1" / "no scene 1"), and the upload page (a PNG → asset:2 onto a new prop, the link
  then "already used", a second link a different address); balance 11,486 before and after.
  Left on account 1, labelled "Live check": scenes 405/406/407, prop "Live check 2026-10-12",
  recipe `live-check` v1–v2, one feedback row, preferences `seconds=10 / ltx2.3 / draft_first=false`
  (the studio's own defaults). Props "Connector check" and "Connector live check" are from
  2026-10-11.
- **NOT done: the reviewer walk as the test account.** `zp-billing-test` = account 5. The user
  `deals4michael@gmail.com` is a member of account 5 AND owns account 8 (the fresh sign-up of
  2026-10-08); the connector resolves a caller to the OLDEST membership, so a sign-in as that user
  acts in account 5. Account 5 holds four product props (2026-10-08), the project "Spring product
  spots", scene #400, three renders, 501 credits, and ZERO rows in `upload_claims`,
  `mcp_preferences`, `mcp_feedback`, `mcp_recipes`, `cut_media`.
- **NOT done:** the MCP Inspector against either door (SUBMISSION.md C26 "Inspector not run"); the
  review-note screenshots (no `docs/directory/screens/`); any portal submission
  (`claude.ai/directory/manage` read "0 submissions"); the OpenAI side (its organization's
  verification state is unknown from here).
- **Fly secrets by name (values never read):** `ZEROPAGE_MCP`, `ZEROPAGE_MCP_TOKEN`,
  `ZEROPAGE_MCP_HOSTS`, `ZEROPAGE_MCP_ENGINE` exist; `ZEROPAGE_CLAUDE_DIRECTORY_URL`,
  `ZEROPAGE_SIGNUP_URL`, `ZEROPAGE_UPLOAD_ORIGIN` do not (right until the listing is public).
- **The local OAuth client of 2026-10-08 is not in the repo**; step 1 builds one. The Mac's
  throwaway Postgres (Postgres.app, 5432) was off on 2026-10-12: database-backed tests error
  locally, CI runs them (`gh pr checks <n> --watch`).
- Vercel's daily deployment limit was hit on 2026-10-11; #282 is the only PR here that builds the
  site.

## Rules for this task

- **The one thing a session cannot do is the sign-in as the test account.** Never type, store by
  hand, or print its password or any token. Step 2 is one command Mike runs; the client keeps its
  own session file under `data/` (gitignored); the session reads it only through the client and
  never prints it.
- **Merges are authorized for exactly these:** #283, #284, #281, #282, the plugin's pull 4, and
  the docs PRs this task opens -- each only when its CI is green, with
  `gh pr merge <n> --repo <repo> --merge --delete-branch`. Nothing else merges. A push to `main`
  deploys Fly; a change under `web/` deploys Vercel.
- **Spending is capped and only on the test account:** step 5 may spend up to 130 credits of
  account 5's 501 (one still, two keyframes, one LTX 2.3 shot), nothing else, nothing on account 1,
  nothing twice. Every spend goes through a quote and its token, as the tools require.
- Branch for every change; never commit to `main`. `CLAUDE.md`'s MCP block and the two directory
  docs are the references: point, do not restate.
- Keep the Mac awake for the run (`mcp__ccd_host__request_keep_awake`). Shared machine: kill only
  by pid; a full suite here is 30–75 minutes, so lean on CI for the suites.
- Every refusal from the connector is a plain sentence; repeat it in the report, never retry the
  same call in a loop. Never "Always allow" anything; the client needs no approvals at all.
- Write the final report in this file under "## As run" (per step: what ran, what it showed, what
  is left), and commit it with the docs PR of step 7.

## Steps

### 1. Build the connector's local OAuth client and walker (no sign-in yet)
- [ ] On branch `claude/connector-walk-client` from `origin/main`, write `ops/connector_walk.py`
  (stdlib + `requests`/`httpx`, whichever the repo already has), with these subcommands:
  - `signin [--door claude|render]`: discovery (`GET <door>` → 401 `WWW-Authenticate` →
    `/.well-known/oauth-protected-resource/mcp[/claude]` → `authorization_servers[0]` →
    `<as>/.well-known/oauth-authorization-server`), dynamic client registration with the loopback
    redirect `http://localhost:53682/callback` exactly as OAUTH_TEST.md's script did, PKCE S256,
    opens the authorize URL in the default browser, catches the code on the loopback, exchanges it,
    and writes `data/connector_walk/<door>.json` (access token, refresh token, expiry, client id)
    with mode 0600. Prints only the authorize URL and "signed in as workspace <whoami>".
  - `call <door> <tool> [--json '{...}']`: one JSON-RPC `tools/call` over streamable HTTP
    (`initialize` first, `Accept: application/json, text/event-stream`), refreshing the token
    through the refresh grant when expired and rewriting the file; prints the tool's result JSON.
  - `walk <door> --out <file.md>`: the whole reviewer list below, in order, each result written to
    the file under the tool's name, with a PASS/CHECK verdict per expectation; never prints tokens.
  - `upload <url> <file>`: `multipart/form-data` POST of a file to a one-time upload page (the
    page's form field name is in `app/templates/upload.html`), then a GET of the same URL; prints
    both pages' text.
  - Hermetic tests in `tests/test_connector_walk.py`: discovery parsing off canned documents, PKCE
    shape, the token file never written world-readable, the walk's verdict table off canned
    results; `conftest` blocks the network, so nothing live.
  - Done when: `venv/bin/ruff check .` is clean, the new tests pass, the PR is open, CI is green and
    it is merged; `venv/bin/python ops/connector_walk.py signin --door claude --dry-run` prints a
    `https://ewkbrenbjsiggufegrnd.supabase.co/auth/v1/...` authorize URL with `code_challenge` and
    the loopback redirect, and exits without a browser.

### 2. The one sign-in — **MIKE**, tonight if awake, else in the morning
- [ ] The session prints, as soon as step 1 is merged, exactly this for Mike:
  `cd "/Users/iphone/Documents/PRODUCTION PIPLINE .GIT" && venv/bin/python ops/connector_walk.py signin --door claude`
  then "sign in as the test account on the page that opens (sign out of the studio first if you are
  signed in as yourself), press Allow, and you are done". The same command with `--door render`
  signs in for `/mcp`; one Supabase token serves both doors (`aud` is `authenticated`), so the
  client reuses the claude door's session for the render door and only asks again if refused.
- [ ] The session then polls for `data/connector_walk/claude.json` every 10 minutes while doing
  steps 3 and 4 (which need no sign-in), and continues with step 5 the moment it appears. If it is
  still absent when steps 3, 4 and 7a are done, the session stops with the report and the command
  above at the top of it.
  - Done when: `venv/bin/python ops/connector_walk.py call claude whoami` prints a workspace with
    `slug: zp-billing-test` (id 5) and `member.role: owner`.

### 3. Merge the open PRs, in order, each after its CI is green
- [ ] #283 first. Then confirm the fix live.
  - Done when: `curl -s -o /dev/null -w "%{http_code}" -X POST https://api.zeropage.studio/mcp`
    prints `401` (it prints `307` today) and `fly releases --app zeropage-studio` shows a release
    newer than v291.
- [ ] #284. Done when: `gh pr view 284 --json state -q .state` prints `MERGED` and the Fly release
  after it is complete.
- [ ] #281 (docs). Done when: `docs/tasks/task-connector-overnight.md` on `origin/main` ends with
  "## As built".
- [ ] #282 (the `/connector` sentence). If Vercel refuses the build (the daily limit), merge anyway
  and note it: the site redeploys on the next push. Done when:
  `curl -s https://zeropage.studio/connector | grep -c "pick the file yourself"` prints `1`, or the
  note says why not yet.
- [ ] The plugin's pull 4: `gh pr merge 4 --repo zeropage-onryo/phantra-claude-plugin --merge
  --delete-branch`. Done when: `gh api repos/zeropage-onryo/phantra-claude-plugin/contents/.claude-plugin/plugin.json -q .content | base64 -d | grep version`
  prints `0.3.0`.

### 4. Work that needs no sign-in (while waiting for step 2)
- [ ] Re-check the connector's "add" path after #283 deploys: the bare `/mcp` POST answers 401 (step
  3's check), and both metadata documents (`/.well-known/oauth-protected-resource/mcp` and
  `/mcp/claude`) still answer with `authorization_servers`.
  - Done when: both curls print `401` and both documents name the Supabase authorization server.
- [ ] Draft the docs changes of step 7 on branch `claude/connector-submission-pack` (from `main`
  after #281 merges): in SUBMISSION.md replace "Icon: none prepared" and by-hand item 8 with the two
  files under `docs/directory/icon/`, mark by-hand items 13, 14, 16, 18 done with dates (15 and 19
  after step 5), add #283/#284 to "What changed", and write `docs/directory/PORTAL_PASTE.md`: every
  portal field for the connector and the plugin in paste order, taken verbatim from "The portal
  fields", with the icon path, the test account's EMAIL (never the password) and the compliance
  answers as sentences Mike can paste. In TWO_LISTINGS.md "By hand" item 7: done, with the date.
  - Done when: the branch builds (`ruff` clean, no code touched) and the PR is open as a draft.

### 5. With the sign-in: the reviewer walk as the test account, both doors
- [ ] `venv/bin/python ops/connector_walk.py walk claude --out docs/directory/walk-2026-10-13-claude.md`
  runs, in order: `whoami` → `projects` → `project` (Spring product spots) → `elements` →
  `upload_link` (purpose reference, element_kind prop, element_name "Reviewer check") → `upload`
  of `docs/directory/icon/zeropage-studio-icon-512.png` to that link, then the GET again →
  `elements` → `write_scene` (a two-window prompt held to the Tonal One headphones' ref first and a
  second product's ref with `roles` {ref: "light"}, `project_id` from `projects`) → `scene` →
  `quote` → `library` → `reformat` of the account's rendered clip to 1:1 crop → `job` wait=15 until
  done → `trim_clip` 0–1 s → `job` → `assemble_clips` of the two → `job` → `share_link` →
  `share_link hours=200` → `balance`, `credit_history`, `recent`, `search q="headphones"`,
  `video_models`, `recommend_model what="a cheap test"`, `recommend_model what="a final client spot
  with sound" seconds=25`, `preferences`, `set_preferences seconds=12 video_model=wan3
  draft_first=true`, `set_preferences video_model=sora`, `quote` (expect `preference` wan3 480p),
  `quote model=ltx2.3` (expect no `preference`), `duplicate_scene`, `duplicate_scene refs=[]`,
  `feedback`, `save_recipe` ×2, `recipe`, `recipe name="single-shot"`, `what_works`,
  `score_caption`, `project project_id=1`, `scene scene_id=375`, `balance`, then
  `set_preferences seconds=8 video_model=ltx2.3 draft_first=false` (preferences cannot be cleared,
  only set back to the catalogue's defaults).
  - Done when: the out file shows PASS on every expectation in each PR's "Live check after deploy"
    (`task-connector-overnight.md` As built): `whoami` names `zp-billing-test` and `owner`; the
    upload page says Saved with an `asset:<id>`, "Added to Reviewer check (prop)", a Size line and
    (after #284) no Length line, and the second GET says "already used"; `what_works` says
    `enough_data: false` and nothing posted; `project 1` → "no project 1", `scene 375` → "no scene
    375"; the first and last `balance` are equal; no `$` and no `usd` key anywhere in the file.
- [ ] The `/mcp` half, capped at 130 credits of account 5: `venv/bin/python ops/connector_walk.py
  call render ...` for `image_models` → `generate_image` (a one-line prompt, no reference; expect a
  quote with `quote_token` and nothing drawn) → `generate_image` again with that token → `job` until
  done → `quote` on the scene written above → `approve what="keyframes"` with the quote's token →
  `job` → `approve what="clip"` with the quote's token → `job` → `generate_image` once more with the
  SAME first token (expect `already_used`, nothing charged) → `credit_history` → `balance`.
  - Done when: `credit_history` shows one hold and one settle per spend, the balance dropped by
    exactly the quoted credits (at most 130 in total), `scene` shows the keyframes and the clip, and
    the walk file records each answer. If any quote exceeds the cap, skip that spend and say so.
- [ ] The MCP Inspector, both doors, without a browser:
  `npx -y @modelcontextprotocol/inspector --cli https://api.zeropage.studio/mcp/claude --method tools/list --header "Authorization: Bearer $TOKEN"`
  with `TOKEN` exported by the client (`eval "$(venv/bin/python ops/connector_walk.py env claude)"`,
  a subcommand step 1 adds that prints `export TOKEN=...` to be eval'd, never echoed), and the same
  for `/mcp`; save each JSON listing to `docs/directory/screens/inspector-<door>.json`.
  - Done when: the two files hold 32 and 34 tools by name, and SUBMISSION.md's C26 reads PASS with
    the date. If the Inspector's `--cli` cannot take a header in the installed version, say so and
    leave C26 for Mike.

### 6. The review-note screenshots
- [ ] Into `docs/directory/screens/` on the step-4 branch: the tool list (if Chrome with the Claude
  extension is reachable, `claude.ai/customize/connectors/yours/id/4c1040ec-1061-4751-b46e-aeec363e2698`
  on Mike's own connector, 32 tools with titles; else render `inspector-claude.json` as a plain PNG
  table with Pillow), the refused foreign id (the `scene 375` block of the walk file, as a PNG of the
  text), and a note that the 429 numbers are OAUTH_TEST.md's of 2026-10-08. The consent page
  screenshot is Mike's (taken during his sign-in); say so.
  - Done when: at least two PNGs exist and SUBMISSION.md's "Screenshots" list names each file and
    which are still Mike's.

### 7. Record it all and merge the docs
- [ ] (7a, before the sign-in if need be) In `docs/tasks/task-connector-overnight.md` add "## Live
  checks run" under the As built: the 2026-10-12 walk as account 1 (done), and placeholders for
  step 5 to fill. (7b, after step 5) Fill them: the test-account walk's result file names, the
  `/mcp` spends with their credits, the Inspector result, what the walk added to the test account
  (the prop "Reviewer check", the scene, the copies, the recipe, the preferences now at the
  defaults), and update SUBMISSION.md "Test & launch" step 1 to list exactly that. Append "## As
  run" to THIS file. Then take the step-4 PR out of draft, wait for CI, merge it.
  - Done when: `origin/main` carries the walk files, `PORTAL_PASTE.md`, the screens, and this file's
    "As run"; `grep -n "none prepared\|Inspector not run" docs/directory/SUBMISSION.md` prints
    nothing.

### 8. Morning report
- [ ] End with: the five merges and their Fly/Vercel releases; the walk verdicts (both doors) and
  the credits spent on account 5; the Inspector result; what is left for Mike: the portals, with
  `docs/directory/PORTAL_PASTE.md` open beside him, then the pairing, then
  `ZEROPAGE_CLAUDE_DIRECTORY_URL` on Fly once the listing is public, and the optional clean-up of
  account 1's "Live check" leftovers in the studio. If the sign-in never came, the report opens with
  the one command and says which steps wait on it (5, 6 in part, 7b).

## Done means

- #281–#284 and the plugin's pull 4 merged; the bare `/mcp` answers 401 live; the `/connector` page
  carries the upload-page sentence (or the note says Vercel's limit held it).
- `ops/connector_walk.py` on `main` with its tests; the reviewer walk run as the test account on
  `/mcp/claude` with every verdict PASS, the `/mcp` half run within the cap, both recorded in the
  repo; the Inspector listings saved; the test account's preferences back at the defaults.
- SUBMISSION.md and TWO_LISTINGS.md say what is true today, `PORTAL_PASTE.md` holds every field
  Mike pastes, and this file's "As run" says what happened.
- The only things left are Mike's: the three portal submissions, the pairing, and the Fly secret
  after the listing is live.

## As run

Run 2026-10-12 by one unattended Claude Code session (worktree `eloquent-kilby-972d70`); the
sign-in came by day (14:21 UTC), not overnight, so the walk files keep the names this task gave
them (`walk-2026-10-13-*`) and carry the real date inside. Every rule above held: no password or
token was typed, stored by hand or printed; nothing was submitted to a directory; the spend was
117 credits of account 5's 501, all through quotes and single-use tokens, nothing on account 1,
nothing twice. Mike was awake for parts of it and gave the word on two merges this task had not
named (#285, #287).

### 1. The client -- done

- `ops/connector_walk.py` and `tests/test_connector_walk.py` (36 tests, no network, no database):
  PR #285. CI failed once, on `tests/test_output_roots.py` (a module-level `SESSION_DIR` into
  `data/`): registered in conftest's `OUTPUT_ROOTS`, read at call time; CI green; merged 34158be
  on Mike's word. The live dry-run printed the Supabase authorize URL with `code_challenge`,
  `S256` and the loopback redirect and exited without a browser; a redirect-free GET of that URL
  answered `302` to `https://api.zeropage.studio/oauth/consent?authorization_id=…` (with and
  without an `offline_access` scope).
- Before the first live walk, three independent reviewers read the client (OAuth, the MCP
  transport, the walk against the server's answer shapes), every claim adversarially verified:
  20 claims, 16 confirmed, 10 distinct defects, all fixed in PR #287 (52 tests), merged 9725262 on
  Mike's word. The ones that would have mattered live: `done` undefined when `reformat` was
  refused (the trim's wait would have crashed), a dropped connection or a non-JSON 200 aborting the
  walk with the test account's preferences changed, a 429 swallowed and the rest of the list sent
  into the closed window, `env` printing the bearer token to stdout (now a named file descriptor
  only, and an `inspector` subcommand keeps the token inside the process).

### 2. The sign-in -- done (Mike, 14:21 UTC)

- The command was printed as soon as #285 merged, with the main checkout fast-forwarded first
  (two untracked docs there collided with files now committed and were kept beside as
  `docs/tasks/task-connector-overnight.local-2026-10-12.md` and
  `task-connector-elements.local-2026-10-12.md`; neither was deleted).
- It printed `signed in as workspace zp-billing-test`; `whoami` → id 5, member Michael Massaad,
  role **`member`** (the invite's default, `accounts.invite`; the task said `owner`), a refresh
  token present without any scope having been asked for. The session file is
  `<main checkout>/data/connector_walk/claude.json`, mode 0600, and every later call from the
  worktree passed `--sessions` pointing at it.

### 3. The merges -- done, all CI-green, `--merge --delete-branch`

| PR | merge commit | live |
|---|---|---|
| #283 bare `/mcp` 401 | 07971ac | Fly v292; `POST https://api.zeropage.studio/mcp` → `401` |
| #284 upload page Size, not Length | 1877e65 | Fly v293 |
| #281 the submission pack | 9f7c416 | (its own deploy was superseded by #282's) |
| #282 the `/connector` sentence | d70b22a | Fly v294; Vercel built it; `grep -c "pick the file yourself"` → 1 |
| plugin pull 4, v0.3.0 | b1c6b93 | `plugin.json` on `main` reads 0.3.0 |
| #285 the client | 34158be | Fly v295+ |
| #287 the client's review fixes | 9725262 | by 14:40 UTC Fly was at v303, other sessions' merges in between |

### 4. No sign-in needed -- done

- After v292 and again after v294: both doors' unsigned POST → 401; both metadata documents name
  `https://ewkbrenbjsiggufegrnd.supabase.co/auth/v1`.
- The docs branch `claude/connector-submission-pack` (draft PR #286): SUBMISSION.md (the icon, by-hand
  items 8, 13, 14, 16 and 18 done with dates, "What changed on 2026-10-12"), TWO_LISTINGS.md item
  7, `PORTAL_PASTE.md`, and (7a) the overnight doc's "Live checks run".

### 5. The reviewer walk as the test account -- done, both doors

- **`/mcp/claude`** (`walk-2026-10-13-claude.md`): 39 steps, 70 of 72 expectations PASS on the
  first pass. The two CHECKs were the account's state, not the connector: (a) step 12 found no
  rendered clip in the library (its three renders were stills), so the walk skipped the free edits
  with a row saying so; once the render half had made a clip they were run through the same door
  as Addendum 1, 7 of 7 PASS (gen:108 the 1:1 crop, gen:109 the first second, gen:110 the join, a
  24-hour link, 200 hours refused, balance unchanged); (b) step 36's `project 1` is the test
  account's OWN project ("Spring product spots"), so it was answered, not refused; the
  cross-tenant refusal stands on step 37 (`scene 375` → "no scene 375") and on the account-1 walk,
  where that same project 1 answered "no project 1" (Addendum 2). The upload page said Saved,
  `asset:3`, "Added to Reviewer check (prop)", a Size line and no Length line (#284 live), and the
  second GET "already used"; `what_works` said `enough_data: false` and nothing posted; the first
  and last balance were equal; no `$` and no `usd` in the file.
- **`/mcp`** (`walk-2026-10-13-render.md`): 11 of 12 PASS, **117 credits** of the 130: the still
  gen:104 (FLUX 1.1 Pro, 10), scene 408's two keyframes (20), one LTX 2.3 shot (87) on scene 411,
  a free one-window `duplicate_scene` copy of 408 -- because 408's own two-shot clip quoted 174,
  over what the cap left (100), and was skipped as the rule says. The replayed token answered
  `already_used` and charged nothing; `credit_history` shows one hold and one settle per spend;
  the balance went 501 → 384. The one CHECK is a finding about the render listing: `approve
  what=clip` answers the Queue's own JSON with the provider's estimate under dollar-named keys
  (`render.estimate_usd`, `quote.estimate_usd`, `quote.renders[0].estimate_usd`), which `quote` on
  the same door drops; the listed approve wants the same `_credits_only` pass.
- **The MCP Inspector** (`inspector --cli … --transport http --method tools/list`, the token never
  shown): `screens/inspector-claude.json` 32 tools, `screens/inspector-render.json` **35** -- the
  docs' "34" was a miscount (the Claude 32 plus `image_models`, `generate_image`, `approve`);
  corrected in SUBMISSION.md, TWO_LISTINGS.md and PORTAL_PASTE.md. C26 reads PASS.
- Also seen: the API machine redeployed more than once during the half-hour (other sessions'
  merges), so job ids restarted at 1 and one `credit_history` call dropped mid-response (asked
  once more, fine); a production SQL read for a foreign project id was refused by the auto-mode
  classifier, and was not needed.

### 6. The screens -- done, with one left to Mike

`docs/directory/screens/`: `tool-list.png` (the 32 tools with titles, hints and a line of each
description, rendered with Pillow from the Inspector's listing; the claude.ai page of Mike's own
connector was not screenshotted), `cross-tenant-refused.png` (step 37 as text), the two Inspector
listings, and a note in SUBMISSION.md that the 429 numbers are OAUTH_TEST.md's of 2026-10-08.
`consent-page.png` is Mike's to take.

### 7. The record -- done

7a and 7b are in PR #286: C26, "Test & launch" step 1 (what the walk added to the test account),
by-hand item 15, the screens list, the 35 count, the overnight doc's "Live checks run", this file
with this section. Taken out of draft and merged once its CI was green.

### What is left, all Mike's

- The three portal submissions with `docs/directory/PORTAL_PASTE.md` open beside him (the test
  account's email is there; its password is his to type into the portal field only), then the
  pairing, then `ZEROPAGE_CLAUDE_DIRECTORY_URL` on Fly once the listing is public.
- The consent-page screenshot, if a browser shot is wanted for the review note.
- The render listing's `approve` answer dropping its dollar-named keys (a one-line
  `_credits_only` in `src/mcp_server.py`'s listed `approve`; not changed by this run).
- Optional: the account-1 "Live check" leftovers (scenes 405/406/407, the prop "Live check
  2026-10-12", recipe `live-check`). The test account now also holds the reviewer-walk leftovers
  listed in SUBMISSION.md "Test & launch"; a fully populated reviewer account wants them.
