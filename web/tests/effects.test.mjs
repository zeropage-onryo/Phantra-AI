import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  candidates, sourcesFor, unavailable, defaults, settle, optionLabel, valueLabel, missing, takesLine,
  fromPrice, requestOf, begin, candidateOf, addToPair, facesOf,
} from '../src/lib/effects.ts';

const KLING = {
  id: 'kling-effect', label: 'Kling effects', category: 'video_effect', blurb: 'templates',
  takes: 'image', output: 'video', sources: { min: 1, max: 2 }, prompt: 'none', credits: 68,
  options: {
    effect_scene: { values: ['heart_gesture', 'bloom_bloom'], default: null, required: true },
    duration: { values: ['5', '10'], default: '5', required: false },
  },
};
const EDIT = {
  id: 'nano-banana-edit', label: 'Nano Banana edit', category: 'image_edit', blurb: 'edit',
  takes: 'image', output: 'image', sources: { min: 1, max: 4 }, prompt: 'required', credits: 10,
  options: { aspect_ratio: { values: ['auto', '1:1'], default: 'auto', required: false } },
};
const SOUND = {
  id: 'add-sound', label: 'Add sound', category: 'finish', blurb: 'sound',
  takes: 'video', output: 'video', sources: { min: 1, max: 1 }, prompt: 'required', credits: null, options: {},
};

test('what an effect can act on: the attached images first, then results from the newest back', () => {
  const all = candidates(['/refs/a.jpg', '/refs/b.jpg'], [
    { image: 'https://r2/old.png' },
    { clip: 'https://r2/clip.mp4', asset: 'gen:7' },
    { clip: 'https://r2/unnamed.mp4' },                 // a clip with no id cannot be a source
    { image: 'https://r2/new.png', asset: 'gen:9' },
  ]);
  assert.deepEqual(all.map((c) => `${c.kind}:${c.ref}:${c.from}`), [
    'image:/refs/a.jpg:attached',
    'image:/refs/b.jpg:attached',
    'image:gen:9:the last still',
    'clip:gen:7:the last clip',
    'image:https://r2/old.png:an earlier still',
  ]);
  // a render is drawn by its address and named by its id
  assert.equal(all[2].thumb, 'https://r2/new.png');
});

test('an effect is bound to what is attached, else to the newest result that fits', () => {
  const all = candidates(['/refs/a.jpg', '/refs/b.jpg', '/refs/c.jpg'], [{ clip: 'x', asset: 'gen:7' }]);
  assert.deepEqual(sourcesFor(KLING, all).map((c) => c.ref), ['/refs/a.jpg', '/refs/b.jpg']);   // up to what it takes
  assert.deepEqual(sourcesFor(SOUND, all).map((c) => c.ref), ['gen:7']);
  const results = candidates([], [{ image: 'old' }, { image: 'new', asset: 'gen:9' }]);
  assert.deepEqual(sourcesFor(EDIT, results).map((c) => c.ref), ['gen:9']);                     // one, the newest
  assert.equal(unavailable(EDIT, results), '');
  assert.match(unavailable(SOUND, results), /Needs a clip/);
  assert.match(unavailable(EDIT, []), /Needs an image/);
  // an effect that takes two binds to the two newest; with one there, it says so
  const pair = { takes: 'image', sources: { min: 2, max: 2 } };
  assert.deepEqual(sourcesFor(pair, results).map((c) => c.ref), ['gen:9', 'old']);
  assert.match(unavailable(pair, candidates([], [{ image: 'only' }])), /Needs 2 images/);
});

test('options start at the table\'s defaults, and a proposal\'s are held to the table', () => {
  assert.deepEqual(defaults(KLING), { duration: '5' });                     // the required one is the person's to pick
  assert.deepEqual(settle(KLING, { effect_scene: 'bloom_bloom', duration: 10, colour: 'red' }),
    { duration: '10', effect_scene: 'bloom_bloom' });                       // legal values, as the table spells them
  assert.deepEqual(settle(KLING, { effect_scene: 'melt-it' }), { duration: '5' });
  assert.deepEqual(settle(KLING, null), { duration: '5' });
});

