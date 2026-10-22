/* Showcase media for the Create page and the Effects tab (2026-10-22,
   docs/tasks/task-overnight-2026-10-22.md groups 3, 4 and 12).

   `web/public/showcase/manifest.json` maps a KEY ("create.hero.split",
   "look.noir") to one before/after pair or still, as media URLs on R2,
   never copied files. Group 12 fills it from its showcase renders; until
   then every key points at the neutral placeholder under
   `public/showcase/placeholder/`. A page asks `showcaseItem(manifest, key)`
   and always gets something drawable: a key the manifest lacks is the
   placeholder too, so a page never waits on a render.

   The manifest is fetched ONCE per page load. No "@/..." imports: the node
   tests load this file as it is. Shared word for word with the Effects
   tab's branch -- keep the shape, keep it small. */

export type Aspect = "16:9" | "9:16" | "4:5" | "1:1";

export type Item = {
  kind: "clip" | "still";
  /** the untouched source, for a before/after pair; null for a still */
  before: string | null;
  /** the result: a clip's URL or the still's */
  after: string;
  /** a clip's poster frame, when there is one */
  poster: string | null;
  aspect: Aspect;
  /** what the showcase render cost, for the log; NEVER drawn on a card */
  credits: number;
  model: string;
  /** the Library row it came from, "gen:<id>", or null */
  gen_id: string | null;
};

export type Manifest = { version: 1; items: Record<string, Item> };

export const MANIFEST_URL = "/showcase/manifest.json";
export const PLACEHOLDER_URL = "/showcase/placeholder/still.svg";

export const PLACEHOLDER: Item = {
  kind: "still",
  before: null,
  after: PLACEHOLDER_URL,
  poster: null,
  aspect: "16:9",
  credits: 0,
  model: "placeholder",
  gen_id: null,
};

export const EMPTY: Manifest = { version: 1, items: {} };

const ASPECTS: Aspect[] = ["16:9", "9:16", "4:5", "1:1"];

/** One manifest item, every field checked; anything off-shape is the placeholder. */
export function parseItem(raw: unknown): Item {
  if (!raw || typeof raw !== "object") return PLACEHOLDER;
  const r = raw as Record<string, unknown>;
  const after = typeof r.after === "string" && r.after ? r.after : PLACEHOLDER.after;
  return {
    kind: r.kind === "clip" ? "clip" : "still",
    before: typeof r.before === "string" && r.before ? r.before : null,
    after,
    poster: typeof r.poster === "string" && r.poster ? r.poster : null,
    aspect: ASPECTS.includes(r.aspect as Aspect) ? (r.aspect as Aspect) : "16:9",
    credits: typeof r.credits === "number" && Number.isFinite(r.credits) ? r.credits : 0,
    model: typeof r.model === "string" ? r.model : "",
    gen_id: typeof r.gen_id === "string" && r.gen_id ? r.gen_id : null,
  };
}

/** The manifest as fetched, or EMPTY when it is not version 1. */
export function parseManifest(raw: unknown): Manifest {
  if (!raw || typeof raw !== "object") return EMPTY;
  const r = raw as Record<string, unknown>;
  if (r.version !== 1 || !r.items || typeof r.items !== "object") return EMPTY;
  const items: Record<string, Item> = {};
  for (const [key, value] of Object.entries(r.items as Record<string, unknown>)) items[key] = parseItem(value);
  return { version: 1, items };
}

/** The item for a key, else the placeholder: a card always has a picture. */
export function showcaseItem(manifest: Manifest | null | undefined, key: string): Item {
  return manifest?.items[key] ?? PLACEHOLDER;
}

export const isPlaceholder = (item: Item) => item.after === PLACEHOLDER_URL;

let loading: Promise<Manifest> | null = null;

/** Fetch the manifest once per page load; a missing or broken one is EMPTY
 *  (every key then draws the placeholder). A failed fetch is not cached,
 *  so the next page can try again. */
export function loadShowcase(): Promise<Manifest> {
  if (!loading) {
    loading = (typeof fetch === "function" ? fetch(MANIFEST_URL, { cache: "no-store" }) : Promise.reject(new Error("no fetch")))
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => parseManifest(body))
      .catch(() => {
        loading = null;
        return EMPTY;
      });
  }
  return loading;
}
