"use client";

/* A dub's card (lib/dubbing.ts; docs/tasks/task-dubbing.md).

   The clip to re-speak, the language, the person's word that the voices on
   it are theirs or their owners agreed, and Render -- the click that spends
   -- beside what it costs. The price is the server's (POST /api/dubbing/quote:
   the clip's length in whole minutes), asked again whenever a choice that
   moves it changes, and Render sends that number back so the run happens at
   the price shown or not at all.

   The look is the step card's (still-step.css + effect-step.css). */
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Languages } from "lucide-react";
import { quoteDub } from "@/lib/studio-api";
import { madeStatus } from "@/lib/made-state";
import {
  dubMissing,
  dubPriceKey,
  dubRequest,
  languageName,
  priceLine,
  type ClipChoice,
  type DubMenu,
  type DubState,
  type Paid,
} from "@/lib/dubbing";
import type { Turn } from "@/lib/assistant";
import "@/components/studio/still-step.css";
import "@/components/studio/effect-step.css";
import "@/components/studio/dubbing-step.css";

type StepState = "waiting" | "running" | "done" | "failed";
const LABEL: Record<StepState, string> = {
  waiting: "Waiting for approval",
  running: "Working",
  done: "Done",
  failed: "Not made",
};
const SHOW_CLIPS = 6;

export function DubbingStep({
  turn,
  menu,
  choices,
  busy,
  projectId,
  onPatch,
  onApprove,
}: {
  turn: Turn;
  /** GET /api/dubbing; null while it loads */
  menu: DubMenu | null;
  /** the clips there are to dub: the thread's, newest first */
  choices: ClipChoice[];
  busy: boolean;
  projectId?: number | null;
  /** a change to this card, applied to its CURRENT state */
  onPatch: (fn: (s: DubState) => DubState) => void;
  /** the Render click: `credits` is the price this card is showing */
  onApprove: (credits: number, charged: boolean) => void;
}) {
  const db = turn.dub as DubState;
  const status = turn.made ? madeStatus(turn.made) : undefined;
  const state: StepState = !turn.made ? "waiting" : status === "running" ? "running" : status === "done" ? "done" : "failed";
  const open = state === "waiting" || state === "failed";
  const exempt = !!menu?.exempt;

  const [price, setPrice] = useState<(Paid & { minutes: number; seconds: number }) | null>(null);
  const [problem, setProblem] = useState("");
  const asked = useRef(0);

  const shown = useMemo(() => {
    const list = choices.slice(0, SHOW_CLIPS);
    // the picked clip stays listed whatever else arrives
    return db.clip && !list.some((c) => c.ref === db.clip?.ref) ? [db.clip, ...list.slice(0, SHOW_CLIPS - 1)] : list;
  }, [choices, db.clip]);

  /* the dub's price: the clip decides it (its minutes), then the language
     and speakers only when they are wrong; consent and the project do not */
  const gap = menu ? dubMissing(db, menu) : "loading";
  const req = dubRequest(db, projectId);
  const priceKey = dubPriceKey(db);
  useEffect(() => {
    if (!open || !req || gap) return;
    const mine = ++asked.current;
    const timer = setTimeout(() => {
      quoteDub(req)
        .then((q) => {
          if (mine !== asked.current) return;
          setPrice({ credits: q.credits, charged: q.charged, minutes: q.billed_minutes, seconds: q.clip_seconds });
          setProblem("");
        })
        .catch((e) => {
          if (mine !== asked.current) return;
          setPrice(null);
          setProblem(e instanceof Error ? e.message : "That cannot be priced.");
        });
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- priceKey stands for the request
  }, [priceKey, open, gap]);

  const canRender = open && !busy && !gap && !!price && db.consent;
  const language = languageName(menu, db.target);
  const line = !open
    ? db.paid
      ? priceLine(db.paid, exempt)
      : ""
    : gap && gap !== "loading"
      ? gap
      : problem ||
        (price
          ? `${Math.round(price.seconds)}s · billed as ${price.minutes} minute${price.minutes === 1 ? "" : "s"} · ${priceLine(price, exempt)}`
          : "Pricing…");

  return (
    <div className="ss fx db" data-state={state}>
      <div className="ss-head">
        <Languages strokeWidth={1.6} />
        <b>Dub a clip</b>
        <span>{menu?.label ?? "ElevenLabs Dubbing"}</span>
        <em>{LABEL[state]}</em>
      </div>

      {open ? (
        <>
          <div className="db-sec">
            <span className="db-k">Clip</span>
            <div className="db-clips" role="radiogroup" aria-label="The clip to dub">
              {shown.map((c) => (
                <button
                  type="button"
                  key={c.ref}
                  role="radio"
                  aria-checked={db.clip?.ref === c.ref}
                  className={db.clip?.ref === c.ref ? "on" : ""}
                  onClick={() => onPatch((s) => ({ ...s, clip: c }))}
                >
                  {c.from}
                </button>
              ))}
            </div>
            {!shown.length ? <small className="fx-none">There is no clip here yet. Make one, or open a clip from the Library.</small> : null}
          </div>

          <div className="db-row">
            <label className="fx-opt">
              <span>Dub into</span>
              <select value={db.target} aria-label="Language to dub into" onChange={(e) => onPatch((s) => ({ ...s, target: e.target.value }))}>
                <option value="">Pick a language</option>
                {(menu?.languages ?? []).map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="fx-opt">
              <span>Spoken now</span>
              <input
                value={db.source}
                maxLength={2}
                placeholder="auto"
                aria-label="Language spoken on the clip, a two-letter code"
                onChange={(e) => onPatch((s) => ({ ...s, source: e.target.value }))}
              />
            </label>
            <label className="fx-opt">
              <span>People</span>
              <input
                value={db.speakers}
                inputMode="numeric"
                maxLength={2}
                placeholder="auto"
                aria-label="How many people speak"
                onChange={(e) => onPatch((s) => ({ ...s, speakers: e.target.value }))}
              />
            </label>
          </div>

          <label className="db-consent">
            <input type="checkbox" checked={db.consent} onChange={(e) => onPatch((s) => ({ ...s, consent: e.target.checked }))} />
            <span>The voices on this clip are mine, or the people who own them agreed to it being dubbed.</span>
          </label>
        </>
      ) : (
        <div className="fx-on">
          <small>
            {db.clip?.from ?? "A clip"} · into {language}
          </small>
        </div>
      )}

      <div className="ss-go">
        {open ? (
          <button type="button" disabled={!canRender} onClick={() => price && onApprove(price.credits, price.charged && !exempt)}>
            {state === "failed" ? "Render again" : "Render"}
          </button>
        ) : (
          <span className="ss-ok">
            {state === "done" ? <Check strokeWidth={2.2} /> : <span className="ss-live" aria-hidden />}
            {state === "done" ? "Approved" : "Working…"}
          </span>
        )}
        <small>{open && !gap && price && !db.consent ? `${line} · tick the box above first` : line}</small>
      </div>
    </div>
  );
}
