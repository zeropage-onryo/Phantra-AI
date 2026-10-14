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
  // (the phantra-media bucket, served at media.phantra.ai)
  // (src/content/landing-media.ts); next/image resizes and re-encodes
  // them, so a 2MB PNG reaches the page as a ~60KB WebP.
  images: {
    remotePatterns: [{ protocol: "https", hostname: "media.phantra.ai" }],
    // the qualities the pages ask for (70 on the landing tiles, 60 on the
    // /make close); Next 16 warns on any value not listed here
    qualities: [60, 70, 75],
  },
  // Two kinds of old address go to phantra.ai for good (308).
  //
  // The site was zeropage.studio until 2026-10-13: every path on that
  // domain goes to the same path here, query string kept, so a search
  // result or an old link lands on the page it meant.
  //
  // Vercel's own host serves the same public pages, which is a duplicate
  // site to a crawler: its PUBLIC pages go to the real domain. Everything
  // else on that host -- /studio, sign-in, /auth, the API proxy, media --
  // stays, because the API's STUDIO_URL and the sign-in handoff may still
  // name it. Preview deployments have other hosts and are untouched. The
  // list is the sitemap's (src/app/sitemap.ts).
  async redirects() {
    const old = ["zeropage.studio", "www.zeropage.studio"].map((value) => ({
      source: "/:path*",
      has: [{ type: "host" as const, value }],
      destination: "https://phantra.ai/:path*",
      permanent: true,
    }));
    const host = [{ type: "host" as const, value: "zpf-web.vercel.app" }];
    const vercel = [
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
      destination: `https://phantra.ai${source}`,
      permanent: true,
    }));
    // /connector became /mcp (2026-10-12). The directory submissions named
    // /connector as the documentation URL, so it stays a permanent redirect.
    const moved = [{ source: "/connector", destination: "/mcp", permanent: true }];
    return [...old, ...moved, ...vercel];
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
      "/account/:path*",
      "/brand/:path*",
    ].map((source) => ({ source, destination: `${upstream}${source}` }));
  },
  distDir: process.env.NEXT_BUILD_DIR || ".next",
};

export default nextConfig;
