"""A brand kit started from a website (2026-10-21, step 3 of
docs/tasks/task-brand-kit-import-and-chat.md; BACKLOG #28).

The page is RENDERED in headless Chromium (Playwright; Mike's call, option A:
the browser lives in the Fly image and an import runs as a job), then
measured: every colour weighed by the screen area it covers and by where it
sits (a button fill says more than a footer link), the fonts that set the
headings and the body, the logo element, and the page's own name and
description. What comes back is a `brand_kits.clean_spec`-valid spec, the
files by role, and the evidence for each colour -- how sure the import is
and why -- which the kit page shows (`spec["import"]`).

THE PAGE IS UNTRUSTED. Every request the browser makes goes through one
handler (`_guard`): it is fetched by Playwright itself with redirects OFF,
so every hop comes back through the handler, and each hop must be http(s),
carry no credentials and name a public host (`refbin.public_host`, the same
allow-list every fetcher here uses). Websockets are closed, service workers
blocked, a page gets `PAGE_SECONDS` and `MAX_BYTES`, and the site's FONT
FILES are never downloaded: a family found on Google Fonts is fetched from
Google (open licences), any other is named in the spec only.

Nothing here writes a row or spends. `app.brand_routes` turns the result
into a new kit; the eval in evals/brand_import/ scores it by hand (it reads
the web, so it never runs in CI).
"""
from __future__ import annotations

import colorsys
import io
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

PROBE = (Path(__file__).with_name("brand_import_probe.js")).read_text()

PAGE_SECONDS = 60            # the whole visit: load, settle, measure
NAV_SECONDS = 30             # the first load
MAX_BYTES = 25 << 20         # everything the page pulls in, together
MAX_RESPONSE = 10 << 20      # any one response
MAX_HOPS = 5                 # redirects followed for one request
VIEWPORT = {"width": 1366, "height": 900}
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 Phantra-brand-import")
GOOGLE_FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
GOOGLE_FONT_LICENCE = ("Google Fonts (open licence: SIL OFL 1.1 or Apache 2.0), "
                       "fetched from fonts.googleapis.com")

# what a colour's place on the page says about it being the brand's
WHERE_WEIGHT = {"button": 6.0, "header": 1.6, "heading": 1.8, "link": 2.0, "body": 1.0}
KIND_WEIGHT = {"bg": 1.0, "fill": 1.5, "text": 1.2, "border": 0.6}
NEUTRAL_CHROMA = 14.0        # Lab chroma under this is a grey, a white or a black
SAME_COLOUR = 8.0            # ΔE under this is one colour
DISTINCT = 25.0              # an accent is at least this far from the primary


class ImportRefused(ValueError):
    """An import that cannot start: the address, said in one line."""


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------

def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lab(rgb) -> tuple[float, float, float]:
    r, g, b = (_lin(v) for v in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b) -> float:
    la, lb = lab(a), lab(b)
    return math.dist(la, lb)


def chroma(rgb) -> float:
    _l, a, b = lab(rgb)
    return math.hypot(a, b)


def luminance(rgb) -> float:
    r, g, b = (_lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def hexof(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(int(v) for v in rgb))


def rgb_of(text: str) -> Optional[tuple[int, int, int]]:
    """A CSS colour value (hex or rgb()) as an RGB triple, or None."""
    text = (text or "").strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", text)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+%?))?\s*\)", text)
    if m:
        return tuple(min(255, int(m.group(i))) for i in (1, 2, 3))
    return None


def colour_word(rgb) -> str:
    """A plain name for a colour, for the palette's `name`."""
    r, g, b = (v / 255 for v in rgb)
    h, light, sat = colorsys.rgb_to_hls(r, g, b)
    if chroma(rgb) < NEUTRAL_CHROMA:
        return "White" if light > 0.92 else "Black" if light < 0.12 else (
            "Light grey" if light > 0.6 else "Dark grey" if light < 0.35 else "Grey")
    hue = h * 360
    names = ((15, "Red"), (40, "Orange"), (65, "Yellow"), (160, "Green"), (200, "Teal"),
             (255, "Blue"), (290, "Purple"), (335, "Pink"), (361, "Red"))
    name = next(n for limit, n in names if hue < limit)
    if name == "Orange" and light < 0.35:
        name = "Brown"
    return ("Dark " if light < 0.3 else "Light " if light > 0.75 else "") + name.lower()


