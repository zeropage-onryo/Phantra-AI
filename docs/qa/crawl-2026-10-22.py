import json, re, sys, time, html
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl

HOST = "phantra.ai"
BASE = "https://phantra.ai/"
OUT = sys.argv[1]
CAP = 150
UA = "phantra-qa-crawl/2026-10-22 (+docs/qa)"
CTX = ssl.create_default_context()

MODEL_WORDS = [
 "Kling", "Veo", "Seedance", "LTX", "Wan", "FLUX", "Flux", "Seedream", "GPT Image", "GPT-Image",
 "Ideogram", "Nano Banana", "Gemini", "Topaz", "MMAudio", "PixVerse", "Luma", "Ray 2", "OmniHuman",
 "ElevenLabs", "Runway", "Sora", "MiniMax", "Hailuo", "Pika", "Imagen", "Hunyuan", "Mochi", "Whisper",
 "Claude", "ChatGPT", "Higgsfield", "Midjourney", "Recraft", "Stable Diffusion", "Sunburst", "Flare",
]
# name with optional version right after it
MODEL_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in MODEL_WORDS) + r")(?:[ \-]?(\d+(?:\.\d+)?(?:[ \-]?(?:Pro|Turbo|Fast|Flash|Lite|Std|Standard|Master|Flare|Sunburst|Max|Image|Pro Image))*)?)?", re.I)

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
        # pop stack to matching tag
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

seeds=[BASE, BASE+"pricing", BASE+"models", BASE+"faq", BASE+"connector", BASE+"mcp", BASE+"mcp/claude", BASE+"privacy", BASE+"terms", BASE+"make", BASE+"legal"]
pages={}; q=deque((s,0) for s in seeds); seen=set(seeds); extern={}; assets_cache={}
order=[]
while q and len(pages)<CAP:
    u,d=q.popleft()
    r=fetch(u)
    rec={"url":u,"depth":d,"status":r["status"],"final":r["final"],"ctype":r["ctype"],"html_bytes":r["bytes"],"ms":r["ms"],"error":r["error"],"links_out":[],"broken":[]}
    pages[u]=rec; order.append(u)
    if r["error"] and r["status"] is None: continue
    if "text/html" not in r["ctype"]: continue
    doc=r["body"].decode("utf-8","replace")
    p=P(); p.parse_err=None
    try: p.feed(doc)
    except Exception as e: p.parse_err=repr(e)
    text=" ".join(p.text)
    rec["title"]=p.title.strip(); rec["meta"]=p.meta
    rec["zeropage_html"]=len(re.findall("zeropage", doc, re.I))
    rec["zeropage_text"]=len(re.findall("zeropage", text, re.I))
    rec["zeropage_contexts"]=[doc[max(0,m.start()-60):m.end()+60].replace("\n"," ") for m in re.finditer("zeropage", doc, re.I)][:8]
    def models(ts):
        out=[]
        for m in MODEL_RE.finditer(ts):
            out.append(re.sub(r"\s+"," ",m.group(0)).strip())
        return sorted(set(out), key=str.lower)
    rec["models_all"]=models(text); rec["models_footer"]=models(" ".join(p.footer)); rec["models_marquee"]=models(" ".join(p.marquee))
    rec["imgs"]=[norm(i,u) for i in p.imgs if norm(i,u)]; rec["scripts"]=[norm(i,u) for i in p.scripts if norm(i,u)]; rec["css"]=[norm(i,u) for i in p.css if norm(i,u)]
    for l in p.links:
        n=norm(l,u)
        if not n: continue
        rec["links_out"].append(n)
        s=urlsplit(n)
        if s.netloc==HOST or s.netloc=="www."+HOST:
            if n not in seen and d<2:
                seen.add(n); q.append((n,d+1))
        else:
            extern.setdefault(n,set()).add(u)
# status of same-host links discovered beyond the cap/depth and all links: HEAD-check any internal link not fetched
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
# external links: HEAD check
ext_status={}
for n in list(extern)[:80]:
    r=fetch(n, head=True, timeout=15)
    if r["status"] in (405,403,None): r=fetch(n, timeout=15)
    ext_status[n]={"status":r["status"],"error":r["error"],"ms":r["ms"],"from":sorted(extern[n])}
# page weight: home and /make/*
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
    path=urlsplit(u).path
    if not (path=="/" or path.startswith("/make")): continue
    if rec.get("status")!=200: continue
    w={"html":rec["html_bytes"],"images":0,"scripts":0,"css":0,"n_images":0,"n_scripts":0,"n_css":0,"missing":[]}
    for kind,key in (("images","imgs"),("scripts","scripts"),("css","css")):
        for a in dict.fromkeys(rec.get(key,[])):
            s=asset_size(a)
            if s["status"] and s["status"]>=400: w["missing"].append((a,s["status"]))
            w[kind]+=s["bytes"] or 0; w["n_"+kind]+=1
    w["total"]=w["html"]+w["images"]+w["scripts"]+w["css"]
    weights[u]=w
json.dump({"pages":[pages[u] for u in order],"link_status":link_status,"ext_status":ext_status,"weights":weights,"assets":assets_cache}, open(OUT,"w"), indent=1, default=list)
print("pages",len(pages),"unfetched internal checked",len(link_status),"external checked",len(ext_status))
