"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { checkSession, goToSignIn } from "@/lib/api";
import { DEFAULT_MASCOT, mascotSrc, type Mood } from "@/lib/mascot";
import { useStill } from "@/components/motion/use-still";

// The hero's front door (2026-10-11, Mike's L5 hero): Nimbus, the studio's
// default creature, asking what we are making. It replaced HeroPrompt and
// keeps its one promise -- the sentence a visitor types is carried into
// the studio composer as ?spark= rather than thrown away. A chip also
// carries the frame the composer opens in (?frame=, matched against the
// composer's own list, ignored when it is not offered).
//
// "Try for free" is true because a new workspace gets a one-time trial of
// credits (ZEROPAGE_SIGNUP_CREDITS). A visitor who is signed out goes
// through Sign up with the composer as the place to land; one who is
// signed in goes straight there. The session is asked about once, the
// first time the box is touched, so the click does not wait on it.
//
// Nothing here calls a model or spends: the creature's lines are fixed
// copy, and the images are the renders the studio already serves.

type Chip = { id: "shorts" | "reels" | "brand"; label: string; frame: string; line: string };

const CHIPS: Chip[] = [
  {
    id: "shorts",
    label: "Shorts",
    frame: "9:16",
    line: "Shorts — tell me the hook and I’ll write it as timed, vertical shots.",
  },
  { id: "reels", label: "Reels", frame: "9:16", line: "Reels — give me the idea and I’ll draw the first keyframe." },
  { id: "brand", label: "Brand ad", frame: "16:9", line: "A brand ad — I’ll keep every scene on your references." },
];

const HELLO = "Hi, I’m Nimbus. What are we making today?";
const NUDGE = "Go on — a sentence is enough.";
const TYPED = "Love it. I’ll write the scene and show you the price before anything renders.";

const face = (mood: Mood) => mascotSrc(DEFAULT_MASCOT, mood, 320);

export function HeroNimbus() {
  const router = useRouter();
  const still = useStill();
  const [spark, setSpark] = useState("");
  const [chip, setChip] = useState<Chip | null>(null);
  const [focused, setFocused] = useState(false);
  const [going, setGoing] = useState(false);
  const session = useRef<Promise<boolean> | null>(null);

  // the thinking face is fetched before it is needed, so the swap is not a
  // blink; and a page restored from the back button gets its button back
  useEffect(() => {
    const img = new Image();
    img.src = face("think");
    const back = () => setGoing(false);
    window.addEventListener("pageshow", back);
    return () => window.removeEventListener("pageshow", back);
  }, []);

  const askSession = () => {
    session.current ??= checkSession().catch(() => false);
    return session.current;
  };

  const line = spark.trim() ? TYPED : chip ? chip.line : focused ? NUDGE : HELLO;
  const mood: Mood = spark.trim() || chip ? "think" : "talk";

  async function go(event: FormEvent) {
    event.preventDefault();
    if (going) return;
    setGoing(true);
    const params = new URLSearchParams();
    if (spark.trim()) params.set("spark", spark.trim());
    if (chip) params.set("frame", chip.frame);
    const query = params.toString();
    const path = query ? `/studio?${query}` : "/studio";
    if (await askSession()) router.push(path);
    else goToSignIn("signup", path);
  }

  return (
    <form
      onSubmit={go}
      className="flex w-full flex-col gap-3 rounded-[20px] border border-border bg-card p-4 text-left lg:gap-4 lg:rounded-[24px] lg:p-5 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.9)]"
    >
      <div className="flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- a 320px webp from the mascot set, sized here */}
        <img
          src={face(mood)}
          alt=""
          width={56}
          height={56}
          className={`size-14 flex-none object-contain lg:size-16 ${still ? "" : "nimbus-bob"}`}
        />
        <div className="flex min-w-0 flex-col gap-[3px]">
          <span className="font-mono text-[10px] tracking-[0.12em] lg:text-[11px] text-[var(--ink-3)]">NIMBUS</span>
          <span aria-live="polite" className="relative min-h-[2.8em] text-[15px] leading-[1.4] lg:text-[17px] text-[#e9e7e3]">
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={line}
                className="block"
                initial={still ? false : { opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={still ? undefined : { opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
              >
                {line}
              </motion.span>
            </AnimatePresence>
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="What kind of video">
        {CHIPS.map((c) => {
          const on = chip?.id === c.id;
          return (
            <button
              key={c.id}
              type="button"
              aria-pressed={on}
              onClick={() => {
                setChip(on ? null : c);
                askSession();
              }}
              className={`h-[30px] rounded-full border px-3 text-[12px] lg:h-[34px] lg:px-3.5 lg:text-[13px] transition-colors ${
                on
                  ? "border-white/40 bg-white/[0.08] text-foreground"
                  : "border-border text-[#c6c4c0] hover:border-white/25 hover:text-foreground"
              }`}
            >
              {c.label}
            </button>
          );
        })}
      </div>

      <label htmlFor="hero-spark" className="sr-only">
        Tell Nimbus what you’re making
      </label>
      <input
        id="hero-spark"
        value={spark}
        onChange={(e) => setSpark(e.target.value)}
        onFocus={() => {
          setFocused(true);
          askSession();
        }}
        placeholder="A 15-second Short: my sneaker drops into a puddle in slow motion…"
        autoComplete="off"
        className="h-[50px] w-full rounded-xl border border-white/[0.14] bg-white/[0.04] px-4 text-[15px] lg:h-14 lg:px-5 lg:text-[16px] text-foreground outline-none transition-colors placeholder:text-[var(--ink-3)] focus:border-white/30"
      />
      <button
        type="submit"
        disabled={going}
        className="flex h-[50px] w-full items-center justify-center rounded-xl bg-foreground text-[15px] lg:h-14 lg:text-[16px] font-semibold text-background transition-opacity hover:opacity-90 disabled:opacity-70"
      >
        Try for free
      </button>
    </form>
  );
}
