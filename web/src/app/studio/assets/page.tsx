"use client";

/* Assets — the GENERATED media wall (2026-09-18, Mike's call: Assets are
   the content the studio generated; Elements are the characters, props
   and places a scene is held to -- two things, not four chips on one
   wall). Every render as a date-grouped wall, newest day first, off
   /api/media?kind=all&scope=generated -- one row per clip or still
   carrying its provider, prompt, folder and star. You can view them,
   organize them (Images / Clips / Starred / your own folders, a provider
   filter) and delete them -- a SOFT delete: the render leaves the wall
   and the RAG shelf, the file stays, and a concept whose shot already
   carries the clip keeps it. "Make element" is the bridge to the other
   side: a still becomes a character / prop / place with that frame as
   its first photo (the "Create Element" move).

   2026-10-19 (Mike's call, mockup "Assets Viewer Mockup"): a render opens
   in the full-screen viewer (components/studio/asset-viewer.tsx), not the
   old 360px rail, and the wall keeps every render's own shape -- justified
   rows of the 480px thumbnails instead of square crops of the 2K masters.
   The slider's five stops are row heights now. */
/* eslint-disable @next/next/no-img-element */
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { Film, Folder, Search, Sparkles, Star, Trash2 } from "lucide-react";
import { API_URL } from "@/lib/api";
import {
  deleteGenerated,
  restoreGenerated,
  getMedia,
  getTrash,
  organizeGenerated,
  type MediaFilter,
  type MediaItem,
  type MediaWall,
} from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { AddElement } from "@/components/studio/add-element";
import { AssetViewer, modelName } from "@/components/studio/asset-viewer";
import { UrlParams } from "@/components/studio/url-params";
import { TrashView } from "@/components/studio/trash-view";

type Chip = { id: string; label: string; count: number; filter: MediaFilter; icon?: "folder" | "star" | "trash" };
// a row's height at each stop; a phone draws them at PHONE_SCALE
const STEPS = [
  { h: 96, label: "XS" },
  { h: 140, label: "S" },
  { h: 200, label: "M" },
  { h: 300, label: "L" },
  { h: 460, label: "XL" },
];
const PHONE_SCALE = 0.62;

/* each render's width/height, learned from its tile the first time it
   draws (the API carries no dimensions) and remembered per browser, so a
   wall seen before lays out in its real shapes from the first frame */
const RATIO_KEY = "zp.asset-ratios.v1";
const readRatios = (): Record<string, number> => {
  try {
    return JSON.parse(window.localStorage.getItem(RATIO_KEY) || "{}");
  } catch {
    return {};
  }
};
const saveRatios = (r: Record<string, number>) => {
  try {
    // the newest 600 are plenty; an old wall re-learns as it draws
    const keys = Object.keys(r);
    const keep = keys.length > 600 ? Object.fromEntries(keys.slice(-600).map((k) => [k, r[k]])) : r;
    window.localStorage.setItem(RATIO_KEY, JSON.stringify(keep));
  } catch {
    /* private mode / quota: the wall still draws, it just re-learns */
  }
};
const ratioKey = (url: string) => url.split("?")[0];
const DATE_FMT = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "long", day: "numeric" });
const dateLabel = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return DATE_FMT.format(new Date(y, m - 1, d));
};
const EMPTY: MediaWall = { items: [], counts: { all: 0 }, wall: { image: 0, video: 0, starred: 0 }, folders: {}, providers: {} };

/* the phone breakpoint, as studio.css draws it (2026-10-19): the viewer is
   a bottom sheet there and the desktop rail everywhere else, and the motion
   has to follow the CSS, so the page asks the same query */
const PHONE = "(max-width: 720px)";
const subscribePhone = (cb: () => void) => {
  const mq = window.matchMedia(PHONE);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
};
const usePhone = () =>
  useSyncExternalStore(
    subscribePhone,
    () => window.matchMedia(PHONE).matches,
    () => false,
  );
const typing = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));

