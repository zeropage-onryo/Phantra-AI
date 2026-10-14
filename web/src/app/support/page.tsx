import type { Metadata } from "next";
import Link from "next/link";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { LEGAL_CONTACT } from "@/components/legal-page";
import { CONNECTOR_NAME } from "@/lib/connect-claude";
import { pageMeta } from "@/lib/page-meta";

// The support URL both directory listings name (docs/directory/PORTAL_PASTE.md).
export const metadata: Metadata = pageMeta({
  title: "Support",
  description: "How to reach Phantra support, and where the answers to common questions are.",
  path: "/support",
});

export default function SupportPage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Support"
          title="Need a hand?"
          dek="Write to us and a person answers. Most questions are already answered on the pages below."
        />
        <section className="mx-auto max-w-[760px] px-6 pb-24">
          <h2 className="serif mb-4 text-[clamp(1.5rem,3vw,2rem)]">Email</h2>
          <p className="text-[17px] leading-relaxed text-[#afafaf]">
            <a className="text-foreground underline underline-offset-4" href={`mailto:${LEGAL_CONTACT}`}>
              {LEGAL_CONTACT}
            </a>
          </p>
          <h2 className="serif mb-4 mt-14 text-[clamp(1.5rem,3vw,2rem)]">Answers</h2>
          <ul className="list-disc space-y-2 pl-5 text-[17px] leading-relaxed text-[#afafaf]">
            <li>
              <Link className="text-foreground underline underline-offset-4" href="/faq">
                FAQ
              </Link>{" "}
              — how the studio works.
            </li>
            <li>
              <Link className="text-foreground underline underline-offset-4" href="/connector">
                Connector for Claude and ChatGPT
              </Link>{" "}
              — how to add it and what it can do.
            </li>
          </ul>
          <h2 className="serif mb-4 mt-14 text-[clamp(1.5rem,3vw,2rem)]">Disconnecting</h2>
          <p className="text-[17px] leading-relaxed text-[#afafaf]">
            Remove {CONNECTOR_NAME} where you added it. In Claude that is Customize, then Connectors.
          </p>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
