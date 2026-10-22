import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { ModelMedia } from "@/components/site/model-media";
import { Button } from "@/components/ui/button";
import { HERO_REEL } from "@/content/hero-reel";
import { CreateCtaButton } from "@/landing-pages/components/create-cta-button";
import { makePath, pagesIn, type MakePage, type MakeTile } from "@/landing-pages/pages";
import { IMAGE_MODELS, isVideoModelPage } from "@/landing-pages/shared";
import { CATALOG, MODELS, frameLabel, num } from "@/lib/catalog";
import { pageMeta } from "@/lib/page-meta";

// /models, the one-stop models page (2026-10-20, Mike's call, after
// runway.com/product): every model the studio offers on one page, each
// with its own clip or still off its landing page, a line on what it is
// for, its price from the catalog, and two doors -- try it in the studio,
// or read its page. Nothing here is typed by hand that a catalog or an
// entry already says: names, prices and media are read off the same lists
// the header menu and the landing pages read.

export const metadata: Metadata = pageMeta({
  title: "AI Video and Image Models",
  description:
    "Kling, Seedance, Veo, LTX, Wan, Nano Banana, FLUX, Seedream, GPT Image and Ideogram in one studio — every model on every plan, paid for in one balance of credits.",
  path: "/models",
});

const isVideoPage = isVideoModelPage;

/** The page's own picture: a clip when it has one, else its first still. */
function tileFor(page: MakePage): MakeTile | undefined {
  const tiles = [...(page.heroMedia ?? []), ...page.wall.tiles];
  return tiles.find((t) => t.video) ?? tiles.find((t) => t.src);
}

function nameOf(page: MakePage): string {
  if (page.navLabel) return page.navLabel;
  const video = MODELS.find((m) => m.model === page.modelIds?.[0]);
  if (video) return video.name;
  return IMAGE_MODELS.find((m) => m.id === page.modelIds?.[0])?.label ?? page.menu;
}

/** "From 87 credits · 6s at 1080p" off the catalog, for a video page. */
function priceLine(page: MakePage): string | null {
  const rows = MODELS.filter((m) => page.modelIds?.includes(m.model));
  // a talking photo is priced by its voice, not per catalog clip
  if (!rows.length && page.modelIds?.includes("omnihuman-v2"))
    return `${num(CATALOG.actions.talking_photo.per_10s)} credits · 10s of voice`;
  if (!rows.length) return null;
  const cheapest = rows.reduce((a, b) => (a.credits <= b.credits ? a : b));
  return `From ${num(cheapest.credits)} credits · ${cheapest.seconds}s at ${frameLabel(cheapest.frame)}`;
}

function imageLine(page: MakePage): string {
  const m = IMAGE_MODELS.find((x) => x.id === page.modelIds?.[0]);
  const refs = m ? (m.references ? "Takes your reference photos" : "Draws from the prompt alone") : "";
  return [refs, `${num(CATALOG.actions.still.standard)}+ credits a still`].filter(Boolean).join(" · ");
}

// the hero strip: portrait clips off the model pages (hero-reel.ts)
const STRIP = HERO_REEL.filter((c) => c.poster.startsWith("/models/")).slice(0, 5);

