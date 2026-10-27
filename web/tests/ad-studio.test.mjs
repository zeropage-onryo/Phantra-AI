import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  MAKE_NOW, article, answer, asPick, briefText, handoffHref, missing, pickLabel, pickOf, startBrief,
  switchFormat, unlockState,
} from '../src/lib/ad-studio.ts';

const PAGE = {
  id: 'ads', title: 'Ad Studio', tagline: '', entitled: true, gated: true,
  intake: [
    { id: 'platform', label: 'Where will it run?', kind: 'choice', options: [
      { id: 'tiktok', label: 'TikTok', aspect: '9:16' }, { id: 'feed', label: 'Feed post', aspect: '1:1' },
      { id: 'youtube', label: 'YouTube / TV', aspect: '16:9' }] },
    { id: 'audience', label: 'Who is it for?', kind: 'text' },
    { id: 'offer', label: 'What should they do?', kind: 'text' },
    { id: 'tone', label: 'Tone', kind: 'choice', options: [{ id: 'bold', label: 'Bold' }] },
  ],
  formats: [
    { id: 'product_showcase', title: 'Product showcase', blurb: '', skill: 'ad', skill_title: 'Ad', output: 'video',
      aspects: ['9:16', '1:1', '16:9'], seconds: [6, 15], default_seconds: 10, needs: ['product'] },
    { id: 'ugc', title: 'UGC review', blurb: '', skill: 'ugc', skill_title: 'UGC-style clip', output: 'video',
      aspects: ['9:16'], seconds: [8, 20], default_seconds: 15, needs: ['product'], cast: true },
    { id: 'motion_ad', title: 'Motion ad', blurb: '', skill: 'motion-ad', skill_title: 'Motion ad', output: 'video',
      aspects: ['16:9', '9:16', '1:1'], seconds: [10, 60], default_seconds: 15, needs: ['kit'] },
    { id: 'product_still', title: 'Product still', blurb: '', skill: 'product-still', skill_title: 'Product still',
      output: 'image', aspects: ['4:5', '1:1'], seconds: null, default_seconds: null, needs: ['product'] },
  ],
  addon: { key: 'studios', name: 'Studios', blurb: '', monthly_usd: null, on_sale: true, has_plan: true },
};
const fmt = (id) => PAGE.formats.find((f) => f.id === id);

test('a brief starts on the format\'s first shape and default length', () => {
  const b = startBrief(fmt('ugc'));
  assert.deepEqual([b.format, b.aspect, b.seconds], ['ugc', '9:16', 15]);
});

test('a platform answer moves the shape only to one the format makes', () => {
  let b = startBrief(fmt('product_showcase'));
  b = answer(PAGE, b, 'platform', 'feed');
  assert.equal(b.aspect, '1:1');
  b = answer(PAGE, b, 'platform', 'youtube');
  assert.equal(b.aspect, '16:9');
  let u = startBrief(fmt('ugc'));
  u = answer(PAGE, u, 'platform', 'youtube');        // UGC is vertical only
  assert.equal(u.aspect, '9:16');
  assert.equal(answer(PAGE, u, 'audience', '   ').intake.audience, undefined);
});

test('switching format keeps the answers and what still fits', () => {
  let b = answer(PAGE, startBrief(fmt('product_showcase')), 'platform', 'feed');
  b = { ...b, seconds: 12, product: { id: 'prop-shoe', name: 'Halo runner' } };
  const m = switchFormat(PAGE, b, fmt('motion_ad'));
  assert.deepEqual([m.aspect, m.seconds, m.product?.id, m.intake.platform], ['1:1', 12, 'prop-shoe', 'feed']);
  const u = switchFormat(PAGE, b, fmt('ugc'));
  assert.deepEqual([u.aspect, u.seconds], ['9:16', 12]);
  const s = switchFormat(PAGE, b, fmt('product_still'));
  assert.deepEqual([s.aspect, s.seconds], ['1:1', null]);
  // a length nobody chose follows the format: 10s showcase -> 15s UGC
  const fresh = switchFormat(PAGE, startBrief(fmt('product_showcase')), fmt('ugc'));
  assert.equal(fresh.seconds, 15);
  // and back from a still to a clip lands on the clip's default
  assert.equal(switchFormat(PAGE, s, fmt('ugc')).seconds, 15);
});

test('the first message reads as a sentence', () => {
  let b = startBrief(fmt('ugc'), { product: { id: 'p', name: '  Halo   runner ' } });
  b = answer(PAGE, b, 'platform', 'tiktok');
  b = answer(PAGE, b, 'audience', 'new runners');
  b = answer(PAGE, b, 'offer', 'Shop the drop!');
  b = answer(PAGE, b, 'tone', 'bold');
  assert.equal(briefText(PAGE, b),
    'A 15-second 9:16 UGC review ad for Halo runner. It runs on TikTok, for new runners. They should: Shop the drop. Tone: bold.');
  assert.equal(briefText(PAGE, { ...startBrief(fmt('motion_ad')), seconds: 18 }), 'An 18-second 16:9 motion ad.');
  assert.equal(briefText(PAGE, startBrief(fmt('product_still'))), 'A 4:5 product still.');
  assert.equal(briefText(PAGE, { ...startBrief(fmt('ugc')), format: 'nope' }), '');
});

test('a/an follows how the number is said', () => {
  assert.deepEqual(['8-second', '11-second', '18-second', '80-second', '15-second', '9:16', 'ad', 'motion'].map(article),
    ['an', 'an', 'an', 'an', 'a', 'a', 'an', 'a']);
});

