/* The showcase manifest (web/public/showcase/manifest.json, 2026-10-22,
   docs/tasks/task-effects-tab.md): the before / after media the Effects
   tab's cards play, and the stills the Create page's sections show. The
   file is filled by the showcase slate (group 12 of the overnight task);
   this reads it, and a card whose key is not in it, or whose entry is
   malformed, draws the placeholder instead of breaking.

   Version 1, agreed between the streams: {"version": 1, "items": {<key>:
   {kind, before, after, poster, aspect, credits, model, gen_id}}}. The
   KEYS are fixed (showcaseKey); the slate only replaces URLs (and `kind`,
   once a placeholder still becomes a clip). `credits` is what the example
   cost to make, a record for the log -- NEVER drawn on a card.

   Pure and import-free on purpose: tests/effects-tab.test.mjs runs this
   file as it is; the fetch is a parameter. */

export const SHOWCASE_URL = "/showcase/manifest.json";
export const PLACEHOLDER_URL = "/showcase/placeholder/still.svg";

export type ShowcaseAspect = "16:9" | "9:16" | "4:5" | "1:1";
export type ShowcaseItem = {
  kind: "clip" | "still";
  /** the untouched source; null when the example has no before (a still
   *  made from a prompt) */
  before: string | null;
  after: string;
  /** a frame of `after`, for a clip's resting state */
  poster: string | null;
  aspect: ShowcaseAspect;
  /** what the example cost to make: the slate's log, never a card's label */
  credits: number;
  model: string;
  gen_id: string | null;
};
export type ShowcaseManifest = { version: 1; items: Record<string, ShowcaseItem> };

export const PLACEHOLDER: ShowcaseItem = {
  kind: "still",
  before: null,
  after: PLACEHOLDER_URL,
  poster: null,
  aspect: "16:9",
  credits: 0,
  model: "placeholder",
  gen_id: null,
};
export const EMPTY: ShowcaseManifest = { version: 1, items: {} };

/** The free looks (group 2 of the overnight task) are keyed `look.<id>`. */
export const LOOK_IDS = ["film_grade", "noir", "flash_2000s", "crash_zoom", "vertical_ready", "make_it_pro"] as const;
/** The priced effects the slate renders an example for, by the table's id. */
const EFFECT_KEYS: Record<string, string> = {
  "kling-effect": "effect.bullet_time",
  "camera-move": "effect.product_orbit",
  upscale: "effect.4k_smooth",
  "add-sound": "effect.sound_pass",
  reframe: "effect.reframe",
};

/** The manifest key for an effect: `look.<id>` for a free look, the slate's
 *  name for an effect it renders, `effect.<id>` for everything else. */
export function showcaseKey(effectId: string): string {
  const id = (effectId ?? "").trim();
  if ((LOOK_IDS as readonly string[]).includes(id)) return `look.${id}`;
  return EFFECT_KEYS[id] ?? `effect.${id}`;
}

const ASPECTS: readonly string[] = ["16:9", "9:16", "4:5", "1:1"];

/** One entry, whole, or null when it is not one (no `after`, an unknown
 *  kind): a half-written entry draws the placeholder, never a broken tile. */
export function readItem(raw: unknown): ShowcaseItem | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.after !== "string" || !r.after.trim()) return null;
  if (r.kind !== "clip" && r.kind !== "still") return null;
  const str = (v: unknown) => (typeof v === "string" && v.trim() ? v : null);
  return {
    kind: r.kind,
    before: str(r.before),
    after: r.after,
    poster: str(r.poster),
    aspect: (ASPECTS.includes(String(r.aspect)) ? r.aspect : "16:9") as ShowcaseAspect,
    credits: typeof r.credits === "number" && Number.isFinite(r.credits) ? r.credits : 0,
    model: str(r.model) ?? "",
    gen_id: str(r.gen_id),
  };
}

/** The file as it is read, held to version 1: anything else is empty, and
 *  every card then shows the placeholder. */
export function parseManifest(raw: unknown): ShowcaseManifest {
  if (!raw || typeof raw !== "object") return EMPTY;
  const r = raw as { version?: unknown; items?: unknown };
  if (r.version !== 1 || !r.items || typeof r.items !== "object") return EMPTY;
  const items: Record<string, ShowcaseItem> = {};
  for (const [key, value] of Object.entries(r.items as Record<string, unknown>)) {
    const item = readItem(value);
    if (item) items[key] = item;
  }
  return { version: 1, items };
}

/** The example for an effect: its entry, else the placeholder. */
export function itemFor(manifest: ShowcaseManifest | null | undefined, effectId: string): ShowcaseItem {
  return manifest?.items[showcaseKey(effectId)] ?? PLACEHOLDER;
}

export const isPlaceholder = (item: ShowcaseItem) => item.after === PLACEHOLDER_URL;

/** What a card shows at rest: the before, else the poster, else the after. */
export const restingFrame = (item: ShowcaseItem) => item.before ?? item.poster ?? item.after;

/** "16:9" -> "16 / 9", for CSS aspect-ratio. */
export const cssAspect = (aspect: ShowcaseAspect) => aspect.replace(":", " / ");

type Fetcher = (url: string) => Promise<{ ok: boolean; json(): Promise<unknown> }>;
let loading: Promise<ShowcaseManifest> | null = null;

/** The manifest, read ONCE per page load and shared by every card; a
 *  missing or unreadable file is the empty manifest, never an error. */
export function loadShowcase(fetcher?: Fetcher): Promise<ShowcaseManifest> {
  if (loading) return loading;
  const get = fetcher ?? (typeof fetch === "function" ? (u: string) => fetch(u, { cache: "no-store" }) : null);
  if (!get) return Promise.resolve(EMPTY);
  loading = get(SHOWCASE_URL)
    .then((res) => (res.ok ? res.json() : null))
    .then(parseManifest)
    .catch(() => EMPTY);
  return loading;
}

/** tests only: forget the shared read */
export function resetShowcase() {
  loading = null;
}
