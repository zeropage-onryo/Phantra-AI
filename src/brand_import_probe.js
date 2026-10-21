// What a rendered page shows, measured in the page (src/brand_import.py).
// Runs as `page.evaluate(PROBE)` and returns plain data: no fetch, no
// navigation, nothing written. Every colour is weighed by the screen area
// it covers in the first viewport and a little below it, because a brand
// colour is the one a visitor SEES, not the one a stylesheet declares.
() => {
  const VIEW_H = window.innerHeight * 2;          // the first two screens
  const out = {
    colours: [],      // {rgb, area, kind: bg|text|border|fill, where: button|link|header|heading|body}
    vars: [],         // {name, value, used}  -- CSS custom properties on :root
    fonts: [],        // {family, area, where: heading|body|button}
    logo: null,       // {selector, rect, kind: img|svg|text, alt, src}
    meta: {},
  };

  const visible = (el, r) => {
    if (!r || r.width < 2 || r.height < 2) return false;
    if (r.bottom < 0 || r.top > VIEW_H) return false;
    const s = getComputedStyle(el);
    return s.visibility !== "hidden" && s.display !== "none" && Number(s.opacity) > 0.05;
  };
  const clipArea = (r) => {
    const top = Math.max(0, r.top), bottom = Math.min(VIEW_H, r.bottom);
    const left = Math.max(0, r.left), right = Math.min(window.innerWidth, r.right);
    return Math.max(0, bottom - top) * Math.max(0, right - left);
  };
  const where = (el) => {
    if (el.closest("button, [role=button], input[type=submit], a.btn, a.button, .btn, .button, [class*=cta]")) return "button";
    if (el.closest("h1, h2, h3")) return "heading";
    if (el.closest("header, nav")) return "header";
    if (el.closest("a")) return "link";
    return "body";
  };
  const parse = (c) => {
    const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(c || "");
    if (!m) return null;
    const a = m[4] === undefined ? 1 : Number(m[4]);
    if (a < 0.5) return null;
    return [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3])];
  };

  // the page's own background, under everything
  const rootBg = parse(getComputedStyle(document.body).backgroundColor)
    || parse(getComputedStyle(document.documentElement).backgroundColor) || [255, 255, 255];
  out.colours.push({ rgb: rootBg, area: window.innerWidth * VIEW_H * 0.5, kind: "bg", where: "body" });

  const textArea = new Map();
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (!visible(el, r)) continue;
    const s = getComputedStyle(el);
    const area = clipArea(r);
    if (!area) continue;
    const kind = where(el);
    const bg = parse(s.backgroundColor);
    if (bg) out.colours.push({ rgb: bg, area, kind: "bg", where: kind });
    if (el.tagName === "path" || el.tagName === "svg" || el.tagName === "rect" || el.tagName === "circle") {
      const fill = parse(s.fill);
      if (fill && el.tagName !== "svg") out.colours.push({ rgb: fill, area: area * 0.5, kind: "fill", where: kind });
    }
    const bw = parseFloat(s.borderTopWidth) || 0;
    if (bw >= 1) {
      const bc = parse(s.borderTopColor);
      if (bc) out.colours.push({ rgb: bc, area: (r.width + r.height) * 2 * bw, kind: "border", where: kind });
    }
    // text: only elements that hold text of their own
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (own) {
      const fg = parse(s.color);
      const size = parseFloat(s.fontSize) || 14;
      const chars = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join(" ").length;
      const ta = Math.min(area, chars * size * size * 0.55);
      if (fg) out.colours.push({ rgb: fg, area: ta, kind: "text", where: kind });
      const family = (s.fontFamily || "").split(",")[0].replace(/["']/g, "").trim();
      if (family) {
        const key = family + "|" + (kind === "heading" ? "heading" : kind === "button" ? "button" : "body");
        textArea.set(key, (textArea.get(key) || 0) + ta * (parseInt(s.fontWeight) >= 600 ? 1.2 : 1));
      }
    }
  }
  for (const [key, area] of textArea) {
    const [family, place] = key.split("|");
    out.fonts.push({ family, area, where: place });
  }

  // custom properties declared on :root, and whether a visible element uses one
  const used = new Set();
  const names = new Set();
  for (const sheet of [...document.styleSheets]) {
    let rules;
    try { rules = sheet.cssRules; } catch { continue; }     // cross-origin sheet
    for (const rule of rules || []) {
      const text = rule.cssText || "";
      for (const m of text.matchAll(/var\((--[\w-]+)/g)) used.add(m[1]);
      if (rule.selectorText && /(^|,)\s*(:root|html)\s*(,|$)/.test(rule.selectorText)) {
        for (const p of rule.style || []) if (p.startsWith("--")) names.add(p);
      }
    }
  }
  const rs = getComputedStyle(document.documentElement);
  for (const name of names) {
    const value = rs.getPropertyValue(name).trim();
    if (value) out.vars.push({ name, value, used: used.has(name) });
  }

  // the logo: an image or svg in the header, or one named "logo", or the home link
  const candidates = [
    ...document.querySelectorAll("header [class*=logo] img, header [class*=logo] svg, [class*=logo] img, [class*=logo] svg, img[alt*=logo i], img[src*=logo i], img[class*=logo i], svg[class*=logo i], [id*=logo i] img, [id*=logo i] svg"),
    ...document.querySelectorAll("header a[href='/'] img, header a[href='/'] svg, nav a[href='/'] img, nav a[href='/'] svg, a[href='/'] img, a[href='/'] svg"),
    ...document.querySelectorAll("header img, header svg, nav img, nav svg"),
  ];
  for (const el of candidates) {
    const r = el.getBoundingClientRect();
    if (!visible(el, r) || r.width < 24 || r.height < 10 || r.top > 400) continue;
    el.setAttribute("data-phantra-logo", "1");
    out.logo = {
      rect: { x: r.left, y: r.top, w: r.width, h: r.height },
      kind: el.tagName.toLowerCase() === "img" ? "img" : "svg",
      alt: el.getAttribute("alt") || el.getAttribute("aria-label") || "",
    };
    break;
  }

  const meta = (sel) => (document.querySelector(sel)?.getAttribute("content") || "").trim();
  out.meta = {
    title: (document.title || "").trim(),
    site_name: meta("meta[property='og:site_name']"),
    description: meta("meta[name=description]") || meta("meta[property='og:description']"),
    theme_color: meta("meta[name=theme-color]"),
    h1: (document.querySelector("h1")?.innerText || "").trim().slice(0, 200),
  };
  return out;
};
