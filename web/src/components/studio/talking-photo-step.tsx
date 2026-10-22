"use client";

/* A talking photo's card (lib/talking-photo.ts; docs/tasks/task-talking-photo.md).

   The photo that speaks, the person's word that the face is theirs or its
   owner agreed, the voice, and Render -- the click that spends -- beside
   what it costs. The voice is an .mp3/.wav upload, or a script read aloud:
   that Preview is a spend of its own, priced on its button and run on its
   own click, and what it reads is played back here before anything else is
   paid for. Both prices are the server's (the /api/talking-photo quote routes),
   asked again whenever a choice that moves them changes, and each click
   sends its number back so the run happens at the price shown or not at all.

   The look is the step card's (still-step.css + effect-step.css). */
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Mic, Upload } from "lucide-react";
import { cutUploadMedia, quoteTalk, quoteVoice, runVoice, uploadRefs, waitForJob } from "@/lib/studio-api";
import { mediaSrc } from "@/lib/composer";
import { madeStatus } from "@/lib/made-state";
import {
  isAudioFile,
  lengthProblem,
  previewCurrent,
  priceLine,
  scriptMissing,
  talkMissing,
  talkRequest,
  voiceRequest,
  voiceSeconds,
  type Paid,
  type PhotoChoice,
  type TalkMenu,
  type TalkState,
} from "@/lib/talking-photo";
import type { Turn } from "@/lib/assistant";
import "@/components/studio/still-step.css";
import "@/components/studio/effect-step.css";
import "@/components/studio/talking-photo-step.css";

type StepState = "waiting" | "running" | "done" | "failed";
const LABEL: Record<StepState, string> = {
  waiting: "Waiting for approval",
  running: "Working",
  done: "Done",
  failed: "Not made",
};
const SHOW_PHOTOS = 8;

