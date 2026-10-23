import { ClipPlayer } from "./clips";
import { REVEAL_CLASS as REVEAL } from "@/lib/motion";
import type { MakePage } from "../pages";

// The "knockout" hero (2026-10-23, the Grok Imagine page, direction C of
// the canvas Mike picked): one huge word with the page's clip playing
// INSIDE its letters, then the H1, one line and the buttons. No caption,
// no eyebrow (the no-small-wording rule).
//
// How the letters become a window: the clip (or, until it lands, a drifting
// marigold plate) sits behind a black layer with the word in white on it,
// blended `multiply` inside the group: white x clip = the clip, black x
// clip = black. The group itself is blended `screen` onto the page, and
// screen(black, ground) is the ground exactly, so no box shows around the
// word whatever the clip's edges are. Plain CSS, every modern browser; the
// word stays real text for layout (aria-hidden: the H1 below is the
// heading). The clip plays muted; its sound belongs to the reel below.
export function KnockoutHero({ page, Buttons }: { page: MakePage; Buttons: (p: { page: MakePage; align?: "center" | "start" }) => React.ReactNode }) {
  const tile = page.heroMedia?.[0];
  const word = page.heroWord ?? page.h1;
  return (
    <section className="relative overflow-hidden pt-[60px]">
      <style>{`
        @keyframes knockout-drift { 0% { background-position: 0% 50% } 100% { background-position: 100% 50% } }
        .knockout-plate { background-image: linear-gradient(110deg, #2a1f06 0%, #a8740a 20%, var(--primary) 36%, #ffe08a 46%, #3a2a08 58%, #e09a0c 72%, #1a1406 86%, var(--primary) 100%); background-size: 300% 100%; animation: knockout-drift 14s linear infinite alternate; }
        @media (prefers-reduced-motion: reduce) { .knockout-plate { animation: none } }
      `}</style>
      {/* bg-background: the entrance makes this wrapper its own stacking
          context, so the `screen` below blends against THIS ground, not the
          page's; painting it the ground keeps the two the same */}
      <div className={`mx-auto max-w-[1440px] bg-background px-2 pt-8 md:px-6 md:pt-12 ${REVEAL} motion-safe:duration-1000`}>
        <div aria-hidden className="relative select-none overflow-hidden mix-blend-screen">
          <div className="absolute inset-0">
            {tile?.video ? <ClipPlayer tile={tile} sound={false} eager /> : <div className="knockout-plate absolute inset-0" />}
          </div>
          <div className="relative bg-black text-center font-sans text-[clamp(6.5rem,25vw,22.5rem)] font-black leading-[0.82] tracking-[-0.06em] text-white mix-blend-multiply">
            {word}
          </div>
        </div>
      </div>

      <div className="mx-auto flex max-w-[1200px] flex-col gap-8 px-4 pb-16 pt-12 md:flex-row md:items-end md:justify-between md:px-6 md:pb-24 md:pt-16">
        <div className="max-w-[640px]">
          <h1 className={`serif serif-bold text-[clamp(2.6rem,5.4vw,4.4rem)] leading-[1.04] ${REVEAL} motion-safe:duration-700`}>{page.h1}</h1>
          <p
            className={`mt-6 max-w-[46ch] text-[clamp(1.05rem,1.5vw,1.2rem)] leading-normal text-[var(--ink-2)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-100`}
          >
            {page.subhead}
          </p>
        </div>
        <div className="shrink-0 [&>div]:mt-0">
          <Buttons page={page} align="start" />
        </div>
      </div>
    </section>
  );
}
