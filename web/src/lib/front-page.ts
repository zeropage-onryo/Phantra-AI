/* The Create home as a front page (2026-10-22, Mike's pick of board 66 with
   the type of 68 on the "Phantra Create Page Redesign" canvas;
   docs/tasks/task-create-front-page.md).

   The page under the box is NEWS: new models, new effects, what is
   trending, updates -- a wall of tiles in five sizes, each the whole click
   (no "Use this" buttons). The entries are a list Mike edits,
   src/content/news.json; this file reads it, never trusting a half-written
   entry, and lays the wall out. The renders between the news are the
   showcase's own (the use-case stills), each filling the box with its
   brief.

   The tray hanging under the box is the person's own work in four stages
   (scenes in progress, stills, clips, final cuts), read off the lists the
   Library and Renders already read. A stage is a filter: it turns the wall
   into that stage's work.

   THE FEED (2026-10-25, docs/tasks/task-whats-new.md step 3): the live
   announcements Mike kept (GET /api/whats-new) join the file's entries,
   newest first, as tiles of the same shapes (`feedNews`). Where a feed tile
   and a file entry name the same thing, the feed wins (`mergeNews`). A
   Coming soon tile makes nothing: its click is Notify me or a page.

   Pure and import-free on purpose (type imports only, which node strips):
   tests/front-page.test.mjs runs this file as it is. No price is drawn
   anywhere here except a deal's own words, and nothing here sends. */
import type { ShowcaseItem } from "./showcase";
import type { FeedItem } from "./whats-new";

export type NewsType = "model" | "effect" | "trending" | "update" | "soon" | "deal";
export type NewsSize = "big" | "wide" | "tall" | "medium" | "small" | "slim";
export type NewsAction =
  | { fill: string; model?: string }
  | { skill: string }
  | { notify: string }
  | { href: string }
  | { effect: string }
  | { look: string }
  | { talk: true };
export type NewsItem = {
  id: string;
  type: NewsType;
  title: string;
  /** the words of the title lit in the tag's colour ("" for none) */
  accent: string;
  line: string;
  /** ISO day, or null for an entry with no date line */
  date: string | null;
  size: NewsSize;
  /** a key in the showcase manifest */
  media: string;
  action: NewsAction;
  /** a capability that must be true, else the entry hides (a parked model) */
  requires: string | null;
  /** also rotates in the peek tab behind the box */
  peek: boolean;
  /** a feed tile's own tag words ("NEW LOOK", "NEW SKILL"), over TAG[type] */
  tag?: string;
  /** a feed tile: its announcement id, unread for this person */
  feedId?: string;
  unread?: boolean;
  /** words only: no picture behind them */
  textOnly?: boolean;
  /** Coming soon's "This month", never a made-up date */
  eta?: string | null;
};

/** The tag on a tile, by type. Words only; the colour is the CSS's (front.css). */
export const TAG: Record<NewsType, string> = {
  model: "NEW MODEL",
  effect: "NEW EFFECT",
  trending: "TRENDING",
  update: "UPDATE",
  soon: "COMING SOON",
  deal: "DEAL",
};

const TYPES: readonly string[] = ["model", "effect", "trending", "update"];
const SIZES: readonly string[] = ["big", "wide", "tall", "medium", "small", "slim"];
const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");

function readAction(raw: unknown): NewsAction | null {
  if (!raw || typeof raw !== "object") return null;
  const a = raw as Record<string, unknown>;
  if (typeof a.fill === "string" && a.fill.trim()) return { fill: a.fill };
  // a studio page only: never an outside address from a hand-edited file
  if (typeof a.href === "string" && a.href.startsWith("/studio")) return { href: a.href };
  if (str(a.effect)) return { effect: str(a.effect) };
  if (str(a.look)) return { look: str(a.look) };
  if (a.talk === true) return { talk: true };
  return null;
}

/** One entry, whole, or null: no id, title, media or action, or an unknown
 *  type, and the entry is left out rather than drawn half-made. An unknown
 *  size reads as medium. */
export function readNewsItem(raw: unknown): NewsItem | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const id = str(r.id);
  const title = str(r.title);
  const media = str(r.media);
  const action = readAction(r.action);
  if (!id || !title || !media || !action || !TYPES.includes(str(r.type))) return null;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(str(r.date)) ? str(r.date) : null;
  const accent = str(r.accent);
  return {
    id,
    type: str(r.type) as NewsType,
    title,
    accent: accent && title.includes(accent) ? accent : "",
    line: str(r.line),
    date,
    size: (SIZES.includes(str(r.size)) ? str(r.size) : "medium") as NewsSize,
    media,
    action,
    requires: str(r.requires) || null,
    peek: r.peek === true,
  };
}

/** The file's entries, whole ones only, in its order, ids unique. */
export function readNews(raw: unknown): NewsItem[] {
  const list = raw && typeof raw === "object" ? (raw as { items?: unknown }).items : null;
  if (!Array.isArray(list)) return [];
  const seen = new Set<string>();
  const out: NewsItem[] = [];
  for (const entry of list) {
    const item = readNewsItem(entry);
    if (!item || seen.has(item.id)) continue;
    seen.add(item.id);
    out.push(item);
  }
  return out;
}

