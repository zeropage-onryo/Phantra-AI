import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Code, Smartphone, SquareTerminal, type LucideIcon } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { CopyField } from "@/components/mcp/copy-field";
import { LEGAL_CONTACT } from "@/components/legal-page";
import { Button } from "@/components/ui/button";
import { CONNECTOR_NAME } from "@/lib/connect-claude";
import { pageMeta } from "@/lib/page-meta";
import { downloadOf, type Entry, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

// Every plugin in one place, each with its setup (2026-10-23, Mike: "lets make
// a plugins page for this for setup"). It is the index, not the manual: the
// steps here are the short form, and each card's guide link goes to the page
// that holds the long one (/mcp for the AI assistants, /download for the editor
// panels). The same facts as those pages, never new ones:
// - the address and the Claude Code / Cursor lines are /mcp's (RENDER_ADDRESS,
//   CLAUDE_CODE_COMMAND, CURSOR_CONFIG there); the connector's name is
//   lib/connect-claude's CONNECTOR_NAME
// - the Resolve panel's requirement and install steps are /download's; its
//   Download button exists only once content/downloads.json marks the build
//   live (lib/downloads.ts), otherwise it reads "Coming soon", like /download
// - Premiere stays "Coming soon" until its build has run in Premiere Pro 25.6+
// - the rows under "On the way" are the studio's Plugins flyout's disabled ones
//   (components/studio/plugins-flyout.tsx), with no setup because none exists
// No price is printed here: every plugin spends credits only through a quote
// the person sees and approves.

export const metadata: Metadata = pageMeta({
  title: "Plugins and setup",
  description:
    "Use Phantra from ChatGPT, Claude, Claude Code, Cursor, DaVinci Resolve and Premiere Pro. Setup for each in a few steps; every image and video is priced in credits before anything is spent.",
  path: "/plugins",
});

const ORIGIN = "https://api.phantra.ai";
const RENDER_ADDRESS = `${ORIGIN}/mcp`;
const PLUGIN_URL = "https://github.com/zeropage-onryo/phantra-claude-plugin";
const CHATGPT_PLUGINS_URL = "https://chatgpt.com/plugins";
const CLAUDE_ADD = `https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=${encodeURIComponent(CONNECTOR_NAME)}&connectorUrl=${encodeURIComponent(RENDER_ADDRESS)}`;
const CLAUDE_CODE_COMMAND = `claude mcp add --transport http phantra-ai ${RENDER_ADDRESS}`;
const CURSOR_CONFIG = `{\n  "mcpServers": {\n    "phantra-ai": { "url": "${RENDER_ADDRESS}" }\n  }\n}`;

const RESOLVE = downloadOf("resolve", DOWNLOADS as Record<PanelId, Entry>);

type Action = { label: string; href: string; external?: boolean };

type Plugin = {
  id: string;
  name: string;
  logo?: string;
  icon?: LucideIcon;
  /** "ready" shows the setup; "soon" says so and links nothing it can't keep */
  status: "ready" | "soon";
  what: string;
  needs?: ReactNode;
  steps?: ReactNode[];
  copy?: { label: string; value: string; multiline?: boolean };
  action?: Action;
  guide?: Action;
};

const ASSISTANTS: Plugin[] = [
  {
    id: "chatgpt",
    name: "ChatGPT",
    logo: "/brand/plugins/chatgpt.svg",
    status: "ready",
    what: "Describe an image or a video in a chat. ChatGPT shows the price in credits and makes it on your yes.",
    needs: "A ChatGPT plan that allows custom MCP servers, and a Phantra account.",
    steps: [
      <>Open chatgpt.com/plugins, press Add and choose Add custom MCP server.</>,
      <>
        Name it {CONNECTOR_NAME} and paste the address below.
      </>,
      <>Sign in with your Phantra account.</>,
    ],
    copy: { label: "Address", value: RENDER_ADDRESS },
    action: { label: "Open ChatGPT plugins", href: CHATGPT_PLUGINS_URL, external: true },
    guide: { label: "Full guide", href: "/mcp" },
  },
  {
    id: "claude",
    name: "Claude",
    logo: "/brand/plugins/claude.svg",
    status: "ready",
    what: "The same in Claude: ask for a still or a clip, see the price first, say yes.",
    needs: "A Claude account and a Phantra account.",
    steps: [
      <>Press Add to Claude: it opens Customize, Connectors with the name and address filled in.</>,
      <>Sign in with your Phantra account and press Allow.</>,
      <>Start a new chat and describe what you want.</>,
    ],
    copy: { label: "Address", value: RENDER_ADDRESS },
    action: { label: "Add to Claude", href: CLAUDE_ADD, external: true },
    guide: { label: "Full guide", href: "/mcp" },
  },
  {
    id: "claude-code",
    name: "Claude Code",
    icon: SquareTerminal,
    status: "ready",
    what: "Make images and video from your terminal, beside the code that uses them.",
    steps: [
      <>Run the command below once.</>,
      <>
        Start Claude Code, type <code className="font-mono text-foreground">/mcp</code>, pick phantra-ai and choose
        Authenticate.
      </>,
      <>Sign in with your Phantra account in the browser and press Allow.</>,
    ],
    copy: { label: "Command", value: CLAUDE_CODE_COMMAND },
    guide: { label: "Full guide", href: "/mcp" },
  },
  {
    id: "cursor",
    name: "Cursor and other MCP apps",
    icon: Code,
    status: "ready",
    what: "Any app that adds a remote MCP server by its address.",
    steps: [
      <>
        In Cursor, add this to <code className="font-mono text-foreground">~/.cursor/mcp.json</code>. Elsewhere, the
        address alone is enough.
      </>,
      <>When the app asks, sign in with your Phantra account and press Allow.</>,
    ],
    copy: { label: "Cursor config", value: CURSOR_CONFIG, multiline: true },
    guide: { label: "Full guide", href: "/mcp" },
  },
  {
    id: "claude-plugin",
    name: "Claude plugin",
    logo: "/brand/plugins/claude.svg",
    status: "ready",
    what: "The connector plus skills that teach Claude to plan with the studio: storyboards, ad variations, product shots, camera moves and the edit.",
    steps: [
      <>Open the plugin on GitHub; its README says how to add it to Claude.</>,
      <>On the plugin&apos;s Connectors tab, connect {CONNECTOR_NAME} and sign in.</>,
    ],
    action: { label: "Get the plugin", href: PLUGIN_URL, external: true },
    guide: { label: "About the plugin", href: "/mcp" },
  },
];

const EDITORS: Plugin[] = [
  {
    id: "resolve",
    name: "DaVinci Resolve",
    logo: "/brand/plugins/davinci-resolve.svg",
    status: RESOLVE.url ? "ready" : "soon",
    what: "A panel inside Resolve: your Library in the Media Pool, and images, video and effects made from the clip you are cutting.",
    needs: (
      <>
        DaVinci Resolve <strong className="font-medium text-foreground">Studio</strong> 19.0.2 or newer on macOS. The
        free version doesn&apos;t load Workflow Integrations.
      </>
    ),
    steps: [
      <>Quit Resolve, unzip the download and double-click install.command (it asks for your Mac password).</>,
      <>Open Resolve, then Workspace, Workflow Integrations, Phantra.</>,
      <>Press Sign in and type the code it shows at phantra.ai/studio/link.</>,
    ],
    action: RESOLVE.url ? { label: "Download", href: "/download" } : undefined,
    guide: { label: "Install guide", href: "/download#install" },
  },
  {
    id: "premiere",
    name: "Premiere Pro",
    logo: "/brand/plugins/premiere-pro.svg",
    status: "soon",
    what: "The same panel in Premiere: your Library in a Phantra bin, and the selected clip or frame sent up to edit.",
    needs: "Adobe Premiere Pro 25.6 or newer.",
    guide: { label: "What it will do", href: "/download" },
  },
];

const ON_THE_WAY: { name: string; logo?: string; icon?: LucideIcon }[] = [
  { name: "After Effects", logo: "/brand/plugins/after-effects.svg" },
  { name: "Grok", logo: "/brand/plugins/grok.svg" },
  { name: "Mobile app", icon: Smartphone },
  { name: "Developer API", icon: Code },
];

const PROSE =
  "text-[15px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4";

function Logo({ src, icon: Icon }: { src?: string; icon?: LucideIcon }) {
  if (!src) {
    const Drawn = Icon ?? Code;
    return (
      <span
        aria-hidden
        className="inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] border border-border bg-secondary text-foreground"
      >
        <Drawn className="size-[18px]" strokeWidth={1.75} />
      </span>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="" width={36} height={36} className="size-9 shrink-0 rounded-[10px]" />;
}

function ActionLink({ action, primary }: { action: Action; primary?: boolean }) {
  const icon = action.external ? <ArrowUpRight data-icon="inline-end" className="size-4" /> : <ArrowRight data-icon="inline-end" className="size-4" />;
  const link = action.external ? (
    <a href={action.href} target="_blank" rel="noopener noreferrer" />
  ) : (
    <Link href={action.href} />
  );
  return (
    <Button size={primary ? "lg" : "default"} variant={primary ? "default" : "outline"} render={link}>
      {action.label}
      {icon}
    </Button>
  );
}

function PluginCard({ plugin }: { plugin: Plugin }) {
  return (
    <article id={plugin.id} className="flex scroll-mt-24 flex-col rounded-[14px] border border-border bg-card p-6">
      <div className="flex items-center gap-3">
        <Logo src={plugin.logo} icon={plugin.icon} />
        <h3 className="text-[19px] font-medium tracking-[-0.01em] text-foreground">{plugin.name}</h3>
        {plugin.status === "soon" && (
          <span className="ml-auto rounded-full border border-border px-2.5 py-0.5 text-[12px] text-[#8a8a8a]">
            Coming soon
          </span>
        )}
      </div>
      <p className={`mt-4 ${PROSE}`}>{plugin.what}</p>
      {plugin.needs && <p className="mt-3 text-[13px] leading-relaxed text-[#8a8a8a]">Needs: {plugin.needs}</p>}

      {plugin.status === "ready" && plugin.steps && (
        <ol className="mt-5 divide-y divide-border border-y border-border">
          {plugin.steps.map((step, i) => (
            <li key={i} className="flex gap-4 py-3.5">
              <span className="eyebrow pt-0.5">{String(i + 1).padStart(2, "0")}</span>
              <p className="text-[14px] leading-relaxed text-[#afafaf]">{step}</p>
            </li>
          ))}
        </ol>
      )}
      {plugin.status === "ready" && plugin.copy && (
        <div className="mt-5">
          <CopyField label={plugin.copy.label} value={plugin.copy.value} multiline={plugin.copy.multiline} />
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-3 pt-6">
        {plugin.status === "ready" && plugin.action && <ActionLink action={plugin.action} primary />}
        {plugin.guide && <ActionLink action={plugin.guide} />}
      </div>
    </article>
  );
}

function Group({ id, eyebrow, title, intro, plugins }: { id: string; eyebrow: string; title: string; intro: ReactNode; plugins: Plugin[] }) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-border">
      <div className="mx-auto max-w-[1200px] px-6 py-16 md:py-20">
        <span className="eyebrow">{eyebrow}</span>
        <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">{title}</h2>
        <p className={`mt-4 max-w-[60ch] ${PROSE} text-[17px]`}>{intro}</p>
        <div className="mt-10 grid gap-3 md:grid-cols-2">
          {plugins.map((plugin) => (
            <PluginCard key={plugin.id} plugin={plugin} />
          ))}
        </div>
      </div>
    </section>
  );
}

export default function PluginsPage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Plugins"
          title="Phantra where you already work."
          dek="Your studio from an AI chat, a terminal or your editing app. Set each one up in a few steps; everything is priced in credits and waits for your yes."
        >
          <nav aria-label="Plugin groups" className="mt-8 flex flex-wrap justify-center gap-2">
            {[
              { href: "#assistants", label: "AI assistants" },
              { href: "#editors", label: "Editing apps" },
              { href: "#soon", label: "On the way" },
            ].map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="rounded-full border border-border px-4 py-2 text-[14px] text-foreground transition-colors hover:bg-secondary"
              >
                {l.label}
              </a>
            ))}
          </nav>
        </PageIntro>

        <Group
          id="assistants"
          eyebrow="AI assistants"
          title="Connect once, then ask."
          intro={
            <>
              One address works in every assistant: {RENDER_ADDRESS}. You sign in with your Phantra account, and the
              assistant can see your Library, write scenes and make stills and clips, each priced before it runs.
            </>
          }
          plugins={ASSISTANTS}
        />

        <Group
          id="editors"
          eyebrow="Editing apps"
          title="A panel inside your editor."
          intro={
            <>
              The panels sign in with a code your editor shows, never a password, and keep the sign-in in your
              Mac&apos;s Keychain. Disconnect any copy under Settings, Connections, Apps in the studio.
            </>
          }
          plugins={EDITORS}
        />

        <section id="soon" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-16 md:py-20">
            <span className="eyebrow">On the way</span>
            <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">Next.</h2>
            <ul className="mt-8 flex flex-wrap gap-3">
              {ON_THE_WAY.map((item) => (
                <li
                  key={item.name}
                  className="flex items-center gap-3 rounded-[14px] border border-border bg-card px-4 py-3 text-[15px] text-[#afafaf]"
                >
                  <Logo src={item.logo} icon={item.icon} />
                  {item.name}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-16">
            <p className={PROSE}>
              The plugins are free to set up and use with your own Phantra account; what you make costs credits, shown
              before anything is spent. The editor panels are under the{" "}
              <Link href="/download/license">Phantra Plugin License</Link>. Questions:{" "}
              <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
