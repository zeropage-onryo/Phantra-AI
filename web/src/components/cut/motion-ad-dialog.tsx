"use client";

/* Make a motion ad (2026-10-20, src/cut/motion_ad.py). Say what the ad is
   for, pick the project (its brand kit is the look), a length and a shape,
   add a few screenshots of the product if there are any -- and the brain
   writes the beats while code places them: flat brand colours, a headline
   per beat, a big faint word behind it, the screenshots on cards, a label
   now and then. One model call, free on a plan; nothing renders and nothing
   is charged. It opens as a new cut to keep, change or throw away. */
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Dialog } from "@base-ui/react/dialog";
import { ImagePlus, Loader2, Sparkles, X } from "lucide-react";
import { listProjects, waitForJob, type Job, type Project } from "@/lib/studio-api";
import { makeMotionAd, uploadMedia } from "@/lib/cut/api";
import type { Aspect } from "@/lib/cut/timeline";
import { useShell } from "@/components/studio/shell";

const LENGTHS = [10, 15, 20, 30, 45, 60];
const SHAPES: Aspect[] = ["16:9", "9:16", "1:1"];
const CARDS_MAX = 8;

type Card = { handle: string; name: string; preview: string };

export function MotionAdDialog({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { toast } = useShell();
  const [brief, setBrief] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [seconds, setSeconds] = useState(20);
  const [aspect, setAspect] = useState<Aspect>("16:9");
  const [cards, setCards] = useState<Card[]>([]);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const running = job !== null && !["done", "failed", "cancelled"].includes(job.status);

  useEffect(() => {
    listProjects()
      .then((r) => setProjects(r.items))
      .catch(() => setProjects([]));
  }, []);

  const addFiles = async (files: File[]) => {
    setUploading(true);
    try {
      for (const f of files.slice(0, CARDS_MAX - cards.length)) {
        const up = await uploadMedia(f);
        if (up.kind !== "image") {
          toast(`${f.name} is not a still image`, "err");
          continue;
        }
        setCards((was) => [...was, { handle: up.handle, name: f.name, preview: URL.createObjectURL(f) }]);
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "The screenshot was not added", "err");
    } finally {
      setUploading(false);
    }
  };

  const start = async () => {
    if (!brief.trim()) return;
    try {
      const res = await makeMotionAd({
        brief: brief.trim(),
        project_id: projectId,
        seconds,
        aspect,
        cards: cards.map((c) => c.handle),
      });
      setJob({ id: res.job_id, kind: "cut", label: "motion ad", status: "queued", progress: 0, detail: "" });
      const done = await waitForJob(res.job_id, setJob, 1200);
      const cutId = (done as Job & { cut_id?: string }).cut_id;
      if (done.status === "done" && cutId) {
        const warnings = (done as Job & { warnings?: string[] }).warnings ?? [];
        toast(warnings.length ? `Made · ${warnings.length} note${warnings.length === 1 ? "" : "s"} in the version list` : "Made — every line is yours to change");
        router.push(`/studio/cut/${encodeURIComponent(cutId)}`);
      } else {
        toast(done.error || done.detail || "The ad was not made. Nothing was charged.", "err");
      }
    } catch (e) {
      setJob(null);
      toast(e instanceof Error ? e.message : "The ad was not started", "err");
    }
  };

  const picked = projects.find((p) => p.id === projectId);
  return (
    <Dialog.Root open onOpenChange={(o) => !o && !running && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="cx-backdrop" />
        <Dialog.Popup className="cx-dialog cx-portal" style={{ maxWidth: 560 }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
            <Dialog.Title render={<h3 />}>Make a motion ad</Dialog.Title>
            <span className="spacer" />
            <Dialog.Close className="cx-btn" disabled={running} aria-label="Close">
              <X />
            </Dialog.Close>
          </div>
          <p className="cx-note" style={{ marginBottom: 14 }}>
            Big type over your brand colours, one idea per beat — the kind of launch video made of words, product
            screens and a logo rather than footage. The AI writes the lines; the editor places and animates them. It
            renders nothing and costs no credits.
          </p>

          <label className="cx-field">
            <span className="cx-label">What is it for?</span>
            <textarea
              className="cx-textarea"
              rows={4}
              maxLength={4000}
              disabled={running}
              placeholder="A 20-second launch ad for Gygler: hotels book trusted shift workers in seconds. End on 'Get a Gyg, stay for good.'"
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              onKeyDown={(e) => e.stopPropagation()}
            />
          </label>

          <label className="cx-field">
            <span className="cx-label">Project — its brand kit is the look</span>
            <select
              className="cx-select"
              value={projectId ?? ""}
              disabled={running}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">No project — plain dark colours, white type</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            {picked ? null : <p className="cx-note">Pick a project with a brand kit for its colours, fonts and end card.</p>}
          </label>

          <div className="cx-field">
            <span className="cx-label">Length</span>
            <span className="cx-seg" style={{ flexWrap: "wrap" }}>
              {LENGTHS.map((s) => (
                <button key={s} type="button" aria-pressed={seconds === s} disabled={running} onClick={() => setSeconds(s)}>
                  {s}s
                </button>
              ))}
            </span>
          </div>
          <div className="cx-field">
            <span className="cx-label">Shape</span>
            <span className="cx-seg">
              {SHAPES.map((a) => (
                <button key={a} type="button" aria-pressed={aspect === a} disabled={running} onClick={() => setAspect(a)}>
                  {a}
                </button>
              ))}
            </span>
          </div>

          <div className="cx-field">
            <span className="cx-label">Product screenshots for cards (optional, up to {CARDS_MAX})</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {cards.map((c) => (
                <span key={c.handle} style={{ position: "relative" }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={c.preview} alt={c.name} style={{ width: 72, height: 54, objectFit: "cover", borderRadius: 6 }} />
                  <button
                    type="button"
                    className="cx-btn"
                    aria-label={`Remove ${c.name}`}
                    style={{ position: "absolute", top: 2, right: 2, height: 18, padding: "0 4px" }}
                    disabled={running}
                    onClick={() => setCards((was) => was.filter((x) => x.handle !== c.handle))}
                  >
                    <X size={10} />
                  </button>
                </span>
              ))}
              {cards.length < CARDS_MAX ? (
                <button
                  type="button"
                  className="cx-btn ghost"
                  style={{ width: 72, height: 54, justifyContent: "center" }}
                  disabled={running || uploading}
                  onClick={() => input.current?.click()}
                  aria-label="Add screenshots"
                >
                  {uploading ? <Loader2 size={14} className="animate-spin" /> : <ImagePlus size={16} />}
                </button>
              ) : null}
            </div>
            <input
              ref={input}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              hidden
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                e.target.value = "";
                if (files.length) void addFiles(files);
              }}
            />
          </div>

          {job ? (
            <div className="cx-field">
              <span className="cx-label">{job.status === "failed" ? "Not made" : job.detail || "Writing the script…"}</span>
              <span className="cx-progress">
                <i style={{ width: `${Math.round((job.status === "done" ? 1 : job.progress || 0.05) * 100)}%` }} />
              </span>
            </div>
          ) : null}

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="cx-go" disabled={running || uploading || !brief.trim()} onClick={() => void start()}>
              {running ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Write and place it · free
            </button>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
