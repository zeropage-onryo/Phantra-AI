import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  countedElsewhere,
  creditsText,
  dayText,
  daysUntil,
  expiringSoon,
  expiry,
  lotLabel,
  lotLeft,
  nextRelease,
  num,
  stamp,
} from '../src/lib/credits.ts';

const NOW = Date.parse('2026-10-11T12:00:00+00:00');
const lot = (over = {}) => ({
  id: 1, kind: 'subscription', credits: 1500, remaining: 900,
  granted_at: '2026-09-20T00:00:00+00:00', expires_at: '2026-11-20T00:00:00+00:00', ...over,
});

test('numbers and their word', () => {
  assert.equal(num(1500), '1,500');
  assert.equal(creditsText(1), '1 credit');
  assert.equal(creditsText(0), '0 credits');
  assert.equal(creditsText(3500), '3,500 credits');
});

test('a ledger stamp carries its offset; a bare one is UTC, never local', () => {
  assert.equal(stamp('2026-10-11T12:00:00+00:00').getTime(), NOW);
  assert.equal(stamp('2026-10-11T12:00:00').getTime(), NOW);
  assert.equal(stamp('2026-10-11T12:00:00Z').getTime(), NOW);
  assert.equal(stamp(''), null);
  assert.equal(stamp('not a date'), null);
  assert.equal(stamp(null), null);
});

test('a day is short, and carries its year only when it is another year', () => {
  assert.equal(dayText('2026-11-03T00:00:00+00:00', NOW), 'Nov 3');
  assert.equal(dayText('2027-01-09T00:00:00+00:00', NOW), 'Jan 9, 2027');
  assert.equal(dayText(null, NOW), '');
});

test('a lot is named in a customer\'s words', () => {
  assert.equal(lotLabel('subscription'), 'Plan credits');
  assert.equal(lotLabel('purchase'), 'Top-up');
  assert.equal(lotLabel('promo'), 'Trial credits');
  assert.equal(lotLabel('something new'), 'Credits');
});

test('expiry is relative, and warns under seven days', () => {
  assert.equal(daysUntil('2026-10-12T12:00:00+00:00', NOW), 1);
  assert.deepEqual(expiry('2026-11-20T00:00:00+00:00', NOW), { text: 'in 39 days', soon: false });
  assert.deepEqual(expiry('2026-10-18T11:00:00+00:00', NOW), { text: 'in 6 days', soon: true });
  assert.deepEqual(expiry('2026-10-18T12:00:00+00:00', NOW), { text: 'in 7 days', soon: false });
  assert.deepEqual(expiry('2026-10-12T13:00:00+00:00', NOW), { text: 'tomorrow', soon: true });
  assert.deepEqual(expiry('2026-10-11T18:00:00+00:00', NOW), { text: 'today', soon: true });
  assert.deepEqual(expiry('2026-10-10T00:00:00+00:00', NOW), { text: 'Expired', soon: false });
  assert.deepEqual(expiry(null, NOW), { text: 'Never', soon: false });
});

test('what is left of a lot is a share between 0 and 1', () => {
  assert.equal(lotLeft(lot()), 0.6);
  assert.equal(lotLeft(lot({ remaining: 0 })), 0);
  assert.equal(lotLeft(lot({ remaining: 2000 })), 1);
  assert.equal(lotLeft(lot({ credits: 0, remaining: 0 })), 0);
});

test('only credit still in a lot that runs out this week is expiring soon', () => {
  const lots = [
    lot({ id: 1, remaining: 40, expires_at: '2026-10-14T00:00:00+00:00' }),
    lot({ id: 2, remaining: 0, expires_at: '2026-10-13T00:00:00+00:00' }),
    lot({ id: 3, remaining: 900, expires_at: '2026-11-20T00:00:00+00:00' }),
    lot({ id: 4, remaining: 25, expires_at: null }),
  ];
  assert.equal(expiringSoon(lots, NOW), 40);
  assert.equal(expiringSoon([], NOW), 0);
});

test('a yearly plan says its next month: how much, and when', () => {
  const creditsOf = (key) => ({ creator: 3500 })[key];
  const schedules = [
    { plan: 'creator', months_released: 2, months_total: 12, next_release_at: '2026-11-03T00:00:00+00:00' },
  ];
  assert.deepEqual(nextRelease(schedules, creditsOf, NOW), { credits: 3500, on: 'Nov 3', left: 10 });
  assert.equal(nextRelease([], creditsOf, NOW), null);
  // a plan the catalog does not know is not guessed at
  assert.equal(nextRelease([{ ...schedules[0], plan: 'gone' }], creditsOf, NOW), null);
  // the soonest of two
  const two = [{ ...schedules[0], next_release_at: '2026-12-03T00:00:00+00:00' }, schedules[0]];
  assert.equal(nextRelease(two, creditsOf, NOW).on, 'Nov 3');
});

test('whose credits: named only when it is not the open workspace', () => {
  const north = { id: 1, label: 'North Films' };
  const south = { id: 2, label: 'South Co', slug: 'south', role: 'member' };
  // in two workspaces with the other one open: both are named
  assert.deepEqual(countedElsewhere(north, south), { counted: 'North Films', open: 'South Co' });
  // the open workspace is where the credits are: nothing to say
  assert.equal(countedElsewhere(north, { ...north, slug: 'north' }), null);
  // an older API, a caller who cannot be named, or nothing open yet
  assert.equal(countedElsewhere(undefined, south), null);
  assert.equal(countedElsewhere(null, south), null);
  assert.equal(countedElsewhere(north, null), null);
});
