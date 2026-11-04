// The signed-out studio (QA 2026-11-02 P14; built 2026-11-03). Create's box
// already opened the sign-up sheet on Send (2026-10-26, phone.test.mjs);
// these are the rest of a visitor's first screen: the header says how to
// get in, Image and Video take a prompt and open the same sheet, and the
// pages that need an account say so instead of a red "SIGN IN FIRST".
// Read as source, like the other shell tests.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = (p) => readFileSync(new URL(p, import.meta.url), "utf8");
const strip = (code) =>
  code
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");

test("signed out, the header has Log in and Sign up, not a blank avatar", () => {
  const shell = strip(src("../src/components/studio/shell.tsx"));
  const right = shell.slice(shell.indexOf('className="hright"'), shell.indexOf("</header>"));
  assert.match(right, /signedOut \? \(/);
  assert.match(right, /className="hlogin"[^>]*onClick=\{\(\) => goToSignIn\(undefined, here\)\}/);
  assert.match(right, /className="hsignup"[^>]*onClick=\{\(\) => goToSignIn\("signup", here\)\}/);
  assert.match(right, />\s*Log in\s*</);
  assert.match(right, />\s*Sign up\s*</);
});

test("the Sign up button is a yellow fill with black text", () => {
  const css = src("../src/app/studio/studio.css");
  // its own rule (not the one it shares with .hlogin), under .hright: a
  // bare .hsignup loses to `.zps button { color: inherit }` (the D8 trap)
  const i = css.indexOf("}\n.hright .hsignup {");
  assert.ok(i >= 0, ".hright .hsignup has a rule");
  const rule = css.slice(i + 1, css.indexOf("}", i + 1));
  assert.match(rule, /background: var\(--signal\)/);
  assert.match(rule, /color: var\(--on-signal\)/);
});

test("pages that need an account show the sign-up wall, not their 401", () => {
  const shell = strip(src("../src/components/studio/shell.tsx"));
  const walled = shell.slice(shell.indexOf("const WALLED"), shell.indexOf("\n", shell.indexOf("const WALLED")));
  for (const v of ["projects", "assets", "elements", "brand", "calendar", "ads", "renders", "cut"]) {
    assert.match(walled, new RegExp(`"${v}"`), v);
  }
  // Create, Image and Video take a prompt signed out; Settings has its own
  for (const v of ["studio", "image", "video", "settings"]) {
    assert.doesNotMatch(walled, new RegExp(`"${v}"`), v);
  }
  assert.match(shell, /const page = signedOut && WALLED\.has\(view\) \? <SignedOutWall view=\{view\} \/> : children;/);
  assert.match(shell, /\{stage \? <div className="stage">\{page\}<\/div> : page\}/);
});

test("the wall says what the page is for and offers both doors", () => {
  const wall = strip(src("../src/components/studio/signed-out-wall.tsx"));
  assert.match(wall, /goToSignIn\("signup", here\)/);
  assert.match(wall, /goToSignIn\(undefined, here\)/);
  assert.match(wall, /href=\{COMPOSE_HOME\}/);
  // no red and no error styling: this is an invitation, not a failure
  assert.doesNotMatch(wall, /className="[^"]*\b(err|red|danger)\b|role="alert"/);
  const css = src("../src/app/studio/studio.css");
  const rules = css.slice(css.indexOf("\n.zwall"), css.lastIndexOf("\n.zwall"));
  assert.ok(rules.length > 0, ".zwall has rules");
  assert.doesNotMatch(rules, /--red|--danger|#e4002b/);
});

test("Image and Video: a signed-out Generate opens the sign-up sheet, never the server", () => {
  // read raw: the file's accept="image/*" would open a comment for strip()
  const code = src("../src/components/studio/direct-generator.tsx");
  assert.match(code, /const \{ toast, me, signedOut \} = useShell\(\);/);
  const go = code.slice(code.indexOf("function go()"), code.indexOf("function go()") + 200);
  assert.match(go, /if \(signedOut\) \{\s*setSignup\(prompt\.trim\(\)\);\s*return;\s*\}\s*void generate\(\);/);
  // every form goes through go(): none calls generate() itself
  // Image panel, Image phone box, Video dock, and the wide card panel (2026-11-03)
  assert.equal((code.match(/onSubmit=/g) ?? []).length, 4);
  assert.doesNotMatch(code, /onSubmit=\{\(e\) => \{\s*e\.preventDefault\(\);\s*void generate\(\);/);
  assert.match(code, /signedOut \? "Sign up to generate" :/);
  assert.match(code, /<SignupSheet prompt=\{signup\} onClose=\{closeSignup\} back=\{PAGE\[kind\]\} \/>/);
});

test("back signed in, Image and Video put the kept prompt in an empty box", () => {
  const code = src("../src/components/studio/direct-generator.tsx");
  assert.match(code, /const kept = takePendingPrompt\(PAGE\[kind\]\);/);
  assert.match(code, /if \(kept && !prompt\.trim\(\)\) setPrompt\(kept\);/);
});

test("a kept prompt goes back only to the page that kept it", () => {
  const code = strip(src("../src/components/studio/phone/signup-sheet.tsx"));
  assert.match(code, /export function keepPendingPrompt\(text: string, where: string = COMPOSE_HREF\)/);
  assert.match(code, /export function takePendingPrompt\(where: string = COMPOSE_HREF\)/);
  // a prompt kept before `where` existed belongs to Create
  assert.match(code, /\(v\.where \?\? COMPOSE_HREF\) !== where/);
  assert.match(code, /keepPendingPrompt\(prompt, back\)/);
  assert.match(code, /goToSignIn\("signup", back, provider\)/);
});

test("on a phone, Generate keeps the box focused so the dock does not jump under the tap", () => {
  // Typing hides the tab bar and drops the dock 64px (phone.css); a press on
  // Generate blurred the box, the bar came back, the button moved up and the
  // click landed on nothing. Found walking this build at 390 (2026-11-03).
  const code = src("../src/components/studio/direct-generator.tsx");
  assert.match(code, /const keepBoxFocus = \{\s*onPointerDown: \(e: \{ preventDefault\(\): void \}\) => e\.preventDefault\(\),\s*onMouseDown: \(e: \{ preventDefault\(\): void \}\) => e\.preventDefault\(\),\s*\};/);
  assert.equal((code.match(/<button type="submit" className="dg-go[^"]*" \{\.\.\.keepBoxFocus\}/g) ?? []).length, 3);
});

test("signed out, Image and Video list their models (the menus are public), never price", () => {
  // Found on the live site 2026-11-03: GET /api/direct/{image,video} is 401
  // signed out (the /api router needs a session), so the picker was empty.
  const code = src("../src/components/studio/direct-generator.tsx");
  assert.match(code, /if \(!workspace && !signedOut\) return;\s*let live = true;\s*const linked = params\.get\("model"\);/);
  assert.match(code, /\}, \[workspace, signedOut, kind\]\);/);
  // signed out the menus come from the public catalogue (app/direct_public.py)
  assert.match(code, /\(signedOut \? getPublicDirectVideo\(\) : getDirectVideo\(\)\)/);
  assert.match(code, /\(signedOut \? getPublicDirectImage\(\) : getDirectImage\(\)\)/);
  const api = src("../src/lib/studio-api.ts");
  assert.match(api, /fetch\(`\$\{API_URL\}\/public\/direct\/\$\{kind\}`\)/);
  // and the studio's origin proxies it to the API, like /api
  assert.match(src("../next.config.ts"), /"\/public\/direct\/:path\*",/);
  // the tray is the person's own Library: not asked for signed out
  assert.match(code, /if \(!signedOut\)\s*getMedia\(\{ kind \}\)/);
  // no quote is asked for signed out: the button says "Sign up to generate"
  assert.match(code, /const priceKey = pick && !signedOut \? JSON\.stringify\(/);
});
