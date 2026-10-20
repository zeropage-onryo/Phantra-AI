/* Brand kits (2026-10-20, docs/tasks/task-brand-kit.md; src/brand_kits.py).

   A kit belongs to the account and does nothing until a project picks it.
   This is the page's half, with nothing imported, so
   tests/brand-kit.test.mjs runs it as it is: the spec's shape and its
   empty value, the checks the form makes before a save (the API makes the
   same ones and is the judge), what a palette role resolves to, which logo
   reads on a card, and the @font-face a kit's font file needs. */

export type PaletteRole = "primary" | "accent" | "background" | "text" | "extra";
export const PALETTE_ROLES: PaletteRole[] = ["primary", "accent", "background", "text", "extra"];
export type Swatch = { hex: string; role: PaletteRole; name: string };
export type Link = { kind: "prop" | "character"; id: number; name: string; claims?: string[] };

export type KitSpec = {
  v?: number;
  identity: { tagline: string; positioning: string; audience: string; url: string };
  palette: Swatch[];
  captions: {
    font: "heading" | "body";
    size: number;
    fill: Exclude<PaletteRole, "extra">;
    outline: "none" | Exclude<PaletteRole, "extra">;
    box: "none" | Exclude<PaletteRole, "extra">;
    position: "bottom" | "lower_third" | "top";
    uppercase: boolean;
  };
  safe_zone: number;
  aspect: "" | "16:9" | "9:16" | "1:1";
  motion: { transition: string; seconds: number };
  end_card: { on: boolean; seconds: number; background: Exclude<PaletteRole, "extra">; show_url: boolean };
  look: { style: string; banned: string[] };
  voice: { tone: string; use: string[]; avoid: string[]; cta: string };
  sound: {
    voice: string;
    music: { genre: string; bpm: number | null; mood: string };
    loudness: number | null;
  };
  products: Link[];
  never_claim: string[];
  characters: Link[];
};

export type KitFile = {
  id: number;
  role: string;
  mime: string;
  filename: string;
  family?: string | null;
  width?: number | null;
  height?: number | null;
  url: string;
};

export type Kit = {
  id: number;
  name: string;
  spec: KitSpec;
  hash: string;
  files: KitFile[];
  projects?: number | null;
  created_at: string;
  updated_at: string;
  /** the line every still, keyframe and clip gains under this kit */
  look_suffix: string;
};

export const LIMITS = { style: 1500, tone: 1000, cta: 300, line: 200, tagline: 120, references: 8, palette: 8 };

export function emptySpec(): KitSpec {
  return {
    identity: { tagline: "", positioning: "", audience: "", url: "" },
    palette: [],
    captions: { font: "heading", size: 0.05, fill: "text", outline: "none", box: "none", position: "bottom", uppercase: false },
    safe_zone: 0.06,
    aspect: "",
    motion: { transition: "fade", seconds: 0.6 },
    end_card: { on: true, seconds: 2.5, background: "background", show_url: true },
    look: { style: "", banned: [] },
    voice: { tone: "", use: [], avoid: [], cta: "" },
    sound: { voice: "", music: { genre: "", bpm: null, mood: "" }, loudness: null },
    products: [],
    never_claim: [],
    characters: [],
  };
}

/** a stored spec over the empty one, so an older or partial spec still fills every field */
export function withDefaults(spec: Partial<KitSpec> | null | undefined): KitSpec {
  const base = emptySpec();
  const s = (spec ?? {}) as Partial<KitSpec>;
  return {
    ...base,
    ...s,
    identity: { ...base.identity, ...(s.identity ?? {}) },
    captions: { ...base.captions, ...(s.captions ?? {}) },
    motion: { ...base.motion, ...(s.motion ?? {}) },
    end_card: { ...base.end_card, ...(s.end_card ?? {}) },
    look: { ...base.look, ...(s.look ?? {}) },
    voice: { ...base.voice, ...(s.voice ?? {}) },
    sound: { ...base.sound, ...(s.sound ?? {}), music: { ...base.sound.music, ...(s.sound?.music ?? {}) } },
    palette: s.palette ?? [],
    products: s.products ?? [],
    characters: s.characters ?? [],
    never_claim: s.never_claim ?? [],
  };
}

const HEX = /^#[0-9a-fA-F]{6}$/;
export const isHex = (v: unknown): v is string => typeof v === "string" && HEX.test(v.trim());

