// /make/ai-short-film-maker (2026-10-11): more than one scene. A project
// holds the film's brief and look, each scene is 4 to 30 seconds of timed
// shots, and the editor joins the scenes into one cut.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - a project's brief, look and memory, handed to every scene written in
//   it: src/projects.py, src/project_context.py, src/looks.py
// - a scene is 4 to 30 seconds of timed shots: src/timeline.py
// - a cut opened from a render in the Library or a rendered scene on the
//   Renders page, more clips added from the editor's bin, and the
//   editor's tools (trim, split, speed and reverse, 58 transition styles,
//   keyframes, a four-control grade, captions, a mixer): src/cut
// - the exports: an MP4 at 9:16, 16:9 or 1:1, the mix alone, a still frame,
//   or an OpenTimelineIO project with captions as .srt: src/cut/otio.py
// - a 480p draft on Wan 3.0 and Seedance 2.5: src/drafts.py
// - sound in the same pass on LTX 2.5, Seedance 2.5 and Veo 3.1: the catalog
// - the studio writes no script for a whole film in one go: a film is
//   written scene by scene. The page does not claim otherwise.
import { VIOLET } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const SHORT_FILM: MakePage = {
  slug: "ai-short-film-maker",
  section: "make",
  title: "AI Short Film Maker",
  description:
    "Make a short film scene by scene: a project keeps the brief and the look, each scene is written as timed shots, and the editor cuts them into one film.",
  h1: "AI Short Film Maker",
  menu: "AI Short Film Maker",
  subhead: "A project holds the film's brief and its look. You write it a scene at a time, and cut the scenes together in the editor.",
  cta: {
    label: "Start a film",
    spark: "The opening scene of a short film, 20 seconds in four shots: [who], [where], [what they want]. Start a project for it.",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: VIOLET,
  layout: { order: ["overview", "features", "models", "howTo", "faq", "related", "final"], features: "split" },
  overview: {
    items: [
      {
        eyebrow: "The film's rules",
        title: "A project keeps the brief and the look.",
        body: "Start a project and say what the film is: who it is about, what it must always have, what it must never show, and how it looks. Every scene written in that project is written to those rules, so scene nine belongs to the same film as scene one.",
        points: [
          "The look is yours to set. The studio has no house style.",
          "The project remembers which scenes you rendered and which you changed.",
        ],
      },
      {
        eyebrow: "Scene by scene",
        title: "Each scene is 4 to 30 seconds of timed shots.",
        body: "Write the scene in a line, or work it out with the assistant. It comes back as timed shots with the cuts written in, each shot drawn as a still from your cast and locations before it is rendered as a clip.",
        points: [
          "Characters and places are saved once as elements and reused in every scene.",
          "Pick the frame as you write: six shapes, from a 21:9 widescreen to a 9:16 vertical.",
          "Draft a scene at 480p on Wan 3.0 or Seedance 2.5 before you commit to it.",
        ],
      },
      {
        eyebrow: "The cut",
        title: "An editor, not a download folder.",
        body: "Open a rendered scene in the editor and bring the other scenes' clips in from its bin. Trim and split, change a clip's speed, set a transition, grade a shot, lay captions and a score you upload, and balance the sound on a mixer.",
      },
      {
        eyebrow: "Out of the studio",
        title: "Export the film, or the project.",
        body: "Export one MP4 at 9:16, 16:9 or 1:1. Or export the cut as an OpenTimelineIO project with its captions, and finish it in the editor you already use.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Film Needs",
    items: [
      {
        icon: "guide",
        title: "A brief every scene obeys",
        body: "The project's brief and look ride into the writing of every scene in it, without being typed again.",
      },
      {
        icon: "elements",
        title: "A cast that stays the cast",
        body: "Each character is an element with photos and a reference sheet, picked again in any scene.",
      },
      {
        icon: "shots",
        title: "Coverage, written in",
        body: "A scene is cut into shots as it is written: the wide, the close, the detail, each with its own timing.",
      },
      {
        icon: "keyframe",
        title: "Stills before clips",
        body: "Every shot is a still first. The film can be read as a board before a second of it is rendered.",
      },
      {
        icon: "sound",
        title: "Sound from the scene",
        body: "Each scene prompt ends in its own sound, and LTX 2.5, Seedance 2.5 and Veo 3.1 render it with the picture.",
      },
      {
        icon: "clock",
        title: "Drafts",
        body: "A 480p draft of a scene costs less than its final. Finish only the takes that make the cut.",
      },
      {
        icon: "edit",
        title: "A real timeline",
        body: "Tracks for picture, sound and captions, with trims, speed, transitions, keyframes and a grade on each shot.",
      },
      {
        icon: "export",
        title: "Two ways out",
        body: "One finished MP4, or an OpenTimelineIO project that opens in another editor with the cut intact.",
      },
      {
        icon: "price",
        title: "Scene by scene, priced",
        body: "Writing a scene is included in your plan. Its stills and clips each show their price before they are made.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("seedance2.5"), model("veo3.1"), model("ltx2.5-fast")]),
  },
  howTo: {
    title: "How to make a short film",
    items: [
      {
        title: "Start a project",
        body: "Sign in and ask the assistant to start a project for the film. Give it the brief and the look, and save your cast and locations as elements.",
      },
      {
        title: "Write and render the scenes",
        body: "One scene at a time: write it, read its shots, draw the stills, then render on the model you pick with the price on the card.",
      },
      {
        title: "Cut it together",
        body: "Open a rendered scene in the editor, add the other scenes' clips from the bin, and edit on the timeline. Export the film as one MP4, or the cut as a project.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Short Film Maker",
    items: [
      {
        q: "Can AI make a whole short film?",
        a: "Scene by scene, yes. The studio does not turn one prompt into a finished film. You write each scene, it is cut into timed shots and rendered as clips, and you join the scenes in the editor. A project keeps the brief and the look the same across all of them.",
      },
      {
        q: "How long can the film be?",
        a: "Each scene runs 4 to 30 seconds. A film is as many scenes as you write, joined on the editor's timeline. Every clip is priced before it is rendered, so the length is a matter of what you choose to render.",
      },
      {
        q: "How do the scenes keep the same look?",
        a: "The project carries a look you write once, and every scene written in the project is held to it. Characters and places are elements with their own photos, so the same pictures are attached wherever they appear.",
      },
      REFERENCES_FAQ,
      {
        q: "Does it write the script?",
        a: "It writes each scene's shots from your line, and the assistant will work through story, structure and pacing with you. It does not write a screenplay for the whole film in one pass.",
      },
      {
        q: "Can I edit the film somewhere else?",
        a: "Yes. The editor exports the cut as an OpenTimelineIO project, with the clips, the cuts, the transitions and the captions as a subtitle file. Or download the clips from your Library and cut them in the editor you use.",
      },
      {
        q: "Can I add music and dialogue?",
        a: "Upload a score and lay it on the timeline under the clips' own sound. Veo 3.1 renders a spoken line with the picture when the scene asks for one. The studio does not compose music.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-storyboard-generator", "consistent-character-video", "ai-music-video-generator"],
  finalCta: {
    eyebrow: "Scene one",
    title: "Start with the brief. Write the first scene.",
    body: "A project for the film, elements for the cast, and a timeline for the cut.",
  },
};
