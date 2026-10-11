import { test } from 'node:test';
import assert from 'node:assert/strict';
import { keepRate, rankRecipes, recipeHint } from '../src/lib/recipes.ts';

const p = (id, tried, kept) => ({ id, label: id, how: '', tried, kept });

test('a tested recipe leads, best keep rate first; untested ones keep the file order', () => {
  const file = [p('push', 0, 0), p('orbit', 4, 1), p('macro', 2, 2), p('pov', undefined, undefined), p('follow', 10, 5)];
  assert.deepEqual(rankRecipes(file).map((x) => x.id), ['macro', 'follow', 'orbit', 'push', 'pov']);
  // the list handed in is not reordered in place
  assert.deepEqual(file.map((x) => x.id), ['push', 'orbit', 'macro', 'pov', 'follow']);
});

test('a tie on keep rate goes to the one tried more, then to the file order', () => {
  const file = [p('a', 2, 1), p('b', 8, 4), p('c', 8, 4)];
  assert.deepEqual(rankRecipes(file).map((x) => x.id), ['b', 'c', 'a']);
});

test('the hint says what is known and never invents a number', () => {
  assert.equal(recipeHint(p('a', 5, 3)), 'kept 3 of 5');
  assert.equal(recipeHint(p('a', 0, 0)), 'untested');
  assert.equal(recipeHint({ id: 'a', label: 'a', how: '' }), 'untested');
  // a count that cannot be true is held to what can: kept never exceeds tried
  assert.equal(recipeHint(p('a', 2, 9)), 'kept 2 of 2');
  assert.equal(keepRate(p('a', 0, 0)), null);
  assert.equal(keepRate(p('a', 4, 1)), 0.25);
});
