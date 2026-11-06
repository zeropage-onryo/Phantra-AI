import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { EffectMedia } from "@/components/effects/effect-media";
import { CreateCtaButton } from "@/landing-pages/components/create-cta-button";
import { allPublicEffects, publicEffect } from "@/lib/public-effects-data";
import { costLine, jsonLdFor, needsLine, related, stillOf, studioPath, titleFor } from "@/lib/public-effects";
import { cssAspect } from "@/lib/showcase";
import { SITE_URL } from "@/lib/site-url";
import { pageMeta } from "@/lib/page-meta";

/* /effects/<slug> (2026-11-05, docs/tasks/task-public-effects-pages.md): one
   page per effect with a kept showcase example, every part of it read off
   the effect (lib/public-effects.ts) -- nothing is written per page. */

export const dynamicParams = false;

export function generateStaticParams() {
  return allPublicEffects().map((e) => ({ slug: e.slug }));
}

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const e = publicEffect(slug);
  if (!e) return {};
  const base = pageMeta({ title: titleFor(e), description: e.description, path: `/effects/${e.slug}` });
  const still = stillOf(e.media);
  if (!still) return base;
  return {
    ...base,
    openGraph: {
      ...base.openGraph,
      images: [{ url: still }],
      ...(e.media.kind === "clip" ? { videos: [{ url: e.media.after, type: "video/mp4" }] } : {}),
    },
    twitter: { ...base.twitter, images: [still] },
  };
}

