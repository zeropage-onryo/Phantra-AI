// The /make hub's groups (2026-10-27): every /make page in exactly one
// group, so the hub links to each of them from one click below the header
// and Google reads them as one family of pages. web/tests/make-hub.test.mjs
// fails when a /make entry is in no group (a new page left off the hub) or
// a group names a slug no entry has.
//
// "Seasonal" holds the pages with a `season` (seasonal.ts). It is listed
// all year, on purpose: the season decides only the header tab and the
// page's look, never whether the page is linked.
//
// Pure: no imports, so the test runs it as is.

export type HubGroup = {
  title: string;
  /** One line under the group's title. */
  line: string;
  slugs: string[];
};

export const HUB_GROUPS: HubGroup[] = [
  {
    title: "Video",
    line: "Turn a sentence or a photo into a clip.",
    slugs: ["ai-video-generator", "text-to-video", "image-to-video", "photo-to-talking-video", "consistent-character-video"],
  },
  {
    title: "Ads and marketing",
    line: "Product ads, commercials and creator-style spots from your own photos.",
    slugs: ["ai-product-ad-generator", "ai-commercial-maker", "ugc-ads"],
  },
  {
    title: "Social",
    line: "Vertical video made for the feed.",
    slugs: ["ai-tiktok-video-generator", "ai-instagram-reels-maker", "ai-youtube-shorts-maker"],
  },
  {
    title: "Film and story",
    line: "Shorts, trailers and music videos, planned shot by shot.",
    slugs: ["ai-movie-maker", "ai-short-film-maker", "ai-trailer-maker", "ai-storyboard-generator", "ai-music-video-generator"],
  },
  {
    title: "Seasonal",
    line: "Made for the holidays, here all year.",
    slugs: ["ai-halloween-costume-try-on"],
  },
];
