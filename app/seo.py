"""
The machine-readable growth surface: robots.txt, llms.txt, sitemap.xml,
and the homepage JSON-LD graph.

Every function here is pure -- it takes the site's base URL and returns a
string. That's deliberate: these files are the one part of the app whose
*exact bytes* matter to a crawler, so they're testable without a server,
and a change to the wording is a diff in a test rather than something you
only notice when a bot stops citing you.

The public surface is small on purpose (one page today). The list below
is the single place to add a page when there is one -- robots, the
sitemap, and llms.txt all read from it, so they can't drift apart.
"""
import json
import os
from datetime import date
from typing import Optional

# The canonical origin. No trailing slash. Local by default so a fresh
# clone serves something coherent; set SITE_URL in .env before the site
# is public or every canonical tag and schema @id points at localhost.
DEFAULT_SITE_URL = "http://127.0.0.1:8000"

# Renamed 2026-10-03 (Mike's call); the description rewritten 2026-10-11 --
# the old one still pitched photographed rooms and real footage, which the
# product dropped in Aug 2026, and this file is the connector listings'
# public documentation (app/mcp_auth `resource_documentation`).
PRODUCT_NAME = "Zeropage Studio"
TAGLINE = (
    "An AI production studio for brands, ad agencies, creators and "
    "filmmakers: write a scene, ground it in your own photos, see the price "
    "in credits, and render it on the leading video models."
)

# path -> (title, one-line description for llms.txt, sitemap priority)
PUBLIC_PAGES = [
    ("/", PRODUCT_NAME, TAGLINE, "1.0"),
]

# The workspace and the pipeline screens behind it. Reachable, useful, and
# nobody's search result -- they're the product, not content.
PRIVATE_PREFIXES = [
    "/studio", "/dashboard", "/concepts", "/locations", "/pitches",
    "/analytics", "/library", "/videos", "/metrics",
]

# Crawlers that feed AI answers. Named explicitly rather than left to the
# `User-agent: *` default: a product that wants to be recommended inside
# AI answers has nothing to gain from blocking the crawlers that build
# them, and being explicit means a future tightening is a visible edit.
AI_CRAWLERS = [
    "GPTBot",           # OpenAI, training + browsing
    "OAI-SearchBot",    # OpenAI, ChatGPT search
    "ChatGPT-User",     # OpenAI, user-initiated fetch
    "ClaudeBot",        # Anthropic
    "Claude-User",      # Anthropic, user-initiated fetch
    "PerplexityBot",    # Perplexity
    "Perplexity-User",  # Perplexity, user-initiated fetch
    "Google-Extended",  # Google, Gemini/AI Overviews grounding
    "Applebot-Extended",
    "meta-externalagent",
    "Bingbot",
    "cohere-ai",
]


def site_url() -> str:
    """The configured origin, without a trailing slash."""
    return (os.environ.get("SITE_URL") or DEFAULT_SITE_URL).rstrip("/")


def absolute(path: str, base: Optional[str] = None) -> str:
    base = (base or site_url()).rstrip("/")
    return base + path if path != "/" else base + "/"


def robots_txt(base: Optional[str] = None) -> str:
    """
    Open the public page to everything, keep the app out of the index,
    and point every crawler at the sitemap.
    """
    base = base or site_url()
    lines = [f"# {PRODUCT_NAME}", ""]

    disallow = [f"Disallow: {p}" for p in PRIVATE_PREFIXES]

    lines += ["User-agent: *", "Allow: /", *disallow, ""]
    for bot in AI_CRAWLERS:
        lines += [f"User-agent: {bot}", "Allow: /", *disallow, ""]

    lines += [f"Sitemap: {absolute('/sitemap.xml', base)}", ""]
    return "\n".join(lines)


def sitemap_xml(base: Optional[str] = None, lastmod: Optional[str] = None) -> str:
    base = base or site_url()
    lastmod = lastmod or date.today().isoformat()
    urls = "".join(
        "\n  <url>"
        f"\n    <loc>{absolute(path, base)}</loc>"
        f"\n    <lastmod>{lastmod}</lastmod>"
        f"\n    <priority>{priority}</priority>"
        "\n  </url>"
        for path, _title, _desc, priority in PUBLIC_PAGES
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}\n</urlset>\n"
    )


