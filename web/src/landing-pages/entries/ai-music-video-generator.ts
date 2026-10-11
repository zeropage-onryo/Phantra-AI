// /make/ai-music-video-generator (2026-10-11). The honest version: the
// studio makes the PICTURES for a song you already have. It generates no
// music (nothing in src/fal.py or src/effects.py does), and it does not
// find the beat for you. The page says both.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - audio is uploaded in the editor and sits on its own music track; the
//   clips' own sound is on another, with a fader each: src/cut (cut_media,
//   the A tracks' roles, set_track_mix)
// - markers on the timeline, placed by hand at the playhead: ops.set_marker
// - trim, split, speed (0.25x to 4x) and reverse: src/cut/ops.py
// - the export is loudness-normalised to -14 LUFS at 9:16, 16:9 or 1:1;
//   the mix alone can be exported: src/cut/render.py
// - performers and places as elements: src/element_sheet.py
// - there is no beat detection and no lip sync (src/effects.py left lip
//   sync out because its price could not be verified)
import { FUCHSIA } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const MUSIC_VIDEO: MakePage = {
  slug: "ai-music-video-generator",
  section: "make",
  title: "AI Music Video Generator",
  description:
    "Make the pictures for a song you already have: scenes written as timed shots, held to your artist's photos, cut to your track in the editor.",
  h1: "AI Music Video Generator",
  menu: "AI Music Video Generator",
  subhead: "Bring the song. The studio makes the pictures: scenes held to your artist's photos, cut to your track on a timeline.",
  cta: {
    label: "Start a music video",
    spark: "A 12-second scene for a music video, four shots: [the artist], [the place], [the mood of the song]. No dialogue.",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: FUCHSIA,
  layout: { order: ["overview", "howTo", "features", "models", "faq", "related", "final"] },
  overview: {
    items: [
      {
        eyebrow: "Your song",
        title: "The track is yours. The studio does not write music.",
        body: "Upload the song in the editor and it sits on its own track under the picture. Everything else on this page is about making the images that go over it.",
        points: [
          "The studio generates video and stills. It does not generate a song.",
          "The beat is found by ear: drop a marker on the timeline where a cut should land.",
        ],
      },
      {
        eyebrow: "The pictures",
        title: "Scenes written as shots, held to the artist.",
        body: "Save the artist as an element with a few photos and write the video a scene at a time: a performance, a street, a room. Each scene comes back as timed shots, each shot is a still first, and each renders as its own clip.",
        points: [
          "Short shots cut faster. Say how many you want in a scene.",
          "A project keeps one look across every scene of the video.",
        ],
      },
      {
        eyebrow: "The cut",
        title: "Trim to the marker, turn the clip's own sound down.",
        body: "On the timeline, trim each clip to the markers you placed, change its speed, reverse it, and set the transition. The clips' own sound has its own fader, so the song is what is heard.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "Pictures for Your Track",
    items: [
      {
        icon: "sound",
        title: "Your audio, on its own track",
        body: "The song is uploaded once and stays under the cut. The clips' sound sits on a separate track with its own fader.",
      },
      {
        icon: "elements",
        title: "The artist, held",
        body: "An element with the artist's photos and a reference sheet, attached to every scene they are in.",
      },
      {
        icon: "shots",
        title: "As many cuts as the song wants",
        body: "Ask for six shots in twelve seconds and the scene is written that way, each shot its own clip.",
      },
      {
        icon: "clock",
        title: "Speed and reverse",
        body: "Slow a clip to a quarter speed, run it four times faster, or play it backwards, on the timeline.",
      },
      {
        icon: "edit",
        title: "Markers where the cuts go",
        body: "Place a marker at the playhead on a hit, name it, and trim clips to it.",
      },
      {
        icon: "keyframe",
        title: "A still before each clip",
        body: "Check the look of every shot as a still. A wrong frame is caught before a clip is paid for.",
      },
      {
        icon: "frame",
        title: "Vertical, wide or square",
        body: "Export the same cut at 9:16, 16:9 or 1:1.",
      },
      {
        icon: "export",
        title: "One file, level set",
        body: "The export is one MP4 with its loudness normalised to a standard level.",
      },
      {
        icon: "price",
        title: "Every clip priced first",
        body: "A music video is many clips. Each one shows its credits before it renders, and a 480p draft is offered on Wan 3.0 and Seedance 2.5.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("kling3-turbo-pro"), model("wan3"), model("seedance2.5")]),
  },
  howTo: {
    title: "How to make a music video",
    items: [
      {
        title: "Save the artist and the look",
        body: "Sign in, add the artist as an element with a few photos, and start a project with the video's look written down.",
      },
      {
        title: "Write and render the scenes",
        body: "Write each scene in a line and say how many shots. Check the stills, then render the shots on the model you pick, with the price on the card.",
      },
      {
        title: "Cut it to the song",
        body: "Open the clips in the editor, upload the track, drop markers where the cuts should land, trim to them, and export one MP4.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Music Video Generator",
    items: [
      {
        q: "Does it make the music?",
        a: "No. The studio generates video and stills, not songs. You upload your own track in the editor, and the studio makes and cuts the pictures that go over it.",
      },
      {
        q: "Does it cut to the beat automatically?",
        a: "No. You place markers on the timeline where you want cuts to land, and trim the clips to them. The scenes are written as timed shots, so you can ask for shot lengths that suit the tempo.",
      },
      {
        q: "Can the artist sing in sync with the song?",
        a: "Not reliably, and the studio has no lip-sync tool. Plan the video around performance shots that do not show the words being sung, or around images that do not show the artist's mouth at all.",
      },
      {
        q: "Can the artist look like the real artist?",
        a: "Save the artist as an element with photos, with their consent, and every scene they are in draws its first frames from those photos. Check each still before you render: video models vary between takes, and no exact match is promised.",
      },
      REFERENCES_FAQ,
      {
        q: "How long can the video be?",
        a: "Each scene runs 4 to 30 seconds. A full video is many scenes, joined on the timeline over the song. Each clip is priced before it renders.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-short-film-maker", "consistent-character-video", "ai-instagram-reels-maker"],
  finalCta: {
    eyebrow: "Bring the song",
    title: "Your track. Pictures made for it.",
    body: "Save the artist, write the scenes, and cut them to the song.",
  },
};
