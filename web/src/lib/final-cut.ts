/* The final cut in the chat (2026-10-20, Mike: "build Runway's Final Cut").

   A timed scene renders shot by shot, each shot its own clip. Runway Agent
   joins a multi-shot video into one file by itself; here, the moment the
   LAST shot of a scene written in the chat lands, the composer asks the
   editor's Assemble (POST /api/cut/assemble) to join the shots in order
   into ONE MP4, and plays it in the same turn. It is free: ffmpeg on our
   server, no model, no credits. The cut is version N of the scene's
   timeline, so "Open in the editor" opens exactly it.

   Pure and import-free: tests/final-cut.test.mjs runs this file as it is. */

export type FinalCut = {
  status: "running" | "done" | "failed";
  /** the assemble job, so a join left running is picked up on return */
  jobId?: number;
  /** the joined MP4 (the job's mp4_url) */
  url?: string | null;
  seconds?: number | null;
  /** the scene timeline's version the cut is */
  version?: number | null;
  /** why it was not made, in plain words */
  detail?: string;
  /** its row in the Library, `gen:<id>` -- the cut is filed there the
   *  moment it is made (2026-10-20, Mike) */
  asset?: string | null;
  /** a trim of it, made here for free (POST /api/quick-edit trim_clip),
   *  filed in the Library as its own clip; the cut itself is untouched */
  trim?: CutTrim;
};

export type CutTrim = {
  status: "running" | "done" | "failed";
  start: number;
  end: number;
  jobId?: number;
  url?: string | null;
  asset?: string | null;
  detail?: string;
};

/** A trim range a person typed, checked before anything runs: a reason,
 *  or "" when it can be made. Refused, never clamped. */
export function trimProblem(start: number, end: number, seconds: number | null | undefined): string {
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "Give the start and end in seconds.";
  if (start < 0) return "The start cannot be before 0s.";
  if (end <= start) return "The end has to come after the start.";
  if (end - start < 0.5) return "Keep at least half a second.";
  if (typeof seconds === "number" && seconds > 0 && end > seconds + 0.05)
    return `The video is ${seconds.toFixed(1)}s long.`;
  return "";
}

type PartLike = { media_url?: string | null };

/** Two or more shots, every one with its clip: something worth joining. */
export function joinable(parts: PartLike[] | null | undefined): boolean {
  const ps = parts ?? [];
  return ps.length >= 2 && ps.every((p) => !!p.media_url);
}

/** Join on its own only on the change: the read that saw the last shot
 *  land, never a scene already whole when the turn was first drawn, and
 *  never twice. */
export function shouldJoin(
  before: PartLike[] | null | undefined,
  after: PartLike[] | null | undefined,
  cut: FinalCut | null | undefined,
): boolean {
  return !cut && joinable(after) && !joinable(before);
}

/** The line under the joined video. */
export function cutLine(cut: FinalCut, shots: number): string {
  if (cut.status === "running") return `Joining ${shots} shots into one video…`;
  if (cut.status === "failed") return cut.detail || "The shots were not joined. Nothing was charged.";
  const len = typeof cut.seconds === "number" && cut.seconds > 0 ? ` · ${cut.seconds.toFixed(1)}s` : "";
  return `Final cut · ${shots} shots${len} · free${cut.asset ? " · in your Library" : ""}`;
}

/** The chat once a scene's shots are joined (2026-10-23, Mike: "the
 *  conversation doesn't clear after we render"): only the turn that carries
 *  the final cut stays, so the next idea starts on a clean chat. Everything
 *  the talk made is in the Library already; nothing is deleted there. A
 *  thread without that turn is left as it is. */
export function keepOnlyCut<T extends { made?: { id?: string } | null }>(turns: T[], madeId: string): T[] {
  const kept = turns.filter((t) => t.made?.id === madeId);
  return kept.length ? kept : turns;
}

type DoneLike = { made?: { output?: string; status?: string; parts?: PartLike[] | null; sceneClip?: string | null; finalCut?: FinalCut | null } | null };

/** A conversation whose work is through: its LAST turn is a written scene
 *  whose render is finished -- the shots joined into the final cut, or a
 *  one-shot scene's clip landed. Such a thread is not kept (2026-10-23,
 *  Mike: "the conversation doesn't go away after render and stays saved"):
 *  coming back to it starts a new session. Anything said after the render
 *  (a new idea) means it is still going. */
export function renderIsThrough(turns: DoneLike[] | null | undefined): boolean {
  const last = turns?.length ? turns[turns.length - 1] : null;
  const m = last?.made;
  if (!m || m.output !== "video" || m.status !== "done") return false;
  if (m.finalCut?.status === "done") return true;
  const parts = m.parts || [];
  return parts.length === 1 ? !!parts[0].media_url : !parts.length && !!m.sceneClip;
}
