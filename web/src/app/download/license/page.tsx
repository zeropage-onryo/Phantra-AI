import type { Metadata } from "next";
import { readFileSync } from "node:fs";
import path from "node:path";
import Link from "next/link";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { LEGAL_CONTACT } from "@/components/legal-page";
import { pageMeta } from "@/lib/page-meta";

// The editor panels' license, word for word. The panels' repos are private, so
// this is where /download links it. content/plugin-license.txt is a copy of the
// LICENSE in phantra-resolve-plugin and phantra-premiere-plugin (the same file
// in both); a change there is a change here. Read once at build: the page is
// static.

export const metadata: Metadata = pageMeta({
  title: "Phantra Plugin License",
  description: "The license the Phantra panels for DaVinci Resolve and Premiere Pro are installed under.",
  path: "/download/license",
});

const TEXT = readFileSync(path.join(process.cwd(), "src/content/plugin-license.txt"), "utf8");

export default function PluginLicensePage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <article className="mx-auto max-w-2xl px-6 pb-28 pt-36">
          <span className="eyebrow block">Legal</span>
          <h1 className="serif mt-5 text-[clamp(2.25rem,5vw,3.5rem)]">Phantra Plugin License</h1>
          <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4">
            The license for the panels on the <Link href="/download">download page</Link>, as it ships in each
            download. Questions: <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
          </p>
          <pre className="mt-10 whitespace-pre-wrap border-t border-border pt-9 font-mono text-[13px] leading-relaxed text-[#c6c4c0]">
            {TEXT}
          </pre>
        </article>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
