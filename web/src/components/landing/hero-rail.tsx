"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/mcp/brand-logos";
import { checkSession, goToSignIn } from "@/lib/api";
import { CHATGPT_PLUGIN_URL } from "@/lib/connect-claude";
import { DEFAULT_MASCOT, mascotSrc } from "@/lib/mascot";
import { clipSrc } from "@/landing-pages/media";
import { HERO_STARTS, type HeroStart } from "@/content/hero-starts";
import { HeroDrawer, type DrawerChoice } from "@/components/landing/hero-drawer";

// The hero's working half since 2026-11-02 (Mike's pick of "B3 · Clip rail"
// on the Phantra Hero canvas, replacing the 17d preview card, whose fixed
// tall box cropped every 16:9 clip and left a gap on wide screens). The
// picked start's clip fills the whole hero; a vertical clip is drawn as a
// phone-shaped card on a wide screen instead of being stretched across it.
// The nine quick starts are a rail of playing clips along the bottom; a tile
// switches the clip and opens the side drawer ("Popup 2"), as the chips did.
// Until someone touches anything, the hero moves to the next start every
// six seconds.
//
// Sizing: the section is exactly one screen tall (hero-section.tsx), so the
// copy, the type and the rail are sized off the viewport, never a fixed
// height, and nothing sits below the fold.
//
// Playing: React does not write `muted` into server-rendered HTML, so a
// browser would refuse autoplay; every clip sets muted itself and asks to
// play when it mounts and again when it can. Clips come from the R2 bucket
// through clipSrc; nothing here calls a model or spends.

const ADVANCE_MS = 6000;
const FADE_MS = 1000;

const REVEAL =
  "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:fill-mode-both";

/** a ref that makes a <video> play muted, inline and on a loop */
function playMuted(el: HTMLVideoElement | null) {
  if (!el) return;
  el.muted = true;
  el.defaultMuted = true;
  el.playsInline = true;
  el.loop = true;
  const go = () => {
    if (el.paused) el.play().catch(() => {});
  };
  go();
  el.addEventListener("canplay", go, { once: true });
}

function useWide() {
  const [wide, setWide] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return wide;
}

