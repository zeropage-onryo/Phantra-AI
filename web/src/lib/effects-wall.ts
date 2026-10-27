/* The Effects page's wall (2026-10-26, Mike's pick "R2·04",
   docs/tasks/task-effects-page-r2.md): every effect the table runs as a
   tile, with the TEMPLATED rows split into one tile per template.

   Kling's 91 templates, PixVerse's 154 and the named camera moves used to be
   three cards with a dropdown behind each. Here each template is its own
   tile, read off the table's own option values (GET /api/effects lists
   every legal value), so nothing is a second table: a tile is just
   "this row, with this option already chosen". Running one sends exactly
   what the card used to: the row's id and the option.

   A tile shows on the wall only when the showcase manifest has an example
   for it (Mike, 2026-10-25: a tile stays hidden until he keeps its showcase
   render). A search reaches every tile, with or without one.

   Pure and import-free (type imports only): tests/effects-wall.test.mjs runs
   it with node. */
import type { Effect } from "./effects";
import type { ShowcaseItem, ShowcaseManifest } from "./showcase";

/** The option a templated row's tiles fix, by row id. */
export const PRESET_OPTION: Record<string, string> = {
  "kling-effect": "effect_scene",
  "pixverse-effect": "effect",
  "camera-move": "camera_movement",
  // the Halloween costumes (2026-10-27): one tile per costume
  "costume-preview": "costume",
};

/** The showcase keys the overnight slate wrote before templates had tiles. */
const SHOWCASE_ALIASES: Record<string, string> = {
  "kling-effect:bullet_time_360": "effect.bullet_time",
  "camera-move:camera_rotation": "effect.product_orbit",
};
const LOOK_IDS = ["film_grade", "noir", "flash_2000s", "crash_zoom", "vertical_ready", "make_it_pro",
  "title_sequence", "the_ward", "haunted_manor", "found_tape"];
const EFFECT_KEYS: Record<string, string> = {
  upscale: "effect.4k_smooth",
  "add-sound": "effect.sound_pass",
  reframe: "effect.reframe",
};

/** What a plain row's tile is called: what it does, in a customer's words.
 *  The model that runs it is the table's label, said in the panel. */
const ROW_NAMES: Record<string, string> = {
  "nano-banana-edit": "Edit With Words",
  "flux-kontext-pro": "Precise Edit",
  "seedream-edit": "Combine Images",
  "remove-background": "Remove Background",
  upscale: "Upscale",
  "add-sound": "Add Sound",
  reframe: "Reframe",
  "reframe-hq": "Reframe HQ",
  "remove-video-background": "Cut Out",
  "remove-video-background-pro": "Replace Background",
};
/** The camera moves' names, where the table's value is not the move a person would say. */
const MOVE_NAMES: Record<string, string> = { camera_rotation: "Product Orbit" };

export type TabId = "all" | "halloween" | "new" | "free" | "transform" | "product" | "dance" | "camera" | "holiday" | "tools";
export const TABS: { id: TabId; label: string }[] = [
  { id: "all", label: "All" },
  { id: "halloween", label: "Halloween" },
  { id: "new", label: "New" },
  { id: "free", label: "Free" },
  { id: "transform", label: "Transform" },
  { id: "product", label: "Product" },
  { id: "dance", label: "Dance" },
  { id: "camera", label: "Camera" },
  { id: "holiday", label: "Holiday" },
  { id: "tools", label: "Tools" },
];

/* ── the Halloween season (2026-10-27, Mike: the neon sign, design 08) ──
   One switch for the page's neon sign, the Halloween tab and the rail's
   neon tag: on until the end of HALLOWEEN_UNTIL's eve, then gone with no
   deploy. The tab holds the Halloween templates (read off their names) and
   the rows named below: the four free looks and the recipes. */
