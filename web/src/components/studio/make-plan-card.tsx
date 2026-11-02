"use client";

/* A plan's card (lib/make-plan.ts; docs/tasks/task-studio-agent.md item 2):
   the steps the brain proposed, in order, as one checklist. Each step
   says what it is, what it will do, and what it costs; a step can be
   edited or skipped before it runs, and one that costs credits is
   approved here, beside its price. What a step MAKES is drawn under the
   card as its own turn -- the still's step card and tile, the scene's
   shots -- exactly as if it had been asked for on its own.

   A render step (the scene's clip) is the one that always asks: "Approve
   all" neither counts nor covers it, and it waits for its own Approve with
   Auto on too. Its button says Render, at the price beside it.

   The look is the step card's (still-step.css), one row per step. */
import { useState } from "react";
import { Check, ListChecks } from "lucide-react";
import {
  alwaysAsks,
  batchOf,
  editable,
  isPaid,
  phase,
  progress,
  renderAhead,
  stepText,
  stepTitle,
  type GenerateMode,
  type Plan,
  type PlanStep,
  type Prices,
  type StepStatus,
  type FieldLimits,
  budget,
  cleanEdit,
  fieldsOf,
} from "@/lib/make-plan";
import "@/components/studio/make-plan-card.css";
import { TopUpLink } from "@/components/studio/top-up-link";

export type PlanHandlers = {
  busy: boolean;
  mode: GenerateMode;
  prices: Prices;
  /** an account that is not charged: prices read "not charged" */
  exempt: boolean;
  /** beside a paid step: "Nano Banana · 10 credits" */
  priceLine: (s: PlanStep) => string;
  /** under a step: the model proposed for it and why, or "" */
  modelNote: (s: PlanStep) => string;
  /** run from the first unfinished step; `all` approves the priced steps first */
  onStart: (all: boolean) => void;
  onApprove: (n: number) => void;
  /** what a step can be changed to: the frames a still takes, a scene's length */
  limits: FieldLimits;
  /** the account's balance, or null while it has not been read */
  have: number | null;
  /** the fields that changed (lib/make-plan.ts cleanEdit) */
  onEdit: (n: number, args: Record<string, unknown>) => void;
  onSkip: (n: number) => void;
  onRestore: (n: number) => void;
  onStop: () => void;
};

const STATUS: Record<StepStatus, string> = {
  pending: "",
  waiting: "Waiting for approval",
  running: "Working",
  done: "Done",
  failed: "Did not finish",
  skipped: "Skipped",
};

