import type { Metadata } from "next";
import Link from "next/link";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { pageMeta } from "@/lib/page-meta";
import { SITE_URL } from "@/lib/site-url";
import { absolute, longDate, readPublicNews, type PublicNews } from "@/lib/whats-new-public";

/* What's new (2026-10-26, docs/tasks/task-whats-new.md step 4): the public
   list of what landed in the studio -- new models, effects, looks, skills and
   features, what is coming soon and Phantra's own deals -- the same rows the
   Create wall shows a signed-in person, newest first. Each row is one Mike
   kept in the Showcase list; nothing here is written by hand. Rebuilt at most
   every five minutes; an API that does not answer is an empty list. Indexed,
   with each row as a NewsArticle in the page's JSON-LD and an RSS feed. */

export const revalidate = 300;

const meta = pageMeta({
  title: "What's new",
  description: "New models, effects, looks and features in the Phantra AI studio, newest first.",
  path: "/whats-new",
});
export const metadata: Metadata = {
  ...meta,
  alternates: { ...meta.alternates, types: { "application/rss+xml": "/whats-new/rss.xml" } },
};

/* eslint-disable @next/next/no-img-element -- showcase media on the bucket, already sized */
function Picture({ n }: { n: PublicNews }) {
  if (!n.media?.url || n.media.kind === "none") return null;
  return (
    <div className="overflow-hidden rounded-xl border border-[#262522] bg-black">
      {n.media.kind === "video" ? (
        <video
          src={n.media.url}
          poster={n.media.poster ?? undefined}
          muted
          loop
          playsInline
          controls
          preload="metadata"
          className="block aspect-video w-full object-cover"
        />
      ) : (
        <img src={n.media.url} alt="" loading="lazy" className="block aspect-video w-full object-cover" />
      )}
    </div>
  );
}

function cta(n: PublicNews): string {
  if (n.source === "soon") return "See the studio";
  if (n.source === "deal") return "See the offer";
  if (n.href.startsWith("/studio?spark=")) return "Try it in the studio";
  return n.href.startsWith("/studio") ? "Open the studio" : "Read more";
}

function jsonLd(items: PublicNews[]) {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "What's new at Phantra",
    url: `${SITE_URL}/whats-new`,
    itemListElement: items.map((n, i) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "NewsArticle",
        headline: n.title,
        description: n.line || undefined,
        datePublished: n.live_at || undefined,
        url: absolute(SITE_URL, n.href),
        image:
          absolute(SITE_URL, n.media?.kind === "video" ? n.media.poster : n.media?.url) || undefined,
        publisher: { "@type": "Organization", name: "Phantra", url: SITE_URL },
      },
    })),
  };
}

export default async function WhatsNewPage() {
  const items = await readPublicNews();
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Changelog"
          title="What's new"
          dek="New models, effects, looks and features in the studio, newest first. Each one opens in the studio, ready to try."
        >
          <a href="/whats-new/rss.xml" className="mt-6 text-[13px] text-[#afafaf] underline underline-offset-4 hover:text-[#f4f3f2]">
            Follow by RSS
          </a>
        </PageIntro>
        <section className="mx-auto max-w-[760px] px-6 pb-24">
          {items.length ? (
            <ol className="flex flex-col gap-14">
              {items.map((n) => (
                <li key={n.id} id={n.id.replace(/[^a-z0-9]+/gi, "-")} className="flex flex-col gap-4">
                  <div className="flex items-center gap-3 text-[12px] tracking-[0.08em]">
                    <span className="rounded-[4px] bg-[#e4002b] px-2 py-[3px] font-semibold text-white">{n.tag}</span>
                    {n.source === "soon" && n.eta ? (
                      <span className="text-[#afafaf]">{n.eta}</span>
                    ) : n.live_at ? (
                      <time dateTime={n.live_at} className="text-[#afafaf]">
                        {longDate(n.live_at)}
                      </time>
                    ) : null}
                    {n.source === "deal" && n.ends ? <span className="text-[#afafaf]">until {longDate(n.ends)}</span> : null}
                  </div>
                  <h2 className="serif text-[clamp(1.5rem,3vw,2rem)]">{n.title}</h2>
                  {n.line ? <p className="leading-normal text-[#cfcdc8]">{n.line}</p> : null}
                  <Picture n={n} />
                  <Link href={n.href} className="self-start text-[14px] text-[#f4f3f2] underline underline-offset-4">
                    {cta(n)} →
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-center text-[#afafaf]">Nothing posted yet. New models and features show up here as they land.</p>
          )}
        </section>
        {items.length ? (
          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(items)).replace(/</g, "\\u003c") }} />
        ) : null}
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