@dataclass
class Cluster:
    rgb: tuple
    weight: float = 0.0
    area: float = 0.0
    kinds: dict = field(default_factory=dict)       # (kind, where) -> area

    def add(self, rgb, area: float, kind: str, where: str) -> None:
        w = area * WHERE_WEIGHT.get(where, 1.0) * KIND_WEIGHT.get(kind, 1.0)
        # the cluster keeps the colour that carries the most weight
        if w > self.weight:
            self.rgb = tuple(rgb)
        self.weight += w
        self.area += area
        self.kinds[(kind, where)] = self.kinds.get((kind, where), 0.0) + area

    def share(self, kind: str, where: Optional[str] = None) -> float:
        return sum(a for (k, w), a in self.kinds.items()
                   if k == kind and (where is None or w == where))


# the browser's own link colours: a page that never styled a link says nothing
BROWSER_DEFAULTS = {(0, 0, 238), (85, 26, 139), (0, 0, 255)}


def cluster(colours: list[dict]) -> list[Cluster]:
    """The page's colours merged where they are one to the eye (ΔE < 8)."""
    out: list[Cluster] = []
    for c in sorted(colours, key=lambda c: -c.get("area", 0)):
        rgb = tuple(c["rgb"])
        if rgb in BROWSER_DEFAULTS:
            continue
        home = next((k for k in out if delta_e(k.rgb, rgb) < SAME_COLOUR), None)
        if home is None:
            home = Cluster(rgb)
            out.append(home)
        home.add(rgb, float(c.get("area") or 0), c.get("kind") or "bg", c.get("where") or "body")
    return out


# --------------------------------------------------------------------------
# from what the page showed to a spec
# --------------------------------------------------------------------------

def pixel_shares(png: Optional[bytes], colours: int = 24) -> list[tuple[tuple, float]]:
    """The rendered screen's main colours and their share of the pixels."""
    if not png:
        return []
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        small = im.convert("RGB").resize((320, int(320 * im.height / max(1, im.width))))
    q = small.quantize(colors=colours, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()
    counts = q.getcolors() or []
    total = sum(n for n, _i in counts) or 1
    return [(tuple(palette[i * 3:i * 3 + 3]), n / total) for n, i in counts]


def logo_colours(png: Optional[bytes]) -> list[tuple[tuple, float]]:
    """A logo's opaque, coloured pixels by share (transparent and grey pixels
    left out): what colour the mark itself is."""
    if not png:
        return []
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        rgba = im.convert("RGBA")
        rgba.thumbnail((200, 200))
        raw = rgba.tobytes()             # RGBA, four bytes a pixel, any Pillow
        pixels = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] > 200]
    if not pixels:
        return []
    groups: list[list] = []
    for p in pixels[::2]:
        if chroma(p) < NEUTRAL_CHROMA:
            continue
        home = next((g for g in groups if delta_e(g[0], p) < 12), None)
        if home is None:
            groups.append([p, 1])
        else:
            home[1] += 1
    total = sum(n for _p, n in groups) or 1
    return sorted(((tuple(p), n / total) for p, n in groups), key=lambda t: -t[1])


def _rendered(rgb, pixels) -> float:
    return sum(s for p, s in pixels if delta_e(p, rgb) < 12)