export const HALLOWEEN_UNTIL = "2026-11-03T00:00:00-05:00";
export const halloweenOn = (now: Date = new Date()) => now.getTime() < Date.parse(HALLOWEEN_UNTIL);
const HALLOWEEN = /halloween|pumpkin|witch|vampire|zombie|mummy|demon|voodoo|werewolf|skeletal|devil[ _]smile/i;
export const HALLOWEEN_IDS = new Set([
  "title_sequence", "the_ward", "haunted_manor", "found_tape",
  "coven", "sideshow", "seance", "the_hotel", "costume_try_on",
  // the costume preview's twelve tiles (src/costumes.py)
  "costume-preview",
]);

export type Tile = {
  /** the row id, or <row id>:<template value> */
  key: string;
  effect: Effect;
  /** the option this tile fixes, or null for a row that is one tile */
  preset: { name: string; value: string } | null;
  /** what the tile says */
  name: string;
  tabs: TabId[];
  free: boolean;
  isNew: boolean;
  /** the example, or null when there is none yet */
  media: ShowcaseItem | null;
};

export type PageContent = { featured: string[]; new: string[] };
export const EMPTY_CONTENT: PageContent = { featured: [], new: [] };

/** the content file as read, held to its shape */
export function readContent(raw: unknown): PageContent {
  if (!raw || typeof raw !== "object") return EMPTY_CONTENT;
  const r = raw as Record<string, unknown>;
  const list = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);
  return { featured: list(r.featured), new: list(r.new) };
}

/** "bullet_time_360" -> "Bullet Time 360"; a value already written for a
 *  person ("Liquid Metal", "Who's Arrested?") is left as it is. */
export function titleOf(value: string): string {
  const v = String(value ?? "").trim();
  if (!/^[a-z0-9_]+$/.test(v)) return v;
  return v
    .split("_")
    .filter(Boolean)
    .map((w) => (/^\d/.test(w) ? w : w[0].toUpperCase() + w.slice(1)))
    .join(" ");
}

/** The manifest key for a tile. */
export function tileShowcaseKey(key: string): string {
  if (SHOWCASE_ALIASES[key]) return SHOWCASE_ALIASES[key];
  const [id, value] = splitKey(key);
  if (value !== null) return `template.${id}.${value}`;
  if (LOOK_IDS.includes(id)) return `look.${id}`;
  return EFFECT_KEYS[id] ?? `effect.${id}`;
}

function splitKey(key: string): [string, string | null] {
  const at = key.indexOf(":");
  return at < 0 ? [key, null] : [key.slice(0, at), key.slice(at + 1)];
}

/* What a template is, read off its name. Advice for a filter, never a gate:
   a template that matches nothing is a Transform. */
const DANCE = /danc|moonwalk|poping|popping|swing|swish|skate|vroom|subject[ _]?3|daoma|bouncy|strikout|ghost[ _]step|running[ _]man|groove|twerk|pole/i;
const HOLIDAY = /christmas|xmas|santa|snow|halloween|pumpkin|witch|vampire|zombie|mummy|demon|voodoo|new[ _]year|lion[ _]dance|red[ _]packet|prosperity|fortune|lucky|lantern|dumpling|reindeer|grinch|stocking|birthday|cheers|horse|ornament|toast|bouquet|gift/i;
const PRODUCT = /product|\bad\b|_ad\b| AD\b|billboard|package|supermarket|macaron|poster|truck|mechanical|giant|dishes|shoal|parachute|figurine|unbox|mint[ _]?in[ _]?box/;

function templateTabs(effectId: string, value: string): TabId[] {
  if (effectId === "camera-move") return ["camera"];
  if (effectId === "costume-preview") return ["holiday"];
  const tabs: TabId[] = [];
  if (DANCE.test(value)) tabs.push("dance");
  if (HOLIDAY.test(value)) tabs.push("holiday");
  if (PRODUCT.test(value) || /product/i.test(value)) tabs.push("product");
  return tabs.length ? tabs : ["transform"];
}

function rowTabs(e: Effect): TabId[] {
  if (e.free) return ["free"];
  if (e.category === "camera") return ["camera"];
  // a recipe says where it belongs; a product one is a Product tile
  if (e.recipe && (e.tags ?? []).includes("product")) return ["product"];
  if (e.category === "video_effect") return ["transform"];
  return ["tools"];
}

