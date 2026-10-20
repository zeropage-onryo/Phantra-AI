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
};

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
  return `Final cut · ${shots} shots${len} · free`;
}
