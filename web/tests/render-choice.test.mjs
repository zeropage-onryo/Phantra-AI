import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { held, usable, firstUsable, defaultPick, pickFor, withModel, planFor, approveText, renderText, chipText, creditsText, legalDuration, specOf, draftFrame, isDraft, withDraft, shotsToDraw, keyframeNote, keyframeCount, keyframePrice, keyframeButton, keyframeCeilingNote, oneClipNote } from '../src/lib/render-choice.ts';

const choices = (values, d) => ({ kind: 'choices', values, default: d });
const renderers = {
  // an unconfigured renderer (the catalogue is keyed by provider; fal is the only live one)
  off: { label: 'Off', available: false, models: [
    { id: 'dormant', label: 'Dormant', available: true, duration: choices([5, 10], 5), frame: choices(['720p'], '720p'), price: { kind: 'per_second', usd: 0.05 } }] },
  fal: { label: 'fal.ai', available: true, frame_axis: 'resolution', models: [
    { id: 'veo3.1', label: 'Veo 3.1', available: true, duration: choices([4, 6, 8], 8), frame: choices(['720p'], '720p'), price: { kind: 'per_second', usd: 0.4 } },
    { id: 'kling', label: 'Kling', available: true, duration: choices([5, 10], 5), frame: choices(['1080p'], '1080p'), price: { kind: 'per_second', usd: 0.07 } },
    { id: 'ltx', label: 'LTX', available: true, duration: { kind: 'range', min: 1, max: 20, default: 6 }, frame: choices(['1080p', '2160p'], '1080p'), price: { kind: 'per_second', usd_by_frame: { '1080p': 0.04, '2160p': 0.16 } } },
    { id: 'ghost', label: 'Ghost', available: false, duration: choices([5], 5), frame: choices(['1080p'], '1080p'), price: { kind: 'flat', usd: 0.01 } }] },
};
beforeEach(() => held.clear());

test('an unconfigured renderer is never usable, whatever its models report', () => {
  assert.equal(usable(renderers, 'off', 'dormant'), false);
  assert.equal(usable(renderers, 'fal', 'ghost'), false);
  assert.equal(usable(renderers, 'fal', 'kling'), true);
});

test('the plan leads when it can render; otherwise the CHEAPEST usable model, not registry order', () => {
  assert.deepEqual(defaultPick(renderers, { provider: 'fal', model: 'kling' }), { provider: 'fal', model: 'kling', duration: 5, frame: '1080p' });
  // planned for an unconfigured renderer: LTX 6s@0.04 = $0.24 beats Kling $0.35 and Veo $3.20
  assert.deepEqual(defaultPick(renderers, { provider: 'off', model: 'dormant' }), { provider: 'fal', model: 'ltx', duration: 6, frame: '1080p' });
  assert.equal(firstUsable({ off: renderers.off }), null);
  // nothing usable anywhere: the plan is still shown, on a dead button
  assert.equal(defaultPick({ off: renderers.off }, { provider: 'off', model: 'dormant' }).provider, 'off');
});

test('a held pick survives, until it stops being usable', () => {
  held.set(7, { provider: 'fal', model: 'ltx', duration: 9, frame: '2160p' });
  assert.equal(pickFor(renderers, 7, { provider: 'fal', model: 'kling' }).duration, 9);
  held.set(8, { provider: 'off', model: 'dormant', duration: 5, frame: '720p' });
  assert.equal(pickFor(renderers, 8, { provider: 'fal', model: 'kling' }).model, 'kling');
});

test('a new model takes its own defaults', () => {
  assert.deepEqual(withModel(renderers, 'fal', 'veo3.1'), { provider: 'fal', model: 'veo3.1', duration: 8, frame: '720p' });
});

test('a legal length is the model\'s own set', () => {
  const kling = specOf(renderers, 'fal', 'kling').duration;
  assert.equal(legalDuration(kling, 7), false);
  assert.equal(legalDuration(specOf(renderers, 'fal', 'ltx').duration, 7), true);
});

