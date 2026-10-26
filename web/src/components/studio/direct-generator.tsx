"use client";

/* The direct generators (/studio/image and /studio/video, 2026-10-22;
   docs/tasks/task-direct-generators.md, src/direct.py, lib/direct.ts).

   The other door beside Create's chat: pick a model, type a prompt, see
   the price, press Generate. No brain turn and no rewrite -- the prompt
   reaches the model as typed -- and no scene: a clip made here needs no
   photograph (Mike's call), because the reference gate guards a scene's
   shots and one free-standing clip has none.

   The price on the button is ALWAYS the server's quote for exactly the
   pick on screen (re-asked on every change), and the run carries that
   number as `expect_credits`: if it moved, the server refuses (409) and
   the button prices itself again. The click is the one thing that spends.
   Everything made lands in the Library; this page lists this visit's
   makes and the newest of that kind already there. */
import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Check, ChevronDown, Clapperboard, Download, FolderOpen, ImageIcon, Paperclip, Wand2, X } from "lucide-react";
import { useShell } from "@/components/studio/shell";
import { ApiError } from "@/lib/api";
import { mediaSrc, newMadeId } from "@/lib/composer";
import { assetId } from "@/lib/continue";
import { vesperHref } from "@/lib/effects-tab";
import { TOP_UP_HREF, needsCredits } from "@/lib/out-of-credits";
import {
  PICK_KEY,
  buttonLabel,
  directHref,
  imageModelLine,
  imagePickFor,
  keptLine,
  openingModel,
  readPick,
  referencesLine,
  videoRefMode,
  videoRefTags,
  secondsChoices,
  videoModelLine,
  videoPickFor,
  type ImageMenu,
  type ImagePick,
  type Quote,
  type VideoMenu,
  type VideoPick,
} from "@/lib/direct";
import {
  announceBalanceChange,
  getDirectImage,
  getDirectVideo,
  getMedia,
  quoteDirectImage,
  quoteDirectVideo,
  renderDownloadHref,
  runDirect,
  waitForJob,
  type MediaItem,
} from "@/lib/studio-api";
import "@/components/studio/direct-generator.css";
/* eslint-disable @next/next/no-img-element */

/** A still's `thumb` names where its 480px derivative WOULD be, not that R2
 *  has one: when it fails to load, draw the master instead (once). */
const toMaster = (url: string | null | undefined) => (e: { currentTarget: HTMLImageElement }) => {
  if (!url) return;
  const img = e.currentTarget;
  const master = new URL(mediaSrc(url), window.location.href).href;
  if (img.src !== master) img.src = master;
};

type Kind = "image" | "video";

/** one picture this make is sent with: a file dropped or chosen here, or a
 *  render from the Library (sent by its address, as the composer sends a pick) */
type Ref = { key: string; thumb: string; file?: File; url?: string };

/** one make on this visit */
type Made = {
  id: string;
  kind: Kind;
  status: "running" | "done" | "failed";
  detail: string;
  prompt: string;
  label: string;
  credits: number;
  output?: string;
  asset?: string | null;
  outOfCredits?: boolean;
};

const readStore = (key: string): string | null => {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
};
const writeStore = (key: string, value: string) => {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* a private window: the pick is simply not remembered */
  }
};

export function DirectGenerator({ kind }: { kind: Kind }) {
  return (
    <Suspense fallback={null}>
      <Generator kind={kind} />
    </Suspense>
  );
}

