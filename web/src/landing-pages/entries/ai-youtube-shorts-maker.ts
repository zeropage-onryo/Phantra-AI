// /make/ai-youtube-shorts-maker (2026-10-11). What it says about YouTube is
// one fact: a Short is a vertical video. It does not upload to YouTube: the
// page says so.
//
// This page's angle among the three social pages is LENGTH and story: one
// scene up to 30 seconds, several joined, a spoken line, captions. (Reels'
// is the look; TikTok's is speed.)
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and every overview slot is a
// plate.
//
// Checked 2026-10-11 against the code:
// - a scene is 4 to 30 seconds of timed shots; a shot's window is fitted to
//   a length its model renders: src/timeline.py
// - the longest single clip per model is read off fal.VIDEO_MODELS:
//   Seedance 2.5 to 30 s, LTX 2.5 Fast to 20 s, Kling and Seedance 2.0 to 15 s
// - a spoken line rendered with the picture on Veo 3.1: the Veo page's own
//   claim, and the catalog's "with sound"
// - scenes joined on the timeline; captions typed at the playhead or
//   proposed from a clip's speech (kept or undone); the mixer: src/cut
// - 1080p from Kling, and up to 2160p from LTX: the catalog
// - one MP4, loudness-normalised, at 9:16: src/cut/render.py
import { INDIGO } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const SHORTS: MakePage = {
  slug: "ai-youtube-shorts-maker",
  section: "make",
  title: "AI YouTube Shorts Maker",
  description:
    "Make YouTube Shorts with a beginning and an end: vertical scenes up to 30 seconds, written as timed shots, joined, captioned and exported as one MP4.",
  h1: "AI YouTube Shorts Maker",
  menu: "AI YouTube Shorts Maker",
  subhead: "A Short with a beginning and an end: scenes up to 30 seconds, written as shots, joined on a timeline and captioned.",
  cta: {
    label: "Make a Short",
    spark: "A 30-second vertical Short in five shots: a setup, a turn, a payoff. [Who], [where], [what happens].",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: INDIGO,
  layout: { order: ["overview", "features", "models", "howTo", "faq", "related", "final"] },
  overview: {
    items: [
      {
        eyebrow: "Room for a story",
        title: "One scene runs up to 30 seconds.",
        body: "Set the length anywhere from 4 to 30 seconds and the scene is written to fill it: a setup, a turn, a payoff, each a timed shot. Each shot is fitted to a clip length its model renders, and Seedance 2.5 will hold a single shot for the whole 30.",
        points: [
          "As many shots as the story needs, or the number you ask for.",
          "For one unbroken take, ask for one.",
        ],
      },
      {
        eyebrow: "More than one scene",
        title: "Join scenes into a longer Short.",
        body: "Write the next scene in the same project and it is held to the same look and the same people. Bring the clips onto one timeline and the Short is as long as the scenes you made.",
      },
      {
        eyebrow: "Heard as well as seen",
        title: "A spoken line, the room, then captions.",
        body: "Veo 3.1 renders a line of dialogue with the picture, and LTX 2.5 and Seedance 2.5 render the scene's own sound. Captions are typed at the playhead, or proposed from the words spoken in a clip for you to keep or undo.",
      },
      {
        eyebrow: "The upload",
        title: "One vertical MP4, levelled.",
        body: "Export the cut at 9:16 with its loudness normalised and the captions burned in. You upload it to YouTube yourself.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Short Is Made Of",
    items: [
      {
        icon: "clock",
        title: "4 to 30 seconds a scene",
        body: "The length is a slider, and the scene's timed shots add up to it.",
      },
      {
        icon: "shots",
        title: "A structure, written in",
        body: "Say setup, turn, payoff and the shots come back in that order with their timings.",
      },
      {
        icon: "elements",
        title: "The same host every time",
        body: "Save the person who fronts the channel as an element, and every Short draws its first frames from their photos.",
      },
      {
        icon: "sound",
        title: "Dialogue and sound",
        body: "A spoken line on Veo 3.1, and sound rendered with the picture on LTX 2.5 and Seedance 2.5.",
      },
      {
        icon: "type",
        title: "Captions two ways",
        body: "Type them where the playhead is, or have them proposed from the speech and keep the ones that are right.",
      },
      {
        icon: "frame",
        title: "Vertical, at 1080p and up",
        body: "9:16 by default. Kling renders at 1080p and LTX up to 2160p.",
      },
      {
        icon: "edit",
        title: "A timeline for the join",
        body: "Scenes are trimmed against each other, with a transition where you want one and a mixer for the sound.",
      },
      {
        icon: "price",
        title: "Long clips, priced first",
        body: "A 30-second shot costs more than a 5-second one. The Render card shows the number for the length you set.",
      },
      {
        icon: "export",
        title: "A file to upload",
        body: "One MP4. The studio does not upload to YouTube or connect to your channel.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("seedance2.5"), model("veo3.1"), model("ltx2.5-fast")]),
  },
  howTo: {
    title: "How to make a YouTube Short",
    items: [
      {
        title: "Write it with a shape",
        body: "Sign in, set the length, and write one line with a setup, a turn and a payoff. Attach the photos it must be held to.",
      },
      {
        title: "Check the stills and render",
        body: "Draw each shot's still on the scene's Render card. Pick the model, read the price for that length, and approve.",
      },
      {
        title: "Join, caption, export",
        body: "Open the scene in the editor, add any other scenes, lay the captions, and export one vertical MP4.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Shorts Maker",
    items: [
      {
        q: "What is an AI YouTube Shorts maker?",
        a: "A tool that generates short vertical video for YouTube Shorts. This one writes the Short as scenes of timed shots, draws each shot's first frame from your photos, renders the shots on the video model you pick, and exports one captioned MP4.",
      },
      {
        q: "Does it upload to YouTube?",
        a: "No. It exports an MP4 and you upload it. The studio does not upload, schedule, or connect to your channel.",
      },
      {
        q: "How long can a Short be?",
        a: "One scene runs 4 to 30 seconds. Join several scenes on the timeline for a longer one. Check YouTube's current limit for Shorts before you plan the length: the studio does not know it.",
      },
      {
        q: "Can one shot run the full 30 seconds?",
        a: "On Seedance 2.5, yes: it renders a single clip of up to 30 seconds. Other models render shorter clips, so a 30-second scene on them is several shots.",
      },
      {
        q: "Can the person in it speak?",
        a: "Veo 3.1 renders a spoken line with the picture when the scene writes one. Keep lines short, and listen to the clip: speech is the part most likely to need a second take. The studio has no lip-sync tool for audio you recorded.",
      },
      {
        q: "Can I add captions?",
        a: "Yes, in the editor: type a caption where the playhead is, or have captions proposed from the speech in a clip and keep the ones that are right. They are burned into the export.",
      },
      REFERENCES_FAQ,
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-instagram-reels-maker", "ai-tiktok-video-generator", "ai-short-film-maker"],
  finalCta: {
    eyebrow: "Thirty seconds",
    title: "A setup, a turn, a payoff.",
    body: "Write it as shots, check the stills, and export one vertical MP4.",
  },
};
