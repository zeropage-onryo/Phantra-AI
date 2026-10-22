# A motion ad from a brief: the AI places the graphics

Status: **BUILT 2026-10-20**, on Mike's "build the AI does the placing part".

## What it is

The Gygler reference is a motion-graphics ad, not footage: big type over flat brand colours, one
huge faint word behind each line, product screens on cards, a label now and then, and the logo at
the end. The editor's graphics track (`docs/tasks/task-motion-graphics.md`) can draw all of that,
but only by hand. **Make a motion ad** (the Edit page, beside "Start from scratch") does the
placing:

1. **The person** writes a brief, picks a project (its brand kit is the look), a length (10-60s), a
   shape, and up to 8 product screenshots for cards.
2. **The brain writes the script** (`src/cut/motion_ad.write_beats`, `prompts/motion_ad_prompt.txt`).
   It is ONE structured Gemini call, stage `motion_ad`, free on a plan and behind the Create gate.
   It returns a title and 3-15 beats, each with:
   - a headline
   - a big word
   - which screenshot it shows, and its caption
   - a label
   - which brand colour it sits on (background or primary)
   - its seconds
3. **Code checks it** (`clean`). Every fix is a warning, never a refusal:
   - the beats are fitted to the length
   - over-long text is shortened
   - a screenshot that isn't attached is dropped
   - empty beats are left out
   - **any number on screen that the brief and the brand never give is flagged** ("check it is
     true")
4. **Code places it** (`layout`, pure):
   - **V1:** one flat-colour still per beat. `backgrounds` draws them with Pillow and files them in
     the bin, content-addressed.
   - **Graphics tracks:** G1 the big words, G2 the headlines (to the left when a card is on the
     right), G3 the cards (sliding in), G4 the labels, each timed inside its beat.
   - **Type colour:** always reads on its background (`ink_on`: the brand primary where it reads,
     else the brand colour that stands out most). A label on a primary beat gets the other colour
     as its pill.
5. **It is saved as a new cut** (`make`), filed under the studio project with the new
   `cut_projects.studio_project_id`, so the kit's captions and end card reach its export.
   `brand_kits.for_cut` is the one resolver: the scene's project, else this. Version 1 is
   authored `agent`, "motion ad: N beats".

Nothing renders and no credits are spent. The person opens the cut in the editor to keep, change
or throw away.

## Routes

`POST /api/cut/motion-ad` `{brief, project_id?, seconds, aspect, cards: [handles]}` starts a job,
which ends with `{cut_id, title, beats, warnings, brand_kit}`. It refuses:
- someone else's project (404)
- a card that isn't one of the caller's stills (400 `not_a_still`)
- a length off 8-60s (422)
- an account the Create gate refuses (402, before any job)

## The walk

On a throwaway schema, with the bucket and every renderer key blanked:
1. **Stubbed brain:** the dialog made a 21.9-second "Meet Gygler" cut: six beats, the talent card
   twice, two labels, the end card at export.
2. **The real brain**, once, on Mike's word (one Gemini text call on the local key): it wrote a
   clean five-beat script with no fixes needed, which was exported and looked at.
3. **What the real call showed:** it **invented "4.9 Stars" and "$26 / hr"**. The prompt now
   forbids facts the brief or the brand don't give, and the code flags any number that slips
   through. Not re-run after the fix; the tests cover it.

## Not built

- **Music:** BUILT 2026-10-21 (`docs/tasks/task-music-layer.md`).
- **Generated product screens:** cards show only the person's own stills.
- **Footage beats mixed in:** BUILT 2026-10-21, see "Footage beats" below. A whole final cut
  from #392 under the graphics is still not built.
- **Graphics from the connector:** no MCP change was made.
- **A "regenerate one beat" button:** BUILT 2026-10-21, see "Redo one beat" below.

## Redo one beat (2026-10-21)

**Redo beat N** sits on the editor's Text tab, under Add a graphic
(`web/src/components/cut/redo-beat-card.tsx`, `motion_ad.redo_beat`,
`prompts/motion_ad_beat_prompt.txt`, `POST /api/cut/projects/{id}/motion-ad/beat
{base_id, frame, note}`). It is a job behind the Create gate and is free on a plan.
- **A beat** is the V1 clip under the playhead plus the graphics that START inside it. The card
  shows only when there are some, so it also works on a hand-made cut with graphics.
- **The brain** sees the whole ad beat by beat, with the one to rewrite marked, plus the kit, the
  person's note (optional), the beat's length (kept) and the screenshots the ad already shows. It
  answers one beat. `clean` checks it the way it checks a whole script, and a number that nothing
  gives is flagged with the beat number.
- **Applying it** is ordinary ops, applied in order so that a track it adds has the id the later
  ops name: delete the beat's graphics, add the new ones with `set_graphic`, then `overwrite` the
  flat background if its colour changed. `projects.keep` saves this as ONE version by "agent"
  against `base_id`, and Undo takes it back. A stale `base_id` is a 409 before the model is called.
- **A background is swapped only when it is a flat still**, recognised by its bin row
  (`background-<hex>.png`, `motion_ad.flat_colour`). Every `uploads.save` is its own row, so
  handles alone cannot tell. A footage clip under graphics is never replaced. Found on the walk:
  the first version compared handles, so the swap never happened, and the new type, inked for
  orange, sat invisible on cream.
- After it lands the card refreshes the head AND the bin, so the monitor can draw a new still.

Walked with the brain stubbed on a kitted 4-beat ad: beat 2 became "Hire in an afternoon." with
HIRE behind it, the orange background and cream type. "Rated 4.9" was flagged in the toast.
Undo went back, and a second redo landed as version 3. **No real model call was made.**

## Footage beats (2026-10-21)

The dialog has a **Footage** picker: the 12 newest video clips in the bin (renders and uploads,
`GET /api/cut/media`, which is the bin with no cut open), up to `CLIPS_MAX = 6`. The route measures
each clip (`cut_sources.measure`) and refuses anything that isn't this account's readable video
(400 `not_a_clip`).
- **The brain** gets the clips numbered, with their lengths, and a `clip` field per beat. The
  prompt asks for two or three clip beats, rarely back to back, the opening and the call to action
  kept on a brand colour, and no big word on footage.
- **`clean`** drops a clip number that wasn't attached, and shortens a beat to its clip's length
  if it was longer, after the fit to the ad's length. Each is a warning.
- **`layout`** puts the clip on V1 from its start, picture only (its sound is not laid), for the
  beat's length. The type is white (`ON_FOOTAGE`) with `shadow: true`, a new graphic flag: the
  renderer and the monitor draw the soft shadow they already drew for unbranded type, which kit
  type over footage needs too. `set_graphic` takes `shadow`; the check refuses anything but a
  boolean. No flat still is filed for a footage beat.
- **Redo beat** on a footage beat keeps the clip (it is not a flat still) and lays the new beat
  out as a footage beat: white type, shadow, no big word. The beat prompt marks it "over a video
  clip".

Walked with the brain stubbed. Two uploaded 3s clips were picked in the dialog, and the cut opened
with beats 2 and 4 on them. The first export showed white kit type unreadable over busy footage,
which is where `shadow` came from. The second export (19.1s with the end card) reads cleanly.
**No real model call was made.**
