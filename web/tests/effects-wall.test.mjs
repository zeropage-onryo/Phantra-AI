import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PRESET_OPTION, TABS, featured, openOptions, readContent, slotLabel, tabsShown, tileShowcaseKey, tilesFrom, titleOf, waiting, wallFor,
} from '../src/lib/effects-wall.ts';

/* The table as GET /api/effects lists it, cut down: two templated rows, a
   camera row, a finishing tool, an image edit and two free looks. */
const opt = (values, over = {}) => ({ values, default: null, required: true, ...over });
const row = (id, over = {}) => ({
  id, label: id, category: 'finish', blurb: '', takes: 'video', output: 'video',
  sources: { min: 1, max: 1 }, prompt: 'none', options: {}, credits: 40, free: false, tags: [], ...over,
});
const TABLE = [
  row('kling-effect', { label: 'Kling effects', takes: 'image', category: 'video_effect', sources: { min: 1, max: 2 },
    options: { effect_scene: opt(['bullet_time_360', 'motorcycle_dance', 'santa_express', 'golden_wing']), duration: opt(['5', '10'], { default: '5', required: false }) } }),
  row('pixverse-effect', { label: 'PixVerse effects', takes: 'image', category: 'video_effect',
    options: { effect: opt(['Liquid Metal', 'Giant Product', 'Billboard AD']), resolution: opt(['360p', '720p'], { default: '720p', required: false }), duration: opt(['5'], { default: '5', required: false }) } }),
  row('camera-move', { takes: 'image', category: 'camera', prompt: 'required', options: { camera_movement: opt(['camera_rotation', 'zoom_in']) } }),
  row('add-sound', { prompt: 'required' }),
  row('nano-banana-edit', { takes: 'image', output: 'image', category: 'image_edit', prompt: 'required' }),
  row('noir', { credits: 0, free: true, category: 'look' }),
  row('make_it_pro', { credits: 0, free: true, category: 'look' }),
];
const clip = (after) => ({ kind: 'clip', before: null, after, poster: null, aspect: '9:16', credits: 0, model: 'm', gen_id: null });
const MANIFEST = { version: 1, items: {
  'effect.bullet_time': clip('https://m/bt.mp4'),
  'effect.product_orbit': clip('https://m/orbit.mp4'),
  'look.noir': clip('https://m/noir.mp4'),
  'look.make_it_pro': clip('https://m/pro.mp4'),
  'effect.sound_pass': clip('https://m/sound.mp4'),
  'template.pixverse-effect.Liquid Metal': clip('https://m/lm.mp4'),
} };
const CONTENT = { featured: ['kling-effect:bullet_time_360', 'pixverse-effect:Giant Product', 'make_it_pro', 'noir', 'camera-move:camera_rotation'], new: ['kling-effect:bullet_time_360'] };
const keys = (xs) => xs.map((t) => t.key);

test('every template is its own tile, read off the row, and a plain row is one tile', () => {
  const tiles = tilesFrom(TABLE, MANIFEST, CONTENT);
  assert.deepEqual(keys(tiles), [
    'kling-effect:bullet_time_360', 'kling-effect:motorcycle_dance', 'kling-effect:santa_express', 'kling-effect:golden_wing',
    'pixverse-effect:Liquid Metal', 'pixverse-effect:Giant Product', 'pixverse-effect:Billboard AD',
    'camera-move:camera_rotation', 'camera-move:zoom_in',
    'add-sound', 'nano-banana-edit', 'noir', 'make_it_pro',
  ]);
  const bt = tiles[0];
  assert.deepEqual(bt.preset, { name: 'effect_scene', value: 'bullet_time_360' });
  assert.equal(bt.name, 'Bullet Time 360');
  assert.equal(bt.effect.id, 'kling-effect');      // running it sends the row and the option, nothing new
  assert.equal(tiles.find((t) => t.key === 'add-sound').preset, null);
  // a plain row says what it does; the model's name stays the table's label
  assert.equal(tiles.find((t) => t.key === 'add-sound').name, 'Add Sound');
  assert.equal(tiles.find((t) => t.key === 'camera-move:camera_rotation').name, 'Product Orbit');
  assert.equal(tiles.find((t) => t.key === 'camera-move:zoom_in').name, 'Zoom In');
  assert.deepEqual(Object.keys(PRESET_OPTION).sort(), ['camera-move', 'costume-preview', 'kling-effect', 'pixverse-effect']);
});

test('a template name is written for a person; one already written is left alone', () => {
  assert.equal(titleOf('bullet_time_360'), 'Bullet Time 360');
  assert.equal(titleOf('3d_cartoon_2'), '3d Cartoon 2');
  assert.equal(titleOf('Liquid Metal'), 'Liquid Metal');
  assert.equal(titleOf("Who's Arrested?"), "Who's Arrested?");
});

test('the examples the slate made before templates had tiles are still found', () => {
  assert.equal(tileShowcaseKey('kling-effect:bullet_time_360'), 'effect.bullet_time');
  assert.equal(tileShowcaseKey('camera-move:camera_rotation'), 'effect.product_orbit');
  assert.equal(tileShowcaseKey('pixverse-effect:Liquid Metal'), 'template.pixverse-effect.Liquid Metal');
  assert.equal(tileShowcaseKey('noir'), 'look.noir');
  assert.equal(tileShowcaseKey('add-sound'), 'effect.sound_pass');
  assert.equal(tileShowcaseKey('nano-banana-edit'), 'effect.nano-banana-edit');
});

