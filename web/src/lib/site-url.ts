// The public origin every absolute URL a crawler reads is built from: the
// canonical tags (layout.tsx's metadataBase), sitemap.xml and robots.txt.
//
// It used to fall back to Vercel's own deployment URL, and Vercel never had
// NEXT_PUBLIC_SITE_URL set, so until 2026-10-11 every canonical tag, the
// sitemap and robots.txt told Google the site lived at
// zpf-web.vercel.app. The fallback is the real domain now; the variable is
// only for a preview or another host.
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://phantra.ai").replace(/\/+$/, "");

// Vercel's deployment host. It serves the same pages, so next.config.ts
// sends its PUBLIC pages to SITE_URL (the studio, sign-in and the API proxy
// stay where they are).
export const VERCEL_HOST = "zpf-web.vercel.app";
