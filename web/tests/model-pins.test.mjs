// The model pickers (2026-11-02, Mike picked "08 · Pinned chips + sheet"):
// the Image, Video and Voice pages pick their model from a row of starred
// chips and an "All models" list, each model wearing its maker's logo, and
// Create has no model picker at all -- Vesper chooses there. Read as source.
import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const strip = (code) =>
  code
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");

test("the picker shows no price and spends nothing", () => {
  const code = strip(src("../src/components/studio/model-pins.tsx"));
  assert.doesNotMatch(code, /credits|quote|approve|apiFetch/i);
});

test("the Image, Video and Voice pages use the starred-chips picker", () => {
  const direct = src("../src/components/studio/direct-generator.tsx");
  for (const kind of ["image", "video"]) assert.match(direct, new RegExp(`<ModelPins\\s+kind="${kind}"`));
  assert.match(src("../src/components/studio/voice-tab.tsx"), /<ModelPins\s+kind="voice"/);
});

test("every logo the picker names is a file it can load", () => {
  const code = src("../src/components/studio/model-pins.tsx");
  const rules = code.slice(code.indexOf("const rules"), code.indexOf("return rules.find"));
  const keys = [...rules.matchAll(/, "([a-z]+)"\]/g)].map((m) => m[1]);
  assert.ok(keys.length >= 10);
  for (const k of keys) assert.ok(existsSync(new URL(`../public/model-logos/${k}.svg`, import.meta.url)), k);
});

test("Create has no model picker: Vesper chooses the model", () => {
  const view = strip(src("../src/app/studio/(create)/create-view.tsx"));
  assert.doesNotMatch(view, /Which model draws|Which model renders/);
  assert.doesNotMatch(view, /saveImageModel|saveVideoModel/);
});
