// /make/ai-movie-maker (2026-10-14; was /make/ai-short-film-maker from
// 2026-10-11, which now 308s here -- next.config.ts). Retargeted on the
// Semrush read that day: "ai movie maker" 1,900 a month (KD 66) against 40
// for "ai short film maker"; "short film" stays in the copy as the second
// phrase. More than one scene: a project holds the film's brief and look,
// each scene is 4 to 30 seconds of timed shots, and the editor joins them.
//
// Layout: hero "cover" + signature "length-dial" + wall "posters" (no other
// page has that combination), accent VIOLET (this page's since 2026-10-11).
//
// Media (2026-10-14, Mike asked for Higgsfield and Runway): the cover and the
// four posters are Nano Banana 2 stills drawn on Higgsfield (1K, 16:9 and
// 2:3, posters prompted "no text"); the length-dial clip is that cover still
// animated on Runway, Seedance 2.0 Fast, 720p, 8 s, with its own sound.
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
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage, MakeTile } from "../pages";

const DIR = "/make/ai-movie-maker";
const poster = (name: string, title: string, tag: string): MakeTile => ({ title, tag, src: `${DIR}/${name}.jpg`, aspect: "2:3" });

export const MOVIE_MAKER: MakePage = {
  slug: "ai-movie-maker",
  section: "make",
  title: "AI Movie Maker",
  description:
    "Make a movie or a short film with AI, scene by scene: one brief and one look for the whole film, each scene written as timed shots, cut together in the editor.",
  h1: "AI Movie Maker",
  menu: "AI Movie Maker",
  subhead: "Give the film a brief and a look once. Write it a scene at a time, render the shots, and cut the scenes into one movie.",
  cta: {
    label: "Start a film",
    spark: "The opening scene of a short film, 20 seconds in four shots: [who], [where], [what they want]. Start a project for it.",
    secondary: { label: "See the posters", href: "#examples" },
  },
  template: "spark",
  tone: "light",
  accent: VIOLET,
  layout: {
    hero: "cover",
    order: ["signature", "wall", "overview", "features", "howTo", "models", "faq", "related", "final"],
    features: "split",
  },
  heroMedia: [{ title: "A film's opening frame", tag: "", src: `${DIR}/lake.jpg`, aspect: "16:9", meta: "Nano Banana 2 · 16:9" }],
  signature: "length-dial",
  signatureFrames: [
    {
      title: "The frozen lake, 8 s",
      tag: "",
      video: `${DIR}/lake.mp4`,
      src: `${DIR}/lake-poster.jpg`,
      aspect: "16:9",
      meta: "2|the figure standing at the edge of the ice;5|the wind lifting snow across the lake;8|the whole beat: the stillness, the wind and the turn toward the tent",
    },
  ],
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
  wall: {
    title: "One Look a Film",
    tiles: [
      poster("lighthouse", "The Keeper", "Storm drama"),
      poster("greenhouse", "Glasshouse", "Fantasy"),
      poster("planet", "Ring Light", "Science fiction"),
      poster("detective", "Fog Street", "Noir"),
    ],
    explore: { label: "Start a film", href: "#how" },
    layout: "posters",
  },
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
    title: "How to make a movie with AI",
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
    title: "FAQs about the AI Movie Maker",
    items: [
      {
        q: "Can AI make a whole movie or short film?",
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
  related: ["ai-storyboard-generator", "consistent-character-video", "ai-music-video-generator", "text-to-video"],
  finalCta: {
    eyebrow: "Scene one",
    title: "Start with the brief. Write the first scene.",
    body: "A project for the film, elements for the cast, and a timeline for the cut.",
  },
};
