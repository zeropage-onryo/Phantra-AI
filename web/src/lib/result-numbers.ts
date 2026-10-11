/* A short number on every result, usable in a sentence (2026-10-11; item 11
   of docs/tasks/task-studio-agent.md, from invideo's numbered assets).

   Every thing a conversation made -- a still, a clip, a written scene --
   gets a small number the moment it exists, and keeps it: "#3" is the same
   result until the conversation is cleared. A person then points at it the
   way they would across a table ("make 3 warmer", "animate #2"), the brain
   is told the list (src/result_refs.py), and a number its tools name comes
   back on the proposal for the page to bind to the actual picture.

   The number lives ON the result (`made.n`), never derived from where it
   sits in the thread: turns are cleared, retried and re-ordered, and a
   number that moved would point a sentence at the wrong picture.

   Pure and import-free: tests/result-numbers.test.mjs runs it as it is. */

export type ResultKind = "still" | "clip" | "scene";

/** the parts of a made record this file reads (lib/composer.ts `Made`) */
export type Numberable = {
  n?: number;
  output?: string;
  status?: string;
  image?: string | null;
  clip?: string | null;
  asset?: string | null;
  conceptId?: number | null;
  title?: string;
  prompt?: string;
  effect?: string;
};
type TurnLike = { made?: Numberable | null; failed?: boolean; content?: string; effect?: { label?: string } | null };

/** What a finished record IS, or null while it is nothing to point at:
    running, failed, stopped, or a still that "finished" with no picture. */
export function kindOf(m: Numberable | null | undefined): ResultKind | null {
  if (!m || m.status !== "done") return null;
  if (m.clip) return "clip";
  if (m.image) return "still";
  if (m.output === "video" && m.conceptId) return "scene";
  return null;
}

/** The next free number: one past the highest ever given in this thread. */
export function nextNumber(turns: TurnLike[]): number {
  let top = 0;
  for (const t of turns) if (t.made?.n && t.made.n > top) top = t.made.n;
  return top + 1;
}

/** The thread with a number on every result that has none yet, in thread
    order; numbers already given never change. The SAME array comes back
    when nothing needed one, so a write that changes nothing stays a no-op. */
export function numbered<T extends TurnLike>(turns: T[]): T[] {
  if (!turns.some((t) => t.made && !t.made.n && kindOf(t.made))) return turns;
  let next = nextNumber(turns);
  return turns.map((t) => (t.made && !t.made.n && kindOf(t.made) ? { ...t, made: { ...t.made, n: next++ } } : t));
}

export const refTag = (n: number) => `#${n}`;

/** The result a number names, or null. */
export function findResult<T extends TurnLike>(turns: T[], n: number): NonNullable<T["made"]> | null {
  for (const t of turns) if (t.made?.n === n && kindOf(t.made)) return t.made as NonNullable<T["made"]>;
  return null;
}

const LABEL_MAX = 80;
const short = (text: string) => {
  const one = text.replace(/\s+/g, " ").trim();
  return one.length > LABEL_MAX ? `${one.slice(0, LABEL_MAX).replace(/\s+\S*$/, "")}…` : one;
};

export type ResultRef = { n: number; kind: ResultKind; label: string };

/** What the brain is told about the thread's results: number, kind and a
    few words -- never an address. Newest 40, in number order. */
export function resultList(turns: TurnLike[]): ResultRef[] {
  const out: ResultRef[] = [];
  for (const t of turns) {
    const m = t.made;
    const kind = kindOf(m);
    if (!m || !m.n || !kind) continue;
    const label = kind === "scene" ? m.title || m.prompt || "" : m.effect ? t.effect?.label || m.effect : m.prompt || t.content || "";
    out.push({ n: m.n, kind, label: short(label) });
  }
  return out.sort((a, b) => a.n - b.n).slice(-40);
}

/** Numbers out of a tool argument (`on`, `results`): whole, positive, once
    each. Anything else is not a number a result has. */
export function numbersOf(raw: unknown): number[] {
  const list = Array.isArray(raw) ? raw : raw == null ? [] : [raw];
  const out: number[] = [];
  for (const v of list) {
    const n = typeof v === "number" ? v : typeof v === "string" && /^#?\d+$/.test(v.trim()) ? Number(v.trim().replace("#", "")) : NaN;
    if (Number.isInteger(n) && n > 0 && !out.includes(n)) out.push(n);
  }
  return out;
}

/** The pictures a make is held to, for the numbers it named: the stills
    among them, by the address the composer already holds. A number that is
    gone, or is not a still, contributes nothing. */
export function stillsFor<T extends TurnLike>(turns: T[], raw: unknown): { n: number; image: string }[] {
  const out: { n: number; image: string }[] = [];
  for (const n of numbersOf(raw)) {
    const m = findResult(turns, n);
    if (m && kindOf(m) === "still" && m.image) out.push({ n, image: m.image });
  }
  return out;
}

/** "#3" put into what the box holds, with a space each side where one is
    needed, so a click on a result's number reads as a word in the sentence. */
export function insertRef(text: string, n: number): string {
  const tag = refTag(n);
  if (!text) return `${tag} `;
  return `${text}${/\s$/.test(text) ? "" : " "}${tag} `;
}

/** "Held to #1 and #3", for a step's card; "" for none. */
export function heldLine(numbers: number[]): string {
  if (!numbers.length) return "";
  const tags = numbers.map(refTag);
  return `Held to ${tags.length > 1 ? `${tags.slice(0, -1).join(", ")} and ${tags[tags.length - 1]}` : tags[0]}`;
}
