import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LOOKS, USE_CASE_TABS, createV2On, effectsDoor } from '../src/lib/create-v2.ts';

/* What is left of the v2 sections since the front page (2026-10-22,
   docs/tasks/task-create-front-page.md): the flag, the use cases (the
   renders between the news) and the free looks. tests/front-page.test.mjs
   holds the page itself. */

test('the flag is a strict true', () => {
  assert.equal(createV2On({ create_v2: true }), true);
  for (const caps of [{}, { create_v2: false }, { create_v2: 'yes' }, null, undefined]) assert.equal(createV2On(caps), false);
});

test('every use case fills the box with a real brief and has a picture', () => {
  assert.deepEqual(USE_CASE_TABS.map((t) => t.label), ['Marketing', 'Social', 'Film', 'Business']);
  const ids = new Set();
  for (const t of USE_CASE_TABS) {
    for (const c of t.cards) {
      assert.ok(c.brief.length > 20 && c.showcase && c.title, c.id);
      assert.ok(!ids.has(c.id), `${c.id} twice`);
      ids.add(c.id);
      // a card's words carry no price (Mike's call, 2026-10-22)
      assert.doesNotMatch(`${c.title} ${c.line} ${c.brief}`, /credit|\$\s?\d/i, c.id);
    }
  }
});

test('the looks are the six free ones, and the effects door follows its flag', () => {
  assert.deepEqual(LOOKS.map((l) => l.id), ['film_grade', 'noir', 'flash_2000s', 'crash_zoom', 'vertical_ready', 'make_it_pro']);
  for (const l of LOOKS) assert.equal(l.showcase, `look.${l.id}`);
  assert.equal(effectsDoor({ effects_tab: true }), 'tab');
  assert.equal(effectsDoor({}), 'gallery');
});
