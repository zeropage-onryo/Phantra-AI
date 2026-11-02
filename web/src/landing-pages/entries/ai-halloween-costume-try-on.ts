// /make/ai-halloween-costume-try-on (2026-10-27, Mike: "Ai halloween costume
// try on, fix it ... I want this out by today posting on socials"). First
// drafted the same morning as an "AI Halloween video effects" page; Mike
// re-pointed it at a try-on, so the lead is now the Costume Try-On recipe
// and the fourteen Kling / PixVerse Halloween templates are the second act.
//
// SEARCH: Semrush had no API units on 2026-10-27, so the phrase is Mike's
// own, and the one the pages already ranking circle: insMind's "AI Halloween
// Video Effects from Your Photo" (costume cards like Green Witch / Queen of
// Hearts), Morphic's "AI Halloween costume videos" (a "try-on at the mirror"
// scene), Pollo's "Halloween Cosplay", Magic Hour's per-template pages.
// What this page took from them: costume vs creature split (insMind), the
// "Will it keep my face?" and "Can I post it?" FAQs (insMind, Morphic),
// every template named in the copy (Magic Hour). What none of them has: any
// costume you can name (not a fixed card), and the finishing tools after.
// Re-check volume when units return.
//
// LAYOUT: hero "fan" / no signature / wall "bento" -- a twin of no page (the
// other fans are storyboard fan/shot-timeline/editorial and Ideogram
// fan/poster-type/posters; the only other bento is UGC ads
// phone/sound-board/bento). Dark tone, PHANTRA accent. No pricing section
// and no credit figure (Mike, 2026-10-22); no small wording (2026-10-23):
// tiles carry no title, tag or meta, the costume names live in the copy.
//
// NO "FREE" (Mike, 2026-10-27, "dont say free"): no copy on this page says
// free, or what a new account's credits buy. The note below is how the two
// steps work under the hood, kept for whoever revisits it.
// FREE AND PAID (Mike, 2026-10-27, "do option 1"): the preview is a still
// on Nano Banana edit (src/effects.py "nano-banana-edit", "keeps faces and
// identity", priced at pricing.CREDIT_FLOOR), which a new account's one-time
// sign-up credits (PHANTRA_SIGNUP_CREDITS, 100) cover several times over; the
// spin-reveal video is the paid render. No figure is typed: the page says
// "free with a new account's starter credits" and "priced on the card". A
// per-day free preview (no credits at all) is the follow-up, not built.
//
// MEDIA: none yet. Nothing is generated without Mike's yes, and the
// showcase manifest has no Halloween example on 2026-10-27, so every tile
// is a marigold plate until example clips are approved.
// BEFORE AND AFTER (2026-10-27): a wall tile given `from` (the person's original
// photo) and `src` (their costume still) splits down the middle and slides to the
// costume on hover (ad-wall.tsx). When the examples land, give the stills `from`.
//
// Checked 2026-10-27 against the code:
// - Costume Try-On: src/effect_recipes.py RECIPES["costume_try_on"], the
//   prompt in prompts/effects/costume_try_on.txt (one spin, the person comes
//   back around in the costume they typed, face, hair, skin and build kept;
//   a witch when nothing is typed), Kling 3 Turbo Pro image-to-video, one
//   photo in, 5 or 10 seconds (DURATIONS), 1080p (the model's default);
//   listed where PHANTRA_EFFECT_RECIPES=1 (on Fly since 2026-10-26)
// - the templates: src/effects.py "kling-effect" (KLING_EFFECTS:
//   witch_transform, vampire_transform, pumpkin_head_transform,
//   demon_transform, mummy_transform, zombie_transform,
//   cute_pumpkin_transform, halloween_escape; 5 or 10 s) and
//   "pixverse-effect" (PIXVERSE_EFFECTS: Zombie Mode, Werewolf Rage,
//   GhostFace Terror, Skeletal Bae, Creepy Devil Smile, Halloween Voodoo
//   Doll; 5 s, up to 1080p); prompt "none" on both
// - the way in: a photo attached to the composer is the effect's source
//   (create-view.tsx fxCandidates), `/effects` opens the gallery, the
//   brain's apply_effect (guide_tools EFFECT_TOOL) proposes the card from a
//   sentence, and the card's Approve is the one spend (POST /api/effects/run)
// - after: "reframe", "add-sound", "upscale" in src/effects.py; the editor
//   (src/cut/) exports MP4
import { COMMERCIAL_FAQ } from "../shared";
import { HALLOWEEN, PHANTRA } from "../theme";
import type { MakePage, MakeTile } from "../pages";

