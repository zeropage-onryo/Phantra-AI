import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { absolute, isWhole, longDate, rssXml, xml } from '../src/lib/whats-new-public.ts';

/* The public What's new page and its RSS (2026-10-26, docs/tasks/task-whats-new.md step 4). */

const src = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const row = (over = {}) => ({
  id: 'model:grok1.5', source: 'model', tag: 'NEW MODEL', title: 'Grok Imagine is here',
  line: "xAI's video model & more", media: { kind: 'video', url: 'https://media.phantra.ai/m/1/g.mp4', poster: 'https://media.phantra.ai/t/1/g.jpg' },
  href: '/studio?spark=A%20shot', eta: null, ends: null, live_at: '2026-10-26T13:00:00+00:00', ...over,
});

test('only a row with a title and a link on this site is drawn', () => {
  assert.equal(isWhole(row()), true);
  assert.equal(isWhole(row({ title: ' ' })), false);
  assert.equal(isWhole(row({ href: 'https://elsewhere.example' })), false);
  assert.equal(isWhole(row({ href: '//elsewhere.example' })), false);
});

test('the feed is valid RSS: escaped words, absolute links, a date, the poster as the picture', () => {
  const out = rssXml('https://phantra.ai', [row(), row({ id: 'soon:x', source: 'soon', tag: 'COMING SOON', eta: 'This month', live_at: null, href: '/studio', media: { kind: 'none', url: null, poster: null } })]);
  assert.match(out, /^<\?xml version="1.0" encoding="UTF-8"\?>\n<rss version="2.0"/);
  assert.match(out, /<title>NEW MODEL: Grok Imagine is here<\/title>/);
  assert.match(out, /<link>https:\/\/phantra.ai\/studio\?spark=A%20shot<\/link>/);
  assert.match(out, /xAI&apos;s video model &amp; more/);
  assert.match(out, /<pubDate>Mon, 26 Oct 2026 13:00:00 GMT<\/pubDate>/);
  assert.match(out, /<enclosure url="https:\/\/media.phantra.ai\/t\/1\/g.jpg"/);
  assert.match(out, /Coming this month\./);
  assert.equal((out.match(/<item>/g) || []).length, 2);
  assert.doesNotMatch(out, /credit|prompt/i);
});

test('helpers', () => {
  assert.equal(absolute('https://phantra.ai', '/models'), 'https://phantra.ai/models');
  assert.equal(absolute('https://phantra.ai', 'https://x.example/a.jpg'), 'https://x.example/a.jpg');
  assert.equal(absolute('https://phantra.ai', null), null);
  assert.equal(xml('<a & "b">'), '&lt;a &amp; &quot;b&quot;&gt;');
  assert.equal(longDate('2026-10-26T13:00:00+00:00'), 'October 26, 2026');
  assert.equal(longDate(null), '');
});

test('the page is public, listed, linked and redirected like the other public pages', () => {
  assert.match(src('../src/app/sitemap.ts'), /"\/whats-new"/);
  assert.match(src('../src/components/site-footer.tsx'), /\["What's new", "\/whats-new"\]/);
  assert.match(src('../next.config.ts'), /"\/whats-new\/rss.xml"/);
  assert.doesNotMatch(src('../src/app/robots.ts'), /whats-new/);
  assert.match(src('../src/app/whats-new/page.tsx'), /application\/rss\+xml/);
});
