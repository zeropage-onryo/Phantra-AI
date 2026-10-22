import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createElement as h } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  FOUNDING_500, INPUT_CHIPS, LAUNCH_SLIDES, LOOKS, PROMO, SECTIONS, TOOL_TILES, USE_CASE_TABS,
  continueCards, createV2On, effectsDoor, foundingLines, kitPalette, kitVars, madeFeed, personalRow, popularEffect,
} from '../src/lib/create-v2.ts';
import { PLACEHOLDER } from '../src/lib/showcase.ts';
import { register } from 'node:module';

// the cards import their neighbours the way Next does (no extension):
// tests/_resolve-ts.mjs adds the ".ts" for node's loader
register('./_resolve-ts.mjs', import.meta.url);
const {
  ChipButton, ContinueCardView, EffectTileView, FoundingBannerView, LookCardView, MadeCardView, PromoView,
  PersonalCardView, ShowcaseCard, ToolTileView, UseCaseCard, KitBadge, Tag,
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
  const personal = personalRow([{ id: 1, title: 'Headphones', brief: 'An ad for headphones', look: 'noir' }]).cards[0];
  return {
    chip: h(ChipButton, { chip: INPUT_CHIPS[0], onPick: noop }),
    continue: h(ContinueCardView, { card: cont, kit }),
    // EVERY slide, use-case card, look and tile, not the first of each: the
    // words on a card are data in lib/create-v2, and one of them once said
    // "credits" where the test never looked (review of #448, 2026-10-22)
    ...Object.fromEntries(LAUNCH_SLIDES.map((s, i) => [`showcase-${s.id ?? i}`,
      h(ShowcaseCard, { title: s.title, line: s.line, item: PRICED_ITEM, kit, onPick: noop })])),
    ...Object.fromEntries(USE_CASE_TABS.flatMap((t) => t.cards.map((c) => [`usecase-${t.id}-${c.id}`,
      h(UseCaseCard, { card: c, item: PRICED_ITEM, kit, onPick: noop })]))),
    personal: h(PersonalCardView, { card: personal, kit, onPick: noop }),
    ...Object.fromEntries(LOOKS.map((l) => [`look-${l.id}`, h(LookCardView, { look: l, item: PRICED_ITEM, kit, onPick: noop, tag: 'POPULAR' })])),
    effect: h(EffectTileView, { effect: PRICED, item: PRICED_ITEM, kit, onPick: noop, tag: 'FREE' }),
    promo: h(PromoView, { promo: PROMO, item: PRICED_ITEM, kit, onPick: noop }),
    ...Object.fromEntries(TOOL_TILES.map((t) => [`tool-${t.id}`, h(ToolTileView, { tile: t, kit, onPick: noop })])),
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
  // the composer's ONE branch: a null when the flag is off. Since 2026-10-22
  // the composer is app/studio/(create)/create-view.tsx (drawn by the
  // (create) layout on /studio and /studio/chat); the flag is read three
  // times more there, all for the home's own layout (the box near the top,
  // no pinned hint, the chips instead of the starters), never to draw anything of the sections
  const page = readFileSync(new URL('../src/app/studio/(create)/create-view.tsx', import.meta.url), 'utf8');
  const code = page.replace(/\{\/\*[\s\S]*?\*\/\}/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
  assert.equal((code.match(/import \{ CreateV2 \}/g) ?? []).length, 1, 'imported once');
  assert.equal((code.match(/\{caps\.create_v2 === true \? \(/g) ?? []).length, 1, 'branched once');
  assert.equal((code.match(/<CreateV2\b/g) ?? []).length, 1, 'drawn once');
  assert.equal((code.match(/homePage && caps\.create_v2 === true/g) ?? []).length, 3, 'the home layout reads the flag');
  assert.equal((code.match(/CreateV2|create_v2/g) ?? []).length, 6, 'and nothing else of it in the page');
  // drawn on the home only: the chat page (/studio/chat) is the thread
  assert.match(page, /\{caps\.create_v2 === true \? \(\s*\/\/[^\n]*\n\s*homePage \? \(\s*<CreateV2/);
  assert.match(page, /<\/CreateV2>|\/>\s*\) : null\}/);
  const section = page.slice(page.indexOf('{caps.create_v2 === true'), page.indexOf(') : null}', page.indexOf('{caps.create_v2 === true')));
  assert.ok(!/send\(|approve|runEffect|runImage|runScenes/.test(section), 'the branch hands over fills and doors, never a send');
});

test('the sections are the seven of the Runway / Higgsfield pass, in order', () => {
  assert.deepEqual([...SECTIONS], ['vesper', 'launch', 'promo', 'usecases', 'work', 'effects', 'made']);
  assert.deepEqual(INPUT_CHIPS.map((c) => c.label), ['Idea', 'Script', 'Product URL', 'Image', 'Clip']);
  assert.deepEqual(USE_CASE_TABS.map((t) => t.label), ['Marketing', 'Social', 'Film', 'Business']);
  for (const t of USE_CASE_TABS) for (const c of t.cards) assert.ok(c.brief.length > 20 && c.showcase, c.id);
  // one promo (Kling 4.0, the day fal's API opened) and six tool tiles
  assert.equal(PROMO.id, 'kling4');
  assert.ok(PROMO.fill.length > 10 && PROMO.cta && PROMO.showcase);
  assert.deepEqual(TOOL_TILES.map((t) => t.id), ['talking_photo', 'final_cut', 'brand_kit', 'mcp_claude', 'elements', 'discord']);
  // every tile does exactly one thing: a link, a fill or the talking-photo card
  for (const t of TOOL_TILES) assert.equal([t.href, t.fill, t.talk].filter(Boolean).length, 1, t.id);
  for (const t of TOOL_TILES) assert.ok(!t.tag || t.tag === 'NEW' || t.tag === 'FREE', t.id);
  // four highlight tiles since the visuals pass (2026-10-22): the fourth is the effects
  assert.equal(LAUNCH_SLIDES.length, 4);
  for (const s of LAUNCH_SLIDES) assert.ok(s.eyebrow && s.showcase, s.id);
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
  const personal = personalRow(projects, media);
  assert.equal(personal.because, 'Because you made Headphones…');
  assert.equal(personal.cards.length, 3);
  assert.ok(personal.cards.every((c) => c.brief.includes('Headphones') && c.brief.includes('A product ad for headphones')));
  // the card shows a short line, never the brief (a brief is the person's own notes, and long)
  assert.ok(personal.cards.every((c) => c.line && !c.line.includes('headphones')));
  // the picture behind it: the project's cover, else the newest render's
  assert.ok(personal.cards.every((c) => c.thumb === 'https://media/p.jpg'));
  const html = renderToStaticMarkup(h(PersonalCardView, { card: personal.cards[0], onPick: noop }));
  assert.ok(!html.includes('A product ad for headphones</'), 'the brief is not drawn');
  const made = madeFeed(media);
  assert.deepEqual(made.map((m) => [m.id, m.starred, m.thumb]), [[8, true, 'https://media/t.png'], [7, false, 'https://media/p.jpg']]);
});

test('POPULAR is the week\'s most-run effect among the ones the strip shows, and the tags are words', () => {
  const week = { days: 7, since: '', scope: 'account',
    effects: [{ effect: 'voice-eleven-v3', label: 'voice-eleven-v3', runs: 9, kept: 0 }, { effect: 'noir', label: 'Noir', runs: 3, kept: 1 }, { effect: 'crash_zoom', label: 'Crash-Zoom', runs: 4, kept: 0 }],
    briefs: [], events: { kept: 1, discarded: 0, edited: 0 } };
  // an effect the strip never draws (the raw id the old row printed) is not a candidate
  assert.equal(popularEffect(week, LOOKS.map((l) => l.id)), 'crash_zoom');
  assert.equal(popularEffect(week, ['noir']), 'noir');
  assert.equal(popularEffect(week, ['add-sound']), null);
  assert.equal(popularEffect(null, ['noir']), null);
  assert.equal(renderToStaticMarkup(h(Tag, { tag: null })), '');
  assert.match(renderToStaticMarkup(h(Tag, { tag: 'POPULAR' })), /class="cv2-tag t-popular">POPULAR</);
});
