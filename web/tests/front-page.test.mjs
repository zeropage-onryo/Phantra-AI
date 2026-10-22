import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  FILTERS, TAG, countLabel, hasWork, isFinalCut, liveNews, peekItems, plays, readNews, readNewsItem,
  splitAccent, trayStages, wallTiles, whenLabel,
} from '../src/lib/front-page.ts';

/* The Create home as a front page (2026-10-22, docs/tasks/task-create-front-page.md). */

const file = JSON.parse(readFileSync(new URL('../src/content/news.json', import.meta.url), 'utf8'));
const manifest = JSON.parse(readFileSync(new URL('../public/showcase/manifest.json', import.meta.url), 'utf8'));
const src = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');

test('every entry in the news file is whole, real and carries no price', () => {
  const news = readNews(file);
  assert.equal(news.length, file.items.length, 'no entry was dropped as malformed');
  for (const n of news) {
    assert.ok(manifest.items[n.media], `${n.id}: ${n.media} is not in the showcase manifest`);
    assert.ok(n.accent === '' || n.title.includes(n.accent), n.id);
    assert.ok(Object.keys(TAG).includes(n.type), n.id);
    // no offers until one is live (Mike, 2026-10-22), and no price on a tile
    assert.doesNotMatch(`${n.title} ${n.line}`, /credit|\$\s?\d|% off|free credits/i, n.id);
  }
  assert.ok(!file.items.some((i) => i.type === 'offer'), 'no offer entries');
  // Kling 4.0 leads, behind its capability, and opens the peek tab
  assert.equal(news[0].id, 'kling4');
  assert.equal(news[0].requires, 'kling_4');
  assert.equal(news[0].size, 'big');
  assert.equal(peekItems(news)[0].id, 'kling4');
});

test('a half-written entry is left out, never drawn half-made', () => {
  const good = { id: 'a', type: 'model', title: 'A model', media: 'look.noir', action: { fill: 'x' } };
  assert.ok(readNewsItem(good));
  for (const bad of [
    { ...good, id: '' },
    { ...good, type: 'offer' },
    { ...good, media: '' },
    { ...good, action: {} },
    // a hand-edited file never links outside the studio
    { ...good, action: { href: 'https://example.com' } },
    null,
  ]) assert.equal(readNewsItem(bad), null, JSON.stringify(bad));
  assert.equal(readNewsItem({ ...good, size: 'huge' }).size, 'medium');
  assert.equal(readNewsItem({ ...good, accent: 'missing' }).accent, '');
  assert.equal(readNewsItem({ ...good, date: 'yesterday' }).date, null);
  assert.deepEqual(readNews({ items: [good, good] }).map((n) => n.id), ['a'], 'ids are unique');
  assert.deepEqual(readNews(null), []);
});

test('an entry behind a capability shows only while it is on', () => {
  const news = readNews(file);
  assert.ok(!liveNews(news, {}).some((n) => n.id === 'kling4'));
  assert.ok(!liveNews(news, { kling_4: 'yes' }).some((n) => n.id === 'kling4'));
  assert.ok(liveNews(news, { kling_4: true }).some((n) => n.id === 'kling4'));
  assert.equal(liveNews(news, null).length, news.filter((n) => !n.requires).length);
});

test('the accent and the date line', () => {
  assert.deepEqual(splitAccent('Kling 4.0 is here', '4.0'), ['Kling ', '4.0', ' is here']);
  assert.deepEqual(splitAccent('Noir', ''), ['Noir', '', '']);
  const now = new Date(2026, 9, 22, 16, 0);
  assert.equal(whenLabel('2026-10-22', now), 'Today');
  assert.equal(whenLabel('2026-10-21', now), 'Yesterday');
  assert.equal(whenLabel('2026-10-19', now), '3 days ago');
  assert.equal(whenLabel('2026-10-14', now), 'Oct 14');
  assert.equal(whenLabel(null, now), '');
});

