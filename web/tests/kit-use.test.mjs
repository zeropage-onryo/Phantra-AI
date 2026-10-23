import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kitDoors, kitHref, kitParam, kitStarters } from '../src/lib/kit-use.ts';

const kit = { id: 7, name: 'Gygler' };
const q = (href) => new URL(href, 'https://x').searchParams;

test('every Use kit item is a Create link with the kit on', () => {
  for (const use of [...kitDoors(kit), ...kitStarters(kit)]) {
    assert.ok(use.href.startsWith('/studio?'), use.id);
    assert.equal(q(use.href).get('kit'), '7', use.id);
  }
});

test('the doors set the output and type nothing', () => {
  const [agent, image, video] = kitDoors(kit);
  assert.equal(q(agent.href).get('kind'), null);
  assert.equal(q(image.href).get('kind'), 'image');
  assert.equal(q(video.href).get('kind'), 'video');
  for (const d of [agent, image, video]) assert.equal(q(d.href).get('spark'), null);
});

test('a starter types a first line naming the brand, on the right output and frame', () => {
  const [ad, social, hero] = kitStarters(kit);
  assert.equal(q(ad.href).get('kind'), 'video');
  assert.match(q(ad.href).get('spark'), /Gygler/);
  assert.equal(q(social.href).get('frame'), '4:5');
  assert.equal(q(hero.href).get('frame'), '16:9');
  assert.equal(q(hero.href).get('kind'), 'image');
});

test('a kit name with symbols survives the link', () => {
  const href = kitHref({ id: 2, name: 'A&B' }, { spark: 'An A&B ad: ' });
  assert.equal(q(href).get('spark'), 'An A&B ad: ');
});

test('kitParam reads only a positive whole id', () => {
  const p = (s) => new URLSearchParams(s);
  assert.equal(kitParam(p('kit=4')), 4);
  assert.equal(kitParam(p('kit=0')), 0);
  assert.equal(kitParam(p('kit=-2')), 0);
  assert.equal(kitParam(p('kit=1.5')), 0);
  assert.equal(kitParam(p('kit=x')), 0);
  assert.equal(kitParam(p('')), 0);
});
