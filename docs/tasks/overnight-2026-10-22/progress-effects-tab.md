# Progress: group 3, Effects tab (branch `claude/overnight-effects-tab`)

A copy of the group's checkbox list from `docs/tasks/task-overnight-2026-10-22.md`, ticked as
the work lands. The task file itself is never edited from this branch.

- [ ] New page `/studio/effects` reading the same effects table the composer gallery reads; flag `effects_tab`
  - Layout: "Drop a clip" first, then a grid of before/after hover-to-play cards with a Free or Pro badge (no credit numbers), filters Free/Pro and Cinematic/Social/Product.
  - Each result offers: Make It Pro, Share, "Turn this into a full piece with Vesper".
  - Only effects that run today appear. No "coming soon" tiles.
  - Done when: `cd web && npm run typecheck && npm run build` pass, and with the flag on locally the page renders the grid (screenshot in the report). With the flag off, the route 404s or redirects.

Sub-steps this stream works through (its own, finer than the group's one box):

- [x] The `effects_tab` capability flag (off by default) and the table's `free` / `tags` fields on `GET /api/effects`
- [x] The showcase manifest (placeholder) and `web/src/lib/showcase.ts`
- [ ] `/studio/effects`: the page, the rail entry, the cards, the filters, the priced card, the result actions
- [ ] `web/tests/effects-tab.test.mjs` and the Python flag test
- [ ] Local run with the flag on: screenshot `docs/qa/screens-2026-10-22/effects-tab.png`; flag off: 404 by curl
- [ ] `docs/tasks/task-effects-tab.md` with "As built"; PR opened
