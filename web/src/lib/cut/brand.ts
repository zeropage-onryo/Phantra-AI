/* The brand kit in the editor's PREVIEW (2026-10-20; the export's half is
   src/cut/brand.py). The preview approximates; the export is exact. A
   track styled `brand` draws in the kit's font, colours and position here
   the way render.ass_document draws it, inside the kit's safe zone. */
import type { CSSProperties } from "react";
import type { CutKit } from "@/lib/cut/api";

const roleHex = (kit: CutKit, role: string | undefined, fallback: string) =>
  (role && role !== "none" ? kit.palette.find((s) => s.role === role)?.hex : undefined) ?? fallback;

export const cutFontAlias = (kit: CutKit, which: "heading" | "body") => `phantra-cutkit-${kit.id}-${which}`;

/** @font-face rules for the kit's font files, under names only this editor uses */
export function cutFontFaces(kit: CutKit, origin = ""): string {
  return (["heading", "body"] as const)
    .map((which) => {
      const url = kit.font_files[`font_${which}`];
      return url ? `@font-face{font-family:"${cutFontAlias(kit, which)}";src:url("${origin}${url}");font-display:swap}` : "";
    })
    .filter(Boolean)
    .join("\n");
}

/** the caption's box (where it sits) and text (how it reads) at a frame height */
export function brandCaption(kit: CutKit, frameH: number): { box: CSSProperties; text: CSSProperties } {
  const c = kit.captions ?? {};
  const which = c.font === "body" ? "body" : "heading";
  const own = kit.font_files[`font_${which}`] ? `"${cutFontAlias(kit, which)}", ` : "";
  const outline = c.outline && c.outline !== "none" ? roleHex(kit, c.outline, "#000000") : null;
  const boxed = c.box && c.box !== "none";
  const position = c.position ?? "bottom";
  const box: CSSProperties =
    position === "top"
      ? { top: "8%" }
      : position === "lower_third"
        ? { bottom: "12%", textAlign: "left" }
        : { bottom: "12%" };
  return {
    box: { ...box, fontSize: frameH * (c.size ?? 0.05) },
    text: {
      fontFamily: `${own}"${kit.fonts?.[which] ?? "system-ui"}", system-ui, sans-serif`,
      fontWeight: 700,
      color: roleHex(kit, c.fill ?? "text", "#FFFFFF"),
      textTransform: c.uppercase ? "uppercase" : "none",
      ...(boxed ? { background: roleHex(kit, c.box, "#000000"), padding: "0.12em 0.45em" } : {}),
      ...(outline ? { WebkitTextStroke: `1px ${outline}` } : {}),
      boxDecorationBreak: "clone",
      WebkitBoxDecorationBreak: "clone",
    },
  };
}
