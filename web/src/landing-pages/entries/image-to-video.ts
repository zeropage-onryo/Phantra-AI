// /make/image-to-video (2026-10-11): a picture you already have becomes a
// clip. Two real routes, and the page names both: a scene held to the
// picture (rendered shot by shot on a video model), or an effect run on the
// picture itself (a camera move, a template).
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - every video model in the catalog takes an image (fal.VIDEO_MODELS `i2v`),
//   and a clip handed a keyframe takes its frame from the keyframe
//   (src/fal.py: aspect_ratio is sent on text-to-video only)
// - the keyframe is drawn from the scene's references, and the first
//   reference is the one a clip anchors on: src/scene_chain.py, src/ref_roles.py
// - what each photo is for: src/ref_roles.py (subject, product, place, light,
//   palette, framing, style)
// - the effects that take an image and give a clip, with their counts:
//   src/effects.py (Kling 98 templates, PixVerse 154, 20 camera moves)
// - the finishing effects on the clip: the same table
import { AMBER } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, model, modelCards } from "../shared";
import type { MakePage, MakeTile } from "../pages";

// Media (2026-10-14, Mike asked for Higgsfield and Runway): two photos drawn
// on Nano Banana 2 (Higgsfield, 1K), each animated on Runway, Seedance 2.0
// Fast, 720p, 5 s, with sound, starting on that photo. Layout: hero "split"
// + no signature + wall "filmstrip" (Nano Banana's split + filmstrip carries
// the reference-stack signature, so the two are not twins).
const DIR = "/make/image-to-video";
const ROWBOAT_CLIP: MakeTile = {
  title: "The clip",
  tag: "Seedance 2.0 Fast · 5 s · sound",
  video: `${DIR}/rowboat.mp4`,
  src: `${DIR}/rowboat-clip.jpg`,
  aspect: "16:9",
};

