/* What's new (2026-10-25, docs/tasks/task-whats-new.md, src/whats_new.py):
   the Create wall's announcements, and the operator's Showcase list.

   The feed (GET /api/whats-new) is what one person sees: live tiles they can
   use, New ones first, with the unread count for the badge. The Showcase
   list (/api/whats-new/showcase/*) is the house account's owners' alone; a
   404 from it means "not yours", and the section draws nothing. */
import { apiFetch } from "@/lib/api";

export type ShowcaseStatus = "pending" | "rendering" | "review" | "live" | "skipped" | "retired";
export type ShowcaseSource = "model" | "effect" | "look" | "skill" | "feature" | "soon" | "deal";

export type ShowcaseItem = {
  id: string;
  source: ShowcaseSource;
  key: string;
  tag: string;
  title: string;
  line: string;
  accent: string;
  size: string;
  media_kind: "clip" | "still" | "pick" | "none";
  prompt: string;
  model: string;
  params: { seconds?: number; resolution?: string; aspect?: string; takes?: string[] };
  status: ShowcaseStatus;
  media_type: "video" | "image" | null;
  media_url: string | null;
  poster_url: string | null;
  note: string | null;
  gen_id: string | null;
  credits_spent: number;
  /** the render's price on the house account, when it is waiting to be rendered */
  credits?: number | null;
  price_note?: string;
  eta: string | null;
  live_at: string | null;
};

export type FeedItem = {
  id: string;
  source: ShowcaseSource;
  tag: string;
  title: string;
  line: string;
  accent: string;
  size: string;
  action: Record<string, unknown>;
  media: { kind: "video" | "image" | "none"; url: string | null; poster: string | null };
  eta: string | null;
  ends: string | null;
  new: boolean;
  unread: boolean;
  notify: boolean | null;
  you_asked: boolean;
  live_at: string | null;
};

export const whatsNew = () => apiFetch<{ items: FeedItem[]; unread: number }>("/whats-new");
export const markSeen = (ids: string[]) =>
  apiFetch<{ marked: number }>("/whats-new/seen", { method: "POST", body: JSON.stringify({ ids }) });
export const dismiss = (id: string) =>
  apiFetch<{ marked: number }>(`/whats-new/${encodeURIComponent(id)}/dismiss`, { method: "POST" });
export const notifyMe = (id: string) =>
  apiFetch<{ marked: number }>(`/whats-new/${encodeURIComponent(id)}/notify`, { method: "POST" });

const sc = (id: string, act = "") => `/whats-new/showcase/${encodeURIComponent(id)}${act ? `/${act}` : ""}`;

export const showcaseList = () => apiFetch<{ items: ShowcaseItem[] }>("/whats-new/showcase");
export const showcaseEdit = (id: string, fields: Partial<Pick<ShowcaseItem, "title" | "line" | "prompt">> & {
  seconds?: number;
  resolution?: string;
  aspect?: string;
}) => apiFetch<ShowcaseItem>(sc(id), { method: "PUT", body: JSON.stringify(fields) });
export const showcaseApprove = (id: string, expect_credits: number) =>
  apiFetch<{ job_id: string; credits: number }>(sc(id, "approve"), {
    method: "POST",
    body: JSON.stringify({ expect_credits }),
  });
export const showcasePick = (id: string, asset: string) =>
  apiFetch<ShowcaseItem>(sc(id, "pick"), { method: "POST", body: JSON.stringify({ asset }) });
export const showcaseMove = (id: string, act: "keep" | "redo" | "skip" | "restore") =>
  apiFetch<ShowcaseItem>(sc(id, act), { method: "POST" });

/** What the list's buttons may do with a row, by its status and kind. */
export function showcaseActions(item: ShowcaseItem): ("approve" | "pick" | "keep" | "redo" | "skip" | "restore")[] {
  const renders = item.media_kind === "clip" || item.media_kind === "still";
  switch (item.status) {
    case "pending":
      return [
        ...(renders ? (["approve"] as const) : []),
        "pick",
        ...(item.media_kind === "none" ? (["keep"] as const) : []),
        "skip",
      ];
    case "review":
      return ["keep", "redo", "pick", "skip"];
    case "live":
      return ["redo"];
    case "skipped":
      return ["restore"];
    default:
      return [];
  }
}
