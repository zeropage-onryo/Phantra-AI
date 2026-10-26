/* The public What's new (phantra.ai/whats-new and /whats-new/rss.xml,
   2026-10-26, docs/tasks/task-whats-new.md step 4).

   Read on the SERVER from the API's public route (API_UPSTREAM, the same
   upstream the rewrites proxy to), cached five minutes like the route
   itself. Only what the public page may show comes back: the tag, the
   words, the picture, a link on this site and the date. An API that does
   not answer is an empty list -- the page says nothing is posted yet rather
   than breaking. Pure helpers below are what the node test runs. */

export type PublicNews = {
  id: string;
  source: "model" | "effect" | "look" | "skill" | "feature" | "soon" | "deal";
  tag: string;
  title: string;
  line: string;
  media: { kind: "video" | "image" | "none"; url: string | null; poster: string | null };
  href: string;
  eta: string | null;
  ends: string | null;
  live_at: string | null;
};

const UPSTREAM = () => (process.env.API_UPSTREAM || "http://localhost:8000").replace(/\/+$/, "");

export async function readPublicNews(): Promise<PublicNews[]> {
  try {
    const res = await fetch(`${UPSTREAM()}/public/whats-new`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const body = (await res.json()) as { items?: PublicNews[] };
    return Array.isArray(body?.items) ? body.items.filter(isWhole) : [];
  } catch {
    return [];
  }
}

/** A row the page can draw: an id, a title, and a link on this site. */
export function isWhole(n: PublicNews): boolean {
  return (
    !!n &&
    typeof n.id === "string" &&
    typeof n.title === "string" &&
    n.title.trim() !== "" &&
    typeof n.href === "string" &&
    n.href.startsWith("/") &&
    !n.href.startsWith("//")
  );
}

/** An address a crawler or a feed reader can open: this site's own paths
 *  made absolute; a media URL already absolute is kept. */
export const absolute = (site: string, u: string | null | undefined) =>
  !u ? null : /^https?:\/\//.test(u) ? u : `${site}${u.startsWith("/") ? "" : "/"}${u}`;

const XML: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" };
export const xml = (s: string) => s.replace(/[&<>"']/g, (c) => XML[c]);

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
/** "October 26, 2026" from an ISO timestamp, "" without one. */
export function longDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

/** The RSS 2.0 document for the feed: newest first, one item per tile,
 *  each linking to its page on the site, its picture as an enclosure. */
export function rssXml(site: string, items: PublicNews[]): string {
  const entries = items
    .map((n) => {
      const link = absolute(site, n.href) as string;
      const pic = n.media?.kind === "video" ? n.media.poster || null : n.media?.url || null;
      const picUrl = absolute(site, pic);
      const when = n.live_at ? new Date(n.live_at) : null;
      const words = [n.line, n.source === "soon" && n.eta ? `Coming ${n.eta.toLowerCase()}.` : ""].filter(Boolean).join(" ");
      return [
        "    <item>",
        `      <title>${xml(`${n.tag}: ${n.title}`)}</title>`,
        `      <link>${xml(link)}</link>`,
        `      <guid isPermaLink="false">${xml(`phantra-whats-new-${n.id}`)}</guid>`,
        when && !Number.isNaN(when.getTime()) ? `      <pubDate>${when.toUTCString()}</pubDate>` : "",
        `      <category>${xml(n.tag)}</category>`,
        `      <description>${xml(words)}</description>`,
        picUrl ? `      <enclosure url="${xml(picUrl)}" type="${picUrl.endsWith(".png") ? "image/png" : "image/jpeg"}" length="0"/>` : "",
        "    </item>",
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n");
  const newest = items.find((n) => n.live_at)?.live_at;
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    "  <channel>",
    "    <title>What's new at Phantra</title>",
    `    <link>${xml(`${site}/whats-new`)}</link>`,
    `    <atom:link href="${xml(`${site}/whats-new/rss.xml`)}" rel="self" type="application/rss+xml"/>`,
    "    <description>New models, effects, looks and features in the Phantra AI studio.</description>",
    "    <language>en-us</language>",
    newest ? `    <lastBuildDate>${new Date(newest).toUTCString()}</lastBuildDate>` : "",
    entries,
    "  </channel>",
    "</rss>",
    "",
  ]
    .filter((l) => l !== "")
    .join("\n");
}
