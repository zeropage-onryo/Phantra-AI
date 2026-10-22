"use client";

/* A question the person taps (lib/tappable.ts, vesper_v2): swatches,
   aspect chips, an A/B pick or plain chips. A tap sends the option's
   words as their next message; nothing else happens here. */
import { answerText, chipAspect, type AskQuestion } from "@/lib/tappable";
import "@/components/studio/vesper-v2.css";

export function TappableQuestion({
  q,
  answered,
  busy,
  onTap,
}: {
  q: AskQuestion;
  /** what the person already answered (the next message), if they did */
  answered?: string;
  busy: boolean;
  onTap: (text: string) => void;
}) {
  const done = answered !== undefined;
  return (
    <div className="tq" role="group" aria-label={q.ask}>
      <p className="tq-ask">{q.ask}</p>
      <div className={`tq-opts${q.kind === "ab" ? " ab" : ""}`}>
        {q.options.map((o, i) => {
          const text = answerText(q, o);
          const ratio = q.kind === "aspect" ? chipAspect(o) : undefined;
          return (
            <button key={`${o.label}:${i}`} type="button" disabled={busy || done} title={done ? "" : `Sends “${text}”`} onClick={() => onTap(text)}>
              {q.kind === "swatches" && o.swatch ? <span className="tq-swatch" style={{ background: o.swatch }} aria-hidden /> : null}
              {ratio ? (
                <span className="tq-frame" aria-hidden>
                  <i style={{ aspectRatio: ratio }} />
                </span>
              ) : null}
              {q.kind === "ab" ? <b>{String.fromCharCode(65 + i)}{o.on ? ` · #${o.on}` : ""}</b> : null}
              <span>{o.label}</span>
            </button>
          );
        })}
      </div>
      {done ? <p className="tq-picked">You answered: {answered}</p> : null}
    </div>
  );
}