test('a timed scene that fits the model is one clip with its shots inside (2026-10-26)', () => {
  const spec = specOf(renderers, 'fal', 'kling');
  const pick = withModel(renderers, 'fal', 'kling');
  const parts = [{ seconds: 3 }, { seconds: 4 }, { seconds: 3 }];
  const quote = { timed: false, one_clip: true, durations: [10], estimate_usd: 1.2, credits: 288 };
  const plan = planFor(spec, pick, parts, quote);
  assert.equal(plan.oneClip, true);
  assert.equal(plan.n, 1);
  assert.deepEqual(plan.lengths, [10]);
  assert.equal(approveText(plan), 'Approve · 3 shots, one clip · 288 cr');
  assert.equal(renderText(plan), 'Render · 3 shots, one clip · 288 cr');
  assert.equal(chipText(spec, pick, plan), 'KLING · 3 SHOTS · 10S · 1080P');
  assert.equal(oneClipNote(3, 2), 'The whole scene renders as one clip, its 3 shots cut inside it, held to your 2 photos.');
  assert.equal(oneClipNote(3, 0), 'The whole scene renders as one clip, its 3 shots cut inside it.');
});

test('the button carries shot count and price; a timed scene is priced by the server', () => {
  const spec = specOf(renderers, 'fal', 'kling');
  const pick = withModel(renderers, 'fal', 'kling');
  const parts = [{ seconds: 3 }, { seconds: 4, media_url: 'x.mp4' }, { seconds: 7 }];
  // the server's quote for this pick: the windows fitted, the done shot skipped
  const quote = { timed: true, durations: [5, 10], estimate_usd: 1.05, credits: 252 };
  const plan = planFor(spec, pick, parts, quote);
  assert.deepEqual(plan.lengths, [5, 10]);
  assert.equal(approveText(plan), 'Approve · 2 shots · 252 cr');
  assert.equal(chipText(spec, pick, plan), 'KLING · 2 SHOTS · 1080P');
  // no quote yet: the shots are named, the number is not made up here
  const waiting = planFor(spec, pick, parts);
  assert.deepEqual(waiting.lengths, []);
  assert.equal(approveText(waiting), 'Approve · 2 shots · pricing…');
  assert.equal(approveText(planFor(spec, pick, parts, { error: 'no', timed: true, durations: [], estimate_usd: 0 })), 'Approve · 2 shots · refused');
  // a scene that renders whole with no quote yet: no dollar label, ever
  // (2026-10-08) -- the client never prices a render itself
  const whole = planFor(spec, pick, null);
  assert.equal(approveText(whole), 'Approve · 1 shot · pricing…');
  assert.equal(chipText(spec, pick, whole), 'KLING · 5S · 1080P');
  assert.equal(approveText(planFor({ ...spec, price: undefined }, pick, null)), 'Approve · 1 shot · pricing…');
  assert.equal('usd' in whole, false);
});

test('a charged account sees credits from the server, never a client-side conversion', () => {
  const spec = specOf(renderers, 'fal', 'kling');
  const pick = withModel(renderers, 'fal', 'kling');
  // a scene that renders whole, priced by the listing / /quote
  const charged = planFor(spec, pick, null, { timed: false, durations: [5], estimate_usd: 0.35, credits: 84 });
  assert.equal(charged.credits, 84);
  assert.equal(approveText(charged), 'Approve · 1 shot · 84 cr');
  assert.equal(approveText(planFor(spec, pick, null, { timed: false, durations: [5], estimate_usd: 0.35, credits: 1 })), 'Approve · 1 shot · 1 cr');
  assert.equal(approveText(planFor(spec, pick, null, { timed: false, durations: [5], estimate_usd: 0.35, credits: 1840 })), 'Approve · 1 shot · 1,840 cr');
  // there is no BYOK any more: a priced quote is credits, never "on your key"
  assert.equal('byok' in charged, false);
  assert.equal(creditsText(1), '1 credit');
  assert.equal(creditsText(1840), '1,840 credits');
  // asked, not answered: no number is made up
  assert.equal(approveText(planFor(spec, pick, null, null)), 'Approve · 1 shot · pricing…');
  assert.equal(approveText(planFor(spec, pick, null, { error: 'band' })), 'Approve · 1 shot · refused');
  // a timed scene's credits are the quote's sum
  const parts = [{ seconds: 3 }, { seconds: 7 }];
  const timed = planFor(spec, pick, parts, { timed: true, durations: [5, 10], estimate_usd: 1.05, credits: 252 });
  assert.equal(approveText(timed), 'Approve · 2 shots · 252 cr');
});

