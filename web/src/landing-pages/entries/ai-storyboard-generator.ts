// /make/ai-storyboard-generator (2026-10-11): a scene's timed shots and the
// still drawn for each one ARE a storyboard, and here every panel is also
// the first frame of the clip that follows.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - timed windows, one shot a window, the count the idea asks for:
//   src/timeline.py (parse_windows, requested_shots, shot_count_warnings)
// - one still a shot, each labelled as its clip's first frame, the previous
//   shot's still handed in for continuity: scene_chain._keyframe_timeline
// - the strip priced as a whole and one shot's still on its own:
//   scene_chain.keyframe_quote and the per-shot keyframe route (PR #237)
// - a changed shot loses its still and the unchanged ones keep theirs:
//   timeline.ensure (stale on read, stills carried over by window, sentence
//   and refs); the one missing still is then drawn alone
// - a project's brief, look and memory: src/projects.py
// - there is NO storyboard export (no PDF, no contact sheet): the stills
//   are in the Library, one by one. The page does not claim one.
import { SLATE } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

// Media (2026-10-14, Mike asked for Higgsfield): one scene, a courier's
// delivery in the rain, boarded as six stills on Nano Banana 2 (Higgsfield,
// 1K, 16:9), the courier described the same way in every prompt. Layout:
// hero "fan" + signature "shot-timeline" (this page's own scene, through
// `timeline`) + wall "editorial"; no other page has that combination.
const DIR = "/make/ai-storyboard-generator";

