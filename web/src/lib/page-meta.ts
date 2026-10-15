import type { Metadata } from "next";

// The <head> of a fixed public page (/pricing, /models, /faq, /mcp,
// /terms, /privacy).
//
// Next merges metadata SHALLOWLY: a page that sets only a title and a
// description inherits the root layout's whole `openGraph` and `twitter`
// objects, so until 2026-10-11 every one of these pages shared under the
// home page's title with og:url pointing at "/". A page says its own here.
// The landing pages under /make and /models build theirs the same way in
// landing-pages/route.tsx.
export function pageMeta({
  title,
  description,
  path,
}: {
  /** The page's own title; the root layout's template adds " — Phantra". */
  title: string;
  description: string;
  /** The page's path, which is also its canonical URL. */
  path: string;
}): Metadata {
  const shared = `${title} — Phantra`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: "Phantra",
      title: shared,
      description,
      url: path,
      locale: "en_US",
      images: [{ url: "/opengraph-image", width: 1200, height: 630, type: "image/png" }],
    },
    twitter: {
      card: "summary_large_image",
      title: shared,
      description,
      images: ["/opengraph-image"],
    },
  };
}
