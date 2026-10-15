# Remove the brand labels (scoped 2026-10-04; re-scoped and started 2026-10-13)

## Mike's calls, 2026-10-13 (these override the 2026-10-04 text below where they differ)

1. The two legacy brand names (`zeropage`, `antihero`, and `both`) leave the
   code completely. The studio is for anyone; a brand exists only inside a
   PROJECT (its brief and look), never studio-wide.
2. The brand labels leave the data, and the brand-era data is cleared: old
   scenes, scout findings, scout images. "We're starting with fresh data."
3. This is its own branch of work, separate from the rename. Branches are
   `claude/brand-removal-<n>-<what>`, one PR per step. Mike merges.
4. The LAST step renames account 1's slug `zeropage` -> `phantra`, which closes
   phase 6 of `task-rename-to-phantra.md`. It cannot go first:
   `app/api.py` derives `brand = slug if slug in preprod.BRANDS else "antihero"`
   (lines 732, 1035 on 2026-10-13), so the slug IS the brand until step 4.

**Live-data rule:** nothing is deleted or migrated without (a) a read-only
report of row counts per table and per account, (b) a JSON backup in the main
checkout's `data/backups/brand-removal-<date>/`, read back and counted, and
(c) Mike's yes in chat on that exact report. Ledger, billing and credit tables
are never touched.

## Decisions (D1-D4 answered by Mike 2026-10-13; D6 on 2026-10-14; D5 open)

| # | question | recommendation | answer |
| --- | --- | --- | --- |
| D1 | The uncanny judge (`src/uncanny_judge.py`, `orchestrator.brand_gate`) runs for brand `zeropage` only. Delete it, or run it for every account? | Delete it with its three `uncanny_*` columns. It only ever fed auto-post, which is off, and "on brand" has no meaning without a brand. |**Delete it.** |
| D2 | `channels` / autonomy / `autopilot.AUTO_POST_BRANDS` are keyed by brand name. Re-key per account, or remove? | Remove the `channels` table and `hold_queue.channel`; a graph run always holds (what happens today). `hold_queue` stays as the run log. |**Remove channels.** |
| D3 | `scout_findings` / `scout_bin` are SHARED tables with a brand column. Drop the column and keep the scout, or remove the scout? | Drop the column, clear the rows, keep the scout. Removing it is step 9 of `task-higgsfield-shape.md`, a separate call. |**Keep the scout, drop the column.** |
| D4 | `inspiration_accounts` (creator handles keyed by brand; 1 live row). Keep per account, or delete? | Delete the feature and the table: one shared list of handles steering every account's scenes is a studio-wide brand. |**Delete the feature.** |
| D6 | (2026-10-14, Mike, after the clear) Remove the hold queue entirely? | -- |**Yes: the table, the `/holds` page and `/api/holds` routes, the dev console's image "Queue" button, the cards' `gate` verdict (read through the hold row), the MCP run card's `gate`, the cost page's hold counts and the taste judge's hold grades. A graph run ends by returning why it stopped.** |
| D5 | Which scenes are "old"? All 49 live scenes say `brand='zeropage'`, including accounts 5 and 8, so the label cannot choose. | See "Proposed clear" below. | |

## Live data, read-only scan 2026-10-13

Accounts: 1 `zeropage`, 3, 4, 5 `zp-billing-test`, 6, 8.

| table | rows | label values | by account |
| --- | --- | --- | --- |
| `shoot_concepts` | 49 | `brand`: zeropage 49 | 1: 38, 5: 10, 8: 1 |
| `hold_queue` | 220 | `channel`: zeropage 220 (204 held, 14 rejected, 2 approved; 8 point at a scene that still exists) | 1: 220 |
| `prompt_scores` | 470 | none (keyed by run id; last row 2026-09-27) | shared |
| `scout_findings` | 205 | `brand`: zeropage 205 (167 used, 38 unused) | shared |
| `scout_bin` | 138 | `brand`: zeropage 138 (lanes: agent 121, generated 17) | shared |
| `workflows` | 10 | `brand`: zeropage 9, NULL 1 | 1: 8, 5: 2 |
| `generated_assets` | 110 | `project`: NULL 102, zeropage 6, antihero 2 | 1: 100, 5: 10 |
| `rag_documents` | 385 | `project`: zeropage 227 (assets 220, winning_prompts 7), NULL 139 (craft shelves), zp-billing-test 19 | shared |
| `videos` | 23 | `brand`: zeropage 1 (row 11), NULL 22 | 1: 23 |
| `inspiration_accounts` | 1 | `brand`: zeropage | shared |
| `channels` | 2 | names `antihero` (shadow), `zeropage` (queue) | shared |
| `scene_briefs`, `locations`, `settings`, `nightly_runs` | 0 | | |