export const STORYBOARD: MakePage = {
  slug: "ai-storyboard-generator",
  section: "make",
  title: "AI Storyboard Generator",
  description:
    "Turn an idea into a storyboard: timed shots, one still per shot drawn from your own photos, each still the first frame of the clip you can render next.",
  h1: "AI Storyboard Generator",
  menu: "AI Storyboard Generator",
  subhead: "One line becomes timed shots, and each shot gets its own still, held to your photos. The board you approve is the film's first frames.",
  cta: {
    label: "Storyboard a scene",
    spark: "Storyboard a 15-second scene in four shots: [who], [where], [what happens]. One still per shot.",
    secondary: { label: "See the board", href: "#examples" },
  },
  template: "spark",
  tone: "light",
  accent: SLATE,
  layout: {
    hero: "fan",
    order: ["signature", "wall", "overview", "howTo", "features", "faq", "models", "related", "final"],
    features: "split",
  },
  heroMedia: [
    { title: "Shot 1", tag: "", src: `${DIR}/board-1.jpg`, aspect: "16:9" },
    { title: "Shot 2", tag: "", src: `${DIR}/board-2.jpg`, aspect: "16:9" },
    { title: "Shot 4", tag: "", src: `${DIR}/board-4.jpg`, aspect: "16:9" },
  ],
  signature: "shot-timeline",
  signatureFrames: [
    { title: "Wide", tag: "", src: `${DIR}/board-1.jpg`, aspect: "16:9" },
    { title: "Tracking", tag: "", src: `${DIR}/board-2.jpg`, aspect: "16:9" },
    { title: "Insert", tag: "", src: `${DIR}/board-3.jpg`, aspect: "16:9" },
  ],
  timeline: {
    eyebrow: "One line, three timed shots",
    heading: "Every shot gets its still before anything moves.",
    seconds: 10,
    shots: [
      {
        label: "Wide establishing",
        start: 0,
        end: 3,
        prompt: "Wide, night, heavy rain. A bike courier in a yellow raincoat waits at a red light, a delivery box on the rack.",
        sound: "rain on the road, a bus passing",
      },
      {
        label: "Tracking",
        start: 3,
        end: 7,
        prompt: "Tracking, handheld. He pedals hard between the cars, spray off both tires, tail lights smearing red.",
        sound: "his breathing, tires hissing on water",
      },
      {
        label: "Insert",
        start: 7,
        end: 10,
        prompt: "Insert, close. A gloved hand turns a cracked phone to read the map, rain beading on the glass.",
        sound: "rain tapping the screen",
      },
    ],
  },
  overview: {
    items: [
      {
        eyebrow: "The shot list",
        title: "Timed shots, written from one line.",
        body: "Describe the scene and say how many shots you want, or leave the count to the idea. It comes back as timed windows: 0 to 3 seconds a wide, 3 to 7 a close, each one camera setup and one action, with the cuts between them.",
        points: [
          "Ask for a number of shots and the scene is written to it.",
          "Any length from 4 to 30 seconds.",
        ],
      },
      {
        eyebrow: "The panels",
        title: "One still for every shot.",
        body: "Each shot's still is drawn from the photos on the scene, and from the shot before it, so the room, the light and the person carry across the cut. Draw the whole strip, or one shot's still on its own.",
        points: [
          "The price of the strip is shown before it is drawn.",
          "Change one shot's line and only that shot's still is drawn again.",
        ],
      },
      {
        eyebrow: "The board is the film",
        title: "Each panel is the first frame of its clip.",
        body: "A storyboard usually gets thrown away when the shoot starts. Here the still you approved is the frame the video model starts on, so what you signed off is what the clip opens with.",
      },
    ],
  },
  wall: {
    title: "The Whole Board",
    tiles: [
      { title: "Wide, night", tag: "Shot 1", meta: "A bike courier in a yellow raincoat waits at a red light in heavy rain.", src: `${DIR}/board-1.jpg`, aspect: "16:9" },
      { title: "Tracking", tag: "Shot 2", meta: "He pedals hard between cars, spray off the tires.", src: `${DIR}/board-2.jpg`, aspect: "16:9" },
      { title: "Insert", tag: "Shot 3", meta: "A gloved hand checks a cracked phone map.", src: `${DIR}/board-3.jpg`, aspect: "16:9" },
      { title: "Low angle", tag: "Shot 4", meta: "He skids to a stop in front of the apartment door.", src: `${DIR}/board-4.jpg`, aspect: "16:9" },
      { title: "Insert", tag: "Shot 5", meta: "The box changes hands in the lit doorway.", src: `${DIR}/board-5.jpg`, aspect: "16:9" },
      { title: "Wide, dawn", tag: "Shot 6", meta: "He rides off as the rain stops.", src: `${DIR}/board-6.jpg`, aspect: "16:9" },
    ],
    explore: { label: "Board a scene", href: "#how" },
    layout: "editorial",
  },
  features: {
    title: "What the Storyboard Holds",
    items: [
      {
        icon: "shots",
        title: "Shots with their timing",
        body: "Every panel has its window: when it starts, how long it runs, and what happens in it.",
      },
      {
        icon: "keyframe",
        title: "A still a shot",
        body: "The panel is a drawn frame, not a sketch of one: the framing, the light and the subject as the clip will open.",
      },
      {
        icon: "references",
        title: "Held to your photos",
        body: "The stills are drawn from the person, the product and the place you attached, so the board looks like your film.",
      },
      {
        icon: "frame",
        title: "Continuity across the cut",
        body: "Each still is drawn with the previous shot's still beside it, so one shot leads into the next.",
      },
      {
        icon: "edit",
        title: "Redraw one panel",
        body: "Change one shot's line in the scene and that still is drawn again. The other panels are kept.",
      },
      {
        icon: "price",
        title: "The strip's price, first",
        body: "Drawing stills costs credits, and the number for the strip, or for one panel, is on the button.",
      },
      {
        icon: "guide",
        title: "Talk the scene through",
        body: "The assistant will work out the beats with you before a single shot is written, and write the scene when you ask.",
      },
      {
        icon: "elements",
        title: "A project keeps the look",
        body: "File the scene in a project with a brief and a look, and every scene after it is written to the same rules.",
      },
      {
        icon: "model",
        title: "Then render it",
        body: "When the board is right, render the shots on the video model you pick. Or stop at the board.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("ltx2.3"), model("seedance2.5"), model("veo3.1")]),
  },
  howTo: {
    title: "How to make a storyboard",
    items: [
      {
        title: "Write the scene",
        body: "Sign in, write one line, attach the photos it must be held to, and say how many shots. The studio writes the timed shot list.",
      },
      {
        title: "Draw the stills",
        body: "On the scene's Render card, draw its keyframes: one still a shot. The price for the strip is on the button.",
      },
      {
        title: "Fix a panel, then decide",
        body: "Change a shot's line and draw its still again until the board reads right. Download the stills, or render the shots from them.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Storyboard Generator",
    items: [
      {
        q: "What is an AI storyboard generator?",
        a: "A tool that turns a written scene into a sequence of drawn frames, one per shot. This one writes the shot list with timings, draws a still for every shot from photos you attach, and can then render each shot as a clip starting on its still.",
      },
      {
        q: "How do I storyboard a scene with it?",
        a: "Write one line about the scene, attach at least one photo, and say how many shots you want. The studio writes the timed shots. On the scene's Render card you draw the stills, one a shot. Change the line of a shot that is wrong and its still is drawn again.",
      },
      {
        q: "Can I choose how many shots there are?",
        a: "Yes. Say the number, or write your own timed windows, and the scene is written to them. With no number, the scene gets as many shots as the idea needs, and one continuous take only if you ask for one.",
      },
      {
        q: "Does the same character appear in every panel?",
        a: "Every still is drawn from the references on the scene, and from the still of the shot before it. Save a person as an element with a few photos and the studio draws a reference sheet for them, which holds a face better than a single photo. Look at each panel: no exact match is promised.",
      },
      REFERENCES_FAQ,
      {
        q: "Can I export the storyboard as a PDF?",
        a: "No. The stills are in your Library and download one at a time, each with the prompt that drew it. There is no single storyboard file.",
      },
      {
        q: "Do I have to render video after the board?",
        a: "No. Drawing the stills and rendering the clips are separate, each with its own price and its own button. A scene can stay a board.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-movie-maker", "ai-video-generator", "consistent-character-video", "text-to-video", "ai-commercial-maker"],
  finalCta: {
    eyebrow: "Board it first",
    title: "See every shot before you render one.",
    body: "Write the scene, draw a still a shot, fix the panel that is wrong.",
  },
};
