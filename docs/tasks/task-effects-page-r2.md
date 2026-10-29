# Task: the Effects page as "R2·04" (`/studio/effects`, behind `effects_tab`)

**From:** Mike, 2026-10-26. He compared the page with Higgsfield's `/effects`, saw twenty mockups
(the "Phantra Effects — 10 directions" design canvas, two rounds), picked **R2·04**: an upload
panel on the left, and on the right a three-tile featured strip over pill tabs and a dense wall
of examples that play on their own. Buttons rounded ("can you make buttons rounded").
**Branch:** `claude/effects-page-r2-04`. Builds on `docs/tasks/task-effects-tab.md` (the first
version of this page); the flag, the server page and the routes are unchanged.

## What changed

1. **The broken tiles.** `lib/showcase.ts` `restingFrame` put an entry's `before` into an
   `<img>`, and every free look's `before` is an `.mp4`: production drew the six looks as broken
   images. It now returns a PICTURE (`isPicture`) or null, and a clip tile plays its `after`
   with the poster as its resting frame.
2. **One tile per template** (`lib/effects-wall.ts`). Kling's 98 templates, PixVerse's 154 and
   the camera moves were three cards with a dropdown each. The page now splits every templated
   row into a tile per value, read off the option values `GET /api/effects` already lists
   (`PRESET_OPTION`: `kling-effect` -> `effect_scene`, `pixverse-effect` -> `effect`,
   `camera-move` -> `camera_movement`). **No API change**: a tile is "this row, with this option
   chosen", and a run sends exactly what the card used to (`effect` + that option). Template
   names are title-cased (`bullet_time_360` -> "Bullet Time 360"); plain rows get a name for
   what they do (`ROW_NAMES`, "Add Sound", "Reframe"), the model's name staying the table's
   label, shown small in the panel.
3. **What is on the wall.** A tile shows only when `public/showcase/manifest.json` has an
   example for it (Mike, 2026-10-25: a tile stays hidden until he keeps its showcase render).
   Keys: `template.<row id>.<value>` for a template, with the two the overnight slate made before
   templates had tiles aliased (`kling-effect:bullet_time_360` -> `effect.bullet_time`,
   `camera-move:camera_rotation` -> `effect.product_orbit`); the looks and plain rows keep their
   old keys. **Search reaches every tile**, with or without an example ("No example yet"),
   examples first; a line under the wall says how many are waiting.
4. **Tabs**: All, New, Free, Transform, Product, Dance, Camera, Holiday, Tools, each drawn only
   when it has a tile with an example. Templates are sorted by their names (regexes in
   `effects-wall.ts`, advice only; anything unmatched is a Transform); image edits and the
   finishing tools are Tools.
5. **The featured strip and NEW** are hand-picked in `web/src/content/effects-page.json`
   (`featured`, `new`), like the Create page's `news.json`. A pick with no example is skipped.
6. **The panel** (`effects-tab.tsx`): the chosen effect's cover with Change, one source slot
   named for what the effect takes (Photo / Image / Clip; drop, choose a file, or the Library) and
   a second slot for a row that takes two, the effect's prompt when it has one, its other options
   (four values or fewer as round segmented buttons, else a select; the option the tile fixes is
   never shown), and **one Approve button that shows the price**: the server's quote
   (`POST /api/effects/quote`, re-asked when a choice changes; a stale quote is never shown), run
   through `POST /api/effects/run` with `expect_credits`, exactly as before. A free look reads
   "Run Noir · Free". The result plays in the panel with Make It Pro, Share, Download and
   "Make a full piece with Vesper"; earlier results this visit list under the wall.
   `EffectStep` is no longer used here (the composer still uses it); the pricing and checks are
   the same `lib/effects.ts` functions.
7. **Phone** (≤900px): the panel sits over the wall and is hidden until a tile is chosen.

CSS: `effects-tab.css`, rewritten (prefixes `fxp-` panel, `fxw-` wall), every rule scoped under
`.fxw` because `.zps button { font: inherit; color: inherit }` otherwise wins. Headlines are
Anton (`--font-anton`).

## As built (2026-10-26)

- `node --test tests/*.test.mjs` 341 pass (new `tests/effects-wall.test.mjs`, 8 tests; the
  `restingFrame` test now asserts a picture), `npm run typecheck`, `npm run build`, eslint on the
  changed files: clean. No Python changed.
- **Verified by running it**: the API on a throwaway Postgres 16 (+pgvector) in the cloud
  container, one seeded account, a minted session, `PHANTRA_EFFECTS_TAB=1`,
  `PHANTRA_FREE_LOOKS=1`, a fake `FAL_KEY`; the studio on `next dev` against it; Playwright at
  1440x1000 and 390x844. Ten tiles with examples, three in the strip, no broken image, no
  horizontal scroll from this page. Choosing Bullet Time 360 and dropping a photo priced it
  through `/api/effects/quote` at **68 credits** on the button; a search for "dance" listed the
  dance templates with "No example yet". **Approve was never clicked**: nothing ran, nothing
  was spent.
- Not done / next:
  - Example renders for the other ~278 tiles. Each one is a priced run; Mike picks which and
    approves them (the What's new flow, `docs/tasks/task-whats-new.md`).
  - The phone header overflows by ~12px on every studio page (the account avatar); not this page.
