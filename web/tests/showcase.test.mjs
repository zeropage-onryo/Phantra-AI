import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { EMPTY, PLACEHOLDER, PLACEHOLDER_URL, isPlaceholder, readItem, parseManifest } from '../src/lib/showcase.ts';

/* a Create key straight off the manifest, the way create-v2.tsx reads it */
const showcaseItem = (manifest, key) => manifest?.items[key] ?? PLACEHOLDER;

const CREATE_KEYS = [
  'create.hero.split', 'create.hero.phone', 'create.hero.product_ad',
  'create.usecase.saas', 'create.usecase.ugc', 'create.usecase.ab_variants', 'create.usecase.music_video',
  'create.usecase.trailer', 'create.usecase.menu_promo', 'create.usecase.product_ad',
  'create.new.mcp_claude', 'create.new.brand_kit', 'create.new.discord',
  'look.film_grade', 'look.noir', 'look.flash_2000s', 'look.crash_zoom', 'look.vertical_ready', 'look.make_it_pro',
];

test('the placeholder manifest carries every key the Create page reads, version 1', () => {
  const raw = JSON.parse(readFileSync(new URL('../public/showcase/manifest.json', import.meta.url), 'utf8'));
  const manifest = parseManifest(raw);
  assert.equal(manifest.version, 1);
  for (const key of CREATE_KEYS) {
    const item = showcaseItem(manifest, key);
    assert.ok(isPlaceholder(item) || item.after.startsWith('https://'), key);
    assert.equal(typeof item.credits, 'number', key);
  }
});

test('a missing key, a broken item and a wrong version all draw the placeholder', () => {
  assert.deepEqual(showcaseItem(parseManifest({ version: 1, items: {} }), 'create.hero.split'), PLACEHOLDER);
  assert.deepEqual(showcaseItem(null, 'anything'), PLACEHOLDER);
  assert.deepEqual(parseManifest({ version: 2, items: { a: {} } }), EMPTY);
  assert.deepEqual(parseManifest('nope'), EMPTY);
  const item = readItem({ kind: 'clip', after: 'https://media.phantra.ai/site/x.mp4', poster: 'https://media.phantra.ai/site/x.jpg', aspect: '9:16', credits: 87, model: 'LTX 2.3', gen_id: 'gen:9' });
  assert.deepEqual(item, { kind: 'clip', before: null, after: 'https://media.phantra.ai/site/x.mp4', poster: 'https://media.phantra.ai/site/x.jpg', aspect: '9:16', credits: 87, model: 'LTX 2.3', gen_id: 'gen:9' });
  // a half-written entry is left out, so its key draws the placeholder
  assert.equal(showcaseItem(parseManifest({ version: 1, items: { k: { kind: 'clip', aspect: '3:2' } } }), 'k').after, PLACEHOLDER_URL);
  assert.equal(readItem({ kind: 'still', after: 'https://x/y.png', aspect: '3:2' }).aspect, '16:9');
});
