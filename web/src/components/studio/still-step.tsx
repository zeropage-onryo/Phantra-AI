"use client";

/* A still's step card (2026-10-08, after Runway Agent's "Ask before
   generating media"): what the brain will draw, at what frame, and Approve
   -- the one click that spends -- with the model and what a still costs
   under it. It stays as the step's record once drawn ("Approved"), and a
   still that failed can be approved again.

   ONE card for both places the brain talks: the Studio composer's stream
   (composer/turns.tsx, the still drawn below it as the send's tiles) and
   the assistant pill (assistant-pill.tsx, which has no tiles, so the still
   shows inside the card). The turn it reads is the shared thread's: a
   brain answer whose proposal is make_image, its `made` once approved. */
import { useState } from "react";
import { Check, ImagePlus, UserRound } from "lucide-react";
import type { Turn } from "@/lib/assistant";
import { SHEET_TOOL, mediaSrc } from "@/lib/composer";
import { shapeClash } from "@/lib/image-aspects";
import { madeStatus } from "@/lib/made-state";
import { modelLine, optionLabel, type ModelOption, type StepModel } from "@/lib/step-model";
import "@/components/studio/still-step.css";

export type StepState = "waiting" | "running" | "done" | "failed";

/** a brain answer that proposes an element sheet (2026-10-09) */
export const isSheetStep = (t: Turn) => t.role === "assistant" && t.reply?.proposal?.tool === SHEET_TOOL;

/** a brain answer that proposes a still: a step card, wherever it is drawn */
export const isStillStep = (t: Turn) => t.role === "assistant" && t.reply?.proposal?.tool === "make_image";

export function stepOf(t: Turn) {
  const args = (t.reply?.proposal?.args ?? {}) as { prompt?: unknown; aspect?: unknown };
  const prompt = typeof args.prompt === "string" && args.prompt.trim() ? args.prompt.trim() : t.content;
  const aspect = typeof args.aspect === "string" ? args.aspect : undefined;
  // a still that "finished" with nothing drawn is not done (lib/made-state.ts)
  const status = t.made ? madeStatus(t.made) : undefined;
  const state: StepState = !t.made
    ? "waiting"
    : status === "running"
      ? "running"
      : status === "done"
        ? "done"
        : "failed";
  return { prompt, aspect, frame: t.made?.frame ?? aspect ?? "", state };
}

/** the turn's own line says the same words as the card: leave it out */
export const lineIsPrompt = (t: Turn) => isStillStep(t) && t.content.trim() === stepOf(t).prompt;

const LABEL: Record<StepState, string> = {
  waiting: "Waiting for approval",
  running: "Generating",
  done: "Done",
  failed: "Not drawn",
};

