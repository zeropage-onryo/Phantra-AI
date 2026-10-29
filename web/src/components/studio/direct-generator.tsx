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

   Two layouts over one state (2026-10-26, Mike's picks on the design
   canvas, docs/tasks/task-direct-pages-r3.md):
   - Image: the panel on the left, the stage in the middle (the one
     still being looked at, or the one being drawn), the history on the
     right (this visit, then the Library's newest stills).
   - Video: the theatre (the clip being watched or rendered) with the
     strip on the right, and the dock under it holding the pictures, the
     prompt, the model / length / resolution / frame menus and Generate.
   The one button that spends is yellow and carries its price; a white
   button confirms without spending (Add, from the picture picker). */
import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode, type RefObject } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Check, ChevronDown, Clapperboard, Download, LayoutGrid, RotateCcw, Upload, Wand2, X } from "lucide-react";
import { cardFonts } from "@/components/studio/card-fonts";
import { useShell } from "@/components/studio/shell";
import { ApiError } from "@/lib/api";
import { mediaSrc, newMadeId } from "@/lib/composer";
import { vesperHref } from "@/lib/effects-tab";
import { TOP_UP_HREF, needsCredits } from "@/lib/out-of-credits";
import {
  PICK_KEY,
  STARTERS,
  buttonLabel,
  directHref,
  imagePickFor,
  keptLine,
  modelBadges,
  openingModel,
  readPick,
  referencesLine,
  refsCountLine,
  reuseOf,
  videoRefMode,
  videoRefTags,
  secondsChoices,
  videoPickFor,
  type ImageMenu,
  type ImagePick,
  type Quote,
  type VideoMenu,
  type VideoPick,
} from "@/lib/direct";
import {
  announceBalanceChange,
  cancelJob,
  getDirectImage,
  getDirectVideo,
  getElementPhotos,
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
 *  render / element photo (sent by its address, as the composer sends a pick) */
type Ref = { key: string; thumb: string; file?: File; url?: string };

/** one thing the stage or the theatre can show: a make from this visit, or
 *  one of the Library's newest of this kind */
type Shown = {
  id: string;
  kind: Kind;
  from: "visit" | "library";
  status: "running" | "done" | "failed";
  detail: string;
  prompt: string;
  label: string;
  credits?: number;
  src?: string;
  poster?: string | null;
  thumb?: string | null;
  asset?: string | null;
  model?: string | null;
  pick?: VideoPick | ImagePick | null;
  outOfCredits?: boolean;
  jobId?: number;
  cancellable?: boolean;
  /** the starting picture, blurred behind a still being drawn */
  behind?: string | null;
};

type MenuName = "model" | "length" | "res" | "frame" | null | "dock-model" | "dock-shape";

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

const fromLibrary = (m: MediaItem): Shown => ({
  id: `lib-${m.asset_id}`,
  kind: m.kind,
  from: "library",
  status: "done",
  detail: "",
  prompt: m.prompt ?? "",
  label: m.model_label ?? "",
  src: m.url,
  poster: m.poster ?? null,
  thumb: m.thumb ?? null,
  asset: m.generated_id ? `gen:${m.generated_id}` : null,
  model: m.model ?? null,
});

/** Closes a popover on Escape or a press outside `box`. */
function useDismiss(box: RefObject<HTMLElement | null>, open: boolean, close: () => void) {
  useEffect(() => {
    if (!open) return;
    const down = (e: PointerEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) close();
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("pointerdown", down);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", down);
      document.removeEventListener("keydown", key);
    };
  }, [box, open, close]);
}

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
  const [menu, setMenu] = useState<MenuName>(null);

  // a link may carry a prompt and (on Video) a start frame: read once, on arrival
  const [prompt, setPrompt] = useState(() => (params.get("prompt") ?? "").slice(0, 26000));
  const promptEl = useRef<HTMLTextAreaElement>(null);
  // the phone's docked box on Image (2026-10-29): the panel's prompt is hidden there
  const dockPromptEl = useRef<HTMLTextAreaElement>(null);
  const [refs, setRefs] = useState<Ref[]>(() => {
    const start = video ? params.get("start") : null;
    return start ? [{ key: `link-${start}`, thumb: start, url: start }] : [];
  });
  // one picture on a model with a reference endpoint: a start frame unless
  // the person says it is a reference
  const [oneAsRef, setOneAsRef] = useState(false);
  const [over, setOver] = useState(false);
  const [picking, setPicking] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  // the server's price for one exact pick, kept with the pick it was asked
  // for: on screen only while that is still the pick (else "pricing…")
  const [priced, setPriced] = useState<{ key: string; quote: Quote | null; error: string }>({ key: "", quote: null, error: "" });
  const [nonce, setNonce] = useState(0);
  const [sending, setSending] = useState(false);
  const [made, setMade] = useState<Shown[]>([]);
  const [recent, setRecent] = useState<Shown[]>([]);
  const [shownId, setShownId] = useState<string | null>(null);

  /* ── the menu, and the pick it opens on ── */
  useEffect(() => {
    if (!workspace) return;
    let live = true;
    const linked = params.get("model");
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
      .then((w) => live && setRecent(w.items.filter((x) => x.generated_id).slice(0, 12).map(fromLibrary)))
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
  const pick = video ? vPick : iPick;
  const priceKey = pick ? JSON.stringify(video ? [vPick, hasStart, held, nonce] : [iPick, refs.length, nonce]) : "";
  useEffect(() => {
    if (!priceKey) return;
    let live = true;
    const t = window.setTimeout(() => {
      const ask = video
        ? quoteDirectVideo({ ...(vPick as VideoPick), start_frame: hasStart, references: held })
        : quoteDirectImage({ ...(iPick as ImagePick), references: refs.length });
      ask
        .then((q) => live && setPriced({ key: priceKey, quote: { credits: q.credits, charged: q.charged }, error: "" }))
        .catch((e) => live && setPriced({ key: priceKey, quote: null, error: e instanceof Error ? e.message : "This could not be priced" }));
    }, 200);
    return () => {
      live = false;
      window.clearTimeout(t);
    };
    // the key carries every part of the pick the price depends on
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priceKey]);
  const fresh = !!priceKey && priced.key === priceKey;
  const quote = fresh ? priced.quote : null;
  const quoteError = fresh ? priced.error : "";
  const pricing = !!priceKey && !fresh;

  /* ── changing the pick ── */
  const chooseModel = (id: string) => {
    setMenu(null);
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
    setMenu(null);
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
  const drop = {
    onDragOver: (e: DragEvent) => {
      if (!Array.from(e.dataTransfer.types).includes("Files")) return;
      e.preventDefault();
      setOver(true);
    },
    onDragLeave: (e: DragEvent) => {
      if (e.currentTarget === e.target) setOver(false);
    },
    onDrop: (e: DragEvent) => {
      e.preventDefault();
      setOver(false);
      addFiles(e.dataTransfer.files);
    },
  };
  const dropRef = (key: string) => setRefs((was) => was.filter((r) => r.key !== key));
  const room = Math.max(0, cap - refs.length);

  /* ── what the stage / theatre shows ── */
  const all = useMemo(() => [...made, ...recent], [made, recent]);
  const shown = all.find((s) => s.id === shownId) ?? null;
  const patch = (id: string, fields: Partial<Shown>) => setMade((list) => list.map((m) => (m.id === id ? { ...m, ...fields } : m)));

  /** Put a render's prompt and pick back in the controls (nothing runs). */
  const reuse = (s: Shown) => {
    const r = reuseOf(s, video ? vMenu : iMenu);
    setPrompt(r.prompt);
    if (r.model) {
      if (video && vMenu) {
        const model = vMenu.items.find((m) => m.id === r.model);
        if (model) {
          const next = videoPickFor(model, (s.pick as VideoPick | null) ?? vPick);
          setPickNote(keptLine(model, (s.pick as VideoPick | null) ?? null, next));
          setVPick(next);
          writeStore(PICK_KEY.video, JSON.stringify(next));
        }
      } else if (iMenu) {
        const model = iMenu.items.find((m) => m.id === r.model);
        if (model) {
          const next = imagePickFor(model, (s.pick as ImagePick | null) ?? iPick, iMenu.aspects);
          setIPick(next);
          writeStore(PICK_KEY.image, JSON.stringify(next));
        }
      }
    }
    toast(r.model ? "Prompt and settings are back in place. Nothing ran." : "Prompt is back in place. Nothing ran.", "ok");
    promptEl.current?.focus();
  };

  /* ── Generate: the one click that spends, at the price the button showed ── */
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
    setMade((list) => [
      {
        id,
        kind,
        from: "visit",
        status: "running",
        detail: `Starting on ${label}…`,
        prompt: prompt.trim(),
        label,
        credits: quote.credits,
        model: video ? vPick?.model : iPick?.model,
        pick: video ? vPick : iPick,
        behind: refs[0]?.thumb ?? null,
      },
      ...list,
    ]);
    setShownId(id);
    try {
      const started = await runDirect(kind, form);
      announceBalanceChange();
      setSending(false);
      patch(id, { jobId: started.job_id });
      const job = await waitForJob(started.job_id, (j) => patch(id, { detail: j.detail || "Working…", cancellable: !!j.cancellable }));
      announceBalanceChange();
      const extra = job as unknown as { media?: string; asset?: string | null };
      const out = typeof job.output === "string" ? job.output : "";
      if (job.status === "cancelled") {
        patch(id, { status: "failed", detail: job.error || "Cancelled.", cancellable: false });
        return;
      }
      if (job.status !== "done" || !out) {
        const why = job.error || `The ${video ? "clip" : "still"} was not made. Nothing was charged.`;
        patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why), cancellable: false });
        return;
      }
      patch(id, { status: "done", detail: job.detail || "Done", src: out, asset: extra.asset ?? null, cancellable: false });
    } catch (e) {
      setSending(false);
      if (e instanceof ApiError && e.status === 409) {
        // the price moved under the button: nothing ran, and it prices itself again
        setMade((list) => list.filter((m) => m.id !== id));
        setShownId(null);
        setNonce((n) => n + 1);
        toast(`${e.message}. Nothing ran — check the price and press Generate again.`, "err");
        return;
      }
      const why = e instanceof Error ? e.message : "That did not go through.";
      patch(id, { status: "failed", detail: why, outOfCredits: needsCredits(why, e instanceof ApiError ? e.status : undefined) });
    }
  }
  const cancel = (s: Shown) => {
    if (!s.jobId) return;
    cancelJob(s.jobId)
      .then(() => patch(s.id, { detail: "Cancelling…", cancellable: false }))
      .catch((e) => toast(e instanceof Error ? e.message : "It could not be cancelled", "err"));
  };

  /* ── the pieces both layouts draw ── */
  const items = video ? (vMenu?.items ?? []) : (iMenu?.items ?? []);
  const current = video ? vModel : iModel;
  const lengths = secondsChoices(vModel?.seconds);
  const warn = !video && iModel ? referencesLine(iModel, refs.length) : "";
  const notSent = !video && !!iModel && iModel.max_refs <= 0 && refs.length > 0;
  const tags = refMode === "references" ? videoRefTags(vModel, refs.length) : [];
  const insertTag = (tag: string) => {
    const el = promptEl.current;
    const at = el ? el.selectionStart : prompt.length;
    const next = `${prompt.slice(0, at)}${tag} ${prompt.slice(at)}`;
    setPrompt(next);
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(at + tag.length + 1, at + tag.length + 1);
    });
  };
  const goLabel = sending ? "Starting…" : buttonLabel(quote, pricing, exempt);
  const notes = (
    <>
      {pickNote ? <p className="dg-kept">{pickNote}</p> : null}
      {quoteError ? <p className="dg-note err">{quoteError}</p> : null}
      {menuError ? <p className="dg-note err">{menuError}</p> : null}
      {(video ? vMenu : iMenu) && !ready && !menuError ? (
        <p className="dg-note err">{video ? "Video" : "Image"} models are not set up on this server yet.</p>
      ) : null}
    </>
  );
  const modelItems = items.map((m) => ({
    id: m.id,
    name: m.label,
    note: m.note,
    right: modelBadges(m),
  }));
  const fileInput = (
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
  );
  const picker = picking ? (
    <PicturePicker
      room={video && vCap === 1 ? 1 : room}
      note={video ? (vCap > 1 ? `${vModel?.label ?? "This model"} holds up to ${vCap}.` : "One picture: the clip starts on it.") : "Each is sent by its address; nothing is uploaded again."}
      onClose={() => setPicking(false)}
      onAdd={(list) => {
        addRefs(list.map((m) => ({ key: `lib-${m.asset_id}`, thumb: m.thumb ?? m.url, url: m.url })));
        setPicking(false);
      }}
    />
  ) : null;
  const tray = (size: "lg" | "sm") => (
    <div className="dg-tray" data-size={size}>
      {refs.map((r, i) => (
        <span key={r.key} className="dg-thumb" data-off={notSent ? "1" : undefined}>
          <img src={mediaSrc(r.thumb)} alt="" onError={toMaster(r.url)} />
          {video && refMode === "start" ? <i className="dg-tag">Start</i> : null}
          {tags[i] ? (
            <button type="button" className="dg-tag" title="Put this tag in the prompt" onClick={() => insertTag(tags[i])}>
              {tags[i]}
            </button>
          ) : null}
          {notSent ? <i className="dg-tag">Not sent</i> : null}
          <button type="button" className="dg-thumb-x" aria-label="Remove this picture" onClick={() => dropRef(r.key)}>
            <X strokeWidth={2.4} />
          </button>
        </span>
      ))}
      {refs.length < cap || (video && vCap === 1) ? (
        <>
          <button type="button" className="dg-add" onClick={() => file.current?.click()}>
            <Upload strokeWidth={1.8} />
            <span>{video && vCap === 1 && refs.length ? "Replace" : "Upload"}</span>
          </button>
          <button type="button" className="dg-add" onClick={() => setPicking((v) => !v)} aria-expanded={picking}>
            <LayoutGrid strokeWidth={1.8} />
            <span>Library</span>
          </button>
        </>
      ) : null}
      {fileInput}
    </div>
  );

  if (!video) {
    return (
      <section className={`view dg dgi ${cardFonts}`} data-over={over ? "1" : undefined} {...drop}>
        <form
          className="dg-panel"
          onSubmit={(e) => {
            e.preventDefault();
            void generate();
          }}
        >
          <div className="dg-field">
            <span className="dg-lab">Model</span>
            <ModelMenu
              open={menu === "model"}
              onOpen={() => setMenu(menu === "model" ? null : "model")}
              onClose={() => setMenu(null)}
              label={current?.label ?? (menuError ? "Unavailable" : "Loading…")}
              sub={current?.note ?? ""}
              items={modelItems}
              picked={iPick?.model ?? ""}
              onPick={chooseModel}
              title={`${items.length} image models`}
              foot="The price is for one still at this shape. Switching keeps your prompt and your pictures."
              disabled={!items.length}
            />
          </div>

          <label className="dg-field">
            <span className="dg-lab-row">
              <span className="dg-lab">Prompt</span>
              <span className="dg-count">
                {prompt.length.toLocaleString("en-US")} / 4,000
              </span>
            </span>
            <textarea
              ref={promptEl}
              className="dg-prompt"
              value={prompt}
              maxLength={4000}
              rows={6}
              placeholder="A studio product shot of a matte black perfume bottle on wet stone, soft rim light, shallow depth of field…"
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void generate();
                }
              }}
            />
          </label>

          <div className="dg-field">
            <span className="dg-lab-row">
              <span className="dg-lab">
                References <em>optional</em>
              </span>
              <span className="dg-count">{iModel ? refsCountLine(iModel.max_refs, refs.length) : ""}</span>
            </span>
            {tray("lg")}
            {warn ? <p className="dg-kept">{warn}</p> : <p className="dg-hint">Drop pictures anywhere on this panel.</p>}
          </div>

          {iMenu && iPick ? (
            <div className="dg-field">
              <span className="dg-lab">Shape</span>
              <div className="dg-shapes" role="radiogroup" aria-label="Shape">
                {(iModel?.aspects?.length ? iModel.aspects : iMenu.aspects).map((a) => (
                  <button key={a} type="button" role="radio" aria-checked={iPick.aspect === a} onClick={() => setImage({ aspect: a })}>
                    <Frame aspect={a} />
                    {a}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <span className="dg-grow" />
          {notes}
          <button type="submit" className="dg-go" disabled={!canSend} data-busy={pricing || sending ? "1" : undefined}>
            {sending ? <span className="dg-spin sm" aria-hidden /> : <Wand2 strokeWidth={1.8} />}
            {goLabel}
          </button>
          <p className="dg-hint">
            ⌘↵ generates. Rather talk it through? <Link href="/studio">Create</Link> plans it with you.
          </p>
        </form>

        <Stage
          shown={shown}
          video={false}
          onStarter={(t) => {
            setPrompt(t);
            (promptEl.current?.offsetParent ? promptEl : dockPromptEl).current?.focus();
          }}
          onReuse={reuse}
          onCancel={cancel}
        />

        <History made={made} recent={recent} shownId={shownId} onShow={setShownId} />

        {/* THE PHONE'S BOX (2026-10-29, Mike: "the create is still not staying
            at the bottom ... reference higgsfield"): under 720px the panel
            above is hidden and Image takes Video's shape -- pictures, the
            prompt and one line of Model, Shape and Generate, pinned above the
            tab bar from the moment the page opens (direct-generator.css). */}
        <form
          className="dgv-dock dgi-dock"
          onSubmit={(e) => {
            e.preventDefault();
            void generate();
          }}
        >
          <div className="dgv-dock-top">
            {tray("sm")}
            <textarea
              ref={dockPromptEl}
              className="dgv-prompt"
              value={prompt}
              maxLength={4000}
              rows={2}
              aria-label="Prompt"
              placeholder="Describe the image: the subject, the light, the look…"
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>
          {notes}
          <div className="dgv-dock-bar">
            <ChipMenu
              name="Model"
              open={menu === "dock-model"}
              onOpen={() => setMenu(menu === "dock-model" ? null : "dock-model")}
              onClose={() => setMenu(null)}
              strong
              value={current?.label ?? (menuError ? "Unavailable" : "Loading…")}
              items={modelItems}
              picked={iPick?.model ?? ""}
              onPick={chooseModel}
              title={`${items.length} image models`}
              foot="Switching keeps your prompt and your pictures."
              wide
            />
            {iMenu && iPick ? (
              <ChipMenu
                name="Shape"
                open={menu === "dock-shape"}
                onOpen={() => setMenu(menu === "dock-shape" ? null : "dock-shape")}
                onClose={() => setMenu(null)}
                value={
                  <>
                    <Frame aspect={iPick.aspect} /> {iPick.aspect}
                  </>
                }
                items={(iModel?.aspects?.length ? iModel.aspects : iMenu.aspects).map((a) => ({ id: a, name: a, note: "", right: "", icon: <Frame aspect={a} /> }))}
                picked={iPick.aspect}
                onPick={(a) => setImage({ aspect: a })}
                title="Shape"
                shapes
              />
            ) : null}
            <span className="dg-grow" />
            <button type="submit" className="dg-go dgv-go" disabled={!canSend} data-busy={pricing || sending ? "1" : undefined}>
              {sending ? <span className="dg-spin sm" aria-hidden /> : <Wand2 strokeWidth={1.8} />}
              {goLabel}
            </button>
          </div>
        </form>
        {picker}
      </section>
    );
  }

  return (
    <section className={`view dg dgv ${cardFonts}`} data-over={over ? "1" : undefined} {...drop}>
      <div className="dgv-main">
        <Stage
          shown={shown}
          video
          onStarter={(t) => {
            setPrompt(t);
            promptEl.current?.focus();
          }}
          onReuse={reuse}
          onCancel={cancel}
        />

        <form
          className="dgv-dock"
          onSubmit={(e) => {
            e.preventDefault();
            void generate();
          }}
        >
          {picker}
          <div className="dgv-dock-top">
            {tray("sm")}
            <textarea
              ref={promptEl}
              className="dgv-prompt"
              value={prompt}
              maxLength={vModel?.prompt_max ?? 4000}
              rows={2}
              placeholder="Describe the clip: what moves, the camera, the light, the sound…"
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void generate();
                }
              }}
            />
          </div>
          {notes}
          {refMode === "references" && tags.length ? (
            <p className="dg-hint">The clip is held to these pictures. Name them in the prompt; tap a tag to put it there.</p>
          ) : null}
          <div className="dgv-dock-bar">
            <ChipMenu
              name="Model"
              open={menu === "model"}
              onOpen={() => setMenu(menu === "model" ? null : "model")}
              onClose={() => setMenu(null)}
              strong
              value={current?.label ?? (menuError ? "Unavailable" : "Loading…")}
              items={modelItems}
              picked={vPick?.model ?? ""}
              onPick={chooseModel}
              title={`${items.length} video models`}
              foot="Switching keeps your prompt. A length or frame the new model does not take moves to its own, and a line says so."
              wide
            />
            {vModel && vPick ? (
              <>
                <ChipMenu
                  name="Length"
                  open={menu === "length"}
                  onOpen={() => setMenu(menu === "length" ? null : "length")}
                  onClose={() => setMenu(null)}
                  value={`${vPick.seconds}s`}
                  items={lengths.map((s) => ({ id: String(s), name: `${s}s`, note: "", right: "" }))}
                  picked={String(vPick.seconds)}
                  onPick={(s) => setVideo({ seconds: Number(s) })}
                  title={`Length · ${lengths.length > 1 ? `${lengths[0]} to ${lengths[lengths.length - 1]} s` : `${lengths[0] ?? ""} s`}`}
                  foot="Every change is priced again before Generate shows a number."
                  disabled={lengths.length < 2}
                  scroll
                />
                <ChipMenu
                  name="Resolution"
                  open={menu === "res"}
                  onOpen={() => setMenu(menu === "res" ? null : "res")}
                  onClose={() => setMenu(null)}
                  value={vPick.resolution}
                  items={vModel.resolutions.map((r) => ({ id: r, name: r, note: "", right: "" }))}
                  picked={vPick.resolution}
                  onPick={(r) => setVideo({ resolution: r })}
                  title="Resolution"
                  disabled={vModel.resolutions.length < 2}
                />
                {hasStart ? (
                  <span className="dgv-follow">Frame follows the picture</span>
                ) : (
                  <ChipMenu
                    name="Frame"
                    open={menu === "frame"}
                    onOpen={() => setMenu(menu === "frame" ? null : "frame")}
                    onClose={() => setMenu(null)}
                    value={
                      <>
                        <Frame aspect={vPick.aspect} /> {vPick.aspect}
                      </>
                    }
                    items={vModel.aspects.map((a) => ({ id: a, name: a, note: "", right: "", icon: <Frame aspect={a} /> }))}
                    picked={vPick.aspect}
                    onPick={(a) => setVideo({ aspect: a })}
                    title="Frame"
                    disabled={vModel.aspects.length < 2}
                    shapes
                  />
                )}
                {refs.length === 1 && vCap > 1 ? (
                  <span className="dgv-use" role="radiogroup" aria-label="Use the picture as">
                    <button type="button" role="radio" aria-checked={!oneAsRef} onClick={() => setOneAsRef(false)}>
                      Start frame
                    </button>
                    <button type="button" role="radio" aria-checked={oneAsRef} onClick={() => setOneAsRef(true)}>
                      Reference
                    </button>
                  </span>
                ) : null}
              </>
            ) : null}
            <span className="dg-grow" />
            <span className="dg-count">
              {prompt.length.toLocaleString("en-US")} / {(vModel?.prompt_max ?? 4000).toLocaleString("en-US")}
            </span>
            <button type="submit" className="dg-go dgv-go" disabled={!canSend} data-busy={pricing || sending ? "1" : undefined}>
              {sending ? <span className="dg-spin sm" aria-hidden /> : <Wand2 strokeWidth={1.8} />}
              {goLabel}
            </button>
          </div>
        </form>
      </div>

      <History made={made} recent={recent} shownId={shownId} onShow={setShownId} video />
    </section>
  );
}