export function TalkingPhotoStep({
  turn,
  menu,
  choices,
  busy,
  projectId,
  onPatch,
  onApprove,
  onError,
}: {
  turn: Turn;
  /** GET /api/talking-photo; null while it loads */
  menu: TalkMenu | null;
  /** what the photo could be: the box's images, the thread's stills, elements */
  choices: PhotoChoice[];
  busy: boolean;
  projectId?: number | null;
  /** a change to this card, applied to its CURRENT state (an upload or a
   *  preview lands after other changes may have been made) */
  onPatch: (fn: (s: TalkState) => TalkState) => void;
  /** the Render click: `credits` is the price this card is showing */
  onApprove: (credits: number, charged: boolean) => void;
  onError: (why: string) => void;
}) {
  const tp = turn.talk as TalkState;
  const status = turn.made ? madeStatus(turn.made) : undefined;
  const state: StepState = !turn.made ? "waiting" : status === "running" ? "running" : status === "done" ? "done" : "failed";
  const open = state === "waiting" || state === "failed";
  const exempt = !!menu?.exempt;

  const [voicePrice, setVoicePrice] = useState<Paid | null>(null);
  const [voiceProblem, setVoiceProblem] = useState("");
  const [price, setPrice] = useState<(Paid & { seconds: number }) | null>(null);
  const [problem, setProblem] = useState("");
  const [uploading, setUploading] = useState<"" | "photo" | "voice">("");
  const askedVoice = useRef(0);
  const asked = useRef(0);
  const following = useRef<number | null>(null);
  const photoInput = useRef<HTMLInputElement>(null);
  const voiceInput = useRef<HTMLInputElement>(null);

  const shown = useMemo(() => {
    const list = choices.slice(0, SHOW_PHOTOS);
    // the picked photo stays listed whatever else arrives
    return tp.photo && !list.some((c) => c.ref === tp.photo?.ref) ? [tp.photo, ...list.slice(0, SHOW_PHOTOS - 1)] : list;
  }, [choices, tp.photo]);

  /* the preview's price: only for words that can be read */
  const scriptGap = menu ? scriptMissing(tp, menu) : "loading";
  const voiceKey = JSON.stringify(voiceRequest(tp));
  useEffect(() => {
    if (!open || tp.mode !== "script" || scriptGap) return;
    const mine = ++askedVoice.current;
    const timer = setTimeout(() => {
      quoteVoice(voiceRequest(tp))
        .then((q) => {
          if (mine !== askedVoice.current) return;
          setVoicePrice({ credits: q.credits, charged: q.charged });
          setVoiceProblem("");
        })
        .catch((e) => {
          if (mine !== askedVoice.current) return;
          setVoicePrice(null);
          setVoiceProblem(e instanceof Error ? e.message : "That voice cannot be priced.");
        });
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- voiceKey stands for the words, voice and language
  }, [voiceKey, open, tp.mode, scriptGap]);

  /* the clip's price: the photo and the voice decide it, not the words or the box */
  const gap = menu ? talkMissing(tp, menu) : "loading";
  const req = talkRequest(tp, projectId);
  const priceKey = req ? JSON.stringify([req.photo, req.audio, req.project_id ?? null]) : "";
  useEffect(() => {
    if (!open || !req || gap) return;
    const mine = ++asked.current;
    const timer = setTimeout(() => {
      quoteTalk(req)
        .then((q) => {
          if (mine !== asked.current) return;
          setPrice({ credits: q.credits, charged: q.charged, seconds: q.billed_seconds });
          setProblem("");
        })
        .catch((e) => {
          if (mine !== asked.current) return;
          setPrice(null);
          setProblem(e instanceof Error ? e.message : "That cannot be priced.");
        });
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- priceKey stands for the request
  }, [priceKey, open, gap]);

  /* a preview left running (a reload mid-read) is followed to its end */
  const pv = tp.preview;
  useEffect(() => {
    if (pv?.status !== "running" || !pv.jobId || following.current === pv.jobId) return;
    following.current = pv.jobId;
    const jobId = pv.jobId;
    waitForJob(jobId)
      .then((job) => {
        const out = job as unknown as { audio?: string; seconds?: number | null; output?: string | null };
        onPatch((s) =>
          s.preview?.jobId !== jobId
            ? s
            : job.status === "done" && out.audio
              ? { ...s, preview: { ...s.preview, status: "done", audio: out.audio, seconds: out.seconds ?? null, url: out.output ?? undefined } }
              : { ...s, preview: { ...s.preview, status: "failed", error: job.error || "The voice was not made. Nothing was charged." } },
        );
      })
      .catch(() => onPatch((s) => (s.preview?.jobId !== jobId ? s : { ...s, preview: { ...s.preview, status: "failed", error: "That read was lost." } })));
  }, [pv?.status, pv?.jobId, onPatch]);

  async function preview() {
    if (!voicePrice || scriptGap) return;
    const body = voiceRequest(tp);
    try {
      const started = await runVoice({ ...body, expect_credits: voicePrice.credits });
      onPatch((s) => ({
        ...s,
        preview: { status: "running", jobId: started.job_id, ...body, paid: { credits: started.credits, charged: started.charged } },
      }));
    } catch (e) {
      onError(e instanceof Error ? e.message : "The voice did not start.");
    }
  }

  async function pickPhotoFile(file: File | undefined) {
    if (!file) return;
    setUploading("photo");
    try {
      const r = await uploadRefs([file]);
      const url = r.urls[0];
      if (!url) throw new Error("That photo could not be read");
      onPatch((s) => ({ ...s, photo: { ref: url, kind: "image", thumb: url, from: "uploaded" } }));
    } catch (e) {
      onError(e instanceof Error ? e.message : "The photo did not upload.");
    } finally {
      setUploading("");
    }
  }

  async function pickVoiceFile(file: File | undefined) {
    if (!file) return;
    if (!isAudioFile(file.name)) {
      onError("The voice must be an .mp3 or .wav file");
      return;
    }
    setUploading("voice");
    try {
      const r = await cutUploadMedia(file);
      onPatch((s) => ({ ...s, mode: "upload", upload: { audio: r.handle, seconds: r.seconds ?? null, filename: r.filename } }));
    } catch (e) {
      onError(e instanceof Error ? e.message : "The voice did not upload.");
    } finally {
      setUploading("");
    }
  }

  const secs = voiceSeconds(tp);
  const current = previewCurrent(tp);
  const previewing = current && pv?.status === "running";
  const canRender = open && !busy && !gap && !!price && tp.consent;
  const line = !open
    ? tp.paid
      ? priceLine(tp.paid, exempt)
      : ""
    : gap || problem || (price ? `${price.seconds}s of voice · ${priceLine(price, exempt)}` : "Pricing…");

  return (
    <div className="ss fx tk" data-state={state}>
      <div className="ss-head">
        <Mic strokeWidth={1.6} />
        <b>Talking photo</b>
        <span>OmniHuman v2</span>
        <em>{LABEL[state]}</em>
      </div>

      {open ? (
        <>
          <div className="tk-sec">
            <span className="tk-k">Photo</span>
            <div className="tk-photos" role="radiogroup" aria-label="The photo that speaks">
              {shown.map((c) => (
                <button
                  type="button"
                  key={c.ref}
                  role="radio"
                  aria-checked={tp.photo?.ref === c.ref}
                  title={c.from}
                  className={tp.photo?.ref === c.ref ? "on" : ""}
                  onClick={() => onPatch((s) => ({ ...s, photo: c }))}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={mediaSrc(c.thumb ?? c.ref)} alt="" />
                </button>
              ))}
              <button type="button" className="tk-add" disabled={uploading === "photo"} onClick={() => photoInput.current?.click()}>
                <Upload strokeWidth={1.6} />
                <span>{uploading === "photo" ? "…" : "Upload"}</span>
              </button>
              <input
                ref={photoInput}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                onChange={(e) => {
                  void pickPhotoFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </div>
            {!shown.length ? <small className="fx-none">Upload a photo of a person, or attach an element to the box.</small> : null}
            <label className="tk-consent">
              <input type="checkbox" checked={tp.consent} onChange={(e) => onPatch((s) => ({ ...s, consent: e.target.checked }))} />
              <span>This is my face, or the person in the photo agreed to it being animated.</span>
            </label>
          </div>

          <div className="tk-sec">
            <span className="tk-k">Voice</span>
            <div className="tk-tabs" role="tablist">
              <button type="button" role="tab" aria-selected={tp.mode === "script"} onClick={() => onPatch((s) => ({ ...s, mode: "script" }))}>
                Write it
              </button>
              <button type="button" role="tab" aria-selected={tp.mode === "upload"} onClick={() => onPatch((s) => ({ ...s, mode: "upload" }))}>
                Upload it
              </button>
            </div>
            {tp.mode === "script" ? (
              <>
                <textarea
                  className="fx-words"
                  rows={3}
                  value={tp.script}
                  maxLength={menu?.script_max ?? 5000}
                  placeholder="What the photo says. Tags like [laughs] or [whispers] set the delivery."
                  aria-label="What the photo says"
                  onChange={(e) => onPatch((s) => ({ ...s, script: e.target.value }))}
                />
                <div className="tk-row">
                  <label className="fx-opt">
                    <span>Voice</span>
                    <select value={tp.voice} aria-label="Voice" onChange={(e) => onPatch((s) => ({ ...s, voice: e.target.value }))}>
                      {(menu?.voices ?? [tp.voice]).map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="fx-opt tk-lang">
                    <span>Language</span>
                    <input
                      value={tp.language}
                      maxLength={2}
                      placeholder="auto"
                      aria-label="Language, a two-letter code"
                      onChange={(e) => onPatch((s) => ({ ...s, language: e.target.value }))}
                    />
                  </label>
                </div>
                <div className="tk-preview">
                  <button type="button" disabled={busy || !!scriptGap || !voicePrice || previewing} onClick={() => void preview()}>
                    {previewing ? "Reading…" : current && pv?.status === "done" ? "Read it again" : "Preview the voice"}
                  </button>
                  <small>
                    {previewing
                      ? "Reading it aloud…"
                      : scriptGap && tp.script.trim()
                        ? scriptGap
                        : voiceProblem || (voicePrice ? priceLine(voicePrice, exempt) : scriptGap ? "" : "Pricing…")}
                  </small>
                </div>
                {current && pv?.status === "done" && pv.url ? (
                  <div className="tk-heard">
                    <audio controls preload="metadata" src={mediaSrc(pv.url)} />
                    <small>{pv.seconds ? `${pv.seconds.toFixed(1)}s` : ""}</small>
                  </div>
                ) : null}
                {current && pv?.status === "failed" ? <small className="tk-err">{pv.error}</small> : null}
              </>
            ) : (
              <div className="tk-preview">
                <button type="button" disabled={uploading === "voice"} onClick={() => voiceInput.current?.click()}>
                  {uploading === "voice" ? "Uploading…" : tp.upload ? "Replace the file" : "Choose an .mp3 or .wav"}
                </button>
                <small>{tp.upload ? `${tp.upload.filename}${secs ? ` · ${secs.toFixed(1)}s` : ""}` : `4 to ${menu?.audio_cap ?? 30} seconds on your plan`}</small>
                <input
                  ref={voiceInput}
                  type="file"
                  accept=".mp3,.wav,audio/mpeg,audio/wav"
                  hidden
                  onChange={(e) => {
                    void pickVoiceFile(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </div>
            )}
            {menu && secs != null && lengthProblem(secs, menu) ? <small className="tk-err">{lengthProblem(secs, menu)}</small> : null}
          </div>

          <textarea
            className="fx-words"
            rows={2}
            value={tp.prompt}
            maxLength={menu?.prompt_max ?? 1000}
            placeholder="Optional: the scene, the movement, the camera…"
            aria-label="Direction"
            onChange={(e) => onPatch((s) => ({ ...s, prompt: e.target.value }))}
          />
        </>
      ) : (
        <div className="fx-on">
          {tp.photo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={mediaSrc(tp.photo.thumb ?? tp.photo.ref)} alt="" />
          ) : null}
          <small>
            {tp.mode === "upload" ? tp.upload?.filename : `${tp.voice} reading the script`}
            {secs ? ` · ${secs.toFixed(1)}s` : ""}
          </small>
        </div>
      )}

      <div className="ss-go">
        {open ? (
          <button type="button" disabled={!canRender} onClick={() => price && onApprove(price.credits, price.charged && !exempt)}>
            {state === "failed" ? "Render again" : "Render"}
          </button>
        ) : (
          <span className="ss-ok">
            {state === "done" ? <Check strokeWidth={2.2} /> : <span className="ss-live" aria-hidden />}
            {state === "done" ? "Approved" : "Working…"}
          </span>
        )}
        <small>{open && !gap && price && !tp.consent ? `${line} · tick the box above first` : line}</small>
      </div>
    </div>
  );
}
