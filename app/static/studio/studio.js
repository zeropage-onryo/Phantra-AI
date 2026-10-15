/* Studio view: the composer with live RAG grounding, and the asset
   carousel.

   The idea is typed HERE and nowhere else (2026-08-28). Create posts
   /api/scenes/run -- one idea, 1-4 standalone concepts out -- and routes
   to Pipeline, which is now purely the deciding surface. The references
   picked here (uploads, or photos out of the asset bank) ride into the
   generation as vision input AND are stored on each concept's shot, so
   they reach the keyframe and the clip later. */
import { api, esc, loadAssets, openAssetDetail, state, stateline, wireMentions, wireScrub } from './shared.js';

import { initCreativeGuide } from './creative-guide.js';
import { initComposerChrome } from './composer.js';

const promptEl = () => document.getElementById('prompt');
let debounceTimer = null;
let railFilter = 'all';

export function initStudio(go) {
  const prompt = promptEl();
  const goBtn = document.getElementById('go');
  const cbox = document.getElementById('cbox');
  const guide = initCreativeGuide(collectRunForm, {
    getRefs: () => attachments.filter(a => a.kind === 'asset').map(a => a.url),
    hasUploads: () => attachments.some(a => a.kind === 'file'),
    restoreRefs: urls => { clearAttachments(); urls.forEach(url => addAttachment({kind: 'asset', url})); },
  });

  prompt.addEventListener('focus', () => cbox.classList.add('awake'));
  prompt.addEventListener('blur', () => cbox.classList.remove('awake'));
  prompt.addEventListener('input', () => {
    if (!state.caps.retrieve) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(retrieve, 300);
  });

  // @asset mentions: naming a character/prop/room in the idea attaches its
  // photo as a reference for THIS call, the same pathway the + menu
  // uses -- so a run grounds only on what's typed or attached,
  // never the whole bank (src/asset_shelf.in_scope on the server side).
  wireMentions(prompt, document.getElementById('promptmentions'), item => {
    if (item.thumb) addAttachment({ kind: 'asset', url: item.thumb, origin: 'mention' });
  });

  goBtn.addEventListener('click', async () => {
    const text = document.getElementById('guidebrief').value.trim();
    if (!text || prompt.value.trim() || goBtn.disabled) return;
    guide.setBusy(true);
    goBtn.textContent = 'Writing…';
    try {
      await api('/api/scenes/run', { method: 'POST', body: collectRunForm(text) });
      prompt.value = '';
      guide.setBusy(false);
      await guide.reset();
      clearAttachments();
      document.getElementById('upmenu').hidden = true;
      document.getElementById('up').setAttribute('aria-expanded', 'false');
      go('pipeline');
    } catch (e) {
      const hits = document.getElementById('hits');
      document.getElementById('retr').setAttribute('data-on', '');
      hits.innerHTML = `<div class="probeblank" style="color:var(--signal)">${esc(e.message)}</div>`;
    } finally {
      goBtn.textContent = 'Create scene';
      guide.setBusy(false);
    }
  });

  document.getElementById('arrow').onclick = () => {
    const hrail = document.getElementById('hrail');
    hrail.scrollBy({ left: hrail.clientWidth * .8, behavior: 'smooth' });
  };

  initUpload();
  // last, so it can move controls the calls above have already wired
  initComposerChrome(api);
  initSceneLengths();
}

/* Which model writes lives in composer.js now (2026-09-10): the tiers
   still come from /api/brains -> gemini_utils.BRAINS, but the control
   is the LTX-style pill over the same #cbrain select, so the fetch and
   the rendering belong together. collectRunForm below still reads that
   select and nothing else. */

/* ── how long the scene is ──────────────────────────────────────────
   The total the writer fills with timed shots -- (0-3s) one shot, (3-7s)
   the next -- each rendered as its own clip. Choices and default come from
   the server (/api/scene-lengths -> timeline.SCENE_SECONDS_CHOICES) for
   the brains picker's reason. A failed fetch hides the select and sends
   nothing, which the route reads as PHANTRA_SCENE_SECONDS. ── */

async function initSceneLengths() {
  const sel = document.getElementById('cseconds');
  if (!sel) return;
  try {
    const res = await api('/api/scene-lengths');
    sel.innerHTML = (res.choices || []).map(n =>
      `<option value="${esc(n)}"${n === res.default ? ' selected' : ''}>${esc(n)}s scene</option>`
    ).join('');
  } catch (e) {
    sel.hidden = true;
  }
}

/* ── the + media panel: previously saved photos to pick from, plus a
   drop-or-upload tile. Selections attach to THIS generation as image
   references (the same image_refs path the engine composer uses). ── */

// 6 -> 12 on 2026-09-10: references are for PROMPTING, and get narrowed
// afterwards. Same number as api.MAX_IMAGE_REFS and scene_chain.MAX_REFS
// -- the server is the gate, this is the honest UI.
const MAX_ATTACH = 12;
// Videos ground the writer only (Gemini watches them); no renderer takes
// one as a reference. Same cap as api.MAX_VIDEO_REFS.
const MAX_VIDEO = 2;
const attachments = [];   // {kind:'asset', url} | {kind:'file', file, url(objectURL), video?}

