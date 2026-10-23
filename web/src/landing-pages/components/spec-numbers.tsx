"use client";

import { useState } from "react";
import { ClipPlayer } from "./clips";
import { SectionTitle } from "./section-title";
import type { MakePage } from "../pages";

// The "spec-numbers" signature (2026-10-23, the Grok Imagine page): the
// model's few numbers set huge, each one a button, and beside them the clip
// that shows that number (`signatureFrames[i]`; a plate until it lands).
// One short line under each figure and nothing smaller (the no-small-wording
// rule). The picked figure turns white with the accent along its top edge.
export function SpecNumbers({ page }: { page: MakePage }) {
  const [pick, setPick] = useState(0);
  const items = page.specs?.items ?? [];
  if (!items.length) return null;
  const tile = page.signatureFrames?.[pick];
  return (
    <section id="numbers" className="border-t border-border">
      <div className="mx-auto max-w-[1200px] px-4 pb-16 pt-16 md:px-6 md:pb-24 md:pt-24">
        {page.specs?.title && <SectionTitle className="md:text-left">{page.specs.title}</SectionTitle>}
        <div className="mt-10 grid items-center gap-12 md:mt-14 lg:grid-cols-[1.1fr_1fr]">
          <div className="grid grid-cols-2 gap-x-6 gap-y-8">
            {items.map((item, i) => (
              <button
                key={item.big + item.small}
                type="button"
                aria-pressed={i === pick}
                onClick={() => setPick(i)}
                className={`border-t pt-5 text-left outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 ${
                  i === pick ? "border-[var(--primary)] text-foreground" : "border-border text-[var(--ink-3,#6b6964)] hover:text-[var(--ink-2)]"
                }`}
              >
                <span className="block font-sans text-[clamp(4rem,8vw,7.5rem)] font-black leading-[0.9] tracking-[-0.05em]">{item.big}</span>
                <span className="mt-3 block text-[17px] text-[var(--ink-2)]">{item.small}</span>
              </button>
            ))}
          </div>
          <div
            className="relative mx-auto aspect-[4/5] w-full max-w-[460px] overflow-hidden rounded-2xl border border-[var(--card-line)]"
            style={{ boxShadow: "0 40px 100px -40px color-mix(in srgb, var(--primary) 45%, transparent)" }}
          >
            {tile?.video ? (
              <ClipPlayer key={tile.video} tile={tile} />
            ) : (
              <div aria-hidden className="absolute inset-0" style={{ background: tile?.plate ?? (pick % 2 ? "var(--plate-2)" : "var(--plate-1)") }} />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