// MEDIA (2026-10-29, Mike approved each batch): four invented people (no
// real faces) drawn on Seedream 4.5, costumes put on them with Nano Banana
// edit (face kept), and five spin-reveal clips on Kling 3 Turbo Pro from
// the before photos with the Costume Try-On prompt. All of it is in the
// studio's project 7, "Halloween Costume Try-On page". Stills and posters
// live in public/make/ai-halloween-costume-try-on/; the MP4s in R2 at
// site/make/ai-halloween-costume-try-on/ (media.ts). A poster is the clip's
// last frame, the costume, since the first frame is the plain photo.
const DIR = "/make/ai-halloween-costume-try-on";
const still = (name: string): MakeTile => ({ title: "", tag: "", aspect: "9:16", src: `${DIR}/${name}.jpg` });
const spin = (name: string): MakeTile => ({
  title: "",
  tag: "",
  aspect: "9:16",
  video: `${DIR}/spin-${name}.mp4`,
  src: `${DIR}/spin-${name}.jpg`,
});

// the twelve one-tap costumes, in the card's order (src/costumes.py COSTUMES)
const COSTUME_IDEAS = [
  "Vampire",
  "Witch",
  "Pirate",
  "Skeleton",
  "Zombie bride",
  "Werewolf",
  "Mummy",
  "Devil",
  "Angel",
  "Ghost",
  "Scarecrow",
  "Black cat",
];
const KLING_LOOKS = ["Witch", "Vampire", "Pumpkin Head", "Demon", "Mummy", "Zombie", "Cute Pumpkin", "Halloween Escape"];
const PIXVERSE_LOOKS = [
  "Zombie Mode",
  "Werewolf Rage",
  "GhostFace Terror",
  "Skeletal Bae",
  "Creepy Devil Smile",
  "Halloween Voodoo Doll",
];
const list = (xs: string[]) => `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;

export const HALLOWEEN_TRY_ON: MakePage = {
  slug: "ai-halloween-costume-try-on",
  section: "make",
  title: "AI Halloween Costume Try-On: See Yourself in Any Costume",
  description:
    "Try on any Halloween costume with AI: upload a photo, name the costume, and watch yourself spin into it in a short video. Your face stays yours.",
  h1: "AI Halloween Costume Try-On",
  menu: "Halloween Costume Try-On",
  subhead: "Preview any costume on your own photo, then watch yourself spin into it on video. Your face stays yours.",
  cta: {
    label: "Try on a costume",
    spark: "Edit my attached photo to show me in a vampire costume with a high-collared cape. Keep my face, hair and build; change only the clothes.",
    // the CTA opens the costume card itself: a photo, one tap, Approve
    open: "costume",
    secondary: { label: "See the costumes", href: "#examples" },
    startLabel: "Try it",
  },
  template: "spark",
  tone: "dark",
  accent: PHANTRA,
  layout: {
    hero: "fan",
    order: ["wall", "overview", "features", "howTo", "models", "faq", "related", "final"],
    features: "grid",
  },
  // SEASON (2026-10-27, Mike: its own tab, spooky for Halloween, "ends the
  // day after halloween"): the header tab and the pumpkin-and-night look
  // run Oct 1 to Nov 1 on Eastern time, every year. The page itself stays
  // up all year in the footer and the /make hub's Seasonal group.
  season: { start: "10-01", end: "11-01", tab: "Halloween", timeZone: "America/New_York", accent: HALLOWEEN },
  heroMedia: [spin("vampire"), spin("pirate"), spin("witch"), spin("skeleton"), spin("werewolf")],
  card: `${DIR}/denim-vampire.jpg`,
  overview: {
    items: [
      {
        title: "Preview it first.",
        body: "Tap one of twelve costumes and get a photo of you wearing it, face kept. Try on as many as you like before you make the video.",
        points: COSTUME_IDEAS,
        // the before/after slider: drag from the photo to the costume
        media: still("denim-vampire"),
        compare: { media: still("before-denim"), label: "Before", mediaLabel: "After" },
      },
      {
        title: "Then watch the reveal.",
        body: "Found the one? Tap Make it a video: you spin once and come back around wearing it, head to toe. Your face, hair and build stay yours; only the clothes change.",
        media: spin("vampire"),
      },
      {
        title: "Or go full creature.",
        body: `Fourteen one-tap templates turn you into the monster itself. On Kling: ${list(KLING_LOOKS)}. On PixVerse: ${list(PIXVERSE_LOOKS)}.`,
        media: still("hoodie-werewolf"),
      },
    ],
  },
  wall: {
    title: "Try It On Before You Buy It",
    tiles: [
      { ...still("denim-pirate"), prompt: "Show me as a pirate captain: a long burgundy coat with gold buttons, a ruffled shirt and a tricorn hat." },
      { ...still("couple"), prompt: "Dress us as a couple: me as Frankenstein's bride in a white gown, him as a vampire in a high-collared cape." },
      { ...still("varsity-zombie-prom"), prompt: "Show me as a zombie prom date in a tattered powder-blue tuxedo with a wilted corsage." },
      { ...still("hoodie-grim-reaper"), prompt: "Show me as the grim reaper: a long hooded black robe and a tall scythe." },
      { ...still("varsity-scarecrow"), prompt: "Show me as a scarecrow: a patched plaid shirt, overalls, straw at the cuffs and a battered straw hat." },
      { ...still("silver-mummy"), prompt: "Wrap me up as a mummy in aged linen bandages, face uncovered." },
      { ...still("varsity-vampire"), prompt: "Show me as a vampire in a black suit and a cape with a crimson lining." },
      { ...still("silver-green-witch"), prompt: "Show me as a green witch: an emerald velvet dress, a dark green cape and a tall pointed hat." },
    ],
    explore: { label: "Try on a costume", href: "#how" },
    // showcase (2026-10-29): masonry at each tile's own 9:16 frame; bento
    // cropped the full-length costumes to landscape and cut off the heads
    layout: "showcase",
  },
  features: {
    title: "What the Costume Try-On Does",
    items: [
      {
        icon: "assets",
        title: "One photo in",
        body: "A clear photo of one person, ideally head to toe, is all it needs.",
      },
      {
        icon: "type",
        title: "Twelve to tap, or your own",
        body: "Tap a vampire, a witch or a pirate, or tell Vesper any costume you can describe, down to your group's theme.",
      },
      {
        icon: "elements",
        title: "Keeps your face",
        body: "Your face, hair and build are held from the photo. Only the outfit changes.",
      },
      {
        icon: "shots",
        title: "A reveal built in",
        body: "One spin through smoke and falling leaves, then the pose. The clip is made to post.",
      },
      {
        icon: "clock",
        title: "Five or ten seconds",
        body: "Pick the length on the card. Both are 1080p.",
      },
      {
        icon: "guide",
        title: "Ask in plain words",
        body: "Tell Vesper \"try a pirate costume on me\" and it opens the try-on on your photo, ready to approve.",
      },
      {
        icon: "frame",
        title: "Fits every feed",
        body: "Reframe the clip to 9:16 for TikTok and Reels, 1:1 for a post, or 16:9 for YouTube.",
      },
      {
        icon: "sound",
        title: "Add the sound",
        body: "Give the reveal a whoosh, wind or a thunder crack with a sound pass made to the picture.",
      },
      {
        icon: "edit",
        title: "Preview first",
        body: "Try a few costumes as photos, keep the one you like, then make the video of that one.",
      },
    ],
  },
  models: {
    title: "The Effects Behind It",
    items: [
      {
        title: "Costume preview",
        body: "Nano Banana edit puts the costume on your own photo and keeps your face. The first step.",
        spark: "Edit my attached photo to show me as a pirate captain. Keep my face, hair and build; change only the clothes.",
      },
      {
        title: "Costume Try-On",
        body: "A Phantra recipe on Kling 3 Turbo Pro: your photo, the costume you name, a spin-and-reveal clip.",
        spark: "Use the Costume Try-On effect on my attached photo: a pirate captain.",
      },
      {
        title: "Kling Halloween effects",
        body: `Eight one-tap creature templates: ${list(KLING_LOOKS)}.`,
        spark: "Turn the person in my attached photo into a vampire with the Kling vampire effect.",
      },
      {
        title: "PixVerse Halloween effects",
        body: `Six one-tap scares: ${list(PIXVERSE_LOOKS)}.`,
        spark: "Give the person in my attached photo the PixVerse Werewolf Rage effect.",
      },
    ],
  },
  howTo: {
    title: "How to try on a Halloween costume",
    items: [
      {
        title: "Add your photo",
        body: "Sign in and drop a photo of yourself into the box. Head to toe works best.",
      },
      {
        title: "Preview it first",
        body: "Tap a costume and see yourself in it in seconds. Try a few.",
      },
      {
        title: "Make the video",
        body: "Tap Make it a video under the photo you like, approve the card, and download the MP4.",
      },
    ],
  },
  faq: {
    title: "FAQs about the AI Costume Try-On",
    items: [
      {
        q: "What is an AI Halloween costume try-on?",
        a: "You upload a photo of yourself and name a costume. The AI makes a short video of you spinning once and coming back around dressed in it, so you can see the costume on you before you buy or make it.",
      },
      {
        q: "Which costumes can I try on?",
        a: `Twelve with one tap: ${list(COSTUME_IDEAS)}. Any other costume you can describe works too: tell Vesper, or type it on the Costume Try-On video.`,
      },
      {
        q: "Will it keep my face?",
        a: "The clip starts from your photo and the try-on is written to change only the clothes, keeping your face, hair, skin tone and build. A clear photo of one person, facing the camera, keeps the most of you. Watch the clip before you post it.",
      },
      {
        q: "Can I try on more than one costume?",
        a: "Yes. Preview as many costumes as you like as photos, keep the one you love, then make the spin-reveal video of that one.",
      },
      {
        q: "What is the difference between the try-on and the creature effects?",
        a: `The try-on dresses you in the costume you name and keeps you looking like you. The ${KLING_LOOKS.length + PIXVERSE_LOOKS.length} creature templates turn you into the monster itself, like a zombie or a werewolf, and change your face on purpose. They take no costume text.`,
      },
      {
        q: "How long is the video?",
        a: "The try-on is five or ten seconds at 1080p. The Kling creature effects run five or ten seconds, the PixVerse ones five.",
      },
      {
        q: "Can I post it to TikTok or Instagram Reels?",
        a: "Yes. Download the MP4, or reframe it to 9:16 first. You can also add sound, or cut several costumes into one video in the editor.",
      },
      {
        q: "Can I use a photo of someone else?",
        a: "Only with their permission. You are responsible for the photos you upload, and the output is AI-made, so review it before you share it.",
        link: { href: "/terms", label: "Read the terms" },
      },
      COMMERCIAL_FAQ,
    ],
  },
  related: ["image-to-video", "photo-to-talking-video", "ai-tiktok-video-generator", "ai-instagram-reels-maker"],
  finalCta: {
    eyebrow: "",
    title: "See yourself in it.",
    body: "Preview the costume on your own photo, then make the video of the one you love.",
  },
};
