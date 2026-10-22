import { test } from 'node:test';
import assert from 'node:assert/strict';
import { photoSources, photoThumb } from '../src/lib/element-photos.ts';

const R2 = 'https://pub-x.r2.dev';
const head = '/characters/michael/photo/01-headshot.jpg';
const sheet = '/characters/michael/photo/sheet.jpg';

// what GET /api/assets?scope=elements answers on the tenant rung
const michael = {
  photos: [head, sheet],
  photo_full: [`${R2}/m/1/characters/michael/01-headshot.jpg`, `${R2}/m/1/characters/michael/sheet.jpg`],
  photo_thumbs: [`${R2}/t/1/characters/michael/01-headshot.jpg`, `${R2}/t/1/characters/michael/sheet.jpg`],
};

test('a stored name is drawn from the address minted beside it, then from its own route', () => {
  assert.deepEqual(photoSources(michael, head), [`${R2}/m/1/characters/michael/01-headshot.jpg`, head]);
  assert.deepEqual(photoSources(michael, sheet), [`${R2}/m/1/characters/michael/sheet.jpg`, sheet]);
  // the route rides the API base; the minted address is already absolute
  assert.deepEqual(photoSources(michael, head, 'https://api.test'),
    [`${R2}/m/1/characters/michael/01-headshot.jpg`, `https://api.test${head}`]);
});

test('the full-size choice is never the thumbnail', () => {
  for (const src of photoSources(michael, head)) assert.ok(!src.includes('/t/1/'), src);
});

test('a strip tile draws the 480px derivative', () => {
  assert.equal(photoThumb(michael, head), `${R2}/t/1/characters/michael/01-headshot.jpg`);
  assert.equal(photoThumb(michael, sheet), `${R2}/t/1/characters/michael/sheet.jpg`);
});

test('a listing with no minted lists falls back to the name through the route', () => {
  const old = { photos: [head] };
  assert.deepEqual(photoSources(old, head), [head]);
  assert.equal(photoThumb(old, head), head);
  assert.equal(photoThumb(old, head, 'https://api.test'), `https://api.test${head}`);
  // no thumbs, but a master: the small choice is the master, not the name
  assert.equal(photoThumb({ photos: [head], photo_full: [`${R2}/m/1/a.jpg`] }, head), `${R2}/m/1/a.jpg`);
});

test('a list that is not parallel to photos is not trusted', () => {
  const skewed = { photos: [head, sheet], photo_full: [`${R2}/m/1/only-one.jpg`], photo_thumbs: [] };
  assert.deepEqual(photoSources(skewed, sheet), [sheet]);
  assert.equal(photoThumb(skewed, sheet), sheet);
  assert.deepEqual(photoSources({ ...michael, photo_full: null }, head), [head]);
});

test('with the bucket off the minted address IS the route, listed once', () => {
  const local = { photos: [head], photo_full: [head], photo_thumbs: [`${head}?thumb=1`] };
  assert.deepEqual(photoSources(local, head), [head]);
  assert.equal(photoThumb(local, head, 'https://api.test'), `https://api.test${head}?thumb=1`);
});

test('on the legacy rung the name is already a public address', () => {
  const url = `${R2}/characters/michael/01-headshot.jpg`;
  assert.deepEqual(photoSources({ photos: [url], photo_full: [url] }, url, 'https://api.test'), [url]);
});

test('a frame that is not one of the photos (the poster) is drawn as it is', () => {
  const poster = `${R2}/t/1/characters/michael/sheet.jpg`;
  assert.deepEqual(photoSources(michael, poster), [poster]);
  assert.equal(photoThumb(michael, poster), poster);
  assert.deepEqual(photoSources(michael, ''), []);
});

import { sourcePhotos, framesLine } from '../src/lib/element-photos.ts';

test('a sheeted element files its other photos as sources and the card says so', () => {
  const withSheet = { photos: [sheet, head, '/characters/michael/photo/02.jpg'], sheet };
  assert.deepEqual(sourcePhotos(withSheet), [head, '/characters/michael/photo/02.jpg']);
  assert.equal(framesLine(withSheet), 'sheet · from 2 photos');
  assert.equal(framesLine({ photos: [sheet], sheet }), 'sheet');
});

test('an element with no sheet reads as before', () => {
  assert.deepEqual(sourcePhotos({ photos: [head] }), [head]);
  assert.equal(framesLine({ photos: [head] }), '1 frame');
  assert.equal(framesLine({ photos: [] }), 'no photos yet');
});
