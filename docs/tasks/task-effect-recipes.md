# Task: recipe effects (behind `PHANTRA_EFFECT_RECIPES`)

**From:** Mike, 2026-10-26: "now i should add more effects, show me the top effects on higgsfield
first and lets compare", then "lets go" on the ten proposed.
**Branch:** `claude/effect-recipes`.

## Why

Higgsfield's effects page lists 87 effects (read through its connector, `get_presets
source=viral`, 2026-10-26; the order its gallery shows, not a published popularity number). Every
one is a "chain": a written prompt run on a video model with the person's photo, not a model of
its own. Of its first twenty, Phantra had two outright (Earth Zoom on PixVerse, Bullet Time on
Kling) and five near ones. The gap is recipes and examples, not models: Phantra's 252 Kling and
PixVerse templates lean holiday and dance, theirs lean cinematic transitions and product reveals.

## What is built

- `src/effect_recipes.py`: ten recipes, each a row of `src/effects.py` (category `video_effect`,
  `recipe: True`), so the quote, the Approve, the hold, the cap, the generations row and the
  Assets wall are the table's own. Our names and our words, written from the effect's idea, never
  copied: Float Drop, Window Grab, Gone, Iris Dive, Echo Crowd, Time Stop, City Giant, Meltdown,
  Pocket Me, Overhead Flip.
- **The prompts are plain text** in `prompts/effects/<id>.txt` (format in its README): the prompt,
  and for four recipes a `{detail}` slot with a `---detail---` line and a `---default---`. The
  person types at most one short detail (200 characters, `effects.RECIPE_MAX_NOTE`) into that
  slot (the product, where the camera comes out, where they land); a recipe with no slot takes
  no words at all (`prompt: "none"`). `effects.build_body` writes the prompt; what was typed never
  replaces it.
- **One model, read off the video table**: `fal.VIDEO_MODELS["kling3-turbo-pro"]` image-to-video
  (its `i2v`, its field, its $0.14/s at 1080p, its 3-15 s). Lengths 5 or 10 s, anything else
  refused. **5 s = $0.70 = 168 credits.** That is more than Higgsfield's ~70-90 for the same
  kind of effect; Kling 3 Turbo was chosen for quality on these prompts, and a cheaper model
  (LTX 2.5 fast at $0.09/s, Wan 3 at $0.10/s at 720p) is one line (`MODEL`) to try against the
  examples.
- **Off by default**: `PHANTRA_EFFECT_RECIPES=1` lists them (`effects.listed_names`) and lets them
  run (`effects.spec` refuses one otherwise), like the free looks' flag. On the Effects page a
  recipe tile shows only once the showcase manifest has an example for it (`effect.<id>`); search
  finds it before that. Product recipes sit under Product, the rest under Transform.
- `GET /api/effects` carries `recipe`, `hint` (what the optional box is for, its label on the
  page) and `made_with` ("Kling 3 Turbo Pro", shown in the panel as "Phantra recipe · ...").

## As built (2026-10-26)

- `tests/test_effect_recipes.py` (6 tests), `tests/effects-wall.test.mjs` (+1). Full Python suite
  in the cloud container against Postgres 16: 4,876 passed, 1 failed,
  `test_generative_init_once.py::test_two_inits_at_once_are_why[fal_requests]`, a race that
  asserts two inits DO deadlock and depends on timing; nothing here touches `fal_requests`.
  `ruff check .`, the 358 web tests, typecheck: clean.
- **Ran it**: the API with the flag on lists 29 effects, the ten recipes at 168 credits each with
  their hints; on the page a search for "float" finds Float Drop ("No example yet"), a dropped
  photo and a typed product price it through `/api/effects/quote` at **Approve · 168 credits**.
  Approve was never clicked: nothing ran, nothing was spent.

## Next (Mike's calls)

1. Merge, then set `PHANTRA_EFFECT_RECIPES=1` on Fly (`fly secrets set` on `phantra-api`).
2. One example render per recipe, each approved at its price (10 x 168 = 1,680 credits), proposed
   sources from the Library: the dancer still (gen:168) for the full-body ones, the UGC still
   (gen:174) for the face and hands ones. Each kept example goes into
   `web/public/showcase/manifest.json` as `effect.<id>`, and its tile appears.
3. Look at the examples before more recipes: rewrite a prompt that misses, or move a recipe to
   another model.
