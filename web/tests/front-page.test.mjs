import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  FILTERS, TAG, countLabel, feedAction, feedNews, hasWork, isFinalCut, liveNews, mergeNews, peekItems, plays,
  readNews, readNewsItem, splitAccent, trayStages, wallTiles, whenLabel,
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
  assert.deepEqual(FILTERS.map((f) => f.id), ['all', 'model', 'effect', 'trending', 'update', 'soon', 'made']);
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
  for (const piece of ['FrontBackdrop', 'FrontPeek', 'FrontWall']) {
    assert.equal((code.match(new RegExp(`<${piece}\\b`, 'g')) ?? []).length, 1, `${piece} drawn once`);
  }
  // the tray under the box is gone (2026-10-23, Mike)
  assert.ok(!/<FrontTray\b|FrontTray/.test(code), 'no tray under the box');
  assert.ok(!/<CreateV2\b|create-v2\/create-v2/.test(code), 'the old sections are gone');
  // the peek tab replaces the plain Kling line on the front page only
  assert.match(code, /caps\.kling_4 === true && !frontOn/);
  const front = src('../src/components/studio/front/front.tsx');
  assert.doesNotMatch(front, /send\(|approve|runEffect|runImage|runScenes|runDirect|quote/i);
  // no "Use this" button on the tiles: the whole tile is the click
  assert.doesNotMatch(front, /Use this/);
});


/* The feed (2026-10-25, docs/tasks/task-whats-new.md step 3): live announcements join the wall. */
const feedItem = (over = {}) => ({
  id: 'model:grok1.5', source: 'model', tag: 'NEW MODEL', title: 'Grok Imagine is here', line: 'xAI video',
  accent: 'Grok Imagine', size: 'big', action: { fill: 'A shot on Grok: ', model: 'grok1.5' },
  media: { kind: 'video', url: 'https://media.example/g.mp4', poster: null }, eta: null, ends: null,
  new: true, unread: true, notify: null, you_asked: false, live_at: '2026-10-26T13:00:00+00:00', ...over,
});

test('a feed tile becomes a wall entry with its picture in the manifest', () => {
  const { news, media } = feedNews([feedItem()]);
  assert.equal(news.length, 1);
  const [n] = news;
  assert.equal(n.type, 'model');
  assert.equal(n.date, '2026-10-26');
  assert.equal(n.media, 'feed:model:grok1.5');
  assert.deepEqual(n.action, { fill: 'A shot on Grok: ', model: 'grok1.5' });
  assert.equal(n.unread, true);
  assert.equal(media['feed:model:grok1.5'].kind, 'clip');
  assert.equal(media['feed:model:grok1.5'].after, 'https://media.example/g.mp4');
});

test('a words-only tile has no picture and a look or a skill keeps its own tag', () => {
  const { news, media } = feedNews([
    feedItem({ id: 'skill:ad', source: 'skill', tag: 'NEW SKILL', size: 'small', media: { kind: 'none', url: null, poster: null },
               action: { skill: 'ad' } }),
  ]);
  assert.equal(news[0].textOnly, true);
  assert.equal(news[0].size, 'medium', 'words need room');
  assert.equal(feedNews([feedItem({ line: "xAI's video model" })]).news[0].line, "xAI's video model");
  assert.equal(feedNews([feedItem({ line: 'a short ad' })]).news[0].line, 'A short ad');
  assert.equal(news[0].type, 'update');
  assert.equal(news[0].tag, 'NEW SKILL');
  assert.deepEqual(news[0].action, { skill: 'ad' });
  assert.deepEqual(media, {});
});

test('a coming-soon tile never fills the box, and an outside address is never a door', () => {
  assert.deepEqual(feedAction({ id: 'soon:x', source: 'soon', action: { fill: 'go' } }), { notify: 'soon:x' });
  assert.deepEqual(feedAction({ id: 'soon:x', source: 'soon', action: { href: '/models/x' } }), { href: '/models/x' });
  assert.equal(feedAction({ id: 'f', source: 'feature', action: { href: 'https://evil.example' } }), null);
  assert.equal(feedAction({ id: 'f', source: 'feature', action: { href: '//evil.example' } }), null);
  const { news } = feedNews([feedItem({ id: 'f', source: 'feature', action: {} })]);
  assert.equal(news.length, 0, 'a tile with no door is left out');
});

test('the feed leads the wall and wins over the file entry it names', () => {
  const file = readNews(JSON.parse(readFileSync(new URL('../src/content/news.json', import.meta.url), 'utf8')));
  const { news } = feedNews([feedItem({ id: 'model:kling4', title: 'Kling 4.0 is here', accent: '4.0' })]);
  const merged = mergeNews(file, news);
  assert.equal(merged[0].id, 'model:kling4');
  assert.ok(!merged.some((n) => n.id === 'kling4'), 'the file copy is left out');
  assert.equal(merged.length, file.length);
});

test('a feed tile carries no price', () => {
  const { news } = feedNews([feedItem()]);
  assert.doesNotMatch(JSON.stringify(news), /credit|\$\s?\d/i);
});
