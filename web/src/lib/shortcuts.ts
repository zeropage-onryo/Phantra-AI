/* The keyboard shortcuts the studio has, as a list to READ (Settings →
   Preferences, 2026-10-11). Nothing here binds a key: each row names a
   shortcut that already exists where it says, and the file that handles it,
   so a key that changes there is changed here.

     - everywhere: lib/palette.ts isPaletteKey
     - the editor: components/cut/commands.ts

   The Queue's and the scene list's A / X verdict keys were listed here
   too. They went with the idea board on 2026-10-11
   (docs/tasks/task-higgsfield-shape.md): a scene is rendered from its own
   Render card, by a click on the priced button.

   `mod` is ⌘ on a Mac and Ctrl elsewhere; the page swaps it in. */

export type Shortcut = { keys: string[]; does: string };
export type ShortcutGroup = { where: string; note?: string; items: Shortcut[] };

export const SHORTCUTS: ShortcutGroup[] = [
  {
    where: "Everywhere",
    items: [{ keys: ["mod", "K"], does: "Search, and every command" }],
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