def pick_roles(probe: dict, pixels, logo) -> dict:
    """{role: {rgb, why, confidence}} plus `candidates`, from the probe."""
    clusters = cluster(probe.get("colours") or [])
    if not clusters:
        raise ValueError("the page showed no colours")
    bgs = sorted(clusters, key=lambda k: -k.share("bg"))
    background = bgs[0]
    roles: dict[str, dict] = {"background": {
        "rgb": background.rgb, "confidence": "high" if _rendered(background.rgb, pixels) > 0.3
        else "medium", "why": f"the page background, {_pct(_rendered(background.rgb, pixels))} "
                              "of the first screens"}}
    texts = sorted((k for k in clusters if k.share("text") > 0
                    and contrast(k.rgb, background.rgb) >= 3), key=lambda k: -k.share("text"))
    if texts:
        total = sum(k.share("text") for k in clusters) or 1
        share = texts[0].share("text") / total
        roles["text"] = {"rgb": texts[0].rgb, "confidence": "high" if share > 0.5 else "medium",
                         "why": f"most of the page's text, {_pct(share)} of it"}

    # the CSS-var visibility gate: a custom property counts only when a rule
    # uses it AND its colour is one the page actually shows
    var_hits = []
    for v in probe.get("vars") or []:
        rgb = rgb_of(v.get("value"))
        if rgb and v.get("used"):
            var_hits.append((v["name"], rgb))
    theme = rgb_of((probe.get("meta") or {}).get("theme_color") or "")

    chromatic = [k for k in clusters if chroma(k.rgb) >= NEUTRAL_CHROMA and k is not background]
    scored = []
    for k in chromatic:
        score = k.weight
        why = []
        if k.share("bg", "button") or k.share("fill", "button"):
            why.append("the buttons")
        if k.share("text", "link") or k.share("text", "heading"):
            why.append("links and headings")
        on_screen = _rendered(k.rgb, pixels)
        score *= 1 + 4 * on_screen
        named = [n for n, rgb in var_hits if delta_e(rgb, k.rgb) < SAME_COLOUR]
        if named:
            score *= 1.5
            why.append(f"the site's {named[0]}")
        if theme and delta_e(theme, k.rgb) < SAME_COLOUR:
            score *= 1.3
            why.append("its theme colour")
        in_logo = sum(s for p, s in logo if delta_e(p, k.rgb) < 12)
        if in_logo > 0.25:
            score *= 1 + 2 * in_logo
            why.append(f"{_pct(in_logo)} of the logo")
        scored.append((score, k, why, on_screen, in_logo))
    scored.sort(key=lambda t: -t[0])

    candidates = [{"hex": hexof(k.rgb), "why": ", ".join(w) or "seen on the page"}
                  for _s, k, w, _o, _l in scored[:4]]
    if scored:
        total = sum(s for s, *_ in scored) or 1
        score, k, why, on_screen, in_logo = scored[0]
        share = score / total
        sure = ("high" if share > 0.55 and (in_logo > 0.25 or k.share("bg", "button"))
                else "medium" if share > 0.35 else "low")
        roles["primary"] = {"rgb": k.rgb, "confidence": sure,
                            "why": (", ".join(why) or "the most-seen colour")
                                   + f"; {_pct(share)} of the colour on the page"}
        accent = next(((s, k2, w2) for s, k2, w2, *_ in scored[1:]
                       if delta_e(k2.rgb, k.rgb) > DISTINCT), None)
        if accent:
            a_share = accent[0] / total
            roles["accent"] = {"rgb": accent[1].rgb,
                               "confidence": "medium" if a_share > 0.2 else "low",
                               "why": (", ".join(accent[2]) or "the next colour on the page")
                                      + f"; {_pct(a_share)} of the colour"}
    elif texts:
        roles["primary"] = {"rgb": texts[0].rgb, "confidence": "low",
                            "why": "the page shows no strong colour; its text colour stands in"}
    roles["candidates"] = candidates[1:4]
    return roles


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


def on_primary(rgb) -> tuple:
    """The WCAG rule for type on the primary: white or black, whichever
    reads better (4.5:1 or more is AA)."""
    return (255, 255, 255) if contrast((255, 255, 255), rgb) >= contrast((0, 0, 0), rgb) \
        else (0, 0, 0)


