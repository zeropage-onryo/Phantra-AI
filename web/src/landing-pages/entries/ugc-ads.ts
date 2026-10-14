// /make/ugc-ads (2026-10-14): new. Picked off the Semrush read that day:
// "ugc ads" 1,300 a month (KD 44, $9 a click), "ai ugc video generator" 590
// (KD 44), "ai ugc ads" 480 (KD 40). Runway and invideo both carry the page.
//
// Layout: hero "phone" + signature "sound-board" + wall "bento" (no other
// page has that combination); accent TEAL, new in theme.ts for this page.
//
// What the page does NOT claim: there is no avatar presenter, no lip-sync
// track and no voice cloning in the studio (src/effects.py has no lip sync;
// the Ferryman avatar page is docs/BACKLOG.md #28). A UGC ad here is a scene
// with a person talking to camera written into it, and the line is rendered
// with the picture by the models that render sound.
//
// Media (2026-10-14, Mike asked for Higgsfield and Runway): the three talking
// clips are Kling 3.0 on Higgsfield, std, 9:16, 5 s, sound on, the line in
// the prompt; the four product photos are Nano Banana 2 stills on Higgsfield
// (1K). The products are invented and carry no logos.
//
// Checked 2026-10-14 against the code:
// - a product saved as an element from its photos: app/api.py create_element;
//   a pasted product page gives the assistant its pictures and its stated
//   facts (name, colour, size): src/linkrefs.py, assistant_brain.link_facts
// - 9:16 frames and the scene length slider: src/timeline.py,
//   /api/scene-lengths
// - sound (a spoken line included) rendered with the picture on LTX 2.5,
//   Seedance 2.5 and Veo 3.1: the catalog
// - the priced Render card and the held credit: src/pricing.py, src/charge.py
// - captions, a music bed and a 9:16 export: src/cut
import { TEAL } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, model, modelCards } from "../shared";
import type { MakePage, MakeTile } from "../pages";

const DIR = "/make/ugc-ads";
const talk = (name: string, title: string, meta: string): MakeTile => ({
  title,
  tag: "",
  meta,
  video: `${DIR}/${name}.mp4`,
  src: `${DIR}/${name}.jpg`,
  aspect: "9:16",
});
const product = (name: string, title: string, aspect: string): MakeTile => ({
  title,
  tag: "Product photo",
  src: `${DIR}/${name}.jpg`,
  aspect,
});

const BOTTLE = talk("bottle", "“Keeps my water cold all day.”", "A gym selfie for a water bottle · Kling 3.0 · 5 s · sound");
const SERUM = talk("serum", "“Two drops at night.”", "A bathroom-mirror review for a serum · Kling 3.0 · 5 s · sound");
const COFFEE = talk("coffee", "“Better than the cafe.”", "A kitchen demo for a pour-over set · Kling 3.0 · 5 s · sound");

