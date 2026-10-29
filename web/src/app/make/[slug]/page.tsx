import type { Metadata } from "next";
import { LandingRoute, metadataFor, staticParams } from "@/landing-pages/route";

// /make/<slug>: the "make a thing" landing pages. Everything it renders
// comes from src/landing-pages (pages.ts, entries/); this file only binds
// the section. The image-model pages live at /models/<slug>.

export const dynamicParams = false;

// Hourly (2026-10-27): a seasonal page (landing-pages/seasonal.ts) reads
// the date at render to wear its season's look, and a page built once at
// deploy would keep the look it was built with. Every page is still
// static between rebuilds.
export const revalidate = 3600;

export function generateStaticParams() {
  return staticParams("make");
}

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return metadataFor("make", slug);
}

export default async function Page({ params }: Props) {
  const { slug } = await params;
  return <LandingRoute section="make" slug={slug} />;
}
