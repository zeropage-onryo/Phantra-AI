# ruff: noqa: E501, E701, E702, E741
# QA crawler for docs/qa/2026-11-02/01-public-ui.md, the dated copy of docs/qa/crawl-2026-10-22.py.
# Two modes, both read-only against https://phantra.ai signed out (no form is submitted, nothing is clicked):
#   venv/bin/python -I crawl-2026-11-02.py crawl   <out.json>
#       stdlib only: the 10-22 crawl (BFS two levels from the home page + every sitemap.xml <loc>),
#       link checks, model names, "zeropage"/"Zero Page" residue, price/credit strings, declared weight.
#   venv/bin/python -I crawl-2026-11-02.py browser <crawl.json> <out.json> <screens_dir> <axe.min.js>
#       headless Playwright (the venv's Chromium): per page and viewport, transfer bytes, JS bytes,
#       LCP (buffered PerformanceObserver), horizontal overflow, clipped text, broken images, failed
#       requests, console errors, axe-core serious/critical, computed contrast of the yellow accents,
#       and a full-page PNG <slug>-<width>.png.
# A dense one-off tool kept for reproducibility, hence the style exemptions above.
import json
import re
import ssl
import sys
import time
from collections import deque
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

HOST = "phantra.ai"
BASE = "https://phantra.ai/"
CAP = 150
UA = "phantra-qa-crawl/2026-11-02 (+docs/qa)"
CTX = ssl.create_default_context()

MODEL_WORDS = [
 "Kling", "Veo", "Seedance", "LTX", "Wan", "FLUX", "Flux", "Seedream", "GPT Image", "GPT-Image",
 "Ideogram", "Nano Banana", "Gemini", "Topaz", "MMAudio", "PixVerse", "Luma", "Ray 2", "OmniHuman",
 "ElevenLabs", "Runway", "Sora", "MiniMax", "Hailuo", "Pika", "Imagen", "Hunyuan", "Mochi", "Whisper",
 "Claude", "ChatGPT", "Higgsfield", "Midjourney", "Recraft", "Stable Diffusion", "Sunburst", "Flare",
 "Grok Imagine", "Grok",
]
MODEL_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in MODEL_WORDS) + r")(?:[ \-]?(\d+(?:\.\d+)?(?:[ \-]?(?:Pro|Turbo|Fast|Flash|Lite|Std|Standard|Master|Flare|Sunburst|Max|Image|Pro Image))*)?)?", re.I)
# a price or a credit count in visible text
PRICE_RE = re.compile(r"(\$\s?\d[\d,.]*(?:\s?/\s?(?:mo|month|yr|year))?|\b\d[\d,]*\s+credits?\b|\b\d[\d,]*\s?cr\b)", re.I)
BRAND_RE = re.compile(r"zero\s?-?page", re.I)

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]; self.imgs=[]; self.scripts=[]; self.css=[]; self.text=[]; self.title=""
        self._skip=0; self._title=False
        self.footer=[]; self.marquee=[]; self._in_footer=0; self._in_marq=0; self.stack=[]
        self.meta={}
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"): self.links.append(a["href"])
        if tag=="img" and a.get("src"): self.imgs.append(a["src"])
        if tag=="source" and a.get("src"): self.imgs.append(a["src"])
        if tag=="video" and a.get("src"): self.imgs.append(a["src"])
        if tag=="video" and a.get("poster"): self.imgs.append(a["poster"])
        if tag=="script" and a.get("src"): self.scripts.append(a["src"])
        if tag=="link" and (a.get("rel") or "").find("stylesheet")>=0 and a.get("href"): self.css.append(a["href"])
        if tag=="link" and (a.get("rel") or "")=="preload" and a.get("as")=="script" and a.get("href"): self.scripts.append(a["href"])
        if tag=="meta" and a.get("name") in ("description","viewport") : self.meta[a["name"]]=a.get("content","")
        if tag in ("script","style","noscript"): self._skip+=1
        if tag=="title": self._title=True
        if tag=="footer": self._in_footer+=1
        cls=(a.get("class") or "")+" "+(a.get("id") or "")+" "+(a.get("aria-label") or "")
        marq = "marquee" in cls.lower() or "ticker" in cls.lower()
        self.stack.append((tag, marq))
        if marq: self._in_marq+=1
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript") and self._skip: self._skip-=1
        if tag=="title": self._title=False
        if tag=="footer" and self._in_footer: self._in_footer-=1
        while self.stack:
            t,m=self.stack.pop()
            if m and self._in_marq: self._in_marq-=1
            if t==tag: break
    def handle_data(self, d):
        if self._title: self.title+=d
        if self._skip: return
        s=d.strip()
        if not s: return
        self.text.append(s)
        if self._in_footer: self.footer.append(s)
        if self._in_marq: self.marquee.append(s)

