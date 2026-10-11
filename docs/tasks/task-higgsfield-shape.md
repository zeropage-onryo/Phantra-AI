# Task: the Higgsfield shape — no idea board, an output-based eval layer, prompts that learn

Written 2026-10-11 from Mike's decisions in chat. **PR 1 (steps 0–3) is built** — see
"As built" at the bottom, which also says what it decided where this plan left a choice open
and what it deliberately left alone. Steps 4–9 are not started. The open questions at the
bottom still need his answer before the step that depends on them starts; PR 1 took the
proposed answer to Q1, Q2 and Q4 and says so there.

## Why

The board was built for a pipeline that wrote ideas faster than a person could choose between
them: the night wrote, the morning picked, the pick was the label. The night is deleted
(2026-10-07), the Pipeline tab folded into Projects the same day, and Claude Desktop already
launches the studio MCP surface, which has no board tools. What is left of the board is
leftovers, and they still decide two important things: **a scene cannot be rendered until it
has been picked**, and **the eval layer is built on picks**.

The eval layer is not earning its place. Live numbers, read 2026-10-11:

| Signal | Rows |
|---|---|
| `prompt_scores` (the LLM rubric judge) | 470 |
| `generations` marked kept | 1 of 141 |
| `generated_assets` starred | 0 of 99 |
| concepts passed with a human reason | 1 |
| posted videos linked to a concept | 1 |

The rubric agreed with Mike's verdicts ~38% of the time (`credit_gate.md`, "THE GATES ARE
INVERTED"). It measures whether a prompt is complete; what actually fails is whether the shot
is feasible for the model and whether it looks good, and both only show in the output.

Higgsfield and Runway don't grade prompts. Their good prompts come from tested recipes (presets,
modes), per-model rewriters, reference images carrying the look so the prompt only directs
motion, and outcome data at scale (which outputs people keep). This plan copies that shape.

## Decisions (Mike's, 2026-10-11)

1. **No idea board.** The studio is Higgsfield-shaped: you make something and it lands in its
   project or on the Assets wall. The only decision is spend or don't, made at the moment of
   making, with the price shown.
2. **The eval layer moves from the idea to the output.** The unit is a generation; the signal is
   what the person does with it, collected without asking them to grade anything.
3. **The prompt-rubric judge goes.** Code checks that are facts (empty prompt, a leftover
   `{token}`, too short to render) stay.
4. **Prompts improve by per-model writing and by learning from the person's own keepers**, not by
   a judge.
5. **Nothing is lost.** Old picks, archive reasons, gate scores and hold grades are snapshotted
   before anything that reads them is removed. Scenes and renders are never deleted by this work.

Standing rules this work must keep: the spend is always quoted first and runs only on a yes (the
signed quote token, the ledger hold); nothing renders on its own; the reference gate stays.

## What goes, what stays

**Goes (this doc):** pick as the spend predicate; Pick / Not this one / the verdict keys on
scene lists; the Queue page as a separate stop; the board MCP surface and its tools on the hosted
connector; the Guide's board tools; the `zeropage-board` desktop entry; `pick_rate`,
`shoot_rate`, `reason_counts`, `evaluator_agreement`, `prompt_gate_agreement`; the Dev Studio's
Grade and Teach tabs; the rubric layer of `score_prompts`.

