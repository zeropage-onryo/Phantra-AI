"use client";

import { useState, type ReactNode } from "react";
import { ArrowUpRight, Check, Copy, HelpCircle } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
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
        role="tablist"
        aria-label="Where to use Phantra"
        className="flex max-w-full flex-wrap justify-center gap-1 rounded-full border border-white/10 bg-white/[0.06] p-1.5 backdrop-blur-md"
      >
        {clients.map((c) => (
          <button
            key={c.id}
            role="tab"
            aria-selected={c.id === active}
            onClick={() => setActive(c.id)}
            className={`rounded-full px-4 py-2 text-[14px] font-medium transition-colors outline-none focus-visible:outline-2 focus-visible:outline-white sm:px-5 sm:text-[15px] ${
              c.id === active ? "bg-white text-black" : "text-[var(--ink-3)] hover:text-foreground"
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
        className="mt-6 max-w-full break-all rounded-lg px-3 py-1.5 font-mono text-[14px] text-[var(--ink-3)] transition-colors hover:text-foreground"
      >
        {copied === "address" ? "Copied" : client.address}
      </button>

      <Dialog open={howOpen} onOpenChange={setHowOpen}>
        <DialogContent
          className="max-h-[92vh] overflow-y-auto rounded-3xl border border-white/10 bg-[#1c1c1c] p-0 text-foreground sm:max-w-[1040px]"
          showCloseButton
        >
          <div className="px-6 pb-3 pt-6 sm:px-8 sm:pt-8">
            <DialogTitle className="pr-10 text-[clamp(1.25rem,2.4vw,1.75rem)] font-semibold leading-tight">{client.how.title}</DialogTitle>
          </div>
          <div className={`grid gap-8 px-6 pb-8 sm:px-8 ${client.how.video ? "lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]" : ""}`}>
            <ol className="flex flex-col rounded-2xl bg-white/[0.04] p-5 sm:p-7">
              {client.how.steps.map((step, i) => (
                <li key={step.title} className={`flex flex-col gap-3 py-6 first:pt-0 last:pb-0 ${i > 0 ? "border-t border-white/10" : ""}`}>
                  <span className="flex size-9 items-center justify-center rounded-full bg-white/10 text-[15px] font-semibold">{i + 1}</span>
                  <h3 className="mt-2 text-[20px] font-semibold leading-snug">{step.title}</h3>
                  <p className="text-[16px] leading-relaxed text-[var(--ink-3)]">
                    {step.body}
                    {step.link && (
                      <>
                        {" "}
                        <a href={step.link.href} target="_blank" rel="noopener noreferrer" className="text-foreground underline underline-offset-4">
                          {step.link.label}
                        </a>
                      </>
                    )}
                  </p>
                  {step.action &&
                    (step.action.href ? (
                      <a
                        href={step.action.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`${btn} mt-1 h-12 w-fit px-5 text-[16px]`}
                        style={step.action.primary ? btnStyle : { backgroundColor: "rgba(255,255,255,0.12)", color: "#fff" }}
                      >
                        {step.action.logo && <BrandLogo name={step.action.logo} className="size-5" />}
                        {step.action.label}
                        <ArrowUpRight className="size-4" aria-hidden />
                      </a>
                    ) : (
                      <button
                        type="button"
                        onClick={() => copy(step.action!.copy ?? "", `step-${i}`)}
                        className={`${btn} mt-1 h-12 w-fit px-5 text-[16px]`}
                        style={{ backgroundColor: "rgba(255,255,255,0.12)", color: "#fff" }}
                      >
                        {copied === `step-${i}` ? <Check className="size-5" aria-hidden /> : <Copy className="size-5" aria-hidden />}
                        {copied === `step-${i}` ? "Copied" : step.action.label}
                      </button>
                    ))}
                </li>
              ))}
            </ol>
            {client.how.video && (
              <div className="overflow-hidden rounded-2xl border border-white/10 bg-black lg:self-start">
                <video key={client.how.video} src={client.how.video} controls playsInline preload="metadata" className="aspect-video w-full bg-black object-contain" />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
