// /models/omnihuman-video-generator (2026-10-21): OmniHuman v2's own model
// page, the "week 2" page of docs/tasks/task-talking-photo.md. Competitors
// keep a model page for the model's name (Dreamina's omnihuman-ai, Hedra's
// model pages) beside the feature page for the job; this one links to
// /make/photo-to-talking-video for the job and keeps to the model.
//
// Layout: phone hero / no signature / showcase wall (each clip opens the
// script it speaks) -- no other page has that set (the video generator is
// reel/-/showcase, Kling phone/-/reels). Features "list". Accent MAROON, new.
// The /models listing and the header file it under Video (`modelKind`),
// since OmniHuman is not a catalog render model.
//
// Media: the three clips of the make page (entries/photo-to-talking-video.ts
// says how they were made); every one is OmniHuman v2's own output.
//
// Checked 2026-10-21 against the code and fal's schema (read 2026-10-20):
// - bytedance/omnihuman/v2: image_url + audio_url (+ an optional prompt for
//   scene, movement and camera); motion follows the audio; talking or
//   singing; billed per second of the audio: src/talking_photo.py TALK
// - the model takes 4-300s of audio; the studio caps a clip per plan
//   (30/60/120s): PLAN_AUDIO_CAP, check_audio
// - the photo: 300-6000 px a side, width/height 0.4-2.5: check_image
// - the prompt's own languages (Chinese, English, Japanese, Korean, Mexican
//   Spanish, Indonesian) are the schema's; the AUDIO may be any language
// - prices are pricing.json's actions.talking_photo, never typed
import { CATALOG, num, PLANS } from "@/lib/catalog";
import { MAROON } from "../theme";
import { COMMERCIAL_FAQ } from "../shared";
import type { MakePage } from "../pages";
import { CARMEN, LENA, MECHANIC } from "./photo-to-talking-video";

const TP = CATALOG.actions.talking_photo;
const CAPS = PLANS.map((p) => `${TP.max_seconds[p.key]} seconds on ${p.name}`).join(", ");

