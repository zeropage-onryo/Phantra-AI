import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  proposedOf, stepModel, optionLabel, modelLine, referencesWarning, autoCovers, creditsById, renderLine,
} from '../src/lib/step-model.ts';

const MENU = [
  { id: 'nano', label: 'Nano Banana', references: true, credits: 10 },
  { id: 'flux-pro1.1', label: 'FLUX 1.1 Pro', references: false, credits: 10 },
  { id: 'ideogram4.5', label: 'Ideogram 4.5', references: false, credits: 19 },
  { id: 'gpt-image-2', label: 'GPT Image 2', references: true, credits: 33 },
  { id: 'unpriced', label: 'No price yet', references: true, credits: null },
];

test('a proposal counts only when the menu has that model', () => {
  assert.deepEqual(proposedOf({ model: ' ideogram4.5 ', model_why: ' the words must read ' }, MENU),
    { id: 'ideogram4.5', why: 'the words must read' });
  assert.deepEqual(proposedOf({ model: 'nano' }, MENU), { id: 'nano', why: '' });
  for (const none of [{ model: 'veo3.1' }, { model: '' }, { model_why: 'x' }, { model: 7 }, {}, null, undefined]) {
    assert.equal(proposedOf(none, MENU), null);
  }
  assert.equal(proposedOf({ model: 'nano' }, []), null);
});

test('a still is made on your choice, else the proposal, else the picker', () => {
  const args = { model: 'ideogram4.5', model_why: 'the words must read' };
  assert.deepEqual(stepModel(null, args, MENU, 'nano'), { id: 'ideogram4.5', by: 'proposed', why: 'the words must read' });
  assert.deepEqual(stepModel('gpt-image-2', args, MENU, 'nano'), { id: 'gpt-image-2', by: 'you', why: '' });
  assert.deepEqual(stepModel(null, {}, MENU, 'nano'), { id: 'nano', by: 'picked', why: '' });
  // a choice the menu no longer lists falls through
  assert.deepEqual(stepModel('retired', args, MENU, 'nano').by, 'proposed');
  assert.deepEqual(stepModel('retired', { model: 'also-gone' }, MENU, 'nano'), { id: 'nano', by: 'picked', why: '' });
});

test('the card says whose pick the model is, and why', () => {
  assert.equal(modelLine({ id: 'ideogram4.5', by: 'proposed', why: 'the words must read' }, MENU), 'Ideogram 4.5 proposed: the words must read');
  assert.equal(modelLine({ id: 'ideogram4.5', by: 'proposed', why: '' }, MENU), 'Ideogram 4.5 proposed');
  assert.equal(modelLine({ id: 'nano', by: 'you', why: '' }, MENU), 'Your choice for this still');
  assert.equal(modelLine({ id: 'nano', by: 'picked', why: '' }, MENU), '');
  // the pulldown names the model only; the price is on Approve (2026-10-27)
  assert.equal(optionLabel(MENU[2]), 'Ideogram 4.5');
  assert.equal(optionLabel(MENU[4]), 'No price yet');
  assert.equal(optionLabel({ id: 'x', label: 'Big', credits: 1250 }), 'Big');
});

test('a model that takes no references says so before the click', () => {
  assert.equal(referencesWarning(MENU[2], 2), 'Ideogram 4.5 takes no references: the 2 pictures attached will not reach it.');
  assert.equal(referencesWarning(MENU[2], 1), 'Ideogram 4.5 takes no references: the picture attached will not reach it.');
  assert.equal(referencesWarning(MENU[2], 0), '');
  assert.equal(referencesWarning(MENU[0], 3), '');
  assert.equal(referencesWarning(null, 3), '');
  // not known is not "takes none"
  assert.equal(referencesWarning({ id: 'x', label: 'X' }, 3), '');
});

test('with Auto on, a model that costs more than the send said waits for its Approve', () => {
  const step = (id) => ({ id, by: 'proposed', why: '' });
  assert.equal(autoCovers(step('nano'), MENU, 'nano'), true);          // the picked model itself
  assert.equal(autoCovers(step('flux-pro1.1'), MENU, 'nano'), true);   // the same price
  assert.equal(autoCovers(step('ideogram4.5'), MENU, 'nano'), false);  // dearer
  assert.equal(autoCovers(step('nano'), MENU, 'gpt-image-2'), true);   // cheaper
  assert.equal(autoCovers(step('unpriced'), MENU, 'nano'), false);     // an unknown price is not "no more"
  assert.equal(autoCovers(step('ideogram4.5'), MENU, 'unpriced'), false);
  assert.equal(autoCovers(step('unpriced'), MENU, 'unpriced'), true);
});

test('a plan prices each still by its own model, and a scene names where its card opens', () => {
  assert.deepEqual(creditsById(MENU), { nano: 10, 'flux-pro1.1': 10, 'ideogram4.5': 19, 'gpt-image-2': 33 });
  const clips = [{ id: 'kling3-turbo-pro', label: 'Kling 3 Turbo Pro' }, { id: 'veo3.1', label: 'Veo 3.1' }];
  assert.equal(renderLine(clips, 'kling3-turbo-pro', 'people moving'), 'Its Render card opens on Kling 3 Turbo Pro: people moving');
  assert.equal(renderLine(clips, 'veo3.1'), 'Its Render card opens on Veo 3.1');
  assert.equal(renderLine(clips, 'sora', 'x'), '');
  assert.equal(renderLine(clips, null), '');
});
