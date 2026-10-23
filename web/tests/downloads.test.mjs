import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DOWNLOAD_BASE, downloadOf, fileName, humanSize } from '../src/lib/downloads.ts';

const file = JSON.parse(readFileSync(new URL('../src/content/downloads.json', import.meta.url), 'utf8'));
const src = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const SHA = 'b'.repeat(64);

test('a build is named the way ops/upload_plugin_r2.py insists', () => {
  assert.equal(fileName('resolve', '0.1.0'), 'phantra-resolve-plugin-0.1.0.pkg');
  assert.equal(fileName('premiere', '0.2.0'), 'phantra-premiere-plugin-0.2.0.ccx');
});

test('a live build with its size and sha256 links its site/downloads address', () => {
  const d = downloadOf('resolve', { resolve: { version: '0.1.0', size: 48405, sha256: SHA, live: true } });
  assert.equal(d.url, `${DOWNLOAD_BASE}/resolve/0.1.0/phantra-resolve-plugin-0.1.0.pkg`);
  assert.equal(d.size, 48405);
  assert.equal(d.sha256, SHA);
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
});

test('today nothing is up: neither panel has a download link yet', () => {
  assert.equal(downloadOf('resolve', file).url, null);
  assert.equal(downloadOf('premiere', file).url, null);
});

test('the studio flyout sends both panels to their setup on /plugins (Mike, 2026-10-23)', () => {
  const flyout = src('../src/components/studio/plugins-flyout.tsx');
  assert.match(flyout, /name: "DaVinci Resolve", href: "\/studio\/plugins#resolve"/);
  assert.match(flyout, /name: "Premiere Pro", href: "\/studio\/plugins#premiere"/);
  const page = src('../src/app/plugins/page.tsx');
  assert.match(page, /id: "resolve"/);
  assert.match(page, /id: "premiere"/);
  // the page draws its Download button from downloadOf, so it can't link a file that isn't up
  assert.match(page, /downloadOf\(panel\.id, ENTRIES\)/);
  assert.match(src('../src/app/sitemap.ts'), /"\/plugins"/);
});

test('the versions on the page are versions', () => {
  for (const id of ['resolve', 'premiere']) assert.match(file[id].version, /^\d+\.\d+\.\d+$/);
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
