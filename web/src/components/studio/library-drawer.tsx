"use client";

/* The Library drawer (2026-10-26, concept A of the picker concepts: Runway's
   Media drawer, Mike's pick). The ONE way a studio door picks from what the
   person has made: a panel that slides in over the right of the page, with
   tabs (Library, Elements), pills (All / Stills / Clips / Starred), search
   and folders over a masonry wall of tiles at their real shape; the first
   tile drops or uploads a file through the door's own upload. A door that
   takes several picks numbers them in click order (the first anchors the
   look) and adds them with one button; a door that takes one closes on the
   click. Rules live in lib/library-drawer.ts.

   Base UI mounts it on <body>, outside the studio wrapper, so every colour
   is a :root palette token and the faces come from the root layout's font
   variables, as the palette (command-palette.tsx) does. */

import {
  Children,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type ReactNode,
  type SyntheticEvent,
} from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Check, FolderOpen, Search, Star, Upload, X } from "lucide-react";
import { mediaSrc } from "@/lib/composer";
import {
  PAGE,
  PILL_LABEL,
  addLabel,
  folders as foldersOf,
  keyOf,
  numberOf,
  pills,
  tileSrc,
  tileTag,
  toggle,
  visible,
  type Accept,
  type Show,
  type Tab,
} from "@/lib/library-drawer";
import { getElementPhotos, getMedia, type MediaItem } from "@/lib/studio-api";
import "@/components/studio/library-drawer.css";
/* eslint-disable @next/next/no-img-element */

export type LibraryDrawerProps = {
  open: boolean;
  onClose: () => void;
  /** what the door takes */
  accept: Accept;
  /** how many it may add in one go; 1 picks on the click */
  max: number;
  /** what one pick is called on the button ("reference", "start frame") */
  noun?: string;
  /** the line beside the count in the footer */
  note?: string;
  /** the picks, in the order they were clicked */
  onPick: (items: MediaItem[]) => void;
  /** files dropped or chosen in the drawer go to the door's own upload;
   *  without it there is no drop tile */
  onFiles?: (files: File[]) => void;
  /** offer the Elements tab (element photos, sent by their address) */
  elements?: boolean;
};

