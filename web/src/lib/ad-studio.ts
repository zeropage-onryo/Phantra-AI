/* The Ad Studio (2026-10-26, Mike: "give it its own UI and title 'Ad Studio'
   in the Phantra studio. Combine what we already have").

   A page over the ONE composer, not a second one. It draws the studio's
   config (GET /api/studios/ads, src/studios.py): a format, the product, a
   short brief and a brand kit. Its one action is a LINK into Create that
   carries all of it -- the first message typed in the box, the format's
   skill picked, the shape and length set, the kit switched on, the product's
   photos attached, and the studio pick kept on the conversation's draft so
   every turn after it is told the brief. Nothing here sends, makes or
   spends: the send is still the person's, and its price is on the card.

   Pure (no imports), so node --test can load it: web/tests/ad-studio.test.mjs. */

export type IntakeOption = { id: string; label: string; aspect?: string };
export type IntakeQuestion = {
  id: string;
  label: string;
  kind: "text" | "choice";
  placeholder?: string;
  max?: number;
  options?: IntakeOption[];
};
export type AdFormat = {
  id: string;
  title: string;
  blurb: string;
  skill: string;
  skill_title: string | null;
  output: "image" | "video";
  aspects: string[];
  seconds: [number, number] | null;
  default_seconds: number | null;
  needs: ("product" | "kit" | "clip")[];
  free?: boolean;
};
export type StudioPage = {
  id: string;
  title: string;
  tagline: string;
  intake: IntakeQuestion[];
  formats: AdFormat[];
  entitled: boolean;
  gated: boolean;
  addon: {
    key: string;
    name: string;
    blurb: string;
    monthly_usd: number | null;
    on_sale: boolean;
    has_plan: boolean;
  } | null;
};

/** What the person filled in on the page. */
export type AdBrief = {
  format: string;
  aspect: string;
  seconds: number | null;
  intake: Record<string, string>;
  /** the product element (an Elements id), or null */
  product: { id: string; name: string } | null;
  kit: { id: number; name: string } | null;
};

/** What rides on the conversation's draft and every brain turn
 *  (src/studios.py clean_pick is the server's cleaner of the same shape). */
export type StudioPick = {
  id: string;
  format: string;
  aspect: string | null;
  seconds: number | null;
  intake: Record<string, string>;
};

export const AD_STUDIO_HREF = "/studio/ads";

export function formatOf(page: StudioPage | null | undefined, id: string | null | undefined): AdFormat | null {
  return page?.formats.find((f) => f.id === id) ?? null;
}

/** A fresh brief on a format: its first shape and its default length. */
export function startBrief(format: AdFormat, keep?: Partial<AdBrief>): AdBrief {
  return {
    format: format.id,
    aspect: format.aspects[0] ?? "9:16",
    seconds: format.default_seconds,
    intake: keep?.intake ?? {},
    product: keep?.product ?? null,
    kit: keep?.kit ?? null,
  };
}

/** The shape a platform answer asks for, when the format can make it. */
export function aspectForPlatform(page: StudioPage, format: AdFormat, platform: string | undefined): string | null {
  const q = page.intake.find((x) => x.id === "platform");
  const want = q?.options?.find((o) => o.id === platform)?.aspect;
  return want && format.aspects.includes(want) ? want : null;
}

/** The brief moved to another format: the answers, product and kit stay;
 *  the shape stays if the new format makes it, the length if it fits. */
export function switchFormat(page: StudioPage, brief: AdBrief, format: AdFormat): AdBrief {
  const aspect = format.aspects.includes(brief.aspect)
    ? brief.aspect
    : aspectForPlatform(page, format, brief.intake.platform) ?? format.aspects[0] ?? brief.aspect;
  // a length the person chose (not the old format's default) is kept when
  // the new format can take it; otherwise the new format's own default
  const s = format.seconds;
  const chose = brief.seconds !== (formatOf(page, brief.format)?.default_seconds ?? null);
  const fits = !!(s && brief.seconds && brief.seconds >= s[0] && brief.seconds <= s[1]);
  const seconds = chose && fits ? brief.seconds : format.default_seconds;
  return { ...brief, format: format.id, aspect, seconds };
}

/** One answer changed; a platform answer also moves the shape. */
export function answer(page: StudioPage, brief: AdBrief, id: string, value: string): AdBrief {
  const intake = { ...brief.intake };
  if (value.trim()) intake[id] = value;
  else delete intake[id];
  const next = { ...brief, intake };
  if (id === "platform") {
    const format = formatOf(page, brief.format);
    const aspect = format ? aspectForPlatform(page, format, value) : null;
    if (aspect) next.aspect = aspect;
  }
  return next;
}

function labelOf(page: StudioPage, id: string, value: string): string {
  const q = page.intake.find((x) => x.id === id);
  if (q?.kind === "choice") return q.options?.find((o) => o.id === value)?.label ?? value;
  return value;
}

const clean = (s: string | undefined) => (s ?? "").replace(/\s+/g, " ").trim();

/** "a" or "an" before a word as it is said: an 8-second, an 18-second,
 *  an 11-second, an ad; a 15-second, a 9:16. */
export function article(word: string): "a" | "an" {
  const w = word.trim().toLowerCase();
  if (/^(8|11|18)(\D|$)/.test(w) || /^8\d(\D|$)/.test(w)) return "an";
  if (/^\d/.test(w)) return "a";
  return /^[aeiou]/.test(w) ? "an" : "a";
}

