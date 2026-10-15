"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { animate, motion, useInView, type AnimationPlaybackControls } from "motion/react";
import { EASE_OUT } from "@/lib/motion";
import { useStill } from "@/components/motion/use-still";
import { PREFILL_EVENT, STRIP_MODELS } from "@/components/landing/vesper-content";

// The small moving parts of the Vesper sections (2026-10-15). Each one is a
// client leaf that wraps server-rendered copy, and each one stands still
// under reduced motion (useStill).

/** A lantern's slow flicker: the pool, the bright core and the floor light
 *  breathe on one 7-second loop. */
const FLICKER = {
  opacity: [1, 0.93, 0.99, 0.9, 1, 0.95, 0.91, 1, 1],
  times: [0, 0.14, 0.17, 0.41, 0.46, 0.68, 0.72, 0.8, 1],
};
export function Flicker({
  className,
  breathe = false,
  style,
}: {
  className: string;
  breathe?: boolean;
  style?: CSSProperties;
}) {
  const still = useStill();
  return (
    <motion.i
      aria-hidden
      className={className}
      style={{ x: "-50%", y: "-50%", ...style }}
      animate={
        still
          ? { opacity: 1, scale: 1 }
          : { opacity: FLICKER.opacity, ...(breathe ? { scale: [1, 1.06, 0.97, 1] } : {}) }
      }
      transition={
        still
          ? { duration: 0 }
          : {
              opacity: { duration: 7, times: FLICKER.times, ease: "easeInOut", repeat: Infinity },
              scale: { duration: 7, times: [0, 0.45, 0.7, 1], ease: "easeInOut", repeat: Infinity },
            }
      }
    />
  );
}

/**
 * A section that settles as you reach it, from a VISIBLE resting state:
 * the server HTML is the finished layout and nothing is ever transparent.
 * Only a block that mounts below the fold is lowered (instantly, unseen)
 * and rises into place when it comes into view; transform only.
 */
export function Rise({ children, className }: { children: ReactNode; className?: string }) {
  const still = useStill();
  const ref = useRef<HTMLDivElement>(null);
  const [below, setBelow] = useState(false);
  const inView = useInView(ref, { once: true, amount: 0.12 });
  useEffect(() => {
    const el = ref.current;
    if (!el || still) return;
    if (el.getBoundingClientRect().top > window.innerHeight) setBelow(true);
  }, [still]);
  const lowered = below && !inView && !still;
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={false}
      animate={{ y: lowered ? 36 : 0 }}
      transition={lowered || still ? { duration: 0 } : { duration: 0.9, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

/** A card whose click puts a line into the demo's composer. */
export function PrefillButton({
  text,
  className,
  label,
  children,
  onPointerEnter,
  onPointerLeave,
  onFocus,
  onBlur,
  dataPlaying,
}: {
  text: string;
  className: string;
  label?: string;
  children: ReactNode;
  onPointerEnter?: () => void;
  onPointerLeave?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
  dataPlaying?: boolean;
}) {
  return (
    <button
      type="button"
      className={className}
      aria-label={label}
      data-playing={dataPlaying ? "true" : undefined}
      onClick={() => window.dispatchEvent(new CustomEvent(PREFILL_EVENT, { detail: text }))}
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      {children}
    </button>
  );
}

/** "Make one like these": scroll to the composer without changing it. */
export function MakeLikeLink({ className, children }: { className: string; children: ReactNode }) {
  return (
    <a
      href="#stage"
      className={className}
      onClick={(e) => {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent(PREFILL_EVENT, { detail: null }));
      }}
    >
      {children}
    </a>
  );
}

/**
 * A showcase tile: the real clip plays by itself, muted and looping, while
 * the tile is on screen AND the tab is showing (hero-reel.tsx's pattern; Mike,
 * 2026-10-15: "have the clips playing without hover"). preload="none" behind
 * the poster, so nothing loads until the tile comes into view; under reduced
 * motion the clip is never attached and the poster stands still.
 */
export function ShowcaseTile({
  mp4,
  poster,
  model,
  caption,
  ar,
}: {
  mp4: string;
  poster: string;
  model: string;
  caption: string;
  ar: string;
}) {
  const still = useStill();
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const el = video.current;
    if (!el || still) return;
    let visible = false;
    const sync = () => {
      if (visible && document.visibilityState === "visible") {
        el.play().then(
          () => setPlaying(true),
          () => setPlaying(false),
        );
      } else {
        el.pause();
        setPlaying(false);
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
    <PrefillButton
      text={caption}
      className="vh-sh"
      label={`${caption} · ${model}. Use this line`}
      dataPlaying={playing}
    >
      <span className="vh-tile" style={{ "--ar": ar } as CSSProperties}>
        {/* eslint-disable-next-line @next/next/no-img-element -- a poster that already ships in public/, sized by the tile */}
        <img src={poster} alt="" loading="lazy" decoding="async" />
        <video
          ref={video}
          src={still ? undefined : mp4}
          muted
          loop
          playsInline
          preload="none"
          aria-hidden
          tabIndex={-1}
          style={{ opacity: playing ? 1 : 0 }}
        />
        <span className="vh-tag">{model}</span>
        <span className="vh-glyph" aria-hidden>
          <span>
            <svg viewBox="0 0 16 16" fill="#fff">
              <path d="M4.5 2.8v10.4l8.5-5.2z" />
            </svg>
          </span>
        </span>
      </span>
      <span className="vh-cap">{caption}</span>
    </PrefillButton>
  );
}

/** The models strip: two copies of the list drift left on a 60-second loop
 *  and pause on hover; under reduced motion it is one wrapped, still list. */
export function ModelsDrift() {
  const still = useStill();
  const track = useRef<HTMLDivElement>(null);
  const run = useRef<AnimationPlaybackControls | null>(null);
  useEffect(() => {
    const el = track.current;
    if (!el || still) return;
    run.current = animate(el, { x: ["0%", "-50%"] }, { duration: 60, ease: "linear", repeat: Infinity });
    return () => {
      run.current?.stop();
      run.current = null;
      el.style.transform = "";
    };
  }, [still]);
  const list = (hidden: boolean) => (
    <ul aria-label={hidden ? undefined : "Models in Phantra"} aria-hidden={hidden || undefined}>
      {STRIP_MODELS.map((m) => (
        <li key={m}>{m}</li>
      ))}
    </ul>
  );
  return (
    <div
      className="vh-mq"
      data-still={still ? "true" : undefined}
      onPointerEnter={() => run.current?.pause()}
      onPointerLeave={() => run.current?.play()}
    >
      <div className="vh-mq-track" ref={track}>
        {list(false)}
        {list(true)}
      </div>
    </div>
  );
}
