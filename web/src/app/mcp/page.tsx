import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, Sparkles } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { LEGAL_CONTACT as SUPPORT_EMAIL } from "@/components/legal-page";
import { Aurora } from "@/components/mcp/aurora";
import { UseCases, type UseCase } from "@/components/mcp/use-cases";
import { SetupTabs, type SetupTab } from "@/components/mcp/setup-tabs";
import { FaqSection } from "@/landing-pages/components/faq-section";
import { SectionTitle } from "@/landing-pages/components/section-title";
import { pagesIn, makePath } from "@/landing-pages/pages";
import { IMAGE_MODELS, pageLabel } from "@/landing-pages/shared";
import { MODELS } from "@/lib/catalog";
import { CLAUDE_CONNECTORS_URL, CONNECTOR_NAME } from "@/lib/connect-claude";
import { pageMeta } from "@/lib/page-meta";
import { REVEAL_CLASS as REVEAL } from "@/lib/motion";

// The MCP server and Claude plugin page (2026-10-12, Mike: "rework the
// landing page for the mcp connector"). It replaced /connector, which now
// redirects here (next.config.ts), so the documentation URL both directory
// submissions carry keeps working. Laid out after higgsfield.ai/mcp and
// runway.com/mcp: a hero, setup tabs per client with real screenshots, prompts
// to try, the models, the two addresses, the FAQ.
//
// Mike's calls that day: this is an AI image and video generator, so the page
// does not talk about reference photos; the contact is the support address,
// never a personal one.
//
// Checked against the code that day:
// - the addresses: fly.toml PHANTRA_MCP_RESOURCE (/mcp) and + "/claude"
//   (app/mcp_auth.CLAUDE_SUFFIX); /mcp draws stills (generate_image) and
//   renders (approve) after a quote; /mcp/claude writes and prices, and its
//   quote hands back the scene's studio link where the render is approved
//   (docs/directory/TWO_LISTINGS.md)
// - reformat / trim_clip / assemble_clips / library / share_link are free and
//   on both addresses; balance / credit_history / recommend_model read only
// - the screenshots under public/mcp/ were taken in Mike's own Chrome on
//   2026-10-12: claude.ai's Add custom connector dialog (filled, not saved),
//   his connected Phantra connector, and ChatGPT's Plugins page
// - the plugin: github.com/zeropage-onryo/phantra-claude-plugin (MIT, the
//   connector plus 22 skills, per its README that day)
// - model names come off the catalog and the image list, never typed; no
//   price is printed here.
const ORIGIN = "https://api.phantra.ai";
const RENDER_ADDRESS = `${ORIGIN}/mcp`;
const PLUGIN_URL = "https://github.com/zeropage-onryo/phantra-claude-plugin";
const CHATGPT_PLUGINS_URL = "https://chatgpt.com/plugins";
const CHATGPT_HELP_URL = "https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt";

export const metadata: Metadata = pageMeta({
  title: "MCP Server for Claude and ChatGPT",
  description:
    "Phantra's MCP server and Claude plugin: generate AI images and video from Claude, ChatGPT, Claude Code or Cursor. See the price in credits, say yes, and it lands in your library.",
  path: "/mcp",
});

const CLIENTS = ["Claude", "ChatGPT", "Claude Code", "Cursor", "Any MCP client"];

