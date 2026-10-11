"use client";

/* Renders — what is rendering and what finished (2026-10-11,
   docs/tasks/task-higgsfield-shape.md step 1; it was the Queue).

   NOTHING IS APPROVED HERE. The Queue page was the spend gate: a scene
   was picked on a board, waited here, and its card's priced button
   rendered it. A scene is rendered FROM the scene now -- its Render card
   (components/studio/render-card.tsx), opened from a project's scene list,
   the canvas or Create -- so this page only reports:

   - JOBS, off the studio's one job stream (lib/jobs.ts): what is running,
     what it holds or spent, what finished. The registry is in memory and a
     restart clears it, and the page says so.
   - NOT FINISHED, off the rows (GET /api/renders/unfinished), which a
     restart does not clear: a scene whose render failed or was cut short,
     a timed scene with some shots rendered, and anything picked or parked
     before the board went. Each links to its scene; the price and the
     button are there.
   - READY TO CUT (Assemble v0, 2026-09-26): a scene whose every shot has a
     clip, with Export -- /api/cut/assemble puts the clips on a versioned
     timeline in the order the scene was written and renders ONE MP4 with
     ffmpeg. Nothing here spends.
   - The MANUAL IMPORT LANE, for the operator only: a clip rendered
     anywhere, by hand, dropped on its card and filed free
     (/api/queue/manual, gated server-side; the `manual_lane` capability
     only decides whether the section is drawn). */
/* eslint-disable @next/next/no-img-element */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Clock, Copy, Film, Monitor, Music, RectangleVertical, Scissors, Upload, X } from "lucide-react";
import { OpenInEditor } from "@/components/cut/open-in-editor";
import { API_URL } from "@/lib/api";
import {
  QUEUE_EVENT,
  announceQueueChange,
  cancelJob,
  clearFinishedJobs,
  clearJob,
  cutAssemble,
  cutReady,
  cutUploadMedia,
  fileLaneClip,
  getCapabilities,
  queueManual,
  rendersUnfinished,
  sceneHref,
  type Concept,
  type CutReady,
  type Job,
  type LaneItem,
} from "@/lib/studio-api";
import { RefImg, heroOf, partsOf } from "@/components/studio/concept-card";
import { useShell } from "@/components/studio/shell";
import { creditsLabel, resultOf, sceneOf } from "@/lib/job-feed";
import { forgetJobs, refreshJobs, useJobs } from "@/lib/jobs";
import { liveJobFor, renderedOf } from "@/lib/render-choice";

type JobRow = Job & { cancellable?: boolean };
/* export jobs whose ending has already been toasted */
const announced = new Set<number>();

/* where a job's result opens, as a link (lib/job-feed.ts): a finished job
   its result, a render or keyframe job its scene -- while it runs, and
   after it failed, since rendering again is done from the scene */
function resultHref(job: Job): { href: string; label: string } | null {
  const to = resultOf(job);
  if (!to) {
    const scene = sceneOf(job);
    return scene ? { href: sceneHref(scene, 1), label: "Open scene" } : null;
  }
  if (to.to === "scene") return { href: sceneHref(to.id, 1), label: "Open scene" };
  if (to.to === "cut") return { href: `/studio/cut?project=${to.id}`, label: "Open in the editor" };
  if (to.to === "elements") return { href: "/studio/elements", label: "Open Elements" };
  return { href: "/studio/assets", label: "Open the Library" };
}

/* what an unfinished scene is waiting on, in one line */
function waitingOn(c: Concept, rendering: boolean): string {
  if (rendering) return "rendering now";
  if (c.blocked) return `cannot render yet · ${c.blocked}`;
  const done = renderedOf(c.media_url, partsOf(c));
  if (done.state === "partial") return `${done.clips} of ${done.of} shots rendered · render the rest from the scene`;
  return c.picked ? "render started, no clip yet · render it from the scene" : "written, not rendered · render it from the scene";
}