/* ── the feed ── */
const FEED_TYPE: Record<string, NewsType> = {
  model: "model",
  effect: "effect",
  look: "effect",
  skill: "update",
  feature: "update",
  soon: "soon",
  deal: "deal",
};

/** What a feed tile's click does, or null when it has no door. Server
 *  copy, so a page anywhere on this site is allowed (a model's own page);
 *  never an outside address. A coming-soon tile never fills the box. */
export function feedAction(f: Pick<FeedItem, "id" | "source" | "action">): NewsAction | null {
  const a = (f.action ?? {}) as Record<string, unknown>;
  const href = typeof a.href === "string" && a.href.startsWith("/") && !a.href.startsWith("//") ? a.href : "";
  if (f.source === "soon") return href ? { href } : { notify: f.id };
  if (str(a.fill)) return str(a.model) ? { fill: a.fill as string, model: str(a.model) } : { fill: a.fill as string };
  if (href) return { href };
  if (str(a.effect)) return { effect: str(a.effect) };
  if (str(a.look)) return { look: str(a.look) };
  if (str(a.skill)) return { skill: str(a.skill) };
  if (a.talk === true) return { talk: true };
  return null;
}

/** The feed's live tiles as wall entries, with the showcase items their
 *  pictures are (keyed `feed:<id>`). A tile with no door is left out. */
export function feedNews(feed: FeedItem[]): { news: NewsItem[]; media: Record<string, ShowcaseItem> } {
  const news: NewsItem[] = [];
  const media: Record<string, ShowcaseItem> = {};
  for (const f of feed ?? []) {
    const action = feedAction(f);
    const type = FEED_TYPE[f.source];
    if (!action || !type || !str(f.title)) continue;
    const key = `feed:${f.id}`;
    const url = f.media?.url ?? null;
    const textOnly = !url || f.media.kind === "none";
    if (!textOnly) {
      const clip = f.media.kind === "video";
      media[key] = {
        kind: clip ? "clip" : "still",
        before: null,
        after: url as string,
        poster: f.media.poster ?? null,
        aspect: "16:9",
        credits: 0,
        model: "",
        gen_id: null,
      };
    }
    const accent = str(f.accent);
    // words need room: a tile with no picture is never smaller than medium
    let size = (SIZES.includes(str(f.size)) ? str(f.size) : "medium") as NewsSize;
    if (textOnly && (size === "small" || size === "slim")) size = "medium";
    const line = str(f.line);
    news.push({
      id: f.id,
      type,
      title: str(f.title),
      accent: accent && f.title.includes(accent) ? accent : "",
      // a skill's line starts lowercase ("a short product ad"); a name like xAI does not change
      line: /^[a-z]+\b/.test(line) && /^[a-z]+(\s|$|[,.;:])/.test(line) ? line[0].toUpperCase() + line.slice(1) : line,
      date: /^\d{4}-\d{2}-\d{2}/.test(f.live_at ?? "") ? (f.live_at as string).slice(0, 10) : null,
      size,
      media: key,
      action,
      requires: null,
      peek: f.new && f.source === "model",
      tag: str(f.tag) || undefined,
      feedId: f.id,
      unread: !!f.unread,
      textOnly,
      eta: f.source === "soon" ? f.eta : null,
    });
  }
  return { news, media };
}

/** The wall's entries: the feed's (New first, as the server sent them), then
 *  the file's, leaving out a file entry the feed already names (`kling4` and
 *  `model:kling4` are the same news; the feed's is the one Mike kept). */
export function mergeNews(file: NewsItem[], feed: NewsItem[]): NewsItem[] {
  const named = new Set(feed.flatMap((n) => [n.id, n.id.split(":").slice(1).join(":")]));
  return [...feed, ...file.filter((n) => !named.has(n.id))];
}

/** The entries this studio can act on: one that needs a capability shows
 *  only while the server says it is on. */
export function liveNews(items: NewsItem[], caps: Record<string, unknown> | null | undefined): NewsItem[] {
  return items.filter((i) => !i.requires || caps?.[i.requires] === true);
}

