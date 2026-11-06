/* The public effects pages (2026-11-05, docs/tasks/task-public-effects-pages.md):
   phantra.ai/effects and phantra.ai/effects/<slug>, the signed-out side of
   the studio's Effects wall.

   NOTHING here is a second list. The tiles are the wall's own
   (lib/effects-wall.ts `tilesFrom`, over the committed effects catalogue and
   the showcase manifest), and a tile gets a public page exactly when it has a
   kept showcase example -- the wall's own rule for being shown. Keeping a
   showcase render is what publishes an effect; the title, description,
   canonical, video markup, breadcrumbs, sitemap entry and related links all
   follow from this file.

   Pure and import-free (type imports only): tests/public-effects.test.mjs
   runs it with node. */
import type { Tile } from "./effects-wall";
import type { ShowcaseItem } from "./showcase";

export type EffectGroup = "Transform" | "Free looks" | "Camera and product" | "Finishing tools" | "Halloween";
export const GROUP_ORDER: EffectGroup[] = ["Transform", "Free looks", "Camera and product", "Finishing tools", "Halloween"];
export const GROUP_LINES: Record<EffectGroup, string> = {
  Transform: "One photo of a person in, a short clip of something impossible out.",
  "Free looks": "A finished look on a clip you already have. These cost nothing.",
  "Camera and product": "Camera moves and product shots made from one still.",
  "Finishing tools": "Sound, shape and sharpness for a clip you already like.",
  Halloween: "Costumes and horror looks. Here all year.",
};

/** The date the showcase examples went up: VideoObject requires an
 *  uploadDate, and the manifest keeps none per entry. */
export const SHOWCASE_PUBLISHED = "2026-10-26";

export type PublicEffect = {
  slug: string;
  /** the wall tile's key: what "Try it" opens in the studio */
  key: string;
  name: string;
  /** one or two sentences: the meta description and the page's dek */
  description: string;
  group: EffectGroup;
  media: ShowcaseItem;
  takes: "image" | "video";
  output: "image" | "video";
  free: boolean;
  /** credits at its defaults; null when the clip's length decides */
  credits: number | null;
};

