# Handoff: finish the overnight connector build (2026-10-12)

**From:** the unattended Claude Code session that ran `docs/tasks/task-connector-overnight.md`
on the night of 2026-10-11 → 10-12 (worktree `.claude/worktrees/clever-bhabha-609359`).
**For:** one new session on Mike's Mac, to finish PRs 6 and 7 and write the task doc's
"As built" report. **Rules are the task doc's**: nothing spends, nothing goes live (push
branches and open PRs only, never merge, never deploy, never write the live database),
every edit makes a new item, each PR's full suite green and `ruff check .` clean.

> **Finished (2026-10-12, the session that picked this up).** Every item below is done: PR 4's
> merged tip ran green (3,961 passed), PR 6 is
> https://github.com/zeropage-onryo/zeropage-studio-plugin/pull/4 (after 57 corrections to the
> skills, found by verifying them against the code), PR 7 is this branch's PR, and the
> `suite-*` worktrees are removed. The state below is the night's; the current state is the
> "As built" section at the bottom of `task-connector-overnight.md`.

## State at handoff (all pushed unless marked)

Five stacked PRs are OPEN in `zeropage-onryo/video-pipeline`, each branch from the previous:

| PR | branch (tip) | base | full suite |
|---|---|---|---|
| #276 PR 1 uploads | `claude/connector-overnight-1-uploads` (f43e380) | main | **green** (3890 passed, 34 skipped, 8 xfailed) |
| #277 PR 2 library | `claude/connector-overnight-2-library` (2490176) | PR 1 | first run 1 failure = the stale pin fixed in 2490176; the re-run `pr2b` was still running at handoff |
| #278 PR 3 reading | `claude/connector-overnight-3-reading` (e2aca89, merged 2 in) | PR 2 | first run (3df703c) 1 failure = the same pin; `pr3b` on e2aca89 was running |
| #279 PR 4 writes | `claude/connector-overnight-4-writes` (954e999, merged 3 in) | PR 3 | `pr4` on the pre-fix tip 5338579 was running (expect the same single pin failure); a run on 954e999 has NOT been started |
| #280 PR 5 insights | `claude/connector-overnight-5-insights` (ac7ad59, merged 4 in) | PR 4 | `pr5` on ac7ad59 was running |
| (PR 7 docs) | `claude/connector-overnight-7-docs` (facfffc + this handoff) | PR 5 | not run; docs only; **no PR opened yet** |

The one failure seen in every pre-fix suite is `tests/test_mcp_add_element.py::
test_the_claude_listing_adds_a_picture_and_still_draws_nothing`, a pin that said `job` was
not on the Claude listing. PR 2 put `job` there (the free edits start jobs); the pin was
fixed in 2490176 and merged forward into 3, 4 and 5. Nothing else failed in 3,890+ tests.

PR 6 is in the plugin repo `/Users/iphone/Documents/zeropage-studio-plugin`, branch
`claude/v0.3.0-skills` (from main 02995db), **uncommitted**: `plugin.json` (0.3.0, new
description), `README.md` (rewritten: 32-tool table, 22 skills, data section), 17 new skill
folders and 2 updated ones, written by a Workflow of agents from the brief in the scratchpad.
`claude plugin validate .` passed on the manifest. The workflow (run id `wf_46d2484f-57a`,
journal under `~/.claude/projects/-Users-iphone-Documents-PRODUCTION-PIPLINE--GIT--claude-
worktrees-clever-bhabha-609359/ba780487-391c-49f6-aa78-cd2658864ad5/subagents/workflows/`)
had written all 7 batches and finished 13 of 19 verifications when this session stopped;
its verdicts (ok / problems per skill) are in `journal.jsonl`.

## Where things are

- **Worktree:** `/Users/iphone/Documents/PRODUCTION PIPLINE .GIT/.claude/worktrees/clever-bhabha-609359`,
  on branch `claude/connector-overnight-7-docs`. `venv` is a symlink to the main checkout's.
  **Run every test with** `PYTHONPATH="$S/pyfix:$PWD" venv/bin/python -m pytest ...` where
  `$S/pyfix/sitecustomize.py` drops the editable finder (else `src` resolves to the MAIN
  checkout). `$S` = the session scratchpad:
  `/private/tmp/claude-501/-Users-iphone-Documents-PRODUCTION-PIPLINE--GIT--claude-worktrees-clever-bhabha-609359/ba780487-391c-49f6-aa78-cd2658864ad5/scratchpad`
  (a new session gets its own scratchpad; recreate `pyfix/sitecustomize.py` -- two lines:
  `import sys; sys.meta_path[:] = [f for f in sys.meta_path if "_EditableFinder" not in repr(f)]`).
- **Full suites** run detached by `$S/run_suite.sh <sha> <label>`: a scratch worktree at
  `$S/suite-<label>` (venv symlinked), `nohup`, log `$S/suite-<label>.log` whose last line is
  `pytest exit: N`, pid in `$S/suite-<label>.pid`. Seven such worktrees exist
  (`git worktree list | grep suite-`); remove them with `git worktree remove --force` when
  their runs are done (kill only by the pid file, never by name -- other sessions run pytest).
  A full run takes 28-32 min alone, longer with others.
- **Throwaway Postgres:** `postgresql://zeropage:zeropage@localhost:5432/zeropage` (Postgres.app
  18), conftest's `TEST_DSN`; the `pg` fixture makes a schema per test.
- **PR bodies** for 1-5 are in `$S/pr<N>-body.md`; `$S/pr6-body.md` is drafted and unused.
- **Skill brief and tool dump** for the plugin: `$S/skill-brief.md`, `$S/claude-tools.md`
  (the 32 tools on `/mcp/claude` with their descriptions, generated off the code).
