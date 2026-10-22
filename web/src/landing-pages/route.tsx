import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MakePage } from "./components/make-page";
import { getMakePage, makePath, pagesIn, type MakeSection } from "./pages";

// The one template behind every landing page, shared by the two thin
// routes (app/make/[slug] and app/models/[slug], 2026-10-05): static
// params for a section, the <head>, and the FAQPage JSON-LD. A slug asked
// for under the wrong section is a 404, so a page has exactly one URL.

export function staticParams(section: MakeSection) {
  return pagesIn(section).map((p) => ({ slug: p.slug }));
}

export function metadataFor(section: MakeSection, slug: string): Metadata {
  const page = getMakePage(slug, section);
  if (!page) return {};
  const path = makePath(page);
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: "Phantra AI",
      title: `${page.title} — Phantra AI`,
      description: page.description,
      url: path,
      locale: "en_US",
      // No `images` here on purpose: each page has its own card, the file
      // app/<section>/[slug]/opengraph-image.tsx (og.tsx, 2026-10-11), and
      // an image named in this object would be used instead of it. With
      // none named, twitter:image follows og:image.
    },
    twitter: {
      card: "summary_large_image",
      title: `${page.title} — Phantra AI`,
      description: page.description,
    },
    robots: { index: true, follow: true },
  };
}

export function LandingRoute({ section, slug }: { section: MakeSection; slug: string }) {
  const page = getMakePage(slug, section);
  if (!page) notFound();

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: page.faq.items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        // JSON.stringify output with "<" escaped: the one way a string in
        // this attribute could close the tag.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, "\\u003c") }}
      />
      <MakePage page={page} />
    </>
  );
}
