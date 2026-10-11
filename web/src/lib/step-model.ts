/* The model a step is made on (2026-10-11; item 12 of
   docs/tasks/task-studio-agent.md, src/model_menu.py).

   The brain may propose a model with a still or a scene -- an id out of
   the list the studio handed it -- and say why in a few words. This is how
   the page reads that proposal:

   - A STILL is drawn on the model the person chose on its card; else the
     one the brain proposed, when the picker has it; else the picker's. The
     price beside Approve is that model's, whichever it is.
   - A SCENE's proposed model is only where its Render card opens. Nothing
     here picks a renderer.

   One promise is kept in code rather than left to a model: with Auto on,
   a send said what it could spend (lib/continue.ts sendCost, the PICKED
   model's price). A proposed model that costs MORE than that is therefore
   never drawn on without asking -- the still waits on its card.

   Pure and import-free: tests/step-model.test.mjs runs it as it is. */

export type ModelOption = {
  id: string;
  label: string;
  note?: string;
  references?: boolean;
  credits?: number | null;
};

export type StepModel = {
  /** the model the step is made on right now */
  id: string;
  /** who put it there */
  by: "you" | "proposed" | "picked";
  /** the brain's reason, shown only while its proposal stands */
  why: string;
};

const text = (v: unknown) => (typeof v === "string" ? v.trim() : "");

/** The brain's proposal off a make's arguments, when the menu has that
    model; null for none, or for an id the menu does not list (a model this
    account cannot use is no proposal). */
export function proposedOf(args: Record<string, unknown> | null | undefined, menu: ModelOption[]): { id: string; why: string } | null {
  const id = text(args?.model);
  if (!id || !menu.some((m) => m.id === id)) return null;
  return { id, why: text(args?.model_why) };
}

/** Which model a still's step is made on: the person's own choice on the
    card, else the proposal, else the picker's. A choice the menu no longer
    lists falls through to the next. */
export function stepModel(
  chosen: string | null | undefined,
  args: Record<string, unknown> | null | undefined,
  menu: ModelOption[],
  picker: string,
): StepModel {
  if (chosen && menu.some((m) => m.id === chosen)) return { id: chosen, by: "you", why: "" };
  const proposed = proposedOf(args, menu);
  if (proposed) return { id: proposed.id, by: "proposed", why: proposed.why };
  return { id: picker, by: "picked", why: "" };
}

export const optionOf = (menu: ModelOption[], id: string | null | undefined) => menu.find((m) => m.id === id) ?? null;

/** "Ideogram 4.5 · 19 credits" for the card's select. */
export function optionLabel(m: ModelOption): string {
  return typeof m.credits === "number" ? `${m.label} · ${m.credits.toLocaleString("en-US")} credits` : m.label;
}

/** What the card says under the model: whose pick it is, and why. */
export function modelLine(step: StepModel, menu: ModelOption[]): string {
  const name = optionOf(menu, step.id)?.label ?? "";
  if (step.by === "proposed") return `${name ? `${name} proposed` : "Proposed"}${step.why ? `: ${step.why}` : ""}`;
  if (step.by === "you") return "Your choice for this still";
  return "";
}

/** A model with no reference input, and references that would not reach
    it: said on the card before the click, never after. "" otherwise. */
export function referencesWarning(m: ModelOption | null, attached: number): string {
  if (!m || m.references !== false || attached <= 0) return "";
  return `${m.label} takes no references: the ${attached === 1 ? "picture" : `${attached} pictures`} attached will not reach it.`;
}

/** With Auto on: may this step be drawn without asking? Only when its
    model costs no more than the one the send button priced. An unknown
    price is not "no more". */
export function autoCovers(step: StepModel, menu: ModelOption[], picker: string): boolean {
  if (step.id === picker) return true;
  const mine = optionOf(menu, step.id)?.credits;
  const picked = optionOf(menu, picker)?.credits;
  return typeof mine === "number" && typeof picked === "number" && mine <= picked;
}

/** id -> credits, for a plan's per-step prices. */
export function creditsById(menu: ModelOption[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of menu) if (typeof m.credits === "number") out[m.id] = m.credits;
  return out;
}

/** What a scene's result says about its proposed renderer; "" for none. */
export function renderLine(clips: ModelOption[], id: string | null | undefined, why?: string | null): string {
  const m = optionOf(clips, id);
  if (!m) return "";
  return `Its Render card opens on ${m.label}${why ? `: ${why}` : ""}`;
}
