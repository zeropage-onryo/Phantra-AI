# Handoff — the studio agent (the chat box as Runway / Higgsfield / invideo run theirs)

**From:** a Claude Code session, 2026-10-10/11, worktree `project-look-config-62c331`.
**For:** the next Claude Code session in this repo on Mike's Mac.
**Read first:** `docs/tasks/task-studio-agent.md` (the record: the research, every item "as
built", the open decisions). Do not re-research. Then the `CLAUDE.md` entries it names.

**Mike's rules for this task, in his words:** "Don't make changes until i give approval / Build
on top of what I currently have / Suggest improvements / Do deep reserach on competitors and
different designs." In practice: one PR per numbered item, stop after each and report, merge
only when he says so, and an item approved to build is not approval to merge it or to start
the next one.

## State right now

- **Merged, all on his word.** Batch 1: #212 skills, #213 plan with step cards, #215 effects in
  chat, #217 "continue" actions, #219 draft then finish. The invideo batch: #230 item 6, #231
  item 7, #232 item 8 (one deploy, a92d31b), #238 item 9 (1aa1581), #243 item 10 (3e2a9b2),
  #249 item 11 (ecaa2b6).
- **Open, NOT merged: PR #262, item 12** — "the brain proposes the model a step is made on".
  Branch `claude/studio-agent-model-per-step`. CI at the time of writing: `web` passed, `test`
  still running. Mike has not said to merge it, and has not said to start item 13.
- **Not started:** 13 (an explore / execute switch per project), 14 (spend modes and a credit
  cap per project). **Held:** 15 (a casting skill for invented characters) — it reverses
  `prompts/stages/cast.md` and needs his explicit yes.
- **Nothing uncommitted.** No local server is running; every throwaway schema was dropped.
- **Tools kept for you** (gitignored, in the MAIN checkout):
  `/Users/iphone/Documents/PRODUCTION PIPLINE .GIT/data/_scratch_studio_agent/` — the stub
  servers, `seed.py`, `render_check.py`, and the screenshots already sent to Mike (`shots/`).
- **A side task is running in another session** (started by Mike from a chip): "Stop
  billing.balance creating tables on every read". Two balance reads at once deadlocked on the
  stub server (`billing.release_due` -> `billing.init` -> `db.own_table`). It is not this
  task's; do not fix it here.

### Traps

- **PR #262's "Vercel" check shows FAIL, and it is not the code.** Its text is "Deployment
  rate limited — retry in 24 hours": the Vercel project hit its daily build limit on
  2026-10-11, after a day of pushes from several sessions. Until it resets, a merge that
  touches `web/` deploys the API on Fly but NOT the studio front end. For #262 that split is
  harmless (an older page ignores the new `model` arguments and never sends `render_model`),
  but say so to Mike before merging, and check the front end actually went live afterwards.
  The live stylesheet had items 9, 10 and 11 at handoff (`.zpa-facts`, `.zlr-card`,
  `.zc-num`); item 12's marker is `.ss-opt`. Read-only check: fetch
  `https://zeropage.studio/studio`, follow its `/_next/static/*.css` links, grep the class.

- **Main moves 15 to 40 commits between two of your pushes.** Other sessions merge all day.
  Twice a test from this task went red ON MAIN because of someone else's merge (a skill
  sentence after the sheet's background changed; a gate renamed to
  `charge.create_refusal_code`). After every sync, re-run this task's own test files:
  `tests/test_skills.py tests/test_make_plan.py tests/test_effects_studio.py
  tests/test_continue_actions.py tests/test_drafts.py tests/test_out_of_credits.py
  tests/test_ref_roles.py tests/test_linkrefs.py tests/test_look_research.py
  tests/test_look_tools.py tests/test_result_refs.py tests/test_model_menu.py`.
- **A push to main deploys Fly without waiting for CI.** Run the render check before every
  merge (below).
- **Bring main in with the app's tool**, `mcp__ccd_host__sync_with_base_branch` (base `main`),
  not `git merge`. Never force-push: once another session had already merged main into this
  task's PR branches on the remote, and the right move was to take theirs.
