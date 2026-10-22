/* The settings area's sections (2026-10-11, docs/tasks/task-settings-page.md):
   ONE list that the left nav, the ⌘K palette and the redirect all read, so
   a section cannot be in the nav and missing from the palette, or the other
   way round.

   A settings AREA, not a settings page: one section on screen at a time,
   each with its own URL, the way Runway and Higgsfield lay theirs out.

   No "@/..." imports and no icons: tests/settings-sections.test.mjs loads
   this file with node. The nav maps each id to its icon. */

export type SectionId = "account" | "plan" | "usage" | "workspace" | "connections" | "preferences";

export type Section = {
  id: SectionId;
  /** the nav's label, and the section's title */
  label: string;
  href: string;
  /** the one line under the section's title */
  description: string;
  /** what the ⌘K palette matches besides the label */
  keywords: string;
};

export const SETTINGS_ROOT = "/studio/settings";

const section = (id: SectionId, label: string, description: string, keywords: string): Section => ({
  id,
  label,
  href: `${SETTINGS_ROOT}/${id}`,
  description,
  keywords,
});

export const SECTIONS: Section[] = [
  section(
    "account",
    "Account",
    "Your name, your email and how you sign in.",
    "settings profile name email password sign in security",
  ),
  section(
    "plan",
    "Plan & credits",
    "Your balance, your plan and where to add credits.",
    "settings billing balance subscription top up buy stripe invoices",
  ),
  section(
    "usage",
    "Usage",
    "Where your credits went: every hold, charge and grant.",
    "settings history ledger spend spent credits charges",
  ),
  section(
    "workspace",
    "Workspace",
    "The workspaces you belong to and who is in this one.",
    "settings team members accounts switch workspace",
  ),
  section(
    "connections",
    "Connections",
    "Your social accounts, and your studio from Claude, ChatGPT and other MCP apps.",
    "settings social accounts instagram discord tiktok youtube post publish mcp connect connector claude chatgpt claude desktop server address integrations",
  ),
  section(
    "preferences",
    "Preferences",
    "The assistant, your generation defaults, notifications and keys.",
    "settings assistant mascot defaults model notifications keyboard shortcuts",
  ),
];

/** One ⌘K command per section: "Settings · Plan & credits". The title
 *  starts with "Settings" so typing that word lists all six. */
export const SECTION_COMMANDS: { id: SectionId; title: string; href: string; keywords: string }[] = SECTIONS.map(
  (s) => ({ id: s.id, title: `Settings · ${s.label}`, href: s.href, keywords: s.keywords }),
);

/** where a bare /studio/settings lands */
export const SETTINGS_HOME = SECTIONS[0].href;

const byId = new Map(SECTIONS.map((s) => [s.id as string, s]));

/** the section a pathname is showing, or null when it is none of them */
export function sectionOf(pathname: string | null | undefined): Section | null {
  const path = (pathname ?? "").split(/[?#]/)[0].replace(/\/+$/, "");
  if (!path.startsWith(`${SETTINGS_ROOT}/`)) return null;
  const id = path.slice(SETTINGS_ROOT.length + 1).split("/")[0];
  return byId.get(id) ?? null;
}

/** The old one-page URL and anything unknown under it: the named section
 *  when there is one, the first section otherwise. */
export function settingsTarget(section?: string | null): string {
  return byId.get((section ?? "").trim().toLowerCase())?.href ?? SETTINGS_HOME;
}