**Goes later (step 9, only on Mike's yes):** the scout and spark bank, `src/research_agent.py`,
the idea-agent skill, `prompts/sparks.txt`, `src/rework.py`.

**Stays:** projects, the workspace, the Director canvas, the composer and its brain, the Assets
wall, the cut editor, the ledger and signed quotes, the reference gate, edit-teach pairs
(`src/edit_teach.py`), the retrieval eval (hit@k / MRR), the cost tracker, `posted_outcomes`, the
uncanny judge (kept by Mike's earlier call), and `archived_at` on scenes as plain "hide".

## Steps

Each step is one PR unless noted. Every PR: `pytest tests/ -q` and ruff clean, `tsc` + eslint +
`node --test` for `web/`, and a click-through on a throwaway schema with every model call
stubbed. **No approve is clicked and no render runs during verification** (Mike's rule).

### Step 0 — snapshot (report first)

`ops/snapshot_board_evals.py`: for every account, writes to `data/backups/board-evals-<date>/`
(untracked; the repo is public) the picked / archived / reason columns of `shoot_concepts`,
`prompt_scores`, graded `hold_queue` rows, pending and ingested `winning_prompts` /
`avoid_prompts`, and the current output of the five rate functions. Report-only by default,
`--write` to save. Nothing is dropped in this whole doc; columns and tables are left in place
and simply stop being written or read.

### Step 1 — spend from the scene, not from the Queue

- `app.api.approve_render` and `approve_keyframes` stop requiring `picked or parked`
  (`not_queued` goes). Every other refusal stays and stays in order: no prompt, no reference
  (`preprod.reference_gate`), `missing_quote` / the six quote refusals, the ledger hold, the cap.
- The approve stamps `picked_at` (the column stays; it now means "was rendered on purpose").
- **A Render button on the scene**, in the workspace's scene list
  (`components/studio/project-workspace.tsx`) and on the solo canvas
  (`components/studio/scene-canvas.tsx`): renderer / length / frame pickers and the price, fed by
  the existing quote route. That's the Queue card's body moved onto the scene, not a second
  implementation. `GET /api/queue/{id}/quote` and `POST /api/queue/{id}/approve` get
  `/api/scenes/{id}/…` names; the old paths stay as aliases for one release.
- The composer's **Send to Queue** becomes **Render…**, opening the same priced card (the
  still step card's pattern, always "ask": a clip is never auto-rendered).
- Draw keyframes moves onto the scene the same way.
- The composer's plan runner (`src/make_plan.py`, `web/src/lib/make-plan.ts`) has a `queue`
  step that picks a scene. It becomes a `render` step: priced on the plan card once the scene
  exists, and it always stops for its own Approve, even under "Approve all" and Auto, because a
  plan never renders a clip unasked.
- **The Queue page becomes "Renders"**: what is running and what finished, off the job feed
  (`lib/jobs.ts`) and the activity tray. No approve lives there any more. The rail badge goes.
  Open question Q1.

### Step 2 — take the board out of the studio UI

- Remove Pick, Not this one, the archive-reason picker and the verdict keys
  (`lib/verdict-keys.ts`, `lib/use-verdict-keys.ts`) from scene lists. "Remove scene" stays, as
  archive with no reason.
- `POST /api/concepts/{id}/pick` is deleted. `POST /api/concepts/{id}/archive` stays (hide /
  unhide); its `reason` is ignored.
- The scene drawer keeps the prompt editor and the references; it loses the verdict row.
- `GET /api/pipeline/concepts` stays as the workspace's scene listing; the `status` filter
  reduces to live / removed.
- `web/src/lib/legacy-routes.ts` redirects stay.

### Step 3 — the board leaves both MCP doors and the Guide

- `mcp_server.LISTED_TOOLS` (the hosted connector) drops `board`, `idea`, `search`, `capture`,
  `pick`, `shoot`, `archive`, `stats`. It keeps `projects`, `project`, `project_chat`,
  `create_project`, `save_chat`, `elements`, `write_scene`, `quote`, `approve`, `job`.
  `write_scene` takes a `project_id` (or none) and creates the scene, rather than writing onto
  an existing idea. `approve` follows step 1's rules.
- **The board surface is deleted.** `SURFACES = ("studio",)`; the operator's static key on the
  HTTP mount gets the studio surface's tools instead of the board's.
  `src/research_agent.py` asked for `--surface board`; it stops working here and is removed in
  step 9 (open question Q3).
- `ops/claude-desktop-mcp.json` loses the `zeropage-board` entry; `ops/connect-claude.md` and
  `ops/register-claude-desktop.command` say so. That also settles the open init-time worry in
  CLAUDE.md: with one entry, Desktop never queues four inits.
- Guide: `guide_tools.READ_TOOLS` drops `board`, `sparks`, `stats`, `tonight`;
  `WRITE_TOOLS` drops `add_spark`. The Guide prompts lose every line that offers them.
- `TITLES` / `DESCRIPTIONS` / `HINTS`, the mount's ordering test, the directory docs
  (`docs/directory/`) and the public plugin repo's skills get the same cut.

### Step 4 — the eval layer, part A: outcome events

One OWNED table, `output_events`: `id, account_id, generation_id, asset_id, event, source, meta,
at`. One writer, `src/outcomes.py record(...)`, which never raises (the `spend.record_call`
shape). The vocabulary is closed:

| Kept | Discarded | Edited |
|---|---|---|
| `cut_add` — a `gen:` handle enters a timeline (`src/cut/projects.py`, `assemble_clips`) | `delete` — the wall's soft delete | `prompt_edit` — `edit_teach`'s pair, linked to the generation it led to |
| `export` — a cut containing it is exported | `regen` — the same scene part, or the same prompt hash, rendered again within 10 minutes with nothing kept in between | |
| `element_from` — a render becomes an element (`photo_urls` on the create routes) | | |
| `ref_reuse` — a `gen:` id is used as a reference or a clip source (the composer's "Use as reference" and effect cards, `/api/effects/run`, the MCP, `edit_clip`, `apply_effect`) | | |
| `continued` — any of the result's continue actions that makes something from it (Variation, Animate, Turn into a shot; `web/src/lib/continue.ts`) | | |
| `download` — `GET /api/assets/generated/{id}/download` | | |
| `star` — the wall's star | | |
| `post` — a `videos` row is linked to it | | |

`generations.kept` becomes derived (any kept event sets it), so `tool_scoreboard` and
`attempts_to_keeper`, which already exist and read `kept`, start meaning something.
A backfill pass (`ops/backfill_output_events.py`, report first) reads what already happened:
timelines' handles, element photos that point at renders, deleted assets.

### Step 5 — the eval layer, part B: new numbers, old tabs out

- **Dev Studio Stats** shows: keep rate by model, by brain tier and by writer template hash;
  attempts before a keeper; **credits per kept output** (ledger settles joined to kept
  generations); discard mix (deleted vs regenerated). Windowed by week, per account, never
  averaged across accounts.
- The five old tiles go. Grade and Teach go: `/grade/*`, `/concepts/{id}/grade`, `/pass`,
  `/concepts/grade-all`, `_dev_grade.html`, `_dev_graded.html`.
- **Teach ingested pending pairs by hand; now it happens automatically.** An edit-teach pair is
  ingested onto the winning / avoid shelves when the generation made from the edited prompt
  gets a kept event. A pair whose output is discarded is withdrawn.
- `posted_outcomes` and the retrieval eval stay as they are.

### Step 6 — the rubric judge goes

- `orchestrator.score_prompts` keeps layer 1 (`_structural_check`) and loses the LLM rubric;
  `PROMPT_GATE_MIN`, the `prompt_gate_min` setting and `ZEROPAGE_GATES` go with it.
  `prompt_scores` stops being written.
- The rubric's checklist (subject, camera, motion, lighting, coherence) moves into the writer
  templates as instructions, where it costs nothing.
- `src.trigger` still runs the graph by hand; it just has no judge in the middle.

### Step 7 — prompts that learn (per-model writing, tested recipes, your own keepers)

This is the "per-model prompt dialects" item `task-studio-agent.md` lists as not built; it
goes beside the skill shelf (`src/skills.py`), not in place of it.

1. **Audit first, then build.** Confirm what a model actually receives: `fal.generate_for_shot`
   sends `target["prompt"]` as written, and `shot.py`'s per-platform renderers
   (`render_kling`, `render_ltx`, …) look unused at the render boundary. Write down the finding
   before changing it.
2. **Per-model prompt at the render boundary.** One function, `prompts_for.render(model, part,
   anchored)`: when a keyframe or reference anchors the clip, a short motion-and-camera prompt
   in that model's dialect; when nothing anchors it, the full scene. Each model's rules live in a
   dated table beside `fal.VIDEO_MODELS` (the `task-runway-prompting-best-practices.md` /
   `task-veo-prompting-best-practices.md` pattern), checked against the vendor's own guide.
3. **Presets become tested recipes.** `prompts/presets.json` rows gain `kept` / `tried` counts
   from step 4; the composer's `/` menu sorts by keep rate and marks untested ones.
4. **Few-shot from the person's own keepers.** The writer's retrieval draws from winning prompts
   **whose output was kept**, same model family first, the caller's account first
   (`prefer_project`, as today).

### Step 8 — offline brain eval, then an output judge

- **A frozen brief set.** ~30 briefs with their references, chosen with Mike from the surviving
  scenes, in `evals/briefs/`. `python -m src.brain_eval --a <template|tier> --b <…>` writes both
  sides and has Claude compare each pair blind, then prints the wins and the pairs worth a human
  look. Model text only: nothing renders.
- **An output judge, advisory.** After ~100 kept/discarded events: a vision check on stills
  against their references (identity, reference adherence, stray text, artifacts). It records
  only. Its agreement with the keep signal is on the Stats tab; it only becomes a gate if that
  number is high and Mike says so. The clip-level hook already exists
  (`orchestrator.JUDGE` / `select_clip`).

### Step 9 — the second pass (only on Mike's yes)

Scout and spark bank (`src/scout.py`, `scout_findings`, `scout_bin` stay readable), the research
agent, the idea-agent skill, `sparks.txt`, `rework`, `promote_winners`' proposal flow. CLAUDE.md's
"Where the project stands" and every section naming the board are rewritten in the same PR.

## Order

PR 1 = steps 0–3 (the board is gone, spending is from the scene). PR 2 = steps 4–6. PR 3 =
step 7. PR 4 = step 8. PR 5 = step 9. PR 1 is the one that changes how the studio feels; the
rest change what it learns.

## Open questions for Mike

- **Q1. The Queue page:** turn it into "Renders" (running and finished jobs), or remove it and
  rely on the activity tray?
- **Q2. Video spend in the composer:** always ask (proposed), or follow the Ask first / Auto
  pill like stills do?
- **Q3. The research agent and scout:** delete in step 9, or keep as a CLI you run by hand?
- **Q4. The hosted connector's `stats` tool:** drop it (proposed), or bring it back once step 5's
  keep numbers exist?
- **Q5. The brief set in step 8:** pick the ~30 together, or let Claude propose and you strike?

## As built — PR 1 (steps 0–3), 2026-10-11

Mike's go-ahead was "do the tasks". Q1, Q2 and Q4 were taken as proposed in this doc (Renders
page; a clip always asks; `stats` dropped). Each is one line to reverse.

### Step 0 — the snapshot

`ops/snapshot_board_evals.py` (tests: `tests/test_snapshot_board_evals.py`). Report by default,
`--write` saves `data/backups/board-evals-<date>/`: one `account-<id>-<slug>.json` per account
(the label columns of every concept, never the prompt; graded holds; `pick_rate`,
`shoot_rate`, `reason_counts`, `evaluator_agreement`, `ungrounded_count`), `shared.json`
(`prompt_scores`, `winning_prompts` both shelves, `prompt_gate_agreement`,
`first_try_pass_rate`) and a manifest. It refuses to overwrite a snapshot and never guesses the
database. **It has not been run against the live database** — that is the one thing to do
before PR 1 is deployed, because after it `picked_at` starts meaning "rendered on purpose" and
un-archiving a scene clears its old reason. From the MAIN checkout (a worktree's `data/` is
pruned with it), with `DATABASE_URL` exported for the live database:

    venv/bin/python -m ops.snapshot_board_evals            # read the report
    venv/bin/python -m ops.snapshot_board_evals --write

### Step 1 — spend from the scene

- `app.api.approve_render` no longer refuses `not_queued`; every other refusal is unchanged and
  in the same order. It stamps `picked_at` before the spend, as before — and now also files the
  project's "pick" lesson there (`projects.remember_decision`), because the board's pick was
  what used to teach the project and it is gone.
- Routes: `GET /api/scenes/{id}/render` (new: the Render card's whole state in one answer — the
  scene card, `render_default`, the default pick's `quote` with its tokens, `blocked`, the
  renderer catalogue), `GET /api/scenes/{id}/quote`, `POST /api/scenes/{id}/approve`,
  `POST /api/scenes/{id}/keyframes`. The old `/api/queue/{id}/quote`, `/api/queue/{id}/approve`
  and `/api/concepts/{id}/keyframes` are the same functions under a second decorator, for one
  release. The render and keyframe jobs now carry `ref_id` from the start, so a scene can say
  "rendering" off the live job list and a failed render's row links back to its scene.
- **One Render card**, `web/src/components/studio/render-card.tsx` (`RenderCard`,
  `RenderDialog`): the Queue card's body — shot strip, priced "Draw keyframes first", renderer
  chip with model / length / frame, the priced Render button, the locked and partial states.
  Opened from the workspace's scene list (the clapperboard button), the canvas ("Render…", in a
  project and solo) and the composer's result row. Nothing in it computes a price.
- The composer's **Send to Queue is Render…** (`lib/continue.ts`), always asked.
- The plan's `queue` step is a **`render` step** (`src/make_plan.py`, `web/src/lib/make-plan.ts`):
  priced when the plan reaches it, at the scene's default renderer, and it always stops for its
  own button — "Approve all" neither counts nor covers it (`batchOf`), Auto does not cover it
  (`alwaysAsks`), and its approval only counts once a price is on the card. A price that moved
  between the card and the click stops the step instead of spending. `queue` in a saved plan,
  or from the model, is read as `render`.
- **Renders** (`/studio/renders`; `/studio/queue` redirects): Jobs off the one job stream, then
  "Not finished" (`GET /api/renders/unfinished`, off the rows: a render that failed or was cut
  short, a timed scene with some shots rendered, anything picked or parked before today — each
  links to its scene, nothing is priced or approved there), then Ready to cut and the
  operator's manual import lane, both as they were. The rail badge and its 60-second poll are
  gone.

### Step 2 — the board out of the studio UI

- Pick, "Not this one", the A / X keys and their hint are gone from the scene list;
  `lib/verdict-keys.ts`, `lib/use-verdict-keys.ts` and their test are deleted. **Remove** stays:
  a plain hide with an Undo.
- `POST /api/concepts/{id}/pick` is deleted. `POST /api/concepts/{id}/archive` files no verdict
  and writes no "passed" lesson; a `reason` in the body is ignored. Putting a scene back still
  withdraws a pending board lesson and the project's "passed" entry filed before today.
- The drawer lost the prompt gate's verdict row; the warnings that are facts stay.
- The projects board's card no longer prints a "picked" count.

### Step 3 — the board off both MCP doors and the Guide

- `LISTED_TOOLS` is the ten this doc lists. `write_scene(prompt, seconds, refs, title,
  project_id, scene_id)` makes the scene (or, with `scene_id`, rewrites one) and returns
  `scene_id`; `quote` and `approve` take `scene_id`. Everything that can refuse refuses before a
  row is written.
- `SURFACES = ("studio",)`. `build_server()` defaults to the studio; `surface="board"` raises.
  The HTTP mount gives the operator's key the studio surface, built with `local_files=False` so
  `import_file` — which reads the disk of the machine the server runs on — stays a stdio-only
  tool. `--surface board` and `--engine` on the command line are accepted, ignored and said so.
- Removed with the surface: the board tools and their functions (`list_ideas`, `get_idea`,
  `search_ideas`, `capture_idea`, `pick_idea`, `shoot_idea`, `archive_idea`, `pipeline_stats`)
  and the registrations of the spark-bank and engine tools. The spark-bank and graph functions
  themselves stay as plain functions (`ops/bank.py` uses two of them) until step 9.
- **The Guide has no MCP bridge at all now.** After `board`, `sparks`, `stats`, `tonight` and
  `add_spark` went, the two left had nothing to do: `reference` banks an image behind a spark
  the model can no longer look up, and `images_for` was already hidden on every Guide turn. So
  `READ_TOOLS` / `WRITE_TOOLS` are empty, `guide_tools` imports no `mcp`, and the Guide's own
  tools (references, footage search, skills, effects, projects, the makes) are unchanged.
- `ops/claude-desktop-mcp.json` has one entry; `ops/register-claude-desktop.command` removes a
  leftover `zeropage-board` from the Desktop config (with its usual backup).
- `src/research_agent.py` answers "not runnable" from `ready()` with the reason; its 34 old
  tests are skipped with that reason and `tests/test_research_agent_gone.py` asserts what is
  true now. Deleting or rebuilding it is still step 9.
- `docs/directory/SUBMISSION.md` has the new tool list, listing copy and reviewer steps; the
  four older records there carry a dated note.

### Decided here because the plan did not say

1. **The project learns from the approve.** See step 1. Without it a project's memory would
   only ever learn from hand edits.
2. **The legacy `/ui` shell** (reachable at `/ui?legacy=1`) lost its Pick button, since the
   route is gone; its Queue view still lists and approves through the old `/api/queue/...`
   paths. It was not rebuilt.
3. **The public site's copy** said "the Queue" in about fifty places (the model landing pages,
   FAQ, pricing, models, privacy, the plan cards). Reworded to "the scene's Render card" in its
   own commit, so it can be dropped or re-edited on its own.
4. **`/api/queue/pending`, `/queue/count`, `/queue/{id}/reject`, `/queue/{id}/shot`** still
   answer. Only the legacy shell and tests call them.

### Merged with main the same day: draft, then finish

Main gained "draft, then finish" (PR #219, `src/drafts.py`) on the Queue page while this was
being built. It is carried over rather than dropped:

- **Draft first** is on the Render card, under the renderer chip, where the Queue card had
  it. It only moves the pick to the model's cheapest frame; the priced button then reads
  "Draft · n shots · price" and is still the one click that spends.
- **Finish shot NN** is on the Renders page's "Ready to cut" cards, where the Queue page had
  it: two clicks, the first only shows the price. It is the upscale effect
  (`/api/effects/run`), not a render, and it is the one button on Renders that spends. Say if
  it should move onto the scene's Render card instead.
- The Library's draft line links to Renders.

### Left alone, and what that means

- **The manual import lane** still lists picked scenes with no clip yet. Nothing picks a scene
  any more except the render approve, so a new scene gets there only once a paid render was
  started on it and did not finish; scenes picked before 2026-10-11 still list. BACKLOG #21
  already expects the lane to be retired; say if it should instead list every unrendered scene.
- **The public plugin repo** (`../zeropage-studio-plugin`, its skills name `board`, `pick`,
  `capture`…) is not touched: it is a separate public repository. It needs the same cut before
  the listing is submitted.
- **The directory listing** was walked live on the old tool set; that walk, and one scene on the
  reviewer account written with the new `write_scene`, are owed before submitting. If the
  listing has already been submitted, the reviewers need to know the tools changed.
- **The idea-agent skill** drove the board tools and has nothing to drive (step 9).
- **`pick_rate`, `shoot_rate`, the Dev Studio's Grade and Teach tabs, the prompt gate** are all
  still there and still computed — steps 5 and 6. From this PR on `pick_rate` counts scenes
  whose render was approved, which is why the snapshot comes first.
- The keyframes quote on a half-rendered timed scene counts a still for every shot without
  one, including shots that already have a clip. It did before; noted, not changed.

### Verified

The backend test suite and ruff; the web typecheck, eslint and node tests. A click-through on
a throwaway schema with every model, still and render call replaced in the server process: the
workspace's scene list and its Render card (priced, re-priced on another model through
`/quote`, partial, blocked with the link to attach references, rendered), the canvas button,
the composer's Render…, a plan ending on a render step (it waited with its own button and no
"Approve all"), the Renders page, the `/studio/queue` redirect, and the dialog at phone width.
**No approve was clicked and nothing was rendered or drawn.** Not verified: a real render
through the new route (the API tests cover the body with fal stood in for), and how the live
brain uses the `render` step.

