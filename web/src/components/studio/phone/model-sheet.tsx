"use client";

/* The phone's model sheet (2026-10-26, board 3 of the "Phantra Mobile
   Studio" canvas). On a phone the composer's settings line folds into ONE
   button on the box ("Auto ▾", or the model picked), and this sheet holds
   what the line held, at thumb size: the model, the frame (or a still's
   shape) and the length. It sets the same state the desktop pickers set;
   nothing here prices or spends -- the price stays on the card. */
import { useEffect } from "react";
import { ShellPortal } from "./portal";
import { Check } from "lucide-react";
import type { SceneLengths } from "@/components/studio/duration-pill";

export type SheetOption = { id: string; label: string; note?: string };

/** The lengths offered as buttons: the usual cuts that fit the span (the
 *  desktop's slider takes any second; a phone gets five taps). A span that
 *  fits none of them offers its default. */
export function lengthChoices(span: SceneLengths): number[] {
  const fit = [5, 10, 15, 20, 30].filter((s) => s >= span.min && s <= span.max);
  return fit.length ? fit : [span.default];
}

type Props = {
  open: boolean;
  onClose: () => void;
  output: "image" | "video";
  models: SheetOption[];
  model: string;
  onModel: (id: string) => void;
  frames: SheetOption[];
  frame: string;
  onFrame: (id: string) => void;
  lengths: SceneLengths | null;
  seconds: number;
  onSeconds: (s: number) => void;
};

export function PhoneModelSheet(p: Props) {
  useEffect(() => {
    if (!p.open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && p.onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [p]);
  if (!p.open) return null;
  const value = p.lengths ? Math.min(p.lengths.max, Math.max(p.lengths.min, p.seconds || p.lengths.default)) : 0;
  return (
    <ShellPortal>
      <div className="ph-sheet-wrap">
        <button type="button" className="ph-scrim" aria-label="Close" onClick={p.onClose} />
        <section className="ph-sheet" role="dialog" aria-modal="true" aria-label={p.output === "video" ? "Video settings" : "Image settings"}>
          <span className="ph-grab" aria-hidden />
          <h2>Model</h2>
          <div className="ph-models" role="radiogroup" aria-label="Model">
            {p.models.map((m) => (
              <button key={m.id || "auto"} type="button" role="radio" aria-checked={p.model === m.id} onClick={() => p.onModel(m.id)}>
                <span>
                  <b>{m.label}</b>
                  {m.note ? <small>{m.note}</small> : null}
                </span>
                {p.model === m.id ? <Check strokeWidth={2.6} aria-hidden /> : null}
              </button>
            ))}
          </div>
          {p.frames.length ? (
            <>
              <h3>{p.output === "video" ? "Frame" : "Shape"}</h3>
              <div className="ph-segs" role="radiogroup" aria-label={p.output === "video" ? "Frame" : "Shape"}>
                {p.frames.map((f) => (
                  <button key={f.id} type="button" role="radio" aria-checked={p.frame === f.id} onClick={() => p.onFrame(f.id)}>
                    {f.label}
                  </button>
                ))}
              </div>
            </>
          ) : null}
          {p.output === "video" && p.lengths ? (
            <>
              <h3>Length</h3>
              <div className="ph-segs" role="radiogroup" aria-label="Length">
                {lengthChoices(p.lengths).map((s) => (
                  <button key={s} type="button" role="radio" aria-checked={value === s} onClick={() => p.onSeconds(s)}>
                    {s}s
                  </button>
                ))}
              </div>
            </>
          ) : null}
          <button type="button" className="ph-go" onClick={p.onClose}>
            Done
          </button>
        </section>
      </div>
    </ShellPortal>
  );
}
