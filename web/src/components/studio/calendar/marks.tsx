"use client";

/* The two marks every calendar surface draws (2026-10-22,
   docs/tasks/task-calendar.md):

   PlatformIcon -- the platform's own glyph, from `simple-icons` (CC0), in
   its brand colour. TikTok and X are black marks, so they are drawn in
   bone on the studio's dark ground. A platform the set lacks (LinkedIn
   asked to be removed from it) gets a two-letter text mark until its own
   kit lands with its provider.

   StateGlyph -- one ring, five fills, so a post's state reads without a
   colour legend and survives the fade on a sent post: hollow = queued,
   half = sending, full = published, barred = refused, dashed = draft. */
import { siDiscord, siFacebook, siInstagram, siReddit, siTiktok, siX, siYoutube } from "simple-icons";
import type { PostState } from "@/lib/studio-api";

type Icon = { path: string; hex: string; title: string };
const ICONS: Record<string, Icon> = {
  instagram: siInstagram,
  tiktok: siTiktok,
  youtube: siYoutube,
  discord: siDiscord,
  x: siX,
  facebook: siFacebook,
  reddit: siReddit,
};
const TEXT_MARKS: Record<string, string> = { linkedin: "in", linkedin_page: "in" };
/** a black brand mark reads as nothing on the studio's ground */
const DARK = new Set(["000000", "010101"]);

export const PLATFORM_NAMES: Record<string, string> = {
  instagram: "Instagram",
  tiktok: "TikTok",
  youtube: "YouTube",
  discord: "Discord",
  x: "X",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  linkedin_page: "LinkedIn Page",
  reddit: "Reddit",
};

export function PlatformIcon({ provider, size = 14, mono = false, title }: { provider: string; size?: number; mono?: boolean; title?: string }) {
  const icon = ICONS[provider];
  const label = title ?? PLATFORM_NAMES[provider] ?? provider;
  if (!icon) {
    return (
      <span className="cal-textmark" style={{ width: size, height: size, fontSize: Math.max(8, size * 0.55) }} role="img" aria-label={label}>
        {TEXT_MARKS[provider] ?? provider.slice(0, 2).toUpperCase()}
      </span>
    );
  }
  const fill = mono || DARK.has(icon.hex.toLowerCase()) ? "var(--bone)" : `#${icon.hex}`;
  return (
    <svg className="cal-pi" width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={label}>
      <path d={icon.path} fill={fill} />
    </svg>
  );
}

const STATE_WORDS: Record<PostState, string> = {
  draft: "Draft",
  queued: "Queued",
  publishing: "Sending",
  published: "Published",
  error: "Refused, needs you",
  cancelled: "Cancelled",
};

export const stateWord = (state: PostState) => STATE_WORDS[state] ?? state;

export function StateGlyph({ state, size = 11 }: { state: PostState; size?: number }) {
  return <span className={`cal-glyph ${state}`} style={{ width: size, height: size }} role="img" aria-label={stateWord(state)} />;
}
