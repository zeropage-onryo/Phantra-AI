/* THE EDITOR IS OFF THE UI (2026-11-02, Mike's call): the timeline editor
   stays built and reachable at /studio/cut while he finishes testing it,
   but nothing in the studio's chrome points at it -- not the top bar, not
   the ⌘K palette's pages, new-cut commands or search results, not Vesper's
   "Open in the editor". Flip this to true to bring every one of them back.

   Left on purpose: a built motion ad's "Open in the editor" (ad-step.tsx),
   which is the only place a built ad can be seen, and a finished job's
   result link (activity tray, Renders), which only exists once a cut does. */
export const EDITOR_IN_UI = false;
