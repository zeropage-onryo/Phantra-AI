import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  AUDIENCES, TIERS, MAKE_IT_PRO, acceptsFile, badgeOf, filterEffects, fits, makeItPro, sourceLine, tierCounts, tierOf, vesperHref,
} from '../src/lib/effects-tab.ts';
import {
  EMPTY, PLACEHOLDER, PLACEHOLDER_URL, SHOWCASE_URL, cssAspect, isPlaceholder, itemFor, loadShowcase, parseManifest, readItem,
  resetShowcase, restingFrame, showcaseKey,
} from '../src/lib/showcase.ts';

/* The table as GET /api/effects lists it today (every row priced), plus the
   free looks the looks stream is adding (ids and the bundle agreed in
   docs/tasks/task-overnight-2026-10-22.md group 2), marked free with their
   own tags -- so the Free filter is exercised before that branch merges. */
const row = (id, over = {}) => ({
  id, label: id, category: 'finish', blurb: '', takes: 'video', output: 'video',
  sources: { min: 1, max: 1 }, prompt: 'none', options: {}, credits: 40, free: false, tags: ['cinematic'], ...over,
});
const TABLE = [
  row('kling-effect', { takes: 'image', category: 'video_effect', tags: ['social'] }),
  row('camera-move', { takes: 'image', category: 'camera', tags: ['cinematic', 'product'] }),
  row('upscale', { credits: null, tags: ['cinematic'] }),
  row('add-sound', { credits: null, prompt: 'required', tags: ['cinematic'] }),
  row('reframe', { credits: null, tags: ['social'] }),
  row('remove-background', { takes: 'image', output: 'image', category: 'image_edit', credits: 10, tags: ['product'] }),
  // the free looks: 0 credits, free, tagged by the looks stream
  row('film_grade', { credits: 0, free: true, tags: ['cinematic'] }),
  row('noir', { credits: 0, free: true, tags: ['cinematic'] }),
  row('flash_2000s', { credits: 0, free: true, tags: ['social'] }),
  row('crash_zoom', { credits: 0, free: true, tags: ['social'] }),
  row('vertical_ready', { credits: 0, free: true, tags: ['social'] }),
  row('make_it_pro', { credits: 0, free: true, tags: ['social', 'cinematic'] }),
  // a row with no tags at all: never hidden by an audience filter
  row('untagged-thing', { tags: [] }),
];
const ids = (xs) => xs.map((e) => e.id);

test('Free is what the table says, everything priced is Pro, and nothing on the badge is a number', () => {
  assert.equal(tierOf(TABLE[0]), 'pro');
  assert.equal(badgeOf(TABLE[0]), 'Pro');
  assert.equal(badgeOf(TABLE.find((e) => e.id === 'noir')), 'Free');
  // a 0-credit row that is not marked free is still Pro: the badge reads
  // the table's word, never the price
  assert.equal(badgeOf(row('x', { credits: 0 })), 'Pro');
  assert.equal(badgeOf(row('y', { free: undefined })), 'Pro');
  assert.deepEqual(tierCounts(TABLE), { free: 6, pro: 7 });
  for (const e of TABLE) assert.doesNotMatch(badgeOf(e), /\d/);
  assert.deepEqual(TIERS.map((t) => t.id), ['all', 'free', 'pro']);
  assert.deepEqual(AUDIENCES.map((a) => a.id), ['all', 'cinematic', 'social', 'product']);
});

test('the Free / Pro filter and the audience filter compose, and an untagged row is never hidden', () => {
  assert.deepEqual(ids(filterEffects(TABLE, 'all', 'all')), ids(TABLE));
  assert.deepEqual(ids(filterEffects(TABLE, 'free', 'all')),
    ['film_grade', 'noir', 'flash_2000s', 'crash_zoom', 'vertical_ready', 'make_it_pro']);
  assert.deepEqual(ids(filterEffects(TABLE, 'pro', 'product')), ['camera-move', 'remove-background', 'untagged-thing']);
  assert.deepEqual(ids(filterEffects(TABLE, 'free', 'cinematic')), ['film_grade', 'noir', 'make_it_pro']);
  assert.deepEqual(ids(filterEffects(TABLE, 'all', 'social')),
    ['kling-effect', 'reframe', 'flash_2000s', 'crash_zoom', 'vertical_ready', 'make_it_pro', 'untagged-thing']);
  // the order is the table's: a filter never re-sorts
  assert.deepEqual(ids(filterEffects(TABLE, 'pro', 'cinematic')), ['camera-move', 'upscale', 'add-sound', 'untagged-thing']);
});

