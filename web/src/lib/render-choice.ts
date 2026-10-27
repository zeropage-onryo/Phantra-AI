/* The Queue card's renderer pick, as pure functions (2026-09-17).

   Ported from app/static/studio/queue.js so the React Queue and the vanilla
   one cannot disagree about what a card opens on or what its button says:

   - `usable` needs BOTH a configured renderer and a reachable model. A
     model always reports available (render_specs has no per-account
     probe), so reading only the model let an unconfigured renderer win the
     default. Since 2026-09-26 the only renderer is fal.ai, on the
     operator's key; the catalogue stays keyed by provider regardless.
   - `firstUsable` is the CHEAPEST usable model at its own default length,
     not the first in registry order -- a card quietly defaulting to a $3
     Veo render is a silent spend. Unpriced models sort last.
   - `defaultPick`: the plan leads when this account can render it, else
     the cheapest it can; a plan nobody can render is not a default (the
     2026-09-11 dead-button fix).
   - `held` keeps a pick by concept id for the life of the tab, so it
     survives repaints AND leaving the page and coming back. Dropped once
     the card is approved or rejected.
   - `estimate` ORDERS models, it is never shown: `firstUsable` sorts by
     it to find the cheapest. tests/test_providers.py pins this shape
     (flat, or a per-second rate optionally keyed by frame) to the adapters.
     The studio shows CREDITS, never dollars (2026-10-08): every number a
     person reads is the server's (pricing.display), and a pick it has not
     priced yet says "pricing…".
   - A TIMED scene is priced by the SERVER (src/pricing.py): each shot
     renders at its window's length fitted UP to what the model can make,
     and that fitting is done once, on the server, never here -- the
     listing serves `quote` for the card's default pick and /quote answers
     any other. `planFor` takes that quote; without one it says "pricing…"
     rather than make a number up. There is no fitSeconds twin any more.

   No "@/..." imports: tests/render-choice.test.mjs loads this with node. */

export type AxisLike = {
  kind: "choices" | "range" | "fixed";
  values?: (string | number)[];
  min?: number;
  max?: number;
  default?: string | number | null;
  note?: string;
};
export type PriceLike = { kind: string; usd?: number | null; usd_by_frame?: Record<string, number> };
export type ModelLike = {
  id: string;
  label: string;
  available?: boolean;
  duration: AxisLike;
  frame: AxisLike;
  price?: PriceLike;
  /** the frame a DRAFT renders at -- the catalogue says (src/drafts.py) --
   *  or null when this model has no cheaper tier than its default */
  draft?: string | null;
};
export type RendererLike = { label: string; available: boolean; frame_axis?: string; models: ModelLike[] };
export type Renderers = Record<string, RendererLike>;
export type Pick = { provider: string; model: string; duration: number | null; frame: string | null };
export type PartLike = { seconds?: number | null; media_url?: string | null };
export type ShotLike = PartLike & { n: number; reference_image?: string | null };

export const held = new Map<number, Pick>();

export const specOf = (renderers: Renderers, provider?: string, model?: string): ModelLike | null =>
  (provider && renderers[provider]?.models?.find((m) => m.id === model)) || null;

export const usable = (renderers: Renderers, provider?: string, model?: string): boolean => {
  const r = provider ? renderers[provider] : undefined;
  const spec = specOf(renderers, provider, model);
  return !!(r && r.available && spec && spec.available !== false);
};

export const axisDefault = (axis?: AxisLike): string | number | null =>
  !axis ? null : axis.kind === "range" ? (axis.default ?? axis.min ?? null) : (axis.default ?? axis.values?.[0] ?? null);

const asPick = (provider: string, spec: ModelLike): Pick => {
  const duration = axisDefault(spec.duration);
  const frame = axisDefault(spec.frame);
  return { provider, model: spec.id, duration: duration === null ? null : Number(duration), frame: frame === null ? null : String(frame) };
};

export function estimate(spec: ModelLike | null, frame: string | null, seconds: number | null): number | null {
  const price = spec?.price;
  if (!price) return null;
  if (price.kind === "flat") return price.usd ?? null;
  const per = price.usd_by_frame && frame !== null ? price.usd_by_frame[frame] : price.usd;
  return per === undefined || per === null || seconds === null ? null : per * seconds;
}

