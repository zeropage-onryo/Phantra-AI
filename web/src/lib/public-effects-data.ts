import catalog from "@/content/effects-catalog.json";
import pageContent from "@/content/effects-page.json";
import showcase from "../../public/showcase/manifest.json";
import { readContent, tilesFrom } from "@/lib/effects-wall";
import type { Effect } from "@/lib/effects";
import { parseManifest } from "@/lib/showcase";
import { publicEffects, type PublicEffect } from "@/lib/public-effects";

/* The public effects, read at BUILD time from the three committed files the
   studio's wall already reads (2026-11-05, docs/tasks/task-public-effects-pages.md):
   the effects catalogue (generated from src/effects.py by
   `python -m ops.export_effects_catalog`), the showcase manifest and the
   hand-picked featured / new lists. A deploy is what publishes a change. */

let cached: PublicEffect[] | null = null;

export function allPublicEffects(): PublicEffect[] {
  if (cached) return cached;
  const items = (catalog as { items: unknown[] }).items as Effect[];
  cached = publicEffects(tilesFrom(items, parseManifest(showcase), readContent(pageContent)));
  return cached;
}

export function publicEffect(slug: string): PublicEffect | null {
  return allPublicEffects().find((e) => e.slug === slug) ?? null;
}

/** The featured picks (effects-page.json) that have a public page, in order. */
export function featuredEffects(max = 3): PublicEffect[] {
  const keys = readContent(pageContent).featured;
  const all = allPublicEffects();
  return keys.map((k) => all.find((e) => e.key === k)).filter((e): e is PublicEffect => Boolean(e)).slice(0, max);
}
