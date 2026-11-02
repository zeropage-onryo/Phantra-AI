import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cleanRef, refCookie, readRef } from '../src/lib/affiliate-ref.ts';

const AFFILIATE_TERMS = JSON.parse(readFileSync(new URL('../src/content/affiliate.json', import.meta.url), 'utf8'));

test('the page prints the three tiers Mike set', () => {
  assert.deepEqual(
    AFFILIATE_TERMS.tiers.map((t) => [t.key, t.percent, t.months]),
    [['starter', 25, 6], ['pro', 30, 6], ['partner', 35, 12]],
  );
  assert.equal(AFFILIATE_TERMS.tiers[2].min_paying, 50);
  assert.equal(AFFILIATE_TERMS.buyer_discount_percent, 10);
});

test('a ref is a short lowercase code or nothing', () => {
  assert.equal(cleanRef(' Ana '), 'ana');
  assert.equal(cleanRef('ana_2-x'), 'ana_2-x');
  for (const bad of [null, undefined, '', 'ab', 'a b', '<script>', '-ana', 'x'.repeat(41)]) {
    assert.equal(cleanRef(bad), null, String(bad));
  }
});

test('the cookie lasts 60 days and is shared with the API on phantra.ai only', () => {
  const prod = refCookie('ana', 'phantra.ai', true, AFFILIATE_TERMS.cookie_days);
  assert.match(prod, /^phantra_ref=ana; Max-Age=5184000; Path=\//);
  assert.match(prod, /Domain=\.phantra\.ai/);
  assert.match(prod, /Secure/);
  const www = refCookie('ana', 'www.phantra.ai', true, 60);
  assert.match(www, /Domain=\.phantra\.ai/);
  const dev = refCookie('ana', 'localhost', false, 60);
  assert.doesNotMatch(dev, /Domain=/);
  assert.doesNotMatch(dev, /Secure/);
  assert.equal(readRef('a=1; phantra_ref=ana; b=2'), 'ana');
  assert.equal(readRef('a=1'), null);
});

import { estimate, tierFor } from '../src/lib/affiliate-estimate.ts';

test('the calculator books each referral at the tier the partner was on when they paid', () => {
  const { tiers, buyer_discount_percent: off } = AFFILIATE_TERMS;
  assert.equal(tierFor(tiers, 0).key, 'starter');
  assert.equal(tierFor(tiers, 9).key, 'starter');
  assert.equal(tierFor(tiers, 10).key, 'pro');
  assert.equal(tierFor(tiers, 50).key, 'partner');
  // one $15 referral: $13.50 first month + 5 x $15 = $88.50 paid over 6 months, 25% = $22.125
  const one = estimate(tiers, 1, 15, off);
  assert.ok(Math.abs(one.total - 22.125) < 1e-9);
  // the 11th referral is the first booked at Pro
  const eleven = estimate(tiers, 11, 15, off);
  assert.equal(eleven.last.key, 'pro');
  assert.equal(eleven.byTier[0].referrals, 10);
  assert.equal(eleven.byTier[1].referrals, 1);
  assert.equal(estimate(tiers, 0, 15, off).total, 0);
});

import { monthlyEarnings } from '../src/lib/affiliate-estimate.ts';

test('the monthly chart sums to what each referral earns and flattens once the windows fill', () => {
  const { tiers, buyer_discount_percent: off } = AFFILIATE_TERMS;
  // ten months, one $15 referral a month: all ten join before the 10-referral Pro mark, so all are Starter (25% x 6)
  const m = monthlyEarnings(tiers, 1, 10, 15, off);
  assert.ok(Math.abs(m.byMonth[0] - 3.375) < 1e-9);             // month 1: 25% of $13.50
  assert.ok(Math.abs(m.byMonth[1] - (3.75 + 3.375)) < 1e-9);    // month 2: one at $15, one new at $13.50
  assert.ok(m.byMonth[5] > m.byMonth[0]);
  assert.ok(Math.abs(m.byMonth[9] - m.byMonth[6]) < 1e-9);      // the first referral's six months are spent: steady state
  const expected = Array.from({ length: 10 }, (_, j) => {
    const n = Math.min(6, 10 - j);
    return ((15 * 0.9 + 15 * (n - 1)) * 25) / 100;
  }).reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(m.total - expected) < 1e-9);
  // the 11th referral onward earns at Pro, so a longer run beats Starter-only
  assert.ok(monthlyEarnings(tiers, 1, 12, 15, off).total > monthlyEarnings(tiers, 1, 10, 15, off).total);
  assert.equal(monthlyEarnings(tiers, 0, 12, 15, off).total, 0);
});
