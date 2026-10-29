import { SectionTitle } from "./section-title";
import { ClipPlayer } from "./clips";
import type { MakePage, MakeTile } from "../pages";

// The spec-compare signature (2026-10-22, the Kling 4.0 page): a model's
// spec sheet as the studio runs it, then the model against its neighbours
// in one table, then (when the entry names two `signatureFrames`) one
// prompt rendered on two models side by side. A frame with no `video` is a
// gradient plate off the accent, the template's no-media state, captioned
// by the entry's `meta` until the clip lands. Every value comes from the
// entry (`specSheet`), which reads the catalog and src/fal.py; nothing is typed
// here. The table scrolls inside its own box on a phone, never the page,
// with the row labels pinned to its left edge.
export function SpecCompare({ page }: { page: MakePage }) {
  const s = page.specSheet;
  if (!s) return null;
  const pair = (page.signatureFrames ?? []).slice(0, 2);
  return (
    <>
      <section id="specs" className="border-t border-border">
        <div className="mx-auto max-w-[1000px] px-4 py-20 md:px-6 md:py-24">
          <div className="flex flex-col items-center gap-4 text-center">
            <span className="eyebrow">{s.sheet.eyebrow}</span>
            <SectionTitle>{s.sheet.title}</SectionTitle>
            <p className="max-w-[640px] text-[var(--ink-3)]">{s.sheet.intro}</p>
          </div>
          <dl className="mt-12 border-t border-border">
            {s.sheet.rows.map((r) => (
              <div key={r.label} className="grid gap-1 border-b border-border py-5 md:grid-cols-[minmax(0,15rem)_1fr] md:gap-8">
                <dt className="text-[14px] font-medium text-[var(--ink-3)]">{r.label}</dt>
                <dd>
                  <span className="text-[16px] leading-relaxed text-foreground">{r.value}</span>
                  {r.note && <span className="mt-1 block text-[13px] leading-relaxed text-[var(--ink-3)]">{r.note}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section id="compare" className="border-t border-border bg-[color-mix(in_oklab,var(--primary)_4%,var(--background))]">
        <div className="mx-auto max-w-[1100px] px-4 py-20 md:px-6 md:py-24">
          <div className="flex flex-col items-center gap-4 text-center">
            <span className="eyebrow">{s.compare.eyebrow}</span>
            <SectionTitle>{s.compare.title}</SectionTitle>
            <p className="max-w-[640px] text-[var(--ink-3)]">{s.compare.intro}</p>
          </div>

          {pair.length === 2 && (
            <div className="mt-12 grid gap-5 md:grid-cols-2">
              {pair.map((tile, i) => (
                <Slot key={tile.title} tile={tile} plate={i % 2 ? "var(--plate-2)" : "var(--plate-1)"} />
              ))}
            </div>
          )}

          <div className="mt-12 overflow-x-auto rounded-2xl border border-border bg-background">
            <table className="w-full min-w-[680px] border-collapse text-left text-[14px]">
              <thead>
                <tr className="border-b border-border">
                  <th scope="col" className="sticky left-0 bg-background px-4 py-4 font-medium text-[var(--ink-3)]">
                    <span className="sr-only">Spec</span>
                  </th>
                  {s.compare.columns.map((c, i) => (
                    <th key={c} scope="col" className={`px-4 py-4 font-semibold ${i === 0 ? "text-[var(--primary)]" : ""}`}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {s.compare.rows.map((r) => (
                  <tr key={r.label} className="border-b border-border last:border-b-0">
                    <th scope="row" className="sticky left-0 bg-background px-4 py-4 align-top font-medium text-[var(--ink-3)]">
                      {r.label}
                    </th>
                    {r.values.map((v, i) => (
                      <td key={`${r.label}-${i}`} className={`px-4 py-4 align-top tabular-nums ${i === 0 ? "font-semibold" : ""}`}>
                        {v}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="mt-8 space-y-2 text-[14px] leading-relaxed text-[var(--ink-3)]">
            {s.compare.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
          <p className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-[var(--ink-3)]">
            {s.sources.map((src) => (
              <a key={src.href} href={src.href} rel="noopener noreferrer" target="_blank" className="underline underline-offset-4 hover:text-foreground">
                {src.label}
              </a>
            ))}
          </p>
        </div>
      </section>
    </>
  );
}

/** One side of the pair: the clip when it exists, else the accent's plate
 *  with the model's name and the entry's caption. */
function Slot({ tile, plate }: { tile: MakeTile; plate: string }) {
  return (
    <figure>
      <div className="relative overflow-hidden rounded-2xl bg-card" style={{ aspectRatio: (tile.aspect ?? "16:9").replace(":", " / ") }}>
        {tile.video ? (
          <ClipPlayer tile={tile} />
        ) : (
          <div aria-hidden className="absolute inset-0" style={{ background: tile.plate ?? plate }} />
        )}
        <span className="absolute left-3 top-3 rounded-md bg-black/55 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur-sm">
          {tile.tag}
        </span>
      </div>
      <figcaption className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[16px] font-semibold tracking-[-0.01em]">{tile.title}</span>
        {tile.meta && <span className="text-[13px] text-[var(--ink-3)]">{tile.meta}</span>}
      </figcaption>
    </figure>
  );
}
