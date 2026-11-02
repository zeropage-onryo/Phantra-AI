import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PLACES, SHAPES, resultId, shapeLine, shapesSummary } from '../src/lib/every-shape.ts';

test('the three shapes an ad runs in, each with where it runs', () => {
  assert.deepEqual([...SHAPES], ['9:16', '1:1', '16:9']);
  for (const s of SHAPES) assert.ok(PLACES[s]);
});

test('each shape says what it is, how it was fitted and whether it is new', () => {
  assert.equal(shapeLine({ aspect: '9:16', status: 'same' }), '9:16 · Reels, Stories, TikTok, Shorts · this one');
  assert.equal(shapeLine({ aspect: '1:1', status: 'made', fit: 'crop' }), '1:1 · Feed · cropped · new');
  assert.equal(shapeLine({ aspect: '16:9', status: 'have', fit: 'pad' }), '16:9 · YouTube, TV, web · with bars · made before');
  assert.equal(shapeLine({ aspect: '16:9', status: 'failed' }), '16:9 · YouTube, TV, web · could not be made');
});

test('the summary counts what happened and says it was free', () => {
  assert.equal(shapesSummary([{ aspect: '9:16', status: 'same' }, { aspect: '1:1', status: 'made' }, { aspect: '16:9', status: 'made' }]),
    '2 new shapes · free');
  assert.equal(shapesSummary([{ aspect: '1:1', status: 'have' }, { aspect: '16:9', status: 'failed' }]),
    '1 already in your Library · 1 could not be made · free');
  assert.equal(shapesSummary([{ aspect: '9:16', status: 'same' }]), 'Every shape is already here.');
});

test('a result links to its Library item by id or by its gen ref', () => {
  assert.equal(resultId({ aspect: '1:1', status: 'made', asset_id: 12 }), 12);
  assert.equal(resultId({ aspect: '1:1', status: 'have', ref: 'gen:7' }), 7);
  assert.equal(resultId({ aspect: '1:1', status: 'same', ref: 'asset:3' }), null);
});