const TABS: SetupTab[] = [
  {
    id: "claude",
    label: "Claude",
    title: "Add it to Claude",
    intro: (
      <p>
        Works in Claude on the web, the desktop app and the phone once it is added to your account. Claude draws
        stills and renders video itself: it shows you the price in credits first and waits for your yes.
      </p>
    ),
    copy: [{ label: "Address", value: RENDER_ADDRESS }],
    steps: [
      <>
        Open claude.ai, then <strong>Customize</strong> → <strong>Connectors</strong> → <strong>Add</strong> →{" "}
        <strong>Add custom connector</strong>.
      </>,
      <>
        Name it {CONNECTOR_NAME}, paste the address above and press <strong>Continue</strong>.
      </>,
      <>
        Sign in with your Phantra account. The studio&apos;s page names the app asking for access; press{" "}
        <strong>Allow</strong>.
      </>,
      <>Start a chat and ask for an image or a video.</>,
    ],
    chat: {
      label: "Open Claude with the setup",
      href: `https://claude.ai/new?q=${encodeURIComponent(`Help me add a custom connector named ${CONNECTOR_NAME} with this address: ${RENDER_ADDRESS}`)}`,
    },
    action: { label: "Open Claude connectors", href: CLAUDE_CONNECTORS_URL },
    shots: [
      {
        src: "/mcp/claude-add.png",
        alt: "Claude's Add custom connector dialog with the name Phantra and the address api.phantra.ai/mcp filled in",
        width: 834,
        height: 700,
        caption: "Step 2: the name and the address in Claude's Add custom connector dialog.",
      },
      {
        src: "/mcp/claude-connected.png",
        alt: "The connected Phantra connector in Claude, showing its address and tool permissions",
        width: 1170,
        height: 600,
        caption: "Connected: the connector's page in Claude, where you choose which tools need your approval.",
      },
    ],
  },
  {
    id: "chatgpt",
    label: "ChatGPT",
    title: "Add it to ChatGPT",
    intro: (
      <p>
        In ChatGPT the chat can draw stills and render video itself: it shows you the price in credits first and
        waits for your yes. Phantra is in review for ChatGPT&apos;s plugin directory; until it is listed, add it by
        address.
      </p>
    ),
    copy: [{ label: "Address", value: RENDER_ADDRESS }],
    steps: [
      <>
        In ChatGPT, open <strong>Settings</strong> → <strong>Plugins</strong>.
      </>,
      <>
        Turn on <strong>Developer mode</strong> (on paid plans), then choose <strong>Create</strong>.
      </>,
      <>
        Name it {CONNECTOR_NAME}, paste the address above and sign in with your Phantra account.
      </>,
      <>In a new chat, pick Phantra from the + menu and ask for an image or a video.</>,
    ],
    chat: {
      label: "Open ChatGPT with the setup",
      href: `https://chatgpt.com/?q=${encodeURIComponent(`Help me add an MCP server named ${CONNECTOR_NAME} with this address: ${RENDER_ADDRESS}`)}`,
    },
    action: { label: "Open ChatGPT plugins", href: CHATGPT_PLUGINS_URL },
    note: (
      <>
        ChatGPT moves its menus now and then. OpenAI&apos;s own steps are in{" "}
        <a href={CHATGPT_HELP_URL} target="_blank" rel="noopener noreferrer">
          its help center
        </a>
        .
      </>
    ),
    shots: [
      {
        src: "/mcp/chatgpt-plugins.png",
        alt: "ChatGPT's Plugins page with its search box and installed plugins",
        width: 982,
        height: 350,
        caption: "Step 1: ChatGPT's Plugins page.",
      },
    ],
  },
  {
    id: "claude-code",
    label: "Claude Code",
    title: "Add it to Claude Code",
    intro: <p>One command in your terminal, then sign in once from inside Claude Code.</p>,
    copy: [{ label: "Command", value: `claude mcp add --transport http phantra-ai ${RENDER_ADDRESS}` }],
    steps: [
      <>Run the command above.</>,
      <>
        Start Claude Code, type <code>/mcp</code>, pick <strong>phantra-ai</strong> and choose{" "}
        <strong>Authenticate</strong>.
      </>,
      <>Sign in with your Phantra account in the browser window that opens, and press Allow.</>,
    ],
  },
  {
    id: "other",
    label: "Cursor & others",
    title: "Any other MCP client",
    intro: (
      <p>
        Phantra is a remote MCP server over streamable HTTP with OAuth sign-in. Any client that adds a server by
        address can use it. In Cursor, add this to <code className="font-mono text-[14px]">~/.cursor/mcp.json</code>:
      </p>
    ),
    copy: [
      { label: "Address", value: RENDER_ADDRESS },
      {
        label: "Cursor mcp.json",
        value: `{\n  "mcpServers": {\n    "phantra-ai": { "url": "${RENDER_ADDRESS}" }\n  }\n}`,
        multiline: true,
      },
    ],
    steps: [
      <>Add the server with the address above.</>,
      <>When the client asks, sign in with your Phantra account and press Allow.</>,
    ],
  },
  {
    id: "plugin",
    label: "Claude plugin",
    title: "The Phantra plugin for Claude",
    intro: (
      <p>
        The plugin bundles the connector with 22 skills that teach Claude how to plan with the studio: storyboards,
        ad variations, product shots, camera moves, UGC ads, explainers, hooks and the edit. Free and open source
        (MIT).
      </p>
    ),
    steps: [
      <>
        Get the plugin from GitHub. Its README says how to add it to Claude.
      </>,
      <>
        On the plugin&apos;s Connectors tab, connect {CONNECTOR_NAME} and sign in with your Phantra account.
      </>,
      <>Ask Claude for a storyboard, an ad or a product shot; the skills load as they are needed.</>,
    ],
    action: { label: "Get the plugin on GitHub", href: PLUGIN_URL },
  },
];

