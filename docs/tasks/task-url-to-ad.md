# Task: from a brand's URL to a finished short ad

Mike, 2026-10-21. Rewritten the same day against `origin/main`; the first draft was written
against a stale checkout and planned four things that already exist. Read "What already
exists" before touching anything.

**Why.** Mike gave Higgsfield: "Write a full 10-second motion ad script and shot-by-shot
storyboard for Gygler, including timing, voiceover copy, on-screen text, and which existing
Gygler brand images to use for each shot." It wrote a good storyboard -- five timed shots on
real `brand-image-N.png` files, voiceover, on-screen text, guard notes ("don't invent interface
details", "crop out the timeline date") -- then refused to make it: *"I can't render a timed
animatic with motion and audio in this Gygler campaign chat; it supports still ad creatives,
not video assembly."* Phantra can make the video. The line is **paste your URL, get a finished
ad** -- where Higgsfield sends its user somewhere else.

**What "right" means here is decided outside this repo** (step 5): the ad is put unlabelled
beside Higgsfield's storyboard and the real Gygler reference video, and judged by someone who
did not build it. Every earlier "Done when" proves the plumbing; only step 5 proves the ad.

## What already exists (do not rebuild)

| Need | Where it lives | State |
|---|---|---|
| Brand identity, look, voice, products, end card, caption font | `src/brand_kits.py`, `app/brand_routes.py`, `web/src/app/studio/brand/` (PR #397) | on main |
| Kit read off a website: Playwright render, colour scoring, fonts, logo, name, description, evidence per colour | `src/brand_import.py` + `evals/brand_import/` (10/16 primaries exact, 19/21 logos, 7/9 fonts) | on main (PR #423) |
| Brief -> beats -> placed cut: flat brand-colour plates, big faint word, headline, screenshot cards, labels, kit end card | `src/cut/motion_ad.py`, `src/cut/graphics.py`, `POST /api/cut/motion-ad`, `components/cut/motion-ad-dialog.tsx` | on main, reachable from the editor only |
| Voiceover read aloud, priced per character, kit's default voice | `src/voiceover.py` (ElevenLabs v3 via `talking_photo`), the editor's Audio tab | on main |
| Music bed sized to the cut in the kit's direction | `src/music.py` | on main |
| Brand font on captions + logo end card | `src/cut/brand.py` (licence attestation) | on main |
| A product page -> one element with its facts | `add_element` / `mcp_server._picture_from_page`, `linkrefs.parse_facts` | on main |

**Brand data lives in the KIT, never in a project's look or loose project elements.** The first
draft wrote the import into the project; that would be a second brand store the kit does not
know about. A project picks a kit (`projects.brand_kit_id`).

## Ground rules

- `git fetch`; branch off `origin/main`. Read `CLAUDE.md`, `docs/tasks/task-brand-kit.md`,
  `task-brand-kit-import-and-chat.md`, `task-motion-ad.md`, `task-music-layer.md` first.
- One PR per numbered step; **stop after each and report** before the next. Mike merges.
- Design-first: a NEW card or page goes on a design canvas for Mike's pick before code (the kit
  page's redesign is its own canvas, "Brand Kit Redesign"; this task does not redesign it).
- No live spend while building; stub every model call in the server process. Any real render,
  voice or still is Mike's call, priced and approved like any other.
- Model output is advised, never trusted: named lists in code, every fix a visible warning.
- Checks: `venv/bin/python -m pytest tests/ -q`, `venv/bin/ruff check .`; in `web/`:
  `npm run typecheck`, `npx eslint src`, `node --test tests/<file>.test.mjs`.

## Decisions (Mike said "let's go" on the recommendations, 2026-10-21)

- **D1. The import branch.** Already merged as PR #423 before step 1 started. Closed.
- **D2. Site images.** Home page + up to 5 same-host nav pages, at most 12 pictures kept.
  As built, a product or a screen of the app becomes a PRODUCT element linked on the kit, and
  everything else kept (people, places, textures) becomes a kit LOOK REFERENCE -- not a
  character or a location. Changed from the recommendation on purpose: the people on a
  brand's site are models, not its recurring cast, and the kit has no places list. Mike can
  move one by hand on the kit page.
- **D3. robots.txt.** Honoured for the nav pages; a skipped page is said. The home page is
  the one the person asked for and is always read.
- **D4. Rights.** "Use pictures you have the right to use." under the import field.
- **D5. Where the ad is asked for.** The composer (a skill + a write tool), the same body the
  editor's dialog uses -- not a second engine.

## Steps

### 1. Finish the import: pictures as well as identity -- BUILT (see "As built")

- `brand_import` gains the pictures (D2): `og:image`, JSON-LD, `<img>` and CSS backgrounds as
  drawn; drop logos, SVGs, chrome-looking names, icons and small pictures in the header / nav /
  footer; one file under two schemes is one picture; under 400 px long side dropped. Products
  become elements through `api.create_element(strict=True)` and are linked on the kit.
- Every refusal said plainly: robots-disallowed pages, pictures that would not open, pictures
  too small, running out of time.
- **Done when:** fixtures with no network yield the expected pictures, the filing makes one
  element per product with the model and the create stubbed, and the by-hand eval is re-run
  and reported with a new "pictures kept / pictures a person would keep" column scored by hand
  on 6 sites (gygler.com, one Shopify store, one with no og:image among them). **The eval run is
  still open** -- it reads the live web and spends one sorting call per site, so it waits for
  Mike's OK.

### 2. Motion ad: real pictures, named moves, a voiceover per beat

`motion_ad` already places beats; extend it, do not fork it.
- A beat may sit on an element PHOTO (a screenshot card today); `move` is a closed list in code
  (`hold`, `push_in`, `pull_out`, `pan_left`, `pan_right`, `rise`, `drift`, `scale_in`), each a
  fixed key set checked against `lanes.py`'s numbers; anything else is a warning and `hold`.
- Each beat carries an optional `voiceover` line; the script is the lines joined. `clean`
  refuses numbers and claims not in the kit's facts or allowed claims (it already flags
  `unsourced_numbers`), never invents interface details, and warns on dates/stale text.
- **Done when:** a stubbed Gygler-shaped plan (five beats on element photos, a logo end card)
  becomes a cut whose v1 validates, renders with real ffmpeg in the test, and lasts exactly
  `seconds`; each move's keys match `lanes.py`.

### 3. The ad from the chat

- `prompts/skills/ad.md` on the skill shelf: a 6-30 s ad as timed beats on the project kit's
  pictures, short on-screen text (six words or fewer), voiceover by beat, end card on the logo,
  and the guard notes in our words.
- A composer write tool `make_ad {brief, seconds, aspect}`, a proposal: the card shows the beats
  as a strip (picture, time, text, move, voiceover line), every field editable like a plan
  step, and **Build the ad** calls the SAME body as `POST /api/cut/motion-ad` (free, so Auto may
  run it). `check_args` refuses any picture that is not the account's element or result.
- A chat with only a URL and no kit offers the import first (step 1's job) as a plan step.
- **Done when:** with the model stubbed, a turn in a project on the Gygler kit ends on the card
  and Build makes a cut project that opens in the editor. NEW card look -> canvas first.

### 4. Voice and music on the ad (wire, don't build)

- On the ad card: **Read it** (the voiceover, priced by `src/voiceover.py`, approved like a
  still) and the music bed from `src/music.py`, both landing on the cut's own tracks with music
  ducked under voice. No new model, no new price table.
- **Done when:** a stubbed read lands on the voice track, a failed read releases its hold and
  says so through `failures.plain`.

### 5. The outside check (the only proof the ad is good)

Mike approves the spend; nothing here runs on its own.
- Make the Gygler ad end to end from `https://gygler.com`: import -> kit -> ad -> voice -> export,
  at 9:16 and 16:9.
- Lay out, unlabelled, on one page: our export, Higgsfield's storyboard for the same prompt (its
  screenshots, as Mike has them), and frames from the real Gygler reference
  (`~/Downloads/IMG_3912.MOV`).
- Record, from someone who did not build it (the Gygler client, or two people outside the
  project): which is on-brand, which they would post, and what they would change.
- Report the numbers too: time from pasting the URL to the first export; edits needed before it
  was postable; credits spent; every warning the pipeline raised.
- **Done when:** that page and those answers exist. If ours loses, the report says why, and the
  fix is the next task -- not a tweak made quietly inside this one.

## Not in this task

- Redesigning the kit page (separate canvas and handoff).
- Logo animation beyond `scale_in`; footage beats under the graphics; reading sites behind
  sign-in or built entirely in script; posting the ad anywhere; Higgsfield-style single still
  ad creatives.

## As built

### Step 1 (2026-10-21)

- **The visit collects pictures** (`src/brand_import.py`). `PICTURES_JS` runs after the probe
  (which marks the logo) and lists every `<img>` and CSS background the page drew -- drawn size,
  file size, alt, whether it sits in a header / nav / footer, whether it is the logo -- and the
  same-host links in the navigation. `rank_pictures` (pure) puts the page's own og:image /
  JSON-LD pictures first (read off the rendered HTML with `linkrefs.parse_images`), then what was
  drawn biggest; a header / nav / footer picture is kept only when drawn at least 400x300 and
  ranks lower. `_gather_pictures` then reads up to `NAV_PAGES` (5) nav pages as HTML only (never
  run) for their preview pictures, skipping any robots.txt disallows for `Phantra-brand-import`,
  and fetches at most `PICTURE_CANDIDATES` (30) addresses through the visit's own guarded door
  (`_guarded_get`: public hosts only, every hop checked), at most 8 MB each and 40 MB together,
  none started after 80 s of the visit (the child is killed at 120).
- **`keep_pictures`** (parent, pure): upright JPEG through `refbin.to_jpeg`, at least 400 px on the
  long side, one per content hash, at most 12. What was left out is said in the notes.
- **`sort_pictures`**: ONE vision call on the fast brain (`prompts/brand_import_pictures.txt`,
  512 px thumbnails, JSON schema, metered as stage `brand_import`). Code checks the answer: an
  unknown kind is "other", an out-of-range or repeated number is ignored, names lose any address
  and are cut at 60 characters, a picture the model skipped stays a look reference. No key or a
  failed call: every picture is a look reference, with a note. The `_sort_model` seam is what
  tests replace.
- **`brand_routes.file_pictures`**: asks the Create gate (`charge.create_refusal_code`) because
  sorting and describing are model text. Refused: every picture becomes a look reference and the
  note quotes the refusal, no model and no element. Allowed: a product becomes an element through
  the Elements page's own create (`api.create_element`, `strict=True`, category `product`, notes
  "From the website: <page>"), names made unique against the account's props so a second
  picture never lands as a second photo on the first, and linked on the kit's products (up to
  `PRODUCTS_MAX`); a refused create falls back to a look reference with the reason; look
  references stop at the kit's eight. The job answers `products`, `references`, `dropped`.
- **The kit page** says pictures come too, says the rights line, and after an import lists
  "From its pictures: N products added to Elements, M look references." before the notes.
- Tests: `tests/test_brand_import_pictures.py` -- ranking, keeping, sorting (stubbed), filing
  (stubbed model and create, real kit tables), the gate's refusal, and one real visit to a
  two-page local site (og:image first, logo / badge / robots-disallowed page left out, a picture
  drawn big from a small file dropped). The existing import tests are unchanged and pass.
- **Not done in step 1:** the by-hand eval on real sites (needs the live web and Mike's OK, one
  sorting call per site); nothing reads a picture behind sign-in or one only a script loads
  after scrolling past 5000 px.

## Progress

- Step 1: built (PR pending Mike's review); its live eval waits on his OK.
- Steps 2-5: not started.
