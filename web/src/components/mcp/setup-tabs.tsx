"use client";

import { useEffect, useState, type ReactNode } from "react";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { CopyField } from "./copy-field";

// The setup section of /mcp: one tab per place the connector goes, the way
// higgsfield.ai/mcp and runway.com/mcp lay it out. The tab is in the URL
// hash (#claude, #chatgpt, ...) so a link can open the right one, and the
// hero's buttons do exactly that.

export type SetupShot = { src: string; alt: string; width: number; height: number; caption: string };
export type SetupTab = {
  id: string;
  label: string;
  title: string;
  intro: ReactNode;
  steps: ReactNode[];
  copy?: { label: string; value: string; multiline?: boolean }[];
  shots?: SetupShot[];
  action?: { label: string; href: string };
  note?: ReactNode;
};

export function SetupTabs({ tabs }: { tabs: SetupTab[] }) {
  const [active, setActive] = useState(tabs[0].id);

  // follow the hash: a hero button, a pasted link, the back button
  useEffect(() => {
    const read = () => {
      const id = window.location.hash.replace("#", "");
      if (tabs.some((t) => t.id === id)) setActive(id);
    };
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, [tabs]);

  const pick = (id: string) => {
    setActive(id);
    window.history.replaceState(null, "", `#${id}`);
  };

  const tab = tabs.find((t) => t.id === active) ?? tabs[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label="Where to connect"
        className="mx-auto flex w-fit max-w-full flex-wrap justify-center gap-1 rounded-2xl border border-border bg-secondary p-1"
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={t.id === tab.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => pick(t.id)}
            className={`rounded-xl px-4 py-2 text-[14px] font-medium tracking-[-0.005em] transition-colors outline-none focus-visible:outline-2 focus-visible:outline-[var(--primary)] ${
              t.id === tab.id ? "bg-background text-foreground shadow-sm" : "text-[var(--ink-3)] hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`panel-${tab.id}`}
        aria-labelledby={`tab-${tab.id}`}
        className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-14"
      >
        <div>
          <h3 className="serif text-[clamp(1.75rem,3.2vw,2.5rem)] leading-tight">{tab.title}</h3>
          <div className="mt-4 text-[16px] leading-relaxed text-[var(--ink-2)] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4">
            {tab.intro}
          </div>

          {tab.copy && (
            <div className="mt-6 flex flex-col gap-4">
              {tab.copy.map((c) => (
                <CopyField key={c.label} label={c.label} value={c.value} multiline={c.multiline} />
              ))}
            </div>
          )}

          <ol className="mt-7 flex flex-col gap-4">
            {tab.steps.map((step, i) => (
              <li key={i} className="flex gap-4">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-[13px] font-semibold text-[var(--primary-foreground)]">
                  {i + 1}
                </span>
                <div className="pt-0.5 text-[15.5px] leading-relaxed text-foreground [&_a]:underline [&_a]:underline-offset-4 [&_code]:rounded [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px]">
                  {step}
                </div>
              </li>
            ))}
          </ol>

          {tab.action && (
            <a
              href={tab.action.href}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-8 inline-flex h-11 items-center gap-2 rounded-full bg-[var(--primary)] px-5 text-[14px] font-semibold text-[var(--primary-foreground)] transition-opacity hover:opacity-90"
            >
              {tab.action.label}
              <ArrowUpRight className="size-4" aria-hidden />
            </a>
          )}

          {tab.note && <p className="mt-6 text-[14px] leading-relaxed text-[var(--ink-3)] [&_a]:underline [&_a]:underline-offset-4">{tab.note}</p>}
        </div>

        <div className="flex flex-col gap-6">
          {(tab.shots ?? []).map((shot) => (
            <figure key={shot.src}>
              <div className="overflow-hidden rounded-2xl border border-border bg-[#1f1f1e] shadow-[0_30px_70px_-35px_rgba(0,0,0,0.45)]">
                <div aria-hidden className="flex items-center gap-1.5 border-b border-white/10 px-4 py-3">
                  <span className="size-2.5 rounded-full bg-white/20" />
                  <span className="size-2.5 rounded-full bg-white/20" />
                  <span className="size-2.5 rounded-full bg-white/20" />
                </div>
                <Image
                  src={shot.src}
                  alt={shot.alt}
                  width={shot.width}
                  height={shot.height}
                  sizes="(min-width: 1024px) 620px, 92vw"
                  className="h-auto w-full"
                />
              </div>
              <figcaption className="mt-3 text-[13.5px] text-[var(--ink-3)]">{shot.caption}</figcaption>
            </figure>
          ))}
        </div>
      </div>
    </div>
  );
}