export function StillStep({
  turn,
  line,
  busy,
  onApprove,
  showImage = false,
  held = "",
  models,
  model,
  onModel,
  warn = "",
  drawAt = "",
  onFrame,
  kit = "",
}: {
  turn: Turn;
  /** under Approve: "Nano Banana · 10 credits" */
  line: string;
  busy: boolean;
  onApprove: () => void;
  /** the pill draws the still inside the card; the composer draws it below */
  showImage?: boolean;
  /** "Held to #1 and #3": the earlier results the brain named for this
   *  still (lib/result-numbers.ts); "" for none */
  held?: string;
  /** THE MODEL THIS STILL IS DRAWN ON (lib/step-model.ts): the menu, the
   *  model it stands on now -- the person's choice, else the brain's
   *  proposal, else the picker's -- and the change. Absent, the card is the
   *  card it was and the picker decides. `line` is that model's price. */
  models?: ModelOption[];
  model?: StepModel;
  onModel?: (id: string) => void;
  /** a model with no reference input while pictures are attached; "" for none */
  warn?: string;
  /** THE FRAME THIS STILL IS DRAWN IN before it is drawn (2026-10-24): the
   *  person's switch, else the brain's `aspect`, else the settings line.
   *  "" leaves the card on the proposal's own frame. */
  drawAt?: string;
  /** switch this still's frame (the prompt named another shape) */
  onFrame?: (id: string) => void;
  /** the brand kit whose look is added to the prompt, or "" (the kit chip
   *  turns it off): nothing reaches the model that the card did not show */
  kit?: string;
}) {
  const [more, setMore] = useState(false);
  const { prompt, frame: drawn, state } = stepOf(turn);
  const open = state === "waiting" || state === "failed";
  const frame = open && drawAt ? drawAt : drawn;
  const clash = open && onFrame ? shapeClash(prompt, frame) : "";
  // offered while the click that spends has not happened; a card that has
  // run says what it ran on in `line`
  const choosing = !!models && models.length > 1 && !!model && !!onModel && (state === "waiting" || state === "failed");
  const said = models && model ? modelLine(model, models) : "";
  const image = showImage && state === "done" ? turn.made?.image : null;
  return (
    <div className="ss" data-state={state}>
      <div className="ss-head">
        <ImagePlus strokeWidth={1.6} />
        <b>Image</b>
        {frame ? <span>{frame}</span> : null}
        {held ? <span>{held}</span> : null}
        <em>{LABEL[state]}</em>
      </div>
      <p className={more ? "open" : undefined}>{prompt}</p>
      {prompt.length > 240 ? (
        <button type="button" className="ss-more" onClick={() => setMore((v) => !v)}>
          {more ? "Less" : "Full prompt"}
        </button>
      ) : null}
      {kit ? <small className="ss-kit">+ {kit} kit: look, palette, avoid list</small> : null}
      {clash ? (
        <div className="ss-clash" role="status">
          <span>
            The prompt says {clash}; the frame is {frame}.
          </span>
          <button type="button" disabled={busy} onClick={() => onFrame?.(clash)}>
            Use {clash}
          </button>
        </div>
      ) : null}
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img className="ss-image" src={mediaSrc(image)} alt="" />
      ) : null}
      {choosing ? (
        <label className="ss-opt">
          <span>Model</span>
          <select value={model.id} disabled={busy} onChange={(e) => onModel(e.target.value)}>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {optionLabel(m)}
              </option>
            ))}
          </select>
          {said ? <small>{said}</small> : null}
          {warn ? <small className="warn">{warn}</small> : null}
        </label>
      ) : null}
      <div className="ss-go">
        {state === "waiting" || state === "failed" ? (
          <button type="button" disabled={busy} onClick={onApprove}>
            {state === "failed" ? "Approve again" : "Approve"}
          </button>
        ) : (
          <span className="ss-ok">
            {state === "done" ? <Check strokeWidth={2.2} /> : <span className="ss-live" aria-hidden />}
            {state === "done" ? "Approved" : "Generating…"}
          </span>
        )}
        {line ? <small>{line}</small> : null}
      </div>
    </div>
  );
}

const SHEET_LABEL: Record<StepState, string> = {
  waiting: "Waiting for approval",
  running: "Drawing",
  done: "Done",
  failed: "Not drawn",
};

/* The element sheet's step (2026-10-09): who is saved and what is drawn
   (the turn's own line, written by src/creative_guide), Approve, and the
   price of one still under it -- a sheet is one GPT Image 2.5 still. The
   sheet itself lands below as the turn's tile, like a still. */
export function SheetStep({
  turn,
  line,
  busy,
  onApprove,
}: {
  turn: Turn;
  line: string;
  busy: boolean;
  onApprove: () => void;
}) {
  const { state } = stepOf(turn);
  const args = (turn.reply?.proposal?.args ?? {}) as { name?: unknown };
  const name = typeof args.name === "string" ? args.name : "";
  return (
    <div className="ss" data-state={state}>
      <div className="ss-head">
        <UserRound strokeWidth={1.6} />
        <b>Element sheet</b>
        <span>16:9</span>
        <em>{SHEET_LABEL[state]}</em>
      </div>
      <p className="open">{turn.content}</p>
      <div className="ss-go">
        {state === "waiting" || state === "failed" ? (
          <button type="button" disabled={busy} onClick={onApprove}>
            {state === "failed" ? "Approve again" : "Approve"}
          </button>
        ) : (
          <span className="ss-ok">
            {state === "done" ? <Check strokeWidth={2.2} /> : <span className="ss-live" aria-hidden />}
            {state === "done" ? `Saved${name ? ` ${name}` : ""} to Elements` : "Drawing…"}
          </span>
        )}
        {line ? <small>{line}</small> : null}
      </div>
    </div>
  );
}
