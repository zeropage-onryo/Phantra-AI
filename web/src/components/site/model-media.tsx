"use client";

import { ClipPlayer } from "@/landing-pages/components/clips";
import type { MakeTile } from "@/landing-pages/pages";

// One model's picture on /models (2026-10-20): its landing page's own clip,
// looping muted while on screen (ClipPlayer's rules: lazy, one sound at a
// time), or its still. The parent sizes the box and must be `relative`.
export function ModelMedia({ tile, eager = false, sound = false }: { tile: MakeTile; eager?: boolean; sound?: boolean }) {
  if (tile.video) return <ClipPlayer tile={tile} eager={eager} sound={sound} />;
  if (!tile.src) return <div className="absolute inset-0 bg-secondary" />;
  // eslint-disable-next-line @next/next/no-img-element -- a plain still from public/, sized by its box
  return <img src={tile.src} alt={tile.title} loading={eager ? "eager" : "lazy"} className="absolute inset-0 h-full w-full object-cover" />;
}