export function firstUsable(renderers: Renderers): Pick | null {
  let best: { pick: Pick; cost: number } | null = null;
  for (const [name, r] of Object.entries(renderers)) {
    // an unconfigured renderer is not usable, however many models it lists
    if (!r.available) continue;
    for (const m of r.models || []) {
      if (m.available === false) continue;
      const pick = asPick(name, m);
      const usd = estimate(m, pick.frame, pick.duration);
      const cost = usd === null ? Infinity : usd;
      if (!best || cost < best.cost) best = { pick, cost };
    }
  }
  return best && best.pick;
}

export function defaultPick(renderers: Renderers, want?: { provider?: string; model?: string } | null): Pick | null {
  const planned = specOf(renderers, want?.provider, want?.model);
  if (planned && usable(renderers, want?.provider, want?.model)) return asPick(want!.provider!, planned);
  return firstUsable(renderers) || (planned ? asPick(want!.provider!, planned) : null);
}

/** The pick a card shows: the held one while it is still usable, else the default. */
export function pickFor(renderers: Renderers, id: number, want?: { provider?: string; model?: string } | null): Pick | null {
  const kept = held.get(id);
  if (kept && usable(renderers, kept.provider, kept.model)) return kept;
  return defaultPick(renderers, want);
}

/** Changing the model takes the NEW model's defaults, never the old values:
 *  10s is legal on LTX and refused by Veo. */
export function withModel(renderers: Renderers, provider: string, model: string): Pick | null {
  const spec = specOf(renderers, provider, model);
  return spec ? asPick(provider, spec) : null;
}

export function legalDuration(axis: AxisLike, seconds: number): boolean {
  if (!Number.isFinite(seconds)) return false;
  if (axis.kind === "range") return seconds >= (axis.min ?? -Infinity) && seconds <= (axis.max ?? Infinity);
  return (axis.values || []).map(Number).includes(seconds);
}

export type Plan = {
  timed: boolean;
  n: number;
  lengths: number[];
  /** what it costs THIS account in credits (the server's quote, markup
   *  included); null only when not priced yet. There is no dollar field:
   *  the studio never shows the provider's cost (2026-10-08). */
  credits: number | null;
  pending?: boolean;
  refused?: string;
  /** a timed scene rendered as ONE clip with its cuts inside (`n` is 1);
   *  `shots` is how many shots ride inside it */
  oneClip?: boolean;
  shots?: number;
};
/** the server's price for a pick (pricing.display), or its refusal */
export type QuoteLike = {
  error?: string;
  timed?: boolean;
  one_clip?: boolean;
  durations?: number[];
  credits?: number | null;
} | null | undefined;

/** What an approve would make and cost. `parts` is the scene's timeline
 *  (null for a scene that renders whole). A timed scene's lengths and
 *  price are the server's `quote` for THIS pick: shots that already have
 *  a clip are not in it, as the server's resume skips them.
 *
 *  CREDITS COME ONLY FROM THE SERVER (2026-09-25). The credit price is
 *  pricing.credits_for -- markup, rounding up, a floor per render -- and
 *  this file does not keep a second copy of that rule. `quote`:
 *    - a quote: its credits are the button's number
 *    - null or undefined: not answered yet -- "pricing…", never a guess.
 *      (Until 2026-10-08 an undefined quote fell back to the rate card's
 *      dollar label; the studio shows no dollars now.) */
export function planFor(spec: ModelLike, pick: Pick, parts: PartLike[] | null | undefined, quote?: QuoteLike): Plan {
  if (!parts || !parts.length) {
    const base = { timed: false, n: 1, lengths: [pick.duration ?? 0] };
    if (!quote) return { ...base, credits: null, pending: true };
    if (quote.error) return { ...base, credits: null, refused: quote.error };
    return { ...base, credits: quote.credits ?? null };
  }
  const todo = parts.filter((p) => !p.media_url);
  if (quote && !quote.error && quote.one_clip && quote.durations) {
    // the whole scene in one generation, the cuts in its prompt
    return { timed: false, oneClip: true, shots: parts.length, n: 1, lengths: quote.durations, credits: quote.credits ?? null };
  }
  if (!quote || quote.error || !quote.timed || !quote.durations) {
    return { timed: true, n: todo.length, lengths: [], credits: null, pending: !quote, refused: quote?.error ?? "" };
  }
  return { timed: true, n: quote.durations.length, lengths: quote.durations, credits: quote.credits ?? null };
}

/** Beside a credit price on an exempt (operator) account. */
export const NOT_CHARGED = " · not charged";

export const creditsText = (credits: number, exempt = false): string =>
  `${credits.toLocaleString("en-US")} credit${credits === 1 ? "" : "s"}${exempt ? NOT_CHARGED : ""}`;

