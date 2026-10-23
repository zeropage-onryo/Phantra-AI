# Task: the Create page, v2 (group 4 of `task-overnight-2026-10-22.md`)

> **Superseded on the home (2026-10-22, night):** the sections below were replaced by the front page,
> `task-create-front-page.md`. The flag, the use cases and the free looks are kept (`lib/create-v2.ts`);
> the section components and their cards are gone (their words are in git).

**Mike's call (2026-10-22):** restructure `/studio` along Runway / Higgsfield lines, keep a
**Trending this week** row, a **personalized row** and a **brand kit badge**, and put **no prices on
any Create page card** (the priced card before a spend still shows its price). Everything behind a
flag, off by default, no renders, no spend.

Built overnight on `claude/overnight-create-page`; "As built" at the end. Nothing rendered or spent.

## What it is

Behind the `create_v2` capability (`GET /api/capabilities`; ON by default since the visuals
pass of 2026-10-22, `PHANTRA_CREATE_V2=0` on the deployment turns it off), `/studio` is, top to
bottom:

1. **The Vesper bar first**: the composer box exactly as it is, with input chips under it
   (Idea · Script · Product URL · Image · Clip) that focus or pre-fill the box, attach a photo or open
   the effects door, and a "Drop a clip → Effects" affordance beside them.
2. **Continue where you left off**: the newest project and the newest render, from the lists the
   Projects page and the Library already read; hidden on a first visit.
3. **A launch carousel** of live features only (graded phone footage, a vertical cut, an ad from a
   link); no "coming soon".
4. **Use-case tabs** Marketing · Social · Film · Business, three cards each; a card fills the box with
   a brief and focuses it, never sends.
5. **Trending this week**: `GET /api/trending`, this account's own week.
6. **Because you made <project>…**: three next things from the newest project's brief and look.
7. **The effects strip**: the six free looks (group 2's names) and the first six live effects off the
   table; "All effects" opens the Effects tab when `effects_tab` is on, else the composer's gallery.
8. **New at Phantra**: MCP for Claude, Brand Kit, Discord, Models.
9. **One Founding 500 banner**, its numbers placeholders in `FOUNDING_500` (`web/src/lib/create-v2.ts`).
10. **Made in Phantra**: the account's renders (starred first) with **Remix this**: a still is attached
    to the box with "Remix this: <prompt>", a clip opens the effects gallery on it.

With the flag off the page is the component tree it was: the one change to `page.tsx` is a
`{caps.create_v2 === true ? <CreateV2 …/> : null}` branch between the composer and the elements
shelf, which `web/tests/create-v2.test.mjs` pins (imported once, tested once, drawn once, nothing
else of it in the file, no send inside the branch).

## Files

- `app/api.py`: the `create_v2` capability; `GET /api/trending`.
- `src/trending.py`: the week's effects (from `generations.params_json`'s `effect`), briefs
  (`shoot_concepts.spark`) and kept / discarded / edited counts (`output_events`), over seven days,
  for ONE account. `tests/test_trending.py`.
- `web/src/lib/create-v2.ts`: the pure parts (chips, use cases, trend cards, continue and personal
  rows, the looks, the New tiles, `FOUNDING_500`, `kitPalette` / `kitVars`, `SECTIONS`); no imports.
- `web/src/components/studio/create-v2/cards.ts`: every card, with `createElement` so node renders
  them; `create-v2.tsx`: the sections and their reads; `create-v2.css`.
- `web/src/lib/showcase.ts` and `web/public/showcase/placeholder/still.svg`: byte for byte the
  Effects tab stream's (PR #436), so the branches merge clean. `web/public/showcase/manifest.json`:
  version 1, every Create key and the Effects tab's effect keys, all on the placeholder until group 12
  fills it.
- `web/tests/create-v2.test.mjs`, `web/tests/showcase.test.mjs`, `web/tests/_resolve-ts.mjs` (a
  resolve hook so node can load a component file that imports its neighbours without an extension).

## Trending: why it is this account's week, not the studio's

