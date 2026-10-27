import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site-url";
import { MAKE_PAGES, makePath } from "@/landing-pages/pages";


// The public pages only -- everything under /studio is behind sign-in and
// disallowed in robots.ts. Every /make landing page is listed off its
// entry, so adding one there is adding it here.
export default function sitemap(): MetadataRoute.Sitemap {
  const weekly = new Set(["/", "/whats-new"]);
  const monthly = new Set(["/pricing", "/models", "/faq", "/mcp", "/mcp/claude", "/support", "/affiliates", "/download", "/plugins"]);
  const fixed = ["/", "/pricing", "/models", "/faq", "/mcp", "/mcp/claude", "/support", "/affiliates", "/plugins", "/whats-new", "/download", "/download/license", "/terms", "/privacy", "/data-deletion"].map((path) => ({
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
  return [...fixed, ...make];
}
