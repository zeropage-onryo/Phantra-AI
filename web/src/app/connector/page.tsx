import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { FaqList } from "@/components/site/faq-list";
import { LEGAL_CONTACT } from "@/components/legal-page";
import { Button } from "@/components/ui/button";
import { CONNECTOR_NAME } from "@/lib/connect-claude";
import { pageMeta } from "@/lib/page-meta";

// The connector's public page (2026-10-11): what it does, its two
// addresses and how to add it. It is also the docs URL the two directory
// listings name (docs/directory/TWO_LISTINGS.md).
//
// Every claim was checked against the code that day, and again after PR
// #244 (add_element, a still on /mcp, draft scenes) reached main:
// - the addresses: fly.toml ZEROPAGE_MCP_RESOURCE, and the same + "/claude"
//   (app/mcp_auth.CLAUDE_SUFFIX); both answered their OAuth metadata live
// - what each address can do: src/mcp_server.py LISTED_TOOLS (thirteen
//   tools: it renders through `approve` and draws a still through
//   `generate_image`, each behind a quote) and CLAUDE_LISTED_TOOLS (nine:
//   the same minus `image_models`, `generate_image`, `approve` and `job`;
//   its `quote` returns the scene's studio link)
// - a picture becomes an element from the chat: `add_element` takes the
//   https address of an image file or one of the person's own renders,
//   draws nothing and spends no credits
// - a scene with no photo is saved as a draft and cannot be priced or
//   rendered until one of the person's element photos is on it: `write_scene`
// - writing and pricing spend nothing; credit is held before a render is
//   sent and released if it fails: the tools' own descriptions
// - a spend needs the quote's own signed, single-use token, so nothing is
//   spent without a price having been quoted; that the PERSON saw it and
//   said yes is the chat app following its instructions, which the server
//   cannot check, and the Limits list says so (2026-10-11)
// - no tool takes the conversation: neither list has `save_chat`
// - the consent page names the app and where it sends you back:
//   app/templates/oauth_consent.html
// No price, plan or rating is printed here. A change to what the connector
// does is a change to this page.
const ORIGIN = "https://api.zeropage.studio";
const CLAUDE_ADDRESS = `${ORIGIN}/mcp/claude`;
const RENDER_ADDRESS = `${ORIGIN}/mcp`;

export const metadata: Metadata = pageMeta({
  title: "Connector for Claude and ChatGPT",
  description:
    "Use Zero Page Studio from Claude or ChatGPT: open your projects, add your photos as elements, write scenes held to them, see the price in credits, and render after your yes.",
  path: "/connector",
});

const DOES: { title: string; body: string }[] = [
  {
    title: "Open your projects",
    body: "Read a project's brief and look, its scenes, the reference photos those scenes used, and its chat history.",
  },
  {
    title: "Start a project",
    body: "Give it a name, a brief and a look. It appears on your projects board in the studio.",
  },
  {
    title: "Use your elements",
    body: "The characters, products and places a scene is held to. Add them in the studio, or hand the chat a picture: the web address of an image, and it becomes an element.",
  },
  {
    title: "Write a scene",
    body: "The chat writes the scene as timed shots and saves it to your studio, in a project or on its own. With none of your photos on it, it is saved as a draft until you add one.",
  },
  {
    title: "Read it back",
    body: "Where a scene stands, its shots, the clips rendered so far, and a link that opens it in the studio.",
  },
  {
    title: "See the price first",
    body: "What the keyframes and the clip would cost in credits, on the model you ask for, beside your balance.",
  },
];

const ADDRESSES: { eyebrow: string; title: string; address: string; body: string }[] = [
  {
    eyebrow: "Claude",
    title: "Write and price. Approve in the studio.",
    address: CLAUDE_ADDRESS,
    body: "Claude writes the scene and asks what it would cost. The answer comes with a link to the scene in your studio, and you approve the render there, on its Render card, where the price is shown again. Nothing renders from the chat.",
  },
  {
    eyebrow: "ChatGPT and other clients",
    title: "Write, price, draw and render.",
    address: RENDER_ADDRESS,
    body: "Everything the Claude address does, and the making itself: after a price and your yes, the chat renders the scene or draws a still on the image model you pick. Credit is held before anything is sent and released if it fails. The chat can check on the job, and the result lands in your studio.",
  },
];

const STEPS: { title: string; body: ReactNode }[] = [
  {
    title: "Sign in to the studio once",
    body: (
      <>
        <Link href="/studio">Open the studio</Link> and sign in, so your workspace exists. Elements can be added
        there with your photos, or later from the chat.
      </>
    ),
  },
  {
    title: "Add the address",
    body: (
      <>
        In Claude, open Customize, then Connectors, then Add custom connector. Paste the Claude address and name it{" "}
        {CONNECTOR_NAME}. In another client, add the second address the way that client adds a connector.
      </>
    ),
  },
  {
    title: "Allow it",
    body: (
      <>
        Press Connect and sign in with the account you use for the studio. The studio&apos;s own page names the app
        that is asking and where it will send you back. Press Allow.
      </>
    ),
  },
  {
    title: "Ask for a scene",
    body: (
      <>
        For example: &ldquo;Add the picture at this address as a product called Bottle, then write a ten second
        scene with it in a new project called Spring launch, and tell me what it would cost.&rdquo;
      </>
    ),
  },
];

const NEVER: string[] = [
  "Spend without a price quoted first. The chat app is told to show you that price and wait for your yes, and the Studio cannot see whether it did. On the Claude address it cannot spend at all.",
  "See your password. You sign in on the studio's own page, and the app is given access to your workspace only.",
  "Reach anybody else's workspace, or hold a scene to a photo that is not one of your elements.",
  "Read files off your computer, or post anywhere. A picture reaches it as the web address of an image you give the chat, or as one of your own renders.",
  "Take your conversation. The studio receives what a tool is handed: a project's name and brief, a scene's prompt, the photos picked for it, and a picture you asked it to keep.",
];

