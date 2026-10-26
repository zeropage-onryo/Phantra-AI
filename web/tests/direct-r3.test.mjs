import { test } from 'node:test';
import assert from 'node:assert/strict';
import { STARTERS, modelBadges, refsCountLine, reuseOf } from '../src/lib/direct.ts';

/* The r3 Image and Video pages (2026-10-26): what a menu row says, the
   reference count, Reuse settings and the starters. */
const KLING4 = {
  id: 'kling4', label: 'Kling 4.0', note: 'up to 30 s', credits: 189,
  seconds: { kind: 'range', min: 3, max: 30, default: 5 }, resolutions: ['720p', '1080p'], resolution: '720p',
  aspects: ['9:16', '16:9'], aspect: '9:16', prompt_max: 26000, max_refs: 10, ref_tag: '@Image1', ref_resolutions: null,
};
const VEO = { ...KLING4, id: 'veo3.1', label: 'Veo 3.1', credits: 1576, seconds: { kind: 'choices', values: [4, 6, 8], default: 6 }, max_refs: 0 };

test('a menu row says the price, then the longest take and the pictures a clip holds', () => {
  assert.equal(modelBadges(KLING4), '189 cr · 30s · 10 pics');
  assert.equal(modelBadges(VEO), '1,576 cr · 8s');
  assert.equal(modelBadges({ id: 'nano', label: 'Nano Banana', note: '', references: true, credits: 10, max_refs: 12 }), '10 cr · 12 refs');
  assert.equal(modelBadges({ id: 'flux', label: 'FLUX 1.1 Pro', note: '', references: false, credits: 10, max_refs: 0 }), '10 cr · text only');
});

test('the reference count says when a text-only model would not send them', () => {
  assert.equal(refsCountLine(12, 2), '2 of 12');
  assert.equal(refsCountLine(0, 3), 'not sent');
  assert.equal(refsCountLine(0, 0), 'text only');
});

test('reuse puts the prompt back, and the model only when this menu has it', () => {
  const menu = { items: [{ id: 'kling4' }, { id: 'veo3.1' }] };
  assert.deepEqual(reuseOf({ prompt: 'a rider', model: 'kling4' }, menu), { prompt: 'a rider', model: 'kling4' });
  assert.deepEqual(reuseOf({ prompt: 'a rider', model: 'runway-gen4' }, menu), { prompt: 'a rider', model: null });
  assert.deepEqual(reuseOf({ prompt: 'a rider' }, null), { prompt: 'a rider', model: null });
});

test('the starters are prompts, not runs', () => {
  for (const kind of ['image', 'video']) {
    assert.ok(STARTERS[kind].length >= 3);
    for (const s of STARTERS[kind]) assert.ok(s.length > 20 && s.length < 200);
  }
});
