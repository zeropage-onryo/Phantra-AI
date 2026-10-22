/* The Create page, v2 (2026-10-22; docs/tasks/task-create-page-v2.md,
   group 4 of docs/tasks/task-overnight-2026-10-22.md).

   The Runway / Higgsfield-shaped page under the composer: input chips,
   "Continue where you left off", a launch carousel, use-case tabs,
   Trending this week, a personalized row, an effects strip, New at
   Phantra, one Founding 500 banner and a Made in Phantra feed. Behind the
   `create_v2` capability (GET /api/capabilities): ON unless the server
   sets PHANTRA_CREATE_V2=0 (on by default since 2026-10-22, #448); with it
   off the page is the tree it was.

   NO PRICES ON ANY CARD (Mike's call, 2026-10-22). Nothing in this file
   knows a credit number; the priced card before a spend still shows one.
   A card only ever FILLS the composer's box, opens the gallery or links
   somewhere -- never sends, never renders.

   Pure and import-free on purpose: tests/create-v2.test.mjs loads this
   file with node. The section component (components/studio/create-v2)
   does the fetching. */

export type Capabilities = Record<string, boolean>;

/** The flag, read the way every capability is read: a strict true. */
export const createV2On = (caps: Capabilities | null | undefined) => caps?.create_v2 === true;

/* ── 1. input chips beside the Vesper bar ── */
export type ChipAction = "focus" | "fill" | "attach" | "effects";
export type InputChip = { id: string; label: string; action: ChipAction; fill?: string; title: string };
export const INPUT_CHIPS: InputChip[] = [
  { id: "idea", label: "Idea", action: "focus", title: "Describe what you want in a sentence" },
  { id: "script", label: "Script", action: "fill", fill: "Script:\n", title: "Paste a script; Vesper breaks it into shots" },
  {
    id: "url",
    label: "Product URL",
    action: "fill",
    fill: "Make an ad from this product page: ",
    title: "Paste a product page; its photos and facts come along",
  },
  { id: "image", label: "Image", action: "attach", title: "Attach a photo as a reference" },
  { id: "clip", label: "Clip", action: "effects", title: "Change a clip you made: effects, sound, a new shape" },
];

/* ── 3. the highlights row: four tiles, live features only (no "coming soon") ── */
export type LaunchSlide = { id: string; eyebrow: string; title: string; line: string; showcase: string; href?: string; fill?: string };
export const LAUNCH_SLIDES: LaunchSlide[] = [
  { id: "split", eyebrow: "Free looks", title: "Phone footage, graded", line: "Drop a clip; the free looks grade it in seconds.", showcase: "create.hero.split", href: "effects" },
  { id: "phone", eyebrow: "Vertical", title: "Ready to post", line: "One brief, one 9:16 cut, filed in your Library.", showcase: "create.hero.phone", fill: "A 9:16 vertical for social: " },
  { id: "product", eyebrow: "Product ad", title: "An ad from a link", line: "Paste a product page; Vesper plans the shots.", showcase: "create.hero.product_ad", fill: "Make an ad from this product page: " },
  { id: "effects", eyebrow: "Effects", title: "Bullet Time and twenty more", line: "Templates, camera moves, sound and upscale, each on a priced card.", showcase: "effect.bullet_time", href: "effects" },
];

