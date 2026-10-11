/* Presets as tested recipes (2026-10-11; step 7 item 3 of
   docs/tasks/task-higgsfield-shape.md).

   A camera preset used to be a line of advice with nothing behind it.
   The server now says, for this account, how many outputs were made with
   each one and how many of those were kept (src/outcomes.py
   `preset_counts`, on GET /api/presets). This is the pure half: the order
   the composer's `/` menu lists them in, and the few words beside each.

   Tested ones lead, best keep rate first; ties go to the one tried more,
   then to the file's own order. Untested ones follow in the file's order
   and say so -- an untested recipe is not a bad one, it is an unknown. */

export type Recipe = { id: string; label: string; how: string; tried?: number | null; kept?: number | null };

const tried = (p: Recipe) => Math.max(0, Number(p.tried) || 0);
const kept = (p: Recipe) => Math.min(tried(p), Math.max(0, Number(p.kept) || 0));

/** Kept over tried, or null when it has never been tried. */
export const keepRate = (p: Recipe): number | null => (tried(p) ? kept(p) / tried(p) : null);

/** The menu's order: tested by keep rate, then untested as the file has them. */
export function rankRecipes<T extends Recipe>(presets: T[]): T[] {
  const at = new Map(presets.map((p, i) => [p.id, i]));
  return [...presets].sort((a, b) => {
    const ra = keepRate(a);
    const rb = keepRate(b);
    if ((ra === null) !== (rb === null)) return ra === null ? 1 : -1;
    if (ra !== null && rb !== null) {
      if (rb !== ra) return rb - ra;
      if (tried(b) !== tried(a)) return tried(b) - tried(a);
    }
    return (at.get(a.id) ?? 0) - (at.get(b.id) ?? 0);
  });
}

/** What the menu says beside a preset: "kept 3 of 5", or "untested". */
export const recipeHint = (p: Recipe): string => (tried(p) ? `kept ${kept(p)} of ${tried(p)}` : "untested");
