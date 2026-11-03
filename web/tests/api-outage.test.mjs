import { test } from 'node:test';
import assert from 'node:assert/strict';

// QA 2026-11-02 T11: with the API down the studio read an outage as an
// empty account or printed "INTERNAL SERVER ERROR". apiFetch now says it.
const heard = [];
globalThis.window = new EventTarget();
globalThis.window.addEventListener('phantra:reach', (e) => heard.push(e.detail.up));
const { apiFetch, ApiError, UNREACHABLE } = await import('../src/lib/api.ts');

const answer = (status, body, type = 'application/json') => async () =>
  new Response(body, { status, headers: { 'content-type': type } });

async function refusal(fetcher) {
  globalThis.fetch = fetcher;
  try {
    await apiFetch('/me');
  } catch (e) {
    assert.ok(e instanceof ApiError);
    return e;
  }
  assert.fail('no refusal');
}

test('a fetch that cannot connect is an outage, said plainly', async () => {
  const e = await refusal(async () => { throw new TypeError('Failed to fetch'); });
  assert.equal(e.code, 'unreachable');
  assert.equal(e.status, 0);
  assert.equal(e.message, UNREACHABLE);
  assert.deepEqual(heard, [false]);
});

test("the proxy's bare 500 is an outage, never its raw text", async () => {
  const e = await refusal(answer(500, 'Internal Server Error', 'text/plain'));
  assert.equal(e.code, 'unreachable');
  assert.doesNotMatch(e.message, /internal server error/i);
});

test('our own 5xx keeps its words', async () => {
  const e = await refusal(answer(503, JSON.stringify({ error: { code: 'not_saved', message: 'the picture could not be saved just now' } })));
  assert.equal(e.code, 'not_saved');
  assert.equal(e.message, 'the picture could not be saved just now');
});

test('a 4xx is not an outage, and the first answer clears one', async () => {
  heard.length = 0;
  await refusal(async () => { throw new TypeError('Failed to fetch'); });
  const e = await refusal(answer(404, JSON.stringify({ error: { code: 'not_found', message: 'no such scene' } })));
  assert.equal(e.code, 'not_found');
  globalThis.fetch = answer(200, JSON.stringify({ ok: true }));
  assert.deepEqual(await apiFetch('/me'), { ok: true });
  assert.deepEqual(heard, [false, true]);
});

test('a cancelled request is not an outage', async () => {
  globalThis.fetch = async () => { throw new DOMException('aborted', 'AbortError'); };
  await assert.rejects(apiFetch('/me'), (e) => e.name === 'AbortError');
});

test('the studio shell says an outage above every page', async () => {
  const { readFileSync } = await import('node:fs');
  const shell = readFileSync(new URL('../src/components/studio/shell.tsx', import.meta.url), 'utf8');
  assert.match(shell, /addEventListener\(REACH_EVENT/);
  assert.match(shell, /\{UNREACHABLE\}/);
});
