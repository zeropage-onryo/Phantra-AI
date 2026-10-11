import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  kindOf, nextNumber, numbered, findResult, resultList, numbersOf, stillsFor, insertRef, heldLine, refTag,
} from '../src/lib/result-numbers.ts';

const still = (over = {}) => ({ output: 'image', status: 'done', image: '/renders/a.png', prompt: 'the can on wet steel', ...over });
const clip = (over = {}) => ({ output: 'image', status: 'done', clip: '/renders/c.mp4', asset: 'gen:9', effect: 'camera-move', ...over });
const scene = (over = {}) => ({ output: 'video', status: 'done', conceptId: 41, title: 'Night ride', prompt: 'she rides', ...over });

test('only something finished and drawable is a result', () => {
  assert.equal(kindOf(still()), 'still');
  assert.equal(kindOf(clip()), 'clip');
  assert.equal(kindOf(scene()), 'scene');
  for (const not of [null, undefined, still({ status: 'running' }), still({ status: 'failed' }),
    still({ image: null }), scene({ conceptId: null }), { output: 'video', status: 'done' }]) {
    assert.equal(kindOf(not), null);
  }
});

test('a result is numbered once, in thread order, and never renumbered', () => {
  const thread = [
    { role: 'user', content: 'hi' },
    { role: 'assistant', content: 'a still', made: still() },
    { role: 'assistant', content: 'still running', made: still({ status: 'running', image: null }) },
    { role: 'assistant', content: 'a scene', made: scene() },
  ];
  const first = numbered(thread);
  assert.deepEqual(first.map((t) => t.made?.n), [undefined, 1, undefined, 2]);
  // nothing new to number: the very same array, so a write stays a no-op
  assert.equal(numbered(first), first);
  // the running one finishes later: it takes the NEXT number, and 1 and 2 stay
  const later = numbered(first.map((t, i) => (i === 2 ? { ...t, made: still() } : t)));
  assert.deepEqual(later.map((t) => t.made?.n), [undefined, 1, 3, 2]);
  // a result removed from the thread does not free its number
  const cut = later.filter((t) => t.made?.n !== 3);
  assert.equal(nextNumber(cut), 3);
  assert.equal(nextNumber([...cut, { made: still({ n: 7 }) }]), 8);
  assert.equal(nextNumber([]), 1);
  // the input is not changed in place
  assert.equal(thread[1].made.n, undefined);
});

test('a number finds its result, and only a result', () => {
  const made = numbered([{ made: still() }, { made: clip() }, { made: still() }]);
  // the third is drawn again and that draw fails: it keeps its number, and is no result now
  const thread = made.map((t, i) => (i === 2 ? { ...t, made: { ...t.made, status: 'failed', image: null } } : t));
  assert.equal(findResult(thread, 1).image, '/renders/a.png');
  assert.equal(findResult(thread, 2).clip, '/renders/c.mp4');
  assert.equal(findResult(thread, 3), null);
  assert.equal(findResult(thread, 4), null);
  assert.equal(refTag(3), '#3');
});

test('the brain is told number, kind and a few words, never an address', () => {
  const thread = numbered([
    { content: 'a still', made: still() },
    { content: 'Camera move', effect: { label: 'Camera move' }, made: clip() },
    { content: 'a scene', made: scene() },
    { content: 'no prompt of its own', made: still({ prompt: undefined }) },
    { content: 'x', made: still({ prompt: 'word '.repeat(60) }) },
    { content: 'failed', made: still({ status: 'failed' }) },
  ]);
  const list = resultList(thread);
  assert.deepEqual(list.slice(0, 4), [
    { n: 1, kind: 'still', label: 'the can on wet steel' },
    { n: 2, kind: 'clip', label: 'Camera move' },
    { n: 3, kind: 'scene', label: 'Night ride' },
    { n: 4, kind: 'still', label: 'no prompt of its own' },
  ]);
  assert.ok(list[4].label.length <= 81 && list[4].label.endsWith('…'));
  assert.equal(list.length, 5);
  assert.doesNotMatch(JSON.stringify(list), /renders|gen:|http/);
  // the newest forty
  const many = numbered(Array.from({ length: 50 }, () => ({ made: still() })));
  const kept = resultList(many);
  assert.equal(kept.length, 40);
  assert.equal(kept[0].n, 11);
  assert.equal(kept.at(-1).n, 50);
});

test('numbers out of a tool argument are whole, positive and once each', () => {
  assert.deepEqual(numbersOf([3, '1', '#2', 3, 0, -1, 2.5, 'x', null, true]), [3, 1, 2]);
  assert.deepEqual(numbersOf(4), [4]);
  assert.deepEqual(numbersOf('#4'), [4]);
  assert.deepEqual(numbersOf(undefined), []);
  assert.deepEqual(numbersOf({ n: 1 }), []);
});

test('a make is held to the stills it named, and to nothing that is not one', () => {
  const thread = numbered([{ made: still() }, { made: clip() }, { made: scene() }, { made: still({ image: '/refs/b.jpg' }) }]);
  assert.deepEqual(stillsFor(thread, [4, 2, 3, 1, 9]), [{ n: 4, image: '/refs/b.jpg' }, { n: 1, image: '/renders/a.png' }]);
  assert.deepEqual(stillsFor(thread, undefined), []);
});

test('a clicked number reads as a word in the sentence', () => {
  assert.equal(insertRef('', 3), '#3 ');
  assert.equal(insertRef('make', 3), 'make #3 ');
  assert.equal(insertRef('make ', 3), 'make #3 ');
  assert.equal(heldLine([]), '');
  assert.equal(heldLine([1]), 'Held to #1');
  assert.equal(heldLine([1, 3]), 'Held to #1 and #3');
  assert.equal(heldLine([1, 3, 4]), 'Held to #1, #3 and #4');
});
