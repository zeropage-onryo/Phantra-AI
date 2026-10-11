// /make/ai-instagram-reels-maker (2026-10-11). What it says about Instagram
// is one fact: a Reel is a vertical video. Everything else is what the
// studio does. It does not post: the page says so.
//
// This page's angle among the three social pages is the LOOK: one grid that
// reads as one account. (TikTok's is speed and effects; Shorts' is length.)
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and every overview slot is a
// plate.
//
// Checked 2026-10-11 against the code:
// - 9:16 is the default frame a scene is written for, one of six:
//   render_specs.FRAME_SIZES, /api/render-choices
// - a project's look and brief on every scene in it: src/looks.py, src/projects.py
// - recurring people and products as elements: src/element_sheet.py
// - a cover as a still at 9:16 or 4:5: fal.IMAGE_SIZES
// - sound in the same pass on LTX 2.5, Seedance 2.5 and Veo 3.1: the catalog
// - captions in three styles, burned in; a music bed you upload; one MP4,
//   loudness-normalised: src/cut
// - the studio posts nothing (autopilot.AUTO_POST_BRANDS is empty and no
//   posting is offered in the studio)
import { ROSE } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const REELS: MakePage = {
  slug: "ai-instagram-reels-maker",
  section: "make",
  title: "AI Instagram Reels Maker",
  description:
    "Make Reels that look like one account: vertical scenes written as timed shots, held to your own photos and one look, captioned and exported as one MP4.",
  h1: "AI Instagram Reels Maker",
  menu: "AI Instagram Reels Maker",
  subhead: "Vertical scenes, written as shots and held to your photos and your look, so every Reel reads as the same account.",
  cta: {
    label: "Make a Reel",
    spark: "A 9-second vertical Reel in three shots: [the subject], [the place], [the moment]. Our usual look.",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: ROSE,
  layout: { order: ["overview", "features", "howTo", "models", "faq", "related", "final"], features: "split" },
  overview: {
    items: [
      {
        eyebrow: "Vertical from the start",
        title: "A scene is written for 9:16 unless you say otherwise.",
        body: "The frame is chosen when the scene is written, and vertical is the default. Each shot's still is drawn at that shape and the clip starts on the still, so nothing is cropped from a wide picture afterwards.",
      },
      {
        eyebrow: "One look",
        title: "The grid reads as one account.",
        body: "Put the account's look and its rules in a project, and save the people, products and places that recur as elements. Every Reel written in the project is held to the same look and the same faces, week after week.",
        points: [
          "The look is a paragraph you write once. The studio has no style of its own to impose.",
          "A cover can be drawn as a still in the same look, at 9:16 or 4:5.",
        ],
      },
      {
        eyebrow: "Ready to upload",
        title: "Captioned, levelled, one file.",
        body: "Join the shots on the timeline, add caption cues in one of three styles and a music bed you upload, and export one MP4 with its loudness normalised. You upload it to Instagram yourself.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Reel Is Made Of",
    items: [
      {
        icon: "frame",
        title: "9:16 by default",
        body: "The scene, its stills and its clips are all made vertical. Wide and square are there when you want them.",
      },
      {
        icon: "guide",
        title: "A look that is kept",
        body: "A project's look rides into every scene written in it, so the fortieth Reel matches the first.",
      },
      {
        icon: "elements",
        title: "The faces of the account",
        body: "A founder, a product, a studio: saved once as elements and attached wherever they appear.",
      },
      {
        icon: "shots",
        title: "Short shots, real cuts",
        body: "A scene is cut into timed shots as it is written. Ask for three in nine seconds and that is what you get.",
      },
      {
        icon: "sound",
        title: "Sound in the clip",
        body: "LTX 2.5, Seedance 2.5 and Veo 3.1 render the scene's own sound with the picture.",
      },
      {
        icon: "type",
        title: "Captions burned in",
        body: "Caption cues go on the timeline, in bold centre, lower third or a small top line, and are part of the export.",
      },
      {
        icon: "keyframe",
        title: "The first frame, checked",
        body: "Each shot is a still before it is a clip, so the opening frame is one you have already looked at.",
      },
      {
        icon: "price",
        title: "A week of Reels, priced",
        body: "Each clip shows its credits before it renders. Draft on Wan 3.0 or Seedance 2.5 at 480p when you are still deciding.",
      },
      {
        icon: "export",
        title: "A file, not a post",
        body: "The studio exports an MP4. It does not post to Instagram, schedule, or read your account.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("kling3-turbo-pro"), model("ltx2.5-fast"), model("seedance2.5")]),
  },
  howTo: {
    title: "How to make a Reel",
    items: [
      {
        title: "Set the look once",
        body: "Sign in, start a project for the account, and write its look. Add the people and products that recur as elements.",
      },
      {
        title: "Write this week's scenes",
        body: "One line a Reel, with the number of shots. Check each shot's still, then render on the model you pick, with the price on the card.",
      },
      {
        title: "Caption and export",
        body: "Open the scene in the editor, add captions and your audio, and export one vertical MP4. Upload it from your phone as usual.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Reels Maker",
    items: [
      {
        q: "What is an AI Reels maker?",
        a: "A tool that generates short vertical video for Instagram Reels. This one writes each Reel as a scene of timed shots, draws each shot's first frame from your own photos, renders the shots on the video model you pick, and exports them as one captioned MP4.",
      },
      {
        q: "Does it post to Instagram for me?",
        a: "No. It exports a file and you upload it. The studio does not post, schedule, or connect to your Instagram account.",
      },
      {
        q: "How do I keep every Reel in the same style?",
        a: "Write the look once in a project and make every Reel inside it. Save recurring people, products and places as elements. Each scene is then written to the same look and its first frames are drawn from the same pictures.",
      },
      {
        q: "Are the videos vertical?",
        a: "Yes, by default. A scene is written for 9:16 unless you choose another of the six frames, and the stills and clips are made at that shape.",
      },
      {
        q: "How long can a Reel be?",
        a: "One scene runs 4 to 30 seconds. For something longer, write several scenes and join them on the timeline.",
      },
      {
        q: "Can I add captions and music?",
        a: "Yes, in the editor. Caption cues come in three styles and are burned into the export. Audio you upload sits on its own track under the clips' sound. The studio does not supply or license music.",
      },
      REFERENCES_FAQ,
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-tiktok-video-generator", "ai-youtube-shorts-maker", "ai-commercial-maker"],
  finalCta: {
    eyebrow: "This week's Reels",
    title: "One look. A Reel a line.",
    body: "Set the look once, write the scenes, export vertical MP4s.",
  },
};