def llms_txt(base: Optional[str] = None) -> str:
    """
    A markdown index for language models: what the product is, what the
    words mean, and the canonical URL for each page. The concept
    definitions are the point -- an LLM asked "what is grounded
    pre-production" can answer from this file, and that answer is where a
    citation comes from.
    """
    base = base or site_url()
    pages = "\n".join(
        f"- [{title}]({absolute(path, base)}): {desc}"
        for path, title, desc, _priority in PUBLIC_PAGES
    )
    return f"""# {PRODUCT_NAME}

> {TAGLINE}

{PRODUCT_NAME} turns an idea into finished video. You describe what you
want; the studio's assistant helps write it as a scene of timed shots;
every shot renders against reference photos you attached; and nothing is
spent until you approve a price.

## How it works

1. **Projects** -- each piece of work (a client's ad, a short) keeps its
   own brief, look and memory of what was picked and passed over.
2. **Elements** -- upload photos of your characters, products and places.
   The studio draws a reference sheet for each, so a face or a product
   stays the same from shot to shot.
3. **Scenes** -- a scene is written as timed shots, (0-3s), (3-7s) and
   so on, each rendered as its own clip and joined in order.
4. **Your photos, always** -- a scene renders only against photos you
   attached; one with no photos never reaches the render queue.
5. **The price first** -- every render, still and effect is quoted in
   credits before it runs. Credit is held when you approve and released
   if the render fails.
6. **Finish** -- effects (upscale, reframe, camera moves, sound, background
   removal) and a timeline editor with captions, transitions and export.

## Capabilities

- Video on Kling, LTX, Wan, Seedance and Veo; stills on FLUX, Nano Banana
  Pro, Seedream, GPT Image and Ideogram -- one studio, one balance.
- Character, product and place reference sheets drawn from your photos.
- Scenes of several timed shots, rendered shot by shot with continuity.
- A quote in credits before every spend, and holds released on failure.
- Effects and finishing: image edits, template effects, camera moves,
  upscaling, frame interpolation, sound, video background removal.
- A timeline editor: trim, split, speed, keyframes, grading, captions,
  mixer, export to MP4, audio, still or an editable OpenTimelineIO project.
- A connector for Claude and ChatGPT: plan scenes with your own photos in
  the chat and send them to the studio to render.

## Pages

{pages}

## Attribution

Built by Michael Massaad, a filmmaker and editor, for Zero Page.
"""


def homepage_schema(base: Optional[str] = None) -> dict:
    """
    The homepage @graph: who publishes this, what site it is, and what the
    software does. Only things actually on the page are marked up, and
    there is no Offer -- nothing is for sale yet, and inventing a price in
    schema is the kind of thing that costs you a rich result.
    """
    base = base or site_url()
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{base}/#org",
                "name": PRODUCT_NAME,
                "url": f"{base}/",
                "description": TAGLINE,
                "founder": {"@type": "Person", "name": "Michael Massaad"},
            },
            {
                "@type": "WebSite",
                "@id": f"{base}/#site",
                "url": f"{base}/",
                "name": PRODUCT_NAME,
                "publisher": {"@id": f"{base}/#org"},
                "inLanguage": "en",
            },
            {
                "@type": "SoftwareApplication",
                "@id": f"{base}/#app",
                "name": PRODUCT_NAME,
                "url": f"{base}/",
                "applicationCategory": "MultimediaApplication",
                "operatingSystem": "Web",
                "description": TAGLINE,
                "publisher": {"@id": f"{base}/#org"},
                "featureList": [
                    "Vision-described shooting locations",
                    "Concepts mixing real and AI-generated shots",
                    "AI video prompts for Runway, Veo, Kling, Seedance, LTX, and Wan, "
                    "anchored by Midjourney reference stills",
                    "Cut plans built from ingested real footage",
                    "Retrieval-grounded reference library",
                    "Performance analytics that ground the next slate",
                ],
            },
        ],
    }


def homepage_schema_json(base: Optional[str] = None) -> str:
    return json.dumps(homepage_schema(base), indent=2, ensure_ascii=False)
