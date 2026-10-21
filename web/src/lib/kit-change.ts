/* A brand kit changed from the chat (2026-10-21, src/kit_changes.py).

   Vesper's propose_kit_change comes back as a proposal whose args carry the
   kit, the changes and a `diff`: one row per field, before and after. The
   card draws the rows and only its Apply changes the kit (POST
   /creative-guide/act); Undo PATCHes back the spec Apply replaced.

   This is the page's half, with nothing imported, so
   tests/kit-change.test.mjs runs it as it is. */

export const KIT_TOOL = "propose_kit_change";
export const isKitTool = (tool?: string | null) => tool === KIT_TOOL;

export type KitDiffRow = { field: string; label: string; kind: "colour" | "text"; before: string; after: string };

const HEX = /^#[0-9A-Fa-f]{6}$/;

/** the rows a proposal's args carry, each checked for its shape; anything
    else is dropped rather than drawn */
export function diffRows(args: Record<string, unknown> | null | undefined): KitDiffRow[] {
  const raw = (args ?? {}).diff;
  if (!Array.isArray(raw)) return [];
  const out: KitDiffRow[] = [];
  for (const r of raw) {
    if (!r || typeof r !== "object") continue;
    const row = r as Record<string, unknown>;
    if (typeof row.field !== "string" || typeof row.label !== "string") continue;
    const kind = row.kind === "colour" ? "colour" : "text";
    const before = typeof row.before === "string" ? row.before : "";
    const after = typeof row.after === "string" ? row.after : "";
    out.push({ field: row.field, label: row.label, kind, before, after });
  }
  return out;
}

/** a colour row's swatch, or null when the side is empty or not a hex */
export const swatch = (value: string) => (HEX.test(value) ? value.toUpperCase() : null);

/** what one side of a row reads as when it is empty */
export const shown = (value: string) => (value.trim() ? value : "(empty)");

/** the kit a proposal names, for the toast and the link to its page */
export function kitOf(args: Record<string, unknown> | null | undefined): { id: number; name: string } | null {
  const id = Number((args ?? {}).kit_id);
  if (!Number.isInteger(id) || id <= 0) return null;
  const name = typeof (args ?? {}).kit_name === "string" ? String((args ?? {}).kit_name) : "the kit";
  return { id, name };
}
