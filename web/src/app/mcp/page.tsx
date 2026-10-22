import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { LEGAL_CONTACT as SUPPORT_EMAIL } from "@/components/legal-page";
import { ParticleMorph } from "@/components/mcp/particle-morph";
import { McpClientProvider } from "@/components/mcp/client-context";
import { HeroConnect, type HeroClient, type HowStep } from "@/components/mcp/hero-connect";
import { CopyField } from "@/components/mcp/copy-field";
import { SetupTabs, type SetupTab } from "@/components/mcp/setup-tabs";
import { ToolList, toolCount, type ToolGroup } from "@/components/mcp/tool-list";
import { UseCases, type UseCase } from "@/components/mcp/use-cases";
import { FaqSection } from "@/landing-pages/components/faq-section";
import { SectionTitle } from "@/landing-pages/components/section-title";
import { pagesIn, makePath } from "@/landing-pages/pages";
import { IMAGE_MODELS, pageLabel } from "@/landing-pages/shared";
import { MODELS } from "@/lib/catalog";
import { CONNECTOR_NAME } from "@/lib/connect-claude";
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


// The hero's one button per client, in that client's colours, and the steps its
// "How to connect?" modal shows. Since 2026-10-16 this is the page's only setup
// (the "Connect in a minute" tabs were removed, Mike's call), and ChatGPT is the
// pill the page opens on (it comes first here, and McpClientProvider takes these
// ids). Claude's button opens claude.ai's Add custom connector dialog with the
// name and address already filled in (claude.ai reads `connectorName` and
// `connectorUrl`; found on higgsfield.ai/mcp 2026-10-16). ChatGPT's cannot be
// opened filled in: its "Add custom MCP server" dialog lives at chatgpt.com/plugins
// with no URL of its own and reads no URL parameters (checked in a real session,
// 2026-10-16). So the ChatGPT button opens that page AND copies the address in
// the same click.
// TODO: once the ChatGPT directory listing is approved, point the ChatGPT button
// at `https://chatgpt.com/plugins/<slug>?open_in_app=1` (a one-click install, the
// way higgsfield.ai/mcp does it) and drop `copyAlso`.
const START_PROMPT = "Using Phantra, draw me a poster for a coffee brand and show me the price first.";
const CLAUDE_ADD = `https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=${encodeURIComponent(CONNECTOR_NAME)}&connectorUrl=${encodeURIComponent(RENDER_ADDRESS)}`;
const CLAUDE_START = `https://claude.ai/new?q=${encodeURIComponent(START_PROMPT)}`;
const CHATGPT_START = `https://chatgpt.com/?q=${encodeURIComponent(START_PROMPT)}`;
const CLAUDE_CODE_COMMAND = `claude mcp add --transport http phantra-ai ${RENDER_ADDRESS}`;
const CURSOR_CONFIG = `{\n  "mcpServers": {\n    "phantra-ai": { "url": "${RENDER_ADDRESS}" }\n  }\n}`;
const CLAUDE_TONE = { bg: "#d97757", fg: "#ffffff", edge: "#a4573d" };
const WHITE_TONE = { bg: "#ffffff", fg: "#0d0d0d", edge: "rgba(255,255,255,0.3)" };
const CURSOR_TONE = { bg: "#f2f1ed", fg: "#14120b", edge: "rgba(242,241,237,0.3)" };

