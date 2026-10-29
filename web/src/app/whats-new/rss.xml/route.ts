import { SITE_URL } from "@/lib/site-url";
import { readPublicNews, rssXml } from "@/lib/whats-new-public";

/* The What's new feed as RSS (2026-10-26, docs/tasks/task-whats-new.md
   step 4): the same rows as the page, for feed readers, the Discord bot and
   socials later. Rebuilt at most every five minutes. */
export const revalidate = 300;

export async function GET() {
  const items = await readPublicNews();
  return new Response(rssXml(SITE_URL, items), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=300, s-maxage=300",
    },
  });
}
