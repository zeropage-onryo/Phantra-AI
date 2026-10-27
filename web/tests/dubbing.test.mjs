import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  clipChoices, beginDub, speakerCount, dubMissing, dubRequest, dubPriceKey, languageName, priceLine,
} from '../src/lib/dubbing.ts';

const MENU = {
  languages: [{ code: 'es', name: 'Spanish' }, { code: 'fr', name: 'French' }],
  speakers_max: 50,
};
const CLIP = { ref: 'gen:13', kind: 'clip', from: 'the last clip' };
const OLDER = { ref: 'asset:4', kind: 'clip', from: 'an earlier clip' };
const STILL = { ref: 'gen:12', kind: 'image', thumb: '/r/a.png', from: 'the last still' };

test('the clip choices are clips, each once, in order', () => {
  assert.deepEqual(clipChoices([STILL, CLIP, OLDER, CLIP]), [CLIP, OLDER]);
});

test('a new card takes the pointed-at clip, else the newest, never a still', () => {
  assert.equal(beginDub([STILL, CLIP, OLDER], 'a').clip, CLIP);
  assert.equal(beginDub([CLIP, OLDER], 'a', { on: OLDER }).clip, OLDER);
  assert.equal(beginDub([STILL], 'a', { on: STILL }).clip, null);
  const s = beginDub([CLIP], 'a');
  assert.equal(s.consent, false, 'consent is never pre-ticked');
  assert.equal(s.target, '');
});

test('a named language is kept only when the menu offers it', () => {
  assert.equal(beginDub([CLIP], 'a', { target: ' ES ' }, MENU).target, 'es');
  assert.equal(beginDub([CLIP], 'a', { target: 'it' }, MENU).target, '');
  assert.equal(beginDub([CLIP], 'a', { target: 'es' }, null).target, '');
});

test('speakers is a whole number in range, else left to the model', () => {
  assert.equal(speakerCount('3'), 3);
  assert.equal(speakerCount(' 50 '), 50);
  for (const bad of ['', '0', '51', '2.5', '-1', 'two', '1e2']) assert.equal(speakerCount(bad), null, bad);
});

test('what is missing is said in order, and "" when nothing is', () => {
  const ok = { ...beginDub([CLIP], 'a'), target: 'es' };
  assert.equal(dubMissing({ ...ok, clip: null }, MENU), 'Pick the clip to dub');
  assert.equal(dubMissing({ ...ok, target: '' }, MENU), 'Pick the language to dub it into');
  assert.match(dubMissing({ ...ok, target: 'it' }, MENU), /not offered/);
  assert.match(dubMissing({ ...ok, source: 'english' }, MENU), /two-letter/);
  assert.match(dubMissing({ ...ok, source: 'ES' }, MENU), /already in that language/);
  assert.match(dubMissing({ ...ok, speakers: '99' }, MENU), /1 to 50/);
  assert.equal(dubMissing({ ...ok, source: 'en', speakers: '2' }, MENU), '');
  assert.equal(dubMissing(ok, MENU), '', 'consent is not a reason the price cannot show');
});

test('the request carries ids, the box and only what was filled in', () => {
  const s = { ...beginDub([CLIP], 'a'), target: 'es', consent: true };
  assert.deepEqual(dubRequest(s), { source: 'gen:13', target_language: 'es', source_language: '', consent: true });
  assert.deepEqual(dubRequest({ ...s, source: ' EN ', speakers: '2' }, 7), {
    source: 'gen:13', target_language: 'es', source_language: 'en', speakers: 2, consent: true, project_id: 7,
  });
  assert.equal(dubRequest({ ...s, target: '' }), null);
  assert.equal(dubRequest({ ...s, clip: null }), null);
  assert.equal(dubRequest({ ...s, consent: false }).consent, false, 'the box is sent as it stands');
});

test('the price key moves with the clip, language and speakers, not the box', () => {
  const s = { ...beginDub([CLIP], 'a'), target: 'es' };
  assert.equal(dubPriceKey(s), dubPriceKey({ ...s, consent: true }));
  assert.notEqual(dubPriceKey(s), dubPriceKey({ ...s, target: 'fr' }));
  assert.notEqual(dubPriceKey(s), dubPriceKey({ ...s, clip: OLDER }));
  assert.notEqual(dubPriceKey(s), dubPriceKey({ ...s, speakers: '3' }));
  assert.equal(dubPriceKey({ ...s, target: '' }), '');
});

test('names and price lines', () => {
  assert.equal(languageName(MENU, 'fr'), 'French');
  assert.equal(languageName(null, 'fr'), 'fr');
  assert.equal(priceLine({ credits: 1440, charged: true }), '1,440 credits');
  assert.equal(priceLine({ credits: 144, charged: true }, true), '144 credits · not charged');
});