What depends on the scenes:

- **Rendered clips on a scene (Library rows that must survive):** account 1:
  #121, #135, #194, #375 (one clip each), #384 (three); account 5: #411.
  Those 8 `generated_assets` rows are also the 8 that carry a `project` label.
- **The measured loop:** scene #375 <- `videos` row 11 (`concept_id`, 6 metric
  snapshots) and cut project `concept:375`. The other 22 `videos` rows (10
  legacy YouTube, 12 Instagram reels, 129 snapshots in all) link to no scene.
- **Projects:** only account 5 has one (project 1, 8 scenes). Account 1's
  scenes are in no project.
- **Saved canvases:** `workflows` rows for scenes 122, 194, 353, 354, 375, 402
  (account 1) and 409, 410 (account 5).
- **Scout images on a scene's shots:** scenes 192, 194, 195, 198, 354, 358
  carry bin images as refs. Clearing `scout_bin` rows removes only the source
  link on those tiles; the files stay in the bucket.
- **Accounts 5 and 8:** account 5's 10 scenes, 5 props, project and cuts are
  the billing and reviewer fixtures; account 8 has one smoke-test scene.

## Proposed clear (waits for Mike's yes on these exact numbers)

Delete:

- `shoot_concepts`, account 1: the 33 scenes with no rendered clip (everything
  except #121, #135, #194, #375, #384), with their `workflows` rows (4: scenes
  122, 353, 354, 402) and `concept_locations` (0).
- `hold_queue` 220, `prompt_scores` 470 (the unattended graph's run log, last
  written 2026-09-27; every row is channel `zeropage`).
- `scout_findings` 205, `scout_bin` 138.
- `inspiration_accounts` 1 and `channels` 2, if D2 and D4 are "remove".
- Dead since post-production was cut: `ideas` 20, `pitch_runs` 2.

Keep:

