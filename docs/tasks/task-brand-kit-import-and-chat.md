# Task — Put the Gygler brand kit in Phantra, then add import-from-URL, the composer kit chip and kit edits through Vesper

**From:** a Claude session on 2026-10-21 (the Gygler client job, a website brand-kit extractor built and scored there, and a 3-screen mockup).
**For:** Claude Code, in `phantra-ai` on Mike's Mac.

**Mike's calls already made:**
- Build a brand kit section like Canva, Runway and Higgsfield. Brand kits are BUILT and live since PR #397 (`docs/tasks/task-brand-kit.md`). This task extends them; it does not rebuild them.
- Take three things from the comparison:
  1. Runway-style references: the kit already has look references plus product and character links.
  2. Higgsfield-style copy fields: description, selling points, aesthetics, made from a URL.
  3. The kit switched on where you write: a chip in the composer, and Vesper can edit the kit by chat.
- Approved the mockup look. Studio accent is the Phantra yellow (black text on yellow fills); red is only for errors and destructive actions (`studio.css :root`).
- No renders, stills or generation unless he says so in chat.

**Read first:**
1. `docs/tasks/task-brand-kit.md`, all of it, including "As built".
2. `docs/BACKLOG.md` #28.
3. `src/brand_kits.py`, then `app/brand_routes.py`.

## State right now

