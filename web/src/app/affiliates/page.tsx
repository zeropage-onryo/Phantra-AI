import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { AffiliateModal, ApplyButton } from "@/components/site/affiliate-apply";
import { MARIGOLD } from "@/components/site/marigold";
import { AffiliateEstimator } from "@/components/site/affiliate-estimator";
import { AFFILIATE_TERMS as T } from "@/lib/affiliate";
import { pageMeta } from "@/lib/page-meta";

export const metadata: Metadata = pageMeta({
  title: "Affiliate program",
  description: `Earn ${T.tiers[0].percent}% to ${T.tiers[2].percent}% of what the people you bring pay Phantra, paid in cash. They get ${T.buyer_discount_percent}% off their first month.`,
  path: "/affiliates",
});

const lede = "text-[17px] leading-relaxed text-[#afafaf]";
const h2 = "serif text-[clamp(1.875rem,4vw,3rem)]";
const longest = Math.max(...T.tiers.map((t) => t.months));

const STEPS = [
  { title: "Apply", body: "Add your channel and agree to the rules. Your link is ready the moment you do, with nothing to wait on." },
  { title: "Share it", body: "Put it where you already talk about your work: video descriptions, a bio link, a newsletter, a tutorial." },
  { title: "Get paid in cash", body: `You earn on every payment your referrals make. After a ${T.hold_days}-day hold we send it by PayPal or bank transfer.` },
];

const FAQ: { q: string; a: string }[] = [
  {
    q: "When and how do I get paid?",
    a: `In cash, by PayPal or bank transfer, once your cleared balance reaches $${T.min_cash_payout_dollars}. Each commission waits ${T.hold_days} days, the refund window, then it’s yours. We look at your channel and your referrals before a first payment, so a link built to game the program doesn’t get paid.`,
  },
  {
    q: "What do the people I bring get?",
    a: `${T.buyer_discount_percent}% off their first month on a monthly plan. Yearly plans already include 20% off, so no second discount stacks on them.`,
  },
  {
    q: "What do I earn on?",
    a: "What the customer actually paid, before tax. Top-up packs and refunded payments don’t earn. A yearly plan earns the same as the months it covers.",
  },
  {
    q: "Does my rate change?",
    a: "A referral’s rate and length are set by your tier the day they first pay and stay that way. Reaching a higher tier raises what the next people you bring earn, never what you’ve already been promised.",
  },
  {
    q: "How long is my link tracked?",
    a: `${T.cookie_days} days from the click. The first link a person uses is the one that counts, and only for new accounts.`,
  },
  {
    q: "What’s not allowed?",
    a: "Signing yourself up, or people at your own address, through your own link. Paid ads on Phantra’s name or your link, or bidding on “Phantra” as a search term. Not saying you’re an affiliate where you share the link, or claiming Phantra says things it doesn’t. We can pause or end a partnership for breaking these, and commissions already earned and clear of the hold are still paid.",
  },
];

