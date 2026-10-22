# Brand kit §9 done-walk — overnight 2026-10-22

Group 5 of `docs/tasks/task-overnight-2026-10-22.md`, branch `claude/overnight-brand-kit`.
The walk in `docs/tasks/task-brand-kit.md` §9, run against the local stack with **no spend**:
the worktree's API on :8005 (reading the LIVE database through the linked `.env`, with every
provider key and the R2 bucket blanked in that process, `FAL_RECOVER=0`) and the Next studio on
:3005 (`next dev --webpack`, the Turbopack dev server refuses the worktree's `node_modules`
symlink). Signed in to the studio as Mike's own user (account 1, `phantra`) through a minted
two-minute handoff token on a session-unique host (`bkwalk.localhost`). Nothing rendered, drew,
or was quoted; no priced card was reached (the walk has none: every door it touches is free).

Proof of a kit being applied is `GET /api/scenes/{id}/prompt-preview`, as the task file asks.
Screenshots are in `docs/qa/screens-2026-10-22/brand-kit-*.png`.

## What the walk made (QA rows in Mike's workspace, listed for deletion)

| Row | Where | Id |
|---|---|---|
| Brand kit "QA 2026-10-22 kit A" (logo, 2 fonts, 5 references) | `brand_kits` / `brand_kit_assets` | kit 4, files 30-37 (+49-51 added then soft-removed) |
| Brand kit "QA 2026-10-22 kit B" (duplicate of A, then its own palette, fonts, logo) | same | kit 5, files 38-48 |
| Project "QA 2026-10-22 project" (kit cleared at the end) | `projects` | 5 |
| Scene "QA 2026-10-22 scene" (filed in project 5, no references: a draft) | `shoot_concepts` | 435 |
| Cut of that scene (one synthetic clip, one brand-styled caption) | `cut_projects` / `timelines` | `44320fc0-ad3f-45a3-a7f2-7fa2e119962d`, versions 1-3 |
| Bin upload `QA-2026-10-22-testsrc.mp4` (ffmpeg `testsrc2`, 4 s) | `cut_media` | `asset:33` |
| Three MP4 exports + their `.ass` files (A, B, none) | `generations` / `cut_exports` rows; files under this worktree's `data/renders/cut/concept-435-v3-60-*` | — |

The kit files and the export files exist only on this Mac (the API ran with the bucket
blanked): production would show the two QA kits with missing thumbnails until the rows go.
Nothing of Mike's was changed: his two "Gygler" kits (1 and 2), project 2's pick of kit 2 and
project 4 (the showcase) were only read.

## §9 steps

