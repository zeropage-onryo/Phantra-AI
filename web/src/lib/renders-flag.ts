/* RENDERS IS OFF THE UI (2026-11-03, Mike's call, "for now"): the page
   stays built and answers at /studio/renders, but the studio's chrome does
   not point at it -- not the top bar (#562), not the ⌘K palette's pages,
   not the editor's "Open Renders". Flip this to true to bring the palette
   row and that button back (the top bar is GROUPS in shell.tsx).

   Left on purpose: a draft's "Finish it on Renders" in the Library viewer
   (asset-viewer.tsx), because Renders is the only place a draft is
   finished. */
export const RENDERS_IN_UI = false;
