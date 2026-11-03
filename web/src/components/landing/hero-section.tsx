import { ChatGptNewsBar } from "@/components/landing/chatgpt-news-bar";
import { HeroStudio } from "@/components/landing/hero-studio";

// The hero (2026-11-02, Mike's pick of "17d" on the Phantra Homepage canvas,
// built on the page it replaced, which was the L5 "Split Reel" of
// 2026-10-11): the lemon news bar saying Phantra is now an approved ChatGPT
// app, then the headline, Vesper's box, the ChatGPT line and nine quick
// starts on the left, and the picked start's picture large on the right. A
// quick start opens the side drawer ("Popup 2"). Every other section of the
// homepage is unchanged. The old hero's pieces (hero-nimbus, hero-reel,
// ascii-ripple) are left in the tree, unused, in case Mike wants one back.
export function HeroSection() {
  return (
    <section id="studio" className="relative overflow-hidden pt-[60px]">
      <ChatGptNewsBar />
      <div className="relative px-4 pb-12 pt-10 sm:px-6 lg:flex lg:min-h-[max(720px,calc(100svh-120px))] lg:items-center lg:px-10 lg:pb-16 lg:pt-8 xl:px-20">
        <HeroStudio />
      </div>
    </section>
  );
}
