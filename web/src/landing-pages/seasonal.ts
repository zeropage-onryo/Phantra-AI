// Seasonal pages (2026-10-27, Mike: a Halloween page "can get its own tab
// that makes it spooky for halloween but ends the day after halloween").
//
// A page with a `season` is a normal page all year: it keeps its URL, its
// place in the sitemap, the footer's Tools column and the /make hub's
// Seasonal group, so Google keeps it indexed and it ranks again next year.
// Only two things follow the calendar: the header's tab for it, and its
// seasonal look (the entry's `season.accent` and the atmosphere layer).
// Taking the PAGE down after the season (a 404, a redirect, a noindex)
// would throw that ranking away; nothing here ever does.
//
// Pure: no imports, so web/tests/seasonal.test.mjs runs it as is.

export type Season = {
  /** First day the season is on, "MM-DD", inclusive. */
  start: string;
  /** Last day the season is on, "MM-DD", inclusive. A window that ends
   *  before it starts wraps the new year (Dec 20 to Jan 2). */
  end: string;
  /** The header tab's label while the season is on. */
  tab: string;
  /** Whose calendar decides the day. Default America/New_York. */
  timeZone?: string;
};

const MONTH_DAY = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

/** True for "MM-DD" with a real month and a day up to 31. */
export function isMonthDay(value: string): boolean {
  return MONTH_DAY.test(value);
}

/** Today's "MM-DD" on the given zone's wall clock. */
export function monthDayIn(now: Date, timeZone = "America/New_York"): string {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone, month: "2-digit", day: "2-digit" }).formatToParts(now);
  const month = parts.find((p) => p.type === "month")?.value ?? "01";
  const day = parts.find((p) => p.type === "day")?.value ?? "01";
  return `${month}-${day}`;
}

/** Is the season on at `now`? "MM-DD" strings compare in calendar order. */
export function inSeason(season: Season, now: Date = new Date()): boolean {
  if (!isMonthDay(season.start) || !isMonthDay(season.end)) return false;
  const today = monthDayIn(now, season.timeZone);
  return season.start <= season.end
    ? today >= season.start && today <= season.end
    : today >= season.start || today <= season.end;
}
