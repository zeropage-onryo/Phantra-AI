/* Settings → Usage, the pure half (2026-10-11): how the credit history is
   filtered and worded, and the arithmetic of its 30-day chart. The history
   itself is the server's -- GET /api/billing/history, src/credit_history.py
   -- one row per movement of the ledger, in CREDITS; nothing here knows a
   dollar.

   No "@/..." imports: tests/credit-history.test.mjs loads this with node. */

export type EntryKind = "grant" | "hold" | "settle" | "release" | "expire";
/** what the credit was for: a clip, a still, an effect; or credit itself */
export type EntryGroup = "render" | "still" | "effect" | "grant";

export type Entry = {
  id: number;
  at: string;
  kind: EntryKind;
  /** signed: negative is credit leaving the balance */
  credits: number;
  /** the line: "LTX 2.3 clip, 6s", "Still · Nano Banana", "Monthly credits" */
  what: string;
  group: EntryGroup;
  /** the model, or the kind of credit */
  label: string;
  /** where the line can be opened, when there is somewhere */
  ref: { kind: "scene"; id: number; title: string } | { kind: "render"; id: number } | null;
  balance_after: number;
};

export type Summary = {
  window_days: number;
  /** every UTC day of the window, oldest first; 0 where nothing was spent */
  days: { day: string; credits: number }[];
  totals: { label: string; group: EntryGroup; credits: number; count: number }[];
  spent: number;
};

export type History = { items: Entry[]; next: number | null; summary?: Summary };

/* ── the filter chips ── */

export type HistoryFilter = "all" | "render" | "still" | "grant";
export const HISTORY_FILTERS: { id: HistoryFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "render", label: "Renders" },
  { id: "still", label: "Stills" },
  { id: "grant", label: "Grants" },
];

/** Renders are clips and effects, Stills are stills, Grants are credit
 *  arriving or lapsing. */
export function matches(entry: Pick<Entry, "group">, filter: HistoryFilter): boolean {
  if (filter === "all") return true;
  if (filter === "render") return entry.group === "render" || entry.group === "effect";
  return entry.group === filter;
}

/* ── the words ── */

const KIND_WORD: Record<EntryKind, string> = {
  grant: "Added",
  hold: "Held",
  settle: "Settled",
  release: "Returned",
  expire: "Expired",
};
/** the one word for what a row did */
export const kindWord = (kind: EntryKind) => KIND_WORD[kind] ?? "Changed";

/** What a row adds to its line. A hold takes the credit and its settle is
 *  only the DIFFERENCE between the hold and the final price -- usually
 *  nothing -- which reads as a mistake unless it is said. */
export function kindNote(entry: Pick<Entry, "kind" | "credits">): string {
  switch (entry.kind) {
    case "hold":
      return "held until it finishes";
    case "settle":
      return entry.credits === 0
        ? "finished at the held price"
        : entry.credits > 0
          ? "finished under the held price, the difference returned"
          : "finished over the held price";
    case "release":
      return "did not finish, the hold returned in full";
    default:
      return "";
  }
}

const num = (n: number) => n.toLocaleString("en-US");
/** "+1,500", "−87", "0": a real minus sign, so a column of them lines up */
export const signed = (n: number) => `${n > 0 ? "+" : n < 0 ? "−" : ""}${num(Math.abs(n))}`;

/** "2 clips", "1 still", "3 effects" */
export function countText(count: number, group: EntryGroup): string {
  const word = group === "still" ? "still" : group === "effect" ? "effect" : group === "grant" ? "grant" : "clip";
  return `${num(count)} ${word}${count === 1 ? "" : "s"}`;
}

/** The totals a list can hold: the largest `keep - 1` as they are and the
 *  rest folded into one "Everything else" row -- a long tail is never
 *  dropped, and never given a row each. */
export function foldTotals(totals: Summary["totals"], keep = 6): Summary["totals"] {
  if (totals.length <= keep) return totals;
  const head = totals.slice(0, keep - 1);
  const tail = totals.slice(keep - 1);
  return [
    ...head,
    {
      label: "Everything else",
      group: "render",
      credits: tail.reduce((sum, t) => sum + t.credits, 0),
      count: tail.reduce((sum, t) => sum + t.count, 0),
    },
  ];
}

/* ── the chart ── */

/** The top of the y axis for a largest value: a round number at or above
 *  it, never 0, whose half is round too (it is the middle gridline). */
export function niceMax(value: number): number {
  if (!(value > 0)) return 10;
  const pow = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 4, 5, 10]) {
    if (value <= step * pow) return Math.max(10, step * pow);
  }
  return 10 * pow;
}

/** "Oct 8" for a UTC day key ("2026-10-08") */
export function dayLabel(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  return Number.isNaN(d.getTime())
    ? day
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

/** Which days carry a label under the axis: the first, the last, and
 *  every `every`th in between that is not crowding either end. */
export function tickDays(count: number, every = 7): number[] {
  if (count <= 0) return [];
  if (count === 1) return [0];
  const ticks = [0];
  for (let i = every; i < count - 1; i += every) {
    if (count - 1 - i >= Math.ceil(every / 2)) ticks.push(i);
  }
  ticks.push(count - 1);
  return ticks;
}

export type Bar = { x: number; width: number; y: number; height: number };

/** Where each day's bar sits in a plot `width` by `height` (px), under a
 *  y axis that tops out at `max`. A bar is at most 24px wide and never
 *  fills its slot: 2px of surface stays between neighbours. A day with any
 *  spend at all is at least 2px tall, so it is never invisible. */
export function layoutBars(values: number[], width: number, height: number, max: number): Bar[] {
  const slot = values.length ? width / values.length : 0;
  const barWidth = Math.max(1, Math.min(24, slot - 2));
  return values.map((value, i) => {
    const tall = value > 0 ? Math.max(2, (Math.min(value, max) / max) * height) : 0;
    return { x: i * slot + (slot - barWidth) / 2, width: barWidth, y: height - tall, height: tall };
  });
}

/** A bar's outline: square at the baseline, its data end rounded by up
 *  to 4px (less when the bar is too small to carry it). */
export function barPath(bar: Bar, radius = 4): string {
  const r = Math.max(0, Math.min(radius, bar.width / 2, bar.height));
  const { x, y, width: w, height: h } = bar;
  if (h <= 0) return "";
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

/** the busiest day of the window, or null when nothing was spent */
export function peakDay(days: Summary["days"]): { day: string; credits: number } | null {
  const top = days.reduce<{ day: string; credits: number } | null>(
    (best, d) => (d.credits > (best?.credits ?? 0) ? d : best),
    null,
  );
  return top;
}
