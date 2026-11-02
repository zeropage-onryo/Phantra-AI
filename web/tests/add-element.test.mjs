import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { addLabel, SHEET_BY_DEFAULT } from '../src/lib/add-element.ts';

// QA 2026-11-02 T10: the sheet is a paid still, asked for, and the
// button that spends says what it spends.
test('the sheet is never pre-ticked', () => {
  assert.equal(SHEET_BY_DEFAULT, false);
  const modal = readFileSync(new URL('../src/components/studio/add-element.tsx', import.meta.url), 'utf8');
  assert.match(modal, /useState\(SHEET_BY_DEFAULT\)/);
  assert.match(modal, /addLabel\(/);
});

test('Add is free; Add with a sheet carries its price', () => {
  assert.equal(addLabel(false, false, '10 credits'), 'Add');
  assert.equal(addLabel(false, true, '10 credits'), 'Add · 10 credits');
  assert.equal(addLabel(false, true, null), 'Add');
  assert.equal(addLabel(true, true, '10 credits'), 'Saving…');
});
