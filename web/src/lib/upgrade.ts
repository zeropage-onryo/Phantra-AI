/* The out-of-credits popup (2026-11-10, Mike: "get people to sign up after
   using credits with like a popup ... maybe like a discount signup too").

   Before this, running out was a red line with a small "Choose a plan" link
   beside it. Now the first refusal for an empty balance on a page opens the
   upgrade popup (components/studio/upgrade-modal.tsx): the three plans, with
   the welcome offer (src/welcome_offer.py) taken off the first month when the
   server says this workspace has one, and Checkout one click away.

   Any surface asks for it through one window event, so nothing has to hold a
   reference to the popup: lib/api.ts fires it on every 402, the shell's
   toast and <TopUpLink> fire it on a refusal they recognise
   (lib/out-of-credits.ts). The popup decides whether to actually open.

   Pure and import-free: tests/upgrade.test.mjs runs it as it is. */

export const UPGRADE_EVENT = "phantra:upgrade";

/** why the popup was asked for: an automatic refusal, or a person's click */
export type UpgradeReason = "refused" | "clicked";

/** Ask for the popup. A no-op on the server. */
export function requestUpgrade(reason: UpgradeReason = "refused") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(UPGRADE_EVENT, { detail: { reason } }));
}

/** The welcome offer as /api/billing/balance carries it. */
export type WelcomeOffer = {
  percent_off: number | null;
  amount_off_cents: number | null;
  duration: string;
  months: number | null;
  label: string;
};

/** A refusal opens the popup by itself at most once in this window: a
    person who closed it and tries again gets the link, not the popup in
    their face every click. A click on the link always opens it. */
export const AUTO_OPEN_GAP_MS = 10 * 60 * 1000;

export function shouldOpen(
  reason: UpgradeReason,
  account: { plan?: unknown; exempt?: boolean } | null | undefined,
  lastAutoOpenAt: number | null,
  now: number,
): boolean {
  // an operator account is never charged, so never sold to
  if (account?.exempt) return false;
  if (reason === "clicked") return true;
  return lastAutoOpenAt === null || now - lastAutoOpenAt >= AUTO_OPEN_GAP_MS;
}

/** A plan's first month with the offer taken off, in whole cents; the
    plain price when there is no offer. Never below zero. */
export function firstMonthCents(monthlyUsd: number, offer: WelcomeOffer | null | undefined): number {
  const cents = Math.round(monthlyUsd * 100);
  if (!offer) return cents;
  if (offer.percent_off) return Math.max(0, Math.round((cents * (100 - offer.percent_off)) / 100));
  if (offer.amount_off_cents) return Math.max(0, cents - offer.amount_off_cents);
  return cents;
}

/** "$10.50", "$24" -- cents shown only when there are some. */
export function dollars(cents: number): string {
  const whole = cents % 100 === 0;
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: whole ? 0 : 2,
  })}`;
}

/** What one plan card prints for its price, at one billing interval
    (2026-11-12, the Higgsfield-shaped popup): the big figure, the
    struck-through one beside it, the chip inside the button, and the line
    under the price. Yearly never carries the welcome offer (the server
    applies it to monthly plans only, src/welcome_offer.py). */
export type CardPrice = { cents: number; wasCents: number | null; chip: string | null; note: string };

export function cardPrice(
  plan: { monthly_usd: number; yearly_usd: number; yearly_monthly_usd: number },
  interval: "month" | "year",
  offer: WelcomeOffer | null | undefined,
): CardPrice {
  const full = Math.round(plan.monthly_usd * 100);
  if (interval === "year") {
    const yearCents = Math.round(plan.yearly_usd * 100);
    const saved = full * 12 - yearCents;
    const pct = Math.round((saved / (full * 12)) * 100);
    return {
      cents: Math.round(plan.yearly_monthly_usd * 100),
      wasCents: saved > 0 ? full : null,
      chip: saved > 0 ? `−${pct}% · Save ${dollars(saved)}/yr` : null,
      note: `billed yearly, ${dollars(yearCents)}`,
    };
  }
  const first = firstMonthCents(plan.monthly_usd, offer);
  if (offer && first < full) {
    const chip = offer.percent_off
      ? `−${offer.percent_off}% first month`
      : `${dollars(full - first)} off first month`;
    return { cents: first, wasCents: full, chip, note: `first month, then ${dollars(full)}/mo` };
  }
  return { cents: full, wasCents: null, chip: null, note: "billed monthly · cancel any time" };
}

/** How many of something a month's credits buy, floored, never negative. */
export function howMany(credits: number, each: number): number {
  return each > 0 ? Math.max(0, Math.floor(credits / each)) : 0;
}
