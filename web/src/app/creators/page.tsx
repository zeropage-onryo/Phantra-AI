import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import { Coins, Link2, Megaphone, MessagesSquare, Rocket, Users } from "lucide-react";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Marquee } from "@/components/ui/marquee";
import { CreatorApplyButton, CreatorModal } from "@/components/site/creator-apply";
import { MARIGOLD } from "@/components/site/marigold";
import { pageMeta } from "@/lib/page-meta";

export const metadata: Metadata = pageMeta({
  title: "Phantra Creators",
  description:
    "A small program for filmmakers, designers and AI-native creators who share their work in public. Credits to make more, early access to new tools, and a direct line to the team.",
  path: "/creators",
});

const lede = "text-[17px] leading-relaxed text-[#afafaf]";
const h2 = "serif text-[clamp(1.875rem,4vw,3rem)]";
const pill =
  "inline-flex h-10 items-center rounded-full border border-border px-4 text-[15px] text-[#d6d4d0] transition hover:border-[#6f6f6f] hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground";

// Real output from the studio, already on the site's model pages.
const ROW_ONE = [
  "kling-video-generator/rooftop.jpg",
  "flux-image-generator/glasshouse.jpg",
  "seedance-video-generator/moto-720p.jpg",
  "nano-banana-image-generator/market.jpg",
  "kling-video-generator/dock.jpg",
  "ideogram-image-generator/neon.jpg",
  "ltx-video-generator/diver.jpg",
  "gpt-image-generator/hero.jpg",
];
const ROW_TWO = [
  "flux-image-generator/suit.jpg",
  "kling-video-generator/boxer.jpg",
  "nano-banana-image-generator/honey.jpg",
  "seedance-video-generator/kitchen.jpg",
  "flux-image-generator/stairwell.jpg",
  "kling-video-generator/dancer.jpg",
  "ideogram-image-generator/magazine.jpg",
  "ltx-video-generator/ramen.jpg",
];

const BENEFITS = [
  { icon: Coins, title: "Credits to create more", body: "Phantra credits each month, so you can make, test and explore without counting every render.", wide: true },
  { icon: Rocket, title: "Early access", body: "Try new tools, models and features before they reach everyone else." },
  { icon: Link2, title: "Your own link", body: "Earn when people you send sign up and subscribe, on the same terms as the open affiliate program." },
  { icon: Megaphone, title: "Seen by our audience", body: "Standout work gets featured across Phantra’s own channels." },
  { icon: Users, title: "A space for creators", body: "A private place to swap workflows and see what the others are making." },
  { icon: MessagesSquare, title: "A direct line to us", body: "Tell us what’s missing and what you’d change. The people who build Phantra read it.", wide: true },
];

const STEPS = [
  { title: "Apply", body: "Share where you post your work and tell us a little about it. It takes a few minutes." },
  { title: "We read every one", body: "We pick a small group, based on the work and how well it fits Phantra. If there’s a fit, you hear from us by email." },
  { title: "Create in the open", body: "Use your credits, try new features early, post what you make with Phantra, and tell us what works and what doesn’t." },
];

const LOOK_FOR = [
  { title: "A point of view", body: "Work that looks like it came from you, not from a prompt anyone could type." },
  { title: "Work shared in public", body: "Posts, reels, breakdowns and films people can see, process included." },
  { title: "Real use of the tool", body: "Filmmakers, designers, ad makers and fashion creators who’d use Phantra for actual projects." },
  { title: "Useful feedback", body: "You tell us plainly what’s working, what isn’t, and what you’d build next." },
];

const FAQ: { q: string; a: string }[] = [
  {
    q: "Is there a follower minimum?",
    a: "No. We look at the work and how it fits Phantra, not the size of your audience.",
  },
  {
    q: "How is this different from the affiliate program?",
    a: "The affiliate program is open to everyone: apply, get a link, earn on referrals. Phantra Creators is a small group we choose, with credits, early access and a direct line to the team on top. Creators also have their own affiliate link.",
  },
  {
    q: "What do I have to do?",
    a: "Use Phantra for your own projects, share some of what you make in public, say when a post is part of the program, and tell us honestly what works and what doesn’t. There’s no post quota and you don’t need to say anything you don’t believe.",
  },
  {
    q: "How many credits do I get?",
    a: "A monthly amount, set per creator, and it may change as the program grows. We’ll tell you the number when you’re accepted.",
  },
  {
    q: "Do I need a Phantra account?",
    a: "Yes. You apply from your account, which is free to create. Creators work inside Phantra, and it keeps your application tied to you.",
  },
  {
    q: "Can I leave, or can you end my place?",
    a: "Either of us can. We may end a place if the guidelines aren’t followed or the credits aren’t being used.",
  },
];