/** "Bullet Time 360" -> "bullet-time-360"; "2000s Flash" -> "2000s-flash". */
export function slugOf(name: string): string {
  return String(name ?? "")
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function groupOf(t: Tile): EffectGroup {
  if (t.tabs.includes("halloween")) return "Halloween";
  if (t.free) return "Free looks";
  if (t.tabs.includes("camera") || t.tabs.includes("product")) return "Camera and product";
  if (t.tabs.includes("tools")) return "Finishing tools";
  return "Transform";
}

/** A template tile's own sentence: the row's blurb describes all 98 (or 154)
 *  templates, which is no description of this one. */
function describe(t: Tile): string {
  const row = t.effect;
  if (t.preset) {
    if (row.id === "costume-preview") return `See yourself as a ${t.name.toLowerCase()} on your own photo, your face kept. One photo in, one picture out.`;
    if (row.id === "camera-move") return `${t.name}: a camera move made from one still. Add a photo, get a short clip with the move already in it.`;
    return `${t.name}: a one-click animated effect. Add one photo and get a short video with the effect applied.`;
  }
  const blurb = (row.blurb || row.label).trim();
  return /[.!?]$/.test(blurb) ? blurb : `${blurb}.`;
}

/** Every tile with a kept example, as a public page, in the wall's order.
 *  Slugs are unique: a second tile with the same name takes its row's id. */
export function publicEffects(tiles: Tile[]): PublicEffect[] {
  const out: PublicEffect[] = [];
  const taken = new Set<string>();
  for (const t of tiles) {
    if (!t.media) continue;
    let slug = slugOf(t.name) || slugOf(t.key);
    if (taken.has(slug)) slug = `${slug}-${slugOf(t.effect.id)}`;
    if (!slug || taken.has(slug)) continue;
    taken.add(slug);
    out.push({
      slug,
      key: t.key,
      name: t.name,
      description: describe(t),
      group: groupOf(t),
      media: t.media,
      takes: t.effect.takes,
      output: t.effect.output,
      free: t.free,
      credits: t.free ? 0 : t.effect.credits,
    });
  }
  return out;
}

/** The groups in page order, each with its effects; empty groups left out. */
export function grouped(list: PublicEffect[]): { group: EffectGroup; line: string; effects: PublicEffect[] }[] {
  return GROUP_ORDER.map((group) => ({ group, line: GROUP_LINES[group], effects: list.filter((e) => e.group === group) })).filter(
    (g) => g.effects.length > 0,
  );
}

/** The effects a page links to: its own group first, then the rest, in
 *  order, never itself. These links are what keep every page reachable. */
export function related(list: PublicEffect[], slug: string, n = 4): PublicEffect[] {
  const self = list.find((e) => e.slug === slug);
  if (!self) return [];
  const others = list.filter((e) => e.slug !== slug);
  const same = others.filter((e) => e.group === self.group);
  const rest = others.filter((e) => e.group !== self.group);
  // the rest start after this page, so neighbours differ page to page
  const at = list.indexOf(self);
  rest.sort((a, b) => ((list.indexOf(a) - at + list.length) % list.length) - ((list.indexOf(b) - at + list.length) % list.length));
  return [...same, ...rest].slice(0, n);
}

/** The page's title: the effect's name and what kind of effect it is. */
export function titleFor(e: PublicEffect): string {
  return `${e.name} — AI ${e.output === "image" ? "Photo" : "Video"} Effect`;
}

/** What it costs, in a person's words. */
export function costLine(e: PublicEffect): string {
  if (e.free) return "Free";
  if (e.credits === null) return "Priced by your clip's length";
  return `${e.credits} credits`;
}

/** What it needs from the person. */
export function needsLine(e: PublicEffect): string {
  return e.takes === "video" ? "One clip" : "One photo";
}

/** The studio address "Try it" opens after sign-in: that effect's card,
 *  its template already chosen (create-view's ?open=effect). */
export function studioPath(e: PublicEffect): string {
  return `/studio?open=effect&effect=${encodeURIComponent(e.key)}`;
}

/** The picture a card or the share preview rests on, or null. */
export function stillOf(m: ShowcaseItem): string | null {
  const pic = (u: string | null | undefined) => !!u && /\.(jpe?g|png|webp|gif|avif)(\?|#|$)/i.test(u);
  if (pic(m.poster)) return m.poster;
  if (m.kind === "still" && pic(m.after)) return m.after;
  if (pic(m.before)) return m.before;
  return null;
}

/** schema.org data for one page: the breadcrumb trail, and the example as a
 *  VideoObject (a clip with a poster) or an ImageObject (a still). A clip
 *  with no poster gets no VideoObject: a thumbnail is required. */
export function jsonLdFor(e: PublicEffect, site: string): Record<string, unknown>[] {
  const url = `${site}/effects/${e.slug}`;
  const out: Record<string, unknown>[] = [
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Effects", item: `${site}/effects` },
        { "@type": "ListItem", position: 2, name: e.name, item: url },
      ],
    },
  ];
  const still = stillOf(e.media);
  if (e.media.kind === "clip" && still) {
    out.push({
      "@context": "https://schema.org",
      "@type": "VideoObject",
      name: `${e.name} — made with Phantra`,
      description: e.description,
      thumbnailUrl: [still],
      contentUrl: e.media.after,
      uploadDate: SHOWCASE_PUBLISHED,
      url,
    });
  } else if (e.media.kind === "still") {
    out.push({
      "@context": "https://schema.org",
      "@type": "ImageObject",
      name: `${e.name} — made with Phantra`,
      description: e.description,
      contentUrl: e.media.after,
      url,
    });
  }
  return out;
}
