"use client";

/* Settings → Usage (2026-10-11): where the credits went.

   The top is the last 30 days -- one number, a bar a day, and the same
   spend by model -- and under it the ledger itself, read back a line at a
   time: every hold, settle, return, grant and expiry, each with the
   balance it left. All of it is GET /api/billing/history
   (src/credit_history.py), in CREDITS; a provider's price never reaches
   this page. Nothing here spends.

   A render is two lines on purpose: the hold that took the credit, then
   how it finished. That is what the ledger recorded, and it is why the
   "balance after" column can be exact. */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, ChartNoAxesColumn, ReceiptText } from "lucide-react";
import {
  HISTORY_FILTERS,
  countText,
  dayLabel,
  foldTotals,
  kindNote,
  kindWord,
  matches,
  peakDay,
  signed,
  type Entry,
  type EntryKind,
  type History,
  type HistoryFilter,
  type Summary,
} from "@/lib/credit-history";
import { countedElsewhere, creditsText, num, stamp } from "@/lib/credits";
import { SECTIONS } from "@/lib/settings-sections";
import { BALANCE_EVENT, getCreditHistory, sceneHref } from "@/lib/studio-api";
import { useShell } from "@/components/studio/shell";
import { SpendChart } from "@/components/studio/settings/spend-chart";
import {
  Badge,
  Button,
  Chip,
  EmptyState,
  Notice,
  SectionHeader,
  SettingsCard,
  Skeleton,
  Stat,
  errorText,
  type Tone,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "usage")!;

const TONE: Record<EntryKind, Tone> = {
  grant: "ok",
  hold: "neutral",
  settle: "neutral",
  release: "ok",
  expire: "warn",
};

const when = (iso: string) => {
  const d = stamp(iso);
  return d
    ? d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    : "";
};

function Opens({ entry }: { entry: Entry }) {
  if (!entry.ref) return null;
  const href = entry.ref.kind === "scene" ? sceneHref(entry.ref.id) : `/studio/assets?open=${entry.ref.id}`;
  return (
    <Link className="zset-link zset-hist-open" href={href}>
      {entry.ref.kind === "scene" ? entry.ref.title || "Open the scene" : "Open in the Library"}
      <ArrowUpRight strokeWidth={1.7} aria-hidden />
    </Link>
  );
}