`tests/test_tenancy.py` fails any statement on an owned table that does not name `account_id`, and
`src/outcomes.py` reads "per account, by week, never averaged across accounts". A studio-wide
"most used" would need a shared read nothing here may make, so the row is **"Trending this week ·
in your studio"** and the answer says `scope: "account"`. If Mike wants a cross-account row later, it
needs its own rule (an aggregate with no row-level read, listed in the tenancy test's exempt list).

## The brand kit badge

When the composer's project has a kit (`GET /api/projects/{id}/brand-kit`), every card gets the kit's
palette roles as CSS variables **on that card alone** (`--kit-primary`, `--kit-accent`,
`--kit-background`, `--kit-text`; a role the kit did not fill is left to the studio's palette) and a
"Kit: <name>" badge; the card previews in the kit's colours. Without a kit a card carries no kit
colour at all; the node test renders every card both ways and asserts exactly that.

## No prices

No card reads `credits` off anything it is handed. The node test renders every card with a priced
effect (68 credits) and a priced showcase item (87) and asserts no "credit", no 68 / 87 and no "$" in
the markup. The one card that may say "credits" is the Founding banner's sign-up GRANT (the offer's
copy, placeholder numbers Mike edits), never a price; the test pins that too.

## As built (2026-10-22)

- Backend first: `src/trending.py` + route + `tests/test_trending.py` (4 tests), ruff clean, the
  tenancy route and SQL audits green.
- Then the page: typecheck, `npm run build` and `node --test tests/*.test.mjs` (263 tests) pass.
- Verified by running it (API on 8004 against a throwaway schema with every spend key blanked and a
  fake `FAL_KEY`; studio on 3004 at `create-page.localhost`; a seeded account with two projects, a
  Gygler kit on one, six renders, three effect runs, three scenes). Playwright (the venv's Chromium)
  took the full-page captures and drove the checks; the built-in Browser pane cannot save a PNG, so
  the files came from Playwright:
  - `docs/qa/screens-2026-10-22/create-v2.png` (flag on, project with the kit: all ten sections, 38
    cards, every one wearing "Kit: Gygler"), `create-v2-nokit.png` (same sections, no kit colour on any
    card), `create-v2-390.png` (phone width, no horizontal scroll), `create-v1.png` (flag off: the
    current page, no v2 section in the DOM).
  - A chip ("Script") and a use-case card only filled the box; no POST reached `/api/creative-guide`,
    `/api/scenes/run`, `/api/effects/run`, `/api/generate/run` or any approve during the whole walk.
  - Every section's text was checked for "credit" and "$": only the Founding banner's grant line.
- Two things the walk found and fixed: a grid section's `min-width: auto` widened the page to
  2570px at 390px (rows now scroll); the shell's `.zps button { color: inherit }` outranked the
  Remix button's colour, so on a kit card it was dark on dark (two-class selectors now, and the kit
  card's Remix wears the kit's primary).
- Not verified: the Effects tab door (`effects_tab` on; that stream's branch, #436, is not merged
  here), real showcase media (group 12 fills the manifest), the connector / Desktop surfaces
  (untouched), and the full pytest suite (the parent runs it).
- Local only: this worktree's `web/node_modules` is a real `npm ci` (the shared symlink lacked
  `react-resizable-panels` and Turbopack refuses a symlinked node_modules outside the project root).

## Visuals pass (2026-10-22, evening; branch `claude/create-visuals`)

Mike's references: Runway's "New at Runway" cards and Higgsfield's home ("i wanted the widgets
below the create box to be like this, so phantra has visuals ... thats why we generated images
and videos"). The sections keep their order and ids (`SECTIONS` unchanged) and every card now
draws a group 12 render off the manifest; the overnight screenshot's "Example coming" boxes
predate the manifest.

- **Three shapes** (`cards.ts`): a TILE (picture first; words under it for the highlights row and
  the effects strip, words OVER it bottom-left on a fade for the use-case strip), a BIG CARD
  (eyebrow, display title, line, a button, the picture bleeding off the right edge, rotated)
  and the small text cards. Every export name the node test imports is kept.
- **Layouts** (`create-v2.css`): `cv2-grid4` (the four highlights, every picture cropped
  16:9), `cv2-strip` (tiles of one height, each as wide as its picture's shape; `cv2-strip-tall`
  for the 9:16 look clips), `cv2-grid2` (New at Phantra, two across, one across under 900px).
  The carousel and its arrows are gone: the highlights are a row.
- **New at Phantra** (`NEW_TILES`): `eyebrow`, `cta`, optional `fill` (the button fills the box
  instead of linking) and `tone: "spotlight"` (no picture, the studio's signal as a wash).
  Kling 4.0 is the spotlight and leads; the component hides it unless `caps.kling_4` is true.
  The Models card borrows the phone hero still. `LAUNCH_SLIDES` gained an `eyebrow` and a
  fourth tile (the Bullet Time clip) for the effects.
- **The kit**: every card still carries the kit's variables and badge in the markup (the test
  holds), but the CSS paints the kit only on the cards that make something in it (a brief for
  you, continue, trending) and on the use-case caption's fade; a tile of a render keeps its
  picture and shows no badge.
