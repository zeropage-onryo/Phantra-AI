import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site-url";
import { MAKE_PAGES, makePath } from "@/landing-pages/pages";
import { allPublicEffects } from "@/lib/public-effects-data";


// The public pages only -- everything under /studio is behind sign-in and
// disallowed in robots.ts. Every /make landing page is listed off its
// entry, so adding one there is adding it here.
export default function sitemap(): MetadataRoute.Sitemap {
  const weekly = new Set(["/", "/whats-new"]);
  const monthly = new Set(["/make", "/pricing", "/models", "/faq", "/mcp", "/mcp/claude", "/support", "/affiliates", "/creators", "/download", "/plugins"]);
  const fixed = ["/", "/make", "/pricing", "/models", "/faq", "/mcp", "/mcp/claude", "/support", "/affiliates", "/creators", "/plugins", "/whats-new", "/download", "/download/license", "/terms", "/privacy", "/data-deletion"].map((path) => ({
    url: `${SITE_URL}${path === "/" ? "" : path}`,
    changeFrequency: (weekly.has(path) ? "weekly" : monthly.has(path) ? "monthly" : "yearly") as
      | "weekly"
      | "monthly"
      | "yearly",
    priority: path === "/" ? 1 : path === "/whats-new" ? 0.8 : monthly.has(path) ? 0.7 : 0.3,
  }));
  const make = MAKE_PAGES.map((page) => ({
    url: `${SITE_URL}${makePath(page)}`,
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));
  // the public effects (2026-11-05): the gallery and one page per effect
  // with a kept showcase example, off the same list the pages are built from
  const effects = [
    { url: `${SITE_URL}/effects`, changeFrequency: "weekly" as const, priority: 0.8 },
    ...allPublicEffects().map((e) => ({
      url: `${SITE_URL}/effects/${e.slug}`,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
  return [...fixed, ...make, ...effects];
}
