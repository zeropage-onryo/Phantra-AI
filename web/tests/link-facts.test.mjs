import { test } from 'node:test';
import assert from 'node:assert/strict';
import { factsLine, factsBlurb } from '../src/lib/link-facts.ts';

test('a pasted page\'s facts read as one line: what the thing is, never its blurb', () => {
  const facts = { name: 'ORANGE CREAM ENERGY', brand: 'GHOST', price: '2.99 USD', color: 'Orange',
    description: '200mg natural caffeine, zero sugar.' };
  assert.equal(factsLine(facts), 'ORANGE CREAM ENERGY · GHOST · Orange · 2.99 USD');
  assert.equal(factsBlurb(facts), '200mg natural caffeine, zero sugar.');
});

test('a brand the name already says is not said twice', () => {
  assert.equal(factsLine({ name: 'GHOST ENERGY - ORANGE CREAM', brand: 'Ghost' }), 'GHOST ENERGY - ORANGE CREAM');
  assert.equal(factsLine({ name: 'Orange', color: 'orange' }), 'Orange');
});

test('a page that said nothing draws nothing', () => {
  for (const none of [null, undefined, {}, { description: 'only a blurb' }, { name: '  ' }]) {
    assert.equal(factsLine(none), '');
  }
  assert.equal(factsBlurb(null), '');
});
