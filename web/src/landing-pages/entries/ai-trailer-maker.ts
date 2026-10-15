// /make/ai-trailer-maker (2026-10-15). Targets "ai trailer maker" (260, KD
// 20), "ai trailer generator" (110, KD 3) and "ai movie trailer maker" (140,
// KD 19), Semrush US, 2026-10-15. A trailer is a short run of timed shots,
// which is what a scene is; the page says what the studio does and what it
// does not.
//
// TODO(media): no still or clip picked (Mike picks from renders that exist),
// so no wall and a text-only overview.
//
// Checked 2026-10-15 against the code:
// - a scene is 4 to 30 seconds of timed shots: src/timeline.py
// - one still per shot, drawn before any clip: src/scene_chain.keyframe_scene
// - a project's brief and look on every scene in it: src/projects.py, src/looks.py
// - characters as elements with a reference sheet: src/element_sheet.py
// - the editor joins clips in order, with trims, speed, 58 transition styles,
//   captions (cues with text, three styles) and an uploaded music track:
//   src/cut/ops.py, src/cut/render.py
// - NOT in the studio: no music is composed, nothing is cut to a beat
//   automatically, there is no title-card or text-over-picture tool (the only
//   on-screen text is caption cues), no voice-over. The page says so.
import { AMBER } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const TRAILER: MakePage = {
  slug: "ai-trailer-maker",
  section: "make",
  title: "AI Trailer Maker",
  description:
    "Make a trailer for a film, a game or a product with AI: scenes written as timed shots, held to your own photos, joined in the editor over a track you upload.",
  h1: "AI Trailer Maker",
  menu: "AI Trailer Maker",
  subhead: "A trailer is a run of short shots. Write them as one scene, render each one, and cut them together over your own music.",
  cta: {
    label: "Make a trailer",
    spark: "A 30-second trailer in six timed shots for [the film]: the world, the hero, the threat, the turn, the stakes, a final image.",
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: AMBER,
  layout: { order: ["overview", "features", "howTo", "models", "faq", "related", "final"], features: "list" },
  overview: {
    items: [
      {
        eyebrow: "Shots, timed",
        title: "A trailer's shape is a scene's shape.",
        body: "A scene runs 4 to 30 seconds as timed shots, each with its own prompt and its own render. Write the six beats of a trailer and each comes back as a shot with its window written in.",
        points: ["Longer than 30 seconds is several scenes joined on the timeline."],
      },
      {
        eyebrow: "The same faces",
        title: "Your hero is the hero in every shot.",
        body: "Save the characters and places as elements with photos and a reference sheet. Every shot's first frame is drawn from them before a clip is rendered, so you see the face before you pay for the motion.",
      },
      {
        eyebrow: "The cut",
        title: "Cut it in the editor, to your own track.",
        body: "Trim each clip, set a transition, change a speed, add captions and lay a music track you upload under the clips' own sound. Export one MP4.",
        points: [
          "The studio does not compose music and does not cut to the beat for you: place the cuts by ear.",
          "There are no title cards: the only on-screen text is captions.",
        ],
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Trailer Needs",
    items: [
      { icon: "shots", title: "Timed beats", body: "Each beat is a shot with a start and an end inside the scene's length." },
      { icon: "elements", title: "A cast that stays", body: "Characters and places saved once as elements, attached wherever they appear." },
      { icon: "keyframe", title: "Stills first", body: "Every shot's first frame is drawn before its clip, so the trailer can be read as a board." },
      { icon: "guide", title: "One look", body: "A project's brief and look are applied to every scene written in it." },
      { icon: "sound", title: "Sound with the picture", body: "LTX 2.5, Seedance 2.5 and Veo 3.1 render sound in the same pass." },
      { icon: "clock", title: "Drafts", body: "A 480p draft on Wan 3.0 or Seedance 2.5 costs less than the final." },
      { icon: "edit", title: "A real timeline", body: "Trim, split, speed, reverse, 58 transition styles, captions and a mixer." },
      { icon: "export", title: "One MP4", body: "Export at 9:16, 16:9 or 1:1, loudness-normalised." },
      { icon: "price", title: "Priced per shot", body: "Writing is included in your plan; stills and clips show their credits before they are made." },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("veo3.1"), model("seedance2.5"), model("kling3-turbo-pro")]),
  },
  howTo: {
    title: "How to make a trailer with AI",
    items: [
      { title: "Write the beats", body: "Describe the film or the product, with the six beats you want, as one scene. It comes back as timed shots." },
      { title: "Check the frames, render", body: "Draw every shot's first frame, look at the faces, then approve each clip with its price on the card." },
      { title: "Cut it to your track", body: "Open the scene in the editor, upload the music, place the cuts, and export one MP4." },
    ],
  },
  faq: {
    title: "FAQs about the AI Trailer Maker",
    items: [
      {
        q: "Can AI make a movie trailer?",
        a: "It makes the picture. You write the beats, each becomes a timed shot, and the shots render as clips you cut together. It does not produce a finished trailer in one click.",
      },
      {
        q: "Does it add music, a voice-over or title cards?",
        a: "No. You upload your own track in the editor. The studio composes no music, records no narration and has no title-card tool; captions are the only on-screen text. Veo 3.1 can render a spoken line with the picture when a shot asks for one.",
      },
      {
        q: "Does it cut to the beat?",
        a: "Not automatically. Place the cuts by ear on the timeline, with markers if you like.",
      },
      {
        q: "How long can a trailer be?",
        a: "A scene runs 4 to 30 seconds. A longer trailer is several scenes joined in the editor.",
      },
      REFERENCES_FAQ,
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-movie-maker", "ai-short-film-maker", "ai-storyboard-generator", "ai-music-video-generator"],
  finalCta: {
    eyebrow: "Coming soon, to you",
    title: "Write the beats. Cut the trailer.",
    body: "Timed shots, a cast that stays, and your own score.",
  },
};
