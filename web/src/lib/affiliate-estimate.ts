// What a partner would earn, worked out the way the server books it
// (src/affiliates.py): each referral's tier is fixed the day they first pay,
// by how many paying referrals the partner already has; commission is the
// tier's percent of what the customer actually paid, for the tier's months.
// The referred buyer's first monthly payment carries the buyer discount.
// A estimate for the page's calculator -- the real numbers are the server's.

export type EstimateTier = { key: string; label: string; percent: number; months: number; min_paying: number };

export type Estimate = {
  /** total commission in dollars across every referral, hold ignored */
  total: number;
  /** the tier the Nth referral (1-based) is booked at */
  tierAt: (n: number) => EstimateTier;
  /** the tier of the most recent referral */
  last: EstimateTier;
  /** how much of the total each tier produced, in tier order */
  byTier: { tier: EstimateTier; referrals: number; dollars: number }[];
};

export function tierFor(tiers: EstimateTier[], alreadyPaying: number): EstimateTier {
  let hit = tiers[0];
  for (const t of tiers) if (alreadyPaying >= t.min_paying) hit = t;
  return hit;
}

export function estimate(tiers: EstimateTier[], referrals: number, monthlyPrice: number, buyerDiscountPercent: number): Estimate {
  const n = Math.max(0, Math.floor(referrals));
  const byTier = tiers.map((tier) => ({ tier, referrals: 0, dollars: 0 }));
  let total = 0;
  for (let k = 1; k <= n; k++) {
    const tier = tierFor(tiers, k - 1);
    const first = monthlyPrice * (1 - buyerDiscountPercent / 100);
    const paid = first + monthlyPrice * (tier.months - 1);
    const dollars = (paid * tier.percent) / 100;
    total += dollars;
    const row = byTier.find((r) => r.tier.key === tier.key)!;
    row.referrals += 1;
    row.dollars += dollars;
  }
  return {
    total,
    tierAt: (i) => tierFor(tiers, Math.max(0, i - 1)),
    last: tierFor(tiers, Math.max(0, n - 1)),
    byTier,
  };
}

/**
 * Month by month: `perMonth` new paying referrals join at the start of every
 * month for `months` months. A referral's tier is fixed by how many paying
 * referrals the partner already had when it joined; it pays its tier's months
 * of commission from the month it joins, the first at the buyer discount.
 * Returns what the partner earns in each calendar month and the total.
 */
export function monthlyEarnings(
  tiers: EstimateTier[],
  perMonth: number,
  months: number,
  monthlyPrice: number,
  buyerDiscountPercent: number,
): { byMonth: number[]; total: number } {
  const n = Math.max(0, Math.floor(perMonth));
  const byMonth = Array.from({ length: months }, () => 0);
  let joined = 0;
  for (let join = 0; join < months; join++) {
    for (let i = 0; i < n; i++) {
      const tier = tierFor(tiers, joined);
      joined += 1;
      for (let age = 0; age < tier.months && join + age < months; age++) {
        const paid = age === 0 ? monthlyPrice * (1 - buyerDiscountPercent / 100) : monthlyPrice;
        byMonth[join + age] += (paid * tier.percent) / 100;
      }
    }
  }
  return { byMonth, total: byMonth.reduce((a, b) => a + b, 0) };
}
