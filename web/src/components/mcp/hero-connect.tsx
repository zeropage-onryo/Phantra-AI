"use client";

import { useState, type ReactNode } from "react";
import { Check, Copy, HelpCircle, XIcon } from "lucide-react";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { BrandLogo, type LogoName } from "./brand-logos";
import { useMcpClientOptional } from "./client-context";

// The hero's switcher (after higgsfield.ai/mcp): a pill row to pick where
// Phantra goes, then ONE primary button in that client's own colour and logo,
// the "How to connect?" button (opens a three-step modal for that client) and
// the address to paste. The pick is shared with the setup steps further down.

export type HowStep = {
  title: string;
  body: string;
  /** an inline link after the body ("Open claude.ai") */
  link?: { label: string; href: string };
  /** a button under the step: a link, or a value to copy */
  action?: { label: string; href?: string; copy?: string; logo?: LogoName; primary?: boolean };
};

export type HeroClient = {
  id: string;
  label: string;
  button: { label: string; href?: string; copy?: string; logo: LogoName; bg: string; fg: string; edge: string };
  /** the line shown under the buttons */
  address: string;
  how: {
    title: string;
    steps: HowStep[];
    /** a walkthrough video (mp4 address); the panel is left out until there is one */
    video?: string;
  };
};

export function HeroConnect({ clients, children }: { clients: HeroClient[]; children?: ReactNode }) {
  const shared = useMcpClientOptional();
  const [own, setOwn] = useState(clients[0].id);
  const active = shared?.active ?? own;
  const setActive = shared?.setActive ?? setOwn;
  const [copied, setCopied] = useState<string | null>(null);
  const [howOpen, setHowOpen] = useState(false);
  const client = clients.find((c) => c.id === active) ?? clients[0];
  const b = client.button;

  const copy = async (value: string, key: string) => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
      window.setTimeout(() => setCopied((k) => (k === key ? null : k)), 1600);
    } catch {
      /* the text is on the page to select */
    }
  };

  const btn =
    "inline-flex h-14 items-center justify-center gap-2.5 rounded-2xl px-7 text-[17px] font-semibold transition-transform hover:-translate-y-0.5 active:translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";
  const btnStyle = { backgroundColor: b.bg, color: b.fg, boxShadow: `0 5px 0 0 ${b.edge}` };

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
          <a href={b.href} target="_blank" rel="noopener noreferrer" className={`${btn} w-full sm:w-auto`} style={btnStyle}>
            <BrandLogo name={b.logo} className="size-6" />
            {b.label}
          </a>
        ) : (
          <button type="button" onClick={() => copy(b.copy ?? "", "button")} className={`${btn} w-full sm:w-auto`} style={btnStyle}>
            {copied === "button" ? <Check className="size-6" aria-hidden /> : <BrandLogo name={b.logo} className="size-6" />}
            {copied === "button" ? "Copied" : b.label}
          </button>
        )}
        <button
          type="button"
          onClick={() => setHowOpen(true)}
          className="inline-flex h-14 w-full items-center justify-center gap-2.5 rounded-2xl border border-white/15 bg-white/[0.05] px-7 text-[17px] font-semibold text-foreground transition-colors hover:bg-white/10 sm:w-auto"
        >
          <HelpCircle className="size-6" aria-hidden />
          How to connect?
        </button>
      </div>

      <button
        type="button"
        onClick={() => copy(client.address, "address")}
        aria-label={`Copy ${client.address}`}
        className="mt-6 max-w-full break-all rounded-lg px-3 py-1.5 font-mono text-[14px] text-[var(--ink-2)] transition-colors hover:text-foreground"
      >
        {copied === "address" ? "Copied" : client.address}
      </button>

      <Dialog open={howOpen} onOpenChange={setHowOpen}>
        <DialogContent
          className="top-[2dvh] flex max-h-[96dvh] w-full max-w-[calc(100%-8px)] -translate-y-0 flex-col gap-0 overflow-y-auto rounded-[16px] border-0 bg-[linear-gradient(135deg,#1b1c1f_0%,#141416_55%,#1a1a1d_100%)] p-0 text-foreground ring-1 ring-white/[0.09] sm:max-w-[min(1240px,calc(100vw-8px))]"
          showCloseButton={false}
        >
          <div className="flex items-center justify-between px-[14px] pb-[10px] pt-[9px]">
            <DialogTitle className="pr-3 text-[15px] font-semibold leading-snug text-white">{client.how.title}</DialogTitle>
            <DialogClose
              aria-label="Close"
              className="inline-flex size-[34px] shrink-0 items-center justify-center rounded-full bg-white/[0.07] text-white/80 transition-colors hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-white"
            >
              <XIcon className="size-[17px]" aria-hidden />
            </DialogClose>
          </div>
          <div className="mx-[8px] mb-[8px] rounded-[16px] bg-[linear-gradient(160deg,rgba(255,255,255,0.075)_0%,rgba(255,255,255,0.045)_55%,rgba(255,255,255,0.06)_100%)] p-5 sm:px-[21px] sm:pb-[21px] sm:pt-[22px]">
            <div className={`grid items-start gap-6 ${client.how.video ? "md:grid-cols-[minmax(0,0.405fr)_minmax(0,0.595fr)] md:gap-[25px]" : ""}`}>
              <ol className="flex flex-col">
                {client.how.steps.map((step, i) => (
                  <li key={step.title} className={`flex flex-col ${i > 0 ? "mt-[19px] border-t border-white/[0.09] pt-[19px]" : ""} ${i === client.how.steps.length - 1 ? "" : "pb-[2px]"}`}>
                    <span className="flex size-[25px] items-center justify-center rounded-full bg-white/[0.12] text-[12.5px] font-medium text-white">{i + 1}</span>
                    <h3 className="mt-[28px] flex flex-wrap items-center gap-x-1.5 text-[15px] font-medium leading-snug text-white">
                      {step.title}
                      {i === 1 && (step.action?.logo ?? client.button.logo) && (
                        <span className="inline-flex size-[19px] items-center justify-center rounded-[5px] bg-white/[0.14]">
                          <BrandLogo name={step.action?.logo ?? client.button.logo} className="size-[12px]" />
                        </span>
                      )}
                    </h3>
                    <p className="mt-[9px] text-[13px] leading-[18px] text-white/60 [overflow-wrap:anywhere]">
                      {step.body}
                      {step.link && (
                        <>
                          {" "}
                          <a href={step.link.href} target="_blank" rel="noopener noreferrer" className="underline underline-offset-[3px] hover:text-white/70">
                            {step.link.label}
                          </a>
                        </>
                      )}
                    </p>
                    {step.action &&
                      (() => {
                        const a = step.action;
                        const cls =
                          "mt-[17px] inline-flex h-[35px] w-fit items-center gap-2 rounded-[9px] px-[16px] text-[13.5px] font-medium transition-transform hover:-translate-y-px active:translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";
                        const style = a.primary
                          ? { backgroundColor: b.bg, color: b.fg, boxShadow: `0 3px 0 0 ${b.edge}` }
                          : { backgroundColor: "rgba(110,118,122,0.42)", color: "#fff" };
                        const inner = (
                          <>
                            {a.href ? (
                              a.logo && <BrandLogo name={a.logo} className="size-[16px]" />
                            ) : copied === `step-${i}` ? (
                              <Check className="size-[16px]" aria-hidden />
                            ) : (
                              <Copy className="size-[16px]" aria-hidden />
                            )}
                            {!a.href && copied === `step-${i}` ? "Copied" : a.label}
                          </>
                        );
                        return a.href ? (
                          <a href={a.href} target="_blank" rel="noopener noreferrer" className={cls} style={style}>
                            {inner}
                          </a>
                        ) : (
                          <button type="button" onClick={() => copy(a.copy ?? "", `step-${i}`)} className={cls} style={style}>
                            {inner}
                          </button>
                        );
                      })()}
                  </li>
                ))}
              </ol>
              {client.how.video && (
                <div className="overflow-hidden rounded-[16px] bg-black md:sticky md:top-0">
                  <video key={client.how.video} src={client.how.video} controls playsInline preload="metadata" className="aspect-video w-full bg-black object-contain" />
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
