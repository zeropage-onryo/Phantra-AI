---
name: phantra-new-effect
description: Publish a Phantra effect to the public /effects pages, or check why one is missing. Use when Mike says "/new-effect", "add this effect to the site", "make a page for <effect>", or asks why an effect has no public page.
---

# New effect

The public `/effects` pages are generated: an effect gets its page, title, description, video
markup, breadcrumbs, sitemap entry and related links automatically once it has a kept showcase
example. Nothing is written per page. `docs/tasks/task-public-effects-pages.md` is the design.

Your job is to get the effect to that state, and nothing else.

## Steps

1. **Find the tile.** Name the effect row in `src/effects.py`, or the template value on a
   templated row (`kling-effect`, `pixverse-effect`, `camera-move`, `costume-preview`; see
   `PRESET_OPTION` in `web/src/lib/effects-wall.ts`). The tile key is `<row id>` or
   `<row id>:<value>`. A new row means editing `src/effects.py` first, as its own change.
2. **Check the example.** Its manifest key is `tileShowcaseKey(<tile key>)`
   (`web/src/lib/effects-wall.ts`). Look it up in `web/public/showcase/manifest.json`.
   - Present: go on.
   - Missing: the page cannot exist yet. Say what example is needed (what to feed the effect,
     shape 9:16 preferred). **Do not render it.** Rendering spends credits and Mike approves every
     render. Offer the quote; render only on his yes, then add the entry (kind, before, after,
     poster, aspect, credits, model, gen_id) with a poster still, because a clip with no poster
     gets no VideoObject.
3. **Regenerate the catalogue:** `venv/bin/python -m ops.export_effects_catalog`.
4. **Check the page:** `cd web && node --test tests/public-effects.test.mjs && npm run build`,
   then confirm `/effects/<slug>` is in the build output. The slug is the tile's name, lowercased
   and hyphenated.
5. **Optional, Mike's call:** add the tile key to `featured` in `web/src/content/effects-page.json`
   to put it in the gallery's featured strip (and the studio wall's).
6. **Ship:** a branch and a PR. Mike merges.

## Rules

- Never write SEO copy into a page by hand. If an effect's description reads badly, fix the
  source: the row's blurb (`EFFECT_BLURBS` in `app/api.py`, or the look / recipe table), or
  `describe()` in `web/src/lib/public-effects.ts` for template tiles.
- Never link an effect from the header or the home page. The footer's "Effects" link and the
  pages' own related links are the only entries (Mike, 2026-11-05).
- Never render or spend without Mike's explicit yes on a quoted price.
