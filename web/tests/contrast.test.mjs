// The axe findings on the new pages (QA 2026-11-02 T14): small labels in
// --dimmer (#55534f, 2.38:1 on the panels), yellow buttons whose black text
// lost to `.zps button/a { color: inherit }`, a link told from its sentence
// by colour alone, and a scrolling grid no keyboard could reach. Read as
// source: which rule paints what.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const rule = (css, sel) => {
  const i = css.indexOf(`\n${sel} {`);
  assert.ok(i >= 0, `no rule ${sel}`);
  return css.slice(i, css.indexOf("}", i));
};

test("labels are read in --dim, never --dimmer", () => {
  const dg = src("../src/components/studio/direct-generator.css");
  for (const sel of [".dg .dg-lab", ".dg .dg-count", ".dg .dg-menu-title", ".dg .dg-empty small"]) {
    assert.doesNotMatch(rule(dg, sel), /--dimmer/, sel);
  }
  const as = src("../src/components/studio/ads/ad-studio.css");
  for (const sel of [".as .as-lab", ".as .as-step h2 span", ".as .as-table thead th"]) {
    assert.doesNotMatch(rule(as, sel), /--dimmer/, sel);
  }
  // a chosen format's blurb sits on a yellow-tinted card: one step brighter
  assert.match(rule(as, '.as .as-format[aria-checked="true"] .as-format-blurb'), /color: var\(--bone-2\)/);
});

test("a link inside a sentence is underlined, not only coloured", () => {
  assert.match(rule(src("../src/components/studio/direct-generator.css"), ".dg .dg-hint a"), /text-decoration: underline/);
});

test("yellow buttons keep black text against the studio's colour reset", () => {
  const css = src("../src/app/studio/studio.css");
  assert.match(rule(css, ".zps .zplug-get-btn"), /color: var\(--on-signal\)/);
  const cal = src("../src/components/studio/calendar/calendar.css");
  assert.match(rule(cal, ".zps .cal-primary"), /color: var\(--on-signal\)/);
});

test("the calendar's scrolling week can be reached by keyboard", () => {
  const files = ["calendar.tsx"].map((f) => {
    try { return src(`../src/components/studio/calendar/${f}`); } catch { return ""; }
  }).join("\n");
  assert.match(files, /className="cal-week-body"[^>]*tabIndex=\{0\}/);
});

test("the brand page's labels and the canvas's save note are in --dim", () => {
  assert.doesNotMatch(rule(src("../src/app/studio/brand/brand.css"), ".bk .bk-lab"), /--dimmer/);
  assert.doesNotMatch(rule(src("../src/components/flows/flows.css"), ".save-indicator"), /--dimmer/);
});

test("a kit card is not a button with buttons inside it", () => {
  // axe nested-interactive: the card was role=button around Use, Duplicate
  // and Delete. The card opens from a real button on its name instead.
  const page = src("../src/app/studio/brand/page.tsx");
  const card = page.slice(page.indexOf("function KitCard"), page.indexOf("</article>"));
  assert.doesNotMatch(card, /role="button"/);
  assert.match(card, /<button[^>]*className="bk-card-open"/);
  assert.match(rule(src("../src/app/studio/brand/brand.css"), ".bk .bk-card-open::after"), /inset: 0/);
});

test("the editor's empty-frame note is readable and its timeline reachable by keyboard", () => {
  assert.doesNotMatch(rule(src("../src/components/cut/cut.css"), ".cx-frame .cx-empty-frame"), /--dimmer/);
  assert.match(src("../src/components/cut/timeline.tsx"), /className="cx-scroll"[^>]*tabIndex=\{0\}/);
});
