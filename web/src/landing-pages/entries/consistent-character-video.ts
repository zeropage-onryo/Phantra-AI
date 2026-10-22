// /make/consistent-character-video (2026-10-11): the same person from shot
// to shot, which here means an element (photos + a drawn reference sheet)
// that every scene's first frames are drawn from.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - an element is photos plus a reference sheet drawn from them, five views
//   for a person; the sheet never replaces a real photo as the first
//   reference: src/element_sheet.py, prompts/element_sheet_character.txt
// - a still becomes an element ("Make element"): web/src/lib/continue.ts
// - an element is added from a chat too: the connector's add_element
// - each shot's still is drawn from the scene's references and the previous
//   shot's still: scene_chain._keyframe_timeline
// - references per image model: fal.IMAGE_MODELS / shared.ts IMAGE_MODELS
// - no match is promised anywhere in the product, and the page says so
import { LIME } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const CONSISTENT_CHARACTER: MakePage = {
  slug: "consistent-character-video",
  section: "make",
  title: "Consistent Character AI Video",
  description:
    "Keep the same character across shots and scenes: save a person as an element with photos and a reference sheet, and every first frame is drawn from them.",
  h1: "Consistent Character Video",
  menu: "Consistent Character Video",
  subhead: "Save a person once, with their photos and a reference sheet. Every scene after is held to the same face, shot by shot.",
  cta: {
    label: "Save a character",
    spark: "Make an element sheet of the person in the attached photos, then a 10-second scene with them: [where], [what they do].",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: LIME,
  layout: { order: ["overview", "features", "howTo", "faq", "models", "related", "final"], features: "list" },
  overview: {
    items: [
      {
        eyebrow: "Once",
        title: "A character is saved as an element.",
        body: "Give it a name and a few photos. The studio draws a reference sheet from them: the same person from the front, three-quarter, in profile, from behind and close up. The photos and the sheet are what every later scene is shown.",
        points: [
          "The person can be real, with their consent, or a still you drew and kept.",
          "The sheet is drawn from the photos you gave. It adds views; it does not replace them.",
        ],
      },
      {
        eyebrow: "Every scene",
        title: "The first frame of each shot is drawn from them.",
        body: "Name the element in a scene and its pictures are attached. Each shot's still is drawn from those pictures and from the still of the shot before, so the face, the clothes and the room carry across a cut. The clip then starts on that still.",
        points: ["Attach a second element for the place or the product, and say what each is for."],
      },
      {
        eyebrow: "Checked before it costs",
        title: "You see the face in a still before a clip is rendered.",
        body: "A drifted face shows up in the keyframe, and a still costs a fraction of a clip. Change the line of the shot that is off, draw its still again, then approve the render with the price on the card.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "How a Character Is Held",
    items: [
      {
        icon: "elements",
        title: "One element, many scenes",
        body: "The character is saved once and picked again in any scene, in any project, with an @ or from the list.",
      },
      {
        icon: "references",
        title: "Shown, not described",
        body: "The model is handed the person's pictures. A sentence about brown hair holds nothing; a photo does.",
      },
      {
        icon: "frame",
        title: "A sheet of views",
        body: "Front, three-quarter, profile, back and close-up on one sheet, drawn from the photos, so a turn of the head has something to go on.",
      },
      {
        icon: "keyframe",
        title: "Shot leads into shot",
        body: "Each still is drawn with the previous shot's still beside it, for the continuity a single photo cannot give.",
      },
      {
        icon: "edit",
        title: "A still can become a character",
        body: "Draw a person on an image model, keep the still you like, and make it an element. Invented people work the same way as real ones.",
      },
      {
        icon: "model",
        title: "Models that hold people",
        body: "Kling 3 Turbo Pro is the catalog's model for people in motion. The first frame a clip starts on is the same whichever model you pick.",
      },
      {
        icon: "shots",
        title: "Wardrobe and place too",
        body: "A product, an outfit or a room is an element like a person is, and a scene can be held to several at once.",
      },
      {
        icon: "price",
        title: "A cheap check",
        body: "Stills are priced before they are drawn and cost far less than a clip, which is where a wrong face should be caught.",
      },
      {
        icon: "guide",
        title: "From the chat as well",
        body: "The connector adds a picture as an element from Claude or ChatGPT and writes scenes held to it.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("kling3-turbo-pro"), model("seedance2.5"), model("wan3")]),
  },
  howTo: {
    title: "How to keep a character consistent",
    items: [
      {
        title: "Save the person as an element",
        body: "Sign in, open Elements, add a character with a name and a few clear photos. Leave the reference sheet on: it is drawn once the photos are saved, and is charged as one still.",
      },
      {
        title: "Write scenes with them in it",
        body: "In the box, pick the element and write what happens. Every shot's first frame is drawn from the element's pictures.",
      },
      {
        title: "Check the stills, then render",
        body: "Look at each shot's still. Change the line of a shot whose face is off and draw it again, then approve the render on the scene's card.",
      },
    ],
  },
  faq: {
    title: "FAQs about Consistent Characters",
    items: [
      {
        q: "How do I keep the same character in every shot?",
        a: "Save the person as an element with a few photos. The studio draws a reference sheet from them, and every scene that names the element draws each shot's first frame from those pictures and from the previous shot's still. The clip starts on that frame.",
      },
      {
        q: "Is the character identical in every clip?",
        a: "No tool can promise that, and this one does not. The first frame of each shot is drawn from the same pictures, which holds a face far better than a description. Once things move, video models vary, so check each still before you approve and render a second take when one drifts.",
      },
      {
        q: "What is a reference sheet?",
        a: "One image of the same person from five views: front, three-quarter, profile, back and close-up. It is drawn from the photos you uploaded and saved with the element. It gives the models angles your photos may not have.",
      },
      {
        q: "Can I use a character that is not a real person?",
        a: "Yes. Draw the character as a still on an image model, keep the one you like, and make it an element. From then on it is held the way a photographed person is.",
      },
      {
        q: "Can I use photos of a real person?",
        a: "Only with the consent of the person in them. You are responsible for the photos you upload, and the output is AI-made, so review it before you publish it.",
        link: { href: "/terms", label: "Read the terms" },
      },
      {
        q: "How many photos does a character need?",
        a: "One works. A few clear ones, from more than one angle and in even light, work better, because the reference sheet and every first frame are drawn from them.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["image-to-video", "photo-to-talking-video", "ai-storyboard-generator", "ai-movie-maker"],
  finalCta: {
    eyebrow: "The same face",
    title: "Save them once. Hold every shot to them.",
    body: "Photos in, a reference sheet out, and a still to check before each clip.",
  },
};
