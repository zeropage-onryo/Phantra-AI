"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { CopyButton } from "./copy-field";
import { clipSrc } from "@/landing-pages/media";

// What the connector does, as a Runway-style gallery: a filter row, then one
// card per ask with the work it made, the prompt in a mono block and the two
// buttons that matter -- open that chat with the prompt typed in, or copy it.
// The first line of every prompt names Phantra so the chat reaches for the
// connector. A prompt in a link is only the example text, never anything
// about the person.

export type UseCase = {
  title: string;
  prompt: string;
  group: "Images" | "Video" | "Edit" | "Plan" | "Account";
  /** a still under /public, and optionally the clip it is the poster of */
  src?: string;
  video?: string;
  note?: string;
};

const GROUPS = ["All", "Images", "Video", "Edit", "Plan", "Account"] as const;

const chatGpt = (p: string) => `https://chatgpt.com/?q=${encodeURIComponent(p)}`;
const claude = (p: string) => `https://claude.ai/new?q=${encodeURIComponent(p)}`;

function Loop({ src, poster }: { src: string; poster: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  // play only what is on screen; reduced motion keeps the poster
  useEffect(() => {
    const v = ref.current;
    if (!v || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) v.play().catch(() => {});
      else v.pause();
    });
    io.observe(v);
    return () => io.disconnect();
  }, []);
  if (failed) return null;
  return (
    <video
      ref={ref}
      src={clipSrc(src)}
      poster={poster}
      muted
      loop
      playsInline
      preload="none"
      onError={() => setFailed(true)}
      className="absolute inset-0 size-full object-cover"
    />
  );
}

export function UseCases({ items }: { items: UseCase[] }) {
  const [group, setGroup] = useState<(typeof GROUPS)[number]>("All");
  const shown = items.filter((i) => group === "All" || i.group === group);
  return (
    <div>
      <div role="tablist" aria-label="Filter examples" className="flex flex-wrap gap-x-7 gap-y-2 border-b border-white/10">
        {GROUPS.map((g) => (
          <button
            key={g}
            role="tab"
            aria-selected={g === group}
            onClick={() => setGroup(g)}
            className={`-mb-px border-b-2 pb-3 text-[15px] font-medium transition-colors outline-none focus-visible:text-foreground ${
              g === group ? "border-white text-foreground" : "border-transparent text-[var(--ink-3)] hover:text-foreground"
            }`}
          >
            {g}
          </button>
        ))}
      </div>
      <p className="mt-5 text-[14px] text-[var(--ink-3)]">{shown.length} examples</p>
      <div className="mt-6 grid gap-x-6 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
        {shown.map((c) => (
          <article key={c.title} className="flex flex-col">
            {c.src && (
              <div className="relative aspect-[16/10] overflow-hidden rounded-2xl bg-white/5">
                <Image src={c.src} alt="" fill sizes="(min-width: 1024px) 380px, (min-width: 768px) 46vw, 92vw" quality={70} className="object-cover" />
                {c.video && <Loop src={c.video} poster={c.src} />}
                <span className="absolute left-3 top-3 rounded-full bg-black/60 px-2.5 py-1 text-[12px] font-medium text-white backdrop-blur-md">
                  {c.video ? "Video" : c.group}
                </span>
              </div>
            )}
            <h3 className="mt-5 text-[20px] font-semibold leading-tight tracking-[-0.01em] text-foreground">{c.title}</h3>
            <p className="mt-4 flex-1 whitespace-pre-wrap rounded-xl bg-white/[0.06] p-4 font-mono text-[13px] leading-relaxed text-[var(--ink-2)]">
              {c.prompt}
            </p>
            {c.note && <p className="mt-2 text-[13px] text-[var(--ink-3)]">{c.note}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              <a
                href={chatGpt(c.prompt)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-2 text-[13px] font-semibold text-black transition-opacity hover:opacity-85"
              >
                Try in ChatGPT <ArrowUpRight className="size-3.5" aria-hidden />
              </a>
              <a
                href={claude(c.prompt)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-2 text-[13px] font-semibold text-black transition-opacity hover:opacity-85"
              >
                Try in Claude <ArrowUpRight className="size-3.5" aria-hidden />
              </a>
              <CopyButton value={c.prompt} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
