import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cleanRef, refCookie, readRef } from '../src/lib/affiliate-ref.ts';

const AFFILIATE_TERMS = JSON.parse(readFileSync(new URL('../src/content/affiliate.json', import.meta.url), 'utf8'));

test('the page prints the three tiers Mike set', () => {
  assert.deepEqual(
    AFFILIATE_TERMS.tiers.map((t) => [t.key, t.percent, t.months]),
    [['starter', 20, 3], ['pro', 30, 6], ['partner', 35, 12]],
  );
  assert.equal(AFFILIATE_TERMS.tiers[2].min_paying, 50);
  assert.equal(AFFILIATE_TERMS.buyer_discount_percent, 20);
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