test('Make It Pro is offered only when the table has the bundle', () => {
  assert.equal(makeItPro(TABLE)?.id, MAKE_IT_PRO);
  assert.equal(makeItPro(TABLE.filter((e) => e.id !== 'make_it_pro')), null);
  assert.equal(makeItPro([]), null);
});

test('a dropped file is a clip or a still by its type, and a source fits an effect by what it takes', () => {
  assert.equal(acceptsFile({ type: 'video/mp4', name: 'a.mp4' }), 'clip');
  assert.equal(acceptsFile({ type: '', name: 'take.MOV' }), 'clip');
  assert.equal(acceptsFile({ type: 'image/jpeg', name: 'x.jpg' }), 'image');
  assert.equal(acceptsFile({ type: 'application/pdf', name: 'x.pdf' }), null);
  assert.equal(acceptsFile({}), null);
  const clip = { ref: 'gen:7', kind: 'clip', from: 'dropped' };
  const still = { ref: '/refs/a.jpg', kind: 'image', from: 'dropped' };
  assert.equal(fits(TABLE[0], still), true);     // kling takes an image
  assert.equal(fits(TABLE[0], clip), false);
  assert.equal(fits(TABLE[2], clip), true);      // upscale takes a clip
  assert.equal(fits(TABLE[2], null), false);
  assert.match(sourceLine(null), /Drop a clip or a still/);
  assert.match(sourceLine(clip), /A clip is loaded \(dropped\)/);
  assert.match(sourceLine(still), /A still is loaded/);
});

test('"Turn this into a full piece with Vesper" is Create with the render attached and named', () => {
  const href = vesperHref('gen:42', 'Noir');
  assert.ok(href.startsWith('/studio?attach=generated-42&spark='));
  assert.equal(new URLSearchParams(href.split('?')[1]).get('spark'), 'Turn this Noir result (gen:42) into a full piece');
  assert.equal(vesperHref(null, 'Noir'), null);        // a result with no render id has no door
  assert.equal(vesperHref('asset:3', 'Noir'), null);
  assert.equal(vesperHref('https://evil/x', 'Noir'), null);
});

test('every card has a fixed manifest key: look.<id> for a free look, the slate\'s name for an effect it renders', () => {
  assert.equal(showcaseKey('film_grade'), 'look.film_grade');
  assert.equal(showcaseKey('noir'), 'look.noir');
  assert.equal(showcaseKey('flash_2000s'), 'look.flash_2000s');
  assert.equal(showcaseKey('crash_zoom'), 'look.crash_zoom');
  assert.equal(showcaseKey('vertical_ready'), 'look.vertical_ready');
  assert.equal(showcaseKey('make_it_pro'), 'look.make_it_pro');
  assert.equal(showcaseKey('kling-effect'), 'effect.bullet_time');
  assert.equal(showcaseKey('camera-move'), 'effect.product_orbit');
  assert.equal(showcaseKey('upscale'), 'effect.4k_smooth');
  assert.equal(showcaseKey('add-sound'), 'effect.sound_pass');
  assert.equal(showcaseKey('reframe'), 'effect.reframe');
  assert.equal(showcaseKey('remove-background'), 'effect.remove-background');   // anything else: effect.<id>
  assert.equal(showcaseKey(' pixverse-effect '), 'effect.pixverse-effect');
});

