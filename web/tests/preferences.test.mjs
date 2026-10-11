import { test } from 'node:test';
import assert from 'node:assert/strict';
import { startFrame, startSeconds } from '../src/lib/scene-defaults.ts';
import { SHORTCUTS, keyLabel } from '../src/lib/shortcuts.ts';

test('a new scene starts at the stored length only when the server offers it', () => {
  const bounds = { min: 4, max: 30, default: 10 };
  assert.equal(startSeconds(0, bounds), 10);       // nothing stored
  assert.equal(startSeconds(15, bounds), 15);
  assert.equal(startSeconds(4, bounds), 4);
  assert.equal(startSeconds(30, bounds), 30);
  assert.equal(startSeconds(45, bounds), 10);      // stored on a server that allowed more
  assert.equal(startSeconds(2, bounds), 10);
});

test('a new scene starts in the stored frame only while it is still offered', () => {
  const ids = ['720:1280', '1280:720', '960:960'];
  assert.equal(startFrame('', ids, '720:1280'), '720:1280');
  assert.equal(startFrame('1280:720', ids, '720:1280'), '1280:720');
  assert.equal(startFrame('gone', ids, '720:1280'), '720:1280');
});

test('the shortcut list is grouped by where a key works, and prints the platform modifier', () => {
  assert.deepEqual(SHORTCUTS.map((g) => g.where), ['Everywhere', 'Queue', "A project's scenes", 'Editor']);
  for (const group of SHORTCUTS) {
    assert.ok(group.items.length, group.where);
    for (const item of group.items) assert.ok(item.keys.length && item.does, group.where);
  }
  assert.equal(keyLabel('mod', '⌘'), '⌘');
  assert.equal(keyLabel('mod', 'Ctrl'), 'Ctrl');
  assert.equal(keyLabel('K', 'Ctrl'), 'K');
});
