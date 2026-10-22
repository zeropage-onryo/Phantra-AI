import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  AUTONOMY_MODES, PRICE_CHECKPOINT, generateModeFor, stopsAt, startsPlans, isAutonomy, autonomyLine,
} from '../src/lib/autonomy.ts';
import { planOf, needsApproval, alwaysAsks, approveAll } from '../src/lib/make-plan.ts';
import { ASK_TOOL, isAskTool, questionOf, answerText, chipAspect } from '../src/lib/tappable.ts';
import { boardsOf, reorder, ordered, withText, redoTarget, shotLabel } from '../src/lib/storyboard.ts';
import { nextStepsFor, variantsPlan, rendered } from '../src/lib/next-steps.ts';

const PLAN = planOf({
  summary: 'an ad',
  steps: [
    { n: 1, do: 'image', args: { prompt: 'the can' }, why: '', uses: [] },
    { n: 2, do: 'scene', args: { prompt: 'she lifts the can', seconds: 10 }, why: '', uses: [1] },
    { n: 3, do: 'keep', args: { candidate_ids: ['c1'] }, why: '', uses: [] },
    { n: 4, do: 'keyframes', args: {}, why: '', uses: [], scene: 2 },
    { n: 5, do: 'render', args: {}, why: '', uses: [], scene: 2 },
  ],
}, 'p1');

test('the dial has three settings and every one keeps the price checkpoint', () => {
  assert.deepEqual(AUTONOMY_MODES.map((m) => m.id), ['ask', 'checkpoints', 'autopilot']);
  assert.match(PRICE_CHECKPOINT, /Nothing is charged without your click/);
  for (const mode of AUTONOMY_MODES.map((m) => m.id)) {
    // never the composer's "auto": that draws a still on the send
    assert.equal(generateModeFor(mode), 'ask', mode);
    // a paid step stops in every setting: the still, the sheet, the keyframes, the clip
    for (const s of PLAN.steps.filter((x) => ['image', 'keyframes', 'render'].includes(x.do))) {
      assert.equal(stopsAt(mode, s), true, `${mode} ${s.do}`);
      assert.equal(needsApproval(PLAN, s, generateModeFor(mode)), true, `${mode} ${s.do} runner`);
    }
    assert.match(autonomyLine(mode), /price|waits for you/);
  }
  assert.equal(isAutonomy('autopilot'), true);
  assert.equal(isAutonomy('auto'), false);
});

test('Autopilot runs only the free steps on its own; Ask me everything stops at every step', () => {
  const scene = PLAN.steps[1];
  const keep = PLAN.steps[2];
  assert.equal(stopsAt('autopilot', scene), false);
  assert.equal(stopsAt('autopilot', keep), false);
  assert.equal(stopsAt('checkpoints', scene), false);
  assert.equal(stopsAt('ask', scene), true);
  assert.equal(stopsAt('ask', keep), true);
  assert.equal(startsPlans('autopilot'), true);
  assert.equal(startsPlans('checkpoints'), true);
  assert.equal(startsPlans('ask'), false);
  // and even "Approve all" on an Autopilot plan leaves the clip waiting
  const approved = approveAll(PLAN, { image: 10, sheet: 30 });
  const render = approved.steps[4];
  assert.equal(alwaysAsks(render), true);
  assert.equal(needsApproval(approved, render, generateModeFor('autopilot')), true);
});

test('a tappable question is the ask_choice tool, cleaned like the server cleans it', () => {
  const server = readFileSync(new URL('../../src/guide_tools.py', import.meta.url), 'utf8');
  assert.match(server, new RegExp(`ASK_TOOL = "${ASK_TOOL}"`));
  assert.equal(isAskTool(ASK_TOOL), true);
  assert.equal(isAskTool('make_image'), false);
  const q = questionOf({ ask: 'Which palette?', kind: 'swatches', options: [
    { label: 'Warm', swatch: '#D97A2B' }, { label: 'Cold', swatch: '#2b6fd9' }, { label: 'Mono', swatch: 'nope' },
  ] });
  // one option without a colour: the question is still asked, as chips
  assert.equal(q.kind, 'chips');
  assert.equal(q.options.length, 3);
  assert.equal(q.options[0].swatch, '#d97a2b');
  const sw = questionOf({ ask: 'Which palette?', kind: 'swatches', options: [
    { label: 'Warm', swatch: '#D97A2B' }, { label: 'Cold', swatch: '#2b6fd9' },
  ] });
  assert.equal(sw.kind, 'swatches');
  assert.equal(answerText(sw, sw.options[0]), 'Warm (#d97a2b)');
  const ar = questionOf({ ask: 'Which shape?', kind: 'aspect', options: ['4:5', '9:16', '16:9'] });
  assert.equal(ar.kind, 'aspect');
  assert.equal(answerText(ar, ar.options[1]), '9:16');
  assert.equal(chipAspect(ar.options[1]), '9 / 16');
  const ab = questionOf({ ask: 'Which one?', kind: 'ab', options: [{ label: 'the wide one', on: 1 }, { label: 'the close one', on: 2 }] });
  assert.equal(answerText(ab, ab.options[1]), '#2 — the close one');
  // not a question a card can draw
  assert.equal(questionOf({ ask: 'x', options: ['only one'] }), null);
  assert.equal(questionOf({ options: ['a', 'b'] }), null);
  assert.equal(questionOf(null), null);
  assert.equal(questionOf({ ask: 'k?', kind: 'nope', options: ['a', 'b'] }).kind, 'chips');
});

