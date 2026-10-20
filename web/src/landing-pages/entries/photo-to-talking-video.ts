// /make/photo-to-talking-video (2026-10-20): a photo of a person plus a
// voice -> a clip of them saying it, on OmniHuman v2. The plan Mike approved
// that day (docs/tasks/task-talking-photo.md) picked the phrase "photo to
// talking video" without a Semrush read (the subscription had lapsed);
// refine it off Search Console once the page has impressions. Competitors
// sell the same job on a feature page (HeyGen, invideo, Creatify, CapCut),
// so this is a /make page, not a /models page; an `omnihuman` model page
// linking here is the follow-up.
//
// Layout: center hero / no signature / no wall (NO_WALL until renders
// exist), features "grid", and the page's own "pricing" table -- the only
// /make page with one. Accent SKY, new.
//
// TODO(media): no example renders yet. The first real render (one 10s clip)
// waits on Mike's OK; until then the page draws no wall and the overview is
// text only.
//
// Checked 2026-10-20 against the code:
// - the clip: OmniHuman v2 (bytedance/omnihuman/v2) on a photo + a voice,
//   priced per second of the voice rounded up: src/talking_photo.py TALK,
//   billed_seconds, talk_usd; the credits below are pricing.json's
//   actions.talking_photo (src/pricing.py talking_photo_catalog)
// - the voice: an upload (.mp3 / .wav) or a typed script read by
//   ElevenLabs v3, quoted and approved on its own, filed as audio you can
//   hear before the clip: talking_photo.VOICE, mcp_server.run_voice_preview
// - 21 named voices, delivery tags like [laughs], an optional language
//   code: talking_photo.VOICES, check_language; the 5000-character limit
// - the voice must be 4s or more and within the plan's cap (30/60/120s):
//   talking_photo.check_audio, PLAN_AUDIO_CAP
// - the photo: 300-6000 px a side, width/height 0.4-2.5: check_image
// - consent is a required yes before any quote: run_talking_photo
// - the clip lands on the Assets wall and takes the usual effects and the
//   editor: effects.run (the wall row), src/effects.py, src/cut/
// - the scene/reference gate does NOT apply: a talking photo is one photo,
//   not a scene, so this page never says a scene needs references
import { CATALOG, num, PLANS } from "@/lib/catalog";
import { SKY } from "../theme";
import { COMMERCIAL_FAQ, NO_WALL } from "../shared";
import type { MakePage } from "../pages";

const TP = CATALOG.actions.talking_photo;
const CAPS = PLANS.map((p) => `${TP.max_seconds[p.key]} seconds on ${p.name}`).join(", ");

