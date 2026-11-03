"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/mcp/brand-logos";
import { checkSession, goToSignIn } from "@/lib/api";
import { CHATGPT_PLUGIN_URL } from "@/lib/connect-claude";
import { DEFAULT_MASCOT, mascotSrc } from "@/lib/mascot";
import { HERO_STARTS, type HeroStart } from "@/content/hero-starts";
import { HeroDrawer, type DrawerChoice } from "@/components/landing/hero-drawer";

// The hero's working half (2026-11-02, Mike's "17d" pick on the Phantra
// Homepage canvas): the headline, Vesper's box, the line that says the same
// ask works in ChatGPT, nine quick starts and, on a wide screen, the big
// preview that follows the chip last picked. A chip opens the side drawer.
//
// It keeps the old hero's one promise: what a visitor types is carried into
// the studio composer (?spark=), never thrown away. A visitor who is signed
// out goes through Sign up with the composer as the place to land; one who
// is signed in goes straight there. The session is asked about once, the
// first time anything is touched, so a click does not wait on it. Nothing
// here calls a model or spends.

const REVEAL =
  "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:fill-mode-both";

export function HeroStudio() {
  const router = useRouter();
  const [picked, setPicked] = useState(0);
  const [open, setOpen] = useState(false);
  const [spark, setSpark] = useState("");
  const [going, setGoing] = useState(false);
  const session = useRef<Promise<boolean> | null>(null);
  const start = HERO_STARTS[picked];

  // a page restored from the back button gets its buttons back
  useEffect(() => {
    const back = () => setGoing(false);
    window.addEventListener("pageshow", back);
    return () => window.removeEventListener("pageshow", back);
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

  return (
    <>
      <div className="flex w-full flex-col gap-6 lg:w-[min(50%,720px)] lg:gap-7">
        <h1
          className={`serif text-[clamp(2.75rem,6vw,5.25rem)] leading-[0.98] tracking-[-0.02em] ${REVEAL} motion-safe:duration-700 motion-safe:delay-150`}
        >
          AI image &amp; video, <span className="text-[var(--lemon)]">made</span> for you.
        </h1>

        <form
          onSubmit={submitBox}
          className={`flex items-center gap-3 rounded-[22px] border border-[#343331] bg-card py-2.5 pl-3.5 pr-2.5 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.9)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-300`}
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
            onFocus={() => void askSession()}
            placeholder={start.example}
            autoComplete="off"
            className="min-h-11 min-w-0 flex-1 bg-transparent text-[16px] text-foreground outline-none placeholder:text-[var(--ink-3)] lg:text-[17px]"
          />
          <button
            type="submit"
            disabled={going}
            className="h-12 flex-none rounded-full bg-[var(--lemon)] px-5 text-[15px] font-semibold text-[var(--lemon-ink)] transition-[filter] hover:brightness-105 disabled:opacity-70 lg:px-6 lg:text-[16px]"
          >
            Start free
          </button>
        </form>

        <a
          href={CHATGPT_PLUGIN_URL}
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex w-fit items-center gap-2.5 text-[15px] font-semibold text-[#e9e7e3] transition-colors hover:text-foreground lg:text-[16px] ${REVEAL} motion-safe:duration-700 motion-safe:delay-[400ms]`}
        >
          <BrandLogo name="openai" className="size-5 flex-none" />
          <span>
            Or ask for it in ChatGPT: <span className="text-[var(--lemon)]">“@Phantra {start.ask}”</span>
          </span>
          <span className="sr-only">(opens in a new tab)</span>
        </a>

        <div
          role="group"
          aria-label="Quick starts"
          className={`grid grid-cols-2 gap-2.5 sm:grid-cols-3 ${REVEAL} motion-safe:duration-700 motion-safe:delay-500`}
        >
          {HERO_STARTS.map((s, i) => (
            <Chip
              key={s.id}
              start={s}
              on={i === picked}
              onPick={() => {
                setPicked(i);
                setOpen(true);
                void askSession();
              }}
            />
          ))}
        </div>
      </div>

      {/* the preview: the chip last picked, large, on the right */}
      <div
        aria-hidden
        className={`absolute bottom-10 right-6 top-8 hidden overflow-hidden rounded-[26px] bg-[#151413] shadow-[0_0_0_2px_var(--lemon),0_40px_100px_rgba(0,0,0,0.6)] lg:right-10 lg:block lg:w-[min(38%,560px)] xl:right-20 ${REVEAL} motion-safe:duration-1000 motion-safe:delay-300`}
      >
        {HERO_STARTS.map((s, i) => (
          // eslint-disable-next-line @next/next/no-img-element -- shipped landing-page stills, one shown at a time
          <img
            key={s.id}
            src={s.image}
            alt=""
            loading={i === 0 ? "eager" : "lazy"}
            className={`absolute inset-0 block size-full object-cover transition-opacity duration-700 ${
              i === picked ? "opacity-100" : "opacity-0"
            }`}
          />
        ))}
        <div className="absolute inset-0 bg-gradient-to-t from-[rgba(11,10,8,0.8)] to-transparent to-40%" />
        <div className="serif absolute bottom-5 left-6 text-[34px] leading-none">{start.label}</div>
      </div>

      {open && <HeroDrawer key={start.id} start={start} idea={spark} going={going} onClose={close} onStart={startFromDrawer} />}
    </>
  );
}

function Chip({ start, on, onPick }: { start: HeroStart; on: boolean; onPick: () => void }) {
  return (
    <button
      type="button"
      aria-haspopup="dialog"
      aria-pressed={on}
      onClick={onPick}
      className={`flex min-h-[52px] items-center gap-2.5 rounded-2xl border py-1.5 pl-1.5 pr-3 text-left text-[15px] transition-colors lg:text-[16px] ${
        on
          ? "border-[var(--lemon)] bg-[var(--lemon)] font-bold text-[var(--lemon-ink)]"
          : "border-[#2c2b29] bg-card font-medium text-foreground hover:border-[var(--lemon)]"
      }`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- a shipped landing-page still, 40px */}
      <img src={start.image} alt="" width={40} height={40} className="size-10 flex-none rounded-[10px] object-cover" />
      <span className="leading-tight">{start.label}</span>
    </button>
  );
}
