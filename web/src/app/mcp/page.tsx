import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, Sparkles } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { SUPPORT_EMAIL } from "@/components/legal-page";
import { CopyButton, CopyField } from "@/components/mcp/copy-field";
import { SetupTabs, type SetupTab } from "@/components/mcp/setup-tabs";
import { FaqSection } from "@/landing-pages/components/faq-section";
import { SectionTitle } from "@/landing-pages/components/section-title";
import { RED, accentVars } from "@/landing-pages/theme";
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
const CLAUDE_ADDRESS = `${ORIGIN}/mcp/claude`;
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
        Works in Claude on the web, the desktop app and the phone once it is added to your account. Claude writes
        the shot and prices it, and you approve the render in your studio with one click.
      </p>
    ),
    copy: [{ label: "Claude address", value: CLAUDE_ADDRESS }],
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
    action: { label: "Open Claude connectors", href: CLAUDE_CONNECTORS_URL },
    shots: [
      {
        src: "/mcp/claude-add.png",
        alt: "Claude's Add custom connector dialog with the name Phantra and the address api.phantra.ai/mcp/claude filled in",
        width: 536,
        height: 449,
        caption: "Step 2: the name and the address in Claude's Add custom connector dialog.",
      },
      {
        src: "/mcp/claude-connected.png",
        alt: "The connected Phantra connector in Claude, showing its address and tool permissions",
        width: 990,
        height: 340,
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
    copy: [{ label: "ChatGPT address", value: RENDER_ADDRESS }],
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

const PROMPTS: { title: string; prompt: string; tag: string }[] = [
  {
    title: "Draw a poster",
    prompt:
      "Draw a 4:5 poster for an energy drink called VOLT: the can bursting out of fresh snow, the headline \"Charge the drop\". Show me the price first.",
    tag: "Image",
  },
  {
    title: "Make a product ad",
    prompt:
      "Write a 10-second ad for my coffee bag in three shots, render it on Kling, and tell me what it costs before you start.",
    tag: "Video",
  },
  {
    title: "Pick the right model",
    prompt: "Which video model should I use for a 6-second product spin, with sound, under 200 credits?",
    tag: "Advice",
  },
  {
    title: "Make it vertical",
    prompt: "Make my last clip 9:16 for Reels and give me a download link.",
    tag: "Free",
  },
  {
    title: "Cut it together",
    prompt: "Join my last three clips into one video with a short crossfade between them.",
    tag: "Free",
  },
  {
    title: "Check my credits",
    prompt: "How many credits do I have left, and what did I spend them on this week?",
    tag: "Account",
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

const ADDRESSES = [
  {
    name: "Claude",
    address: CLAUDE_ADDRESS,
    points: [
      "Writes the shot and prices it in credits",
      "You approve the render in your studio with one click",
      "Free edits: reformat, trim, join, download links",
    ],
  },
  {
    name: "ChatGPT, Claude Code, Cursor and others",
    address: RENDER_ADDRESS,
    points: [
      "Draws stills and renders video in the chat",
      "Shows the price first and waits for your yes",
      "Free edits: reformat, trim, join, download links",
    ],
  },
];

const SAFE = [
  {
    title: "A price before anything spends",
    body: "Every image and video is quoted in credits first, and the chat is told to show you that price and wait for your yes. In Claude, the render is approved in your studio instead.",
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
    q: "Why are there two addresses?",
    a: `Claude's connector directory does not list connectors that generate media in the chat, so the Claude address (${CLAUDE_ADDRESS}) writes and prices your shot, and you approve the render in your studio. The other address (${RENDER_ADDRESS}) draws and renders in the chat after your yes, for ChatGPT and other clients.`,
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
    <EditorialSkin tone="light" style={accentVars(RED)}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD).replace(/</g, "\\u003c") }}
      />
      <SiteHeader />
      <main className="flex-1">
        {/* HERO */}
        <section className="relative overflow-hidden pt-[60px]">
          <div className="mx-auto grid max-w-[1200px] items-center gap-14 px-4 pb-20 pt-12 md:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr]">
            <div className="flex flex-col items-start">
              <span className={`eyebrow ${REVEAL} motion-safe:duration-700`}>MCP server · Claude plugin</span>
              <h1
                className={`serif serif-bold mt-5 max-w-[12ch] text-[clamp(2.75rem,7vw,5.75rem)] ${REVEAL} motion-safe:duration-700`}
              >
                AI images and video, inside your chat.
              </h1>
              <p
                className={`mt-7 max-w-[46ch] text-[clamp(1rem,1.5vw,1.125rem)] leading-normal text-[var(--ink-2)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-100`}
              >
                Connect Phantra to Claude, ChatGPT or any MCP client. Ask for a still or a video in plain words, see
                the price in credits, say yes, and it lands in your library.
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
        <section id="setup" className="relative scroll-mt-20 border-t border-border">
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

        {/* PROMPTS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Things to ask for</SectionTitle>
            <p className="mx-auto mt-5 max-w-[50ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              Copy one into your chat once Phantra is connected.
            </p>
            <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {PROMPTS.map((p) => (
                <article key={p.title} className="flex flex-col rounded-2xl border border-[var(--card-line)] bg-card p-6">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-[18px] font-semibold tracking-[-0.01em] text-foreground">{p.title}</h3>
                    <span className="rounded-full bg-secondary px-2.5 py-1 text-[12px] font-medium text-[var(--ink-2)]">{p.tag}</span>
                  </div>
                  <p className="serif mt-4 flex-1 text-[19px] leading-snug text-foreground">&ldquo;{p.prompt}&rdquo;</p>
                  <div className="mt-6">
                    <CopyButton value={p.prompt} />
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* MODELS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Every model, one connector</SectionTitle>
            <p className="mx-auto mt-5 max-w-[56ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              {MODELS.length} video models and {IMAGE_MODELS.length} image models, priced in the same credits. Each still
              below is that model&apos;s own work.
            </p>
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

        {/* ADDRESSES */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Two addresses</SectionTitle>
            <p className="mx-auto mt-5 max-w-[56ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              Both reach the same studio, projects and library. They differ in where a render is approved.
            </p>
            <div className="mt-12 grid gap-4 md:grid-cols-2">
              {ADDRESSES.map((a) => (
                <article key={a.address} className="flex flex-col rounded-2xl border border-[var(--card-line)] bg-card p-6 md:p-8">
                  <h3 className="serif text-[1.75rem] leading-tight">{a.name}</h3>
                  <div className="mt-5">
                    <CopyField value={a.address} label="Address" />
                  </div>
                  <ul className="mt-6 flex flex-col gap-3">
                    {a.points.map((pt) => (
                      <li key={pt} className="flex gap-3 text-[15.5px] leading-snug text-foreground">
                        <Check className="mt-0.5 size-4 shrink-0 text-[var(--primary)]" aria-hidden />
                        {pt}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
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