export default function AffiliatesPage() {
  return (
    <EditorialSkin style={{ "--mari": "#FFC800" } as CSSProperties}>
      <SiteHeader />
      <main className="flex-1">
        {/* hero: one big claim over a frame of real studio output */}
        <section className="px-3 pb-6 pt-[72px] sm:px-4">
          <div className="relative mx-auto flex min-h-[520px] max-w-[1400px] items-center justify-center overflow-hidden rounded-[20px] bg-card md:min-h-[600px]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/models/kling-video-generator/rooftop.jpg"
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
            />
            <div aria-hidden className="absolute inset-0 bg-[linear-gradient(180deg,rgba(11,10,8,0.55),rgba(11,10,8,0.8))]" />
            <div className="relative z-10 mx-auto flex max-w-[720px] flex-col items-center px-6 py-16 text-center">
              <h1 className="serif text-[clamp(2.75rem,8vw,5.5rem)]">Share Phantra. Get paid.</h1>
              <p className="mt-6 max-w-[48ch] text-[clamp(1rem,1.7vw,1.1875rem)] leading-normal text-[#d6d4d0]">
                Earn up to {T.tiers[2].percent}% of what the people you bring pay us, in cash, for up to {longest} months. They get{" "}
                {T.buyer_discount_percent}% off their first month.
              </p>
              <ApplyButton className={`mt-9 inline-flex h-14 items-center rounded-[12px] px-9 text-[17px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground ${MARIGOLD}`} />
              <p className="mt-4 text-[16px] text-[#d6d4d0]">Free to join. Your link is live right away.</p>
            </div>
          </div>
        </section>

        {/* three steps */}
        <section className="mx-auto max-w-[1100px] px-6 py-20 md:py-28">
          <h2 className={`${h2} text-center`}>Three steps to start earning.</h2>
          <ol className="mt-12 grid gap-4 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rounded-[14px] border border-border bg-card p-6">
                <span className="serif text-[32px] tabular-nums text-[#6f6f6f]">{i + 1}</span>
                <h3 className="mt-4 text-[18px] font-medium text-foreground">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-[#afafaf]">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* the calculator */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1100px] px-6 py-20 md:py-28">
            <div className="mx-auto max-w-[620px] text-center">
              <h2 className={h2}>See what it adds up to.</h2>
              <p className={`${lede} mt-4`}>New subscribers keep stacking on the ones already paying you, so each month lands higher than the last.</p>
            </div>
            <div className="mt-12">
              <AffiliateEstimator />
            </div>
          </div>
        </section>

        {/* the tiers, kept short */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1100px] px-6 py-20 md:py-28">
            <div className="mx-auto max-w-[620px] text-center">
              <h2 className={h2}>Bring more, earn more.</h2>
              <p className={`${lede} mt-4`}>Everyone starts on {T.tiers[0].label}. Your tier moves up on paying referrals, people who have actually subscribed.</p>
            </div>
            <ul className="mt-12 grid gap-4 md:grid-cols-3">
              {T.tiers.map((t) => (
                <li key={t.key} className="rounded-[14px] border border-border bg-card p-6">
                  <p className="text-[15px] text-[#afafaf]">{t.label}</p>
                  <p className="serif mt-2 text-[clamp(3rem,6vw,4rem)] tabular-nums text-[var(--mari,#FFC800)]">{t.percent}%</p>
                  <p className="mt-1 text-[16px] text-foreground">for {t.months} months of each referral’s payments</p>
                  <p className="mt-4 text-[16px] text-[#afafaf]">{t.min_paying === 0 ? "From day one." : `After ${t.min_paying} paying referrals.`}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* questions */}
        <section className="border-t border-border">
          <div className="mx-auto max-w-[760px] px-6 py-20 md:py-28">
            <h2 className={`${h2} text-center`}>Questions.</h2>
            <div className="mt-10 divide-y divide-border border-y border-border">
              {FAQ.map((f) => (
                <details key={f.q} className="group py-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-[17px] text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <span aria-hidden className="text-[22px] leading-none text-[#6f6f6f] transition-transform group-open:rotate-45">
                      +
                    </span>
                  </summary>
                  <p className={`${lede} mt-3 max-w-[62ch]`}>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* the last nudge. Already a partner? The same button opens your link and numbers. */}
        <section className="border-t border-border">
          <div className="mx-auto flex max-w-[620px] flex-col items-center px-6 py-20 text-center md:py-28">
            <h2 className={h2}>Ready when you are.</h2>
            <p className={`${lede} mt-4`}>Already a partner? The same button opens your link and your earnings.</p>
            <ApplyButton className={`mt-8 inline-flex h-14 items-center rounded-[12px] px-9 text-[17px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground ${MARIGOLD}`} />
            <p className="mt-8 text-[16px] text-[#afafaf]">
              Questions? <Link className="text-foreground underline underline-offset-4" href="/support">Write to support</Link>.
            </p>
          </div>
        </section>
        <AffiliateModal />
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
