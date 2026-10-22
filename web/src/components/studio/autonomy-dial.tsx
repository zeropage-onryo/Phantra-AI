"use client";

/* The autonomy dial (lib/autonomy.ts, vesper_v2): Ask me everything ·
   Checkpoints · Autopilot, with the one line that holds in every setting --
   nothing is charged without the person's click. */
import { AUTONOMY_MODES, PRICE_CHECKPOINT, type Autonomy } from "@/lib/autonomy";
import "@/components/studio/vesper-v2.css";

export function AutonomyDial({ value, onChange, busy = false }: { value: Autonomy; onChange: (mode: Autonomy) => void; busy?: boolean }) {
  return (
    <div className="ad">
      <div className="ad-seg" role="radiogroup" aria-label="How much Vesper does on its own">
        {AUTONOMY_MODES.map((m) => (
          <button key={m.id} type="button" role="radio" aria-checked={m.id === value} title={m.note} disabled={busy} onClick={() => onChange(m.id)}>
            {m.label}
          </button>
        ))}
      </div>
      <span className="ad-line">{PRICE_CHECKPOINT}</span>
    </div>
  );
}
