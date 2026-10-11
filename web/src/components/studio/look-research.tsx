/* A look researched by name, as the thread draws it (2026-10-11; item 10 of
   docs/tasks/task-studio-agent.md, lib/look-research.ts).

   Two pieces, both built from looks the studio already has:

   - LookResearchNote sits under the brain's answer and says where a look
     came from: the name, how many pages were read, and the pages as links.
     "A reference must be traceable to where it came from" -- a look read
     off the web is no different. Only http(s) is linked.
   - LookCard is the confirm card (.ccard) for set_project_look: the look as
     its labelled lines, a line saying what saving does -- and that it
     replaces a look the project already has -- and the one click that
     saves it. Nothing here spends. */
"use client";

import {
  lookLines,
  researchLine,
  saveNote,
  shownSources,
  type LookResearch,
} from "@/lib/look-research";

export function LookResearchNote({ items }: { items?: LookResearch[] | null }) {
  if (!items?.length) return null;
  return (
    <div className="zlr">
      {items.map((r, i) => {
        const sources = r.ok ? shownSources(r) : [];
        return (
          <p key={`${r.subject}-${i}`} className={`zlr-row${r.ok ? "" : " off"}`}>
            <span className="zlr-line">{researchLine(r)}</span>
            {sources.length ? (
              <span className="zlr-sources">
                {sources.map((s, j) =>
                  s.href ? (
                    <a key={j} href={s.href} target="_blank" rel="noopener noreferrer nofollow">
                      {s.name}
                    </a>
                  ) : (
                    <span key={j}>{s.name}</span>
                  ),
                )}
              </span>
            ) : null}
          </p>
        );
      })}
    </div>
  );
}

export function LookCard({
  label,
  look,
  current,
  decided,
  busy,
  onDecide,
}: {
  label: string;
  look: string;
  /** the look the project has now ("" for none): saving replaces it */
  current?: string | null;
  decided?: "done" | "skipped";
  busy: boolean;
  onDecide: (yes: boolean) => void;
}) {
  const lines = lookLines(look);
  return (
    <div className={`ccard zlr-card${decided ? ` ${decided}` : ""}`}>
      <b>{label}</b>
      <dl>
        {lines.map((l, i) => (
          <div key={i}>
            <dt>{l.label}</dt>
            <dd>{l.text}</dd>
          </div>
        ))}
      </dl>
      {decided ? (
        <span className="ccard-state">{decided === "done" ? "Saved" : "Skipped"}</span>
      ) : (
        <>
          <p className="zlr-note">{saveNote(current)}</p>
          <div className="ccard-actions">
            <button type="button" className="yes" disabled={busy} onClick={() => onDecide(true)}>
              Save look
            </button>
            <button type="button" disabled={busy} onClick={() => onDecide(false)}>
              Skip
            </button>
          </div>
        </>
      )}
    </div>
  );
}
