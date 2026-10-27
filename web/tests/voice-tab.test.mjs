import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  pickModel, beginSpeak, speakMissing, speakRequest, speakPriceKey, charCount, priceLine, settleRead, readLine,
} from '../src/lib/voice-tab.ts';

const MODELS = [{ id: 'eleven-v3', kind: 'speak' }, { id: 'elevenlabs-dubbing', kind: 'dub' }];
const MENU = { speak: { voices: ['Rachel', 'Aria'], default_voice: 'Rachel', script_max: 5000 } };

test('the page opens on the named model, by id or kind, else the first', () => {
  assert.equal(pickModel(MODELS, 'elevenlabs-dubbing'), 'elevenlabs-dubbing');
  assert.equal(pickModel(MODELS, 'dub'), 'elevenlabs-dubbing');
  assert.equal(pickModel(MODELS, 'nope'), 'eleven-v3');
  assert.equal(pickModel(MODELS, null), 'eleven-v3');
  assert.equal(pickModel([], 'dub'), '');
});

test('a new read starts empty on the default voice', () => {
  assert.deepEqual(beginSpeak(MENU), { script: '', voice: 'Rachel', language: '' });
  assert.equal(beginSpeak(null).voice, 'Rachel');
});

test('what stops a read is said, and "" when nothing does', () => {
  const ok = { script: 'Hi there.', voice: 'Aria', language: '' };
  assert.equal(speakMissing(ok, MENU), '', 'three words are enough');
  assert.equal(speakMissing({ ...ok, script: '   ' }, MENU), 'Write the words to be read');
  assert.match(speakMissing({ ...ok, script: 'x'.repeat(5001) }, MENU), /5,000/);
  assert.match(speakMissing({ ...ok, voice: 'Darth' }, MENU), /voices/);
  assert.match(speakMissing({ ...ok, language: 'english' }, MENU), /two-letter/);
  assert.equal(speakMissing({ ...ok, language: ' ES ' }, MENU), '');
});

test('the request is trimmed, lower-cased, and carries a project only when there is one', () => {
  const s = { script: '  Hello. ', voice: 'Aria', language: ' FR ' };
  assert.deepEqual(speakRequest(s), { script: 'Hello.', voice: 'Aria', language: 'fr' });
  assert.deepEqual(speakRequest(s, 4), { script: 'Hello.', voice: 'Aria', language: 'fr', project_id: 4 });
  assert.equal(speakPriceKey(s), speakPriceKey({ ...s, script: 'Hello.' }), 'whitespace does not move the price');
  assert.notEqual(speakPriceKey(s), speakPriceKey({ ...s, voice: 'Rachel' }));
});

test('counts and price lines', () => {
  assert.equal(charCount({ script: ' abc ' }, 5000), '3 / 5,000');
  assert.equal(priceLine({ credits: 1200, charged: true }), '1,200 credits');
  assert.equal(priceLine({ credits: 10, charged: false }), '10 credits · not charged');
});

test('a finished job lands on its read; a failed one says nothing was charged', () => {
  const r = { id: 'a', status: 'running', voice: 'Aria', script: 'Hi', paid: { credits: 10, charged: true } };
  const done = settleRead(r, { status: 'done', audio: 'asset:3', seconds: 2.5, output: '/m/a.mp3' });
  assert.equal(done.status, 'done');
  assert.equal(done.audio, 'asset:3');
  assert.equal(done.url, '/m/a.mp3');
  const failed = settleRead(r, { status: 'failed', error: '' });
  assert.equal(failed.status, 'failed');
  assert.match(failed.error, /Nothing was charged/);
  assert.equal(settleRead(r, { status: 'done' }).status, 'failed', 'done with no audio is not a read');
  assert.equal(readLine(done), 'Aria · 2.5s · 10 credits');
  assert.equal(readLine(r, true), 'Aria · 10 credits · not charged');
});

import {
  beginLibrary, libraryMissing, libraryRequest, libraryVoiceName, libraryVoiceIds,
  beginDialogue, presetLabel, addSpeaker, removeSpeaker, addLine, dialogueScript, dialogueMissing, dialogueRequest,
} from '../src/lib/voice-tab.ts';