/** Every tile, in the table's order, templates in the table's order. */
export function tilesFrom(effects: Effect[], manifest: ShowcaseManifest | null, content: PageContent = EMPTY_CONTENT): Tile[] {
  const items = manifest?.items ?? {};
  const fresh = new Set(content.new);
  const out: Tile[] = [];
  const add = (key: string, effect: Effect, preset: Tile["preset"], name: string, tabs: TabId[]) => {
    const isNew = fresh.has(key);
    const free = !!effect.free;
    const all = [...tabs];
    if ((HALLOWEEN_IDS.has(effect.id) || (preset && HALLOWEEN.test(preset.value))) && !all.includes("halloween")) all.push("halloween");
    if (isNew && !all.includes("new")) all.push("new");
    if (free && !all.includes("free")) all.push("free");
    out.push({ key, effect, preset, name, tabs: all, free, isNew, media: items[tileShowcaseKey(key)] ?? null });
  };
  for (const e of effects) {
    const option = PRESET_OPTION[e.id];
    const values = option ? (e.options?.[option]?.values ?? []) : [];
    if (option && values.length) {
      for (const v of values) {
        const value = String(v);
        const name = (e.id === "camera-move" && MOVE_NAMES[value]) || titleOf(value);
        add(`${e.id}:${value}`, e, { name: option, value }, name, templateTabs(e.id, value));
      }
    } else {
      add(e.id, e, null, ROW_NAMES[e.id] ?? e.label, rowTabs(e));
    }
  }
  return out;
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/** The wall for a tab and a search. Browsing shows only tiles with an
 *  example; a search looks through every tile, and lists the ones with an
 *  example first. The Halloween tab is opened on purpose from the neon
 *  sign, so it answers like a search: every Halloween tile, examples first. */
export function wallFor(tiles: Tile[], tab: TabId, query: string): Tile[] {
  const q = norm(query);
  const inTab = (t: Tile) => tab === "all" || t.tabs.includes(tab);
  if (!q && tab === "halloween") {
    const hit = tiles.filter(inTab);
    return [...hit.filter((t) => t.media), ...hit.filter((t) => !t.media)];
  }
  if (!q) return tiles.filter((t) => t.media && inTab(t));
  const hit = tiles.filter((t) => inTab(t) && (norm(t.name).includes(q) || norm(t.effect.label).includes(q)));
  return [...hit.filter((t) => t.media), ...hit.filter((t) => !t.media)];
}

/** The tabs worth drawing while browsing: All, and every tab with a tile
 *  that has an example. */
export function tabsShown(tiles: Tile[], now: Date = new Date()): typeof TABS {
  const have = new Set(tiles.filter((t) => t.media).flatMap((t) => t.tabs));
  const spooky = halloweenOn(now) && tiles.some((t) => t.tabs.includes("halloween"));
  return TABS.filter((t) => t.id === "all" || (t.id === "halloween" ? spooky : have.has(t.id)));
}

/** The featured strip: the content file's picks that have an example, in
 *  its order, at most three. */
export function featured(tiles: Tile[], content: PageContent, max = 3): Tile[] {
  const byKey = new Map(tiles.map((t) => [t.key, t]));
  const out: Tile[] = [];
  for (const key of content.featured) {
    const t = byKey.get(key);
    if (t?.media && !out.includes(t)) out.push(t);
    if (out.length >= max) break;
  }
  return out;
}

/** How many tiles are waiting on an example: said under the wall. */
export const waiting = (tiles: Tile[]) => tiles.filter((t) => !t.media).length;

/** The options a tile leaves for the person: everything but the one it fixes. */
export function openOptions(tile: Tile): [string, Effect["options"][string]][] {
  return Object.entries(tile.effect.options ?? {}).filter(([name, o]) => name !== tile.preset?.name && !(o.values.length === 1 && o.default !== null));
}

/** What the source slot is called for this effect. */
export function slotLabel(effect: Pick<Effect, "takes" | "category">, presetName?: string | null): string {
  if (effect.takes === "video") return "Clip";
  if (presetName === "camera_movement" || effect.category === "image_edit") return "Image";
  return "Photo";
}