/** The price half of the button: the server's credits, or "pricing…"
 *  until it answers -- never a dollar figure (2026-10-08). "cr" rather than
 *  "credits" because the button is 22px Bebas in a card a third of the
 *  page wide -- the /models page abbreviates the same way. An exempt
 *  account still sees the price (it is still what the render costs) with
 *  "not charged" beside it, so the button agrees with the shell's pill. */
export const priceText = (plan: Plan, exempt = false): string =>
  plan.refused
    ? "refused"
    : plan.credits !== null && !plan.pending
      ? `${plan.credits.toLocaleString("en-US")} cr${exempt ? NOT_CHARGED : ""}`
      : "pricing…";

/** "3 shots" -- or "3 shots, one clip" when they render as one generation */
export const shotsText = (plan: Plan): string =>
  plan.oneClip ? `${plan.shots} shots, one clip` : `${plan.n} shot${plan.n === 1 ? "" : "s"}`;

export const approveText = (plan: Plan, exempt = false, draft = false): string =>
  `${draft ? "Draft" : "Approve"} · ${shotsText(plan)} · ${priceText(plan, exempt)}`;

/* ── draft, then finish (2026-10-11; src/drafts.py) ──
   A draft is the scene's same Render at the model's cheapest frame. The catalogue
   says which frame that is; nothing here knows a price. */

/** The frame a draft of this model renders at, or null: no draft offered. */
export const draftFrame = (spec: ModelLike | null | undefined): string | null => {
  const d = spec?.draft;
  return d && (spec.frame.values || []).map(String).includes(d) ? d : null;
};
/** Is this pick the model's draft? */
export const isDraft = (spec: ModelLike | null | undefined, pick: Pick | null | undefined): boolean =>
  !!pick?.frame && draftFrame(spec) === pick.frame;
/** Draft on: the draft frame. Off: back to the frame the model renders at
 *  by default. A model with no draft is left as it is. */
export const withDraft = (spec: ModelLike, pick: Pick, on: boolean): Pick => {
  const d = draftFrame(spec);
  if (!d) return pick;
  return { ...pick, frame: on ? d : spec.frame.default != null ? String(spec.frame.default) : pick.frame };
};

/** The scene's own priced button (2026-10-11): the same plan and the same
 *  price as `approveText`, said as what the click does. A pick at the
 *  model's draft frame says so, like the Queue card it replaced. */
export const renderText = (plan: Plan, exempt = false, draft = false): string =>
  `${draft ? "Draft" : "Render"} · ${shotsText(plan)} · ${priceText(plan, exempt)}`;

/** Where a scene stands with its clips, off its own row: every shot (or
 *  the whole scene) rendered, some of a timed scene's shots rendered, or
 *  none. `parts` is the scene's timeline, empty for one that renders whole. */
export type Rendered = { state: "none" | "partial" | "done"; clips: number; of: number };
export function renderedOf(mediaUrl: string | null | undefined, parts: PartLike[] | null | undefined): Rendered {
  const list = parts || [];
  if (!list.length) return { state: mediaUrl ? "done" : "none", clips: mediaUrl ? 1 : 0, of: 1 };
  const clips = list.filter((p) => !!p.media_url).length;
  // the scene's own media_url is set when its LAST shot lands (timeline.attach_part)
  if (clips >= list.length || mediaUrl) return { state: "done", clips: Math.max(clips, 0), of: list.length };
  return { state: clips ? "partial" : "none", clips, of: list.length };
}

/** A job that is working on this scene right now: its render, or its
 *  keyframes. The approve names the scene on the job from the start
 *  (`ref_id`), so this is read off the live job list, never remembered. */
/** The shots whose keyframe can be drawn on its own: every timed shot with
    no still and no clip yet -- and only while two or more are missing one.
    The last one missing is what the strip's own button draws, at the same
    price, so offering it twice would be two buttons for one thing. */
export function shotsToDraw<P extends ShotLike>(parts: P[] | null | undefined, stills: number | null | undefined): P[] {
  if (!stills || stills < 2) return [];
  const open = (parts || []).filter((p) => !p.reference_image && !p.media_url);
  return open.length >= 2 ? open : [];
}

/** A keyframe quote as the server prices it (scene_chain.keyframe_quote).
 *  `up_to` means the count is a CEILING: a scene with no timed shots is
 *  drawn as one still per moment of its move, so fewer may be drawn and
 *  charged than the number here -- never more (the draw is capped at it). */
