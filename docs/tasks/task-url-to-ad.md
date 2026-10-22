# Task: from a brand's URL to a finished short ad

Mike, 2026-10-21. Rewritten the same day against `origin/main` (b5aee007+) and the unmerged
branch `claude/brand-kit-import-chat`. The first draft (kept at
`Claude outputs/task-url-to-ad.v1-before-rebase.md`) was written against a stale checkout and
planned four things that already exist; see "What already exists" before touching anything.

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
| Kit read off a website: Playwright render, colour scoring, fonts, logo, name, description, evidence per colour | `src/brand_import.py` + `evals/brand_import/` (10/16 primaries exact, 19/21 logos, 7/9 fonts) | **branch only**: `claude/brand-kit-import-chat` (52b021eb, 2ab96563, 6124c614) |
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
  `npx tsc --noEmit`, `npx eslint src`, `node --test tests/<file>.test.mjs`.

## Decisions for Mike before starting

- **D1. Land the import branch as is, or after step 1's fixes?** Recommended: merge it first
  (its own PR is already the work), then step 1 adds images on top.
- **D2. Site images.** The import reads identity, not pictures. Step 1 adds them: home page +
  up to 5 same-host nav pages, at most 12 images, each filed as an element ON THE KIT
  (products/characters lists), classified off its vision description (person -> character,
  product or interface screenshot -> product/prop, place -> location). Recommended: yes, with
  Mike re-filing on the kit page.
- **D3. robots.txt.** Recommended: honour it; a skipped page is said.
- **D4. Rights.** One line on the confirm card: "use pictures you have the right to use".
- **D5. Where the ad is asked for.** Recommended: the composer (a skill + a write tool), the
  same body the editor's dialog uses -- not a second engine.

## Steps

### 1. Finish the import: pictures as well as identity

- Merge or rebase `claude/brand-kit-import-chat` (D1); its evals and tests must still pass.
- `brand_import` gains the pictures (D2): `og:image`, JSON-LD, `<img>` with a size hint (the
  Ghost lesson); drop chrome/logos/placeholders (`linkrefs._looks_like_chrome`), one file under
  two schemes is one image, under 400 px long side dropped. Kept images become elements through
  `api.create_element(strict=True)` and are linked on the kit's products / characters.
- Every refusal said plainly: a page that gave nothing, robots-disallowed, a picture that would
  not decode, content behind sign-in or script.
- **Done when:** saved HTML fixtures (no network) yield the expected pictures and kinds, the job
  makes one element per kept image with fetch/describe/save stubbed, and the by-hand eval is
  re-run on its golden set and reported (primaries, logos, fonts, plus a new "pictures kept /
  pictures a person would keep" column scored by hand on 6 sites including gygler.com, one
  Shopify store and one site with no og:image).

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

## Progress

Nothing built yet in this task. Existing pieces are listed above.
