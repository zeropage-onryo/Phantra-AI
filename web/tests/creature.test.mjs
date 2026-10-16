import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_PARK, DOCK, clampDock, clickIntent, readPark, snapPark } from '../src/lib/creature.ts';

test('a stored park is read back, and anything else is the default', () => {
  assert.deepEqual(readPark(JSON.stringify({ side: 'left', y: 180.4, small: true })), { side: 'left', y: 180, small: true });
  for (const bad of [null, undefined, '', 'nope', '[]', '1', JSON.stringify({ side: 'up', y: 'x', small: 'yes' })])
    assert.deepEqual(readPark(bad), { side: 'right', y: DEFAULT_PARK.y, small: false }, String(bad));
  assert.equal(readPark(JSON.stringify({ y: -40 })).y, 0);
});

test('a drag lets go on the nearer side, inside the window', () => {
  const view = { width: 1440, height: 900 };
  const at = (left, top) => snapPark({ left, top, width: 320, height: 320 }, view, false);
  assert.equal(at(100, 400).side, 'left');
  assert.equal(at(1000, 400).side, 'right');
  assert.equal(at(1000, 400).y, 180); // 900 - (400 + 320)
  assert.equal(at(1000, 700).y, 0); // dropped below the window: sits on its bottom
  assert.equal(at(1000, -200).y, 900 - 72 - 320); // dropped over the header: kept under it
  assert.equal(snapPark({ left: 10, top: 10, width: 80, height: 80 }, view, true).small, true);
});

test('one click waits for a second; a pair makes it small; a small one comes back at once', () => {
  assert.equal(clickIntent(0, false), 'now'); // Enter or Space
  assert.equal(clickIntent(1, false), 'later');
  assert.equal(clickIntent(2, false), 'double');
  assert.equal(clickIntent(3, false), 'ignore');
  assert.equal(clickIntent(0, true), 'now');
  assert.equal(clickIntent(1, true), 'now');
  assert.equal(clickIntent(2, true), 'ignore');
});

test('the dock is never shorter than its minimum nor taller than most of the window', () => {
  assert.equal(clampDock(100, 900), DOCK.min);
  assert.equal(clampDock(5000, 900), Math.round(900 * DOCK.share));
  assert.equal(clampDock(400, 900), 400);
  assert.equal(clampDock(NaN, 900), DOCK.start);
  assert.equal(clampDock(400, 300), DOCK.min); // a tiny window still gets the minimum
});

test('on the Create page the creature rests at its full size (2026-10-16), and the stored park is untouched', async () => {
  const { restingPark, isCreatePage, restsSmall } = await import('../src/lib/creature.ts');
  const full = { side: 'right', y: 24, small: false };
  assert.equal(isCreatePage('/studio'), true);
  assert.equal(restsSmall('/studio'), false);
  assert.equal(restingPark(full, '/studio'), full);
  assert.equal(restingPark(full, '/studio/'), full);
  assert.equal(full.small, false);
  for (const p of ['/studio/queue', '/studio/projects/4', '/studio/assets', '/'])
    assert.equal(restingPark(full, p), full, p);
  assert.equal(isCreatePage('/studio/elements'), false);
});

test('on the settings pages it rests small too, by the same rule', async () => {
  const { restingPark, restsSmall, isSettingsPage, isCreatePage } = await import('../src/lib/creature.ts');
  const full = { side: 'left', y: 40, small: false };
  for (const p of ['/studio/settings', '/studio/settings/', '/studio/settings/plan', '/studio/settings/preferences']) {
    assert.equal(isSettingsPage(p), true, p);
    assert.equal(restsSmall(p), true, p);
    // drawn small where it was parked; the stored park is untouched
    assert.deepEqual(restingPark(full, p), { side: 'left', y: 40, small: true }, p);
  }
  assert.equal(full.small, false);
  // settings is not Create: the composer's own layout rule stays Create's
  assert.equal(isCreatePage('/studio/settings/account'), false);
  // a page that only starts with the same letters is not settings
  for (const p of ['/studio/settings-old', '/studio/projects/4', '/studio/renders', '/settings'])
    assert.equal(restsSmall(p), false, p);
  // a creature already small stays as it is, everywhere
  const small = { side: 'right', y: 24, small: true };
  assert.equal(restingPark(small, '/studio/assets'), small);
});
