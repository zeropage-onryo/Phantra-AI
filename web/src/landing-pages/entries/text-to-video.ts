// /make/text-to-video (2026-10-11). The honest version of the phrase: this
// studio does not render a clip from words alone. A scene with no picture on
// it is refused at the render (approve_render answers `no_reference`), so the
// page says what does happen: the words become a still first, you look at
// it, and the clip starts on that still.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and every overview slot is a
// plate.
//
// Checked 2026-10-11 against the code:
// - a still from words alone: fal.IMAGE_MODELS (FLUX 1.1 Pro and Ideogram
//   4.5 take no reference; the others draw without one too), ten frames
// - a still becomes a scene's reference: the thread's "Turn into a shot"
//   and "Use as reference" (web/src/lib/continue.ts)
// - a still is animated directly: "Animate" opens the effects that take an
//   image and give a clip (src/effects.py: Kling and PixVerse template
//   effects, PixVerse camera moves)
// - the scene, its timed shots and its priced Render card: as on
//   /make/ai-video-generator
import { EMERALD } from "../theme";
import { COMMERCIAL_FAQ, IMAGE_MODELS, MODELS_FAQ, MODELS_TITLE, NO_WALL, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const TEXT_TO_VIDEO: MakePage = {
  slug: "text-to-video",
  section: "make",
  title: "Text to Video AI",
  description:
    "Turn a written idea into video. The studio draws the first frame from your words, you look at it, and the shot renders from that frame on the model you pick.",
  h1: "Text to Video",
  menu: "Text to Video",
  subhead: "Write what happens. The studio draws the first frame from your words, then renders the shot from the frame you kept.",
  cta: {
    label: "Start from words",
    spark: "A still of [the opening moment], then a 6-second shot from it: [what moves, where the camera goes].",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: EMERALD,
  layout: { order: ["overview", "howTo", "features", "models", "faq", "related", "final"], features: "list" },
  overview: {
    items: [
      {
        eyebrow: "Words to a frame",
        title: "First the still. You see it before any clip exists.",
        body: `Describe the opening moment and pick an image model: ${IMAGE_MODELS.length} are in the picker, each with its credits beside it. The still comes back in the frame you chose, and you can draw it again or edit it until it is the picture you meant.`,
        points: [
          "A still costs a fraction of a clip, so the wrong guess is a cheap one.",
          "Ten frames, from 9:16 to 21:9.",
        ],
      },
      {
        eyebrow: "Frame to a shot",
        title: "Then the clip, starting on that frame.",
        body: "Turn the still into a shot and write what happens next. The studio writes the scene as timed shots held to your still, and each shot renders as its own clip on the video model you pick. The clip opens on the frame you approved.",
        points: [
          "The studio does not render a clip from words alone. A scene needs at least one picture on it.",
          "The still can also be animated directly, with a camera move or a template effect.",
        ],
      },
      {
        eyebrow: "The price first",
        title: "Two prices, each shown before it is spent.",
        body: "The still's price is beside the model that draws it. The clip's price is on the scene's Render card, for the model, length and frame you picked. Neither runs until you press its button.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "From a Sentence to a Shot",
    items: [
      {
        icon: "type",
        title: "Write it plainly",
        body: "One line is enough: who or what, where, and what happens. The studio writes the full scene prompt, the camera and the sound from it.",
      },
      {
        icon: "frame",
        title: "A first frame from your words",
        body: "The opening still is drawn from the description alone, on the image model and in the frame you choose.",
      },
      {
        icon: "edit",
        title: "Change one thing",
        body: "Edit the still with a sentence, or draw a variation, before it becomes the start of a clip.",
      },
      {
        icon: "shots",
        title: "Timed shots",
        body: "What happens next is written as timed windows, 4 to 30 seconds in all, each one shot with its own clip.",
      },
      {
        icon: "keyframe",
        title: "The clip opens on your still",
        body: "Image to video, from the frame you approved: the model continues a picture you have already seen.",
      },
      {
        icon: "model",
        title: "The model is your choice",
        body: "LTX, Wan, Kling, Seedance or Veo for the clip, picked on the Render card with its price.",
      },
      {
        icon: "guide",
        title: "Talk it through first",
        body: "Not sure what the scene is yet? The assistant works through the idea with you and writes the prompt when you ask it to.",
      },
      {
        icon: "sound",
        title: "Sound, written in",
        body: "Every scene prompt ends in its own sound: the footstep, the room. LTX 2.5, Seedance 2.5 and Veo 3.1 render it with the picture.",
      },
      {
        icon: "assets",
        title: "Kept in your Library",
        body: "The still and the clip both land in your Library with the prompt and the model that made them.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("ltx2.3"), model("wan3"), model("veo3.1")]),
  },
  howTo: {
    title: "How to go from text to video",
    items: [
      {
        title: "Describe the first moment",
        body: "Sign in, switch the box to Image, write the opening frame and send. Pick the image model in the picker; the still's price is beside it.",
      },
      {
        title: "Turn the still into a shot",
        body: "Under the still, choose Turn into a shot and write what happens. The studio writes the scene as timed shots held to that still.",
      },
      {
        title: "Approve the render",
        body: "Open the scene's Render card, pick the video model, the length and the frame, read the price and approve. The clip lands in your Library.",
      },
    ],
  },
  faq: {
    title: "FAQs about Text to Video",
    items: [
      {
        q: "What is text to video?",
        a: "Making a video clip from a written description. In this studio the words first become a still you can look at and change, and the clip is then rendered from that still, so you see the opening frame before paying for a clip.",
      },
      {
        q: "Can I get a clip from a prompt with no image at all?",
        a: "Not in one step. A scene with no picture on it cannot be rendered here. You draw a still from your words first, which takes one send, and the clip starts on that still. The still can come from the prompt alone: no photo of yours is needed for it.",
      },
      {
        q: "How do I write a good prompt?",
        a: "Say who or what is in the frame, where it is, and one action. Add the light and the camera if you care about them. The studio writes the full scene prompt from that line, and the assistant will work through it with you if you would rather talk first.",
      },
      {
        q: "Which image models draw the first frame?",
        a: `${IMAGE_MODELS.map((m) => m.label).join(", ")}. Each shows its credits per still in the picker.`,
        link: { href: "/models#image-models", label: "See the image models" },
      },
      MODELS_FAQ,
      {
        q: "How long is the clip?",
        a: "A scene runs 4 to 30 seconds, written as timed shots. Each shot renders as its own clip, fitted to a length the model you picked supports.",
      },
      {
        q: "Can I animate the still without writing a scene?",
        a: "Yes. Under the still, Animate opens the effects that take an image and give a clip: a camera move, or a template effect. Each shows its price on a card before it runs.",
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["image-to-video", "ai-video-generator", "ai-storyboard-generator"],
  finalCta: {
    eyebrow: "Start with a sentence",
    title: "Write it. See the frame. Then the shot.",
    body: "The still comes first, so you know what the clip starts on.",
  },
};