test('the card says what is still missing, the nearest thing first', () => {
  const start = begin(KLING, candidates(['/refs/a.jpg'], []), 'e1');
  assert.equal(missing(KLING, start), 'Pick a template');
  assert.equal(missing(KLING, { ...start, options: { ...start.options, effect_scene: 'bloom_bloom' } }), '');
  assert.equal(missing(KLING, { ...start, sources: [] }), 'Needs an image to work on');
  const edit = begin(EDIT, candidates(['/refs/a.jpg'], []), 'e2');
  assert.equal(missing(EDIT, edit), 'Say what to change');
  assert.equal(missing(EDIT, { ...edit, prompt: 'make it blue' }), '');
  const sound = begin(SOUND, candidates([], [{ clip: 'x', asset: 'gen:7' }]), 'e3');
  assert.equal(missing(SOUND, sound), 'Say what it should sound like');
  assert.equal(missing(SOUND, { ...sound, sources: [] }), 'Needs a clip to work on');
});

test('a new effect carries the brain\'s words only where the effect takes words', () => {
  const all = candidates(['/refs/a.jpg'], []);
  const edit = begin(EDIT, all, 'e1', { prompt: '  make the label blue ', options: { aspect_ratio: '1:1' } });
  assert.equal(edit.prompt, 'make the label blue');
  assert.deepEqual(edit.options, { aspect_ratio: '1:1' });
  assert.equal(begin(KLING, all, 'e2', { prompt: 'ignored' }).prompt, '');
  assert.deepEqual(requestOf({ ...edit, prompt: ' x ' }), {
    effect: 'nano-banana-edit', sources: ['/refs/a.jpg'], prompt: 'x', options: { aspect_ratio: '1:1' },
  });
});

test('names and values read as words, and a price is credits or says why it is not known', () => {
  assert.equal(optionLabel('effect_scene'), 'Template');
  assert.equal(optionLabel('camera_movement'), 'Camera move');
  assert.equal(optionLabel('some_new_option'), 'Some new option');
  assert.equal(valueLabel('effect_scene', 'bloom_bloom'), 'Bloom bloom');
  assert.equal(valueLabel('duration', '5'), '5s');
  assert.equal(valueLabel('upscale_factor', 2), '2x');
  assert.equal(valueLabel('upscale_factor', 1), 'Keep the size');
  assert.equal(valueLabel('target_fps', 60), '60 fps');
  assert.equal(valueLabel('subject_is_person', false), 'No');
  assert.equal(valueLabel('resolution', '1080p'), '1080p');
  assert.equal(takesLine(KLING), 'Up to 2 images in, a clip out');
  assert.equal(takesLine(SOUND), 'A clip in, a clip out');
  assert.equal(fromPrice(KLING, false), 'From 68 credits');
  assert.equal(fromPrice(KLING, true), '68 credits · not charged');
  assert.equal(fromPrice(SOUND, false), "Priced by the clip's length");
});

test('an action taken on one result is bound to THAT result, not to the newest', () => {
  const all = candidates(['/refs/attached.jpg'], [
    { image: '/renders/old.png', asset: 'gen:1' },
    { image: '/renders/new.png', asset: 'gen:2' },
  ]);
  // "Edit" under the older still: it is the source, though one is attached and one is newer
  const on = [candidateOf({ image: '/renders/old.png', asset: 'gen:1' }, 'this still')];
  const state = begin(EDIT, all, 'e1', { on });
  assert.deepEqual(state.sources.map((x) => x.ref), ['gen:1']);
  assert.equal(state.sources[0].from, 'this still');
  // a result that does not fit the effect is not forced onto it
  const clip = [candidateOf({ clip: '/renders/c.mp4', asset: 'gen:9' }, 'this clip')];
  assert.deepEqual(begin(EDIT, all, 'e2', { on: clip }).sources.map((x) => x.ref), ['/refs/attached.jpg']);
  // a still with no render id is named as the box holds it; a clip with none is no source
  assert.equal(candidateOf({ image: '/refs/x.jpg' }, 'this still').ref, '/refs/x.jpg');
  assert.equal(candidateOf({ clip: '/renders/c.mp4' }, 'this clip'), null);
  assert.equal(candidateOf({}, 'this still'), null);
});


test('a hook card carries its scene, and the scene never reaches the run', () => {
  const card = begin(KLING, candidates(['/refs/a.jpg'], []), 'h1', { hookFor: 42 });
  assert.equal(card.hookFor, 42);
  assert.equal('hookFor' in requestOf(card), false);
  assert.equal('hookFor' in begin(KLING, candidates(['/refs/a.jpg'], []), 'h2'), false);
});

