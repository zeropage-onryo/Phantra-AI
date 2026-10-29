import { test } from 'node:test';
import assert from 'node:assert/strict';
import { addLabel, folders, keyOf, numberOf, offered, pills, tileSrc, tileTag, toggle, visible } from '../src/lib/library-drawer.ts';

const still = (id, extra = {}) => ({ url: `https://media/m/1/s${id}.jpg`, asset_id: `generated-${id}`, kind: 'image', generated_id: id, model_label: 'FLUX', ...extra });
const clip = (id, extra = {}) => ({ url: `https://media/m/1/c${id}.mp4`, asset_id: `generated-${id}`, kind: 'video', generated_id: id, poster: `https://media/t/1/c${id}.jpg`, ...extra });
const photo = (n) => ({ url: `/assets/photo/characters/mike/${n}.jpg`, asset_id: 'character-mike', asset_name: 'Mike', category: 'character', kind: 'image' });
const ALL = { show: 'all', folder: '', q: '' };

test('a stills door is never offered a clip, a clips door never a still', () => {
  assert.equal(offered(clip(1), 'image', 'library'), false);
  assert.equal(offered(still(1), 'video', 'library'), false);
  assert.equal(offered(still(1), 'any', 'library'), true);
});

test('the Library tab is renders only; the Elements tab is element photos', () => {
  assert.equal(offered(photo(1), 'image', 'library'), false);
  assert.equal(offered(photo(1), 'image', 'elements'), true);
});

test('a stills-only door has no Clips pill', () => {
  assert.deepEqual(pills('image', 'library'), ['all', 'starred']);
  assert.deepEqual(pills('any', 'library'), ['all', 'image', 'video', 'starred']);
});

test('the filters narrow: kind, starred, folder and the search words', () => {
  const rows = [still(1, { prompt: 'honey jar on linen' }), clip(2), still(3, { starred: true, folder: 'Gygler' })];
  assert.deepEqual(visible(rows, 'any', 'library', { ...ALL, show: 'video' }).map((r) => r.generated_id), [2]);
  assert.deepEqual(visible(rows, 'any', 'library', { ...ALL, show: 'starred' }).map((r) => r.generated_id), [3]);
  assert.deepEqual(visible(rows, 'any', 'library', { ...ALL, folder: 'Gygler' }).map((r) => r.generated_id), [3]);
  assert.deepEqual(visible(rows, 'any', 'library', { ...ALL, q: 'HONEY' }).map((r) => r.generated_id), [1]);
  assert.deepEqual(visible(rows, 'image', 'library', ALL).map((r) => r.generated_id), [1, 3]);
});

test('folders count only what this door may be offered', () => {
  const rows = [still(1, { folder: 'B' }), clip(2, { folder: 'B' }), still(3, { folder: 'A' })];
  assert.deepEqual(folders(rows, 'image', 'library'), [['A', 1], ['B', 1]]);
});

test('a pick queues in order, a second click takes it off, a full door takes no more', () => {
  let p = [];
  p = toggle(p, 'a', 2);
  p = toggle(p, 'b', 2);
  assert.deepEqual(toggle(p, 'c', 2), ['a', 'b'], 'full: unchanged');
  assert.equal(numberOf(p, 'b'), 2);
  p = toggle(p, 'a', 2);
  assert.deepEqual(p, ['b'], 'the rest keep their order');
  assert.equal(numberOf(p, 'b'), 1);
  assert.equal(numberOf(p, 'a'), 0);
});

test('an element has several photos under one asset id, each its own key', () => {
  assert.notEqual(keyOf(photo(1)), keyOf(photo(2)));
});

test('a tile draws the thumbnail when named, a clip its poster', () => {
  assert.equal(tileSrc(still(1, { thumb: 'https://media/t/1/s1.jpg' })), 'https://media/t/1/s1.jpg');
  assert.equal(tileSrc(still(1)), 'https://media/m/1/s1.jpg');
  assert.equal(tileSrc(clip(2)), 'https://media/t/1/c2.jpg');
  assert.equal(tileTag(clip(2)), 'Clip');
  assert.equal(tileTag(photo(1)), 'Mike');
});

test('the button counts what it adds', () => {
  assert.equal(addLabel(0, 'reference'), 'Add');
  assert.equal(addLabel(1, 'reference'), 'Add 1 reference');
  assert.equal(addLabel(3, 'reference'), 'Add 3 references');
});
