// What a rendered page shows, measured in the page (src/brand_import.py).
// Ported 2026-10-21 from the brand-kit extraction core built in the chat
// (brandkit.zip, extractor/page_probe.js; scored 12/18 primaries exact).
// Changes: no social-profile scrape (socials are cut from the kit spec on
// purpose), the copy is the title / description / h1 only, and the chosen
// logo element is marked data-phantra-logo so it can be captured alone.
// Returns raw brand evidence; no judgement here.
// Every colour is normalised through a 1x1 canvas so oklch(), color(), hsl(), named colours etc. all become sRGB.
() => {
  const cv = document.createElement('canvas');
  cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const cache = new Map();
  function toRGBA(c) {
    if (!c) return null;
    if (cache.has(c)) return cache.get(c);
    let out = null;
    try {
      if (CSS.supports('color', c)) {
        cx.clearRect(0, 0, 1, 1);
        cx.fillStyle = '#000';
        cx.fillStyle = c;
        cx.fillRect(0, 0, 1, 1);
        const d = cx.getImageData(0, 0, 1, 1).data;
        out = [d[0], d[1], d[2], +(d[3] / 255).toFixed(3)];
      }
    } catch (e) {}
    cache.set(c, out);
    return out;
  }
  // Tailwind/shadcn style channel-only vars: "220 90% 56%" or "37 99 235"
  function channelVar(v) {
    const s = v.trim();
    if (/^-?[\d.]+(deg)?\s+[\d.]+%\s+[\d.]+%(\s*\/\s*[\d.]+%?)?$/.test(s)) return toRGBA(`hsl(${s})`);
    if (/^\d{1,3}\s+\d{1,3}\s+\d{1,3}$/.test(s)) return toRGBA(`rgb(${s})`);
    return null;
  }

  const docH = Math.max(document.documentElement.scrollHeight, 1);
  const vw = window.innerWidth, vh = window.innerHeight;
  const MAXY = Math.min(docH, 6000);

  // ---------- CSS custom properties ----------
  const varNames = new Set();
  const blockedSheets = [];
  for (const sh of Array.from(document.styleSheets)) {
    let rules;
    try { rules = sh.cssRules; } catch (e) { if (sh.href) blockedSheets.push(sh.href); continue; }
    const walk = (rs) => {
      for (const r of Array.from(rs || [])) {
        if (r.style) for (const p of Array.from(r.style)) if (p && p.startsWith('--')) varNames.add(p);
        if (r.cssRules) walk(r.cssRules);
      }
    };
    walk(rules);
  }
  const rootCS = getComputedStyle(document.documentElement);
  const bodyCS = getComputedStyle(document.body);
  const cssVars = [];
  for (const n of varNames) {
    const raw = (rootCS.getPropertyValue(n) || bodyCS.getPropertyValue(n) || '').trim();
    if (!raw || raw.length > 80) continue;
    const rgba = toRGBA(raw) || channelVar(raw);
    if (rgba && rgba[3] > 0.5) cssVars.push({ name: n, raw, rgba });
  }

  // ---------- element walk: colours weighted by area ----------
  const colorHits = []; // {rgba, w, kind}
  const textFonts = new Map(); // family stack -> weight
  const headingFonts = new Map();
  const cta = [];
  // the page's own canvas: the body's background (or the root's), which the
  // element walk below never visits (added 2026-10-21: without it a cream
  // page snapped to the white of its button type)
  for (const el of [document.body, document.documentElement]) {
    const c = toRGBA(getComputedStyle(el).backgroundColor);
    if (c && c[3] > 0.5) { colorHits.push({ rgba: c, w: vw * Math.min(docH, MAXY), kind: 'bg' }); break; }
  }
  const els = Array.from(document.body.querySelectorAll('*')).slice(0, 8000);
  for (const el of els) {
    const tag = el.tagName.toLowerCase();
    if (['script', 'style', 'noscript', 'meta', 'link', 'head', 'template'].includes(tag)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const top = r.top + window.scrollY;
    if (top > MAXY) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.1) continue;
    const area = Math.min(r.width, vw) * Math.min(r.height, MAXY);
    const fold = top < vh ? 2 : 1; // above-the-fold counts double
    const bg = toRGBA(cs.backgroundColor);
    if (bg && bg[3] > 0.5) colorHits.push({ rgba: bg, w: area * fold, kind: 'bg' });
    const bgi = cs.backgroundImage || '';
    if (bgi.includes('gradient')) {
      const stops = bgi.match(/(rgba?\([^)]+\)|oklch\([^)]+\)|color\([^)]+\)|#[0-9a-f]{3,8})/gi) || [];
      for (const s of stops) { const c = toRGBA(s); if (c && c[3] > 0.5) colorHits.push({ rgba: c, w: (area * fold) / stops.length, kind: 'gradient' }); }
    }
    // direct text
    let chars = 0;
    for (const n of el.childNodes) if (n.nodeType === 3) chars += n.textContent.trim().length;
    if (chars > 0) {
      const fs = parseFloat(cs.fontSize) || 16;
      const tc = toRGBA(cs.color);
      const w = chars * fs * fs * 0.5 * fold;
      if (tc && tc[3] > 0.5) colorHits.push({ rgba: tc, w, kind: 'text' });
      const fam = cs.fontFamily;
      const isHead = /^h[1-3]$/.test(tag) || fs >= 28;
      const m = isHead ? headingFonts : textFonts;
      m.set(fam, (m.get(fam) || 0) + chars * fs);
    }
    const bw = parseFloat(cs.borderTopWidth) || 0;
    if (bw >= 1) { const bc = toRGBA(cs.borderTopColor); if (bc && bc[3] > 0.5) colorHits.push({ rgba: bc, w: (r.width + r.height) * 2 * bw, kind: 'border' }); }
    if (['path', 'rect', 'circle', 'polygon', 'ellipse'].includes(tag)) {
      const f = toRGBA(cs.fill); if (f && f[3] > 0.5 && cs.fill !== 'none') colorHits.push({ rgba: f, w: area * 0.5 * fold, kind: 'svg' });
    }
    // CTA candidates
    const isBtn = tag === 'button' || el.getAttribute('role') === 'button' || (tag === 'a' && /btn|button|cta/i.test(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className));
    if (isBtn && bg && bg[3] > 0.5 && r.width < 600 && r.height < 120) {
      cta.push({ rgba: bg, text: (el.innerText || '').trim().slice(0, 40), fg: toRGBA(cs.color), area, top, radius: parseFloat(cs.borderTopLeftRadius) || 0, h: r.height });
    }
  }

  // ---------- fonts ----------
  const loadedFaces = [];
  try { for (const f of document.fonts) loadedFaces.push({ family: f.family.replace(/["']/g, ''), weight: f.weight, style: f.style, status: f.status }); } catch (e) {}
  const rank = (m) => Array.from(m.entries()).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([stack, w]) => ({ stack, w }));

  // ---------- logo candidates ----------
  const title = document.title || '';
  const host = location.hostname.replace(/^www\./, '').split('.')[0];
  const logoCands = [];
  const scope = Array.from(document.querySelectorAll('header, nav, [role=banner], body > div:first-child')).slice(0, 6);
  const pool = new Set();
  for (const s of scope.length ? scope : [document.body]) for (const e of s.querySelectorAll('svg, img, a')) pool.add(e);
  for (const e of document.querySelectorAll('[class*=logo i], [id*=logo i], [aria-label*=logo i], img[alt*=logo i], img[src*=logo i]')) pool.add(e);
  for (const e of pool) {
    const r = e.getBoundingClientRect();
    if (r.width < 12 || r.height < 8 || r.width > 500 || r.height > 200) continue;
    const top = r.top + window.scrollY;
    if (top > 400) continue;
    const tag = e.tagName.toLowerCase();
    if (tag === 'a' && !e.querySelector('svg, img')) continue;
    const target = tag === 'a' ? e.querySelector('svg, img') : e;
    if (!target) continue;
    const t2 = target.tagName.toLowerCase();
    const link = e.closest('a');
    const meta = [target.getAttribute('class'), target.id, target.getAttribute('alt'), target.getAttribute('aria-label'), target.getAttribute('src'), link && link.getAttribute('aria-label'), link && link.getAttribute('title')].join(' ');
    let score = 0;
    if (/logo/i.test(meta)) score += 4;
    if (new RegExp(host, 'i').test(meta)) score += 3;
    if (link && /^(\/|https?:\/\/[^/]+\/?)(\?.*)?$/.test(link.getAttribute('href') || '') ) score += 3;
    if (e.closest('header, nav, [role=banner]')) score += 2;
    if (r.left < vw * 0.3) score += 2;
    if (top < 120) score += 1;
    if (t2 === 'svg' && target.querySelectorAll('path').length >= 2) score += 1;
    if (r.width < 24 && r.height < 24) score -= 3; // icons
    let svg = null;
    if (t2 === 'svg') {
      const clone = target.cloneNode(true);
      const src = target.querySelectorAll('*'), dst = clone.querySelectorAll('*');
      src.forEach((n, i) => { const c = getComputedStyle(n); if (dst[i] && c.fill && c.fill !== 'none') dst[i].setAttribute('fill', c.fill); if (dst[i] && c.stroke && c.stroke !== 'none') dst[i].setAttribute('stroke', c.stroke); });
      if (!clone.getAttribute('xmlns')) clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      // resolve <use href="#id"> references
      for (const u of clone.querySelectorAll('use')) {
        const ref = (u.getAttribute('href') || u.getAttribute('xlink:href') || '');
        if (ref.startsWith('#')) { const def = document.getElementById(ref.slice(1)); if (def) u.replaceWith(def.cloneNode(true)); }
      }
      svg = clone.outerHTML.slice(0, 200000);
    }
    logoCands.push({ el: target, tag: t2, score, src: t2 === 'img' ? (target.currentSrc || target.src) : null, svg, box: { x: r.left, y: top, w: r.width, h: r.height }, meta: meta.replace(/\s+/g, ' ').trim().slice(0, 160) });
  }
  logoCands.sort((a, b) => b.score - a.score);
  if (logoCands[0]) logoCands[0].el.setAttribute('data-phantra-logo', '1');
  for (const c of logoCands) delete c.el;

  // a page with no address of its own (a fixture) resolves nothing
  const abs = (href) => { try { return new URL(href, location.href).href; } catch (e) { return null; } };
  const linkHref = (sel) => { const l = document.querySelector(sel); return l ? abs(l.getAttribute('href')) : null; };
  const metaC = (sel) => { const m = document.querySelector(sel); return m ? m.getAttribute('content') : null; };

  const copy = {
    title, description: metaC('meta[name=description]') || metaC('meta[property="og:description"]'),
    h1: Array.from(document.querySelectorAll('h1')).map(e => (e.innerText || '').trim()).filter(Boolean).slice(0, 3),
    buttons: Array.from(new Set(cta.map(c => c.text).filter(Boolean))).slice(0, 12),
  };
  const siteName = metaC('meta[property="og:site_name"]');

  return {
    url: location.href, title, docH, siteName,
    cssVars, blockedSheets,
    colorHits, cta,
    fonts: { faces: loadedFaces, body: rank(textFonts), heading: rank(headingFonts) },
    logos: logoCands.slice(0, 5),
    icons: { favicon: linkHref('link[rel~="icon"]') || abs('/favicon.ico'), appleTouch: linkHref('link[rel="apple-touch-icon"]'), ogImage: metaC('meta[property="og:image"]') },
    manifestUrl: linkHref('link[rel="manifest"]'),
    themeColorMeta: metaC('meta[name="theme-color"]'),
    themeColorRgba: toRGBA(metaC('meta[name="theme-color"]')),
    copy,
  };
}
