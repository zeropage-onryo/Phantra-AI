# Motion graphics in the editor (BACKLOG #28, the first item)

Status: **BUILT 2026-10-20**, on Mike's "start the motion-graphics layer from BACKLOG #28".
Nothing was generated or spent building it; the walk ran on a throwaway schema with every
provider key and the bucket blanked.

## What it is

The Gygler reference (`IMG_3912.MOV`) is mostly composited motion graphics: kinetic headlines,
one oversized faint word behind each beat, UI cards sliding in, small pills of text. The editor
had no way to lay anything over the picture (one video track, captions only). This adds a
**graphics track** to the Cut:

- `{"id": "G1", "kind": "graphic", "items": [...]}`. Items are timed like caption cues and come
  in four types:
  - `headline`
  - `background_word` (one word, huge, 14% ink, drifting 4% left over its life)
  - `card` (a still from the bin on a rounded card with a soft shadow, optional caption under it)
  - `label` (a pill)
- Each item has a `position` (center / left / right / top / bottom / lower_left), `anim_in`
  (none / fade / rise / slide_left / slide_right), `anim_out` (none / fade / sink / slide_left /
  slide_right), a `size` (s / m / l) and a `color` (auto / a palette role / #RRGGBB).
- Items on one track may not overlap. Tracks stack: G1 is drawn first, so the background word
  goes on the lowest track.

## How it renders (`src/cut/graphics.py`)

- **Drawing.** Every item is drawn ONCE with Pillow as a canvas-sized transparent PNG at its
  resting place. Fonts and colours come from the project's brand kit when it has one
  (`Style.from_kit`, fed the kit's font files by `src/cut/brand.prepare`); otherwise the item is
  white, with a soft shadow on headlines, in Pillow's own scalable font.
- **Moving.** The export lays each PNG over the picture with ffmpeg's `overlay`, using an eased
  x/y expression of `t` and `fade ... alpha=1` in and out, gated to the item's time. The order is
  picture (padded to length), then graphics, bottom first, then captions, then the trim.
- **No libass, no drawtext.** This runs the same on the Mac's Homebrew ffmpeg and on Fly.
- **Nothing changes without graphics.** A doc with no graphics track compiles the same argv as
  before (`tests/test_brand_kit_no_kit.py` still holds). The sound-only export opens no graphic.
  OTIO export leaves graphics out; it only carries video and audio.

## The editor

- **Adding.** The Text tab's "Add a graphic" puts a headline / big word / card / label at the
  playhead, on the first graphics track with room (a new G track when none has), and selects it.
- **Timeline.** Graphics tracks sit above the picture; blocks move and trim like cues
  (`set_graphic`).
- **Inspector.** Type, words, picture, start / end, where, in, out, size, colour, drift, delete.
  Every change is one op, one undoable version.
- **Edit index.** It lists graphics under their own filter.
- **Program viewer.** It draws every item at the playhead, posed per frame by
  `lib/cut/graphics.pose`, the export's own eased moves and fades. The fonts are approximated;
  the export is exact.
- **The editor agent.** It gets `set_graphic` / `delete_graphic` in its catalogue (it is derived
  from `ops.OPS`), and its read of the timeline lists graphics. So "add a headline at 2s" is a
  proposal it can make.

## The walk

1. In the editor, on a project with the Gygler kit, the four "Add a graphic" buttons made G1-G4
   through the real ops.
2. The Inspector edited each one: text, and position for the headline.
3. The preview drew them in the kit's look.
4. The MP4 export (local ffmpeg, free) came out 4.0s with all four: "BOOK" faint and drifting,
   the orange headline in Arial Rounded, the talent card sliding in from the right with
   "Alex R. · Line cook" under it, and the orange "$24 / hr" pill, each fading in and out.

## Not built yet

- **Per-letter and per-word kinetic type**, and scale or "pop" moves. Each item moves as one
  layer.
- **Graphics on the connector.** The connector's tools do not add graphics, and no MCP file was
  touched.
- **Graphics in OTIO / NLE export.**
- **A cut made by Assemble stays bare.** It gets no graphics automatically; the editor agent can
  propose them.
