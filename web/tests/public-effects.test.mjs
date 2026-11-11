import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { readContent, tilesFrom } from '../src/lib/effects-wall.ts';
import { parseManifest } from '../src/lib/showcase.ts';
import {
  costLine, grouped, jsonLdFor, publicEffects, related, slugOf, studioPath, titleFor,
} from '../src/lib/public-effects.ts';

/* The public /effects pages (2026-11-05, docs/tasks/task-public-effects-pages.md)
   are built from the committed catalogue, manifest and picks, so these run on
   the REAL files: a kept showcase render that would break a page fails here. */
const read = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'));
const catalog = read('../src/content/effects-catalog.json');
const manifest = parseManifest(read('../public/showcase/manifest.json'));
const content = readContent(read('../src/content/effects-page.json'));
const tiles = tilesFrom(catalog.items, manifest, content);
const all = publicEffects(tiles);

test('a page exists exactly for each tile with a kept example', () => {
  assert.equal(all.length, tiles.filter((t) => t.media).length);
  assert.ok(all.length > 0);
  for (const e of all) assert.ok(e.media && e.media.after);
});

test('slugs are unique and URL-safe', () => {
  const slugs = all.map((e) => e.slug);
  assert.equal(new Set(slugs).size, slugs.length);
  for (const s of slugs) assert.match(s, /^[a-z0-9]+(-[a-z0-9]+)*$/);
  assert.equal(slugOf('Bullet Time 360'), 'bullet-time-360');
  assert.equal(slugOf('Crash-Zoom Hook'), 'crash-zoom-hook');
  assert.equal(slugOf("Who's Arrested?"), 'whos-arrested');
});

test('every page has a title, a description that ends a sentence, and a price line', () => {
  for (const e of all) {
    assert.match(titleFor(e), /— AI (Photo|Video) Effect$/);
    assert.ok(e.description.length >= 20, e.slug);
    assert.match(e.description, /[.!?]$/, e.slug);
    assert.ok(costLine(e));
  }
});

test('a template page is described as itself, not as the whole template row', () => {
  for (const e of all.filter((x) => x.key.includes(':'))) {
    assert.ok(e.description.toLowerCase().includes(e.name.toLowerCase()), e.slug);
    assert.doesNotMatch(e.description, /\d+ looks/);
  }
});

test('Try it opens that effect in the studio', () => {
  for (const e of all) assert.equal(studioPath(e), `/studio?open=effect&effect=${encodeURIComponent(e.key)}`);
});

test('every page links to others, never itself, and stays reachable', () => {
  const reached = new Set();
  for (const e of all) {
    const more = related(all, e.slug, 4);
    assert.ok(more.length > 0 || all.length === 1);
    assert.ok(!more.some((m) => m.slug === e.slug));
    for (const m of more) reached.add(m.slug);
  }
  // the gallery links all of them; the related links alone reach most
  assert.ok(reached.size >= Math.min(all.length, 4));
});

test('groups keep every effect once, in a fixed order', () => {
  const g = grouped(all);
  assert.equal(g.reduce((n, x) => n + x.effects.length, 0), all.length);
  assert.ok(g.every((x) => x.effects.length > 0));
});

test('structured data: breadcrumbs always; a clip with a poster is a VideoObject with what Google requires', () => {
  for (const e of all) {
    const ld = jsonLdFor(e, 'https://phantra.ai');
    assert.equal(ld[0]['@type'], 'BreadcrumbList');
    const video = ld.find((b) => b['@type'] === 'VideoObject');
    if (video) {
      for (const k of ['name', 'description', 'thumbnailUrl', 'contentUrl', 'uploadDate']) assert.ok(video[k], `${e.slug} ${k}`);
      assert.match(video.contentUrl, /^https:\/\//);
    }
  }
});