- **Skill checker:** `$S/overnight_check_skills.py` (lines < 100, frontmatter, tool names
  against the listing, operator words, money figures). `$S/check_skills.py` was OVERWRITTEN
  by a workflow agent with its own checker (shared scratchpad; name collision) -- use the
  `overnight_` one. Run it with `venv/bin/python -I`.

## What the five PRs built (read each PR's body for the live checks)

1. `upload_link` + the `/u/<token>` page (`src/upload_links.py`, `app/upload_page.py`,
   `templates/upload.html`, OWNED `upload_claims`); `add_element` from a product page;
   `mcp_server.CALLER_USER` set by the mount's guard. Tests `tests/test_upload_link.py`.
2. `library`, `share_link`, `reformat`, `trim_clip` (`src/cut/quick.py`), `assemble_clips`
   on both listings, `job(wait)` back on the Claude listing. `tests/test_connector_library.py`.
3. `balance`, `search`, `whoami`, `recent`, `credit_history`, `video_models` (credits on a
   listed server), `recommend_model` (`src/model_pick.py`). `tests/test_connector_reading.py`.
4. `roles` on `write_scene`, `duplicate_scene`, `feedback`, `preferences`/`set_preferences`,
   `recipes`/`recipe`/`save_recipe`; three OWNED tables (`src/mcp_feedback.py`,
   `src/mcp_preferences.py`, `src/mcp_recipes.py`). `tests/test_connector_writes.py`.
5. `what_works`, `score_caption`. `tests/test_connector_insights.py`.

CLAUDE.md's MCP block has one paragraph per PR (search "task-connector-overnight"). The
Claude listing is 32 tools, `/mcp` 34; the tuples and their order are pinned in
`tests/test_mcp_server.py::test_the_two_servers_publish_exactly_their_sets`.

## What is left, in order

1. **Read the suite logs** (`grep "pytest exit" $S/suite-*.log`). Expected: `pr2b`, `pr3b`,
   `pr5` exit 0; `pr4` exit 1 with only the stale pin (it ran on 5338579). Start
   `run_suite.sh 954e999 pr4b` for PR 4's merged tip and confirm exit 0. If anything else
   fails, fix on the lowest branch it belongs to, commit, push, and merge forward
   (`git merge --no-edit <previous branch>` on each later branch, push each) -- the pattern
   used for the pin fix.
2. **Finish PR 6 (the plugin).** In the plugin repo on `claude/v0.3.0-skills`:
   - read the workflow's verdicts in `journal.jsonl` (or re-read each skill yourself) and
     fix any problem; the three batch-E skills (`ugc-ad`, `product-shots`, `ad-variations`)
     were the last written -- check they exist and are under 100 lines;
   - run `venv/bin/python -I $S/overnight_check_skills.py` from the plugin repo: every skill
     "ok" except two pre-existing files you may leave (`write-scene` is 111 lines since
     v0.2.0; `ideas-and-projects` says "there is no idea board", true and in the negative);
   - run `claude plugin validate .` (must pass; put the date in the README's "Validated");
   - `git add -A && git commit` (attribution line as the main repo), `git push -u origin
     claude/v0.3.0-skills`, `gh pr create --base main --body-file $S/pr6-body.md` with the
     title "Plugin v0.3.0: seventeen skills for the overnight connector tools". Never merge.
3. **Finish PR 7 (docs).** On `claude/connector-overnight-7-docs` (this file is committed
   there; `docs/directory/SUBMISSION.md` and `TWO_LISTINGS.md` are already updated in
   facfffc): write the **"As built"** section at the bottom of
   `docs/tasks/task-connector-overnight.md` -- per PR: link, status (ready / draft), what it
   does, what was NOT done and why, anything Mike must decide, the exact live checks to run
   after deploy as the test account (each PR body already has a "Live check after deploy"
   list and a "Not done / to decide" list: copy them in). Then commit, `git push -u origin
   claude/connector-overnight-7-docs`, `gh pr create --base claude/connector-overnight-5-insights`
   with the title "docs: the submission pack and the As built report (overnight PR 7)".
   `web/` is untouched on purpose (no tool name there is wrong); the one `/connector` Limits
   sentence is item 18 of SUBMISSION.md's by-hand list.
4. **Clean up:** remove the `suite-*` worktrees once their runs are done; leave the branches.
5. **Report to Mike** in the final message: the five PR links + 6 + 7, each suite's result,
   and the by-hand list (set the test account's password; merge 1→7 in order; deploy; walk
   the reviewer steps on `/mcp/claude`; merge the plugin PR; submit; pair).

## Things that bit this session (so they do not bite twice)

- `git worktree list` and `gh pr list --state open` FIRST (memory rule); PRs #261-#275 from
  other sessions were open all night and none touched these files.
- The mount's operator key reaches the STUDIO surface at `/mcp`; a listed-only tool is
  reachable for the operator only on `/mcp/claude`.
- A still's probe shape carries `frames = STILL_SECONDS * fps`; a stub with `frames: 0`
  makes the validator refuse the insert.
- The suite turns the reference rule OFF outside `test_reference_*`: a draft assertion needs
  `monkeypatch.setattr(preprod, "refs_required", lambda: True)`.
- This FastAPI keeps included routers as `_IncludedRouter` entries: probe a route with
  `TestClient(main.app)`, not by enumerating `app.routes`.
- mcp 2.x `Tool` has `input_schema`, not `inputSchema`.
- A module-level function named `set` shadows the builtin inside that module (it did, in
  `mcp_preferences`; renamed `save`).
- Vercel builds are rate-limited; a failed Vercel check on a PR is not CI.
