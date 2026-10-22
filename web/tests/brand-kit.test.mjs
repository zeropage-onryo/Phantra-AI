import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  emptySpec, withDefaults, normaliseHex, splitList, problems, roleColour, logoFor,
  fontFaces, fontStack, fontAlias, kitSummary, fileFor, isSvg, captionSample, CAPTION_SAMPLE,
  contrastRatio, contrastChecks, primaryChoices, evidenceFor, parseAesthetics, formatAesthetics, splitLines,
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

const GYGLER = () => {
  const spec = emptySpec();
  spec.palette = [
    { hex: '#FF880B', role: 'primary', name: 'Gygler orange' },
    { hex: '#FAF0E4', role: 'background', name: 'Cream' },
    { hex: '#151515', role: 'text', name: 'Near-black' },
    { hex: '#FFFFFF', role: 'extra', name: 'White' },
  ];
  return spec;
};

test('the WCAG ratio is the published one', () => {
  assert.equal(contrastRatio('#FFFFFF', '#000000'), 21);
  assert.equal(contrastRatio('#FFFFFF', '#FF880B'), 2.39);
  assert.equal(contrastRatio('#000000', '#FF880B'), 8.78);
  assert.equal(contrastRatio('#FF880B', '#FFFFFF'), 2.39);
});

test('white on the Gygler orange is flagged and black is offered', () => {
  const checks = contrastChecks(GYGLER());
  const white = checks.find((c) => c.fg === '#FFFFFF' && c.bg === '#FF880B');
  assert.ok(white);
  assert.equal(white.ok, false);
  assert.equal(white.ratio, 2.39);
  assert.deepEqual(white.alternative, { hex: '#000000', ratio: 8.78 });
  assert.equal(white.fgIndex, 3);
  const body = checks.find((c) => c.fg === '#151515' && c.bg === '#FAF0E4');
  assert.equal(body.ok, true);
  assert.deepEqual(contrastChecks(emptySpec()), []);
});

test('confidence and the brand-colour pick appear only on an imported kit', () => {
  const made = GYGLER();
  assert.equal(evidenceFor(made, 'primary'), null);
  assert.deepEqual(primaryChoices(made), []);
  const imported = { ...GYGLER(), import: {
    source: 'https://gygler.com', at: '2026-10-21',
    roles: { primary: { why: 'buttons', confidence: 'medium' } },
    candidates: [{ hex: '#ff880b', why: 'dup' }, { hex: '#371901', why: 'headings' }, { hex: '#00AAFF', why: 'links' }, { hex: '#123456', why: 'x' }],
  } };
  assert.equal(evidenceFor(imported, 'primary').confidence, 'medium');
  assert.deepEqual(primaryChoices(imported).map((c) => c.hex), ['#FF880B', '#371901', '#00AAFF']);
  imported.import.roles.primary.confidence = 'high';
  assert.deepEqual(primaryChoices(imported), []);
});

test('selling points are one per line and aesthetics are tag: reason', () => {
  assert.deepEqual(splitLines('Vetted staff, in 24 hours\n\nOne rate\nOne rate'), ['Vetted staff, in 24 hours', 'One rate']);
  const list = parseAesthetics('warm minimal: cream and one orange\nfriendly\nFriendly: again');
  assert.deepEqual(list, [{ tag: 'warm minimal', because: 'cream and one orange' }, { tag: 'friendly', because: '' }]);
  assert.equal(formatAesthetics(list), 'warm minimal: cream and one orange\nfriendly');
  const spec = emptySpec();
  spec.identity.selling_points = Array.from({ length: 9 }, (_, i) => `p${i}`);
  spec.look.aesthetics = [{ tag: 'x'.repeat(41), because: '' }];
  assert.deepEqual(problems('Kit', spec).map(([f]) => f), ['selling points', 'aesthetics']);
});

test("the caption preview reads the kit's own tagline, never another client's", () => {
  const spec = withDefaults({ identity: { tagline: "Built to last the season." } });
  assert.equal(captionSample(spec), "Built to last the season.");
  assert.equal(captionSample(withDefaults({ identity: { tagline: "   " } })), CAPTION_SAMPLE);
  assert.equal(captionSample(emptySpec()), CAPTION_SAMPLE);
  assert.equal(captionSample(null), CAPTION_SAMPLE);
  assert.ok(!CAPTION_SAMPLE.includes("Gyg"), "the sample names no client");
});
