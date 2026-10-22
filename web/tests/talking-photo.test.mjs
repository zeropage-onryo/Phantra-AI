import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  beginTalk, photoChoices, isAudioFile, previewCurrent, voiceOf, voiceSeconds, scriptMissing,
  lengthProblem, talkMissing, voiceRequest, talkRequest, priceLine,
} from '../src/lib/talking-photo.ts';

const MENU = { script_min: 50, script_max: 5000, audio_min: 4, audio_cap: 30 };
const STILL = { ref: 'gen:12', kind: 'image', thumb: '/r/a.png', from: 'the last still' };
const BOXED = { ref: '/photos/x.jpg', kind: 'image', thumb: '/photos/x.jpg', from: 'attached' };
const CLIP = { ref: 'gen:13', kind: 'clip', from: 'the last clip' };
const WORDS = 'Hi, I am Maya. Welcome to the shop -- everything here was made by hand.';

test('a new card takes the pointed-at still, else the first image, never a clip', () => {
  assert.equal(beginTalk([CLIP, BOXED, STILL], 'a').photo, BOXED);
  assert.equal(beginTalk([CLIP, BOXED], 'a', { on: STILL }).photo, STILL);
  assert.equal(beginTalk([CLIP], 'a', { on: CLIP }).photo, null);
  const s = beginTalk([], 'a', { script: '  hello ', prompt: ' push in ' });
  assert.equal(s.script, 'hello');
  assert.equal(s.prompt, 'push in');
  assert.equal(s.consent, false, 'consent is never pre-ticked');
  assert.equal(s.mode, 'script');
});

test('the photo choices are images, each once', () => {
  assert.deepEqual(photoChoices([CLIP, STILL, BOXED, STILL]), [STILL, BOXED]);
});

test('only mp3 and wav are a voice', () => {
  assert.ok(isAudioFile('Voice.MP3') && isAudioFile('a.wav'));
  assert.ok(!isAudioFile('a.m4a') && !isAudioFile('a.mp4'));
});

test('a preview is the voice only while its words, voice and language stand', () => {
  const s = {
    ...beginTalk([STILL], 'a', { script: WORDS }),
    preview: { status: 'done', script: WORDS, voice: 'Rachel', language: '', paid: { credits: 10, charged: true }, audio: 'asset:9', seconds: 6.2 },
  };
  assert.ok(previewCurrent(s));
  assert.equal(voiceOf(s), 'asset:9');
  assert.equal(voiceSeconds(s), 6.2);
  assert.equal(voiceOf({ ...s, script: WORDS + '!' }), null);
  assert.equal(voiceOf({ ...s, voice: 'Aria' }), null);
  assert.equal(voiceOf({ ...s, language: 'es' }), null);
  assert.equal(voiceOf({ ...s, preview: { ...s.preview, status: 'running' } }), null);
  // an upload is the voice in upload mode, whatever the preview
  assert.equal(voiceOf({ ...s, mode: 'upload', upload: { audio: 'asset:5', seconds: 10, filename: 'v.mp3' } }), 'asset:5');
  assert.equal(voiceOf({ ...s, mode: 'upload' }), null);
});

test('the script is held to the bounds before it is priced', () => {
  assert.match(scriptMissing({ script: ' ' }, MENU), /Write/);
  assert.match(scriptMissing({ script: 'too short' }, MENU), /at least 50/);
  assert.match(scriptMissing({ script: 'x'.repeat(5001) }, MENU), /under 5,000/);
  assert.equal(scriptMissing({ script: WORDS }, MENU), '');
});

test('the voice length is held to the floor and the plan cap', () => {
  assert.equal(lengthProblem(null, MENU), '');
  assert.match(lengthProblem(3.2, MENU), /at least 4s/);
  assert.match(lengthProblem(31, MENU), /up to 30s/);
  assert.equal(lengthProblem(30.4, MENU), '', 'a "30s" file measures 30.04');
});

test('the render waits on a photo and a voice, not on the consent box', () => {
  const base = beginTalk([], 'a', { script: WORDS });
  assert.match(talkMissing(base, MENU), /photo/);
  const withPhoto = { ...base, photo: STILL };
  assert.match(talkMissing(withPhoto, MENU), /Preview the voice/);
  assert.match(talkMissing({ ...withPhoto, mode: 'upload' }, MENU), /Upload/);
  const up = { ...withPhoto, mode: 'upload', upload: { audio: 'asset:5', seconds: 10, filename: 'v.mp3' } };
  assert.equal(talkMissing(up, MENU), '');
  assert.match(talkMissing({ ...up, upload: { ...up.upload, seconds: 45 } }, MENU), /up to 30s/);
});

test('the bodies the routes take', () => {
  assert.deepEqual(voiceRequest({ script: ` ${WORDS} `, voice: 'Aria', language: ' ES ' }), { script: WORDS, voice: 'Aria', language: 'es' });
  const up = { ...beginTalk([STILL], 'a', { prompt: 'push in' }), mode: 'upload', consent: true, upload: { audio: 'asset:5', seconds: 10, filename: 'v.mp3' } };
  assert.deepEqual(talkRequest(up, 7), { photo: 'gen:12', audio: 'asset:5', prompt: 'push in', consent: true, project_id: 7 });
  assert.deepEqual(talkRequest(up), { photo: 'gen:12', audio: 'asset:5', prompt: 'push in', consent: true });
  assert.equal(talkRequest({ ...up, upload: undefined }), null);
});

test('the price line says credits, and says when nothing is charged', () => {
  assert.equal(priceLine({ credits: 1252, charged: true }), '1,252 credits');
  assert.equal(priceLine({ credits: 10, charged: true }, true), '10 credits · not charged');
});
