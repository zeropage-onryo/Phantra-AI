// What the homepage's Vesper sections draw from (2026-10-15, the mockup Mike
// approved): the demo's scripted briefs, the stills it shows, the three
// models its price checkpoint offers, and the showcase's clips. Pure data,
// so the server sections and the client demo read the same list.
//
// Nothing here is generated: the stills are the posters of the studio's own
// renders that already ship in public/ (via HERO_REEL), and Vesper is the
// Ferryman set already on R2 (lib/mascot.ts). Prices are never typed: the
// checkpoint reads each model's credits off the generated catalogue
// (content/pricing.json, through lib/catalog), for 5-second clips.
import { MODELS, type CatalogModel } from "@/lib/catalog";
import { HERO_REEL, type ReelClip } from "@/content/hero-reel";
import { DEFAULT_MASCOT, MOODS, mascotSrc, type Mood } from "@/lib/mascot";

/** Vesper is the default mascot, the Ferryman in Storm. */
export const vesperSrc = (mood: Mood, size: 320 | 640 = 640) => mascotSrc(DEFAULT_MASCOT, mood, size);
export const VESPER_MOODS = MOODS;
export const VESPER_ALT = "Vesper, the Phantra AI agent";
/** The pitch's one line on a phone, in place of the paragraph (1C · Peek). */
export const PITCH_SHORT = "Plans, draws and renders. Asks before spending.";

/** A reel clip by its poster's file stem ("rooftop", "c375", ...). */
const stem = (clip: ReelClip) => clip.poster.split("/").pop()!.replace(/\.[a-z]+$/, "");
const REEL_BY_STEM = new Map(HERO_REEL.map((clip) => [stem(clip), clip]));
export function reelClip(name: string): ReelClip {
  const clip = REEL_BY_STEM.get(name);
  if (!clip) throw new Error(`vesper: no reel clip "${name}" in HERO_REEL`);
  return clip;
}
/** The poster of a reel clip, a path under public/. */
export const still = (name: string) => reelClip(name).poster;

/* ---- the demo's price checkpoint ---------------------------------- */

export const CLIP_SECONDS = 5;

export type DemoModel = { id: string; name: string; perClip: number };

/** The three the mockup offers, by catalogue id: Kling 3 Turbo Pro (Vesper's
 *  suggestion), Seedance 2.5, Wan 3.0. A 5-second clip's credits, off the
 *  catalogue's own clip length. */
const DEMO_MODEL_IDS = ["kling3-turbo-pro", "seedance2.5", "wan3"] as const;
const byId = (id: string): CatalogModel => {
  const m = MODELS.find((x) => x.model === id);
  if (!m) throw new Error(`vesper: no model ${id} in pricing.json`);
  return m;
};
export const DEMO_MODELS: DemoModel[] = DEMO_MODEL_IDS.map((id) => {
  const m = byId(id);
  return { id, name: m.name, perClip: Math.round((m.credits * CLIP_SECONDS) / m.seconds) };
});
export const priceFor = (model: DemoModel, clips: number) => model.perClip * clips;

/* ---- the demo's scripted briefs ---------------------------------- */

export const LOOKS = ["Moody", "Bright", "Close-up"] as const;
export const TIMECODES = ["0:00–0:05", "0:05–0:10", "0:10–0:15"] as const;

export type Shot = { title: string; looks: [string, string, string] };
export type Brief = {
  say: string;
  ratio: "9:16" | "16:9";
  look: number[];
  stills: string[];
  pool: string[];
  shots: Shot[];
};
export type BriefKey = "sneaker" | "coffee" | "rooftop";

const shot = (title: string, looks: [string, string, string]): Shot => ({ title, looks });

