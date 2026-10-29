/* The Library drawer's rules (2026-10-26, Mike picked concept A of the
   picker concepts: Runway's Media drawer). Pure, so the drawer, every door
   that opens it and tests/library-drawer.test.mjs read the same answers:
   what a door may be offered, what the filters keep, and how a pick is
   ordered. Order matters because the first reference anchors a still or a
   clip (CLAUDE.md, "References live on the shot"), so a pick carries its
   number and a later pick never jumps the queue. */

/** what a door takes: stills only, clips only, or either */
export type Accept = "image" | "video" | "any";

/** the drawer's top tabs: the person's renders, or their element photos */
export type Tab = "library" | "elements";

/** the pill row under the tabs */
export type Show = "all" | "image" | "video" | "starred";

/** the fields of a /api/media row the drawer reads (MediaItem's subset) */
export type Row = {
  url: string;
  asset_id: string;
  asset_name?: string;
  category?: string;
  kind: "image" | "video";
  generated_id?: number;
  prompt?: string;
  model_label?: string | null;
  folder?: string | null;
  starred?: boolean;
  poster?: string | null;
  thumb?: string | null;
};

export type Filter = { show: Show; folder: string; q: string };

/** one row's stable key: an element has several photos under one asset id */
export const keyOf = (r: Row) => `${r.asset_id}|${r.url}`;

/** may this door be offered this row at all (before any filter) */
export function offered(r: Row, accept: Accept, tab: Tab): boolean {
  if (accept !== "any" && r.kind !== accept) return false;
  // the Library tab is renders; a still or clip with no generated id is
  // not one (an element photo listed on the same endpoint)
  if (tab === "library") return r.generated_id != null;
  return r.kind === "image";
}

/** which pills a door shows: a stills-only door has no Clips pill */
export function pills(accept: Accept, tab: Tab): Show[] {
  if (tab === "elements") return ["all"];
  if (accept === "any") return ["all", "image", "video", "starred"];
  return ["all", "starred"];
}

export const PILL_LABEL: Record<Show, string> = {
  all: "All",
  image: "Stills",
  video: "Clips",
  starred: "Starred",
};

/** the rows the grid draws, newest first as the endpoint sent them */
export function visible<T extends Row>(rows: T[], accept: Accept, tab: Tab, f: Filter): T[] {
  const needle = f.q.trim().toLowerCase();
  return rows.filter((r) => {
    if (!offered(r, accept, tab)) return false;
    if (f.show === "image" && r.kind !== "image") return false;
    if (f.show === "video" && r.kind !== "video") return false;
    if (f.show === "starred" && !r.starred) return false;
    if (f.folder && r.folder !== f.folder) return false;
    if (needle) {
      const hay = `${r.prompt ?? ""} ${r.model_label ?? ""} ${r.asset_name ?? ""} ${r.folder ?? ""}`.toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    return true;
  });
}

/** the folders a door can filter by, with how many of ITS rows are in each */
export function folders(rows: Row[], accept: Accept, tab: Tab): [string, number][] {
  const n = new Map<string, number>();
  for (const r of rows) {
    if (!r.folder || !offered(r, accept, tab)) continue;
    n.set(r.folder, (n.get(r.folder) ?? 0) + 1);
  }
  return [...n.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

/** a click on a tile: off if it was picked, else on the end of the queue,
 *  and nothing at all when the door is full (the tile says why) */
export function toggle(picked: string[], key: string, max: number): string[] {
  if (picked.includes(key)) return picked.filter((k) => k !== key);
  if (picked.length >= max) return picked;
  return [...picked, key];
}

/** the 1-based number a picked tile wears, or 0 */
export const numberOf = (picked: string[], key: string) => picked.indexOf(key) + 1;

/** what a tile draws: a clip its poster, a still its 480px thumbnail when
 *  one is named (the tile falls back to the master when that fails to
 *  load: `thumb` says where one WOULD be, not that it is) */
export function tileSrc(r: Row): string {
  if (r.kind === "video") return r.poster ?? "";
  return r.thumb ?? r.url;
}

/** the label on a tile's corner */
export function tileTag(r: Row): string {
  if (r.kind === "video") return "Clip";
  if (r.category && r.category !== "generated") return r.asset_name ?? "";
  return r.model_label ?? "";
}

/** how many tiles one page of the grid draws before the next scroll asks
 *  for more: 48 full-size masters at once was the old picker's lag */
export const PAGE = 40;

/** the primary button's words for a pick of n */
export function addLabel(n: number, noun: string): string {
  if (n <= 0) return "Add";
  return n === 1 ? `Add 1 ${noun}` : `Add ${n} ${noun}s`;
}