def norm(u, base):
    u=urljoin(base,u)
    s=urlsplit(u)
    if s.scheme not in ("http","https"): return None
    return urlunsplit((s.scheme, s.netloc.lower(), s.path or "/", s.query, ""))

def fetch(u, head=False, timeout=20):
    t=time.time()
    req=Request(u, headers={"User-Agent":UA, "Accept":"*/*"}, method="HEAD" if head else "GET")
    try:
        with urlopen(req, timeout=timeout, context=CTX) as r:
            body=b"" if head else r.read()
            cl=r.headers.get("Content-Length")
            return {"status":r.status,"final":r.geturl(),"ctype":r.headers.get("Content-Type",""),"bytes":(int(cl) if (head and cl) else len(body)),"body":body,"ms":int((time.time()-t)*1000),"error":None}
    except HTTPError as e:
        return {"status":e.code,"final":u,"ctype":"","bytes":0,"body":b"","ms":int((time.time()-t)*1000),"error":str(e)}
    except URLError as e:
        return {"status":None,"final":u,"ctype":"","bytes":0,"body":b"","ms":int((time.time()-t)*1000),"error":"timeout" if "timed out" in str(e).lower() else str(e)}
    except Exception as e:
        return {"status":None,"final":u,"ctype":"","bytes":0,"body":b"","ms":int((time.time()-t)*1000),"error":"timeout" if "timed out" in str(e).lower() else repr(e)}

