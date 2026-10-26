import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowDown } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { LEGAL_CONTACT } from "@/components/legal-page";
import { Button } from "@/components/ui/button";
import { pageMeta } from "@/lib/page-meta";
import { downloadOf, humanSize, type Download, type Entry, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

// The editor panels' setup page (2026-10-23, Mike: "make da vinci and premier
// live and connected and it sends to this page, only showing the two"). The
// studio's Plugins flyout sends its DaVinci Resolve and Premiere Pro rows here
// (/plugins#resolve, /plugins#premiere); nothing else on the site links it.
// The panels' facts are /download's (their READMEs, in the private repos
// phantra-resolve-plugin and phantra-premiere-plugin). The Download button
// exists only once content/downloads.json marks a build live with its size and
// sha256 (lib/downloads.ts), so the page never links a file that is not up;
// until then each card says its download is on the way. No price is printed:
// the panels spend credits only through the studio's own quote-and-approve.

export const metadata: Metadata = pageMeta({
  title: "DaVinci Resolve and Premiere Pro plugins",
  description:
    "Set up Phantra inside DaVinci Resolve Studio and Adobe Premiere Pro: your Library on the timeline, and AI images, video and effects made from the clip you are cutting, priced before anything is spent.",
  path: "/plugins",
});

const ENTRIES = DOWNLOADS as Record<PanelId, Entry>;

type Step = { title: string; body: ReactNode };

type Panel = {
  id: PanelId;
  app: string;
  logo: string;
  requires: ReactNode;
  does: string;
  install: Step[];
};

const SIGN_IN: Step[] = [
  {
    title: "Press Sign in",
    body: (
      <>
        The panel shows a code like <code className="font-mono text-foreground">KDPX-7QHR</code> and opens{" "}
        <span className="text-foreground">phantra.ai/studio/link</span> in your browser.
      </>
    ),
  },
  {
    title: "Type the code and press Connect",
    body: <>On that page, signed in to your studio. The panel signs in by itself a few seconds later.</>,
  },
];

const PANELS: Panel[] = [
  {
    id: "resolve",
    app: "DaVinci Resolve",
    logo: "/brand/plugins/davinci-resolve.svg",
    requires: (
      <>
        DaVinci Resolve <strong className="font-medium text-foreground">Studio</strong> 20.1 or newer on macOS. The
        panel does not work in the free version of Resolve.
      </>
    ),
    does: "Your Library in the Media Pool and at the playhead, and images, video and effects made from the clip on your timeline or the frame at the playhead.",
    install: [
      {
        title: "Quit Resolve and open the installer",
        body: (
          <>
            Double-click the .pkg, press Continue and type your Mac password (Resolve keeps plugins in /Library). The
            first time, macOS may ask before opening it: right-click it and choose Open.
          </>
        ),
      },
      {
        title: "Open the panel",
        body: <>Start Resolve, then Workspace, Workflow Integrations, Phantra.</>,
      },
      ...SIGN_IN,
    ],
  },
  {
    id: "premiere",
    app: "Premiere Pro",
    logo: "/brand/plugins/premiere-pro.svg",
    requires: <>Adobe Premiere Pro 25.6 or newer, with the Creative Cloud app.</>,
    does: "Your Library in a Phantra bin and at the playhead, and the selected clip or the frame at the playhead sent up to edit, then brought back.",
    install: [
      {
        title: "Install the .ccx file",
        body: <>Double-click it; the Creative Cloud app installs the panel into Premiere.</>,
      },
      {
        title: "Open the panel",
        body: <>In Premiere, Window, Extensions (or UXP Plugins), Phantra.</>,
      },
      ...SIGN_IN,
    ],
  },
];

const PROSE =
  "text-[15px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4";

function DownloadBox({ download }: { download: Download }) {
  if (!download.url || download.size === null || !download.sha256) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <span
          aria-disabled="true"
          className="inline-flex h-10 items-center rounded-lg border border-border px-4 text-[14px] text-[#8a8a8a]"
        >
          Download on the way
        </span>
        <span className="text-[13px] text-[#8a8a8a]">Version {download.version}</span>
      </div>
    );
  }
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="lg" render={<a href={download.url} download={download.file} />}>
          Download
          <ArrowDown data-icon="inline-end" className="size-4" />
        </Button>
        <span className="text-[13px] text-[#afafaf]">
          Version {download.version}, {humanSize(download.size)}
        </span>
      </div>
      <p className="mt-4 text-[12px] text-[#8a8a8a]">
        {download.file}, sha256{" "}
        <code className="block select-all font-mono text-[12px] text-[#afafaf] [overflow-wrap:anywhere]">
          {download.sha256}
        </code>
      </p>
    </div>
  );
}

function PanelCard({ panel }: { panel: Panel }) {
  const download = downloadOf(panel.id, ENTRIES);
  return (
    <article id={panel.id} className="flex scroll-mt-24 flex-col rounded-[14px] border border-border bg-card p-6 md:p-8">
      <div className="flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={panel.logo} alt="" width={40} height={40} className="size-10 shrink-0 rounded-[10px]" />
        <h2 className="serif text-[clamp(1.5rem,3vw,2rem)]">{panel.app}</h2>
      </div>
      <p className={`mt-5 ${PROSE}`}>{panel.does}</p>
      <p className="mt-3 text-[13px] leading-relaxed text-[#8a8a8a]">Needs: {panel.requires}</p>

      <div className="mt-6">
        <DownloadBox download={download} />
      </div>

      <span className="eyebrow mt-8 block">Setup</span>
      <ol className="mt-3 divide-y divide-border border-y border-border">
        {panel.install.map((step, i) => (
          <li key={step.title} className="flex gap-4 py-4">
            <span className="eyebrow pt-1">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <h3 className="text-[16px] font-medium tracking-[-0.005em] text-foreground">{step.title}</h3>
              <p className="mt-1.5 text-[14px] leading-relaxed text-[#afafaf]">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}

export default function PluginsPage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Plugins"
          title="Phantra inside your editor."
          dek="A panel in DaVinci Resolve and Premiere Pro, connected to your studio: your Library on the timeline, and images, video and effects made from the clip you are cutting. Everything is priced in credits and waits for your yes."
        />

        <section className="mx-auto max-w-[1200px] px-6 pb-16">
          <div className="grid gap-3 md:grid-cols-2">
            {PANELS.map((panel) => (
              <PanelCard key={panel.id} panel={panel} />
            ))}
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-16">
            <p className={PROSE}>
              The panels sign in with a code, never a password, and keep the sign-in in your Mac&apos;s Keychain; a
              panel left unused for 90 days asks again. Disconnect any copy with Sign out in the panel, or under
              Settings, Connections, Apps in the studio. Never type a code someone else sent you. The panels are free to
              install and use with your own Phantra account, under the{" "}
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