/* ── a frame's shape, drawn ── */
function Frame({ aspect }: { aspect: string }) {
  const [w, h] = aspect.split(":").map(Number);
  const big = 16;
  const ww = w >= h ? big : Math.round((big * w) / h);
  const hh = h >= w ? big : Math.round((big * h) / w);
  return <span className="dg-frame" style={{ width: ww || big, height: hh || big }} aria-hidden />;
}

export type MenuItem = { id: string; name: string; note: string; right: string; icon?: ReactNode };

function MenuList({ items, picked, onPick, title, foot, shapes, scroll }: {
  items: MenuItem[];
  picked: string;
  onPick: (id: string) => void;
  title?: string;
  foot?: string;
  shapes?: boolean;
  scroll?: boolean;
}) {
  return (
    <div className="dg-menu" role="listbox" aria-label={title} data-scroll={scroll ? "1" : undefined}>
      {title ? <span className="dg-menu-title">{title}</span> : null}
      {shapes ? (
        <div className="dg-menu-shapes">
          {items.map((m) => (
            <button key={m.id} type="button" role="option" aria-selected={m.id === picked} onClick={() => onPick(m.id)}>
              {m.icon}
              {m.name}
            </button>
          ))}
        </div>
      ) : (
        <div className="dg-menu-rows">
          {items.map((m) => (
            <button key={m.id} type="button" role="option" aria-selected={m.id === picked} onClick={() => onPick(m.id)}>
              <span className="dg-menu-name">
                <b>{m.name}</b>
                {m.note ? <small>{m.note}</small> : null}
              </span>
              {m.right ? <span className="dg-menu-right">{m.right}</span> : null}
              <span className="dg-menu-check">{m.id === picked ? <Check strokeWidth={2.4} /> : null}</span>
            </button>
          ))}
        </div>
      )}
      {foot ? <span className="dg-menu-foot">{foot}</span> : null}
    </div>
  );
}

