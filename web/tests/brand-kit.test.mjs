import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  emptySpec, withDefaults, normaliseHex, splitList, problems, roleColour, logoFor,
  fontFaces, fontStack, fontAlias, kitSummary, fileFor, isSvg,
} from '../src/lib/brand-kit.ts';

test('a hex is normalised or refused', () => {
  assert.equal(normaliseHex('f7931e'), '#F7931E');
  assert.equal(normaliseHex('#F93'), '#FF9933');
  assert.equal(normaliseHex(' #0a2540 '), '#0A2540');
  for (const bad of ['orange', '#12345', '#GGGGGG', '', null]) assert.equal(normaliseHex(bad), null, String(bad));
});

test('a list field splits on commas and lines, once each', () => {
  assert.deepEqual(splitList('neon, night clubs\nneon\n  '), ['neon', 'night clubs']);
  assert.deepEqual(splitList(''), []);
});

test('a partial stored spec fills every field', () => {
  const spec = withDefaults({ look: { style: 'warm' }, sound: { music: { bpm: 96 } } });
  assert.equal(spec.look.style, 'warm');
  assert.deepEqual(spec.look.banned, []);
  assert.equal(spec.sound.music.bpm, 96);
  assert.equal(spec.sound.music.genre, '');
  assert.equal(spec.end_card.on, true);
  assert.deepEqual(withDefaults(null), emptySpec());
});

test('the form names what the API would refuse', () => {
  const spec = emptySpec();
  spec.palette = [{ hex: '#000000', role: 'primary', name: '' }, { hex: 'nope', role: 'primary', name: '' }];
  const found = problems('', spec).map(([f]) => f);
  assert.deepEqual(found, ['name', 'palette', 'palette']);
  assert.deepEqual(problems('Kit', emptySpec()), []);
});

test('a role resolves to its colour and a logo is picked for the card it sits on', () => {
  const spec = emptySpec();
  spec.palette = [{ hex: '#FFF4E6', role: 'background', name: 'cream' }];
  assert.equal(roleColour(spec, 'background'), '#FFF4E6');
  assert.equal(roleColour(spec, 'primary', '#111111'), '#111111');
  assert.equal(logoFor('#FFF4E6'), 'logo_light');
  assert.equal(logoFor('#0A2540'), 'logo_dark');
});

test('a kit font loads under its own name, so two kits never collide', () => {
  const kit = { id: 7, files: [
    { id: 1, role: 'font_heading', mime: 'font/otf', filename: 'a.otf', url: '/api/brand-kits/7/assets/1/file' },
  ] };
  const css = fontFaces(kit, '');
  assert.match(css, /font-family:"phantra-kit-7-heading"/);
  assert.match(css, /format\("opentype"\)/);
  assert.equal(fontAlias(8, 'heading'), 'phantra-kit-8-heading');
  // no body font: the body falls back to the heading font, then the system
  assert.equal(fontStack(kit, 'body'), '"phantra-kit-7-heading", system-ui, sans-serif');
  assert.equal(fontFaces({ id: 1, files: [] }), '');
});

test('the card line counts what a kit holds', () => {
  const files = [{ role: 'reference' }, { role: 'reference' }, { role: 'font_heading' }];
  assert.equal(kitSummary({ files, projects: 1, spec: { palette: [{}, {}] } }),
    '2 colours · 1 font · 2 references · in 1 project');
  assert.equal(kitSummary({ files: [], projects: 0, spec: { palette: [] } }),
    '0 colours · 0 fonts · 0 references · not picked yet');
  assert.equal(fileFor({ files: [{ role: 'x', id: 1 }, { role: 'x', id: 2 }] }, 'x').id, 2);
  assert.ok(isSvg({ name: 'logo.SVG' }) && !isSvg({ name: 'logo.png', type: 'image/png' }));
});
