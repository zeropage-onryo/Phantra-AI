/* The Video page's Camera move and Lens cards (2026-11-03, src/camera.py,
   prompts/camera.json, docs/tasks/task-camera-lens.md).

   The server decides the words and places them (camera.dress); this file only
   says, for the pick on screen, HOW a move reaches the model -- the same rule
   as camera.mode -- and what to show as chips under the prompt. Nothing here
   changes a price: the words and LTX's own setting cost nothing, and a
   reference clip rides only where the server lists it.

   Pure and import-free: tests/camera.test.mjs runs it as it is. */

export type CameraEntry = { id: string; label: string; words: string };
export type CameraCatalogue = {
  moves: CameraEntry[];
  focal: CameraEntry[];
  aperture: CameraEntry[];
  looks: CameraEntry[];
  conflicts: { a: string; b: string; why: string }[];
};
/** per model, from GET /api/direct/video (camera.menu_for) */
export type ModelCamera = { exact: string[]; clips: string[]; clip_resolutions: string[] };
export type CameraPick = { move: string; focal: string; aperture: string; look: string };
export type CameraMode = "exact" | "clip" | "guided";

export const NO_CAMERA: CameraPick = { move: "", focal: "", aperture: "", look: "" };

export const MODE_LABEL: Record<CameraMode, string> = {
  exact: "Exact",
  clip: "Reference clip",
  guided: "Guided",
};
export const MODE_NOTE: Record<CameraMode, string> = {
  exact: "the model's own camera setting",
  clip: "a reference clip of the move rides with the render",
  guided: "fixed words added to your prompt",
};

/** How this move reaches this model: camera.mode's rule. */
export function cameraMode(
  model: { camera?: ModelCamera | null } | null,
  moveId: string,
  startFrame: boolean,
  resolution: string | null | undefined,
): CameraMode | null {
  if (!moveId) return null;
  const cam = model?.camera;
  if (cam?.exact.includes(moveId)) return "exact";
  if (!startFrame && cam?.clips.includes(moveId) && resolution && cam.clip_resolutions.includes(resolution)) return "clip";
  return "guided";
}

/** Why two picks contradict each other, or "". */
export function cameraConflict(cat: CameraCatalogue | null | undefined, pick: CameraPick): string {
  if (!cat) return "";
  const chosen = new Set([pick.move, pick.focal, pick.aperture, pick.look].filter(Boolean));
  const hit = cat.conflicts.find((c) => chosen.has(c.a) && chosen.has(c.b));
  return hit ? hit.why : "";
}

/** Would picking `id` contradict what is already picked? Its reason, or "". */
export function blockedBy(cat: CameraCatalogue | null | undefined, pick: CameraPick, id: string): string {
  if (!cat || !id) return "";
  const chosen = new Set([pick.move, pick.focal, pick.aperture, pick.look].filter(Boolean));
  const hit = cat.conflicts.find((c) => (c.a === id && chosen.has(c.b)) || (c.b === id && chosen.has(c.a)));
  return hit ? hit.why : "";
}

const find = (list: CameraEntry[] | undefined, id: string) => (id ? (list ?? []).find((e) => e.id === id) ?? null : null);

export type CameraChip = { key: "move" | "lens"; badge: string; text: string };

/** The lines the server will add, as chips. */
export function cameraChips(
  cat: CameraCatalogue | null | undefined,
  model: { camera?: ModelCamera | null } | null,
  pick: CameraPick,
  startFrame: boolean,
  resolution: string | null | undefined,
): CameraChip[] {
  if (!cat) return [];
  const out: CameraChip[] = [];
  const move = find(cat.moves, pick.move);
  const how = cameraMode(model, pick.move, startFrame, resolution);
  if (move && how) {
    out.push({
      key: "move",
      badge: MODE_LABEL[how],
      text: how === "clip" ? `Follows the ${move.label.toLowerCase()} reference clip` : move.words,
    });
  }
  const lens = [find(cat.focal, pick.focal), find(cat.aperture, pick.aperture), find(cat.looks, pick.look)].filter(Boolean) as CameraEntry[];
  if (lens.length) out.push({ key: "lens", badge: "Lens", text: lens.map((e) => e.words).join("; ") });
  return out;
}

/** The dock chips' short values. */
export function moveValue(cat: CameraCatalogue | null | undefined, pick: CameraPick): string {
  return find(cat?.moves, pick.move)?.label ?? "Camera";
}
export function lensValue(cat: CameraCatalogue | null | undefined, pick: CameraPick): string {
  const parts = [find(cat?.focal, pick.focal)?.label, find(cat?.aperture, pick.aperture)?.label, find(cat?.looks, pick.look)?.label].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Lens";
}

/** The form fields the run sends (empty picks are left off). */
export function cameraFields(pick: CameraPick): [string, string][] {
  return (
    [
      ["camera_move", pick.move],
      ["lens_focal", pick.focal],
      ["lens_aperture", pick.aperture],
      ["lens_look", pick.look],
    ] as [string, string][]
  ).filter(([, v]) => !!v);
}
