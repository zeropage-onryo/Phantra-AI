"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { CopyField } from "./copy-field";
import { useState } from "react";
import { useMcpClientOptional } from "./client-context";
import { CLIP_BASE } from "@/landing-pages/media";

// The setup section of /mcp and /mcp/claude: one tab per place the connector
// goes, the way higgsfield.ai/mcp and runway.com/mcp lay it out. The tab is in
// the URL hash (#claude, #chatgpt, ...) so a link can open the right one, and
// the hero's buttons do exactly that.
//
// EVERY panel is in the server HTML (2026-10-22): the inactive ones carry the
// `hidden` attribute instead of being left out. Both pages are the
// documentation URL a directory listing names (Claude's requires "clear setup
// and usage instructions" at that address), and a reviewer's fetch or a
// crawler reads the HTML without clicking a tab; until today only the first
// tab's steps were in it.

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
  /** A link that opens that chat with the setup already typed in. */
  chat?: { label: string; href: string };
  note?: ReactNode;
  /** the walkthrough video is uploaded (see SetupVideo) */
  video?: boolean;
  /** a walkthrough video served from this site instead (mp4, optional webm, poster) */
  videoSrc?: { mp4: string; webm?: string; poster?: string; caption?: string };
};

// A tab's walkthrough lives in the bucket at site/mcp/setup-<id>.mp4 (poster:
// the tab's first screenshot). A tab sets `video: true` once its file is
// uploaded; the browser cannot ask R2 whether a file exists (no CORS), so
// the flag is the switch and the screenshots carry a tab until then.
function SetupVideo({ id, poster, src }: { id: string; poster?: string; src?: SetupTab["videoSrc"] }) {
  return (
    <figure>
      <div className="overflow-hidden rounded-2xl border border-border bg-black shadow-[0_30px_80px_-30px_rgba(0,0,0,0.8)]">
        <video controls playsInline preload="metadata" poster={src?.poster ?? poster} className="aspect-video w-full bg-black object-contain">
          {src?.webm && <source src={src.webm} type="video/webm" />}
          <source src={src?.mp4 ?? `${CLIP_BASE}/mcp/setup-${id}.mp4`} type="video/mp4" />
        </video>
      </div>
      <figcaption className="mt-3 text-[13.5px] text-[var(--ink-3)]">
        {src?.caption ?? "Video: the whole setup in under a minute."}
      </figcaption>
    </figure>
  );
}

export function SetupTabs({ tabs }: { tabs: SetupTab[] }) {
  // the page-wide pick when a provider wraps the page (/mcp); its own otherwise (/mcp/claude)
  const shared = useMcpClientOptional();
  const [own, setOwn] = useState(tabs[0].id);
  const active = shared?.active ?? own;
  const pick = shared?.setActive ?? setOwn;

  const tab = tabs.find((t) => t.id === active) ?? tabs[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label="Where to connect"
        className="mx-auto flex w-fit max-w-full flex-wrap justify-center gap-1 rounded-full border border-white/10 bg-white/[0.06] p-1.5 backdrop-blur-md"
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={t.id === tab.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => pick(t.id)}
            className={`rounded-full px-5 py-2.5 text-[14px] font-medium tracking-[-0.005em] transition-colors outline-none focus-visible:outline-2 focus-visible:outline-[var(--primary)] ${
              t.id === tab.id ? "bg-white text-black shadow-sm" : "text-[var(--ink-3)] hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tabs.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`panel-${t.id}`}
          aria-labelledby={`tab-${t.id}`}
          hidden={t.id !== tab.id}
          className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-14"
        >
          <div>
            <h3 className="serif text-[clamp(1.75rem,3.2vw,2.5rem)] leading-tight">{t.title}</h3>
            <div className="mt-4 text-[16px] leading-relaxed text-[var(--ink-2)] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4">
              {t.intro}
            </div>

            {t.copy && (
              <div className="mt-6 flex flex-col gap-4">
                {t.copy.map((c) => (
                  <CopyField key={c.label} label={c.label} value={c.value} multiline={c.multiline} />
                ))}
              </div>
            )}

            <ol className="mt-7 flex flex-col gap-4">
              {t.steps.map((step, i) => (
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

            {t.chat && (
              <a
                href={t.chat.href}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-8 mr-3 inline-flex h-11 items-center gap-2 rounded-full bg-[var(--primary)] px-5 text-[14px] font-semibold text-[var(--primary-foreground)] transition-opacity hover:opacity-90"
              >
                {t.chat.label}
                <ArrowUpRight className="size-4" aria-hidden />
              </a>
            )}
            {t.action && (
              <a
                href={t.action.href}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex h-11 items-center gap-2 rounded-full px-5 text-[14px] font-semibold transition-colors ${t.chat ? "border border-border bg-transparent text-foreground hover:bg-secondary" : "mt-8 bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90"}`}
              >
                {t.action.label}
                <ArrowUpRight className="size-4" aria-hidden />
              </a>
            )}

            {t.note && <p className="mt-6 text-[14px] leading-relaxed text-[var(--ink-3)] [&_a]:underline [&_a]:underline-offset-4">{t.note}</p>}
          </div>

          <div className="flex flex-col gap-6">
            {(t.video || t.videoSrc) && t.id === tab.id && (
              <SetupVideo key={t.id} id={t.id} poster={t.shots?.[0]?.src} src={t.videoSrc} />
            )}
            {(t.shots ?? []).map((shot) => (
              <figure key={shot.src}>
                <div className="overflow-hidden rounded-2xl border border-border bg-[#141414] shadow-[0_30px_70px_-35px_rgba(0,0,0,0.45)]">
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
      ))}
    </div>
  );
}