test('an exempt account still sees the price, marked not charged', () => {
  const spec = specOf(renderers, 'fal', 'kling');
  const pick = withModel(renderers, 'fal', 'kling');
  const plan = planFor(spec, pick, null, { timed: false, durations: [5], estimate_usd: 0.3, credits: 72 });
  assert.equal(approveText(plan, true), 'Approve · 1 shot · 72 cr · not charged');
  assert.equal(approveText(plan), 'Approve · 1 shot · 72 cr');
  assert.equal(creditsText(72, true), '72 credits · not charged');
  // nothing priced yet: no suffix on a number that is not there
  assert.equal(approveText(planFor(spec, pick, null, null), true), 'Approve · 1 shot · pricing…');
  assert.equal(approveText(planFor(spec, pick, null, { error: 'band' }), true), 'Approve · 1 shot · refused');
});

test('a draft is the same approve at the frame the catalogue names, and nothing else', () => {
  const wan = {
    id: 'wan3', label: 'wan3 (wan)', draft: '480p',
    duration: { kind: 'range', min: 2, max: 10, default: 5 },
    frame: { kind: 'choices', values: ['480p', '720p', '1080p'], default: '720p' },
  };
  const pick = { provider: 'fal', model: 'wan3', duration: 5, frame: '720p' };
  assert.equal(draftFrame(wan), '480p');
  assert.equal(isDraft(wan, pick), false);
  const drafting = withDraft(wan, pick, true);
  assert.deepEqual(drafting, { ...pick, frame: '480p' });
  assert.equal(isDraft(wan, drafting), true);
  // off again is the frame the model renders at by default, not whatever came before
  assert.equal(withDraft(wan, { ...drafting }, false).frame, '720p');
  assert.equal(withDraft(wan, { ...pick, frame: '1080p' }, false).frame, '720p');
  // the button says which it is; the price is still the server's
  const plan = { timed: true, n: 2, lengths: [5, 5], usd: 0.5, credits: 120, refused: '' };
  assert.equal(approveText(plan, false, true), 'Draft · 2 shots · 120 cr');
  assert.equal(approveText(plan, false, false), 'Approve · 2 shots · 120 cr');
  // the scene's own Render button (the Render card) says the same
  assert.equal(renderText(plan, false, true), 'Draft · 2 shots · 120 cr');
  assert.equal(renderText(plan, false, false), 'Render · 2 shots · 120 cr');
  assert.equal(renderText(plan, true, true), 'Draft · 2 shots · 120 cr · not charged');

  // a model with no draft offers none, whatever is asked of it
  const kling = { ...wan, id: 'kling', draft: null, frame: { kind: 'fixed', values: ['1080p'], default: '1080p' } };
  assert.equal(draftFrame(kling), null);
  assert.equal(isDraft(kling, { ...pick, frame: '1080p' }), false);
  assert.deepEqual(withDraft(kling, pick, true), pick);
  // a draft frame the card cannot pick is not a draft (a stale catalogue)
  assert.equal(draftFrame({ ...wan, draft: '360p' }), null);
  assert.equal(draftFrame(null), null);
  assert.equal(isDraft(wan, null), false);
});


