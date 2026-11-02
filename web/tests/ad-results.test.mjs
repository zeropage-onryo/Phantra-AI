import { test } from 'node:test';
import assert from 'node:assert/strict';
import { adCode, count, importLine, money, percent, ranked, times } from '../src/lib/ad-results.ts';
import { planOf, variantOf } from '../src/lib/make-plan.ts';

test('an output has one ad code, the one the server reads back', () => {
  assert.equal(adCode(4821), 'PH4821');
  assert.equal(adCode('12'), 'PH12');
});

test('money is the export’s own currency, never a guessed one', () => {
  assert.equal(money(12.5, 'USD'), '$12.50');
  assert.equal(money(12.5, 'EUR'), '€12.50');
  assert.equal(money(12.5, null), '12.50');
  assert.equal(money(12.5, 'nope'), '12.50');
  assert.equal(money(null, 'USD'), '—');
});

test('rates read plainly, and a missing one is a dash', () => {
  assert.equal(percent(0.0202), '2.02%');
  assert.equal(percent(0.25), '25.0%');
  assert.equal(percent(null), '—');
  assert.equal(times(4), '4.00x');
  assert.equal(times(null), '—');
  assert.equal(count(1200), '1,200');
  assert.equal(count(2.5), '2.5');
});

test('ads with results come first, cheapest result first, then by spend', () => {
  const ad = (name, cpa, spend) => ({ ad_name: name, cpa, spend });
  const out = ranked([ad('none-big', null, 90), ad('pricey', 20, 40), ad('cheap', 8, 10), ad('none-small', null, 5)]);
  assert.deepEqual(out.map((a) => a.ad_name), ['cheap', 'pricey', 'none-big', 'none-small']);
});

test('the import says what happened in one line', () => {
  const r = { platform: 'meta', rows: 3, added: 2, updated: 1, matched: 1 };
  assert.equal(importLine(r), '3 ad rows from Meta report · 2 new, 1 updated · 1 matched a render.');
  assert.equal(importLine({ ...r, platform: 'tiktok', rows: 1, added: 0, matched: 0 }),
    '1 ad row from TikTok report · 1 updated · none matched a render.');
});

test('a plan of versions keeps each label and its test, and files them under the plan', () => {
  const plan = planOf({
    test: 'which hook', steps: [
      { n: 1, do: 'scene', args: { prompt: 'a' }, variant: 'Hook: the spill' },
      { n: 2, do: 'scene', args: { prompt: 'b' }, variant: 'Hook: price first' },
      { n: 3, do: 'render', args: {}, scene: 1, variant: 'not on a render' },
    ],
  }, 'abc-123');
  assert.equal(plan.test, 'which hook');
  assert.deepEqual(plan.steps.map((s) => s.variant), ['Hook: the spill', 'Hook: price first', undefined]);
  assert.deepEqual(variantOf(plan, plan.steps[0]), { label: 'Hook: the spill', group: 'abc-123', test: 'which hook' });
  assert.equal(variantOf(plan, plan.steps[2]), null);
  // a plan with no versions carries no test
  const plain = planOf({ test: 'x', steps: [{ do: 'scene', args: {} }, { do: 'scene', args: {} }] }, 'p');
  assert.equal(plain.test, undefined);
  assert.equal(variantOf(plain, plain.steps[0]), null);
});