/** The first message typed into Create's box: the brief in a sentence the
 *  person can still edit before they send it. */
export function briefText(page: StudioPage, brief: AdBrief): string {
  const format = formatOf(page, brief.format);
  if (!format) return "";
  const title = format.title.charAt(0).toLowerCase() + format.title.slice(1);
  // "UGC review", "TV spot" keep their capitals; "Product showcase" does not
  const named = /^[A-Z]{2}/.test(format.title) ? format.title : title;
  const what = format.output === "image" || /\bad$/i.test(named) ? named : `${named} ad`;
  const length = format.output === "video" && brief.seconds ? `${brief.seconds}-second ` : "";
  const product = brief.product?.name ? ` for ${clean(brief.product.name)}` : "";
  const lead = `${length}${brief.aspect} ${what}`;
  const a = article(lead);
  const parts = [`${a.charAt(0).toUpperCase()}${a.slice(1)} ${lead}${product}.`];
  const platform = brief.intake.platform ? labelOf(page, "platform", brief.intake.platform) : "";
  const audience = clean(brief.intake.audience);
  if (platform && audience) parts.push(`It runs on ${platform}, for ${audience}.`);
  else if (platform) parts.push(`It runs on ${platform}.`);
  else if (audience) parts.push(`It's for ${audience}.`);
  const offer = clean(brief.intake.offer);
  if (offer) parts.push(`They should: ${offer.replace(/[.!]+$/, "")}.`);
  if (brief.intake.tone) parts.push(`Tone: ${labelOf(page, "tone", brief.intake.tone).toLowerCase()}.`);
  return parts.join(" ");
}

/** The pick the draft keeps (and every turn carries). */
export function pickOf(page: StudioPage, brief: AdBrief): StudioPick {
  const intake: Record<string, string> = {};
  for (const [k, v] of Object.entries(brief.intake)) if (clean(v)) intake[k] = clean(v);
  return { id: page.id, format: brief.format, aspect: brief.aspect, seconds: brief.seconds, intake };
}

/** What is missing for this format, said plainly. Advice: nothing here
 *  blocks the hand-off (Vesper asks for what it still needs). */
export function missing(format: AdFormat, brief: AdBrief): string[] {
  const out: string[] = [];
  if (format.needs.includes("product") && !brief.product)
    out.push("No product picked: Vesper will ask for its photos before it writes.");
  if (format.needs.includes("kit") && !brief.kit)
    out.push("A motion ad is built from a brand kit: pick one, or read a website into one.");
  if (format.needs.includes("clip")) out.push("Attach the ad to cut down from your Library once you're in Create.");
  return out;
}

/** The link into Create. Every param is one the composer already reads
 *  (spark, kind, frame, kit, attach) plus the studio's own (studio, skill,
 *  seconds). */
export function handoffHref(page: StudioPage, brief: AdBrief): string {
  const format = formatOf(page, brief.format);
  const q = new URLSearchParams();
  q.set("spark", briefText(page, brief));
  if (format) q.set("kind", format.output);
  if (brief.aspect) q.set("frame", brief.aspect);
  if (format?.skill) q.set("skill", format.skill);
  if (format?.output === "video" && brief.seconds) q.set("seconds", String(brief.seconds));
  q.set("studio", JSON.stringify(pickOf(page, brief)));
  if (brief.kit) q.set("kit", String(brief.kit.id));
  if (brief.product) q.set("attach", brief.product.id);
  return `/studio?${q}`;
}

/** A studio pick read off a link (?studio=<json>) or a saved draft, in a
 *  shape the page can trust. The server cleans it again on every turn. */
export function asPick(raw: unknown): StudioPick | null {
  let v: unknown = raw;
  if (typeof v === "string") {
    try {
      v = v.trim() ? JSON.parse(v) : null;
    } catch {
      return null;
    }
  }
  if (!v || typeof v !== "object") return null;
  const d = v as Record<string, unknown>;
  if (typeof d.id !== "string" || typeof d.format !== "string" || !d.id || !d.format) return null;
  const intake: Record<string, string> = {};
  if (d.intake && typeof d.intake === "object")
    for (const [k, x] of Object.entries(d.intake as Record<string, unknown>)) if (typeof x === "string") intake[k] = x;
  return {
    id: d.id,
    format: d.format,
    aspect: typeof d.aspect === "string" ? d.aspect : null,
    seconds: typeof d.seconds === "number" && Number.isFinite(d.seconds) ? d.seconds : null,
    intake,
  };
}

/** The chip on Create's settings line: "Ad Studio · UGC review". */
export function pickLabel(pick: StudioPick, formats?: { id: string; title: string }[]): string {
  const title = formats?.find((f) => f.id === pick.format)?.title ?? pick.format.replace(/_/g, " ");
  return `Ad Studio · ${title}`;
}

/** The add-on's state, as the page's one line and button say it. */
export type Unlock =
  | { kind: "open" }
  | { kind: "buy"; label: string }
  | { kind: "plan-first" }
  | { kind: "not-on-sale" };

export function unlockState(page: StudioPage): Unlock {
  if (page.entitled) return { kind: "open" };
  const addon = page.addon;
  if (!addon || !addon.on_sale) return { kind: "not-on-sale" };
  if (!addon.has_plan) return { kind: "plan-first" };
  return { kind: "buy", label: addon.monthly_usd ? `Add Ad Studio · $${addon.monthly_usd}/mo` : "Add Ad Studio" };
}
