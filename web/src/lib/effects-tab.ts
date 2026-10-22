/* The Effects tab (/studio/effects, 2026-10-22, docs/tasks/task-effects-tab.md):
   the composer's effects table (GET /api/effects, lib/effects.ts) laid out
   as a page -- a drop zone, then before / after cards with a Free or Pro
   badge and two filters. NO credit number is drawn on this page: the price
   is on the card a click opens (effect-step.tsx), the same card the
   composer uses, and its Approve is the only click that spends.

   What is here is the page's arithmetic -- the badge, the filters, the
   source's fit, the deep link to Vesper -- so tests/effects-tab.test.mjs
   can run it with node. Pure and import-free (a type import only). */
import type { Candidate, Effect } from "./effects";

export type Tier = "all" | "free" | "pro";
export type Audience = "all" | "cinematic" | "social" | "product";

export const TIERS: { id: Tier; label: string }[] = [
  { id: "all", label: "All" },
  { id: "free", label: "Free" },
  { id: "pro", label: "Pro" },
];
export const AUDIENCES: { id: Audience; label: string }[] = [
  { id: "all", label: "Everything" },
  { id: "cinematic", label: "Cinematic" },
  { id: "social", label: "Social" },
  { id: "product", label: "Product" },
];

/** the bundle the result's "Make It Pro" opens, when the table has it */
export const MAKE_IT_PRO = "make_it_pro";

type Badged = Pick<Effect, "free" | "tags">;

/** Free when the table says so; everything priced is Pro. */
export const tierOf = (e: Badged): Exclude<Tier, "all"> => (e.free ? "free" : "pro");
export const badgeOf = (e: Badged) => (e.free ? "Free" : "Pro");

/** The cards shown for a pair of filters. An effect with no tags is shown
 *  under every audience: the table's word outranks a filter it never heard
 *  of, and a row is never hidden for being unlabelled. */
export function filterEffects<E extends Badged>(items: E[], tier: Tier, audience: Audience): E[] {
  return items.filter((e) => {
    if (tier !== "all" && tierOf(e) !== tier) return false;
    if (audience === "all") return true;
    const tags = e.tags ?? [];
    return tags.length === 0 || tags.includes(audience);
  });
}

/** how many of each, for the filter chips */
export function tierCounts(items: Badged[]): { free: number; pro: number } {
  let free = 0;
  for (const e of items) if (e.free) free++;
  return { free, pro: items.length - free };
}

/** the bundle, or null when this server's table has none */
export function makeItPro<E extends Pick<Effect, "id">>(items: E[]): E | null {
  return items.find((e) => e.id === MAKE_IT_PRO) ?? null;
}

/** Does the dropped thing fit what this effect takes? */
export const fits = (effect: Pick<Effect, "takes">, source: Pick<Candidate, "kind"> | null) =>
  !!source && (effect.takes === "video" ? source.kind === "clip" : source.kind === "image");

/** A dropped file, by what the page can make of it. */
export function acceptsFile(file: { type?: string | null; name?: string | null }): "clip" | "image" | null {
  const type = (file.type ?? "").toLowerCase();
  const name = (file.name ?? "").toLowerCase();
  if (type.startsWith("video/") || /\.(mp4|mov|webm|m4v)$/.test(name)) return "clip";
  if (type.startsWith("image/") || /\.(jpe?g|png|webp|gif|heic)$/.test(name)) return "image";
  return null;
}

/** The line over the drop zone: what is loaded, or what to do. */
export function sourceLine(source: Candidate | null): string {
  if (!source) return "Drop a clip or a still here, or pick one from your Library. It becomes the source for every card.";
  return source.kind === "clip" ? `A clip is loaded (${source.from}). Every card works on it.` : `A still is loaded (${source.from}). Every card works on it.`;
}

/** The render's number inside `gen:<id>`, or null. */
const genId = (ref: string | null | undefined): number | null => {
  const m = /^gen:(\d+)$/.exec(ref ?? "");
  return m ? Number(m[1]) : null;
};

/** "Turn this into a full piece with Vesper": Create, with the result
 *  attached (`?attach=generated-<id>`, the Library's own hand-off) and a
 *  first line in the box that names it, so the brain knows what to build
 *  on. null for a result that has no render id. */
export function vesperHref(assetRef: string | null | undefined, label: string): string | null {
  const id = genId(assetRef);
  if (id === null) return null;
  const spark = `Turn this ${label ? `${label} result` : "result"} (gen:${id}) into a full piece`;
  return `/studio?attach=generated-${id}&spark=${encodeURIComponent(spark)}`;
}
