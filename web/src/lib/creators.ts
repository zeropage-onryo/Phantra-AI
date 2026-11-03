// Phantra Creators' web half (2026-11-03; the rules are src/creators.py and
// the routes app/creator_routes.py). The application needs a Phantra sign-in,
// like the affiliate one, so a creator is someone who has used the studio.
import { ApiError, apiFetch } from "@/lib/api";

export type CreatorStatus = null | "pending" | "approved" | "rejected";
export type CreatorSummary = { status: CreatorStatus; applied_at?: string };

export type Loaded = { kind: "ok"; summary: CreatorSummary } | { kind: "sign-in" } | { kind: "error"; message: string };

function outcome(e: unknown): Loaded {
  if (e instanceof ApiError) {
    if (e.status === 401) return { kind: "sign-in" };
    return { kind: "error", message: e.status >= 500 ? "The studio is unreachable right now. Try again in a minute." : e.message };
  }
  return { kind: "error", message: "Could not reach the studio." };
}

export async function loadCreator(): Promise<Loaded> {
  try {
    return { kind: "ok", summary: await apiFetch<CreatorSummary>("/creators/me") };
  } catch (e) {
    return outcome(e);
  }
}

export async function applyCreator(body: {
  channel_url: string;
  what_you_make: string;
  accept_terms: boolean;
  full_name?: string;
  country?: string;
  more_links?: string;
  contribute?: string;
}): Promise<Loaded> {
  try {
    return { kind: "ok", summary: await apiFetch<CreatorSummary>("/creators/apply", { method: "POST", body: JSON.stringify(body) }) };
  } catch (e) {
    return outcome(e);
  }
}
