import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { AUTO_OPEN_GAP_MS, UPGRADE_EVENT, dollars, firstMonthCents, shouldOpen } from '../src/lib/upgrade.ts';

const src = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const OFFER30 = { percent_off: 30, amount_off_cents: null, duration: 'once', months: null, label: '30% off your first month' };

test('a refusal opens the popup once in a while; a click always does', () => {
  const trial = { plan: null, exempt: false };
  assert.equal(shouldOpen('refused', trial, null, 1000), true);
  assert.equal(shouldOpen('refused', trial, 1000, 1000 + 60_000), false);
  assert.equal(shouldOpen('refused', trial, 1000, 1000 + AUTO_OPEN_GAP_MS), true);
  assert.equal(shouldOpen('clicked', trial, 1000, 1001), true);
});

test('an exempt operator account is never sold to', () => {
  assert.equal(shouldOpen('refused', { exempt: true }, null, 0), false);
  assert.equal(shouldOpen('clicked', { exempt: true }, null, 0), false);
});

test('the first month comes off exactly as the coupon says', () => {
  assert.equal(firstMonthCents(35, null), 3500);
  assert.equal(firstMonthCents(35, OFFER30), 2450);
  assert.equal(firstMonthCents(15, { ...OFFER30, percent_off: null, amount_off_cents: 500 }), 1000);
  assert.equal(firstMonthCents(15, { ...OFFER30, percent_off: null, amount_off_cents: 9000 }), 0);
  assert.equal(dollars(2450), '$24.50');
  assert.equal(dollars(9500), '$95');
});

test('lib/api.ts fires the same event the popup listens for', () => {
  assert.ok(src('../src/lib/api.ts').includes(`"${UPGRADE_EVENT}"`));
  assert.ok(src('../src/components/studio/upgrade-modal.tsx').includes('UPGRADE_EVENT'));
  assert.ok(src('../src/components/studio/shell.tsx').includes('<UpgradeModal />'));
});
