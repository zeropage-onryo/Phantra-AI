import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, Sparkles } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { LEGAL_CONTACT as SUPPORT_EMAIL } from "@/components/legal-page";
import { CopyButton, CopyField } from "@/components/mcp/copy-field";
import { SetupTabs, type SetupTab } from "@/components/mcp/setup-tabs";
import { FaqSection } from "@/landing-pages/components/faq-section";
import { SectionTitle } from "@/landing-pages/components/section-title";
import { RED, accentVars } from "@/landing-pages/theme";
import { CLAUDE_CONNECTORS_URL, CONNECTOR_NAME } from "@/lib/connect-claude";
import { pageMeta } from "@/lib/page-meta";
import { REVEAL_CLASS as REVEAL } from "@/lib/motion";

// The Claude connector's own documentation page (2026-10-15). It is the
// documentation URL in the Claude plugin's manifest and in the Anthropic
// directory submission (docs/directory/PORTAL_PASTE.md section 1), so it
// documents ONLY the /mcp/claude address and its 32 tools. The other address
// (/mcp, which draws and renders after a quote) lives on /mcp, which the
// ChatGPT listing uses; this page does not name it or link to its setup.
//
// What the connector does, checked against the server that day
// (src/mcp_server.py CLAUDE_LISTED_TOOLS, docs/directory/TWO_LISTINGS.md):
// - 32 tools; none of them draws, renders or spends credits. Not on this
//   address: approve, generate_image, image_models, effects, apply_effect
// - `quote` prices a scene in credits beside the balance and returns
//   `approve_url`, the scene's page in the studio, where the person approves
//   the render; the studio shows the price again before anything is spent
// - reformat / trim_clip / assemble_clips run on the studio's own server over
//   the person's own files and cost nothing
// - no tool takes the conversation (save_chat is on neither list)
// The tool list below is that list, grouped as the plugin README groups it.
// No price, plan or model showcase is printed here.
const ORIGIN = "https://api.phantra.ai";
const CLAUDE_ADDRESS = `${ORIGIN}/mcp/claude`;
const PLUGIN_URL = "https://github.com/zeropage-onryo/phantra-claude-plugin";

export const metadata: Metadata = pageMeta({
  title: "Phantra connector for Claude",
  description:
    "Plan, write, organise, price and edit short video scenes from your own photos and clips in a conversation with Claude. Renders are approved and made in the Phantra studio, never in the chat.",
  path: "/mcp/claude",
});

const CLIENTS = ["Claude on the web", "Claude desktop", "Claude mobile", "Claude Code"];

const TABS: SetupTab[] = [
  {
    id: "claude",
    label: "Claude",
    title: "Add it to Claude",
    intro: (
      <p>
        Works in Claude on the web, the desktop app and the phone once it is added to your account. Claude plans and
        writes the scene with you and prices it; you approve the render on the scene&apos;s page in your studio.
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
      <>Start a chat and ask what you are working on, or describe the piece you want to plan.</>,
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
    ],
  },
  {
    id: "plugin",
    label: "Claude plugin",
    title: "The Phantra plugin for Claude",
    intro: (
      <p>
        The plugin bundles this connector with 22 skills that teach Claude how to plan with the studio: storyboards,
        ad variations, product scenes, camera moves, UGC ads, explainers, hooks, sound and the edit. Free and open
        source (MIT).
      </p>
    ),
    steps: [
      <>Get the plugin from GitHub. Its README says how to add it to Claude.</>,
      <>
        On the plugin&apos;s Connectors tab, connect {CONNECTOR_NAME} and sign in with your Phantra account.
      </>,
      <>Ask Claude for a storyboard, an ad plan or a scene; the skills load as they are needed.</>,
    ],
    action: { label: "Get the plugin on GitHub", href: PLUGIN_URL },
  },
  {
    id: "claude-code",
    label: "Claude Code",
    title: "Add it to Claude Code",
    intro: <p>One command in your terminal, then sign in once from inside Claude Code.</p>,
    copy: [{ label: "Command", value: `claude mcp add --transport http phantra-ai ${CLAUDE_ADDRESS}` }],
    steps: [
      <>Run the command above.</>,
      <>
        Start Claude Code, type <code>/mcp</code>, pick <strong>phantra-ai</strong> and choose{" "}
        <strong>Authenticate</strong>.
      </>,
      <>Sign in with your Phantra account in the browser window that opens, and press Allow.</>,
    ],
  },
];

