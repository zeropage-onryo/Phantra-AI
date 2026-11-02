import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { CreateCtaButton } from "@/landing-pages/components/create-cta-button";
import { HUB_GROUPS } from "@/landing-pages/hub";
import { getMakePage, makePath, type MakePage } from "@/landing-pages/pages";
import { SITE_URL } from "@/lib/site-url";
import { pageMeta } from "@/lib/page-meta";

// /make, the use-case hub (2026-10-27, Mike: organise the landing pages so
// Google still sees them). Until today /make itself was a 404 and the
// /make pages were reached only from the header's eight, the footer and
// each other's related links. The hub is one click from the header and
// the footer, links every /make page under its group (landing-pages/hub.ts),
// and each card's link text is the page's own H1, the phrase it ranks for.
// /models stays the hub for the model pages.

export const metadata: Metadata = pageMeta({
  title: "AI Video Tools and Use Cases",
  description:
    "Everything you can make with Phantra: AI video from text or a photo, product ads and UGC, TikTok, Reels and Shorts, short films, trailers, storyboards and more.",
  path: "/make",
});

const groups = HUB_GROUPS.map((group) => ({
  ...group,
  pages: group.slugs.map((slug) => getMakePage(slug, "make")).filter((p): p is MakePage => Boolean(p)),
}));

export default function MakeHub() {
  const listJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "AI video tools and use cases",
    url: `${SITE_URL}/make`,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: groups
        .flatMap((g) => g.pages)
        .map((p, i) => ({ "@type": "ListItem", position: i + 1, name: p.h1, url: `${SITE_URL}${makePath(p)}` })),
    },
  };

  return (
    <EditorialSkin>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(listJsonLd).replace(/</g, "\\u003c") }}
      />
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Use cases"
          title="What you can make with Phantra."
          dek="AI video, ads and short films from your idea and your own photos. Pick what you are making and start from there."
        >
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <CreateCtaButton label="Start creating" spark="" />
          </div>
          <ul className="mt-10 flex max-w-[860px] flex-wrap justify-center gap-2">
            {groups.map((g) => (
              <li key={g.title}>
                <a
                  href={`#${anchor(g.title)}`}
                  className="inline-flex h-8 items-center rounded-full border border-border bg-card px-3.5 text-[13px] text-[#c6c4c0] transition-colors hover:border-[#343331] hover:text-foreground"
                >
                  {g.title}
                </a>
              </li>
            ))}
          </ul>
        </PageIntro>

        {groups.map((g) => (
          <section key={g.title} id={anchor(g.title)} className="scroll-mt-20 border-t border-border">
            <div className="mx-auto max-w-[1200px] px-6 py-16 md:py-20">
              <h2 className="serif text-[clamp(2rem,4.2vw,3.25rem)]">{g.title}</h2>
              <p className="mt-4 max-w-[56ch] text-[17px] leading-relaxed text-[#afafaf]">{g.line}</p>
              <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {g.pages.map((p) => (
                  <li key={p.slug}>
                    <Link
                      href={makePath(p)}
                      className="group flex h-full flex-col rounded-[16px] border border-border bg-card p-6 transition-colors hover:border-[#343331]"
                    >
                      <h3 className="serif text-2xl">{p.h1}</h3>
                      <p className="mt-2 flex-1 text-[15px] leading-relaxed text-[#afafaf]">{p.subhead}</p>
                      <span className="mt-6 inline-flex items-center gap-1.5 text-[14px] text-foreground">
                        Open
                        <ArrowRight
                          aria-hidden
                          strokeWidth={1.75}
                          className="size-4 transition-transform group-hover:translate-x-0.5"
                        />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ))}

        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[1200px] flex-col items-center px-6 py-20 text-center">
            <p className="serif max-w-[24ch] text-[clamp(1.75rem,4.4vw,3rem)] leading-[1.08]">
              Looking for a model instead?
            </p>
            <Link
              href="/models"
              className="mt-6 inline-flex items-center gap-1.5 text-[16px] text-foreground underline-offset-4 hover:underline"
            >
              See every video and image model
              <ArrowRight aria-hidden strokeWidth={1.75} className="size-4" />
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}

function anchor(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
