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

// The editor panels' download page (docs/tasks/task-plugin-repos.md, Part 2,
// step 12). What each panel does is said from its own README (the private
// repos phantra-resolve-plugin and phantra-premiere-plugin); a change to a
// panel's README is a change here. The Download button exists only once
// content/downloads.json marks a build live with its size and sha256
// (lib/downloads.ts); until then the panel reads "Coming soon" and links
// nothing. Premiere stays "Coming soon" until its build has been run in
// Premiere Pro 25.6+. No price is printed here: the panels spend credits only
// through the studio's own quote-and-approve.

export const metadata: Metadata = pageMeta({
  title: "Download the editor panels",
  description:
    "Phantra inside DaVinci Resolve Studio and Adobe Premiere Pro: your Library in the Media Pool, AI images, video and effects made from the timeline, priced before anything is spent.",
  path: "/download",
});

const ENTRIES = DOWNLOADS as Record<PanelId, Entry>;

type Panel = {
  id: PanelId;
  app: string;
  requires: ReactNode;
  does: { title: string; body: string }[];
};

const PANELS: Panel[] = [
  {
    id: "resolve",
    app: "DaVinci Resolve",
    requires: (
      <>
        Requires DaVinci Resolve <strong className="font-medium text-foreground">Studio</strong> 19.0.2 or newer on
        macOS. The free version of Resolve does not load Workflow Integrations.
      </>
    ),
    does: [
      {
        title: "Your Library",
        body: "Everything you have made or uploaded in Phantra. Import puts a file in the project's Phantra bin in the Media Pool; Insert also places it at the playhead.",
      },
      {
        title: "Make",
        body: "An image, a video, or an effect: a camera move, an image edit, a cut-out, an upscale, added sound, a reframe, or a clip edited with a prompt. Each shows its price in credits first.",
      },
      {
        title: "From the timeline",
        body: "Send the clip on the timeline, just the part it uses, or the frame at the playhead. Sending is free. An edit by prompt shows you one frame before you pay for the clip.",
      },
    ],
  },
  {
    id: "premiere",
    app: "Premiere Pro",
    requires: <>Requires Adobe Premiere Pro 25.6 or newer.</>,
    does: [
      {
        title: "Your Library",
        body: "Everything you have made or uploaded in Phantra, imported into the project's Phantra bin or dropped at the playhead.",
      },
      {
        title: "Make",
        body: "An image, a video, or an effect on a Library item, each priced in credits before anything is charged.",
      },
      {
        title: "From the timeline",
        body: "Send the selected clip or the frame at the playhead to Phantra, edit it, and bring the result back.",
      },
    ],
  },
];

const RESOLVE_STEPS: { title: string; body: ReactNode }[] = [
  {
    title: "Quit DaVinci Resolve",
    body: <>Unzip the download first. The installer adds the panel while Resolve is closed.</>,
  },
  {
    title: "Run install.command",
    body: (
      <>
        Double-click it. If macOS says it is from an unidentified developer, right-click it and choose Open. It asks
        for your Mac password, because Resolve keeps plugins in /Library, and takes the bridge Resolve needs from your
        own Resolve install.
      </>
    ),
  },
  {
    title: "Open the panel",
    body: (
      <>
        Start Resolve, then Workspace, Workflow Integrations, Phantra. After updating Resolve, run the installer
        again. uninstall.command removes the panel.
      </>
    ),
  },
];

const SIGN_IN: { title: string; body: ReactNode }[] = [
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
    title: "Type the code",
    body: (
      <>
        Type it on that page, signed in to your studio, and press Connect. The panel signs in by itself a few seconds
        later. Never type a code someone else sent you.
      </>
    ),
  },
  {
    title: "Disconnect any time",
    body: (
      <>
        Sign out in the panel, or remove it under Settings, Connections, Apps in the studio. No password goes into the
        editor.
      </>
    ),
  },
];

const PROSE =
  "text-[15px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4";

