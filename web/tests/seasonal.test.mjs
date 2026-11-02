import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { inSeason, monthDayIn, isMonthDay } from '../src/landing-pages/seasonal.ts';

// The Halloween window as the entry states it (Mike, 2026-10-27: on for
// Halloween, "ends the day after halloween").
const HALLOWEEN = { start: '10-01', end: '11-01', tab: 'Halloween', timeZone: 'America/New_York' };

test('the day is read on Eastern time, not UTC', () => {
  // 03:00 UTC on Nov 2 is still 11pm on Nov 1 in New York
  assert.equal(monthDayIn(new Date('2026-11-02T03:00:00Z'), 'America/New_York'), '11-01');
  assert.equal(monthDayIn(new Date('2026-11-02T03:00:00Z'), 'UTC'), '11-02');
});

test('the Halloween tab is on from Oct 1 through Nov 1, every year', () => {
  assert.equal(inSeason(HALLOWEEN, new Date('2026-10-01T04:30:00Z')), true, 'Oct 1, 00:30 ET');
  assert.equal(inSeason(HALLOWEEN, new Date('2026-10-27T17:00:00Z')), true, 'today');
  assert.equal(inSeason(HALLOWEEN, new Date('2026-10-31T23:00:00Z')), true, 'Halloween night');
  assert.equal(inSeason(HALLOWEEN, new Date('2026-11-02T03:30:00Z')), true, 'Nov 1, 11:30pm ET');
  assert.equal(inSeason(HALLOWEEN, new Date('2027-10-15T12:00:00Z')), true, 'next year');
});

test('and off outside it', () => {
  assert.equal(inSeason(HALLOWEEN, new Date('2026-10-01T03:30:00Z')), false, 'Sep 30, 11:30pm ET');
  assert.equal(inSeason(HALLOWEEN, new Date('2026-11-02T05:00:00Z')), false, 'Nov 2, 00:00 ET');
  assert.equal(inSeason(HALLOWEEN, new Date('2026-12-25T12:00:00Z')), false);
  assert.equal(inSeason(HALLOWEEN, new Date('2027-03-01T12:00:00Z')), false);
});

test('a window that ends before it starts wraps the new year', () => {
  const holidays = { start: '12-20', end: '01-02', tab: 'Holidays' };
  assert.equal(inSeason(holidays, new Date('2026-12-28T17:00:00Z')), true);
  assert.equal(inSeason(holidays, new Date('2027-01-02T17:00:00Z')), true);
  assert.equal(inSeason(holidays, new Date('2027-01-03T17:00:00Z')), false);
  assert.equal(inSeason(holidays, new Date('2026-12-19T17:00:00Z')), false);
});

test('a malformed window is never on', () => {
  assert.equal(isMonthDay('10-1'), false);
  assert.equal(isMonthDay('13-01'), false);
  assert.equal(inSeason({ start: '10-1', end: '11-01', tab: 'x' }, new Date('2026-10-15T12:00:00Z')), false);
});

test('the Halloween page carries that window and the spooky accent', () => {
  const entry = readFileSync(new URL('../src/landing-pages/entries/ai-halloween-costume-try-on.ts', import.meta.url), 'utf8');
  assert.match(entry, /season: \{ start: "10-01", end: "11-01", tab: "Halloween", timeZone: "America\/New_York", accent: HALLOWEEN \}/);
});

test('the season decides the tab and the look, never whether the page exists', () => {
  // the template keeps every page in its static params and the sitemap
  // lists every entry; a seasonal page must not be filtered out of either
  const route = readFileSync(new URL('../src/landing-pages/route.tsx', import.meta.url), 'utf8');
  const sitemap = readFileSync(new URL('../src/app/sitemap.ts', import.meta.url), 'utf8');
  for (const src of [route, sitemap]) assert.doesNotMatch(src, /inSeason|season/);
  // the make route rebuilds hourly so the look follows the calendar
  const page = readFileSync(new URL('../src/app/make/[slug]/page.tsx', import.meta.url), 'utf8');
  assert.match(page, /export const revalidate = 3600;/);
});

test('the Halloween page never says "free" (Mike, 2026-10-27)', () => {
  const entry = readFileSync(new URL('../src/landing-pages/entries/ai-halloween-costume-try-on.ts', import.meta.url), 'utf8');
  const copy = entry.split('\n').filter((line) => !line.trim().startsWith('//')).join('\n');
  assert.doesNotMatch(copy, /\bfree\b/i);
});