/** The panel's model button: a dropdown that opens downward. (The Voice
 *  page's pickers are this button too.) */
export function ModelMenu(props: {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  label: string;
  sub: string;
  items: MenuItem[];
  picked: string;
  onPick: (id: string) => void;
  title: string;
  foot: string;
  disabled?: boolean;
}) {
  const box = useRef<HTMLDivElement>(null);
  useDismiss(box, props.open, props.onClose);
  return (
    <div className="dg-pop" ref={box}>
      <button type="button" className="dg-model" aria-haspopup="listbox" aria-expanded={props.open} onClick={props.onOpen} disabled={props.disabled}>
        <span className="dg-model-txt">
          <b>{props.label}</b>
          <small>{props.sub}</small>
        </span>
        <ChevronDown strokeWidth={1.8} className="dg-chev" />
      </button>
      {props.open ? (
        <div className="dg-pop-down">
          <MenuList items={props.items} picked={props.picked} onPick={props.onPick} title={props.title} foot={props.foot} />
        </div>
      ) : null}
    </div>
  );
}

/** A dock chip: its value, and a menu that opens upward. */
function ChipMenu(props: {
  name: string;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  value: ReactNode;
  items: MenuItem[];
  picked: string;
  onPick: (id: string) => void;
  title: string;
  foot?: string;
  strong?: boolean;
  disabled?: boolean;
  wide?: boolean;
  shapes?: boolean;
  scroll?: boolean;
}) {
  const box = useRef<HTMLDivElement>(null);
  useDismiss(box, props.open, props.onClose);
  return (
    <div className="dg-pop" ref={box}>
      <button
        type="button"
        className="dgv-chip"
        data-strong={props.strong ? "1" : undefined}
        aria-label={props.name}
        aria-haspopup="listbox"
        aria-expanded={props.open}
        onClick={props.onOpen}
        disabled={props.disabled}
      >
        {props.value}
        {props.disabled ? null : <ChevronDown strokeWidth={2} className="dg-chev" />}
      </button>
      {props.open ? (
        <div className="dg-pop-up" data-wide={props.wide ? "1" : undefined}>
          <MenuList items={props.items} picked={props.picked} onPick={props.onPick} title={props.title} foot={props.foot} shapes={props.shapes} scroll={props.scroll} />
        </div>
      ) : null}
    </div>
  );
}

