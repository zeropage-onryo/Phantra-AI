// /make/ai-tiktok-video-generator (2026-10-11). What it says about TikTok is
// one fact: a TikTok is a vertical video. It does not post, it does not
// follow trends, and it has no TikTok sounds: the page says so.
//
// This page's angle among the three social pages is SPEED: a cheap draft,
// several takes, template effects on a still. (Reels' is the look; Shorts'
// is length.)
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - 9:16 is the default frame: render_specs.FRAME_SIZES
// - a 480p draft where it is cheaper (Wan 3.0, Seedance 2.5), finished by
//   upscaling that same clip: src/drafts.py
// - the cheapest clip in the catalog is read off pricing.json at build time
// - effects that run on a still: Kling (98 templates), PixVerse (154),
//   twenty camera moves, each 5 seconds (Kling 5 or 10): src/effects.py
// - finishing a clip: upscale, add sound, re-frame, remove background
// - captions and one exported MP4: src/cut
import { MODELS, num } from "@/lib/catalog";
import { CYAN } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

// The catalog's least expensive row (a model at its listed length and
// frame), read at build time so the sentence changes when the prices do.
// It is not the floor: a shorter clip or a 480p draft can cost less.
const cheapest = [...MODELS].sort((a, b) => a.credits - b.credits)[0];

export const TIKTOK: MakePage = {
  slug: "ai-tiktok-video-generator",
  section: "make",
  title: "AI TikTok Video Generator",
  description:
    "Make vertical videos for TikTok fast: draft a scene cheaply, try a second take, run an effect on a still, and export one captioned MP4.",
  h1: "AI TikTok Video Generator",
  menu: "AI TikTok Video Generator",
  subhead: "Draft it cheap, try it twice, keep the take that works. Vertical clips from your own photos, with the price on every button.",
  cta: {
    label: "Make a TikTok",
    spark: "A 6-second vertical video, two shots: [the subject] does [one surprising thing]. Fast cut.",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: CYAN,
  layout: { order: ["overview", "howTo", "features", "models", "faq", "related", "final"], features: "list" },
  overview: {
    items: [
      {
        eyebrow: "Cheap first",
        title: "A draft before the real thing.",
        body: `Most ideas for a feed do not survive the first look. Render the scene on a fast model, or as a 480p draft on Wan 3.0 or Seedance 2.5, and spend on the full version only for the take you would post. The least expensive model in the catalog is ${cheapest.name}: ${num(cheapest.credits)} credits for a ${cheapest.seconds}-second ${cheapest.frame} clip.`,
        points: ["Finishing a draft upscales the take you liked. It is not a second roll of the dice."],
      },
      {
        eyebrow: "One still, many clips",
        title: "Run an effect on a picture, with no scene to write.",
        body: "Any still can be animated directly: a template effect, or one of twenty camera moves. Pick it from the gallery, read its price on the card, and a five-second clip comes back.",
        points: ["The templates are the effect makers' own lists. They are not TikTok's trends, and no TikTok sound comes with them."],
      },
      {
        eyebrow: "Out the door",
        title: "Vertical, captioned, one file.",
        body: "A scene is vertical unless you choose otherwise. Join the shots, add captions and audio you upload, and export one MP4. You post it yourself.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "Built for Trying Things",
    items: [
      {
        icon: "clock",
        title: "Drafts at 480p",
        body: "On Wan 3.0 and Seedance 2.5 a draft costs less than the final, and its price is on the button.",
      },
      {
        icon: "price",
        title: "The price on every button",
        body: "A take, a second take, an effect: each shows its credits before it runs, so trying something is a decision you can see.",
      },
      {
        icon: "open",
        title: "Camera moves on a still",
        body: "A zoom in, a whip pan, a crane up: twenty moves that turn one picture into a five-second clip.",
      },
      {
        icon: "edit",
        title: "Template effects",
        body: "Hundreds of ready-made effects that run on a picture of a person or a product, picked from a gallery by name.",
      },
      {
        icon: "references",
        title: "Your face, your product",
        body: "Scenes are held to photos you attach, so the video is of your thing and not a stock stand-in.",
      },
      {
        icon: "shots",
        title: "Fast cuts",
        body: "Ask for two shots in six seconds. The scene is written with the cut in it and each shot renders as its own clip.",
      },
      {
        icon: "sound",
        title: "Sound, or add it",
        body: "Three models render sound with the picture. Any other clip can be given sound as an effect.",
      },
      {
        icon: "type",
        title: "Captions",
        body: "Caption cues on the timeline, burned into the export in the style you pick.",
      },
      {
        icon: "export",
        title: "A file to post",
        body: "One vertical MP4. The studio does not post to TikTok or connect to your account.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("ltx2.3"), model("wan3"), model("kling3-turbo-pro")]),
  },
  howTo: {
    title: "How to make a TikTok video",
    items: [
      {
        title: "Write the hook",
        body: "Sign in, write one line with the surprising thing in it, attach a photo of the person or product, and set a short length.",
      },
      {
        title: "Draft and pick a take",
        body: "Render a draft on a fast model, look at it, and render again if it missed. Each try shows its price first.",
      },
      {
        title: "Finish and export",
        body: "Finish the take you kept, add captions and your audio in the editor, and export one vertical MP4.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI TikTok Video Generator",
    items: [
      {
        q: "What is an AI TikTok video generator?",
        a: "A tool that generates short vertical video for TikTok. This one writes your idea as timed shots, holds them to your own photos, renders each shot as a clip on the video model you pick, and exports one MP4. It can also animate a single still with an effect or a camera move.",
      },
      {
        q: "Does it post to TikTok?",
        a: "No. It exports an MP4 and you upload it. It does not post, schedule, or connect to your TikTok account.",
      },
      {
        q: "Does it use trending sounds or follow trends?",
        a: "No. It has no access to TikTok's sounds or trends. Sound comes from the video model, from an effect that adds sound to a clip, or from audio you upload. Add a TikTok sound in the TikTok app after you upload.",
      },
      {
        q: "What is the cheapest way to try an idea?",
        a: `Render it on the least expensive model, or as a 480p draft where one is offered. In the catalog that model is ${cheapest.name}, at ${num(cheapest.credits)} credits for a ${cheapest.seconds}-second ${cheapest.frame} clip, and every button shows its price before you press it.`,
        link: { href: "/models", label: "See what each model costs" },
      },
      {
        q: "Are the videos vertical?",
        a: "Yes, by default. A scene is written for 9:16 unless you pick another frame.",
      },
      {
        q: "Can I put myself or my product in the video?",
        a: "Yes. Attach your photos, or save yourself or the product as an element, and each shot's first frame is drawn from them. You need the consent of anyone else whose photo you upload.",
      },
      REFERENCES_FAQ,
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-instagram-reels-maker", "ai-youtube-shorts-maker", "image-to-video"],
  finalCta: {
    eyebrow: "Try the idea",
    title: "Draft it cheap. Keep the take that works.",
    body: "One line, one photo, a price on every try.",
  },
};
