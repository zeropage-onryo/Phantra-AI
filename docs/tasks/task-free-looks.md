# Task: free looks (five non-generative effects, Make It Pro, the end card)

**From:** group 2 of `docs/tasks/task-overnight-2026-10-22.md` (Mike, 2026-10-22 00:25 ET).
**Branch:** `claude/overnight-looks`. **Status:** built 2026-10-22, PR open, not merged.

Five looks that cost nothing -- ffmpeg filter graphs on the API host, no provider, no
credit hold -- so the Effects tab (group 3) has a free row and a clip can go through
the studio before a credit is spent. They go through the effects door unchanged:
`src/effects.py` rows, the composer's priced card (showing 0), `POST /api/effects/run`,
the connector's `apply_effect`. `CLAUDE.md` ("Rendering, pricing and the spend gate",
"Effects") has the door; this file has what the looks are.

## As built (2026-10-22)

**Ids** (other streams depend on them): `film_grade`, `noir`, `flash_2000s`, `crash_zoom`,
`vertical_ready`, and the bundle `make_it_pro`. The module is **`src/free_looks.py`**
(`src/looks.py` is the project look, `looks.look_block`, and was there first); the table
rows are built from `free_looks.LOOKS` into `effects.EFFECTS` with `provider: "local"`,
`free: True`, `category: "look"`, `tags` from Cinematic / Social / Product, `price` 0,
`checked` 2026-10-22, `source` this file.

**The flag.** `PHANTRA_FREE_LOOKS=1` (`free_looks.enabled()`, capability `free_looks` on
`GET /api/capabilities`), OFF by default. Off: `effects.listed_names()` leaves the rows out
of the gallery and the connector's `effects`, and `effects.spec()` refuses the ids at the one
gate every door passes ("not switched on"), so production is unchanged.

**Filter graphs** (W, H, fps from `effects.probe_video`; every output is x264 yuv420p):
- `film_grade`: `format=rgb24, lut3d=film_grade.cube (tetrahedral), format=yuv420p,
  noise=c0s=14:c0f=t+u` (luma grain), then two `drawbox` bars when `letterbox` (default on):
  the active picture is `round(W/2.39)` rows, parity-matched to H so both bars are equal
  (`letterbox_bar`). 1280x720 -> 536 active rows = 2.388:1.
- `noir`: `lut3d=noir.cube, noise=c0s=12 (luma only), vignette=angle=PI/4.5, hue=s=0` last,
  so U and V are 128 exactly.
- `flash_2000s`: `curves` (a cheap-digicam lift), `eq=saturation=1.3:contrast=1.1:gamma=0.98`,
  luma grain, then the generated `flash.png` overlaid for 0.1s every 2.4s from t=0
  (`enable='lt(mod(t,2.4),0.1)'`), then the date stamp PNG (`MM DD 'YY`, orange,
  bottom-right) when `stamp` (default on). The looped PNG inputs are bounded with
  `-t <seconds>` and `overlay=shortest=1`: without that ffmpeg never ends.
- `crash_zoom`: `zoompan` with `z` = 1 -> `zoom` (1.25 / 1.35 / 1.5, default 1.35) over
  0-0.3s, held to 0.9s, eased back to 1 by 1.4s (`zoom_at`), `d=1`, the clip's own size and
  rate; the generated `whoosh.wav` mixed under the clip's sound (`amix normalize=0`) or, for
  a silent clip, padded to its length as the track.
