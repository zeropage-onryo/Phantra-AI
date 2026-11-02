"use client";

/* Every shape (2026-11-02, lib/every-shape.ts, POST /api/every-shape): one
   button that makes 9:16, 1:1 and 16:9 from one finished clip or still, each a
   free reformat in the Library. Used under the in-chat Final cut and in the
   Library viewer; `look` picks which of the two button styles it wears. It
   holds its own small state: idle, working, or the list of shapes. Nothing
   here spends. Styles: every-shape.css (es-). */
import { useState } from "react";
import Link from "next/link";
import { LayoutGrid } from "lucide-react";
import { runEveryShape, waitForJob } from "@/lib/studio-api";
import { resultId, shapeLine, shapesSummary, type ShapeResult } from "@/lib/every-shape";
import "./every-shape.css";

export function EveryShape({ source, look, onMade }: {
  /** the item, as gen:<id> */
  source: string;
  /** the button style of the place it sits in */
  look: "chat" | "viewer";
  /** told when new items landed (a wall to refresh) */
  onMade?: () => void;
}) {
  const [state, setState] = useState<"idle" | "working" | "done" | "failed">("idle");
  const [line, setLine] = useState("");
  const [results, setResults] = useState<ShapeResult[]>([]);

  async function go() {
    if (state === "working") return;
    setState("working");
    setLine("Making the other shapes…");
    try {
      const started = await runEveryShape(source);
      if (!started.making.length) setLine("Checking what is already here…");
      const job = await waitForJob(started.job_id, (j) => setLine(j.detail || "Making the other shapes…"));
      const shapes = (job as unknown as { shapes?: ShapeResult[] }).shapes ?? [];
      if (job.status !== "done") throw new Error(job.error || "The shapes were not made. Nothing was charged.");
      setResults(shapes);
      setLine(shapesSummary(shapes));
      setState("done");
      if (shapes.some((r) => r.status === "made")) onMade?.();
    } catch (e) {
      setLine(e instanceof Error ? e.message : "The shapes were not made. Nothing was charged.");
      setState("failed");
    }
  }

  return (
    <div className={`es es-${look}`}>
      <button
        type="button"
        className={look === "chat" ? "zc-act" : "av-ghost"}
        onClick={go}
        disabled={state === "working"}
        title="Make 9:16, 1:1 and 16:9 versions of this for every placement. Free."
      >
        <LayoutGrid strokeWidth={1.6} aria-hidden /> {state === "working" ? "Making shapes…" : "Every shape · free"}
      </button>
      {line ? (
        <p className={`es-line${state === "failed" ? " is-failed" : ""}`} role="status">
          {line}
        </p>
      ) : null}
      {results.length ? (
        <ul className="es-list">
          {results.map((r) => {
            const id = r.status === "same" ? null : resultId(r);
            return (
              <li key={r.aspect} className={r.status === "failed" ? "is-failed" : undefined}>
                {id !== null ? (
                  <Link href={`/studio/assets?open=${id}`} className="es-link" title="Open it in the Library">
                    {shapeLine(r)}
                  </Link>
                ) : (
                  <span>{shapeLine(r)}</span>
                )}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
