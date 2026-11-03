// /pricing sells plans, not a model list (Mike, 2026-11-03: "i dont think i
// need to show all the models available like that in a pricing plan").
// The 13-row "What a month buys." table is gone: each plan card already
// says the range, from the cheapest model to the dearest, and each model's
// price is on its own page under /models. Read as source.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const pricing = src("../src/app/pricing/page.tsx");

test("/pricing has no per-model table", () => {
  assert.doesNotMatch(pricing, /MODELS\.map/);
  assert.doesNotMatch(pricing, /<table/);
  assert.doesNotMatch(pricing, /id="models"/);
  assert.doesNotMatch(pricing, /What a month buys/);
});

test("each plan card still says what a month buys, cheapest to dearest", () => {
  const cards = src("../src/components/site/plan-cards.tsx");
  assert.match(cards, /≈ \{clipsPerMonth\(plan, cheapest\)\} × \{CATALOG\.clip_seconds\}s on \{cheapest\.name\}, or/);
  assert.match(cards, /\{clipsPerMonth\(plan, dearest\)\} on \{dearest\.name\}\./);
});

test("the credits answer points at the model pages, not a table that is gone", () => {
  assert.doesNotMatch(pricing, /table above/);
  assert.match(pricing, /<Link href="\/models">/);
});

test("/models sends people to the plans, not to an anchor that is gone", () => {
  const models = src("../src/app/models/page.tsx");
  assert.doesNotMatch(models, /pricing#models/);
  assert.match(models, /<Link href="\/pricing" \/>/);
});

test("the credits answer keeps its spaces (it read 'and a5-second Veo clip')", () => {
  // JSX drops a line break between text and an expression: the space has to be written
  assert.doesNotMatch(pricing, /and a\n\s*\{CATALOG\.clip_seconds\}/);
  assert.match(pricing, /and a\{" "\}\n\s*\{CATALOG\.clip_seconds\}-second Veo clip/);
});
