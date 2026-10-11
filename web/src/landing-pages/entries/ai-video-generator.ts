// /make/ai-video-generator (2026-10-11): the head term, and the whole studio
// on one page: write, hold to photos, price, render, finish.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - timed shots, 4 to 30 seconds, one clip a shot, one take only when asked:
//   src/timeline.py; the length slider: /api/scene-lengths
// - no photo, no render: preprod.reference_gate at approve_render
// - elements and their reference sheets: src/element_sheet.py
// - what each attached photo is for: src/ref_roles.py
// - the priced Render card, held and released credit: src/pricing.py, src/charge.py
// - a 480p draft on Wan 3.0 and Seedance 2.5, finished by upscaling the same
//   clip: src/drafts.py
// - sound in the same pass on LTX 2.5, Seedance 2.5 and Veo 3.1: the catalog
// - the finishing effects: src/effects.py; the editor and its export at
//   9:16, 16:9 or 1:1: src/cut
// - the assistant's plan with a price per step: src/make_plan.py
import { BLUE } from "../theme";
import { MODELS } from "@/lib/catalog";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const VIDEO_GENERATOR: MakePage = {
  slug: "ai-video-generator",
  section: "make",
  title: "AI Video Generator",
  description:
    "Write a scene as timed shots, hold every shot to your own photos, see the price in credits, and render it on Kling, Seedance, LTX, Wan or Veo.",
  h1: "AI Video Generator",
  menu: "AI Video Generator",
  subhead: "Write the scene, hold every shot to your own photos, and render it on the model you pick, with the price shown first.",
  cta: {
    label: "Make a video",
    spark: "A 10-second scene in three shots: [who or what], [where], [what happens].",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: BLUE,
  layout: { order: ["overview", "features", "models", "howTo", "faq", "related", "final"] },
  overview: {
    items: [
      {
        eyebrow: "From one line",
        title: "A scene is written as timed shots.",
        body: "Type the idea, or talk it through with the assistant first. The studio writes it as timed windows, 0 to 3 seconds one shot, 3 to 7 the next, and each window renders as its own clip. Ask for one continuous take and it writes one.",
        points: [
          "As many shots as the idea needs. A count you ask for is kept.",
          "The length is a slider: any whole second from 4 to 30.",
        ],
      },
      {
        eyebrow: "Held to your photos",
        title: "Every shot starts on a frame drawn from them.",
        body: "Attach photos of the person, the product or the place, or save them once as elements. Each shot's first frame is drawn from those photos and the clip starts on that frame. A scene with no photo on it cannot be rendered.",
        points: [
          "An element gets a reference sheet, so a face or a product stays the same from shot to shot.",
          "Say what each photo is for: the subject, the light, the palette or the framing.",
        ],
      },
      {
        eyebrow: "The price first",
        title: "Nothing is spent until you have seen the number.",
        body: "The scene's Render card prices its keyframes and its clip in credits, for the exact model, length and frame you picked. That number is what is charged, and credit held for a render that fails is released.",
        points: ["On Wan 3.0 and Seedance 2.5, draft at 480p first and finish only the take you keep."],
      },
      {
        eyebrow: "Finish it here",
        title: "Cut it, caption it, export one MP4.",
        body: "Clips land in your Library. Upscale one, add sound, change its shape or remove its background, then open the editor: trim, split, speed, transitions, captions and a mixer, exported at 9:16, 16:9 or 1:1.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What the Video Generator Does",
    items: [
      {
        icon: "references",
        title: "Your photos in every shot",
        body: "The photos you attach ride into the prompt, the first frame and the clip, so the model is shown what to make and not only told.",
      },
      {
        icon: "elements",
        title: "People, products, places",
        body: "Save one once as an element with its photos and its reference sheet, and hold any later scene to it.",
      },
      {
        icon: "shots",
        title: "Cuts, written in",
        body: "A scene comes back as timed shots with the cuts between them. Each shot is one camera setup and one action.",
      },
      {
        icon: "keyframe",
        title: "A still before the clip",
        body: "Draw each shot's first frame and look at it. Change a shot's line and its still is drawn again. The clip starts on the frame you kept.",
      },
      {
        icon: "price",
        title: "Credits on the button",
        body: "Every still, clip and effect shows its price in credits before it runs, and a clip always waits for your approval.",
      },
      {
        icon: "model",
        title: `${MODELS.length} video models, one card`,
        body: "LTX, Wan, Kling, Seedance and Veo, chosen per render with the length and the frame beside them.",
      },
      {
        icon: "sound",
        title: "Sound with the picture",
        body: "LTX 2.5, Seedance 2.5 and Veo 3.1 render the sound in the same pass as the frame. Any clip can have sound added afterwards.",
      },
      {
        icon: "edit",
        title: "An editor at the end",
        body: "A timeline for the clips you kept: trims, transitions, captions, a music bed you upload, and one exported file.",
      },
      {
        icon: "guide",
        title: "An assistant that plans",
        body: "Ask for an ad or a short and it lays out the steps, each with its price, and waits for your yes before anything spends.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("ltx2.5-fast"), model("kling3-turbo-pro"), model("seedance2.5")]),
  },
  howTo: {
    title: "How to make a video",
    items: [
      {
        title: "Write the idea",
        body: "Sign in, type one line about the scene, attach the photos it must be held to, and set the length. The studio writes the scene as timed shots.",
      },
      {
        title: "Check the first frames",
        body: "Open the scene's Render card and draw its keyframes. Change the line of any shot that is wrong and draw its still again, until the frames are what you meant.",
      },
      {
        title: "Approve, then finish",
        body: "Pick the model, see the price, and approve. Clips render one shot at a time into your Library, and the editor joins them into one MP4.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Video Generator",
    items: [
      {
        q: "What is an AI video generator?",
        a: "A tool that makes video from a description. This one writes your idea as a scene of timed shots, draws each shot's first frame from photos you attach, and renders each shot as its own clip on the video model you pick. The clips join into one file in the editor.",
      },
      {
        q: "How do I make a video with it?",
        a: "Sign in, write one line about the scene and attach at least one photo of what must appear in it. The studio writes the shots. On the scene's Render card you draw the keyframes, pick a model, see the price in credits and approve. The clips land in your Library.",
      },
      REFERENCES_FAQ,
      {
        q: "Can it keep the same person or product from shot to shot?",
        a: "Save the person or product as an element with a few photos. The studio draws a reference sheet for it, and every scene held to that element draws its first frames from those pictures. Video models still vary between renders, so look at each keyframe before you approve. No exact match is promised.",
      },
      MODELS_FAQ,
      {
        q: "How long can a video be?",
        a: "One scene runs 4 to 30 seconds, written as timed shots, and each shot renders as its own clip. A longer piece is several scenes joined on the editor's timeline.",
      },
      {
        q: "Does the video have sound?",
        a: "LTX 2.5, Seedance 2.5 and Veo 3.1 render sound together with the picture. For a clip from another model you can add sound afterwards as an effect, and the editor takes a music bed you upload.",
      },
      {
        q: "Do I see the price before anything is made?",
        a: "Yes. Stills, clips and effects each show their price in credits on the button that starts them, and nothing runs until you press it.",
        link: { href: "/pricing", label: "See the plans" },
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["text-to-video", "image-to-video", "ai-storyboard-generator", "ai-product-ad-generator"],
  finalCta: {
    eyebrow: "Your first scene",
    title: "Write one line. See it as shots.",
    body: "Attach a photo, set the length, look at the first frames, then render.",
  },
};