/* ── 4. use-case tabs: each card fills the box with a brief, never sends ── */
export type UseCase = { id: string; title: string; line: string; brief: string; showcase: string };
export type UseCaseTab = { id: "marketing" | "social" | "film" | "business"; label: string; cards: UseCase[] };
export const USE_CASE_TABS: UseCaseTab[] = [
  {
    id: "marketing",
    label: "Marketing",
    cards: [
      {
        id: "saas",
        title: "SaaS explainer",
        line: "A 20s walk through one feature, on a dark dashboard.",
        brief: "A 20-second SaaS explainer: one feature of our product on a glowing dashboard in a dark modern office, calm voiceover, 16:9.",
        showcase: "create.usecase.saas",
      },
      {
        id: "product_ad",
        title: "Product ad",
        line: "Studio light, slow orbit, one line of type.",
        brief: "A 15-second product ad: the product on a concrete plinth under studio light, a slow orbit, one headline at the end, 16:9.",
        showcase: "create.usecase.product_ad",
      },
      {
        id: "ab_variants",
        title: "A/B variants",
        line: "Three colourways of one shot, side by side.",
        brief: "Three A/B variants of one product shot, each in a different colourway, same framing and light, 4:5.",
        showcase: "create.usecase.ab_variants",
      },
    ],
  },
  {
    id: "social",
    label: "Social",
    cards: [
      {
        id: "ugc",
        title: "UGC ad",
        line: "A creator to camera, warm bathroom light, 9:16.",
        brief: "A UGC-style ad: a creator holding our product to camera in warm bathroom light, talking naturally, 9:16, 15 seconds.",
        showcase: "create.usecase.ugc",
      },
      {
        id: "vertical",
        title: "Vertical-ready",
        line: "Your clip, centred and cut to 9:16.",
        brief: "Cut my last clip to 9:16, centred on the subject, ready for Reels.",
        showcase: "look.vertical_ready",
      },
      {
        id: "flash",
        title: "2000s flash",
        line: "Flash pops, a date stamp, a party look.",
        brief: "A 2000s flash-photo look on a night-out clip: flash pops, grain, a date stamp in the corner, 9:16.",
        showcase: "look.flash_2000s",
      },
    ],
  },
  {
    id: "film",
    label: "Film",
    cards: [
      {
        id: "music_video",
        title: "Music video",
        line: "A singer in a red-lit tunnel, haze, slow push.",
        brief: "A music video scene: a singer in a red-lit tunnel with haze, slow push in, cuts on the beat, 16:9, 20 seconds.",
        showcase: "create.usecase.music_video",
      },
      {
        id: "trailer",
        title: "Trailer",
        line: "A lone figure, a monolith at dusk, one title.",
        brief: "A 20-second trailer: a lone figure in the desert facing a giant monolith at dusk, wide shots, a single title card at the end, 2.39:1.",
        showcase: "create.usecase.trailer",
      },
      {
        id: "noir",
        title: "Noir short",
        line: "Black and white, one streetlight, rain.",
        brief: "A noir short: one figure under a single streetlight on a wet sidewalk at night, black and white, grain and vignette, 16:9.",
        showcase: "look.noir",
      },
    ],
  },
  {
    id: "business",
    label: "Business",
    cards: [
      {
        id: "menu_promo",
        title: "Menu promo",
        line: "Overhead steam, dark wood, the dish of the week.",
        brief: "A 10-second menu promo: overhead shot of steaming ramen on dark wood, slow drift, the dish name at the end, 4:5.",
        showcase: "create.usecase.menu_promo",
      },
      {
        id: "local",
        title: "Local business ad",
        line: "Your storefront clip, graded and cut vertical.",
        brief: "A local business ad from my storefront clip: film grade, cut to 9:16, our name and hours at the end.",
        showcase: "look.make_it_pro",
      },
      {
        id: "talking",
        title: "Talking photo",
        line: "A photo of the owner says the offer.",
        brief: "A talking photo: the owner's portrait reads a 10-second welcome and this week's offer.",
        showcase: "look.film_grade",
      },
    ],
  },
];

/* ── 5. trending this week (GET /api/trending; this account's week) ── */
export type TrendingWeek = {
  days: number;
  since: string;
  scope: "account";
  effects: { effect: string; label: string; runs: number; kept: number }[];
  briefs: { text: string; count: number; concept_id: number }[];
  events: { kept: number; discarded: number; edited: number };
};
export type TrendCard = { id: string; kind: "effect" | "brief"; label: string; note: string; effect?: string; brief?: string };

/** The row's cards: effects first by runs, then briefs by count. The
 *  note says how often, never what it cost. */
export function trendCards(week: TrendingWeek | null | undefined, max = 8): TrendCard[] {
  if (!week) return [];
  const out: TrendCard[] = [];
  for (const e of week.effects) {
    out.push({
      id: `effect:${e.effect}`,
      kind: "effect",
      label: e.label,
      note: `${e.runs} run${e.runs === 1 ? "" : "s"} this week${e.kept ? ` · ${e.kept} kept` : ""}`,
      effect: e.effect,
    });
  }
  for (const b of week.briefs) {
    out.push({
      id: `brief:${b.concept_id}`,
      kind: "brief",
      label: b.text.length > 72 ? `${b.text.slice(0, 71)}…` : b.text,
      note: `${b.count} scene${b.count === 1 ? "" : "s"} this week`,
      brief: b.text,
    });
  }
  return out.slice(0, max);
}

/* ── 2 and 6: the account's own recent work ── */
export type ProjectLite = { id: number; title: string; brief?: string; look?: string; updated_at?: string; archived?: boolean; cover_thumb?: string | null; cover?: string | null };
export type MediaLite = {
  generated_id?: number;
  url: string;
  kind: "image" | "video";
  poster?: string | null;
  thumb?: string | null;
  prompt?: string;
  starred?: boolean;
  model_label?: string | null;
  date?: string;
  created_at?: string | null;
};

export type ContinueCard = { id: string; kind: "project" | "render"; title: string; line: string; href: string; thumb: string | null };

/** "Continue where you left off": the newest project and the newest
 *  render; nothing for a first visit (the section hides). */