/** "#f7931e" / "f7931e" / "#F93" -> "#F7931E", or null */
export function normaliseHex(raw: string): string | null {
  let v = (raw ?? "").trim().replace(/^#?/, "#");
  if (/^#[0-9a-fA-F]{3}$/.test(v)) v = "#" + v.slice(1).split("").map((c) => c + c).join("");
  return isHex(v) ? v.toUpperCase() : null;
}

/** a comma- or line-separated field -> its trimmed, de-duplicated entries */
export function splitList(raw: string): string[] {
  const out: string[] = [];
  for (const part of (raw ?? "").split(/[\n,]/)) {
    const t = part.trim();
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

/** the problems the form shows before a save: [field, message] */
export function problems(name: string, spec: KitSpec): [string, string][] {
  const out: [string, string][] = [];
  if (!name.trim()) out.push(["name", "a brand kit needs a name"]);
  spec.palette.forEach((s, i) => {
    if (!isHex(s.hex)) out.push(["palette", `colour ${i + 1} is not a #RRGGBB hex`]);
  });
  for (const role of PALETTE_ROLES.slice(0, -1)) {
    if (spec.palette.filter((s) => s.role === role).length > 1) out.push(["palette", `only one colour can be the ${role}`]);
  }
  if (spec.palette.length > LIMITS.palette) out.push(["palette", `a palette holds at most ${LIMITS.palette} colours`]);
  if (spec.look.style.length > LIMITS.style) out.push(["style description", `at most ${LIMITS.style} characters`]);
  if (spec.voice.tone.length > LIMITS.tone) out.push(["tone", `at most ${LIMITS.tone} characters`]);
  return out;
}

/** the colour a role resolves to, or the fallback */
export function roleColour(spec: KitSpec, role: string, fallback = "#FFFFFF"): string {
  return spec.palette.find((s) => s.role === role)?.hex ?? fallback;
}

export function luma(hex: string): number {
  const h = (normaliseHex(hex) ?? "#FFFFFF").slice(1);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** the logo role that reads on a background: the light-background logo on a light card */
export function logoFor(background: string): "logo_light" | "logo_dark" {
  return luma(background) >= 0.5 ? "logo_light" : "logo_dark";
}

/** the kit's file in a role (newest), or undefined */
export const fileFor = (kit: Pick<Kit, "files">, role: string) =>
  [...(kit.files ?? [])].reverse().find((f) => f.role === role);

/** the CSS family a kit's font is loaded under on this page, so two kits'
    "Inter"s never collide */
export const fontAlias = (kitId: number, which: "heading" | "body") => `phantra-kit-${kitId}-${which}`;

/** @font-face rules for a kit's two fonts; `origin` is the API origin ("" behind the proxy) */
export function fontFaces(kit: Pick<Kit, "id" | "files">, origin = ""): string {
  const rules: string[] = [];
  for (const which of ["heading", "body"] as const) {
    const f = fileFor(kit, `font_${which}`);
    if (!f) continue;
    const format = f.mime === "font/otf" ? "opentype" : "truetype";
    rules.push(`@font-face{font-family:"${fontAlias(kit.id, which)}";src:url("${origin}${f.url}") format("${format}");font-display:swap}`);
  }
  return rules.join("\n");
}

/** the font stack a preview uses for one of the kit's fonts */
export function fontStack(kit: Pick<Kit, "id" | "files">, which: "heading" | "body"): string {
  const own = fileFor(kit, `font_${which}`) ? `"${fontAlias(kit.id, which)}", ` : "";
  const other = which === "heading" ? "body" : "heading";
  const fallback = fileFor(kit, `font_${other}`) ? `"${fontAlias(kit.id, other)}", ` : "";
  return `${own}${fallback}system-ui, sans-serif`;
}

/** what the kit card says under its name */
export function kitSummary(kit: Pick<Kit, "files" | "projects" | "spec">): string {
  const refs = (kit.files ?? []).filter((f) => f.role === "reference").length;
  const fonts = (kit.files ?? []).filter((f) => f.role.startsWith("font_")).length;
  const bits = [
    `${kit.spec?.palette?.length ?? 0} colour${kit.spec?.palette?.length === 1 ? "" : "s"}`,
    `${fonts} font${fonts === 1 ? "" : "s"}`,
    `${refs} reference${refs === 1 ? "" : "s"}`,
  ];
  const used = kit.projects ?? 0;
  bits.push(used ? `in ${used} project${used === 1 ? "" : "s"}` : "not picked yet");
  return bits.join(" · ");
}

/** the roles an upload slot takes, in the order the form shows them */
export const FILE_SLOTS: { role: string; label: string; accept: string }[] = [
  { role: "logo_light", label: "Logo · for light backgrounds", accept: "image/png,image/webp,image/jpeg,image/svg+xml" },
  { role: "logo_dark", label: "Logo · for dark backgrounds", accept: "image/png,image/webp,image/jpeg,image/svg+xml" },
  { role: "font_heading", label: "Heading font", accept: ".ttf,.otf,font/ttf,font/otf" },
  { role: "font_body", label: "Body font", accept: ".ttf,.otf,font/ttf,font/otf" },
];

export const isFontRole = (role: string) => role === "font_heading" || role === "font_body";
export const isSvg = (file: { type?: string; name?: string }) =>
  file.type === "image/svg+xml" || /\.svg$/i.test(file.name ?? "");
