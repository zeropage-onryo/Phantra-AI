"use client";

import { useId, useState } from "react";
import { AFFILIATE_TERMS as T } from "@/lib/affiliate";
import { monthlyEarnings } from "@/lib/affiliate-estimate";
import { PLANS } from "@/lib/catalog";
import { ApplyButton } from "@/components/site/affiliate-apply";

const MONTHS = 12;

const money = (n: number) =>
  n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: n >= 1000 ? 0 : 2,
    maximumFractionDigits: n >= 1000 ? 0 : 2,
  });

// The calculator: new subscribers per month and the plan they take, a
// twelve-bar chart of what lands each month, and the year's total.
export function AffiliateEstimator() {
  const [perMonth, setPerMonth] = useState(5);
  const [planKey, setPlanKey] = useState(PLANS[0].key);
  const id = useId();
  const plan = PLANS.find((p) => p.key === planKey) ?? PLANS[0];
  const { byMonth, total } = monthlyEarnings(T.tiers, perMonth, MONTHS, plan.monthly_usd, T.buyer_discount_percent);
  const peak = Math.max(...byMonth, 1);

  return (
    <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
      <div className="flex flex-col gap-4">
        <div className="rounded-[14px] border border-border bg-card p-6">
          <div className="flex items-baseline justify-between gap-3">
            <label htmlFor={`${id}-n`} className="text-[15px] text-[#afafaf]">
              New subscribers a month
            </label>
            <output htmlFor={`${id}-n`} className="serif text-[28px] tabular-nums">
              {perMonth}
            </output>
          </div>
          <input
            id={`${id}-n`}
            type="range"
            min={1}
            max={40}
            value={perMonth}
            onChange={(ev) => setPerMonth(Number(ev.target.value))}
            className="mt-4 h-1.5 w-full cursor-pointer accent-[var(--mari,#F3F48B)]"
          />

          <p className="mt-6 text-[15px] text-[#afafaf]">Plan they pick</p>
          <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Plan your referrals subscribe to">
            {PLANS.map((p) => (
              <button
                key={p.key}
                type="button"
                role="radio"
                aria-checked={p.key === plan.key}
                onClick={() => setPlanKey(p.key)}
                className={`rounded-lg border px-3.5 py-2 text-[15px] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground ${
                  p.key === plan.key ? "border-[var(--mari,#F3F48B)] bg-[var(--mari,#F3F48B)] text-[#0b0a08]" : "border-border text-[#afafaf] hover:border-[#565553] hover:text-foreground"
                }`}
              >
                {p.name} ${p.monthly_usd}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-[14px] bg-[var(--mari,#F3F48B)] p-6 text-[#0b0a08]">
          <div>
            <p className="text-[16px] opacity-75">Estimated, first 12 months</p>
            <p className="serif mt-1 text-[clamp(2.25rem,5vw,3rem)] tabular-nums" aria-live="polite">
              {money(total)}
            </p>
          </div>
          <ApplyButton className="inline-flex h-12 shrink-0 items-center rounded-[10px] bg-[#0b0a08] px-5 text-[16px] font-medium text-foreground transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0b0a08]" />
        </div>
      </div>

      <figure className="flex min-h-[320px] flex-col rounded-[14px] border border-border bg-card p-6">
        <figcaption className="text-[15px] text-[#afafaf]">What lands each month</figcaption>
        <div className="mt-6 flex flex-1 items-end gap-1.5 sm:gap-2.5" role="img" aria-label={`Monthly commission, month 1 to 12, rising from ${money(byMonth[0])} to ${money(byMonth[MONTHS - 1])}`}>
          {byMonth.map((v, i) => (
            <div key={i} className="flex h-full flex-1 flex-col justify-end" title={`Month ${i + 1}: ${money(v)}`}>
              <div
                className="w-full rounded-t-[4px] bg-gradient-to-t from-[var(--mari,#F3F48B)]/25 to-[var(--mari,#F3F48B)]"
                style={{ height: `${Math.max(3, (v / peak) * 100)}%` }}
              />
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-1.5 text-[15px] text-[#9d9a95] sm:gap-2.5" aria-hidden>
          {byMonth.map((_, i) => (
            <span key={i} className="flex-1 text-center tabular-nums">
              {i + 1}
            </span>
          ))}
        </div>
      </figure>

      <p className="text-[15px] leading-relaxed text-[#9d9a95] lg:col-span-2">
        An estimate. It assumes everyone stays subscribed for the full term on monthly billing, with {T.buyer_discount_percent}% off their first month, and
        it moves you up the tiers as your referrals add up. Paid after a {T.hold_days}-day hold. Your dashboard shows the real numbers.
      </p>
    </div>
  );
}