// The 32 tools on /mcp/claude, grouped as the plugin README groups them.
const TOOLS: { tools: string[]; does: string }[] = [
  {
    tools: ["projects", "project", "project_chat", "create_project"],
    does: "Your projects: list them, open one (brief, look, scenes, references, renders, recent chat), page its chat, start one.",
  },
  {
    tools: ["elements", "add_element"],
    does: "The characters, props and places a scene is held to, with their photos; add one from an image address or a product page you give.",
  },
  {
    tools: ["upload_link"],
    does: "A one-time page where you upload a picture or a clip from your device into your studio, optionally straight onto an element.",
  },
  {
    tools: ["write_scene", "duplicate_scene", "scene"],
    does: "Save a scene written with you as timed shots (with what each photo is for), copy one with changes, read one back.",
  },
  {
    tools: ["quote", "video_models", "recommend_model"],
    does: "Price a scene in credits beside your balance, with the link to its page in the studio where you approve the render; the models and what each takes; which model suits a job.",
  },
  {
    tools: ["library", "share_link"],
    does: "What is in your library (renders and uploads); a time-limited download link for one of them.",
  },
  {
    tools: ["reformat", "trim_clip", "assemble_clips", "job"],
    does: "A clip or still in a new shape, a range of a clip, clips joined into one: free, on the studio's own server. Check on a job.",
  },
  {
    tools: ["balance", "credit_history", "whoami", "recent", "search"],
    does: "Your credits and where they went; your workspace and plan; your latest work; search your studio.",
  },
  {
    tools: ["preferences", "set_preferences"],
    does: "Your workspace's defaults: frame, length, model, draft first.",
  },
  {
    tools: ["recipes", "recipe", "save_recipe"],
    does: "The studio's recipes and your own.",
  },
  {
    tools: ["what_works", "score_caption"],
    does: "What you kept and what reached an audience; a caption scored against your own posts.",
  },
  {
    tools: ["feedback"],
    does: "A note to the studio.",
  },
];
const TOOL_COUNT = TOOLS.reduce((n, g) => n + g.tools.length, 0);

const PROMPTS: { title: string; prompt: string; tag: string }[] = [
  {
    title: "Pick up where you left off",
    prompt: "What am I working on? Open my latest project and show me its scenes.",
    tag: "Projects",
  },
  {
    title: "Plan a product spot",
    prompt:
      "I want a 10-second spot for my matte black water bottle on a wet gym floor, no people. Give me three ideas, then write the one I pick as timed shots.",
    tag: "Plan",
  },
  {
    title: "Storyboard a launch",
    prompt: "Storyboard a 30-second launch for my coffee brand as four scenes, all held to my bag and café photos.",
    tag: "Plan",
  },
  {
    title: "Price it",
    prompt: "What would scene 408 cost to render, and which model suits it best?",
    tag: "Price",
  },
  {
    title: "Make it vertical",
    prompt: "Make my last clip 9:16 for Reels and give me a download link.",
    tag: "Free edit",
  },
  {
    title: "Check my credits",
    prompt: "How many credits do I have left, and what did I spend them on this week?",
    tag: "Account",
  },
];

const NOT: string[] = [
  "Draw an image, render a clip or spend credits. The render is approved by you on the scene's page in the Phantra studio, where the price is shown again.",
  "Buy credits, change a plan or post anywhere.",
  "Delete or overwrite your work. Every edit is a new item; rewriting a scene replaces only that scene's text, after Claude shows you the new version.",
  "Reach anybody else's workspace, or hold a scene to a photo that is not one of your elements.",
  "Take your conversation. The studio receives what a tool is handed: a project's name and brief, a scene's text, the photos picked for it.",
];