def pick_fonts(probe: dict) -> dict:
    """{heading, body}: the family that sets the most of each."""
    out = {}
    for role, places in (("heading", ("heading", "button")), ("body", ("body",))):
        totals: dict[str, float] = {}
        for f in probe.get("fonts") or []:
            if f.get("where") in places and f.get("family"):
                totals[f["family"]] = totals.get(f["family"], 0) + float(f.get("area") or 0)
        if totals:
            out[role] = max(totals, key=totals.get)
    if "heading" not in out and "body" in out:
        out["heading"] = out["body"]
    return out


GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "system-ui", "-apple-system",
                    "blinkmacsystemfont", "cursive", "fantasy", "ui-sans-serif", "ui-serif",
                    "arial", "helvetica", "helvetica neue", "times new roman", "georgia",
                    "segoe ui", "roboto mono"}


def site_name(meta: dict, host: str) -> str:
    for raw in (meta.get("site_name"), meta.get("title")):
        name = re.split(r"\s+[|–—\-:·]\s+", (raw or "").strip())[0].strip()
        if 1 < len(name) <= 60:
            return name
    return host.split(".")[0].capitalize() if host else "Imported kit"


def build(probe: dict, *, source: str, screenshot: Optional[bytes] = None,
          logo_png: Optional[bytes] = None) -> dict:
    """The kit a probe describes: {name, spec, files, fonts, notes}. `files`
    holds the logo; fonts are named here and fetched by `fetch_fonts`."""
    from . import brand_kits

    pixels = pixel_shares(screenshot)
    logo = logo_colours(logo_png)
    roles = pick_roles(probe, pixels, logo)
    candidates = roles.pop("candidates", [])
    meta = probe.get("meta") or {}
    host = (urlparse(source).hostname or "").removeprefix("www.")
    palette, evidence = [], {}
    names = {"primary": "Primary", "accent": "Accent", "background": "Background", "text": "Text"}
    for role in ("primary", "accent", "background", "text"):
        if role in roles:
            rgb = roles[role]["rgb"]
            palette.append({"hex": hexof(rgb), "role": role,
                            "name": f"{colour_word(rgb).capitalize()}"[:40] or names[role]})
            evidence[role] = {"why": roles[role]["why"][:200],
                              "confidence": roles[role]["confidence"]}
    notes = []
    if "primary" in roles:
        on = on_primary(roles["primary"]["rgb"])
        ratio = contrast(on, roles["primary"]["rgb"])
        if not any(s["hex"] == hexof(on) for s in palette):
            palette.append({"hex": hexof(on), "role": "extra",
                            "name": ("White" if on[0] else "Black") + " on primary"})
        notes.append(f"type on the primary: {hexof(on)} at {ratio:.2f}:1")
    if logo_png:
        evidence["logo"] = {"why": "the image in the page header" if probe.get("logo") else
                            "the page's mark", "confidence": "high" if probe.get("logo", {}).get(
                                "kind") in ("img", "svg") else "medium"}

    fonts = pick_fonts(probe)
    for role, family in fonts.items():
        evidence[f"font_{role}"] = {"why": f"{family} sets most of the "
                                           f"{'headings' if role == 'heading' else 'body text'}",
                                    "confidence": "medium"}
    description = " ".join((meta.get("description") or "").split())
    h1 = " ".join((meta.get("h1") or "").split())
    raw = {"identity": {"tagline": h1 if 3 <= len(h1) <= 120 else "",
                        "positioning": description[:200],
                        "url": host},
           "palette": palette,
           "captions": {"fill": "text" if "text" in roles else "primary"},
           "end_card": {"background": "background" if "background" in roles else "primary"},
           "import": {"source": source[:300],
                      "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "roles": evidence,
                      "candidates": [c for c in candidates
                                     if not any(c["hex"] == s["hex"] for s in palette[:1])][:4]}}
    spec = brand_kits.clean_spec(raw)
    files = logo_files(logo_png, roles, host) if logo_png else []
    return {"name": site_name(meta, host), "spec": spec, "files": files, "fonts": fonts,
            "notes": notes}


