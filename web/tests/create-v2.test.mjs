import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createElement as h } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  FOUNDING_500, INPUT_CHIPS, LAUNCH_SLIDES, LOOKS, NEW_TILES, SECTIONS, USE_CASE_TABS,
  continueCards, createV2On, effectsDoor, foundingLines, kitPalette, kitVars, madeFeed, personalRow, trendCards,
} from '../src/lib/create-v2.ts';
import { PLACEHOLDER } from '../src/lib/showcase.ts';
import { register } from 'node:module';

// the cards import their neighbours the way Next does (no extension):
// tests/_resolve-ts.mjs adds the ".ts" for node's loader
register('./_resolve-ts.mjs', import.meta.url);
const {
  ChipButton, ContinueCardView, EffectCardView, FoundingBannerView, LookCardView, MadeCardView, NewTileView,
  PersonalCardView, ShowcaseCard, TrendCardView, UseCaseCard, KitBadge,
} = await import('../src/components/studio/create-v2/cards.ts');

/* a priced effect off the table, exactly as GET /api/effects hands it */
const PRICED = {
  id: 'kling-effect', label: 'Kling effects', category: 'video_effect', blurb: 'templates on a still',
  takes: 'image', output: 'video', sources: { min: 1, max: 2 }, prompt: 'none', credits: 68,
  options: { effect_scene: { values: ['bullet_time_360'], default: null, required: true } },
};
const PRICED_ITEM = { ...PLACEHOLDER, credits: 87, model: 'LTX 2.3', gen_id: 'gen:12' };
const KIT = kitPalette({ id: 3, name: 'Gygler', palette: [
  { hex: '#F7931E', role: 'primary' }, { hex: '#0A2540', role: 'accent' }, { hex: '#FFF8EC', role: 'background' }, { hex: '#1A1A1A', role: 'text' },
] });
const noop = () => {};

/** every card, rendered with a priced fixture, with or without a kit */
function everyCard(kit) {
  const made = madeFeed([{ generated_id: 12, url: 'https://media/x.png', kind: 'image', prompt: 'a still', starred: true, model_label: 'FLUX' }])[0];
  const cont = continueCards([{ id: 1, title: 'Headphones', brief: 'An ad', updated_at: '2026-10-21' }], [])[0];
  const trend = trendCards({ days: 7, since: '', scope: 'account', effects: [{ effect: 'kling-effect', label: 'Kling effects', runs: 3, kept: 1 }], briefs: [], events: { kept: 1, discarded: 0, edited: 0 } })[0];
  const personal = personalRow([{ id: 1, title: 'Headphones', brief: 'An ad for headphones', look: 'noir' }]).cards[0];
  return {
    chip: h(ChipButton, { chip: INPUT_CHIPS[0], onPick: noop }),
    continue: h(ContinueCardView, { card: cont, kit }),
    showcase: h(ShowcaseCard, { title: LAUNCH_SLIDES[0].title, line: LAUNCH_SLIDES[0].line, item: PRICED_ITEM, kit, onPick: noop }),
    usecase: h(UseCaseCard, { card: USE_CASE_TABS[0].cards[0], item: PRICED_ITEM, kit, onPick: noop }),
    trend: h(TrendCardView, { card: trend, kit, onPick: noop }),
    personal: h(PersonalCardView, { card: personal, kit, onPick: noop }),
    look: h(LookCardView, { look: LOOKS[0], item: PRICED_ITEM, kit, onPick: noop }),
    effect: h(EffectCardView, { effect: PRICED, kit, onPick: noop }),
    tile: h(NewTileView, { tile: NEW_TILES[0], item: PRICED_ITEM, kit }),
    founding: h(FoundingBannerView, { kit }),
    made: h(MadeCardView, { card: made, kit, onRemix: noop }),
  };
}

