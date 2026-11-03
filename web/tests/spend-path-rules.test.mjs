// Mike's rules on the path to a spend (QA 2026-11-02 T1, T3, T5):
// black text on a yellow fill, red only for errors, and the price on the
// one button that spends -- never in a model picker.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { approveText } from '../src/lib/step-model.ts';

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '');
const rules = (css) => [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  .map((m) => ({ selector: m[1].trim(), body: m[2] }));
const colorOf = (body) => (body.match(/(?:^|[;\s])color:\s*([^;]+)/) || [])[1]?.trim();

test('the still card: black on yellow, and waiting is not red', () => {
  const css = rules(read('components/studio/still-step.css'));
  const go = css.find((r) => r.selector === '.ss-go button');
  assert.match(go.body, /background:\s*var\(--signal/);
  assert.match(colorOf(go.body), /var\(--on-signal/);
  for (const r of css.filter((r) => r.selector.includes('data-state="waiting"'))) {
    assert.doesNotMatch(r.body, /228 0 43|#e4002b|#ff4d6a|--danger/i, r.selector);
  }
  const off = css.find((r) => r.selector === '.ss-go button:disabled');
  assert.doesNotMatch(off.body, /#6e1a1f|--danger/i);
});

test('the still card puts the price on Approve', () => {
  assert.equal(approveText('waiting', 'Nano Banana · 10 credits'), 'Approve · Nano Banana · 10 credits');
  assert.equal(approveText('failed', 'FLUX.2 Pro · 10 credits'), 'Approve again · FLUX.2 Pro · 10 credits');
  assert.equal(approveText('waiting', ''), 'Approve');
});

test('"New element" beats the studio button reset', () => {
  // `.zps button { color: inherit }` is (0,1,1); a bare `.elnew` loses to it
  const css = rules(read('app/studio/studio.css'));
  const scoped = css.find((r) => r.selector === '.zps .elnew');
  assert.ok(scoped, 'a .zps .elnew rule');
  assert.match(colorOf(scoped.body), /var\(--on-signal/);
});

test('the composer has no clip-model menu to print a price in (Vesper chooses, 2026-11-02)', () => {
  const view = read('app/studio/(create)/create-view.tsx');
  assert.equal(view.indexOf('heading="Which model renders"'), -1);
  assert.equal(view.indexOf('heading="Which model draws"'), -1);
});
