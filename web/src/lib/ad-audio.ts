/* The voice and the music on a built ad (2026-10-21, step 4 of
   docs/tasks/task-url-to-ad.md). Wired, not built: the editor's own
   voiceover and music routes price and make them (src/voiceover.py,
   src/music.py), and the editor's own placements lay them on the cut
   (lib/cut/voiceover.ts, lib/cut/music.ts) -- the read on the voice track
   from the start, the bed on the music track ducking under it. Each is a
   spend on its own button, at the price the button shows; nothing here
   runs one unasked. Pure, so tests/ad-audio.test.mjs runs it as it is. */

export type AudioPart = {
  /** off: this server cannot make it, or there is nothing to read */
  status: "pricing" | "ready" | "running" | "placed" | "failed" | "off";
  credits?: number | null;
  charged?: boolean;
  /** the voice that reads it, or the music model's label */
  label?: string;
  /** why it is off, or what went wrong, in plain words */
  note?: string;
};

type Step<D> = { op: string; args: (doc: D) => Record<string, unknown> };
type Head<D> = { id: number; doc: D };

/** Lay `steps` on the cut one edit at a time, each built from the doc as
 *  the edit before left it and sent against that version (so a stale head
 *  is refused by the server, never written over). Returns the last head. */
export async function lay<D>(
  head: Head<D>,
  steps: Step<D>[],
  apply: (baseId: number, op: string, args: Record<string, unknown>) => Promise<{ head: Head<D> }>,
): Promise<Head<D>> {
  let at = head;
  for (const step of steps) {
    at = (await apply(at.id, step.op, step.args(at.doc))).head;
  }
  return at;
}

/** The button's words for one part. */
export function partButton(kind: "voice" | "music", p: AudioPart | undefined, exempt: boolean): string {
  const verb = kind === "voice" ? "Read it" : "Add music";
  if (!p || p.status === "pricing") return `${verb} · pricing…`;
  if (p.status === "running") return kind === "voice" ? "Reading…" : "Composing…";
  if (p.credits == null) return verb;
  return `${verb} · ${p.credits} credit${p.credits === 1 ? "" : "s"}${exempt || p.charged === false ? " (not charged)" : ""}`;
}

/** What a 409 from a run says: the price moved, so the button shows the new one. */
export function priceMoved(p: AudioPart, credits: number | null | undefined): AudioPart {
  return { ...p, status: "ready", credits: credits ?? p.credits, note: "The price changed. Check the button and try again." };
}