export const BRIEFS: Record<BriefKey, Brief> = {
  sneaker: {
    say: "A 15-second Short: my sneaker drops into a puddle in slow motion.",
    ratio: "9:16",
    look: [0, 2, 0],
    stills: ["skate", "noodles", "surfer"],
    pool: ["leaves", "c135"],
    shots: [
      shot("Sneaker falls", [
        "Night street, one sodium lamp catching the laces as it drops.",
        "Clean daylight, a white sneaker against a pale sky on the way down.",
        "Tight on the sole, tread filling the frame as it falls.",
      ]),
      shot("Impact, water crowns", [
        "A crown of black water lifts in slow motion, neon in every drop.",
        "The splash freezes mid-air, each drop lit by noon sun.",
        "Macro on the toe cap as the water breaks around it.",
      ]),
      shot("Ripples settle", [
        "Ripples fade and the logo surfaces in the reflection.",
        "Wide on the puddle, sky reflected, the sneaker standing still.",
        "The last drop rolls off the heel tab. Hold.",
      ]),
    ],
  },
  coffee: {
    say: "A 15-second brand ad for my coffee roastery, 16:9, warm and slow.",
    ratio: "16:9",
    look: [0, 1, 2],
    stills: ["honey", "noodles", "leaves"],
    pool: ["balloons", "dock"],
    shots: [
      shot("Beans tumble", [
        "Dark roast pours through a single shaft of window light.",
        "Beans bounce across a white counter in morning sun.",
        "Macro on one bean cracking open, oil catching the light.",
      ]),
      shot("The pour", [
        "Espresso threads into the cup, steam curling in the dark.",
        "Milk folds into the cup, a café full of daylight behind.",
        "Tight on the crema as it blooms gold.",
      ]),
      shot("Cup on the counter", [
        "The cup slides in beside the logo, lamp-lit.",
        "A hand lifts the cup; the brand mark sits in soft focus.",
        "Steam rises past the logo on the sleeve. Hold.",
      ]),
    ],
  },
  rooftop: {
    say: "A rooftop reel for Instagram: a dancer at golden hour, 9:16.",
    ratio: "9:16",
    look: [1, 0, 0],
    stills: ["rooftop", "dancer", "boxer"],
    pool: ["c375", "dock"],
    shots: [
      shot("Golden hour on the roof", [
        "Blue hour, city lights coming on behind a lone figure.",
        "Warm sun low on the parapet, long shadows across the roof.",
        "Tight on hands tying a jacket, light flaring through.",
      ]),
      shot("The move", [
        "One spin under string lights, the skyline smeared in motion.",
        "A jump between beats, sun flaring through the hair.",
        "Feet hit the gravel on the beat; dust lifts.",
      ]),
      shot("Skyline wide", [
        "Pull back to the whole skyline, the figure a silhouette.",
        "A slow rise over the roof as the sun touches the horizon.",
        "Eyes to camera, the city out of focus. Cut.",
      ]),
    ],
  },
};

/** A typed idea becomes a three-shot plan of the same shape. */
export function customBrief(text: string): Brief {
  let w = text
    .replace(/[.,!?;:…]+$/, "")
    .split(/\s+/)
    .slice(0, 3)
    .join(" ")
    .replace(/[.,!?;:…]+$/, "");
  if (!/^I\b/.test(w)) w = w.charAt(0).toLowerCase() + w.slice(1);
  return {
    say: text,
    ratio: "9:16",
    look: [0, 0, 0],
    stills: ["c375", "dancer", "leaves"],
    pool: ["dock", "balloons", "boxer"],
    shots: [
      shot(`Open on ${w}`, [
        "Low light and a slow push in, one practical lamp in frame.",
        "Clean, high-key daylight with a slow push in.",
        "Tight framing, shallow focus, detail first.",
      ]),
      shot("The turn", [
        "The moment shifts: a cut to shadow and motion.",
        "The beat lands: a quick move, bright and open.",
        "Macro on the detail that changes everything.",
      ]),
      shot("Close on the payoff", [
        "Hold on the result, lit from one side. Fade.",
        "A wide reveal of the result in full light.",
        "End on a tight hero frame. Cut.",
      ]),
    ],
  };
}

/** The three scene cards under the stage. */
/** `chip` is the one-word name a phone's scene chip shows. */
export const SCENES: { key: BriefKey; label: string; title: string; line: string; chip: string }[] = [
  {
    key: "sneaker",
    label: "Scene 01 · 9:16",
    title: "Sneaker Short",
    line: "A sneaker drops into a puddle in slow motion.",
    chip: "Sneaker",
  },
  {
    key: "coffee",
    label: "Scene 02 · 16:9",
    title: "Coffee brand ad",
    line: "A warm, slow 15-second ad for a roastery.",
    chip: "Coffee",
  },
  { key: "rooftop", label: "Scene 03 · 9:16", title: "Rooftop reel", line: "A dancer on a rooftop at golden hour.", chip: "Rooftop" },
];
export const SCENE_STILL: Record<BriefKey, string> = { sneaker: "skate", coffee: "honey", rooftop: "rooftop" };

/* ---- the showcase ------------------------------------------------- */

/** The eight tiles, by reel clip, with the tile's shape. The caption is the
 *  mockup's line for the same clip where it has one, else the clip's title. */
export const SHOWCASE: { name: string; ar: string; line?: string }[] = [
  { name: "rooftop", ar: "9/16", line: "A laugh on a windy rooftop, golden hour" },
  { name: "honey", ar: "4/5" },
  { name: "c375", ar: "1/1", line: "Neon city, rain on the lens" },
  { name: "boxer", ar: "4/5" },
  { name: "balloons", ar: "9/16" },
  { name: "dock", ar: "1/1", line: "Two hands on one fishing rod at dawn" },
  { name: "dancer", ar: "9/16" },
  { name: "leaves", ar: "4/5" },
];

/* ---- the models strip --------------------------------------------- */

export const STRIP_MODELS = [
  "Kling 3",
  "Seedance 2.5",
  "Veo 3.1",
  "Wan 3.0",
  "LTX 2.3",
  "Nano Banana Pro",
  "FLUX.2",
  "GPT Image 2",
  "Seedream 4.5",
  "Ideogram 4.5",
];

/* ---- prefill: a starting point or a showcase tile into the demo ---- */

/** The event a card sends and the demo's composer answers. */
export const PREFILL_EVENT = "vesper:prefill";