test('no card shows a price: no "credit" and no price number, handed a priced effect and a priced showcase item', () => {
  for (const [name, el] of Object.entries(everyCard(null))) {
    const html = renderToStaticMarkup(el);
    assert.ok(html.length > 20, name);
    // the Founding banner is the one card that may say "credits": its
    // sign-up GRANT (lib/create-v2 FOUNDING_500, a placeholder Mike edits),
    // never a price -- the next test pins that
    if (name !== 'founding') assert.doesNotMatch(html, /credit/i, `${name} says credits`);
    assert.doesNotMatch(html, /\b(68|87)\b/, `${name} shows the fixture's price`);
    assert.doesNotMatch(html, /\$\s?\d/, `${name} shows dollars`);
    assert.doesNotMatch(html, /\d+\s*credits?\s+(each|per|for)/i, `${name} prices something`);
  }
});

test('the Founding banner prints its placeholder numbers and nothing else prices anything', () => {
  // the one place a number is drawn on purpose: the offer Mike edits in lib/create-v2
  const html = renderToStaticMarkup(h(FoundingBannerView, {}));
  const lines = foundingLines(FOUNDING_500);
  assert.ok(html.includes(lines.title) && html.includes(`${FOUNDING_500.signupCredits} credits on sign-up`));
  assert.equal(FOUNDING_500.placeholder, true, 'the numbers are placeholders until Mike sets them');
  assert.equal(FOUNDING_500.seats, 500);
});

test('the kit colour is on a card only with a kit, scoped to that card', () => {
  const withKit = everyCard(KIT);
  const without = everyCard(null);
  for (const name of Object.keys(withKit)) {
    if (name === 'chip') continue;
    const on = renderToStaticMarkup(withKit[name]);
    const off = renderToStaticMarkup(without[name]);
    assert.ok(on.includes('--kit-primary:#F7931E'), `${name} with a kit carries the primary`);
    assert.ok(on.includes('--kit-accent:#0A2540') && on.includes('--kit-background:#FFF8EC') && on.includes('--kit-text:#1A1A1A'), name);
    assert.ok(on.includes('Kit: Gygler') && on.includes('class="cv2-card kit'), `${name} wears the badge`);
    assert.ok(!off.includes('kit-') && !off.includes('#F7931E') && !off.includes('Gygler'), `${name} without a kit has no kit colour`);
    assert.ok(off.includes('class="cv2-card '), name);
  }
  assert.equal(renderToStaticMarkup(h(KitBadge, { kit: null })), '');
  // a role the kit did not fill is left to the studio's palette
  assert.deepEqual(kitVars(kitPalette({ id: 1, name: 'Bare', palette: [{ hex: '#111111', role: 'primary' }] })), { '--kit-primary': '#111111' });
  assert.deepEqual(kitVars(null), {});
  assert.equal(kitPalette(null), null);
});