- Verified in the dev server on a throwaway schema with `create_v2`, `free_looks` and the Kling
  slot on, signed in through `/auth/handoff`: 17 renders drawn, 0 placeholders, 0 broken, no
  horizontal overflow at 1280 or 390 (the big cards clip their own bleed), typecheck, the node
  tests (the slide count is 4). Not verified: the Effects tab door, a kit on the cards, the
  Made in Phantra feed with real renders (the QA account has none).

## The Runway / Higgsfield pass, and the chat's own page (2026-10-22, afternoon; branch `claude/create-page-layout`)

Mike picked the layout on the "Phantra Create Page Redesign" design canvas ("this looks great"), then:
the chat "opens up its own page", FREE / NEW / POPULAR tags are fine, and render new use-case stills.

- **Two addresses, one composer.** `app/studio/page.tsx` moved to `app/studio/(create)/create-view.tsx`;
  the `(create)` route group's `layout.tsx` draws it, and `/studio` (`page.tsx`) and `/studio/chat`
  (`chat/page.tsx`) draw nothing. A layout stays mounted between its pages, so a send started on the
  home keeps its wait, progress line and job when the address moves. The view reads the path:
  - **Home** (`/studio`): always drawn "empty" (headline, box, sections); never the thread. With a
    conversation in the store, a "Continue your chat" card under the box links to `/studio/chat`.
    With `create_v2` on, the box sits near the top (`.zc-home`, no full-screen centring), the old
    starters give way to the v2 input chips, and the pinned keyboard hint is not drawn.
  - **Chat** (`/studio/chat`): the thread with the docked box; no sections. Empty (New session, or
    the address opened with no conversation) it replaces itself with `/studio`.
  - **Home -> chat** happens when the thread GROWS through this component (a send, a card, the
    talking-photo card): `setThread` is wrapped to mark that it wrote, and the growth is measured
    against the length last seen after `ready`, so the saved thread loading, or a project's
    conversation swapped in by the provider, never moves anybody. URL-param handlers that tidy the
    address now `replace` to the current path, not `/studio`.
  - `lib/creature.ts isCreatePage` counts `/studio/chat` as Create (the creature rests small there too).
- **Sections** (`SECTIONS`: vesper, launch, promo, usecases, work, effects, made; down from ten):
  - full width (`.cv2` up to 1480px; it was 1180), section headings Inter 20/600, highlight titles
    in Oswald caps;
  - **promo + tool tiles**: `PROMO` (Kling 4.0, only while `caps.kling_4`; picture
    `create.usecase.trailer`) beside `TOOL_TILES` (Talking photo NEW, Final cut FREE, Brand Kit,
    Phantra in Claude, Elements, Discord). Each tile links, fills the box, or opens the
    talking-photo card (`onTalk`, a new prop). Replaces the two-across New at Phantra cards;
  - **use cases**: six cards a tab (twelve new stills, below), the "Start with Vesper" eyebrow gone;
  - **work**: Continue and "Because you made…" are one row; the personal cards show a short `line`
    over a faded picture (the project's cover, else the newest render), never the brief;
  - **effects**: portrait tiles with names under them, the looks tagged FREE, live effects shown only
    when the manifest has an example (`EffectTileView`); the week's most-run shown effect wears
    POPULAR (`popularEffect`). The text-only Trending row is gone: it printed the effect table's raw
    ids (`voice-eleven-v3`) for effects the strip never shows. `/api/trending` stays, for the tag;
  - rows scroll with Embla (`Rail`: drag, snap, arrow buttons that show only when there is somewhere
    to go), never a browser scrollbar; Made in Phantra is a picture grid with Remix on hover
    (always shown on touch), twelve on desktop, six on a phone;
  - the Founding 500 banner is not drawn (its numbers are still placeholders); `FoundingBannerView`
    and `FOUNDING_500` stay for the promo slot.
- **Media**: twelve Seedream 4.5 stills at 4:5 (`gen:190`-`gen:201`, 10 credits each, 120 in all, on
  Mike's yes), quoted and approved through the studio connector, filed in the manifest as
  `create.usecase.{launch_teaser,seasonal,founder,hook,day_in_life,unboxing,scifi,horror,period,
  real_estate,gym,event}`. Invented people and products, no logos.
- **Verified**: typecheck, eslint (no new errors), `npm run build` (`/studio` and `/studio/chat`
  static), `node --test tests/*.test.mjs`. In a browser: `next dev` with every `/api` route mocked by
  Playwright interception (no API, nothing could spend; the guide POST was refused by the mock) at
  1440 and 390: the seven sections, no horizontal overflow, the tabs switch, the effects arrow pages,
  "Continue your chat" goes to `/studio/chat` and back, a send on the home lands on `/studio/chat`
  with no sections there. Not verified against the real API or a real account's data.