def _mark(png: bytes):
    """(mean luminance of the opaque pixels, one colour or None): whether a
    logo reads light or dark, and whether it is a single-colour mark."""
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        rgba = im.convert("RGBA")
    small = rgba.copy()
    small.thumbnail((160, 160))
    raw = small.tobytes()
    pixels = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] > 200]
    if not pixels:
        return 0.0, None
    mean = sum(luminance(p) for p in pixels) / len(pixels)
    first = pixels[len(pixels) // 2]
    one = all(delta_e(p, first) < 10 for p in pixels[::7])
    return mean, (first if one else None)


def _recolour(png: bytes, rgb) -> bytes:
    """A single-colour mark in another colour, its alpha kept."""
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        alpha = im.convert("RGBA").getchannel("A")
    out = Image.new("RGBA", alpha.size, tuple(int(v) for v in rgb) + (255,))
    out.putalpha(alpha)
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def logo_files(png: bytes, roles: dict, host: str) -> list[dict]:
    """The logo by role: a light mark is the logo for DARK backgrounds and a
    dark mark the one for light. A single-colour mark also gets the other
    variant, recoloured -- a white mark in the primary (or the text colour
    when the primary is too pale on white), a dark one in white -- so the
    kit has a logo for either card."""
    mean, one = _mark(png)
    name = host or "logo"
    light_mark = mean > 0.6
    files = [{"role": "logo_dark" if light_mark else "logo_light", "data": png,
              "filename": f"{name}.png"}]
    if one is not None:
        if light_mark:
            ink = (roles.get("primary") or {}).get("rgb")
            if not ink or contrast(ink, (255, 255, 255)) < 2:
                ink = (roles.get("text") or {}).get("rgb") or (20, 20, 20)
            files.append({"role": "logo_light", "data": _recolour(png, ink),
                          "filename": f"{name}-on-light.png"})
        else:
            files.append({"role": "logo_dark", "data": _recolour(png, (255, 255, 255)),
                          "filename": f"{name}-on-dark.png"})
    return files


# --------------------------------------------------------------------------
# fonts: Google's own files, never the site's
# --------------------------------------------------------------------------

def google_font(family: str, weight: int, *, get: Optional[Callable] = None) -> Optional[bytes]:
    """A Google Fonts family's TTF at one weight, or None when Google does not
    serve that family. Only Google's two hosts are ever asked."""
    if not family or family.strip().lower() in GENERIC_FAMILIES:
        return None
    import requests
    get = get or requests.get
    name = re.sub(r"[^A-Za-z0-9 ]", "", family).strip()
    if not name:
        return None
    for w in (weight, 400):
        css_url = (f"https://fonts.googleapis.com/css2?family={name.replace(' ', '+')}"
                   f":wght@{w}&display=swap")
        try:
            # an old user agent is answered with TTF rather than WOFF2
            resp = get(css_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        except Exception:
            return None
        if getattr(resp, "status_code", 500) != 200:
            continue
        m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", resp.text or "")
        if not m:
            continue
        try:
            font = get(m.group(1), timeout=15)
        except Exception:
            return None
        if getattr(font, "status_code", 500) == 200 and len(font.content) < (15 << 20):
            return font.content
    return None


def fetch_fonts(fonts: dict, *, get: Optional[Callable] = None) -> tuple[list[dict], list[str]]:
    """(files by role, notes): a family Google serves comes as its TTF; any
    other is only named, with the fallback the kit will use."""
    files, notes = [], []
    for role, weight in (("heading", 700), ("body", 400)):
        family = fonts.get(role)
        if not family:
            continue
        data = google_font(family, weight, get=get)
        if data:
            files.append({"role": f"font_{role}", "data": data,
                          "filename": f"{family.replace(' ', '')}-{weight}.ttf"})
        else:
            notes.append(f"{role} font {family}: not on Google Fonts, so not downloaded "
                         "(upload it on the kit page if you hold a licence; captions and the "
                         "end card use a default face until then)")
    return files, notes


# --------------------------------------------------------------------------
# the visit
# --------------------------------------------------------------------------

@dataclass
class Visit:
    blocked: list = field(default_factory=list)      # (url, why)
    bytes: int = 0
    started: float = field(default_factory=time.monotonic)


def check_address(url: str) -> str:
    """The address an import may start from, or ImportRefused."""
    from . import refbin
    url = (url or "").strip()
    if url and "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ImportRefused("give the website's address, like https://example.com")
    if parsed.username or parsed.password:
        raise ImportRefused("an address with a username or password in it is not taken")
    if not refbin.public_host(parsed.hostname):
        raise ImportRefused("that address is not on the public internet")
    return url


def _guard(visit: Visit, public: Callable[[str], bool]):
    """The one door every request of the page goes through."""
    def handle(route):
        req = route.request
        parsed = urlparse(req.url)
        if parsed.scheme in ("data", "blob", "about"):
            return route.continue_()

        def refuse(why: str):
            visit.blocked.append((req.url[:200], why))
            return route.abort("blockedbyclient")

        if parsed.scheme not in ("http", "https"):
            return refuse("not http(s)")
        if req.resource_type == "font":
            return refuse("font files are never downloaded")
        if req.resource_type in ("media", "websocket", "eventsource"):
            return refuse("not needed to read a brand")
        if parsed.username or parsed.password:
            return refuse("credentials in the address")
        if not parsed.hostname or not public(parsed.hostname):
            return refuse("not a public address")
        if time.monotonic() - visit.started > PAGE_SECONDS:
            return refuse("out of time")
        if visit.bytes > MAX_BYTES:
            return refuse("out of bytes")
        # Fetched HERE, one hop at a time with redirects off: a browser handed
        # a 3xx follows it without coming back through this door (the test
        # that showed it: tests/test_brand_import.py), so every hop is
        # checked here and the browser only ever sees the final answer.
        current = req.url
        for _hop in range(MAX_HOPS + 1):
            try:
                resp = route.fetch(url=current, max_redirects=0, timeout=15_000)
            except Exception:
                return refuse("no answer")
            if resp.status not in (301, 302, 303, 307, 308):
                break
            target = urljoin(current, resp.headers.get("location") or "")
            hop = urlparse(target)
            if hop.scheme not in ("http", "https") or hop.username or hop.password \
                    or not hop.hostname or not public(hop.hostname):
                visit.blocked.append((target[:200], "not a public address"))
                return route.abort("blockedbyclient")
            current = target
        else:
            return refuse("too many redirects")
        try:
            body = resp.body()
        except Exception:
            return refuse("no answer")
        if len(body) > MAX_RESPONSE:
            return refuse("too large")
        visit.bytes += len(body)
        headers = {k: v for k, v in resp.headers.items() if k.lower() != "location"}
        return route.fulfill(status=resp.status, headers=headers, body=body)
    return handle


_HIDE_OVERLAYS = """() => {
  const pick = (re) => [...document.querySelectorAll('button, a, [role=button]')]
    .find((b) => re.test((b.innerText || b.getAttribute('aria-label') || '').trim())
      && b.closest('[id*=cookie i], [class*=cookie i], [id*=consent i], [class*=consent i], '
        + '[id*=onetrust i], [class*=gdpr i], [aria-modal=true], [role=dialog]'));
  const ok = pick(/^(accept( all)?( cookies)?|agree|i agree|allow all|got it|ok(ay)?)$/i);
  if (ok) ok.click();
  const big = window.innerWidth * window.innerHeight * 0.3;
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if ((s.position === 'fixed' || s.position === 'sticky') && Number(s.zIndex) >= 100) {
      const r = el.getBoundingClientRect();
      if (r.width * r.height > big && el.tagName !== 'HEADER' && !el.querySelector('nav')) {
        el.style.setProperty('display', 'none', 'important');
      }
    }
  }
  document.documentElement.style.overflow = 'auto';
  document.body.style.overflow = 'auto';
  return !!ok;
}"""


_ISOLATE_LOGO = """() => {
  const mark = document.querySelector('[data-phantra-logo]');
  if (!mark) return;
  for (let el = mark.parentElement; el; el = el.parentElement) {
    el.style.setProperty('background', 'transparent', 'important');
    el.style.setProperty('box-shadow', 'none', 'important');
    el.style.setProperty('backdrop-filter', 'none', 'important');
  }
  for (const el of document.querySelectorAll('body *')) {
    if (el !== mark && !el.contains(mark) && !mark.contains(el)) {
      el.style.setProperty('visibility', 'hidden', 'important');
    }
  }
}"""


def visit_page(*, url: Optional[str] = None, html: Optional[str] = None,
               public: Optional[Callable[[str], bool]] = None,
               on_step: Optional[Callable[[str], None]] = None) -> dict:
    """Render one page and measure it: {probe, screenshot, logo_png, blocked,
    source}. `html` renders a fixture with no address of its own (tests).
    Raises ImportRefused when the page cannot be read."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    from . import refbin

    public = public or refbin.public_host
    say = on_step or (lambda _t: None)
    visit = Visit()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            # 2x, so the logo comes back sharp enough for an end card
            context = browser.new_context(viewport=VIEWPORT, user_agent=USER_AGENT,
                                          device_scale_factor=2,
                                          service_workers="block", java_script_enabled=True,
                                          accept_downloads=False)
            context.route("**/*", _guard(visit, public))
            try:
                context.route_web_socket("**/*", lambda ws: ws.close())
            except AttributeError:             # an older Playwright: websockets are
                pass                           # refused by resource type above
            page = context.new_page()
            page.set_default_timeout(NAV_SECONDS * 1000)
            try:
                if html is not None:
                    say("reading the page")
                    page.set_content(html, wait_until="load")
                else:
                    say("opening the website")
                    page.goto(url, wait_until="load", timeout=NAV_SECONDS * 1000)
            except PlaywrightError as e:
                if html is None:
                    raise ImportRefused(f"the website did not open: {str(e).splitlines()[0]}") \
                        from None
            page.wait_for_timeout(1200)        # late styles and hero images
            page.evaluate(_HIDE_OVERLAYS)
            page.wait_for_timeout(300)
            say("measuring colours, fonts and the logo")
            probe = page.evaluate(PROBE)
            # the rendered screen, through CDP, for the colours actually painted
            screenshot = page.screenshot(type="png", full_page=False)
            logo_png = None
            mark = page.query_selector("[data-phantra-logo]")
            if mark is not None:
                # the mark alone: whatever sits behind it (a coloured header,
                # the page) is made transparent first, so the PNG keeps only
                # the logo's own pixels
                page.evaluate(_ISOLATE_LOGO)
                try:
                    logo_png = mark.screenshot(type="png", omit_background=True)
                except PlaywrightError:
                    logo_png = None
            source = url or "about:blank"
        finally:
            browser.close()
    return {"probe": probe, "screenshot": screenshot, "logo_png": logo_png,
            "blocked": visit.blocked, "source": source}


def extract(html: Optional[str] = None, *, url: Optional[str] = None, fonts: bool = False,
            public: Optional[Callable[[str], bool]] = None,
            on_step: Optional[Callable[[str], None]] = None,
            get: Optional[Callable] = None) -> dict:
    """A kit from a page: {name, spec, files, notes, blocked}. Pass `html`
    (a fixture, rendered offline) or `url` (a website). `fonts=True` fetches
    the families Google serves."""
    if html is None:
        url = check_address(url or "")
    seen = visit_page(url=url, html=html, public=public, on_step=on_step)
    kit = build(seen["probe"], source=url or "about:blank", screenshot=seen["screenshot"],
                logo_png=seen["logo_png"])
    if fonts:
        if on_step:
            on_step("looking the fonts up on Google Fonts")
        files, notes = fetch_fonts(kit["fonts"], get=get)
        kit["files"] += files
        kit["notes"] += notes
    kit["blocked"] = seen["blocked"]
    return kit


def available() -> bool:
    """Whether this machine can run an import (Playwright and its browser)."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    return True


__all__ = ["ImportRefused", "available", "build", "check_address", "extract",
           "fetch_fonts", "google_font", "pick_roles", "visit_page"]

