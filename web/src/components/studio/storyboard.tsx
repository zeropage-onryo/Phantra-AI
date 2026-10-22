"use client";

/* The storyboard (lib/storyboard.ts, vesper_v2): the written scenes of the
   conversation as shot cards -- still or clip, length, the model its
   Render card opens on, its words (editable on the card), drag to
   reorder the view, and "Redo this shot only", which opens that scene's
   priced Render card on the shot. Nothing here renders. */
import { useState, type ReactNode } from "react";
import { Clapperboard, GripVertical, RotateCcw } from "lucide-react";
import { mediaSrc } from "@/lib/composer";
import { ordered, redoTarget, reorder, shotLabel, type SceneBoard, type ShotCard } from "@/lib/storyboard";
import "@/components/studio/vesper-v2.css";

export function Storyboard({
  boards,
  orders,
  texts,
  busy,
  header,
  onReorder,
  onEdit,
  onRedo,
  onSelect,
}: {
  boards: SceneBoard[];
  /** the kept view order per scene (shot numbers) */
  orders: Record<string, number[]>;
  /** words edited on a card, by shot key */
  texts: Record<string, string>;
  busy: boolean;
  /** the autonomy dial, drawn in the head */
  header?: ReactNode;
  onReorder: (madeId: string, order: number[]) => void;
  onEdit: (key: string, text: string) => void;
  onRedo: (target: { conceptId: number; part: number }) => void;
  onSelect: (madeId: string, n: number) => void;
}) {
  const [which, setWhich] = useState<string | null>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const board = boards.find((b) => b.madeId === which) ?? boards[0] ?? null;
  const shots = board ? ordered(board, orders[board.madeId]) : [];

  const drop = (to: number) => {
    if (board && drag !== null && drag !== to) {
      onReorder(board.madeId, reorder(shots, drag, to).map((s) => s.n));
    }
    setDrag(null);
    setOver(null);
  };

  return (
    <aside className="sb" aria-label="Storyboard">
      <div className="sb-head">
        <Clapperboard strokeWidth={1.6} size={16} aria-hidden />
        <b>Storyboard</b>
        <span className="spacer" />
        {header}
      </div>
      {boards.length > 1 ? (
        <div className="sb-tabs" role="tablist" aria-label="Scenes">
          {boards.map((b) => (
            <button key={b.madeId} type="button" role="tab" aria-selected={b.madeId === board?.madeId} onClick={() => setWhich(b.madeId)}>
              {b.title}
              {b.rendered ? " · rendered" : ""}
            </button>
          ))}
        </div>
      ) : null}
      {!board ? (
        <div className="sb-empty">
          <b>Shots appear here as Vesper writes them.</b>
          Describe a scene in the box: each timed shot becomes a card you can edit, reorder and redo on its own.
        </div>
      ) : (
        <>
          <div className="sb-grid">
            {shots.map((s: ShotCard, i: number) => {
              const text = texts[s.key] ?? s.text;
              const target = redoTarget(s);
              return (
                <div
                  key={s.key}
                  className={`sb-card${drag === i ? " dragging" : ""}${over === i && drag !== i ? " over" : ""}`}
                  draggable={!busy}
                  onDragStart={() => setDrag(i)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setOver(i);
                  }}
                  onDragLeave={() => setOver((o) => (o === i ? null : o))}
                  onDrop={(e) => {
                    e.preventDefault();
                    drop(i);
                  }}
                  onDragEnd={() => {
                    setDrag(null);
                    setOver(null);
                  }}
                >
                  <div className="sb-media" role="button" tabIndex={0} aria-label={shotLabel(s)} onClick={() => onSelect(s.madeId, s.n)} onKeyDown={(e) => e.key === "Enter" && onSelect(s.madeId, s.n)}>
                    {s.clip ? (
                      <video src={mediaSrc(s.clip)} poster={s.still ? mediaSrc(s.still) : undefined} muted loop playsInline preload="metadata" />
                    ) : s.still ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={mediaSrc(s.still)} alt="" />
                    ) : (
                      <span className="sb-n">{String(s.n).padStart(2, "0")}</span>
                    )}
                    <span className="sb-grip" aria-hidden>
                      <GripVertical strokeWidth={2} />
                    </span>
                    <span className="sb-badge">{s.seconds}s</span>
                  </div>
                  <div className="sb-meta">
                    <span>{shotLabel(s)}</span>
                    <span className="sb-chip" title="The model this shot's Render card opens on; you pick and pay there">
                      {s.modelLabel}
                    </span>
                  </div>
                  {editing === s.key ? (
                    <textarea
                      className="sb-edit"
                      autoFocus
                      defaultValue={text}
                      aria-label={`Words for ${shotLabel(s)}`}
                      onBlur={(e) => {
                        onEdit(s.key, e.target.value);
                        setEditing(null);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          (e.target as HTMLTextAreaElement).blur();
                        }
                        if (e.key === "Escape") setEditing(null);
                      }}
                    />
                  ) : (
                    <p className="sb-text" title="Click to edit this shot's words" onClick={() => !busy && setEditing(s.key)}>
                      {text || "No words yet"}
                    </p>
                  )}
                  <div className="sb-acts">
                    <button type="button" disabled={busy || !target} title="Opens this scene's priced Render card on this shot. Nothing renders until you approve." onClick={() => target && onRedo(target)}>
                      <RotateCcw strokeWidth={1.8} aria-hidden />
                      Redo this shot only
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="sb-note">Drag to reorder the board. The order here is yours to arrange; the clips are cut in the editor.</p>
        </>
      )}
    </aside>
  );
}