- `vertical_ready`: a centred `crop=9k:16k` with k = min(W//9, H//16) rounded down to even,
  so width/height is exactly 9/16 and both sides are even (1280x720 -> 396x704; 720x1280
  stays). No scaling.
- `make_it_pro`: the film grade (no bars) then the 9:16 crop in one graph; the result carries
  `next`, the Sound Pass slot: a priced `add-sound` card on the new clip (`sound_pass_card`:
  the table's MMAudio price at `ledger.charge_credits`, the quote `/api/effects/quote` would
  give) that runs only after its own Approve. Nothing runs for it here.

**The end card.** `free_looks.append_end_card(src, dst, seconds=1.0)`: a 1s "Made in Phantra"
card (the studio's dark ground, the red dot, white words) at the clip's size and rate,
`concat`ed on the end; silence under it when the clip has sound. Every free-look export gets
it (`run_effect(end_card=True)`); it is a function of its own so PR #233's watermark can
adopt it. Drawn with Pillow's bundled font (`ImageFont.load_default(size=)`), not `drawtext`.

**Assets** (`src/looks_assets.py` -> `data/looks/`, gitignored, written on first use):
`film_grade.cube` and `noir.cube` (33^3, from formulas: an S-curve, teal into the shadows
and orange into the highlights; Rec.709 luminance with lifted blacks), `whoosh.wav` (0.7s,
seeded noise through a swept one-pole low-pass), `flash.png` (a drawn radial bloom), and a
README that says so. Nothing downloaded; nothing to license.

**One flow.** `effects.run` hands a local row to `free_looks.run_effect` before the key check,
the stills' cap and `Charge.take`, so a free look never reaches fal and never takes a hold
(`tests/test_looks.py` fails if any of the three is touched). The clip is read by id from this
disk (`cut.sources.resolve`, a download when only the bucket has it) -- `_video_sources(fetch=
False)` on the connector, `_effect_urls -> []` on the route -- or a file path handed straight
to `effects.run(urls=[path])` (the showcase stream). The output is a `generations` row under
the free tool `cut` (`cost_usd` NULL; params: provider `local`, `free`, `credits` 0, the graph,
the timing, `end_card`), a `generated_assets` row (model = the look id), the file under
`data/renders/looks/look-<id>-<stamp>-<32 hex>.mp4` (`render_names.unguessable`), mirrored
to `renders/looks/` in the bucket with a poster. `/api/effects/quote` answers `credits 0,
charged false, free true`; `/api/effects/run` takes `expect_credits: 0` (409 at any other
number, as always) and needs no fal key; the job's `detail` ends "· free" and a Make It Pro
job carries `next`. The connector's `apply_effect` quotes 0 and runs with no token (the
approval gate would price $0 at the 10-credit floor), as `reformat` and `trim_clip` do.

**Timing.** Every look and the end card log one stderr line, `[looks] <id>: 0.42s of work per
second of input (2.00s in, 0.84s elapsed)`, and carry `{seconds_in, elapsed, per_second}` in
the result and on the row. On this Mac, 1280x720: 0.1-0.7 s per second of input.

**Degraded, on purpose.** The Mac's Homebrew ffmpeg has no `drawtext` (no libfreetype) and no
libass, so the date stamp and the card's words are Pillow PNGs overlaid; `has_drawtext()` says
whether the host has the filter and nothing uses it. The contact sheet
(`docs/qa/looks-contact-sheet.png`, `ops/looks_contact_sheet.py`) is from synthetic `testsrc2`
fixtures only: real phone clips need Mike's yes (step 10 of the overnight task), and the script
takes them with `--clip` once he gives it.

**Tests.** `tests/test_looks.py` (skips cleanly without ffmpeg; fixtures made in the test):
the table and the flag; the assets deterministic; each look runs and logs its time; noir U/V
within +-2 of 128; 9:16 exact on 1280x720 and 1000x600; the letterbox 2.39:1 +-0.01 and off
when asked; the zoom at 0.3s >= 1.15 from the parameters AND measured on the frames of a held
still (`measured_zoom`); the flash pop brighter and the stamp in its corner; the end card =
input + 1s within a frame, its frames not the clip's; effects.run, the studio door and the
connector with zero holds, no fal, no cap. `tests/test_effects*.py` and the connector's
listing test compare against `effects.listed_names()` now.

**Not built / open.** The Effects tab itself (group 3) and the brain naming a look (group 6)
read these rows. The composer's card shows "Free · made on the studio's server" at 0 credits;
the gallery tile has no Free badge yet (group 3's page does). `make_it_pro`'s Sound Pass card
is in the job result (`next`) and the studio does not open it on its own yet. Real-clip
contact sheet: Mike's call.
