import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  secondsChoices, openingModel, videoPickFor, keptLine, secondsSpan, imagePickFor,
  referencesLine, buttonLabel, videoModelLine, imageModelLine, readPick, directHref,
  videoRefMode, videoRefTags,
} from '../src/lib/direct.ts';

const VEO = {
  id: 'veo3.1', label: 'Veo 3.1', note: 'with sound', credits: 768,
  seconds: { kind: 'choices', values: [4, 6, 8], default: 6 },
  resolutions: ['720p', '1080p'], resolution: '720p',
  aspects: ['16:9', '9:16'], aspect: '9:16',
};
const SEEDANCE = {
  id: 'seedance2.5', label: 'Seedance 2.5', note: 'up to 30s', credits: 300,
  seconds: { kind: 'range', min: 4, max: 30, default: 5 },
  resolutions: ['480p', '720p', '1080p'], resolution: '720p',
  aspects: ['16:9', '9:16', '1:1', '21:9'], aspect: '9:16',
};

test('every legal length, from a list or a span', () => {
  assert.deepEqual(secondsChoices(VEO.seconds), [4, 6, 8]);
  assert.equal(secondsChoices(SEEDANCE.seconds).length, 27);
  assert.equal(secondsChoices(SEEDANCE.seconds)[0], 4);
  assert.deepEqual(secondsChoices({ kind: 'fixed', values: [5], default: 5 }), [5]);
  assert.deepEqual(secondsChoices(null), []);
  assert.equal(secondsSpan(VEO.seconds), '4-8s');
  assert.equal(secondsSpan({ kind: 'fixed', values: [5], default: 5 }), '5s');
});

test('the page opens on the link, then the last pick, then the default', () => {
  const menu = { items: [VEO, SEEDANCE], default: 'veo3.1' };
  assert.equal(openingModel(menu, 'seedance2.5', 'veo3.1'), 'seedance2.5');
  assert.equal(openingModel(menu, 'sora-9', 'seedance2.5'), 'seedance2.5');
  assert.equal(openingModel(menu, null, 'gone'), 'veo3.1');
  assert.equal(openingModel({ items: [SEEDANCE], default: 'veo3.1' }, null, null), 'seedance2.5');
  assert.equal(openingModel({ items: [], default: '' }, 'x', 'y'), '');
});

test('a pick keeps what the new model takes and resets the rest to its opening, never a nearest', () => {
  const was = { model: 'seedance2.5', seconds: 12, resolution: '1080p', aspect: '21:9' };
  const now = videoPickFor(VEO, was);
  assert.deepEqual(now, { model: 'veo3.1', seconds: 6, resolution: '1080p', aspect: '9:16' });
  assert.equal(keptLine(VEO, was, now), 'Veo 3.1 does not take that, so 12s became 6s, 21:9 became 9:16.');
  const back = videoPickFor(SEEDANCE, now);
  assert.deepEqual(back, { model: 'seedance2.5', seconds: 6, resolution: '1080p', aspect: '9:16' });
  assert.equal(keptLine(SEEDANCE, now, back), '');
  assert.deepEqual(videoPickFor(VEO, null), { model: 'veo3.1', seconds: 6, resolution: '720p', aspect: '9:16' });
  assert.equal(keptLine(VEO, null, videoPickFor(VEO, null)), '');
});

test('a still pick keeps its frame when the frame is offered', () => {
  const m = { id: 'flux2-pro', label: 'FLUX.2 Pro', note: '', references: true, credits: 12, max_refs: 8 };
  assert.deepEqual(imagePickFor(m, { aspect: '16:9' }, ['1:1', '16:9']), { model: 'flux2-pro', aspect: '16:9' });
  assert.deepEqual(imagePickFor(m, { aspect: '7:3' }, ['1:1', '16:9']), { model: 'flux2-pro', aspect: '1:1' });
});

test('the reference line says before the click what will not reach the model', () => {
  assert.equal(referencesLine({ label: 'Ideogram', max_refs: 0 }, 0), '');
  assert.match(referencesLine({ label: 'Ideogram', max_refs: 0 }, 1), /prompt only: the picture attached will not reach it/);
  assert.match(referencesLine({ label: 'Ideogram', max_refs: 0 }, 3), /the 3 pictures attached/);
  assert.equal(referencesLine({ label: 'FLUX.2', max_refs: 8 }, 8), '');
  assert.equal(referencesLine({ label: 'GPT', max_refs: 4 }, 6), 'GPT takes 4; the first 4 attached are sent.');
  assert.equal(referencesLine(null, 4), '');
});

test('the button always says the credits of the quote on screen', () => {
  assert.equal(buttonLabel(null, false, false), 'Generate · pricing…');
  assert.equal(buttonLabel({ credits: 1234, charged: true }, true, false), 'Generate · pricing…');
  assert.equal(buttonLabel({ credits: 1234, charged: true }, false, false), 'Generate · 1,234 credits');
  assert.equal(buttonLabel({ credits: 50, charged: false }, false, false), 'Generate · 50 credits · not charged');
  assert.equal(buttonLabel({ credits: 50, charged: true }, false, true), 'Generate · 50 credits · not charged');
  for (const s of [buttonLabel({ credits: 9, charged: true }, false, false), videoModelLine(VEO)]) assert.ok(!s.includes('$'));
});

test('the picker lines', () => {
  // no price in a picker line (2026-10-27): only the Generate button says one
  assert.equal(videoModelLine(VEO), '4-8s · 720p-1080p');
  assert.equal(imageModelLine({ id: 'x', label: 'X', note: '', references: false, credits: 19, max_refs: 0 }), 'prompt only');
  assert.equal(imageModelLine({ id: 'x', label: 'X', note: '', references: true, credits: 33, max_refs: 8 }), 'up to 8 references');
});

test('a remembered pick is read back field by field, and junk is nothing', () => {
  assert.deepEqual(readPick('{"model":"veo3.1","seconds":8,"evil":{"x":1}}', ['model', 'seconds', 'evil']), { model: 'veo3.1', seconds: 8 });
  assert.equal(readPick('not json', ['model']), null);
  assert.equal(readPick(null, ['model']), null);
  assert.equal(readPick('7', ['model']), null);
});

test('the link onto a page with its model picked', () => {
  assert.equal(directHref('video', 'kling4'), '/studio/video?model=kling4');
  assert.equal(directHref('image'), '/studio/image');
});

test('a clip\'s pictures: one is a start frame, two or more are references, where the model takes them', () => {
  const seedance = { max_refs: 30 }, veo = { max_refs: 0 };
  assert.equal(videoRefMode(seedance, 0), 'none');
  assert.equal(videoRefMode(seedance, 1), 'start');
  assert.equal(videoRefMode(seedance, 1, true), 'references');
  assert.equal(videoRefMode(seedance, 3), 'references');
  // a model with no reference endpoint only ever starts on a picture
  assert.equal(videoRefMode(veo, 1, true), 'start');
  assert.equal(videoRefMode(null, 2), 'start');
});

test('the prompt names pictures by the model\'s own tags', () => {
  assert.deepEqual(videoRefTags({ ref_tag: '@Image1' }, 3), ['@Image1', '@Image2', '@Image3']);
  assert.deepEqual(videoRefTags({ ref_tag: '<IMAGE_0>' }, 2), ['<IMAGE_0>', '<IMAGE_1>']);
  assert.deepEqual(videoRefTags({ ref_tag: null }, 2), []);
});