export const TALKING_PHOTO: MakePage = {
  slug: "photo-to-talking-video",
  section: "make",
  title: "Photo to Talking Video: Make a Photo Talk with AI",
  description:
    "Turn a photo into a talking video: upload a portrait, type a script or add a voice, and the person speaks it with matching lips, face and gestures.",
  h1: "Photo to Talking Video",
  menu: "Talking Photo",
  subhead:
    "One photo of a person and a voice. Type what they say or upload a recording, and the photo speaks it: lips, face and body moving with the sound.",
  cta: {
    label: "Make a photo talk",
    spark: "Make the person in the attached photo say: [your script]",
    secondary: { label: "See the prices", href: "#pricing" },
  },
  template: "spark",
  tone: "light",
  accent: SKY,
  layout: {
    order: ["overview", "features", "howTo", "pricing", "models", "faq", "related", "final"],
    features: "grid",
  },
  overview: {
    items: [
      {
        eyebrow: "The voice",
        title: "Type it, or upload it.",
        body: "Upload an .mp3 or .wav of the words, or type a script and pick one of 21 voices. A typed script is read aloud first, as its own small step, so you hear the voice and know the clip's exact length before anything else is made.",
        points: [
          "Delivery tags like [laughs] or [whispers] go in the script.",
          `A voice preview starts at ${num(TP.voice_preview_from)} credits.`,
        ],
      },
      {
        eyebrow: "The photo",
        title: "The photo speaks.",
        body: "OmniHuman v2 animates the person to the sound: the lips follow the words, and the face, head and hands move with how they are said. It sings as well as it speaks. A line of direction can set the scene, the movement and the camera.",
        points: [
          "A clear photo of one person, from the chest up or wider, works best.",
          `The clip is as long as the voice: ${TP.min_seconds} seconds and up, to ${CAPS}.`,
        ],
      },
      {
        eyebrow: "After",
        title: "Then finish the clip.",
        body: "The clip lands in your Library like any render. Upscale it, give it a new shape for another platform, cut it into a longer video in the editor, or export it as an MP4.",
      },
    ],
  },
  wall: NO_WALL,
  features: {
    title: "What a Talking Photo Does",
    items: [
      {
        icon: "type",
        title: "Script to speech",
        body: "Type the words and pick a voice. The script is read aloud before the clip, so a wrong word costs a preview, not a video.",
      },
      {
        icon: "sound",
        title: "Your own recording",
        body: "Upload a voiceover, a podcast clip or a song as an .mp3 or .wav, and the photo is animated to it.",
      },
      {
        icon: "frame",
        title: "Lips that match",
        body: "The mouth is driven by the sound itself, so the words land on the lips at the right moment.",
      },
      {
        icon: "shots",
        title: "More than a mouth",
        body: "Head turns, expressions and hand gestures follow the voice, so the person reads as speaking, not a moving cut-out.",
      },
      {
        icon: "guide",
        title: "Direct the shot",
        body: "An optional line sets the scene, the movement and the camera: a slow push in, a nod at the end, a laugh.",
      },
      {
        icon: "clock",
        title: "As long as the voice",
        body: `From ${TP.min_seconds} seconds up to ${TP.max_seconds.studio} on the Studio plan. The clip runs exactly the length of the audio.`,
      },
      {
        icon: "price",
        title: "Priced before it runs",
        body: "The voice is measured first, and the card shows the credits for that length. Nothing is spent until you approve it.",
      },
      {
        icon: "elements",
        title: "Your own photos",
        body: "Use a photo you upload, a still you made in the studio, or one of your saved elements.",
      },
      {
        icon: "edit",
        title: "Keeps going after",
        body: "Upscale the clip, reframe it to 9:16 or 16:9, or cut it with other clips in the editor.",
      },
    ],
  },
  pricing: {
    title: "Talking Photo Pricing",
    intro:
      "A talking photo is priced by the length of its voice, per second, rounded up to the whole second. The card shows the exact credits for your voice before anything renders.",
    rows: TP.clips.map((c) => ({ label: `${c.seconds}-second clip`, credits: c.credits })),
    notes: [
      `The longest voice per clip is ${CAPS}.`,
      `A typed script's voice preview is priced by its length, from ${num(TP.voice_preview_from)} credits. An uploaded recording costs nothing extra.`,
      `The plans grant ${PLANS.map((p) => `${num(p.credits)} credits a month on ${p.name}`).join(", ")}. A new workspace starts with ${num(CATALOG.trial.credits)} free credits.`,
    ],
    link: { href: "/pricing", label: "See the plans" },
  },
  models: {
    title: "The Models Behind It",
    items: [
      {
        title: "OmniHuman v2",
        body: "ByteDance's model for a person in a photo speaking or singing to a voice track. It draws the clip.",
      },
      {
        title: "ElevenLabs v3",
        body: "Reads a typed script aloud in the voice you pick, with delivery tags for laughs, whispers and pauses.",
      },
      {
        title: "Any video model, after",
        body: "The clip is a render like any other: finish it with an upscale or a reframe, or cut it beside clips from Kling, Veo or Seedance.",
        link: { href: "/models", label: "See every model" },
      },
    ],
  },
  howTo: {
    title: "How to make a photo talk",
    items: [
      {
        title: "Pick the photo",
        body: "Sign in and choose a photo of one person: an upload, a still you made, or an element. Confirm it is you, or that the person agreed.",
      },
      {
        title: "Add the voice",
        body: "Upload an .mp3 or .wav, or type the script, pick a voice and listen to the preview.",
      },
      {
        title: "Approve and render",
        body: "The card shows the credits for the voice's length. Approve it, and the clip lands in your Library.",
      },
    ],
  },
  faq: {
    title: "FAQs about Talking Photos",
    items: [
      {
        q: "What is a photo to talking video?",
        a: "A short clip made from one still photo of a person and a voice. The person in the photo appears to say the words: their lips, face and head move with the sound.",
      },
      {
        q: "How do I make a photo talk?",
        a: "Pick a photo of one person, then add the voice: upload a recording, or type a script and choose a voice. You see the price for that length, approve it, and the clip is rendered on OmniHuman v2.",
      },
      {
        q: "Can I type the words instead of recording them?",
        a: "Yes. Type a script of at least a sentence or two, pick one of 21 voices and the studio reads it aloud with ElevenLabs v3. You hear that preview before the clip is made, and it is priced on its own.",
      },
      {
        q: "Which languages and voices can it speak?",
        a: "An uploaded recording can be in any language. A typed script is read by ElevenLabs v3, which speaks many languages; you can name the language with a two-letter code. There are 21 voices to choose from. Voice cloning is not offered.",
      },
      {
        q: "Can I use a photo of someone else?",
        a: "Only with their consent. Before a talking photo is priced you confirm that the face is yours or that the person agreed. You are responsible for the photos you upload, and the output is AI-made, so review it before you publish it.",
        link: { href: "/terms", label: "Read the terms" },
      },
      {
        q: "Which AI model does it use?",
        a: "OmniHuman v2, ByteDance's model for animating a person in a photo to a voice. Typed scripts are voiced by ElevenLabs v3.",
      },
      {
        q: "How long can a talking video be?",
        a: `At least ${TP.min_seconds} seconds, and up to ${CAPS}. The clip is exactly as long as the voice.`,
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["image-to-video", "consistent-character-video", "ugc-ads", "ai-product-ad-generator"],
  finalCta: {
    eyebrow: "One photo, one voice",
    title: "Make a photo talk.",
    body: "Type the words or upload them, hear the voice, then approve the clip at the price on the card.",
  },
};
