import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  SECTIONS,
  SECTION_COMMANDS,
  SETTINGS_HOME,
  SETTINGS_ROOT,
  sectionOf,
  settingsTarget,
} from '../src/lib/settings-sections.ts';
import { rankCommands } from '../src/lib/palette.ts';

test('six sections, each its own URL under /studio/settings', () => {
  assert.deepEqual(
    SECTIONS.map((s) => s.id),
    ['account', 'plan', 'usage', 'workspace', 'connections', 'preferences'],
  );
  for (const s of SECTIONS) {
    assert.equal(s.href, `${SETTINGS_ROOT}/${s.id}`);
    assert.ok(s.label && s.description, s.id);
  }
  assert.equal(new Set(SECTIONS.map((s) => s.href)).size, SECTIONS.length);
});

test('the old one-page address opens the first section', () => {
  assert.equal(SETTINGS_HOME, '/studio/settings/account');
  assert.equal(settingsTarget(), '/studio/settings/account');
  assert.equal(settingsTarget(''), '/studio/settings/account');
  assert.equal(settingsTarget('Plan'), '/studio/settings/plan');
  assert.equal(settingsTarget('../x'), '/studio/settings/account');
});

test('a pathname names its section, whatever follows it', () => {
  assert.equal(sectionOf('/studio/settings/plan')?.id, 'plan');
  assert.equal(sectionOf('/studio/settings/usage/')?.id, 'usage');
  assert.equal(sectionOf('/studio/settings/account?x=1')?.id, 'account');
  assert.equal(sectionOf('/studio/settings'), null);
  assert.equal(sectionOf('/studio/settings/nope'), null);
  assert.equal(sectionOf('/studio/queue'), null);
  assert.equal(sectionOf(null), null);
});

test('the palette has one command per section, and "settings" lists them all', () => {
  assert.equal(SECTION_COMMANDS.length, SECTIONS.length);
  assert.deepEqual(
    rankCommands(SECTION_COMMANDS, 'settings', 6).map((c) => c.id),
    SECTIONS.map((s) => s.id),
  );
});

test('a section is found by what a person would type for it', () => {
  const first = (q) => rankCommands(SECTION_COMMANDS, q, 6)[0]?.id;
  assert.equal(first('plan'), 'plan');
  assert.equal(first('billing'), 'plan');
  assert.equal(first('credits'), 'plan');
  assert.equal(first('password'), 'account');
  assert.equal(first('history'), 'usage');
  assert.equal(first('members'), 'workspace');
  assert.equal(first('claude'), 'connections');
  assert.equal(first('notifications'), 'preferences');
  assert.equal(first('keyboard'), 'preferences');
});