function Last30({ summary }: { summary: Summary }) {
  const peak = peakDay(summary.days);
  if (!summary.spent)
    return (
      <EmptyState icon={ChartNoAxesColumn} title={`Nothing spent in the last ${summary.window_days} days`}>
        Stills, clips and effects show up here on the day their credits are held. Writing a scene is included and never
        appears.
      </EmptyState>
    );
  return (
    <div className="zset-usage">
      <div className="zset-usage-main">
        <Stat value={num(summary.spent)} label={`credits spent · last ${summary.window_days} days`} />
        {peak ? (
          <p className="zset-note">
            Busiest day: <b>{dayLabel(peak.day)}</b>, {creditsText(peak.credits)}. Days are counted in UTC.
          </p>
        ) : null}
        <SpendChart days={summary.days} />
      </div>
      <div className="zset-usage-side">
        <h4>By model</h4>
        <ul>
          {foldTotals(summary.totals).map((t) => (
            <li key={t.label}>
              <span>
                <b>{t.label}</b>
                <i>{t.label === "Everything else" ? `${num(t.count)} more` : countText(t.count, t.group)}</i>
              </span>
              <span className="zset-table-num">{num(t.credits)}</span>
              <span className="zset-meter" aria-hidden>
                <span style={{ width: `${Math.max(2, Math.round((t.credits / summary.spent) * 100))}%` }} />
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function UsageSection() {
  const { me } = useShell();
  const account = me?.account?.id ?? null;
  const [items, setItems] = useState<Entry[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  // whose history this is: the person's first workspace, whichever is open
  const [counted, setCounted] = useState<History["account"]>(null);
  const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  // a re-read keeps what is on screen, dimmed, instead of flashing a skeleton
  const [stale, setStale] = useState(false);
  const [filter, setFilter] = useState<HistoryFilter>("all");

  const load = useCallback(() => {
    if (account === null) return;
    getCreditHistory()
      .then((res) => {
        setItems(res.items);
        setSummary(res.summary ?? null);
        setCounted(res.account ?? null);
        setNext(res.next);
        setError(null);
      })
      .catch((err) => setError(errorText(err, "Could not read your history")))
      .finally(() => setStale(false));
  }, [account]);
  // a re-read (credit moved, or "Try again"): what is on screen stays, dimmed
  const reload = useCallback(() => {
    setStale(true);
    load();
  }, [load]);
  useEffect(() => {
    if (account === null) return;
    load();
    // an approve took a hold, a render settled: read it again
    window.addEventListener(BALANCE_EVENT, reload);
    return () => window.removeEventListener(BALANCE_EVENT, reload);
  }, [account, load, reload]);

  const more = async () => {
    if (!next) return;
    setLoadingMore(true);
    try {
      const res = await getCreditHistory(next);
      setItems((was) => [...(was ?? []), ...res.items]);
      setNext(res.next);
    } catch (err) {
      setError(errorText(err, "Could not read more of your history"));
    } finally {
      setLoadingMore(false);
    }
  };

  const shown = (items ?? []).filter((e) => matches(e, filter));
  const elsewhere = countedElsewhere(counted, me?.account);
  const filterName = HISTORY_FILTERS.find((f) => f.id === filter)?.label.toLowerCase() ?? "";

  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />

      {error ? (
        <Notice tone="err">
          {error}{" "}
          <button type="button" className="zset-link" onClick={reload}>
            Try again
          </button>
        </Notice>
      ) : null}

      <SettingsCard title={`Last ${summary?.window_days ?? 30} days`}>
        {summary ? (
          <div style={stale ? { opacity: 0.55 } : undefined}>
            <Last30 summary={summary} />
          </div>
        ) : error ? (
          <EmptyState icon={ChartNoAxesColumn} title="Your spend could not be read" />
        ) : (
          <div className="zset-card-pad" style={{ display: "grid", gap: 14 }} aria-busy="true" aria-label="Loading your spend">
            <Skeleton width={110} height={30} />
            <Skeleton width="38%" height={10} />
            <Skeleton width="100%" height={150} />
          </div>
        )}
        {elsewhere ? (
          <p className="zset-note zset-foot">
            This is the usage of <b>{elsewhere.counted}</b>, the first workspace you joined. You have{" "}
            <b>{elsewhere.open}</b> open.
          </p>
        ) : null}
      </SettingsCard>

      <section className="zset-group" aria-labelledby="history-title">
        <div className="zset-group-head zset-group-head-split">
          <h3 id="history-title">History</h3>
          <div className="zset-chips" role="group" aria-label="Show">
            {HISTORY_FILTERS.map((f) => (
              <Chip key={f.id} pressed={filter === f.id} onClick={() => setFilter(f.id)}>
                {f.label}
              </Chip>
            ))}
          </div>
        </div>
        <div className="zset-card">
          {items === null ? (
            error ? (
              <EmptyState icon={ReceiptText} title="Your history could not be read" />
            ) : (
              <div aria-busy="true" aria-label="Loading your history">
                {[0, 1, 2, 3].map((i) => (
                  <div className="zset-row" key={i}>
                    <div style={{ display: "grid", gap: 8 }}>
                      <Skeleton width={i % 2 ? "44%" : "58%"} />
                      <Skeleton width="30%" height={10} />
                    </div>
                    <Skeleton width={64} />
                  </div>
                ))}
              </div>
            )
          ) : items.length === 0 ? (
            <EmptyState icon={ReceiptText} title="No history yet">
              When credits arrive or a render holds some, each movement is listed here with the balance it left.
            </EmptyState>
          ) : shown.length === 0 ? (
            <EmptyState icon={ReceiptText} title={`No ${filterName} in what is loaded`}>
              {next ? "Older history may have some. Load more to look further back." : "Nothing of that kind in your history."}
            </EmptyState>
          ) : (
            <table className="zset-table zset-hist" style={stale ? { opacity: 0.55 } : undefined}>
              <caption className="sr-only">Your credit history, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">Activity</th>
                  <th scope="col" className="zset-num">
                    Credits
                  </th>
                  <th scope="col" className="zset-num zset-hist-bal">
                    Balance after
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((e) => (
                  <tr key={e.id}>
                    <th scope="row">
                      <span className="zset-hist-line">
                        <Badge tone={TONE[e.kind]}>{kindWord(e.kind)}</Badge>
                        {e.what}
                      </span>
                      <span className="zset-hist-sub">
                        <time dateTime={e.at}>{when(e.at)}</time>
                        {kindNote(e) ? <> · {kindNote(e)}</> : null}
                        <Opens entry={e} />
                      </span>
                    </th>
                    <td className="zset-num" data-sign={e.credits > 0 ? "+" : e.credits < 0 ? "-" : "0"}>
                      {signed(e.credits)}
                    </td>
                    <td className="zset-num zset-hist-bal">{num(e.balance_after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {next ? (
            <div className="zset-more">
              <Button onClick={more} disabled={loadingMore}>
                {loadingMore ? "Loading…" : "Load more"}
              </Button>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}