def crawl(OUT):
    sm=fetch(BASE+"sitemap.xml")
    sitemap=[norm(x, BASE) for x in re.findall(r"<loc>([^<]+)</loc>", sm["body"].decode("utf-8","replace"))]
    seeds=[BASE]+[BASE+p for p in ("pricing","models","faq","connector","mcp","mcp/claude","privacy","terms","make","legal","support","v","v/qa-not-a-token","studio")]
    for s in sitemap:
        if s and s not in seeds and s.rstrip("/")+"/"!=BASE: seeds.append(s)
    pages={}; q=deque((s,0) for s in seeds); seen=set(seeds); extern={}; assets_cache={}
    order=[]
    while q and len(pages)<CAP:
        u,d=q.popleft()
        r=fetch(u)
        rec={"url":u,"depth":d,"status":r["status"],"final":r["final"],"ctype":r["ctype"],"html_bytes":r["bytes"],"ms":r["ms"],"error":r["error"],"links_out":[],"broken":[],"in_sitemap":u in sitemap}
        pages[u]=rec; order.append(u)
        if r["error"] and r["status"] is None: continue
        if "text/html" not in r["ctype"]: continue
        doc=r["body"].decode("utf-8","replace")
        p=P()
        try: p.feed(doc)
        except Exception as e: rec["parse_err"]=repr(e)
        text=" ".join(p.text)
        rec["title"]=p.title.strip(); rec["meta"]=p.meta
        rec["zeropage_html"]=len(BRAND_RE.findall(doc))
        rec["zeropage_text"]=len(BRAND_RE.findall(text))
        rec["zeropage_contexts"]=[doc[max(0,m.start()-60):m.end()+60].replace("\n"," ") for m in BRAND_RE.finditer(doc)][:8]
        rec["zeropage_text_contexts"]=[text[max(0,m.start()-60):m.end()+60] for m in BRAND_RE.finditer(text)][:8]
        rec["prices"]=sorted(set(re.sub(r"\s+"," ",m.group(0)) for m in PRICE_RE.finditer(text)))
        rec["price_contexts"]=[text[max(0,m.start()-50):m.end()+30] for m in PRICE_RE.finditer(text)][:12]
        def models(ts):
            return sorted(set(re.sub(r"\s+"," ",m.group(0)).strip() for m in MODEL_RE.finditer(ts)), key=str.lower)
        rec["models_all"]=models(text); rec["models_footer"]=models(" ".join(p.footer)); rec["models_marquee"]=models(" ".join(p.marquee))
        rec["imgs"]=[norm(i,u) for i in p.imgs if norm(i,u)]; rec["scripts"]=[norm(i,u) for i in p.scripts if norm(i,u)]; rec["css"]=[norm(i,u) for i in p.css if norm(i,u)]
        for l in p.links:
            n=norm(l,u)
            if not n: continue
            rec["links_out"].append(n)
            s=urlsplit(n)
            if s.netloc==HOST or s.netloc=="www."+HOST:
                if n not in seen and d<2 and not s.path.startswith(("/api/","/auth","/signin","/account","/studio/")):
                    seen.add(n); q.append((n,d+1))
            else:
                extern.setdefault(n,set()).add(u)
    internal_links=set()
    for rec in pages.values():
        for n in rec["links_out"]:
            if urlsplit(n).netloc in (HOST,"www."+HOST): internal_links.add(n)
    unfetched=[n for n in internal_links if n not in pages]
    link_status={}
    for n in unfetched[:200]:
        r=fetch(n, head=True, timeout=15)
        if r["status"] in (405,403,None): r=fetch(n, timeout=15)
        link_status[n]={"status":r["status"],"error":r["error"],"ms":r["ms"]}
    ext_status={}
    for n in list(extern)[:120]:
        r=fetch(n, head=True, timeout=15)
        if r["status"] in (405,403,None): r=fetch(n, timeout=15)
        ext_status[n]={"status":r["status"],"error":r["error"],"ms":r["ms"],"from":sorted(extern[n])}
    weights={}
    def asset_size(a):
        if a in assets_cache: return assets_cache[a]
        r=fetch(a, head=True, timeout=15)
        b=r["bytes"]
        if (r["status"] and r["status"]<400) and not b:
            r=fetch(a, timeout=20); b=r["bytes"]
        assets_cache[a]={"bytes":b,"status":r["status"],"error":r["error"]}
        return assets_cache[a]
    for u,rec in pages.items():
        if rec.get("status")!=200 or "text/html" not in (rec.get("ctype") or ""): continue
        w={"html":rec["html_bytes"],"images":0,"scripts":0,"css":0,"n_images":0,"n_scripts":0,"n_css":0,"missing":[]}
        for kind,key in (("images","imgs"),("scripts","scripts"),("css","css")):
            for a in dict.fromkeys(rec.get(key,[])):
                s=asset_size(a)
                if s["status"] and s["status"]>=400: w["missing"].append((a,s["status"]))
                w[kind]+=s["bytes"] or 0; w["n_"+kind]+=1
        w["total"]=w["html"]+w["images"]+w["scripts"]+w["css"]
        weights[u]=w
    json.dump({"sitemap":sitemap,"pages":[pages[u] for u in order],"link_status":link_status,"ext_status":ext_status,"weights":weights,"assets":assets_cache}, open(OUT,"w"), indent=1, default=list)
    print("pages",len(pages),"sitemap",len(sitemap),"unfetched internal checked",len(link_status),"external checked",len(ext_status))

# ---------------------------------------------------------------- browser mode
def SLUG(path):
    return ("home" if path in ("","/") else path.strip("/").replace("/","-"))

