import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PHRASES, needsCredits, shortfall, topUpLabel, TOP_UP_HREF } from '../src/lib/out-of-credits.ts';

// the server's own sentences, as src/charge.py writes them
const REFUSED = 'out of credits: this still needs 10 and the account has 4 -- top up to continue';
const NO_PLAN = 'Create is included with a plan -- subscribe or top up credits to continue';

test('the studio\'s own refusals for an empty balance are recognised', () => {
  assert.equal(needsCredits(REFUSED), true);
  assert.equal(needsCredits(NO_PLAN), true);
  assert.equal(needsCredits('OUT OF CREDITS: THIS RENDER NEEDS 240 AND THE ACCOUNT HAS 0 -- TOP UP TO CONTINUE'), true);
  // a route's 402 is only ever this, whatever it says
  assert.equal(needsCredits('', 402), true);
  assert.equal(needsCredits(undefined, 402), true);
});

test('no other failure is mistaken for one', () => {
  for (const other of [
    'The still was not made: the image service turned the studio away. That is ours to fix, not yours. Nothing was charged.',
    'the image service is busy. Try again in a minute',
    'HTTP Error 403: Forbidden -- {"detail":"User is locked. Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing."}',
    'this costs 96 credits now',
    'That run was lost (the server restarted while it ran).',
    '', null, undefined,
  ]) assert.equal(needsCredits(other), false, String(other));
  assert.equal(needsCredits('not found', 404), false);
});

test('the numbers are read off the sentence when it has them', () => {
  assert.deepEqual(shortfall(REFUSED), { needs: 10, has: 4 });
  assert.deepEqual(shortfall('out of credits: this render needs 1,365 and the account has 0 -- top up to continue'), { needs: 1365, has: 0 });
  assert.equal(shortfall(NO_PLAN), null);
  assert.equal(shortfall(null), null);
});

test('the way out is named as the credit pill names it, and goes where it goes', () => {
  assert.equal(TOP_UP_HREF, '/pricing');
  assert.equal(topUpLabel({ plan: { key: 'creator', name: 'Creator' } }), 'Buy credits');
  assert.equal(topUpLabel({ plan: null, exempt: true }), 'Buy credits');
  assert.equal(topUpLabel({ plan: null, exempt: false }), 'Choose a plan');
  assert.equal(topUpLabel(null), 'Choose a plan');
});

test('the phrases are plain lower-case substrings, so the server test can read them', () => {
  assert.ok(PHRASES.length >= 2);
  for (const p of PHRASES) assert.equal(p, p.toLowerCase().trim());
});
