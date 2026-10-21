import { test } from 'node:test';
import assert from 'node:assert/strict';
import { musicPlacement } from '../src/lib/cut/music.ts';

const doc = (tracks, duration = 600) => ({ fps: 30, duration, tracks });

test('a cut with no music track gets one, then the bed from 0, then a fade out', () => {
  const d = doc([{ id: 'V1', kind: 'video', clips: [] }]);
  const steps = musicPlacement(d, 'asset:9', 25);
  assert.deepEqual(steps.map((s) => s.op), ['add_track', 'overwrite', 'set_fade']);
  assert.deepEqual(steps[0].args(d), { kind: 'audio', role: 'music' });
  const after = doc([...d.tracks, { id: 'A2', kind: 'audio', role: 'music', clips: [] }]);
  assert.deepEqual(steps[1].args(after), { track_id: 'A2', clip: { media: 'asset:9', src_in: 0, src_out: 600 }, at: 0 });
  const laid = doc([{ id: 'A2', kind: 'audio', role: 'music', clips: [{ id: 'c7', media: 'asset:9', at: 0, src_in: 0, src_out: 600 }] }]);
  assert.deepEqual(steps[2].args(laid), { clip_id: 'c7', fade_out: 30 });
});

test('the bed is cut to the cut, and a voice makes it duck', () => {
  const d = doc([
    { id: 'A2', kind: 'audio', role: 'music', clips: [] },
    { id: 'A3', kind: 'audio', role: 'voice', clips: [{ id: 'v1', media: 'asset:1', at: 0, src_in: 0, src_out: 90 }] },
  ], 300);
  const steps = musicPlacement(d, 'asset:9', 25);
  assert.deepEqual(steps.map((s) => s.op), ['overwrite', 'set_fade', 'duck']);
  assert.equal(steps[0].args(d).clip.src_out, 300);              // 25s of music on a 10s cut: 10s
  assert.deepEqual(steps[2].args(d), { track_id: 'A2', under: 'voice' });
  // a short bed is laid whole
  assert.equal(musicPlacement(d, 'asset:9', 4)[0].args(d).clip.src_out, 120);
});