// motion control (2026-11-14): a still of the character AND a clip, in that order
const MOTION = {
  id: 'motion-control', label: 'Motion control (Kling 3)', category: 'motion', blurb: 'moves',
  takes: 'image+video', output: 'video', sources: { min: 2, max: 2 }, prompt: 'optional', credits: null,
  options: {
    character_orientation: { values: ['image', 'video'], default: 'image', required: false },
    keep_original_sound: { values: [true, false], default: false, required: false },
  },
};

test('motion control binds a still then a clip, and says which half is missing', () => {
  const all = candidates(['/refs/jensen.jpg'], [
    { clip: 'https://r2/strut.mp4', asset: 'asset:12' },
    { image: 'https://r2/later.png', asset: 'gen:3' },
  ]);
  assert.deepEqual(sourcesFor(MOTION, all).map((c) => c.ref), ['/refs/jensen.jpg', 'asset:12']);
  assert.equal(unavailable(MOTION, all), '');
  const stillOnly = candidates(['/refs/jensen.jpg'], []);
  assert.equal(unavailable(MOTION, stillOnly), 'Needs a clip to copy the movement from');
  assert.equal(unavailable(MOTION, []), 'Needs a still of the character and a clip to copy');
  const half = begin(MOTION, stillOnly, 'fx1');
  assert.equal(missing(MOTION, half), 'Needs a clip to copy the movement from');
  // a clip acted on fills ITS half, the still stays
  const clip = { ref: 'asset:12', kind: 'clip', from: 'dropped · strut.mp4' };
  const both = begin(MOTION, half.sources, 'fx1', { on: [clip] });
  assert.deepEqual(requestOf(both).sources, ['/refs/jensen.jpg', 'asset:12']);
  assert.equal(missing(MOTION, both), '');
  assert.deepEqual(both.options, { character_orientation: 'image', keep_original_sound: false });
});

test('motion control reads as words', () => {
  assert.equal(takesLine(MOTION), "A still and a clip in, the still doing the clip's moves out");
  assert.equal(optionLabel('character_orientation'), 'Framing from');
  assert.equal(valueLabel('character_orientation', 'video'), 'The clip (up to 30s)');
  assert.equal(valueLabel('keep_original_sound', false), 'No');
});

test('a clip attached to the box is a clip source, ahead of the thread\'s clips', () => {
  const all = candidates(['/refs/jensen.jpg'], [{ clip: 'https://r2/made.mp4', asset: 'gen:4' }],
    [{ ref: 'asset:12', name: 'strut.mp4' }]);
  assert.deepEqual(all.map((c) => `${c.kind}:${c.ref}:${c.from}`),
    ['image:/refs/jensen.jpg:attached', 'clip:asset:12:attached', 'clip:gen:4:the last clip']);
  assert.deepEqual(sourcesFor(MOTION, all).map((c) => c.ref), ['/refs/jensen.jpg', 'asset:12']);
  assert.deepEqual(sourcesFor(SOUND, all).map((c) => c.ref), ['asset:12']);
});

test('motion control: attached photos after the first lock the face, and need the clip\'s framing', () => {
  const all = candidates(['/refs/stage.jpg', '/refs/headshot.jpg'], [], [{ ref: 'asset:12' }]);
  const fx = begin(MOTION, all, 'fx2');
  assert.deepEqual(requestOf(fx).sources, ['/refs/stage.jpg', 'asset:12', '/refs/headshot.jpg']);
  assert.deepEqual(facesOf(fx).map((c) => c.ref), ['/refs/headshot.jpg']);
  assert.equal(fx.options.character_orientation, 'video');        // turned on with the face lock
  assert.equal(missing(MOTION, fx), '');
  assert.equal(missing(MOTION, { ...fx, options: { ...fx.options, character_orientation: 'image' } }),
    'Face lock needs Framing from: the clip');
  // dropped in any order: a clip takes the clip's place, images fill still then faces
  const img = (ref) => ({ ref, kind: 'image', from: 'dropped' });
  const clip = { ref: 'asset:7', kind: 'clip', from: 'dropped' };
  let cur = addToPair([], [img('/a.jpg')]);
  cur = addToPair(cur, [img('/face1.jpg')]);
  cur = addToPair(cur, [clip]);
  cur = addToPair(cur, [img('/face1.jpg')]);                        // the same photo once
  assert.deepEqual(cur.map((c) => c.ref), ['/a.jpg', 'asset:7', '/face1.jpg']);
  for (const n of [2, 3, 4, 5]) cur = addToPair(cur, [img(`/f${n}.jpg`)]);
  assert.equal(cur.length, 6);                                      // still + clip + 4 faces at most
});