const HERO_CLIENTS: HeroClient[] = [
  {
    id: "chatgpt",
    label: "ChatGPT",
    button: {
      label: "Connect Phantra",
      href: CHATGPT_PLUGINS_URL,
      copyAlso: RENDER_ADDRESS,
      copiedHint: "Paste it in ChatGPT: Add → Add custom MCP server",
      logo: "openai",
      ...WHITE_TONE,
    },
    address: RENDER_ADDRESS,
    how: {
      title: "Connect Phantra to ChatGPT in under a minute",
      steps: [
        {
          title: "Log in to ChatGPT in your browser",
          body: "Go to chatgpt.com and log in. You also need a Phantra account: sign in once at phantra.ai to create your workspace.",
          link: { label: "Open ChatGPT", href: "https://chatgpt.com" },
        },
        {
          title: "Add Phantra and sign in",
          body: `Open chatgpt.com/plugins, press Add and choose Add custom MCP server. Name it ${CONNECTOR_NAME}, paste this address: ${RENDER_ADDRESS}, and sign in with your Phantra account. The button below opens the page and copies the address for you. Custom MCP servers depend on your ChatGPT plan and workspace settings; if you don't see Add, your plan doesn't allow them yet.`,
          link: { label: "OpenAI's own steps", href: CHATGPT_HELP_URL },
          action: { label: "Open ChatGPT plugins", href: CHATGPT_PLUGINS_URL, copyAlso: RENDER_ADDRESS, logo: "openai" },
        },
        {
          title: "Create with Phantra in ChatGPT",
          body: "Start a new chat and describe the image or video you want. ChatGPT shows the price in credits first and waits for your yes.",
          action: { label: "Start creating", href: CHATGPT_START, logo: "openai", primary: true },
        },
      ],
    },
  },
  {
    id: "claude",
    label: "Claude",
    button: { label: "Connect Phantra", href: CLAUDE_ADD, logo: "claude", ...CLAUDE_TONE },
    address: RENDER_ADDRESS,
    how: {
      title: "Connect Phantra to Claude in under a minute",
      steps: [
        {
          title: "Log in to Claude in your browser",
          body: "Go to claude.ai and log in. You also need a Phantra account: sign in once at phantra.ai to create your workspace.",
          link: { label: "Open Claude", href: "https://claude.ai" },
        },
        {
          title: "Add Phantra and sign in",
          body: `Go to Customize, then Connectors. Add a custom connector, name it ${CONNECTOR_NAME} and paste this address: ${RENDER_ADDRESS}, or press the button below to open it filled in. Then sign in with your Phantra account and press Allow.`,
          action: { label: "Add Phantra MCP", href: CLAUDE_ADD, logo: "claude" },
        },
        {
          title: "Create with Phantra in Claude",
          body: "Start a new chat and describe the image or video you want. Claude uses Phantra to draw it and shows you the price first.",
          action: { label: "Start creating", href: CLAUDE_START, logo: "claude", primary: true },
        },
      ],
      // Mike's own screen recording, trimmed 2026-10-16 (public/mcp/how/)
      video: "/mcp/how/claude-connect.mp4",
      videoWebm: "/mcp/how/claude-connect.webm",
      poster: "/mcp/how/claude-connect-poster.jpg",
      caption:
        "Claude shows a note when a connector comes from a link. That's expected: check the name says Phantra and the address is api.phantra.ai.",
    },
  },
  {
    id: "claude-code",
    label: "Claude Code",
    button: { label: "Copy command", copy: CLAUDE_CODE_COMMAND, logo: "terminal", ...CLAUDE_TONE },
    address: CLAUDE_CODE_COMMAND,
    how: {
      title: "Connect Phantra to Claude Code in under a minute",
      steps: [
        { title: "Add the server", body: "In your terminal, run this command once.", action: { label: "Copy command", copy: CLAUDE_CODE_COMMAND, logo: "terminal" } },
        { title: "Sign in", body: "Start Claude Code, type /mcp, pick phantra-ai and choose Authenticate. Sign in with your Phantra account in the browser window that opens and press Allow." },
        { title: "Create with Phantra in Claude Code", body: "Ask for an image or a video. Claude Code shows the price in credits and waits for your yes." },
      ],
    },
  },
  {
    id: "other",
    label: "Cursor & others",
    button: { label: "Copy Cursor config", copy: CURSOR_CONFIG, logo: "cursor", ...CURSOR_TONE },
    address: RENDER_ADDRESS,
    how: {
      title: "Connect Phantra to Cursor in under a minute",
      steps: [
        { title: "Add the server", body: "Open ~/.cursor/mcp.json and add this. Any other client that adds a remote MCP server by address works with the address alone.", action: { label: "Copy Cursor config", copy: CURSOR_CONFIG, logo: "cursor" } },
        { title: "Sign in", body: "When the client asks, sign in with your Phantra account and press Allow." },
        { title: "Create with Phantra", body: "Ask for an image or a video. The client shows the price in credits and waits for your yes." },
      ],
    },
  },
  {
    id: "plugin",
    label: "Claude plugin",
    button: { label: "Get the plugin", href: PLUGIN_URL, logo: "claude", ...CLAUDE_TONE },
    address: PLUGIN_URL,
    how: {
      title: "Add the Phantra plugin to Claude in under a minute",
      steps: [
        {
          title: "Get the plugin",
          body: "It bundles the connector with 22 skills that teach Claude how to plan with the studio: storyboards, ad variations, product shots, camera moves, UGC ads, explainers, hooks and the edit. Free and open source (MIT); its README says how to add it to Claude.",
          action: { label: "Open the plugin on GitHub", href: PLUGIN_URL, logo: "claude" },
        },
        { title: "Connect Phantra", body: `On the plugin's Connectors tab, connect ${CONNECTOR_NAME} and sign in with your Phantra account.` },
        { title: "Create with the skills", body: "Ask Claude for a storyboard, an ad or a product shot. The plugin's skills load as they are needed." },
      ],
    },
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


// THE SETUP AND THE TOOLS, IN THE PAGE'S HTML (2026-10-22). The hero's "How to
// connect?" modal renders only when opened, so a reviewer's fetch of this page
// -- the documentation URL the ChatGPT listing and every MCP directory name --
// found no setup steps and no tool list (the 2026-10-22 site audit and
// directory pack both flagged it; Claude's directory requires "clear setup and
// usage instructions" at the docs URL). The section below is the SAME steps
// (`how` on HERO_CLIENTS, one tab per client, every tab in the HTML) and the
// server's listed tools. It sits after the examples and the models, because
// the hero still goes straight into the examples (Mike's call, 2026-10-16).
function stepNode(step: HowStep, i: number) {
  const a = step.action;
  return (
    <div key={i}>
      <strong>{step.title}.</strong> {step.body}
      {step.link && (
        <>
          {" "}
          <a href={step.link.href} target="_blank" rel="noopener noreferrer">
            {step.link.label}
          </a>
        </>
      )}
      {a?.copy && (
        <div className="mt-3">
          <CopyField value={a.copy} label={a.label} multiline={a.copy.includes("\n")} />
        </div>
      )}
      {a?.href && !a.copy && (
        <>
          {" "}
          <a href={a.href} target="_blank" rel="noopener noreferrer">
            {a.label}
          </a>
        </>
      )}
    </div>
  );
}
const SETUP_INTRO: Record<string, string> = {
  chatgpt: "Phantra in ChatGPT: ask for an image or a video, see the price in credits, say yes.",
  claude: "Phantra in Claude on the web, the desktop app and the phone, once it is added to your account.",
  "claude-code": "One command in your terminal, then sign in once from inside Claude Code.",
  other: "Cursor, and any client that adds a remote MCP server by its address and signs in with OAuth.",
  plugin: "The connector plus the skills that teach Claude how to plan with the studio.",
};
// The ChatGPT screenshot was taken in Mike's own Chrome on 2026-10-12 (public/mcp/);
// the Claude walkthrough is his screen recording (public/mcp/how/).
const SETUP_SHOTS: Record<string, SetupTab["shots"]> = {
  chatgpt: [
    {
      src: "/mcp/chatgpt-plugins.png",
      alt: "ChatGPT's Plugins page, where Add custom MCP server takes the Phantra address",
      width: 982,
      height: 350,
      caption: "Step 2: chatgpt.com/plugins, then Add → Add custom MCP server.",
    },
  ],
  // no still for Claude here: public/mcp/claude-add.png shows the /mcp/claude
  // address (it belongs to that page); the walkthrough video shows this one.
};
const SETUP_TABS: SetupTab[] = HERO_CLIENTS.map((c) => ({
  id: c.id,
  label: c.label,
  title: c.how.title,
  intro: <p>{SETUP_INTRO[c.id]}</p>,
  copy: c.id === "chatgpt" || c.id === "claude" ? [{ label: "Address", value: c.address }] : undefined,
  steps: c.how.steps.map(stepNode),
  action: c.button.href && !c.button.copy ? { label: c.button.label, href: c.button.href } : undefined,
  shots: SETUP_SHOTS[c.id],
  videoSrc: c.how.video
    ? { mp4: c.how.video, webm: c.how.videoWebm, poster: c.how.poster, caption: c.how.caption }
    : undefined,
}));

// The tools on api.phantra.ai/mcp, in src/mcp_server.py's LISTED_TOOLS order
// (42 on 2026-10-22), grouped by what a person asks for. A group marked
// `spends` runs only after a quote and a yes; everything else spends nothing.
const TOOLS: ToolGroup[] = [
  {
    tools: ["generate_image", "image_models"],
    does: "Draw an image from a prompt on the model you name, with your own photos as references; the image models and what each takes.",
    spends: true,
  },
  {
    tools: ["write_scene", "quote", "approve", "video_models", "recommend_model", "scene", "duplicate_scene", "job"],
    does: "Write a video scene as timed shots, price its stills and clip in credits beside your balance, render it on the model you pick; the video models and which suits a job; read a scene back, copy one with changes, check on a job.",
    spends: true,
  },
  {
    tools: ["edit_image", "remove_background", "animate_still", "camera_move", "upscale_clip", "add_sound", "reframe_clip"],
    does: "Change something already made: edit a still by instruction, cut out its background, animate it with a template or a camera move, upscale a clip, add sound to it, reframe it to a new shape.",
    spends: true,
  },
  {
    tools: ["projects", "project", "project_chat", "create_project"],
    does: "Your projects: list them, open one (brief, look, scenes, references, renders, recent chat), page its chat, start one.",
  },
  {
    tools: ["elements", "add_element", "upload_link"],
    does: "The characters, products and places a scene is held to, with their photos; add one from an image address, a product page or a render; a one-time page to upload a picture or a clip from your device.",
  },
  {
    tools: ["library", "share_link", "reformat", "trim_clip", "assemble_clips"],
    does: "What is in your library (renders and uploads); a time-limited download link; a clip or still in a new shape, a range of a clip, clips joined into one, all free on the studio's own server.",
  },
  {
    tools: ["balance", "credit_history", "whoami", "recent", "search"],
    does: "Your credits and where they went; your workspace and plan; your latest work; search your studio.",
  },
  {
    tools: ["preferences", "set_preferences", "recipes", "recipe", "save_recipe"],
    does: "Your workspace's defaults (frame, length, model, draft first); the studio's recipes and your own.",
  },
  {
    tools: ["what_works", "score_caption", "feedback"],
    does: "What you kept and what reached an audience; a caption scored against your own posts; a note to the studio.",
  },
];
const TOOL_COUNT = toolCount(TOOLS);

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
  // The setup steps live in the hero's modal, which renders only when opened;
  // this answer keeps them in the page's HTML, since /mcp is the documentation
  // address the ChatGPT directory submission names (2026-10-16).
  {
    q: "How do I add Phantra to ChatGPT?",
    a: `Open chatgpt.com/plugins, press Add and choose Add custom MCP server. Name it ${CONNECTOR_NAME}, paste ${RENDER_ADDRESS}, and sign in with your Phantra account. Then start a chat and ask for an image or a video. Custom MCP servers depend on your ChatGPT plan and workspace settings; if you don't see Add, your plan doesn't allow them yet.`,
  },
  {
    q: "How do I add Phantra to Claude?",
    a: `In claude.ai, open Customize, then Connectors, and add a custom connector named ${CONNECTOR_NAME} with the address ${RENDER_ADDRESS}, or press Connect Phantra at the top of this page to open it filled in. Then sign in with your Phantra account and press Allow.`,
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
    a: `Remove ${CONNECTOR_NAME} where you added it. In Claude that is Customize, then Connectors; in ChatGPT, at chatgpt.com/plugins.`,
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
      <McpClientProvider ids={HERO_CLIENTS.map((c) => c.id)}>
      <main className="flex-1">
        {/* HERO */}
        <section id="connect" className="relative isolate overflow-hidden pt-[60px]">
          {/* the hash targets (/mcp#claude, the closing "Connect to Claude"):
              landing on one picks that client (client-context.tsx) */}
          {HERO_CLIENTS.map((c) => (
            <span key={c.id} id={c.id} aria-hidden className="absolute top-0 block scroll-mt-20" />
          ))}
          <ParticleMorph />
          <div className="mx-auto flex max-w-[1100px] flex-col items-center px-4 pb-24 pt-10 text-center md:px-6 md:pb-32 md:pt-14">
            <HeroConnect clients={HERO_CLIENTS}>
              <h1
                className={`display mt-12 text-[clamp(3rem,9vw,7rem)] leading-[0.95] text-foreground md:mt-16 ${REVEAL} motion-safe:duration-700`}
              >
                Phantra MCP
              </h1>
              <p
                className={`mt-5 max-w-[20ch] text-[clamp(1.5rem,3.6vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground ${REVEAL} motion-safe:duration-700 motion-safe:delay-100`}
              >
                AI images and video inside your chat.
              </p>
              <p
                className={`mt-5 max-w-[44ch] text-[clamp(1rem,1.5vw,1.125rem)] leading-normal text-[var(--ink-2)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-150`}
              >
                Use Phantra in ChatGPT, Claude, and other compatible agents.
              </p>
            </HeroConnect>
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

        {/* SETUP */}
        <section id="setup" className="scroll-mt-20 border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Set up, step by step</SectionTitle>
            <p className="mx-auto mt-5 max-w-[52ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              You need a Phantra account first, on any plan.{" "}
              <Link href="/studio" className="text-foreground underline underline-offset-4">
                Sign in once
              </Link>{" "}
              to create your workspace, then add the connector where you chat.
            </p>
            <div className="mt-12">
              <SetupTabs tabs={SETUP_TABS} />
            </div>
          </div>
        </section>

        {/* TOOLS */}
        <section id="tools" className="scroll-mt-20 border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>What the connector does</SectionTitle>
            <p className="mx-auto mt-5 max-w-[60ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              {TOOL_COUNT} tools on {RENDER_ADDRESS.replace("https://", "")}. They read and write your own projects,
              scenes, elements and library. The ones that draw or render are quoted in credits first and run only
              after your yes; everything else spends nothing.
            </p>
            <ToolList groups={TOOLS} />
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
      </McpClientProvider>
      <SiteFooter />
    </EditorialSkin>
  );
}
