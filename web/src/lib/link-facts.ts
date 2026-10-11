/* What a pasted page said about its product, as one line on its row of the
   contact sheet (item 9 of docs/tasks/task-studio-agent.md;
   src/linkrefs.py parse_facts is the reader).

   The facts are the server's and are already plain and short. This only
   decides what fits on one line: what the thing IS, never its blurb.

   Pure and import-free: tests/link-facts.test.mjs runs it as it is. */

export type LinkFacts = Record<string, string>;

/* the order they are read in; the description is left for the tooltip */
const ON_THE_LINE = ["name", "brand", "color", "size", "material", "price"];

/** "GHOST ENERGY - ORANGE CREAM · GHOST · Orange · 2.99 USD", or "" */
export function factsLine(facts: LinkFacts | null | undefined): string {
  const f = facts ?? {};
  const seen = new Set<string>();
  const bits: string[] = [];
  for (const key of ON_THE_LINE) {
    const value = (f[key] ?? "").trim();
    // a brand already in the name is not said twice
    const low = value.toLowerCase();
    if (!value || seen.has(low)) continue;
    if (key === "brand" && (f.name ?? "").toLowerCase().includes(low)) continue;
    seen.add(low);
    bits.push(value);
  }
  return bits.join(" · ");
}

/** the page's own blurb, for the line's tooltip; "" when it gave none */
export const factsBlurb = (facts: LinkFacts | null | undefined): string => (facts?.description ?? "").trim();