const LIB = {
  languages: [
    { language: 'English', voices: [{ id: 'Wise_Woman', name: 'Wise Woman' }, { id: 'English_CalmWoman', name: 'Calm Woman' }] },
    { language: 'Spanish', voices: [{ id: 'Spanish_Narrator', name: 'Narrator' }] },
  ],
  default_voice: 'Wise_Woman', emotions: ['neutral', 'happy', 'sad'], speed: [0.5, 2], pitch: [-12, 12], script_max: 5000,
};
const DIA = {
  presets: ['Alice [EN]', 'Carter [EN]', 'Frank [EN]', 'Mary [EN] (Background Music)', 'Maya [EN]', 'Bowen [ZH]'],
  max_speakers: 4, max_lines: 200, script_max: 5000,
};

test('a library read starts on the default voice, neutral, at normal speed and pitch', () => {
  assert.deepEqual(beginLibrary(LIB), { script: '', voice: 'Wise_Woman', emotion: '', speed: 1, pitch: 0 });
  assert.deepEqual(libraryVoiceIds(LIB), ['Wise_Woman', 'English_CalmWoman', 'Spanish_Narrator']);
  assert.equal(libraryVoiceName(LIB, 'Spanish_Narrator'), 'Narrator · Spanish');
  assert.equal(libraryVoiceName(null, 'x'), 'x');
});

test('what stops a library read is said in order', () => {
  const ok = { ...beginLibrary(LIB), script: 'Hello.' };
  assert.equal(libraryMissing(ok, LIB), '');
  assert.match(libraryMissing({ ...ok, script: ' ' }, LIB), /Write/);
  assert.match(libraryMissing({ ...ok, voice: 'Nope' }, LIB), /voices/);
  assert.match(libraryMissing({ ...ok, emotion: 'smug' }, LIB), /emotions/);
  assert.match(libraryMissing({ ...ok, speed: 2.5 }, LIB), /Speed/);
  assert.match(libraryMissing({ ...ok, pitch: 1.5 }, LIB), /Pitch/);
  assert.match(libraryMissing({ ...ok, pitch: -13 }, LIB), /Pitch/);
  assert.deepEqual(libraryRequest({ ...ok, script: ' Hi ', emotion: 'sad' }, 3), {
    script: 'Hi', voice: 'Wise_Woman', emotion: 'sad', speed: 1, pitch: 0, project_id: 3,
  });
});

test('a dialogue starts with two English speakers, a line each', () => {
  const s = beginDialogue(DIA);
  assert.deepEqual(s.speakers, ['Alice [EN]', 'Carter [EN]']);
  assert.deepEqual(s.lines, [{ speaker: 0, text: '' }, { speaker: 1, text: '' }]);
  assert.equal(presetLabel('Mary [EN] (Background Music)'), 'Mary · EN · with music');
  assert.equal(presetLabel('Bowen [ZH]'), 'Bowen · ZH');
});

test('speakers are added up to the cap and removed with their lines', () => {
  let s = beginDialogue(DIA);
  s = addSpeaker(s, DIA);
  assert.deepEqual(s.speakers, ['Alice [EN]', 'Carter [EN]', 'Frank [EN]']);
  s = addSpeaker(addSpeaker(s, DIA), DIA);
  assert.equal(s.speakers.length, 4, 'four at most');
  s = { ...s, lines: [{ speaker: 0, text: 'a' }, { speaker: 1, text: 'b' }, { speaker: 2, text: 'c' }, { speaker: 3, text: 'd' }] };
  const r = removeSpeaker(s, 1);
  assert.deepEqual(r.speakers, ['Alice [EN]', 'Frank [EN]', 'Mary [EN] (Background Music)']);
  assert.deepEqual(r.lines, [{ speaker: 0, text: 'a' }, { speaker: 1, text: 'c' }, { speaker: 2, text: 'd' }]);
  assert.equal(removeSpeaker({ speakers: ['Alice [EN]'], lines: [] }, 0).speakers.length, 1, 'the last one stays');
});

test('a new line goes round the table', () => {
  const s = addLine(beginDialogue(DIA));
  assert.deepEqual(s.lines.at(-1), { speaker: 0, text: '' });
  assert.deepEqual(addLine({ speakers: ['Alice [EN]'], lines: [] }).lines, [{ speaker: 0, text: '' }]);
});

