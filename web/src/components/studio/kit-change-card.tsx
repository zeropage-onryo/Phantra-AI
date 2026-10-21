"use client";

/* The card under Vesper's propose_kit_change (2026-10-21, lib/kit-change.ts):
   each field before and after, swatches for colours, Apply and Discard.
   Nothing changes until Apply. */
import Link from "next/link";
import { diffRows, kitOf, shown, swatch } from "@/lib/kit-change";

export function KitChangeCard({
  label,
  args,
  decided,
  busy,
  onDecide,
}: {
  label: string;
  args: Record<string, unknown>;
  decided?: "done" | "skipped";
  busy: boolean;
  onDecide: (yes: boolean) => void;
}) {
  const rows = diffRows(args);
  const kit = kitOf(args);
  return (
    <div className={`ccard zkc-card${decided ? ` ${decided}` : ""}`}>
      <b>
        {label}
        {kit ? ` · ${kit.name}` : ""}
      </b>
      <dl>
        {rows.map((r) => (
          <div key={r.field}>
            <dt>{r.label}</dt>
            <dd className="zkc-row">
              <Side kind={r.kind} value={r.before} old />
              <span aria-hidden className="zkc-arrow">→</span>
              <Side kind={r.kind} value={r.after} />
            </dd>
          </div>
        ))}
      </dl>
      {decided ? (
        <span className="ccard-state">
          {decided === "done" ? "Applied" : "Discarded"}
          {decided === "done" && kit ? (
            <>
              {" · "}
              <Link href={`/studio/brand/${kit.id}`}>open the kit</Link>
            </>
          ) : null}
        </span>
      ) : (
        <>
          <p className="zkc-note">Nothing changes until you apply it. Every project on this kit uses it from the next scene, still, clip and export.</p>
          <div className="ccard-actions">
            <button type="button" className="yes" disabled={busy || !rows.length} onClick={() => onDecide(true)}>
              Apply
            </button>
            <button type="button" disabled={busy} onClick={() => onDecide(false)}>
              Discard
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function Side({ kind, value, old }: { kind: "colour" | "text"; value: string; old?: boolean }) {
  const hex = kind === "colour" ? swatch(value) : null;
  return (
    <span className={`zkc-side${old ? " old" : ""}`}>
      {hex ? <span className="zkc-swatch" style={{ background: hex }} aria-hidden /> : null}
      <span className="zkc-value">{shown(value)}</span>
    </span>
  );
}
