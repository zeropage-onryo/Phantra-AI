/* What Settings says about credits, as pure functions (2026-10-11): how a
   lot is named, when it runs out and what a yearly plan releases next.
   The numbers themselves are the server's (GET /api/billing/balance);
   nothing here converts money, and nothing here knows a dollar.

   No "@/..." imports: tests/credits.test.mjs loads this file with node. */

export const num = (n: number) => n.toLocaleString("en-US");

/** "1 credit", "1,500 credits" */
export const creditsText = (n: number) => `${num(n)} ${Math.abs(n) === 1 ? "credit" : "credits"}`;

/** a ledger stamp as a time, or null when it is not one */
export function stamp(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  // the ledger writes offsets; a bare stamp (an older row) is UTC, never local
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "Nov 3", and the year when it is not this one */
export function dayText(iso: string | null | undefined, now: number = Date.now()): string {
  const d = stamp(iso);
  if (!d) return "";
  const sameYear = d.getUTCFullYear() === new Date(now).getUTCFullYear();
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
    timeZone: "UTC",
  });
}

/* ── lots ── */

export type Lot = {
  id: number;
  kind: string;
  credits: number;
  remaining: number;
  granted_at: string;
  expires_at: string | null;
};

const LOT_KIND: Record<string, string> = {
  subscription: "Plan credits",
  purchase: "Top-up",
  promo: "Trial credits",
  refund: "Refund",
  adjustment: "Adjustment",
};
/** what a lot is, in a customer's words */
export const lotLabel = (kind: string) => LOT_KIND[kind] ?? "Credits";

/** whole days until a stamp; 0 on its last day, negative once past */
export function daysUntil(iso: string | null | undefined, now: number = Date.now()): number | null {
  const d = stamp(iso);
  if (!d) return null;
  return Math.floor((d.getTime() - now) / 86_400_000);
}

/** under this many days a lot is "expiring soon" */
export const SOON_DAYS = 7;

export type Expiry = { text: string; soon: boolean };
/** "in 23 days", "tomorrow", "today" -- and whether to warn about it */
export function expiry(iso: string | null | undefined, now: number = Date.now()): Expiry {
  const days = daysUntil(iso, now);
  if (days === null) return { text: "Never", soon: false };
  if (days < 0) return { text: "Expired", soon: false };
  const text = days === 0 ? "today" : days === 1 ? "tomorrow" : `in ${days} days`;
  return { text, soon: days < SOON_DAYS };
}

/** the share of a lot still unspent, 0..1 */
export const lotLeft = (lot: Pick<Lot, "credits" | "remaining">) =>
  lot.credits > 0 ? Math.min(1, Math.max(0, lot.remaining / lot.credits)) : 0;

/** credits in lots that run out within SOON_DAYS */
export function expiringSoon(lots: Lot[], now: number = Date.now()): number {
  return lots
    .filter((l) => l.remaining > 0 && expiry(l.expires_at, now).soon)
    .reduce((sum, l) => sum + l.remaining, 0);
}

/* ── a yearly plan's next month ── */

export type Schedule = { plan: string; months_released: number; months_total: number; next_release_at: string | null };

/** The next monthly release of a yearly plan: how many credits, and when.
 *  `creditsOf` is the catalog's allowance for a plan key. */
export function nextRelease(
  schedules: Schedule[],
  creditsOf: (plan: string) => number | undefined,
  now: number = Date.now(),
): { credits: number; on: string; left: number } | null {
  const due = schedules
    .filter((s) => stamp(s.next_release_at))
    .sort((a, b) => stamp(a.next_release_at)!.getTime() - stamp(b.next_release_at)!.getTime())[0];
  if (!due) return null;
  const credits = creditsOf(due.plan);
  if (!credits) return null;
  return {
    credits,
    on: dayText(due.next_release_at, now),
    left: Math.max(0, due.months_total - due.months_released),
  };
}
