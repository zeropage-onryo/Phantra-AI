/* Where a made music bed goes (2026-10-21, src/music.py). Pure, with nothing
   imported, so tests/cut-music.test.mjs runs it as it is: the edits that lay
   a bed on the cut, in order, each built from the doc as it is when that
   edit runs (an earlier edit may have added the track).

     1. a music track when the cut has none (add_track)
     2. the bed from frame 0, OVER whatever was on the music track there
        (overwrite), cut to the cut's length
     3. a one-second fade out at its end (set_fade)
     4. ducking under the voice when the cut has a voice track with sound
        on it and the music does not duck yet (duck) */

type Clip = { id: string; media: string; at: number; src_in: number; src_out: number };
type Track = { id: string; kind: string; role?: string; duck_under?: string | null; clips?: Clip[] };
type Doc = { fps: number; duration: number; tracks: Track[] };
type Step = { op: string; args: (doc: Doc) => Record<string, unknown> };

export const FADE_SECONDS = 1;

const musicTrack = (doc: Doc) => doc.tracks.find((t) => t.kind === "audio" && t.role === "music");

export function musicPlacement(doc: Doc, handle: string, seconds: number): Step[] {
  const frames = Math.max(1, Math.min(Math.round(seconds * doc.fps) || doc.duration, doc.duration || 1));
  const steps: Step[] = [];
  if (!musicTrack(doc)) steps.push({ op: "add_track", args: () => ({ kind: "audio", role: "music" }) });
  steps.push({
    op: "overwrite",
    args: (d) => ({ track_id: musicTrack(d)?.id ?? "A2", clip: { media: handle, src_in: 0, src_out: frames }, at: 0 }),
  });
  steps.push({
    op: "set_fade",
    args: (d) => {
      const clip = (musicTrack(d)?.clips ?? []).find((c) => c.media === handle && c.at === 0);
      return { clip_id: clip?.id ?? "", fade_out: Math.min(Math.round(FADE_SECONDS * d.fps), Math.floor(frames / 2)) };
    },
  });
  const voice = doc.tracks.find((t) => t.kind === "audio" && t.role === "voice" && (t.clips ?? []).length);
  if (voice && !musicTrack(doc)?.duck_under) {
    steps.push({ op: "duck", args: (d) => ({ track_id: musicTrack(d)?.id ?? "A2", under: "voice" }) });
  }
  return steps;
}