export function HeroRail() {
  const router = useRouter();
  const wide = useWide();
  const [picked, setPicked] = useState(0);
  const [prev, setPrev] = useState<number | null>(null);
  const [auto, setAuto] = useState(true);
  const [open, setOpen] = useState(false);
  const [spark, setSpark] = useState("");
  const [going, setGoing] = useState(false);
  const session = useRef<Promise<boolean> | null>(null);
  const fade = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = HERO_STARTS[picked];

  // a page restored from the back button gets its buttons back
  useEffect(() => {
    const back = () => setGoing(false);
    window.addEventListener("pageshow", back);
    return () => window.removeEventListener("pageshow", back);
  }, []);

  const show = useCallback((i: number) => {
    setPicked((cur) => {
      if (cur === i) return cur;
      setPrev(cur);
      if (fade.current) clearTimeout(fade.current);
      fade.current = setTimeout(() => setPrev(null), FADE_MS + 100);
      return i;
    });
  }, []);

  // the hero walks through the starts on its own until someone touches it;
  // with reduced motion it holds still
  useEffect(() => {
    if (!auto || open) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => show((picked + 1) % HERO_STARTS.length), ADVANCE_MS);
    return () => clearInterval(t);
  }, [auto, open, picked, show]);

  useEffect(() => () => {
    if (fade.current) clearTimeout(fade.current);
  }, []);

  const askSession = () => {
    session.current ??= checkSession().catch(() => false);
    return session.current;
  };

  async function go(params: URLSearchParams) {
    if (going) return;
    setGoing(true);
    const query = params.toString();
    const path = query ? `/studio?${query}` : "/studio";
    if (await askSession()) router.push(path);
    else goToSignIn("signup", path);
  }

  function submitBox(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (spark.trim()) params.set("spark", spark.trim());
    void go(params);
  }

  function startFromDrawer(choice: DrawerChoice) {
    const params = new URLSearchParams();
    const idea = choice.idea.trim();
    const words = [`${start.label}${idea ? `: ${idea.replace(/[.\s]+$/, "")}` : ""}.`, `Look: ${choice.look}.`];
    if (start.kind === "image") words.push(`${choice.length.label}.`);
    params.set("spark", words.join(" "));
    params.set("kind", start.kind);
    params.set("frame", choice.frame);
    if (start.kind === "video" && choice.length.seconds) params.set("seconds", String(choice.length.seconds));
    void go(params);
  }

  const close = useCallback(() => setOpen(false), []);
  const layers = prev === null ? [picked] : [prev, picked];

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* the clip, edge to edge: the outgoing one stays under the incoming one
          while it fades in */}
      <div aria-hidden className="absolute inset-0 overflow-hidden bg-[#0b0a08]">
        {layers.map((i) => (
          <BackdropClip key={HERO_STARTS[i].id} start={HERO_STARTS[i]} fadeIn={i === picked && prev !== null} />
        ))}
        <div className="absolute inset-0 bg-[rgba(10,10,10,0.55)] lg:bg-[linear-gradient(90deg,rgba(10,10,10,0.92)_0%,rgba(10,10,10,0.72)_30%,rgba(10,10,10,0.06)_56%,rgba(10,10,10,0)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-[42%] bg-gradient-to-t from-background via-[rgba(10,10,10,0.8)] to-transparent" />
      </div>

      <div className="relative flex min-h-0 flex-1 items-center px-4 sm:px-6 lg:px-10 xl:px-20">
        {/* a vertical clip on a wide screen: a phone-shaped card on the right,
            inside the copy's band so it never runs into the rail */}
        {wide &&
          layers.map((i) =>
            HERO_STARTS[i].clip.tall ? <PhoneCard key={HERO_STARTS[i].id} start={HERO_STARTS[i]} fadeIn={i === picked && prev !== null} /> : null,
          )}

        <div className="relative flex w-full max-w-[640px] flex-col gap-[clamp(14px,2.6svh,28px)] py-[clamp(12px,3svh,40px)] lg:w-[min(46%,860px)] lg:max-w-none">
          <h1
            className={`serif text-[clamp(2.4rem,min(6vw,8.6svh),6.5rem)] leading-[0.97] tracking-[-0.02em] [text-shadow:0_4px_40px_rgba(0,0,0,0.5)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-150`}
          >
            AI image &amp; video, <span className="text-[var(--lemon)]">made</span> for you.
          </h1>

          <form
            onSubmit={submitBox}
            className={`flex items-center gap-3 rounded-[22px] border border-white/15 bg-[rgba(21,20,19,0.74)] py-2.5 pl-3.5 pr-2.5 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.9)] backdrop-blur-xl lg:max-w-[760px] ${REVEAL} motion-safe:duration-700 motion-safe:delay-300`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- a 320px webp from the mascot set, sized here */}
            <img
              src={mascotSrc(DEFAULT_MASCOT, "talk", 320)}
              alt="Vesper"
              width={48}
              height={48}
              className="size-11 flex-none object-contain lg:size-12"
            />
            <label htmlFor="hero-spark" className="sr-only">
              Tell Vesper what you’re making
            </label>
            <input
              id="hero-spark"
              value={spark}
              onChange={(e) => setSpark(e.target.value)}
              onFocus={() => {
                setAuto(false);
                void askSession();
              }}
              placeholder={start.example}
              autoComplete="off"
              className="min-h-11 min-w-0 flex-1 bg-transparent text-[16px] text-foreground outline-none placeholder:text-[#a9a6a1] lg:text-[17px] 2xl:text-[19px]"
            />
            <button
              type="submit"
              disabled={going}
              className="h-12 flex-none rounded-full bg-[var(--lemon)] px-5 text-[15px] font-semibold text-[var(--lemon-ink)] transition-[filter] hover:brightness-105 disabled:opacity-70 lg:px-6 lg:text-[16px] 2xl:h-14 2xl:px-7 2xl:text-[17px]"
            >
              Start free
            </button>
          </form>

          <a
            href={CHATGPT_PLUGIN_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={`inline-flex w-fit items-center gap-2.5 text-[15px] font-semibold text-[#e9e7e3] transition-colors hover:text-foreground lg:text-[16px] 2xl:text-[17px] ${REVEAL} motion-safe:duration-700 motion-safe:delay-[400ms]`}
          >
            <BrandLogo name="openai" className="size-5 flex-none" />
            <span>
              Or ask for it in ChatGPT: <span className="text-[var(--lemon)]">“@Phantra {start.ask}”</span>
            </span>
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        </div>
      </div>

      {/* the quick starts: nine playing clips. A row that fills the width on a
          wide screen; a strip that scrolls sideways on a phone or tablet */}
      <div
        role="group"
        aria-label="Quick starts"
        className={`relative flex flex-none snap-x snap-mandatory scroll-px-4 gap-3 overflow-x-auto px-4 pb-[clamp(14px,3svh,44px)] pt-2 [scrollbar-width:none] sm:px-6 lg:grid lg:snap-none lg:grid-cols-9 lg:overflow-visible lg:px-10 xl:gap-4 xl:px-20 sm:scroll-px-6 [&::-webkit-scrollbar]:hidden ${REVEAL} motion-safe:duration-700 motion-safe:delay-500`}
      >
        {HERO_STARTS.map((s, i) => (
          <RailTile
            key={s.id}
            start={s}
            on={i === picked}
            running={auto && !open}
            playing={wide}
            onPick={() => {
              setAuto(false);
              show(i);
              setOpen(true);
              void askSession();
            }}
          />
        ))}
      </div>

      {open && <HeroDrawer key={start.id} start={start} idea={spark} going={going} onClose={close} onStart={startFromDrawer} />}
    </div>
  );
}

