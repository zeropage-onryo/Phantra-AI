/* Where a made voiceover goes (2026-10-21, src/voiceover.py). Pure, with
   nothing imported, so tests/cut-voiceover.test.mjs runs it as it is: the
   edits that lay a read on the cut, in order, each built from the doc as it
   is when that edit runs (an earlier edit may have added the track).

     1. a voice track when the cut has none (add_track)
     2. the read at the playhead, OVER whatever was on the voice track there
        (overwrite), whole: a line is never cut off mid-word, so a read that
        runs past the picture makes the cut that much longer (undo takes it
        back)
     3. the music ducking under the voice when the cut has music on it and
        it does not duck yet (duck) */

type Clip = { id: string; media: string; at: number; src_in: number; src_out: number };
type Track = { id: string; kind: string; role?: string; duck_under?: string | null; clips?: Clip[] };
type Doc = { fps: number; duration: number; tracks: Track[] };
type Step = { op: string; args: (doc: Doc) => Record<string, unknown> };

const roleTrack = (doc: Doc, role: string) => doc.tracks.find((t) => t.kind === "audio" && t.role === role);

/* seconds -> whole frames, FLOORED as the server measures a file
   (src/cut/doc.to_frames): rounding up claimed a frame past the end of a
   3.03s read, and the validator refused the whole placement (2026-10-21) */
export const toFrames = (seconds: number, fps: number) => Math.max(0, Math.floor(seconds * fps + 1e-6));

export function voiceoverPlacement(doc: Doc, handle: string, seconds: number, playhead: number): Step[] {
  const frames = Math.max(1, toFrames(seconds, doc.fps));
  const at = Math.max(0, Math.round(playhead) || 0);
  const steps: Step[] = [];
  if (!roleTrack(doc, "voice")) steps.push({ op: "add_track", args: () => ({ kind: "audio", role: "voice" }) });
  steps.push({
    op: "overwrite",
    args: (d) => ({ track_id: roleTrack(d, "voice")?.id ?? "A1", clip: { media: handle, src_in: 0, src_out: frames }, at }),
  });
  const music = roleTrack(doc, "music");
  if (music && (music.clips ?? []).length && !music.duck_under) {
    steps.push({ op: "duck", args: () => ({ track_id: music.id, under: "voice" }) });
  }
  return steps;
}

/* how far past the picture a read at `at` runs, in seconds (0 when it fits) */
export function overrun(doc: Doc, seconds: number, playhead: number): number {
  const end = Math.max(0, Math.round(playhead) || 0) + toFrames(seconds, doc.fps);
  return Math.max(0, end - doc.duration) / doc.fps;
}
