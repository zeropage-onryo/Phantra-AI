import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  HISTORY_FILTERS,
  barPath,
  countText,
  dayLabel,
  foldTotals,
  kindNote,
  kindWord,
  layoutBars,
  matches,
  niceMax,
  peakDay,
  signed,
  tickDays,
} from '../src/lib/credit-history.ts';

test('the chips: renders take clips and effects, stills take stills, grants take credit', () => {
  assert.deepEqual(HISTORY_FILTERS.map((f) => f.id), ['all', 'render', 'still', 'grant']);
  const groups = ['render', 'effect', 'still', 'grant'];
  const pass = (filter) => groups.filter((group) => matches({ group }, filter));
  assert.deepEqual(pass('all'), groups);
  assert.deepEqual(pass('render'), ['render', 'effect']);
  assert.deepEqual(pass('still'), ['still']);
  assert.deepEqual(pass('grant'), ['grant']);
});

test('a row says what it did, and a settle says why it may read as nothing', () => {
  assert.equal(kindWord('grant'), 'Added');
  assert.equal(kindWord('hold'), 'Held');
  assert.equal(kindWord('settle'), 'Settled');
  assert.equal(kindWord('release'), 'Returned');
  assert.equal(kindWord('expire'), 'Expired');
  assert.equal(kindNote({ kind: 'settle', credits: 0 }), 'finished at the held price');
  assert.match(kindNote({ kind: 'settle', credits: 12 }), /difference returned/);
  assert.match(kindNote({ kind: 'settle', credits: -5 }), /over the held price/);
  assert.match(kindNote({ kind: 'release', credits: 87 }), /did not finish/);
  assert.equal(kindNote({ kind: 'grant', credits: 100 }), '');
});

test('credits are signed with a real minus, and counted in their own word', () => {
  assert.equal(signed(1500), '+1,500');
  assert.equal(signed(-87), '−87');
  assert.equal(signed(0), '0');
  assert.equal(countText(2, 'render'), '2 clips');
  assert.equal(countText(1, 'still'), '1 still');
  assert.equal(countText(3, 'effect'), '3 effects');
});

test('the y axis tops out at a round number whose half is round too', () => {
  assert.equal(niceMax(0), 10);
  assert.equal(niceMax(7), 10);
  assert.equal(niceMax(87), 100);
  assert.equal(niceMax(147), 200);
  assert.equal(niceMax(233), 400);
  assert.equal(niceMax(420), 500);
  assert.equal(niceMax(980), 1000);
  assert.equal(niceMax(1000), 1000);
  assert.equal(niceMax(1001), 2000);
  for (const v of [3, 87, 147, 233, 420, 980, 1001, 7300]) {
    assert.ok(niceMax(v) >= v, String(v));
    assert.equal((niceMax(v) / 2) % 1, 0, String(v));
  }
});

test('days are labelled first, last, and weekly between without crowding the end', () => {
  assert.deepEqual(tickDays(30), [0, 7, 14, 21, 29]);
  assert.deepEqual(tickDays(8), [0, 7]);
  assert.deepEqual(tickDays(1), [0]);
  assert.deepEqual(tickDays(0), []);
  assert.equal(dayLabel('2026-10-08'), 'Oct 8');
  assert.equal(dayLabel('nope'), 'nope');
});

test('bars are thin, gapped, and grow from one baseline', () => {
  const bars = layoutBars([0, 50, 100, 1], 400, 100, 100);
  assert.equal(bars.length, 4);
  // 100px slots: capped at 24px, centred, so the rest of the slot is air
  assert.deepEqual(bars.map((b) => b.width), [24, 24, 24, 24]);
  assert.equal(bars[1].x, 100 + (100 - 24) / 2);
  // every bar ends on the baseline
  for (const b of bars) assert.equal(b.y + b.height, 100);
  assert.deepEqual(bars.map((b) => b.height), [0, 50, 100, 2]);
  // 30 days in a narrow plot: 2px of surface between neighbours
  const narrow = layoutBars(new Array(30).fill(10), 300, 100, 100);
  assert.equal(narrow[0].width, 8);
  assert.equal(Math.round((narrow[1].x - (narrow[0].x + narrow[0].width)) * 100) / 100, 2);
  // a value over the axis is drawn at the top, never above it
  assert.equal(layoutBars([500], 100, 100, 100)[0].y, 0);
});

test('a bar is square at the baseline and rounded at its data end', () => {
  assert.equal(barPath({ x: 0, y: 0, width: 24, height: 0 }), '');
  const path = barPath({ x: 10, y: 20, width: 24, height: 80 });
  assert.ok(path.startsWith('M10,100V24Q10,20 14,20H30Q34,20 34,24V100Z'), path);
  // too short to carry 4px: the radius shrinks to the bar
  assert.ok(barPath({ x: 0, y: 98, width: 24, height: 2 }).includes('Q0,98 2,98'));
});

test('the busiest day, or none', () => {
  assert.deepEqual(peakDay([{ day: 'a', credits: 3 }, { day: 'b', credits: 9 }, { day: 'c', credits: 9 }]), { day: 'b', credits: 9 });
  assert.equal(peakDay([{ day: 'a', credits: 0 }]), null);
  assert.equal(peakDay([]), null);
});

test('a long list of models keeps its largest and folds the rest into one row', () => {
  const totals = [9, 8, 7, 6, 5, 4, 3].map((credits, i) => ({ label: `m${i}`, group: 'render', credits, count: 1 }));
  assert.equal(foldTotals(totals.slice(0, 6)).length, 6);
  const folded = foldTotals(totals);
  assert.deepEqual(folded.map((t) => t.label), ['m0', 'm1', 'm2', 'm3', 'm4', 'Everything else']);
  assert.deepEqual(folded[5], { label: 'Everything else', group: 'render', credits: 7, count: 2 });
  // nothing is lost
  assert.equal(folded.reduce((s, t) => s + t.credits, 0), totals.reduce((s, t) => s + t.credits, 0));
});
