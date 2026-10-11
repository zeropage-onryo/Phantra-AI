import type { Metadata } from "next";
import { EditorialSkin } from "@/components/editorial-skin";
import { PLANS } from "@/lib/catalog";
import { SITE_URL } from "@/lib/site-url";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { HeroSection } from "@/components/landing/hero-section";
import { PipelineSequence } from "@/components/landing/pipeline-sequence";
import { FeatureSection } from "@/components/landing/feature-section";
import { FramesSection } from "@/components/landing/frames-section";
import { WorkSection } from "@/components/landing/work-section";
import { StartingPointsSection } from "@/components/landing/starting-points-section";
import { CtaSection } from "@/components/landing/cta-section";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

// What the home page tells a search engine the site IS (2026-10-11). The
// /make and /models pages carry their own FAQPage block; until today the
// home page carried none. Prices come off pricing.json (the generated
// catalogue), never typed here.
const monthly = PLANS.map((p) => p.monthly_usd);
const HOME_JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: "Zero Page",
      url: SITE_URL,
      logo: `${SITE_URL}/brand/zp_black_favicon_512.png`,
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: "Zero Page",
      url: SITE_URL,
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
    {
      "@type": "SoftwareApplication",
      name: "Zero Page Studio",
      url: SITE_URL,
      applicationCategory: "MultimediaApplication",
      operatingSystem: "Web",
      description:
        "An AI content studio for filmmakers, brands, and creators: write a scene from an idea and your own reference photos, see its price in credits, and render it on the video and image model you pick.",
      publisher: { "@id": `${SITE_URL}/#organization` },
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "USD",
        lowPrice: Math.min(...monthly),
        highPrice: Math.max(...monthly),
        offerCount: PLANS.length,
        url: `${SITE_URL}/pricing`,
      },
    },
  ],
};

export default function Home() {
  return (
    <EditorialSkin>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(HOME_JSON_LD).replace(/</g, "\\u003c") }}
      />
      <SiteHeader />
      <main className="flex-1">
        <HeroSection />
        <PipelineSequence />
        <FeatureSection />
        <FramesSection />
        <WorkSection />
        <StartingPointsSection />
        <CtaSection />
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