| # | Step | Result | Evidence |
|---|---|---|---|
| 1a | Create kit A from a logo, a palette, two fonts and 5 reference images | **pass** | `POST /api/brand-kits` → kit 4; uploads `logo_light`, `font_heading` (read as "Arial Rounded MT Bold"), `font_body` ("Verdana"), 5× `reference` all 200; a font **without** the licence box → 400 "confirm you have the right to embed this font in video"; a bad hex → 400 `field: palette` "colour 1 is not a #RRGGBB hex". `/studio/brand` card reads "4 colours · 2 fonts · 5 references" (`brand-kit-01-brand-page.png`); the kit page draws the swatches, the caption sample in the kit font and the server end card (`brand-kit-02-kit-A-page.png`). |
| 1b | Create kit B by duplicating A, then change its palette, fonts and logo | **pass** | `POST /brand-kits/4/duplicate` → kit 5 "QA 2026-10-22 kit A copy", same hash as A (`6c3913f473ef`), 8 copied file rows; `PATCH` (navy/cyan/ink/white, caption top in cyan, its own look and tone) + new `logo_light`, `font_heading` ("Georgia"), `font_body` ("Trebuchet MS") → hash `899c857cd4fc`. Page: `brand-kit-08-kit-B-page.png`. |
| 2 | Set a project to A; `prompt-preview` shows A's look line, Avoid line and reference refs; the brief block shows A's tone | **pass** | `PUT /projects/5/brand-kit {4}`; preview: `brand_kit {id 4, hash 6c39…}`, `kit_references: 3` (five on file, capped at `STILL_REFS_MAX`), clip and still `branded` end with `BRAND LOOK (QA 2026-10-22 kit A): QA-A LOOK … Brand palette: pine #0B6E4F (primary); …` + `Avoid: neon, lens flare, stock smiles.`; `writer_block` carries `- Tone: QA-A TONE …`, words to use/avoid, CTA, never-claim and "Never write into a scene". With no kit the same route gives `brand_kit: null` and `branded == prompt` for every entry. Writing a real scene (a Gemini call) **not run**, as §9 says. Panel: `brand-kit-04a-project-panel-A.png`. |
| 3 | Cut export of a rendered scene in that project (local ffmpeg, free) → A's end card; `.ass` style text and fonts dir, not burned pixels | **pass** (with the Mac caveat) | No rendered scene exists in Mike's workspace (nothing may render tonight), so the cut holds a synthetic 4 s `testsrc2` clip uploaded to the bin, plus a `brand`-styled caption. `POST /cut/projects/…/export` → `5.9s · brand end card added (2.5s) · captions NOT burned in: this ffmpeg has no libass -- written beside the MP4`. ffprobe 5.900 s (= 4 + 2.5 − 0.6 fade); the last frame's corner pixel is (243,232,215) ≈ linen `#F4E9D8` (`brand-kit-03-export-A-end-card.png`). `.ass` Style line: `Style: S1,Arial Rounded MT Bold,64,&H004F6E0B,&H004F6E0B,&H22D8E9F4,&H80000000,…,3,12,0,1,43,43,154,1` (pine fill, linen box, lower-left, lower-third margin). Editor: the T1 track reads "BRAND", the program preview draws the caption in the kit's style, the Export panel shows "BRAND · QA 2026-10-22 kit A" and the ticked end-card switch (`brand-kit-12…`, `brand-kit-13…`). Burned pixels need the Fly/CI ffmpeg, as §9 says. |
| 4 | Switch the project to B with no other edit: preview, caption style and end card all change | **pass** | Switched in the studio's project panel (`brand-kit-04-project-picked-B.png`, toast "QA 2026-10-22 kit B on this project — its next scene, still, clip and export use it", Undo; the pick survives a reload, `brand-kit-09…`). Preview: `brand_kit {id 5, hash 899c…}`, B's look and Avoid, `- Tone: QA-B TONE …`. Cut state `brand_kit` = B. Export: 5.9 s, last frame corner (10,14,29) ≈ ink `#0A0F1E` (`brand-kit-05-export-B-last-frame.png`); Style `S1,Georgia,64,&H00F0C94C,…,8,43,43,102,1` (cyan, top). |
| 5 | Clear the kit: preview and export match the no-kit goldens | **pass** | Cleared in the panel (toast "No brand kit — this project works as before", `brand-kit-10…`). Preview `brand_kit: null`, `kit_references 0`, `branded == prompt`. Cut `brand_kit: null`. Export 4.000 s, no card, last frame is the clip (`brand-kit-05-export-none-last-frame.png`). The `brand` track's Style line equals the `preset:bold_center` line character for character and the golden `cut/ass_assembled` S1 line: `Style: S1,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,58,58,256,1`. |

Priced doors: none reached. The QA scene has no reference, so its Render card refuses by the
reference gate ("NO REFERENCE · cannot render yet") before any price; the composer's send,
"Make this image", "Keep 2 · 0 cr" and "Render MP4" were not clicked.

## Beside §9 (free)

