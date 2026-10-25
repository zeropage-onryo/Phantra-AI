/* Aspect ratios a Nano Banana still can be drawn at. The API keeps its
   own allowlist (app/api.py GENERATE_ASPECTS); an id it does not know
   falls back to the server default, never a failed call. */
export const IMAGE_ASPECTS: { id: string; label: string }[] = [
  { id: "4:5", label: "4:5" },
  { id: "1:1", label: "1:1" },
  { id: "16:9", label: "16:9" },
  { id: "9:16", label: "9:16" },
  // the rest of the shapes the connector's `open_in_studio` can name
  // (2026-10-20); every image model takes them (src/fal.py IMAGE_SIZES)
  { id: "4:3", label: "4:3" },
  { id: "3:4", label: "3:4" },
  { id: "21:9", label: "21:9" },
];

/** The image shape a frame names (2026-10-20): "1104:832" -> "4:3". A
    frame is a pixel size, so it matches the shape whose ratio is within 3%
    of its own; anything further off (or not w:h) is null, never a guess. */
export function imageAspectFor(frame: string | null | undefined): string | null {
  const ratio = (s: string) => {
    const m = /^(\d+):(\d+)$/.exec(s.trim());
    return m && Number(m[2]) > 0 ? Number(m[1]) / Number(m[2]) : null;
  };
  const want = frame ? ratio(frame) : null;
  if (!want) return null;
  let best: { id: string; off: number } | null = null;
  for (const a of IMAGE_ASPECTS) {
    const r = ratio(a.id);
    if (!r) continue;
    const off = Math.abs(want - r) / r;
    if (off <= 0.03 && (!best || off < best.off)) best = { id: a.id, off };
  }
  return best ? best.id : null;
}

const SHAPE_WORDS: [RegExp, string][] = [
  [/\b(vertical|portrait[- ]orientation|phone[- ]screen)\b/i, "9:16"],
  [/\b(landscape|widescreen|wide[- ]screen|horizontal)\b/i, "16:9"],
  [/\bsquare\s+(frame|format|crop|post|image|still)\b/i, "1:1"],
];

/** The shape a still's prompt names in words, as one of IMAGE_ASPECTS, or ""
    (2026-10-24, the Vesper audit: 5 of 6 traced stills said "9:16" in the
    prompt and were drawn 4:5). A ratio written out wins over a word; a pair
    of numbers that is not one of the shapes (a time, "3:45") is not one. */
export function shapeInPrompt(text: string | null | undefined): string {
  const t = text || "";
  for (const m of t.matchAll(/\b(\d{1,2})\s*:\s*(\d{1,2})\b/g)) {
    const id = `${Number(m[1])}:${Number(m[2])}`;
    if (IMAGE_ASPECTS.some((a) => a.id === id)) return id;
  }
  for (const [re, id] of SHAPE_WORDS) if (re.test(t)) return id;
  return "";
}

/** The shape the prompt names when the still is drawn in another, or "".
    Said on the card before Approve, never fixed behind the person's back. */
export const shapeClash = (prompt: string | null | undefined, frame: string): string => {
  const named = shapeInPrompt(prompt);
  return named && frame && named !== frame ? named : "";
};