export type KeyframeQuoteLike = { stills: number; credits: number; up_to?: boolean };

/** "1 keyframe" · "3 keyframes" · "up to 2 keyframes" */
export const keyframeCount = (q: KeyframeQuoteLike): string =>
  `${q.up_to ? "up to " : ""}${q.stills} keyframe${q.stills === 1 ? "" : "s"}`;

/** The price beside it: what is charged, or the most that can be. */
export const keyframePrice = (q: KeyframeQuoteLike, exempt = false): string =>
  `${q.up_to ? "up to " : ""}${creditsText(q.credits, exempt)}`;

/** The strip button's words. One still reads "Draw keyframe first", as it
 *  always did; a ceiling always carries its number. */
export const keyframeButton = (q: KeyframeQuoteLike): string =>
  q.stills === 1 && !q.up_to ? "Draw keyframe first" : `Draw ${keyframeCount(q)} first`;

/** Under the button when the price is a ceiling: why the number may come in
 *  lower. "" for an exact quote, which needs no explaining. */
export const keyframeCeilingNote = (q: KeyframeQuoteLike | null | undefined): string =>
  q?.up_to
    ? `One still for each moment of the take, ${q.stills} at most · you are charged for the ones drawn.`
    : "";

/** What the card says about keyframes, read off the shots themselves. The
    scene's own still is shot 1's, so with shots drawn one at a time it can
    be missing while a later shot has one -- "no keyframes drawn" was then
    untrue. */
/** Under a timed scene that renders as ONE clip (src/timeline.py renders_as_one). */
export const oneClipNote = (shots: number, photos: number): string =>
  `The whole scene renders as one clip, its ${shots} shots cut inside it` +
  (photos ? `, held to your ${photos} photo${photos === 1 ? "" : "s"}` : "") + ".";

export function keyframeNote(parts: ShotLike[] | null | undefined, sceneStill: string | null | undefined): string {
  const shots = parts || [];
  const drawn = shots.filter((p) => p.reference_image).length;
  if (drawn && drawn < shots.length)
    return `${drawn} of ${shots.length} shots have a keyframe · the others render from the prompt and the references.`;
  return drawn || sceneStill
    ? "Each clip starts on its keyframe."
    : "No keyframes drawn · the clips render from the prompt and the references.";
}

export type JobLike = { id: number; kind: string; status: string; ref_id?: number | string | null; detail?: string; progress?: number };
export const liveJobFor = <J extends JobLike>(jobs: J[], sceneId: number, kind: "render" | "keyframe"): J | null =>
  jobs.find((j) => j.kind === kind && j.ref_id === sceneId && (j.status === "queued" || j.status === "running")) ?? null;

export const chipText = (spec: ModelLike, pick: Pick, plan: Plan): string =>
  `${spec.label} · ${plan.oneClip ? `${plan.shots} shots · ${plan.lengths[0]}s` : plan.timed ? `${plan.n} shot${plan.n === 1 ? "" : "s"}` : `${pick.duration}s`} · ${pick.frame ?? "—"}`.toUpperCase();

/** A scene's clips are 9:16: its keyframes are drawn at nano_banana.ASPECT_RATIO
 *  and a text clip at fal.DEFAULT_ASPECT; a scene has no shape of its own
 *  (2026-10-24, the render test). The chat's Approve button says so. */
export const SCENE_SHAPE = "9:16";

const SHAPE_WORDS: [RegExp, string][] = [
  [/\b(\d{1,2})\s*[:x×]\s*(\d{1,2})\b/i, ""],
  [/\b(landscape|widescreen|wide[- ]screen|horizontal|cinemascope|letterbox(?:ed)?)\b/i, "16:9"],
  [/\bsquare (?:frame|format|video|clip|crop)\b/i, "1:1"],
];
const RATIOS = new Set(["1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9", "2:1", "1:2", "2.39:1"]);

/** The shape a prompt asks for when it is NOT the scene's 9:16, or "".
 *  Advice only: the clip still renders 9:16, and the card says so. */
export function shapeAsked(prompt: string | null | undefined): string {
  const text = prompt || "";
  for (const [re, shape] of SHAPE_WORDS) {
    const m = text.match(re);
    if (!m) continue;
    const named = shape || `${Number(m[1])}:${Number(m[2])}`;
    if (!shape && !RATIOS.has(named)) continue;
    if (named !== SCENE_SHAPE) return named;
  }
  return "";
}
