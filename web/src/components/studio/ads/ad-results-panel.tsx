"use client";

/* Results on the Ad Studio (2026-10-29, src/ad_results.py,
   docs/tasks/task-ad-results.md): what the person's ads did once they ran.

   They export the ad-level report from Meta or TikTok Ads Manager as CSV and
   drop it here. An ad whose name carries a render's ad code (PH…, shown in the
   Library viewer) is matched to that render, and versions of one ad written by
   an Ad Studio plan read back as a test with a verdict. Vesper reads the same
   numbers on every Ad Studio turn. Nothing here spends; the money is the
   person's own ad spend, in their export's currency. Styles: ad-studio.css. */
import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, Trophy, X } from "lucide-react";
import {
  count,
  importLine,
  money,
  percent,
  ranked,
  times,
  type AdResults,
  type ImportResult,
} from "@/lib/ad-results";
import { deleteAdImport, getAdResults, importAdReport } from "@/lib/ad-results-api";
import { useShell } from "@/components/studio/shell";

const PLATFORM: Record<string, string> = { meta: "Meta", tiktok: "TikTok", csv: "CSV" };
const UNMATCHED_SHOWN = 5;

export function AdResultsPanel() {
  const { toast } = useShell();
  const [data, setData] = useState<AdResults | null>(null);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    getAdResults()
      .then(setData)
      .catch(() => setData({ ads: [], tests: [], imports: [], unmatched: 0 }));
  }, []);
  useEffect(load, [load]);

  async function take(file: File | undefined) {
    if (!file || busy) return;
    setBusy(true);
    setError("");
    try {
      const got = await importAdReport(file);
      setLast(got);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That file could not be read.");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  async function undo(importId: string) {
    try {
      const { deleted } = await deleteAdImport(importId);
      toast(`Removed ${deleted} row${deleted === 1 ? "" : "s"}`);
      if (last?.import_id === importId) setLast(null);
      load();
    } catch {
      toast("Could not remove that import. Try again.", "err");
    }
  }

  const ads = data ? ranked(data.ads) : [];
  const newest = data?.imports[0];

  return (
    <section className="as-step as-results" aria-labelledby="as-results">
      <h2 id="as-results">
        <span>05</span> Results
        <small>from your ads manager</small>
      </h2>
      <p className="as-results-how">
        Put each render&apos;s <b>ad code</b> (PH and a number, under Details in the Library) in the ad&apos;s
        name. Then export the <b>ad-level</b> report from Meta Ads Manager or TikTok Ads Manager as CSV and drop
        it here. Vesper reads these numbers when it writes your next ad.
      </p>

      <label
        className={`as-drop${over ? " is-over" : ""}${busy ? " is-busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          void take(e.dataTransfer.files?.[0]);
        }}
      >
        <FileUp size={18} strokeWidth={1.8} aria-hidden />
        <span>{busy ? "Reading your report…" : "Drop a CSV report, or choose a file"}</span>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          className="as-file"
          disabled={busy}
          onChange={(e) => void take(e.target.files?.[0])}
        />
      </label>

      {error ? (
        <p className="as-results-error" role="alert">
          {error}
        </p>
      ) : null}
      {last ? (
        <div className="as-results-done" role="status">
          <p>{importLine(last)}</p>
          {last.unmatched_count ? (
            <p className="as-hint">
              {last.unmatched_count} ad{last.unmatched_count === 1 ? " has" : "s have"} no ad code of yours in
              {last.unmatched_count === 1 ? " its" : " their"} name, so {last.unmatched_count === 1 ? "it is" : "they are"} kept
              but not tied to a render: {last.unmatched.slice(0, UNMATCHED_SHOWN).join(", ")}
              {last.unmatched_count > UNMATCHED_SHOWN ? `, and ${last.unmatched_count - UNMATCHED_SHOWN} more` : ""}.
            </p>
          ) : null}
        </div>
      ) : null}

      {data && data.tests.length ? (
        <div className="as-tests">
          {data.tests.map((t) => (
            <div key={t.group_id} className="as-test">
              <div className="as-test-head">
                <b>{t.test || "Versions of one ad"}</b>
                <span className={t.winner ? "is-won" : ""}>
                  {t.winner ? <Trophy size={12} strokeWidth={2} aria-hidden /> : null} {t.verdict}
                </span>
              </div>
              <ol>
                {t.ads.map((a) => (
                  <li key={`${a.platform}-${a.ad_name}`} className={a.code && a.code === t.winner ? "is-won" : ""}>
                    <span>{a.variant ?? a.ad_name}</span>
                    <span className="mono">{a.cpa !== null ? `${money(a.cpa, a.currency)} / result` : "no results yet"}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      ) : null}

      {ads.length ? (
        <div className="as-table-wrap">
          <table className="as-table">
            <thead>
              <tr>
                <th scope="col">Ad</th>
                <th scope="col">Spent</th>
                <th scope="col">Results</th>
                <th scope="col">Per result</th>
                <th scope="col">CTR</th>
                <th scope="col">Return</th>
              </tr>
            </thead>
            <tbody>
              {ads.map((a) => (
                <tr key={`${a.platform}-${a.ad_name}`}>
                  <th scope="row">
                    <span className="as-ad-name">{a.ad_name}</span>
                    <span className="as-ad-meta">
                      {PLATFORM[a.platform] ?? a.platform}
                      {a.code ? <span className="mono"> · {a.code}</span> : <em> · no ad code</em>}
                      {a.variant ? <span className="as-ad-variant">{a.variant}</span> : null}
                    </span>
                  </th>
                  <td className="mono">{money(a.spend, a.currency)}</td>
                  <td className="mono">{count(a.results)}</td>
                  <td className="mono">{money(a.cpa, a.currency)}</td>
                  <td className="mono">{percent(a.ctr)}</td>
                  <td className="mono">{times(a.roas)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : data ? (
        <p className="as-hint">No ad reports yet.</p>
      ) : null}

      {newest ? (
        <p className="as-results-imports">
          Last report: {newest.filename || PLATFORM[newest.platform] || "CSV"} · {newest.rows} row
          {newest.rows === 1 ? "" : "s"}
          <button type="button" className="as-link" onClick={() => void undo(newest.import_id)} title="Take this report back out">
            <X size={12} strokeWidth={2} aria-hidden /> Remove
          </button>
        </p>
      ) : null}
    </section>
  );
}
