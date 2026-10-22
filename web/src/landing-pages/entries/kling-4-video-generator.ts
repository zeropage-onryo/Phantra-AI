// The Kling 4.0 page (2026-10-22, Mike's ask the day Kling 4.0 went live in
// the studio, PR #445). Its own URL so "kling 4.0" has one page to rank:
// /models/kling-video-generator went back to the evergreen "Kling AI Video
// Generator" (the family) the same day and links here.
//
// SEARCH: the versioned queries of Mike's 2026-10-16 Kling 4 playbook --
// "kling 4.0", "kling 4.0 ai video generator", "try kling 4.0 online",
// "kling 4.0 vs kling 3.0", "30 second ai video". The
// title leads with "Try Kling 4.0 Online" and "30-Second" (50 characters,
// 60 with " — Phantra"), the H1 is "Kling 4.0 AI Video Generator", the
// comparison section is titled "Kling 4.0 vs Kling 3.0".
//
// LAYOUT: center hero (the spotlight, no media) + the new `spec-compare`
// signature (components/spec-compare.tsx) + no wall, features as a list,
// accent SIGNAL (the studio's own Kling 4.0 spotlight colours). No other
// page has this hero + signature + wall, and no other page is SIGNAL.
//
// MEDIA: none yet. generated_assets on the live database had no Kling 4.0
// row of any kind (read-only SELECT, 2026-10-22), and nothing is generated
// for a page unless Mike says so. The page ships in the template's no-media
// state: no wall, a text-only hero, and the comparison pair as two plates.
// SLOT(kling-4-vs-3): `signatureFrames` below are the two sides of Mike's
// upcoming Kling 4.0 vs 3.0 renders (one prompt on both models). To fill
// them: upload each MP4 to R2 at site/models/kling-4-video-generator/<name>.mp4,
// put the poster JPEG under public/models/kling-4-video-generator/, give
// each frame `video` + `src` (and its real `aspect`), drop the "on the way"
// meta, and add "wall" back to `layout.order` once there are wall clips.
//
// CHECKED 2026-10-22 against the code and the web:
// - src/fal.py SLOTS["kling4"] (enabled into VIDEO_MODELS when ready):
//   kling/v4/text-to-video + kling/v4/image-to-video, duration an INTEGER
//   3-30, resolution 720p or 1080p (720p the default, 1080p on the card),
//   aspect 16:9 / 9:16 / 1:1 / 21:9 on text-to-video only, multi_prompt
//   NOT sent, sound is the model's. fal.build_body renders image-to-video
//   whenever the shot has a keyframe, and a scene with no photos does not
//   render (preprod.reference_gate), so every studio clip starts from a
//   keyframe. fal's queue schemas for both ids read the same that day
//   (start_image_url, end_image_url, multi_prompt, duration 3-30, 720p /
//   1080p); fal's listing also has reference-to-video and
//   video-to-video/edit endpoints the studio does not wire.
// - Kling's launch (the-decoder.com, 2026-10-19): up to 30 s in one pass,
//   two-channel stereo, up to 10 keyframe images, Omni Reference up to 15
//   assets, "Creative Recreation" editing; 4K / HDR "coming soon".
// - NO COST ON THIS PAGE (2026-10-22, Mike: "never anything about costs...
//   ever"): no price, credits or cost in the copy, the meta, the FAQ, the
//   JSON-LD or the tables. `model()` is read for names only.
// - Comparison: Kling 3 Turbo Pro 3-15 s, 1080p only (fal.py); Seedance 2.5
//   4-30 s, 480p/720p/1080p, generate_audio defaults on (fal schema); Veo 3.1
//   4/6/8 s, 720p/1080p, with audio (fal.py). A Kling 3 Turbo Pro
//   render in the live bucket (generated_assets 135, 1080x1920) carries a
//   two-channel AAC track, so sound is NOT claimed as a 4.0-only difference.
// - Vesper's routing: src/model_menu.routing_line / slot_preference read
//   fal.SLOTS["kling4"]["routing"]: a single continuous shot of 15-30 s, or
//   a scene held to 3+ references. A proposal only opens the card; the
//   person picks the model and approves the render there.
// - The connector: every plan; a custom connector in Claude or ChatGPT at
//   https://api.phantra.ai/mcp (app/mcp page). The directory listings are
//   still pending, so the page never says "find it in the directory".
// - The CTA's spark is the studio's own "Try Kling 4.0" starter line
//   (app/studio/page.tsx, lib/create-v2.ts NEW_TILES kling4 `fill`).
import { COMMERCIAL_FAQ, MODELS_TITLE, PLAN_FOR, REFERENCES_FAQ, model, plainModelCards } from "../shared";
import { SIGNAL } from "../theme";
import type { MakePage, MakeTile } from "../pages";