export default async function EffectPage({ params }: Props) {
  const { slug } = await params;
  const e = publicEffect(slug);
  if (!e) notFound();
  const all = allPublicEffects();
  const more = related(all, e.slug, 4);
  const made = e.output === "image" ? "picture" : "video";
  const source = e.takes === "video" ? "clip" : "photo";
  const ld = jsonLdFor(e, SITE_URL);

  return (
    <EditorialSkin>
      {ld.map((block, i) => (
        <script key={i} type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(block).replace(/</g, "\\u003c") }} />
      ))}
      <SiteHeader />
      <main className="flex-1 pt-[60px]">
        <div className="relative overflow-hidden">
          <div aria-hidden className="hero-grid pointer-events-none absolute inset-0 z-0" />
          <div className="relative z-10 mx-auto max-w-[1200px] px-6 pb-16 pt-10 md:pb-20">
            <nav aria-label="Breadcrumb" className="mb-10 text-[13px] text-muted-foreground">
              <Link href="/effects" className="hover:text-foreground">
                Effects
              </Link>
              <span aria-hidden className="mx-2">
                /
              </span>
              <span className="text-foreground">{e.name}</span>
            </nav>
            <div className="flex flex-col gap-12 md:flex-row md:items-center">
              <div className="flex min-w-0 flex-1 flex-col gap-6">
                <span className="eyebrow">{e.group === "Free looks" ? "Free look" : `Effect · ${e.group}`}</span>
                <h1 className="serif serif-bold max-w-[14ch] text-[clamp(2.5rem,6vw,4.5rem)]">{e.name}</h1>
                <p className="max-w-[46ch] text-[18px] leading-relaxed text-[#afafaf]">{e.description}</p>
                <div className="flex flex-wrap gap-3">
                  <CreateCtaButton label={`Try ${e.name}`} spark="" to={studioPath(e)} />
                </div>
                <dl className="mt-2 grid max-w-[520px] grid-cols-3 gap-4 border-t border-border pt-5 text-[14px]">
                  <div>
                    <dt className="eyebrow">You add</dt>
                    <dd className="mt-2">{needsLine(e)}</dd>
                  </div>
                  <div>
                    <dt className="eyebrow">You get</dt>
                    <dd className="mt-2">{e.output === "image" ? "A picture" : "A video"}</dd>
                  </div>
                  <div>
                    <dt className="eyebrow">Cost</dt>
                    <dd className="mt-2">{costLine(e)}</dd>
                  </div>
                </dl>
              </div>
              <div className="mx-auto w-full max-w-[360px] md:mx-0 md:w-[40%] md:max-w-[440px]">
                <div
                  className="overflow-hidden rounded-[20px] border border-border bg-muted shadow-[var(--card-shadow)]"
                  style={{ aspectRatio: cssAspect(e.media.aspect) }}
                >
                  <EffectMedia media={e.media} alt={`${e.name}, an example made with Phantra`} />
                </div>
              </div>
            </div>
          </div>
        </div>

        <section aria-labelledby="how" className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-16 md:py-20">
            <h2 id="how" className="serif text-[clamp(1.75rem,3.6vw,2.75rem)]">
              How {e.name} works
            </h2>
            <ol className="mt-10 grid gap-8 md:grid-cols-3">
              <li className="flex flex-col gap-2">
                <span className="eyebrow text-[var(--lemon)]">01</span>
                <strong className="text-[18px] font-semibold">Add your {source}</strong>
                <span className="text-[#afafaf]">
                  {e.takes === "video" ? "Pick a clip from your Library or upload one." : "Upload a photo, or use one you made in Phantra."}
                </span>
              </li>
              <li className="flex flex-col gap-2">
                <span className="eyebrow text-[var(--lemon)]">02</span>
                <strong className="text-[18px] font-semibold">See the price</strong>
                <span className="text-[#afafaf]">
                  {e.free ? "This one is free." : "The button shows the credits before anything runs. Nothing is charged until you click it."}
                </span>
              </li>
              <li className="flex flex-col gap-2">
                <span className="eyebrow text-[var(--lemon)]">03</span>
                <strong className="text-[18px] font-semibold">Get your {made}</strong>
                <span className="text-[#afafaf]">It lands in your Library, ready to download or post.</span>
              </li>
            </ol>
          </div>
        </section>

        <section aria-labelledby="questions" className="border-t border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-6 py-16 md:grid-cols-[1fr_2fr] md:py-20">
            <h2 id="questions" className="serif text-[clamp(1.75rem,3.6vw,2.75rem)]">
              Questions
            </h2>
            <dl className="flex flex-col gap-7">
              <div>
                <dt className="text-[17px] font-semibold">Do I need an account?</dt>
                <dd className="mt-2 leading-relaxed text-[#afafaf]">Yes, a free one. New accounts start with free credits to try effects like this.</dd>
              </div>
              <div>
                <dt className="text-[17px] font-semibold">What does {e.name} cost?</dt>
                <dd className="mt-2 leading-relaxed text-[#afafaf]">
                  {e.free
                    ? "Nothing. It runs on Phantra's own servers and takes no credits."
                    : e.credits === null
                      ? "It is priced by the length of your clip, and the price is shown before you run it."
                      : `${e.credits} credits at its default settings. The exact price is on the button before you run it.`}
                </dd>
              </div>
              <div>
                <dt className="text-[17px] font-semibold">Can I use someone else&apos;s {source}?</dt>
                <dd className="mt-2 leading-relaxed text-[#afafaf]">Only one you have the right to use. If it shows another person, they need to have said yes.</dd>
              </div>
            </dl>
          </div>
        </section>

        {more.length > 0 && (
          <section aria-labelledby="more" className="border-t border-border">
            <div className="mx-auto max-w-[1200px] px-6 py-16">
              <div className="flex items-baseline justify-between gap-4">
                <h2 id="more" className="eyebrow">
                  More effects
                </h2>
                <Link href="/effects" className="inline-flex items-center gap-1.5 text-[14px] text-foreground underline-offset-4 hover:underline">
                  All effects
                  <ArrowRight aria-hidden strokeWidth={1.75} className="size-4" />
                </Link>
              </div>
              <ul className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                {more.map((m) => (
                  <li key={m.slug}>
                    <Link
                      href={`/effects/${m.slug}`}
                      className="group flex h-full flex-col overflow-hidden rounded-[16px] border border-border bg-card transition-colors hover:border-[#343331]"
                    >
                      <div className="aspect-[4/5] overflow-hidden bg-muted">
                        <EffectMedia media={m.media} alt={`${m.name} example`} rest />
                      </div>
                      <span className="p-4 text-[15px] font-semibold">{m.name}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
