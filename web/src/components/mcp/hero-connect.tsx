"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Check, Copy, HelpCircle, XIcon } from "lucide-react";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { BrandLogo, type LogoName } from "./brand-logos";
import { useMcpClientOptional } from "./client-context";

// The hero's switcher (after higgsfield.ai/mcp): a pill row to pick where
// Phantra goes, then ONE primary button in that client's own colour and logo,
// the "How to connect?" button (opens a three-step modal for that client) and
// the address to paste. The pick is shared with the anchors on the page, so a
// link to /mcp#claude opens on Claude. Restyled 2026-10-16 to the approved
// Figma mockup (Phantra MCP — How to connect).

export type HowStep = {
  title: string;
  body: string;
  /** an inline link after the body ("Open claude.ai") */
  link?: { label: string; href: string };
  /** a button under the step: a link, or a value to copy. A link with
   *  `copyAlso` opens the page AND copies that value in the same click. */
  action?: { label: string; href?: string; copy?: string; copyAlso?: string; logo?: LogoName; primary?: boolean };
};

export type HeroClient = {
  id: string;
  label: string;
  button: {
    label: string;
    href?: string;
    copy?: string;
    /** with `href`: the click also copies this, for a client whose own setup
     *  page cannot be opened filled in (ChatGPT, 2026-10-16) */
    copyAlso?: string;
    /** shown under the buttons once `copyAlso` has been copied */
    copiedHint?: string;
    logo: LogoName;
    bg: string;
    fg: string;
    edge: string;
  };
  /** the line shown under the buttons */
  address: string;
  how: {
    title: string;
    steps: HowStep[];
    /** a walkthrough video (mp4 address); the panel is left out until there is one */
    video?: string;
    /** the frame shown before the video plays */
    poster?: string;
    /** one plain line under the video */
    caption?: string;
  };
};

const COPIED_MS = 2500;

