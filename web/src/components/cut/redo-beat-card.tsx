"use client";

/* Redo the beat under the playhead (2026-10-21, src/cut/motion_ad.py): the
   brain rewrites that one beat of a motion ad with the rest of the ad in
   front of it -- free, one model call -- and the editor keeps it as ONE
   version, so Undo takes it back. A beat is the picture clip under the
   playhead and the graphics that start inside it; the card shows only when
   there are some. */
import { useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { useCut, useDrawnDoc } from "@/lib/cut/store";
import { redoBeat } from "@/lib/cut/api";
import { waitForJob, type Job } from "@/lib/studio-api";
import { clipAt, clipEnd, timecode } from "@/lib/cut/timeline";

export function RedoBeatCard() {
  const doc = useDrawnDoc();
  const playhead = useCut((s) => s.playhead);
  const projectId = useCut((s) => s.projectId);
  const toast = useCut((s) => s.toast);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  if (!doc) return null;
  const v1 = doc.tracks.find((t) => t.id === "V1");
  const clip = v1 ? clipAt(v1, playhead) : null;
  if (!clip) return null;
  const end = clipEnd(clip);
  const items = doc.tracks
    .filter((t) => t.kind === "graphic")
    .flatMap((t) => t.items ?? [])
    .filter((g) => clip.at <= g.start && g.start < end);
  if (!items.length) return null;
  const n = (v1?.clips ?? []).filter((c) => c.at <= clip.at).length;

  const redo = async () => {
    const s = useCut.getState();
    if (!projectId || !s.head) return;
    setBusy(true);
    try {
      const res = await redoBeat(projectId, { base_id: s.head.id, frame: playhead, note: note.trim() });
      const done = (await waitForJob(res.job_id, () => {}, 1000)) as Job & { warnings?: string[] };
      if (done.status !== "done") {
        toast(done.error || "The beat was not rewritten", "err");
        return;
      }
      // a swapped background is a new still in the bin: the monitor needs it there
      await Promise.all([useCut.getState().refresh(), useCut.getState().loadBin()]);
      setNote("");
      const w = done.warnings ?? [];
      toast(w.length ? `Beat ${n} rewritten · check: ${w.join("; ")}` : `Beat ${n} rewritten — undo takes it back`);
    } catch (e) {
      const err = e as Error & { status?: number };
      toast(err.status === 409 ? "The cut changed — try again" : err.message || "The beat was not rewritten", "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cx-card">
      <h4 className="cx-h">
        <RefreshCw size={13} style={{ verticalAlign: -2 }} /> Redo beat {n}
      </h4>
      <p className="cx-note" style={{ marginBottom: 8 }}>
        {timecode(clip.at, doc.fps)}–{timecode(end, doc.fps)} · {items.length} graphic{items.length === 1 ? "" : "s"}.
        Rewritten to fit the beats around it, in the same length. Free.
      </p>
      <label className="cx-field">
        <span className="cx-label">What to change (optional)</span>
        <textarea
          className="cx-textarea"
          rows={2}
          maxLength={400}
          disabled={busy}
          placeholder="e.g. lead with speed, use the second screenshot"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => e.stopPropagation()}
        />
      </label>
      <button type="button" className="cx-go" disabled={busy} onClick={() => void redo()}>
        {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} Redo this beat
      </button>
    </div>
  );
}
