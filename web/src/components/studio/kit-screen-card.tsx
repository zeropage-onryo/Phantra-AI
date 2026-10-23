"use client";

/* The card under Vesper's make_screen (2026-10-22, lib/kit-screen.ts,
   src/kit_screens.py): the app screen drawn from the brand kit in its own
   fonts and colours, any word the kit says never to use, and Keep. Drawing
   it and keeping it are both free; Keep files it in the Library and puts it
   first in the box, so the next shot is held to it; the kept still is then
   the turn's own numbered tile, and this card says where it went. */
import { useEffect, useState } from "react";
import { previewKitScreen } from "@/lib/studio-api";
import { screenOf, screenTitle } from "@/lib/kit-screen";

export function KitScreenCard({
  args,
  decided,
  busy,
  onDecide,
}: {
  args: Record<string, unknown>;
  decided?: "done" | "skipped";
  busy: boolean;
  onDecide: (yes: boolean) => void;
}) {
  const screen = screenOf(args);
  const [image, setImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const specKey = screen ? JSON.stringify(screen.spec) : "";

  useEffect(() => {
    if (!screen || decided) return;
    let stale = false;
    previewKitScreen(screen.kitId, screen.spec)
      .then((r) => !stale && setImage(r.image))
      .catch((e) => !stale && setError(e instanceof Error ? e.message : "The screen could not be drawn"));
    return () => {
      stale = true;
    };
    // the spec is the card's whole input; specKey names it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specKey, decided]);

  if (!screen) return null;
  return (
    <div className={`ccard zks-card${decided ? ` ${decided}` : ""}`} data-kit-screen={screen.kitId}>
      <b>
        {screenTitle(screen.summary)} · {screen.kitName}
      </b>
      {decided ? null : (
        <div className="zks-frame">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element -- a data URL drawn by the server
            <img src={image} alt={`${screen.summary}, drawn from ${screen.kitName}`} />
          ) : (
            <span className="zks-wait" role={error ? "alert" : undefined}>
              {error || "Drawing it in the kit's fonts and colours…"}
            </span>
          )}
        </div>
      )}
      {screen.warnings.length ? (
        <ul className="zks-warn">
          {screen.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      ) : null}
      {decided ? (
        <span className="ccard-state">
          {decided === "done" ? "Kept in the Library · first in the box for the next shot" : "Discarded"}
        </span>
      ) : (
        <>
          <p className="zks-note">Free: drawn in code from the kit, nothing is generated or charged.</p>
          <div className="ccard-actions">
            <button type="button" className="yes" disabled={busy || !image} onClick={() => onDecide(true)}>
              Keep · free
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
