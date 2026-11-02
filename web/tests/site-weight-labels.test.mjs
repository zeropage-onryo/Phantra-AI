// The public site, QA 2026-11-02 (01 P3-P8, 02 T8): the home names only
// models Phantra offers, by their catalogue names; a fan hero plays one
// clip, not four; and a keyboard user can see where focus is.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const catalog = JSON.parse(read('content/pricing.json'));
const VIDEO = catalog.models.map((m) => m.name);

test('the home reel tags only catalogue models', () => {
  const reel = read('content/hero-reel.ts');
  assert.doesNotMatch(reel, /Runway|Seedance 2 Fast/);
  const tags = [...reel.matchAll(/,\s*"([^"]+)",\s*[01]\)/g)].map((m) => m[1]);
  assert.ok(tags.length > 5);
  for (const t of tags) assert.ok(VIDEO.includes(t), `${t} is not a catalogue model`);
  const literal = [...reel.matchAll(/model:\s*"([^"]+)"/g)].map((m) => m[1]);
  for (const t of literal) assert.ok(VIDEO.includes(t), `${t} is not a catalogue model`);
});

test('the models strip is read off the catalogue, not typed', () => {
  const src = read('components/landing/vesper-content.ts');
  const strip = src.slice(src.indexOf('export const STRIP_MODELS'));
  assert.doesNotMatch(strip.split(';')[0], /"Kling 3"|"FLUX.2"|"GPT Image 2"/);
  assert.match(strip.split(';')[0], /MODELS/);
  assert.match(strip.split(';')[0], /IMAGE_MODELS/);
});

test('a fan hero plays one clip; the others are stills', () => {
  const hero = read('landing-pages/components/make-hero.tsx');
  assert.match(hero, /function Media\([^)]*still/);
  const fan = hero.slice(hero.indexOf('function FanHero'), hero.indexOf('function ReelHero'));
  assert.match(fan, /<Media[^>]*still=\{i !== 1\}/);
});

test('the site header shows a focus ring, never the red one', () => {
  const header = read('components/site-header.tsx');
  // every control (a hover state says it is one; the popups that take focus
  // when they open are not)
  const controls = header.split('\n').filter((l) => l.includes('outline-none') && l.includes('hover:'));
  assert.ok(controls.length >= 10);
  for (const line of controls) {
    assert.match(line, /focus-visible:ring-/, line.trim().slice(0, 90));
    assert.doesNotMatch(line, /ring-ring/, line.trim().slice(0, 90));
  }
});

test('the composer box shows where focus is', () => {
  const css = read('components/studio/composer/composer.css');
  assert.match(css, /\.zc \.zc-box:has\(textarea:focus-visible\)\s*\{[^}]*outline:\s*2px solid/);
});
