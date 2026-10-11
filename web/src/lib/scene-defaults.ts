/* The frame and the scene length a new scene STARTS from (2026-10-11,
   Settings → Preferences), kept in this browser.

   The image model and Ask / Auto are remembered by the composer itself
   (lib/composer.ts: the last choice survives a reload). These two are
   different on purpose: changing the frame or the length on Create is for
   that scene only and is not remembered -- they are a default the person
   sets here, and "" / 0 means the server's own.

   No "@/..." imports: tests/preferences.test.mjs loads this with node. */

const FRAME_KEY = "zpf:composer:frame";
export function loadFrame(): string {
  try {
    return localStorage.getItem(FRAME_KEY) ?? "";
  } catch {
    return "";
  }
}
export function saveFrame(id: string) {
  try {
    if (id) localStorage.setItem(FRAME_KEY, id);
    else localStorage.removeItem(FRAME_KEY);
  } catch {
    /* fine */
  }
}
const SECONDS_KEY = "zpf:composer:seconds";
export function loadSceneSeconds(): number {
  try {
    const n = Number(localStorage.getItem(SECONDS_KEY));
    return Number.isFinite(n) && n > 0 ? Math.round(n) : 0;
  } catch {
    return 0;
  }
}
export function saveSceneSeconds(seconds: number) {
  try {
    if (seconds > 0) localStorage.setItem(SECONDS_KEY, String(Math.round(seconds)));
    else localStorage.removeItem(SECONDS_KEY);
  } catch {
    /* fine */
  }
}
/** The length a new scene starts at: the stored default when it is inside
 *  what the server offers, the server's own otherwise. */
export function startSeconds(stored: number, bounds: { min: number; max: number; default: number }): number {
  return stored >= bounds.min && stored <= bounds.max ? stored : bounds.default;
}
/** The frame a new scene starts in: the stored default when the server
 *  still offers it, the server's own otherwise. */
export function startFrame(stored: string, ids: string[], fallback: string): string {
  return stored && ids.includes(stored) ? stored : fallback;
}
