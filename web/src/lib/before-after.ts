/* Before and after (2026-10-27, Mike: "Am I able to do the before and after").

   A Halloween costume still is the one result whose "before" the studio
   knows for sure: the photo the card ran on (its source) beside what it
   made. The pair is compared on a slider where the result is drawn, and
   downloaded as one image (GET /api/side-by-side, src/side_by_side.py,
   free). Pure and import-free: tests/before-after.test.mjs runs it as is. */

/** The effects whose result is compared with its source. */
export const PAIRED_EFFECTS = new Set(["costume-preview"]);

export type Pair = {
  /** the source as the server is sent it (an upload's URL, `gen:<id>`) */
  beforeRef: string;
  /** a drawable address for it */
  before: string;
  /** the result's drawable address */
  after: string;
  /** the result's render id, `gen:<id>` -- what the download names */
  afterAsset: string | null;
};

type Source = { ref: string; kind: string; thumb?: string };

/** The pair for one finished effect, or null when it has none: another
    effect, a clip, no source that can be drawn, or nothing made yet. */
export function pairOf(
  effect: { effect: string; sources: Source[] } | null | undefined,
  made: { image?: string | null; clip?: string | null; asset?: string | null } | null | undefined,
): Pair | null {
  if (!effect || !made || !PAIRED_EFFECTS.has(effect.effect)) return null;
  const src = effect.sources[0];
  if (!src || src.kind !== "image" || !src.thumb || !made.image || made.clip) return null;
  return { beforeRef: src.ref, before: src.thumb, after: made.image, afterAsset: made.asset ?? null };
}

/** Where the side-by-side downloads from; null without a render id. */
export function sideBySideHref(pair: Pair): string | null {
  if (!pair.afterAsset || !/^gen:\d+$/.test(pair.afterAsset)) return null;
  return `/api/side-by-side?before=${encodeURIComponent(pair.beforeRef)}&after=${encodeURIComponent(pair.afterAsset)}`;
}
