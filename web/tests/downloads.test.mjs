import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DOWNLOAD_BASE, downloadOf, fileName, humanSize, osesOf } from '../src/lib/downloads.ts';

const file = JSON.parse(readFileSync(new URL('../src/content/downloads.json', import.meta.url), 'utf8'));
const src = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const SHA = 'b'.repeat(64);
const LIVE = { version: '0.3.0', size: 100, sha256: SHA, live: true, windows: { size: 200, sha256: 'c'.repeat(64) } };

test('a build is named the way ops/upload_plugin_r2.py insists', () => {
  assert.equal(fileName('resolve', '0.1.0'), 'phantra-resolve-plugin-0.1.0.pkg');
  assert.equal(fileName('adobe', '0.3.0'), 'phantra-adobe-plugin-0.3.0.pkg');
  assert.equal(fileName('adobe', '0.3.0', 'windows'), 'phantra-adobe-plugin-0.3.0.zxp');
  // Resolve has no Windows build, so there is no name for one
  assert.equal(fileName('resolve', '0.1.0', 'windows'), null);
});

test('the Adobe panel ships for Mac and Windows; Resolve for Mac only', () => {
  assert.deepEqual(osesOf('resolve'), ['mac']);
  assert.deepEqual(osesOf('adobe'), ['mac', 'windows']);
});

test('a live build with its size and sha256 links its site/downloads address', () => {
  const d = downloadOf('resolve', { resolve: { version: '0.1.0', size: 48405, sha256: SHA, live: true } });
  assert.equal(d.url, `${DOWNLOAD_BASE}/resolve/0.1.0/phantra-resolve-plugin-0.1.0.pkg`);
  assert.equal(d.size, 48405);
  assert.equal(d.sha256, SHA);
  assert.equal(d.os, 'mac');
});

test('the Adobe .pkg and .zxp are each offered on their own facts', () => {
  const mac = downloadOf('adobe', { adobe: LIVE });
  assert.equal(mac.url, `${DOWNLOAD_BASE}/adobe/0.3.0/phantra-adobe-plugin-0.3.0.pkg`);
  assert.equal(mac.size, 100);
  const win = downloadOf('adobe', { adobe: LIVE }, 'windows');
  assert.equal(win.url, `${DOWNLOAD_BASE}/adobe/0.3.0/phantra-adobe-plugin-0.3.0.zxp`);
  assert.equal(win.size, 200);
  assert.equal(win.sha256, 'c'.repeat(64));
  // the .pkg up and the .zxp not yet: only the .pkg is linked
  const half = downloadOf('adobe', { adobe: { ...LIVE, windows: { size: null, sha256: null } } }, 'windows');
  assert.equal(half.url, null);
  assert.equal(downloadOf('adobe', { adobe: { ...LIVE, windows: null } }).url, mac.url);
  // and a Resolve for Windows is nothing at all
  const none = downloadOf('resolve', { resolve: { version: '0.1.0', size: 48405, sha256: SHA, live: true } }, 'windows');
  assert.equal(none.url, null);
  assert.equal(none.file, null);
});

test('nothing is linked until the build is live AND its size and sha256 are filled in', () => {
  for (const entry of [
    { version: '0.1.0', size: 48405, sha256: SHA, live: false },
    { version: '0.1.0', size: null, sha256: SHA, live: true },
    { version: '0.1.0', size: 48405, sha256: null, live: true },
    { version: '0.1.0', size: 48405, sha256: 'not-a-sha', live: true },
    { version: '0.1.0', size: 0, sha256: SHA, live: true },
  ]) {
    const d = downloadOf('resolve', { resolve: entry });
    assert.equal(d.url, null, JSON.stringify(entry));
    assert.equal(d.sha256, null);
  }
  // `live` is the panel's switch: off, the Windows file stays unlinked too
  assert.equal(downloadOf('adobe', { adobe: { ...LIVE, live: false } }, 'windows').url, null);
});

