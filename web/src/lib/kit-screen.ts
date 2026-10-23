/* An app screen drawn from the brand kit (2026-10-22, src/kit_screens.py,
   docs/tasks/task-kit-products-and-screens.md Part C). Vesper's make_screen
   comes back as a proposal whose args carry the checked spec, the kit and a
   one-line summary; its card draws the screen (free) and Keep files it in
   the Library, where it can hold a shot as its first reference.

   Pure and import-free: tests/kit-screen.test.mjs runs it as it is. */

export const SCREEN_TOOL = "make_screen";
export const isScreenTool = (tool?: string | null) => tool === SCREEN_TOOL;

export type ScreenArgs = {
  kitId: number;
  kitName: string;
  spec: Record<string, unknown>;
  summary: string;
  warnings: string[];
};

/** The proposal's args as the card reads them, or null when they are not a screen. */
export function screenOf(args: unknown): ScreenArgs | null {
  if (!args || typeof args !== "object") return null;
  const a = args as Record<string, unknown>;
  const kitId = typeof a.kit_id === "number" ? a.kit_id : Number(a.kit_id);
  if (!Number.isInteger(kitId) || kitId <= 0 || !a.spec || typeof a.spec !== "object") return null;
  const warnings = Array.isArray(a.warnings) ? a.warnings.filter((w): w is string => typeof w === "string") : [];
  return {
    kitId,
    kitName: typeof a.kit_name === "string" ? a.kit_name : "the kit",
    spec: a.spec as Record<string, unknown>,
    summary: typeof a.summary === "string" ? a.summary : "app screen",
    warnings,
  };
}

/** "phone screen, 3-row schedule: Staffed" -> "Phone screen · 3-row schedule · Staffed" */
export function screenTitle(summary: string): string {
  const [head, ...rest] = summary.split(": ");
  const parts = head.split(", ");
  const out = [...parts, ...(rest.length ? [rest.join(": ")] : [])].filter(Boolean);
  return out.map((p, i) => (i === 0 ? p.charAt(0).toUpperCase() + p.slice(1) : p)).join(" · ");
}
