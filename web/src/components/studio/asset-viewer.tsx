"use client";

/* The Assets viewer (2026-10-19, Mike's call: "the image doesn't open up
   fully or do it justice"). It REPLACES the 360px detail rail, which drew
   a render at most 316px wide -- a 16:9 still came out 316x176. Now a
   render opens full-screen: the media fitted on a stage (never cropped)
   over a blurred, darkened copy of itself, and a panel on the right with
   the prompt (Copy), its details and ONE main action -- "Use in studio"
   for a still, "Edit" for a clip. Approved mockup: the Design canvas
   "Assets Viewer Mockup". On a phone the panel is a sheet that peeks
   (prompt + the main action) and pulls up for the details.

   Everything stateful about the RENDER stays in the page (open, star,
   folder, remove + undo, stepping, the keyboard); this file draws it and
   keeps only view state of its own: zoom, the delete confirm, the folder
   draft, the measured size, the sheet. */
/* eslint-disable @next/next/no-img-element */
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  Film,
  FolderInput,
  Image as ImageIcon,
  Link2Off,
  Maximize,
  Scissors,
  Share2,
  Star,
  Trash2,
  UserRound,
  Wand2,
  X,
} from "lucide-react";
import { OpenInEditor } from "@/components/cut/open-in-editor";
import { API_URL } from "@/lib/api";
import {
  getShare,
  renderDownloadHref,
  sceneHref,
  shareRender,
  unshareRender,
  workspaceHref,
  type MediaItem,
} from "@/lib/studio-api";
import "./asset-viewer.css";

/* SHARE (2026-10-20, src/shares.py): a public page for this one render --
   the video, Vesper and the workspace's name, nothing else. Nothing is
   public until this is pressed; the link is copied, and Unshare takes the
   page down. Its own small state: whether it is shared, and "Copied". */
function ShareControls({ id }: { id: number }) {
  const [path, setPath] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    // a new item is a new component (keyed by its id), so nothing to reset here
    let live = true;
    getShare(id)
      .then((s) => live && setPath(s.path))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [id]);
  const say = (text: string) => {
    setNote(text);
    window.setTimeout(() => setNote((now) => (now === text ? "" : now)), 2400);
  };
  async function share() {
    if (busy) return;
    setBusy(true);
    try {
      const s = await shareRender(id);
      setPath(s.path);
      const link = s.path ? `${window.location.origin}${s.path}` : "";
      try {
        await navigator.clipboard.writeText(link);
        say("Link copied · anyone with it can watch");
      } catch {
        say(link);
      }
    } catch {
      say("Could not share it. Try again.");
    } finally {
      setBusy(false);
    }
  }
  async function unshare() {
    if (busy) return;
    setBusy(true);
    try {
      await unshareRender(id);
      setPath(null);
      say("Unshared · the page is down");
    } catch {
      say("Could not unshare it. Try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button
        type="button"
        className={`av-ib${path ? " on" : ""}`}
        onClick={share}
        aria-label={path ? "Copy the share link" : "Share a public link"}
        title={path ? "Shared · copy the link" : "Share a public link"}
        disabled={busy}
      >
        <Share2 strokeWidth={1.8} />
      </button>
      {path ? (
        <button type="button" className="av-ib" onClick={unshare} aria-label="Unshare" title="Unshare · take the page down" disabled={busy}>
          <Link2Off strokeWidth={1.8} />
        </button>
      ) : null}
      {note ? (
        <span className="av-note" role="status">
          {note}
        </span>
      ) : null}
    </>
  );
}

const DATE_FMT = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" });
const TIME_FMT = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });

/** "Sep 30, 2026 · 2:54 PM" from the record's created_at, or the day alone
 *  from the wall's date when an older row carries no timestamp */
export function whenOf(m: MediaItem): string {
  if (m.created_at) {
    // a naive timestamp is UTC, as the server reads it
    const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(m.created_at) ? m.created_at : `${m.created_at}Z`;
    const d = new Date(iso);
    if (!Number.isNaN(d.getTime())) return `${DATE_FMT.format(d)} · ${TIME_FMT.format(d)}`;
  }
  const [y, mo, d] = m.date.split("-").map(Number);
  return DATE_FMT.format(new Date(y, mo - 1, d));
}

