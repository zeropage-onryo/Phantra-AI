import type { Metadata } from "next";
import { EditorialSkin } from "@/components/editorial-skin";
import { PLANS } from "@/lib/catalog";
import { SITE_URL } from "@/lib/site-url";
import { SOCIALS } from "@/lib/socials";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { HeroSection } from "@/components/landing/hero-section";
import {
  ClosingCtaSection,
  ModelsStripSection,
  ShowcaseSection,
  StartAnywhereSection,
  VesperSection,
} from "@/components/landing/vesper-sections";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

// What the home page tells a search engine the site IS (2026-10-11). The
// /make and /models pages carry their own FAQPage block; until today the
// home page carried none. Prices come off pricing.json (the generated
// catalogue), never typed here. Since 2026-10-15 the organisation and the
// app are "Phantra AI", and the app's description names its agent, Vesper.
const monthly = PLANS.map((p) => p.monthly_usd);
const HOME_JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: "Phantra AI",
      url: SITE_URL,
      // the accounts in the header's Resources menu (2026-10-23)
      sameAs: SOCIALS.map((s) => s.href),
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: "Phantra",
      url: SITE_URL,
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
    {
      "@type": "SoftwareApplication",
      name: "Phantra AI",
      url: SITE_URL,
      applicationCategory: "MultimediaApplication",
      operatingSystem: "Web",
      description:
        "An AI content studio with its own AI agent, Vesper, for filmmakers, brands, and creators: tell the agent what you are making and it plans the shots, writes the scene from your idea and reference photos, shows its price in credits, and renders it on the video and image model you pick.",
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
        <VesperSection />
        {/* on a phone (2026-10-26, the "Phantra Mobile Studio" canvas) the
            page is the hero, Vesper, one reel and the closing call: the
            starting points and the model strip are for wider screens */}
        <div className="hidden md:block">
          <StartAnywhereSection />
        </div>
        <ShowcaseSection />
        <div className="hidden md:block">
          <ModelsStripSection />
        </div>
        <ClosingCtaSection />
      </main>
      <SiteFooter compact />
    </EditorialSkin>
  );
}
