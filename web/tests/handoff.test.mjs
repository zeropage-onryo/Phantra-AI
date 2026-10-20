import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handoffKind, openingProject } from '../src/lib/handoff.ts';

const q = (s) => new URLSearchParams(s);

test('a hand-off is a prompt with a kind, the shape open_in_studio writes', () => {
  assert.equal(handoffKind(q('spark=a+can+on+slate&kind=image&frame=1104%3A832')), 'image');
  assert.equal(handoffKind(q('spark=a+can&kind=video')), 'video');
  // the landing page's hero and the palette send ?spark= alone: not a hand-off
  assert.equal(handoffKind(q('spark=a+can')), null);
  assert.equal(handoffKind(q('kind=image')), null);
  assert.equal(handoffKind(q('spark=++&kind=image')), null);
  assert.equal(handoffKind(q('spark=a+can&kind=music')), null);
});

test('a hand-off opens no remembered project; a named one always opens', () => {
  const remembered = () => 12;
  assert.equal(openingProject(q('spark=a+can&kind=image'), remembered), 0);
  assert.equal(openingProject(q('spark=a+can&kind=image&project=7'), remembered), 7);
  assert.equal(openingProject(q('spark=a+can'), remembered), 12);
  assert.equal(openingProject(q(''), remembered), 12);
  assert.equal(openingProject(q(''), () => null), 0);
});
