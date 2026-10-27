import type { Metadata } from "next";
import Link from "next/link";
import { EditorialSkin } from "@/components/editorial-skin";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageIntro } from "@/components/site/page-intro";
import { AffiliatePanel } from "@/components/site/affiliate-panel";
import { AFFILIATE_TERMS as T } from "@/lib/affiliate";
import { pageMeta } from "@/lib/page-meta";

export const metadata: Metadata = pageMeta({
  title: "Affiliate program",
  description: `Earn ${T.tiers[0].percent}% to ${T.tiers[2].percent}% of what the people you bring pay Phantra. They get ${T.buyer_discount_percent}% off their first month.`,
  path: "/affiliates",
});

const h2 = "serif mb-4 mt-14 text-[clamp(1.5rem,3vw,2rem)]";
const p = "text-[17px] leading-relaxed text-[#afafaf]";

export default function AffiliatesPage() {
  return (
    <EditorialSkin>
      <SiteHeader />
      <main className="flex-1">
        <PageIntro
          eyebrow="Affiliate program"
          title="Get paid for the people you bring."
          dek={`Share Phantra with your audience. They get ${T.buyer_discount_percent}% off their first month; you earn ${T.tiers[0].percent}% to ${T.tiers[2].percent}% of what they pay.`}
        />
        <section className="mx-auto max-w-[760px] px-6 pb-24">
          <h2 className="serif mb-4 text-[clamp(1.5rem,3vw,2rem)]">What you earn</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] border-collapse text-left text-[16px]">
              <thead>
                <tr className="border-b border-border text-[#afafaf]">
                  <th className="py-3 pr-4 font-normal">Tier</th>
                  <th className="py-3 pr-4 font-normal">You earn</th>
                  <th className="py-3 pr-4 font-normal">For</th>
                  <th className="py-3 font-normal">How you get there</th>
                </tr>
              </thead>
              <tbody>
                {T.tiers.map((t) => (
                  <tr key={t.key} className="border-b border-border">
                    <td className="py-3 pr-4 text-foreground">{t.label}</td>
                    <td className="py-3 pr-4 text-foreground">{t.percent}%</td>
                    <td className="py-3 pr-4 text-[#afafaf]">{t.months} months of each referral’s payments</td>
                    <td className="py-3 text-[#afafaf]">{t.min_paying === 0 ? "When you’re approved" : `${t.min_paying} paying referrals`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={`${p} mt-4`}>
            A referral’s rate and length are set by your tier the day they first pay, and stay that way — reaching a higher tier
            raises what the <em>next</em> people you bring earn, never what you’ve already been promised. A yearly plan earns the same as
            the months it covers.
          </p>

          <h2 className={h2}>How it works</h2>
          <ol className={`${p} list-decimal space-y-2 pl-5`}>
            <li>Apply below. A person reads your channel and answers by email.</li>
            <li>Once approved you get a link. Anyone who signs up from it within {T.cookie_days} days is yours.</li>
            <li>They get {T.buyer_discount_percent}% off their first month on a monthly plan.</li>
            <li>When they pay, your commission is held for {T.hold_days} days (the refund window), then paid.</li>
          </ol>

          <h2 className={h2}>How you’re paid</h2>
          <p className={p}>
            By default as Phantra credits (1 credit = 1¢) on your own account, good for {T.credit_expiry_months} months — use them to make
            your own videos. Cash by bank or PayPal is available to partners we’ve worked with for a while, in payouts of ${T.min_cash_payout_dollars} or more.
          </p>

          <h2 className={h2}>The rules</h2>
          <ul className={`${p} list-disc space-y-2 pl-5`}>
            <li>No signing yourself up, or people at your own address, through your own link.</li>
            <li>No paid ads on Phantra’s name or on your link, and no bidding on “Phantra” as a search term.</li>
            <li>Commission is on what the customer actually paid, before tax. Top-up packs and refunded payments don’t earn.</li>
            <li>Say you’re an affiliate where you share the link. Don’t claim Phantra says things it doesn’t.</li>
            <li>We can pause or end a partnership for breaking these; commissions already earned and clear of the hold are still paid.</li>
          </ul>

          <h2 className={h2}>Apply</h2>
          <AffiliatePanel />

          <p className={`${p} mt-14`}>
            Questions? <Link className="text-foreground underline underline-offset-4" href="/support">Write to support</Link>.
          </p>
        </section>
      </main>
      <SiteFooter />
    </EditorialSkin>
  );
}
