// The nine quick starts on the homepage hero (2026-11-02, Mike's pick of the
// "17d" direction on the Phantra Homepage canvas, with the "Side drawer"
// popup). A chip swaps the big preview and opens the drawer; the drawer's
// choices travel into the studio composer as the query it already reads
// (?spark=, ?frame=, ?seconds=, ?kind=), so nothing here calls a model or
// spends.
//
// Every option is one the studio really offers: frames are labels the
// composer matches against the server's own list (one it does not offer is
// ignored), and lengths stay inside a scene's 4-30 seconds. The pictures are
// real studio output already shipped with the landing pages.

export type StartKind = "video" | "image";

export type HeroStart = {
  id: string;
  label: string;
  kind: StartKind;
  /** the picture on the chip, the preview and the drawer */
  image: string;
  /** the clip the hero plays for this start (2026-11-02, the B3 "clip rail"
   *  hero): a public /make, /models or /mcp path that clipSrc maps onto the
   *  R2 bucket, its first-frame poster under public/, and whether it is a
   *  vertical clip (drawn as a phone-shaped card on a wide screen rather than
   *  stretched across it) */
  clip: { src: string; poster: string; tall?: boolean };
  /** the placeholder: an example of what to type */
  example: string;
  /** what the ChatGPT line suggests asking for */
  ask: string;
  /** Vesper's one line in the drawer */
  line: string;
  frames: string[];
  /** seconds for a video; for a still, how many (carried as words) */
  lengths: { label: string; seconds?: number }[];
  looks: string[];
  /** pictures under the looks, one per look (cycled) */
  lookImages: string[];
};

const M = "/models";
const K = "/make";