export default function CreatorsPage() {
  return (
    <EditorialSkin style={{ "--mari": "#F3F48B" } as CSSProperties}>
      <SiteHeader />
      <main className="flex-1">
        {/* hero */}
        <section className="px-3 pb-6 pt-[72px] sm:px-4">
          <div className="relative mx-auto flex min-h-[460px] max-w-[1400px] items-center justify-center overflow-hidden rounded-[20px] bg-card md:min-h-[520px]">
            <div
              aria-hidden
              className="absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_0%,rgba(243,244,139,0.30),rgba(110,112,50,0.16)_42%,rgba(11,10,8,0)_72%)]"
            />
            <div aria-hidden className="absolute inset-0 bg-[linear-gradient(180deg,rgba(11,10,8,0.1),rgba(11,10,8,0.85))]" />
            <div className="relative z-10 mx-auto flex max-w-[720px] flex-col items-center px-6 py-16 text-center">
              <h1 className="serif text-[clamp(2.75rem,8vw,5.5rem)]">Phantra Creators</h1>
              <p className="mt-6 max-w-[44ch] text-[clamp(1.0625rem,1.8vw,1.25rem)] leading-normal text-[#e4e2de]">
                Join the creators shaping what’s next with Phantra.
              </p>
              <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
                <CreatorApplyButton
                  className={`inline-flex h-14 items-center rounded-[12px] px-9 text-[17px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground ${MARIGOLD}`}
                >
                  Apply
                </CreatorApplyButton>
                <a href="#benefits" className="inline-flex h-14 items-center rounded-[12px] border border-[#6f6f6f] px-8 text-[17px] text-foreground transition hover:border-foreground">
                  Benefits
                </a>
              </div>
              <p className="mt-8 max-w-[52ch] text-[16px] leading-relaxed text-[#d6d4d0]">
                For filmmakers, designers, ad makers and AI-native creators who share their work in public. Credits to make more, early access, and a direct line to the team.
              </p>
            </div>
          </div>
        </section>

        {/* work from the studio */}
        <section aria-label="Work made with Phantra" className="overflow-hidden py-6">
          <div className="space-y-3 motion-reduce:[&_.animate-marquee]:![animation:none]">
            <Marquee className="[--duration:70s] [--gap:0.75rem]" repeat={3}>
              {ROW_ONE.map((src) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={src} src={`/models/${src}`} alt="" loading="lazy" className="h-[150px] w-auto rounded-[12px] object-cover md:h-[190px]" />
              ))}
            </Marquee>
            <Marquee reverse className="[--duration:80s] [--gap:0.75rem]" repeat={3}>
              {ROW_TWO.map((src) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={src} src={`/models/${src}`} alt="" loading="lazy" className="h-[150px] w-auto rounded-[12px] object-cover md:h-[190px]" />
              ))}
            </Marquee>
          </div>
          <p className="mt-4 text-center text-[15px] text-[#afafaf]">Made with Phantra</p>
        </section>

        {/* section nav */}
        <nav aria-label="On this page" className="mx-auto flex max-w-[1100px] flex-wrap items-center justify-center gap-2 px-6 py-8">
          <a className={pill} href="#what">What it is</a>
          <a className={pill} href="#benefits">Benefits</a>
          <a className={pill} href="#how">How it works</a>
          <a className={pill} href="#who">Who applies</a>
          <a className={pill} href="#faq">FAQ</a>
        </nav>

        {/* what it is */}
        <section id="what" className="scroll-mt-24">
          <div className="mx-auto grid max-w-[1000px] gap-10 px-6 py-20 md:grid-cols-[1fr_1.1fr] md:gap-16 md:py-28">
            <h2 className={`${h2} max-w-[14ch]`}>A program for creators making work with Phantra</h2>
            <div className="space-y-5 md:border-l md:border-border md:pl-12">
              <p className="text-[19px] leading-snug text-foreground">A small program for creators who make and share their work in public.</p>
              <p className={lede}>
                We give a chosen few more room to experiment with Phantra, early access to new tools, and a link of their own. In return we ask for honest feedback.
              </p>
              <p className={lede}>
                It goes both ways. As you share what you’re making, we put Phantra’s reach behind it and give you room to take on more ambitious projects.
              </p>
            </div>
          </div>
        </section>

        {/* benefits */}
        <section id="benefits" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto max-w-[1100px] px-6 py-20 md:py-28">
            <h2 className={`${h2} text-center`}>Everything you get as a creator</h2>
            <ul className="mt-12 grid gap-4 md:grid-cols-12">
              {BENEFITS.map((b) => {
                const Icon = b.icon;
                return (
                  <li key={b.title} className={`rounded-[14px] border border-border bg-card p-6 ${b.wide ? "md:col-span-6" : "md:col-span-3"}`}>
                    <span className="grid size-10 place-items-center rounded-[10px] bg-secondary text-[var(--mari,#F3F48B)]">
                      <Icon aria-hidden className="size-5" />
                    </span>
                    <h3 className="mt-5 text-[18px] font-medium text-foreground">{b.title}</h3>
                    <p className="mt-2 text-[16px] leading-relaxed text-[#afafaf]">{b.body}</p>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* how it works */}
        <section id="how" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto max-w-[1100px] px-6 py-20 md:py-28">
            <h2 className={`${h2} text-center`}>How it works</h2>
            <ol className="mt-12 grid gap-4 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <li key={s.title} className="rounded-[14px] border border-border bg-card p-6">
                  <span className="serif text-[32px] tabular-nums text-[#6f6f6f]">{i + 1}</span>
                  <h3 className="mt-4 text-[18px] font-medium text-foreground">{s.title}</h3>
                  <p className="mt-2 text-[16px] leading-relaxed text-[#afafaf]">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* who applies */}
        <section id="who" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto max-w-[1000px] px-6 py-20 md:py-28">
            <div className="mx-auto max-w-[620px] text-center">
              <h2 className={h2}>Who should apply</h2>
              <p className={`${lede} mt-4`}>You don’t need a big audience. You need good work and something to say about it.</p>
            </div>
            <dl className="mt-12 grid gap-x-12 gap-y-8 md:grid-cols-2">
              {LOOK_FOR.map((l) => (
                <div key={l.title} className="border-t border-border pt-5">
                  <dt className="text-[18px] font-medium text-foreground">{l.title}</dt>
                  <dd className="mt-2 text-[16px] leading-relaxed text-[#afafaf]">{l.body}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* questions */}
        <section id="faq" className="scroll-mt-24 border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-20 md:py-28">
            <h2 className={`${h2} text-center`}>Questions</h2>
            <div className="mt-10 divide-y divide-border border-y border-border">
              {FAQ.map((f) => (
                <details key={f.q} className="group py-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-[17px] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <span aria-hidden className="text-[22px] leading-none text-[#6f6f6f] transition-transform group-open:rotate-45">
                      +
                    </span>
                  </summary>
                  <p className={`${lede} mt-3`}>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* close */}
        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[760px] flex-col items-center px-6 py-20 text-center md:py-28">
            <h2 className={h2}>Ready when you are.</h2>
            <p className={`${lede} mt-4 max-w-[46ch]`}>
              Just want a link to share? The{" "}
              <Link href="/affiliates" className="text-foreground underline underline-offset-4">
                affiliate program
              </Link>{" "}
              is open to everyone.
            </p>
            <CreatorApplyButton
              className={`mt-9 inline-flex h-14 items-center rounded-[12px] px-9 text-[17px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground ${MARIGOLD}`}
            >
              Apply
            </CreatorApplyButton>
          </div>
        </section>
      </main>
      <SiteFooter />
      <CreatorModal />
    </EditorialSkin>
  );
}