test('the dialogue script and request are the server\'s shape', () => {
  const s = { speakers: ['Alice [EN]', 'Carter [EN]'], lines: [{ speaker: 0, text: ' Hi\n there ' }, { speaker: 1, text: '' }, { speaker: 1, text: 'Hey.' }] };
  assert.equal(dialogueScript(s), 'Speaker 0: Hi there\nSpeaker 1: Hey.');
  assert.deepEqual(dialogueRequest(s, 2), {
    speakers: ['Alice [EN]', 'Carter [EN]'], lines: [{ speaker: 0, text: 'Hi there' }, { speaker: 1, text: 'Hey.' }], project_id: 2,
  });
});

test('what stops a dialogue is said', () => {
  const ok = { speakers: ['Alice [EN]', 'Carter [EN]'], lines: [{ speaker: 0, text: 'Hi' }, { speaker: 1, text: 'Hey' }] };
  assert.equal(dialogueMissing(ok, DIA), '');
  assert.match(dialogueMissing({ ...ok, lines: [{ speaker: 0, text: '' }] }, DIA), /first line/);
  assert.match(dialogueMissing({ ...ok, lines: [{ speaker: 0, text: 'Hi' }] }, DIA), /Speaker 2 has no lines/);
  assert.match(dialogueMissing({ ...ok, speakers: ['Alice [EN]', 'Darth'] }, DIA), /voice for every/);
  assert.match(dialogueMissing({ ...ok, lines: [{ speaker: 0, text: 'Speaker 1: hi' }, { speaker: 1, text: 'x' }] }, DIA), /labels/);
  assert.match(dialogueMissing({ ...ok, lines: [{ speaker: 0, text: 'x'.repeat(5000) }, { speaker: 1, text: 'y' }] }, DIA), /5,000/);
});

import { isSampleFile, cloneMissing, cloneRequest, keepLine } from '../src/lib/voice-tab.ts';

const CM = { min_seconds: 10, max_seconds: 300, name_max: 40, max_clones: 10, voices: [], types: ['.mp3', '.wav', '.m4a', '.ogg', '.aac'] };

test('a clone needs a sample of the right length and a name', () => {
  const sample = { audio: 'asset:7', seconds: 24, filename: 'me.m4a' };
  assert.equal(cloneMissing({ name: 'Me', sample }, CM), '');
  assert.match(cloneMissing({ name: 'Me', sample: null }, CM), /Upload/);
  assert.match(cloneMissing({ name: 'Me', sample: { ...sample, seconds: 8 } }, CM), /at least 10s/);
  assert.match(cloneMissing({ name: 'Me', sample: { ...sample, seconds: 400 } }, CM), /trim/);
  assert.match(cloneMissing({ name: ' ', sample }, CM), /Name/);
  assert.match(cloneMissing({ name: 'Me', sample }, { ...CM, voices: Array(10).fill({}) }), /remove one/);
  assert.deepEqual(cloneRequest({ name: '  My  voice ', sample }), { sample: 'asset:7', name: 'My voice' });
  assert.equal(cloneRequest({ name: 'Me', sample: null }), null);
  assert.equal(isSampleFile('Memo.M4A', CM.types), true);
  assert.equal(isSampleFile('memo.flac', CM.types), false);
});

test('a voice says how long it has before MiniMax deletes it', () => {
  const now = new Date('2026-10-27T12:00:00Z');
  assert.equal(keepLine({ kept: true, expires_at: null }, now), 'Kept');
  assert.match(keepLine({ kept: false, expires_at: '2026-11-01T12:00:00Z' }, now), /within 5 days/);
  assert.match(keepLine({ kept: false, expires_at: '2026-10-28T06:00:00Z' }, now), /today/);
});

import { goLabel, waveBars, VOICE_STARTERS } from '../src/lib/voice-tab.ts';

test('the spend button says what it makes and its price', () => {
  assert.equal(goLabel('Make the voice', { credits: 1200, charged: true }, false, false), 'Make the voice · 1,200 credits');
  assert.equal(goLabel('Dub it', { credits: 144, charged: true }, true, false), 'Dub it · pricing…');
  assert.equal(goLabel('Dub it', null, false, false), 'Dub it · pricing…');
  assert.equal(goLabel('Dub it', { credits: 144, charged: false }, false, false), 'Dub it · 144 credits · not charged');
});

test('a read draws the same bars every time, inside the box', () => {
  const a = waveBars('hello'), b = waveBars('hello'), c = waveBars('other');
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, c);
  assert.equal(a.length, 48);
  assert.ok(a.every((x) => x >= 0.15 && x <= 1));
  assert.ok(VOICE_STARTERS.length >= 3);
});
