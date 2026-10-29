// The affiliate program's web half (2026-10-26; the rules are
// src/affiliates.py, the terms printed here are generated from it into
// src/content/affiliate.json, and a Python test fails when they drift).
import { ApiError, apiFetch } from "@/lib/api";
import terms from "@/content/affiliate.json";
import { REF_COOKIE, cleanRef, dollars, readRef, refCookie as cookieFor } from "@/lib/affiliate-ref";

export const AFFILIATE_TERMS = terms;
export { REF_COOKIE, cleanRef, dollars, readRef };

/** The Set-Cookie string for a visit to a partner's link, for the terms' cookie length. */
export function refCookie(code: string, hostname: string, https: boolean): string {
  return cookieFor(code, hostname, https, terms.cookie_days);
}
export type Tier = { key: string; label: string; percent: number; months: number };
export type AffiliateSummary = {
  status: null | "pending" | "approved" | "rejected" | "suspended";
  code?: string | null;
  link?: string | null;
  payout_mode?: "credits" | "cash";
  paying_referrals?: number;
  signups?: number;
  tier?: Tier;
  next_tier?: (Tier & { needs: number }) | null;
  earnings?: { held_cents: number; payable_cash_cents: number; paid_cents: number };
  recent?: { id: number; date: string; cents: number; status: string; payout: string | null; percent: number; pays_on: string }[];
};

export type Loaded = { kind: "ok"; summary: AffiliateSummary } | { kind: "sign-in" } | { kind: "error"; message: string };

function outcome(e: unknown): Loaded {
  if (e instanceof ApiError) {
    if (e.status === 401) return { kind: "sign-in" };
    return { kind: "error", message: e.status >= 500 ? "The studio is unreachable right now — try again in a minute." : e.message };
  }
  return { kind: "error", message: "could not reach the studio" };
}

export async function loadAffiliate(): Promise<Loaded> {
  try {
    return { kind: "ok", summary: await apiFetch<AffiliateSummary>("/affiliates/me") };
  } catch (e) {
    return outcome(e);
  }
}

export async function applyAffiliate(body: {
  channel_url: string;
  audience: string;
  plan: string;
  accept_terms: boolean;
}): Promise<Loaded> {
  try {
    return { kind: "ok", summary: await apiFetch<AffiliateSummary>("/affiliates/apply", { method: "POST", body: JSON.stringify(body) }) };
  } catch (e) {
    return outcome(e);
  }
}

/** Tell the API which partner's link this person arrived on. Fire-and-forget:
 *  a failure must never show. The server ignores it unless the account is new
 *  and unpaid. */
export async function reportRef(code: string): Promise<void> {
  try {
    await apiFetch("/affiliates/attribute", { method: "POST", body: JSON.stringify({ code }) });
  } catch {
    // not signed in, or nothing to attribute -- both are fine
  }
}

