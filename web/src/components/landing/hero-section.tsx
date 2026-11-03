import { ChatGptNewsBar } from "@/components/landing/chatgpt-news-bar";
import { HeroRail } from "@/components/landing/hero-rail";

// The hero (2026-11-02, Mike's pick of "B3 · Clip rail" on the Phantra Hero
// canvas, built on the 17d hero it replaces): the lemon news bar saying
// Phantra is now an approved ChatGPT app, then the picked start's clip edge
// to edge behind the headline, Vesper's box and the ChatGPT line, with the
// nine quick starts as a rail of playing clips along the bottom.
//
// The section is exactly one screen tall (header 60px + the bar + the hero
// = 100svh), so nothing sits under the fold on any monitor; a very short
// window gets a floor so the box and the rail never collide. The 17d pieces
// (hero-studio) and the older ones (hero-nimbus, hero-reel, ascii-ripple)
// stay in the tree, unused, in case Mike wants one back.
export function HeroSection() {
  return (
    <section id="studio" className="relative flex h-svh min-h-[600px] flex-col overflow-hidden pt-[60px]">
      <ChatGptNewsBar />
      <HeroRail />
    </section>
  );
}
