/* The calendar's clock (2026-10-22, docs/tasks/task-calendar.md): every
   date on the page is the person's local time (the browser's zone); the
   API speaks ISO 8601 in UTC. Weeks start on Monday. */

export const DAY_MS = 24 * 60 * 60 * 1000;
export const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

/** the browser's IANA zone, for posting times and the drawer's words */
export const localZone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
};

export const startOfDay = (d: Date) => {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
};

/** Monday 00:00 of the week holding `d` */
export const startOfWeek = (d: Date) => {
  const x = startOfDay(d);
  const back = (x.getDay() + 6) % 7;
  x.setDate(x.getDate() - back);
  return x;
};

export const addDays = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};

export const addMonths = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(1);
  x.setMonth(x.getMonth() + n);
  return x;
};

export const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** YYYY-MM-DD in local time, the key a day's posts are grouped under */
export const dayKey = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

/** what a datetime-local input holds for a Date */
export const toLocalInput = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

export const fmtTime = (d: Date) => d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
export const fmtDay = (d: Date) => d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
export const fmtWhen = (d: Date) => `${fmtDay(d)} · ${fmtTime(d)}`;
export const fmtHour = (h: number) => (h === 0 ? "12 AM" : h < 12 ? `${h} AM` : h === 12 ? "12 PM" : `${h - 12} PM`);

/** "Oct 19 – 25, 2026" / "Oct 27 – Nov 2, 2026" */
export const fmtWeekRange = (monday: Date) => {
  const sunday = addDays(monday, 6);
  const m = (d: Date) => d.toLocaleDateString(undefined, { month: "short" });
  if (monday.getMonth() === sunday.getMonth()) {
    return `${m(monday)} ${monday.getDate()} – ${sunday.getDate()}, ${sunday.getFullYear()}`;
  }
  return `${m(monday)} ${monday.getDate()} – ${m(sunday)} ${sunday.getDate()}, ${sunday.getFullYear()}`;
};

export const fmtMonth = (d: Date) => d.toLocaleDateString(undefined, { month: "long", year: "numeric" });

/** a Date from a post's publish_at (null = now) */
export const whenOf = (iso: string | null | undefined) => (iso ? new Date(iso) : new Date());

/** the 15-minute mark nearest a y offset inside a column of `hourPx` per hour */
export const snapHour = (y: number, hourPx: number) => {
  const raw = y / hourPx;
  const quarter = Math.round(raw * 4) / 4;
  return Math.max(0, Math.min(23.75, quarter));
};

export const atHour = (day: Date, hour: number) => {
  const x = startOfDay(day);
  x.setMinutes(Math.round(hour * 60));
  return x;
};