export default function ModelsPage() {
  const pages = pagesIn("models");
  const video = pages.filter(isVideoPage);
  const image = pages.filter((p) => !isVideoPage(p));
  const uses = pagesIn("make");

  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Models"
          title="Every model you need, in one studio."
          dek="The best video and image models, side by side. Pick the one that suits the shot, see its price in credits before you approve, and keep the faces and the look you set across all of them."
        >
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <CreateCtaButton label="Start creating" spark="" />
            <Button size="lg" variant="outline" render={<Link href="/pricing" />}>
              See pricing
            </Button>
          </div>
          <ul className="mt-10 flex max-w-[860px] flex-wrap justify-center gap-2">
            {[...video, ...image].map((p) => (
              <li key={p.slug}>
                <Link
                  href={makePath(p)}
                  className="inline-flex h-8 items-center rounded-full border border-border bg-card px-3.5 text-[13px] text-[#c6c4c0] transition-colors hover:border-[#343331] hover:text-foreground"
                >
                  {nameOf(p)}
                </Link>
              </li>
            ))}
          </ul>
        </PageIntro>

        {/* the strip: real studio clips, one per tile */}
        <section aria-label="Made in the studio" className="mx-auto max-w-[1200px] px-6">
          <div className="-mx-6 flex snap-x gap-3 overflow-x-auto px-6 pb-2 md:mx-0 md:grid md:grid-cols-5 md:overflow-visible md:px-0">
            {STRIP.map((c, i) => (
              <figure key={c.mp4} className="w-[58vw] shrink-0 snap-start md:w-auto">
                <div className="relative aspect-[9/16] overflow-hidden rounded-[14px] border border-border bg-card">
                  <ModelMedia tile={{ title: c.title, tag: "", video: c.mp4, src: c.poster }} eager={i < 3} />
                </div>
                <figcaption className="mt-2 text-[12.5px] text-[#82807d]">
                  <span className="text-foreground">{c.model}</span> · {c.title}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-6 py-24 md:py-32">
          <p className="serif max-w-[24ch] text-[clamp(1.75rem,4.4vw,3.5rem)] leading-[1.08]">
            Write the scene once, hold it to your photos, and send each shot to the model that suits it.
          </p>
        </section>

        {/* video models: one row each, the clip beside the words */}
        <section id="video-models" className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-20">
            <span className="eyebrow">Video models</span>
            <h2 className="serif mt-5 text-[clamp(2rem,4.2vw,3.25rem)]">Our video models.</h2>
            <div className="mt-12 flex flex-col gap-6">
              {video.map((p, i) => {
                const tile = tileFor(p);
                const price = priceLine(p);
                return (
                  <article
                    key={p.slug}
                    className="grid overflow-hidden rounded-[18px] border border-border bg-card md:grid-cols-2"
                  >
                    <div className={`relative aspect-[16/10] bg-secondary md:aspect-auto md:min-h-[360px] ${i % 2 ? "md:order-2" : ""}`}>
                      {tile && <ModelMedia tile={tile} sound />}
                    </div>
                    <div className="flex flex-col justify-center p-7 md:p-10">
                      <h3 className="serif text-[clamp(1.75rem,3vw,2.5rem)]">{nameOf(p)}</h3>
                      <p className="mt-3 text-[16px] leading-relaxed text-[#afafaf]">{p.subhead}</p>
                      {price && <p className="mt-4 text-[13px] text-[#82807d]">{price} · on every plan</p>}
                      <div className="mt-7 flex flex-wrap items-center gap-3">
                        <CreateCtaButton label="Try now" spark={p.cta.spark} size="default" />
                        <Button variant="outline" render={<Link href={makePath(p)} />}>
                          Learn more
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* image models: a grid of stills */}
        <section id="image-models" className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-20">
            <span className="eyebrow">Image models</span>
            <h2 className="serif mt-5 text-[clamp(2rem,4.2vw,3.25rem)]">Stills, keyframes and elements.</h2>
            <p className="mt-5 max-w-[56ch] text-[17px] leading-relaxed text-[#afafaf]">
              Draw a keyframe, a product shot or a character sheet on any of them. Every still lands in your library
              and can become the first frame of a clip.
            </p>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {image.map((p) => {
                const tile = tileFor(p);
                return (
                  <article key={p.slug} className="flex flex-col overflow-hidden rounded-[16px] border border-border bg-card">
                    <div className="relative aspect-[4/3] bg-secondary">{tile && <ModelMedia tile={tile} />}</div>
                    <div className="flex flex-1 flex-col p-6">
                      <h3 className="serif text-2xl">{nameOf(p)}</h3>
                      <p className="mt-2 text-[15px] leading-relaxed text-[#afafaf]">{p.subhead}</p>
                      <p className="mt-3 text-[13px] text-[#82807d]">{imageLine(p)}</p>
                      <div className="mt-auto flex items-center gap-4 pt-6">
                        <CreateCtaButton variant="link" label="Try now" spark={p.cta.spark} />
                        <Link href={makePath(p)} className="text-[13px] text-[#82807d] transition-colors hover:text-foreground">
                          Learn more
                        </Link>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* what people make with them */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-20">
            <span className="eyebrow">What you can make</span>
            <h2 className="serif mt-5 text-[clamp(2rem,4.2vw,3.25rem)]">Dozens of ways to use them.</h2>
            <ul className="mt-10 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {uses.map((p) => (
                <li key={p.slug}>
                  <Link
                    href={makePath(p)}
                    className="group flex items-center justify-between rounded-[12px] border border-border bg-card px-4 py-3.5 text-[14px] text-[#c6c4c0] transition-colors hover:border-[#343331] hover:text-foreground"
                  >
                    {p.menu}
                    <ArrowRight className="size-3.5 opacity-50 transition-transform group-hover:translate-x-0.5 group-hover:opacity-100" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-6 py-20 md:grid-cols-2 md:gap-16">
            <div>
              <span className="eyebrow">Keyframes</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">Every clip starts from a still you approved.</h2>
              <p className="mt-5 text-[17px] leading-relaxed text-[#afafaf]">
                Each shot&apos;s first frame is drawn from the references you attached, and the clip renders from it on
                whichever model you pick. The face, the room and the wardrobe are settled before a credit goes on video.
              </p>
            </div>
            <div>
              <span className="eyebrow">One balance</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">Every model, one bill in credits.</h2>
              <p className="mt-5 text-[17px] leading-relaxed text-[#afafaf]">
                Every plan renders every model, with nothing to connect and no second bill. The Render card shows each
                clip&apos;s price in credits before you approve it.
              </p>
              <Button size="lg" variant="outline" className="mt-7" render={<Link href="/pricing#models" />}>
                Compare what a month buys
                <ArrowRight data-icon="inline-end" className="size-4" />
              </Button>
            </div>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[1200px] flex-col items-center px-6 py-24 text-center">
            <h2 className="serif max-w-[18ch] text-[clamp(2rem,4.8vw,3.5rem)]">Pick a model. Make the shot.</h2>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <CreateCtaButton label="Start creating" spark="" />
              <Button size="lg" variant="outline" render={<Link href="/pricing" />}>
                See pricing
              </Button>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
