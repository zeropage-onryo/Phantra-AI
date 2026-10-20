import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pose, moves, problems, trackWithRoom, nextTrackId, starter, withDefaults } from '../src/lib/cut/graphics.ts';

const fps = 30;

test('the preview poses an item the way the export moves it', () => {
  const rise = { start: 30, end: 90, type: 'headline', text: 'x', anim_in: 'rise', anim_out: 'fade' };
  assert.equal(pose(rise, 29, fps), null);                       // before it
  assert.equal(pose(rise, 90, fps), null);                       // after it
  const first = pose(rise, 30, fps);
  assert.ok(Math.abs(first.dy - 0.05) < 1e-9 && first.alpha === 0);  // starts low and clear
  const rest = pose(rise, 60, fps);
  assert.deepEqual(rest, { dx: 0, dy: 0, alpha: 1 });            // at rest mid-item
  assert.ok(pose(rise, 88, fps).alpha < 0.2);                    // fading out at the end
  const slide = pose({ ...rise, anim_in: 'slide_left' }, 30, fps);
  assert.ok(Math.abs(slide.dx - 0.28) < 1e-9);                   // comes in from the right
});

test('a still item does not move and the big word drifts left over its life', () => {
  const still = { start: 0, end: 60, type: 'label', text: 'x', anim_in: 'none', anim_out: 'none' };
  assert.deepEqual(pose(still, 0, fps), { dx: 0, dy: 0, alpha: 1 });
  assert.deepEqual(moves(still, fps), { inS: 0, outS: 0 });
  const word = { start: 0, end: 60, type: 'background_word', text: 'BOOK', anim_in: 'none', anim_out: 'none' };
  assert.ok(Math.abs(pose(word, 30, fps).dx + 0.02) < 1e-9);    // half its life: half of 4%
  assert.equal(pose({ ...word, drift: false }, 30, fps).dx, 0);
  // a short item gets a third of its length each way
  assert.ok(Math.abs(moves({ start: 0, end: 9, type: 'headline', text: 'x' }, fps).inS - 0.1) < 1e-9);
});

test('the form names what the server would refuse', () => {
  assert.deepEqual(problems({ start: 0, end: 30, type: 'headline', text: ' ' }), ['type some text']);
  assert.deepEqual(problems({ start: 0, end: 30, type: 'card' }), ['a card needs a still from the bin']);
  assert.deepEqual(problems({ start: 0, end: 30, type: 'background_word', text: 'x'.repeat(25) }), ['at most 24 characters']);
  assert.deepEqual(problems({ start: 30, end: 30, type: 'label', text: 'a' }), ['it must end after it starts']);
  assert.deepEqual(problems({ start: 0, end: 30, type: 'card', media: 'asset:3' }), []);
});

test('a new graphic goes on the first track with room, or a new one', () => {
  const tracks = [
    { id: 'V1', kind: 'video' },
    { id: 'G2', kind: 'graphic', items: [{ start: 0, end: 30 }] },
    { id: 'G1', kind: 'graphic', items: [{ start: 0, end: 90 }] },
  ];
  assert.equal(trackWithRoom(tracks, 30, 60), 'G2');
  assert.equal(trackWithRoom(tracks, 0, 10), null);
  assert.equal(nextTrackId(tracks), 'G3');
  assert.equal(nextTrackId([{ id: 'V1' }]), 'G1');
  const card = starter('card', 15, fps, 'asset:4');
  assert.deepEqual([card.start, card.end, card.media, card.anim_in], [15, 105, 'asset:4', 'slide_left']);
  assert.equal(withDefaults({ start: 0, end: 1, type: 'label', text: 'a' }).position, 'lower_left');
});