test('the hand-off carries everything the composer reads', () => {
  const b = { ...answer(PAGE, startBrief(fmt('ugc')), 'platform', 'tiktok'),
    product: { id: 'prop-shoe', name: 'Halo' }, kit: { id: 7, name: 'Halo' } };
  const href = handoffHref(PAGE, b);
  assert.ok(href.startsWith('/studio?'));
  const q = new URLSearchParams(href.split('?')[1]);
  assert.equal(q.get('kind'), 'video');
  assert.equal(q.get('frame'), '9:16');
  assert.equal(q.get('skill'), 'ugc');
  assert.equal(q.get('seconds'), '15');
  assert.equal(q.get('kit'), '7');
  assert.equal(q.get('attach'), 'prop-shoe');
  assert.match(q.get('spark'), /^A 15-second 9:16 UGC review ad for Halo\./);
  assert.deepEqual(asPick(q.get('studio')), { id: 'ads', format: 'ugc', aspect: '9:16', seconds: 15, intake: { platform: 'tiktok' } });
  // a still carries no length
  const s = new URLSearchParams(handoffHref(PAGE, startBrief(fmt('product_still'))).split('?')[1]);
  assert.equal(s.get('kind'), 'image');
  assert.equal(s.get('seconds'), null);
  assert.equal(s.get('kit'), null);
});

test('a pick off a link is read defensively', () => {
  assert.equal(asPick('{'), null);
  assert.equal(asPick(''), null);
  assert.equal(asPick({ id: 'ads' }), null);
  assert.deepEqual(asPick({ id: 'ads', format: 'ugc', seconds: 'x', intake: { a: 1, b: 'y' } }),
    { id: 'ads', format: 'ugc', aspect: null, seconds: null, intake: { b: 'y' } });
  assert.equal(pickOf(PAGE, answer(PAGE, startBrief(fmt('ugc')), 'audience', '  a  b ')).intake.audience, 'a b');
});

test('the chip names the format', () => {
  assert.equal(pickLabel({ id: 'ads', format: 'ugc', aspect: null, seconds: null, intake: {} }, PAGE.formats), 'Ad Studio · UGC review');
  assert.equal(pickLabel({ id: 'ads', format: 'tv_spot', aspect: null, seconds: null, intake: {} }), 'Ad Studio · tv spot');
});

test('missing things are advice, by what the format needs', () => {
  // UGC casts someone: no product and no person are two lines of advice
  assert.equal(missing(fmt('ugc'), startBrief(fmt('ugc'))).length, 2);
  assert.equal(missing(fmt('ugc'), { ...startBrief(fmt('ugc')), product: { id: 'p', name: 'P' } }).length, 1);
  assert.equal(missing(fmt('product_showcase'), { ...startBrief(fmt('product_showcase')), product: { id: 'p', name: 'P' } }).length, 0);
  assert.match(missing(fmt('motion_ad'), startBrief(fmt('motion_ad')))[0], /brand kit/);
});

test('the unlock says what the person can do', () => {
  assert.deepEqual(unlockState(PAGE), { kind: 'open' });
  const locked = { ...PAGE, entitled: false };
  assert.deepEqual(unlockState(locked), { kind: 'buy', label: 'Add Ad Studio' });
  assert.deepEqual(unlockState({ ...locked, addon: { ...locked.addon, monthly_usd: 19 } }), { kind: 'buy', label: 'Add Ad Studio · $19/mo' });
  assert.deepEqual(unlockState({ ...locked, addon: { ...locked.addon, has_plan: false } }), { kind: 'plan-first' });
  assert.deepEqual(unlockState({ ...locked, addon: { ...locked.addon, on_sale: false } }), { kind: 'not-on-sale' });
  assert.deepEqual(unlockState({ ...locked, addon: null }), { kind: 'not-on-sale' });
});

test('a cast format names the person and attaches them before the product', () => {
  const b = { ...answer(PAGE, startBrief(fmt('ugc')), 'platform', 'tiktok'),
    product: { id: 'prop-shoe', name: 'Halo' }, actor: { id: 'character-maya', name: 'Maya' } };
  assert.match(briefText(PAGE, b), /^A 15-second 9:16 UGC review ad for Halo, with Maya on camera\./);
  const q = new URLSearchParams(handoffHref(PAGE, b).split('?')[1]);
  assert.equal(q.get('attach'), 'character-maya,prop-shoe');
  // a format that casts nobody ignores the person, but keeps them for later
  const s = switchFormat(PAGE, b, fmt('product_showcase'));
  assert.equal(s.actor?.id, 'character-maya');
  assert.doesNotMatch(briefText(PAGE, s), /on camera/);
  assert.equal(new URLSearchParams(handoffHref(PAGE, s).split('?')[1]).get('attach'), 'prop-shoe');
  assert.match(missing(fmt('ugc'), { ...b, actor: null }).join(' '), /stand-in/);
});

test('make it now asks for the make and sends once', () => {
  const b = startBrief(fmt('ugc'));
  const q = new URLSearchParams(handoffHref(PAGE, b, { now: true }).split('?')[1]);
  assert.equal(q.get('send'), '1');
  assert.ok(q.get('spark').endsWith(` ${MAKE_NOW}`));
  assert.equal(new URLSearchParams(handoffHref(PAGE, b).split('?')[1]).get('send'), null);
});