test('a missing key, a malformed entry or an unreadable file falls back to the placeholder', () => {
  const good = { kind: 'clip', before: 'https://m/before.mp4', after: 'https://m/after.mp4', poster: 'https://m/p.jpg', aspect: '9:16', credits: 87, model: 'LTX 2.3', gen_id: 'gen:9' };
  const manifest = parseManifest({ version: 1, items: {
    'look.noir': good,
    'look.film_grade': { kind: 'clip', before: null },                 // no after: not an entry
    'effect.reframe': { kind: 'gif', after: 'https://m/x.gif' },       // an unknown kind: not an entry
    'effect.4k_smooth': { kind: 'still', after: 'https://m/s.png', aspect: '3:2', credits: 'ten' },
  } });
  assert.deepEqual(Object.keys(manifest.items), ['look.noir', 'effect.4k_smooth']);
  assert.deepEqual(itemFor(manifest, 'noir'), good);
  assert.equal(isPlaceholder(itemFor(manifest, 'noir')), false);
  assert.equal(restingFrame(itemFor(manifest, 'noir')), 'https://m/before.mp4');
  // tolerated fields: an odd aspect reads 16:9, a wordy credits reads 0
  assert.equal(itemFor(manifest, 'upscale').aspect, '16:9');
  assert.equal(itemFor(manifest, 'upscale').credits, 0);
  assert.equal(restingFrame(itemFor(manifest, 'upscale')), 'https://m/s.png');  // no before, no poster: the after
  // the fallbacks
  assert.deepEqual(itemFor(manifest, 'film_grade'), PLACEHOLDER);
  assert.deepEqual(itemFor(manifest, 'camera-move'), PLACEHOLDER);
  assert.deepEqual(itemFor(null, 'noir'), PLACEHOLDER);
  assert.equal(isPlaceholder(PLACEHOLDER), true);
  assert.equal(PLACEHOLDER.after, PLACEHOLDER_URL);
  assert.deepEqual(parseManifest({ version: 2, items: { 'look.noir': good } }), EMPTY);
  assert.deepEqual(parseManifest('nope'), EMPTY);
  assert.deepEqual(parseManifest(null), EMPTY);
  assert.equal(readItem(good).before, 'https://m/before.mp4');
  assert.equal(readItem({ ...good, before: '  ' }).before, null);
  assert.equal(cssAspect('9:16'), '9 / 16');
});

test('the manifest is fetched once, and a failed or missing fetch is the empty manifest', async () => {
  resetShowcase();
  let calls = 0;
  const fetcher = async (url) => {
    calls++;
    assert.equal(url, SHOWCASE_URL);
    return { ok: true, json: async () => ({ version: 1, items: { 'look.noir': { kind: 'still', after: 'https://m/a.png' } } }) };
  };
  const a = await loadShowcase(fetcher);
  const b = await loadShowcase(fetcher);
  assert.equal(calls, 1);
  assert.equal(a, b);
  assert.equal(itemFor(a, 'noir').after, 'https://m/a.png');
  resetShowcase();
  assert.deepEqual(await loadShowcase(async () => ({ ok: false, json: async () => ({}) })), EMPTY);
  resetShowcase();
  assert.deepEqual(await loadShowcase(async () => { throw new Error('offline'); }), EMPTY);
  resetShowcase();
});

test('the manifest on disk names every agreed key: real media, or pending with a reason', async () => {
  // Group 12 filled the manifest with the showcase renders (2026-10-22); a key with
  // no media yet is listed under `pending` with why, and the page draws the
  // placeholder for it. Either way every Effects card has somewhere to look.
  const fs = await import('node:fs');
  const raw = JSON.parse(fs.readFileSync(new URL('../public/showcase/manifest.json', import.meta.url), 'utf8'));
  const manifest = parseManifest(raw);
  const keys = ['look.film_grade', 'look.noir', 'look.flash_2000s', 'look.crash_zoom', 'look.vertical_ready', 'look.make_it_pro',
    'effect.bullet_time', 'effect.product_orbit', 'effect.4k_smooth', 'effect.sound_pass', 'effect.reframe'];
  const pending = raw.pending && typeof raw.pending === 'object' ? raw.pending : {};
  for (const k of keys) {
    const item = manifest.items[k];
    if (item) {
      assert.match(item.after, /^https:\/\//, k);
      assert.ok(['clip', 'still'].includes(item.kind), k);
    } else {
      assert.equal(typeof pending[k], 'string', `${k} is neither rendered nor explained`);
    }
  }
  assert.ok(fs.existsSync(new URL('../public/showcase/placeholder/still.svg', import.meta.url)));
});
