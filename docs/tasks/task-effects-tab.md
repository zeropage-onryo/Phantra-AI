# Task: the Effects tab (`/studio/effects`, behind `effects_tab`)

**From:** group 3 of `docs/tasks/task-overnight-2026-10-22.md` (Mike, 2026-10-22: build the
effects first, give them their own Effects tab, no prices on cards, everything behind flags).
**Branch:** `claude/overnight-effects-tab`. **Flag:** `effects_tab` on `GET /api/capabilities`,
set by `PHANTRA_EFFECTS_TAB=1`, off by default.

## What it is

One table, two doors. The composer's `/effects` gallery (`components/studio/effect-gallery.tsx`)
and this page read the SAME listing, `GET /api/effects` (a projection of `src/effects.py`, never a
second table), and a click on either opens the SAME priced card, `components/studio/effect-step.tsx`.
What the page adds is a way in for someone who has a clip and wants a look, not a conversation:

1. **"Drop a clip" first.** A dropped file (a clip through `POST /api/cut/media` → `asset:<id>`, a
   still through `POST /api/refs/upload` → its ref) or a pick from the Library (`gen:<id>`)
   becomes the source for every card. A card already open and still waiting re-binds to it.
2. **A grid of before / after cards**, one per effect the table runs today (no "coming soon"
   tiles: the table only lists what `effects.run` will take). Each card plays its "after" on hover
   (a clip) or swaps to it (a still), and carries a **Free** or **Pro** badge. **No credit number
   anywhere on the page**: the price is on the card a click opens, as it is in the composer.
3. **Filters** read off the table's own fields: Free / Pro from `free`, and Cinematic / Social /
   Product from `tags`. An effect with no tags is never hidden by an audience filter.
4. **A click opens the priced card** (`EffectStep`) on this page's own turn. Its Approve is the one
   click that spends, through `POST /api/effects/run` at the price the card showed (`expect_credits`),
   exactly as the composer's `approveEffect` does. A card with no fitting source says what it needs
   and cannot be approved.
