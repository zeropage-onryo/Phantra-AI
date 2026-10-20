# Brand Kit — spec (Phase 1, waiting on Mike's approval)

Status: **SPEC ONLY. Nothing built, nothing rendered, nothing spent.** Phase 2 starts on Mike's yes.

A brand kit is an opt-in, account-owned record (many per account, one per client) that a
project picks. When a project has no kit, every route, generator and export behaves exactly
as it does today, byte for byte. The MCP connector is in directory review, so no MCP tool, no
MCP server file (`src/mcp_server.py`, `app/mcp_mount.py`, `app/mcp_auth.py`) and nothing in the
plugin repos changes.

## 0. What the reference asks for

`docs/reference/gygler.mov` is not in the repo. The video attached to the brief
(`~/Downloads/IMG_3912.MOV`, 60 s, 1920x1080, 30 fps) was read as frames instead. It is
motion graphics, not generated footage:

- one orange (≈#F7931E) on cream, with white type on full-orange beats;
- one rounded geometric sans for every headline, set large and short ("Find the right
  talent.", "Book Gygs in seconds.");
- oversized, low-opacity background words behind each headline (FIND, BOOK, RATE, SKILLS);
- sliding, softly blurred UI cards, and soft fades between beats;
- an end card with the logo, the tagline "Get a Gyg, stay for good." and the URL, on the cream
  background;
- one continuous music bed.

What a kit can enforce in Phase 2: palette, type, caption style, the logo end card, tone,
banned elements and a look line on every still and clip. What it cannot do yet: the
oversized background words and the sliding cards are composited motion graphics, and the
Cut refuses a second video track (`src/cut/render.py:256`). That layer is a separate build;
it goes to `docs/BACKLOG.md` (§9), not into this one.

## 1. How the comparables model a brand

Sources: official help pages, product pages and the vendors' own MCP tool descriptions. Only
Runway's article was read in full. Canva's and Adobe's help pages refuse automated fetches,
so their entries come from search excerpts of the official pages.

| | Runway | Higgsfield Ads / Marketing Studio | Adobe Express | Canva |
|---|---|---|---|---|
| Shape | Kit = named **sections** of images, video and audio; an optional description per section goes into a system prompt | Brand: logo, palette (main + hex extras), fonts (display/body), tone of voice, audience, aesthetics, description, selling points, socials. **Products** are their own records (url, up to 8 images, text) | Brand: logos and colours tagged primary/secondary, fonts tagged Header/Body, palettes, graphics, templates | Logos, palettes, font pairings (heading/body/sizes), brand voice (500 chars), photos, graphics, icons, charts, Brand Templates |
| Kits | Many per workspace; one brand or project each; shared to a whole workspace or to projects ("agencies… each with its own kit") | Brand id per product; count not stated | Several per account | Up to 1,000 depending on plan (Canva's own pages give conflicting figures), plus one personal kit |
| Who reads it | Agent (a Brand toggle per session), Apps, image generation | Ad generation; `brand_kit:false` turns it off per run; the kit reaches only its own products | AI prompt bar and AI Assistant (colours, fonts, text), Text-to-Template | Magic Write (voice), Magic Design (templates) |
| Fonts | none (images only) | not stated | upload OTF/TTF on paid plans; Enterprise docs require "rights and licenses" | upload OTF/TTF/WOFF on paid plans; the licence must allow embedding |
| Enforcement | none | none | element locks, template unlock rules, "Lock & Restrictions" | template locks, Brand Controls, approvals |

What Phantra takes from them:

- **Higgsfield's split** between brand and product. Phantra already has products: a
  `props` element with photos and a vision description. The kit **links** them and adds
  allowed claims. It does not copy photos.
- **Runway's scoping** (many kits; a project picks one) and its idea that free text in a kit
  becomes model instructions.
- **Adobe/Canva's typed roles** (primary/accent/background/text colours, heading/body fonts)
  and their font licence rule.
- **Not taken:** locks, approvals and templates. This is a one-operator studio, and there is
  no template system for a lock to protect.

## 2. Scoping and tenancy

**A kit belongs to an account; a project picks at most one.** There is no studio-wide or
default kit. That keeps Mike's 2026-10-13 rule ("a brand exists only inside a PROJECT…
never studio-wide", `task-remove-brand-labels.md`): a kit is inert until a project chooses it.

What changes in tenancy:

- Two new **owned** tables in `db.OWNED_TABLES`, each with a dated reason, created through
  `own_table`:
  - `brand_kits`
  - `brand_kit_assets`
- One additive column, `projects.brand_kit_id BIGINT NULL`. This is the same shape as
  `shoot_concepts.project_id`, with no FK, so init order stays free.
- Every query against the two tables carries `account_id` in the same SQL literal (the
  `test_no_query_against_an_owned_table_forgets_its_owner` guard).
- Setting `brand_kit_id` on a project checks that the kit's `account_id` equals the
  caller's, the way `_form_project` checks a project.
- A new owned media root, `brandkits`, added to `media.OWNED_ROOTS` and
  `asset_shelf.URL_ROOTS` / `parse_ref`. Keys become `m/<account>/brandkits/<kit>/<sha24>.<ext>`
  (tenant-fenced, content-addressed, so a duplicate kit shares the files).

What does not change:

- `auth.current_account_id` is the tenant of every route.
- `accounts` keeps no brand column.
- The shared learning shelves stay shared.
- No `brand` column returns anywhere.
- `docs/tasks/brand-allowlist.txt` targets the old names only, so "brand kit" passes it.

## 3. Fields

Fields 1-5 are stored in `brand_kits.spec` (JSONB, validated by `src/brand_kits.py` with
fixed limits and versioned `"v": 1`). Files go in `brand_kit_assets`
(`id, kit_id, account_id, role, stored, mime, meta jsonb, created_at, deleted_at`).

| Group | Field | Keep? | Read by (Phase 2) |
|---|---|---|---|
| Identity | name | keep | studio |
| | logo light, logo dark (asset roles `logo_light`, `logo_dark`) | keep. **PNG is what renders**; an SVG is turned into a 2048 px PNG in the browser on upload and both are stored, so no new Python dependency | end card |
| | tagline | keep | end card, writer |
| | one-line positioning | keep | writer, brain |
| | **url** | **add** (the reference end card shows it) | end card |
| | **audience** (one line) | **add** (Higgsfield stores it; the writer needs to know who it is talking to) | writer |
| Visual | palette: hex with role primary / accent / background / text (+ up to 4 extras) | keep | captions, end card, look line (hex plus an optional colour word, because models read words better than hex) |
| | fonts heading / body (asset roles `font_heading`, `font_body`; TTF/OTF only) | keep. Upload needs a **licence attestation** ("I have the right to embed this font in video") stored in `meta`. The family name is read with Pillow | captions, end card, studio preview (@font-face) |
| | caption style: font (heading or body), size, fill/outline/box colours (by palette role), position (bottom / lower third / top), uppercase | keep | Cut captions |
| | safe zones: one inset % (top, bottom, sides) | keep, **simplified** (one inset, not a value per aspect) | caption margins, end-card layout |
| | aspect presets | **simplified to one default aspect** | Cut export's default aspect only (scene defaults untouched) |
| | **motion: transition style (one of the 58) + length** | **add** (the reference's "soft fades") | end-card transition; default for new transitions in the editor |
| Look | reference images (asset role `reference`, up to 8) | keep | stills and keyframes as **look-only** refs, appended after the scene's refs (never first; `refs[0]` anchors). Clip renders do not get them: the keyframe already carries the look, and adding refs changes some models' input mode |
| | style description (≤ 1,500 chars) | keep | appended to every still, keyframe and clip prompt |
| | banned elements | keep | writer ("never write"), plus an `Avoid:` line on every render, which `prompts_for`'s `negative_field` rule can lift |
| Voice | tone rules, words to use, words to avoid, CTA style | keep | writer, brain |
| Sound | default voice slot, music direction (genre, BPM, mood, reference tracks as `music_ref` assets), loudness target | **stored only**. The Cut keeps -14 LUFS until the audio layer reads it | nothing yet |
| Products | links to `props` element ids, each with allowed claims; plus a kit-wide "never claim" list | keep as **links** (no copied photos) | writer |
| Characters | links to `characters` element ids | keep as links | writer (named as the brand's recurring cast). Refs stay per scene |
| — | locks, approvals, templates, socials | **cut** | — |

## 4. Schema and migration plan

All of it is additive and runs inside `init()` with `IF NOT EXISTS`:

```sql
CREATE TABLE IF NOT EXISTS brand_kits (
  id BIGSERIAL PRIMARY KEY, account_id BIGINT, name TEXT NOT NULL,
  spec JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS brand_kits_account ON brand_kits (account_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS brand_kit_assets (
  id BIGSERIAL PRIMARY KEY, kit_id BIGINT NOT NULL, account_id BIGINT, role TEXT NOT NULL,
  stored TEXT NOT NULL, mime TEXT NOT NULL, meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS brand_kit_id BIGINT;
```

- `src/brand_kits.py` owns both tables: `init(dsn)` plus `ensure(dsn)` under
  `db.run_init`, the `generative` shape.
- It is registered in `app/main.py:init_tables` and in `tests/test_tenancy.py:_init_everything`.
- No backfill: every live project gets `NULL`, meaning no kit. No live row is rewritten, so no
  backup is needed. Rollback is to leave the column unread.
- Delete is soft (`deleted_at`). A project pointing at a deleted kit reads as no kit, and its
  panel says the kit was deleted.

## 5. API routes

These live in `app/api.py`, and every one takes `account_id = Depends(auth.current_account_id)`.
None of them spends.

| Route | Does |
|---|---|
| `GET /api/brand-kits` | list (name, swatches, logo thumb, projects using it) |
| `POST /api/brand-kits` | create from `{name, spec}` |
| `GET /api/brand-kits/{id}` | the kit with minted asset URLs (`media.url_for`) |
| `PATCH /api/brand-kits/{id}` | edit the spec; refuses fields that fail validation (400 with the field) |
| `POST /api/brand-kits/{id}/duplicate` | copies the spec and asset rows (same stored names); returns the new kit |
| `DELETE /api/brand-kits/{id}` | soft delete; Undo restores |
| `POST /api/brand-kits/{id}/assets` | multipart `role` + file (logo PNG/SVG+PNG, font TTF/OTF + attestation, reference JPEG/PNG/WEBP/HEIC, music ref audio); size caps per role |
| `DELETE /api/brand-kits/{id}/assets/{asset_id}` | soft delete |
| `GET /api/brand-kits/{id}/end-card.png?aspect=` | the end card drawn with Pillow (free, local) for the preview |
| `PATCH /api/projects/{id}` | `ProjectBody` gains `brand_kit_id: int \| None` (explicit `null` clears; absent means untouched) |
| `GET /api/scenes/{id}/prompt-preview` | **new, free**: the exact still and clip prompts (and refs) a render would send, with and without the kit. It is how the done-walk proves the kit is applied without spending a credit |

`GET /api/projects/{id}` adds a `brand_kit` summary (id, name, swatches) only when one is set.

## 6. How each generator reads the kit

There is one resolver, `brand_kits.for_project(project_id | concept_id, account_id) -> Kit | None`.
Every hook is written as `if kit: ...`, so the no-kit path never enters new code.

1. **Scene writer and the brain (tone).** `projects.brief_block(project)` appends a
   `BRAND:` block when the project has a kit: name, positioning, audience, tone rules,
   words to use and avoid, CTA style, products with allowed claims, the never-claim list,
   recurring characters, and banned elements as "never write". This one function feeds
   `shootgen.project_brief()`, which reaches `{project}` in `scene_brief_prompt.txt` and
   `scenes_prompt.txt`, `creative_guide.instructions()`, `rework` and the shot list. The
   ContextVar is only set by `/creative-guide` and `/scenes/run`, and those are the two
   routes that write in a project.
2. **Look on clips (render time, not baked).** `timeline.render_target()` (`src/timeline.py:639`)
   appends `BRAND LOOK: <style description; palette words>` and `Avoid: <banned>` after
   `for_render`, for both whole-scene and per-part renders.
   - The saved `shot["prompt"]` is never rewritten, so existing quotes, the re-plan check and
     MCP-written scenes (`write_scene` saves verbatim) all work unchanged.
   - Switching kits changes the next render with no edits.
   - The kit is found from the concept's `project_id` (`projects.project_for_concept`).
3. **Look on stills and keyframes.** `scene_chain.keyframe_scene` / `_keyframe_timeline` and
   `fal.generate_image_from_prompt` / `nano_banana.generate_from_prompt` (when given a
   `project_id`) append the same look line and add the kit's reference images as look-only refs
   (`ref_roles` style), after the scene's own refs and within each model's ref cap.
   - Element sheets (`literal=True`) are **excluded**: a sheet is evidence of the face, not a
     look.
4. **Quotes stay honest.** `pricing.content_hash` adds the kit's hash **only when a kit is
   set**. Switching or editing a kit between quote and approve then gives `stale_content`
   instead of rendering something the person did not price.
   - No-kit hashes stay identical.
   - Prices do not change: they are per second or per still. The one exception is a still model
     priced per input image; for those the quote counts the added refs, and the spec lists them.
5. **Provenance.** `generations.params_json` records `{brand_kit: {id, hash}}` on kitted
   renders, as the "provenance in params_json" rule requires.
6. **Cut captions.**
   - `CAPTION_STYLES` gains `brand`. A caption track created in a cut whose project has a kit
     defaults to `brand`; an existing track can be switched to it in the inspector.
   - At export, `ass_document()` writes the `brand` style from the kit (font family, size,
     palette-role colours as ASS `&HAABBGGRR`, position, safe-zone margins) and the burn runs
     as `ass=…:fontsdir=<tempdir>`, with the kit's fonts fetched from the bucket into that
     tempdir.
   - With no kit, a `brand` track falls back to `bold_center`. Docs without a `brand` track
     produce exactly the argv and `.ass` text they do today.
   - The studio caption preview loads the kit font through @font-face.
7. **Logo end card.**
   - At export (`POST /api/cut/projects/{id}/export`, mp4 and still), when the cut's concept
     belongs to a kitted project, `render` appends one still segment: the card PNG (Pillow,
     the background-role colour, the logo variant that contrasts with it, tagline and url in
     the heading font, inside the safe zone), joined to the last clip with the kit's transition.
     It is 2.5 s by default.
   - `ExportBody` gains `end_card: bool | None` (None means follow the kit), and the export
     panel shows a thumbnail and an off switch.
   - The card is added at export, so the saved doc and its versions are untouched.
   - The music bed is not stretched: when it is shorter than the export, the card runs
     under silence. Mike's call whether the card should instead hold the music's last bar
     (§10).
8. **Not touched:**
   - MCP `assemble_clips` / `join`, `/assemble`, OTIO/SRT export, effects, clip edits,
     element sheets, the orchestrator.
   - Kitted projects reached through the connector do get the look at render (point 2),
     because it lives in the render path the studio and the connector share. No MCP file
     changes, and a reviewer's fresh account has no kit, so the reviewer sees today's
     behaviour.

## 7. The Brand Kit page (Next studio)

- `/studio/brand`: one card per kit (swatches, logo, name, "used by N projects"), with New,
  Duplicate and Delete (with Undo). The nav gains "Brand" beside Elements.
- `/studio/brand/[id]`: the attached reference shot's layout, a left form column and a
  right live preview. Sections: Identity, Visual, Look, Voice, Sound, Products & characters.
  - **Uploads:** drop a logo, fonts and up to 8 reference images.
  - **Products & characters:** pick from the existing Elements; nothing is re-uploaded.
  - **Live preview, all free:** palette swatches, a caption sample in the kit font, the
    server-drawn end card in 16:9 / 9:16 / 1:1, and the exact look line that will be appended.
- **Picking a kit per project:** a "Brand kit" select in the project's brief / look / memory
  panel (`PATCH /api/projects/{id}`). The Render card and the Cut export panel show a small
  "Brand: <name>" chip, so the person can see a kit is on.
- New colours go into `studio.css :root`. Kit colours are data, applied inline only inside the
  preview.

## 8. Tests (Phase 2, in this order)

1. **First commit, before any behaviour change:** `tests/test_brand_kit_no_kit.py` captures
   golden outputs **on today's code**. Every later commit must keep them byte-identical:
   - `build_scene_brief_prompt` / `build_scenes_prompt` for a fixed project;
   - `project_brief()`;
   - `creative_guide.instructions()`;
   - `timeline.render_target` (whole and per part);
   - `as_still_frame` and the Gemini request parts (provider patched);
   - `fal.image_request` body and `generate_for_shot`'s fal arguments (patched);
   - `pricing.content_hash`;
   - `render.compile_args` argv plus `ass_document()` text for the assemble fixture, a stills
     doc and a three-style caption doc;
   - `assemble.build_doc` and `join.plan`;
   - a snapshot of the three MCP tool lists (names, titles, schemas).
   No network, no Create gate (stubbed per conftest).
2. Unit tests: spec validation and limits; ASS colour conversion; font family read; the
   end-card layout box; `content_hash` with a kit; the kit resolver refusing another
   account's kit.
3. Tenancy: the new tables are owned, every route declares its account, and setting another
   account's kit on a project is a 404.
4. Kit-on tests: brief block, render_target suffix, still refs order (kit refs never first),
   the `brand` caption style, and the end card appended in `compile_args`. Switching kit A to
   kit B changes all of them.
5. Web: `node --test` for the kit form's validation helpers, typecheck, build.
6. The whole suite as CI runs it (pytest, ruff, web tests, typecheck, build).

## 9. Done-walk (no spend)

1. In the studio, create kit A from a logo, a palette, two fonts and 5 reference images.
   Create kit B by duplicating A, then change its palette, fonts and logo.
2. Set a project to A.
   - Writing a scene calls Gemini. That is free model text on a plan, but it is still a model
     call, so it waits for Mike's word.
   - Without it: `prompt-preview` shows A's look line, Avoid line and reference refs, and the
     brief block shows A's tone.
3. Run a Cut export of an existing rendered scene in that project (local ffmpeg, free).
   - Expected: A's end card.
   - **Caveat:** Homebrew's ffmpeg on this Mac has no libass, so the Mac proves the `.ass` style
     text and the fonts dir, not burned pixels. A burned check needs the Fly image (or CI's).
4. Switch the project to B with no other edit: preview, caption style and end card all change.
5. Clear the kit: preview and export match the no-kit goldens.

A real still, keyframe or clip render under a kit happens only on Mike's explicit go-ahead.

**BACKLOG entries this adds:**
- a motion-graphics overlay layer (oversized background words, sliding cards: needs a second
  video track in the Cut);
- the audio layer reading the kit's voice, music direction and loudness;
- "import a kit from a website" (Higgsfield and Adobe both do it; `linkrefs` could).

## 10. Mike's calls

1. **Kit look on connector renders of a kitted project.** It is applied, because it lives in
   the shared render path. The no-kit path, which is what directory review sees, is unchanged.
   The alternative is studio-only, which needs a studio flag threaded into `approve_render`.
   Recommendation: apply it.
2. **End card under a short music bed:** silence (recommended, simplest) or hold the music.
3. **Font licence:** an attestation checkbox only (recommended), or also restrict uploads to
   a known OFL list.
