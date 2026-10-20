import { test } from 'node:test';
import assert from 'node:assert/strict';
import { joinable, shouldJoin, cutLine } from '../src/lib/final-cut.ts';

const clip = (u) => ({ media_url: u });

test('two or more shots, every one with a clip, can be joined', () => {
  assert.equal(joinable([clip('/a.mp4'), clip('/b.mp4')]), true);
  assert.equal(joinable([clip('/a.mp4'), clip(null)]), false);
  // one shot is already the whole video
  assert.equal(joinable([clip('/a.mp4')]), false);
  assert.equal(joinable(undefined), false);
});

test('the join starts on the read that saw the last shot land, and only once', () => {
  const half = [clip('/a.mp4'), clip(null)];
  const whole = [clip('/a.mp4'), clip('/b.mp4')];
  assert.equal(shouldJoin(half, whole, null), true);
  // already whole when the turn was drawn: the person asks for it
  assert.equal(shouldJoin(whole, whole, null), false);
  // already joining or joined
  assert.equal(shouldJoin(half, whole, { status: 'running', jobId: 3 }), false);
  assert.equal(shouldJoin(half, whole, { status: 'failed' }), false);
  assert.equal(shouldJoin(half, half, null), false);
});

test('the line says what it is, and that it was free', () => {
  assert.equal(cutLine({ status: 'running' }, 3), 'Joining 3 shots into one video…');
  assert.equal(cutLine({ status: 'done', seconds: 9.04 }, 3), 'Final cut · 3 shots · 9.0s · free');
  assert.equal(cutLine({ status: 'done' }, 2), 'Final cut · 2 shots · free');
  assert.match(cutLine({ status: 'failed' }, 2), /Nothing was charged/);
  assert.equal(cutLine({ status: 'failed', detail: 'ffmpeg is not installed' }, 2), 'ffmpeg is not installed');
});
