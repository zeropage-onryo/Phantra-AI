/* The ad card in the composer (2026-10-21, step 3 of
   docs/tasks/task-url-to-ad.md). The brain proposes `make_ad` with a brief;
   the page asks the motion ad for a PREVIEW (the beats, checked, nothing
   saved -- POST /api/cut/motion-ad {preview: true}), the person reads them,
   changes a headline or a voiceover line or removes a beat, and Build makes
   the cut from exactly those beats (the same route with `script`, no model
   call). Both are free. Pure: the page holds the state, this shapes it.

   Kept simple on purpose (Mike, "make it simplistic"): a beat's headline
   and voiceover are the only things changed here; everything else is the
   editor's, once it is built. */

export const AD_TOOL = "make_ad";
export const AD_ASPECTS = ["16:9", "9:16", "1:1"] as const;
export type AdAspect = (typeof AD_ASPECTS)[number];
export const AD_SECONDS_DEFAULT = 20;

export type AdBeat = {
  headline: string;
  big_word: string;
  card: number | null;
  card_caption: string;
  label: string;
  background: string;
  seconds: number;
  picture?: number | null;
  move?: string;
  voiceover?: string;
};

export type AdThing = { handle: string; name: string };

export type AdState = {
  id: string;
  brief: string;
  seconds: number;
  aspect: AdAspect;
  status: "writing" | "ready" | "building" | "built" | "failed";
  title?: string;
  beats?: AdBeat[];
  warnings?: string[];
  cards?: AdThing[];
  pictures?: AdThing[];
  kit?: string | null;
  /** the beat open for changes (1-based), if any */
  open?: number | null;
  /** the person changed the beats since the preview: say so on the card */
  edited?: boolean;
  cutId?: string;
  error?: string;
};

export const isAdTool = (tool?: string | null) => tool === AD_TOOL;

/** A new card from the brain's proposal. Off-list values were refused by
 *  the server (guide_tools.check_ad); the defaults are the route's. */
export function beginAd(id: string, args: { brief?: unknown; seconds?: unknown; aspect?: unknown }): AdState {
  const aspect = AD_ASPECTS.includes(args.aspect as AdAspect) ? (args.aspect as AdAspect) : "16:9";
  const seconds = typeof args.seconds === "number" && args.seconds > 0 ? Math.round(args.seconds) : AD_SECONDS_DEFAULT;
  return {
    id,
    brief: typeof args.brief === "string" ? args.brief.trim() : "",
    seconds,
    aspect,
    status: "writing",
  };
}

/** The route's body for the preview (no script) or the build (the card's beats). */
export function adRequest(s: AdState, projectId: number | null | undefined, build: boolean) {
  const body: Record<string, unknown> = {
    brief: s.brief,
    seconds: s.seconds,
    aspect: s.aspect,
    ...(projectId != null ? { project_id: projectId } : {}),
  };
  if (!build) return { ...body, preview: true };
  return {
    ...body,
    script: { title: s.title ?? "Ad", beats: s.beats ?? [] },
    cards: (s.cards ?? []).map((c) => c.handle),
    pictures: (s.pictures ?? []).map((p) => p.handle),
    kit_pictures: false,
  };
}

/** The preview job's answer onto the card. */
export function withPreview(s: AdState, job: Record<string, unknown>): AdState {
  return {
    ...s,
    status: "ready",
    title: typeof job.title === "string" ? job.title : "Ad",
    beats: Array.isArray(job.beats) ? (job.beats as AdBeat[]) : [],
    warnings: Array.isArray(job.warnings) ? (job.warnings as string[]) : [],
    cards: Array.isArray(job.cards) ? (job.cards as AdThing[]) : [],
    pictures: Array.isArray(job.pictures) ? (job.pictures as AdThing[]) : [],
    kit: typeof job.brand_kit === "string" ? job.brand_kit : null,
    open: null,
    edited: false,
  };
}

/** Each beat's window, in seconds, in order. */
export function windows(beats: AdBeat[]): { start: number; end: number }[] {
  let at = 0;
  return beats.map((b) => {
    const start = at;
    at += Number(b.seconds) || 0;
    return { start: round1(start), end: round1(at) };
  });
}

const round1 = (n: number) => Math.round(n * 10) / 10;
export const span = (w: { start: number; end: number }) => `${trim(w.start)}–${trim(w.end)}s`;
const trim = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/** What a beat sits on, in words: its screen, its photo, or the colour. */
export function onWhat(b: AdBeat, s: AdState): string {
  if (b.picture && s.pictures?.[b.picture - 1]) return `photo · ${s.pictures[b.picture - 1].name}`;
  if (b.card && s.cards?.[b.card - 1]) return `screen · ${s.cards[b.card - 1].name}`;
  return b.background === "primary" ? "brand colour" : "flat";
}

/** One beat changed: only its headline and voiceover line. */
export function editBeat(s: AdState, n: number, change: { headline?: string; voiceover?: string }): AdState {
  const beats = (s.beats ?? []).map((b, i) =>
    i === n - 1
      ? {
          ...b,
          ...(change.headline !== undefined ? { headline: change.headline } : {}),
          ...(change.voiceover !== undefined ? { voiceover: change.voiceover } : {}),
        }
      : b,
  );
  return { ...s, beats, edited: true };
}

/** A beat removed; the others are fitted back to the length when it is built.
 *  The last beat is never removed: an ad has at least one. */
export function removeBeat(s: AdState, n: number): AdState {
  const beats = s.beats ?? [];
  if (beats.length <= 1) return s;
  return { ...s, beats: beats.filter((_, i) => i !== n - 1), open: null, edited: true };
}

/** The voiceover, read in order. */
export const scriptOf = (beats: AdBeat[]) =>
  beats
    .map((b) => (b.voiceover ?? "").trim())
    .filter(Boolean)
    .join(" ");

export const wordCount = (text: string) => (text.trim() ? text.trim().split(/\s+/).length : 0);

/** Build is possible only on a written card with a beat that says something. */
export const canBuild = (s: AdState) =>
  s.status === "ready" && !!s.beats?.length && s.beats.some((b) => b.headline.trim() || b.big_word || b.card || b.picture);

export const editorHref = (cutId: string) => `/studio/cut/${encodeURIComponent(cutId)}`;
