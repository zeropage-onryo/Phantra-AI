"use client";

/* Beside a refusal for an empty balance: the way to fix it (2026-10-11;
   lib/out-of-credits.ts). It draws NOTHING for any other failure, so a
   caller can put it after every failure line without asking first. */
import Link from "next/link";
import { useShell } from "@/components/studio/shell";
import { TOP_UP_HREF, needsCredits, shortfall, topUpLabel } from "@/lib/out-of-credits";

export function TopUpLink({ text, always, className }: { text?: string | null; always?: boolean; className?: string }) {
  const { balance } = useShell();
  if (!always && !needsCredits(text)) return null;
  // how far short, when the refusal said: the number a top-up has to cover
  const gap = shortfall(text);
  const more = gap ? Math.max(gap.needs - Math.max(gap.has, 0), 0) : 0;
  return (
    <Link
      href={TOP_UP_HREF}
      className={className ?? "ztopup"}
      title={more > 0 ? `${more.toLocaleString("en-US")} more credit${more === 1 ? "" : "s"} needed` : undefined}
    >
      {topUpLabel(balance)}
    </Link>
  );
}
