import { KineticText } from "@/components/motion/kinetic-text";
import { HeroNimbus } from "@/components/landing/hero-nimbus";
import { AsciiRipple } from "@/components/landing/ascii-ripple";
import { HeroReelColumns, HeroReelStrip } from "@/components/landing/hero-reel";

// The hero (2026-10-11, Mike's pick of the L5 "Split Reel" direction, built
// on the page it replaced): the headline alone, Nimbus asking what we are
// making with "Try for free" under it, and the studio's own renders drifting
// past on the right. The sub-paragraph, the letterbox bars, the spotlight,
// the cursors and the tilted product plate were left out on purpose (Mike:
// "drop the product preview"). Below 1024px the columns give way to one
// sideways strip under the box, so a phone still sees real footage first.
const REVEAL =
  "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:fill-mode-both";

export function HeroSection() {
  return (
    <section id="studio" className="relative overflow-hidden pt-[60px] lg:h-svh lg:min-h-[720px]">
      {/* the ASCII layer (2026-10-15, Mike's "Ripple" pick): first in the
          section so the reel and the copy paint over it; a click anywhere in
          the hero drops an orange ring into the field */}
      <AsciiRipple />
      {/* the reel: everything right of the copy column, under the header, so
          the two sit flush however wide the screen is */}
      <div
        className={`absolute inset-y-0 right-0 hidden lg:block lg:left-[min(52%,800px)] ${REVEAL} motion-safe:duration-1000 motion-safe:delay-300`}
      >
        <HeroReelColumns />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-[140px] bg-gradient-to-b from-background to-transparent"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-[140px] bg-gradient-to-t from-background to-transparent"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-background to-transparent"
        />
      </div>

      <div className="relative z-10 flex h-full flex-col justify-center px-4 pb-10 pt-10 sm:px-6 lg:px-10 lg:pb-16 lg:pt-6">
        <div className="flex w-full max-w-[540px] flex-col gap-8 lg:w-[50%] lg:max-w-[660px] lg:gap-10 xl:w-[46%]">
          {/* the new-model eyebrow (2026-10-22, Kling 4.0 the day fal's API
              opened): one line above the headline, to the model's page */}
          <a
            href="/make/kling-video-generator"
            className={`${REVEAL} motion-safe:duration-700 motion-safe:delay-150 inline-flex w-fit items-center gap-2 rounded-full border border-border bg-card/60 px-3.5 py-1.5 font-mono text-[10px] tracking-[0.14em] text-[var(--ink-3)] transition-colors hover:text-[#e9e7e3] lg:text-[11px]`}
          >
            <span className="text-[#e9e7e3]">NEW</span>
            <span>KLING 4.0 IS IN THE STUDIO</span>
            <span aria-hidden="true">→</span>
          </a>
          <KineticText
            as="h1"
            trigger="mount"
            delay={0.35}
            stagger={0.06}
            text="The AI content studio that creates for you."
            className="serif text-[clamp(2.75rem,6.2vw,5.5rem)] leading-[1.0]"
          />
          <div className={`${REVEAL} motion-safe:duration-700 motion-safe:delay-[900ms]`}>
            <HeroNimbus />
          </div>
        </div>
      </div>

      {/* the reel on a phone or tablet: one strip under the box */}
      <div className={`relative pb-12 lg:hidden ${REVEAL} motion-safe:duration-700 motion-safe:delay-[1100ms]`}>
        <HeroReelStrip />
      </div>
    </section>
  );
}