function BackdropClip({ start, fadeIn }: { start: HeroStart; fadeIn: boolean }) {
  return (
    <div className={`absolute inset-0 ${fadeIn ? "motion-safe:animate-in motion-safe:fade-in motion-safe:duration-1000" : ""}`}>
      <video
        ref={playMuted}
        src={clipSrc(start.clip.src)}
        poster={start.clip.poster}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        className={`absolute inset-0 size-full object-cover ${
          start.clip.tall ? "lg:scale-110 lg:blur-[40px] lg:brightness-50 lg:saturate-150" : ""
        }`}
      />
    </div>
  );
}

function PhoneCard({ start, fadeIn }: { start: HeroStart; fadeIn: boolean }) {
  return (
    <div
      aria-hidden
      className={`absolute bottom-[clamp(12px,3svh,40px)] right-[clamp(40px,11vw,300px)] top-[clamp(12px,3svh,40px)] aspect-[9/16] overflow-hidden rounded-[26px] shadow-[0_0_0_2px_var(--lemon),0_50px_120px_rgba(0,0,0,0.7)] ${
        fadeIn ? "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-6 motion-safe:duration-700" : ""
      }`}
    >
      <video
        ref={playMuted}
        src={clipSrc(start.clip.src)}
        poster={start.clip.poster}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        className="block size-full object-cover"
      />
    </div>
  );
}

function RailTile({
  start,
  on,
  running,
  playing,
  onPick,
}: {
  start: HeroStart;
  on: boolean;
  running: boolean;
  playing: boolean;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      aria-haspopup="dialog"
      aria-pressed={on}
      onClick={onPick}
      className={`group flex w-[clamp(132px,34vw,200px)] flex-none snap-start flex-col gap-2 rounded-[16px] text-left outline-none transition-opacity focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--lemon)] lg:w-auto ${
        on ? "opacity-100" : "opacity-80 hover:opacity-100"
      }`}
    >
      <span
        className={`relative block aspect-video w-full overflow-hidden rounded-[14px] bg-[#151413] transition-[box-shadow,transform] duration-300 group-hover:-translate-y-1 2xl:rounded-[18px] ${
          on ? "shadow-[0_0_0_3px_var(--lemon),0_24px_60px_rgba(0,0,0,0.6)]" : "shadow-[0_0_0_1px_rgba(255,255,255,0.14)]"
        }`}
      >
        {playing ? (
          <video
            ref={playMuted}
            src={clipSrc(start.clip.src)}
            poster={start.clip.poster}
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            className="absolute inset-0 block size-full object-cover"
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- the clip's shipped poster, a thumbnail
          <img src={start.clip.poster} alt="" className="absolute inset-0 block size-full object-cover" />
        )}
        {on && running && (
          <span aria-hidden className="absolute inset-x-0 bottom-0 h-1 bg-black/50">
            <span
              className="block h-full origin-left bg-[var(--lemon)] motion-safe:animate-[hero-rail-fill_6s_linear_both]"
            />
          </span>
        )}
      </span>
      <span
        className={`text-[15px] leading-tight transition-colors 2xl:text-[17px] ${
          on ? "font-bold text-[var(--lemon)]" : "font-medium text-foreground"
        }`}
      >
        {start.label}
      </span>
    </button>
  );
}
