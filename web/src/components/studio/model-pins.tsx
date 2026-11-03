"use client";

/* The model picker of the Image, Video and Voice pages (2026-11-02, Mike
   picked "08 · Pinned chips + sheet" off the "Model Picker — 10 Directions"
   canvas). A row of the person's starred models as chips -- one tap picks --
   and an "All models" button that opens the whole list, Recent first, where a
   star keeps a model in the row (four at most). The model in use is always in
   the row, starred or not. Each model wears its maker's logo
   (public/model-logos, from LobeHub's MIT icon set; see its README).

   Stars and recents live in this browser only (localStorage): a convenience,
   never state anything else reads. No price is shown here; it stays on the
   Generate button (2026-10-27). Create has no model picker at all: Vesper
   chooses there (2026-11-02). */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { LayoutGrid, Star } from "lucide-react";
import "@/components/studio/model-pins.css";

export type PinItem = { id: string; name: string; note: string; right: string; icon?: ReactNode };

const MAX_PINS = 4;
const MAX_RECENT = 3;

/** Which logo a model wears, by the words in its id and name. "" is none:
 *  the tile shows the item's own icon, else its first letter. */
export function logoFor(item: { id: string; name: string; note?: string }): string {
  const t = `${item.id} ${item.name} ${item.note ?? ""}`.toLowerCase();
  const rules: [RegExp, string][] = [
    [/nano[\s-]?banana/, "nanobanana"],
    [/\bveo|gemini|imagen/, "google"],
    [/gpt|openai|sora/, "openai"],
    [/flux/, "flux"],
    [/seedream|seedance|omnihuman|bytedance/, "bytedance"],
    [/ideogram/, "ideogram"],
    [/kling/, "kling"],
    [/grok|xai/, "grok"],
    [/\bwan\s?\d|\bwan\b/, "alibaba"],
    [/\bltx/, "lightricks"],
    [/minimax|hailuo/, "minimax"],
    [/eleven/, "elevenlabs"],
    [/vibevoice/, "microsoft"],
    [/qwen/, "qwen"],
    [/recraft/, "recraft"],
    [/hunyuan/, "hunyuan"],
    [/pixverse/, "pixverse"],
    [/topaz/, "topazlabs"],
    [/runway|\bgen-?4/, "runway"],
    [/\bluma|ray\s?\d/, "luma"],
    [/midjourney/, "midjourney"],
    [/sync\s?lip|lipsync|\bsync\b/, "sync"],
  ];
  return rules.find(([re]) => re.test(t))?.[1] ?? "";
}

/** The square tile with a model's logo in it. */
export function ModelLogo({ item, size = 32 }: { item: PinItem; size?: number }) {
  const key = logoFor(item);
  const style = { width: size, height: size, ...(key ? { "--mp-logo": `url(/model-logos/${key}.svg)` } : {}) } as CSSProperties;
  return (
    <span className="mp-logo" style={style} aria-hidden>
      {key ? <i /> : item.icon ? item.icon : <b>{item.name.slice(0, 1)}</b>}
    </span>
  );
}

function readList(key: string): string[] | null {
  try {
    const raw = window.localStorage.getItem(key);
    const v = raw ? JSON.parse(raw) : null;
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : null;
  } catch {
    return null;
  }
}
function writeList(key: string, list: string[]) {
  try {
    window.localStorage.setItem(key, JSON.stringify(list));
  } catch {
    /* a private window: the row still works, it is just not remembered */
  }
}