// Every card's picture is a real output of its own prompt, drawn on the studio
// 2026-10-15 and kept under public/mcp/examples/. Clips are played from the
// bucket (site/mcp/examples/<name>.mp4, see UseCases); the poster beside each
// is a frame of the clip.
const EX = "/mcp/examples";
const USE_CASES: UseCase[] = [
  {
    title: "A fashion editorial",
    group: "Images",
    src: `${EX}/fashion-tokyo.jpg`,
    aspect: "4/5",
    prompt:
      "Using Phantra, draw a fashion editorial: a woman in a red trench coat crossing a rain-slick Tokyo crosswalk at dusk, neon signs reflecting on the wet street, shallow depth of field, shot on 85mm. Show me the price first.",
  },
  {
    title: "A logo on a real storefront",
    group: "Images",
    src: `${EX}/logo-kuma-ramen.jpg`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a logo and a noren curtain for a ramen shop called KUMA RAMEN: a simple white bear-head mark above the name in bold clean lettering, hanging in a wooden shop doorway in evening light.",
  },
  {
    title: "Food photography",
    group: "Images",
    src: `${EX}/food-pancakes.jpg`,
    aspect: "4/5",
    prompt:
      "Using Phantra, draw a tall stack of fluffy blueberry pancakes with maple syrup mid-pour and a pat of melting butter, soft window light, crumbs and berries on a linen cloth.",
  },
  {
    title: "A storybook illustration",
    group: "Images",
    src: `${EX}/illustration-fox.jpg`,
    aspect: "4/5",
    prompt:
      "Using Phantra, paint a children's-book watercolor of a small orange fox carrying a paper lantern through a quiet blue forest at night, fireflies, soft washes, hand-painted texture.",
  },
  {
    title: "An interior for a listing",
    group: "Images",
    src: `${EX}/interior-living-room.jpg`,
    aspect: "16/9",
    prompt:
      "Using Phantra, draw a sunlit Scandinavian living room: a linen sofa, a pale oak coffee table with one ceramic vase of dried grass, a big window with sheer curtains, soft morning light, as an interior design photograph.",
  },
  {
    title: "A drone shot of a breaching whale",
    group: "Video",
    src: `${EX}/video-whale.jpg`,
    video: `${EX}/video-whale.mp4`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a 5-second drone follow shot of a humpback whale breaching out of a calm sea at sunrise, a huge spray of water, golden light. Render it on Kling and tell me the price first.",
  },
  {
    title: "A night market, with the sound",
    group: "Video",
    src: `${EX}/video-wok.jpg`,
    video: `${EX}/video-wok.mp4`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a 4-second handheld close shot of a street-food vendor flipping noodles in a flaming wok at a night market, with the sizzle and clatter of the wok. Which model, and what does it cost?",
  },
  {
    title: "Slow motion sport",
    group: "Video",
    src: `${EX}/video-skate.jpg`,
    video: `${EX}/video-skate.mp4`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a slow-motion shot of a skateboarder landing a kickflip at an empty skatepark at golden hour, dust lifting from the concrete, low tracking camera.",
  },
  {
    title: "A cinematic street at night",
    group: "Video",
    src: `${EX}/video-cat.jpg`,
    video: `${EX}/video-cat.mp4`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a cinematic 4-second shot of a grey cat walking under a shop awning on a neon-lit street in the rain, reflections on the pavement, with rain sound.",
  },
  {
    title: "Macro, in slow motion",
    group: "Video",
    src: `${EX}/video-milk.jpg`,
    video: `${EX}/video-milk.mp4`,
    aspect: "4/5",
    prompt:
      "Using Phantra, make a macro slow-motion shot of a single drop of milk falling into black coffee and blooming into a crown, then settling into swirling cream, extreme close-up on a dark background.",
  },
];