const kling4 = model("kling4");
const kling3 = model("kling3-turbo-pro");
const seedance = model("seedance2.5");
const veo = model("veo3.1");

// the studio's own starter line for Kling 4.0 (lib/create-v2.ts, page.tsx)
const SPARK = "One continuous 20-second take on Kling 4.0: ";

// SLOT(kling-4-vs-3): Mike's comparison renders land here (see the top comment)
const slot = (title: string, plate: string): MakeTile => ({
  title,
  tag: "Same prompt",
  meta: "Comparison render on the way",
  aspect: "16:9",
  plate,
});

export const KLING_4: MakePage = {
  slug: "kling-4-video-generator",
  section: "models",
  modelIds: ["kling4"],
  title: "Try Kling 4.0 Online: 30-Second AI Video Generator",
  description:
    "Try Kling 4.0 online: AI video in single takes up to 30 seconds, 720p or 1080p, with stereo sound. See its specs and how Kling 4.0 compares with Kling 3.0.",
  h1: "Kling 4.0 AI Video Generator",
  menu: "Kling 4.0",
  subhead:
    "Kling 4.0 is in Phantra: one continuous take up to 30 seconds, 720p or 1080p, with stereo sound. Vesper plans the shots from your photos, you review the plan, and nothing renders until you approve.",
  cta: {
    label: "Try Kling 4.0 free",
    spark: SPARK,
    secondary: { label: "Kling 4.0 vs 3.0", href: "#compare" },
    startLabel: "Start a take",
  },
  template: "spark",
  tone: "light",
  accent: SIGNAL,
  layout: {
    hero: "center",
    order: ["signature", "features", "howTo", "models", "faq", "related", "final"],
    features: "list",
  },
  signature: "spec-compare",
  signatureFrames: [
    slot("Kling 4.0", "linear-gradient(135deg, #fefce8 0%, #fee32d 48%, #151514 100%)"),
    slot("Kling 3 Turbo Pro", "linear-gradient(135deg, #f5f5f4 0%, #a8a29e 50%, #151514 100%)"),
  ],
  specs: {
    sheet: {
      eyebrow: "Kling 4.0 in Phantra",
      title: "Kling 4.0 Specs",
      intro: "What Kling 4.0 does in the studio today, as the Render card offers it.",
      rows: [
        {
          label: "Made by",
          value: "Kling AI, Kuaishou's video model team. Kling launched 4.0 in October 2026.",
          note: "In Phantra since October 22, 2026, the day fal opened its Kling 4.0 API.",
        },
        {
          label: "Length per clip",
          value: "Any whole number of seconds from 3 to 30, so one continuous take can run the full 30 seconds.",
          note: "A scene runs 4 to 30 seconds in all, written as timed shots; each shot renders as its own clip.",
        },
        {
          label: "Resolution",
          value: "720p or 1080p, picked on the scene's Render card. 720p is the default.",
        },
        {
          label: "Frame",
          value: "The clip keeps the shape of the shot's first frame: vertical for the feed, or wide.",
          note: "Kling 4.0 also takes 1:1 and 21:9 when it works from text alone; Phantra renders every Kling 4.0 clip from a keyframe, so the still sets the frame.",
        },
        {
          label: "Sound",
          value: "Made with the picture, in two-channel stereo.",
          note: "The sound is the model's; there is no separate sound setting on the card.",
        },
        {
          label: "How a clip starts",
          value: "From the shot's keyframe: a still drawn from your reference photos, which Kling 4.0 animates.",
        },
        {
          label: "Plans",
          value: `On ${PLAN_FOR[kling4.tier]}.`,
        },
        {
          label: "Not in the studio yet",
          value: "Kling 4.0 can also take an end frame, its own per-shot prompts, up to 10 keyframes, reference images and videos (Omni Reference), and edit an existing video. Phantra does not offer these yet.",
        },
      ],
    },
    compare: {
      eyebrow: "Kling 4.0 vs 3.0, Seedance and Veo",
      title: "Kling 4.0 vs Kling 3.0",
      intro: "Kling 4.0 against the other video models in the studio, as each runs in Phantra today.",
      columns: [kling4.name, kling3.name, seedance.name, veo.name],
      rows: [
        { label: "Made by", values: ["Kling AI (Kuaishou)", "Kling AI (Kuaishou)", "ByteDance", "Google"] },
        {
          label: "Length per clip",
          values: ["3 to 30 seconds", "3 to 15 seconds", "4 to 30 seconds", "4, 6 or 8 seconds"],
        },
        { label: "Resolution", values: ["720p or 1080p", "1080p only", "480p, 720p or 1080p", "720p or 1080p"] },
        {
          label: "Sound",
          values: ["Stereo, with the picture", "With the picture", "With the picture", "With the picture"],
        },
        {
          label: "Plans",
          values: [kling4, kling3, seedance, veo].map((m) => PLAN_FOR[m.tier].replace(/^./, (c) => c.toUpperCase())),
        },
      ],
      notes: [
        "Lengths and resolutions are what each model takes in the studio (its row in our model table, checked against fal's schema).",
        "Kling 4.0's stereo is Kling's own launch claim. Kling 3 Turbo Pro clips also come back with a sound track, so sound alone is not the difference: length and the 720p option are.",
      ],
    },
    sources: [
      { href: "https://fal.ai/models/kling/v4/image-to-video/api", label: "fal: Kling 4.0 image-to-video (checked 2026-10-22)" },
      { href: "https://fal.ai/models/fal-ai/kling-video/v3/turbo/pro/image-to-video/api", label: "fal: Kling 3 Turbo Pro" },
      {
        href: "https://the-decoder.com/kling-ai-drops-version-4-0-with-stereo-audio-multilingual-lip-sync-and-a-lighter-flash-variant/",
        label: "The Decoder: Kling 4.0 launch",
      },
    ],
  },
  // the type wants a wall; this page draws none until it has clips (not in layout.order)
  wall: {
    title: "Kling 4.0 Takes",
    tiles: [],
    explore: { label: "See the specs", href: "#specs" },
  },
  features: {
    title: "Kling 4.0 in the Studio",
    items: [
      {
        icon: "clock",
        title: "One take, up to 30 seconds",
        body: "Any whole number of seconds from 3 to 30 a clip, so a 30-second AI video can be one continuous take instead of stitched shots.",
      },
      {
        icon: "frame",
        title: "720p or 1080p",
        body: "Pick the resolution on the scene's Render card. 720p is the default; 1080p is one pick away.",
      },
      {
        icon: "sound",
        title: "Stereo sound",
        body: "Kling 4.0 makes two-channel stereo sound with the picture. There is nothing to switch on.",
      },
      {
        icon: "guide",
        title: "Vesper plans the shots",
        body: "Tell Vesper, the studio's AI agent, what you're making. It plans the shots and writes the scene, and for a single 15 to 30 second take it suggests Kling 4.0. You pick the model on the card.",
      },
      {
        icon: "shots",
        title: "Review the plan, approve the render",
        body: "Vesper's plan and every shot are yours to read and change first. Nothing renders until you approve it.",
      },
      {
        icon: "references",
        title: "Your photos in every keyframe",
        body: "Each shot's first frame is drawn from the people, products and places you uploaded, and Kling 4.0 animates that frame.",
      },
      {
        icon: "keyframe",
        title: "See the first frame first",
        body: "Draw each shot's keyframe on the Render card and check the face before the clip renders.",
      },
      {
        icon: "open",
        title: "From Claude or ChatGPT",
        body: "The Phantra connector is on every plan. Add it to Claude or ChatGPT as a custom connector today and plan a Kling 4.0 scene in the chat. Nothing renders until you approve it.",
      },
      {
        icon: "export",
        title: "One MP4",
        body: "When the last shot lands, the clips are joined in order into one MP4, filed in your Library.",
      },
    ],
  },
  models: {
    title: MODELS_TITLE,
    items: plainModelCards(
      [
        { m: kling4, body: "Kling's newest: one continuous take up to 30 seconds, 720p or 1080p, stereo sound, strong on people." },
        { m: kling3, body: "Quick 3 to 15 second shots at 1080p. Cinematic motion, strong on people." },
        { m: seedance, body: "ByteDance's newest, with sound, up to 30 seconds a clip at 480p, 720p or 1080p." },
      ],
      (m) => `One continuous 20-second take on ${m.name}: `,
    ),
  },
  howTo: {
    title: "How Kling 4.0 Works in Phantra",
    items: [
      {
        title: "Tell Vesper the idea",
        body: "Sign up, describe the take and add your photos. Vesper plans the shots and writes the scene; for a single 15 to 30 second take it suggests Kling 4.0.",
      },
      {
        title: "Review the plan",
        body: "Read the shots Vesper wrote and change any of them. On the scene's Render card, choose Kling 4.0, 720p or 1080p, and the length.",
      },
      {
        title: "Approve to render",
        body: "Press approve and Kling 4.0 animates each shot's keyframe. Nothing renders before that click.",
      },
    ],
  },
  faq: {
    title: "Kling 4.0 FAQs",
    items: [
      {
        q: "What is Kling 4.0?",
        a: "Kling 4.0 is the newest video model from Kling AI, Kuaishou's video team, launched in October 2026. It renders single takes of up to 30 seconds with stereo sound. In Phantra it runs at 720p or 1080p, on every plan.",
      },
      {
        q: "Can I try Kling 4.0 online?",
        a: "Yes. Sign up at phantra.ai, describe the take and add your photos, choose Kling 4.0 on the scene's Render card and approve. It runs in the browser, with nothing to install.",
      },
      {
        q: "How long can a Kling 4.0 video be?",
        a: "Any whole number of seconds from 3 to 30 per clip, so a 30-second video can be one continuous take. A scene runs 4 to 30 seconds in all, written as timed shots.",
      },
      {
        q: "What is the difference between Kling 4.0 and Kling 3.0?",
        a: `In Phantra, Kling 4.0 renders 3 to 30 seconds a clip at 720p or 1080p, and Kling 3 Turbo Pro renders 3 to 15 seconds at 1080p only. Both make sound with the picture, and both are on every plan.`,
      },
      {
        q: "Does Kling 4.0 make sound?",
        a: "Yes. Kling 4.0 makes two-channel stereo sound with the picture. There is no separate sound setting.",
      },
      {
        q: "Can I use Kling 4.0 from Claude or ChatGPT?",
        a: "Yes. The Phantra connector is on every plan. Add it to Claude or ChatGPT as a custom connector with the address https://api.phantra.ai/mcp, sign in with your Phantra account, and plan a Kling 4.0 scene in the chat. Nothing renders until you approve it.",
        link: { href: "/mcp", label: "Set up the connector" },
      },
      {
        q: "What can Kling 4.0 do that Phantra does not offer yet?",
        a: "Kling 4.0 can also take an end frame, its own per-shot prompts, up to 10 keyframes, reference images and videos, and edit an existing video. Phantra does not offer these yet. Tell us which you want first at support@phantra.ai.",
      },
      REFERENCES_FAQ,
      COMMERCIAL_FAQ,
    ],
  },
  related: ["kling-video-generator", "seedance-video-generator", "veo-video-generator", "ai-video-generator"],
  finalCta: {
    eyebrow: "Kling 4.0",
    title: "One take, thirty seconds, your photos.",
    body: "Tell Vesper the idea, review the plan, approve the render.",
  },
};