export function ModelPins(props: {
  /** whose stars these are: one list per page */
  kind: "image" | "video" | "voice";
  items: PinItem[];
  picked: string;
  onPick: (id: string) => void;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  /** the sheet opens upward (a dock at the bottom of the page) */
  up?: boolean;
  title: string;
  foot?: string;
  disabled?: boolean;
}) {
  const { kind, items, picked, onPick, open, onClose } = props;
  const box = useRef<HTMLDivElement>(null);
  const pinKey = `phantra.modelPins.${kind}`;
  const recentKey = `phantra.modelRecent.${kind}`;
  const [pins, setPins] = useState<string[] | null>(null);
  const [recent, setRecent] = useState<string[]>([]);

  // read after mount: localStorage is not there on the server
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- localStorage is only readable after mount */
    setPins(readList(pinKey));
    setRecent(readList(recentKey) ?? []);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [pinKey, recentKey]);

  useEffect(() => {
    if (!open) return;
    const down = (e: PointerEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) onClose();
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("pointerdown", down);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", down);
      document.removeEventListener("keydown", key);
    };
  }, [open, onClose]);

  const known = (id: string) => items.some((m) => m.id === id);
  // never starred anything: the first three models stand in
  const starred = (pins ?? items.slice(0, 3).map((m) => m.id)).filter(known);
  const row = starred.includes(picked) || !known(picked) ? starred : [...starred, picked];
  const byId = (id: string) => items.find((m) => m.id === id)!;

  const pick = (id: string) => {
    onPick(id);
    const next = [id, ...recent.filter((x) => x !== id)].slice(0, MAX_RECENT);
    setRecent(next);
    writeList(recentKey, next);
  };
  const star = (id: string) => {
    const on = starred.includes(id);
    // a fifth star lets the oldest go
    const next = on ? starred.filter((x) => x !== id) : [...starred, id].slice(-MAX_PINS);
    setPins(next);
    writeList(pinKey, next);
  };

  const line = (m: PinItem, sec: string) => {
    const on = starred.includes(m.id);
    return (
      <div className="mp-line" key={`${sec}-${m.id}`} data-on={m.id === picked ? "1" : undefined}>
        <button type="button" className="mp-pick" role="option" aria-selected={m.id === picked} onClick={() => pick(m.id)}>
          <ModelLogo item={m} size={36} />
          <span className="mp-txt">
            <b>{m.name}</b>
            {m.note || m.right ? <small>{[m.note, m.right].filter(Boolean).join(" · ")}</small> : null}
          </span>
        </button>
        <button
          type="button"
          className="mp-star"
          aria-pressed={on}
          aria-label={on ? `Take ${m.name} out of your row` : `Keep ${m.name} in your row`}
          title={on ? "Starred: in your row" : "Star to keep it in your row"}
          onClick={() => star(m.id)}
        >
          <Star strokeWidth={1.8} />
        </button>
      </div>
    );
  };
  const recentShown = recent.filter(known);

  return (
    <div className="mp" ref={box}>
      <div className="mp-row" role="radiogroup" aria-label={`Your ${kind} models`}>
        {row.map((id) => {
          const m = byId(id);
          return (
            <button
              key={id}
              type="button"
              role="radio"
              className="mp-chip"
              aria-checked={id === picked}
              onClick={() => pick(id)}
              disabled={props.disabled}
              title={m.note || m.name}
            >
              <ModelLogo item={m} size={24} />
              <span>{m.name}</span>
            </button>
          );
        })}
        <button
          type="button"
          className="mp-all"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={props.onOpen}
          disabled={props.disabled || !items.length}
        >
          <LayoutGrid strokeWidth={1.8} />
          All models
        </button>
      </div>
      {open ? (
        <div className="mp-sheet" data-up={props.up ? "1" : undefined} role="dialog" aria-label={props.title}>
          <div className="mp-head">
            <b>{props.title}</b>
            <span>Star up to {MAX_PINS} to keep them in your row</span>
          </div>
          <div className="mp-list" role="listbox" aria-label={props.title}>
            {recentShown.length ? (
              <>
                <span className="mp-sec">Recent</span>
                {recentShown.map((id) => line(byId(id), "recent"))}
                <span className="mp-sec">Everything</span>
              </>
            ) : null}
            {items.map((m) => line(m, "all"))}
          </div>
          {props.foot ? <span className="mp-foot">{props.foot}</span> : null}
        </div>
      ) : null}
    </div>
  );
}