const FAQS = [
  {
    q: "What does the Phantra connector for Claude do?",
    a: "It lets Claude work in your Phantra studio with you: open and start projects, bring in your own photos and clips as elements, write scenes as timed shots held to those photos, price a scene in credits, and trim, reshape and join clips you already have. Renders are approved and made in the Phantra studio, never in the chat.",
  },
  {
    q: "Where are scenes rendered?",
    a: "In the Phantra studio. When you ask what a scene would cost, Claude shows the price in credits beside your balance and a link to the scene's page in your studio. You open it, see the price again and press Render there. Nothing on this connector draws, renders or spends credits.",
  },
  {
    q: "Do I need a Phantra account?",
    a: "Yes. Sign in once at phantra.ai to create your workspace; a new workspace comes with a one-time trial of credits. Then add the connector and sign in with the same account.",
  },
  {
    q: "What does it cost?",
    a: "Adding the connector, planning, writing, pricing and the free edits (reformat, trim, join, download links) cost nothing. A render you approve in the studio spends credits from your balance, at the price the studio shows you there.",
  },
  {
    q: "What does the connector send to Phantra?",
    a: "Only what a tool is handed: the scene text Claude writes with you, a project's name and brief, the ids of your projects, scenes and photos, an address you give add_element, and the words of a search, a recipe, a caption or a feedback note. It does not send the conversation.",
  },
  {
    q: "How do I disconnect?",
    a: `Remove ${CONNECTOR_NAME} where you added it: in Claude, Customize, then Connectors.`,
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

export default function McpClaudePage() {
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
              <span className={`eyebrow ${REVEAL} motion-safe:duration-700`}>Claude connector · Claude plugin</span>
              <h1
                className={`serif serif-bold mt-5 max-w-[14ch] text-[clamp(2.75rem,7vw,5.75rem)] ${REVEAL} motion-safe:duration-700`}
              >
                Plan your video scenes with Claude.
              </h1>
              <p
                className={`mt-7 max-w-[48ch] text-[clamp(1rem,1.5vw,1.125rem)] leading-normal text-[var(--ink-2)] ${REVEAL} motion-safe:duration-700 motion-safe:delay-100`}
              >
                Plan, write, organise, price and edit short video scenes from your own photos and clips in a
                conversation. Renders are approved and made in the Phantra studio, never in the chat.
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
                  href="#plugin"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-border bg-background px-6 text-[15px] font-semibold text-foreground transition-colors hover:bg-secondary"
                >
                  Get the Claude plugin
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

            {/* An illustration of the flow, drawn here: a question, the priced plan, the studio link. */}
            <div className={`relative mx-auto w-full max-w-[480px] ${REVEAL} motion-safe:duration-1000 motion-safe:delay-150`} aria-hidden>
              <div className="rounded-[28px] border border-border bg-card p-4 shadow-[0_40px_90px_-40px_rgba(0,0,0,0.35)] sm:p-5">
                <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-foreground px-4 py-3 text-[14px] leading-snug text-background">
                  Write the bottle spot as two shots and tell me what it would cost.
                </div>
                <div className="mt-4 flex items-start gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-white">
                    <Sparkles className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1 rounded-2xl border border-border bg-background p-4">
                    <p className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-3)]">
                      Saved to Spring launch
                    </p>
                    <ol className="mt-3 flex flex-col gap-2 text-[14px] leading-snug text-foreground">
                      <li>
                        <span className="font-mono text-[12px] text-[var(--ink-3)]">0–4s</span> Bottle on the wet floor,
                        slow push-in.
                      </li>
                      <li>
                        <span className="font-mono text-[12px] text-[var(--ink-3)]">4–8s</span> Macro on the cap as a drop
                        runs down.
                      </li>
                    </ol>
                    <p className="mt-4 text-[14px] leading-snug text-[var(--ink-2)]">
                      Priced in credits beside your balance. Approve it on the scene&apos;s page in your studio.
                    </p>
                    <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1.5 text-[12px] font-medium text-foreground">
                      <Check className="size-3.5" /> Open in studio
                    </span>
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
              to create your workspace, then add the connector.
            </p>
            <div className="mx-auto mt-8 max-w-[560px]">
              <CopyField value={CLAUDE_ADDRESS} label="Address" />
            </div>
            <div className="mt-12">
              <SetupTabs tabs={TABS} />
            </div>
          </div>
        </section>

        {/* TOOLS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>What the connector does</SectionTitle>
            <p className="mx-auto mt-5 max-w-[60ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              {TOOL_COUNT} tools on {CLAUDE_ADDRESS.replace("https://", "")}. They read and write your own projects,
              scenes, elements and library. None of them draws, renders or spends credits.
            </p>
            <div className="mx-auto mt-12 max-w-[960px] divide-y divide-border border-y border-border">
              {TOOLS.map((g) => (
                <div key={g.tools.join(",")} className="grid gap-3 py-5 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:gap-8">
                  <div className="flex flex-wrap gap-1.5">
                    {g.tools.map((t) => (
                      <code
                        key={t}
                        className="rounded-md border border-border bg-secondary px-2 py-0.5 font-mono text-[13px] text-foreground"
                      >
                        {t}
                      </code>
                    ))}
                  </div>
                  <p className="text-[15.5px] leading-relaxed text-[var(--ink-2)]">{g.does}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PROMPTS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>Things to ask for</SectionTitle>
            <p className="mx-auto mt-5 max-w-[50ch] text-center text-[17px] leading-relaxed text-[var(--ink-2)]">
              Copy one into a Claude chat once Phantra is connected.
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

        {/* LIMITS */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6 md:py-24">
            <SectionTitle>What it will not do</SectionTitle>
            <ul className="mx-auto mt-12 flex max-w-[760px] flex-col gap-4">
              {NOT.map((line) => (
                <li key={line} className="flex gap-3 text-[15.5px] leading-relaxed text-foreground">
                  <Check className="mt-1 size-4 shrink-0 text-[var(--primary)]" aria-hidden />
                  {line}
                </li>
              ))}
            </ul>
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

        <FaqSection title="Questions" items={FAQS} />

        {/* FINAL */}
        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[760px] flex-col items-center gap-7 px-4 py-24 text-center md:px-6 md:py-32">
            <span className="eyebrow">Get started</span>
            <h2 className="serif text-[clamp(2.25rem,5.5vw,4rem)]">Plan the scene with Claude. Render it in the studio.</h2>
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
