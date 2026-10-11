/* The keyboard shortcuts the studio has, as a list to READ (Settings →
   Preferences, 2026-10-11). Nothing here binds a key: each row names a
   shortcut that already exists where it says, and the file that handles it,
   so a key that changes there is changed here.

     - everywhere: lib/palette.ts isPaletteKey
     - the Queue and a project's scene list: lib/verdict-keys.ts
     - the editor: components/cut/commands.ts

   `mod` is ⌘ on a Mac and Ctrl elsewhere; the page swaps it in. */

export type Shortcut = { keys: string[]; does: string };
export type ShortcutGroup = { where: string; note?: string; items: Shortcut[] };

export const SHORTCUTS: ShortcutGroup[] = [
  {
    where: "Everywhere",
    items: [{ keys: ["mod", "K"], does: "Search, and every command" }],
  },
  {
    where: "Queue",
    note: "A key never spends on its own: the first A shows the price, the second approves.",
    items: [
      { keys: ["A"], does: "Approve the scene" },
      { keys: ["X"], does: "Reject it" },
      { keys: ["←", "→"], does: "Move between scenes" },
    ],
  },
  {
    where: "A project's scenes",
    items: [
      { keys: ["A"], does: "Pick the open scene" },
      { keys: ["X"], does: "Pass on it" },
      { keys: ["↑", "↓"], does: "Move between scenes" },
    ],
  },
  {
    where: "Editor",
    items: [
      { keys: ["Space"], does: "Play or pause" },
      { keys: ["J", "K", "L"], does: "Play back, stop, play forward (again to go faster)" },
      { keys: ["←", "→"], does: "One frame; with Shift, one second" },
      { keys: ["↑", "↓"], does: "The cut before, the cut after" },
      { keys: ["I", "O"], does: "Mark in and out on the source clip" },
      { keys: ["F9"], does: "Insert the marked range at the playhead (also ,)" },
      { keys: ["F10"], does: "Overwrite with it (also .)" },
      { keys: ["Shift", "F12"], does: "Append it to the end" },
      { keys: ["B"], does: "Split at the playhead" },
      { keys: ["M"], does: "Add a marker" },
      { keys: ["N"], does: "Snapping on or off" },
      { keys: ["mod", "Z"], does: "Undo; with Shift, redo" },
      { keys: ["mod", "E"], does: "Export" },
      { keys: ["Shift", "4 / 7 / 6"], does: "The Edit, Audio and Color pages" },
    ],
  },
];

/** a key as it is printed: ⌘ or Ctrl for `mod` */
export const keyLabel = (key: string, mod: "⌘" | "Ctrl") => (key === "mod" ? mod : key);
