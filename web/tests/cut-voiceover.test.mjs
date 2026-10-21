import { test } from 'node:test';
import assert from 'node:assert/strict';
import { voiceoverPlacement, overrun } from '../src/lib/cut/voiceover.ts';

const doc = (tracks, duration = 300) => ({ fps: 30, duration, tracks });

test('a cut with no voice track gets one, then the read at the playhead, whole', () => {
  const d = doc([{ id: 'V1', kind: 'video', clips: [] }]);
  const steps = voiceoverPlacement(d, 'asset:5', 2.5, 60);
  assert.deepEqual(steps.map((s) => s.op), ['add_track', 'overwrite']);
  assert.deepEqual(steps[0].args(d), { kind: 'audio', role: 'voice' });
  const after = doc([...d.tracks, { id: 'A3', kind: 'audio', role: 'voice', clips: [] }]);
  assert.deepEqual(steps[1].args(after), { track_id: 'A3', clip: { media: 'asset:5', src_in: 0, src_out: 75 }, at: 60 });
});

test('music on the cut ducks under the read, once', () => {
  const bed = { id: 'c1', media: 'asset:9', at: 0, src_in: 0, src_out: 300 };
  const d = doc([
    { id: 'A1', kind: 'audio', role: 'voice', clips: [] },
    { id: 'A2', kind: 'audio', role: 'music', clips: [bed] },
  ]);
  const steps = voiceoverPlacement(d, 'asset:5', 2, 0);
  assert.deepEqual(steps.map((s) => s.op), ['overwrite', 'duck']);
  assert.deepEqual(steps[1].args(d), { track_id: 'A2', under: 'voice' });
  const ducked = doc([d.tracks[0], { ...d.tracks[1], duck_under: 'voice' }]);
  assert.deepEqual(voiceoverPlacement(ducked, 'asset:5', 2, 0).map((s) => s.op), ['overwrite']);
  // an empty music track has nothing to duck
  const empty = doc([d.tracks[0], { id: 'A2', kind: 'audio', role: 'music', clips: [] }]);
  assert.deepEqual(voiceoverPlacement(empty, 'asset:5', 2, 0).map((s) => s.op), ['overwrite']);
});

test('a read past the picture is measured, not cut', () => {
  const d = doc([], 300);
  assert.equal(overrun(d, 3, 240), 1);        // 8s + 3s on a 10s cut
  assert.equal(overrun(d, 3, 0), 0);
  assert.equal(voiceoverPlacement(d, 'asset:5', 3, 240)[1].args({ ...d, tracks: [{ id: 'A1', kind: 'audio', role: 'voice', clips: [] }] }).clip.src_out, 90);
});
