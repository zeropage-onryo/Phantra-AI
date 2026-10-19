import { num } from "@/lib/catalog";
import { SectionTitle } from "./section-title";
import type { MakePage } from "../pages";

// An optional pricing block (2026-10-15, the Kling page's "Kling AI
// pricing"): lengths and the credits each costs, read off the catalog by
// the entry, never typed here. Renders nothing while the entry has no
// `pricing`. A third-party price is only ever a dated link, not a figure.
export function PricingSection({ page }: { page: MakePage }) {
  const p = page.pricing;
  if (!p) return null;
  return (
    <section id="pricing" className="border-t border-border">
      <div className="mx-auto max-w-[900px] px-4 py-20 md:px-6 md:py-24">
        <SectionTitle>{p.title}</SectionTitle>
        <p className="mx-auto mt-6 max-w-[640px] text-center text-[var(--ink-3)]">{p.intro}</p>
        <table className="mt-10 w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border text-sm text-[var(--ink-3)]">
              <th className="py-3 font-medium">Clip</th>
              <th className="py-3 text-right font-medium">Credits</th>
            </tr>
          </thead>
          <tbody>
            {p.rows.map((r) => (
              <tr key={r.label} className="border-b border-border">
                <td className="py-4">{r.label}</td>
                <td className="py-4 text-right font-semibold tabular-nums">{num(r.credits)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="mt-8 space-y-2 text-[var(--ink-3)]">
          {p.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <a
          href={p.link.href}
          rel="noopener noreferrer"
          target="_blank"
          className="mt-6 inline-block underline underline-offset-4"
        >
          {p.link.label}
        </a>
      </div>
    </section>
  );
}
