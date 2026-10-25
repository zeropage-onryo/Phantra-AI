/* The direct generators (/studio/image and /studio/video, 2026-10-22;
   src/direct.py, docs/tasks/task-direct-generators.md).

   One prompt, one model the person picked, one priced button. The menus
   come from GET /api/direct/{image,video}; the price on the button is
   always the server's quote for exactly the pick on screen
   (POST /api/direct/{image,video}/quote), and the run is refused (409) if that number
   moved -- this file never computes a price, it only decides which pick
   is on screen.

   Pure and import-free: tests/direct.test.mjs runs it as it is. */

export type SecondsAxis =
  | { kind: "choices"; values: number[]; default: number }
  | { kind: "range"; min: number; max: number; default: number }
  | { kind: "fixed"; values: number[]; default: number; note?: string };

export type VideoModel = {
  id: string;
  label: string;
  note: string;
  seconds: SecondsAxis;
  resolutions: string[];
  resolution: string;
  aspects: string[];
  aspect: string;
  /** what the model's opening pick costs */
  credits: number;
  /** the longest prompt the model takes (refused past it, never cut) */
  prompt_max: number;
  /** how many pictures it can be held to as references; 0 = one start frame only */
  max_refs: number;
  /** how the prompt names the first picture ("@Image1", "<IMAGE_0>") */
  ref_tag: string | null;
  /** the resolutions it renders with references, null = all of them */
  ref_resolutions: string[] | null;
};
export type VideoMenu = { ready: boolean; items: VideoModel[]; default: string; exempt: boolean };

export type ImageModel = {
  id: string;
  label: string;
  note: string;
  references: boolean;
  credits: number;
  max_refs: number;
};
export type ImageMenu = {
  ready: boolean;
  items: ImageModel[];
  default: string;
  aspects: string[];
  aspect: string;
  exempt: boolean;
};

export type VideoPick = { model: string; seconds: number; resolution: string; aspect: string };
export type ImagePick = { model: string; aspect: string };

export type Quote = { credits: number; charged: boolean };

/** Every length the model takes, in order. */
export function secondsChoices(axis: SecondsAxis | null | undefined): number[] {
  if (!axis) return [];
  if (axis.kind === "range") {
    const out: number[] = [];
    for (let s = axis.min; s <= axis.max; s++) out.push(s);
    return out;
  }
  return [...(axis.values ?? [])];
}

/** The model a page opens on: the link's ?model= when the menu has it,
    else the one this person last used, else the menu's default, else the
    first. "" for an empty menu. */
export function openingModel(menu: { items: { id: string }[]; default: string }, linked?: string | null, last?: string | null): string {
  const has = (id?: string | null) => !!id && menu.items.some((m) => m.id === id);
  if (has(linked)) return linked as string;
  if (has(last)) return last as string;
  if (has(menu.default)) return menu.default;
  return menu.items[0]?.id ?? "";
}

/** A clip pick moved onto `model`: what was on screen is KEPT where the new
    model takes it (a person who chose 10s and 9:16 keeps them), and each
    part it does not take falls to the model's own opening value -- never a
    nearest value, which would be a pick nobody made. */
export function videoPickFor(model: VideoModel, was?: Partial<VideoPick> | null): VideoPick {
  const lengths = secondsChoices(model.seconds);
  const seconds = was?.seconds !== undefined && lengths.includes(was.seconds) ? was.seconds : model.seconds.default;
  const resolution = was?.resolution && model.resolutions.includes(was.resolution) ? was.resolution : model.resolution;
  const aspect = was?.aspect && model.aspects.includes(was.aspect) ? was.aspect : model.aspect;
  return { model: model.id, seconds, resolution, aspect };
}

/** What of a clip pick changed against the person's: the parts the new
    model could not keep, said in one line ("Veo 3.1 renders 4-8s, so 10s
    became 8s"); "" when everything was kept. */
export function keptLine(model: VideoModel, was: Partial<VideoPick> | null | undefined, now: VideoPick): string {
  if (!was) return "";
  const parts: string[] = [];
  if (was.seconds !== undefined && was.seconds !== now.seconds) parts.push(`${was.seconds}s became ${now.seconds}s`);
  if (was.resolution && was.resolution !== now.resolution) parts.push(`${was.resolution} became ${now.resolution}`);
  if (was.aspect && was.aspect !== now.aspect) parts.push(`${was.aspect} became ${now.aspect}`);
  return parts.length ? `${model.label} does not take that, so ${parts.join(", ")}.` : "";
}

