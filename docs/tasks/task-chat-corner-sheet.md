# Task: the chat page's corner sheet (2026-10-23)

**Mike's pick:** on the "Phantra Chat Panel Options" design canvas he chose direction C (the work
on stage, the chat pulls up), then from its variations **C2d** for desktop (a tall chat sheet
rising from the bottom-left corner, the stage showing the shots large, prices on the cards in the
chat) and **C2f** for phones (the same sheet from the bottom edge, above the tab bar, a strip of
shots over it).

## What changed

Only the chat page with `vesper_v2` on (`/studio/chat`; the home and every other page are as
they were):

- `create-view.tsx`: `.stack` becomes the sheet (`zc-sheet`) with a head (`Chat`, the project's
  title, a Lower button). Lowered, it is one tab carrying Vesper's last line (`lastSaid`); the
  box stays mounted under it, so a draft and a wait survive the fold. The auto-scroll that lifts
  the newest turn clear of the box scrolls the sheet's `.zc-stream`, not the window.
- The autonomy dial is drawn ONCE, in the box's settings line (the storyboard's head copy is
  gone: the screenshot showed it twice).
- `lib/storyboard.ts`: a board carries the scene's `frame`, and `aspectOf` turns "9:16" into a CSS
  aspect ratio, so the stage draws shots in their own shape.
- "10ss": a scene's duration can arrive as the string "10s"; `asSeconds` (create-view) and
  `madeMeta` (lib/composer) no longer add a second "s".
- `vesper-v2.css`: the sheet. Over 1100px it is a sticky column (`top: 92px`, the header plus the
  hero's padding); lowered, the stage takes the full width and the tab rests on its corner. At
  1100px and under it rises from the bottom (sticky; fixed above the tab bar at 720px and under),
  the stage is a strip of shots, and the resting creature is hidden while the sheet is up (it
  would sit on the send button).

Nothing here spends: no new button prices or approves anything. The Render card, the plan's
steps and every other priced card stay in the thread, as before.

## As built

- typecheck, `node --test tests/*.test.mjs` (324 pass), eslint (no errors), `npm run build`.
- Verified in `next dev` with every `/api` route mocked by Playwright (no API, any approve / run /
  guide POST refused by the mock; none was made) at 1440x900, 1000x800 and 390x844, open and
  lowered: no horizontal overflow, nothing clipped inside the sheet, the box at the sheet's foot
  in view, the lowered tab on the bottom edge. Screens: `docs/qa/screens-2026-10-23/chat-sheet-*.png`.
- Not verified: the real API and a real account's thread, a project's dock row inside the sheet,
  and a long conversation's scroll against live job updates.

## Approve buttons only, and the chat clears after a render (2026-10-23, later)

Mike: "i just want approve buttons, when we render the seperate clips ffmeg assembles one video",
and "the conversation doesnt clear after we render" (he picked "keep only the final video").

- `RenderCard approveOnly` (the chat turn's card): only `APPROVE N KEYFRAMES · <price>` and
  `Approve · <model> · N shots · <price>`, plus why a scene cannot render yet. The model popover,
  draft toggle, one-shot keyframe buttons and the long notes stay on the full card (the
  storyboard's Redo and the workspace open it); the model is picked on the box's settings line.
- The join was already there: the last shot landing joins the shots into one MP4 (the editor's
  Assemble, ffmpeg, free) and files it as "Final cut".
- When that join finishes, the thread is cut to the one turn carrying the final cut
  (`final-cut.keepOnlyCut`); a one-shot scene clears the same way when its clip lands. Through
  `setTurnsRaw`, so the shrink never moves the address. Nothing is deleted from the Library.
- Checked: typecheck, node tests (325, one new), eslint, and the card in the mocked dev server.
  Not checked live: a real render ending, the join and the clear in order.