export default function AssetsPage() {
  const { toast } = useShell();
  const [chip, setChip] = useState("all");
  const [provider, setProvider] = useState("");
  const [query, setQuery] = useState("");
  const [step, setStep] = useState(2);
  const phone = usePhone();
  const [wall, setWall] = useState<MediaWall | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<MediaItem | null>(null);
  const [making, setMaking] = useState<MediaItem | null>(null);
  // the Trash chip's count (2026-10-20): read on its own, the wall's
  // totals never include deleted renders
  const [trashCount, setTrashCount] = useState(0);
  const countTrash = () =>
    getTrash()
      .then((r) => setTrashCount(r.items.length))
      .catch(() => {});
  useEffect(() => {
    countTrash();
    // Settings' storage bar links here as /studio/assets#trash
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (typeof window !== "undefined" && window.location.hash === "#trash") setChip("trash");
  }, []);
  const track = useRef<HTMLDivElement>(null);
  const [ratios, setRatios] = useState<Record<string, number>>({});
  useEffect(() => {
    // read after mount: the server render has no localStorage
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRatios(readRatios());
  }, []);
  const learnRatio = (url: string, w: number, h: number) => {
    if (!w || !h) return;
    const r = Math.round((w / h) * 1000) / 1000;
    const k = ratioKey(url);
    setRatios((all) => {
      if (all[k] === r) return all;
      const next = { ...all, [k]: r };
      saveRatios(next);
      return next;
    });
  };

  // the chips are derived from the set totals, so a folder appears the
  // moment a render lands in it and disappears when the last one leaves
  const chips: Chip[] = useMemo(() => {
    const w = wall ?? EMPTY;
    const out: Chip[] = [
      { id: "all", label: "All", count: w.counts.all, filter: {} },
      { id: "image", label: "Images", count: w.wall.image, filter: { kind: "image" } },
      { id: "video", label: "Clips", count: w.wall.video, filter: { kind: "video" } },
      { id: "starred", label: "Starred", count: w.wall.starred, filter: { starred: true }, icon: "star" },
    ];
    for (const [name, count] of Object.entries(w.folders)) {
      out.push({ id: `folder:${name}`, label: name, count, filter: { folder: name }, icon: "folder" });
    }
    out.push({ id: "trash", label: "Trash", count: trashCount, filter: {}, icon: "trash" });
    return out;
  }, [wall, trashCount]);
  const active = chips.find((c) => c.id === chip) ?? chips[0];

  const show = (m: MediaItem | null) => setOpen(m);
  // a render a deep link asked for (?open=<generated id>, the ⌘K palette):
  // opened in the viewer as soon as a loaded wall holds it
  const router = useRouter();
  const wantRef = useRef<number | null>(null);
  const openWanted = (list: MediaItem[]) => {
    const id = wantRef.current;
    if (id === null) return;
    const hit = list.find((m) => m.generated_id === id);
    if (hit) {
      wantRef.current = null;
      show(hit);
    }
  };

  const load = (q = query, c = active, p = provider) => {
    getMedia({ ...c.filter, q: q.trim() || undefined, provider: p || undefined })
      .then((r) => {
        setWall(r);
        setError(null);
        openWanted(r.items);
        // a folder chip whose last render moved out falls back to All
        if (c.filter.folder && !(c.filter.folder in r.folders)) setChip("all");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Media unavailable"));
  };
  // an Undo pressed later reloads the wall under the filters showing then,
  // not the ones showing when the render was removed
  const latestLoad = useRef(() => load());
  useEffect(() => {
    latestLoad.current = () => load();
  });
  useEffect(() => {
    const timer = setTimeout(() => load(query, active, provider), query ? 220 : 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, chip, provider]);
  const items = wall?.items ?? null;
  const groups = useMemo(() => {
    const out: { date: string; items: MediaItem[] }[] = [];
    for (const item of items || []) {
      const last = out[out.length - 1];
      if (last && last.date === item.date) last.items.push(item);
      else out.push({ date: item.date, items: [item] });
    }
    return out;
  }, [items]);

  // one place patches the open item, the wall row and the server
  const patchOpen = (id: number, body: { folder?: string; starred?: boolean }) =>
    organizeGenerated(id, body)
      .then((r) => {
        const apply = (m: MediaItem) => (m.generated_id === id ? { ...m, folder: r.folder, starred: r.starred } : m);
        setOpen((o) => (o ? apply(o) : o));
        setWall((w) => (w ? { ...w, items: w.items.map(apply) } : w));
        load();
        return r;
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not save", "err"));

  const remove = (m: MediaItem) => {
    if (!m.generated_id) return;
    deleteGenerated(m.generated_id)
      .then(() => {
        show(null);
        setWall((w) => (w ? { ...w, items: w.items.filter((x) => x.generated_id !== m.generated_id) } : w));
        toast(`${modelName(m)} moved to the Trash · restore it there within 7 days`, "ok", {
          // the delete is a move to the trash, so Undo is the server's own inverse
          action: {
            label: "Undo",
            run: () =>
              restoreGenerated(m.generated_id!).then(() => {
                latestLoad.current();
                countTrash();
                toast(`${modelName(m)} is back on the wall`);
              }),
          },
        });
        load();
        countTrash();
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Could not delete", "err"));
  };

  const pickStop = (clientX: number) => {
    const el = track.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const pad = 34;
    const t = Math.min(1, Math.max(0, (clientX - (r.left + pad)) / (r.width - pad * 1.6)));
    setStep(Math.round(t * (STEPS.length - 1)));
  };
  // pointer events, so a finger drags it as a mouse does (2026-10-19); the
  // capture keeps a drag that leaves the track following it, as the window
  // listeners did
  const onSliderDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pickStop(e.clientX);
  };
  const onSliderMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) pickStop(e.clientX);
  };
  const onSliderUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  // previous / next through the wall as it is filtered now; `open` stays
  // the one source of truth, a step is just show() on a neighbour
  const at = open && items ? items.findIndex((m) => m.url === open.url) : -1;
  const prev = at > 0 && items ? items[at - 1] : null;
  const next = at >= 0 && items && at < items.length - 1 ? items[at + 1] : null;
  const stepTo = useRef<(d: -1 | 1) => void>(() => {});
  useEffect(() => {
    stepTo.current = (d) => {
      const m = d < 0 ? prev : next;
      if (m) show(m);
    };
  });
  // Escape closes, the arrows step; never while typing (the folder box) or
  // while the Make element form is up over the viewer
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (making || e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return;
      if (e.key === "Escape") show(null);
      else if (e.key === "ArrowLeft") stepTo.current(-1);
      else if (e.key === "ArrowRight") stepTo.current(1);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, making]);
  // the viewer covers the whole page, so the wall behind must not scroll
  // under the wheel or the finger
  const isOpen = !!open;
  useEffect(() => {
    if (!isOpen) return;
    const root = document.documentElement;
    const was = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = was;
    };
  }, [isOpen]);
  // the neighbours' full-size stills start loading while this one is
  // looked at, so an arrow press lands on a picture, not a blank stage
  const prevUrl = prev?.kind === "image" ? prev.url : null;
  const nextUrl = next?.kind === "image" ? next.url : null;
  useEffect(() => {
    for (const u of [prevUrl, nextUrl]) if (u) new Image().src = `${API_URL}${u}`;
  }, [prevUrl, nextUrl]);

  const shown = items?.length ?? 0;
  const total = wall?.counts.all ?? 0;
  const countLine = items ? `${shown}${shown !== total ? ` of ${total}` : ""} render${total === 1 ? "" : "s"}` : "loading…";
  const providers = Object.entries(wall?.providers ?? {});

  return (
    <section className="view" style={{ paddingTop: 0 }}>
      <UrlParams
        onParams={(params) => {
          const id = Number(params.get("open"));
          if (!id) return;
          wantRef.current = id;
          // nothing may hide it: the filters go back to the whole wall (a
          // change reloads it, and the load opens it); on the whole wall
          // already, it opens from what is drawn
          setChip("all");
          setQuery("");
          setProvider("");
          if (wall) openWanted(wall.items);
          router.replace("/studio/assets", { scroll: false });
        }}
      />
      <div className="vhead" style={{ marginTop: 8, flexWrap: "wrap" }}>
        <h2>Assets</h2>
        <label className="asearch">
          <Search size={14} strokeWidth={1.7} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search prompts…" aria-label="Search generated assets" />
        </label>
        <span className="m">{countLine}</span>
        <span className="spacer" />
        {providers.length > 1 ? (
          <select className="zin" value={provider} onChange={(e) => setProvider(e.target.value)} aria-label="Provider" style={{ width: "auto" }}>
            <option value="">Every provider</option>
            {providers.map(([name, n]) => (
              <option key={name} value={name}>
                {name} · {n}
              </option>
            ))}
          </select>
        ) : null}
        <div
          ref={track}
          className="azoom"
          role="slider"
          aria-label="Tile size"
          aria-valuemin={1}
          aria-valuemax={STEPS.length}
          aria-valuenow={step + 1}
          title={`Tile size · ${STEPS[step].label}`}
          onPointerDown={onSliderDown}
          onPointerMove={onSliderMove}
          onPointerUp={onSliderUp}
          onPointerCancel={onSliderUp}
        >
          <Search size={13} strokeWidth={1.7} />
          <span className="aztrack">
            <span className="azknob" style={{ left: `${(step / (STEPS.length - 1)) * 100}%` }} />
          </span>
          <span className="m">{STEPS[step].label}</span>
        </div>
      </div>

      <div className="cats acats">
        {chips.map((c) => (
          <button type="button" key={c.id} className="cat" aria-pressed={chip === c.id} onClick={() => setChip(c.id)}>
            {c.icon === "folder" ? <Folder size={11} strokeWidth={1.7} className="mr-1.5 inline-block align-[-1px]" /> : null}
            {c.icon === "star" ? <Star size={11} strokeWidth={1.7} className="mr-1.5 inline-block align-[-1px]" /> : null}
            {c.icon === "trash" ? <Trash2 size={11} strokeWidth={1.7} className="mr-1.5 inline-block align-[-1px]" /> : null}
            {c.label}
            <u>{c.count}</u>
          </button>
        ))}
      </div>

      {error ? <div className="stateline err astate">{error}</div> : null}

      {chip === "trash" ? (
        <TrashView
          toast={toast}
          onChange={() => {
            countTrash();
            load();
          }}
        />
      ) : null}
      <div className="wall" hidden={chip === "trash"}>
        {items && !items.length ? (
          <p className="stateline astate">
            {total ? "Nothing matches — clear the search or pick another chip" : "No renders yet — an image made in Create, or the keyframes and clips you render from a scene, land here"}
          </p>
        ) : null}
        {groups.map((g) => (
          <div key={g.date} className="wgroup">
            <div className="wdate">
              <span>{dateLabel(g.date)}</span>
              <span className="m">
                {g.items.length} item{g.items.length === 1 ? "" : "s"}
              </span>
            </div>
            {/* justified rows (2026-10-19): a tile's grow and basis are both
                its width/height ratio, so every tile in a row scales by the
                same factor and the row shares one height; the last row keeps
                the stop's height (the filler takes its slack) */}
            <div className="wgrid jrows" style={{ ["--rowh" as string]: `${Math.round(STEPS[step].h * (phone ? PHONE_SCALE : 1))}px` }}>
              <AnimatePresence initial={false}>
                {g.items.map((m) => {
                  const ar = ratios[ratioKey(m.url)] ?? 1;
                  const still = m.kind === "image" ? `${API_URL}${m.thumb || m.url}` : null;
                  return (
                  <motion.button
                    layout
                    initial={{ opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.94 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    type="button"
                    key={m.url}
                    className={`wtile${m.kind === "video" ? " video" : ""}${open?.url === m.url ? " on" : ""}`}
                    aria-label={`${modelName(m)} · ${m.kind === "video" ? "clip" : "still"}`}
                    style={{ ["--ar" as string]: ar }}
                    onClick={() => show(m)}
                    // a mouse only: a tap fires an emulated enter and no leave,
                    // which left a phone's tile playing behind the viewer
                    onPointerEnter={(e) => {
                      if (e.pointerType === "mouse") e.currentTarget.querySelector("video")?.play().catch(() => {});
                    }}
                    onPointerLeave={(e) => {
                      if (e.pointerType !== "mouse") return;
                      const v = e.currentTarget.querySelector("video");
                      if (v) {
                        v.pause();
                        v.currentTime = 0;
                      }
                    }}
                  >
                    {still ? (
                      // the 480px thumbnail; a render made before thumbnails
                      // (or with R2 off) falls back to its master, once
                      <img
                        src={still}
                        alt=""
                        loading="lazy"
                        decoding="async"
                        draggable={false}
                        onLoad={(e) => learnRatio(m.url, e.currentTarget.naturalWidth, e.currentTarget.naturalHeight)}
                        onError={(e) => {
                          const img = e.currentTarget;
                          const master = `${API_URL}${m.url}`;
                          if (img.src !== new URL(master, window.location.href).href) img.src = master;
                        }}
                      />
                    ) : (
                      // #t=0.5 makes Safari draw a frame instead of a dark box
                      // when a clip has no poster yet (renders before 2026-09-28)
                      <video
                        src={`${API_URL}${m.url}#t=0.5`}
                        poster={m.poster ? `${API_URL}${m.poster}` : undefined}
                        muted
                        loop
                        playsInline
                        preload="metadata"
                        // a cached clip can have its metadata before React
                        // listens, so the mount asks as well as the event
                        ref={(v) => {
                          if (v && v.readyState >= 1) learnRatio(m.url, v.videoWidth, v.videoHeight);
                        }}
                        onLoadedMetadata={(e) => learnRatio(m.url, e.currentTarget.videoWidth, e.currentTarget.videoHeight)}
                      />
                    )}
                    {m.starred ? <Star size={11} strokeWidth={2} className="absolute top-2 right-2 fill-current text-[var(--signal)]" /> : null}
                    <span className="wname">
                      {m.kind === "video" ? <Film size={11} strokeWidth={1.6} /> : <Sparkles size={11} strokeWidth={1.6} />}
                      <span>
                        {modelName(m)}
                        {m.folder ? ` · ${m.folder}` : ""}
                      </span>
                    </span>
                  </motion.button>
                  );
                })}
              </AnimatePresence>
              <span className="jfill" aria-hidden />
            </div>
          </div>
        ))}
      </div>

      <AnimatePresence>
        {open ? (
          <AssetViewer
            key="viewer"
            item={open}
            index={at + 1}
            total={items?.length ?? 0}
            hasPrev={!!prev}
            hasNext={!!next}
            onStep={(d) => stepTo.current(d)}
            onClose={() => show(null)}
            phone={phone}
            folders={Object.keys(wall?.folders ?? {})}
            onStar={() => open.generated_id && patchOpen(open.generated_id, { starred: !open.starred })}
            onFolder={(f) => {
              if (!open.generated_id) return;
              patchOpen(open.generated_id, { folder: f }).then((r) => (r ? toast(r.folder ? `moved to ${r.folder}` : "taken out of its folder") : null));
            }}
            onRemove={() => remove(open)}
            onMakeElement={() => setMaking(open)}
            onCopied={(ok) => toast(ok ? "prompt copied" : "Could not copy — select the text instead", ok ? "ok" : "err")}
          />
        ) : null}
      </AnimatePresence>

      {making ? (
        <AddElement
          title="Make element"
          initialPhotoUrls={[making.url]}
          initialNotes={making.prompt ?? ""}
          onClose={() => setMaking(null)}
          onSaved={(name, photos, note, sheetJob) => {
            setMaking(null);
            toast(
              `${name} saved as an element · ${photos} photo${photos === 1 ? "" : "s"}${sheetJob ? " · drawing its sheet" : ""}${note ? ` · ${note}` : ""}`,
            );
          }}
        />
      ) : null}
    </section>
  );
}
