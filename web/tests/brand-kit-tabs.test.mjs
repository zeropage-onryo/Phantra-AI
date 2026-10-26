import { test } from 'node:test';
import assert from 'node:assert/strict';
import { problems, tabOfProblem, withDefaults } from '../src/lib/brand-kit.ts';

/* r3 kit page (2026-10-26): a problem's dot lands on the tab that holds it. */
test('every problem the kit can have names a tab, except the name in the bar', () => {
  assert.equal(tabOfProblem('palette'), 'visual');
  assert.equal(tabOfProblem('selling points'), 'identity');
  assert.equal(tabOfProblem('style description'), 'look');
  assert.equal(tabOfProblem('aesthetics'), 'look');
  assert.equal(tabOfProblem('tone'), 'voice');
  assert.equal(tabOfProblem('name'), null);
});

test('the problems a real spec raises all find their tab', () => {
  const spec = withDefaults(null);
  spec.palette = [{ hex: '#fee32d', role: 'primary', name: '' }, { hex: '#e5c916', role: 'primary', name: '' }];
  const found = problems('Phantra', spec);
  assert.ok(found.length > 0);
  for (const [field] of found) assert.notEqual(tabOfProblem(field), undefined);
  assert.ok(found.some(([f]) => tabOfProblem(f) === 'visual'));
});