test('Resolve 0.1.2 is offered (it copies the bridge from your Resolve; upload it before this merges); the Adobe panel has no download yet', () => {
  const resolve = downloadOf('resolve', file);
  assert.equal(resolve.url, `${DOWNLOAD_BASE}/resolve/0.1.2/phantra-resolve-plugin-0.1.2.pkg`);
  assert.equal(resolve.size, 44181);
  assert.equal(resolve.sha256, '1c07b580d4039025cb9be0f4ed601c8bd15c81c5829033c2e89f42a8cd1d5052');
  // 0.3.0 is the first build for both apps (phantra-premiere-plugin PR #3,
  // 2026-11-03); it goes live only after a real Premiere Pro and After
  // Effects have opened a signed build and ops/upload_plugin_r2.py put it up
  assert.equal(file.adobe.version, '0.3.0');
  assert.equal(downloadOf('adobe', file).url, null);
  assert.equal(downloadOf('adobe', file, 'windows').url, null);
  assert.equal('premiere' in file, false, 'the Premiere entry became the Adobe one');
});

test('the studio flyout sends every editor row to its setup on /studio/plugins (Mike, 2026-10-23; After Effects 2026-11-03)', () => {
  const flyout = src('../src/components/studio/plugins-flyout.tsx');
  assert.match(flyout, /name: "DaVinci Resolve", href: "\/studio\/plugins#resolve"/);
  assert.match(flyout, /name: "Premiere Pro", href: "\/studio\/plugins#premiere"/);
  assert.match(flyout, /name: "After Effects", href: "\/studio\/plugins#aftereffects"/);
  // and the studio page knows both Adobe anchors as the one panel
  const shared = src('../src/components/studio/plugins/shared.tsx');
  assert.match(shared, /aliases: \["premiere", "aftereffects"\]/);
  const page = src('../src/app/plugins/page.tsx');
  assert.match(page, /id: "resolve"/);
  assert.match(page, /id: "adobe"/);
  assert.match(page, /aliases: \["premiere", "aftereffects"\]/);
  // the page draws its Download buttons from downloadOf, so it can't link a file that isn't up
  assert.match(page, /downloadOf\(panel\.id, ENTRIES, os\)/);
  assert.match(src('../src/app/sitemap.ts'), /"\/plugins"/);
});

test('the Adobe pages say both apps, the CEP menu and the Windows installer', () => {
  for (const p of ['../src/app/plugins/page.tsx', '../src/app/download/page.tsx', '../src/components/studio/plugins/plugins-page.tsx']) {
    const page = src(p);
    assert.match(page, /After Effects/, p);
    assert.match(page, /Window(,| →) Extensions(,| →) Phantra/, p);
    assert.match(page, /aescripts\.com\/learn\/zxp-installer/, p);
    assert.doesNotMatch(page, /\.ccx/, `${p} still describes the UXP .ccx`);
    assert.doesNotMatch(page, /UXP Plugins/, p);
  }
});

test('the versions on the page are versions', () => {
  for (const id of ['resolve', 'adobe']) assert.match(file[id].version, /^\d+\.\d+\.\d+$/);
});

test('sizes read the way a download button says them', () => {
  assert.equal(humanSize(48405), '47 KB');
  assert.equal(humanSize(5 * 1024 * 1024), '5.0 MB');
});

test('the page, its license and the sitemap are wired', () => {
  assert.match(src('../src/app/sitemap.ts'), /"\/download"/);
  assert.match(src('../src/app/download/page.tsx'), /href="\/download\/license"/);
  assert.match(src('../src/content/plugin-license.txt'), /^Phantra Plugin License/);
});

test('the Resolve card says where Studio has to come from', () => {
  const page = src('../src/app/download/page.tsx');
  assert.match(page, /not the Mac App Store/);
  assert.match(page, /href="https:\/\/www\.blackmagicdesign\.com\/support\/family\/davinci-resolve-and-fusion"/);
});

test('the unsigned installer gets past Gatekeeper the way macOS 15+ allows', () => {
  const page = src('../src/app/download/page.tsx');
  assert.match(page, /Open Anyway/);
  assert.doesNotMatch(page, /right-click it and choose Open/);
});