test('a shot is offered on its own only while two or more still need a keyframe', () => {
  const parts = [
    { n: 1, seconds: 3, reference_image: '/k1.jpg' },
    { n: 2, seconds: 4 },
    { n: 3, seconds: 3 },
    { n: 4, seconds: 2, media_url: '/c4.mp4' },        // rendered already: nothing to anchor
  ];
  assert.deepEqual(shotsToDraw(parts, 2).map((p) => p.n), [2, 3]);
  // the last one missing is the strip button's, at the same price
  assert.deepEqual(shotsToDraw([parts[0], parts[1]], 1), []);
  // nothing quoted (drawing is off, or it is all drawn): nothing offered
  assert.deepEqual(shotsToDraw(parts, 0), []);
  assert.deepEqual(shotsToDraw(parts, null), []);
  // a scene that renders whole has no shots to pick between
  assert.deepEqual(shotsToDraw([], 1), []);
  assert.deepEqual(shotsToDraw(null, 3), []);
});

test('the keyframe line is read off the shots, not only the scene\'s own still', () => {
  const none = 'No keyframes drawn · the clips render from the prompt and the references.';
  const all = 'Each clip starts on its keyframe.';
  const shots = (...stills) => stills.map((s, i) => ({ n: i + 1, seconds: 3, reference_image: s }));
  assert.equal(keyframeNote(shots(null, null, null), null), none);
  // shot 2 drawn first: the scene's own still (shot 1's) is not set yet
  assert.equal(keyframeNote(shots(null, '/k2.jpg', null), null),
    '1 of 3 shots have a keyframe · the others render from the prompt and the references.');
  assert.equal(keyframeNote(shots('/k1.jpg', '/k2.jpg', null), '/k1.jpg'),
    '2 of 3 shots have a keyframe · the others render from the prompt and the references.');
  assert.equal(keyframeNote(shots('/k1.jpg', '/k2.jpg', '/k3.jpg'), '/k1.jpg'), all);
  // a scene that renders whole has the one still, or none
  assert.equal(keyframeNote([], '/k.jpg'), all);
  assert.equal(keyframeNote(null, null), none);
});

test('a keyframe price that is a ceiling says "up to", on the count and on the credits', () => {
  // the server marks it (scene_chain.keyframe_quote): a scene with no timed
  // shots is drawn as a still per moment of its move, so fewer may be charged
  const ceiling = { stills: 2, each: 10, credits: 20, up_to: true };
  assert.equal(keyframeButton(ceiling), 'Draw up to 2 keyframes first');
  assert.equal(keyframePrice(ceiling), 'up to 20 credits');
  assert.equal(keyframeCount(ceiling), 'up to 2 keyframes');
  assert.equal(keyframeCeilingNote(ceiling),
    'One still for each moment of the take, 2 at most · you are charged for the ones drawn.');
  // an account that is not charged still sees the price, said once
  assert.equal(keyframePrice(ceiling, true), 'up to 20 credits · not charged');
});

test('an exact keyframe price reads as it always did, and explains nothing', () => {
  const strip = { stills: 3, each: 10, credits: 30 };
  assert.equal(keyframeButton(strip), 'Draw 3 keyframes first');
  assert.equal(keyframePrice(strip), '30 credits');
  assert.equal(keyframeCount(strip), '3 keyframes');
  assert.equal(keyframeCeilingNote(strip), '');
  const one = { stills: 1, each: 10, credits: 10 };
  assert.equal(keyframeButton(one), 'Draw keyframe first');
  assert.equal(keyframeCount(one), '1 keyframe');
  assert.equal(keyframeCeilingNote(null), '');
  assert.equal(keyframeCeilingNote(undefined), '');
});

test('a prompt naming another shape than the scene renders is said; vertical or silent is not', async () => {
  const { shapeAsked, SCENE_SHAPE } = await import('../src/lib/render-choice.ts');
  assert.equal(SCENE_SHAPE, '9:16');
  assert.equal(shapeAsked('A 16:9 cinematic shot of a can on ice'), '16:9');
  assert.equal(shapeAsked('wide landscape frame, slow push in'), '16:9');
  assert.equal(shapeAsked('square format, top-down'), '1:1');
  assert.equal(shapeAsked('vertical 9:16, handheld'), '');
  assert.equal(shapeAsked('a can on a table at 3:45 pm'), '');   // a time is not a frame
  assert.equal(shapeAsked('(0-3s) close-up; (3-6s) wide'), '');
  assert.equal(shapeAsked(''), '');
  assert.equal(shapeAsked(null), '');
});