export const IMAGE_TO_VIDEO: MakePage = {
  slug: "image-to-video",
  section: "make",
  title: "Image to Video AI",
  description:
    "Turn a photo into a video clip. Hold a scene to your picture and render it shot by shot, or animate the picture itself with a camera move or an effect.",
  h1: "Image to Video",
  menu: "Image to Video",
  subhead: "Start from a picture you already have. Write what happens next, or pick a camera move, and it becomes a clip.",
  cta: {
    label: "Animate a picture",
    spark: "From the attached photo, a 6-second shot: [what moves], [where the camera goes].",
  },
  template: "spark",
  tone: "light",
  accent: AMBER,
  layout: { hero: "split", order: ["wall", "overview", "features", "howTo", "models", "faq", "related", "final"], features: "split" },
  heroMedia: [ROWBOAT_CLIP, { title: "The photo", tag: "", src: `${DIR}/rowboat.jpg`, aspect: "16:9" }],
  overview: {
    items: [
      {
        eyebrow: "A scene from your picture",
        title: "The clip opens on the picture you gave it.",
        body: "Attach the photo and write what happens. The studio writes the scene as timed shots, draws each shot's first frame from your picture, and every video model in the studio starts its clip on that frame. The clip keeps the frame's shape, so a vertical photo makes a vertical clip.",
        points: [
          "One photo is enough. Several can each do a job: the subject, the place, the light.",
          "The first photo you attach is the one the clip anchors on.",
        ],
      },
      {
        eyebrow: "Or move the picture itself",
        title: "A camera move or an effect, with no scene to write.",
        body: "Open the effects on any still: twenty camera moves, and template effects by the hundred. Pick one, see its price on the card, and approve. The result is a clip in your Library.",
      },
      {
        eyebrow: "Then finish the clip",
        title: "Upscale it, give it sound, change its shape.",
        body: "A clip can be upscaled, given sound, re-framed to another shape, or have its background removed. Each is an effect with its price shown first. The result is a new clip in your Library, and the one it came from stays.",
      },
    ],
  },
  wall: {
    title: "The Photo, Then the Clip",
    tiles: [
      { title: "The photo", tag: "A bakery at 7am", src: `${DIR}/baker.jpg`, aspect: "4:5" },
      { title: "The clip", tag: "The dough is pressed, the flour drifts", video: `${DIR}/baker.mp4`, src: `${DIR}/baker-clip.jpg`, aspect: "3:4" },
      { title: "The photo", tag: "A dock at sunrise", src: `${DIR}/rowboat.jpg`, aspect: "16:9" },
      { ...ROWBOAT_CLIP, tag: "The mist moves, the boat rocks" },
    ],
    explore: { label: "Animate a photo", href: "#how" },
    layout: "filmstrip",
  },
  features: {
    title: "What a Picture Becomes",
    items: [
      {
        icon: "references",
        title: "Your picture is the first frame",
        body: "The clip does not start from a description of your photo. It starts from a frame drawn from the photo itself.",
      },
      {
        icon: "frame",
        title: "The shape is the picture's",
        body: "Handed a still, the video model takes its frame from the still: portrait in, portrait out.",
      },
      {
        icon: "elements",
        title: "Use it again",
        body: "Save the picture as an element and every later scene can be held to the same person, product or place.",
      },
      {
        icon: "shots",
        title: "More than one shot",
        body: "A scene from one photo can still cut: a wide, a close, a detail, each its own clip held to the same picture.",
      },
      {
        icon: "keyframe",
        title: "Look before you render",
        body: "Each shot's first frame is a still you can redraw before a clip is paid for.",
      },
      {
        icon: "open",
        title: "Camera moves",
        body: "Twenty named moves that run on a still directly: a zoom in, a crane up, a whip pan, a dolly zoom.",
      },
      {
        icon: "model",
        title: "Every model takes an image",
        body: "LTX, Wan, Kling, Seedance and Veo all render from a starting frame. You pick which on the Render card.",
      },
      {
        icon: "price",
        title: "Priced on the card",
        body: "A scene's clip and an effect each show their credits before they run. Some effects are priced by the clip's length, measured first.",
      },
      {
        icon: "assets",
        title: "The photo, the still, the clip",
        body: "All three stay in your Library, so a second take starts from the same picture.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("wan3"), model("kling3-turbo-pro"), model("seedance2.5")]),
  },
  howTo: {
    title: "How to turn an image into video",
    items: [
      {
        title: "Attach the picture",
        body: "Sign in and drop the photo into the box, or pick one of your elements. Say what it is for if you attach more than one.",
      },
      {
        title: "Write what happens, or pick a move",
        body: "One line about the motion makes a scene of timed shots. Or open Animate on a still and choose a camera move or an effect.",
      },
      {
        title: "Read the price and approve",
        body: "The scene's Render card, or the effect's card, shows the credits. Approve it and the clip lands in your Library.",
      },
    ],
  },
  faq: {
    title: "FAQs about Image to Video",
    items: [
      {
        q: "What is image to video?",
        a: "Making a video clip that starts from a still picture. Here the picture can be a photo you upload, one of your elements, or a still drawn in the studio. The clip opens on a frame drawn from it and continues with the motion you described.",
      },
      {
        q: "How do I turn a photo into a video?",
        a: "Attach the photo, write one line about what moves, and send. The studio writes the scene, draws the first frame from your photo, and you approve the render on the scene's Render card. To skip the scene, open Animate on a still and pick a camera move or an effect.",
      },
      {
        q: "Does the clip keep my picture's shape?",
        a: "Yes. A clip rendered from a starting frame takes that frame's shape. To get another shape afterwards, the re-frame effect redraws a clip at a new aspect ratio.",
      },
      {
        q: "Can I use more than one photo?",
        a: "Yes, and you can say what each one is for: the subject, the product, the place, the light, the palette, the framing or the style. The first photo is the one the clip anchors on.",
      },
      {
        q: "Will the person or product look the same in the clip?",
        a: "The first frame is drawn from your photo, and the clip starts there. Video models still vary once things move, so look at the keyframe before you approve and render a second take if the first drifts. No exact match is promised, and you need the consent of anyone whose likeness you upload.",
      },
      MODELS_FAQ,
      {
        q: "How long can the clip be?",
        a: "A scene runs 4 to 30 seconds in timed shots, each shot fitted to a length its model supports. A camera move is 5 seconds, and a template effect 5 or 10, chosen on its card.",
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["text-to-video", "photo-to-talking-video", "consistent-character-video", "ai-video-generator", "ugc-ads", "ai-product-ad-generator"],
  finalCta: {
    eyebrow: "Start from a picture",
    title: "Give it a photo. Say what moves.",
    body: "The clip opens on your picture, and you see the first frame before you render.",
  },
};
