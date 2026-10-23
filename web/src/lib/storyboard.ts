/* The storyboard (2026-10-22, vesper_v2; docs/tasks/task-vesper-v2.md).

   With the flag on the shots are the main area and Vesper docks beside
   them. A storyboard is read OFF THE THREAD: every written scene in the
   conversation (a video `made` with timed shots), newest first, each shot
   as a card -- its still or clip, its length, the model its Render card
   opens on, its words. Nothing here is a second store: the thread is the
   record, and the cards are a view of it.

   Reordering is a VIEW order kept per browser (the scene's timed windows
   on the server are not rewritten by a drag; the editor cuts, this
   arranges). Editing a shot's words here changes what the card shows and
   what "Redo this shot only" is asked with; the scene row is the writer's.
   "Redo this shot only" names {conceptId, part}: the page opens that
   scene's priced Render card on it. It never renders.

   Pure: tests/vesper-v2.test.mjs runs this file as it is. */
import type { Turn } from "./assistant";
import type { Made } from "./composer";

export type ShotCard = {
  /** unique on the board: `${madeId}:${n}` */
  key: string;
  madeId: string;
  conceptId: number | null;
  n: number;
  seconds: number;
  start: number;
  end: number;
  text: string;
  still: string | null;
  clip: string | null;
  /** the clip model the Render card opens on ("" = the studio's default) */
  model: string;
  modelLabel: string;
};

export type SceneBoard = {
  madeId: string;
  conceptId: number | null;
  title: string;
  prompt: string;
  seconds: number | null;
  /** the scene's frame ("9:16"), so the stage draws its shots in their shape */
  frame: string | null;
  shots: ShotCard[];
  /** every shot has its clip */
  rendered: boolean;
};

const pad = (n: number) => String(n).padStart(2, "0");

/** Every written scene in the thread as a board, newest first. */
export function boardsOf(turns: Turn[], labelFor: (id?: string) => string | undefined = () => undefined): SceneBoard[] {
  const out: SceneBoard[] = [];
  for (let i = turns.length - 1; i >= 0; i--) {
    const m = turns[i].made as Made | undefined;
    if (!m || m.output !== "video" || m.status !== "done" || !m.parts?.length) continue;
    const model = m.renderModel ?? "";
    const modelLabel = (model && labelFor(model)) || (model ? model : "Default model");
    const shots: ShotCard[] = m.parts.map((p) => ({
      key: `${m.id}:${p.n}`,
      madeId: m.id,
      conceptId: m.conceptId ?? null,
      n: p.n,
      seconds: p.seconds,
      start: p.start,
      end: p.end,
      text: (p.text || p.prompt || "").trim(),
      still: p.reference_image ?? null,
      clip: p.media_url ?? null,
      model,
      modelLabel,
    }));
    out.push({
      madeId: m.id,
      conceptId: m.conceptId ?? null,
      title: m.title || `Scene ${out.length + 1}`,
      prompt: m.prompt ?? "",
      seconds: m.seconds ?? null,
      frame: m.frame ?? null,
      shots,
      rendered: shots.every((s) => !!s.clip),
    });
  }
  return out;
}

/** A frame ("9:16") as a CSS aspect-ratio ("9 / 16"); null for anything else. */
export function aspectOf(frame: string | null | undefined): string | null {
  const m = /^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$/.exec((frame ?? "").trim());
  return m && Number(m[1]) > 0 && Number(m[2]) > 0 ? `${m[1]} / ${m[2]}` : null;
}

/** The list with the item at `from` moved to `to`; the same list when the
    move is out of range or a no-op. */
export function reorder<T>(list: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0 || from >= list.length || to >= list.length) return list;
  const out = list.slice();
  const [item] = out.splice(from, 1);
  out.splice(to, 0, item);
  return out;
}

/** The board's shots in a kept order (shot numbers); numbers the board
    does not have are dropped, shots the order forgot go last. */
export function ordered(board: SceneBoard, order: number[] | undefined): ShotCard[] {
  if (!order?.length) return board.shots;
  const byN = new Map(board.shots.map((s) => [s.n, s]));
  const seen = new Set<number>();
  const out: ShotCard[] = [];
  for (const n of order) {
    const s = byN.get(n);
    if (s && !seen.has(n)) {
      out.push(s);
      seen.add(n);
    }
  }
  for (const s of board.shots) if (!seen.has(s.n)) out.push(s);
  return out;
}

/** A shot's words changed on the card. */
export function withText(board: SceneBoard, n: number, text: string): SceneBoard {
  return { ...board, shots: board.shots.map((s) => (s.n === n ? { ...s, text: text.trim() } : s)) };
}

/** What "Redo this shot only" asks for: that scene's Render card, on this
    shot. Never a render. */
export const redoTarget = (s: Pick<ShotCard, "conceptId" | "n">) =>
  s.conceptId ? { conceptId: s.conceptId, part: s.n } : null;

export const shotLabel = (s: Pick<ShotCard, "n" | "start" | "end">) => `Shot ${pad(s.n)} · ${s.start}–${s.end}s`;

/* the view order survives a reload, per browser */
const KEY = "phantra:storyboard:order";
export function loadOrders(): Record<string, number[]> {
  try {
    const raw = sessionStorage.getItem(KEY);
    const v = raw ? (JSON.parse(raw) as unknown) : null;
    return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, number[]>) : {};
  } catch {
    return {};
  }
}
export function saveOrders(orders: Record<string, number[]>) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(orders));
  } catch {
    /* fine */
  }
}
