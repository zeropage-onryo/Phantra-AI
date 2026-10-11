import type { Metadata } from "next";
import Link from "next/link";
import { LEGAL_CONTACT, LegalPage, type LegalSection } from "@/components/legal-page";
import { pageMeta } from "@/lib/page-meta";

// Ported 2026-09-17 from the policy the API origin serves
// (app/templates/privacy.html -- the URL already on file with the OAuth app
// registrations). Rewritten 2026-10-03 against what the product actually
// does now: open sign-up with a trial grant (2026-09-24), Stripe billing
// (2026-09-18), the Serper image search behind the Guide, the optional
// ChatGPT / Claude sign-in, and BYOK gone (2026-09-26). The research
// accounts (Instagram, Pinterest, YouTube) are the operator's own, never a
// member's, and the policy says so now. A change to one copy should be
// made to the other.
//
// 2026-10-11: the connector (a chat app such as Claude or ChatGPT working in
// a person's workspace through /mcp) had no words here, and both app
// directories ask for a policy that covers it. Added: the section
// "Connecting a chat app", a line under "What's collected", the connector in
// the OpenAI / Anthropic line, and how to disconnect under "Retention &
// control". Each sentence was checked against the code that day:
// src/mcp_server.py (what the listed tools read, write and answer),
// app/mcp_auth.py + app/oauth_consent.py (the token is Supabase's and is not
// kept; the Allow page names the app), src/mcp_connections.py (what is
// recorded, and that a disconnect is never seen), app/mcp_mount.py (the
// rate limit), refbin.fetch_public_image (a picture added by address).

export const metadata: Metadata = pageMeta({
  title: "Privacy Policy",
  description:
    "What Zero Page collects, why, and how it is handled — across the studio itself and the third-party services it connects to.",
  path: "/privacy",
});

