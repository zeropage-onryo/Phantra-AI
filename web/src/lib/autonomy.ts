/* The autonomy dial (2026-10-22, vesper_v2; docs/tasks/task-vesper-v2.md).

   Three settings for how much Vesper does on its own: Ask me everything,
   Checkpoints, Autopilot. ONE rule holds in every one of them: THE PRICE
   CHECKPOINT. A step that costs credits -- a still, a sheet, a scene's
   keyframes, a clip -- waits at its price for the person's own click,
   whatever the dial says. Autopilot may run the FREE steps (write a
   scene, keep references) without asking and start a plan on its own;
   it never approves a spend.

   So the dial never maps to the composer's "auto" GenerateMode (which
   draws a still on the send): with vesper_v2 on, `generateModeFor` is
   "ask" for every setting, and tests/vesper-v2.test.mjs holds it there.

   Pure and import-free on purpose (type imports only): the node tests run
   this file as it is. */
import type { GenerateMode, PlanStep } from "./make-plan";

/* what spends: lib/make-plan.ts PAID, kept in step by tests/vesper-v2.test.mjs */
const PAID: PlanStep["do"][] = ["image", "sheet", "keyframes", "render"];

export type Autonomy = "ask" | "checkpoints" | "autopilot";

export const AUTONOMY_MODES: { id: Autonomy; label: string; note: string }[] = [
  { id: "ask", label: "Ask me everything", note: "Vesper stops at every step, free or paid, and asks one question when the brief is thin" },
  { id: "checkpoints", label: "Checkpoints", note: "Free steps run; anything that costs credits waits at its price" },
  { id: "autopilot", label: "Autopilot", note: "Plans start on their own and free steps run; every credit still waits for your click" },
];

/** the line under the dial, in every mode */
export const PRICE_CHECKPOINT = "Every setting stops at the price. Nothing is charged without your click.";

export const isAutonomy = (v: unknown): v is Autonomy => AUTONOMY_MODES.some((m) => m.id === v);

const KEY = "phantra:composer:autonomy";
export function loadAutonomy(): Autonomy {
  try {
    const v = localStorage.getItem(KEY);
    return isAutonomy(v) ? v : "checkpoints";
  } catch {
    return "checkpoints";
  }
}
export function saveAutonomy(mode: Autonomy) {
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    /* fine */
  }
}

/** The composer's GenerateMode under the dial: ALWAYS "ask". "auto" draws
    a still on the send, and no setting of the dial may do that. */
export const generateModeFor = (_mode: Autonomy): GenerateMode => "ask";

/** Does a plan step stop for the person under this setting? A paid step
    always does (the price checkpoint); a free step only under Ask me
    everything. */
export function stopsAt(mode: Autonomy, step: Pick<PlanStep, "do">): boolean {
  if (PAID.includes(step.do)) return true;
  return mode === "ask";
}

/** Does a proposed plan start without a Start click? Checkpoints and
    Autopilot start it; its first paid step then waits at its price. */
export const startsPlans = (mode: Autonomy) => mode !== "ask";

export const autonomyLabel = (mode: Autonomy) => AUTONOMY_MODES.find((m) => m.id === mode)?.label ?? "Ask me everything";

/** what the plan card says beside its progress, per setting */
export function autonomyLine(mode: Autonomy): string {
  if (mode === "autopilot") return "Autopilot: free steps run on their own · each paid step waits at its price";
  if (mode === "checkpoints") return "Checkpoints: free steps run · each paid step waits at its price";
  return "Ask me everything: every step waits for you";
}