5. **Each result offers three doors**: **Make It Pro** (opens the `make_it_pro` bundle's own priced
   card on the result; hidden when the table has no such row), **Share** (the Library's share and
   download: `ShareControls` from `asset-viewer.tsx`, now exported, and `renderDownloadHref`) and
   **"Turn this into a full piece with Vesper"** (`/studio?attach=generated-<id>&spark=…`, the
   Library's own hand-off; see the gap below).

## Where things are

- `app/api.py`: `compute_capabilities` → `effects_tab`; `_effect_view` → `free`, `tags`;
  `EFFECT_TAGS` (the fallback tags for rows that predate the field, beside `EFFECT_BLURBS`).
- `web/src/app/studio/effects/page.tsx`: a SERVER page that asks the API for the flag per request,
  forwarding the person's cookies, and answers 404 (`notFound()`) with it off or with no session.
- `web/src/components/studio/effects-tab.tsx` + `effects-tab.css` (prefix `fxt-`, studio tokens
  only; no new colour was needed).
- `web/src/lib/effects-tab.ts`: the page's arithmetic (badge, filters, a dropped file's kind, the
  source's fit, the Vesper link). `web/src/lib/showcase.ts`: the manifest reader.
- `web/src/components/studio/shell.tsx`: the rail's "Effects" entry, drawn only while the
  capability is on (`NavItem.cap`); the shell reads `/api/capabilities` once per account.
- `web/public/showcase/manifest.json` + `placeholder/still.svg`: the showcase media, version 1.
- Tests: `web/tests/effects-tab.test.mjs`; `tests/test_api.py::test_effects_tab_is_off_unless_the_flag_says_one`;
  `tests/test_effects_studio.py::test_the_gallery_says_free_and_what_each_effect_is_for`.

## The showcase manifest (shared with the showcase slate, group 12)

`web/public/showcase/manifest.json`, version 1:

```json
{"version": 1, "items": {"<key>": {"kind": "clip"|"still", "before": "<url|null>", "after": "<url>",
  "poster": "<url|null>", "aspect": "16:9"|"9:16"|"4:5"|"1:1", "credits": 0, "model": "<name>", "gen_id": "gen:<id>|null"}}}
```

Keys (fixed; `showcase.showcaseKey`): `look.film_grade`, `look.noir`, `look.flash_2000s`,
`look.crash_zoom`, `look.vertical_ready`, `look.make_it_pro`, `effect.bullet_time` (the table's
`kling-effect`), `effect.product_orbit` (`camera-move`), `effect.4k_smooth` (`upscale`),
`effect.sound_pass` (`add-sound`), `effect.reframe` (`reframe`); any other effect id maps to
`effect.<id>`. The placeholder file has every key on `/showcase/placeholder/still.svg` with
`kind: "still"`: the slate replaces the URLs AND sets `kind: "clip"` where the example is a clip
(an SVG cannot play in a `<video>`). A missing key, a malformed entry (no `after`, an unknown
kind) or an unreadable file draws the placeholder. `credits` is the slate's own record, never drawn.

## Free looks (group 2, not on this branch)

The five looks (`film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`) and the
`make_it_pro` bundle are built generically: a table row that carries `free: True` and `tags` is
listed as `free` at 0 credits with its tags, and the page's Free filter, badge and Make It Pro door
need nothing more. `tests/effects-tab.test.mjs` exercises them with a stub table.

## As built (2026-10-22, overnight)

- Built as described above. `cd web && npm run typecheck && npm run build` pass;
  `node --test tests/effects-tab.test.mjs` (9 tests) passes; the two Python tests pass;
  `ruff check .` clean.
- **Verified by running it** on a throwaway Postgres schema (`fxtab` on the tests' server, one seeded
  account, a minted session cookie, a fake `FAL_KEY` so the server reports `ready`, R2 blanked), the
  API on 8003 with `PHANTRA_EFFECTS_TAB=1` and the studio on 3003 at `fxtab.localhost`:
  - the rail shows "Effects" and `/studio/effects` renders the grid (13 cards, all Pro since the
    free looks are not on this branch), the filters and the drop zone:
    `docs/qa/screens-2026-10-22/effects-tab.png` (the pane's capture, 800×561, saved as PNG);
  - a click opens the priced card with Approve disabled, "Needs an image to work on":
    `docs/qa/screens-2026-10-22/effects-tab-card.png`;
  - a synthetic PNG dropped on the zone (a `DragEvent` from the page's console) uploads through
    `/api/refs/upload`, loads as the source ("A still is loaded (dropped · fxtab-test.png)"), and
    the open card binds to it ("On dropped · fxtab-test.png"); with words typed, the card priced
    itself off `POST /api/effects/quote` at **10 credits** and Approve lit up:
    `docs/qa/screens-2026-10-22/effects-tab-card-priced.png`. The check stopped there;
  - with no session the route answers **404** (curl); with the flag off (API restarted without
    `PHANTRA_EFFECTS_TAB`) the API reports `effects_tab: false` and the route answers **404** with a
    session, while `/studio/projects` still answers 200 with the same session (curl).
  - The worktree's `web/node_modules` symlink pointed at the main checkout's install, which lacks
    `react-resizable-panels` (main's `package.json` has it); `npm ci` in the worktree replaced it.
    Not a change to the repo; worth knowing for every other overnight stream's typecheck.
  - **Run was never clicked.** Nothing rendered, nothing spent.
- Not done / gaps:
  - The ⌘K palette has no "Effects" row (it does not read capabilities); the rail entry and the
    address reach the page. A one-line add once the flag is permanent.
  - "Turn this into a full piece with Vesper" attaches the result through `?attach=generated-<id>`,
    which today carries a STILL's frame into the picks and nothing for a clip (`/api/assets` lists a
    generated video with no photos). The spark line names the render (`gen:<id>`) so the brain can
    reach it by id; a clip-aware attach is the Create page's to add (group 4 / BACKLOG).
  - Results live in page state for the visit (they are in the Library too); a reload forgets the
    list, and a run left mid-way is not resumed on this page (the composer resumes its own).
  - The server page 404s for a VISITOR (no session) as well as with the flag off, where other
    studio pages draw the shell with "Sign in". Chosen so a curl shows the posture plainly.
  - Nothing here is an edit to `src/effects.py`: the free looks' `free` / `tags` fields are read if
    present. If group 2 names its fields differently, `_effect_view` is the one place to adjust.
