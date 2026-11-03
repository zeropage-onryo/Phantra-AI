"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BrandLogo } from "@/components/mcp/brand-logos";
import { skinClass, useTone } from "@/components/editorial-skin";
import { CHATGPT_PLUGIN_URL } from "@/lib/connect-claude";
import { frameLabel, type HeroStart } from "@/content/hero-starts";

// The side drawer a hero chip opens (2026-11-02, Mike's pick: "Popup 2 · Side
// drawer" on the Phantra Homepage canvas). It sets up the piece -- what it is
// about, a look, a frame and a length -- and "Start with Vesper" carries all
// of it into the studio composer through the query it already reads. Nothing
// here calls a model or spends: the person sees the price in the studio.
//
// It is a modal dialog: Escape and the scrim close it, focus goes to the idea
// box on open and back to the chip on close, Tab stays inside, and the page
// under it does not scroll. With reduced motion it appears without sliding.

export type DrawerChoice = { idea: string; look: string; frame: string; length: HeroStart["lengths"][number] };

export function HeroDrawer({
  start,
  idea: initialIdea,
  onClose,
  onStart,
  going,
}: {
  start: HeroStart;
  idea: string;
  onClose: () => void;
  onStart: (choice: DrawerChoice) => void;
  going: boolean;
}) {
  const tone = useTone();
  const panel = useRef<HTMLElement>(null);
  const ideaBox = useRef<HTMLTextAreaElement>(null);
  const [idea, setIdea] = useState(initialIdea);
  const [look, setLook] = useState(0);
  const [frame, setFrame] = useState(0);
  const [length, setLength] = useState(0);

  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ideaBox.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel.current) return;
      const items = panel.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, [tabindex]:not([tabindex="-1"])',
      );
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      before?.focus?.();
    };
  }, [onClose]);

  const titleId = `hero-drawer-${start.id}`;
  const lengthLabel = start.kind === "video" ? "Length" : "How many";

  return createPortal(
    <div className={`${skinClass(tone)} fixed inset-0 z-[80]`}>
      <div
        aria-hidden
        onClick={onClose}
        className="absolute inset-0 bg-[rgba(5,5,4,0.55)] backdrop-blur-[6px] motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300"
      />
      <aside
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-y-0 right-0 flex w-full max-w-[560px] flex-col border-l-2 border-[var(--lemon)] bg-card text-foreground shadow-[-40px_0_120px_rgba(0,0,0,0.6)] motion-safe:animate-in motion-safe:slide-in-from-right motion-safe:duration-[450ms] motion-safe:ease-out"
      >
        <div className="relative h-[180px] flex-none overflow-hidden sm:h-[220px]">
          {/* eslint-disable-next-line @next/next/no-img-element -- a shipped landing-page still */}
          <img src={start.image} alt="" className="block size-full object-cover" />
          <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-card to-transparent to-70%" />
          <h2 id={titleId} className="serif absolute bottom-3 left-6 text-[36px] leading-none sm:left-7 sm:text-[44px]">
            {start.label}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-4 top-4 flex size-11 items-center justify-center rounded-full bg-[rgba(11,10,8,0.7)] text-[22px] text-foreground transition-colors hover:bg-[rgba(11,10,8,0.9)]"
          >
            ×
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-6 py-5 sm:px-7">
          <p className="text-[16px] leading-[1.45] text-[#e9e7e3]">
            <span className="font-semibold text-foreground">Vesper: </span>
            {start.line}
          </p>
          <div className="flex flex-col gap-2">
            <label htmlFor={`${titleId}-idea`} className="text-[16px] font-semibold text-[#c9c6c0]">
              What’s it about?
            </label>
            <textarea
              id={`${titleId}-idea`}
              ref={ideaBox}
              rows={2}
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder={start.example}
              className="resize-none rounded-[14px] border border-[#343331] bg-background px-4 py-3 text-[16px] leading-[1.45] text-foreground outline-none transition-colors placeholder:text-[var(--ink-3)] focus:border-[var(--lemon)]"
            />
          </div>

          <div className="flex flex-col gap-2.5" role="group" aria-label="Pick a look">
            <span className="serif text-[22px]">Pick a look</span>
            <div className="grid grid-cols-2 gap-2.5">
              {start.looks.map((name, i) => {
                const on = look === i;
                return (
                  <button
                    key={name}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setLook(i)}
                    className={`relative h-[96px] overflow-hidden rounded-[14px] border-2 bg-[#151413] text-left sm:h-[110px] ${
                      on ? "border-[var(--lemon)]" : "border-transparent hover:border-white/25"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element -- a shipped landing-page still */}
                    <img
                      src={start.lookImages[i % start.lookImages.length]}
                      alt=""
                      className="absolute inset-0 block size-full object-cover"
                    />
                    <span aria-hidden className="absolute inset-0 bg-gradient-to-t from-[rgba(11,10,8,0.85)] to-transparent to-60%" />
                    <span className="serif absolute bottom-2.5 left-3.5 text-[19px] text-white">{name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <Options label="Format" values={start.frames.map(frameLabel)} picked={frame} onPick={setFrame} />
          <Options label={lengthLabel} values={start.lengths.map((l) => l.label)} picked={length} onPick={setLength} />
        </div>

        <div className="flex flex-none gap-2.5 border-t border-border px-6 py-4 sm:px-7">
          <button
            type="button"
            disabled={going}
            onClick={() =>
              onStart({ idea, look: start.looks[look], frame: start.frames[frame], length: start.lengths[length] })
            }
            className="flex h-14 flex-1 items-center justify-center rounded-full bg-[var(--lemon)] text-[17px] font-bold text-[var(--lemon-ink)] transition-[filter] hover:brightness-105 disabled:opacity-70"
          >
            Start with Vesper →
          </button>
          <a
            href={CHATGPT_PLUGIN_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Make it in ChatGPT (opens in a new tab)"
            className="flex size-14 flex-none items-center justify-center rounded-full border-[1.5px] border-[#4a4845] text-foreground transition-colors hover:border-[var(--lemon)]"
          >
            <BrandLogo name="openai" className="size-6" />
          </a>
        </div>
      </aside>
    </div>,
    document.body,
  );
}

function Options({
  label,
  values,
  picked,
  onPick,
}: {
  label: string;
  values: string[];
  picked: number;
  onPick: (i: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2" role="group" aria-label={label}>
      <span className="text-[16px] font-semibold text-[#c9c6c0]">{label}</span>
      <div className="flex flex-wrap gap-2">
        {values.map((v, i) => {
          const on = picked === i;
          return (
            <button
              key={v}
              type="button"
              aria-pressed={on}
              onClick={() => onPick(i)}
              className={`min-h-11 rounded-xl border px-4 text-[15px] font-semibold transition-colors ${
                on
                  ? "border-[var(--lemon)] bg-[var(--lemon)] text-[var(--lemon-ink)]"
                  : "border-[#343331] bg-[#161513] text-[#e9e7e3] hover:border-[var(--lemon)]"
              }`}
            >
              {v}
            </button>
          );
        })}
      </div>
    </div>
  );
}
