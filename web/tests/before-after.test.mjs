import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PAIRED_EFFECTS, pairOf, sideBySideHref } from '../src/lib/before-after.ts';

const costume = { effect: 'costume-preview', sources: [{ ref: 'https://media.phantra.ai/m/1/refs/me.jpg', kind: 'image', thumb: 'https://media.phantra.ai/m/1/refs/me.jpg' }] };
const still = { image: '/renders/costume-abc.png', clip: null, asset: 'gen:42' };

test('a costume still pairs with the photo it was made from', () => {
  assert.ok(PAIRED_EFFECTS.has('costume-preview'));
  const pair = pairOf(costume, still);
  assert.deepEqual(pair, { beforeRef: costume.sources[0].ref, before: costume.sources[0].thumb, after: still.image, afterAsset: 'gen:42' });
  assert.equal(sideBySideHref(pair), `/api/side-by-side?before=${encodeURIComponent(costume.sources[0].ref)}&after=gen%3A42`);
});

test('nothing else pairs: another effect, a clip, no drawable source, nothing made', () => {
  assert.equal(pairOf({ ...costume, effect: 'nano-banana-edit' }, still), null);
  assert.equal(pairOf(costume, { ...still, clip: '/renders/x.mp4' }), null);
  assert.equal(pairOf({ ...costume, sources: [{ ref: 'gen:3', kind: 'image' }] }, still), null);
  assert.equal(pairOf(costume, null), null);
  assert.equal(pairOf(null, still), null);
});

test('no render id, no download', () => {
  assert.equal(sideBySideHref({ ...pairOf(costume, still), afterAsset: null }), null);
  assert.equal(sideBySideHref({ ...pairOf(costume, still), afterAsset: 'https://evil/x.jpg' }), null);
});