/** The span a model's lengths cover, for its line in the picker ("4-8s"). */
export function secondsSpan(axis: SecondsAxis): string {
  const all = secondsChoices(axis);
  if (!all.length) return "";
  const lo = all[0];
  const hi = all[all.length - 1];
  return lo === hi ? `${lo}s` : `${lo}-${hi}s`;
}

/** A still pick moved onto a model: the frame is every model's, so only
    the model changes. */
export function imagePickFor(model: ImageModel, was?: Partial<ImagePick> | null, aspects: string[] = []): ImagePick {
  const aspect = was?.aspect && (!aspects.length || aspects.includes(was.aspect)) ? was.aspect : aspects[0] ?? "1:1";
  return { model: model.id, aspect };
}

/** How many of `attached` pictures reach `model`, and the line that says
    so before the click ("" when every one does). */
export function referencesLine(model: Pick<ImageModel, "label" | "max_refs"> | null, attached: number): string {
  if (!model || attached <= 0) return "";
  if (model.max_refs <= 0) {
    return `${model.label} draws from the prompt only: the ${attached === 1 ? "picture" : `${attached} pictures`} attached will not reach it.`;
  }
  if (attached > model.max_refs) return `${model.label} takes ${model.max_refs}; the first ${model.max_refs} attached are sent.`;
  return "";
}

/** The Generate button's words. Null credits = still pricing. */
export function buttonLabel(quote: Quote | null, pricing: boolean, exempt: boolean): string {
  if (!quote || pricing) return "Generate · pricing…";
  const n = quote.credits.toLocaleString("en-US");
  return exempt || !quote.charged ? `Generate · ${n} credits · not charged` : `Generate · ${n} credits`;
}

/** The picker's line for one clip model: lengths, resolutions, its price
    at its opening pick. */
export function videoModelLine(m: VideoModel): string {
  const res = m.resolutions.length > 1 ? `${m.resolutions[0]}-${m.resolutions[m.resolutions.length - 1]}` : m.resolutions[0] ?? "";
  return [secondsSpan(m.seconds), res, `from ${m.credits.toLocaleString("en-US")} credits`].filter(Boolean).join(" · ");
}

/** The picker's line for one still model. */
export function imageModelLine(m: ImageModel): string {
  const refs = m.max_refs > 0 ? `up to ${m.max_refs} references` : "prompt only";
  return `${refs} · ${m.credits.toLocaleString("en-US")} credits`;
}

/** A remembered pick, read back from storage: only its fields, only when
    they are the right shape. null for anything else. */
export function readPick<T extends object>(raw: string | null, fields: (keyof T)[]): Partial<T> | null {
  if (!raw) return null;
  try {
    const v = JSON.parse(raw) as Record<string, unknown>;
    if (!v || typeof v !== "object") return null;
    const out: Record<string, unknown> = {};
    for (const f of fields) {
      const x = v[f as string];
      if (typeof x === "string" || typeof x === "number") out[f as string] = x;
    }
    return out as Partial<T>;
  } catch {
    return null;
  }
}

export const PICK_KEY = { image: "phantra.direct.image", video: "phantra.direct.video" } as const;

/** The link from a model page (or anywhere) straight onto a direct page
    with its model picked. */
export const directHref = (kind: "image" | "video", model?: string) =>
  `/studio/${kind}${model ? `?model=${encodeURIComponent(model)}` : ""}`;

/** What a clip's pictures are (2026-10-25): none, ONE start frame the clip
    opens on and takes the shape of, or references the model is held to on
    its reference endpoint -- two or more pictures always, one when the
    person said so. A model with no reference endpoint only ever starts. */
export type VideoRefMode = "none" | "start" | "references";
export function videoRefMode(model: Pick<VideoModel, "max_refs"> | null, count: number, oneAsReference = false): VideoRefMode {
  if (count <= 0) return "none";
  if (!model || model.max_refs <= 0) return "start";
  return count >= 2 || oneAsReference ? "references" : "start";
}

/** The tags the prompt names `n` pictures by, counted on from the model's
    first ("@Image1" -> "@Image2"; "<IMAGE_0>" -> "<IMAGE_1>"). */
export function videoRefTags(model: Pick<VideoModel, "ref_tag"> | null, n: number): string[] {
  const first = model?.ref_tag;
  const m = first?.match(/\d+/);
  if (!first || !m || m.index === undefined) return [];
  const from = Number(m[0]);
  return Array.from({ length: n }, (_, i) => first.slice(0, m.index) + String(from + i) + first.slice(m.index! + m[0].length));
}