/** What made a render, as a person would say it: the model's public name
 *  ("FLUX.2 Pro"), else its raw id, never the platform that hosted it --
 *  "fal" is not a name anybody picked (2026-10-20, Mike's call). A host
 *  name survives only when nothing better is on the row. */
const HOSTS = new Set(["fal", "fal.ai"]);
export function modelName(m: MediaItem): string {
  if (m.model_label) return m.model_label;
  if (m.model) return m.model;
  if (m.provider && !HOSTS.has(m.provider.toLowerCase())) return m.provider;
  return m.kind === "video" ? "Clip" : "Still";
}

/** the named shape nearest to w×h ("9:16"), else the reduced ratio */
const NAMED: [number, number][] = [
  [1, 1], [4, 5], [5, 4], [3, 4], [4, 3], [2, 3], [3, 2], [9, 16], [16, 9], [21, 9], [9, 21],
];
function shapeOf(w: number, h: number): string {
  const r = w / h;
  for (const [a, b] of NAMED) if (Math.abs(r / (a / b) - 1) < 0.025) return `${a}:${b}`;
  return r >= 1 ? `${r.toFixed(2)}:1` : `1:${(1 / r).toFixed(2)}`;
}

type Props = {
  item: MediaItem;
  /** 1-based place in the wall as filtered now, and its length */
  index: number;
  total: number;
  hasPrev: boolean;
  hasNext: boolean;
  onStep: (d: -1 | 1) => void;
  onClose: () => void;
  phone: boolean;
  folders: string[];
  onStar: () => void;
  onFolder: (folder: string) => void;
  onRemove: () => void;
  onMakeElement: () => void;
  onCopied: (ok: boolean) => void;
};

