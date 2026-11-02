/* What an ad did once it ran (2026-10-29, src/ad_results.py,
   docs/tasks/task-ad-results.md).

   The person exports the ad-level report from Meta Ads Manager or TikTok Ads
   Manager as CSV and drops it on the Ad Studio. Each output's AD CODE
   (`adCode`, "PH" and its Library id) in the ad's name is what joins a row to
   its render; the server reads it back (src/ad_results.py `codes_in`), and
   tests/test_ad_results.py holds the prefix the same on both sides.

   The money here is the person's OWN ad spend, in the currency their export
   names, printed through Intl -- never a Phantra price (the studio shows
   credits for those). Pure (no imports, so node --test reads it): web/tests/ad-results.test.mjs;
   the fetches are lib/ad-results-api.ts. */
export const AD_CODE_PREFIX = "PH";

/** The ad code of one Library output. */
export const adCode = (assetId: number | string) => `${AD_CODE_PREFIX}${assetId}`;

export type AdRow = {
  platform: string;
  ad_name: string;
  currency: string | null;
  asset_id: number | null;
  concept_id: number | null;
  code: string | null;
  variant: string | null;
  group_id: string | null;
  test: string | null;
  first_day: string | null;
  last_day: string | null;
  spend: number;
  impressions: number;
  clicks: number;
  results: number;
  result_type: string | null;
  revenue: number | null;
  ctr: number | null;
  cpa: number | null;
  roas: number | null;
};

export type AdTest = {
  group_id: string;
  test: string | null;
  ads: AdRow[];
  winner: string | null;
  verdict: string;
};

export type AdImport = {
  import_id: string;
  platform: string;
  filename: string | null;
  imported_at: string;
  rows: number;
};

export type AdResults = { ads: AdRow[]; tests: AdTest[]; imports: AdImport[]; unmatched: number };

export type ImportResult = {
  import_id: string;
  platform: string;
  currency: string | null;
  rows: number;
  added: number;
  updated: number;
  matched: number;
  skipped: number;
  unmatched: string[];
  unmatched_count: number;
};

/** The person's own money, in their export's currency; a bare number when
    the export named none. */
export function money(value: number | null | undefined, currency: string | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (currency && /^[A-Z]{3}$/.test(currency)) {
    try {
      return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
    } catch {
      // an unknown code: fall through to the plain number
    }
  }
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export const percent = (r: number | null | undefined) =>
  r === null || r === undefined ? "—" : `${(r * 100).toFixed(r < 0.1 ? 2 : 1)}%`;

export const times = (r: number | null | undefined) => (r === null || r === undefined ? "—" : `${r.toFixed(2)}x`);

export const count = (n: number) =>
  Number.isInteger(n) ? n.toLocaleString("en-US") : n.toLocaleString("en-US", { maximumFractionDigits: 1 });

/** The import's outcome in one sentence. */
export function importLine(r: ImportResult): string {
  const where = r.platform === "meta" ? "Meta" : r.platform === "tiktok" ? "TikTok" : "your";
  const rows = `${r.rows} ad row${r.rows === 1 ? "" : "s"} from ${where} report`;
  const changed = r.added && r.updated ? `${r.added} new, ${r.updated} updated` : r.added ? `${r.added} new` : `${r.updated} updated`;
  const matched = r.matched ? `${r.matched} matched a render` : "none matched a render";
  return `${rows} · ${changed} · ${matched}.`;
}

/** Ads best first: the ones with results by cost per result, then by spend. */
export function ranked(ads: AdRow[]): AdRow[] {
  return [...ads].sort((a, b) => {
    if ((a.cpa === null) !== (b.cpa === null)) return a.cpa === null ? 1 : -1;
    if (a.cpa !== null && b.cpa !== null && a.cpa !== b.cpa) return a.cpa - b.cpa;
    return b.spend - a.spend;
  });
}
