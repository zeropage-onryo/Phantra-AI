// /pricing's "What a month buys." table on a phone (QA 2026-11-02 P9 / M1):
// at 390px the table is 640px in a 342px box, so Standard, Pro and Max sat
// off-screen with no cue, and the box could not be scrolled from a keyboard
// (axe serious, scrollable-region-focusable). Read as source.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../src/app/pricing/page.tsx", import.meta.url), "utf8");
const section = page.slice(page.indexOf('id="models"'), page.indexOf("</section>", page.indexOf('id="models"')));

test("the table's scroll box is a labelled region a keyboard can focus", () => {
  const box = section.match(/<div[^>]*overflow-x-auto[^>]*>/)?.[0] ?? "";
  assert.match(box, /tabIndex=\{0\}/);
  assert.match(box, /role="region"/);
  assert.match(box, /aria-label="Clips a month on each model, by plan"/);
  // a visible focus ring, since the box now takes focus
  assert.match(box, /focus-visible:outline/);
});

test("a phone is told the plans are to the side, and only a phone", () => {
  const cue = section.match(/<p[^>]*sm:hidden[^>]*>[\s\S]*?<\/p>/)?.[0] ?? "";
  assert.ok(cue, "a cue hidden from sm up");
  assert.match(cue, /Swipe/);
  for (const plan of ["Standard", "Pro", "Max"]) assert.match(cue, new RegExp(plan));
  // readable: not the 4.46:1 grey the QA flagged on /mcp (P10)
  assert.doesNotMatch(cue, /#82807d/);
});

test("the model column stays put while the plans swipe under it", () => {
  const firstHead = section.match(/<th[^>]*>\s*Model\s*<\/th>/)?.[0] ?? "";
  assert.match(firstHead, /sticky left-0/);
  const firstCell = section.slice(section.indexOf("<tbody>")).match(/<td[^>]*>/)?.[0] ?? "";
  assert.match(firstCell, /sticky left-0/);
  // an opaque fill, or the swiped columns show through it
  assert.match(firstHead, /bg-background/);
  assert.match(firstCell, /bg-background/);
});

test("on a phone the tier sits under the model's name, so the fixed column stays narrow", () => {
  // side by side, the column took 243 of the box's 342px and left room for one plan
  assert.match(section, /<span className="ml-2 text-\[12px\] text-\[#82807d\] max-sm:ml-0 max-sm:block">\{TIER_LABEL\[m\.tier\]\}<\/span>/);
});

test("on a phone the table is as wide as its content, so no column is padded out", () => {
  // min-w-[640px] spread the spare width into every column, the fixed one too
  assert.match(section, /<table className="w-full min-w-\[640px\] border-collapse text-left text-sm max-sm:w-max max-sm:min-w-0">/);
});
