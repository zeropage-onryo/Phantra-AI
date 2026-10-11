"use client";

import { useEffect, useRef } from "react";
import { HERO_REEL, type ReelClip } from "@/content/hero-reel";
import { useStill } from "@/components/motion/use-still";

// The hero's reel (2026-10-11, the L5 "Split Reel" Mike picked): the
// studio's own renders, two columns drifting in opposite directions on a
// wide screen, one sideways strip under the chat box on a phone.
//
// What keeps it light: no clip loads until its tile is on screen
// (preload="none" behind a poster), a tile plays only while it is in view
// and the tab is showing, and with reduced motion nothing moves or plays --
// the posters stand still. Each list is drawn twice so the loop's seam is
// never seen; the second copy is hidden from screen readers.

function ReelTile({ clip, still }: { clip: ReelClip; still: boolean }) {
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = video.current;
    if (!el || still) return;
    let visible = false;
    const sync = () => {
      if (visible && document.visibilityState === "visible") {
        el.play().catch(() => {});
      } else {
        el.pause();
      }
    };
    const io = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        sync();
      },
      { threshold: 0.25 },
    );
    io.observe(el);
    document.addEventListener("visibilitychange", sync);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", sync);
      el.pause();
    };
  }, [still]);

  return (
    <div className="relative aspect-[9/16] w-full overflow-hidden rounded-[14px] bg-[#151413]">
      <video
        ref={video}
        src={still ? undefined : clip.mp4}
        poster={clip.poster}
        muted
        loop
        playsInline
        preload="none"
        aria-hidden
        className="block size-full object-cover"
      />
      <span className="absolute left-3 top-3 rounded-[5px] bg-black/45 px-[7px] py-1 font-mono text-[10px] uppercase tracking-[0.08em] text-white">
        {clip.model}
      </span>
    </div>
  );
}

/** Two columns, opposite directions: the wide-screen reel. */
export function HeroReelColumns() {
  const still = useStill();
  const columns = [0, 1].map((c) => HERO_REEL.filter((clip) => clip.column === c));
  return (
    <div
      role="img"
      aria-label="Clips made in Zeropage"
      className="grid h-full grid-cols-2 gap-1.5 px-1.5"
    >
      {columns.map((clips, c) => (
        <div key={c} className="h-full overflow-hidden">
          <div className={`flex flex-col ${still ? "" : c === 0 ? "hero-reel-up" : "hero-reel-down"}`}>
            {[...clips, ...clips].map((clip, i) => (
              // padding, not gap: the loop moves by exactly half its height,
              // so every tile carries its own spacing
              <div key={i} className="pb-1.5" aria-hidden={i >= clips.length || undefined}>
                <ReelTile clip={clip} still={still} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/** One sideways strip: the reel on a phone. */
export function HeroReelStrip() {
  const still = useStill();
  // alternate the two columns so a phone sees the same mix of looks
  const left = HERO_REEL.filter((c) => c.column === 0);
  const right = HERO_REEL.filter((c) => c.column === 1);
  const clips = Array.from({ length: Math.max(left.length, right.length) }, (_, i) => [left[i], right[i]])
    .flat()
    .filter((c): c is ReelClip => Boolean(c));
  return (
    <div role="img" aria-label="Clips made in Zeropage" className="hero-reel-strip-mask overflow-hidden">
      <div className={`flex w-max ${still ? "" : "hero-reel-side"}`}>
        {[...clips, ...clips].map((clip, i) => (
          <div key={i} className="w-[38vw] max-w-[180px] shrink-0 pr-2" aria-hidden={i >= clips.length || undefined}>
            <ReelTile clip={clip} still={still} />
          </div>
        ))}
      </div>
    </div>
  );
}