export const UGC_ADS: MakePage = {
  slug: "ugc-ads",
  section: "make",
  title: "AI UGC Ads Generator",
  description:
    "Make UGC-style video ads with AI: a person talks to camera about your product, in 9:16, with the line rendered in the same pass. Captions and export included.",
  h1: "UGC Ads, Made With AI",
  menu: "UGC Ads",
  subhead: "A person holds your product up to the camera and says one line about it. Vertical, natural light, the sound rendered with the picture.",
  cta: {
    label: "Make a UGC ad",
    spark:
      "A 10-second UGC ad, 9:16, phone-camera look: a [person] in a [place] holds up my [product] and says \"[one line]\". Natural light, two shots.",
    secondary: { label: "Hear the ads", href: "#sound" },
    startLabel: "Make one",
  },
  template: "spark",
  tone: "light",
  accent: TEAL,
  layout: {
    hero: "phone",
    order: ["signature", "wall", "features", "howTo", "models", "faq", "related", "final"],
    features: "grid",
  },
  heroMedia: [BOTTLE],
  signature: "sound-board",
  signatureFrames: [BOTTLE, SERUM, COFFEE],
  wall: {
    title: "From a Product Photo to an Ad",
    tiles: [
      product("bottle-photo", "Water bottle", "1:1"),
      SERUM,
      product("serum-photo", "Night serum", "3:4"),
      product("shoes-photo", "Running shoes", "1:1"),
      COFFEE,
      product("coffee-photo", "Pour-over set", "3:4"),
    ],
    explore: { label: "Make one", href: "#how" },
    layout: "bento",
  },
  features: {
    title: "What Goes Into a UGC Ad",
    items: [
      {
        icon: "elements",
        title: "Your product, saved once",
        body: "Add the product as an element from its photos. Every ad you write after that is held to it.",
      },
      {
        icon: "references",
        title: "The real thing in frame",
        body: "Each shot's first frame is drawn from your product photos, so the bottle in the ad is your bottle.",
      },
      {
        icon: "sound",
        title: "The line, spoken in the clip",
        body: "Write what the person says. LTX 2.5, Seedance 2.5 and Veo 3.1 render the voice and the room with the picture.",
      },
      {
        icon: "frame",
        title: "Made for 9:16",
        body: "Pick the vertical frame as you write. The ad is drawn and rendered upright, not cropped from a wide shot.",
      },
      {
        icon: "shots",
        title: "Hook, show, say",
        body: "A 10-second ad comes back as timed shots: the reach for the product, the close-up, the line to camera.",
      },
      {
        icon: "keyframe",
        title: "See the person first",
        body: "Every shot is a still before it is a clip. Redraw the one that looks wrong before you pay for motion.",
      },
      {
        icon: "guide",
        title: "Variations from one brief",
        body: "Ask the assistant for three takes on the same product: a gym, a kitchen, a commute. Each is its own scene.",
      },
      {
        icon: "edit",
        title: "Captions and a music bed",
        body: "Lay captions over the line, add a track you upload, and export one vertical MP4.",
      },
      {
        icon: "price",
        title: "Priced before it runs",
        body: "Every still and clip shows its price in credits on the button that starts it.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("veo3.1"), model("seedance2.5"), model("ltx2.5-fast")]),
  },
  howTo: {
    title: "How to make a UGC ad",
    items: [
      {
        title: "Add the product",
        body: "Sign in and save the product as an element from two or three photos. Or paste its product page into the chat.",
      },
      {
        title: "Write the person and the line",
        body: "Say who is holding it, where they are and the one line they say. Pick 9:16 and the length. The studio writes the shots.",
      },
      {
        title: "Render, caption, export",
        body: "Check the first frames, pick a model that renders sound, approve the price, then caption it in the editor and export.",
      },
    ],
  },
  faq: {
    title: "FAQs about AI UGC Ads",
    items: [
      {
        q: "What is a UGC ad?",
        a: "A short video ad made to look like a customer filmed it: a person holding the product to a phone camera, in a real room, saying one honest-sounding line. Here you write that scene and the studio renders it, so no creator has to be booked.",
      },
      {
        q: "How do I make a UGC ad with AI?",
        a: "Save your product as an element, then write one line: who is holding it, where, and what they say. The studio writes the scene as timed 9:16 shots, draws each first frame from your product photos, and renders the clips on the model you pick after you see the price.",
      },
      {
        q: "Does the person actually speak?",
        a: "Yes, on the models that render sound with the picture: LTX 2.5, Seedance 2.5 and Veo 3.1. Put the line in quotes in the scene. The studio has no separate voice track or lip-sync tool, so the line is part of the clip as it is rendered.",
      },
      {
        q: "Can I use my own product?",
        a: "Yes. Save it as an element from its photos and every shot's first frame is drawn from them. Paste its product page into the chat and the assistant offers the page's pictures and reads the name, colour and size the page states.",
      },
      {
        q: "Can I use a real creator's face?",
        a: "Only a face you have the right to use. The people in your ads are described in words or drawn from photos you upload, and the studio does not supply stock creators or avatars.",
      },
      {
        q: "What sizes can I export?",
        a: "The editor exports one MP4 at 9:16, 16:9 or 1:1, with captions and any music you uploaded mixed in.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-product-ad-generator", "ai-tiktok-video-generator", "ai-instagram-reels-maker", "consistent-character-video"],
  finalCta: {
    eyebrow: "Your first ad",
    title: "One product. One line. Ten seconds.",
    body: "Save the product, write who says what, see the price, render.",
  },
};