- **Guards that will bite:** `tests/test_project_look.py` holds that `prompts/look_*.txt` is
  `look_unset.txt` alone (name a new prompt file something else);
  `test_every_concept_writing_route_uses_the_one_collector` counts the literal
  `attach_refs=_attach_scene_refs`; every `/api` route must declare
  `auth.current_account_id`; a new `GET /assets/generated/...` route must sit above
  `/assets/{category}/{item_id}`; a job's result dict is merged onto the job, so never return
  a key called `kind`.
- **On a stub server, the plan's Render button reaches the real renderer check.** It was
  refused for having no key, and nothing was sent. Use `stub_server5.py` (it fakes
  `fal.generate_video`) before clicking any Render.
- **Chrome automation:** typing into the composer fails right after a navigation. Set the
  textarea with the native value setter plus an `input` event and click Send by script
  (`stub_server10`'s check did this). Base UI menus do not open from synthetic events; set
  the browser setting instead (`zpf:composer:generate`, `zpf:composer:image-model`).
- **This Mac is shared by several sessions.** Stop a server by PID only
  (`lsof -tiTCP:<port> -sTCP:LISTEN`), never `pkill -f`. Use the default `web/.next`, and
  afterwards `rm -rf web/.next` and `git checkout -- web/next-env.d.ts`. `npm run -s
  typecheck`, not bare `tsc`. Check a file name is free before writing a new file.
- eslint on main now reports 4 warnings, 0 errors: two old `<img>` ones and two "unused
  eslint-disable" lines in `web/src/app/studio/page.tsx` that arrived with main. Not ours.

## What was verified

Every item: its own tests, the wider suites, then a browser walk against the real routes with
the models replaced inside the server process. **No real model or provider was called for any
item** (one stray call to Google with a fake key was refused, during an element describe).

- Item 12 (PR #262): `tests/test_model_menu.py` 15 passed; 651 server tests around the Guide,
  pricing, providers and scenes before merging main; after it, 345 of the Guide and pricing
  set passed and the 3 that failed were item 11's route test (fixed in this PR, 14 passed);
  `web` 187 unit tests, typecheck clean. Browser, with a CHARGED test account (400 credits):
  a poster proposed for Ideogram at 15 credits while the picker held Nano Banana at 10, the
  price following a change on the card, the still drawn on the chosen model; a scene proposed
  for Kling with its quote on Kling though written for LTX; a plan with a model per step and
  the total following an edit; with Auto on the dearer proposal waited and a same-price one
  drew at once; the no-references warning; a 390px frame.
- Full Python suite from a clean copy: item 10 on `1119c4d` 3688 passed, 34 skipped, 8
  xfailed; item 11's merged tree 3764 passed, 34 skipped, 8 xfailed. The 34 skipped are all of
  `tests/test_research_agent.py`, switched off on main. Item 12's full run was still going at
  handoff; CI is the authority.
- After every merge: `https://zeropage-studio.fly.dev/api/me` 401, `/mcp/` 401,
  `https://zeropage.studio/studio` 200. Last checked after #249.

**Not verified, and said so to Mike each time:** how the live brain uses any of it (skills,
plans, effects, roles, link facts, look research, result numbers, proposed models). The first
real look research will be on the live site, because this Mac's Serper key is invalid. The live
composer showed fal's "Exhausted balance" on 2026-10-10 and was not re-checked. A finished
draft is priced the dear way (Topaz's page does not say which dimension its tiers measure), so
the first real finish should be compared with fal's invoice.

## What is next

Rules for the run: no renders and no paid calls; tests and `venv/bin/ruff check .` before every
push; conventional commit subjects with no model identifiers and no co-author trailer (the
`/ship` rule); PR bodies end with the Claude Code line; check CI once with
`mcp__ccd_pr__get_status` or one `gh pr checks`, never in a loop; a NEW look goes on a design
canvas for Mike's pick before code (reusing a card he already picked is fine); report in plain
language.

0. **PR #262 — only when Mike says merge.**
   ```bash
   git fetch origin && gh pr checks 262
   ```
   Confirm the PR head is the commit CI ran, then the render check as its own command:
   ```bash
   venv/bin/python "/Users/iphone/Documents/PRODUCTION PIPLINE .GIT/data/_scratch_studio_agent/render_check.py"
   ```
   It must print `open holds: 0 | generations in the last 10 min: 0 | unresolved fal requests: 0`.
   Then:
   ```bash
   gh pr merge 262 --merge
   ```
   Delete the remote branch, run the three live checks above, branch the next item from the
   new main.
1. **Item 13 — an explore / execute switch per project** (invideo: talk freely first, make
   only once switched). Not designed yet. What exists to build on: a project row
   (`src/projects.py`, additive columns), `creative_guide.project_note` (what a turn inside a
   project is told), `guide_tools.session(maker=...)` (whether make tools are offered at all),
   the composer's project chip and the workspace's right panel. A natural shape: a `mode`
   column on `projects`, explore = the turn is not handed the make tools and is told so,
   execute = today. The switch itself is a new control, so show Mike the design before code.
2. **Item 14 — spend modes and a credit cap per project** (the largest). The shape recommended
   to Mike and assumed unless he says otherwise: three modes (always ask / ask before anything
   that makes a clip / always allow), Ask first staying the default, and a cap per project
   that no mode can pass. Where the pieces are: `GENERATE_MODES` in `web/src/lib/composer.ts`,
   `needsApproval` / `alwaysAsks` in `web/src/lib/make-plan.ts`, `autoCovers` in
   `web/src/lib/step-model.ts`, `sendCost` in `web/src/lib/continue.ts`. The cap must be held
   on the SERVER, where a hold is taken (`src/charge.py`, `ledger.hold_for_render`), or it is
   a number on a page; a still made from the composer is filed outside a project today
   (`/generate/run` takes no project), which the cap has to account for.
3. **Item 15 — held.** Do not start it.

### Local browser check, in short

Throwaway Postgres: `postgresql://zeropage:zeropage@localhost:5432/zeropage`, one schema per
check (`options='-c search_path=<name>'`; drop it afterwards). Seed with
`appmain.init_tables()` and `accounts.seed(email)`, then either
`accounts.set_credit_exempt("zeropage", True)` or `ledger.grant(account, 400, "promo")` for a
charged account. Mint the cookie with `auth._serializer().dumps({"uid": ...})` under
`SESSION_SECRET=demo` and set it with `document.cookie` on a fresh `*.localhost` host. Start
a stub server (`stub_server3.py` is the base: every model replaced in-process; 5 adds a fake
renderer, 6 a still refused for a low balance, 7 link facts, 8 look research, 9 numbered
results, 10 proposed models) with `PYTHONPATH="$PWD:<scratch dir>"` and the R2 / FAL / Serper /
Stripe variables blank, and Next with `API_UPSTREAM=http://127.0.0.1:<port>`.

## Mike's calls

1. **Merge #262?** It was waiting on its `test` job at handoff.
2. **Start item 13?** And which shape: a per-project switch that withholds the make tools in
   explore (recommended), or only a note to the brain that it should not make yet.
3. **Item 14's shape.** Confirm the three modes and the per-project cap, and say what the cap
   counts: only scenes filed under the project, or also stills made from the composer while
   the project is open.
4. **Item 15, invented characters:** yes or no. It reverses the rule that a face is always an
   Element from real photos.
5. **A plan's render step and a proposed model.** Since item 12 that step is priced on the
   model the brain proposed for the scene (a Veo proposal made it 1,152 credits in the stub
   check). It still waits for his click beside the price. Keep that, or have a plan's render
   always price on the studio's default unless the person picked a model?
6. **A supervised live walk.** Nothing in either batch has been tried against the real brain.
   Does he want one (it costs model text only, no renders), and on which account?
