/* Dubbing in the composer (src/dubbing.py through /api/dubbing/*;
   docs/tasks/task-dubbing.md, 2026-10-26).

   A clip with speech on it, spoken again in another language in the same
   voices. Two ways it starts, both ending on one card in the thread:
   `/dub`, or the brain's dub_clip proposal (which may name a clip by
   number and a language). The card asks for the clip, the language and the
   person's word that the voices are theirs or their owners agreed; its one
   click, Render, spends -- at the price the card showed (the server's
   /api/dubbing/quote, asked again whenever a choice that moves it changes).

   Pure and import-free on purpose: tests/dubbing.test.mjs runs this file
   as it is. */

export const DUB_TOOL = "dub_clip";

/** Something the dub could act on (the shape of lib/effects.ts Candidate). */
export type ClipChoice = {
  /** what the server is sent: `gen:<id>` / `asset:<id>`, never an address */
  ref: string;
  kind: "image" | "clip";
  thumb?: string;
  from: string;
};

/** GET /api/dubbing */
export type DubMenu = {
  languages: { code: string; name: string }[];
  max_seconds: number;
  speakers_max: number;
  label: string;
  ready: boolean;
  exempt: boolean;
};

export type Paid = { credits: number; charged: boolean };

/** One dub, on its way to a clip: saved on its turn (`Turn.dub`). */
export type DubState = {
  id: string;
  clip: ClipChoice | null;
  /** the code of the language to dub INTO, or "" until one is picked */
  target: string;
  /** an ISO 639-1 code, or "" to let the model tell */
  source: string;
  /** how many people talk, as typed; "" to let the model count */
  speakers: string;
  consent: boolean;
  /** what Render was pressed at */
  paid?: Paid;
};

/** The clips the card offers: clips only, each once, in order. */
export function clipChoices(all: ClipChoice[]): ClipChoice[] {
  const seen = new Set<string>();
  return all.filter((c) => c.kind === "clip" && !seen.has(c.ref) && (seen.add(c.ref), true));
}

/** A new card. The clip is the one the proposal pointed at, else the
    newest. The language is the one the proposal named if the menu offers
    it, else none: the person picks. Consent is never pre-ticked. */
export function beginDub(
  all: ClipChoice[],
  id: string,
  given: { on?: ClipChoice | null; target?: string | null } = {},
  menu?: Pick<DubMenu, "languages"> | null,
): DubState {
  const on = given.on && given.on.kind === "clip" ? given.on : null;
  const code = (given.target ?? "").trim().toLowerCase();
  const offered = menu ? menu.languages.some((l) => l.code === code) : false;
  return {
    id,
    clip: on ?? clipChoices(all)[0] ?? null,
    target: offered ? code : "",
    source: "",
    speakers: "",
    consent: false,
  };
}

/** The speakers box as the number the server takes, or null (let the model
    count). NaN-safe: anything that is not a whole 1..max is null. */
export function speakerCount(text: string, max = 50): number | null {
  const t = text.trim();
  if (!/^\d+$/.test(t)) return null;
  const n = Number(t);
  return n >= 1 && n <= max ? n : null;
}

/** What stops the dub from being priced: "" when nothing does. The consent
    box is not here: the price shows before it is ticked. */
export function dubMissing(s: DubState, menu: Pick<DubMenu, "languages" | "speakers_max">): string {
  if (!s.clip) return "Pick the clip to dub";
  if (!s.target) return "Pick the language to dub it into";
  if (!menu.languages.some((l) => l.code === s.target)) return "That language is not offered";
  const src = s.source.trim().toLowerCase();
  if (src && !/^[a-z]{2}$/.test(src)) return "The spoken language is a two-letter code, like en";
  if (src && src === s.target) return "The clip is already in that language: pick a different one";
  const sp = s.speakers.trim();
  if (sp && speakerCount(sp, menu.speakers_max) === null) return `People speaking is a whole number, 1 to ${menu.speakers_max}`;
  return "";
}

/** The body /api/dubbing/{quote,run} take; null until there is one. */
export function dubRequest(s: DubState, projectId?: number | null) {
  if (!s.clip || !s.target) return null;
  const speakers = speakerCount(s.speakers);
  return {
    source: s.clip.ref,
    target_language: s.target,
    source_language: s.source.trim().toLowerCase(),
    ...(speakers ? { speakers } : {}),
    consent: s.consent,
    ...(projectId ? { project_id: projectId } : {}),
  };
}

/** The key a price depends on: consent and the project do not move it. */
export const dubPriceKey = (s: DubState) => {
  const r = dubRequest(s);
  return r ? JSON.stringify([r.source, r.target_language, r.source_language, r.speakers ?? null]) : "";
};

/** A language's name for a code, else the code. */
export const languageName = (menu: Pick<DubMenu, "languages"> | null | undefined, code: string) =>
  menu?.languages.find((l) => l.code === code)?.name ?? code;

/** "144 credits", or "… · not charged" on an exempt account */
export const priceLine = (p: Paid, exempt = false) =>
  p.charged && !exempt ? `${p.credits.toLocaleString()} credits` : `${p.credits.toLocaleString()} credits · not charged`;
