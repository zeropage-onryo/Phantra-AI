import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lookLines, safeHref, shownSources, researchLine, saveNote, isLookTool } from '../src/lib/look-research.ts';

test('a stored look splits into its labelled lines', () => {
  const look = 'PALETTE: teal shadows, sodium orange\n\nLENS AND FRAMING: wide, low horizon: figures small\nKeep it quiet.\nShe said: wait';
  assert.deepEqual(lookLines(look), [
    { label: 'PALETTE', text: 'teal shadows, sodium orange' },
    { label: 'LENS AND FRAMING', text: 'wide, low horizon: figures small' },
    { label: '', text: 'Keep it quiet.' },
    // a sentence with a colon in it is not a label
    { label: '', text: 'She said: wait' },
  ]);
  assert.deepEqual(lookLines(''), []);
  assert.deepEqual(lookLines(null), []);
  // a label with nothing after it draws nothing
  assert.deepEqual(lookLines('LIGHT:   \nAVOID: neon'), [{ label: 'AVOID', text: 'neon' }]);
});

test('only an http or https address is ever linked', () => {
  assert.equal(safeHref('https://mag.example/a?b=1'), 'https://mag.example/a?b=1');
  assert.equal(safeHref(' http://mag.example '), 'http://mag.example');
  for (const bad of ['javascript:alert(1)', 'data:text/html,x', '/local/path', 'mag.example', 'https://a.example/"><script>', '', null, undefined]) {
    assert.equal(safeHref(bad), null, String(bad));
  }
});

const research = {
  subject: 'Blade Runner 2049', kind: 'title', ok: true, checked: true,
  lines: [{ label: 'PALETTE', text: 'teal and orange' }],
  sources: [
    { title: 'On colour', host: 'mag.example', url: 'https://mag.example/a' },
    { title: 'Again', host: 'mag.example', url: 'https://mag.example/a' },
    { title: 'A script', host: 'bad.example', url: 'javascript:alert(1)' },
    { title: '', host: '', url: 'https://nameless.example/' },
  ],
};

test('sources are shown once each, by site, and an unsafe one is named but not linked', () => {
  assert.deepEqual(shownSources(research), [
    { name: 'mag.example', href: 'https://mag.example/a' },
    { name: 'bad.example', href: null },
  ]);
  assert.deepEqual(shownSources(null), []);
});

test('a research record says where the look stands', () => {
  assert.equal(researchLine(research), 'The look of “Blade Runner 2049”, read from 2 pages');
  assert.equal(researchLine({ ...research, sources: [research.sources[0]] }), 'The look of “Blade Runner 2049”, read from 1 page');
  assert.match(researchLine({ ...research, checked: false, sources: [] }), /general knowledge.*unchecked/);
  assert.equal(researchLine({ ...research, ok: false, note: 'could not tell what that is' }),
    'Could not research “Blade Runner 2049”: could not tell what that is');
  assert.equal(researchLine({ ...research, ok: false, subject: '', note: '' }), 'Could not research “that”');
});

test('the card says when saving replaces a look the project already has', () => {
  assert.match(saveNote('PALETTE: grey'), /^Replaces the look this project has now/);
  assert.doesNotMatch(saveNote('   '), /Replaces/);
  assert.doesNotMatch(saveNote(undefined), /Replaces/);
  assert.equal(isLookTool('set_project_look'), true);
  assert.equal(isLookTool('create_project'), false);
});