export default function RendersPage() {
  const { me, brand, toast } = useShell();
  // the account's jobs, off the studio's one stream (lib/jobs.ts)
  const jobs = useJobs() as JobRow[];
  const [unfinished, setUnfinished] = useState<Concept[] | null>(null);
  // the lane: drawn only when the capability says so; the routes re-ask the gate
  const [laneOn, setLaneOn] = useState(false);
  const [lane, setLane] = useState<LaneItem[] | null>(null);
  const [lanePicks, setLanePicks] = useState<Record<number, { model?: string; ratio?: string; duration?: number; anchored?: boolean }>>({});
  const [dropping, setDropping] = useState<Record<number, string>>({});
  // ready to cut: the rendered scenes, the export job each one has running,
  // and the music bed picked for it (an asset:<id> handle once uploaded)
  const [ready, setReady] = useState<CutReady[] | null>(null);
  const [cutOk, setCutOk] = useState(true);
  const [cutting, setCutting] = useState<Record<number, number>>({});
  const [beds, setBeds] = useState<Record<number, { handle?: string; name: string }>>({});

  // `stale` lets an effect drop a response that arrives after the brand
  // changed (the shell resolves the brand a beat after mount)
  const loadUnfinished = useCallback((stale: () => boolean = () => false) => {
    rendersUnfinished(brand || undefined)
      .then((r) => !stale() && setUnfinished(r.items))
      .catch(() => !stale() && setUnfinished([]));
  }, [brand]);
  const loadLane = useCallback((stale: () => boolean = () => false) => {
    queueManual(brand || undefined)
      .then((r) => {
        if (stale()) return;
        setLane(r.items);
      })
      .catch(() => {
        if (!stale()) setLane([]);
      });
  }, [brand]);
  const loadReady = useCallback((stale: () => boolean = () => false) => {
    cutReady(brand || undefined)
      .then((r) => {
        if (stale()) return;
        setReady(r.ready);
        setCutOk(r.ffmpeg);
      })
      .catch(() => {
        if (!stale()) setReady([]);
      });
  }, [brand]);
  const loadJobs = refreshJobs;
  useEffect(() => {
    getCapabilities()
      .then((c) => setLaneOn(c.manual_lane === true))
      .catch(() => setLaneOn(false));
  }, []);
  // the rows are re-read when the registry goes quiet: a finished clip
  // leaves "not finished" and joins "ready to cut"
  const active = jobs.some((j) => ["queued", "running"].includes(j.status));
  useEffect(() => {
    if (!me) return;
    let stale = false;
    loadUnfinished(() => stale);
    loadReady(() => stale);
    return () => {
      stale = true;
    };
  }, [active, me, loadUnfinished, loadReady]);
  useEffect(() => {
    if (!me || !laneOn) return;
    let stale = false;
    loadLane(() => stale);
    return () => {
      stale = true;
    };
  }, [active, me, laneOn, loadLane]);
  // a render approved on a scene in another tab, a scene removed
  useEffect(() => {
    const reread = () => loadUnfinished();
    window.addEventListener(QUEUE_EVENT, reread);
    return () => window.removeEventListener(QUEUE_EVENT, reread);
  }, [loadUnfinished]);
  // an export that ended says how it went, once. Whether a card is still
  // cutting is READ off the registry (cutLive), never stored beside it.
  useEffect(() => {
    for (const jobId of Object.values(cutting)) {
      const j = jobs.find((x) => x.id === jobId);
      if (!j || ["queued", "running"].includes(j.status) || announced.has(jobId)) continue;
      announced.add(jobId);
      if (j.status === "done") toast(`Cut v${j.version ?? "?"} ready — ${j.detail || "exported"}`);
      else toast(j.error || "The export did not finish", "err");
    }
  }, [jobs, cutting, toast]);

  /* ── the manual import lane: what rendered it is free text, and the frame
     and length are what the person says they are (no model table) ── */
  const lanePick = (item: LaneItem) => {
    const p = lanePicks[item.concept_id] || {};
    return {
      model: p.model ?? "",
      ratio: p.ratio ?? item.ratio,
      duration: p.duration ?? item.duration,
      anchored: p.anchored ?? !!item.keyframe_url,
    };
  };
  const fileClip = async (item: LaneItem, file: File | undefined) => {
    if (!file) return;
    const pick = lanePick(item);
    setDropping((d) => ({ ...d, [item.concept_id]: "filing…" }));
    try {
      const res = await fileLaneClip(item.concept_id, file, {
        shot_n: item.shot_n,
        model: pick.model.trim() || undefined,
        ratio: pick.ratio,
        duration: pick.duration,
        anchored: pick.anchored,
      });
      toast(`${item.title} filed — free, imported by hand${res.media_url ? ` · ${res.media_url}` : ""}`);
      loadUnfinished();
      loadLane();
      announceQueueChange();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not file the clip", "err");
    } finally {
      setDropping((d) => {
        const next = { ...d };
        delete next[item.concept_id];
        return next;
      });
    }
  };
  /* ── ready to cut ── */
  const pickBed = async (item: CutReady, file: File | undefined) => {
    if (!file) return;
    setBeds((w) => ({ ...w, [item.concept_id]: { name: `${file.name} · uploading…` } }));
    try {
      const res = await cutUploadMedia(file);
      setBeds((w) => ({ ...w, [item.concept_id]: { handle: res.handle, name: res.filename } }));
    } catch (e) {
      setBeds((w) => {
        const next = { ...w };
        delete next[item.concept_id];
        return next;
      });
      toast(e instanceof Error ? e.message : "Could not upload the music", "err");
    }
  };
  const exportCut = async (item: CutReady) => {
    const bed = beds[item.concept_id];
    try {
      const res = await cutAssemble(item.concept_id, bed?.handle ? { music: bed.handle } : {});
      setCutting((w) => ({ ...w, [item.concept_id]: res.job_id }));
      toast(`Cutting ${item.title} — ${res.clips} clip${res.clips === 1 ? "" : "s"}${bed?.handle ? " + music bed" : ""}`);
      loadJobs();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not start the export", "err");
    }
  };
  // just started and not in the registry yet counts as cutting
  const cutLive = (cid: number) => {
    const id = cutting[cid];
    if (id == null || announced.has(id)) return false;
    const j = jobs.find((x) => x.id === id);
    return !j || ["queued", "running"].includes(j.status);
  };
  const mediaHref = (url: string) => (url.startsWith("/") ? `${API_URL}${url}` : url);

  const copyPrompt = async (item: LaneItem) => {
    try {
      await navigator.clipboard.writeText(item.prompt);
      toast(`${item.title}'s prompt copied — paste it into your render app`);
    } catch {
      toast("Clipboard blocked — select the prompt and copy it by hand", "err");
    }
  };

  const live = jobs.filter((j) => ["queued", "running"].includes(j.status));
  const finished = jobs.filter((j) => !["queued", "running"].includes(j.status));
  const clearFinished = async () => {
    // one request for every finished job (DELETE /api/jobs); the stream
    // tells every open tab, and a polling one is told here
    await clearFinishedJobs().catch(() => {});
    forgetJobs(finished.map((j) => j.id));
  };

  return (
    <section className="view" style={{ paddingTop: 0 }}>
      <div className="vhead" style={{ marginTop: 8 }}>
        <h2>Renders</h2>
        <span className="spacer" />
        <span className="m">
          {live.length ? `${live.length} running` : "nothing running"} · a scene is rendered from its own Render button
        </span>
      </div>

      <div className="chead">
        <h3>Jobs</h3>
        <span className="m">live · this list clears when the server restarts</span>
        <span className="spacer" />
        <span className="m">
          {live.length} running · {jobs.length} total
        </span>
        {finished.length > 1 ? (
          <button type="button" className="tag" onClick={() => void clearFinished()}>
            Clear {finished.length} finished
          </button>
        ) : null}
      </div>
      <div className="qlist">
        {!jobs.length ? (
          <p className="stateline" style={{ padding: 0 }}>
            Nothing running. A job appears here when you render a scene, draw keyframes, write a scene or export a cut.
          </p>
        ) : null}
        {jobs.map((j) => {
          const running = ["queued", "running"].includes(j.status);
          return (
            <div key={j.id} className="qrow">
              <span className={`dot ${j.status === "failed" ? "bad" : running ? "run" : "ok"}`} />
              <div className="qinfo">
                <div className="qn">{j.label}</div>
                <div className="qm m">
                  {j.kind} · {j.status}
                  {j.detail ? ` · ${j.detail}` : ""}
                  {j.error ? ` · ${j.error}` : ""}
                  {creditsLabel(j) ? ` · ${creditsLabel(j)}` : ""}
                </div>
              </div>
              <div className="qbar">
                <i style={{ width: `${Math.round((j.progress || 0) * 100)}%` }} />
              </div>
              <span className="m">{j.status}</span>
              {/* one cell: the row is a five-column grid (dot, text, bar, status, actions) */}
              <span className="flex items-center justify-end gap-2">
                {(() => {
                  const open = resultHref(j);
                  return open ? (
                    <Link className="tag" href={open.href}>
                      {open.label}
                    </Link>
                  ) : null;
                })()}
                {running ? (
                  j.cancellable ? (
                    <button
                      type="button"
                      className="tag"
                      onClick={() =>
                        cancelJob(j.id)
                          .then(loadJobs)
                          .catch((e) => toast(e instanceof Error ? e.message : "Could not cancel", "err"))
                      }
                    >
                      Cancel
                    </button>
                  ) : null
                ) : (
                  <button
                    type="button"
                    className="tag"
                    onClick={() =>
                      clearJob(j.id)
                        .then(loadJobs)
                        .catch((e) => toast(e instanceof Error ? e.message : "Could not clear", "err"))
                    }
                  >
                    Clear
                  </button>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {unfinished && unfinished.length ? (
        <>
          <div className="chead">
            <h3>Not finished</h3>
            <span className="m">{`${unfinished.length} scene${unfinished.length === 1 ? "" : "s"} with no clip yet`}</span>
            <span className="spacer" />
            <span className="m">Open a scene to see its price and render it</span>
          </div>
          <div className="qlist">
            {unfinished.map((c) => {
              const hero = heroOf(c);
              const rendering = !!liveJobFor(jobs, c.id, "render");
              return (
                // its own four columns (dot, still, text, link): the job row's
                // five would squeeze the title into the progress bar's cell
                <div
                  key={`u-${c.id}`}
                  className="qrow"
                  data-unfinished={c.id}
                  style={{ gridTemplateColumns: "8px 72px minmax(0, 1fr) auto" }}
                >
                  <span className={`dot ${c.blocked ? "bad" : rendering ? "run" : "ok"}`} />
                  <span className="relative block h-10 w-[72px] overflow-hidden rounded-[4px] bg-noir-slate">
                    {hero.url ? <RefImg url={hero.url} className="block size-full object-cover" deadLabel="" /> : null}
                  </span>
                  <div className="qinfo">
                    <div className="qn">{c.title || "Untitled"}</div>
                    <div className="qm m">
                      {c.n} · {waitingOn(c, rendering)}
                    </div>
                  </div>
                  <Link className="tag" href={sceneHref(c.id, 1)}>
                    Open scene
                  </Link>
                </div>
              );
            })}
          </div>
        </>
      ) : null}

      {ready && ready.length ? (
        <>
          <div className="chead">
            <h3>Ready to cut</h3>
            <span className="m">{`${ready.length} rendered scene${ready.length === 1 ? "" : "s"}`}</span>
            <span className="spacer" />
            <span className="m">{cutOk ? "Export · the clips in shot order, one MP4 · free" : "Export needs ffmpeg on the server"}</span>
          </div>
          <div className="scenegrid">
            {ready.map((item) => {
              const busyCut = cutLive(item.concept_id);
              const bed = beds[item.concept_id];
              const poster = item.poster ? mediaHref(item.poster) : null;
              return (
                <article key={`cut-${item.concept_id}`} className="scene lane">
                  <div className="schead">
                    <h4>{item.title}</h4>
                    <span className="m">
                      {item.clips} clip{item.clips === 1 ? "" : "s"}
                    </span>
                    <span className="spacer" />
                    <span className="m">{item.export ? `v${item.export.version}` : "not cut yet"}</span>
                  </div>
                  <div className="scframe">
                    {poster ? (
                      <img src={poster} alt="" />
                    ) : (
                      <span className="scempty">
                        <span className="m">no keyframe</span>
                      </span>
                    )}
                  </div>
                  <div className="scchoice">
                    <label className="scsel" title="An optional music bed — it ducks under the clips' own sound">
                      <Music size={11} />
                      <input type="file" accept="audio/*" hidden onChange={(e) => void pickBed(item, e.target.files?.[0])} />
                      {bed ? bed.name : "add a music bed"}
                    </label>
                    {bed ? (
                      <button
                        type="button"
                        className="tag"
                        aria-label="Remove the music bed"
                        onClick={() =>
                          setBeds((w) => {
                            const next = { ...w };
                            delete next[item.concept_id];
                            return next;
                          })
                        }
                      >
                        <X size={12} strokeWidth={1.6} />
                      </button>
                    ) : null}
                  </div>
                  <div className="scfoot">
                    {item.export?.url ? (
                      <a className="tag" href={mediaHref(item.export.url)} target="_blank" rel="noreferrer">
                        <Film size={12} strokeWidth={1.6} /> Open v{item.export.version} MP4
                      </a>
                    ) : null}
                    <span className="spacer" />
                    <OpenInEditor concept_id={item.concept_id} className="tag">
                      <Scissors size={12} strokeWidth={1.6} /> Open in editor
                    </OpenInEditor>
                    <button
                      type="button"
                      className="tag"
                      disabled={!cutOk || busyCut || (!!bed && !bed.handle)}
                      onClick={() => void exportCut(item)}
                    >
                      {busyCut ? "Cutting…" : item.export ? "Export again" : "Export"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      ) : null}

      {laneOn ? (
        <>
          <div className="chead">
            <h3>Manual import</h3>
            <span className="m">{lane ? `${lane.length} to render by hand` : ""}</span>
            <span className="spacer" />
            <span className="m">Manual import · a clip rendered anywhere · filed free</span>
          </div>
          {lane && !lane.length ? (
            <p className="stateline" style={{ padding: "0 42px" }}>
              Nothing to render by hand — the lane lists scenes whose render was started and that have no clip yet
            </p>
          ) : null}
          <div className="scenegrid">
            {(lane || []).map((item) => {
              const pick = lanePick(item);
              const still = item.keyframe_url
                ? item.keyframe_url.startsWith("/")
                  ? `${API_URL}${item.keyframe_url}`
                  : item.keyframe_url
                : null;
              return (
                <article key={`lane-${item.concept_id}`} className="scene lane">
                  <div className="schead">
                    <h4>{item.title}</h4>
                    <span className="m">shot {item.shot_n}</span>
                    <span className="spacer" />
                    <span className="m">
                      {pick.duration}s · {pick.ratio}
                    </span>
                  </div>
                  <div className="scframe drag">
                    {still ? (
                      <img src={still} alt="" draggable title="Drag me into your render app's start-image slot" />
                    ) : (
                      <span className="scempty">
                        <span className="m">no keyframe · text-to-video</span>
                      </span>
                    )}
                  </div>
                  <p className="scpre">{item.prompt}</p>
                  <div className="scchoice">
                    <label className="scsel" title="What rendered it — free text, optional">
                      <Monitor size={11} />
                      <input
                        type="text"
                        aria-label="What rendered it"
                        placeholder="what rendered it, e.g. Kling 3 web app"
                        value={pick.model}
                        onChange={(e) => setLanePicks((w) => ({ ...w, [item.concept_id]: { ...w[item.concept_id], model: e.target.value } }))}
                      />
                    </label>
                    <label className="scsel" title="Frame rendered">
                      <RectangleVertical size={11} />
                      <input
                        type="text"
                        aria-label="Frame rendered"
                        value={pick.ratio}
                        onChange={(e) => setLanePicks((w) => ({ ...w, [item.concept_id]: { ...w[item.concept_id], ratio: e.target.value } }))}
                        style={{ width: "10ch" }}
                      />
                    </label>
                    <label className="scsel" title="Length rendered, in seconds">
                      <Clock size={11} />
                      <input
                        type="number"
                        min={1}
                        step={1}
                        aria-label="Length rendered, in seconds"
                        value={Number.isFinite(pick.duration) ? String(pick.duration) : ""}
                        onChange={(e) => setLanePicks((w) => ({ ...w, [item.concept_id]: { ...w[item.concept_id], duration: e.target.value === "" ? undefined : Number(e.target.value) } }))}
                        style={{ width: "6ch" }}
                      />
                      sec
                    </label>
                    {still ? (
                      <label className="scsel" title="Was the keyframe used as the start image">
                        <input type="checkbox" checked={pick.anchored} onChange={(e) => setLanePicks((w) => ({ ...w, [item.concept_id]: { ...w[item.concept_id], anchored: e.target.checked } }))} />
                        anchored
                      </label>
                    ) : null}
                  </div>
                  <label
                    className={`lanedrop${dropping[item.concept_id] ? " busy" : ""}`}
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.currentTarget.classList.add("over");
                    }}
                    onDragLeave={(e) => e.currentTarget.classList.remove("over")}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.currentTarget.classList.remove("over");
                      void fileClip(item, e.dataTransfer.files?.[0]);
                    }}
                  >
                    <input type="file" accept="video/mp4" hidden onChange={(e) => void fileClip(item, e.target.files?.[0])} />
                    <Upload size={14} strokeWidth={1.6} />
                    {dropping[item.concept_id] ?? "Drop the finished mp4 here, or click to pick it"}
                  </label>
                  <div className="scfoot">
                    <button type="button" className="tag" onClick={() => void copyPrompt(item)}>
                      <Copy size={12} strokeWidth={1.6} /> Copy prompt
                    </button>
                    <span className="spacer" />
                    <span className="m">{item.lane || "manual import"} · filed as free</span>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      ) : null}

    </section>
  );
}
