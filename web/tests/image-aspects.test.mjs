import { test } from 'node:test';
import assert from 'node:assert/strict';
import { IMAGE_ASPECTS, imageAspectFor } from '../src/lib/image-aspects.ts';

test('every frame the connector names is a still shape the picker has', () => {
  // src/mcp_server.py STUDIO_FRAMES: the frames open_in_studio puts in ?frame=
  const frames = { '9:16': '720:1280', '16:9': '1280:720', '1:1': '960:960',
                   '4:3': '1104:832', '3:4': '832:1104', '21:9': '1584:672' };
  for (const [shape, frame] of Object.entries(frames)) {
    assert.equal(imageAspectFor(frame), shape, frame);
    assert.ok(IMAGE_ASPECTS.some((a) => a.id === shape), shape);
  }
});

test('a shape names itself, and nothing near enough is no shape', () => {
  assert.equal(imageAspectFor('4:5'), '4:5');
  assert.equal(imageAspectFor('1000:1000'), '1:1');
  assert.equal(imageAspectFor('1000:300'), null);
  assert.equal(imageAspectFor('wide'), null);
  assert.equal(imageAspectFor(''), null);
  assert.equal(imageAspectFor(null), null);
});

test('the shape a still prompt names, and when it is not the frame it is drawn in', async () => {
  const { shapeInPrompt, shapeClash } = await import('../src/lib/image-aspects.ts');
  assert.equal(shapeInPrompt('A 9:16 vertical poster of a jar'), '9:16');
  assert.equal(shapeInPrompt('a vertical poster of a jar'), '9:16');
  assert.equal(shapeInPrompt('wide landscape shot of a field'), '16:9');
  assert.equal(shapeInPrompt('square format, top-down flat lay'), '1:1');
  assert.equal(shapeInPrompt('a square jar on a table'), '');          // a square THING is no frame
  assert.equal(shapeInPrompt('the clock reads 3:45'), '');
  assert.equal(shapeInPrompt(''), '');
  assert.equal(shapeClash('a 9:16 poster', '4:5'), '9:16');
  assert.equal(shapeClash('a 9:16 poster', '9:16'), '');
  assert.equal(shapeClash('a jar of honey', '4:5'), '');
});
