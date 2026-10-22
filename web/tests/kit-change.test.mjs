import { test } from 'node:test';
import assert from 'node:assert/strict';
import { diffRows, isKitTool, kitOf, shown, swatch } from '../src/lib/kit-change.ts';

test('the kit tool is named once', () => {
  assert.equal(isKitTool('propose_kit_change'), true);
  assert.equal(isKitTool('set_project_look'), false);
  assert.equal(isKitTool(undefined), false);
});

test('a proposal draws only well-formed rows', () => {
  const rows = diffRows({ diff: [
    { field: 'palette.background', label: 'Background colour', kind: 'colour', before: '#FAF0E4', after: '#FCF4EB' },
    { field: 'look.banned', label: 'Banned elements', kind: 'text', before: 'neon', after: 'neon, cold blue' },
    { label: 'no field' },
    'junk',
  ] });
  assert.deepEqual(rows.map((r) => r.field), ['palette.background', 'look.banned']);
  assert.deepEqual(diffRows({}), []);
  assert.deepEqual(diffRows(null), []);
});

test('a swatch is drawn only for a hex, and an empty side says so', () => {
  assert.equal(swatch('#fcf4eb'), '#FCF4EB');
  assert.equal(swatch(''), null);
  assert.equal(swatch('cream'), null);
  assert.equal(shown(''), '(empty)');
  assert.equal(shown('neon'), 'neon');
});

test('the kit is read off the args', () => {
  assert.deepEqual(kitOf({ kit_id: 3, kit_name: 'Gygler' }), { id: 3, name: 'Gygler' });
  assert.equal(kitOf({ kit_id: 'x' }), null);
  assert.deepEqual(kitOf({ kit_id: 4 }), { id: 4, name: 'the kit' });
});
