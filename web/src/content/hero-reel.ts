// The clips in the homepage hero's reel (2026-10-11, Mike's L5 "Split
// Reel"). Every one is REAL studio output -- a render a scene in the
// studio made -- never stock. The files are web copies (540x960 H.264,
// muted on the page) in public/site/reel/, the poster beside each one.
//
// To change the reel, change this list: add a clip to public/site/reel/
// with a poster frame, and name it here. `column` is which of the two
// scrolling columns it rides in (0 scrolls up, 1 scrolls down); on a
// phone the two are one strip, in list order. Each column wants at least
// three clips so a loop is taller than the screen.

export type ReelClip = {
  /** the concept it was rendered for, for the record */
  concept: number;
  title: string;
  /** the model's name, as the tag on the tile reads it */
  model: string;
  mp4: string;
  poster: string;
  column: 0 | 1;
};

const R = "/site/reel";

export const HERO_REEL: ReelClip[] = [
  { concept: 384, title: "Product film", model: "LTX 2.3", mp4: `${R}/c384-1.mp4`, poster: `${R}/c384-1.jpg`, column: 0 },
  { concept: 194, title: "Night-shift horror", model: "LTX 2.3", mp4: `${R}/c194.mp4`, poster: `${R}/c194.jpg`, column: 0 },
  { concept: 384, title: "Product film", model: "LTX 2.3", mp4: `${R}/c384-3.mp4`, poster: `${R}/c384-3.jpg`, column: 0 },
  { concept: 135, title: "Creature comedy", model: "Seedance 2 Fast", mp4: `${R}/c135.mp4`, poster: `${R}/c135.jpg`, column: 1 },
  { concept: 375, title: "Neon city", model: "Runway Gen-4 Turbo", mp4: `${R}/c375.mp4`, poster: `${R}/c375.jpg`, column: 1 },
  { concept: 384, title: "Product film", model: "LTX 2.3", mp4: `${R}/c384-2.mp4`, poster: `${R}/c384-2.jpg`, column: 1 },
];