/** Pictures from the Library (renders) or from Elements (their photos):
 *  pick several, then Add. Nothing is spent here. */
function PicturePicker({ room, note, onClose, onAdd }: { room: number; note: string; onClose: () => void; onAdd: (list: MediaItem[]) => void }) {
  const { toast } = useShell();
  const [tab, setTab] = useState<"stills" | "elements">("stills");
  const [lists, setLists] = useState<{ stills: MediaItem[] | null; elements: MediaItem[] | null }>({ stills: null, elements: null });
  const [chosen, setChosen] = useState<string[]>([]);
  const box = useRef<HTMLDivElement>(null);
  useDismiss(box, true, onClose);
  const list = lists[tab];
  useEffect(() => {
    if (lists[tab] !== null) return;
    const ask = tab === "stills" ? getMedia({ kind: "image" }) : getElementPhotos();
    ask
      .then((w) => setLists((l) => ({ ...l, [tab]: w.items.filter((m) => m.url) })))
      .catch(() => {
        setLists((l) => ({ ...l, [tab]: [] }));
        toast(tab === "stills" ? "The Library could not be read" : "Elements could not be read", "err");
      });
  }, [tab, lists, toast]);
  const everything = [...(lists.stills ?? []), ...(lists.elements ?? [])];
  const toggle = (id: string) =>
    setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : room <= 1 ? [id] : c.length >= room ? c : [...c, id]));
  return (
    <div className="dg-picker" ref={box} role="dialog" aria-label="Add pictures">
      <div className="dg-picker-head">
        <b>Add pictures</b>
        <span className="dg-grow" />
        <span className="dg-seg-pills" role="tablist">
          <button type="button" role="tab" aria-selected={tab === "stills"} onClick={() => setTab("stills")}>
            Library
          </button>
          <button type="button" role="tab" aria-selected={tab === "elements"} onClick={() => setTab("elements")}>
            Elements
          </button>
        </span>
        <button type="button" className="dg-icon" aria-label="Close" onClick={onClose}>
          <X strokeWidth={2} />
        </button>
      </div>
      {list === null ? (
        <p className="dg-hint">Loading…</p>
      ) : list.length ? (
        <ul className="dg-picker-grid">
          {list.slice(0, 60).map((m) => (
            <li key={m.asset_id}>
              <button
                type="button"
                aria-pressed={chosen.includes(m.asset_id)}
                onClick={() => toggle(m.asset_id)}
                title={m.prompt || m.asset_name}
              >
                <img src={mediaSrc(m.thumb ?? m.url)} alt="" loading="lazy" onError={toMaster(m.url)} />
                {chosen.includes(m.asset_id) ? (
                  <span className="dg-picked">
                    <Check strokeWidth={2.6} />
                  </span>
                ) : null}
                {tab === "elements" ? <span className="dg-picker-name">{m.asset_name}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="dg-hint">
          {tab === "stills" ? "No stills yet. What you make here lands in the Library." : <>No element photos yet. <Link href="/studio/elements">Add an element</Link>.</>}
        </p>
      )}
      <div className="dg-picker-foot">
        <p className="dg-hint">{room <= 0 ? "This model holds no more pictures." : note}</p>
        <span className="dg-grow" />
        <button
          type="button"
          className="dg-ok"
          disabled={!chosen.length}
          onClick={() => onAdd(chosen.map((id) => everything.find((m) => m.asset_id === id)).filter((m): m is MediaItem => !!m))}
        >
          {chosen.length ? `Add ${chosen.length}` : "Add"}
        </button>
      </div>
    </div>
  );
}

/** The stage (a still) or the theatre (a clip): what is being looked at,
 *  drawn, or what went wrong. */
function Stage({ shown, video, onStarter, onReuse, onCancel }: {
  shown: Shown | null;
  video: boolean;
  onStarter: (t: string) => void;
  onReuse: (s: Shown) => void;
  onCancel: (s: Shown) => void;
}) {
  if (!shown) {
    return (
      <div className="dg-stage" data-empty="1">
        <div className="dg-empty">
          <span className="dg-anton">{video ? "What you make plays here" : "What you make lands here"}</span>
          <p>
            {video
              ? "Text alone, one start frame, or several pictures held as references on the models that take them. Everything also lands in your Library."
              : "And in your Library, with everything else you have made. Nothing is drawn until Generate."}
          </p>
          <div className="dg-starters">
            {STARTERS[video ? "video" : "image"].map((s) => (
              <button key={s} type="button" onClick={() => onStarter(s)}>
                {s}
              </button>
            ))}
          </div>
          <small>A starter only fills the prompt.</small>
        </div>
      </div>
    );
  }
  const genId = /^gen:(\d+)$/.exec(shown.asset ?? "")?.[1];
  const toVesper = vesperHref(shown.asset, shown.label);
  return (
    <div className="dg-stage-wrap">
      <div className="dg-stage" data-status={shown.status}>
        {shown.status === "done" && shown.src ? (
          video ? (
            <video key={shown.src} src={mediaSrc(shown.src)} poster={shown.poster ? mediaSrc(shown.poster) : undefined} controls playsInline autoPlay muted loop />
          ) : (
            <img key={shown.src} src={mediaSrc(shown.src)} alt={shown.prompt} />
          )
        ) : (
          <div className="dg-wait">
            {shown.behind ? <img className="dg-wait-behind" src={mediaSrc(shown.behind)} alt="" /> : null}
            <div className="dg-wait-card">
              {shown.status === "running" ? <span className="dg-spin" aria-hidden /> : null}
              <b data-failed={shown.status === "failed" ? "1" : undefined}>
                {shown.status === "failed" ? "Not made" : shown.detail}
              </b>
              <p>
                {shown.status === "failed"
                  ? shown.detail
                  : video
                    ? `Clips take a few minutes. Leave the page and it keeps going; it lands here and in your Library.${shown.credits ? ` ${shown.credits.toLocaleString("en-US")} credits are held, and given back if it fails.` : ""}`
                    : `It lands here and in your Library.${shown.credits ? ` ${shown.credits.toLocaleString("en-US")} credits are held, and given back if it fails.` : ""}`}
              </p>
              <div className="dg-acts">
                {shown.status === "running" && shown.cancellable ? (
                  <button type="button" className="dg-btn" onClick={() => onCancel(shown)}>
                    Cancel
                  </button>
                ) : null}
                {shown.status === "failed" && shown.outOfCredits ? (
                  <Link className="dg-btn" href={TOP_UP_HREF}>
                    Add credits
                  </Link>
                ) : null}
                {shown.status === "failed" ? (
                  <button type="button" className="dg-btn" onClick={() => onReuse(shown)}>
                    <RotateCcw strokeWidth={1.8} /> Use these settings
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="dg-bar">
        {shown.label ? <span className="dg-chip">{shown.label}</span> : null}
        {shown.pick && "aspect" in shown.pick ? (
          <span className="dg-chip">
            <Frame aspect={shown.pick.aspect} /> {shown.pick.aspect}
          </span>
        ) : null}
        {shown.pick && "seconds" in shown.pick ? <span className="dg-chip">{shown.pick.seconds}s · {shown.pick.resolution}</span> : null}
        {shown.credits !== undefined ? (
          <span className="dg-chip">
            {shown.credits.toLocaleString("en-US")} credits{shown.status === "running" ? " held" : ""}
          </span>
        ) : null}
        <span className="dg-grow" />
        {shown.status === "done" ? (
          <>
            {shown.prompt ? (
              <button type="button" className="dg-btn" onClick={() => onReuse(shown)} title="Put this prompt and its settings back in the controls">
                <RotateCcw strokeWidth={1.8} /> Reuse settings
              </button>
            ) : null}
            {!video && shown.src ? (
              <Link className="dg-btn" href={`${directHref("video")}?start=${encodeURIComponent(shown.src)}`} title="Make a clip that starts on this still">
                <Clapperboard strokeWidth={1.8} /> Animate
              </Link>
            ) : null}
            {toVesper ? (
              <Link className="dg-btn" href={toVesper} title="Opens Create with this attached">
                <Wand2 strokeWidth={1.8} /> Use in Create
              </Link>
            ) : null}
            {genId ? (
              <Link className="dg-btn" href={`/studio/assets?open=${genId}`}>
                <LayoutGrid strokeWidth={1.8} /> Open in Library
              </Link>
            ) : null}
            {genId ? (
              <a className="dg-icon" href={renderDownloadHref(Number(genId))} download title="Download" aria-label="Download">
                <Download strokeWidth={1.8} />
              </a>
            ) : null}
          </>
        ) : null}
      </div>
      {shown.prompt ? <p className="dg-stage-prompt">{shown.prompt}</p> : null}
    </div>
  );
}

/** This visit's makes, then the Library's newest of this kind. A click puts
 *  one on the stage; nothing here navigates away. */
function History({ made, recent, shownId, onShow, video }: {
  made: Shown[];
  recent: Shown[];
  shownId: string | null;
  onShow: (id: string) => void;
  video?: boolean;
}) {
  const tile = (s: Shown) => (
    <li key={s.id}>
      <button type="button" className="dg-hist" aria-pressed={s.id === shownId} onClick={() => onShow(s.id)} title={s.prompt || s.label}>
        {s.status === "done" && s.src ? (
          s.kind === "video" ? (
            <video
              src={mediaSrc(s.src)}
              poster={s.poster ? mediaSrc(s.poster) : undefined}
              muted
              loop
              playsInline
              preload="metadata"
              onMouseEnter={(e) => void e.currentTarget.play().catch(() => {})}
              onMouseLeave={(e) => e.currentTarget.pause()}
            />
          ) : (
            <img src={mediaSrc(s.thumb ?? s.src)} alt="" loading="lazy" onError={toMaster(s.src)} />
          )
        ) : (
          <span className="dg-hist-wait" data-failed={s.status === "failed" ? "1" : undefined}>
            {s.status === "running" ? <span className="dg-spin sm" aria-hidden /> : "not made"}
          </span>
        )}
      </button>
    </li>
  );
  return (
    <aside className="dg-history" data-video={video ? "1" : undefined} aria-label="Made on this visit and in your Library">
      {made.length ? (
        <>
          <span className="dg-lab">This visit</span>
          <ul>{made.map(tile)}</ul>
          <span className="dg-rule" />
        </>
      ) : null}
      <span className="dg-lab">Library</span>
      {recent.length ? <ul>{recent.map(tile)}</ul> : <p className="dg-hint">Nothing yet.</p>}
      <Link className="dg-hist-more" href="/studio/assets">
        Open the Library
      </Link>
    </aside>
  );
}