test('the flag is a strict true, and with it off the page keeps its old tree', () => {
  assert.equal(createV2On({ create_v2: true }), true);
  for (const caps of [{}, { create_v2: false }, { create_v2: 'yes' }, null, undefined]) assert.equal(createV2On(caps), false);
  // the page's ONE branch: a null when the flag is off, nothing else of
  // this feature in the file, so the flag-off render is the pre-change render
  const page = readFileSync(new URL('../src/app/studio/page.tsx', import.meta.url), 'utf8');
  const code = page.replace(/\{\/\*[\s\S]*?\*\/\}/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
  assert.equal((code.match(/import \{ CreateV2 \}/g) ?? []).length, 1, 'imported once');
  assert.equal((code.match(/caps\.create_v2 === true \?/g) ?? []).length, 1, 'tested once');
  assert.equal((code.match(/<CreateV2\b/g) ?? []).length, 1, 'drawn once');
  assert.equal((code.match(/CreateV2|create_v2/g) ?? []).length, 3, 'and nothing else of it in the page');
  assert.match(page, /\{caps\.create_v2 === true \? \(\s*<CreateV2/);
  assert.match(page, /<\/CreateV2>|\/>\s*\) : null\}/);
  const section = page.slice(page.indexOf('{caps.create_v2 === true'), page.indexOf(') : null}', page.indexOf('{caps.create_v2 === true')));
  assert.ok(!/send\(|approve|runEffect|runImage|runScenes/.test(section), 'the branch hands over fills and doors, never a send');
});

test('the sections are the ten the brief lists, in order', () => {
  assert.deepEqual([...SECTIONS], ['vesper', 'continue', 'launch', 'usecases', 'trending', 'personal', 'effects', 'new', 'founding', 'made']);
  assert.deepEqual(INPUT_CHIPS.map((c) => c.label), ['Idea', 'Script', 'Product URL', 'Image', 'Clip']);
  assert.deepEqual(USE_CASE_TABS.map((t) => t.label), ['Marketing', 'Social', 'Film', 'Business']);
  for (const t of USE_CASE_TABS) for (const c of t.cards) assert.ok(c.brief.length > 20 && c.showcase, c.id);
  // Kling 4.0 leads the tiles since 2026-10-22, the day fal's API opened
  assert.deepEqual(NEW_TILES.map((t) => t.id), ['kling4', 'mcp_claude', 'brand_kit', 'discord', 'models']);
  assert.equal(LAUNCH_SLIDES.length, 3);
  assert.equal(effectsDoor({ effects_tab: true }), 'tab');
  assert.equal(effectsDoor({}), 'gallery');
});

test('continue, personal and made rows come from the account\'s own lists and hide when empty', () => {
  assert.deepEqual(continueCards([], []), []);
  assert.equal(personalRow([]), null);
  assert.deepEqual(madeFeed([]), []);
  const projects = [
    { id: 1, title: 'Old', updated_at: '2026-10-01', brief: 'first' },
    { id: 2, title: 'Headphones', updated_at: '2026-10-21', brief: 'A product ad for headphones\nmore' },
    { id: 3, title: 'Gone', updated_at: '2026-10-22', archived: true },
  ];
  const media = [
    { generated_id: 7, url: 'https://media/clip.mp4', kind: 'video', poster: 'https://media/p.jpg', prompt: 'a clip' },
    { generated_id: 8, url: 'https://media/still.png', kind: 'image', thumb: 'https://media/t.png', prompt: 'a still', starred: true },
    { url: 'https://media/noid.png', kind: 'image' },
  ];
  const cont = continueCards(projects, media);
  assert.deepEqual(cont.map((c) => [c.kind, c.title, c.href]), [['project', 'Headphones', '/studio/projects/2'], ['render', 'Your last clip', '/studio/assets?open=7']]);
  const personal = personalRow(projects);
  assert.equal(personal.because, 'Because you made Headphones…');
  assert.equal(personal.cards.length, 3);
  assert.ok(personal.cards.every((c) => c.brief.includes('Headphones') && c.brief.includes('A product ad for headphones')));
  const made = madeFeed(media);
  assert.deepEqual(made.map((m) => [m.id, m.starred, m.thumb]), [[8, true, 'https://media/t.png'], [7, false, 'https://media/p.jpg']]);
});

test('trend cards count runs and scenes, never credits', () => {
  const cards = trendCards({ days: 7, since: '', scope: 'account',
    effects: [{ effect: 'add-sound', label: 'Add sound', runs: 2, kept: 2 }, { effect: 'upscale', label: 'Upscale', runs: 1, kept: 0 }],
    briefs: [{ text: 'A product ad for the headphones', count: 2, concept_id: 40 }],
    events: { kept: 2, discarded: 0, edited: 0 } });
  assert.deepEqual(cards.map((c) => [c.kind, c.label, c.note]), [
    ['effect', 'Add sound', '2 runs this week · 2 kept'],
    ['effect', 'Upscale', '1 run this week'],
    ['brief', 'A product ad for the headphones', '2 scenes this week'],
  ]);
  assert.deepEqual(trendCards(null), []);
});
