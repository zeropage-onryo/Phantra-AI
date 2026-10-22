/* The Create page's data (2026-10-22; docs/tasks/task-create-page-v2.md,
   then docs/tasks/task-create-front-page.md).

   Since the front page (components/studio/front, Mike's pick of boards 66
   + 68 on the "Phantra Create Page Redesign" canvas) this is what is left
   of the v2 sections: the flag, the use cases (their showcase stills are
   the renders between the news, each filling the box with its brief) and
   the free looks with the door to the effects. The rest -- the promo, the
   tool tiles, the highlights, Continue, the personal row, Made in Phantra,
   the Founding banner -- went with the sections; their words are in git.

   NO PRICES ON ANY CARD (Mike's call, 2026-10-22). Nothing in this file
   knows a credit number. A card only ever FILLS the composer's box, opens
   the effects or links somewhere -- never sends, never renders.

   Pure and import-free on purpose: tests/create-v2.test.mjs loads this
   file with node. */

export type Capabilities = Record<string, boolean>;

/** The flag, read the way every capability is read: a strict true. */
export const createV2On = (caps: Capabilities | null | undefined) => caps?.create_v2 === true;

/* ── the use cases: each fills the box with a brief, never sends ── */
export type UseCase = { id: string; title: string; line: string; brief: string; showcase: string };
export type UseCaseTab = { id: "marketing" | "social" | "film" | "business"; label: string; cards: UseCase[] };
export const USE_CASE_TABS: UseCaseTab[] = [
  {
    id: "marketing",
    label: "Marketing",
    cards: [
      {
        id: "saas",
        title: "SaaS explainer",
        line: "A 20s walk through one feature, on a dark dashboard.",
        brief: "A 20-second SaaS explainer: one feature of our product on a glowing dashboard in a dark modern office, calm voiceover, 16:9.",
        showcase: "create.usecase.saas",
      },
      {
        id: "product_ad",
        title: "Product ad",
        line: "Studio light, slow orbit, one line of type.",
        brief: "A 15-second product ad: the product on a concrete plinth under studio light, a slow orbit, one headline at the end, 16:9.",
        showcase: "create.usecase.product_ad",
      },
      {
        id: "ab_variants",
        title: "A/B variants",
        line: "Three colourways of one shot, side by side.",
        brief: "Three A/B variants of one product shot, each in a different colourway, same framing and light, 4:5.",
        showcase: "create.usecase.ab_variants",
      },
      {
        id: "launch_teaser",
        title: "Launch teaser",
        line: "The product rises out of smoke, one line.",
        brief: "A 10-second launch teaser: our product rising out of swirling smoke on black, one rim light, a slow push in, the launch date at the end, 4:5.",
        showcase: "create.usecase.launch_teaser",
      },
      {
        id: "seasonal",
        title: "Seasonal campaign",
        line: "The product in this season's light.",
        brief: "A seasonal campaign shot: our product on autumn leaves in warm late-afternoon light, shallow focus, a slow drift, 4:5, 10 seconds.",
        showcase: "create.usecase.seasonal",
      },
      {
        id: "founder",
        title: "Founder story",
        line: "The maker at work, documentary light.",
        brief: "A 20-second founder story: the founder at work in their own studio, hands close-up then a wide, warm documentary light, a voiceover line about why they started, 16:9.",
        showcase: "create.usecase.founder",
      },
    ],
  },
  {
    id: "social",
    label: "Social",
    cards: [
      {
        id: "ugc",
        title: "UGC ad",
        line: "A creator to camera, warm bathroom light, 9:16.",
        brief: "A UGC-style ad: a creator holding our product to camera in warm bathroom light, talking naturally, 9:16, 15 seconds.",
        showcase: "create.usecase.ugc",
      },
      {
        id: "vertical",
        title: "Vertical-ready",
        line: "Your clip, centred and cut to 9:16.",
        brief: "Cut my last clip to 9:16, centred on the subject, ready for Reels.",
        showcase: "look.vertical_ready",
      },
      {
        id: "flash",
        title: "2000s flash",
        line: "Flash pops, a date stamp, a party look.",
        brief: "A 2000s flash-photo look on a night-out clip: flash pops, grain, a date stamp in the corner, 9:16.",
        showcase: "look.flash_2000s",
      },
      {
        id: "hook",
        title: "Talking-head hook",
        line: "A creator to camera, first two seconds.",
        brief: "A talking-head hook for TikTok: a creator talking straight to their phone in a bright bedroom, an excited first line in the first two seconds, 9:16, 10 seconds.",
        showcase: "create.usecase.hook",
      },
      {
        id: "day_in_life",
        title: "Day in the life",
        line: "Coffee, the street, the morning, POV.",
        brief: "A day-in-the-life Reel: point-of-view shots of a morning, an iced coffee on a sunny café terrace, quick cuts on the beat, 9:16, 15 seconds.",
        showcase: "create.usecase.day_in_life",
      },
      {
        id: "unboxing",
        title: "Unboxing",
        line: "Hands, a box, the reveal, from above.",
        brief: "An unboxing video from above: hands open a plain kraft box with tissue paper and lift out our product, soft daylight on a wooden desk, 9:16, 12 seconds.",
        showcase: "create.usecase.unboxing",
      },
    ],
  },
  {
    id: "film",
    label: "Film",
    cards: [
      {
        id: "music_video",
        title: "Music video",
        line: "A singer in a red-lit tunnel, haze, slow push.",
        brief: "A music video scene: a singer in a red-lit tunnel with haze, slow push in, cuts on the beat, 16:9, 20 seconds.",
        showcase: "create.usecase.music_video",
      },
      {
        id: "trailer",
        title: "Trailer",
        line: "A lone figure, a monolith at dusk, one title.",
        brief: "A 20-second trailer: a lone figure in the desert facing a giant monolith at dusk, wide shots, a single title card at the end, 2.39:1.",
        showcase: "create.usecase.trailer",
      },
      {
        id: "noir",
        title: "Noir short",
        line: "Black and white, one streetlight, rain.",
        brief: "A noir short: one figure under a single streetlight on a wet sidewalk at night, black and white, grain and vignette, 16:9.",
        showcase: "look.noir",
      },
      {
        id: "scifi",
        title: "Sci-fi short",
        line: "A corridor in neon, one figure walking.",
        brief: "A sci-fi short: an astronaut walking down a narrow spaceship corridor lit in blue and magenta, haze, slow tracking shot, 2.39:1, 20 seconds.",
        showcase: "create.usecase.scifi",
      },
      {
        id: "horror",
        title: "Horror teaser",
        line: "One flashlight, a hallway, a door ajar.",
        brief: "A horror teaser: a flashlight beam moving down a dark hallway in an old house toward a door left ajar, dust in the light, slow and quiet, 16:9, 15 seconds.",
        showcase: "create.usecase.horror",
      },
      {
        id: "period",
        title: "Period drama",
        line: "Candlelight, a letter, a turn of the head.",
        brief: "A period drama scene: a woman in a nineteenth-century dress reading a letter by candlelight, she looks up at a sound, painterly light, 16:9, 15 seconds.",
        showcase: "create.usecase.period",
      },
    ],
  },
  {
    id: "business",
    label: "Business",
    cards: [
      {
        id: "menu_promo",
        title: "Menu promo",
        line: "Overhead steam, dark wood, the dish of the week.",
        brief: "A 10-second menu promo: overhead shot of steaming ramen on dark wood, slow drift, the dish name at the end, 4:5.",
        showcase: "create.usecase.menu_promo",
      },
      {
        id: "local",
        title: "Local business ad",
        line: "Your storefront clip, graded and cut vertical.",
        brief: "A local business ad from my storefront clip: film grade, cut to 9:16, our name and hours at the end.",
        showcase: "look.make_it_pro",
      },
      {
        id: "talking",
        title: "Talking photo",
        line: "A photo of the owner says the offer.",
        brief: "A talking photo: the owner's portrait reads a 10-second welcome and this week's offer.",
        showcase: "look.film_grade",
      },
      {
        id: "real_estate",
        title: "Real estate tour",
        line: "Sunlit rooms, a slow walk through.",
        brief: "A 20-second real estate tour: a slow walk-through of a bright modern living room with floor-to-ceiling windows, afternoon sun, wide lens, 16:9.",
        showcase: "create.usecase.real_estate",
      },
      {
        id: "gym",
        title: "Gym promo",
        line: "Hands wrapped at dawn, light through the windows.",
        brief: "A gym promo: a boxer wrapping her hands at dawn in a gritty gym, shafts of light, then a hard first punch on the bag, 9:16, 15 seconds.",
        showcase: "create.usecase.gym",
      },
      {
        id: "event",
        title: "Event recap",
        line: "String lights, laughter, the best ten seconds.",
        brief: "A 15-second event recap: guests laughing with drinks under string lights in an industrial loft, quick candid cuts, warm bokeh, 9:16.",
        showcase: "create.usecase.event",
      },
    ],
  },
];

