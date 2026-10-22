import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lay, partButton, priceMoved } from '../src/lib/ad-audio.ts';
import { voiceoverPlacement } from '../src/lib/cut/voiceover.ts';
import { musicPlacement } from '../src/lib/cut/music.ts';

/* a built motion ad: picture and graphics, no audio tracks yet */
const AD = { fps: 30, duration: 300, tracks: [
  { id: 'V1', kind: 'video', clips: [] },
  { id: 'G1', kind: 'graphic', items: [] },
] };

/* a stand-in for POST /ops that does the three edits the placements use */
function server(start) {
  let version = 1;
  let doc = structuredClone(start);
  const sent = [];
  const apply = async (baseId, op, args) => {
    assert.equal(baseId, version, 'every edit goes against the head the last one left');
    sent.push(op);
    doc = structuredClone(doc);
    if (op === 'add_track') doc.tracks.push({ id: `A${doc.tracks.filter((t) => t.kind === 'audio').length + 1}`, kind: 'audio', role: args.role, clips: [] });
    if (op === 'overwrite') {
      const t = doc.tracks.find((x) => x.id === args.track_id);
      t.clips.push({ id: `c${version}`, media: args.clip.media, at: args.at, src_in: args.clip.src_in, src_out: args.clip.src_out });
    }
    if (op === 'duck') doc.tracks.find((x) => x.id === args.track_id).duck_under = args.under;
    if (op === 'set_fade') assert.ok(args.clip_id, 'the fade names the bed it just laid');
    version += 1;
    return { head: { id: version, doc } };
  };
  return { apply, sent, doc: () => doc };
}

test('a read lands on a new voice track from the start of the ad', async () => {
  const s = server(AD);
  const head = await lay({ id: 1, doc: AD }, voiceoverPlacement(AD, 'asset:7', 9.5, 0), s.apply);
  const voice = head.doc.tracks.find((t) => t.role === 'voice');
  assert.deepEqual(voice.clips.map((c) => [c.media, c.at, c.src_out]), [['asset:7', 0, 285]]);
  assert.deepEqual(s.sent, ['add_track', 'overwrite']);
});

test('the music after the voice ducks under it; the voice after the music ducks it too', async () => {
  const s = server(AD);
  let head = await lay({ id: 1, doc: AD }, voiceoverPlacement(AD, 'asset:7', 9.5, 0), s.apply);
  head = await lay(head, musicPlacement(head.doc, 'asset:8', 12), s.apply);
  assert.equal(head.doc.tracks.find((t) => t.role === 'music').duck_under, 'voice');

  const t = server(AD);
  let h = await lay({ id: 1, doc: AD }, musicPlacement(AD, 'asset:8', 12), t.apply);
  h = await lay(h, voiceoverPlacement(h.doc, 'asset:7', 9.5, 0), t.apply);
  assert.equal(h.doc.tracks.find((x) => x.role === 'music').duck_under, 'voice');
});

test('a refused edit stops the rest', async () => {
  const steps = [{ op: 'a', args: () => ({}) }, { op: 'b', args: () => ({}) }];
  const seen = [];
  await assert.rejects(lay({ id: 1, doc: {} }, steps, async (_, op) => { seen.push(op); throw new Error('stale'); }));
  assert.deepEqual(seen, ['a']);
});

test('the buttons say the price, and a moved price is said', () => {
  assert.equal(partButton('voice', { status: 'ready', credits: 12, charged: true }, false), 'Read it · 12 credits');
  assert.equal(partButton('music', { status: 'ready', credits: 1 }, true), 'Add music · 1 credit (not charged)');
  assert.equal(partButton('voice', { status: 'running', credits: 12 }, false), 'Reading…');
  assert.equal(partButton('music', undefined, false), 'Add music · pricing…');
  const moved = priceMoved({ status: 'running', credits: 12 }, 14);
  assert.deepEqual([moved.status, moved.credits], ['ready', 14]);
  assert.match(moved.note, /price changed/);
});

test('a read is never claimed a frame longer than the file (3.03s is 90 frames, not 91)', () => {
  const [, put] = voiceoverPlacement(AD, 'asset:7', 3.03, 0);
  assert.equal(put.args({ ...AD, tracks: [...AD.tracks, { id: 'A1', kind: 'audio', role: 'voice', clips: [] }] }).clip.src_out, 90);
  const lay2 = musicPlacement(AD, 'asset:8', 3.03);
  assert.equal(lay2.find((s) => s.op === 'overwrite').args({ ...AD, tracks: [...AD.tracks, { id: 'A1', kind: 'audio', role: 'music', clips: [] }] }).clip.src_out, 90);
});
