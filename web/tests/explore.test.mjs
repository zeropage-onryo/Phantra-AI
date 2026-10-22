import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  SWITCH_TOOL, isSwitchTool, exploring, SWITCH_SIDES, projectLine, EXPLORE_CAPTION, EXPLORE_SEND_LINE,
  explorePlaceholder, exploreCommands, SWITCH_LABEL, switchTitle, switchNote, switchState, askBefore,
} from '../src/lib/explore.ts';

test('a project explores only when its switch says so and there is a brain to talk to', () => {
  assert.equal(exploring({ explore: true }, true), true);
  assert.equal(exploring({ explore: true }, false), false);  // no brain: a send makes directly
  assert.equal(exploring({ explore: false }, true), false);
  assert.equal(exploring({}, true), false);                  // an older row: Make
  assert.equal(exploring({ explore: null }, true), false);
  assert.equal(exploring(null, true), false);                // outside any project
  assert.equal(exploring(undefined, true), false);
});

test('the switch has two halves, Explore then Make', () => {
  assert.deepEqual(SWITCH_SIDES.map((s) => s.id), ['explore', 'make']);
  assert.deepEqual(SWITCH_SIDES.map((s) => s.label), ['Explore', 'Make']);
  for (const s of SWITCH_SIDES) assert.ok(s.title.length > 10);
});

test('the tool name is the server\'s', () => {
  const server = readFileSync(new URL('../../src/guide_tools.py', import.meta.url), 'utf8');
  assert.match(server, new RegExp(`SWITCH_TOOL = "${SWITCH_TOOL}"`));
  assert.equal(isSwitchTool(SWITCH_TOOL), true);
  for (const other of ['make_image', 'set_project_look', '', null, undefined, 7]) {
    assert.equal(isSwitchTool(other), false);
  }
});

test('the card has a title for every kind the server can send', () => {
  const server = readFileSync(new URL('../../src/guide_tools.py', import.meta.url), 'utf8');
  const kinds = /SWITCH_KINDS = \(([^)]*)\)/.exec(server)[1].match(/"(\w+)"/g).map((k) => k.slice(1, -1));
  assert.deepEqual(kinds, ['still', 'scene', 'sheet', 'effect', 'plan']);
  const titles = kinds.map((k) => switchTitle(k));
  assert.equal(new Set(titles).size, kinds.length);
  for (const k of kinds) {
    assert.match(switchTitle(k), /^Switch to Make to /);
    assert.match(switchNote(k), /^Switching costs nothing\. /);
  }
  assert.equal(switchTitle('still'), 'Switch to Make to draw this still');
  // a kind the page does not know still gets a card that says what the click does
  for (const odd of ['clip', '', null, undefined, 3, {}]) {
    assert.equal(switchTitle(odd), 'Switch to Make to make this');
    assert.match(switchNote(odd), /^Switching costs nothing\. .*Approve/);
  }
});

test('nothing the card says promises a spend, and what costs credits waits', () => {
  for (const k of ['still', 'sheet', 'effect']) assert.match(switchNote(k), /waits for your Approve beside its price/);
  assert.match(switchNote('scene'), /only rendered from the scene's own priced button/);
  assert.match(switchNote('plan'), /waits for you to start it/);
  assert.equal(SWITCH_LABEL, 'Explore is on for this project');
});

test('an answered card says which way it went', () => {
  assert.equal(switchState('done'), 'Switched to Make');
  assert.equal(switchState('skipped'), 'Still exploring');
  assert.equal(switchState(undefined), '');
});

test('the project row says what a send does', () => {
  assert.equal(projectLine(true, 3), 'a send makes nothing until you switch');
  assert.equal(projectLine(false, 3), 'written against its brief and 3 learned');
});

test('what the box says while exploring is about a send, and names no price', () => {
  for (const line of [EXPLORE_CAPTION, EXPLORE_SEND_LINE, explorePlaceholder(true), explorePlaceholder(false)]) {
    assert.ok(line.length > 10);
    assert.doesNotMatch(line, /\d/);
  }
  assert.match(EXPLORE_CAPTION, /^Exploring\./);
  assert.match(EXPLORE_SEND_LINE, /^Free to send\./);
  assert.notEqual(explorePlaceholder(true), explorePlaceholder(false));
});

test('exploring, the slash menu keeps only what attaches something', () => {
  const all = [
    { id: 'image', group: 'make' }, { id: 'video', group: 'make' }, { id: 'animate', group: 'use' },
    { id: 'effects', group: 'use' }, { id: 'ref', group: 'use' }, { id: 'element', group: 'use' },
    { id: 'skill:mood-board', group: 'skill' }, { id: 'preset:dolly-in', group: 'camera' },
  ];
  assert.deepEqual(exploreCommands(all).map((c) => c.id), ['ref', 'element']);
  assert.deepEqual(exploreCommands([]), []);
});

test('the ask sent again is the newest thing the person said before the card', () => {
  const turns = [
    { role: 'user', content: 'what should the ad be?' },
    { role: 'assistant', content: 'Three ways in.' },
    { role: 'user', content: 'ok, draw the hero still' },
    { role: 'assistant', content: 'This project is exploring, so nothing has been made.' },
    { role: 'user', content: 'a later message' },
  ];
  assert.equal(askBefore(turns, 3), turns[2]);
  assert.equal(askBefore(turns, 1), turns[0]);
  assert.equal(askBefore(turns, 0), null);
  assert.equal(askBefore(turns, 99), turns[4]);
  // an empty bubble (a send that made directly) is not an ask
  assert.equal(askBefore([{ role: 'user', content: '  ' }, { role: 'assistant', content: 'x' }], 1), null);
  assert.equal(askBefore([], 0), null);
});