test('tabs come off the name and the row; anything unmatched is a Transform', () => {
  const tiles = tilesFrom(TABLE, MANIFEST, CONTENT);
  const tab = (k) => tiles.find((t) => t.key === k).tabs;
  assert.deepEqual(tab('kling-effect:bullet_time_360'), ['transform', 'new']);
  assert.deepEqual(tab('kling-effect:motorcycle_dance'), ['dance']);
  assert.deepEqual(tab('kling-effect:santa_express'), ['holiday']);
  assert.deepEqual(tab('pixverse-effect:Giant Product'), ['product']);
  assert.deepEqual(tab('pixverse-effect:Billboard AD'), ['product']);
  assert.deepEqual(tab('camera-move:zoom_in'), ['camera']);
  assert.deepEqual(tab('add-sound'), ['tools']);
  assert.deepEqual(tab('nano-banana-edit'), ['tools']);
  assert.deepEqual(tab('noir'), ['free']);
  assert.ok(TABS.every((t) => typeof t.label === 'string'));
});

test('browsing shows only tiles with an example; a search finds every tile, examples first', () => {
  const tiles = tilesFrom(TABLE, MANIFEST, CONTENT);
  assert.deepEqual(keys(wallFor(tiles, 'all', '')), [
    'kling-effect:bullet_time_360', 'pixverse-effect:Liquid Metal', 'camera-move:camera_rotation', 'add-sound', 'noir', 'make_it_pro',
  ]);
  assert.deepEqual(keys(wallFor(tiles, 'free', '')), ['noir', 'make_it_pro']);
  assert.deepEqual(keys(wallFor(tiles, 'dance', '')), []);
  // the dance template has no example, so a search is the way to it
  assert.deepEqual(keys(wallFor(tiles, 'all', 'motorcycle')), ['kling-effect:motorcycle_dance']);
  assert.deepEqual(keys(wallFor(tiles, 'all', 'kling')).slice(0, 1), ['kling-effect:bullet_time_360']);
  assert.equal(waiting(tiles), 7);
  // empty tabs are not drawn while browsing
  assert.deepEqual(tabsShown(tiles).map((t) => t.id), ['all', 'new', 'free', 'transform', 'camera', 'tools']);
});

test('the featured strip is the content file in order, skipping picks with no example, at most three', () => {
  const tiles = tilesFrom(TABLE, MANIFEST, CONTENT);
  assert.deepEqual(keys(featured(tiles, CONTENT)), ['kling-effect:bullet_time_360', 'make_it_pro', 'noir']);
  assert.deepEqual(keys(featured(tiles, { featured: [], new: [] })), []);
  assert.equal(tiles[0].isNew, true);
  assert.equal(tiles.find((t) => t.key === 'noir').isNew, false);
});

test('the panel never offers the option a tile fixes, nor one with a single legal value', () => {
  const tiles = tilesFrom(TABLE, MANIFEST, CONTENT);
  assert.deepEqual(openOptions(tiles[0]).map(([n]) => n), ['duration']);
  assert.deepEqual(openOptions(tiles.find((t) => t.key === 'pixverse-effect:Liquid Metal')).map(([n]) => n), ['resolution']);
  assert.equal(slotLabel({ takes: 'image', category: 'video_effect' }), 'Photo');
  assert.equal(slotLabel({ takes: 'video', category: 'finish' }), 'Clip');
  assert.equal(slotLabel({ takes: 'image', category: 'camera' }, 'camera_movement'), 'Image');
});

test('the content file is read defensively', () => {
  assert.deepEqual(readContent(null), { featured: [], new: [] });
  assert.deepEqual(readContent({ featured: ['a', 3], new: 'x' }), { featured: ['a'], new: [] });
});

test('a recipe is one tile, a product recipe sits under Product, and its showcase key is its id', () => {
  const recipe = (id, tags) => ({ id, label: id, category: 'video_effect', blurb: '', takes: 'image', output: 'video',
    sources: { min: 1, max: 1 }, prompt: 'optional', options: { duration: { values: ['5', '10'], default: '5', required: false } },
    credits: 168, free: false, tags, recipe: true, hint: 'The product (optional)' });
  const tiles = tilesFrom([recipe('float_drop', ['product']), recipe('meltdown', ['transform'])], { version: 1, items: {
    'effect.float_drop': { kind: 'clip', before: null, after: 'https://m/f.mp4', poster: null, aspect: '9:16', credits: 0, model: 'm', gen_id: null },
  } });
  assert.deepEqual(tiles.map((t) => [t.key, t.tabs]), [['float_drop', ['product']], ['meltdown', ['transform']]]);
  assert.equal(tileShowcaseKey('float_drop'), 'effect.float_drop');
  assert.deepEqual(wallFor(tiles, 'all', '').map((t) => t.key), ['float_drop']);
  assert.deepEqual(openOptions(tiles[0]).map(([n]) => n), ['duration']);
});

test('the Halloween costumes are one tile each, under Holiday', () => {
  const costume = {
    id: 'costume-preview', label: 'Halloween Costume', category: 'image_edit', blurb: '', takes: 'image', output: 'image',
    sources: { min: 1, max: 1 }, prompt: 'none', credits: 10, free: false, tags: ['social'],
    options: { costume: { values: ['vampire', 'zombie_bride'], default: null, required: true },
      aspect_ratio: { values: ['auto', '1:1'], default: 'auto', required: false } },
  };
  assert.equal(PRESET_OPTION['costume-preview'], 'costume');
  const tiles = tilesFrom([costume], null);
  assert.deepEqual(tiles.map((t) => [t.key, t.name, t.tabs]), [
    ['costume-preview:vampire', 'Vampire', ['holiday']],
    ['costume-preview:zombie_bride', 'Zombie Bride', ['holiday']],
  ]);
  // the tile fixes the costume; the panel offers what is left
  assert.deepEqual(openOptions(tiles[0]).map(([n]) => n), ['aspect_ratio']);
});