const made = (over = {}) => ({
  id: 'm1', output: 'video', status: 'done', refs: [], detail: '', conceptId: 42, title: 'The can', prompt: 'she lifts the can',
  seconds: 10, renderModel: 'kling3-turbo-pro',
  parts: [
    { n: 1, start: 0, end: 4, seconds: 4, text: 'wide on the counter', reference_image: '/renders/s1.png', media_url: '/renders/c1.mp4' },
    { n: 2, start: 4, end: 10, seconds: 6, prompt: 'close on the tab', reference_image: null, media_url: null },
  ],
  ...over,
});

test('the storyboard is read off the thread, newest scene first, one card per shot', () => {
  const turns = [
    { role: 'user', content: 'x', made: { id: 'i1', output: 'image', status: 'done', refs: [], detail: '', image: '/r.png' } },
    { role: 'user', content: 'y', made: made({ id: 'old', title: 'Older' }) },
    { role: 'assistant', content: 'z' },
    { role: 'user', content: 'w', made: made() },
  ];
  const boards = boardsOf(turns, (id) => (id === 'kling3-turbo-pro' ? 'Kling 3 Turbo Pro' : undefined));
  assert.deepEqual(boards.map((b) => b.madeId), ['m1', 'old']);
  const b = boards[0];
  assert.equal(b.title, 'The can');
  assert.equal(b.rendered, false);
  assert.equal(b.shots.length, 2);
  assert.deepEqual(b.shots.map((s) => s.key), ['m1:1', 'm1:2']);
  assert.equal(b.shots[0].clip, '/renders/c1.mp4');
  assert.equal(b.shots[1].still, null);
  assert.equal(b.shots[1].text, 'close on the tab');
  assert.equal(b.shots[0].modelLabel, 'Kling 3 Turbo Pro');
  assert.equal(shotLabel(b.shots[1]), 'Shot 02 · 4–10s');
  // a scene with no model proposed opens on the default
  assert.equal(boardsOf([{ role: 'user', content: '', made: made({ renderModel: undefined }) }])[0].shots[0].modelLabel, 'Default model');
  // a running or imageless turn is no board
  assert.equal(boardsOf([{ role: 'user', content: '', made: made({ status: 'running' }) }]).length, 0);
});

test('reorder, a kept order, an edit and a redo target never touch the server', () => {
  assert.deepEqual(reorder([1, 2, 3], 0, 2), [2, 3, 1]);
  assert.deepEqual(reorder([1, 2, 3], 2, 0), [3, 1, 2]);
  const same = [1, 2, 3];
  assert.equal(reorder(same, 1, 1), same);
  assert.equal(reorder(same, 5, 0), same);
  const b = boardsOf([{ role: 'user', content: '', made: made() }])[0];
  assert.deepEqual(ordered(b, [2, 1]).map((s) => s.n), [2, 1]);
  assert.deepEqual(ordered(b, [2, 9]).map((s) => s.n), [2, 1]);   // unknown dropped, forgotten last
  assert.deepEqual(ordered(b, undefined).map((s) => s.n), [1, 2]);
  const edited = withText(b, 2, '  closer on the tab  ');
  assert.equal(edited.shots[1].text, 'closer on the tab');
  assert.equal(b.shots[1].text, 'close on the tab');              // the original stands
  assert.deepEqual(redoTarget(b.shots[1]), { conceptId: 42, part: 2 });
  assert.equal(redoTarget({ conceptId: null, n: 1 }), null);
});

test('next steps appear only under a rendered scene and each opens a card', () => {
  const half = made();
  assert.equal(rendered(half), false);
  assert.deepEqual(nextStepsFor(half, { effects: ['add-sound', 'reframe'] }), []);
  const done = made({ parts: half.parts.map((p) => ({ ...p, media_url: '/c.mp4' })) });
  const steps = nextStepsFor(done, { effects: ['add-sound', 'reframe', 'upscale'] });
  assert.deepEqual(steps.map((s) => s.id), ['sound', 'vertical', 'variants']);
  assert.deepEqual(steps.map((s) => s.label), ['Add Sound Pass', 'Cut a vertical version', 'Make 3 ad variants']);
  assert.equal(steps[1].effect, 'reframe');
  for (const s of steps) assert.match(s.title, /Nothing runs until you approve/);
  // the free look wins the vertical cut once the table has it
  assert.equal(nextStepsFor(done, { effects: ['vertical_ready', 'reframe'] })[0].effect, 'vertical_ready');
  // a still is never offered these
  assert.deepEqual(nextStepsFor({ ...done, output: 'image' }, { effects: ['add-sound'] }), []);
  // no table yet: only the variants
  assert.deepEqual(nextStepsFor(done, { effects: [] }).map((s) => s.id), ['variants']);
});

test('the variants plan is three scenes whose clips each wait at their price', () => {
  const plan = variantsPlan(made(), 'v1');
  assert.equal(plan.steps.length, 6);
  assert.deepEqual(plan.steps.map((s) => s.do), ['scene', 'scene', 'scene', 'render', 'render', 'render']);
  assert.deepEqual(plan.steps.slice(3).map((s) => s.scene), [1, 2, 3]);
  assert.match(plan.steps[0].args.prompt, /she lifts the can[\s\S]*Variant 1 of 3/);
  assert.equal(plan.steps[0].args.seconds, 10);
  assert.equal(plan.started, undefined);                           // drawn, not started
  for (const r of plan.steps.slice(3)) {
    assert.equal(alwaysAsks(r), true);
    assert.equal(needsApproval(plan, r, 'ask'), true);
  }
  assert.equal(variantsPlan({ prompt: '' }, 'v2'), null);
});