- Account 1's five rendered scenes, with the label removed. Deleting them would
  detach 7 paid clips from their prompts and break the one measured loop
  (#375 -> video 11 -> its metrics -> cut `concept:375`).
- Every `generated_assets`, `generations`, `shots`, `output_events` row.
- All 23 `videos` and 129 `metrics` rows.
- Everything in accounts 3, 4, 5, 6, 8.
- Elements, projects, cuts, uploads, MCP tables.
- RAG: the craft shelves (139 chunks) untouched; `assets` (220) and
  `winning_prompts` (7) keep their rows and are relabelled at the slug rename.
- `llm_calls`, `crag_retrievals`, `eval_*`, `image_candidates` (not brand data).
- Ledger, billing, credits, users, memberships: never touched.
- No bucket object is deleted.

## Where it stands (2026-10-14)

| step | PR | state |
| --- | --- | --- |
| 0 plan | #303 | merged |
| 1 account cookie | #304 | merged |
| 2 doors ignore a brand | #310 (replaced #308) | merged |
| 3 D1, D2, D4 deletions | #309 | merged |
| 4a scout, image search, spark tools (D3) | #313 | merged |
| 4b scene writer, graph, Guide | #314 | merged |
| 4c constants, store, API, dev console | #315 | merged |
| 5 the clear SCRIPT | #305 | merged; **RUN on live 2026-10-14** on Mike's yes (33 / 4 / 220 / 470 / 205 / 138 deleted; backup in the main checkout's `data/backups/brand-removal-2026-10-14/`) |
| 6 the schema SCRIPT | #316 | merged; report run, nothing changed |
| D6 the hold queue, removed | #320 | merged (two of its tests were left behind; fixed in the step 6 code PR) |
| 6 code: no brand column in any schema or INSERT | #322 | merged, deployed |
| 6 move 3 (live drop) | | **RUN on live 2026-10-15** on Mike's yes: the brand columns, the uncanny judge's three, `accounts.scout_instagram`, `idx_scout_brand_used`, the tables `channels`, `inspiration_accounts`, `hold_queue`, `scout_findings`, `scout_bin`; 8 Library project labels cleared. Report afterwards: nothing left. Backup in `data/backups/brand-removal-2026-10-15/schema/` |
| 7 leftovers: `/brand` alias, `brand` cookie, allowlist | this PR | open |
| 8 slug rename | #330 + this PR | **RUN on live 2026-10-15** on Mike's yes: account 1 is `phantra` / "Phantra AI", 224 `rag_documents.project` rows moved; backup in the main checkout's `data/backups/slug-rename-2026-10-15/` |

**Live schema, read 2026-10-14:** every brand column is already nullable
except `hold_queue.channel`, and that table now goes whole (D6), so move 1
has nothing left to do. 8 `generated_assets` rows carry an old brand name
as their project.

**Step 6, code half:** remove the brand columns from every `SCHEMA` string
and INSERT; drop `preprod.LEGACY_BRAND` and `scout.LEGACY_LABEL`.
(`autonomy.HOLD_CHANNEL` went with the hold queue.) Once that and the D6
PR are deployed, move 3 drops the columns and the three dead tables.

**The column order for step 6, decided while building step 2.** The `brand`
columns on `shoot_concepts`, `scene_briefs`, `scout_findings`, `scout_bin`
and `hold_queue.channel` are NOT NULL, so code cannot stop writing them
before the database lets it, and the database cannot drop them while code
still writes them. Three moves, the first and last on Mike's yes:

1. `ALTER ... DROP NOT NULL` on those columns (live; a loosening, nothing
   lost).
2. Merge and deploy the code that no longer names the columns anywhere.
3. Drop the columns, the index and the two dead tables (live).

Until move 2, every writer puts one constant there:
`preprod.LEGACY_BRAND` and `autonomy.HOLD_CHANNEL`.

## Step plan

Each step is one PR off `origin/main`, green in CI, merged by Mike.

1. **Account switching leaves the brand cookie.** A `phantra_account` cookie
   and `POST /account/{slug}`; `auth.current_account` reads it; `/api/me`, the
   React shell and `switchAccount`, the Next proxy rule, `accounts.html` and the
   classic shell follow. `POST /brand/{slug}` and the `brand` cookie are read as
   a fallback until step 7.
   *Done when:* switching workspaces works with no `brand` cookie set; a tab
   holding only the old cookie still lands on the same workspace.
2. **The doors stop asking.** Every `?brand=` / form `brand` / JSON `brand` on
   `/api/*` is accepted and ignored; MCP tool arguments named `brand` become
   optional and ignored; the web client and the classic shell stop sending it.
   *Done when:* `git grep -n brand -- web/src` is product copy only (the
   landing chip, `link-facts`), and no route's behaviour depends on the value.
3. **D1-D4 as decided:** the uncanny judge, `channels` / `AUTO_POST_BRANDS`,
   the scout's brand keying (`PINTEREST_BOARD_<BRAND>` -> `PINTEREST_BOARD`,
   the `scout_sources.txt` tags, the per-brand query dicts, `imagesearch`
   subreddits and `BRAND_LANES`), `inspiration`.
   *Done when:* no code path branches on a brand name.