AUDIT_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const out = {scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth, clientWidth: vw,
               bodyScrollWidth: document.body ? document.body.scrollWidth : null, clipped: [], offRight: [], brokenImgs: [], h1: [], lcp: null};
  const sel = (el) => { let s = el.tagName.toLowerCase(); if (el.id) s += '#' + el.id; const c = (el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).slice(0,3); if (c.length) s += '.' + c.join('.'); return s; };
  // clipped text: overflow hidden / text-overflow ellipsis / line clamp, content wider/taller than its box
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect(); if (r.width <= 2 || r.height <= 2) continue;  // sr-only labels are 1x1 on purpose
    const ownText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    const hid = (cs.overflowX === 'hidden' || cs.overflowX === 'clip' || cs.textOverflow === 'ellipsis');
    if (hid && ownText && el.scrollWidth > el.clientWidth + 1)
      out.clipped.push({sel: sel(el), sw: el.scrollWidth, cw: el.clientWidth, text: el.textContent.trim().slice(0, 70), ellipsis: cs.textOverflow === 'ellipsis'});
    const clamp = cs.webkitLineClamp && cs.webkitLineClamp !== 'none';
    if ((clamp || cs.overflowY === 'hidden') && ownText && el.scrollHeight > el.clientHeight + 2 && cs.overflowY !== 'visible')
      out.clipped.push({sel: sel(el), sh: el.scrollHeight, ch: el.clientHeight, text: el.textContent.trim().slice(0, 70), vertical: true, clamp: !!clamp});
    // elements reaching past the right edge whose every ancestor lets them show (no hidden/auto/scroll overflow)
    if (r.right > vw + 1 && r.width < 4000) {
      let p = el.parentElement, contained = false;
      while (p && p !== document.body) { const pc = getComputedStyle(p); if (pc.overflowX !== 'visible') { contained = true; break; } p = p.parentElement; }
      if (!contained) out.offRight.push({sel: sel(el), right: Math.round(r.right), width: Math.round(r.width)});
    }
  }
  out.clipped = out.clipped.slice(0, 40); out.offRight = out.offRight.slice(0, 20);
  for (const img of document.images) { if (img.complete && img.naturalWidth === 0 && img.currentSrc) out.brokenImgs.push(img.currentSrc); }
  out.h1 = Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim().slice(0, 100));
  const vis = document.body.innerText;
  out.prices = Array.from(new Set((vis.match(/(\$\s?\d[\d,.]*(?:\s?\/\s?(?:mo|month|yr|year))?|\b\d[\d,]*\s+credits?\b)/gi) || []))).slice(0, 30);
  out.brand = (vis.match(/zero\s?-?page/gi) || []).length;
  const res = performance.getEntriesByType('resource');
  const nav = performance.getEntriesByType('navigation')[0];
  out.perf = {navTransfer: nav ? nav.transferSize : null, navEncoded: nav ? nav.encodedBodySize : null,
              resTransfer: res.reduce((a, e) => a + (e.transferSize || 0), 0),
              jsTransfer: res.filter(e => e.initiatorType === 'script' || /\.m?js(\?|$)/.test(e.name)).reduce((a, e) => a + (e.transferSize || 0), 0),
              jsEncoded: res.filter(e => /\.m?js(\?|$)/.test(e.name)).reduce((a, e) => a + (e.encodedBodySize || 0), 0),
              nRes: res.length, nJs: res.filter(e => /\.m?js(\?|$)/.test(e.name)).length,
              domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null, load: nav ? Math.round(nav.loadEventEnd) : null};
  return out;
}
"""

LCP_INIT = r"""
window.__lcp = null; window.__lcpEl = null;
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) { window.__lcp = e.startTime; window.__lcpEl = e.element ? (e.element.tagName + '.' + (e.element.getAttribute('class')||'').split(' ')[0]) : (e.url || null); } }).observe({type: 'largest-contentful-paint', buffered: true}); } catch (e) {}
"""

# computed colours of every element whose background or text uses the yellow accent, against its effective background
CONTRAST_JS = r"""
() => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const A = lum(a), B = lum(b); return (Math.max(A, B) + 0.05) / (Math.min(A, B) + 0.05); };
  const blend = (fg, bg) => ({r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1});
  const effBg = (el) => { const stack = []; let e = el; while (e) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; } e = e.parentElement; }
    let bg = {r: 255, g: 255, b: 255, a: 1}; for (let i = stack.length - 1; i >= 0; i--) bg = blend(stack[i], bg); return bg; };
  const isYellow = (c) => c && c.r > 200 && c.g > 150 && c.b < 120 && c.r - c.b > 120;
  const root = getComputedStyle(document.documentElement);
  const vars = {}; for (const v of ['--signal', '--signal-ink', '--bg', '--ink', '--ink-2', '--background', '--foreground', '--marigold']) vars[v] = root.getPropertyValue(v).trim();
  const sel = (el) => { let s = el.tagName.toLowerCase(); const c = (el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).slice(0,2); if (c.length) s += '.' + c.join('.'); return s; };
  const seen = {}; const rows = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const hasText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    const fg = parse(cs.color), bgOwn = parse(cs.backgroundColor);
    let kind = null, a = null, b = null;
    if (hasText && isYellow(fg)) { kind = 'yellow text'; b = effBg(el); a = blend(fg, b); }
    else if (hasText && bgOwn && bgOwn.a > 0.5 && isYellow(bgOwn)) { kind = 'text on yellow fill'; b = effBg(el); a = blend(fg, b); }
    if (!kind) continue;
    const ratioV = Math.round(ratio(a, b) * 100) / 100;
    const key = kind + '|' + cs.color + '|' + `${Math.round(b.r)},${Math.round(b.g)},${Math.round(b.b)}` + '|' + cs.fontSize;
    if (seen[key]) { seen[key].count++; continue; }
    const row = {kind, sel: sel(el), text: el.textContent.trim().slice(0, 40), fg: cs.color, bg: `rgb(${Math.round(b.r)}, ${Math.round(b.g)}, ${Math.round(b.b)})`, fontSize: cs.fontSize, fontWeight: cs.fontWeight, ratio: ratioV, count: 1};
    seen[key] = row; rows.push(row);
  }
  return {vars, bodyBg: getComputedStyle(document.body).backgroundColor, rows: rows.slice(0, 40)};
}
"""

def browser(crawl_json, OUT, screens, axe_path):
    import os

    from playwright.sync_api import sync_playwright
    data=json.load(open(crawl_json))
    pages=[p for p in data["pages"] if p.get("status")==200 and "text/html" in (p.get("ctype") or "")]
    # one row per final URL (a 308 lands on a page already listed)
    urls=[]; finals=set()
    for p in pages:
        f=p["final"].rstrip("/") or p["final"]
        if f in finals: continue
        finals.add(f); urls.append(p["final"])
    def is_top(path):
        return path.count("/")<=1 or path in ("/mcp/claude","/download/license")
    REP_MAKE=("/make/ai-video-generator","/make/photo-to-talking-video","/make/ai-halloween-costume-try-on")
    REP_MODELS=("/models/kling-4-video-generator","/models/grok-imagine-video-generator")
    AXE_EXTRA=("/make/ai-video-generator","/make/photo-to-talking-video","/make/ai-halloween-costume-try-on")
    axe_src=open(axe_path).read()
    results=[]
    os.makedirs(screens, exist_ok=True)
    with sync_playwright() as pw:
        b=pw.chromium.launch()
        for u in urls:
            path=urlsplit(u).path or "/"
            if path.startswith("/studio"): continue
            top=is_top(path); full = top or path in REP_MAKE or path in REP_MODELS
            widths=(1440,1280,390) if full else (390,)
            for w in widths:
                h={1440:900,1280:800,390:844}[w]
                ctx=b.new_context(viewport={"width":w,"height":h}, device_scale_factor=1, is_mobile=(w==390), has_touch=(w==390),
                                  user_agent=None if w!=390 else "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
                ctx.add_init_script(LCP_INIT)
                pg=ctx.new_page()
                cons=[]; failed=[]; resp_bytes={"total":0,"js":0,"n":0}
                pg.on("console", lambda m, cons=cons: cons.append({"type":m.type,"text":m.text[:300]}) if m.type in ("error",) else None)
                pg.on("pageerror", lambda e, cons=cons: cons.append({"type":"pageerror","text":str(e)[:300]}))
                def onresp(r, failed=failed, resp_bytes=resp_bytes):
                    try:
                        if r.status>=400: failed.append({"url":r.url[:200],"status":r.status})
                    except Exception: pass
                pg.on("response", onresp)
                # true bytes on the wire (cross-origin media reports transferSize 0 to the page), by CDP resource type
                cdp=ctx.new_cdp_session(pg); cdp.send("Network.enable"); net={}
                def on_resp(e, net=net): net.setdefault(e["requestId"], {"bytes":0,"done":False})["type"]=e.get("type"); net[e["requestId"]]["url"]=e["response"]["url"][:160]
                def on_data(e, net=net):
                    n=net.setdefault(e["requestId"], {"bytes":0,"done":False})
                    if not n["done"]: n["bytes"]+=e.get("encodedDataLength",0)
                def on_fin(e, net=net):
                    n=net.setdefault(e["requestId"], {"bytes":0}); n["bytes"]=max(n.get("bytes",0), e.get("encodedDataLength",0)); n["done"]=True
                cdp.on("Network.responseReceived", on_resp); cdp.on("Network.dataReceived", on_data); cdp.on("Network.loadingFinished", on_fin)
                def wire(net=net):
                    by={}
                    for n in net.values(): t=n.get("type") or "Other"; by[t]=by.get(t,0)+n["bytes"]
                    top=sorted(((n["bytes"],n.get("type"),n.get("url")) for n in net.values()), reverse=True)[:5]
                    return {"total":sum(by.values()),"by_type":by,"n":len(net),"top":top}
                pg.on("requestfailed", lambda r, failed=failed: failed.append({"url":r.url[:200],"status":"failed:"+(r.failure or "")[:60]}) if "_rsc" not in r.url else None)
                rec={"url":u,"path":path,"width":w}
                t0=time.time()
                try:
                    resp=pg.goto(u, wait_until="load", timeout=60000)
                    rec["status"]=resp.status if resp else None
                    try: pg.wait_for_load_state("networkidle", timeout=15000)
                    except Exception: rec["networkidle"]="timeout"
                    pg.wait_for_timeout(1500)
                    rec["load_s"]=round(time.time()-t0,2)
                    rec["lcp_ms"]=pg.evaluate("window.__lcp"); rec["lcp_el"]=pg.evaluate("window.__lcpEl")
                    rec["wire_initial"]=wire()
                    rec["audit"]=pg.evaluate(AUDIT_JS)
                    if w in (1440,390): rec["contrast"]=pg.evaluate(CONTRAST_JS)
                    if (top or path in AXE_EXTRA) and w in (1440,390):
                        pg.add_script_tag(content=axe_src)
                        ax=pg.evaluate("""async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}, resultTypes: ['violations']});
                            return {version: axe.version, violations: r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help, count: v.nodes.length, example: v.nodes[0] ? v.nodes[0].target.join(' ') : null, summary: v.nodes[0] ? (v.nodes[0].failureSummary||'').slice(0,240) : null}))}; }""")
                        rec["axe"]=ax
                    # scroll the page through once so lazy media loads, then measure transfer and shoot
                    pg.evaluate("async () => { const H = document.documentElement.scrollHeight; for (let y = 0; y < H; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); }")
                    pg.wait_for_timeout(1200)
                    rec["perf_after_scroll"]=pg.evaluate("() => { const res = performance.getEntriesByType('resource'); const nav = performance.getEntriesByType('navigation')[0]; return {total: (nav ? nav.transferSize : 0) + res.reduce((a, e) => a + (e.transferSize || 0), 0), js: res.filter(e => /\\.m?js(\\?|$)/.test(e.name)).reduce((a, e) => a + (e.transferSize || 0), 0), media: res.filter(e => /\\.(mp4|webm|mov)(\\?|$)/.test(e.name)).reduce((a, e) => a + (e.transferSize || 0), 0), n: res.length, biggest: res.map(e => [e.transferSize || 0, e.name.slice(0, 120)]).sort((a, b) => b[0] - a[0]).slice(0, 5)}; }")
                    rec["wire_after_scroll"]=wire()
                    shot=os.path.join(screens, f"{SLUG(path)}-{w}.png")
                    pg.screenshot(path=shot, full_page=True)
                    rec["screenshot"]=shot
                except Exception as e:
                    rec["error"]=repr(e)[:300]
                rec["console_errors"]=cons; rec["failed"]=failed
                results.append(rec)
                print(w, path, rec.get("status"), rec.get("lcp_ms"), rec.get("audit",{}).get("scrollWidth"), len(cons), flush=True)
                ctx.close()
        b.close()
    json.dump(results, open(OUT,"w"), indent=1)

# ---------------------------------------------------------------- extras mode
#   venv/bin/python -I crawl-2026-11-02.py extras <out.json> <screens_dir>
#   tap targets at 390, a 30-Tab focus walk at 1440, red fills, and the click path from a CTA to the sign-up wall
#   (links are followed; no form is filled or submitted).
TAP_JS = r"""
() => { const out = []; for (const el of document.querySelectorAll('a[href], button, input, select, textarea, [role=button], [role=tab], summary')) {
  const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue; const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
  if (el.closest('footer')) continue;
  const name = (el.getAttribute('aria-label') || el.textContent || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  out.push({tag: el.tagName.toLowerCase(), name, w: Math.round(r.width), h: Math.round(r.height)}); }
  const small = out.filter(t => t.w < 44 || t.h < 44), tiny = out.filter(t => t.w < 24 || t.h < 24);
  return {n: out.length, under44: small.length, under24: tiny.length, examples24: tiny.slice(0, 8), examples44: small.slice(0, 8)}; }
"""
RED_JS = r"""
() => { const rows = []; const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const red = (c) => c && c.a > 0.5 && c.r > 180 && c.g < 60 && c.b < 80;
  for (const el of document.querySelectorAll('body *')) { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue; const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const bg = parse(cs.backgroundColor), fg = parse(cs.color); const own = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
    if (red(bg)) rows.push({kind: 'red fill', tag: el.tagName.toLowerCase(), cls: (el.getAttribute('class') || '').slice(0, 60), text: el.textContent.trim().slice(0, 40), w: Math.round(r.width), h: Math.round(r.height)});
    else if (own && red(fg)) rows.push({kind: 'red text', tag: el.tagName.toLowerCase(), cls: (el.getAttribute('class') || '').slice(0, 60), text: el.textContent.trim().slice(0, 40)}); }
  return rows.slice(0, 15); }
"""
FOCUS_JS = r"""
() => { const el = document.activeElement; if (!el || el === document.body) return null; const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
  return {tag: el.tagName.toLowerCase(), name: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40), outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor, shadow: cs.boxShadow, visible: r.width > 0 && r.height > 0,
          ring: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== 'none')}; }
