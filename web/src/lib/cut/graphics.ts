/* The editor's graphics track, the page's half (2026-10-20; src/cut/graphics.py
   is the export's). The options the inspector offers, a new item's defaults,
   and the motion the preview draws -- the SAME eased offsets and fades the
   export's ffmpeg overlay applies, computed per frame, so the preview moves
   like the render. Nothing imported, so tests/cut-graphics.test.mjs runs it as
   it is. */

export type GType = "headline" | "background_word" | "card" | "label";
export type GItem = {
  id?: string;
  start: number;
  end: number;
  type: GType;
  text?: string;
  media?: string;
  position?: string;
  anim_in?: string;
  anim_out?: string;
  size?: string;
  color?: string;
  drift?: boolean;
  /** a soft shadow under type set over footage */
  shadow?: boolean;
  pill?: string;
};

export const TYPES: { id: GType; label: string; note: string }[] = [
  { id: "headline", label: "Headline", note: "a short line of kinetic text" },
  { id: "background_word", label: "Big word", note: "one huge faint word behind the rest" },
  { id: "card", label: "Card", note: "a still from the bin on a rounded card" },
  { id: "label", label: "Label", note: "a small pill: a name, a price, a place" },
];
export const POSITIONS = ["center", "left", "right", "top", "bottom", "lower_left"] as const;
export const ANIMS_IN = ["none", "fade", "rise", "slide_left", "slide_right"] as const;
export const ANIMS_OUT = ["none", "fade", "sink", "slide_left", "slide_right"] as const;
export const SIZES = ["s", "m", "l"] as const;
export const COLORS = ["auto", "primary", "accent", "background", "text", "white", "black"] as const;
export const WORD_MAX = 24;
export const TEXT_MAX = 120;

export const DEFAULTS: Record<GType, Partial<GItem>> = {
  headline: { position: "center", anim_in: "rise", anim_out: "fade", size: "m" },
  background_word: { position: "center", anim_in: "fade", anim_out: "fade", size: "l", drift: true },
  card: { position: "right", anim_in: "slide_left", anim_out: "fade", size: "m" },
  label: { position: "lower_left", anim_in: "fade", anim_out: "fade", size: "s" },
};

/* what the export's constants are (src/cut/graphics.py) */
export const MOVE_SECONDS = 0.5;
export const RISE = 0.05;
export const SLIDE = 0.28;
export const DRIFT = 0.04;
export const WORD_ALPHA = 0.14;

export const withDefaults = (item: GItem): GItem => ({ ...DEFAULTS[item.type], color: "auto", ...item });

/* how long a move takes each way, seconds */
export function moves(item: GItem, fps: number): { inS: number; outS: number } {
  const it = withDefaults(item);
  const len = (it.end - it.start) / fps;
  const move = Math.min(MOVE_SECONDS, len / 3);
  return { inS: it.anim_in === "none" ? 0 : move, outS: it.anim_out === "none" ? 0 : move };
}

const clamp = (v: number) => Math.min(1, Math.max(0, v));

/* At `frame`, where the item is and how visible: dx / dy as fractions of the
   frame, alpha 0..1. null outside the item's time. Mirrors graphics.motion
   and the fades graphics.overlay_chain builds. */
export function pose(item: GItem, frame: number, fps: number): { dx: number; dy: number; alpha: number } | null {
  const it = withDefaults(item);
  if (frame < it.start || frame >= it.end) return null;
  const t = frame / fps;
  const s = it.start / fps;
  const e = it.end / fps;
  const { inS, outS } = moves(it, fps);
  let dx = 0;
  let dy = 0;
  let alpha = 1;
  if (inS) {
    const p = clamp((t - s) / inS);
    const rest = Math.pow(1 - p, 3);
    if (it.anim_in === "rise") dy += RISE * rest;
    else if (it.anim_in === "slide_left") dx += SLIDE * rest;
    else if (it.anim_in === "slide_right") dx -= SLIDE * rest;
    alpha = Math.min(alpha, p);
  }
  if (outS) {
    const q = clamp((t - (e - outS)) / outS);
    const gone = Math.pow(q, 3);
    if (it.anim_out === "sink") dy += RISE * gone;
    else if (it.anim_out === "slide_left") dx -= SLIDE * gone;
    else if (it.anim_out === "slide_right") dx += SLIDE * gone;
    alpha = Math.min(alpha, 1 - q);
  }
  if (it.type === "background_word" && it.drift !== false) dx -= DRIFT * clamp((t - s) / (e - s));
  return { dx, dy, alpha };
}

/* The problems the server would name, before an op is sent. */
export function problems(item: GItem): string[] {
  const out: string[] = [];
  if (!(item.end > item.start) || item.start < 0) out.push("it must end after it starts");
  if (item.type === "card") {
    if (!item.media) out.push("a card needs a still from the bin");
  } else {
    const text = (item.text ?? "").trim();
    if (!text) out.push("type some text");
    else if (text.length > (item.type === "background_word" ? WORD_MAX : TEXT_MAX))
      out.push(`at most ${item.type === "background_word" ? WORD_MAX : TEXT_MAX} characters`);
  }
  return out;
}

/* the first graphics track with room for [start, end), or null (a new one is needed) */
export function trackWithRoom(
  tracks: { id: string; kind: string; items?: { start: number; end: number }[] }[],
  start: number,
  end: number,
): string | null {
  const n = (id: string) => Number(id.replace(/\D+/g, "")) || 0;
  const g = tracks.filter((t) => t.kind === "graphic").sort((a, b) => n(a.id) - n(b.id));
  for (const t of g) {
    if (!(t.items ?? []).some((i) => i.start < end && start < i.end)) return t.id;
  }
  return null;
}

/* the next graphics track's id when one has to be added */
export function nextTrackId(tracks: { id: string }[]): string {
  let n = 1;
  while (tracks.some((t) => t.id === `G${n}`)) n++;
  return `G${n}`;
}

/* A first item of a type at the playhead: three seconds, the type's defaults,
   and words to replace. */
export function starter(type: GType, at: number, fps: number, media?: string): GItem {
  const text = { headline: "Your headline", background_word: "WORD", card: "", label: "Label" }[type];
  return {
    start: at,
    end: at + 3 * fps,
    type,
    ...(type === "card" ? { media } : { text }),
    ...DEFAULTS[type],
  } as GItem;
}
