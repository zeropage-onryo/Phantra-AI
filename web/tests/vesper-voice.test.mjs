import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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

// QA 2026-11-02 T12: "That one came out" when only a scene had been
// written. He says a make landed only when a still or a clip did.
test('a written scene is not a landed make; a still or a clip is', async () => {
  const { landedFrom } = await import('../src/lib/vesper-voice.ts');
  assert.equal(landedFrom(undefined), null);
  assert.equal(landedFrom({ id: 'a', output: 'video', status: 'done', parts: [{ n: 1 }] }), null);
  assert.equal(landedFrom({ id: 'a', output: 'video', status: 'running', sceneClip: '/c.mp4' }), null);
  assert.deepEqual(landedFrom({ id: 'a', output: 'video', status: 'done', sceneClip: '/c.mp4' }), { key: 'a:clip', kind: 'video' });
  assert.deepEqual(landedFrom({ id: 'a', output: 'video', status: 'done', parts: [{ n: 1, media_url: '/1.mp4' }] }), { key: 'a:clip', kind: 'video' });
  assert.deepEqual(landedFrom({ id: 'b', output: 'image', status: 'done', image: '/s.png' }), { key: 'b:image', kind: 'image' });
  assert.equal(landedFrom({ id: 'b', output: 'image', status: 'done', image: null }), null);
});

test('the peek reacts to what landed, not to a turn ending', () => {
  const peek = readFileSync(new URL('../src/components/studio/vesper-peek.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(peek, /before\.making && !making/);
  assert.match(peek, /landedKey/);
});

// QA 2026-11-02 T12: he sat on "Open the canvas", the project chip and a
// plan card's last line. The docked box keeps his height clear above it.
test('the docked box keeps room for him above it, and the project row steps aside', () => {
  const css = readFileSync(new URL('../src/components/studio/composer/composer.css', import.meta.url), 'utf8');
  assert.match(css, /\.zc\.zc-active \.zc-dock:not\(:has\(\.zc-project\)\) > \.zc-box \{\s*margin-top: 52px;/);
  // with a project row, the same clear band sits between that row and the
  // box (the dock's 12px gap + 40px): his bubble is as wide as the row
  assert.match(css, /\.zc\.zc-active \.zc-dock:has\(\.zc-project\) > \.zc-box \{\s*margin-top: 40px;/);
  assert.doesNotMatch(css, /\.zc-dock:has\(\.zc-project\) \.zc-project \{\s*padding-left/);
  assert.match(css, /@media \(max-width: 720px\) \{\s*\.zc\.zc-active \.zc-dock:not\(:has\(\.zc-project\)\) > \.zc-box \{\s*margin-top: 38px;/);
});

// QA 2026-11-02 T13: with a project and a kit the settings line did not fit
// at 1440 and the send button dropped to a second row on the left.
test('the options wrap inside their own group, so Send keeps its place', () => {
  const css = readFileSync(new URL('../src/components/studio/composer/composer.css', import.meta.url), 'utf8');
  const i = css.indexOf('\n.zc .zc-opts {');
  const opts = css.slice(i, css.indexOf('}', i));
  assert.match(opts, /flex: 1 1 0;/);
  assert.match(opts, /min-width: 0;/);
  assert.match(opts, /flex-wrap: wrap;/);
});
