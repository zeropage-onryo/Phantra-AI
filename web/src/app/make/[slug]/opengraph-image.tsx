import { ogCard, OG_ALT, OG_SIZE, OG_TYPE } from "@/landing-pages/og";
import { pagesIn } from "@/landing-pages/pages";

// /make/<slug>'s own share card: the page's name, its accent and one
// of its stills (landing-pages/og.tsx). This file only binds the section.
//
// generateStaticParams is what makes Next draw every card at BUILD time,
// when the stills are on disk. (With generateImageMetadata, which would
// give each card its own alt text, the route gains a segment the build
// has no params for and each card is drawn on its first request instead.)

// a slug with no page has no card either (never drawn on request)
export const dynamicParams = false;

export const alt = OG_ALT;
export const size = OG_SIZE;
export const contentType = OG_TYPE;

export function generateStaticParams() {
  return pagesIn("make").map((page) => ({ slug: page.slug }));
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return ogCard("make", slug);
}
