"use client";

/* Make a voiceover for this cut (2026-10-21, src/voiceover.py). Your script,
   read by the voice you pick -- the brand kit's default when its line names
   one of the voices on offer -- at the price on the button: the click is the
   approval, and the run is held to that price. When it lands it is in the
   bin like any upload and is laid on the voice track at the playhead, the
   music ducking under it: ordinary edits, each a version you can undo.
   "Draft" writes the words free (one model call: the kit's voice,
   the cut's on-screen text and length) into the box, to edit before any
   price is shown for reading them. */
import { useEffect, useState } from "react";
import { Loader2, Mic, Sparkles } from "lucide-react";
import { useCut } from "@/lib/cut/store";
import { getVoiceoverMenu, quoteVoiceover, runVoiceover, writeVoiceoverScript, type VoiceoverMenu } from "@/lib/cut/api";
import { waitForJob, type Job } from "@/lib/studio-api";
import { overrun, voiceoverPlacement } from "@/lib/cut/voiceover";

export function VoiceoverCard() {
  const projectId = useCut((s) => s.projectId);
  const toast = useCut((s) => s.toast);
  const [menu, setMenu] = useState<VoiceoverMenu | null>(null);
  const [voice, setVoice] = useState("");
  const [script, setScript] = useState("");
  const [credits, setCredits] = useState<number | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [writing, setWriting] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const running = job !== null && !["done", "failed", "cancelled"].includes(job.status);
  const words = script.trim();

  useEffect(() => {
    if (!projectId) return;
    getVoiceoverMenu(projectId)
      .then((m) => {
        setMenu(m);
        setVoice((was) => was || m.default_voice);
      })
      .catch(() => setMenu(null));
  }, [projectId]);

  // the price follows what the button will make: these words, in this voice
  useEffect(() => {
    if (!projectId || !voice || !words) return;
    let live = true;
    const t = setTimeout(() => {
      setQuoting(true);
      quoteVoiceover(projectId, { script: words, voice })
        .then((q) => live && setCredits(q.credits))
        .catch(() => live && setCredits(null))
        .finally(() => live && setQuoting(false));
    }, 300);
    return () => {
      live = false;
      clearTimeout(t);
      setCredits(null);
    };
  }, [projectId, voice, words]);

  if (!menu) return null;

  const make = async () => {
    if (!projectId || credits === null || !words) return;
    const playhead = useCut.getState().playhead;
    try {
      const res = await runVoiceover(projectId, { script: words, voice, expect_credits: credits });
      setJob({ id: res.job_id, kind: "effect", label: "voiceover", status: "queued", progress: 0, detail: "" });
      const done = (await waitForJob(res.job_id, setJob, 1500)) as Job & { audio?: string; seconds?: number };
      if (done.status !== "done" || !done.audio) {
        toast(done.error || "The voiceover was not made", "err");
        return;
      }
      const s = useCut.getState();
      await s.loadBin();
      const doc = s.doc;
      if (!doc) return;
      const seconds = done.seconds ?? 0;
      const past = overrun(doc, seconds, playhead);
      for (const step of voiceoverPlacement(doc, done.audio, seconds, playhead)) {
        if (!(await useCut.getState().op(step.op, step.args(useCut.getState().doc ?? doc)))) break;
      }
      toast(
        past > 0
          ? `Voiceover on the track — it runs ${past.toFixed(1)}s past the picture; undo takes it off`
          : "Voiceover on the track — undo takes it off; it stays in the bin",
      );
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) toast("The price changed — check the button and try again", "err");
      else toast(err.message || "The voiceover was not started", "err");
      setJob(null);
    }
  };

  const write = async () => {
    if (!projectId) return;
    setWriting(true);
    setWarnings([]);
    try {
      const res = await writeVoiceoverScript(projectId);
      const done = (await waitForJob(res.job_id, () => {}, 1000)) as Job & { script?: string; warnings?: string[] };
      if (done.status !== "done" || !done.script) {
        toast(done.error || "The script was not written", "err");
        return;
      }
      setScript(done.script);
      setWarnings(done.warnings ?? []);
    } catch (e) {
      toast((e as Error).message || "The script was not written", "err");
    } finally {
      setWriting(false);
    }
  };

  const kitNote = menu.kit_line
    ? menu.kit_voice
      ? `${menu.kit_name}'s default voice.`
      : `${menu.kit_name} asks for: ${menu.kit_line}. Pick the voice closest to it.`
    : "";

  return (
    <div className="cx-card">
      <h4 className="cx-h">
        <Mic size={13} style={{ verticalAlign: -2 }} /> Make a voiceover
      </h4>
      <p className="cx-note" style={{ marginBottom: 8 }}>
        Your words, read aloud on {menu.label}. It lands on the voice track at the playhead, and any music ducks under
        it.
      </p>
      <label className="cx-field">
        <span className="cx-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          Script
          <button
            type="button"
            className="cx-btn ghost"
            style={{ whiteSpace: "nowrap", padding: "2px 8px", fontSize: 11 }}
            disabled={running || writing}
            title="Write it for me -- free: drafted from the kit's voice and the words on screen"
            onClick={(e) => {
              e.preventDefault();
              void write();
            }}
          >
            {writing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} Draft
          </button>
        </span>
        <textarea
          className="cx-textarea"
          rows={3}
          maxLength={menu.max_chars}
          disabled={running}
          placeholder="e.g. Your evening, back. Book a sitter in two taps."
          value={script}
          onChange={(e) => {
            setScript(e.target.value);
            setWarnings([]);
          }}
          onKeyDown={(e) => e.stopPropagation()}
        />
        {warnings.map((w) => (
          <p key={w} className="cx-note" style={{ color: "var(--warn)" }}>
            Check: {w}
          </p>
        ))}
      </label>
      <label className="cx-field">
        <span className="cx-label">Voice</span>
        <select className="cx-select" value={voice} disabled={running} onChange={(e) => setVoice(e.target.value)}>
          {menu.voices.map((v) => (
            <option key={v} value={v}>
              {v}
              {v === menu.kit_voice ? " (kit)" : ""}
            </option>
          ))}
        </select>
        {kitNote ? <p className="cx-note">{kitNote}</p> : null}
      </label>
      {job ? (
        <div className="cx-field">
          <span className="cx-label">{job.status === "failed" ? "Not made" : job.detail || "Reading…"}</span>
          <span className="cx-progress">
            <i style={{ width: `${Math.round((job.status === "done" ? 1 : job.progress || 0.05) * 100)}%` }} />
          </span>
        </div>
      ) : null}
      <button
        type="button"
        className="cx-go"
        disabled={!menu.ready || running || quoting || credits === null || !words}
        onClick={() => void make()}
      >
        {running ? <Loader2 size={13} className="animate-spin" /> : <Mic size={13} />}
        {!menu.ready
          ? " Voices are not set up on this server"
          : !words
            ? " Write the script first"
            : credits === null
              ? " Pricing…"
              : ` Make voiceover · ${credits} credit${credits === 1 ? "" : "s"}${menu.exempt ? " (not charged)" : ""}`}
      </button>
    </div>
  );
}