## As built — PR 2, step 4 (outcome events), 2026-10-11

`src/outcomes.py` is the module; `tests/test_outcomes.py`, `tests/test_outcome_hooks.py` and
`tests/test_backfill_output_events.py` hold its rules.

### The table and the writer

- `output_events` (OWNED): `id, at, account_id, generation_id, asset_id, event, source, meta`.
  Created at start-up by the web app and by the stdio MCP entry point.
- `outcomes.record(event, asset_id= | generation_id=, account_id=, source=, meta=)` is the one
  writer and never raises. It writes only about an output the caller's own account owns; an
  id that is somebody else's, or nobody's, records nothing.
- A kept event sets `generations.kept = 1` on the output's attempt row. Nothing un-sets it.
  `generative.tool_scoreboard` and `costs.render_costs` already read that column, so the
  cost-per-kept-clip figures on `/costs` start to mean something. (`generative.attempts_to_keeper`
  does not: every render makes its own `shots` row, so it always reads one attempt. The new
  attempts figure is `outcomes.attempts_before_keeper`, step 5.)

### Where each event is recorded

| Event | Where |
|---|---|
| `star` | `PATCH /api/assets/generated/{id}` when `starred` is set to true |
| `delete` | `DELETE /api/assets/generated/{id}`; the Undo (`/restore`) takes the event back |
| `download` | `GET /api/assets/generated/{id}/download`, when a file is actually served |
| `element_from` | the three element create routes, for each `photo_urls` entry that is a render |
| `ref_reuse` | `effects.run` (every effect door: the composer, the MCP, `edit_clip`, a draft's Finish); `/api/scenes/run` and `/api/generate/run` for a render sent back as a reference; the MCP's `generate_image` / `generate_video` once approved |
| `continued` | `/api/generate/run` when the form carries `continued_from=gen:<id>` (a Variation) |
| `cut_add` | `cut.store.save_version`: an output on this version that was not on its parent |
| `export` | `cut.render.render`, for every output in the cut, on success |
| `post` | `POST /api/holds/{id}/post`, on a live post that went out |
| `regen` | `outcomes.note_new`, called by `render_assets.record` for every new output |
| `prompt_edit` | the same place, when the new output is on a shot with a pending edit pair |

### Decided here because the plan did not say

- **A render is recognised by its file, not by the string.** The composer holds minted URLs,
  so "is this reference one of my outputs" is asked of the object's own tail
  (`renders/<provider>/<file>`). An upload or an element's photo is not an output and
  records nothing.
- **`continued` is Variation only.** "Turn into a shot" and "Use as reference" send the
  still back as a reference, so they are recorded as `ref_reuse`. "Animate" goes through the
  effects door and is `ref_reuse` too. All four are kept events; only the name differs.
- **Regen, exactly:** an earlier output of the same account and kind, made in the last ten
  minutes, for the same scene part (concept, shot, part) or, where there is no scene, from
  the same prompt on the same model with the same sources, that has no kept event and is not
  already discarded. An output is never a regen of what it was MADE FROM.
- **An undone delete is withdrawn.** The Undo removes the `delete` event: it was a slip of
  the hand, not a verdict.
- **The edit pair is settled here, ahead of step 5:** a kept event on an output made from an
  edited prompt ingests the pair (`winners.ingest_pending`); a discard withdraws the pair only
  when EVERY output made from that edit is discarded.
- **`post` had no writer to hook.** Nothing in the code links a `videos` row to a scene, so
  the event is recorded where a clip is actually published instead.

### The backfill

`ops/backfill_output_events.py` (report first, `--write`, re-runnable, never guesses the
database): `cut_add` for every output on a cut's timeline, dated at the version it first
appeared in; `export` for every output in an exported version; `star` and `delete` from the
wall's own columns; `element_from` only where this machine holds both files, because an
element photo made from a render is named by a hash of its bytes. Downloads, references,
continue actions, regenerations and posts left no trace and are not invented.

### Not done

- The MCP's two reference hooks have no test of their own (the helper they call does).
- The backfill has not been run against any real database.
- A Variation step that waits on Approve across a page reload may lose its `continued_from`,
  if the saved thread drops the field. Not checked.
