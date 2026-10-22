# Task: the Create home as a front page

**Mike's call (2026-10-22, night):** "I want the front page to be basically news: new offers, new
models, new effects, trending etc." He picked, on the "Phantra Create Page Redesign" canvas:

- **board 66**: the wall runs edge to edge in mixed sizes (big, wide, tall, medium, small), with
  the box floating on top and the tray hanging under it (boards 44 + 48 before it);
- **board 68**: type that pops, tall condensed caps (Anton) with one word of each headline lit
  in its tag's colour;
- the **peek tab** (option A): a slim featured card tucked behind the box's top edge.

His answers before the build: build it; **no offers yet**; **drop the Ideas stage** (nothing
saves an idea today); **autoplay the big tiles, muted**. No "Use this" buttons: the whole tile is
the click.

## What it is

On `/studio` with `create_v2` on (the chat page, `/studio/chat`, draws none of it):

1. **Renders behind the box** (`FrontBackdrop`): the free looks' frames and the first use-case
   stills, dimmed, fading into the page. Decoration only (`aria-hidden`, no clicks).
2. **The headline**: "WHAT ARE WE **MAKING?**" in Anton caps, the last word in the signal yellow.
3. **The peek tab** (`FrontPeek`): the entries marked `peek` in the news file rotate every six
   seconds (held while hovered or focused, still for reduced motion), with dots to pick one. It
   replaces the plain "NEW · Kling 4.0 is in the studio…" line on the home only.
4. **The tray** (`FrontTray`): the person's own work in four stages, Scenes (in progress: the
   scenes a render is waiting on, `GET /api/renders/unfinished`), Stills, Clips and Final cuts
   (the Library's rows and totals, `GET /api/media`). A stage with work waiting on the person is
   lit. A stage is a filter: it turns the wall into that stage's work ("Your stills · 12 · Back to
   the news ×"). A first visit (nothing made) has no tray.
5. **The chips**: All news · New models · Effects · Trending · Updates · Made in Phantra.
6. **The wall** (`FrontWall`): a dense grid, eight columns on a desktop, six on a tablet, four on
   a phone, tiles in six sizes (`big` 4×3, `wide` 3×2, `tall` 2×3, `medium` 2×2, `small` 1×1,
   `slim` 1×2). The news in the file's order, with the showcase's use-case stills spread evenly
   between them (each fills the box with its brief; its name shows on hover). Big and wide clips
   play muted on their own (not on a phone, not with reduced motion); the rest play on hover. A
   clip carries a small ▶.

What a click does, and nothing else: fill the box (never sends), open a studio page, open the
effects (the tab when its flag is on, else the composer's gallery), a free look, or the
talking-photo card. On the tray's own-work wall: a scene opens its page, a still is remixed in the
box, a clip opens the effects on it. **Nothing on the page is priced and nothing spends.**

## The news file

`web/src/content/news.json`, the list Mike edits; `lib/front-page.ts` reads it and leaves out any
entry that is not whole (no id, title, media or action, or an unknown type) rather than drawing it
half-made. An entry:

```json
{
  "id": "kling4", "type": "model", "title": "Kling 4.0 is here", "accent": "4.0",
  "line": "Single takes up to 30 seconds, 1080p, stereo sound.", "date": "2026-10-22",
  "size": "big", "media": "create.usecase.trailer",
  "action": { "fill": "One continuous 20-second take on Kling 4.0: " },
  "requires": "kling_4", "peek": true
}
```

- `type`: `model` (NEW MODEL, yellow), `effect` (NEW EFFECT, blue), `trending` (TRENDING, green),
  `update` (UPDATE, white). The two new tag colours are on `:root` in `studio.css`
  (`--tag-effect`, `--tag-trend`).
- `media`: a key in `public/showcase/manifest.json` (a test fails on one that is not there).
- `action`: `{fill}`, `{href}` (a `/studio` page only: a hand-edited file never links outside),
  `{effect: <tab>}`, `{look: <id>}` or `{talk: true}`.
- `requires`: a capability that must be true (Kling 4.0 hides while its slot is parked).
- `date`: drawn as Today / Yesterday / N days ago / Oct 14; omit it for no date line.

**No offers** until one is live (a test refuses an `offer` type and any price words). **Trending
is picked by hand**: `GET /api/trending` is this account's own week (the tenancy rules allow no
cross-account read), so it cannot say what is trending across the studio; a real studio-wide
Trending needs a shared, count-only aggregate, which is a backend decision for later.

## Files

- `web/src/content/news.json`: the entries.
- `web/src/lib/front-page.ts`: pure and import-free (`tests/front-page.test.mjs` runs it):
  reading the file, gating, the accent split, the date line, the wall's order and sizes, the tray.
- `web/src/components/studio/front/front.tsx` + `front.css`: `useFront` (the reads) and the four
  pieces.
- `web/src/app/studio/(create)/create-view.tsx`: `frontOn = homePage && caps.create_v2 === true`
  draws the four pieces around the one composer; the box itself is unchanged.
- `web/src/components/studio/card-fonts.ts`: Anton (`--font-anton`) beside the studio's card faces.
- Removed: `components/studio/create-v2/` (the v2 sections and their cards) and most of
  `lib/create-v2.ts`; kept there are the flag, the use cases (the renders between the news) and
  the free looks with the effects door.

## As built (2026-10-22)

Branch `claude/create-news-front`. Checked in a browser against `next dev` with every `/api` route
mocked (no request reached a real API; nothing could spend) at 1440, 1024 and 390: no page
errors, no sideways scroll, the wall, chips, peek and tray drawn on the home and none of it on the
chat page; a big tile and the peek fill the box; the Effects chip shows effect entries only; the
Stills stage shows the person's stills; a send on the home still moves to the chat. The
sandbox's Chromium cannot decode H.264, so the muted autoplay was checked in code, not seen;
two showcase clips have no poster (`effect.sound_pass`, `effect.reframe`) and draw their own
first frame instead.

Known gaps: the wall's last row can end ragged (a dense grid packs gaps, it cannot always close
the last one); the elements row under the page is unchanged.