export function LibraryDrawer(props: LibraryDrawerProps) {
  const { open, onClose } = props;
  // the body mounts with the popup, so each open starts clean: the Library
  // tab, nothing picked, the list read fresh (a render made since is on it)
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="lbd-backdrop" />
        <Dialog.Popup className="lbd">
          <Dialog.Title className="lbd-sr">Pick from your Library</Dialog.Title>
          <Body {...props} />
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Body({
  onClose,
  accept,
  max,
  noun = "reference",
  note,
  onPick,
  onFiles,
  elements = false,
}: LibraryDrawerProps) {
  const [tab, setTab] = useState<Tab>("library");
  const [show, setShow] = useState<Show>("all");
  const [folder, setFolder] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Record<Tab, MediaItem[] | null>>({
    library: null,
    elements: null,
  });
  const [failed, setFailed] = useState<Record<Tab, boolean>>({
    library: false,
    elements: false,
  });
  const [picked, setPicked] = useState<string[]>([]);
  const [count, setCount] = useState(PAGE);
  const [over, setOver] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const more = useRef<HTMLDivElement>(null);
  // how many columns the wall has room for; tiles are dealt across them in
  // order, so the newest run along the top row as on Runway's drawer (CSS
  // columns would run them down the first column instead)
  const [cols, setCols] = useState(4);
  useEffect(() => {
    const el = grid.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      const w = e.contentRect.width;
      const min = w < 560 ? 120 : 160;
      setCols(Math.max(2, Math.floor((w + 8) / (min + 8))));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let live = true;
    getMedia(accept === "any" ? {} : { kind: accept })
      .then((w) => live && setRows((r) => ({ ...r, library: w.items })))
      .catch(() => live && setFailed((f) => ({ ...f, library: true })));
    return () => {
      live = false;
    };
  }, [accept]);

  // the Elements tab reads its photos on the first visit
  useEffect(() => {
    if (tab !== "elements" || rows.elements) return;
    let live = true;
    getElementPhotos()
      .then((w) => live && setRows((r) => ({ ...r, elements: w.items })))
      .catch(() => live && setFailed((f) => ({ ...f, elements: true })));
    return () => {
      live = false;
    };
  }, [tab, rows.elements]);

  const all = rows[tab];
  const shown = useMemo(
    () => (all ? visible(all, accept, tab, { show, folder, q }) : []),
    [all, accept, tab, show, folder, q],
  );
  const folderList = useMemo(
    () => (all && tab === "library" ? foldersOf(all, accept, tab) : []),
    [all, accept, tab],
  );
  const byKey = useMemo(() => {
    const m = new Map<string, MediaItem>();
    for (const list of [rows.library, rows.elements])
      for (const r of list ?? []) m.set(keyOf(r), r);
    return m;
  }, [rows]);

  // a new filter starts the wall at its top, one page long (called from
  // the handlers only, never during render)
  const restart = () => {
    setCount(PAGE);
    grid.current?.scrollTo({ top: 0 });
  };

  // the next page when the end of the wall scrolls into view
  useEffect(() => {
    const el = more.current;
    if (!el || !grid.current) return;
    const io = new IntersectionObserver(
      (seen) => seen.some((s) => s.isIntersecting) && setCount((c) => c + PAGE),
      {
        root: grid.current,
        rootMargin: "400px",
      },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [shown.length, count]);

  const full = picked.length >= max;
  const click = (r: MediaItem) => {
    const k = keyOf(r);
    if (max === 1) {
      onPick([r]);
      onClose();
      return;
    }
    setPicked((p) => toggle(p, k, max));
  };
  const add = () => {
    const items = picked
      .map((k) => byKey.get(k))
      .filter((r): r is MediaItem => !!r);
    if (!items.length) return;
    onPick(items);
    onClose();
  };
  const take = (list: FileList | null | undefined) => {
    const files = Array.from(list ?? []);
    if (!files.length || !onFiles) return;
    onFiles(files);
    onClose();
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    take(e.dataTransfer.files);
  };
  // a named thumbnail that is not there falls back to the master, once;
  // a master that fails too leaves a quiet tile, never a broken image
  const fallBack = (r: MediaItem) => (e: SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    const master =
      r.kind === "video"
        ? ""
        : new URL(mediaSrc(r.url), window.location.href).href;
    if (master && img.src !== master) img.src = master;
    else img.dataset.failed = "1";
  };

  const tabs: { id: Tab; label: string; n: number | null }[] = [
    {
      id: "library",
      label: "Library",
      n: rows.library
        ? visible(rows.library, accept, "library", {
            show: "all",
            folder: "",
            q: "",
          }).length
        : null,
    },
    ...(elements
      ? [
          {
            id: "elements" as Tab,
            label: "Elements",
            n: rows.elements ? rows.elements.length : null,
          },
        ]
      : []),
  ];
  const takes =
    accept === "image"
      ? "Stills only"
      : accept === "video"
        ? "Clips only"
        : "Stills or clips";

  return (
    <div
      className="lbd-body"
      data-over={over ? "1" : undefined}
      onDragOver={
        onFiles
          ? (e) => {
              e.preventDefault();
              setOver(true);
            }
          : undefined
      }
      onDragLeave={
        onFiles
          ? (e) => e.currentTarget === e.target && setOver(false)
          : undefined
      }
      onDrop={onFiles ? onDrop : undefined}
    >
      <div className="lbd-head">
        <div className="lbd-tabs" role="tablist" aria-label="What to pick from">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className="lbd-tab"
              onClick={() => {
                setTab(t.id);
                restart();
              }}
            >
              {t.label}
              {t.n != null ? <span>{t.n}</span> : null}
            </button>
          ))}
        </div>
        <Dialog.Close className="lbd-icon" aria-label="Close the Library">
          <X strokeWidth={2} />
        </Dialog.Close>
      </div>

      <div className="lbd-tools">
        <div className="lbd-pills" role="group" aria-label="Show">
          {pills(accept, tab).length > 1 &&
            pills(accept, tab).map((p) => (
              <button
                key={p}
                type="button"
                aria-pressed={show === p}
                onClick={() => {
                  setShow(p);
                  restart();
                }}
              >
                {p === "starred" ? (
                  <Star strokeWidth={1.8} aria-hidden="true" />
                ) : null}
                {PILL_LABEL[p]}
              </button>
            ))}
        </div>
        <span className="lbd-takes">{takes}</span>
        <label className="lbd-search">
          <Search strokeWidth={1.8} aria-hidden="true" />
          <input
            type="search"
            value={q}
            placeholder={
              tab === "elements"
                ? "Search elements"
                : "Search prompts and models"
            }
            aria-label="Search"
            onChange={(e) => {
              setQ(e.target.value);
              restart();
            }}
          />
        </label>
        {folderList.length ? (
          <label className="lbd-folder">
            <FolderOpen strokeWidth={1.8} aria-hidden="true" />
            <select
              value={folder}
              aria-label="Folder"
              onChange={(e) => {
                setFolder(e.target.value);
                restart();
              }}
            >
              <option value="">All folders</option>
              {folderList.map(([name, n]) => (
                <option key={name} value={name}>
                  {name} · {n}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="lbd-wall" ref={grid}>
        {failed[tab] ? (
          <p className="lbd-empty">
            {tab === "elements" ? "Your elements" : "Your Library"} could not be
            read. Close and try again.
          </p>
        ) : !all ? (
          <Wall cols={cols} busy>
            {Array.from({ length: 10 }, (_, i) => (
              <div
                key={i}
                className="lbd-skel"
                style={{
                  aspectRatio:
                    i % 3 === 0 ? "9 / 16" : i % 3 === 1 ? "4 / 5" : "1 / 1",
                }}
              />
            ))}
          </Wall>
        ) : (
          <Wall cols={cols}>
            {onFiles && tab === "library" ? (
              <button
                key="drop"
                type="button"
                className="lbd-drop"
                onClick={() => file.current?.click()}
              >
                <Upload strokeWidth={1.6} aria-hidden="true" />
                <b>{over ? "Let go to add" : "Drop or upload"}</b>
                <span>
                  {accept === "video"
                    ? "A video file"
                    : accept === "image"
                      ? "An image file"
                      : "Image or video"}
                </span>
              </button>
            ) : null}
            {shown.slice(0, count).map((r) => {
              const k = keyOf(r);
              const n = numberOf(picked, k);
              const blocked = !n && full && max > 1;
              const src = tileSrc(r);
              const tag = tileTag(r);
              return (
                <button
                  key={k}
                  type="button"
                  className="lbd-tile"
                  data-picked={n ? "1" : undefined}
                  data-blocked={blocked ? "1" : undefined}
                  aria-pressed={max > 1 ? !!n : undefined}
                  title={
                    blocked
                      ? `This takes up to ${max}`
                      : r.prompt || r.asset_name || ""
                  }
                  aria-label={`${r.kind === "video" ? "Clip" : "Still"}${tag ? `, ${tag}` : ""}${n ? `, picked ${n}` : ""}`}
                  onClick={() => !blocked && click(r)}
                >
                  {src ? (
                    <img
                      src={mediaSrc(src)}
                      alt=""
                      loading="lazy"
                      decoding="async"
                      onError={fallBack(r)}
                    />
                  ) : (
                    <span className="lbd-noposter">Clip</span>
                  )}
                  {n ? <span className="lbd-num">{n}</span> : null}
                  {r.starred ? (
                    <Star
                      className="lbd-star"
                      strokeWidth={2}
                      aria-hidden="true"
                    />
                  ) : null}
                  {tag ? <span className="lbd-tag">{tag}</span> : null}
                </button>
              );
            })}
          </Wall>
        )}
        {all && !failed[tab] && !shown.length ? (
          <p className="lbd-empty">
            {all.length
              ? "Nothing here matches. Try another filter."
              : tab === "elements"
                ? "No elements yet. Add one on Elements."
                : "Nothing in your Library yet. What you make lands here."}
          </p>
        ) : null}
        {shown.length > count ? (
          <div ref={more} className="lbd-more" aria-hidden="true" />
        ) : null}
      </div>

      {max > 1 ? (
        <div className="lbd-foot">
          <span className="lbd-count">
            {picked.length ? `${picked.length} picked` : `Pick up to ${max}`}
          </span>
          {note ? <span className="lbd-note">{note}</span> : null}
          {picked.length ? (
            <button
              type="button"
              className="lbd-btn"
              onClick={() => setPicked([])}
            >
              Clear
            </button>
          ) : null}
          <button
            type="button"
            className="lbd-btn primary"
            disabled={!picked.length}
            onClick={add}
          >
            <Check strokeWidth={2} aria-hidden="true" />
            {addLabel(picked.length, noun)}
          </button>
        </div>
      ) : null}

      {onFiles ? (
        <input
          ref={file}
          type="file"
          hidden
          multiple={max > 1}
          accept={
            accept === "video"
              ? "video/*"
              : accept === "image"
                ? "image/*"
                : "image/*,video/*"
          }
          onChange={(e) => {
            take(e.target.files);
            e.target.value = "";
          }}
        />
      ) : null}
    </div>
  );
}

/** the wall's columns: children dealt across them in order, the first
 *  child (the drop tile) top left */
function Wall({
  cols,
  busy,
  children,
}: {
  cols: number;
  busy?: boolean;
  children: ReactNode;
}) {
  const cells = Children.toArray(children);
  const lanes: ReactNode[][] = Array.from({ length: cols }, () => []);
  cells.forEach((c, i) => lanes[i % cols].push(c));
  return (
    <div className="lbd-grid" aria-busy={busy || undefined}>
      {lanes.map((lane, i) => (
        <div key={i} className="lbd-lane">
          {lane}
        </div>
      ))}
    </div>
  );
}
