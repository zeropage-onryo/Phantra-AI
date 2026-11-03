// Words meant for the operator, on screens a customer reads (QA 2026-11-02
// T17). Read as source: the strings, not the logic.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
// what reaches the screen: comments out
const shown = (p) =>
  src(p)
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");

test("no RAG shelf and no Queue on a customer's screen", () => {
  for (const p of [
    "../src/components/studio/add-element.tsx",
    "../src/app/studio/elements/page.tsx",
    "../src/components/cut/left-panel.tsx",
  ]) {
    const code = shown(p);
    assert.doesNotMatch(code, /RAG|searchable chunk/, p);
    assert.doesNotMatch(code, /in the Queue/, p);
  }
});

test("a missing scene offers Sign in only to someone signed out", () => {
  const code = shown("../src/components/flows/flow-workspace.tsx");
  assert.match(code, /\{signedOut \? <button onClick=\{\(\) => goToSignIn\(\)\}>Sign in<\/button> : null\}/);
  assert.match(code, /setSignedOut\(error instanceof ApiError && error\.status === 401\)/);
  assert.doesNotMatch(code, /no such concept/);
});
