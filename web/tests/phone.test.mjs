// The phone's studio (2026-10-26, Mike's "Phantra Mobile Studio" canvas):
// the shell's phone chrome, the compose page, the model sheet and the
// sign-up sheet a signed-out send opens. Read as source, like the other
// shell tests: these are layout rules and doors, not logic to run.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const strip = (code) =>
  code
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");

test("the bottom bar is Home, Assets, Create, Effects, Profile, in that order", () => {
  const code = strip(src("../src/components/studio/phone/phone-chrome.tsx"));
  const bar = code.slice(code.indexOf("export function PhoneTabs"), code.indexOf("export function PhoneMenu"));
  const order = [...bar.matchAll(/tab\("(\w+)"|className="ph-create"/g)].map((m) => m[1] ?? "create");
  assert.deepEqual(order, ["home", "assets", "create", "effects", "profile"]);
  // Create is the compose page; Effects follows the flag (the page, else the gallery)
  assert.match(code, /export const COMPOSE_HREF = "\/studio\/new";/);
  assert.match(code, /effectsDoor\(caps\) === "tab" \? EFFECTS_TAB_HREF : `\$\{COMPOSE_HREF\}\?open=effects`/);
});

test("the top bar is the menu on the left, then the logo, and nothing else", () => {
  const code = strip(src("../src/components/studio/phone/phone-chrome.tsx"));
  const top = code.slice(code.indexOf("export function PhoneTop"), code.indexOf("const Star"));
  assert.ok(top.indexOf('aria-label="Menu"') < top.indexOf('className="ph-logo"'), "menu before logo");
  assert.doesNotMatch(top, /Credit|balance|Search|ActivityTray/);
});

test("the phone chrome is drawn only under 720px, and the desktop rail and header step aside there", () => {
  const css = src("../src/components/studio/phone/phone.css");
  assert.match(css, /^\.ph-top,\n\.ph-tabs,\n\.ph-menu \{\n  display: none;/m);
  const studio = src("../src/app/studio/studio.css");
  const block = studio.slice(studio.indexOf("THE PHONE, 2026-10-26"));
  assert.match(block, /\.zps \.rail,[\s\S]*?display: none;/);
  assert.match(block, /\.zps \.bar\.hdr \{\s*display: none;/);
});

test("a signed-out send opens the sign-up sheet and asks the server nothing", () => {
  const code = strip(src("../src/app/studio/(create)/create-view.tsx"));
  const send = code.slice(code.indexOf("async function send("));
  const gate = send.indexOf("if (signedOut)");
  assert.ok(gate > 0 && gate < send.indexOf("setBusy(true)"), "the gate comes before any work");
  assert.ok(gate < send.indexOf("runCreativeGuide"), "and before the brain is asked");
  assert.match(code, /<SignupSheet prompt=\{signup\} onClose=\{closeSignup\} \/>/);
});

test("the sign-up sheet keeps the prompt and never sends it", () => {
  const code = strip(src("../src/components/studio/phone/signup-sheet.tsx"));
  assert.match(code, /keepPendingPrompt\(prompt\)/);
  assert.doesNotMatch(code, /send\(|approve|runCreativeGuide|apiFetch/);
  // Google and Discord go straight on; email opens the sign-up page
  assert.match(code, /go\("google"\)/);
  assert.match(code, /go\("discord"\)/);
  const view = strip(src("../src/app/studio/(create)/create-view.tsx"));
  // back signed in, the kept prompt fills the box only when it is empty
  assert.match(view, /if \(kept && !idea\.trim\(\)\) setIdea\(kept\);/);
});

test("the model sheet sets the same state the desktop pickers set and prices nothing", () => {
  const sheet = strip(src("../src/components/studio/phone/model-sheet.tsx"));
  assert.doesNotMatch(sheet, /credits|quote|approve|apiFetch/i);
  const view = strip(src("../src/app/studio/(create)/create-view.tsx"));
  // Create has no model picker (2026-11-02, Mike): Vesper chooses, so the
  // phone's sheet carries no models there
  assert.match(view, /models=\{\[\]\}/);
  assert.match(view, /onFrame=\{\(id\) => \(output === "image" \? setAspect\(id\) : setRatio\(id\)\)\}/);
});

test("on a phone the element shelf under the box is not drawn", () => {
  const css = src("../src/components/studio/composer/composer.css");
  assert.match(css, /\.view\[data-page\] > \.row \{\s*display: none;/);
});

test("Voice is in the phone menu, behind the rail's own flag (QA 2026-11-02 T15)", () => {
  const code = strip(src("../src/components/studio/phone/phone-chrome.tsx"));
  const menu = code.slice(code.indexOf("export function PhoneMenu"));
  assert.match(menu, /caps\.voice_tab === true \? row\("\/studio\/voice", "Voice", AudioLines\)/);
  const shell = strip(src("../src/components/studio/shell.tsx"));
  assert.match(shell, /<PhoneMenu open=\{pmenu\} onClose=\{closePmenu\} caps=\{caps\} \/>/);
  assert.match(shell, /id: "voice", label: "Voice", href: "\/studio\/voice", icon: AudioLines, cap: "voice_tab"/);
});

// QA 2026-11-02 T6 / T7: the two studio pages wider than a phone.
const rule = (css, sel) => {
  const i = css.indexOf(`\n${sel} {`);
  return i < 0 ? "" : css.slice(i, css.indexOf("}", i));
};

test("the Elements cover is never wider than the page (T6: 752px at 390)", () => {
  const css = src("../src/app/studio/studio.css");
  const cover = rule(css, ".elcover");
  assert.match(cover, /width: 100%;/);
  assert.match(cover, /minmax\(min\(320px, 100%\), 1fr\)/);
});

test("the Showcase row stacks on a phone, its columns in CSS where the media query can reach them (T7)", () => {
  const list = src("../src/components/studio/showcase/showcase-list.tsx");
  assert.doesNotMatch(list, /gridTemplateColumns/);
  assert.match(list, /className="qrow showrow"/);
  const css = src("../src/app/studio/studio.css");
  assert.match(rule(css, ".qrow.showrow"), /grid-template-columns: 128px minmax\(0, 1fr\) 96px minmax\(0, max-content\);/);
  assert.match(css, /@media \(max-width: 720px\) \{\s*\.qrow\.showrow \{\s*grid-template-columns: minmax\(0, 1fr\);/);
  // a button's words never wrap into a circle
  assert.match(list, /className="tag whitespace-nowrap"[\s\S]{0,300}Use this Library item/);
});
