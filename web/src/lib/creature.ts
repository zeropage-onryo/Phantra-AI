/* The floating creature's place and its clicks (2026-10-09, the "Creature
   Companions" design canvas; Mike's calls: the creature floats at 320px, a
   click opens the dock, a double-click makes it small and a click brings it
   back, and it can be parked on either side -- the dock then seats it at
   that end). Pure, so web/tests/creature.test.mjs can hold it to that.

   Kept per BROWSER (localStorage), not per account: where a thing sits on a
   screen is a fact about the screen. */

export type Side = "left" | "right";
/* y is the creature's bottom edge, in px up from the bottom of the window */
export type Park = { side: Side; y: number; small: boolean };
export const DEFAULT_PARK: Park = { side: "right", y: 24, small: false };

const PARK_KEY = "phantra.assistant.park";
const DOCK_KEY = "phantra.assistant.dock";

/** whatever was stored, as a park; anything unreadable is the default */
export function readPark(raw: string | null | undefined): Park {
  try {
    const p = JSON.parse(raw || "") as Partial<Park> | null;
    if (!p || typeof p !== "object") return { ...DEFAULT_PARK };
    const y = typeof p.y === "number" && Number.isFinite(p.y) ? Math.max(0, Math.round(p.y)) : DEFAULT_PARK.y;
    return { side: p.side === "left" ? "left" : "right", y, small: p.small === true };
  } catch {
    return { ...DEFAULT_PARK };
  }
}

export function loadPark(): Park {
  try {
    return readPark(localStorage.getItem(PARK_KEY));
  } catch {
    return { ...DEFAULT_PARK };
  }
}

export function savePark(p: Park): void {
  try {
    localStorage.setItem(PARK_KEY, JSON.stringify(p));
  } catch {
    /* a private window: it simply forgets */
  }
}

/** Where a drag lets go: the nearer side, and the height it was dropped at,
    kept inside the window (`top` is what the page's header needs). */
export function snapPark(
  box: { left: number; top: number; width: number; height: number },
  view: { width: number; height: number },
  small: boolean,
  top = 72,
): Park {
  const side: Side = box.left + box.width / 2 < view.width / 2 ? "left" : "right";
  const highest = Math.max(0, view.height - top - box.height);
  const y = Math.min(highest, Math.max(0, Math.round(view.height - (box.top + box.height))));
  return { side, y, small };
}

/* How long a click waits to see whether it is the first half of a
   double-click. Short, so opening the dock never feels slow. */
export const DOUBLE_MS = 240;

/** What a click on the creature means. `detail` is the browser's click
    count: 0 is a keyboard press (Enter or Space), which acts at once.
    - now:    act at once (open or lower the dock; small: come back)
    - later:  a first click; act after DOUBLE_MS unless a second comes
    - double: the second click of a pair; make it small instead
    - ignore: a third click, or the second click on a small creature
      (its first click already brought it back) */
export type Intent = "now" | "later" | "double" | "ignore";
export function clickIntent(detail: number, small: boolean): Intent {
  if (small) return detail <= 1 ? "now" : "ignore";
  if (detail <= 0) return "now";
  if (detail === 1) return "later";
  return detail === 2 ? "double" : "ignore";
}

/* The dock's height: dragged by its handle, remembered per browser. */
export const DOCK = { min: 260, start: 360, share: 0.72 } as const;

export function clampDock(h: number, viewHeight: number): number {
  const most = Math.max(DOCK.min, Math.round(viewHeight * DOCK.share));
  return Math.round(Math.min(most, Math.max(DOCK.min, Number.isFinite(h) ? h : DOCK.start)));
}

export function loadDockHeight(): number {
  try {
    const n = Number(localStorage.getItem(DOCK_KEY));
    return n > 0 ? n : DOCK.start;
  } catch {
    return DOCK.start;
  }
}

export function saveDockHeight(h: number): void {
  try {
    localStorage.setItem(DOCK_KEY, String(Math.round(h)));
  } catch {
    /* forgets */
  }
}

/* The Create page (2026-10-10, Mike: "the creature small in the corner of the
   create page as well"). The Guide talks in the composer's own box there, so
   the creature keeps the person company at its small size -- whatever size it
   rests at on the other pages, and without its thoughts. Only how it is DRAWN
   on that page: the stored park is left alone, so leaving Create brings back
   the size the person chose. */
export function isCreatePage(pathname: string): boolean {
  // the home and, since 2026-10-22, the conversation's own page
  const p = pathname.replace(/\/$/, "");
  return p === "/studio" || p === "/studio/chat";
}

/* Settings (2026-10-11, Mike's pick). At its full size the creature sat over
   the right edge of the settings column, which is where every row's control
   is, so it rests small there too, by the same rule as Create: drawn small,
   a click opens the dock, the stored park untouched. */
export function isSettingsPage(pathname: string): boolean {
  return /^\/studio\/settings(\/|$)/.test(pathname);
}

/* A brand kit's page (2026-10-20, docs/tasks/task-brand-kit.md): its right
   column is the live preview -- the caption sample, the end card, the look
   line -- and the creature at full size sat over it. Same rule as Settings. */
export function isBrandKitPage(pathname: string): boolean {
  return /^\/studio\/brand\/[^/]+\/?$/.test(pathname);
}

/** the pages the creature is DRAWN small on, whatever size it rests at on
 *  the others; it cannot be made big there, and a drag keeps the stored size.
 *  Create left this list on 2026-10-16 (Mike: "still tiny" there): it rests
 *  at its full size on Create, without its thoughts (the composer holds the
 *  thread), and a double-click still makes it small. */
export function restsSmall(pathname: string): boolean {
  return isSettingsPage(pathname) || isBrandKitPage(pathname);
}

export function restingPark(park: Park, pathname: string): Park {
  return restsSmall(pathname) ? { ...park, small: true } : park;
}

/* The corner (2026-10-27, Mike: "move Vesper to the top left corner,
   miniaturize him, and when you click on him it takes you to the Create chat
   box with him small behind it ready to help -- that chat box should be the
   super computer"). Everywhere but Create he sits small in the header's top
   left corner; a click goes to Create, where the composer is the one place
   to talk to him, and he peeks over the box's top edge. The click leaves a
   note for this tab so the box takes focus when Create mounts. */
const TALK_KEY = "phantra.assistant.talk";

/** the corner was clicked: Create should focus its box when it mounts */
export function askToTalk(): void {
  try {
    sessionStorage.setItem(TALK_KEY, "1");
  } catch {
    /* a private window: Create just opens without focusing */
  }
}

/** read once by Create: was it opened from the corner? */
export function takeTalk(): boolean {
  try {
    const asked = sessionStorage.getItem(TALK_KEY) === "1";
    sessionStorage.removeItem(TALK_KEY);
    return asked;
  } catch {
    return false;
  }
}