function DownloadBox({ download }: { download: Download }) {
  if (!download.url || download.size === null || !download.sha256) {
    return (
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <span
          aria-disabled="true"
          className="inline-flex h-10 items-center rounded-lg border border-border px-4 text-[14px] text-[#8a8a8a]"
        >
          Coming soon
        </span>
        <span className="text-[13px] text-[#8a8a8a]">Version {download.version}</span>
      </div>
    );
  }
  return (
    <div className="mt-6">
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

export default function DownloadPage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Download"
          title="Phantra inside your editor."
          dek="A panel in DaVinci Resolve and Premiere Pro: your Library on the timeline, and images, video and effects made from the clip you are cutting. Everything is priced in credits before anything is spent."
        />

        <section className="mx-auto max-w-[1200px] px-6 pb-20">
          <div className="grid gap-3 md:grid-cols-2">
            {PANELS.map((panel) => {
              const download = downloadOf(panel.id, ENTRIES);
              return (
                <article key={panel.id} className="flex flex-col rounded-[14px] border border-border bg-card p-6">
                  <span className="eyebrow">Panel</span>
                  <h2 className="serif mt-4 text-[clamp(1.5rem,3vw,2rem)]">{panel.app}</h2>
                  <p className={`mt-3 ${PROSE}`}>{panel.requires}</p>
                  <ul className="mt-5 divide-y divide-border border-y border-border">
                    {panel.does.map((item) => (
                      <li key={item.title} className="py-4">
                        <h3 className="text-[15px] font-medium text-foreground">{item.title}</h3>
                        <p className="mt-1 text-[14px] leading-relaxed text-[#afafaf]">{item.body}</p>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto">
                    <DownloadBox download={download} />
                  </div>
                </article>
              );
            })}
          </div>
          <p className={`mt-6 max-w-[70ch] ${PROSE}`}>
            A video is always held to one of your own photos, as everywhere in Phantra. Downloads from the panel go to
            your Movies folder, under Phantra, so the project can find them.
          </p>
        </section>

        <section id="install" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-6 py-20 md:grid-cols-2 md:gap-16">
            <div>
              <span className="eyebrow">DaVinci Resolve</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">Install it in three steps.</h2>
              <p className={`mt-5 max-w-[46ch] ${PROSE} text-[17px]`}>
                The panel is a Resolve Workflow Integration. The installer copies it into Resolve&apos;s plugin folder;
                nothing else on your Mac changes.
              </p>
            </div>
            <ol className="divide-y divide-border border-y border-border">
              {RESOLVE_STEPS.map((step, i) => (
                <li key={step.title} className="flex gap-5 py-5">
                  <span className="eyebrow pt-1">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3 className="text-[17px] font-medium tracking-[-0.005em] text-foreground">{step.title}</h3>
                    <p className={`mt-2 max-w-[56ch] ${PROSE}`}>{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-6 py-20 md:grid-cols-2 md:gap-16">
            <div>
              <span className="eyebrow">Sign in</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">With a code, not a password.</h2>
              <p className={`mt-5 max-w-[46ch] ${PROSE} text-[17px]`}>
                Typing the code your own panel shows is what proves the panel is yours. The sign-in is kept in your
                Mac&apos;s Keychain, and a panel left unused for 90 days asks again.
              </p>
            </div>
            <ol className="divide-y divide-border border-y border-border">
              {SIGN_IN.map((step, i) => (
                <li key={step.title} className="flex gap-5 py-5">
                  <span className="eyebrow pt-1">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3 className="text-[17px] font-medium tracking-[-0.005em] text-foreground">{step.title}</h3>
                    <p className={`mt-2 max-w-[56ch] ${PROSE}`}>{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-16">
            <p className={PROSE}>
              The panels are free to install and use with your own Phantra account, under the{" "}
              <Link href="/download/license">Phantra Plugin License</Link>. Your use of Phantra is covered by the{" "}
              <Link href="/terms">terms</Link> and the <Link href="/privacy">privacy policy</Link>. Questions:{" "}
              <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