function Generator({ kind }: { kind: Kind }) {
  const { toast, me } = useShell();
  const params = useSearchParams();
  const video = kind === "video";
  const workspace = me?.account?.slug ?? "";

  const [vMenu, setVMenu] = useState<VideoMenu | null>(null);
  const [iMenu, setIMenu] = useState<ImageMenu | null>(null);
  const [menuError, setMenuError] = useState("");
  const [vPick, setVPick] = useState<VideoPick | null>(null);
  const [iPick, setIPick] = useState<ImagePick | null>(null);
  const [pickNote, setPickNote] = useState("");
  const [modelsOpen, setModelsOpen] = useState(false);

  const [prompt, setPrompt] = useState("");
  const [refs, setRefs] = useState<Ref[]>([]);
  // one picture on a model with a reference endpoint: a start frame unless
  // the person says it is a reference
  const [oneAsRef, setOneAsRef] = useState(false);
  const [over, setOver] = useState(false);
  const [library, setLibrary] = useState<MediaItem[] | null>(null);
  const file = useRef<HTMLInputElement>(null);

  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteError, setQuoteError] = useState("");
  const [pricing, setPricing] = useState(false);
  const [sending, setSending] = useState(false);
  const [made, setMade] = useState<Made[]>([]);
  const [recent, setRecent] = useState<MediaItem[]>([]);

  /* ── the menu, and the pick it opens on ── */
  useEffect(() => {
    if (!workspace) return;
    let live = true;
    const linked = params.get("model");
    const typed = params.get("prompt");
    if (typed) setPrompt(typed.slice(0, 26000));
    const start = params.get("start");
    if (start && video) setRefs([{ key: `link-${start}`, thumb: start, url: start }]);
    if (video) {
      getDirectVideo()
        .then((m) => {
          if (!live) return;
          setVMenu(m);
          const was = readPick<VideoPick>(readStore(PICK_KEY.video), ["model", "seconds", "resolution", "aspect"]);
          const id = openingModel(m, linked, was?.model);
          const model = m.items.find((x) => x.id === id);
          if (model) setVPick(videoPickFor(model, was?.model === id ? was : null));
        })
        .catch((e) => live && setMenuError(e instanceof Error ? e.message : "The models could not be listed"));
    } else {
      getDirectImage()
        .then((m) => {
          if (!live) return;
          setIMenu(m);
          const was = readPick<ImagePick>(readStore(PICK_KEY.image), ["model", "aspect"]);
          const id = openingModel(m, linked, was?.model);
          const model = m.items.find((x) => x.id === id);
          if (model) setIPick(imagePickFor(model, was ?? { aspect: m.aspect }, m.aspects));
        })
        .catch((e) => live && setMenuError(e instanceof Error ? e.message : "The models could not be listed"));
    }
    getMedia({ kind })
      .then((w) => live && setRecent(w.items.filter((x) => x.generated_id).slice(0, 12)))
      .catch(() => {});
    return () => {
      live = false;
    };
    // the link is read once, on arrival
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace, kind]);

  const vModel = useMemo(() => vMenu?.items.find((m) => m.id === vPick?.model) ?? null, [vMenu, vPick]);
  const iModel = useMemo(() => iMenu?.items.find((m) => m.id === iPick?.model) ?? null, [iMenu, iPick]);
  const exempt = !!(video ? vMenu?.exempt : iMenu?.exempt);
  const refMode = video ? videoRefMode(vModel, refs.length, oneAsRef) : "none";
  const hasStart = refMode === "start";
  const held = refMode === "references" ? refs.length : 0;

  /* ── the price of exactly what is on screen ── */
  useEffect(() => {
    const pick = video ? vPick : iPick;
    if (!pick) return;
    let live = true;
    setPricing(true);
    setQuoteError("");
    const t = window.setTimeout(() => {
      const ask = video
        ? quoteDirectVideo({ ...(vPick as VideoPick), start_frame: hasStart, references: held })
        : quoteDirectImage({ ...(iPick as ImagePick), references: refs.length });
      ask
        .then((q) => {
          if (!live) return;
          setQuote({ credits: q.credits, charged: q.charged });
        })
        .catch((e) => {
          if (!live) return;
          setQuote(null);
          setQuoteError(e instanceof Error ? e.message : "This could not be priced");
        })
        .finally(() => live && setPricing(false));
    }, 200);
    return () => {
      live = false;
      window.clearTimeout(t);
    };
  }, [video, vPick, iPick, hasStart, held, refs.length]);

  /* ── changing the pick ── */
  const chooseModel = (id: string) => {
    setModelsOpen(false);
    if (video && vMenu) {
      const model = vMenu.items.find((m) => m.id === id);
      if (!model) return;
      const next = videoPickFor(model, vPick);
      setPickNote(keptLine(model, vPick, next));
      setVPick(next);
      writeStore(PICK_KEY.video, JSON.stringify(next));
    } else if (iMenu) {
      const model = iMenu.items.find((m) => m.id === id);
      if (!model) return;
      const next = imagePickFor(model, iPick, iMenu.aspects);
      setPickNote("");
      setIPick(next);
      writeStore(PICK_KEY.image, JSON.stringify(next));
    }
  };
  const setVideo = (part: Partial<VideoPick>) => {
    if (!vPick) return;
    const next = { ...vPick, ...part };
    setPickNote("");
    setVPick(next);
    writeStore(PICK_KEY.video, JSON.stringify(next));
  };
  const setImage = (part: Partial<ImagePick>) => {
    if (!iPick) return;
    const next = { ...iPick, ...part };
    setIPick(next);
    writeStore(PICK_KEY.image, JSON.stringify(next));
  };

  /* ── pictures: a start frame or references for a clip, references for a still ── */
  const vCap = Math.max(1, vModel?.max_refs ?? 0);
  const cap = video ? vCap : Math.max(1, iMenu ? Math.max(...iMenu.items.map((m) => m.max_refs), 1) : 12);
  const addRefs = useCallback(
    (list: Ref[]) => {
      if (!list.length) return;
      // a model that only starts on a picture swaps it; one with references adds up to its count
      setRefs((was) => (video && vCap === 1 ? [list[0]] : [...was, ...list].slice(0, cap)));
    },
    [video, vCap, cap],
  );
  const addFiles = (files: FileList | File[] | null | undefined) => {
    const pics = Array.from(files ?? []).filter((f) => f.type.startsWith("image/"));
    if (!pics.length) {
      if (files && Array.from(files).length) toast("Add a picture (jpg, png, webp)", "err");
      return;
    }
    addRefs(pics.map((f) => ({ key: newMadeId(), thumb: URL.createObjectURL(f), file: f })));
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    addFiles(e.dataTransfer.files);
  };
  const openLibrary = () => {
    if (library) return setLibrary(null);
    getMedia({ kind: "image" })
      .then((w) => setLibrary(w.items.filter((m) => m.generated_id || m.url)))
      .catch(() => toast("The Library could not be read", "err"));
  };
  const pickLibrary = (m: MediaItem) => {
    addRefs([{ key: `lib-${m.asset_id}`, thumb: m.thumb ?? m.url, url: m.url }]);
    setLibrary(null);
  };
  const dropRef = (key: string) => setRefs((was) => was.filter((r) => r.key !== key));

  /* ── Generate: the one click that spends, at the price the button showed ── */
  const patch = (id: string, fields: Partial<Made>) => setMade((all) => all.map((m) => (m.id === id ? { ...m, ...fields } : m)));
  const ready = video ? !!(vMenu?.ready && vPick) : !!(iMenu?.ready && iPick);
  const canSend = ready && !!prompt.trim() && !!quote && !pricing && !sending && !quoteError;
  async function generate() {
    if (!canSend || !quote) return;
    const label = (video ? vModel?.label : iModel?.label) ?? "";
    const form = new FormData();
    form.set("prompt", prompt.trim());
    form.set("expect_credits", String(quote.credits));
    if (video && vPick) {
      form.set("model", vPick.model);
      form.set("seconds", String(vPick.seconds));
      form.set("resolution", vPick.resolution);
      form.set("aspect", vPick.aspect);
      if (refMode === "references") form.set("ref_mode", "references");
    } else if (iPick) {
      form.set("model", iPick.model);
      form.set("aspect", iPick.aspect);
    }
    for (const r of refs) {
      if (r.file) form.append("files", r.file, r.file.name);
      else if (r.url) form.append("asset_photos", r.url);
    }
    const id = newMadeId();
    setSending(true);
    setMade((all) => [{ id, kind, status: "running", detail: `Starting on ${label}…`, prompt: prompt.trim(), label, credits: quote.credits }, ...all]);
    try {
      const started = await runDirect(kind, form);
      announceBalanceChange();
      setSending(false);
      const job = await waitForJob(started.job_id, (j) => patch(id, { detail: j.detail || "Working…" }));
      announceBalanceChange();
      const extra = job as unknown as { media?: string; asset?: string | null };
      const out = typeof job.output === "string" ? job.output : "";
      if (job.status !== "done" || !out) {
        const why = job.error || `The ${video ? "clip" : "still"} was not made. Nothing was charged.`;
        patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why) });
        return;
      }
      patch(id, { status: "done", detail: job.detail || "Done", output: out, asset: extra.asset ?? null });
    } catch (e) {
      setSending(false);
      if (e instanceof ApiError && e.status === 409) {
        // the price moved under the button: nothing ran, and it prices itself again
        setMade((all) => all.filter((m) => m.id !== id));
        setQuote(null);
        if (video && vPick) setVPick({ ...vPick });
        else if (iPick) setIPick({ ...iPick });
        toast(`${e.message}. Nothing ran — check the price and press Generate again.`, "err");
        return;
      }
      const why = e instanceof Error ? e.message : "That did not go through.";
      patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why, e instanceof ApiError ? e.status : undefined) });
    }
  }

  /* ── drawing ── */
  const title = video ? "Video" : "Image";
  const items = video ? (vMenu?.items ?? []) : (iMenu?.items ?? []);
  const current = video ? vModel : iModel;
  const lengths = secondsChoices(vModel?.seconds);
  const warn = !video && iModel ? referencesLine(iModel, refs.length) : "";

  return (
    <section className="view dg">
      <div className="vhead" style={{ marginTop: 8 }}>
        <h2>{title}</h2>
        <span className="spacer" />
        <span className="m">Your prompt, as typed. The price is on the button.</span>
      </div>

      <div className="dg-grid">
        <form
          className="dg-panel"
          data-over={over ? "1" : undefined}
          onSubmit={(e) => {
            e.preventDefault();
            void generate();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
        >
          {/* 1. the model: the pick is final here */}
          <div className="dg-field">
            <span className="dg-lab">Model</span>
            <button
              type="button"
              className="dg-model"
              aria-haspopup="listbox"
              aria-expanded={modelsOpen}
              onClick={() => setModelsOpen((v) => !v)}
              disabled={!items.length}
            >
              {video ? <Clapperboard strokeWidth={1.6} /> : <ImageIcon strokeWidth={1.6} />}
              <span className="dg-model-txt">
                <b>{current?.label ?? (menuError ? "Unavailable" : "Loading…")}</b>
                <small>{current ? current.note : ""}</small>
              </span>
              <ChevronDown strokeWidth={1.8} className="dg-chev" />
            </button>
            {modelsOpen ? (
              <ul className="dg-models" role="listbox" aria-label={`${title} models`}>
                {video
                  ? (vMenu?.items ?? []).map((m) => (
                      <li key={m.id}>
                        <button type="button" role="option" aria-selected={m.id === vPick?.model} onClick={() => chooseModel(m.id)}>
                          <span>
                            <b>{m.label}</b>
                            <small>{m.note}</small>
                            <i>{videoModelLine(m)}</i>
                          </span>
                          {m.id === vPick?.model ? <Check strokeWidth={2} /> : null}
                        </button>
                      </li>
                    ))
                  : (iMenu?.items ?? []).map((m) => (
                      <li key={m.id}>
                        <button type="button" role="option" aria-selected={m.id === iPick?.model} onClick={() => chooseModel(m.id)}>
                          <span>
                            <b>{m.label}</b>
                            <small>{m.note}</small>
                            <i>{imageModelLine(m)}</i>
                          </span>
                          {m.id === iPick?.model ? <Check strokeWidth={2} /> : null}
                        </button>
                      </li>
                    ))}
              </ul>
            ) : null}
            {pickNote ? <p className="dg-note">{pickNote}</p> : null}
          </div>

          {/* 2. the prompt, as the model will read it */}
          <label className="dg-field">
            <span className="dg-lab">Prompt</span>
            <textarea
              className="dg-prompt"
              value={prompt}
              maxLength={video ? (vModel?.prompt_max ?? 4000) : 4000}
              rows={6}
              placeholder={
                video
                  ? "A slow push-in on a rain-soaked neon street at night, a lone rider pulls up, steam rising from the asphalt…"
                  : "A studio product shot of a matte black perfume bottle on wet stone, soft rim light, shallow depth of field…"
              }
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void generate();
                }
              }}
            />
          </label>

          {/* 3. pictures */}
          <div className="dg-field">
            <span className="dg-lab">
              {video ? (refMode === "references" ? "References" : vCap > 1 ? "Pictures" : "Start frame") : "References"}{" "}
              <em>optional</em>
            </span>
            <div className="dg-refs">
              {refs.map((r) => (
                <span key={r.key} className="dg-ref">
                  <img src={mediaSrc(r.thumb)} alt="" onError={toMaster(r.url)} />
                  <button type="button" aria-label="Remove this picture" onClick={() => dropRef(r.key)}>
                    <X strokeWidth={2} />
                  </button>
                </span>
              ))}
              {refs.length < cap ? (
                <>
                  <input
                    ref={file}
                    type="file"
                    accept="image/*"
                    multiple={!video || vCap > 1}
                    hidden
                    onChange={(e) => {
                      addFiles(e.target.files);
                      e.target.value = "";
                    }}
                  />
                  <button type="button" className="dg-btn" onClick={() => file.current?.click()}>
                    <Paperclip strokeWidth={1.8} /> Add a picture
                  </button>
                  <button type="button" className="dg-btn" onClick={openLibrary} aria-expanded={!!library}>
                    <FolderOpen strokeWidth={1.8} /> From the Library
                  </button>
                </>
              ) : null}
            </div>
            <p className="dg-hint">
              {video
                ? refMode === "references"
                  ? `The clip is held to these pictures. Name them in the prompt: ${videoRefTags(vModel, refs.length).join(", ")}.`
                  : hasStart
                    ? "The clip starts on this picture and takes its shape."
                    : vCap > 1
                      ? `One picture is the start frame; add more and ${vModel?.label ?? "the model"} is held to up to ${vCap} as references.`
                      : "Leave it empty to make the clip from the prompt alone."
                : "Drop pictures here, or add them. Each model takes its own number."}
            </p>
            {video && refs.length === 1 && vCap > 1 ? (
              <div className="dg-seg" role="radiogroup" aria-label="Use the picture as">
                <button type="button" role="radio" aria-checked={!oneAsRef} onClick={() => setOneAsRef(false)}>
                  Start frame
                </button>
                <button type="button" role="radio" aria-checked={oneAsRef} onClick={() => setOneAsRef(true)}>
                  Reference
                </button>
              </div>
            ) : null}
            {warn ? <p className="dg-note">{warn}</p> : null}
            {library ? (
              <div className="dg-lib" role="dialog" aria-label="Pick from the Library">
                <div className="dg-lib-head">
                  <b>Your Library</b>
                  <span>{library.length ? "Pick a still." : "No stills yet."}</span>
                  <button type="button" className="dg-btn" onClick={() => setLibrary(null)}>
                    <X strokeWidth={1.8} /> Close
                  </button>
                </div>
                <ul>
                  {library.slice(0, 48).map((m) => (
                    <li key={m.asset_id}>
                      <button type="button" onClick={() => pickLibrary(m)} title={m.prompt || m.asset_name}>
                        <img src={mediaSrc(m.thumb ?? m.url)} alt="" loading="lazy" onError={toMaster(m.url)} />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          {/* 4. the settings the model takes */}
          {video && vModel && vPick ? (
            <div className="dg-settings">
              <label className="dg-set">
                <span>Length</span>
                <select value={vPick.seconds} onChange={(e) => setVideo({ seconds: Number(e.target.value) })} disabled={lengths.length < 2}>
                  {lengths.map((s) => (
                    <option key={s} value={s}>
                      {s}s
                    </option>
                  ))}
                </select>
              </label>
              <div className="dg-set">
                <span>Resolution</span>
                <div className="dg-seg" role="radiogroup" aria-label="Resolution">
                  {vModel.resolutions.map((r) => (
                    <button key={r} type="button" role="radio" aria-checked={vPick.resolution === r} onClick={() => setVideo({ resolution: r })}>
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div className="dg-set">
                <span>Frame</span>
                {hasStart ? (
                  <em className="dg-follow">follows the start frame</em>
                ) : (
                  <div className="dg-seg" role="radiogroup" aria-label="Frame">
                    {vModel.aspects.map((a) => (
                      <button key={a} type="button" role="radio" aria-checked={vPick.aspect === a} onClick={() => setVideo({ aspect: a })}>
                        {a}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
          {!video && iMenu && iPick ? (
            <div className="dg-settings">
              <div className="dg-set">
                <span>Shape</span>
                <div className="dg-seg" role="radiogroup" aria-label="Shape">
                  {iMenu.aspects.map((a) => (
                    <button key={a} type="button" role="radio" aria-checked={iPick.aspect === a} onClick={() => setImage({ aspect: a })}>
                      {a}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {/* 5. the one button that spends */}
          {quoteError ? <p className="dg-note err">{quoteError}</p> : null}
          {menuError ? <p className="dg-note err">{menuError}</p> : null}
          {(video ? vMenu : iMenu) && !ready && !menuError ? (
            <p className="dg-note err">{video ? "Video" : "Image"} models are not set up on this server yet.</p>
          ) : null}
          <button type="submit" className="dg-go" disabled={!canSend}>
            <Wand2 strokeWidth={1.8} />
            {sending ? "Starting…" : buttonLabel(quote, pricing, exempt)}
          </button>
          <p className="dg-hint">
            Rather talk it through? <Link href="/studio">Create</Link> plans it with you and holds a scene to your photos.
          </p>
        </form>

        <div className="dg-out">
          {made.length ? (
            <ul className="dg-made" aria-label="Made on this visit">
              {made.map((m) => (
                <MadeCard key={m.id} m={m} />
              ))}
            </ul>
          ) : (
            <div className="dg-empty">
              {video ? <Clapperboard strokeWidth={1.3} /> : <ImageIcon strokeWidth={1.3} />}
              <b>What you make lands here</b>
              <span>And in your Library, with everything else you have made.</span>
            </div>
          )}
          {recent.length ? (
            <>
              <div className="dg-recent-head">
                <b>Recent {video ? "clips" : "stills"}</b>
                <Link href="/studio/assets">Open the Library</Link>
              </div>
              <ul className="dg-recent">
                {recent.map((m) => (
                  <li key={m.asset_id}>
                    <Link href={`/studio/assets?open=${m.generated_id}`} aria-label={m.prompt || "Open in the Library"}>
                      {m.kind === "video" ? (
                        // its first frame at rest, playing while the pointer is on it
                        <video
                          src={mediaSrc(m.url)}
                          poster={m.poster ? mediaSrc(m.poster) : undefined}
                          muted
                          loop
                          playsInline
                          preload="metadata"
                          onMouseEnter={(e) => void e.currentTarget.play().catch(() => {})}
                          onMouseLeave={(e) => e.currentTarget.pause()}
                        />
                      ) : (
                        // the 480px thumbnail, or the master when R2 has none
                        // (`thumb` names where one WOULD be, not that it is)
                        <img
                          src={mediaSrc(m.thumb ?? m.url)}
                          alt=""
                          loading="lazy"
                          onError={(e) => {
                            const img = e.currentTarget;
                            const master = new URL(mediaSrc(m.url), window.location.href).href;
                            if (img.src !== master) img.src = master;
                          }}
                        />
                      )}
                      {m.model_label ? <span className="k">{m.model_label}</span> : null}
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function MadeCard({ m }: { m: Made }) {
  const id = assetId(m.asset);
  const toVesper = vesperHref(m.asset, m.label);
  return (
    <li className="dg-card" data-status={m.status}>
      <div className="dg-card-media">
        {m.status === "done" && m.output ? (
          m.kind === "video" ? (
            <video src={mediaSrc(m.output)} controls playsInline autoPlay muted loop />
          ) : (
            <img src={mediaSrc(m.output)} alt={m.prompt} />
          )
        ) : (
          <div className="dg-card-wait">
            {m.status === "running" ? <span className="dg-spin" aria-hidden /> : null}
            <span>{m.detail}</span>
            {m.outOfCredits ? (
              <Link className="dg-btn" href={TOP_UP_HREF}>
                Add credits
              </Link>
            ) : null}
          </div>
        )}
      </div>
      <div className="dg-card-foot">
        <span className="dg-card-what">
          <b>{m.label}</b>
          <small>{m.status === "done" ? `${m.credits.toLocaleString("en-US")} credits` : m.status === "running" ? "working…" : "not made"}</small>
        </span>
        {m.status === "done" ? (
          <span className="dg-card-acts">
            {id !== null ? (
              <a className="dg-btn" href={renderDownloadHref(id)} download title="Save the file">
                <Download strokeWidth={1.8} />
              </a>
            ) : null}
            {m.kind === "image" && m.output ? (
              <Link className="dg-btn" href={`${directHref("video")}${"?start="}${encodeURIComponent(m.output)}`} title="Make a clip that starts on this still">
                <Clapperboard strokeWidth={1.8} /> Animate
              </Link>
            ) : null}
            {toVesper ? (
              <Link className="dg-btn" href={toVesper} title="Opens Create with this attached">
                <Wand2 strokeWidth={1.8} /> Use in Create
              </Link>
            ) : null}
          </span>
        ) : null}
      </div>
      <p className="dg-card-prompt">{m.prompt}</p>
    </li>
  );
}
