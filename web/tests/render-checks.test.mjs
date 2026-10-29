import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkLines } from '../src/lib/render-checks.ts';

test('a clip check reads shot by shot, problems first, clean clips silent', () => {
  assert.deepEqual(checkLines({
    '10': { media: 'c', problems: [], notes: ['the cup leaves frame at 4s'] },
    '2': { media: 'b', problems: ['the brand name is said wrong'], notes: ['at 3s the voice says "Giggler"'] },
    '1': { media: 'a', problems: [], notes: [] },
  }), [
    'Shot 2: The brand name is said wrong',
    'Shot 2: At 3s the voice says "Giggler"',
    'Shot 10: The cup leaves frame at 4s',
  ]);
  assert.deepEqual(checkLines({ '0': { media: 'x', problems: ['on-screen words are garbled'], notes: [] } }),
    ['On-screen words are garbled']);
  assert.deepEqual(checkLines(undefined), []);
});