export const OMNIHUMAN: MakePage = {
  slug: "omnihuman-video-generator",
  section: "models",
  modelIds: ["omnihuman-v2"],
  modelKind: "video",
  navLabel: "OmniHuman v2",
  title: "OmniHuman v2: ByteDance's AI Talking Video Model",
  description:
    "OmniHuman v2 animates a person in one photo to a voice track: lips, face and gestures follow the audio. Use it on Phantra with a typed script or your own recording.",
  h1: "OmniHuman v2",
  menu: "OmniHuman v2",
  subhead:
    "ByteDance's model for a person in a photo speaking or singing to a voice. One still and one sound in, a clip of them saying it out, as long as the audio.",
  cta: {
    label: "Try OmniHuman v2",
    spark: "Make the person in the attached photo say: [your script]",
    open: "talking-photo",
  },
  template: "spark",
  tone: "light",
  accent: MAROON,
  layout: {
    hero: "phone",
    order: ["overview", "wall", "features", "pricing", "howTo", "faq", "related", "final"],
    features: "list",
  },
  heroMedia: [MECHANIC, CARMEN],
  overview: {
    items: [
      {
        eyebrow: "Audio-driven",
        title: "The sound moves the face.",
        body: "OmniHuman v2 takes a single photo and an audio track and draws the person speaking it. The lips follow the words; the head, the brows and the hands follow how they are said.",
      },
      {
        eyebrow: "Speech or song",
        title: "It talks, and it sings.",
        body: "A voiceover, an interview answer or a verse of a song all drive it the same way. The clip is exactly as long as the audio.",
        points: [`On Phantra, ${TP.min_seconds} seconds and up, to ${CAPS}.`],
      },
      {
        eyebrow: "Direction",
        title: "A line of direction sets the shot.",
        body: "An optional prompt sets the scene, the movement and the camera: a slow push in, a turn to the window, a laugh at the end.",
      },
    ],
  },
  wall: {
    title: "Made on OmniHuman v2",
    tiles: [LENA, MECHANIC, CARMEN],
    explore: { label: "Make a talking photo", href: "/make/photo-to-talking-video" },
    layout: "showcase",
  },
  features: {
    title: "What OmniHuman v2 Takes",
    items: [
      { icon: "frame", title: "One photo", body: "A still of one person, 300 to 6000 pixels a side, from a tall portrait to a wide frame." },
      { icon: "sound", title: "One audio track", body: "A recording you upload (.mp3 or .wav), or a script the studio reads aloud for you first." },
      { icon: "type", title: "A typed script", body: "On Phantra, a script is voiced by ElevenLabs v3 in one of 21 voices, and you hear it before the clip." },
      { icon: "shots", title: "Lips, face and hands", body: "Mouth shapes, expressions, head turns and gestures, all timed to the sound." },
      { icon: "guide", title: "An optional prompt", body: "Scene, movement and camera in a line. Written in English, Chinese, Japanese, Korean, Spanish or Indonesian." },
      { icon: "clock", title: "As long as the audio", body: `The model takes up to 300 seconds; Phantra makes ${CAPS}.` },
      { icon: "price", title: "Priced by the second", body: "Billed on the length of the voice, rounded up to the whole second, and shown on the card before it runs." },
      { icon: "elements", title: "Your own photos", body: "An upload, a still you made in the studio or one of your saved elements." },
      { icon: "edit", title: "Then the editor", body: "The clip is a render like any other: upscale it, reframe it or cut it with other clips." },
    ],
  },
  pricing: {
    title: "OmniHuman v2 Pricing",
    intro:
      "What an OmniHuman v2 clip costs on Phantra, in credits. One rate per second of voice, so the price depends only on its length.",
    rows: TP.clips.map((c) => ({ label: `${c.seconds}-second clip`, credits: c.credits })),
    notes: [
      `The longest voice per clip is ${CAPS}.`,
      `A typed script's voice preview starts at ${num(TP.voice_preview_from)} credits; an uploaded recording costs nothing extra.`,
      "ByteDance also sells OmniHuman through its own apps and partners; we quote none of their prices here. Link checked 2026-10-20.",
    ],
    link: { href: "https://fal.ai/models/bytedance/omnihuman/v2", label: "OmniHuman v2 on fal.ai" },
  },
  models: { title: "", items: [] },
  howTo: {
    title: "How to use OmniHuman v2",
    items: [
      {
        title: "Pick a photo",
        body: "Sign in and choose a photo of one person, then confirm it is you or that they agreed.",
      },
      {
        title: "Give it a voice",
        body: "Upload a recording, or type a script, choose a voice and listen to the preview.",
      },
      {
        title: "Approve the clip",
        body: "The card shows the credits for the voice's length. Approve it and the clip lands in your Library.",
      },
    ],
  },
  faq: {
    title: "FAQs about OmniHuman v2",
    items: [
      {
        q: "What is OmniHuman v2?",
        a: "A ByteDance model that turns one photo of a person and an audio track into a video of them speaking or singing it, with lips, expressions and gestures that follow the sound.",
      },
      {
        q: "How long can an OmniHuman v2 video be?",
        a: `The model takes 4 to 300 seconds of audio. On Phantra a clip can run ${CAPS}, and it is always exactly as long as the voice.`,
      },
      {
        q: "Does it need a recording?",
        a: "No. Type a script and pick a voice, and the studio reads it aloud with ElevenLabs v3 before the clip is made. You can also upload an .mp3 or .wav.",
      },
      {
        q: "Which languages does it speak?",
        a: "The audio can be in any language: the model follows the sound, not the words. The optional direction prompt can be written in English, Chinese, Japanese, Korean, Spanish or Indonesian.",
      },
      {
        q: "Can I use a photo of someone else?",
        a: "Only with their consent. Before an OmniHuman v2 clip is priced you confirm the face is yours or that the person agreed. Review the output before you publish it: it is AI-made.",
        link: { href: "/terms", label: "Read the terms" },
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["photo-to-talking-video", "image-to-video", "consistent-character-video"],
  finalCta: {
    eyebrow: "OmniHuman v2",
    title: "One photo. One voice. A clip of them saying it.",
    body: "Type the words or upload them, hear the voice, then approve the clip at the price on the card.",
  },
};