const isVideo = f => (f.type || '').startsWith('video/')
  || /\.(mp4|mov|webm|m4v)$/i.test(f.name || '');
const fileAttachment = f => ({ kind: 'file', file: f, url: URL.createObjectURL(f),
                               video: isVideo(f) });

function initUpload() {
  const plus = document.getElementById('up');
  const menu = document.getElementById('upmenu');
  const files = document.getElementById('upfiles');
  const note = document.getElementById('upnote');
  const cbox = document.getElementById('cbox');

  plus.onclick = async () => {
    const open = menu.hidden;
    menu.hidden = !open;
    plus.setAttribute('aria-expanded', String(open));
    if (open) await renderMediaGrid();
    else note.textContent = '';
  };

  files.onchange = () => {
    for (const f of files.files) addAttachment(fileAttachment(f));
    files.value = '';
  };

  // drag & drop straight onto the composer
  ['dragover', 'drop'].forEach(evt => cbox.addEventListener(evt, e => {
    e.preventDefault();
    if (evt === 'drop') {
      for (const f of e.dataTransfer.files) {
        if (f.type.startsWith('image/') || isVideo(f)) {
          addAttachment(fileAttachment(f));
        }
      }
    }
  }));
}

function addAttachment(item) {
  const note = document.getElementById('upnote');
  const drop = () => { if (item.kind === 'file') URL.revokeObjectURL(item.url); return false; };
  if (item.video) {
    if (attachments.filter(a => a.video).length >= MAX_VIDEO) {
      note.textContent = `at most ${MAX_VIDEO} videos per generation`;
      return drop();
    }
  } else if (attachments.filter(a => !a.video).length >= MAX_ATTACH) {
    note.textContent = `at most ${MAX_ATTACH} images per generation`;
    return drop();
  }
  attachments.push(item);
  renderAttachments();
  return true;
}

function removeAttachment(index) {
  const [gone] = attachments.splice(index, 1);
  if (gone && gone.kind === 'file') URL.revokeObjectURL(gone.url);
  renderAttachments();
  const tile = document.querySelector(`.mtile[data-u="${CSS.escape(gone?.url || '')}"]`);
  if (tile) tile.setAttribute('aria-pressed', 'false');
}

function renderAttachments() {
  const bar = document.getElementById('attachbar');
  bar.innerHTML = attachments.map((a, i) => a.video
    ? `<div class="attach" data-origin="${esc(a.origin || 'user')}" title="video · grounds the writing">
         <video src="${a.url}" muted playsinline preload="metadata"
                style="width:100%;height:100%;object-fit:cover;border-radius:inherit;display:block"></video>
         <button class="ax" data-i="${i}" aria-label="Remove">✕</button>
       </div>`
    : `<div class="attach" data-origin="${esc(a.origin || 'user')}"
          style="background-image:url('${a.url}')" title="${esc(a.kind)}">
       <button class="ax" data-i="${i}" aria-label="Remove">✕</button>
     </div>`).join('');
  bar.querySelectorAll('.ax').forEach(b => b.onclick = () => removeAttachment(+b.dataset.i));
  document.getElementById('cbox').dispatchEvent(new Event('referenceschange'));
}

async function renderMediaGrid() {
  const grid = document.getElementById('mgrid');
  const count = document.getElementById('mcount');
  grid.innerHTML = '<div class="probeblank">Loading media…</div>';
  let media;
  try {
    media = await api('/api/media');
  } catch (e) {
    grid.innerHTML = `<div class="probeblank" style="color:var(--signal)">${esc(e.message)}</div>`;
    return;
  }
  count.textContent = `${media.counts.all} saved`;
  const selected = new Set(attachments.filter(a => a.kind === 'asset').map(a => a.url));
  grid.innerHTML = `
    <button class="mtile mdrop" id="mdrop" type="button">
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4m0 0 4 4m-4-4-4 4M4 20h16"/></svg>
      Drop or upload files
      <small>up to ${MAX_ATTACH} images + ${MAX_VIDEO} videos · this generation only</small>
    </button>` +
    media.items.map(m => `
      <button class="mtile" type="button" data-u="${esc(m.url)}"
              aria-pressed="${selected.has(m.url)}"
              style="background-image:url('${m.url}')">
        <span class="mname">${esc(m.asset_name)}</span>
      </button>`).join('');
  if (!media.items.length) {
    grid.insertAdjacentHTML('beforeend',
      '<div class="probeblank">No saved media yet — photos added on /assets appear here</div>');
  }
  document.getElementById('mdrop').onclick = () =>
    document.getElementById('upfiles').click();
  grid.querySelectorAll('.mtile[data-u]').forEach(tile => tile.onclick = () => {
    const url = tile.dataset.u;
    const existing = attachments.findIndex(a => a.kind === 'asset' && a.url === url);
    if (existing >= 0) {
      removeAttachment(existing);
      tile.setAttribute('aria-pressed', 'false');
    } else if (addAttachment({ kind: 'asset', url })) {
      tile.setAttribute('aria-pressed', 'true');
    }
  });
}

