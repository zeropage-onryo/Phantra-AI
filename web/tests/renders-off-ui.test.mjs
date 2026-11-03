// Renders is off the UI for now (Mike, 2026-11-03): no top-bar entry
// (#562), no ⌘K page, no "Open Renders" button. The page still answers at
// its address, and a draft's Finish link stays, because Renders is the only
// place a draft is finished. Read as source, like the other shell tests.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const strip = (code) =>
  code
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");

test("the flag is off", () => {
  assert.match(src("../src/lib/renders-flag.ts"), /export const RENDERS_IN_UI = false;/);
});

test("⌘K lists the Renders page only with the flag on", () => {
  const code = strip(src("../src/components/studio/command-palette.tsx"));
  assert.match(code, /\.\.\.\(RENDERS_IN_UI \? \[page\("Renders", "\/studio\/renders"/);
  assert.doesNotMatch(code.replace(/\.\.\.\(RENDERS_IN_UI \? \[page\("Renders"[^\n]*/, ""), /"\/studio\/renders"/);
});

test("the editor's empty state has no Open Renders button with the flag off", () => {
  const code = strip(src("../src/app/studio/cut/page.tsx"));
  assert.match(code, /RENDERS_IN_UI && !fresh\.length \?/);
});

test("a draft can still be finished: the viewer keeps its one link to Renders", () => {
  const code = strip(src("../src/components/studio/asset-viewer.tsx"));
  assert.match(code, /<Link href="\/studio\/renders" className="av-lnk">\s*Finish it on Renders/);
});

test("the page still answers at its address", () => {
  assert.match(strip(src("../src/components/studio/shell.tsx")), /\["\/studio\/renders", "renders"\]/);
  assert.match(src("../src/app/studio/queue/page.tsx"), /redirect\("\/studio\/renders"\)/);
});