| Check | Result |
|---|---|
| `GET /brand-kits/4/end-card.png?aspect=9:16` | 200 `image/png` (`brand-kit-11-end-card-A-9x16.png`); `aspect=4:3` → 400 "aspect must be one of 9:16, 16:9, 1:1" |
| `GET /brand-kits/4/assets/30/file` | 200 `image/png`, the logo bytes, to the owning account |
| A 9th reference | 400 `field: reference` "a kit keeps at most 8 of these -- remove one first" |
| A kit id that is not this account's | `PUT /projects/5/brand-kit {999999}` → 404 "no brand kit 999999" |
| Soft delete of a PICKED kit | `DELETE /brand-kits/5` → list drops it; `GET /projects/5/brand-kit` says `picked: 5, brand_kit: null`; the preview reads as no kit; `POST /brand-kits/5/restore` brings the pick back with no edit |
| The composer's "Kit: <name>" chip (project thread, Image mode) | present, `aria-label "Brand kit QA 2026-10-22 kit B: on"`; one click → "off for the next still" (chip struck through, `brand-kit-07…`); a second click → on. Disabled in Video mode, as designed. |
| Server logs | no traceback or error in the API log for the whole walk; the web log only Next's dev warnings |
| `venv/bin/python -m pytest tests/ -q -k "brand or kit"` (throwaway Postgres) | see the bottom of this file |

## Defect fixed (checkbox 2)

- **The kit page's caption preview said "Book Gygs in seconds." on every kit** — the reference
  brief's tagline, hard-coded in `web/src/app/studio/brand/[id]/page.tsx`, so a QA kit (and any
  other client's kit) previewed its captions with Gygler's line (`brand-kit-02-kit-A-page.png`,
  `brand-kit-08-kit-B-page.png`). Fixed: `captionSample(spec)` in `web/src/lib/brand-kit.ts`
  draws the kit's own tagline, or a neutral sample; test in `web/tests/brand-kit.test.mjs`;
  verified on the page (`brand-kit-14-caption-sample-after-fix.png`). No golden changes
  (front end only).

## Gaps for Mike (not built)

1. **Two kits may share a name.** Mike's workspace already has two kits named "Gygler" (ids 1
   and 2; project 2 picks 2). The project panel's picker lists "Gygler" twice with nothing to
   tell them apart, and the brain's `brand_kits.named_in` ("a kit named in the chat") picks
   whichever sorts first on a tie. A uniqueness rule would refuse the live data as it stands;
   the picker could at least show the kit's swatches or id. Mike's call.
2. **The floating creature covers the composer's settings line below ~1000 px width**: at the
   pane's 800×600 the Kit chip sat under the creature and the click never reached it
   (`brand-kit-06a-composer-800px-creature-over-chip.png`); at 1280 it works. The creature also
   overlaps the project panel's Brand kit select at 800 px. This is the dock's open "canvas-page
   size" item, not the kit's.
3. `GET /api/projects/{id}` carries `brand_kit_id` only; the `brand_kit` summary the spec's §5
   describes lives on `GET /api/projects/{id}/brand-kit` (as built). The studio reads the latter;
   nothing is wrong, just a spec/as-built difference worth a line in the task file (added).
4. Kit B's end card draws the light-background logo on the dark card because B holds no
   `logo_dark` — by design (the card uses the variant that contrasts when one exists), but the
   page gives no hint that a dark card wants a dark-background logo.
5. Burned captions are still unprovable on this Mac (no libass): a CI job that exports one
   kitted cut on the Fly image and checks a pixel would close §9's caveat.

## Environment notes for the morning

- The Supabase **session pooler's 15-client cap was hit** once during the walk (a direct
  `psycopg` connection from a script, with several streams' APIs up against the live database);
  the API's own requests kept working. Keep scripts on the API, not on the DSN, while streams
  run in parallel.
- `next dev` (Turbopack) refuses a worktree whose `web/node_modules` is a symlink out of the
  tree ("Symlink [project]/node_modules is invalid"); `next dev --webpack` runs.
- The venv's editable install resolves `app`/`src` from the MAIN checkout for a script run by
  path; the walk ran everything with `PYTHONPATH=<worktree>`.

## Checks run before the commits

- `venv/bin/ruff check .` — all checks passed.
- `venv/bin/python -m pytest tests/ -q -k "brand or kit"` (throwaway Postgres on :5432) — **139 passed**, 4186 deselected, 161 s.
- `cd web && node --test tests/brand-kit.test.mjs` — 12 passed (the new caption-sample test among them); `npm run typecheck` and `npm run build` — see the fix commit.