export function PlanCard({ plan, h }: { plan: Plan; h: PlanHandlers }) {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const now = phase(plan);
  const { done, of } = progress(plan);
  // the plan against the balance, said before Start (invideo's users find
  // out what a job costs when the credits are gone)
  const money = budget(plan, h.prices, { available: h.have, exempt: h.exempt }, h.mode);
  // what "Approve all" covers -- never the clip
  const batch = batchOf(plan, h.prices);
  const clipAhead = renderAhead(plan);
  const current = plan.steps.find((s) => s.status === "running" || s.status === "waiting");
  const head =
    now === "idle"
      ? "Not started"
      : now === "finished"
        ? "Done"
        : now === "paused"
          ? "Paused"
          : now === "waiting"
            ? "Waiting for approval"
            : `Step ${current?.n ?? done + 1} of ${plan.steps.length}`;

  const open = (s: PlanStep) => {
    setEditing(s.n);
    setDraft(Object.fromEntries(fieldsOf(s, h.limits).map((f) => [f.key, f.value === null ? "" : String(f.value)])));
  };
  // null = a required field is empty: nothing to save yet
  const changes = (s: PlanStep) => cleanEdit(s, draft, h.limits);
  const save = (s: PlanStep) => {
    const changed = changes(s);
    if (changed === null) return;
    if (Object.keys(changed).length) h.onEdit(s.n, changed);
    setEditing(null);
  };
  const set = (key: string, value: string) => setDraft((d) => ({ ...d, [key]: value }));

  return (
    <div className="pl" data-phase={now}>
      <div className="pl-head">
        <ListChecks strokeWidth={1.6} />
        <b>Plan</b>
        <span>{plan.steps.length} steps</span>
        <em>{head}</em>
      </div>
      {/* versions of one ad (2026-10-29, src/ad_results.py): what they test */}
      {plan.test ? <p className="pl-test">Testing: {plan.test}</p> : null}
      <ol className="pl-steps">
        {plan.steps.map((s) => {
          const paid = isPaid(s);
          const isEditing = editing === s.n;
          const canSkip = s.status === "pending" || s.status === "waiting" || s.status === "failed";
          return (
            <li key={s.n} className="pl-step" data-status={s.status}>
              <span className="pl-n" aria-hidden>
                {s.status === "done" ? <Check strokeWidth={2.4} /> : s.n}
              </span>
              <div className="pl-body">
                <div className="pl-title">
                  <b>{stepTitle(s)}</b>
                  {s.variant ? <span className="pl-variant">{s.variant}</span> : null}
                  {s.edited ? <i>edited</i> : null}
                  {STATUS[s.status] ? <em>{STATUS[s.status]}</em> : null}
                </div>
                {isEditing ? (
                  <div className="pl-fields">
                    {fieldsOf(s, h.limits).map((f) => {
                      const label = `Step ${s.n}: ${f.label}`;
                      const value = draft[f.key] ?? "";
                      if (f.kind === "words") {
                        return (
                          <textarea
                            key={f.key}
                            className="pl-edit"
                            value={value}
                            rows={4}
                            maxLength={4000}
                            aria-label={label}
                            onChange={(e) => set(f.key, e.target.value)}
                          />
                        );
                      }
                      return (
                        <label key={f.key} className="pl-set">
                          <span>{f.label}</span>
                          {f.kind === "choice" ? (
                            <select value={value} aria-label={label} onChange={(e) => set(f.key, e.target.value)}>
                              {f.value === "" || f.clearable ? <option value="">As picked in the box</option> : null}
                              {f.options.map((o) => (
                                <option key={o} value={o}>
                                  {f.labels?.[o] ?? o}
                                </option>
                              ))}
                            </select>
                          ) : f.kind === "number" ? (
                            <>
                              <input
                                type="number"
                                value={value}
                                min={f.min}
                                max={f.max}
                                step={1}
                                aria-label={`${label}, ${f.min} to ${f.max}`}
                                onChange={(e) => set(f.key, e.target.value)}
                              />
                              <small>
                                {f.unit} · {f.min}–{f.max}
                              </small>
                            </>
                          ) : (
                            <input
                              type="text"
                              value={value}
                              maxLength={200}
                              aria-label={label}
                              placeholder={f.required ? "" : "Optional"}
                              onChange={(e) => set(f.key, e.target.value)}
                            />
                          )}
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <p className="pl-text">{stepText(plan, s)}</p>
                )}
                {s.note && s.status !== "pending" ? (
                  <small className="pl-note">
                    {s.note}
                    <TopUpLink text={s.note} />
                  </small>
                ) : null}
                {s.why && !isEditing ? <small className="pl-why">{s.why}</small> : null}
                {/* the model the brain proposed for this step, and why (lib/step-model.ts) */}
                {!isEditing && h.modelNote(s) ? <small className="pl-why">{h.modelNote(s)}</small> : null}
                {s.uses.length && !isEditing ? (
                  <small className="pl-why">Held to the picture from step {s.uses.join(" and ")}</small>
                ) : null}
                <div className="pl-row">
                  <span className="pl-price">{paid ? h.priceLine(s) : "No credits"}</span>
                  <span className="pl-acts">
                    {isEditing ? (
                      <>
                        <button type="button" className="pl-link" onClick={() => setEditing(null)}>
                          Cancel
                        </button>
                        <button type="button" className="pl-link on" disabled={changes(s) === null} onClick={() => save(s)}>
                          Save
                        </button>
                      </>
                    ) : (
                      <>
                        {/* a step that is not running can be changed while
                            another one runs: the plan reads each step fresh */}
                        {editable(s) ? (
                          <button type="button" className="pl-link" onClick={() => open(s)}>
                            Edit
                          </button>
                        ) : null}
                        {canSkip ? (
                          <button type="button" className="pl-link" onClick={() => h.onSkip(s.n)}>
                            Skip
                          </button>
                        ) : null}
                        {s.status === "skipped" ? (
                          <button type="button" className="pl-link" onClick={() => h.onRestore(s.n)}>
                            Bring back
                          </button>
                        ) : null}
                        {s.status === "waiting" || s.status === "failed" ? (
                          <button type="button" className="pl-approve" disabled={h.busy} onClick={() => h.onApprove(s.n)}>
                            {s.status === "failed" ? "Try again" : alwaysAsks(s) ? "Render" : "Approve"}
                          </button>
                        ) : null}
                      </>
                    )}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="pl-foot">
        {now === "idle" || now === "paused" ? (
          <>
            <button type="button" className="pl-go" disabled={h.busy} onClick={() => h.onStart(false)}>
              {now === "idle" ? "Start" : "Resume"}
            </button>
            {h.mode === "ask" && batch.priced > 0 ? (
              <button
                type="button"
                className="pl-alt"
                disabled={h.busy}
                title={clipAhead ? "Covers the stills and keyframes priced here. The clip asks on its own." : undefined}
                onClick={() => h.onStart(true)}
              >
                Approve all · {h.exempt ? "not charged" : `${batch.credits.toLocaleString()} credits`}
              </button>
            ) : null}
          </>
        ) : null}
        {now === "running" ? (
          <button type="button" className="pl-alt" onClick={h.onStop}>
            Stop
          </button>
        ) : null}
        <small>
          {now === "finished" ? `${done} of ${of} steps done` : money.line}
          {/* short before it starts: the way to cover it, here */}
          {now !== "finished" && money.short > 0 ? <TopUpLink always /> : null}
        </small>
      </div>
    </div>
  );
}
