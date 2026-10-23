import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isScreenTool, screenOf, screenTitle } from '../src/lib/kit-screen.ts';

test('a make_screen proposal reads as its card', () => {
  assert.ok(isScreenTool('make_screen') && !isScreenTool('make_image'));
  const s = screenOf({ kit_id: 1, kit_name: 'Gygler', spec: { template: 'schedule' },
    summary: 'phone screen, 3-row schedule: Staffed', warnings: ['x', 3] });
  assert.deepEqual(s, { kitId: 1, kitName: 'Gygler', spec: { template: 'schedule' },
    summary: 'phone screen, 3-row schedule: Staffed', warnings: ['x'] });
  assert.equal(screenOf({ kit_id: 0, spec: {} }), null);
  assert.equal(screenOf({ kit_id: 1 }), null);
  assert.equal(screenOf(null), null);
});

test('the card title reads in words', () => {
  assert.equal(screenTitle('phone screen, 3-row schedule: Staffed'), 'Phone screen · 3-row schedule · Staffed');
  assert.equal(screenTitle('tablet screen, call to action'), 'Tablet screen · call to action');
});
