/* Every shape (2026-11-02, docs/tasks/task-every-shape.md): the shapes an ad
   runs in, made from one finished clip or still by the free reformat. The
   server decides crop or pad per shape (src/cut/quick.py plan_every_shape);
   this file only says it. Pure, no imports: web/tests/every-shape.test.mjs. */

export const SHAPES = ["9:16", "1:1", "16:9"] as const;

/** where each shape runs, in a person's words */
export const PLACES: Record<string, string> = {
  "9:16": "Reels, Stories, TikTok, Shorts",
  "1:1": "Feed",
  "16:9": "YouTube, TV, web",
  "4:5": "Feed (tall)",
};

export type ShapeResult = {
  aspect: string;
  status: "same" | "have" | "made" | "failed";
  fit?: string | null;
  ref?: string | null;
  asset_id?: number | null;
  media_url?: string | null;
};

/** One shape's line under the button. */
export function shapeLine(r: ShapeResult): string {
  const where = PLACES[r.aspect] ? ` · ${PLACES[r.aspect]}` : "";
  if (r.status === "same") return `${r.aspect}${where} · this one`;
  if (r.status === "failed") return `${r.aspect}${where} · could not be made`;
  const how = r.fit === "crop" ? "cropped" : r.fit === "pad" ? "with bars" : "";
  const when = r.status === "have" ? "made before" : "new";
  return [`${r.aspect}${where}`, how, when].filter(Boolean).join(" · ");
}

/** The job's outcome in one sentence. */
export function shapesSummary(results: ShapeResult[]): string {
  const made = results.filter((r) => r.status === "made").length;
  const have = results.filter((r) => r.status === "have").length;
  const failed = results.filter((r) => r.status === "failed").length;
  const parts = [
    made ? `${made} new shape${made === 1 ? "" : "s"}` : "",
    have ? `${have} already in your Library` : "",
    failed ? `${failed} could not be made` : "",
  ].filter(Boolean);
  return parts.length ? `${parts.join(" · ")} · free` : "Every shape is already here.";
}

/** The Library id of a result, for its link, or null. */
export const resultId = (r: ShapeResult): number | null => {
  if (typeof r.asset_id === "number") return r.asset_id;
  const m = /^gen:(\d+)$/.exec(r.ref ?? "");
  return m ? Number(m[1]) : null;
};
