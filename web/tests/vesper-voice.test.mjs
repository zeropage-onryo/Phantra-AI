import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NO_RECENT, SPEAK_GAP_MS, gaze, greeting, maySpeak, tips } from '../src/lib/vesper-voice.ts';

const recent = {
  projects: [{ id: 7, title: 'Gygler spot', scenes: 3, rendered: 1 }],
  renders: [{ kind: 'video', model: 'Kling 3 Turbo Pro', prompt: 'a ferryman at dawn', project: 'Gygler spot' }],
};

test('he greets by first name, about the newest project when there is one', () => {
  assert.equal(greeting('Mike Massaad', NO_RECENT).text, 'Hey Mike — what are we making today?');
  const g = greeting('Mike Massaad', recent);
  assert.match(g.text, /pick up “Gygler spot”/);
  assert.equal(g.project, 7);
  assert.equal(greeting('', NO_RECENT).text, 'Hey — what are we making today?');
});

test('tips come from what he remembers first, and never repeat until they run out', () => {
  const all = tips(recent);
  assert.match(all[0].text, /last clip on Kling 3 Turbo Pro/);
  assert.match(all[0].fill, /a ferryman at dawn/);
  assert.match(all[1].text, /2 scenes not rendered/);
  assert.equal(all[1].project, 7);
  const said = new Set(all.map((t) => t.id));
  assert.equal(tips(recent, said).length, all.length); // all said: he starts over
  said.delete(all[2].id);
  assert.deepEqual(tips(recent, said).map((t) => t.id), [all[2].id]);
  assert.ok(tips(NO_RECENT).length >= 3);
});

test('he speaks sometimes, not constantly', () => {
  assert.equal(maySpeak(null, 0), true);
  assert.equal(maySpeak(0, SPEAK_GAP_MS - 1), false);
  assert.equal(maySpeak(0, SPEAK_GAP_MS), true);
  assert.equal(maySpeak(0, 1, true), true);
});

test('he only looks at a pointer that is near, and leans further the nearer it is', () => {
  assert.deepEqual(gaze({ x: 0, y: 0 }, null), { x: 0, y: 0 });
  assert.deepEqual(gaze({ x: 0, y: 0 }, { x: 1000, y: 0 }), { x: 0, y: 0 });
  const near = gaze({ x: 0, y: 0 }, { x: 50, y: 0 });
  const far = gaze({ x: 0, y: 0 }, { x: 300, y: 0 });
  assert.ok(near.x > far.x && far.x > 0);
  assert.ok(gaze({ x: 0, y: 0 }, { x: -50, y: 0 }).x < 0);
});
