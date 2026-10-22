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
      {
        id: "launch_teaser",
        title: "Launch teaser",
        line: "The product rises out of smoke, one line.",
        brief: "A 10-second launch teaser: our product rising out of swirling smoke on black, one rim light, a slow push in, the launch date at the end, 4:5.",
        showcase: "create.usecase.launch_teaser",
      },
      {
        id: "seasonal",
        title: "Seasonal campaign",
        line: "The product in this season's light.",
        brief: "A seasonal campaign shot: our product on autumn leaves in warm late-afternoon light, shallow focus, a slow drift, 4:5, 10 seconds.",
        showcase: "create.usecase.seasonal",
      },
      {
        id: "founder",
        title: "Founder story",
        line: "The maker at work, documentary light.",
        brief: "A 20-second founder story: the founder at work in their own studio, hands close-up then a wide, warm documentary light, a voiceover line about why they started, 16:9.",
        showcase: "create.usecase.founder",
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
      {
        id: "hook",
        title: "Talking-head hook",
        line: "A creator to camera, first two seconds.",
        brief: "A talking-head hook for TikTok: a creator talking straight to their phone in a bright bedroom, an excited first line in the first two seconds, 9:16, 10 seconds.",
        showcase: "create.usecase.hook",
      },
      {
        id: "day_in_life",
        title: "Day in the life",
        line: "Coffee, the street, the morning, POV.",
        brief: "A day-in-the-life Reel: point-of-view shots of a morning, an iced coffee on a sunny café terrace, quick cuts on the beat, 9:16, 15 seconds.",
        showcase: "create.usecase.day_in_life",
      },
      {
        id: "unboxing",
        title: "Unboxing",
        line: "Hands, a box, the reveal, from above.",
        brief: "An unboxing video from above: hands open a plain kraft box with tissue paper and lift out our product, soft daylight on a wooden desk, 9:16, 12 seconds.",
        showcase: "create.usecase.unboxing",
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
      {
        id: "scifi",
        title: "Sci-fi short",
        line: "A corridor in neon, one figure walking.",
        brief: "A sci-fi short: an astronaut walking down a narrow spaceship corridor lit in blue and magenta, haze, slow tracking shot, 2.39:1, 20 seconds.",
        showcase: "create.usecase.scifi",
      },
      {
        id: "horror",
        title: "Horror teaser",
        line: "One flashlight, a hallway, a door ajar.",
        brief: "A horror teaser: a flashlight beam moving down a dark hallway in an old house toward a door left ajar, dust in the light, slow and quiet, 16:9, 15 seconds.",
        showcase: "create.usecase.horror",
      },
      {
        id: "period",
        title: "Period drama",
        line: "Candlelight, a letter, a turn of the head.",
        brief: "A period drama scene: a woman in a nineteenth-century dress reading a letter by candlelight, she looks up at a sound, painterly light, 16:9, 15 seconds.",
        showcase: "create.usecase.period",
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
      {
        id: "real_estate",
        title: "Real estate tour",
        line: "Sunlit rooms, a slow walk through.",
        brief: "A 20-second real estate tour: a slow walk-through of a bright modern living room with floor-to-ceiling windows, afternoon sun, wide lens, 16:9.",
        showcase: "create.usecase.real_estate",
      },
      {
        id: "gym",
        title: "Gym promo",
        line: "Hands wrapped at dawn, light through the windows.",
        brief: "A gym promo: a boxer wrapping her hands at dawn in a gritty gym, shafts of light, then a hard first punch on the bag, 9:16, 15 seconds.",
        showcase: "create.usecase.gym",
      },
      {
        id: "event",
        title: "Event recap",
        line: "String lights, laughter, the best ten seconds.",
        brief: "A 15-second event recap: guests laughing with drinks under string lights in an industrial loft, quick candid cuts, warm bokeh, 9:16.",
        showcase: "create.usecase.event",
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
/** The effects strip's POPULAR tag (2026-10-22, the Runway / Higgsfield
 *  pass): the week's most-run effect, read off GET /api/trending, among the
 *  ids the strip actually draws. The text-only "Trending this week" row is
 *  gone -- it printed the effect table's raw ids (`voice-eleven-v3`) for
 *  effects the strip never shows. Null when nothing on the strip ran. */
export function popularEffect(week: TrendingWeek | null | undefined, shown: readonly string[]): string | null {
  if (!week) return null;
  const on = new Set(shown);
  let best: { id: string; runs: number } | null = null;
  for (const e of week.effects) {
    if (!on.has(e.effect) || e.runs < 1) continue;
    if (!best || e.runs > best.runs) best = { id: e.effect, runs: e.runs };
  }
  return best?.id ?? null;
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

/** A next thing for the newest project: the card shows `title` and the
 *  short `line`, never the brief (a brief is long and the person's own
 *  notes); the brief is what a pick puts in the box. `thumb` is the
 *  project's cover, else the newest render, drawn faded behind the words. */
export type PersonalCard = { id: string; title: string; line: string; brief: string; because: string; thumb: string | null };

const firstLine = (text: string | undefined) => (text ?? "").split(/\n/)[0].trim();

/** "Because you made <project>…": three next things for the newest
 *  project, from its brief and look. Nothing for an account with no project. */
export function personalRow(projects: ProjectLite[], media: MediaLite[] = []): { because: string; cards: PersonalCard[] } | null {
  const open = projects.filter((p) => !p.archived);
  const p = [...open].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0];
  if (!p) return null;
  const because = `Because you made ${p.title}…`;
  const brief = firstLine(p.brief) || p.title;
  const look = firstLine(p.look);
  const render = media.find((m) => m.generated_id);
  const thumb = p.cover_thumb ?? p.cover ?? (render ? (render.kind === "video" ? (render.poster ?? null) : (render.thumb ?? render.url)) : null);
  const cards: PersonalCard[] = [
    {
      id: `${p.id}:vertical`,
      title: "A vertical cut",
      line: "The same project, 9:16 for Reels and TikTok.",
      thumb,
      brief: `A 9:16 vertical version of "${p.title}" for Reels and TikTok: ${brief}`,
      because,
    },
    {
      id: `${p.id}:variants`,
      title: "Three ad variants",
      line: "One idea, three different hooks.",
      thumb,
      brief: `Three short ad variants of "${p.title}", each with a different hook: ${brief}`,
      because,
    },
    {
      id: `${p.id}:still`,
      title: look ? "A still in the same look" : "A key still",
      line: look ? "A still in the project's own look." : "One still that sums the project up.",
      thumb,
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

/* ── 3. the promo and the tool tiles (Higgsfield's middle row) ──
   2026-10-22, Mike's pick on the "Phantra Create Page Redesign" canvas: ONE
   big picture banner in the studio's yellow -- the thing that is new this
   month -- beside six small tiles, one per tool. It replaces the two-across
   "New at Phantra" cards. The promo is shown only while it is live (the
   Kling slot: `caps.kling_4`); with nothing live the tiles take the row. */
export type Promo = {
  id: string;
  /** the display lines: the first in the signal colour, the second in ink */
  title: string;
  subtitle: string;
  line: string;
  cta: string;
  /** what the button puts in the box (it never sends) */
  fill: string;
  showcase: string;
};
export const PROMO: Promo = {
  id: "kling4",
  title: "Kling 4.0",
  subtitle: "30-second takes",
  line: "Single takes up to 30 seconds, 720p or 1080p, stereo sound. In every picker now.",
  cta: "Try Kling 4.0",
  fill: "One continuous 20-second take on Kling 4.0: ",
  showcase: "create.usecase.trailer",
};

/** A tool tile: a line icon (inline SVG path data, so the card stays a pure
 *  function), a title, one line, and a tag. A tile LINKS (`href`), FILLS the
 *  box (`fill`) or opens the talking-photo card (`talk`). The tags are words,
 *  never prices: NEW for this month's tool, FREE for one that costs nothing. */
export type ToolTag = "NEW" | "FREE";
export type ToolTile = { id: string; title: string; line: string; icon: string; tag?: ToolTag; href?: string; fill?: string; talk?: true };
/* PLACEHOLDER: the Discord invite is Mike's to set; until it is, the tile
   points at the connections page, which says how to reach us. */
export const DISCORD_INVITE_URL = "";
export const TOOL_TILES: ToolTile[] = [
  {
    id: "talking_photo",
    title: "Talking photo",
    line: "A photo and a voice become a speaking clip.",
    icon: "M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
    tag: "NEW",
    talk: true,
  },
  {
    id: "final_cut",
    title: "Final cut",
    line: "A scene's shots, joined into one MP4.",
    icon: "M3 6h18M3 12h18M3 18h18M8 3v18M15 3v18",
    tag: "FREE",
    fill: "A 15-second video in three shots, joined into one final cut: ",
  },
  {
    id: "brand_kit",
    title: "Brand Kit",
    line: "Your palette, type and logo on every still.",
    icon: "M12 3a9 9 0 1 0 0 18c1 0 1.5-.8 1.5-1.6 0-1-.8-1.4-.8-2.4 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4c0-4.5-4-8.2-9-8.2zM7.5 11.5h.01M10 7.5h.01M15 7.5h.01",
    href: "/studio/brand",
  },
  {
    id: "mcp_claude",
    title: "Phantra in Claude",
    line: "Write and price scenes from a Claude chat.",
    icon: "M4 5h16v11H8l-4 4V5zM8 9h8M8 12h5",
    href: "/studio/settings/connections",
  },
  {
    id: "elements",
    title: "Elements",
    line: "The same face and product, shot to shot.",
    icon: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM12 12l8-4.5M12 12v9M12 12L4 7.5",
    href: "/studio/elements",
  },
  {
    id: "discord",
    title: "Phantra on Discord",
    line: "Share what you made with the people making it.",
    icon: "M7 9h10M7 13h6M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5l-4 3v-3H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
    href: DISCORD_INVITE_URL || "/studio/settings/connections",
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

/** The section ids, top to bottom: the screenshot check and the tests read
 *  this. 2026-10-22, the Runway / Higgsfield pass: seven, down from ten --
 *  continue and the personal row are one "work" row, trending is the
 *  effects strip's POPULAR tag, New at Phantra is the promo and its tiles,
 *  and the Founding banner waits for real numbers (FOUNDING_500 is still
 *  placeholders) before it takes the promo slot. */
export const SECTIONS = ["vesper", "launch", "promo", "usecases", "work", "effects", "made"] as const;
export type SectionId = (typeof SECTIONS)[number];
