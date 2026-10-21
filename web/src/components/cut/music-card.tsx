"use client";

/* Make music for this cut (2026-10-21, src/music.py). An instrumental bed as
   long as the cut, in the brand kit's direction plus your own words, on the
   model you pick, at the price on the button -- the click is the approval,
   and the run is held to that price. When it lands it is in the bin like
   any upload and is laid on the music track from the start, fading out at
   the end, ducking under the voice when there is one: ordinary edits, each
   a version you can undo. */
import { useEffect, useState } from "react";
import { Loader2, Music } from "lucide-react";
import { useCut } from "@/lib/cut/store";
import { getMusicMenu, quoteMusic, runMusic, type MusicMenu } from "@/lib/cut/api";
import { waitForJob, type Job } from "@/lib/studio-api";
import { musicPlacement } from "@/lib/cut/music";

export function MusicCard() {
  const projectId = useCut((s) => s.projectId);
  const duration = useCut((s) => s.doc?.duration ?? 0);
  const toast = useCut((s) => s.toast);
  const [menu, setMenu] = useState<MusicMenu | null>(null);
  const [model, setModel] = useState<string>("");
  const [direction, setDirection] = useState("");
  const [credits, setCredits] = useState<number | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const running = job !== null && !["done", "failed", "cancelled"].includes(job.status);

  useEffect(() => {
    if (!projectId) return;
    getMusicMenu(projectId)
      .then((m) => {
        setMenu(m);
        setModel((was) => was || m.default_model);
      })
      .catch(() => setMenu(null));
  }, [projectId, duration]);

  // the price follows what the button will make: the model, the words, the cut's length
  useEffect(() => {
    if (!projectId || !model) return;
    let live = true;
    const t = setTimeout(() => {
      setQuoting(true);
      quoteMusic(projectId, { model, direction })
        .then((q) => live && setCredits(q.credits))
        .catch(() => live && setCredits(null))
        .finally(() => live && setQuoting(false));
    }, 300);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [projectId, model, direction, duration]);

  if (!menu) return null;
  const picked = menu.models.find((m) => m.id === model);

  const make = async () => {
    if (!projectId || credits === null) return;
    try {
      const res = await runMusic(projectId, { model, direction, expect_credits: credits });
      setJob({ id: res.job_id, kind: "effect", label: "music", status: "queued", progress: 0, detail: "" });
      const done = (await waitForJob(res.job_id, setJob, 1500)) as Job & { audio?: string; seconds?: number };
      if (done.status !== "done" || !done.audio) {
        toast(done.error || "The music was not made", "err");
        return;
      }
      const s = useCut.getState();
      await s.loadBin();
      const doc = s.doc;
      if (!doc) return;
      const plan = musicPlacement(doc, done.audio, done.seconds ?? 0);
      for (const step of plan) {
        if (!(await useCut.getState().op(step.op, step.args(useCut.getState().doc ?? doc)))) break;
      }
      toast("Music on the track — undo takes it off; it stays in the bin");
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) toast("The price changed — check the button and try again", "err");
      else toast(err.message || "The music was not started", "err");
      setJob(null);
    }
  };

  return (
    <div className="cx-card">
      <h4 className="cx-h">
        <Music size={13} style={{ verticalAlign: -2 }} /> Make music
      </h4>
      <p className="cx-note" style={{ marginBottom: 8 }}>
        An instrumental bed as long as this cut
        {menu.kit_direction ? `, in ${menu.kit_name}'s direction: ${menu.kit_direction}` : ""}. It lands on the music
        track, fading out at the end.
      </p>
      <div className="cx-field">
        <span className="cx-label">Model</span>
        <span className="cx-seg" style={{ flexWrap: "wrap" }}>
          {menu.models.map((m) => (
            <button
              key={m.id}
              type="button"
              aria-pressed={model === m.id}
              disabled={running || m.credits === null}
              title={m.refused ?? m.note}
              onClick={() => setModel(m.id)}
            >
              {m.label}
            </button>
          ))}
        </span>
        {picked ? <p className="cx-note">{picked.refused ?? picked.note}</p> : null}
      </div>
      <label className="cx-field">
        <span className="cx-label">{menu.kit_direction ? "Anything to add" : "What it should sound like"}</span>
        <textarea
          className="cx-textarea"
          rows={2}
          maxLength={600}
          disabled={running}
          placeholder="e.g. light claps, a little more energy in the second half"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          onKeyDown={(e) => e.stopPropagation()}
        />
      </label>
      {job ? (
        <div className="cx-field">
          <span className="cx-label">{job.status === "failed" ? "Not made" : job.detail || "Composing…"}</span>
          <span className="cx-progress">
            <i style={{ width: `${Math.round((job.status === "done" ? 1 : job.progress || 0.05) * 100)}%` }} />
          </span>
        </div>
      ) : null}
      <button
        type="button"
        className="cx-go"
        disabled={!menu.ready || running || quoting || credits === null || duration <= 0}
        onClick={() => void make()}
      >
        {running ? <Loader2 size={13} className="animate-spin" /> : <Music size={13} />}
        {!menu.ready
          ? " Music is not set up on this server"
          : credits === null
            ? " Pricing…"
            : ` Make music · ${credits} credit${credits === 1 ? "" : "s"}${menu.exempt ? " (not charged)" : ""}`}
      </button>
    </div>
  );
}