export function collectRunForm(idea) {
  const body = new FormData();
  body.append('idea', idea);
  // One Create, one scene (2026-09-10): the 1-4 picker is gone, and the
  // server writes one whatever `count` says -- api.SCENE_COUNT_MAX.
  // Only when the picker actually has a value: an empty select (the
  // fetch failed) must send nothing rather than an empty string, so the
  // server falls back to its own default instead of clamping a blank.
  const brain = document.getElementById('cbrain');
  if (brain && brain.value) body.append('brain', brain.value);
  const seconds = document.getElementById('cseconds');
  if (seconds && seconds.value && !seconds.hidden) body.append('seconds', seconds.value);
  // The render preference the composer's LTX row carries (2026-09-10).
  // INERT until /api/scenes/run reads them -- FastAPI drops a form field
  // nobody asked for -- and posted anyway so the wiring is one server
  // change rather than a client change too. See composer.js's note: the
  // legal sets belong in a projection route before this means anything.
  for (const id of ['ratio', 'resolution']) {
    const el = document.getElementById(id);
    if (el && el.value) body.append(id, el.value);
  }
  for (const a of attachments) {
    if (a.kind === 'file') body.append('files', a.file);
    else body.append('asset_photos', a.url);
  }
  return body;
}

export function clearAttachments() {
  while (attachments.length) removeAttachment(0);
}

async function retrieve() {
  const q = promptEl().value.trim();
  const retr = document.getElementById('retr');
  const hits = document.getElementById('hits');
  const lat = document.getElementById('lat');
  if (q.length < 3) { retr.removeAttribute('data-on'); lat.textContent = '—'; return; }
  retr.setAttribute('data-on', '');
  try {
    const res = await api('/api/retrieve', { method: 'POST', body: { query: q, k: 4 } });
    lat.textContent = `${res.latency_ms} ms · ${res.model}`;
    if (!res.hits.length) {
      hits.innerHTML = '<div class="probeblank">Nothing retrieved — the library has no match</div>';
      return;
    }
    hits.innerHTML = res.hits.map((h, i) => `
      <div class="hit" style="animation-delay:${i * 46}ms">
        <div>
          <div class="nm">${esc(h.source)} <span class="sr">· ${esc(h.domain)}</span></div>
          <div class="snip">${esc(h.chunk.slice(0, 160))}</div>
        </div>
        <span></span>
        <span class="sc">${h.score.toFixed(2)}</span>
      </div>`).join('');
  } catch (e) {
    lat.textContent = '—';
    hits.innerHTML = `<div class="probeblank" style="color:var(--signal)">${esc(e.message)}</div>`;
  }
}

export async function renderStudio() {
  const railstate = document.getElementById('railstate');
  const hrail = document.getElementById('hrail');
  const filters = document.getElementById('rowfilters');
  stateline(railstate, 'loading', 'Loading assets…');
  let data;
  try {
    data = await loadAssets();
  } catch (e) {
    hrail.innerHTML = '';
    filters.innerHTML = '';
    stateline(railstate, 'error', `Assets unavailable: ${e.message}`, renderStudio);
    return;
  }
  stateline(railstate, null);
  const counts = data.counts;
  const cats = [['all', 'All'], ['location', 'Rooms'], ['character', 'Characters'], ['prop', 'Props']];
  filters.innerHTML = cats.map(([k, l]) =>
    `<button class="chip" aria-pressed="${railFilter === k}" data-f="${k}">${l} · ${counts[k] ?? 0}</button>`).join('');
  filters.querySelectorAll('.chip').forEach(c => c.onclick = () => {
    railFilter = c.dataset.f; renderStudio();
  });
  const items = data.items.filter(a => railFilter === 'all' || a.category === railFilter);
  if (!items.length) {
    hrail.innerHTML = '';
    stateline(railstate, 'empty',
      'No assets yet — photograph rooms, cast and props on the Assets engine page (/assets)');
    return;
  }
  hrail.innerHTML = items.slice(0, 12).map(a => `
    <article class="card" data-id="${a.id}">
      <div class="fr${a.poster ? '' : ' blank'}" ${a.poster ? `style="background-image:url('${a.poster}')"` : ''}></div>
      <div class="cap"><b>${esc(a.name)}</b><span class="tc">${esc(a.category)}</span></div>
    </article>`).join('');
  hrail.querySelectorAll('.card').forEach(card => {
    const asset = items.find(x => x.id === card.dataset.id);
    wireScrub(card.querySelector('.fr'), asset.photos);
    card.onclick = () => openAssetDetail(asset);
  });
}
