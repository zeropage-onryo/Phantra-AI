/* THE EXPLORE / MAKE SWITCH ON A PROJECT (2026-10-11; item 13 of
   docs/tasks/task-studio-agent.md). The page's pure half; node-tested in
   tests/explore.test.mjs.

   A project is in Make unless its switch says Explore (`project.explore`,
   kept on the project's own row). While it explores, a send inside it only
   talks: the SERVER hands the brain no tool that makes, whatever a page
   sends, so nothing here is the rule -- this file is what the page shows
   and what it stops offering.

   - the switch sits on the project row above the box, and is drawn only
     where there is a brain to talk to (without one a send makes directly,
     and "only talks" would be a box that does nothing);
   - in Explore the settings line folds to one caption, the slash menu
     keeps only what attaches something, and the send button says the send
     is free;
   - asked to make while exploring, the brain's turn ends on switch_to_make:
     a card with the way out. Its click flips the project, then the ask is
     sent again and HELD on its card whatever Ask first / Auto says -- a
     click on "Switch to Make" never spends. */

export const SWITCH_TOOL = "switch_to_make";
export const isSwitchTool = (tool: unknown): boolean => tool === SWITCH_TOOL;

/** Is a send in this project one that only talks? */
export function exploring(project: { explore?: boolean | null } | null | undefined, guideReady: boolean): boolean {
  return !!project && project.explore === true && guideReady;
}

/** The two halves of the switch, in the order they are drawn. */
export const SWITCH_SIDES = [
  { id: "explore", label: "Explore", title: "Talk it through. A send makes nothing and spends no credits." },
  { id: "make", label: "Make", title: "A send can make: stills wait for your Approve, a scene is written." },
] as const;
export type SwitchSide = (typeof SWITCH_SIDES)[number]["id"];

/** Beside the switch on the project row. */
export function projectLine(isExploring: boolean, learned: number): string {
  return isExploring ? "a send makes nothing until you switch" : `written against its brief and ${learned} learned`;
}

/** The settings line, folded, while a project explores. */
export const EXPLORE_CAPTION = "Exploring. A send draws nothing and spends no credits.";

/** The send button's title while a project explores. */
export const EXPLORE_SEND_LINE = "Free to send. This project is exploring: nothing is made.";

export function explorePlaceholder(empty: boolean): string {
  return empty ? "Talk it through: the idea, the look, the references…" : "Keep talking it through, or ask for references…";
}

/** The slash commands left while exploring: the ones that attach something.
    The rest set up a make (the output, an effect, a skill, a camera recipe). */
const EXPLORE_COMMANDS = new Set(["ref", "element"]);
export function exploreCommands<T extends { id: string }>(all: T[]): T[] {
  return all.filter((c) => EXPLORE_COMMANDS.has(c.id));
}

/* ---- the card under the brain's answer ---- */

const TITLES: Record<string, string> = {
  still: "Switch to Make to draw this still",
  scene: "Switch to Make to write this scene",
  sheet: "Switch to Make to draw this character sheet",
  effect: "Switch to Make to apply this effect",
  plan: "Switch to Make to run this as a plan",
};
const AFTER: Record<string, string> = {
  still: "The still then waits for your Approve beside its price.",
  scene: "The scene is then written. A clip is only rendered from the scene's own priced button.",
  sheet: "The sheet then waits for your Approve beside its price.",
  effect: "The effect then waits for your Approve beside its price.",
  plan: "The plan then waits for you to start it, each step beside its price.",
};

export const SWITCH_LABEL = "Explore is on for this project";

export function switchTitle(kind: unknown): string {
  return (typeof kind === "string" && TITLES[kind]) || "Switch to Make to make this";
}

/** What the click does, and what it does not: it never spends. */
export function switchNote(kind: unknown): string {
  const after =
    (typeof kind === "string" && AFTER[kind]) || "Anything that costs credits then waits for your Approve beside its price.";
  return `Switching costs nothing. ${after}`;
}

/** The card once it has been answered. */
export function switchState(decided: "done" | "skipped" | undefined): string {
  return decided === "done" ? "Switched to Make" : decided === "skipped" ? "Still exploring" : "";
}

/** The message that asked for the make: the newest thing the person said
    before the card at `at`. It is what gets sent again after the switch. */
export function askBefore<T extends { role: string; content: string }>(turns: T[], at: number): T | null {
  for (let i = Math.min(at, turns.length) - 1; i >= 0; i -= 1) {
    const t = turns[i];
    if (t.role === "user" && t.content.trim()) return t;
  }
  return null;
}