- **Brand kits are on main and deployed.** Merge commit `026d3b2` (PR #397, 2026-10-20). `GET https://api.phantra.ai/api/brand-kits` answers 401 "sign in first", and `https://phantra.ai/studio/brand` serves 200.
- **What exists:**
  - many kits per account; a project picks one (`PUT /api/projects/{id}/brand-kit`)
  - identity (tagline, positioning, audience, url)
  - palette by role
  - fonts with a licence box
  - captions, safe zone, aspect, motion, end card
  - look (style plus banned list)
  - voice (tone, use, avoid, CTA), sound (stored only)
  - product and character links with claims
  - up to 8 look-reference JPEGs
  - the free `GET /api/scenes/{id}/prompt-preview`
- **The editor's graphics track** (motion graphics in a kit's look) is also built (`docs/tasks/task-motion-graphics.md`). That is the layer the Gygler explainer videos need.
- **Not built (BACKLOG #28 and this request):**
  - import a kit from a website
  - one-off composer stills get no kit (`/api/generate/run` takes no project)
  - no composer kit chip
  - no brain tool that proposes kit edits
  - no selling-points field
  - no colour evidence or confidence
  - no contrast warning on the kit page
- **Unknown from here:** whether Mike's live account already has a "Gygler" kit. The 2026-10-20 walk ran on a throwaway schema.
- **Prepared and waiting** (from the chat, sent to Mike as `gygler-kit.zip`, to be placed at `data/_scratch_brand-kit-gygler/`, ignored by the `data/_scratch_*` rule; NOT `data/brandkits/`, which is the app's own kit storage):
  - `gygler-kit.json`: name plus spec. It passed `brand_kits.clean_spec` on main `a7d8071`.
  - `logo_light.png` and `logo_dark.png`: 2048×701, transparent.
  - `logo_light_source.svg` and `logo_dark_source.svg`.
  - `font_heading_Urbanist-Bold.ttf` and `font_body_Urbanist-Medium.ttf`: Google Fonts, SIL OFL, so the licence box is truthful.
  - `reference_1..5.jpg`: frames from the client's two reference videos.

  Every file passed `brand_kits.sniff` and the role rules. The audience line is marked `[CONFIRM WITH CLIENT]`.
- **The extractor to port** is in `gygler-kit.zip`'s sibling `brandkit.zip` (`extractor/`, `apply/compile_prompt.py`, `schema/`, `golden/golden_set.json`, `scoring/score.py`, `REPORT.md`).
  - Its measured result is 12 of 18 official primaries exact (ΔE ≤ 2), logos 19 of 20, fonts 7 of 9.
  - When it says "high confidence" it is right 10 of 12 times.
  - It runs headless Chromium through Playwright.

## Rules for this task

- Branch from main for code (`claude/brand-kit-import-chat`); never commit to `main`. Mike merges.
- The no-kit goldens (`tests/test_brand_kit_no_kit.py`, `tests/goldens/no_brand_kit.json`) stay byte-identical. Never re-capture them with `PHANTRA_UPDATE_GOLDENS=1` to make a test pass.
- Nothing spends without a priced approval. This task adds no spending door.
- A scene write is a Gemini call. Ask Mike first.
- Live data: report first, then write only on Mike's word (CLAUDE.md "Live data"). Never print a secret; names only.
- **The connector is in directory review.** Do not touch `src/mcp_server.py`, `app/mcp_mount.py`, `app/mcp_auth.py` or the plugin repos. MCP kit tools are a later task; ask Mike after review.
- A brand lives inside a project, never studio-wide (task-remove-brand-labels). The chip shows and toggles the current project's kit. It never picks a kit for the whole studio.
- Socials were cut on purpose in the approved spec (§3 "cut"). Do not add them unless Mike says so.
- Tests block network (`tests/conftest.py`). The extractor's tests run Playwright on local fixtures via `page.set_content` or `file://`, never the web.
- Verify by running: the studio at localhost:3000, the free prompt-preview, the test suite.

## Steps

### 0. Get set up
- [ ] Pull main and branch.
  - `git checkout main && git pull && git checkout -b claude/brand-kit-import-chat`
  - Done when: `git log -1 --format=%h` is at or after `a7d8071`, and `src/brand_kits.py` exists.
- [ ] Put Mike's `gygler-kit.zip` contents in `data/_scratch_brand-kit-gygler/`.
  - Done when: `ls data/_scratch_brand-kit-gygler` lists the 12 files above, and `git status` does not show them (gitignored).
- [ ] **MIKE:** open https://phantra.ai/studio/brand and say whether a kit named "Gygler" already exists.
  - If one does, step 1 updates it instead of creating a second.

### 1. Load the Gygler kit into Mike's live account (an importer anyone can reuse)
- [ ] Write `ops/import_brand_kit.py <folder> --account <slug> [--write]`.
  - It reads `<folder>/*.json` (`{name, spec}`) and the files named by role (`logo_light.png`, `logo_dark.png`, `logo_*_source.svg`, `font_heading_*.ttf|otf`, `font_body_*.ttf|otf`, `reference_*.jpg`).
  - It calls `brand_kits.clean_name` / `clean_spec` / `sniff` and prints what it would create. It writes nothing without `--write`.
  - With `--write`, it uses `brand_kits.create` and then `add_asset` (fonts with `licensed=True` only when the folder holds a `FONT_LICENCE.txt` naming the licence).
  - It follows the `ops/` shape (re-runnable, report first) and must not load `.env` itself (the `src.accounts` habit).
  - Done when: `venv/bin/python -m ops.import_brand_kit data/_scratch_brand-kit-gygler --account phantra` prints 1 kit, 5 palette roles and 11 files with no refusal, against the local test DB.
- [ ] Add `data/_scratch_brand-kit-gygler/FONT_LICENCE.txt`: "Urbanist, SIL Open Font License 1.1, https://fonts.google.com/specimen/Urbanist".
- [ ] Test `tests/test_import_brand_kit.py`.
  - A dry run writes no row; `--write` creates the kit, its assets and the font `licensed` meta.
  - A font with no licence file is refused.
  - Another account's kit is never touched.
  - Done when: `venv/bin/python -m pytest tests/test_import_brand_kit.py -q` passes.
- [ ] **MIKE (ask first; live write):** report run, then `--write`.
  - `set -a && source .env && set +a && venv/bin/python -m ops.import_brand_kit data/_scratch_brand-kit-gygler --account phantra`, then the same with `--write` on his word.
  - Done when: https://phantra.ai/studio/brand shows "Gygler" with the orange swatch and logo, and its page draws the end card (cream, orange wordmark, "Get a Gyg, stay for good.", gygler.com).
- [ ] **MIKE:** confirm the audience line with the client. Edit it on the kit page and remove `[CONFIRM WITH CLIENT]`.
  - Done when: the kit page shows no `[CONFIRM` text.

### 2. Use the kit on a Gygler project (free checks only)
- [ ] **MIKE:** in Create, ask the brain to make a project "Gygler explainer" (projects are made only through the brain), then pick the Gygler kit in the project's panel.
  - Done when: `GET /api/projects/{id}/brand-kit` returns the Gygler kit id.
- [ ] Once a scene exists in that project (writing one is a Gemini call, Mike's word), open `GET /api/scenes/{id}/prompt-preview`.
  - Done when: the clip prompt ends with the Gygler look and Avoid lines; the keyframe shows up to 3 kit references after the scene's own; the writer block names Gygler's tone and words.

### 3. Import a kit from a website (BACKLOG #28)
- [ ] **MIKE decides:** how the extractor gets a browser.
  - **A (recommended):** Playwright plus Chromium in the Fly image, run as a job (`app/jobs.py`). Check the image-size increase on a test build and report it before deploying.
  - **B:** no browser. Static HTML/CSS through `refbin.public_bytes`. It loses measured screen area and rendered colours, and it is unscored.
  - Done when: Mike picks one in chat.
- [ ] Port the extractor into `src/brand_import.py` plus `src/brand_import_probe.js`.
  - Carry over: `colors.py`, `fonts.py` and `google_fonts.json` into `src/` or `data/`, the CDP screenshot, consent and overlay handling, logo pixel colours, the CSS-var visibility gate, and the WCAG on-primary rule.
  - Output is a `clean_spec`-valid spec plus files by role, never a fetchable URL on a row.
  - Done when: `brand_import.extract(html_fixture)` returns a spec that `brand_kits.clean_spec` accepts.
- [ ] **Safety.**
  - Navigation and every subresource go only to public hosts: intercept requests in Playwright and refuse private, loopback and link-local addresses, the same rules as `refbin.public_bytes`.
  - Cap page time (60 s) and bytes.
  - Never download the site's font files. A font found on Google Fonts is fetched from Google (OFL); any other font is named in the spec only, with the fallback noted.
  - Done when: a test where the page requests `http://169.254.169.254/` and `http://127.0.0.1/` shows both requests aborted.
- [ ] **Evidence and the new copy fields.**
  - Add `import` to `clean_spec`: `{source, at, roles: {primary|accent|...: {why, confidence}}}`, with fixed limits; dropped when absent.
  - Add `identity.selling_points` (list, ≤ 8 × 120 chars) and `look.aesthetics` (list of `{tag, because}`, ≤ 8).
  - `projects.brief_block` adds selling points to the BRAND block.
  - Done when: the no-kit goldens are unchanged, and a kit test shows selling points in the writer block.
- [ ] Route `POST /api/brand-kits/import {url}`.
  - It starts a job and returns its id; the result is a NEW kit named from the site, never an overwrite.
  - It declares `auth.current_account_id`. It is free, so no ledger hold, but rate-limit it per account (e.g. 10 per hour).
  - Done when: `tests/test_tenancy.py` passes, and a route test with `brand_import.extract` patched creates a kit for the caller only.
- [ ] Eval kept out of CI.
  - Move `golden/golden_set.json` and `scoring/score.py` to `evals/brand_import/`, with a README saying how to run it by hand (it hits the web).
  - Done when: a by-hand run on this Mac reports primary exact ≥ 12 of 18 and logo ≥ 19 of 20, in the README with the date.
- [ ] Studio: "New kit from a website" on `/studio/brand` (URL field, then the job's steps, then a link to the new kit).
  - Done when: in the local studio, entering `https://gygler.com` produces a kit whose primary is #FF880B and whose logo is the Gygler wordmark.

### 4. The kit page: evidence, contrast and copy fields
- [ ] Show `import.roles` on the palette: a confidence chip per colour, the reason on click, and a "Which is your brand colour?" pick of the top 3 when the primary is not high-confidence.
  - Done when: an imported kit shows the chips, and a hand-made kit shows none.
- [ ] Contrast warning: for text on primary and text on background, show the WCAG ratio. Below 4.5:1, show the warning and a one-click accessible alternative. Computed in the browser, nothing stored.
  - Done when: Gygler's page shows white on #FF880B at 2.39:1, flagged, with black at 8.78:1 offered.
- [ ] Selling points and aesthetics fields in the Identity and Look sections, editable, with validation in `web/src/lib/` and `node --test` cases.
  - Done when: `cd web && node --test tests/*.test.mjs && npm run typecheck` passes.

### 5. The kit chip in the composer
- [ ] When the Create thread belongs to a project with a kit, show a "Kit: <name>" chip in the settings line (studio.css tokens; yellow only for the selected state, per the palette). Clicking it turns the kit off for the next send only. With no project or no kit, there is no chip.
  - Done when: in the local studio, the chip appears in the Gygler project's thread and nowhere else.
- [ ] Close BACKLOG #28 "one-off composer stills": the composer passes the thread's `project_id` (and the chip's off flag) to `/api/generate/run`, which hands them to `fal.generate_image_from_prompt` / `nano_banana.generate_from_prompt` (already kit-aware when given a project).
  - Done when: a test with providers patched shows the still request carrying the Gygler look line with the chip on and not with it off, and the no-kit goldens are unchanged.

### 6. Vesper proposes kit edits
- [ ] Add a brain write tool `propose_kit_change` (`src/guide_tools.py`; prompt rule in `prompts/`).
  - Arguments: kit id from a closed list (the thread's project kit) and a field-level diff checked by `brand_kits.clean_spec`.
  - Like every write, the turn ends on it as a proposal.
  - Done when: a guide-tools test shows a valid diff becomes a proposal and an invalid one is refused with the field named.
- [ ] Proposal card in the thread (`assistant-thread.tsx`) showing before and after (swatches for colours), Apply (`PATCH /api/brand-kits/{id}`) and Discard. Nothing changes without Apply.
  - Done when: in the local studio, asking "use #FCF4EB for the background" in the Gygler thread shows the card, and Apply updates the kit page.

### 7. Finish
- [ ] Run the checks as CI does: `venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`, `cd web && node --test tests/*.test.mjs && npm run typecheck && npm run build`.
  - Done when: all pass and the goldens are untouched (`git diff --stat tests/goldens` is empty).
- [ ] Update docs: an "As built" section at the end of this file, BACKLOG #28 (strike "import from a website" and "one-off composer stills"), and one line in CLAUDE.md's Projects or Create section about the chip.
  - Done when: `grep -n "Import a kit from a website" docs/BACKLOG.md` shows it marked BUILT.
- [ ] Open a PR from `claude/brand-kit-import-chat`. **MIKE** merges. Deploy follows his usual path (`docs/DEPLOY_FLY.md`). If he chose option A in step 3, Chromium in the image is part of that deploy.
  - Done when: the PR is open with CI green.

## Done means
- Mike's live account has a Gygler kit with logo, palette, Urbanist, end card and 5 look references, attached to a Gygler project, and the free prompt-preview shows it applied.
- `https://phantra.ai/studio/brand` can make a kit from a website URL. The by-hand eval (≥ 12 of 18 primaries exact) is recorded.
- The kit page shows colour evidence and contrast warnings. The composer shows the project's kit chip, and composer stills honour it. Vesper can propose kit edits that apply only on a click.
- No render, still or scene write happened without Mike's word. The no-kit goldens and the MCP files are unchanged.

## As built (2026-10-21)

Branch `claude/brand-kit-import-chat` off main `1c9eb629`. Steps 0, 1, 3, 4, 5 and 6 are
built; step 2 waits on Mike.

**Step 0.** The 12 files plus `FONT_LICENCE.txt` are in `data/_scratch_brand-kit-gygler/`
(gitignored). The live account had no "Gygler" kit (the importer's report said CREATE).

**Step 1.** `ops/import_brand_kit.py` (report first, `--write` to act, no `.env` load).
- Every upload check runs before anything is written: `brand_kits.check_asset` was split out
  of `add_asset` for that, and `brand_kits.stored_name` names a file the way `_store` does.
- A kit of the same name on the account is UPDATED and files it already holds are skipped, so a
  second run changes nothing. A font needs `FONT_LICENCE.txt`; its line is stored on the font
  row as `meta.licence` beside `licensed`.
- The database line prints host, database and schema only, never the user or password.
- After `--write` it checks every file's key is in the bucket.
- **Run live on Mike's word (2026-10-21), after confirming mikemassaad@gmail.com owns `phantra`
  ("Phantra AI", its only membership):** kit 1 "Gygler", 5 palette roles, 11 files, "bucket:
  every file is there". The audience line still holds `[CONFIRM WITH CLIENT]` (Mike's item).
- Drawn locally from the same files, the end card is cream with the orange wordmark, "Get a Gyg,
  stay for good." and gygler.com, in Urbanist.
- `tests/test_import_brand_kit.py`, 9 tests.

**Step 3, the spec fields.** `clean_spec` takes `identity.selling_points` (8 × 120),
`look.aesthetics` (`{tag, because}`, 8) and an optional `import` block (`{source, at, roles:
{role: {why, confidence}}, candidates}`), dropped when absent. Selling points join the writer's
BRAND block; aesthetic tags ride on the look line ("Aesthetic: ..."). No-kit goldens unchanged.

**Step 3, the import.** Mike picked option A (Playwright and Chromium in the Fly image, run as a
job). **`brandkit.zip` was never in hand** (not in ~/Downloads, Desktop or Documents), and on
"go ahead" the extractor was written fresh from this file's description. So the chat's scores
(12/18 primaries, 19/20 logos, 7/9 fonts) belong to the chat's extractor, not this one.
- `src/brand_import.py` and `src/brand_import_probe.js`:
  - The page is rendered at 1366×900 (2x) and every visible element's background, fill, border
    and text colour is weighed by its screen area in the first two screens.
  - Colours are clustered in Lab (ΔE < 8) and weighted by where they sit: a button counts 6x, a
    link or heading about 2x.
  - The primary is boosted when it is painted on the CDP screenshot, when it is a CSS custom
    property a rule actually uses (the visibility gate: a declared, unused `--var` counts for
    nothing), when it is the theme colour, and when it is in the logo's own pixels.
  - The confidence chip says high, medium or low with the reasons.
  - The WCAG on-primary rule adds black or white as an `extra` swatch.
  - Consent buttons are clicked and large fixed overlays are hidden before measuring.
- **Fonts:** the families that set the most heading and body text. A family Google Fonts serves
  is fetched from Google as TTF (stored with a Google Fonts licence line); any other is named
  only, with a note.
- **The logo:** the header image or SVG, captured alone (its ancestors made transparent), filed
  by how light it reads. A single-colour mark also gets the other variant recoloured: a white
  mark in the primary, a dark one in white.
- **Safety:** one route handler for every request.
  - It refuses non-http(s) addresses, credentials, font files, media and websockets, and any
    host `refbin.public_host` rejects.
  - It follows redirects ITSELF, at most 5 hops, checking every hop. A test showed that a 3xx
    handed back to the browser is followed without coming back through the handler.
  - The visit is capped at 60 s and 25 MB (10 MB per response), and service workers are blocked.
- **The route:** `POST /api/brand-kits/import {url}` checks the address, refuses an account's
  11th import in an hour (429; counted per process, at the start) and runs a `brand-import` job.
  The job always makes a NEW kit named after the site and returns `kit_id`, `notes` and how many
  requests were blocked. The activity tray and Renders link a finished one to the kit.
- **The studio:** "New kit from a website" on `/studio/brand` (an address, the job's steps, then
  a link and the notes).
- **The image:** the Dockerfile installs the headless shell with its system libraries (`playwright
  install --with-deps --only-shell chromium`). Fly build-only runs, nothing deployed: main
  `1c9eb629` 458 MB, this branch 655 MB (**+197 MB**). CI installs the same shell, and there the
  browser tests fail rather than skip when it is missing.
- **The eval:** `evals/brand_import/` (README, `score.py`, `golden_set.json`), by hand only.
  2026-10-21: gygler.com, primary exact 1/1 (#FF880B, "high"), logo 1/1, fonts 1/1 (Urbanist).
  The chat's 18-site golden set goes there when it is in hand.
- `tests/test_brand_import.py`, 11 tests: the fixture's spec, 169.254.169.254 / 127.0.0.1 /
  10.x aborted, a redirect hop to the metadata address refused, the site's font file never
  requested, role picking, Google-only font fetch, the logo variants, and the route (a new kit,
  the caller only, 400 on a bad address, 429 on the 11th).
- **In the local studio:** entering https://gygler.com made a new "Gygler" kit, with primary
  #FF880B (high), the orange wordmark for light backgrounds and the white one for dark,
  Urbanist for both fonts, and the end card drawn from them.
- The first walk caught the logo captured on the header's orange (an RGB block); fixed by
  capturing it alone.

**Step 4.** The kit page:
- a confidence chip per imported colour, with its reason on click;
- "Which is your brand colour?" (the primary and up to two candidates) when the primary is not
  high-confidence;
- WCAG ratios for the text colour on background and on primary, and each extra colour on
  primary, with a one-click black or white fix. Computed in the browser, nothing stored.

Selling points (one per line) and aesthetics (`tag: why`) are editable. Helpers and their
`node --test` cases are in `lib/brand-kit.ts`.

**Step 5.**
- `/api/generate/run` takes `project_id` (404 when it is not the caller's) and `brand_kit=off`.
  `nano_banana.generate_from_prompt` gained `project_id` and `brand_kit`, and
  `fal.generate_image_from_prompt` gained `brand_kit`.
- A Nano still gets the look line in words, like fal stills; no kit images are added.
- The composer shows the chip only in a kitted project's thread. In Video mode it is shown but
  disabled, because a scene's renders always read the project's kit.
- The floating assistant's stills inside a workspace pass the project too.
- The chip first pushed the send button to a second row at 1440px in Image mode. It now fits:
  no separator before it, tighter padding, the name capped at 96px.

**Step 6.**
- `propose_kit_change` is in `src/guide_tools.py`; the field list, apply and diff are in
  `src/kit_changes.py`; the rule is in `prompts/creative_guide_kit.txt`.
- The model gets the kit's id and current values in the tool's description, and changes
  `{field, value}` over 17 fields. Files, products, characters, captions and the end card stay on
  the kit page.
- A refused value goes back to the model naming the field, so it can try again within the same
  turn.
- **Differs from the plan:** Apply posts `/creative-guide/act` (like the look tool), not a
  client-side PATCH. The server re-checks against the kit as it is then and returns the replaced
  spec; Undo is the PATCH.
- The card (`components/studio/kit-change-card.tsx`) is drawn in the composer thread. The
  floating assistant shows the same rows in its own card.
- `tests/test_kit_changes.py`, 13 tests.

**Checked in the local studio** (throwaway schema `bk_import_walk`, provider keys blank, the
brain's model call replaced by a canned `propose_kit_change`, so nothing could spend):
- the Gygler page flags white on #FF880B at 2.39:1 and offers black at 8.78:1;
- an imported copy shows the chips and the pick, and the hand-made kit shows neither;
- "Kit: Gygler" appears in the Gygler project's thread and not in a project without a kit;
- "use #FCF4EB for the background" drew the card, Apply changed the kit to #FCF4EB, and Undo
  put #FAF0E4 back.
