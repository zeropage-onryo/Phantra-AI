// /make/ai-commercial-maker (2026-10-11): broader than the product ad
// page. A commercial here is a brand's project: a brief and a look that
// every spot obeys, the product and the talent as elements, a plan with a
// price on each step, and one cut delivered in three shapes.
//
// TODO(media): no still or clip has been picked for this page (Mike picks
// from renders that exist), so it draws no wall and its overview is text
// only (overview-section.tsx draws no media slot while no block has media).
//
// Checked 2026-10-11 against the code:
// - a project's brief (who it is for, what it must always have and never
//   show) and look, handed to every scene in it: src/projects.py, src/looks.py
// - a pasted product page gives up its facts and its pictures, and nothing
//   the page does not state is used: src/linkrefs.py, assistant_brain.link_facts
// - the plan: two to eight steps, each priced, each waiting for a yes when
//   it spends, and never a clip without its own approval: src/make_plan.py
// - a 480p draft on Wan 3.0 and Seedance 2.5: src/drafts.py
// - re-frame as an effect; the export at 9:16, 16:9 or 1:1; captions:
//   src/effects.py, src/cut
// - the connector for Claude and ChatGPT: /mcp
// - nothing is posted or sent to an ad platform: the page says so
import { ORANGE } from "../theme";
import { COMMERCIAL_FAQ, MODELS_FAQ, MODELS_TITLE, NO_WALL, REFERENCES_FAQ, model, modelCards } from "../shared";
import type { MakePage } from "../pages";

export const COMMERCIAL: MakePage = {
  slug: "ai-commercial-maker",
  section: "make",
  title: "AI Commercial Generator and Commercial Maker",
  description:
    "An AI commercial generator for your brand: a project that holds the brief and the look, your product and talent as elements, a priced plan, and one cut in three shapes.",
  h1: "AI Commercial Generator",
  menu: "AI Commercial Maker",
  subhead: "Give it the brief once. Every spot after is written to it, held to your product, priced before it renders, and cut in three shapes.",
  cta: {
    label: "Make a commercial",
    spark: "A 15-second commercial for [brand]: [the product], [who it is for], [the one thing to remember]. Start a project and plan it.",
    // no wall yet, so no "See examples": the second button goes to the steps
    secondary: { label: "How it works", href: "#how" },
  },
  template: "spark",
  tone: "light",
  accent: ORANGE,
  layout: { order: ["overview", "features", "howTo", "models", "faq", "related", "final"] },
  overview: {
    items: [
      {
        eyebrow: "The brief, once",
        title: "A project holds what the brand always says and never shows.",
        body: "Start a project for the campaign and write the brief: who it is for, what must always be in frame, what must never be. Add the look. Every spot written in the project is written to both, so the fifth film matches the first.",
        points: [
          "Paste the product's page and the studio reads its name, colour, size and photos off it.",
          "It is handed what the page states and told to add nothing to it. Read the result all the same.",
        ],
      },
      {
        eyebrow: "The product and the talent",
        title: "Held to photographs, not to a description.",
        body: "Save the product and the person as elements with their photos. Each shot's first frame is drawn from them, and the clip starts on that frame. You look at the pack shot as a still before a clip is rendered.",
      },
      {
        eyebrow: "A plan with prices",
        title: "The steps, and what each costs, before any of it runs.",
        body: "Ask the assistant for the spot and it lays out a plan: the look as a still, the scene, its keyframes, the render. Each step that spends shows its credits and waits for your yes, and the plan is held against your balance before it starts.",
        points: ["A clip is never rendered without its own approval."],
      },
      {
        eyebrow: "Delivery",
        title: "One cut, three shapes.",
        body: "Cut the spot on the timeline with captions and a music bed you upload, then export it at 9:16, 16:9 and 1:1. A clip that needs a different framing can be re-framed as an effect.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Campaign Needs",
    items: [
      {
        icon: "guide",
        title: "A brief that is obeyed",
        body: "The project's must-haves and nevers ride into every scene written in it.",
      },
      {
        icon: "references",
        title: "The real product",
        body: "The pack, the label and the colour come from your photos, attached to every shot the product is in.",
      },
      {
        icon: "elements",
        title: "Talent and locations",
        body: "A person or a place is saved once with its photos and a reference sheet, and reused across the campaign.",
      },
      {
        icon: "price",
        title: "A quote before the work",
        body: "The plan shows what is still to spend beside what you have, before the first step runs.",
      },
      {
        icon: "clock",
        title: "Draft, then finish",
        body: "Render a 480p draft on Wan 3.0 or Seedance 2.5 to check the idea, and finish only the takes you approve.",
      },
      {
        icon: "model",
        title: "The model per spot",
        body: "LTX, Wan, Kling, Seedance or Veo, chosen for each render with its price on the card.",
      },
      {
        icon: "type",
        title: "Captions and supers",
        body: "Lay caption cues on the timeline in one of three styles, and they are burned into the export.",
      },
      {
        icon: "frame",
        title: "Every placement's shape",
        body: "The same cut exports vertical, wide and square.",
      },
      {
        icon: "open",
        title: "From Claude or ChatGPT",
        body: "The connector opens the project from a chat, writes scenes held to your elements, and prices them.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: modelCards([model("kling3-turbo-pro"), model("seedance2.5"), model("veo3.1")]),
  },
  howTo: {
    title: "How to make a commercial",
    items: [
      {
        title: "Write the brief and add the product",
        body: "Sign in, ask the assistant to start a project, and give it the brief and the look. Save the product and any talent as elements with their photos.",
      },
      {
        title: "Approve the plan, step by step",
        body: "Ask for the spot. Read the plan and its prices, check the look and the keyframes as stills, and approve the render on the model you pick.",
      },
      {
        title: "Cut and deliver",
        body: "Open the clips in the editor, add captions and your music bed, and export the cut in the shapes the placements need.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Commercial Maker",
    items: [
      {
        q: "What is an AI commercial maker?",
        a: "A studio for making a brand's video spots with AI models. This one keeps the campaign's brief and look in a project, holds every shot to photos of your product and talent, shows the price of each still and clip before it is made, and cuts the clips into one film.",
      },
      {
        q: "How is this different from the AI Ad Generator?",
        a: "The Ad Generator is one product ad from a few photos. This is the campaign around it: a project that carries the brief and the look across several spots, talent and locations as well as the product, a priced plan, and delivery in three shapes.",
        link: { href: "/make/ai-product-ad-generator", label: "See the Ad Generator" },
      },
      {
        q: "Will the product look like my product?",
        a: "Every shot's first frame is drawn from the product photos you attach, and the clip starts on that frame. Check the still, especially the label, before you approve. Video models vary once things move, and no exact match is promised.",
      },
      REFERENCES_FAQ,
      {
        q: "Does it write the script and the claims?",
        a: "It writes each scene's shots from your line and your brief, and the assistant will work through the idea with you. It uses the facts you give it or that your product page states. Check every claim in the film yourself: the output is AI-made.",
      },
      {
        q: "Does it publish the ad or send it to an ad platform?",
        a: "No. You export the file and upload it where it runs. Nothing is posted for you.",
      },
      MODELS_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["ai-product-ad-generator", "ugc-ads", "ai-instagram-reels-maker", "consistent-character-video"],
  finalCta: {
    eyebrow: "The first spot",
    title: "Write the brief once. Make every spot to it.",
    body: "A project, your product's photos, a plan with prices, and a cut in three shapes.",
  },
};