4. **The pipeline loses the parameter.** `brand` leaves the signatures of
   shootgen, scene_chain, orchestrator, trigger, rework, refgen, scout,
   research_agent, creative_guide and the MCP server; `preprod.BRANDS`,
   `inspiration.BRANDS`, `scout.BRANDS`, `app.main.BRANDS / DEFAULT_BRAND /
   BRAND_META`, `mcp_server.DEFAULT_BRAND` are deleted; the one place that
   still names a label is the INSERT into each NOT NULL column (see "The
   column order" above); `generated_assets.project` is written as NULL.
   Tests: `tests/test_brand.py` deleted, conftest's `antihero` account gone.
   *Done when:* the constants are gone and a fresh schema has no NOT NULL
   brand column.
5. **The data clear** (live; report, backup, Mike's yes):
   `ops/brand_removal_clear.py` prints the report, `--backup` writes and
   re-reads the JSON, `--write` deletes in one transaction and prints counts
   after.
   *Done when:* the after-counts match the approved report.
6. **Columns dropped** (live; same rule): `shoot_concepts.brand`,
   `scene_briefs.brand`, `workflows.brand`, `videos.brand`,
   `scout_findings.brand` + `idx_scout_brand_used`, `scout_bin.brand`,
   `hold_queue.channel`, the `uncanny_*` columns and the removed tables, per
   D1-D4; `generated_assets.project` values set NULL. The schema in code drops
   them in the same PR, which deploys BEFORE the script runs.
   *Done when:* `information_schema.columns` has no `brand` column.
7. **Leftovers:** the `/brand/{slug}` alias and the `brand` cookie fallback,
   ops scripts' `--brand` flags, env names, the allowlist
   (`docs/tasks/brand-allowlist.txt`, each line with its reason).
   *Done when:* `git grep -niE "antihero|['\"]zeropage['\"]" -- src app ops
   web/src tests` prints only allowlisted lines.
8. **The slug rename** (live; same rule): `ops/rename_account_slug.py --from
   zeropage --to phantra [--write]`: `accounts.slug`, `rag_documents.project`,
   `RESERVED_SLUGS` (both names stay reserved), the seed in `src/accounts.py`,
   `PHANTRA_FOLDER_ACCOUNT` on the Mac, tests.
   *Done when:* `select slug from accounts where id = 1` is `phantra`, Mike
   signs in and `/api/me` shows it; tests, ruff and the web build are green.

---

# The 2026-10-04 scope (history; the survey is still the map)

**Mike's call:** the brand concept goes entirely. The creative half is already
gone (2026-10-04: no brand look files, no brand notes, no `brands.txt`, no
`BRAND_NOTES`, no likeness path, no `HOUSE_LOOK`, no `PHANTRA_FORMATS`, no
`CAST_BRANDS`, no brand-keyed crawl queries, no Zero Page templates). What is
left is the LABEL: the strings `"antihero"` / `"zeropage"` (and `"both"`)
carried on rows, cookies, routes, loops and tests. This doc scopes removing it.
Nothing here is built yet.

## Two facts that shape the plan

- **The `brand` cookie is also the account switcher.** `app/auth.py`
  `current_account` matches `request.cookies["brand"]` against the user's
  account slugs (verified 2026-10-04); `POST /brand/{name}` sets it and
  `/api/me` reads it. Removing the cookie without a replacement removes
  account switching.
- **"zeropage" is not only the brand.** It is also the database name in the
  DSN (`src/db.py`), the Fly app names, the seeded account slug, every
  `ZEROPAGE_*` env var, the MCP server name and the wordmark. A blind
  grep-and-replace breaks all of those. The `antihero` ACCOUNT was deleted on
  2026-09-28, but most code still defaults a missing brand to `"antihero"`.

## Inventory (from a read-only survey, 2026-10-04)

| area | what carries the brand | size |
| --- | --- | --- |
| Database | `shoot_concepts.brand` and `scene_briefs.brand` (NOT NULL, `preprod.py`); `scout_findings.brand` + `idx_scout_brand_used`, `scout_bin.brand` (`scout.py`); `inspiration_accounts.brand` (allows `both`); `workflows.brand`; `videos.brand`; `channels` rows named `zeropage`/`antihero` with `hold_queue.channel` holding the name (`autonomy.py`); `generated_assets.project` filled with the brand (`render_assets.py`, `fal.py`, `ops/render_queue.py`). `scheduled_posts` has none. | 8 columns, 1 index, live rows |
| Constants | `preprod.BRANDS`, `inspiration.BRANDS` (+`both`), `scout.BRANDS`; `app/main.py` `BRANDS` / `DEFAULT_BRAND` / `BRAND_META`; `autopilot.AUTO_POST_BRANDS`; `ValueError` brand checks in preprod, shootgen, scout, inspiration; MCP `_check` calls | ~25 sites |
| Routes / cookies | `brand` cookie (1-year) via `POST /brand/{name}`; `?brand=` / form `brand` on `/api/pipeline/*`, `/api/scenes/run`, `/api/scout/*`, `/api/queue/*`, `/api/director/landing`, `/api/generate/run`, `/api/analytics/*`, `/api/workflows`, `/api/cut/ready`; `/api/holds?channel=` | ~30 sites |
| Pipeline | ~110 functions take `brand`: shootgen (`load_brand`, the `{brand}` slot, `PHANTRA_AI_TOOLS` branches), scene_chain, orchestrator (`state["brand"]`, `brand_gate` runs the uncanny judge on zeropage only, channel/brand coupling in `run()`), nightly (`PAIRS`, per-brand scout), trigger, research_agent (per-brand stamps), scout (`PINTEREST_BOARD_<BRAND>`, `scout_sources.txt` brand tags), imagesearch (per-brand subreddits), uncanny_judge, autopilot (`channel_targets`), rework, refgen, reference_needs (reads `anti_references_<brand>.txt`, none exist), assistant_brain, guide_tools, creative_guide | large |
| Accounts | `accounts.seed` makes slug `zeropage`; `RESERVED_SLUGS`; `invite --brand` is really the slug; `tests/conftest.py` still seeds an `antihero` account | small |
| Front ends | React: `shell.tsx` (brand = account slug; the switcher), `studio-api.ts` (`?brand=` on ~7 calls; `switchAccount` posts `/brand`), pipeline / queue / cut / elements / studio pages, assistant-pill, flow-workspace, director-arrival, concept-card, the Next proxy rule for `/brand`. Vanilla `/ui`: shared.js, app.js, analytics.js, queue.js, scenes.js, genspace.js, studio.js, pipeline.js; templates studio.html, _rail.html, accounts.html, dev_studio.html | ~14 React files, ~10 vanilla |
| Tests | 85 of ~135 files mention a brand (some only the DSN); `tests/test_brand.py` is entirely this feature; heaviest: test_orchestrator, test_scout, test_api, test_scout_api, test_tenancy, test_scenes_pick, test_mcp_server, test_shootgen, test_preprod | large |
| Ops | `run_morning_prompts.sh` and `ops/fly/run-nightly.sh` loop `for BRAND in antihero zeropage`; ops/bank.py, archive_ungrounded.py, render_queue.py, repair-missing-refs.py, billing_walkthrough.py, ingest-saved-images.py | ~10 scripts |

## Risks

- **Live data**: NOT NULL brand columns and the `channels` / `hold_queue` rows
  need a migration; other tenants' rows were labelled `antihero` by default.
- **The cookie/switcher coupling** (above).
- **External MCP clients**: `capture`, `add_spark`, `tonight`, `research` and
  `generate` take `brand`, some require it.
- **Env vars keyed by brand** (`PINTEREST_BOARD_<BRAND>`; check Fly secrets).
- **The uncanny judge** (kept by Mike's call) only runs for zeropage; with no
  brand it needs a new trigger or retirement, and `AUTO_POST_BRANDS` with it.

## Suggested order

1. Split account switching off the brand: an `account` cookie and route, with
   `/brand/{slug}` kept as an alias for a while. Update `auth`, `/api/me`, the
   React switcher, `accounts.html`, `app.js`, `_rail.html` and the proxy.
2. Make the server ignore `?brand=` and form `brand`; make MCP `brand`
   optional and ignored. Then stop the front ends sending it.
3. Strip `brand` from the pipeline (shootgen, scene_chain, orchestrator, scout,
   research, nightly, the shell loops, imagesearch). Decide `brand_gate` /
   uncanny judge and `AUTO_POST_BRANDS`.
4. Collapse `channels` to one and migrate `hold_queue.channel`.
5. Database last: stop writing, drop NOT NULL, then drop the columns and
   `idx_scout_brand_used`; redefine `generated_assets.project`.
6. Tests: delete `test_brand.py`, fix the conftest `antihero` account, update
   fixtures.
7. Clean up env vars, the research stamp files and the `scout_sources.txt`
   brand tags.
