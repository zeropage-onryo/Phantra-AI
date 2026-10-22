/* Tappable questions (2026-10-22, vesper_v2; docs/tasks/task-vesper-v2.md).

   The brain can ask one question as something to TAP rather than type:
   colour swatches, aspect chips, an A/B pick, or plain chips. It emits it
   as the `ask_choice` tool (src/guide_tools.py ASK_TOOL) -- a write in the
   proposal sense, so the turn ends on it and nothing runs -- and the
   thread draws it (components/studio/tappable-question.tsx). A tap sends
   the option's words as the person's next message, exactly as if typed.

   Pure: tests/vesper-v2.test.mjs runs this file as it is. */

export const ASK_TOOL = "ask_choice";
export const ASK_KINDS = ["chips", "swatches", "aspect", "ab"] as const;
export type AskKind = (typeof ASK_KINDS)[number];
export const MAX_OPTIONS = 6;
export const MIN_OPTIONS = 2;

export type AskOption = {
  label: string;
  /** what the tap sends when it is not the label (an aspect's "4:5") */
  value?: string;
  /** swatches: a #rrggbb colour */
  swatch?: string;
  /** ab: the number of an earlier result the option points at */
  on?: number;
};
export type AskQuestion = { ask: string; kind: AskKind; options: AskOption[] };

export const isAskTool = (tool?: string | null) => tool === ASK_TOOL;

const HEX = /^#[0-9a-f]{6}$/i;
const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");

/** The question off a proposal's args, cleaned the way the server cleans
    it, or null when it is not one a card can draw (fewer than two options). */
export function questionOf(raw: unknown): AskQuestion | null {
  const a = (raw ?? {}) as { ask?: unknown; kind?: unknown; options?: unknown };
  const ask = str(a.ask).slice(0, 160);
  if (!ask || !Array.isArray(a.options)) return null;
  const kind = (ASK_KINDS as readonly string[]).includes(str(a.kind)) ? (str(a.kind) as AskKind) : "chips";
  const options: AskOption[] = [];
  for (const item of a.options.slice(0, MAX_OPTIONS)) {
    const o = (typeof item === "string" ? { label: item } : (item ?? {})) as Record<string, unknown>;
    const label = str(o.label).slice(0, 40);
    if (!label) continue;
    const out: AskOption = { label };
    const value = str(o.value).slice(0, 80);
    if (value && value !== label) out.value = value;
    const swatch = str(o.swatch);
    if (HEX.test(swatch)) out.swatch = swatch.toLowerCase();
    if (typeof o.on === "number" && Number.isInteger(o.on) && o.on > 0) out.on = o.on;
    options.push(out);
  }
  if (options.length < MIN_OPTIONS) return null;
  if (kind === "swatches" && !options.every((o) => o.swatch)) return { ask, kind: "chips", options };
  return { ask, kind, options };
}

/** What a tap sends as the person's message: words, never an id. */
export function answerText(q: AskQuestion, o: AskOption): string {
  if (q.kind === "swatches" && o.swatch) return `${o.label} (${o.swatch})`;
  if (q.kind === "ab" && o.on) return `#${o.on} — ${o.label}`;
  return o.value ?? o.label;
}

/** "4:5" -> "4 / 5" for the aspect chip's little frame; undefined otherwise */
export const chipAspect = (o: AskOption) => {
  const m = /^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$/.exec(o.value ?? o.label);
  return m ? `${m[1]} / ${m[2]}` : undefined;
};
