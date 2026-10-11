// The clips in the homepage hero's reel (2026-10-11, Mike's L5 "Split
// Reel"). Every one is REAL studio output -- never stock.
//
// Most come from the model landing pages (Mike, 2026-10-11: "take them
// from the various landing pages for now"): their MP4s live in the R2
// bucket under site/models/<slug>/ (landing-pages/media.ts says why) and
// their posters ship in public/models/<slug>/. Only portrait clips are
// used -- the tiles are 9:16, and a 16:9 clip cropped into one shows a
// sliver. Two are the studio's own renders, web copies in public/site/reel/.
//
// To change the reel, change this list. `column` is which of the two base
// columns a clip rides in (0 scrolls up, 1 down; the extra columns on a
// big screen reuse both, rotated); on a phone the two are one strip.

import { CLIP_BASE } from "@/landing-pages/media";

export type ReelClip = {
  title: string;
  /** the model's name, as the tag on the tile reads it */
  model: string;
  mp4: string;
  poster: string;
  column: 0 | 1;
};

/** a clip from a landing page: bucket MP4, poster from public/models */
const page = (slug: string, name: string, title: string, model: string, column: 0 | 1): ReelClip => ({
  title,
  model,
  mp4: `${CLIP_BASE}/models/${slug}/${name}.mp4`,
  poster: `/models/${slug}/${name}.jpg`,
  column,
});
const KLING = "kling-video-generator";
const WAN = "wan-video-generator";
const SEEDANCE = "seedance-video-generator";
const R = "/site/reel";

export const HERO_REEL: ReelClip[] = [
  page(KLING, "rooftop", "A laugh on a windy rooftop", "Kling 3 Turbo Pro", 0),
  page(SEEDANCE, "honey", "Honey off a dipper, macro", "Seedance 2.5", 0),
  page(WAN, "leaves", "Autumn leaves in a gust", "Wan 3.0", 0),
  page(KLING, "boxer", "Shadowboxing in one shaft of light", "Kling 3 Turbo Pro", 0),
  page(SEEDANCE, "surfer", "Backlight and water", "Seedance 2.5", 0),
  { title: "Neon city", model: "Runway Gen-4 Turbo", mp4: `${R}/c375.mp4`, poster: `${R}/c375.jpg`, column: 0 },
  page(SEEDANCE, "skate", "Spray and momentum", "Seedance 2.5", 0),
  page(KLING, "dancer", "Popping and locking under a bridge", "Kling 3 Turbo Pro", 1),
  page(WAN, "balloons", "Balloons over a canyon at sunrise", "Wan 3.0", 1),
  page(SEEDANCE, "noodles", "Rain and steam", "Seedance 2.5", 1),
  { title: "Creature comedy", model: "Seedance 2 Fast", mp4: `${R}/c135.mp4`, poster: `${R}/c135.jpg`, column: 1 },
  page(KLING, "dock", "Two hands on one fishing rod", "Kling 3 Turbo Pro", 1),
  page(SEEDANCE, "table", "Multi-beat action", "Seedance 2.5", 1),
];
