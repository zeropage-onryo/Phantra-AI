"use client";

/* The next steps offered under a rendered scene (lib/next-steps.ts,
   vesper_v2). Each opens a priced card; nothing runs from a click here. */
import { AudioLines, Copy, Smartphone } from "lucide-react";
import type { NextStep } from "@/lib/next-steps";
import "@/components/studio/vesper-v2.css";

const ICON = { sound: AudioLines, vertical: Smartphone, variants: Copy } as const;

export function NextSteps({ steps, busy, onPick }: { steps: NextStep[]; busy: boolean; onPick: (step: NextStep) => void }) {
  if (!steps.length) return null;
  return (
    <div className="ns" role="group" aria-label="Next steps">
      <span className="ns-label">Next</span>
      {steps.map((s) => {
        const Icon = ICON[s.id];
        return (
          <button key={s.id} type="button" title={s.title} disabled={busy} onClick={() => onPick(s)}>
            <Icon strokeWidth={1.7} aria-hidden />
            {s.label}
          </button>
        );
      })}
      <small>Each opens a card with its price. Nothing runs until you approve.</small>
    </div>
  );
}
