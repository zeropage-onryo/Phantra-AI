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
import { downloadOf, humanSize, osesOf, type Download, type Entry, type PanelId } from "@/lib/downloads";
import DOWNLOADS from "@/content/downloads.json";

// The editor panels' setup page (2026-10-23, Mike: "make da vinci and premier
// live and connected and it sends to this page, only showing the two"). Two
// cards: DaVinci Resolve, and the Adobe panel, ONE extension for Premiere Pro
// and After Effects (2026-11-03, phantra-premiere-plugin 0.3.0, CEP; the old
// #premiere anchor still lands on it, and #aftereffects beside it). The
// panels' facts are /download's (their READMEs, in the private repos
// phantra-resolve-plugin and phantra-premiere-plugin). A Download button
// exists only once content/downloads.json marks that file live with its size
// and sha256 (lib/downloads.ts), so the page never links a file that is not
// up; until then the card says its download is on the way. No price is
// printed: the panels spend credits only through the studio's own
// quote-and-approve.

export const metadata: Metadata = pageMeta({
  title: "DaVinci Resolve, Premiere Pro and After Effects plugins",
  description:
    "Set up Phantra inside DaVinci Resolve Studio, Adobe Premiere Pro and After Effects: your Library on the timeline, and AI images, video and effects made from the clip you are cutting, priced before anything is spent.",
  path: "/plugins",
});

const ENTRIES = DOWNLOADS as Record<PanelId, Entry>;

type Step = { title: string; body: ReactNode };

type Panel = {
  id: PanelId;
  app: string;
  /** one logo per app the panel lives in */
  logos: string[];
  /** anchors that also open this card */
  aliases?: string[];
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
    logos: ["/brand/plugins/davinci-resolve.svg"],
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
    id: "adobe",
    app: "Premiere Pro and After Effects",
    logos: ["/brand/plugins/premiere-pro.svg", "/brand/plugins/after-effects.svg"],
    aliases: ["premiere", "aftereffects"],
    requires: <>Adobe Premiere Pro or After Effects 2025 (25.0) or newer, on Mac or Windows. One install covers both apps.</>,
    does: "Your Library in a Phantra bin or folder and at the playhead or on your comp, and the selected clip or layer, or the frame at the current time, sent up to edit and brought back.",
    install: [
      {
        title: "Quit Premiere and After Effects, then install",
        body: (
          <>
            On a Mac, double-click the .pkg, press Continue and type your Mac password: it puts the panel in
            /Library/Application Support/Adobe/CEP/extensions, which both apps read. On Windows, install the free{" "}
            <a href="https://aescripts.com/learn/zxp-installer/">ZXP Installer</a> from aescripts and drag the .zxp
            onto it.
          </>
        ),
      },
      {
        title: "Open the panel",
        body: <>Start either app, then Window, Extensions, Phantra. If Phantra is not in the menu, quit the app fully and open it again.</>,
      },
      ...SIGN_IN,
    ],
  },
];

const PROSE =
  "text-[15px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4";

const OS_NAME = { mac: "Mac", windows: "Windows" } as const;

function DownloadBox({ download, labelled }: { download: Download; labelled: boolean }) {
  const name = labelled ? ` for ${OS_NAME[download.os]}` : "";
  if (!download.url || download.size === null || !download.sha256 || !download.file) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <span
          aria-disabled="true"
          className="inline-flex h-10 items-center rounded-lg border border-border px-4 text-[14px] text-[#8a8a8a]"
        >
          Download{name} on the way
        </span>
        <span className="text-[13px] text-[#8a8a8a]">Version {download.version}</span>
      </div>
    );
  }
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="lg" render={<a href={download.url} download={download.file} />}>
          Download{name}
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
  const oses = osesOf(panel.id);
  return (
    <article id={panel.id} className="flex scroll-mt-24 flex-col rounded-[14px] border border-border bg-card p-6 md:p-8">
      {panel.aliases?.map((alias) => (
        <span key={alias} id={alias} aria-hidden className="block scroll-mt-24" />
      ))}
      <div className="flex items-center gap-3">
        {panel.logos.map((logo) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={logo} src={logo} alt="" width={40} height={40} className="size-10 shrink-0 rounded-[10px]" />
        ))}
        <h2 className="serif text-[clamp(1.5rem,3vw,2rem)]">{panel.app}</h2>
      </div>
      <p className={`mt-5 ${PROSE}`}>{panel.does}</p>
      <p className="mt-3 text-[13px] leading-relaxed text-[#8a8a8a]">Needs: {panel.requires}</p>

      <div className="mt-6 flex flex-col gap-4">
        {oses.map((os) => (
          <DownloadBox key={os} download={downloadOf(panel.id, ENTRIES, os)} labelled={oses.length > 1} />
        ))}
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
          dek="A panel in DaVinci Resolve, Premiere Pro and After Effects, connected to your studio: your Library on the timeline, and images, video and effects made from the clip you are cutting. Everything is priced in credits and waits for your yes."
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
              The panels sign in with a code, never a password, and keep the sign-in on your own computer; a panel
              left unused for 90 days asks again. Disconnect any copy with Sign out in the panel, or under
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
