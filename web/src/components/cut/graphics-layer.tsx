"use client";

/* The graphics track in the Program viewer (2026-10-20). Each item under the
   playhead is drawn as page elements at the same size, place and colour the
   export's Pillow drawing uses (src/cut/graphics.py), and posed per frame by
   lib/cut/graphics.pose -- the same eased moves and fades the export's
   overlay applies. The preview approximates the fonts; the export is exact. */
import type { CSSProperties } from "react";
import { API_URL } from "@/lib/api";
import type { CutKit } from "@/lib/cut/api";
import { cutFontAlias } from "@/lib/cut/brand";
import { pose, withDefaults, WORD_ALPHA } from "@/lib/cut/graphics";
import type { Doc, GraphicItem } from "@/lib/cut/timeline";
import { useCut } from "@/lib/cut/store";

const SCALE = { s: 0.75, m: 1, l: 1.35 } as const;

function colour(kit: CutKit | null, role: string | undefined, type: string): string {
  const palette = Object.fromEntries((kit?.palette ?? []).map((s) => [s.role, s.hex]));
  if (role && /^#[0-9a-fA-F]{6}$/.test(role)) return role;
  if (role === "white") return "#FFFFFF";
  if (role === "black") return "#000000";
  if (role && role !== "auto") return palette[role] ?? "#FFFFFF";
  if (type === "headline" || type === "background_word") return palette.primary ?? "#FFFFFF";
  return palette.text ?? "#FFFFFF";
}

function place(position: string | undefined, safe: number): CSSProperties {
  const pad = `${Math.max(safe, 0.04) * 100}%`;
  switch (position) {
    case "left":
      return { left: pad, top: "50%", transform: "translateY(-50%)", textAlign: "left" };
    case "right":
      return { right: pad, top: "50%", transform: "translateY(-50%)", textAlign: "left" };
    case "top":
      return { left: "50%", top: pad, transform: "translateX(-50%)", textAlign: "center" };
    case "bottom":
      return { left: "50%", bottom: pad, transform: "translateX(-50%)", textAlign: "center" };
    case "lower_left":
      return { left: pad, bottom: `calc(${pad} + 6%)`, textAlign: "left" };
    default:
      return { left: "50%", top: "50%", transform: "translate(-50%, -50%)", textAlign: "center" };
  }
}

function Item({ item, doc, w, h, kit }: { item: GraphicItem; doc: Doc; w: number; h: number; kit: CutKit | null }) {
  const playhead = useCut((s) => s.playhead);
  const bin = useCut((s) => s.bin);
  const p = pose(item, playhead, doc.fps);
  if (!p) return null;
  const it = withDefaults(item);
  const k = w / doc.size[0];
  const unit = Math.min(doc.size[0], doc.size[1]) * k;
  const scale = SCALE[(it.size ?? "m") as keyof typeof SCALE] ?? 1;
  const ink = colour(kit, it.color, it.type);
  const font = (which: "heading" | "body") =>
    kit?.font_files?.[`font_${which}`] ? `"${cutFontAlias(kit, which)}", system-ui, sans-serif` : "system-ui, sans-serif";
  // the move: an outer box at rest, an inner one offset by the pose
  const outer: CSSProperties = { position: "absolute", pointerEvents: "none", ...place(it.position, 0.06) };
  const inner: CSSProperties = { transform: `translate(${p.dx * w}px, ${p.dy * h}px)`, opacity: p.alpha };

  if (it.type === "background_word") {
    return (
      <div style={{ ...outer, ...place(it.position ?? "center", 0), zIndex: 40 }}>
        <div
          style={{
            ...inner,
            opacity: p.alpha * WORD_ALPHA,
            color: ink,
            font: `${unit * 0.42 * scale}px/1 ${font("heading")}`,
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          {it.text}
        </div>
      </div>
    );
  }
  if (it.type === "card") {
    const b = bin.find((x) => x.handle === it.media);
    const src = b?.url ?? b?.poster;
    const width = (doc.size[0] >= doc.size[1] ? 0.42 : 0.72) * w * scale;
    return (
      <div style={{ ...outer, zIndex: 41 }}>
        <div style={inner}>
          {src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={src.startsWith("http") ? src : `${API_URL}${src}`}
              alt=""
              style={{
                display: "block",
                maxWidth: width,
                maxHeight: h * 0.6 * scale,
                borderRadius: unit * 0.025,
                boxShadow: `0 ${unit * 0.012}px ${unit * 0.04}px rgb(0 0 0 / 0.43)`,
              }}
            />
          ) : null}
          {it.text ? (
            <div style={{ marginTop: unit * 0.02, color: colour(kit, "auto", "label"), font: `${unit * 0.03}px ${font("body")}` }}>
              {it.text}
            </div>
          ) : null}
        </div>
      </div>
    );
  }
  const heading = it.type === "headline";
  const px = unit * (heading ? 0.09 : 0.045) * scale;
  const side = ["left", "right", "lower_left"].includes(it.position ?? "");
  const pill =
    it.pill && it.pill !== "auto" ? colour(kit, it.pill, "label") : kit?.palette.find((s) => s.role === "primary")?.hex;
  const labelInk = it.color && it.color !== "auto" ? ink : pill ? (kit?.palette.find((s) => s.role === "background")?.hex ?? "#FFFFFF") : "#FFFFFF";
  return (
    <div style={{ ...outer, zIndex: 42, maxWidth: heading ? w * (side ? 0.46 : 0.8) : w * 0.8 }}>
      <div
        style={{
          ...inner,
          color: heading ? ink : labelInk,
          font: `${px}px/1.18 ${font(heading ? "heading" : "body")}`,
          textShadow: heading && !kit?.palette.length ? `0 ${px * 0.04}px ${px * 0.12}px rgb(0 0 0 / 0.67)` : undefined,
          ...(heading
            ? {}
            : {
                background: pill ?? "rgb(0 0 0 / 0.59)",
                padding: `${px * 0.45}px`,
                borderRadius: px * 0.6,
                display: "inline-block",
              }),
        }}
      >
        {it.text}
      </div>
    </div>
  );
}

/* every graphics track, G1 first (lowest), each item under the playhead */
export function GraphicsLayer({ doc, w, h, kit }: { doc: Doc; w: number; h: number; kit: CutKit | null }) {
  const tracks = doc.tracks.filter((t) => t.kind === "graphic");
  if (!tracks.length) return null;
  return (
    <>
      {tracks.flatMap((t) =>
        (t.items ?? []).map((g) => <Item key={g.id} item={g} doc={doc} w={w} h={h} kit={kit} />),
      )}
    </>
  );
}