"""
def extras(OUT, screens):
    import os

    from playwright.sync_api import sync_playwright
    PAGES=["/","/pricing","/models","/mcp","/make","/make/ai-video-generator","/make/ai-halloween-costume-try-on","/models/grok-imagine-video-generator","/faq","/plugins"]
    res={"tap":{},"focus":{},"red":{},"paths":[]}
    with sync_playwright() as pw:
        b=pw.chromium.launch()
        m=b.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True, device_scale_factor=1)
        pg=m.new_page()
        for p in PAGES:
            pg.goto(BASE.rstrip("/")+p, wait_until="load"); pg.wait_for_timeout(1500)
            res["tap"][p]=pg.evaluate(TAP_JS); res["red"][p]=pg.evaluate(RED_JS)
        m.close()
        d=b.new_context(viewport={"width":1440,"height":900}, device_scale_factor=1)
        pg=d.new_page()
        for p in ("/","/pricing","/make/ai-video-generator","/mcp"):
            pg.goto(BASE.rstrip("/")+p, wait_until="load"); pg.wait_for_timeout(1500)
            walk=[]
            for i in range(30):
                pg.keyboard.press("Tab"); pg.wait_for_timeout(60); f=pg.evaluate(FOCUS_JS)
                if f: walk.append(f)
            res["focus"][p]=walk
        # the path from a CTA to the sign-up wall: follow links only, stop at the first page with a password or email field
        for start, pattern in (("/", r"^(Sign up|Try for free|Start creating|Get started)"), ("/make/ai-video-generator", r"^(Make a video|Sign up|Try)"), ("/pricing", r"^(Start|Choose|Get|Subscribe|Sign up)")):
            pg.goto(BASE.rstrip("/")+start, wait_until="load"); pg.wait_for_timeout(1200)
            steps=[{"url":pg.url}]
            loc=pg.get_by_role("link", name=re.compile(pattern, re.I)).or_(pg.get_by_role("button", name=re.compile(pattern, re.I))).first
            try:
                steps.append({"click":loc.inner_text(timeout=5000).strip()[:60], "href":loc.get_attribute("href")})
                loc.click(timeout=8000); pg.wait_for_load_state("load"); pg.wait_for_timeout(2500)
                steps.append({"url":pg.url, "title":pg.title(), "fields":pg.evaluate("() => Array.from(document.querySelectorAll('input')).filter(i => i.type !== 'hidden').map(i => i.type + ':' + (i.name || i.placeholder || i.getAttribute('aria-label') || ''))"),
                              "buttons":pg.evaluate("() => Array.from(document.querySelectorAll('button, a')).map(b => b.textContent.trim()).filter(t => /google|discord|email|sign|continue|create/i.test(t)).slice(0, 12)")})
                shot=os.path.join(screens, "signup-wall-from-"+SLUG(start)+"-1440.png"); pg.screenshot(path=shot); steps.append({"screenshot":shot})
            except Exception as e:
                steps.append({"error":repr(e)[:200]})
            res["paths"].append(steps)
        b.close()
    json.dump(res, open(OUT,"w"), indent=1)

if __name__=="__main__":
    if sys.argv[1]=="crawl": crawl(sys.argv[2])
    elif sys.argv[1]=="browser": browser(*sys.argv[2:6])
    elif sys.argv[1]=="extras": extras(*sys.argv[2:4])