// One still per model page, each that model's own output (the entries'
// comments say where each was rendered).
const SHOWCASE: { slug: string; src: string }[] = [
  { slug: "gpt-image-generator", src: "/models/gpt-image-generator/volt.jpg" },
  { slug: "seedance-video-generator", src: "/models/seedance-video-generator/sig-cup.jpg" },
  { slug: "ideogram-image-generator", src: "/models/ideogram-image-generator/jazz.jpg" },
  { slug: "kling-video-generator", src: "/models/kling-video-generator/boxer.jpg" },
  { slug: "nano-banana-image-generator", src: "/models/nano-banana-image-generator/sunflower.jpg" },
  { slug: "veo-video-generator", src: "/models/veo-video-generator/trumpet.jpg" },
  { slug: "seedream-image-generator", src: "/models/seedream-image-generator/flamingo.jpg" },
  { slug: "wan-video-generator", src: "/models/wan-video-generator/flamenco.jpg" },
];
const MODEL_PAGES = pagesIn("models");
const SHOWCASE_TILES = SHOWCASE.flatMap(({ slug, src }) => {
  const page = MODEL_PAGES.find((p) => p.slug === slug);
  return page ? [{ src, href: makePath(page), name: pageLabel(page), video: page.slug.includes("video") }] : [];
});

const SAFE = [
  {
    title: "A price before anything spends",
    body: "Every image and video is quoted in credits first, and the chat is told to show you that price and wait for your yes.",
  },
  {
    title: "Held, then charged",
    body: "Credits are held when a render starts and released if it fails. What you spend is in your studio's usage page, line by line.",
  },
  {
    title: "Your workspace only",
    body: "You sign in on Phantra's own page and the chat app gets access to your workspace and nothing else. It never sees your password.",
  },
];

const FAQS = [
  {
    q: "What is the Phantra MCP server?",
    a: "A way to use Phantra from inside the chat apps you already use. Add it to Claude, ChatGPT, Claude Code or Cursor, then ask for an image or a video in plain words. The chat picks the model, shows you the price in credits, and the result lands in your Phantra library.",
  },
  {
    q: "Which apps does it work with?",
    a: "Claude on the web, desktop and phone, Claude Code, ChatGPT, Cursor, and any other app that adds a remote MCP server by its address and signs in with OAuth.",
  },
  {
    q: "Do I need a Phantra account?",
    a: "Yes. Sign in once at phantra.ai to create your workspace; a new workspace comes with a one-time trial of credits. Then add the connector and sign in with the same account.",
  },
  {
    q: "Which models can I use?",
    a: `The studio's video models (${MODELS.map((m) => m.name).join(", ")}) and image models (${IMAGE_MODELS.map((m) => m.label).join(", ")}). Ask the chat which one suits the job.`,
  },
  {
    q: "What does it cost?",
    a: "Adding the connector, planning, pricing and the free edits (reformat, trim, join, download links) cost nothing. Images and video spend credits from your studio balance, at the price the chat showed you.",
    link: { href: "/pricing", label: "See plans and credits" },
  },
  {
    q: "Where does my work go?",
    a: "Every still and clip is saved to your Phantra library with the prompt and the model that made it, and you can open it in the studio or ask the chat for a download link.",
  },
  {
    q: "How do I disconnect?",
    a: `Remove ${CONNECTOR_NAME} where you added it. In Claude that is Customize, then Connectors; in ChatGPT, Settings, then Plugins.`,
  },
  {
    q: "Who do I contact for help?",
    a: `Email ${SUPPORT_EMAIL}. Bugs in the plugin can also be filed on its GitHub page.`,
  },
];

const FAQ_JSON_LD = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQS.map((item) => ({
    "@type": "Question",
    name: item.q,
    acceptedAnswer: { "@type": "Answer", text: item.a },
  })),
};

