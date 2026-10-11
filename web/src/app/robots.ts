import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site-url";


// The landing page is the indexed surface. /studio is the signed-in
// product and /api/ is the proxy to FastAPI -- neither is for crawlers.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/studio", "/api/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
