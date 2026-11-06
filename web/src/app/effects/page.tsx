import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { EffectMedia } from "@/components/effects/effect-media";
import { CreateCtaButton } from "@/landing-pages/components/create-cta-button";
import { allPublicEffects, featuredEffects } from "@/lib/public-effects-data";
import { costLine, grouped, slugOf, type PublicEffect } from "@/lib/public-effects";
import { SITE_URL } from "@/lib/site-url";
import { pageMeta } from "@/lib/page-meta";

/* /effects (2026-11-05, docs/tasks/task-public-effects-pages.md): the public
   face of the studio's Effects wall. Every effect with a kept showcase
   example, grouped, each card its own page. Linked from the footer and from
   every effect page, never from the header or the home page (Mike: the main
   page stays as it is); the sitemap lists it and every effect. */

export const metadata: Metadata = pageMeta({
  title: "AI Video Effects",
  description:
    "One-click AI video effects from a single photo or clip: vanish, time stop, bullet time, camera moves, free film looks and more. See each one, then make your own.",
  path: "/effects",
});

function Card({ e, big = false }: { e: PublicEffect; big?: boolean }) {
  return (
    <Link
      href={`/effects/${e.slug}`}
      className="group flex h-full flex-col overflow-hidden rounded-[16px] border border-border bg-card transition-colors hover:border-[#343331]"
    >
      <div className={`relative overflow-hidden bg-muted ${big ? "aspect-[4/5]" : "aspect-[4/5]"}`}>
        <EffectMedia media={e.media} alt={`${e.name} example`} rest={!big} />
        {e.free && (
          <span className="absolute left-3 top-3 rounded-[4px] bg-[var(--lemon)] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.06em] text-[var(--lemon-ink)]">
            Free
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <h3 className="text-[16px] font-semibold text-foreground">{e.name}</h3>
        <p className="line-clamp-2 flex-1 text-[14px] leading-snug text-[#afafaf]">{e.description}</p>
        <span className="mt-2 inline-flex items-center gap-1.5 text-[13px] text-[#c6c4c0]">
          {costLine(e)}
          <ArrowRight aria-hidden strokeWidth={1.75} className="ml-auto size-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}

export default function EffectsHub() {
  const all = allPublicEffects();
  const groups = grouped(all);
  const featured = featuredEffects(3);
  const listJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "AI video effects",
    url: `${SITE_URL}/effects`,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: all.map((e, i) => ({ "@type": "ListItem", position: i + 1, name: e.name, url: `${SITE_URL}/effects/${e.slug}` })),
    },
  };

  return (
    <EditorialSkin>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(listJsonLd).replace(/</g, "\\u003c") }} />
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Effects"
          title="AI video effects, one click each."
          dek="Add one photo or one clip, see the price, get the finished video. Every effect here was made in Phantra."
        >
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <CreateCtaButton label="Start creating" spark="" to="/studio?open=effects" />
          </div>
          <ul className="mt-10 flex max-w-[860px] flex-wrap justify-center gap-2">
            {groups.map((g) => (
              <li key={g.group}>
                <a
                  href={`#${slugOf(g.group)}`}
                  className="inline-flex h-8 items-center rounded-full border border-border bg-card px-3.5 text-[13px] text-[#c6c4c0] transition-colors hover:border-[#343331] hover:text-foreground"
                >
                  {g.group}
                </a>
              </li>
            ))}
          </ul>
        </PageIntro>

        {featured.length > 0 && (
          <section aria-labelledby="featured" className="border-t border-border">
            <div className="mx-auto max-w-[1200px] px-6 py-16">
              <h2 id="featured" className="eyebrow">
                Featured
              </h2>
              <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {featured.map((e) => (
                  <li key={e.slug}>
                    <Card e={e} big />
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {groups.map((g) => (
          <section key={g.group} id={slugOf(g.group)} className="scroll-mt-20 border-t border-border">
            <div className="mx-auto max-w-[1200px] px-6 py-16 md:py-20">
              <h2 className="serif text-[clamp(2rem,4.2vw,3.25rem)]">{g.group}</h2>
              <p className="mt-4 max-w-[56ch] text-[17px] leading-relaxed text-[#afafaf]">{g.line}</p>
              <ul className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
                {g.effects.map((e) => (
                  <li key={e.slug}>
                    <Card e={e} />
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ))}

        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[1200px] flex-col items-center px-6 py-20 text-center">
            <p className="serif max-w-[24ch] text-[clamp(1.75rem,4.4vw,3rem)] leading-[1.08]">Want to make something longer?</p>
            <Link href="/make" className="mt-6 inline-flex items-center gap-1.5 text-[16px] text-foreground underline-offset-4 hover:underline">
              See everything you can make
              <ArrowRight aria-hidden strokeWidth={1.75} className="size-4" />
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