export function HeroConnect({ clients, children }: { clients: HeroClient[]; children?: ReactNode }) {
  const shared = useMcpClientOptional();
  const [own, setOwn] = useState(clients[0].id);
  const active = shared?.active ?? own;
  const setActive = shared?.setActive ?? setOwn;
  const [copied, setCopied] = useState<string | null>(null);
  const [howOpen, setHowOpen] = useState(false);
  // the walkthrough video plays on its own only for people who have not asked for less motion
  const [reduceMotion, setReduceMotion] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const read = () => setReduceMotion(mq.matches);
    read();
    mq.addEventListener("change", read);
    return () => mq.removeEventListener("change", read);
  }, []);
  const client = clients.find((c) => c.id === active) ?? clients[0];
  const b = client.button;

  const copy = async (value: string, key: string) => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
      window.setTimeout(() => setCopied((k) => (k === key ? null : k)), COPIED_MS);
    } catch {
      /* the text is on the page to select */
    }
  };

  const lift = (edge: string) => `inset 0 -3px 0 0 rgba(0,0,0,0.25), 0 6px 18px -6px ${edge}`;
  const btn =
    "inline-flex h-12 items-center justify-center gap-2 rounded-[12px] px-6 text-[16px] font-semibold transition-transform hover:-translate-y-0.5 active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";
  const btnStyle = { backgroundColor: b.bg, color: b.fg, boxShadow: lift(b.edge) };
  const heroCopied = copied === `button-${client.id}`;

  return (
    <div className="flex w-full flex-col items-center">
      <div
        role="group"
        aria-label="Where to use Phantra"
        className="flex max-w-full flex-wrap justify-center gap-1 rounded-full border border-white/10 bg-white/[0.06] p-1.5 backdrop-blur-md"
      >
        {clients.map((c) => (
          <button
            key={c.id}
            aria-pressed={c.id === client.id}
            onClick={() => setActive(c.id)}
            className={`rounded-full px-4 py-2 text-[14px] font-medium transition-colors outline-none focus-visible:outline-2 focus-visible:outline-white sm:px-5 sm:text-[15px] ${
              c.id === client.id ? "bg-white text-black" : "text-[var(--ink-2)] hover:text-foreground"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {children}

      <div className="mt-10 flex w-full flex-col items-center justify-center gap-3 sm:mt-12 sm:flex-row">
        {b.href ? (
          // A link with copyAlso still navigates (no preventDefault): the copy
          // rides on the same click.
          <a
            href={b.href}
            target="_blank"
            rel="noopener noreferrer"
            onClick={b.copyAlso ? () => void copy(b.copyAlso ?? "", `button-${client.id}`) : undefined}
            className={`${btn} w-full sm:w-auto`}
            style={btnStyle}
          >
            {heroCopied ? <Check className="size-5" aria-hidden /> : <BrandLogo name={b.logo} className="size-5" />}
            {heroCopied ? "Address copied" : b.label}
          </a>
        ) : (
          <button
            type="button"
            onClick={() => copy(b.copy ?? "", `button-${client.id}`)}
            className={`${btn} w-full sm:w-auto`}
            style={btnStyle}
          >
            {heroCopied ? <Check className="size-5" aria-hidden /> : <BrandLogo name={b.logo} className="size-5" />}
            {heroCopied ? "Copied" : b.label}
          </button>
        )}
        <button
          type="button"
          onClick={() => setHowOpen(true)}
          className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-[12px] border border-white/10 bg-[rgba(35,38,42,0.75)] px-4 text-[16px] font-semibold text-foreground backdrop-blur-[12px] transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white sm:w-auto"
        >
          <HelpCircle className="size-5" aria-hidden />
          How to connect?
        </button>
      </div>

      <p aria-live="polite" className="mt-4 min-h-[20px] text-[14px] text-[var(--ink-2)]">
        {heroCopied && b.copiedHint ? b.copiedHint : ""}
      </p>

      <button
        type="button"
        onClick={() => copy(client.address, "address")}
        aria-label={`Copy ${client.address}`}
        className="mt-2 max-w-full break-all rounded-lg px-3 py-1.5 font-mono text-[14px] text-[var(--ink-2)] transition-colors hover:text-foreground"
      >
        {copied === "address" ? "Copied" : client.address}
      </button>

      <Dialog open={howOpen} onOpenChange={setHowOpen}>
        <DialogContent
          className="flex max-h-[calc(100dvh-32px)] w-full max-w-[calc(100%-32px)] flex-col gap-0 overflow-y-auto rounded-[24px] border border-white/5 bg-[rgba(35,38,42,0.75)] p-2 text-foreground ring-0 backdrop-blur-[40px] sm:max-w-[min(1033px,calc(100vw-32px))]"
          showCloseButton={false}
        >
          <div className="flex items-center justify-between px-3 pb-2 pt-1">
            <DialogTitle className="pr-3 text-[16px] font-semibold leading-snug text-white">{client.how.title}</DialogTitle>
            <DialogClose
              aria-label="Close"
              className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-white/[0.07] text-white/80 transition-colors hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-white"
            >
              <XIcon className="size-[18px]" aria-hidden />
            </DialogClose>
          </div>
          <div className="rounded-[18px] bg-white/[0.05] p-5 sm:p-6">
            <div className={`grid items-start gap-6 ${client.how.video ? "md:grid-cols-[minmax(0,0.43fr)_minmax(0,0.57fr)] md:gap-6" : ""}`}>
              <ol className="flex flex-col">
                {client.how.steps.map((step, i) => (
                  <li key={step.title} className={`flex flex-col ${i > 0 ? "mt-5 border-t border-white/[0.09] pt-5" : ""}`}>
                    <span className="flex size-7 items-center justify-center rounded-full bg-white/[0.12] text-[13px] font-medium text-white">{i + 1}</span>
                    <h3 className="mt-4 flex flex-wrap items-center gap-x-1.5 text-[16px] font-medium leading-snug text-white">
                      {step.title}
                      {i === 1 && (step.action?.logo ?? client.button.logo) && (
                        <span className="inline-flex size-[20px] items-center justify-center rounded-[5px] bg-white/[0.14]">
                          <BrandLogo name={step.action?.logo ?? client.button.logo} className="size-[12px]" />
                        </span>
                      )}
                    </h3>
                    <p className="mt-2 text-[14px] leading-[20px] text-white/60 [overflow-wrap:anywhere]">
                      {step.body}
                      {step.link && (
                        <>
                          {" "}
                          <a href={step.link.href} target="_blank" rel="noopener noreferrer" className="underline underline-offset-[3px] hover:text-white/80">
                            {step.link.label}
                          </a>
                        </>
                      )}
                    </p>
                    {step.action &&
                      (() => {
                        const a = step.action;
                        const key = `step-${client.id}-${i}`;
                        const done = copied === key;
                        const cls = a.primary
                          ? "mt-4 inline-flex h-12 w-fit items-center gap-2 rounded-[12px] px-5 text-[15px] font-semibold transition-transform hover:-translate-y-px active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                          : "mt-4 inline-flex h-10 w-fit items-center gap-2 rounded-[10px] px-4 text-[14px] font-medium transition-transform hover:-translate-y-px active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";
                        const style = a.primary
                          ? { backgroundColor: b.bg, color: b.fg, boxShadow: lift(b.edge) }
                          : { backgroundColor: "rgba(110,118,122,0.42)", color: "#fff" };
                        const icon = done ? (
                          <Check className="size-[16px]" aria-hidden />
                        ) : a.href ? (
                          a.logo && <BrandLogo name={a.logo} className="size-[16px]" />
                        ) : (
                          <Copy className="size-[16px]" aria-hidden />
                        );
                        const label = done ? (a.href ? "Address copied" : "Copied") : a.label;
                        return a.href ? (
                          <a
                            href={a.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={a.copyAlso ? () => void copy(a.copyAlso ?? "", key) : undefined}
                            className={cls}
                            style={style}
                          >
                            {icon}
                            {label}
                          </a>
                        ) : (
                          <button type="button" onClick={() => copy(a.copy ?? "", key)} className={cls} style={style}>
                            {icon}
                            {label}
                          </button>
                        );
                      })()}
                  </li>
                ))}
              </ol>
              {client.how.video && (
                <figure className="md:sticky md:top-0">
                  <div className="overflow-hidden rounded-[16px] bg-black">
                    <video
                      key={client.how.video}
                      src={client.how.video}
                      poster={client.how.poster}
                      autoPlay={!reduceMotion}
                      muted
                      loop={!reduceMotion}
                      playsInline
                      controls
                      preload="metadata"
                      className="aspect-video w-full bg-black object-contain"
                    />
                  </div>
                  {client.how.caption && (
                    <figcaption className="mt-3 text-[13px] leading-[18px] text-white/55">{client.how.caption}</figcaption>
                  )}
                </figure>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
