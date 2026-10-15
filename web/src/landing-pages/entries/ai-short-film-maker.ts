// /make/ai-short-film-maker (2026-10-15, Mike said yes). Targets "ai short
// films" (110, KD 7), "ai short film generator" (90) and "ai short film
// maker", Semrush US, 2026-10-15. This slug 308ed to /make/ai-movie-maker
// from 2026-10-14; that redirect is removed in next.config.ts with this page.
//
// Angle, so it does not compete with /make/ai-movie-maker: a 1-3 minute
// short told in scenes, the length a person can finish. The movie page is
// about the project, the brief and the cast; this one is about how long a
// short is and how many scenes it takes.
//
// TODO(media): no still or clip picked (Mike picks from renders that exist).
//
// Checked 2026-10-15 against the code:
// - a scene is 4 to 30 seconds of timed shots: src/timeline.py. So 1 to 3
//   minutes is about 2 to 45 scenes; "six to twelve scenes" is a suggestion
//   of length, not a limit
// - a project's brief, look and memory: src/projects.py, src/project_context.py
// - elements with a reference sheet: src/element_sheet.py
// - the editor and exports (MP4, mix, still, OpenTimelineIO + SRT): src/cut
// - the studio writes no whole-film script in one pass and composes no music
import { TEAL } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const SHORT_FILM: MakePage = {
  slug: "ai-short-film-maker",
  section: "make",
  title: "AI Short Film Maker",
  description:
    "Make an AI short film of one to three minutes: a brief and a look kept for the whole film, each scene written as timed shots, the scenes cut together in the editor.",
  h1: "AI Short Film Maker",
  menu: "AI Short Film Maker",
  subhead: "A short is a handful of scenes. Write each one as timed shots, keep one cast and one look, and cut it down to a minute or three.",
  cta: {
    label: "Start a short",
    spark: "A two-minute short film in six scenes: [who], [where], [what goes wrong]. Start a project for it and write scene one.",
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: TEAL,
  layout: { order: ["overview", "features", "howTo", "models", "faq", "related", "final"], features: "split" },
  overview: {
    items: [
      {
        eyebrow: "The right size",
        title: "One to three minutes is about six scenes.",
        body: "A scene runs 4 to 30 seconds, so a two-minute short is a handful of scenes, each a few timed shots. Small enough to finish, long enough to tell a story with a turn in it.",
        points: ["The length is yours: a scene's price is shown before it renders, so the film's cost is the sum of the scenes you choose."],
      },
      {
        eyebrow: "One short, one look",
        title: "The project holds the film together.",
        body: "Say who the short is about and how it looks once. Every scene written in the project is held to it, and the characters are elements with their own photos.",
      },
      {
        eyebrow: "Finish it",
        title: "Cut, caption and export.",
        body: "Join the scenes in the editor, trim, set the transitions, add captions and a track you upload, and export one MP4. Or take the cut to another editor as an OpenTimelineIO project.",
        points: ["It does not write the whole script in one pass or compose the music."],
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Short Needs",
    items: [
      { icon: "guide", title: "A brief the scenes obey", body: "The project's brief and look apply to every scene written in it." },
      { icon: "elements", title: "A cast that stays", body: "Characters and places are elements with photos and a reference sheet." },
      { icon: "shots", title: "Coverage, written in", body: "A scene comes back as timed shots: the wide, the close, the detail." },
      { icon: "keyframe", title: "Stills first", body: "See every shot's first frame before a clip is made." },
      { icon: "sound", title: "Sound with the picture", body: "LTX 2.5, Seedance 2.5 and Veo 3.1 render sound in the same pass." },
      { icon: "clock", title: "Drafts", body: "A 480p draft on Wan 3.0 or Seedance 2.5 before the final." },
      { icon: "edit", title: "A timeline", body: "Trim, split, speed, transitions, captions and a mixer." },
      { icon: "export", title: "Two ways out", body: "One MP4, or an OpenTimelineIO project." },
      { icon: "price", title: "Scene by scene, priced", body: "Writing is included in your plan; stills and clips show their price first." },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("veo3.1"), model("seedance2.5"), model("kling3-turbo-pro")]),
  },
  howTo: {
    title: "How to make an AI short film",
    items: [
      { title: "Outline six scenes", body: "Start a project, give it the brief and the look, and save your cast as elements." },
      { title: "Write and render each scene", body: "Write a scene, read its shots, draw the stills, and render on the model you pick with the price on the card." },
      { title: "Cut the short", body: "Join the scenes on the timeline, add captions and your track, and export one MP4." },
    ],
  },
  faq: {
    title: "FAQs about the AI Short Film Maker",
    items: [
      {
        q: "How long can an AI short film be?",
        a: "As long as you want to write and pay for. A scene is 4 to 30 seconds, and the editor joins any number of them. One to three minutes is about six scenes.",
      },
      {
        q: "Does it write the whole short for me?",
        a: "It writes each scene's shots from your line, and the assistant will work through the story with you. It does not write the full script in one pass.",
      },
      {
        q: "Does it make the music and dialogue?",
        a: "It does not compose music: upload your own track. Veo 3.1 can render a spoken line with the picture when a scene asks for one.",
      },
      {
        q: "How is this different from the movie maker?",
        a: "Same studio, different job. This page is about finishing a short; the movie maker is about running a longer film as a project.",
        link: { href: "/make/ai-movie-maker", label: "See the AI Movie Maker" },
      },
      REFERENCES_FAQ,
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-movie-maker", "ai-trailer-maker", "ai-storyboard-generator", "consistent-character-video"],
  finalCta: {
    eyebrow: "Scene one",
    title: "Start a short. Finish it this week.",
    body: "A project, a cast, and a timeline.",
  },
};