test('the wall: news with renders between, one type alone, or the renders alone', () => {
  const news = readNews(file);
  const made = Array.from({ length: 40 }, (_, i) => ({ id: `m${i}`, title: `M${i}`, brief: 'a brief', media: 'create.usecase.gym' }));
  const all = wallTiles('all', news, made);
  assert.equal(all.length, news.length + made.length);
  assert.equal(all[0].kind, 'news');
  assert.equal(all.at(-1).kind, 'made', 'the renders run to the end');
  // spread evenly: never more than one entry's share of renders in a row
  const share = Math.ceil(made.length / news.length);
  let run = 0;
  for (const t of all) {
    run = t.kind === 'made' ? run + 1 : 0;
    assert.ok(run <= share, 'renders bunched together');
  }
  // the renders never take a headline size between the news
  assert.ok(all.filter((t) => t.kind === 'made').every((t) => t.size === 'small' || t.size === 'slim'));
  const effects = wallTiles('effect', news, made);
  assert.ok(effects.length && effects.every((t) => t.kind === 'news' && t.item.type === 'effect'));
  const renders = wallTiles('made', news, made);
  assert.ok(renders.every((t) => t.kind === 'made'));
  assert.equal(new Set(all.map((t) => t.key)).size, all.length, 'keys are unique');
  assert.deepEqual(FILTERS.map((f) => f.id), ['all', 'model', 'effect', 'trending', 'update', 'made']);
  // only the big tiles play on their own (Mike: "autoplay the big tiles muted")
  assert.deepEqual(['big', 'wide', 'tall', 'medium', 'small', 'slim'].filter(plays), ['big', 'wide']);
});

test('the tray counts the person\'s own work by stage', () => {
  const renders = [
    { kind: 'image', url: 'https://m/a.png', thumb: 'https://m/a-t.png' },
    { kind: 'image', url: 'https://m/b.png' },
    { kind: 'video', url: 'https://m/c.mp4', poster: 'https://m/c.jpg', model: 'kling-v3' },
    { kind: 'video', url: 'https://m/d.mp4', poster: 'https://m/d.jpg', model: 'final cut' },
  ];
  const stages = trayStages(['/photos/x.jpg'], renders, { image: 120, video: 9 });
  assert.deepEqual(stages.map((s) => [s.id, s.count, s.hot]), [
    ['scenes', 1, true], ['stills', 120, false], ['clips', 8, false], ['cuts', 1, false],
  ]);
  assert.deepEqual(stages[1].thumbs, ['https://m/a-t.png', 'https://m/b.png']);
  assert.deepEqual(stages[2].thumbs, ['https://m/c.jpg']);
  assert.ok(isFinalCut({ model: 'Final cut' }) && !isFinalCut({ model: null }));
  assert.equal(hasWork(trayStages([], [], null)), false, 'a first visit has no tray');
  assert.equal(countLabel(412), '99+');
});

test('the page draws the front on the home only, and nothing in it spends or sends', () => {
  const page = src('../src/app/studio/(create)/create-view.tsx');
  const code = page.replace(/\{\/\*[\s\S]*?\*\/\}/g, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  assert.match(code, /const frontOn = homePage && caps\.create_v2 === true;/);
  for (const piece of ['FrontBackdrop', 'FrontPeek', 'FrontTray', 'FrontWall']) {
    assert.equal((code.match(new RegExp(`<${piece}\\b`, 'g')) ?? []).length, 1, `${piece} drawn once`);
  }
  assert.ok(!/<CreateV2\b|create-v2\/create-v2/.test(code), 'the old sections are gone');
  // the peek tab replaces the plain Kling line on the front page only
  assert.match(code, /caps\.kling_4 === true && !frontOn/);
  const front = src('../src/components/studio/front/front.tsx');
  assert.doesNotMatch(front, /send\(|approve|runEffect|runImage|runScenes|runDirect|quote/i);
  // no "Use this" button on the tiles: the whole tile is the click
  assert.doesNotMatch(front, /Use this/);
});
