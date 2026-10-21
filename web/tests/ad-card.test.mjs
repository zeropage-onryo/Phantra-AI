import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  beginAd, adRequest, withPreview, windows, span, onWhat, editBeat, removeBeat, scriptOf,
  wordCount, canBuild, isAdTool,
} from '../src/lib/ad-card.ts';

const BEAT = (over = {}) => ({ headline: 'Find the right talent.', big_word: 'TALENT', card: 1,
  card_caption: '', label: '', background: 'background', seconds: 2.5, picture: null,
  move: 'hold', voiceover: 'Find vetted people.', ...over });
const JOB = { title: 'Meet Gygler', beats: [BEAT({ card: null, headline: 'Staffing is a mess.', background: 'primary', voiceover: 'Short-staffed?' }), BEAT(), BEAT({ card: null, picture: 1, voiceover: '' })],
  warnings: ['beat 2: check it'], cards: [{ handle: 'asset:4', name: 'Talent search' }],
  pictures: [{ handle: 'asset:9', name: 'look reference 1' }], brand_kit: 'Gygler' };

test('the tool name is the server one', () => {
  assert.ok(isAdTool('make_ad') && !isAdTool('make_video'));
});

test('a new card takes the brief and falls back to the route defaults', () => {
  const s = beginAd('a', { brief: '  An ad  ', seconds: 30, aspect: '9:16' });
  assert.deepEqual([s.brief, s.seconds, s.aspect, s.status], ['An ad', 30, '9:16', 'writing']);
  const d = beginAd('b', { brief: 'x', aspect: '4:3' });
  assert.deepEqual([d.seconds, d.aspect], [20, '16:9']);
});

test('the preview asks for no script; the build sends the beats and the same screens back', () => {
  const s = withPreview(beginAd('a', { brief: 'An ad' }), JOB);
  assert.deepEqual(adRequest(s, 7, false), { brief: 'An ad', seconds: 20, aspect: '16:9', project_id: 7, preview: true });
  const b = adRequest(s, null, true);
  assert.equal(b.preview, undefined);
  assert.equal(b.script.beats.length, 3);
  assert.deepEqual(b.cards, ['asset:4']);
  assert.deepEqual(b.pictures, ['asset:9']);
  assert.equal(b.kit_pictures, false);            // the kit is not gathered again: numbers would shift
  assert.equal(b.project_id, undefined);
});

test('windows run end to end and read as times', () => {
  assert.deepEqual(windows([BEAT(), BEAT({ seconds: 3 })]), [{ start: 0, end: 2.5 }, { start: 2.5, end: 5.5 }]);
  assert.equal(span({ start: 2.5, end: 5 }), '2.5–5s');
});

test('a beat says what it sits on', () => {
  const s = withPreview(beginAd('a', { brief: 'x' }), JOB);
  assert.equal(onWhat(s.beats[0], s), 'brand colour');
  assert.equal(onWhat(s.beats[1], s), 'screen · Talent search');
  assert.equal(onWhat(s.beats[2], s), 'photo · look reference 1');
});

test('only the headline and voiceover change, and the card says it was edited', () => {
  const s = withPreview(beginAd('a', { brief: 'x' }), JOB);
  const e = editBeat(s, 2, { headline: 'Hire faster.' });
  assert.equal(e.beats[1].headline, 'Hire faster.');
  assert.equal(e.beats[1].voiceover, 'Find vetted people.');
  assert.equal(e.beats[0], s.beats[0]);
  assert.ok(e.edited && !s.edited);
});

test('a beat is removed, never the last one', () => {
  const s = withPreview(beginAd('a', { brief: 'x' }), JOB);
  assert.equal(removeBeat(s, 1).beats.length, 2);
  const one = { ...s, beats: [BEAT()] };
  assert.equal(removeBeat(one, 1), one);
});

test('the script is the lines in order, and a card builds only once written', () => {
  const s = withPreview(beginAd('a', { brief: 'x' }), JOB);
  assert.equal(scriptOf(s.beats), 'Short-staffed? Find vetted people.');
  assert.equal(wordCount(scriptOf(s.beats)), 4);
  assert.ok(canBuild(s));
  assert.ok(!canBuild(beginAd('a', { brief: 'x' })));
  assert.ok(!canBuild({ ...s, status: 'building' }));
});
