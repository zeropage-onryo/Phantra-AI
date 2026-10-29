import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { HUB_GROUPS } from '../src/landing-pages/hub.ts';

// Read the entries as text: they import the catalog through "@/", which
// node:test cannot resolve. Each entry states its slug and section once.
const DIR = new URL('../src/landing-pages/entries/', import.meta.url);
const entries = readdirSync(DIR)
  .filter((f) => f.endsWith('.ts'))
  .map((f) => readFileSync(new URL(f, DIR), 'utf8'))
  .map((src) => ({
    slug: src.match(/\bslug: "([^"]+)"/)?.[1],
    section: src.match(/\bsection: "([a-z]+)"/)?.[1],
    seasonal: /\n  season: \{/.test(src),
  }));
const makeSlugs = entries.filter((e) => e.section === 'make').map((e) => e.slug);
const hubSlugs = HUB_GROUPS.flatMap((g) => g.slugs);

test('every /make page is on the hub, exactly once', () => {
  assert.ok(makeSlugs.length >= 17, `read ${makeSlugs.length} /make entries`);
  const missing = makeSlugs.filter((s) => !hubSlugs.includes(s));
  assert.deepEqual(missing, [], 'add these to a group in landing-pages/hub.ts');
  const twice = hubSlugs.filter((s, i) => hubSlugs.indexOf(s) !== i);
  assert.deepEqual(twice, []);
});

test('the hub names no slug that has no /make entry', () => {
  assert.deepEqual(hubSlugs.filter((s) => !makeSlugs.includes(s)), []);
});

test('seasonal pages sit in the Seasonal group, listed all year', () => {
  const seasonal = HUB_GROUPS.find((g) => g.title === 'Seasonal');
  assert.ok(seasonal);
  for (const e of entries.filter((x) => x.seasonal)) assert.ok(seasonal.slugs.includes(e.slug), e.slug);
});

test('the hub is linked from the header, the footer and the sitemap', () => {
  const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
  assert.match(read('../src/components/site-header.tsx'), /href="\/make"/);
  assert.match(read('../src/components/site-footer.tsx'), /\["All tools", "\/make"\]/);
  assert.match(read('../src/app/sitemap.ts'), /"\/make"/);
});
