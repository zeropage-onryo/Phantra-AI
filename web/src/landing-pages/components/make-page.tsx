import { Fragment, type ReactNode } from "react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { MakeHero } from "./make-hero";
import { Signature } from "./signatures";
import { OverviewSection } from "./overview-section";
import { AdWall } from "./ad-wall";
import { FeaturesSection } from "./features-section";
import { ModelsSection } from "./models-section";
import { HowToSection } from "./how-to-section";
import { PricingSection } from "./pricing-section";
import { FaqSection } from "./faq-section";
import { RelatedSection } from "./related-section";
import { FinalCta } from "./final-cta";
import { SeasonalAtmosphere } from "./seasonal-atmosphere";
import { accentVars } from "../theme";
import { inSeason } from "../seasonal";
import { DEFAULT_ORDER, type MakePage as MakePageEntry, type MakeSectionKey } from "../pages";

// The whole /make page from one entry. The hero always comes first; the
// sections after it follow the entry's `layout.order` (2026-10-08, so no two
// pages are the same page), defaulting to the order the brief fixed: the
// overview when the entry carries one, the signature when it names one, the
// wall, features, models, how-to, FAQ, related, final CTA. Same header,
// footer and skin as the homepage; the entry's accent rides on the skin
// wrapper as CSS variables (theme.ts).
//
// A seasonal page (seasonal.ts) wears its season's accent and the
// atmosphere layer while the season is on. The date is read at render, so
// app/make/[slug] revalidates hourly: a statically built page would keep
// the look it was built with until the next deploy.
export function MakePage({ page }: { page: MakePageEntry }) {
  const order = page.layout?.order ?? DEFAULT_ORDER;
  const seasonal = page.season != null && inSeason(page.season);
  const accent = seasonal ? (page.season?.accent ?? page.accent) : page.accent;
  const section: Record<MakeSectionKey, () => ReactNode> = {
    overview: () => <OverviewSection page={page} />,
    signature: () => <Signature page={page} />,
    wall: () => <AdWall page={page} />,
    features: () => <FeaturesSection page={page} />,
    models: () => <ModelsSection page={page} />,
    howTo: () => <HowToSection page={page} />,
    pricing: () => <PricingSection page={page} />,
    faq: () => <FaqSection title={page.faq.title} items={page.faq.items} />,
    related: () => <RelatedSection page={page} />,
    final: () => <FinalCta page={page} />,
  };
  return (
    <EditorialSkin tone={page.tone} style={accentVars(accent)}>
      <SiteHeader />
      <main className="relative flex-1">
        {seasonal && <SeasonalAtmosphere />}
        <MakeHero page={page} />
        {order.map((key) => (
          <Fragment key={key}>{section[key]()}</Fragment>
        ))}
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
