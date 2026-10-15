"use client";

import { useEffect, useId, useRef } from "react";
import { motion, useAnimationControls, useReducedMotion } from "motion/react";

import { OWL, POSES, VIEWBOX, WALL, WORD } from "@/components/owl-lockup-paths";

// The Phantra lockup: the owl hiding behind the lowercase lettering.
//
// With `intro`, the owl makes one round when the page loads, and again whenever
// the pointer comes onto the logo: it peers over the top of the word, ducks
// behind it and peers up from below, leans out past the last "a", then slides
// back behind the word to rest at the left, behind the p. The owl is clipped by
// the WALL (the letters plus the band between x-height and baseline), so while
// it moves it is only ever seen around the word, never over it.
//
// Reduced motion, or no `intro`: the lockup at rest, nothing moves.

const { top, below, side } = POSES;

// [hold, move] pairs in seconds, so the timing reads like a shot list.
const BEATS = [
  0.5, // rest
  0.7, 1.1, // up and over the top, look
  0.9, 1.1, // down behind the word, peer up from below, look
  0.8, 1.1, // out past the last a, look
  1.2, // back behind the word to the left
] as const;

const TOTAL = BEATS.reduce((a, b) => a + b, 0);
const TIMES = BEATS.reduce<number[]>((acc, beat) => [...acc, (acc[acc.length - 1] ?? 0) + beat / TOTAL], [0]);

const ROUND = {
  x: [0, 0, top.x, top.x, below.x, below.x, side.x, side.x, 0],
  y: [0, 0, top.y, top.y, below.y, below.y, side.y, side.y, 0],
  transition: { duration: TOTAL, times: TIMES, ease: "easeInOut" as const },
};

export function OwlLockup({ intro = false, className = "" }: { intro?: boolean; className?: string }) {
  const clip = `owl-wall-${useId().replace(/:/g, "")}`;
  const reduce = useReducedMotion();
  const controls = useAnimationControls();
  const running = useRef(false);
  const animated = intro && !reduce;

  const play = async () => {
    if (!animated || running.current) return;
    running.current = true;
    try {
      await controls.start(ROUND);
    } finally {
      running.current = false;
    }
  };

  useEffect(() => {
    if (!animated) return;
    const t = window.setTimeout(play, 600);
    return () => window.clearTimeout(t);
    // play is stable for a given `animated`
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [animated]);

  const { x, y, w, h } = VIEWBOX;
  // Everything outside the wall, as one even-odd path: a huge rectangle with the wall cut out.
  const outsideWall = `M-4000 -4000 H4000 V4000 H-4000 Z ${WALL}`;

  return (
    <svg
      viewBox={`${x} ${y} ${w} ${h}`}
      className={`overflow-visible ${className}`}
      aria-hidden
      focusable="false"
      onPointerEnter={play}
    >
      <defs>
        <clipPath id={clip} clipPathUnits="userSpaceOnUse">
          <path d={outsideWall} clipRule="evenodd" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>
        <motion.g initial={{ x: 0, y: 0 }} animate={controls}>
          <path d={OWL} fill="currentColor" fillRule="evenodd" />
        </motion.g>
      </g>
      <path d={WORD} fill="currentColor" fillRule="evenodd" />
    </svg>
  );
}
