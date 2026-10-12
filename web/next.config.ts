import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone is what the Fly image runs (node server.js on a copied
  // .next/standalone); on Vercel the platform packages the app itself and
  // its build hook looks for tracing files standalone does not write
  // (next-server.js.nft.json -- ENOENT on the first Vercel build, 2026-09-14)
  output: process.env.VERCEL ? undefined : "standalone",
  // the in-app Browser pane and curl reach the dev server as 127.0.0.1
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // The landing page's frames are the studio's own keyframes on R2
  // (src/content/landing-media.ts); next/image resizes and re-encodes
  // them, so a 2MB PNG reaches the page as a ~60KB WebP.
  images: {
    remotePatterns: [{ protocol: "https", hostname: "*.r2.dev" }],
    // the qualities the pages ask for (70 on the landing tiles, 60 on the
    // /make close); Next 16 warns on any value not listed here
    qualities: [60, 70, 75],
  },
  // Vercel's own host serves the same public pages as zeropage.studio, which
  // is a duplicate site to a crawler. Its PUBLIC pages go to the real domain
  // for good (308). Everything else -- /studio, sign-in, /auth, the API proxy,
  // media -- stays on this host, because the API's STUDIO_URL and the sign-in
  // handoff may still name it. Preview deployments have other hosts and are
  // untouched. The list is the sitemap's (src/app/sitemap.ts). 2026-10-11.
  async redirects() {
    const host = [{ type: "host" as const, value: "zpf-web.vercel.app" }];
    // /connector became /mcp (2026-10-12). The directory submissions name
    // /connector as the documentation URL, so it stays a permanent redirect.
    const moved = [
      { source: "/connector", destination: "/mcp", permanent: true },
    ];
    return [
      ...moved,
      ...[
        "/",
        "/pricing",
        "/models",
        "/models/:slug",
        "/make/:slug",
        "/faq",
        "/mcp",
        "/terms",
        "/privacy",
        "/sitemap.xml",
        "/robots.txt",
      ].map((source) => ({
        source,
        has: host,
        destination: `https://zeropage.studio${source}`,
        permanent: true,
      })),
    ];
  },
  // A separate build directory lets production validation run alongside dev.
  async rewrites() {
    const upstream = process.env.API_UPSTREAM || "http://localhost:8000";
    return [
      "/api/:path*",
      "/ui",
      "/ui/:path*",
      "/signin",
      "/auth/:path*",
      "/refs/:path*",
      "/renders/:path*",
      "/characters/:path*",
      "/props/:path*",
      "/locations/:path*",
      "/static/:path*",
      "/brand/:path*",
    ].map((source) => ({ source, destination: `${upstream}${source}` }));
  },
  distDir: process.env.NEXT_BUILD_DIR || ".next",
};

export default nextConfig;