export function AssetViewer({
  item,
  index,
  total,
  hasPrev,
  hasNext,
  onStep,
  onClose,
  phone,
  folders,
  onStar,
  onFolder,
  onRemove,
  onMakeElement,
  onCopied,
}: Props) {
  const master = `${API_URL}${item.url}`;
  const poster = item.poster ? `${API_URL}${item.poster}` : undefined;
  const isClip = item.kind === "video";
  // what the ambient backdrop blurs: the still itself, a clip's poster
  const ambient = isClip ? poster : master;

  const [zoom, setZoom] = useState<"fit" | "full">("fit");
  const [confirming, setConfirming] = useState(false);
  const [folderDraft, setFolderDraft] = useState(item.folder ?? "");
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [copied, setCopied] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  // a new render resets everything that described the last one
  const [shownUrl, setShownUrl] = useState(item.url);
  if (shownUrl !== item.url) {
    setShownUrl(item.url);
    setZoom("fit");
    setConfirming(false);
    setFolderDraft(item.folder ?? "");
    setSize(null);
    setCopied(false);
    setPromptOpen(false);
  }
  // the folder can change under the open item (a move from this form)
  const [shownFolder, setShownFolder] = useState(item.folder);
  if (shownFolder !== item.folder) {
    setShownFolder(item.folder);
    setFolderDraft(item.folder ?? "");
  }

  /* ── zoom: Fit shows the whole render; 100% shows its real pixels and
     scrolls, centred where it was clicked, dragged to pan ── */
  const frame = useRef<HTMLDivElement>(null);
  const aim = useRef<{ x: number; y: number } | null>(null);
  const toggleZoom = (e?: React.MouseEvent) => {
    if (isClip || phone) return;
    if (zoom === "fit" && e) {
      const r = (e.target as HTMLElement).getBoundingClientRect();
      aim.current = { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
    } else aim.current = { x: 0.5, y: 0.5 };
    setZoom((z) => (z === "fit" ? "full" : "fit"));
  };
  useEffect(() => {
    const el = frame.current;
    if (zoom !== "full" || !el || !size) return;
    const a = aim.current ?? { x: 0.5, y: 0.5 };
    el.scrollLeft = a.x * size.w - el.clientWidth / 2;
    el.scrollTop = a.y * size.h - el.clientHeight / 2;
  }, [zoom, size]);
  const pan = useRef<{ id: number; x: number; y: number; l: number; t: number; moved: boolean } | null>(null);

  /* ── a sideways swipe on the stage turns the page (touch only) ── */
  const swipe = useRef<{ id: number; x: number; y: number } | null>(null);
  const onStageDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse") return;
    // a clip's own controls sit along its bottom: a drag there scrubs
    const r = e.currentTarget.getBoundingClientRect();
    if (isClip && e.clientY > r.bottom - 64) return;
    swipe.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
  };
  const onStageUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const s = swipe.current;
    swipe.current = null;
    if (!s || s.id !== e.pointerId) return;
    const dx = e.clientX - s.x;
    const dy = e.clientY - s.y;
    if (Math.abs(dx) >= 50 && Math.abs(dx) > Math.abs(dy) * 1.5) onStep(dx < 0 ? 1 : -1);
  };

  /* ── the phone sheet: a tap on the handle, or a drag on it, opens and
     closes it; the stage above stays the picture ── */
  const drag = useRef<{ id: number; y: number } | null>(null);
  const onHandleDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    drag.current = { id: e.pointerId, y: e.clientY };
  };
  const onHandleUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    drag.current = null;
    if (!d || d.id !== e.pointerId) return;
    const dy = e.clientY - d.y;
    if (dy < -24) setSheetOpen(true);
    else if (dy > 24) setSheetOpen(false);
    else setSheetOpen((o) => !o);
  };

  const copyPrompt = () => {
    if (!item.prompt) return;
    navigator.clipboard
      .writeText(item.prompt)
      .then(() => {
        setCopied(true);
        onCopied(true);
        setTimeout(() => setCopied(false), 1600);
      })
      .catch(() => onCopied(false));
  };

  const downloadHref = item.generated_id ? renderDownloadHref(item.generated_id) : master.split("?")[0];
  const downloadProps = item.generated_id ? {} : { target: "_blank", rel: "noreferrer" };
  const when = whenOf(item);
  const title = modelName(item);

  return (
    <motion.div
      className={`adetail av${phone ? " phone" : ""}${sheetOpen ? " sheet-open" : ""}`}
      role="dialog"
      aria-modal="true"
      aria-label={`${title} · ${isClip ? "clip" : "still"}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      {/* ── STAGE ── */}
      <section className="av-stage" aria-label="Media" onPointerDown={onStageDown} onPointerUp={onStageUp} onPointerCancel={() => (swipe.current = null)}>
        {ambient ? <img key={`amb-${ambient}`} className="av-ambient" src={ambient} alt="" aria-hidden /> : null}

        <div className="av-top">
          {phone ? (
            <>
              <button type="button" className="av-glass" onClick={onClose} aria-label="Close viewer">
                <X strokeWidth={2} />
              </button>
              <span className="av-count">
                {index} / {total}
              </span>
              <a className="av-glass" href={downloadHref} {...downloadProps} aria-label="Download" title="Download">
                <Download strokeWidth={1.8} />
              </a>
            </>
          ) : (
            <>
              <span className="av-lab av-crumb">
                Assets <i>/</i> {when.split(" · ")[0]}
              </span>
              <span className="spacer" />
              {!isClip ? (
                <div className="av-seg" role="group" aria-label="Zoom">
                  <button type="button" aria-pressed={zoom === "fit"} onClick={() => zoom !== "fit" && toggleZoom()}>
                    <Maximize strokeWidth={2} /> Fit
                  </button>
                  <button type="button" aria-pressed={zoom === "full"} onClick={() => zoom !== "full" && toggleZoom()}>
                    100%
                  </button>
                </div>
              ) : (
                <span className="av-count">
                  {index} / {total}
                </span>
              )}
            </>
          )}
        </div>

        <div
          ref={frame}
          className={`av-frame${zoom === "full" ? " full" : ""}`}
          onPointerDown={(e) => {
            if (zoom !== "full" || e.pointerType !== "mouse" || e.button !== 0) return;
            const el = e.currentTarget;
            el.setPointerCapture(e.pointerId);
            pan.current = { id: e.pointerId, x: e.clientX, y: e.clientY, l: el.scrollLeft, t: el.scrollTop, moved: false };
          }}
          onPointerMove={(e) => {
            const p = pan.current;
            if (!p || p.id !== e.pointerId) return;
            const dx = e.clientX - p.x;
            const dy = e.clientY - p.y;
            if (Math.abs(dx) + Math.abs(dy) > 3) p.moved = true;
            e.currentTarget.scrollLeft = p.l - dx;
            e.currentTarget.scrollTop = p.t - dy;
          }}
          onPointerUp={(e) => {
            const p = pan.current;
            pan.current = null;
            if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
            // a press that did not drag is a click: back to Fit
            if (p && !p.moved) toggleZoom();
          }}
        >
          {isClip ? (
            <video
              key={master}
              src={master}
              poster={poster}
              controls
              muted
              playsInline
              preload="metadata"
              onLoadedMetadata={(e) => setSize({ w: e.currentTarget.videoWidth, h: e.currentTarget.videoHeight })}
            />
          ) : (
            <img
              key={master}
              src={master}
              alt={item.prompt ? item.prompt.slice(0, 140) : title}
              onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
              onClick={zoom === "fit" ? toggleZoom : undefined}
              draggable={false}
              title={phone ? undefined : zoom === "fit" ? "Click for 100%" : undefined}
            />
          )}
        </div>

        <button type="button" className="av-glass av-nav prev" onClick={() => onStep(-1)} disabled={!hasPrev} aria-label="Previous render">
          <ChevronLeft strokeWidth={1.8} />
        </button>
        <button type="button" className="av-glass av-nav next" onClick={() => onStep(1)} disabled={!hasNext} aria-label="Next render">
          <ChevronRight strokeWidth={1.8} />
        </button>

        {!phone ? (
          <div className="av-bottom">
            <span className="av-lab">← → step · Esc close</span>
            {!isClip ? (
              <span className="av-count">
                {index} / {total}
              </span>
            ) : null}
            <span className="av-lab">{size ? `${shapeOf(size.w, size.h)} · ${zoom === "full" ? "actual pixels" : "fitted, never cropped"}` : ""}</span>
          </div>
        ) : null}
      </section>

      {/* ── PANEL (a sheet on a phone) ── */}
      <aside className="av-panel" aria-label="Render details">
        {phone ? (
          <button
            type="button"
            className="av-handle"
            aria-label={sheetOpen ? "Collapse details" : "Expand details"}
            aria-expanded={sheetOpen}
            onPointerDown={onHandleDown}
            onPointerUp={onHandleUp}
            onPointerCancel={() => (drag.current = null)}
          >
            <span aria-hidden />
          </button>
        ) : null}

        <header className="av-head">
          <div className="av-headtext">
            <div className="av-lab">
              {isClip ? <Film strokeWidth={1.7} /> : <ImageIcon strokeWidth={1.7} />} {isClip ? "Clip" : "Still"}
            </div>
            <h2>{title}</h2>
            <div className="av-when">{when}</div>
          </div>
          {phone ? (
            item.prompt ? (
              <button type="button" className="av-ghost" onClick={copyPrompt} aria-label="Copy prompt">
                {copied ? <Check strokeWidth={2} /> : <Copy strokeWidth={2} />} {copied ? "Copied" : "Copy"}
              </button>
            ) : null
          ) : (
            <button type="button" className="av-ib" onClick={onClose} aria-label="Close viewer" title="Close (Esc)">
              <X strokeWidth={2} />
            </button>
          )}
        </header>

        <div className="av-body">
          {item.prompt ? (
            <div className="av-card av-prompt">
              {!phone ? (
                <div className="av-cardhead">
                  <span className="av-lab">Prompt</span>
                  <button type="button" className="av-ghost" onClick={copyPrompt}>
                    {copied ? <Check strokeWidth={2} /> : <Copy strokeWidth={2} />} {copied ? "Copied" : "Copy"}
                  </button>
                </div>
              ) : null}
              <p className={promptOpen ? "open" : ""}>{item.prompt}</p>
              {item.prompt.length > 260 ? (
                <button type="button" className="av-more" onClick={() => setPromptOpen((o) => !o)}>
                  {promptOpen ? "Show less" : "Show full prompt"}
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="av-card av-details">
            <span className="av-lab">Details</span>
            <dl>
              <dt>Model</dt>
              <dd>
                {title}
                {item.model && item.model !== title ? <span className="av-raw">{item.model}</span> : null}
              </dd>
              <dt>Size</dt>
              <dd className="mono">{size ? `${size.w} × ${size.h}` : "…"}</dd>
              <dt>Created</dt>
              <dd>{when}</dd>
              <dt>Project</dt>
              <dd>
                {item.project_id ? (
                  <Link href={workspaceHref(item.project_id)} className="av-lnk">
                    {item.project_title || `#${item.project_id}`}
                  </Link>
                ) : (
                  <span className="av-none">No project</span>
                )}
              </dd>
              <dt>Concept</dt>
              <dd>
                {item.concept_id ? (
                  <Link href={sceneHref(item.concept_id, item.shot_n ?? 1)} className="av-lnk" title="Open its canvas">
                    #{item.concept_id}
                    {item.shot_n ? <span className="av-none"> · shot {item.shot_n}</span> : null}
                  </Link>
                ) : (
                  <span className="av-none">Not from a concept</span>
                )}
              </dd>
              {item.draft ? (
                <>
                  <dt>Draft</dt>
                  <dd>
                    <span>
                      Rendered at {item.draft.frame}, the cheap tier.{" "}
                      <Link href="/studio/renders" className="av-lnk">
                        Finish it on Renders
                      </Link>{" "}
                      to upscale it onto its shot.
                    </span>
                  </dd>
                </>
              ) : null}
              {item.generated_id ? (
                <>
                  <dt>
                    <label htmlFor="av-folder">Folder</label>
                  </dt>
                  <dd>
                    <form
                      className="av-folder"
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (folderDraft.trim() !== (item.folder ?? "")) onFolder(folderDraft.trim());
                      }}
                    >
                      <input
                        id="av-folder"
                        list="av-folders"
                        value={folderDraft}
                        onChange={(e) => setFolderDraft(e.target.value)}
                        placeholder="None — type to file it"
                      />
                      <datalist id="av-folders">
                        {folders.map((f) => (
                          <option key={f} value={f} />
                        ))}
                      </datalist>
                      <button type="submit" className="av-ghost" disabled={folderDraft.trim() === (item.folder ?? "")} title="Move to folder">
                        <FolderInput strokeWidth={1.8} /> Move
                      </button>
                    </form>
                  </dd>
                </>
              ) : null}
            </dl>
          </div>
        </div>

        <footer className="av-foot">
          {isClip ? (
            item.generated_id ? (
              <OpenInEditor handles={[`gen:${item.generated_id}`]} className="av-primary" title="Start a cut with this clip">
                <Scissors strokeWidth={2} /> Edit
              </OpenInEditor>
            ) : null
          ) : (
            <Link href={`/studio?attach=${encodeURIComponent(item.asset_id)}`} className="av-primary">
              Use in studio <ArrowRight strokeWidth={2.2} />
            </Link>
          )}
          <div className={`av-second${isClip ? " one" : ""}`}>
            {!isClip ? (
              <button type="button" className="av-sec" onClick={onMakeElement} title="Save this still as a character, prop or place">
                <UserRound strokeWidth={1.8} /> Make element
              </button>
            ) : null}
            {item.generated_id ? (
              // change it where it is made: the composer's effects gallery
              // opens ON this render (browsing is free, a pick shows its price)
              <Link href={`/studio?on=gen:${item.generated_id}`} className="av-sec" title="Change it with an effect">
                <Wand2 strokeWidth={1.8} /> Effects
              </Link>
            ) : null}
          </div>
          {confirming ? (
            <div className="av-icons">
              <button type="button" className="av-sec av-danger" onClick={onRemove}>
                <Trash2 strokeWidth={1.8} /> Remove from the wall — the file stays
              </button>
              <button type="button" className="av-ib" onClick={() => setConfirming(false)} aria-label="Keep it">
                <X strokeWidth={2} />
              </button>
            </div>
          ) : (
            <div className="av-icons">
              {item.generated_id ? (
                <button
                  type="button"
                  className={`av-ib${item.starred ? " on" : ""}`}
                  onClick={onStar}
                  aria-label={item.starred ? "Unstar" : "Star"}
                  aria-pressed={!!item.starred}
                  title={item.starred ? "Unstar" : "Star"}
                >
                  <Star strokeWidth={1.8} />
                </button>
              ) : null}
              {item.generated_id ? <ShareControls key={item.generated_id} id={item.generated_id} /> : null}
              {!phone ? (
                <a className="av-ib" href={downloadHref} {...downloadProps} aria-label="Download" title="Download">
                  <Download strokeWidth={1.8} />
                </a>
              ) : null}
              {item.generated_id ? (
                <button type="button" className="av-ib av-end" onClick={() => setConfirming(true)} aria-label="Delete" title="Delete">
                  <Trash2 strokeWidth={1.8} />
                </button>
              ) : null}
            </div>
          )}
        </footer>
      </aside>
    </motion.div>
  );
}