const FAQS: { q: string; a: string }[] = [
  {
    q: "What do I need before I connect?",
    a: "A Zero Page account. A scene has to be held to at least one of your own photos before it can be priced or rendered: add elements in the studio, or give the chat the web address of an image and it is kept as one.",
  },
  {
    q: "Does using the connector cost anything?",
    a: "Opening projects, adding an element, writing a scene and pricing it spend no credits. Drawing a still or a scene's keyframes and rendering clips spend credits from your studio balance, at the price you were shown.",
  },
  {
    q: "Which address do I use?",
    a: `In Claude, ${CLAUDE_ADDRESS}: it writes and prices scenes, and you approve the render in the studio. In ChatGPT or a client where you add a connector by address, ${RENDER_ADDRESS}: it can also draw a still and start the render, each after a price and your yes.`,
  },
  {
    q: "Which models can a scene render on?",
    a: "The studio's video models: Kling, LTX, Wan, Seedance and Veo. A price can be asked for a model, a length and a frame, or left to the studio's default. On the second address a still is drawn on one of the studio's image models, which the chat can list.",
  },
  {
    q: "Where does a render go?",
    a: "A clip lands on its scene in the studio, and a clip or a still is in your Library with the prompt and the model that made it.",
  },
  {
    q: "How do I disconnect?",
    a: `Remove ${CONNECTOR_NAME} where you added it. In Claude that is Customize, then Connectors.`,
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

const PROSE =
  "text-[15px] leading-relaxed text-[#afafaf] [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-4";

export default function ConnectorPage() {
  return (
    <EditorialSkin>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSON_LD).replace(/</g, "\\u003c") }}
      />
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Connector"
          title="Your studio, inside Claude and ChatGPT."
          dek="Plan a scene in the chat with your own reference photos, see what it costs in credits, and render it in the studio. Nothing is spent until you have seen a price and said yes."
        >
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" render={<Link href="#add" />}>
              How to add it
              <ArrowRight data-icon="inline-end" className="size-4" />
            </Button>
            <Button size="lg" variant="outline" render={<Link href="/studio" />}>
              Open your studio
            </Button>
          </div>
        </PageIntro>

        <section className="mx-auto max-w-[1200px] px-6 pb-20">
          <div className="max-w-[560px]">
            <span className="eyebrow">From the chat</span>
            <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">What you can ask for.</h2>
            <p className="mt-5 text-[17px] leading-relaxed text-[#afafaf]">
              The connector is a Model Context Protocol (MCP) server for your own workspace. The chat app talks to
              it as you, after you allow it.
            </p>
          </div>
          <div className="mt-8 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {DOES.map((item) => (
              <article key={item.title} className="rounded-[14px] border border-border bg-card p-6">
                <h3 className="serif text-2xl">{item.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-[#afafaf]">{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[1200px] px-6 py-20">
            <div className="max-w-[560px]">
              <span className="eyebrow">Two addresses</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">One studio, two ways in.</h2>
              <p className="mt-5 text-[17px] leading-relaxed text-[#afafaf]">
                Both open the same projects, elements and scenes. They differ in one thing: where the render is
                approved.
              </p>
            </div>
            <div className="mt-8 grid gap-3 md:grid-cols-2">
              {ADDRESSES.map((item) => (
                <article key={item.address} className="flex flex-col rounded-[14px] border border-border bg-card p-6">
                  <span className="eyebrow">{item.eyebrow}</span>
                  <h3 className="serif mt-4 text-2xl">{item.title}</h3>
                  {/* one click selects the whole address; on a narrow card it
                      breaks between the host and the path, never mid-word */}
                  <code className="mt-5 block select-all rounded-lg border border-border bg-background px-3.5 py-3 font-mono text-[13px] text-foreground [overflow-wrap:anywhere]">
                    {ORIGIN}
                    <wbr />
                    {item.address.slice(ORIGIN.length)}
                  </code>
                  <p className="mt-5 text-[15px] leading-relaxed text-[#afafaf]">{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="add" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-6 py-20 md:grid-cols-2 md:gap-16">
            <div>
              <span className="eyebrow">How to add it</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">Four steps, once.</h2>
              <p className="mt-5 max-w-[46ch] text-[17px] leading-relaxed text-[#afafaf]">
                You add a connector from the chat app, and the studio asks you to allow it. To disconnect, remove
                it where you added it.
              </p>
            </div>
            <ol className="divide-y divide-border border-y border-border">
              {STEPS.map((step, i) => (
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
              <span className="eyebrow">Limits</span>
              <h2 className="serif mt-5 text-[clamp(1.75rem,3.5vw,2.5rem)]">What it will not do.</h2>
              <p className={`mt-5 max-w-[46ch] ${PROSE} text-[17px]`}>
                What the connector reads, sends and records is set out in the{" "}
                <Link href="/privacy">privacy policy</Link>, and the <Link href="/terms">terms</Link> cover the
                studio it reaches. Questions: <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
              </p>
            </div>
            <ul className="divide-y divide-border border-y border-border">
              {NEVER.map((line) => (
                <li key={line} className="py-5 text-[15px] leading-relaxed text-[#c6c4c0]">
                  {line}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-20">
            <h2 className="serif mb-6 text-[clamp(1.5rem,3vw,2rem)]">Questions about the connector</h2>
            <FaqList items={FAQS.map((item) => ({ q: item.q, a: <p>{item.a}</p> }))} />
          </div>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