export default function McpPage() {
  return (
    <EditorialSkin tone="dark">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD).replace(/</g, "\\u003c") }}
      />
      <SiteHeader />
      <main className="flex-1">
        {/* HERO */}
        <section className="relative isolate overflow-hidden pt-[60px]">
          <Aurora />
          <div className="mx-auto grid max-w-[1200px] items-center gap-14 px-4 pb-20 pt-12 md:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr]">
            <div className="flex flex-col items-start">
              <h1
                className={`serif serif-bold text-[clamp(2.5rem,6.5vw,5rem)] leading-[1.02] ${REVEAL} motion-safe:duration-700`}
              >
                Phantra MCP
              </h1>
              <p
                className={`mt-5 max-w-[14ch] text-[clamp(1.75rem,4vw,3rem)] font-semibold leading-[1.08] tracking-[-0.02em] text-foreground ${REVEAL} motion-safe:duration-700 motion-safe:delay-100`}
              >
                AI images and video inside your chat.
              </p>
              <p
                className={`mt-6 max-w-[40ch] text-[clamp(1rem,1.5vw,1.125rem)] leading-normal text-[var(--ink-2)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-150`}
              >
                Use Phantra in ChatGPT, Claude, and other compatible agents.
              </p>
              <div className={`mt-9 flex w-full flex-col gap-3 sm:w-auto sm:flex-row ${REVEAL} motion-safe:duration-700 motion-safe:delay-200`}>
                <a
                  href="#claude"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-6 text-[15px] font-semibold text-[var(--primary-foreground)] transition-opacity hover:opacity-90"
                >
                  Connect to Claude
                  <ArrowRight className="size-4" aria-hidden />
                </a>
                <a
                  href="#chatgpt"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-border bg-background px-6 text-[15px] font-semibold text-foreground transition-colors hover:bg-secondary"
                >
                  Connect to ChatGPT
                </a>
              </div>
              <ul className="mt-9 flex flex-wrap items-center gap-2" aria-label="Works with">
                {CLIENTS.map((c) => (
                  <li key={c} className="rounded-full border border-border px-3 py-1 text-[13px] text-[var(--ink-2)]">
                    {c}
                  </li>
                ))}
              </ul>
            </div>

            {/* An illustration of the flow, drawn here: a request, the quote, the still. */}
            <div className={`relative mx-auto w-full max-w-[480px] ${REVEAL} motion-safe:duration-1000 motion-safe:delay-150`} aria-hidden>
              <div className="rounded-[28px] border border-border bg-card p-4 shadow-[0_40px_90px_-40px_rgba(0,0,0,0.35)] sm:p-5">
                <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-foreground px-4 py-3 text-[14px] leading-snug text-background">
                  Draw a 4:5 poster for my energy drink VOLT bursting out of fresh snow.
                </div>
                <div className="mt-4 flex items-start gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-white">
                    <Sparkles className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[14px] leading-snug text-foreground">
                      Here it is, drawn on {pageLabel(MODEL_PAGES.find((p) => p.slug === "gpt-image-generator")!)} and
                      saved to your library.
                    </p>
                    <div className="relative mt-3 aspect-[4/5] overflow-hidden rounded-2xl bg-secondary">
                      <Image
                        src="/models/gpt-image-generator/volt.jpg"
                        alt=""
                        fill
                        priority
                        sizes="(min-width: 1024px) 400px, 80vw"
                        quality={75}
                        className="object-cover"
                      />
                      <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-[12px] font-medium text-white backdrop-blur-md">
                        <Check className="size-3.5" /> Approved · in your library
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SETUP */}
        <section id="setup" className="relative scroll-mt-20 border-t border-white/10">
          {TABS.map((t) => (
            <span key={t.id} id={t.id} aria-hidden className="absolute top-0 block scroll-mt-20" />
          ))}
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Connect in a minute</SectionTitle>
            <p className="mx-auto mt-5 max-w-[52ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              You need a Phantra account first.{" "}
              <Link href="/studio" className="text-foreground underline underline-offset-4">
                Sign in once
              </Link>{" "}
              to create your workspace, then pick where you work.
            </p>
            <div className="mt-12">
              <SetupTabs tabs={TABS} />
            </div>
          </div>
        </section>

        {/* WHAT YOU CAN DO */}
        <section id="examples" className="scroll-mt-20 border-t border-white/10">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Everything you can ask for</SectionTitle>
            <p className="mx-auto mt-5 mb-12 max-w-[56ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              Images and video, drawn from the chat. Open one in ChatGPT or Claude with the
              prompt typed in, or copy it.
            </p>
            <UseCases items={USE_CASES} />
          </div>
        </section>

        {/* MODELS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <h2 className="display flex flex-wrap items-center justify-center gap-x-[0.3em] text-center text-[clamp(2.25rem,6.4vw,5rem)] text-foreground">
              Every creative model, inside
              <span className="inline-flex items-center gap-[0.2em]">
                <svg viewBox="0 0 24 24" aria-hidden className="size-[0.85em] fill-current">
                  <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z" />
                </svg>
                ChatGPT
              </span>
            </h2>
            <div className="mt-12 grid grid-cols-2 gap-3 md:grid-cols-4">
              {SHOWCASE_TILES.map((t) => (
                <Link
                  key={t.href}
                  href={t.href}
                  className="group relative aspect-[4/5] overflow-hidden rounded-2xl bg-secondary outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--primary)]"
                >
                  <Image
                    src={t.src}
                    alt={`Made with ${t.name}`}
                    fill
                    sizes="(min-width: 768px) 290px, 46vw"
                    quality={70}
                    className="object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                  />
                  <span className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 bg-gradient-to-t from-black/70 to-transparent p-3 pt-10 text-white">
                    <span className="text-[14px] font-semibold">{t.name}</span>
                    <span className="rounded-full bg-white/20 px-2 py-0.5 text-[11px] font-medium backdrop-blur-md">
                      {t.video ? "Video" : "Image"}
                    </span>
                  </span>
                </Link>
              ))}
            </div>
            <div className="mt-8 text-center">
              <Link href="/models" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-foreground hover:opacity-70">
                See every model <ArrowRight className="size-4" aria-hidden />
              </Link>
            </div>
          </div>
        </section>

        {/* SAFE */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Price first, always</SectionTitle>
            <div className="mt-12 grid gap-4 md:grid-cols-3">
              {SAFE.map((s) => (
                <article key={s.title} className="rounded-2xl border border-border bg-card p-6">
                  <h3 className="text-[18px] font-semibold tracking-[-0.01em] text-foreground">{s.title}</h3>
                  <p className="mt-3 text-[15px] leading-relaxed text-[var(--ink-2)]">{s.body}</p>
                </article>
              ))}
            </div>
            <p className="mx-auto mt-8 max-w-[64ch] text-center text-[14px] leading-relaxed text-[var(--ink-3)]">
              What the connector reads and records is in the{" "}
              <Link href="/privacy" className="underline underline-offset-4">
                privacy policy
              </Link>
              ; the{" "}
              <Link href="/terms" className="underline underline-offset-4">
                terms
              </Link>{" "}
              cover the studio it reaches.
            </p>
          </div>
        </section>

        <FaqSection title="MCP questions" items={FAQS} />

        {/* FINAL */}
        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[760px] flex-col items-center gap-7 px-4 py-24 text-center md:px-6 md:py-32">
            <span className="eyebrow">Get started</span>
            <h2 className="serif text-[clamp(2.25rem,5.5vw,4rem)]">Make it from the chat you already use.</h2>
            <div className="flex w-full flex-col justify-center gap-3 sm:w-auto sm:flex-row">
              <a
                href="#claude"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-6 text-[15px] font-semibold text-[var(--primary-foreground)] transition-opacity hover:opacity-90"
              >
                Connect to Claude <ArrowRight className="size-4" aria-hidden />
              </a>
              <a
                href={PLUGIN_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-border bg-background px-6 text-[15px] font-semibold text-foreground transition-colors hover:bg-secondary"
              >
                Get the Claude plugin <ArrowUpRight className="size-4" aria-hidden />
              </a>
            </div>
            <p className="text-[15px] text-[var(--ink-2)]">
              Questions?{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`} className="text-foreground underline underline-offset-4">
                {SUPPORT_EMAIL}
              </a>
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
