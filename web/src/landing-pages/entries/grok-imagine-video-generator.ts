// The Grok Imagine page (2026-10-23, Mike: "grok imagine is available on
// fal ... possibly get a landing page going"; direction C, "Clip in the
// Letters", picked off the canvas and recoloured Marigold the same day).
//
// WHAT RENDERS: Grok Imagine Video 1.5 and 1.5 Lite through fal, xAI's own
// `xai/` endpoints (src/fal.py VIDEO_MODELS "grok1.5" / "grok1.5-lite",
// read off fal's queue OpenAPI schemas 2026-10-23): any whole number of
// seconds from 1 to 15 a take, 480p / 720p / 1080p on the Render card,
// seven frame shapes on text-to-video (fal.T2V_ASPECTS), image-to-video
// off a shot's keyframe, sound generated with the picture (fal's model
// page: "videos from prompts with audio"). The `grok` platform renders on
// Lite by default (fal.PLATFORM_MODELS); 1.5 is one pick away.
//
// LAYOUT: the first page on the dark tone and on the PHANTRA (marigold)
// accent; hero "knockout" (new), signature "spec-numbers" (new), wall
// "tape" (new) -- a twin of no page. No pricing section and no credit
// figure anywhere (Mike, 2026-10-22: nothing about costs on a new page),
// and no small wording (2026-10-23): no eyebrow, no tile caption.
//
// SEARCH: Semrush had no API units on 2026-10-23, so the phrase is the one
// every competitor page uses ("Grok Imagine", invideo/Higgsfield/Krea) plus
// the house "AI Video Generator" suffix. Re-check volume when units return.
//
// MEDIA: none yet, on purpose. The page waits for Grok clips Mike approves
// (2026-10-23); until then every slot is a marigold plate. When they land:
// heroMedia[0] plays inside the letters (muted), signatureFrames[0..3] are
// the four figures' clips, wall.tiles the reel (each with `aspect`), and a
// FAQ answer "Were the clips on this page made on Grok Imagine?" credits
// the model and settings (the no-caption rule puts it there, not on tiles).
import { COMMERCIAL_FAQ, REFERENCES_FAQ } from "../shared";
import { PHANTRA } from "../theme";
import type { MakePage, MakeTile } from "../pages";

/** An empty slot: the accent's plate until a Grok clip is approved. */
const slot = (aspect: string): MakeTile => ({ title: "", tag: "", aspect });

export const GROK: MakePage = {
  slug: "grok-imagine-video-generator",
  section: "models",
  modelIds: ["grok1.5", "grok1.5-lite"],
  navLabel: "Grok Imagine",
  title: "Grok Imagine AI Video Generator: Grok Imagine 1.5 and 1.5 Lite",
  description:
    "Make videos on xAI's Grok Imagine 1.5 with sound made in the same pass. Takes from 1 to 15 seconds, up to 1080p, in seven frame shapes from wide to tall.",
  h1: "Grok Imagine AI Video Generator",
  menu: "Grok Imagine Video Generator",
  subhead: "xAI's video model, with sound made in the same pass as the picture.",
  cta: {
    label: "Make a Grok video",
    spark: "A vertical 8-second take of one person and the sound of the room around them. Render on Grok Imagine 1.5.",
    secondary: { label: "The numbers", href: "#numbers" },
    startLabel: "Start a scene",
  },
  template: "spark",
  tone: "dark",
  accent: PHANTRA,
  layout: {
    hero: "knockout",
    order: ["signature", "wall", "models", "faq", "related", "final"],
  },
  heroWord: "GROK",
  heroMedia: [slot("16:9")],
  signature: "spec-numbers",
  specs: {
    title: "Grok in four numbers",
    items: [
      { big: "15", small: "seconds a take" },
      { big: "1080", small: "p at the top" },
      { big: "7", small: "frame shapes" },
      { big: "1", small: "pass, picture and sound" },
    ],
  },
  signatureFrames: [slot("4:5"), slot("4:5"), slot("4:5"), slot("4:5")],
  wall: {
    title: "Takes on the reel",
    tiles: [slot("9:16"), slot("16:9"), slot("9:16"), slot("1:1"), slot("9:16")],
    explore: { label: "Make a Grok video", href: "#numbers" },
    layout: "tape",
  },
  // Not drawn (layout.order leaves them out): the page is its hero, its
  // numbers and its reel. The type wants them, and they are true.
  features: { title: "Grok in the Studio", items: [] },
  howTo: { title: "How to render on Grok", items: [] },
  models: {
    title: "Two Grok Models",
    items: [
      {
        title: "Grok Imagine 1.5",
        body: "xAI's full model, with sound. Pick 480p, 720p or 1080p on the Render card.",
        spark: "A vertical 10-second take with its own sound. Render on Grok Imagine 1.5.",
      },
      {
        title: "Grok Imagine 1.5 Lite",
        body: "Grok's quick tier, with sound, up to 1080p. Good for trying an idea first.",
        spark: "A vertical 6-second take with its own sound. Render on Grok Imagine 1.5 Lite.",
      },
      {
        title: "Every model",
        body: "Kling, Veo, Seedance, LTX and Wan sit beside Grok on the same card.",
        link: { href: "/models", label: "See every model" },
      },
    ],
  },
  faq: {
    title: "FAQs about Grok Imagine",
    items: [
      {
        q: "What is Grok Imagine?",
        a: "Grok Imagine is xAI's video model. In Phantra you write the idea, and each shot renders as its own Grok Imagine clip, with sound, that you can join into one MP4.",
      },
      {
        q: "How long can a Grok Imagine clip be?",
        a: "Any whole number of seconds from 1 to 15 a take.",
      },
      {
        q: "What resolution does it render at?",
        a: "480p, 720p or 1080p, picked on the scene's Render card. It starts at 720p.",
      },
      {
        q: "Which frame shapes does it make?",
        a: "Seven on text-to-video: 16:9, 4:3, 3:2, 1:1, 2:3, 3:4 and 9:16. From a start frame, the clip takes that picture's shape.",
      },
      {
        q: "Does Grok Imagine make sound?",
        a: "Yes. Grok Imagine makes the sound in the same pass as the picture, and the clip comes back with it.",
      },
      {
        q: "What is the difference between 1.5 and 1.5 Lite?",
        a: "Grok Imagine 1.5 is xAI's full model. 1.5 Lite is its quick tier, with sound and the same lengths, frames and resolutions. Both are on the Render card.",
      },
      REFERENCES_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["veo-video-generator", "kling-video-generator", "seedance-video-generator", "text-to-video"],
  finalCta: {
    eyebrow: "",
    title: "Tell Vesper the idea.",
    body: "It can put the scene on Grok, and you approve the take on its card.",
  },
};
