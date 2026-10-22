"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

// One line of text to paste somewhere else -- an address, a command, a
// prompt -- with a button that copies it. A click on the text selects all of
// it too, for a browser that refuses the clipboard.
export function CopyField({
  value,
  label,
  mono = true,
  multiline = false,
}: {
  value: string;
  label?: string;
  mono?: boolean;
  multiline?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* the text is still selectable */
    }
  };
  return (
    <div>
      {label && <span className="eyebrow mb-2 block">{label}</span>}
      <div className="flex items-stretch gap-2">
        <code
          className={`min-w-0 flex-1 select-all rounded-xl border border-border bg-secondary px-3.5 py-3 text-[13px] leading-relaxed text-foreground [overflow-wrap:anywhere] ${mono ? "font-mono" : "font-sans text-[14px]"} ${multiline ? "whitespace-pre-wrap" : ""}`}
        >
          {value}
        </code>
        <button
          type="button"
          onClick={copy}
          aria-label={copied ? "Copied" : `Copy ${label ?? "text"}`}
          className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-xl border border-border bg-background px-3 py-3 text-[13px] font-medium text-foreground transition-colors hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--primary)]"
        >
          {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          <span className="hidden sm:inline">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
    </div>
  );
}

/** Just the button, for a card that shows its own text. */
export function CopyButton({ value, label = "Copy prompt" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* nothing to do: the text is on the card */
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3.5 py-2 text-[13px] font-medium text-foreground transition-colors hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--primary)]"
    >
      {copied ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
      {copied ? "Copied" : label}
    </button>
  );
}