/** The title cut around its accent, for the lit word. */
export function splitAccent(title: string, accent: string): [string, string, string] {
  const at = accent ? title.indexOf(accent) : -1;
  if (at < 0) return [title, "", ""];
  return [title.slice(0, at), accent, title.slice(at + accent.length)];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "Today", "Yesterday", "3 days ago" inside a week, else "Oct 14"; "" with no date. */
export function whenLabel(date: string | null, now: Date): string {
  if (!date) return "";
  const [y, m, d] = date.split("-").map(Number);
  const day = Date.UTC(y, m - 1, d);
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((today - day) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return `${MONTHS[m - 1]} ${d}`;
}

/* ── the chips over the wall ── */
export type FrontFilter = "all" | NewsType | "made";
export const FILTERS: { id: FrontFilter; label: string }[] = [
  { id: "all", label: "All news" },
  { id: "model", label: "New models" },
  { id: "effect", label: "Effects" },
  { id: "trending", label: "Trending" },
  { id: "update", label: "Updates" },
  { id: "soon", label: "Coming soon" },
  { id: "made", label: "Made in Phantra" },
];

/** A render between the news: a showcase still that fills the box with its brief. */
export type MadeTile = { id: string; title: string; brief: string; media: string };
export type WallTile =
  | { kind: "news"; key: string; size: NewsSize; item: NewsItem }
  | { kind: "made"; key: string; size: NewsSize; made: MadeTile };

/* the renders' sizes, in turn: small and slim, so the news stays the headline */
const MADE_SIZES: NewsSize[] = ["small", "slim", "small", "small", "slim", "small"];
/* the "Made in Phantra" chip: the renders are the page, so they take every size */
const MADE_ONLY_SIZES: NewsSize[] = ["medium", "slim", "small", "tall", "small", "wide", "small", "slim", "medium", "small"];

/** The wall for a chip. All news: every entry in the file's order with the
 *  renders spread evenly between them to the end, so the bottom of the wall
 *  is not news-only (the dense grid packs the renders into the gaps). One
 *  type: its entries only, sizes kept. Made in Phantra: the renders alone. */
export function wallTiles(filter: FrontFilter, news: NewsItem[], made: MadeTile[]): WallTile[] {
  const madeTile = (m: MadeTile, i: number, sizes: NewsSize[]): WallTile => ({
    kind: "made",
    key: `made-${m.id}`,
    size: sizes[i % sizes.length],
    made: m,
  });
  if (filter === "made") return made.map((m, i) => madeTile(m, i, MADE_ONLY_SIZES));
  const newsTile = (item: NewsItem): WallTile => ({ kind: "news", key: `news-${item.id}`, size: item.size, item });
  if (filter !== "all") return news.filter((n) => n.type === filter).map(newsTile);
  const out: WallTile[] = [];
  let next = 0;
  news.forEach((item, i) => {
    out.push(newsTile(item));
    // the renders owed by the end of this entry, at an even rate
    const due = news.length ? Math.round(((i + 1) * made.length) / news.length) : made.length;
    for (; next < due; next++) out.push(madeTile(made[next], next, MADE_SIZES));
  });
  for (; next < made.length; next++) out.push(madeTile(made[next], next, MADE_SIZES));
  return out;
}

/** The tiles a big screen plays muted on their own; the rest wait for a hover. */
export const plays = (size: NewsSize) => size === "big" || size === "wide";

/** What rotates in the peek tab: the entries marked for it, in order. */
export const peekItems = (news: NewsItem[]) => news.filter((n) => n.peek);

/* ── the tray: the person's own work, by stage ── */
export type StageId = "scenes" | "stills" | "clips" | "cuts";
export type Stage = { id: StageId; label: string; count: number; thumbs: string[]; hot: boolean };
export type OwnRender = { kind: "image" | "video"; model?: string | null; thumb?: string | null; poster?: string | null; url: string };

/** A Library row the editor's Assemble filed (src/cut/assemble.py LIBRARY_MODEL). */
export const isFinalCut = (m: { model?: string | null }) => (m.model ?? "").trim().toLowerCase() === "final cut";
const pic = (m: OwnRender) => (m.kind === "video" ? m.poster || m.thumb || "" : m.thumb || m.url);

/** The four stages, from the scenes a render is waiting on (their pictures
 *  passed in) and the Library's rows and totals. A stage with work waiting
 *  on the person (a scene not yet rendered) is `hot`. */
export function trayStages(
  scenes: string[],
  renders: OwnRender[],
  totals: { image: number; video: number } | null,
): Stage[] {
  const cuts = renders.filter(isFinalCut);
  const clips = renders.filter((m) => m.kind === "video" && !isFinalCut(m));
  const stills = renders.filter((m) => m.kind === "image");
  const thumbs = (list: OwnRender[]) => list.map(pic).filter(Boolean).slice(0, 3);
  return [
    { id: "scenes", label: "Scenes", count: scenes.length, thumbs: scenes.filter(Boolean).slice(0, 3), hot: scenes.length > 0 },
    { id: "stills", label: "Stills", count: totals?.image ?? stills.length, thumbs: thumbs(stills), hot: false },
    {
      id: "clips",
      label: "Clips",
      // the total counts every clip, the final cuts among them
      count: Math.max(0, (totals?.video ?? clips.length + cuts.length) - cuts.length),
      thumbs: thumbs(clips),
      hot: false,
    },
    { id: "cuts", label: "Final cuts", count: cuts.length, thumbs: thumbs(cuts), hot: false },
  ];
}

/** The tray shows once there is something in it: a first visit has no tray. */
export const hasWork = (stages: Stage[]) => stages.some((s) => s.count > 0);

/** "99+" past ninety-nine: the tray is a glance, not a ledger. */
export const countLabel = (n: number) => (n > 99 ? "99+" : String(n));