export function continueCards(projects: ProjectLite[], media: MediaLite[]): ContinueCard[] {
  const out: ContinueCard[] = [];
  const open = projects.filter((p) => !p.archived);
  const newest = [...open].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0];
  if (newest) {
    out.push({
      id: `project:${newest.id}`,
      kind: "project",
      title: newest.title,
      line: newest.brief ? (newest.brief.length > 90 ? `${newest.brief.slice(0, 89)}…` : newest.brief) : "Open the project",
      href: `/studio/projects/${newest.id}`,
      thumb: newest.cover_thumb ?? newest.cover ?? null,
    });
  }
  const render = media.find((m) => m.generated_id);
  if (render) {
    out.push({
      id: `render:${render.generated_id}`,
      kind: "render",
      title: render.kind === "video" ? "Your last clip" : "Your last still",
      line: render.prompt ? (render.prompt.length > 90 ? `${render.prompt.slice(0, 89)}…` : render.prompt) : "Open it in the Library",
      href: `/studio/assets?open=${render.generated_id}`,
      thumb: render.kind === "video" ? (render.poster ?? null) : (render.thumb ?? render.url),
    });
  }
  return out;
}

export type PersonalCard = { id: string; title: string; brief: string; because: string };

const firstLine = (text: string | undefined) => (text ?? "").split(/\n/)[0].trim();

/** "Because you made <project>…": three next things for the newest
 *  project, from its brief and look. Nothing for an account with no project. */
export function personalRow(projects: ProjectLite[]): { because: string; cards: PersonalCard[] } | null {
  const open = projects.filter((p) => !p.archived);
  const p = [...open].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0];
  if (!p) return null;
  const because = `Because you made ${p.title}…`;
  const brief = firstLine(p.brief) || p.title;
  const look = firstLine(p.look);
  const cards: PersonalCard[] = [
    {
      id: `${p.id}:vertical`,
      title: "A vertical cut",
      brief: `A 9:16 vertical version of "${p.title}" for Reels and TikTok: ${brief}`,
      because,
    },
    {
      id: `${p.id}:variants`,
      title: "Three ad variants",
      brief: `Three short ad variants of "${p.title}", each with a different hook: ${brief}`,
      because,
    },
    {
      id: `${p.id}:still`,
      title: look ? "A still in the same look" : "A key still",
      brief: look
        ? `A key still for "${p.title}" in the project's look (${look}): ${brief}`
        : `A key still for "${p.title}": ${brief}`,
      because,
    },
  ];
  return { because, cards };
}

/* ── 7. the effects strip: the six free looks, then the live effects ── */
export type LookCard = { id: string; label: string; line: string; showcase: string; tab: string };
export const LOOKS: LookCard[] = [
  { id: "film_grade", label: "Film Grade", line: "LUT, grain, letterbox", showcase: "look.film_grade", tab: "finish" },
  { id: "noir", label: "Noir", line: "Black and white, vignette", showcase: "look.noir", tab: "finish" },
  { id: "flash_2000s", label: "2000s Flash", line: "Flash pops, date stamp", showcase: "look.flash_2000s", tab: "finish" },
  { id: "crash_zoom", label: "Crash-Zoom Hook", line: "A zoom on the first beat", showcase: "look.crash_zoom", tab: "camera" },
  { id: "vertical_ready", label: "Vertical Ready", line: "Centred 9:16 crop", showcase: "look.vertical_ready", tab: "finish" },
  { id: "make_it_pro", label: "Make It Pro", line: "Grade, vertical, sound", showcase: "look.make_it_pro", tab: "finish" },
];

/** Where the Clip chip, the strip and "Drop a clip" go: the Effects tab
 *  when its flag is on, else the composer's own gallery. */
export const effectsDoor = (caps: Capabilities | null | undefined): "tab" | "gallery" =>
  caps?.effects_tab === true ? "tab" : "gallery";
export const EFFECTS_TAB_HREF = "/studio/effects";

/* ── 8. New at Phantra ── */
/** A big card (Runway's "New at Runway" shape): eyebrow, title, line, a
 *  button, and a showcase picture bleeding off its edge. `fill` makes the
 *  button FILL the box instead of linking; `tone: "spotlight"` is the one
 *  card with no picture and the studio's wash behind it (Kling 4.0). */
export type NewTile = {
  id: string;
  eyebrow?: string;
  title: string;
  line: string;
  cta: string;
  href: string;
  fill?: string;
  tone?: "spotlight";
  showcase: string | null;
};
/* PLACEHOLDER: the Discord invite is Mike's to set; until it is, the tile
   points at the connections page, which says how to reach us. */
