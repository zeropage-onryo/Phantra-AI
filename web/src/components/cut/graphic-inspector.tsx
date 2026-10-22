"use client";

/* One graphic on a graphics track, in the Inspector (2026-10-20,
   src/cut/graphics.py). Every change is one set_graphic op -- a version you
   can undo -- and the preview shows it at once. Text saves on blur, the
   choices on click. */
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useCut } from "@/lib/cut/store";
import { FrameField } from "@/components/cut/inspector";
import type { Doc, GraphicItem, Track } from "@/lib/cut/timeline";
import { ANIMS_IN, ANIMS_OUT, COLORS, POSITIONS, SIZES, TYPES, WORD_MAX, TEXT_MAX, withDefaults } from "@/lib/cut/graphics";

const words = (v: string) => v.replace(/_/g, " ");

function Seg<T extends string>({
  label,
  value,
  options,
  onPick,
}: {
  label: string;
  value: T;
  options: readonly T[];
  onPick: (v: T) => void;
}) {
  return (
    <div className="cx-field">
      <span className="cx-label">{label}</span>
      <span className="cx-seg" style={{ flexWrap: "wrap" }}>
        {options.map((o) => (
          <button key={o} type="button" aria-pressed={value === o} onClick={() => value !== o && onPick(o)}>
            {words(o)}
          </button>
        ))}
      </span>
    </div>
  );
}

export function GraphicInspector({ doc, item, track }: { doc: Doc; item: GraphicItem; track: Track }) {
  const op = useCut((s) => s.op);
  const bin = useCut((s) => s.bin);
  const kit = useCut((s) => s.brandKit);
  const it = withDefaults(item);
  const [text, setText] = useState(item.text ?? "");
  const fps = doc.fps;
  const stills = bin.filter((b) => b.kind === "image");

  const save = (patch: Partial<GraphicItem>) =>
    op("set_graphic", {
      track_id: track.id,
      graphic_id: item.id,
      start: patch.start ?? item.start,
      end: patch.end ?? item.end,
      type: patch.type ?? item.type,
      ...Object.fromEntries(Object.entries(patch).filter(([k]) => !["start", "end", "type"].includes(k))),
    });

  const max = it.type === "background_word" ? WORD_MAX : TEXT_MAX;
  return (
    <>
      <div className="cx-field">
        <span className="cx-label">Graphic · {track.id}</span>
        <span className="cx-seg" style={{ flexWrap: "wrap" }}>
          {TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              title={t.note}
              aria-pressed={it.type === t.id}
              // a card has no words to carry over and a word no picture: the
              // type is changed only where the other half is already there
              disabled={(t.id === "card" && !item.media && !stills.length) || (t.id !== "card" && it.type === "card" && !text.trim())}
              onClick={() => {
                if (it.type === t.id) return;
                if (t.id === "card") save({ type: "card", media: item.media ?? stills[0]?.handle });
                else save({ type: t.id, text: text.trim() || "Text" });
              }}
            >
              {t.label}
            </button>
          ))}
        </span>
      </div>

      {it.type === "card" ? (
        <label className="cx-field">
          <span className="cx-label">Picture</span>
          <select className="cx-select" value={item.media ?? ""} onChange={(e) => e.target.value && save({ media: e.target.value })}>
            {!item.media ? <option value="">Pick a still…</option> : null}
            {stills.map((b) => (
              <option key={b.handle} value={b.handle}>
                {b.name}
              </option>
            ))}
          </select>
          {!stills.length ? <p className="cx-note">Upload a still (a UI screenshot, a product shot) into the bin first.</p> : null}
        </label>
      ) : null}

      <label className="cx-field">
        <span className="cx-label">
          {it.type === "card" ? "Caption under the card" : "Text"} · {text.length}/{max}
        </span>
        <textarea
          className="cx-textarea"
          value={text}
          maxLength={max}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            const next = text.trim();
            if (next === (item.text ?? "")) return;
            if (!next && it.type !== "card") return setText(item.text ?? "");
            save({ text: next });
          }}
          onKeyDown={(e) => {
            e.stopPropagation();
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) (e.target as HTMLTextAreaElement).blur();
          }}
        />
      </label>

      <FrameField label="Starts" value={item.start} fps={fps} onCommit={(f) => save({ start: Math.max(0, f) })} />
      <FrameField label="Ends" value={item.end} fps={fps} onCommit={(f) => save({ end: f })} />
      <Seg label="Where" value={(it.position ?? "center") as (typeof POSITIONS)[number]} options={POSITIONS} onPick={(v) => save({ position: v })} />
      <Seg label="In" value={(it.anim_in ?? "fade") as (typeof ANIMS_IN)[number]} options={ANIMS_IN} onPick={(v) => save({ anim_in: v })} />
      <Seg label="Out" value={(it.anim_out ?? "fade") as (typeof ANIMS_OUT)[number]} options={ANIMS_OUT} onPick={(v) => save({ anim_out: v })} />
      <Seg label="Size" value={(it.size ?? "m") as (typeof SIZES)[number]} options={SIZES} onPick={(v) => save({ size: v })} />
      {it.type !== "card" ? (
        <Seg
          label={kit ? `Colour · ${kit.name}` : "Colour · auto is white with no brand kit"}
          value={(COLORS as readonly string[]).includes(it.color ?? "auto") ? ((it.color ?? "auto") as (typeof COLORS)[number]) : "auto"}
          options={COLORS}
          onPick={(v) => save({ color: v })}
        />
      ) : null}
      {it.type === "background_word" ? (
        <label className="cx-check">
          <input type="checkbox" checked={it.drift !== false} onChange={(e) => save({ drift: e.target.checked })} />
          Drift slowly across its time
        </label>
      ) : null}
      <button type="button" className="cx-btn ghost" onClick={() => op("delete_graphic", { track_id: track.id, graphic_id: item.id })}>
        <Trash2 /> Delete graphic
      </button>
    </>
  );
}
