import { test } from 'node:test';
import assert from 'node:assert/strict';
import { joinable, shouldJoin, cutLine, trimProblem } from '../src/lib/final-cut.ts';

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
  assert.equal(cutLine({ status: 'done', seconds: 9.04, asset: 'gen:4' }, 3), 'Final cut · 3 shots · 9.0s · free · in your Library');
  assert.equal(cutLine({ status: 'done' }, 2), 'Final cut · 2 shots · free');
  assert.match(cutLine({ status: 'failed' }, 2), /Nothing was charged/);
  assert.equal(cutLine({ status: 'failed', detail: 'ffmpeg is not installed' }, 2), 'ffmpeg is not installed');
});

test('a trim range is refused, never clamped', () => {
  assert.equal(trimProblem(0, 5, 9), '');
  assert.match(trimProblem(-1, 5, 9), /before 0s/);
  assert.match(trimProblem(5, 5, 9), /after the start/);
  assert.match(trimProblem(2, 2.2, 9), /half a second/);
  assert.match(trimProblem(0, 12, 9), /9\.0s long/);
  assert.match(trimProblem(NaN, 3, 9), /seconds/);
});

test('once the shots are joined, the chat keeps only the final cut turn', async () => {
  const { keepOnlyCut } = await import('../src/lib/final-cut.ts');
  const turns = [
    { role: 'user', content: 'idea' },
    { role: 'assistant', content: 'two ways', made: { id: 'old' } },
    { role: 'assistant', content: 'written', made: { id: 'm1' } },
  ];
  assert.deepEqual(keepOnlyCut(turns, 'm1').map((t) => t.made.id), ['m1']);
  // a turn that is not there leaves the chat alone
  assert.equal(keepOnlyCut(turns, 'gone'), turns);
});

test('a thread whose last scene is rendered and joined is through', async () => {
  const { renderIsThrough } = await import('../src/lib/final-cut.ts');
  const scene = (extra) => ({ role: 'assistant', content: '', made: { output: 'video', status: 'done', ...extra } });
  assert.equal(renderIsThrough([scene({ parts: [clip('/a'), clip('/b')], finalCut: { status: 'done' } })]), true);
  // joined shots not yet joined: still going (the Join button is on the turn)
  assert.equal(renderIsThrough([scene({ parts: [clip('/a'), clip('/b')] })]), false);
  // a one-shot scene with its clip
  assert.equal(renderIsThrough([scene({ parts: [clip('/a')] })]), true);
  assert.equal(renderIsThrough([scene({ parts: [], sceneClip: '/a.mp4' })]), true);
  // something said after the render: a new idea is under way
  assert.equal(renderIsThrough([scene({ parts: [clip('/a')] }), { role: 'user', content: 'next' }]), false);
  assert.equal(renderIsThrough([]), false);
});