export const DISCORD_INVITE_URL = "";
export const NEW_TILES: NewTile[] = [
  {
    id: "kling4",
    eyebrow: "New model",
    title: "Kling 4.0",
    line: "Single takes up to 30 seconds, 720p or 1080p, stereo sound. In every picker now.",
    cta: "Try Kling 4.0",
    href: "/models/kling-video-generator",
    fill: "One continuous 20-second take on Kling 4.0: ",
    tone: "spotlight",
    showcase: null,
  },
  {
    id: "mcp_claude",
    eyebrow: "Phantra MCP",
    title: "With Claude",
    line: "Write and price scenes right in Claude; render them in the studio.",
    cta: "Connect Claude",
    href: "/studio/settings/connections",
    showcase: "create.new.mcp_claude",
  },
  {
    id: "brand_kit",
    eyebrow: "Brand Kit",
    title: "Your look, on every still and cut",
    line: "Palette, type, logo and tone, kept by Vesper from the first frame.",
    cta: "Open Brand Kits",
    href: "/studio/brand",
    showcase: "create.new.brand_kit",
  },
  {
    id: "discord",
    eyebrow: "Community",
    title: "Phantra on Discord",
    line: "Grade a clip from a chat; share what you made with the people making it too.",
    cta: "Join the Discord",
    href: DISCORD_INVITE_URL || "/studio/settings/connections",
    showcase: "create.new.discord",
  },
  {
    id: "models",
    eyebrow: "Models",
    title: "Every model, one bill",
    line: "Kling 4.0, Veo, Seedance, LTX, Wan: one dated table, and every render is priced before you approve.",
    cta: "See every model",
    href: "/models",
    showcase: "create.hero.phone",
  },
];

/* ── 9. the Founding 500 banner ──
   PLACEHOLDER NUMBERS (2026-10-22): the sprint doc's offer -- free near-zero
   looks, a signup grant, a founding price -- with figures Mike edits here.
   The page prints exactly these; nothing else reads them. */
export const FOUNDING_500 = {
  placeholder: true,
  seats: 500,
  signupCredits: 300,
  freeLooks: "Film Grade, Noir, 2000s Flash, Crash-Zoom, Vertical Ready",
  priceLine: "founding price, locked for a year",
  href: "/studio/settings/plan",
};

export const foundingLines = (offer: typeof FOUNDING_500) => ({
  title: `Founding ${offer.seats}`,
  line: `Free looks (${offer.freeLooks}), ${offer.signupCredits} credits on sign-up, and the ${offer.priceLine}.`,
  cta: "See the founding plan",
});

/* ── 10. Made in Phantra: the account's kept renders, with Remix ── */
export type MadeCard = { id: number; kind: "image" | "video"; thumb: string | null; url: string; prompt: string; model: string; starred: boolean };

/** Starred first, then newest; up to `max`. A render with no id cannot be remixed and is left out. */
export function madeFeed(media: MediaLite[], max = 8): MadeCard[] {
  const rows = media.filter((m): m is MediaLite & { generated_id: number } => typeof m.generated_id === "number");
  const sorted = [...rows].sort((a, b) => Number(!!b.starred) - Number(!!a.starred));
  return sorted.slice(0, max).map((m) => ({
    id: m.generated_id,
    kind: m.kind,
    thumb: m.kind === "video" ? (m.poster ?? null) : (m.thumb ?? m.url),
    url: m.url,
    prompt: m.prompt ?? "",
    model: m.model_label ?? "",
    starred: !!m.starred,
  }));
}

/* ── the brand kit badge: cards preview in the kit's palette roles ── */
export type KitSwatch = { hex: string; role: string };
export type KitPalette = { id: number; name: string; primary: string | null; accent: string | null; background: string | null; text: string | null };

/** The kit's palette by role (src/brand_kits.py PALETTE_ROLES), or null when
 *  the project has no kit. A role the kit did not fill is null and the card
 *  keeps the studio's own colour for it. */
export function kitPalette(kit: { id: number; name: string; palette?: KitSwatch[] } | null | undefined): KitPalette | null {
  if (!kit) return null;
  const by = (role: string) => kit.palette?.find((s) => s.role === role)?.hex ?? null;
  return { id: kit.id, name: kit.name, primary: by("primary"), accent: by("accent"), background: by("background"), text: by("text") };
}

/** CSS variables scoped to one card; empty with no kit, so a card without
 *  a kit carries no kit colour at all. */
export function kitVars(kit: KitPalette | null | undefined): Record<string, string> {
  if (!kit) return {};
  const vars: Record<string, string> = {};
  if (kit.primary) vars["--kit-primary"] = kit.primary;
  if (kit.accent) vars["--kit-accent"] = kit.accent;
  if (kit.background) vars["--kit-background"] = kit.background;
  if (kit.text) vars["--kit-text"] = kit.text;
  return vars;
}

/** The section ids, top to bottom: the screenshot check and the tests read this. */
export const SECTIONS = [
  "vesper",
  "continue",
  "launch",
  "usecases",
  "trending",
  "personal",
  "effects",
  "new",
  "founding",
  "made",
] as const;
export type SectionId = (typeof SECTIONS)[number];
