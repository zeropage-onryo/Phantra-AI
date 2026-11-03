import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  cameraMode, cameraConflict, blockedBy, cameraChips, cameraFields, moveValue, lensValue, NO_CAMERA,
} from '../src/lib/camera.ts';

const CAT = {
  moves: [
    { id: 'push_in', label: 'Push in', words: 'The camera slowly dollies in.' },
    { id: 'orbit', label: 'Orbit', words: 'The camera orbits.' },
    { id: 'rack_focus', label: 'Rack focus', words: 'Focus pulls.' },
  ],
  focal: [{ id: '85', label: '85mm', words: 'portrait-lens look' }],
  aperture: [{ id: 'f11', label: 'f/11', words: 'deep focus' }, { id: 'f1.4', label: 'f/1.4', words: 'bokeh' }],
  looks: [{ id: 'anamorphic', label: 'Anamorphic', words: 'anamorphic flares' }],
  conflicts: [{ a: 'rack_focus', b: 'f11', why: 'Rack focus needs a shallow focus.' }],
};
const LTX = { camera: { exact: ['push_in'], clips: [], clip_resolutions: [] } };
const SEED = { camera: { exact: [], clips: ['orbit'], clip_resolutions: ['1080p'] } };
const VEO = { camera: { exact: [], clips: [], clip_resolutions: [] } };

test('a move reaches a model the way the server says', () => {
  assert.equal(cameraMode(LTX, 'push_in', false, '720p'), 'exact');
  assert.equal(cameraMode(LTX, 'orbit', false, '720p'), 'guided');
  assert.equal(cameraMode(SEED, 'orbit', false, '1080p'), 'clip');
  assert.equal(cameraMode(SEED, 'orbit', false, '720p'), 'guided');   // Replicate tier: no clip
  assert.equal(cameraMode(SEED, 'orbit', true, '1080p'), 'guided');   // a start frame: words
  assert.equal(cameraMode(VEO, '', false, '720p'), null);
  assert.equal(cameraMode(null, 'orbit', false, null), 'guided');
});

test('contradicting picks are named and blocked', () => {
  const pick = { ...NO_CAMERA, move: 'rack_focus' };
  assert.equal(blockedBy(CAT, pick, 'f11'), 'Rack focus needs a shallow focus.');
  assert.equal(blockedBy(CAT, pick, 'f1.4'), '');
  assert.equal(cameraConflict(CAT, { ...pick, aperture: 'f11' }), 'Rack focus needs a shallow focus.');
  assert.equal(cameraConflict(CAT, pick), '');
});

test('chips show what is added, and fields carry only the picks', () => {
  const pick = { move: 'push_in', focal: '85', aperture: 'f1.4', look: '' };
  assert.deepEqual(cameraChips(CAT, LTX, pick, false, '720p'), [
    { key: 'move', badge: 'Exact', text: 'The camera slowly dollies in.' },
    { key: 'lens', badge: 'Lens', text: 'portrait-lens look; bokeh' },
  ]);
  assert.deepEqual(cameraChips(CAT, VEO, NO_CAMERA, false, '720p'), []);
  assert.equal(cameraChips(CAT, SEED, { ...NO_CAMERA, move: 'orbit' }, false, '1080p')[0].badge, 'Reference clip');
  assert.deepEqual(cameraFields(pick), [['camera_move', 'push_in'], ['lens_focal', '85'], ['lens_aperture', 'f1.4']]);
  assert.equal(moveValue(CAT, pick), 'Push in');
  assert.equal(lensValue(CAT, pick), '85mm · f/1.4');
  assert.equal(lensValue(CAT, NO_CAMERA), 'Lens');
});