export const HERO_STARTS: HeroStart[] = [
  {
    id: "short-film",
    label: "Short film",
    kind: "video",
    image: "/site/reel/c375.jpg",
    clip: { src: `${K}/ai-short-film-maker/hero.mp4`, poster: `${K}/ai-short-film-maker/busstop.jpg` },
    example: "A stranger in a rain-soaked neon city…",
    ask: "a neon short film",
    line: "I’ll write it shot by shot and show you every still before anything renders.",
    frames: ["16:9", "21:9", "9:16"],
    lengths: [{ label: "15 sec", seconds: 15 }, { label: "20 sec", seconds: 20 }, { label: "30 sec", seconds: 30 }],
    looks: ["Noir", "Neon night", "Golden hour", "Overcast"],
    lookImages: ["/site/reel/c375.jpg", `${M}/kling-video-generator/rooftop.jpg`, `${M}/kling-video-generator/boxer.jpg`, `${M}/seedance-video-generator/sig-wide.jpg`],
  },
  {
    id: "music-video",
    label: "Music video",
    kind: "video",
    image: `${M}/wan-video-generator/flamenco.jpg`,
    clip: { src: `${M}/wan-video-generator/flamenco.mp4`, poster: `${M}/wan-video-generator/flamenco.jpg` },
    example: "A flamenco dancer cut to a slow guitar…",
    ask: "a flamenco music video",
    line: "Give me the mood and the song. I’ll cut the shots to the beat.",
    frames: ["9:16", "16:9", "1:1"],
    lengths: [{ label: "10 sec", seconds: 10 }, { label: "15 sec", seconds: 15 }, { label: "30 sec", seconds: 30 }],
    looks: ["Spotlight", "Club neon", "Film grain", "Dreamy"],
    lookImages: [`${M}/wan-video-generator/flamenco.jpg`, `${M}/kling-video-generator/dancer.jpg`, "/site/reel/c375.jpg", `${M}/seedance-video-generator/surfer.jpg`],
  },
  {
    id: "ugc-ad",
    label: "UGC ad",
    kind: "video",
    image: `${K}/ugc-ads/bottle.jpg`,
    clip: { src: `${K}/ugc-ads/bottle.mp4`, poster: `${K}/ugc-ads/bottle.jpg`, tall: true },
    example: "A gym-goer showing off my steel bottle…",
    ask: "a UGC ad for my bottle",
    line: "Show me the product. I’ll write the hook and the person holding it.",
    frames: ["9:16", "4:5", "1:1"],
    lengths: [{ label: "10 sec", seconds: 10 }, { label: "15 sec", seconds: 15 }, { label: "30 sec", seconds: 30 }],
    looks: ["Selfie cam", "Gym", "Kitchen", "Outdoors"],
    lookImages: [`${K}/ugc-ads/bottle.jpg`, `${K}/ugc-ads/coffee.jpg`, `${K}/ugc-ads/bottle-photo.jpg`, `${K}/ugc-ads/coffee-photo.jpg`],
  },
  {
    id: "product-ad",
    label: "Product ad",
    kind: "video",
    image: `${K}/ai-product-ad-generator/fragrance.jpg`,
    clip: { src: `${M}/seedance-video-generator/soda.mp4`, poster: `${M}/seedance-video-generator/soda.jpg` },
    example: "My fragrance on stone, figs and morning light…",
    ask: "a product ad for my fragrance",
    line: "One product, three hero angles. Pick the one that sells it.",
    frames: ["16:9", "9:16", "1:1"],
    lengths: [{ label: "6 sec", seconds: 6 }, { label: "15 sec", seconds: 15 }, { label: "30 sec", seconds: 30 }],
    looks: ["Studio white", "Stone & light", "Colour pop", "Luxury dark"],
    lookImages: [`${K}/ai-product-ad-generator/fragrance.jpg`, `${K}/ai-product-ad-generator/headphones.jpg`, `${M}/ideogram-image-generator/perfume.jpg`, `${K}/ugc-ads/bottle-photo.jpg`],
  },
  {
    id: "brand-ad",
    label: "Brand ad",
    kind: "video",
    image: `${M}/veo-video-generator/barista.jpg`,
    clip: { src: `${M}/veo-video-generator/barista.mp4`, poster: `${M}/veo-video-generator/barista.jpg` },
    example: "A 15-second café spot in my brand colours…",
    ask: "a 15-second café spot",
    line: "Your colours and logo on every scene. Tell me what the spot should say.",
    frames: ["16:9", "9:16"],
    lengths: [{ label: "15 sec", seconds: 15 }, { label: "20 sec", seconds: 20 }, { label: "30 sec", seconds: 30 }],
    looks: ["My brand kit", "Warm", "Clean", "Bold"],
    lookImages: [`${M}/veo-video-generator/barista.jpg`, `${K}/ugc-ads/coffee.jpg`, `${K}/ugc-ads/coffee-photo.jpg`, `${M}/nano-banana-image-generator/step-3.jpg`],
  },
  {
    id: "trailer",
    label: "Trailer",
    kind: "video",
    image: "/site/reel/c135.jpg",
    clip: { src: `${K}/ai-trailer-maker/hero.mp4`, poster: `${K}/ai-trailer-maker/ship.jpg` },
    example: "A creature-comedy trailer, three beats…",
    ask: "a creature-comedy trailer",
    line: "Three beats, a title card and a sting. I’ll build the trailer around your hook.",
    frames: ["21:9", "16:9"],
    lengths: [{ label: "15 sec", seconds: 15 }, { label: "20 sec", seconds: 20 }, { label: "30 sec", seconds: 30 }],
    looks: ["Horror", "Comedy", "Epic", "Sci-fi"],
    lookImages: ["/site/reel/c135.jpg", "/site/reel/c375.jpg", `${M}/kling-video-generator/boxer.jpg`, `${M}/ltx-video-generator/diver.jpg`],
  },
  {
    id: "shorts-reels",
    label: "Shorts & Reels",
    kind: "video",
    image: `${M}/kling-video-generator/rooftop.jpg`,
    clip: { src: "/mcp/examples/video-skate.mp4", poster: "/mcp/examples/video-skate.jpg", tall: true },
    example: "A laugh on a windy rooftop, 9:16…",
    ask: "a 9:16 rooftop reel",
    line: "Vertical from the first frame, with a hook in the first second.",
    frames: ["9:16"],
    lengths: [{ label: "8 sec", seconds: 8 }, { label: "15 sec", seconds: 15 }, { label: "30 sec", seconds: 30 }],
    looks: ["Trending", "Cinematic", "Lo-fi", "Bright"],
    lookImages: [`${M}/kling-video-generator/rooftop.jpg`, `${M}/seedance-video-generator/dancer.jpg`, `${M}/veo-video-generator/surf.jpg`, `${M}/wan-video-generator/balloons.jpg`],
  },
  {
    id: "storyboard",
    label: "Storyboard",
    kind: "image",
    image: `${M}/seedance-video-generator/sig-wide.jpg`,
    clip: { src: `${K}/ai-movie-maker/lake.mp4`, poster: `${K}/ai-movie-maker/lake-poster.jpg` },
    example: "Board out a potter’s morning in six frames…",
    ask: "a six-frame storyboard",
    line: "Paste the script. I’ll board it frame by frame so you can approve the look.",
    frames: ["16:9", "9:16"],
    lengths: [{ label: "4 frames" }, { label: "6 frames" }, { label: "8 frames" }],
    looks: ["Cinematic", "Moody", "Bright"],
    lookImages: [`${M}/seedance-video-generator/sig-wide.jpg`, `${M}/nano-banana-image-generator/step-1.jpg`, `${M}/nano-banana-image-generator/step-3.jpg`],
  },
  {
    id: "product-shot",
    label: "Product shot",
    kind: "image",
    image: `${K}/ai-product-ad-generator/headphones.jpg`,
    clip: { src: `${M}/seedance-video-generator/honey.mp4`, poster: `${M}/seedance-video-generator/honey.jpg`, tall: true },
    example: "Exploded headphones on a yellow ground…",
    ask: "a headphones product shot",
    line: "Clean, sharp product shots. Want one of them moving too?",
    frames: ["1:1", "4:5", "16:9"],
    lengths: [{ label: "1 still" }, { label: "4 stills" }],
    looks: ["Studio white", "Colour pop", "Lifestyle", "Floating"],
    lookImages: [`${K}/ai-product-ad-generator/headphones.jpg`, `${K}/ai-product-ad-generator/fragrance.jpg`, `${K}/ugc-ads/bottle-photo.jpg`, `${M}/nano-banana-image-generator/honey.jpg`],
  },
];

/** A label for a frame value, as the drawer shows it. */
export const frameLabel = (frame: string) => (frame === "21:9" ? "21:9 cinema" : frame);
