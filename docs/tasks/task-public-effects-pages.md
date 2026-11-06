# Task: public effects pages (`/effects`, `/effects/<slug>`)

**From:** Mike, 2026-11-04/05. He compared Higgsfield's effects SEO (`/effects/examples/<name>`:
87 pages, each with its own sitemap entry, title, VideoObject per example, breadcrumbs and
cross-links; question pages on a hidden `geo.` subdomain) and asked for the same, with two rules:
**"I really just want to create the effect and have all the seo done behind the scenes"**, and
the pages must **not** show up on the main page.
**Branch:** `claude/public-effects-pages`.

## What it is

The signed-out face of the studio's Effects wall (`/studio/effects`, `lib/effects-wall.ts`).
Nothing is a second list:

- **One rule publishes an effect: a kept showcase example.** A wall tile gets a public page
  exactly when `public/showcase/manifest.json` has its example, the wall's own rule for being
  shown. Today that is 31 pages.
- **The data is three committed files the wall already reads**, read at build time
  (`lib/public-effects-data.ts`): `content/effects-catalog.json` (NEW, generated from
  `src/effects.py`), the showcase manifest and `content/effects-page.json` (featured picks).
- **Everything per page is derived** (`lib/public-effects.ts`, pure): slug from the tile's name,
  title `<Name> — AI Video|Photo Effect`, description (the row's blurb; a template tile gets its
  own sentence, since the row's blurb describes all 98 templates), group, cost line, related
  links (own group first), JSON-LD (BreadcrumbList always; VideoObject for a clip with a poster,
  ImageObject for a still), Open Graph image and video.
- **Pages:** `app/effects/page.tsx` (gallery: featured strip, five groups, CollectionPage
  ItemList) and `app/effects/[slug]/page.tsx` (static, `dynamicParams = false`: hero with the
  example playing, You add / You get / Cost, How it works, three questions, four related).
- **Sitemap:** `/effects` and every effect page, off the same list.
- **Where it is linked:** the footer's Tools column ("Effects") and every effect page. NOT the
  header, NOT the home page (Mike's call). `robots.ts` already allows it.
- **"Try it"** signs the person in and lands on `/studio?open=effect&effect=<tile key>`:
  `create-view.tsx` opens that effect's card with its template chosen (`startEffect` now takes
  options; a key that is not on the table opens the gallery instead).

## Adding an effect, end to end

1. The row exists in `src/effects.py` (or a template value on a templated row).
2. Keep its showcase render: an entry in `public/showcase/manifest.json` under the tile's key
   (`lib/effects-wall.ts` `tileShowcaseKey`).
3. `venv/bin/python -m ops.export_effects_catalog` and commit `content/effects-catalog.json`
   (`tests/test_effects_catalog.py` fails CI while it is stale).
4. Deploy. The page, sitemap entry, markup and links follow.

The `/new-effect` skill (`.claude/skills/phantra-new-effect/`) walks these steps and drafts
nothing that needs a render without Mike's yes.

## Not done (on purpose or for later)

- No question pages (`/learn/...`): the hidden-subdomain trick. Next step if the pages index.
- `uploadDate` is one constant (`SHOWCASE_PUBLISHED`, 2026-10-26): the manifest keeps no date
  per entry.
- Showcase data, not code: Time Stop's poster is the same still as Bullet Time 360's (both
  examples were made from it), so their cards rest on the same picture until one poster changes.

## As built (2026-11-05)

- Python: `app.api.public_effects_catalog` (the studio's own `_effect_view`, every row, both row
  switches forced on for the call), `ops/export_effects_catalog.py`, `tests/test_effects_catalog.py`.
- Web: `lib/public-effects.ts`, `lib/public-effects-data.ts`, `components/effects/effect-media.tsx`,
  the two routes, `sitemap.ts`, `site-footer.tsx`, `CreateCtaButton` `to`,
  `tests/public-effects.test.mjs` (runs on the real committed files).
- Checked: web tests, typecheck and build pass; `next start` served `/effects` and pages at
  1440 and 390 wide with no sideways scroll; `/effects/gone` carries its title, description,
  canonical, BreadcrumbList and VideoObject; the sitemap lists 32 effects URLs; an unknown slug
  is a 404.
