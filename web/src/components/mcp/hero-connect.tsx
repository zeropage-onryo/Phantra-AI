"use client";

import { useState, type ReactNode } from "react";
import { ArrowUpRight, Check, Copy, HelpCircle } from "lucide-react";
import { useMcpClientOptional } from "./client-context";

// The hero's switcher (after higgsfield.ai/mcp): a pill row to pick where
// Phantra goes, then ONE primary button for that client, the "How to connect?"
// button that scrolls to the steps, and the address to paste.

export type HeroClient = {
  id: string;
  label: string;
  /** a link, or a value to copy */
  button: { label: string; href?: string; copy?: string };
  /** the line shown under the buttons */
  address: string;
};

export function HeroConnect({ clients, children }: { clients: HeroClient[]; children?: ReactNode }) {
  const shared = useMcpClientOptional();
  const [own, setOwn] = useState(clients[0].id);
  const active = shared?.active ?? own;
  const setActive = shared?.setActive ?? setOwn;
  const [copied, setCopied] = useState<string | null>(null);
  const client = clients.find((c) => c.id === active) ?? clients[0];

  const copy = async (value: string, key: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
      window.setTimeout(() => setCopied((k) => (k === key ? null : k)), 1600);
    } catch {
      /* the address is on the page to select */
    }
  };

  const primary =
    "inline-flex h-14 items-center justify-center gap-2.5 rounded-2xl bg-white px-7 text-[17px] font-semibold text-black shadow-[0_5px_0_0_rgba(255,255,255,0.28)] transition-transform hover:-translate-y-0.5 active:translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";

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
        {client.button.href ? (
          <a href={client.button.href} target="_blank" rel="noopener noreferrer" className={`${primary} w-full sm:w-auto`}>
            {client.button.label}
            <ArrowUpRight className="size-5" aria-hidden />
          </a>
        ) : (
          <button type="button" onClick={() => copy(client.button.copy ?? "", "button")} className={`${primary} w-full sm:w-auto`}>
            {copied === "button" ? <Check className="size-5" aria-hidden /> : <Copy className="size-5" aria-hidden />}
            {copied === "button" ? "Copied" : client.button.label}
          </button>
        )}
        <a
          href="#setup"
          className="inline-flex h-14 w-full items-center justify-center gap-2.5 rounded-2xl border border-white/15 bg-white/[0.05] px-7 text-[17px] font-semibold text-foreground transition-colors hover:bg-white/10 sm:w-auto"
        >
          <HelpCircle className="size-5" aria-hidden />
          How to connect?
        </a>
      </div>

      <button
        type="button"
        onClick={() => copy(client.address, "address")}
        aria-label={`Copy ${client.address}`}
        className="mt-6 max-w-full break-all rounded-lg px-3 py-1.5 font-mono text-[14px] text-[var(--ink-3)] transition-colors hover:text-foreground"
      >
        {copied === "address" ? "Copied" : client.address}
      </button>
    </div>
  );
}