/* ── the six free looks ── */
export type LookCard = { id: string; label: string; line: string; showcase: string; tab: string };
export const LOOKS: LookCard[] = [
  { id: "film_grade", label: "Film Grade", line: "LUT, grain, letterbox", showcase: "look.film_grade", tab: "finish" },
  { id: "noir", label: "Noir", line: "Black and white, vignette", showcase: "look.noir", tab: "finish" },
  { id: "flash_2000s", label: "2000s Flash", line: "Flash pops, date stamp", showcase: "look.flash_2000s", tab: "finish" },
  { id: "crash_zoom", label: "Crash-Zoom Hook", line: "A zoom on the first beat", showcase: "look.crash_zoom", tab: "camera" },
  { id: "vertical_ready", label: "Vertical Ready", line: "Centred 9:16 crop", showcase: "look.vertical_ready", tab: "finish" },
  { id: "make_it_pro", label: "Make It Pro", line: "Grade, vertical, sound", showcase: "look.make_it_pro", tab: "finish" },
];

/** Where an effect or a look on the front page goes: the Effects tab
 *  when its flag is on, else the composer's own gallery. */
export const effectsDoor = (caps: Capabilities | null | undefined): "tab" | "gallery" =>
  caps?.effects_tab === true ? "tab" : "gallery";
export const EFFECTS_TAB_HREF = "/studio/effects";
