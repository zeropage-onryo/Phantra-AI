import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  LOOKS,
  CREATURES,
  MOODS,
  allImages,
  coloursOf,
  decodeMascot,
  encodeMascot,
  isMascotCode,
  looksOf,
  mascotSrc,
  moodFor,
  nameOf,
  sizeFor,
  smallerSrc,
  DEFAULT_AVATAR,
  OFFERED_CREATURES,
} from '../src/lib/mascot.ts';

test('the asset set is the 490 images that were rendered', () => {
  // 16 looks: the Ferryman's Storm in its own colour only; of the plush fifteen,
  // the six that own a shared colour have 4 colours, the other nine 5; 7 moods each
  assert.equal(LOOKS.length, 16);
  assert.deepEqual(coloursOf('ferryman-storm').map((c) => c.id), ['own']);
  const four = LOOKS.filter((l) => coloursOf(l.id).length === 4).map((l) => l.id).sort();
  assert.deepEqual(four, ['glim-clay', 'glim-felt', 'nimbus-felt', 'nimbus-knit', 'pip-orig', 'sprout-felt']);
  assert.equal(allImages().length, 490);
  assert.equal(new Set(allImages()).size, 490);
  assert.deepEqual([...MOODS], ['awake', 'listen', 'think', 'talk', 'made', 'oops', 'sleep']);
  for (const mood of MOODS) assert.ok(allImages().includes(`ferryman-storm-own-${mood}`), mood);
});

test('the Ferryman comes first in one look; every plush creature has three; the names never change', () => {
  assert.deepEqual(CREATURES.map((c) => c.name), ['Vesper', 'Nimbus', 'Mote', 'Sprout', 'Glim', 'Pip']);
  assert.deepEqual(looksOf('ferryman').map((l) => l.id), ['ferryman-storm']);
  for (const c of CREATURES.slice(1)) assert.equal(looksOf(c.id).length, 3, c.id);
  // every look has its own two-letter code
  assert.equal(new Set(LOOKS.map((l) => l.code)).size, LOOKS.length);
});

test('a code fits the server avatar column and survives its cleaner', () => {
  // assistant_store.clean_avatar: drops whitespace, < > & " ' and cuts to 16
  for (const look of LOOKS)
    for (const c of coloursOf(look.id)) {
      const code = encodeMascot({ look: look.id, colour: c.id });
      assert.ok(code.length <= 16, code);
      assert.equal(code.replace(/[\s<>&"']/g, ''), code);
      assert.ok(isMascotCode(code), code);
      // only the Ferryman is offered; a plush code decodes to him
      const want = look.creature === 'ferryman' ? { look: look.id, colour: c.id } : { look: 'ferryman-storm', colour: 'own' };
      assert.deepEqual(decodeMascot(code), want);
    }
});

test('anything that is not a mascot code reads as the Ferryman in Storm', () => {
  for (const old of ['🦊', 'glyph:aperture', '', null, undefined, 'm:zz.own', 'm:fs.xyz'])
    assert.deepEqual(decodeMascot(old), { look: 'ferryman-storm', colour: 'own' }, String(old));
  assert.equal(DEFAULT_AVATAR, 'm:fs.own');
  assert.equal(nameOf(decodeMascot('🦊')), 'Vesper');
  // only the Ferryman is offered (2026-10-15): a stored plush code reads as him
  assert.deepEqual(OFFERED_CREATURES.map((c) => c.id), ['ferryman']);
  assert.equal(nameOf(decodeMascot('m:pm.red')), 'Vesper');
  assert.deepEqual(decodeMascot('m:nf.own'), { look: 'ferryman-storm', colour: 'own' });
});

test('the Ferryman is offered no shared colour', () => {
  assert.deepEqual(decodeMascot('m:fs.red'), { look: 'ferryman-storm', colour: 'own' });
  assert.equal(encodeMascot({ look: 'ferryman-storm', colour: 'sky' }), 'm:fs.own');
  assert.match(mascotSrc({ look: 'ferryman-storm', colour: 'mint' }, 'think', 640), /\/640\/ferryman-storm-own-think\.webp$/);
});

test('a colour a look does not come in falls back to its own', () => {
  // nimbus-felt IS lavender, so it is never offered lavender again
  // (and a plush code now decodes to the Ferryman)
  assert.deepEqual(decodeMascot('m:nf.lav'), { look: 'ferryman-storm', colour: 'own' });
  assert.equal(encodeMascot({ look: 'nimbus-felt', colour: 'lavender' }), 'm:nf.own');
});

test('the image url names the look, colour, mood and size', () => {
  const src = mascotSrc({ look: 'sprout-velvet', colour: 'lightred' }, 'think', 320);
  assert.match(src, /\/320\/sprout-velvet-lightred-think\.webp$/);
  assert.equal(sizeFor(56), 128);
  assert.equal(sizeFor(96), 320);
  assert.equal(sizeFor(320), 640); // the floating creature
  assert.equal(smallerSrc(mascotSrc({ look: 'pip-orig', colour: 'own' }, 'awake', 640)), mascotSrc({ look: 'pip-orig', colour: 'own' }, 'awake', 320));
  assert.equal(smallerSrc(mascotSrc({ look: 'pip-orig', colour: 'own' }, 'awake', 320)), null);
});

test('states map to moods, and talking flaps between two frames', () => {
  assert.equal(moodFor('idle'), 'awake');
  assert.equal(moodFor('listening'), 'listen');
  assert.equal(moodFor('thinking'), 'think');
  assert.equal(moodFor('working'), 'think');
  assert.equal(moodFor('needs'), 'awake');
  assert.equal(moodFor('success'), 'made');
  assert.equal(moodFor('error'), 'oops');
  assert.equal(moodFor('sleeping'), 'sleep');
  assert.equal(moodFor('talking', true), 'talk');
  assert.equal(moodFor('talking', false), 'awake');
});
