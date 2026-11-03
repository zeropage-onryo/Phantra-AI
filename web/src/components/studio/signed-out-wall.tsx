"use client";

/* The page a signed-out visitor sees in place of a studio page that needs
   an account (2026-11-03, QA 2026-11-02 P14). Those pages used to fire
   their reads, get 401s and print the server's "sign in first" in red mono
   with nothing else on the screen. Now: what the page is for, the two
   doors (sign up, log in) coming back to this same page, and a way to try
   Create first, which takes a prompt signed out.

   Drawn by the shell (WALLED in shell.tsx), so a page's own code never
   runs signed out. Create, Image and Video are not walled: their boxes
   take a prompt and open the sign-up sheet on the button. */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { goToSignIn } from "@/lib/api";
import type { ViewId } from "@/components/studio/shell";

const COMPOSE_HOME = "/studio";

const COPY: Partial<Record<ViewId, { title: string; line: string }>> = {
  projects: { title: "Your projects", line: "A brief, a look and the scenes of one piece of work, kept together." },
  assets: { title: "Everything you make", line: "Every still and clip you make lands here, with effects, download and share." },
  elements: { title: "Your elements", line: "Characters, products and places from your own photos, so every shot keeps the same face." },
  brand: { title: "Brand kits", line: "One client's logo, palette, fonts and voice, picked by a project or a chat." },
  calendar: { title: "Your calendar", line: "Plan posts to your own accounts and see what goes out, where and when." },
  ads: { title: "Ad Studio", line: "Pick a format and your product, write a short brief, and make the ad in Create." },
  renders: { title: "Your renders", line: "What is rendering and what is done." },
  cut: { title: "The editor", line: "Your clips on a timeline, cut and exported to MP4." },
};

export function SignedOutWall({ view }: { view: ViewId }) {
  const here = usePathname() || COMPOSE_HOME;
  const copy = COPY[view] ?? { title: "Your studio", line: "Everything you make in Phantra, in one place." };
  return (
    <section className="view zwall" aria-labelledby="zwall-h">
      <div className="zwall-card">
        <h1 id="zwall-h">{copy.title}</h1>
        <p>{copy.line}</p>
        <p className="zwall-ask">Sign up to start. It&apos;s free, and new accounts get credits to try it.</p>
        <div className="zwall-doors">
          <button type="button" className="zbtn pri" onClick={() => goToSignIn("signup", here)}>
            Sign up
          </button>
          <button type="button" className="zbtn" onClick={() => goToSignIn(undefined, here)}>
            Log in
          </button>
        </div>
        <p className="zwall-try">
          Or <Link href={COMPOSE_HOME}>describe an idea in Create</Link> first.
        </p>
      </div>
    </section>
  );
}