const SECTIONS: LegalSection[] = [
  {
    title: "What this is",
    body: (
      <p>
        Zero Page (&ldquo;the Studio&rdquo;) is an AI pre-production studio: it turns ideas, scripts and
        reference photography into scene prompts, keyframes and AI-generated video. It is operated by
        Michael Massaad, trading as Zero Page Films, from the United States. Anyone can sign up; a new
        workspace starts with a small one-time grant of trial credits, and everything beyond that is
        paid for through the plans on the <Link href="/pricing">pricing page</Link>.
      </p>
    ),
  },
  {
    title: "Signing in",
    body: (
      <>
        <p>
          Signing in uses Supabase Auth, either by email and password or through Google or Discord.
          Zero Page never sees or stores your password with those providers. When you sign in with
          Google or Discord, the Studio receives only your basic profile: your email address, display
          name and profile picture. They are used to create and identify your account and for nothing
          else. Zero Page&apos;s use of information received from Google APIs adheres to the{" "}
          <a
            href="https://developers.google.com/terms/api-services-user-data-policy"
            target="_blank"
            rel="noreferrer"
          >
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements.
        </p>
        <p>
          A session is kept in a single signed, HTTP-only cookie on your device, valid for 30 days;
          signing out clears it. One further cookie remembers which workspace you had open, and your
          browser&apos;s own storage keeps an unsent draft so it survives a reload. Zero Page sets no
          advertising or tracking cookies and loads no analytics scripts.
        </p>
      </>
    ),
  },
  {
    title: "What's collected",
    body: (
      <ul>
        <li>
          <strong>Account</strong> — email address, display name, profile picture, an account
          identifier, and which workspaces you belong to.
        </li>
        <li>
          <strong>Production material</strong> — the photos, reference images, audio and video you
          upload; the characters, props and places you add; and the ideas, scene prompts,
          keyframes, rendered clips and cuts produced from them. A web link you paste into the
          Guide is fetched once, by the Studio, to read that page&apos;s own preview image.
        </li>
        <li>
          <strong>Billing</strong> — your plan, your credit balance and a ledger of what each render
          and still cost. Card details are entered on Stripe&apos;s pages and held by Stripe; the
          Studio stores a Stripe customer identifier and the email on it, never a card number.
        </li>
        <li>
          <strong>Connected model accounts</strong> — optionally, your own ChatGPT or Claude sign-in,
          if you connect one to write with. The signed-in session those providers issue is kept on
          the Studio&apos;s server, scoped to your account, used only when you ask that model to
          work, and removed when you press Disconnect.
        </li>
        <li>
          <strong>Chat app connections</strong> — if you connect a chat app to the Studio, the name
          that app gave, the site it sent you back to, when you allowed it and when it was last
          used. See &ldquo;Connecting a chat app&rdquo; below.
        </li>
        <li>
          <strong>Usage</strong> — basic operational data (timestamps, error logs, model-call counts
          and their cost) used to keep the pipeline running, meter spend and grade output quality.
        </li>
      </ul>
    ),
  },
  {
    title: "Third-party services",
    body: (
      <>
        <p>
          The Studio relies on a small set of providers to function, each under its own privacy
          policy:
        </p>
        <ul>
          <li>
            <strong>Supabase</strong> — authentication and database storage. The sign-in step may
            be served under a zeropage.studio address or a supabase.co one; both are this project.
          </li>
          <li>
            <strong>Google (Gemini API)</strong> — writing and judging scenes, describing the photos
            you upload, and drawing keyframes and reference sheets from them.
          </li>
          <li>
            <strong>fal.ai</strong> — video rendering. When you approve a render, the shot&apos;s
            prompt and its reference images are sent to fal.ai, which runs the model you picked
            (from Kling, ByteDance, Lightricks, Alibaba or Google). When you index footage in the
            editor, a clip&apos;s speech is transcribed there too.
          </li>
          <li>
            <strong>Serper</strong> — the web image search behind the Guide&apos;s reference
            suggestions. It receives the search text only, never your material.
          </li>
          <li>
            <strong>Stripe</strong> — payments and subscriptions.
          </li>
          <li>
            <strong>Cloudflare R2</strong> — storage for reference images and rendered media.
          </li>
          <li>
            <strong>OpenAI and Anthropic</strong> — only if you connect your own ChatGPT or Claude
            account to write with, and only for the work you send to it; or if you connect their
            chat app to the Studio, in which case they receive what the connector answers (see
            &ldquo;Connecting a chat app&rdquo;).
          </li>
          <li>
            <strong>Vercel and Fly.io</strong> — application hosting.
          </li>
        </ul>
        <p className="text-muted-foreground">
          The Studio&apos;s research scout also reads public feeds and the operator&apos;s own
          connected Instagram, Pinterest and YouTube accounts for visual reference. It never reads
          a member&apos;s social accounts: the Studio asks for no access to them. None of the
          providers above receive more than what is needed to perform their function, and Zero
          Page does not authorize any of them to use Studio data for advertising.
        </p>
      </>
    ),
  },
  {
    title: "Connecting a chat app",
    body: (
      <>
        <p>
          The Studio has a <Link href="/connector">connector</Link>: an address you can give to a
          chat app such as Claude or ChatGPT so that it can work in your workspace. Nothing is
          connected until you add that address in the chat app yourself, sign in to the Studio, and
          press Allow on a page that names the app that is asking. The chat app is then issued an
          access token by Supabase Auth. The Studio checks that token on every request and does not
          keep it, and it never sees the password of your chat account.
        </p>
        <p>
          <strong>What the chat app can do.</strong> While it is connected it can read your
          projects (their briefs and looks, their scenes, the reference photos those scenes used,
          and the conversation saved with a project), your elements and their photos, your scenes
          with the stills and clips made for them, and your credit balance when it asks a price. It
          can start a project, add a picture as an element, and save a scene it wrote. On the
          address that renders, it can also draw a still or render a scene, each only after showing
          you a price. It reaches your own workspace and no one else&apos;s.
        </p>
        <p>
          <strong>What leaves the Studio.</strong> Whatever the connector answers is sent to the
          chat app, and so to the company that runs it: Anthropic for Claude, OpenAI for ChatGPT.
          That includes text from your projects and scenes, and links to your images and clips.
          From there it is handled under that company&apos;s privacy policy, not this one. Connect a
          chat app only if you are content for it to see that material.
        </p>
        <p>
          <strong>What the Studio receives.</strong> Only what the chat app hands to a tool: a
          project&apos;s name, brief and look; a scene&apos;s text and the photos chosen for it; an
          element&apos;s name and notes; and the web address of a picture you asked it to keep. The
          connector has no tool that takes the conversation itself. A picture added by its address
          is fetched once by the Studio from that address, stored with your elements, and described
          by the Gemini API like any photo you upload.
        </p>
        <p>
          <strong>What is recorded.</strong> That a connection was allowed: the name the app gave,
          the site it sent you back to, when you allowed it and when it was last used. Requests
          are counted for a short time to limit their rate. Projects, elements, scenes, stills and
          clips made through the connector are kept like any others in your workspace.
        </p>
      </>
    ),
  },
  {
    title: "What doesn't happen",
    body: (
      <p className="border-l-2 border-primary bg-card/60 px-5 py-4 text-muted-foreground">
        Zero Page does not sell data, run ads, train models on your material, or share your media,
        images or account details with data brokers or marketers. Nothing is posted anywhere on
        your behalf: every render lands in your own Library, and publishing is an explicit action a person
        takes.
      </p>
    ),
  },
  {
    title: "Retention & control",
    body: (
      <p>
        Production material and account data are kept for as long as your account is active.
        Deleting a render in the Studio removes it from your library at once; the file itself is
        kept until your account is deleted, so a scene that used it keeps playing. You can
        disconnect a connected model account at any time from its settings. To disconnect a chat
        app, remove the connector in that app (in Claude: Customize, then Connectors): the Studio
        is not told when you do, cannot disconnect it for you, and keeps its record that the
        connection was made until you ask for it to be removed. You can ask for your account and
        all of its data to be deleted — see contact below.
      </p>
    ),
  },
  {
    title: "Children",
    body: (
      <p>
        Zero Page is a professional production tool and is not directed at or knowingly used by
        children under 13.
      </p>
    ),
  },
  {
    title: "Changes",
    body: (
      <p>
        If this policy changes materially, the effective date above will be updated. Continued use
        of the Studio after a change means you accept the revised policy.
      </p>
    ),
  },
  {
    title: "Contact",
    body: (
      <p>
        Questions about this policy or your data can be sent to{" "}
        <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
      </p>
    ),
  },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      dek="What Zero Page collects, why, and how it is handled — across the studio itself and the third-party services it connects to."
      effective="11 Oct 2026"
      sections={SECTIONS}
    />
  );
}
