# Halloween: the neon sign, the Halloween tab and eight new effects (2026-10-27)

Mike, 2026-10-27: "design a halloween effects glowing addition to the effects tab to show
they're now available" -> ten designs on a canvas; he picked **08, the neon sign**, with
"neon halloween" on the Effects tab instead of a "14 NEW" count. Then "can we add some ahs
themed effects as well ... to the effects": anthology-horror effects, built as ORIGINAL looks
and recipes -- never the show's name, its seasons' titles or its characters (FX's marks).

## As built

**Four free looks** (`src/free_looks.py`, rows of `effects.EFFECTS` like the other five,
`provider: "local"`, 0 credits, behind `PHANTRA_FREE_LOOKS=1`):
- `title_sequence` (Title Sequence): sepia `colorchannelmixer`, frame jitter (a per-frame
  `crop` x/y on `sin(n*...)`, scaled back to size), luma grain, vignette, a strobe frame
  every 1.7s for 0.07s (`eq=brightness=...:eval=frame`, option `strobe`, default on) and a
  drawn scratches PNG overlaid at a moving x on two frames of three.
- `the_ward` (The Ward): curves + `colorbalance` to a sickly fluorescent green, a buzzing
  brightness flicker with a hard drop every 2.9s, heavy grain.
- `haunted_manor` (Haunted Manor): the clip split, one copy delayed 0.4s (`tpad` clone) at
  33% alpha and shifted a few px over the other, then a sepia-green grade and vignette.
- `found_tape` (Found Tape): half-resolution softness, `rgbashift` chroma split, scanlines,
  a rolling tracking band, and a PLAY / date stamp (option `stamp`, default on).
Their overlays are drawn with Pillow into the run's workdir (`scratches_png`,
`scanlines_png`, `tracking_band_png`, `tape_stamp_png`); `looks_assets` is unchanged.
Aliases for Vesper in `src/effect_names.py`.

**Four recipes** (`src/effect_recipes.py`, `prompts/effects/<id>.txt`, Kling 3 Turbo Pro,
one photo in, 168 credits for 5s, behind `PHANTRA_EFFECT_RECIPES=1`): `coven`, `sideshow`,
`seance` (Seance, label "Séance"), `the_hotel`. Each keeps the face and has one optional
detail slot. `claude/seasonal-halloween-tab` adds `costume_try_on` to the same dict: a merge
of both is a two-sided add at the end of `RECIPES`, keep both (and the test's count becomes 15).

**The season** (`web/src/lib/effects-wall.ts`): `HALLOWEEN_UNTIL` (2026-11-03 00:00 ET) and
`halloweenOn()` switch three things together, with no deploy to end them:
- the neon sign over the wall (`HalloweenSign` in `effects-tab.tsx`, `.fxw-neon` in
  `effects-tab.css`; seasonal orange/violet kept local to it; still under
  prefers-reduced-motion). Its one button opens the Halloween tab. Nothing on it spends.
- a **Halloween** tab (second, after All): the Halloween Kling / PixVerse templates read off
  their names (`HALLOWEEN` regex; "GhostFace Terror" is deliberately not matched) plus
  `HALLOWEEN_IDS` (the eight above and `costume_try_on`). Unlike every other tab it lists
  tiles with NO example too, examples first -- it answers like a search, because the sign
  sends people there on purpose and none of these has a showcase example yet. Every other
  tab still browses only tiles with an example (Mike, 2026-10-25).
- a neon "Halloween" word on the rail's Effects entry (`.rneon`, `[data-neon]` in
  `studio.css`): the word when the rail is open, a glowing icon when it is collapsed. Its
  flicker dims the glow, never `opacity`, which is what hides `.rl` on a collapsed rail.
The eight ids are on `effects-page.json`'s `new` list, so they carry NEW.

**Examples** (2026-10-27, Mike: "yes do examples so we can start marketing", 0 credits): the
four looks run through `free_looks.apply` + `append_end_card` on the manifest's own sources
(Title Sequence on clip2, The Ward on clip4, Haunted Manor on clip1, Found Tape on clip3),
encoded for the web (720 wide / 1280 wide, crf 27, under 1.4 MB each) and uploaded as NEW keys
under `site/showcase/halloween-v1/` (mp4 + a jpg poster each); `look.<id>` entries added to
`web/public/showcase/manifest.json`. No library rows were written (gen_id null).

## Left for Mike
- Showcase examples for the four recipes and the 13 templates: these cost credits, and a
  recipe needs a photo of a person who has agreed to be shown.
- Both flags must be on in production for the new rows to list.
