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
blocked, a page gets `PAGE_SECONDS` and `MAX_BYTES` (and the whole visit, in a
child process, `HARD_SECONDS`), and the site's FONT
FILES are never downloaded: a family found on Google Fonts is fetched from
Google (open licences), any other is named in the spec only.

The colour scoring is the chat's extractor's (brandkit.zip, ported
2026-10-21 after this module's first scoring did worse on the same golden
set: 7/17 primaries exact against its 12/18; ported, 10/16 with the same six
misses), see `analyse`.

Nothing here writes a row or spends. `app.brand_routes` turns the result
into a new kit; the eval in evals/brand_import/ scores it by hand (it reads
the web, so it never runs in CI).
"""
from __future__ import annotations

import colorsys
import io
import json
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

PROBE = (Path(__file__).with_name("brand_import_probe.js")).read_text()

PAGE_SECONDS = 90            # requests are refused after this
HARD_SECONDS = 120           # the child process is killed past this, whatever it is doing
NAV_SECONDS = 30             # the first load
MAX_BYTES = 25 << 20         # everything the page pulls in, together
MAX_RESPONSE = 10 << 20      # any one response
MAX_HOPS = 5                 # redirects followed for one request
VIEWPORT = {"width": 1440, "height": 900}
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 Phantra-brand-import")
GOOGLE_FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
GOOGLE_FONT_LICENCE = ("Google Fonts (open licence: SIL OFL 1.1 or Apache 2.0), "
                       "fetched from fonts.googleapis.com")



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
    if chroma(rgb) < CHROMATIC:
        return "White" if light > 0.92 else "Black" if light < 0.12 else (
            "Light grey" if light > 0.6 else "Dark grey" if light < 0.35 else "Grey")
    hue = h * 360
    names = ((15, "Red"), (40, "Orange"), (65, "Yellow"), (160, "Green"), (200, "Teal"),
             (255, "Blue"), (290, "Purple"), (335, "Pink"), (361, "Red"))
    name = next(n for limit, n in names if hue < limit)
    if name == "Orange" and light < 0.35:
        name = "Brown"
    return ("Dark " if light < 0.3 else "Light " if light > 0.75 else "") + name.lower()


def ciede2000(rgb1, rgb2) -> float:
    """CIEDE2000 between two sRGB triples (Sharma, Wu and Dalal's formulation;
    the chat's extractor used scikit-image's, which this matches)."""
    L1, a1, b1 = lab(rgb1)
    L2, a2, b2 = lab(rgb2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    else:
        dhp = h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    else:
        hpm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hpm - 30)) + 0.24 * math.cos(math.radians(2 * hpm))
         + 0.32 * math.cos(math.radians(3 * hpm + 6)) - 0.20 * math.cos(math.radians(4 * hpm - 63)))
    dtheta = 30 * math.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / math.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


de = ciede2000


def lightness(rgb) -> float:
    return lab(rgb)[0]


def merge_weighted(items, thresh: float = 8.0) -> list[dict]:
    """items: (rgb, weight, meta). Greedy merge by CIEDE2000, heaviest colour
    keeps the hex: [{rgb, w, members}] by weight."""
    groups: list[dict] = []
    for rgb, w, meta in sorted(items, key=lambda x: -x[1]):
        rgb = tuple(int(v) for v in rgb[:3])
        for g in groups:
            if de(g["rgb"], rgb) < thresh:
                g["w"] += w
                g["members"].append(meta)
                break
        else:
            groups.append({"rgb": rgb, "w": w, "members": [meta]})
    return sorted(groups, key=lambda g: -g["w"])


# --------------------------------------------------------------------------
# from the evidence to roles -- the chat's scoring, ported (2026-10-21)
# --------------------------------------------------------------------------
# The chat's extractor (brandkit.zip, extractor/extract.py `analyse`) scored
# 12/18 official primaries exact against this module's first scoring's 7/17
# on the same golden set (evals/brand_import/), so its method is used as it
# was: a pool of candidates from every source (painted screen area, DOM
# area, buttons, CSS custom properties, theme colour, the logo's own pixels),
# a capped, additive brand score, and role rules. KMeans became Pillow's
# median cut (no scikit-learn in the app), snapped to declared colours.

# the browser's own link colours: a page that never styled a link says nothing
BROWSER_DEFAULTS = {(0, 0, 238), (85, 26, 139), (0, 0, 255)}
CHROMATIC = 18.0          # Lab chroma under this is a neutral: no brand score
NAME_HINT_PRIMARY = re.compile(r"(primary|brand|accent|main|key|cta|highlight|theme)", re.I)
NOISE_VAR = re.compile(r"(tw-|shadow|ring|gray|grey|neutral|slate|zinc|stone|black|white|error|"
                       r"danger|warning|success|info|red-|green-|blue-|yellow-|bs-(?!primary))", re.I)


def screen_clusters(png: Optional[bytes], dom_colours, media_rects=(), *, css_width: int,
                    k: int = 10) -> tuple[list[dict], float]:
    """The colours actually PAINTED on the page, photos and video masked out,
    the first screen counted double: ([{rgb, share}], masked share)."""
    if not png:
        return [], 0.0
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        img = im.convert("RGB")
    scale = 240 / img.width
    img = img.resize((240, max(1, int(img.height * scale))))
    css_scale = 240 / css_width            # page CSS px -> this image's px
    H = img.height
    weight = [[1] * 240 for _ in range(H)]
    for y in range(min(H, int(900 * css_scale))):
        weight[y] = [2] * 240
    for x, y, w, h in media_rects or []:
        x0, y0 = max(0, int(x * css_scale)), max(0, int(y * css_scale))
        x1, y1 = min(240, int((x + w) * css_scale) + 1), min(H, int((y + h) * css_scale) + 1)
        for yy in range(y0, y1):
            row = weight[yy]
            for xx in range(x0, x1):
                row[xx] = 0
    total = 240 * H
    kept = sum(1 for row in weight for v in row if v)
    masked = 1 - kept / total
    if kept / total < 0.05:                 # one big image (Discord): every pixel counts
        weight = [[max(1, v) for v in row] for row in weight]
        masked = -1.0
    raw = img.tobytes()
    pixels = bytearray()
    for y in range(H):
        for x in range(240):
            w = weight[y][x]
            if w:
                i = (y * 240 + x) * 3
                pixels += raw[i:i + 3] * w
    n = len(pixels) // 3
    strip = Image.frombytes("RGB", (n, 1), bytes(pixels))
    q = strip.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    # each bucket is reported as its most frequent EXACT pixel, not its mean:
    # flat UI colours repeat exactly, and a mean drifts toward whatever else
    # shares the bucket (cream toward the white type on its buttons)
    from collections import Counter
    modes: dict[int, Counter] = {}
    for i, idx in enumerate(q.tobytes()):
        modes.setdefault(idx, Counter())[bytes(pixels[i * 3:i * 3 + 3])] += 1
    out = []
    for idx, counter in modes.items():
        count = sum(counter.values())
        rgb = tuple(counter.most_common(1)[0][0])
        best = min(dom_colours, key=lambda d: de(d, rgb)) if dom_colours else None
        out.append((best if best is not None and de(best, rgb) < 6 else rgb, count / n, None))
    return [{"rgb": g["rgb"], "share": g["w"]} for g in merge_weighted(out, thresh=6)], masked


def logo_crop_colours(png: Optional[bytes]) -> list[tuple]:
    """Chromatic colours painted in the logo crop. Flat artwork repeats exact
    pixel values and anti-aliased edges do not, so the most frequent exact
    colours are taken (grouped at 3 bits a channel, reported as the modal
    pixel), the crop's border colour being its background."""
    if not png:
        return []
    from collections import Counter

    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        img = im.convert("RGB")
    w, h = img.size
    if w < 6 or h < 6:
        return []
    raw = img.tobytes()
    px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    border = px[:w] + px[-w:] + [px[y * w] for y in range(h)] + [px[y * w + w - 1] for y in range(h)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    fg = [p for p in px if math.dist(p, bg) > 40]
    if len(fg) < 30:
        return []
    bins = Counter((p[0] >> 3, p[1] >> 3, p[2] >> 3) for p in fg)
    out: list[tuple] = []
    for q, n in bins.most_common(6):
        if n / len(fg) < 0.08:
            break
        members = Counter(p for p in fg if (p[0] >> 3, p[1] >> 3, p[2] >> 3) == q)
        rgb = members.most_common(1)[0][0]
        if chroma(rgb) >= CHROMATIC and all(de(rgb, o) > 6 for o in out):
            out.append(rgb)
    return out


def _rgba3(v):
    return tuple(int(x) for x in v[:3]) if v else None


def analyse(ev: dict, *, screen: Optional[bytes], logo_crop: Optional[bytes],
            css_width: int) -> dict:
    """{primary, accents, surface, text, on_primary, roles: {name: {hex, why,
    confidence, ...}}, candidates, masked} from the probe's evidence."""
    bins: dict = {}
    for h in ev.get("colorHits") or []:
        rgb = _rgba3(h["rgba"])
        if rgb in BROWSER_DEFAULTS and h["kind"] in ("text", "border"):
            continue                      # an unstyled link says nothing about the brand
        k = bins.setdefault(rgb, {})
        k[h["kind"]] = k.get(h["kind"], 0) + h["w"]
    dom = [(rgb, sum(k.values()), k) for rgb, k in bins.items()]
    dom_total = sum(d[1] for d in dom) or 1
    dom_groups = merge_weighted([(r, w / dom_total, kinds) for r, w, kinds in dom], thresh=5)
    vis, masked = screen_clusters(screen, [g["rgb"] for g in dom_groups[:200]],
                                  ev.get("mediaRects") or [], css_width=css_width)
    css_vars = ([v for v in ev.get("cssVars") or [] if v.get("rgba")]
                + [v for v in ev.get("crossOriginVars") or []
                   if v.get("rgba") and v["rgba"][3] > 0.5])
    cta = ev.get("cta") or []
    cta_groups = merge_weighted([(_rgba3(c["rgba"]), c["area"] * (2 if c["top"] < 900 else 1), c)
                                 for c in cta], thresh=6)
    theme = [x for x in (ev.get("themeColorRgba"), ev.get("manifestThemeRgba")) if x]
    logo_fills = logo_crop_colours(logo_crop)
    if ev.get("logos") and ev["logos"][0].get("svg"):
        for m in re.findall(r'(?:fill|stroke)="(rgba?\([^)]*\))"', ev["logos"][0]["svg"]):
            nums = [float(x) for x in re.findall(r"[\d.]+", m)]
            if len(nums) >= 3 and (len(nums) < 4 or nums[3] > 0.5):
                logo_fills.append(tuple(int(n) for n in nums[:3]))

    pool = ([(g["rgb"], 0, "vis") for g in vis] + [(g["rgb"], 0, "dom") for g in dom_groups[:40]]
            + [(_rgba3(v["rgba"]), 0, "var") for v in css_vars]
            + [(g["rgb"], 0, "cta") for g in cta_groups[:5]]
            + [(_rgba3(t), 0, "theme") for t in theme] + [(f, 0, "logo") for f in logo_fills])
    cands = merge_weighted(pool, thresh=7)

    def near(rgb, rgbs, t=8):
        return any(de(rgb, x) < t for x in rgbs)

    cta_total = sum(g["w"] for g in cta_groups) or 1
    scored = []
    for c in cands:
        rgb = c["rgb"]
        vshare = sum(g["share"] for g in vis if de(g["rgb"], rgb) < 7)
        dshare = sum(g["w"] for g in dom_groups if de(g["rgb"], rgb) < 7)
        ctashare = sum(g["w"] for g in cta_groups if de(g["rgb"], rgb) < 8) / cta_total
        names = [v["name"] for v in css_vars if de(_rgba3(v["rgba"]), rgb) < 4]
        hint = (any(NAME_HINT_PRIMARY.search(n) and not NOISE_VAR.search(n) for n in names)
                and (vshare > 0.002 or dshare > 0.002))
        logo_de = min([de(rgb, f) for f in logo_fills] or [99])
        s = {"rgb": rgb, "chroma": chroma(rgb), "L": lightness(rgb), "visual_share": vshare,
             "dom_share": dshare, "cta_share": ctashare, "var_names": names[:6],
             "var_hint": hint, "theme_match": near(rgb, [_rgba3(t) for t in theme]),
             "logo_match": near(rgb, logo_fills, 10), "logo_dE": logo_de}
        s["brand_score"] = (min(vshare, 0.25) * 120 + min(dshare, 0.25) * 60 + ctashare * 25
                            + (15 if hint else 0) + (15 if s["theme_match"] else 0)
                            + (30 if logo_de < 3 else 20 if logo_de < 6 else 10 if logo_de < 10
                               else 0)) if s["chroma"] >= CHROMATIC else 0
        scored.append(s)
    if not scored:
        raise ValueError("the page showed no colours")

    surface = max(scored, key=lambda s: s["visual_share"])
    # Added to the chat's rules (2026-10-21, discord.com): the colour that IS
    # the page's background wins on area alone when the page is one big
    # picture, so it competes for primary at half score unless the buttons,
    # the logo, a brand-named variable or the theme colour back it
    if surface["brand_score"] and not (surface["cta_share"] > 0.3 or surface["logo_match"]
                                       or surface["theme_match"] or surface["var_hint"]):
        surface["brand_score"] *= 0.5
    chromatic = sorted((s for s in scored if s["brand_score"] > 0), key=lambda s: -s["brand_score"])
    primary = chromatic[0] if chromatic else None
    accents = ([s for s in chromatic[1:] if de(s["rgb"], primary["rgb"]) > 15][:2]
               if primary else [])
    text_groups = merge_weighted([(r, k.get("text", 0), None) for r, _w, k in dom if k.get("text")],
                                 thresh=5)
    readable = [g for g in text_groups if contrast(g["rgb"], surface["rgb"]) >= 4.5]
    text_rgb = (readable or sorted(text_groups, key=lambda g: -contrast(g["rgb"], surface["rgb"]))
                or [{"rgb": (17, 17, 17)}])[0]["rgb"]

    roles: dict = {}

    def why_of(s):
        bits = [f"{s['visual_share']:.0%} of the painted page" if s["visual_share"] >= 0.005 else "",
                f"{s['cta_share']:.0%} of the buttons" if s["cta_share"] >= 0.05 else "",
                f"the site's {s['var_names'][0]}" if s["var_hint"] and s["var_names"] else "",
                "its theme colour" if s["theme_match"] else "",
                "the logo's own colour" if s["logo_match"] else ""]
        return ", ".join(b for b in bits if b) or "seen on the page"

    on = None
    if primary:
        conf = ("high" if (primary["cta_share"] > 0.3 or primary["logo_match"]
                           or primary["theme_match"]) and primary["brand_score"] > 20
                else "medium" if primary["brand_score"] > 10 else "low")
        roles["primary"] = {"rgb": primary["rgb"], "confidence": conf,
                            "why": f"{why_of(primary)}; brand score {primary['brand_score']:.0f}"}
        # what the brand puts on its own buttons wins; else the most readable
        fgs = merge_weighted([(_rgba3(c["fg"]), c["area"], None) for c in cta
                              if c.get("fg") and c.get("text")
                              and de(_rgba3(c["rgba"]), primary["rgb"]) < 8], thresh=5)
        best = max([(255, 255, 255), (0, 0, 0), text_rgb, surface["rgb"]],
                   key=lambda c: contrast(c, primary["rgb"]))
        on = fgs[0]["rgb"] if fgs else best
        ratio = contrast(on, primary["rgb"])
        roles["on_primary"] = {
            "rgb": on, "accessible": best,
            "why": (f"on the brand's own buttons, {ratio:.2f}:1" if fgs else
                    f"the most readable on the primary, {ratio:.2f}:1")
                   + ("" if ratio >= 4.5 else f" -- below WCAG AA; {hexof(best)} reads at "
                                              f"{contrast(best, primary['rgb']):.2f}:1")}
    for s in accents[:1]:
        roles["accent"] = {"rgb": s["rgb"], "confidence": "medium",
                           "why": f"{why_of(s)}; brand score {s['brand_score']:.0f}"}
    roles["background"] = {"rgb": surface["rgb"], "confidence": "high",
                           "why": f"the largest painted area, {surface['visual_share']:.0%}"}
    roles["text"] = {"rgb": text_rgb, "confidence": "high",
                     "why": f"most of the text, {contrast(text_rgb, surface['rgb']):.1f}:1 "
                            "on the background"}
    candidates = [{"hex": hexof(s["rgb"]), "why": f"{why_of(s)}; brand score {s['brand_score']:.0f}"}
                  for s in chromatic[1:4]]
    return {"roles": roles, "candidates": candidates, "masked": masked}


def on_primary(rgb) -> tuple:
    """The WCAG rule for type on the primary: white or black, whichever
    reads better (4.5:1 or more is AA)."""
    return (255, 255, 255) if contrast((255, 255, 255), rgb) >= contrast((0, 0, 0), rgb) \
        else (0, 0, 0)


# --------------------------------------------------------------------------
# fonts -- the families that set the text, and a free fallback
# --------------------------------------------------------------------------

GOOGLE_FONTS = {f.lower(): f for f in json.loads(
    (Path(__file__).with_name("google_fonts.json")).read_text())}
GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "system-ui", "-apple-system",
                    "blinkmacsystemfont", "cursive", "fantasy", "ui-sans-serif", "ui-serif",
                    "segoe ui", "inherit", "initial"}
# hand-picked free lookalikes for common proprietary faces (the chat's table;
# a heuristic, said as one in the kit's notes)
LOOKALIKE = {
    "circular": "Figtree", "circular std": "Figtree", "graphik": "Inter", "gt america": "Inter",
    "gt walsheim": "DM Sans", "sf pro": "Inter", "sf pro display": "Inter", "helvetica neue": "Inter",
    "helvetica": "Inter", "arial": "Arimo", "proxima nova": "Montserrat", "avenir": "Nunito Sans",
    "avenir next": "Nunito Sans", "futura": "Jost", "gotham": "Montserrat",
    "brandon grotesque": "Josefin Sans", "sohne": "Inter", "söhne": "Inter", "aeonik": "Manrope",
    "basier circle": "Figtree", "cereal": "Nunito Sans", "airbnb cereal": "Nunito Sans",
    "uber move": "Inter", "netflix sans": "Inter", "din": "Barlow", "din next": "Barlow",
    "larsseit": "DM Sans", "sharp grotesk": "Space Grotesk", "gilroy": "Plus Jakarta Sans",
    "neue haas grotesk": "Inter", "ginto": "Manrope", "calibre": "Inter",
}


def font_norm(name: str) -> str:
    n = (name or "").lower().strip().strip("\"'")
    n = re.sub(r"[\s_-]*(variable|var|vf|web|webfont|text|display|regular|bold|medium|book|pro|"
               r"std|\d{2,3})$", "", n)
    n = re.sub(r"[-_]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def google_family(name: str) -> Optional[str]:
    """The Google Fonts family a site's font IS, or None."""
    n = font_norm(name)
    return GOOGLE_FONTS.get(n) or GOOGLE_FONTS.get((name or "").strip().lower())


def fallback_family(name: str) -> str:
    n = font_norm(name)
    for k, v in LOOKALIKE.items():
        if n == k or n.startswith(k):
            return v
    return "Inter"


def pick_fonts(ev: dict) -> dict:
    """{heading, body}: the webfont that actually renders each (the chat's
    rule: a face the page loaded or declared wins, else the stack's first)."""
    fonts = ev.get("fonts") or {}
    faces = fonts.get("faces") or []
    loaded = {f["family"].lower() for f in faces if f.get("status") == "loaded"}
    declared = {f["family"].lower() for f in faces}

    def fam(stack):
        return [f.strip().strip("\"'") for f in (stack or "").split(",") if f.strip()]

    def pick(stacks):
        for st in stacks or []:
            for f in fam(st.get("stack")):
                if f.lower() in loaded or f.lower() in declared:
                    return f
            first = (fam(st.get("stack")) or [None])[0]
            return first if first and first.lower() not in GENERIC_FAMILIES else None
        return None

    out = {}
    body = pick(fonts.get("body"))
    head = pick(fonts.get("heading")) or body
    if head:
        out["heading"] = head
    if body:
        out["body"] = body
    return out


def site_name(name: str, title: str, host: str) -> str:
    for raw in (name, title):
        n = re.split(r"\s+[|–—\-:·]\s+", (raw or "").strip())[0].strip()
        if 1 < len(n) <= 60:
            return n
    return host.split(".")[0].capitalize() if host else "Imported kit"


def build(seen: dict, *, source: str) -> dict:
    """The kit a visit describes: {name, spec, files, fonts, notes}."""
    from . import brand_kits

    ev = seen["probe"]
    found = analyse(ev, screen=seen.get("screen"), logo_crop=seen.get("logo_crop"),
                    css_width=seen.get("css_width") or VIEWPORT["width"])
    roles = found["roles"]
    host = (urlparse(source).hostname or "").removeprefix("www.")
    palette, evidence, notes = [], {}, []
    for role in ("primary", "accent", "background", "text"):
        if role in roles:
            rgb = roles[role]["rgb"]
            if any(s["hex"] == hexof(rgb) for s in palette):
                continue
            palette.append({"hex": hexof(rgb), "role": role,
                            "name": colour_word(rgb).capitalize()[:40]})
            evidence[role] = {"why": roles[role]["why"][:200],
                              "confidence": roles[role]["confidence"]}
    if "on_primary" in roles:
        on = roles["on_primary"]
        if not any(s["hex"] == hexof(on["rgb"]) for s in palette):
            palette.append({"hex": hexof(on["rgb"]), "role": "extra", "name": "On primary"})
        notes.append(f"type on the primary: {on['why']}")
    logo = seen.get("logo_png")
    if logo:
        evidence["logo"] = {"why": "the top-scored mark in the page header",
                            "confidence": "high" if (ev.get("logos") or [{}])[0].get("score", 0) >= 8
                            else "medium"}
    fonts = pick_fonts(ev)
    for role, family in fonts.items():
        evidence[f"font_{role}"] = {"why": f"{family} sets most of the "
                                           f"{'headings' if role == 'heading' else 'body text'}",
                                    "confidence": "high" if google_family(family) else "medium"}
    copy = ev.get("copy") or {}
    description = " ".join((copy.get("description") or "").split())
    h1 = " ".join(((copy.get("h1") or [""])[0] or "").split())
    raw = {"identity": {"tagline": h1 if 3 <= len(h1) <= 120 else "",
                        "positioning": description[:200], "url": host},
           "palette": palette[:8],
           "captions": {"fill": "text" if "text" in roles else "primary"},
           "end_card": {"background": "background" if "background" in roles else "primary"},
           "import": {"source": source[:300],
                      "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "roles": evidence,
                      "candidates": [c for c in found["candidates"]
                                     if not any(c["hex"] == s["hex"] for s in palette)][:4]}}
    spec = brand_kits.clean_spec(raw)
    files = logo_files(logo, roles, host) if logo else []
    return {"name": site_name(ev.get("siteName") or "", copy.get("title") or ev.get("title") or "",
                              host),
            "spec": spec, "files": files, "fonts": fonts, "notes": notes}


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
    """(files by role, notes): a family Google serves (the chat's list of
    1,950, src/google_fonts.json) comes as its TTF from Google; any other is
    only named, with the free lookalike captions can use meanwhile."""
    files, notes = [], []
    for role, weight in (("heading", 700), ("body", 400)):
        family = fonts.get(role)
        if not family:
            continue
        google = google_family(family)
        data = google_font(google, weight, get=get) if google else None
        if data:
            files.append({"role": f"font_{role}", "data": data,
                          "filename": f"{google.replace(' ', '')}-{weight}.ttf"})
        else:
            notes.append(f"{role} font {family}: not on Google Fonts, so not downloaded -- "
                         f"{fallback_family(family)} is a free lookalike (a guess); upload the "
                         "real font on the kit page if you hold a licence for video")
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
    """The one door every request of the page goes through. Async, so the
    page's requests are fetched side by side (with the sync API each handler
    waited for the last, and a heavy page ran out of time in the queue)."""
    import asyncio

    hosts: dict[str, bool] = {}

    async def is_public(host: str) -> bool:
        if host not in hosts:          # DNS off the event loop, once per host
            hosts[host] = await asyncio.get_running_loop().run_in_executor(None, public, host)
        return hosts[host]

    async def handle(route):
        req = route.request
        parsed = urlparse(req.url)
        if parsed.scheme in ("data", "blob", "about"):
            return await route.continue_()

        async def refuse(why: str):
            visit.blocked.append((req.url[:200], why))
            return await route.abort("blockedbyclient")

        if parsed.scheme not in ("http", "https"):
            return await refuse("not http(s)")
        if req.resource_type == "font":
            return await refuse("font files are never downloaded")
        if req.resource_type in ("media", "websocket", "eventsource"):
            return await refuse("not needed to read a brand")
        if parsed.username or parsed.password:
            return await refuse("credentials in the address")
        if not parsed.hostname or not await is_public(parsed.hostname):
            return await refuse("not a public address")
        if time.monotonic() - visit.started > PAGE_SECONDS:
            return await refuse("out of time")
        if visit.bytes > MAX_BYTES:
            return await refuse("out of bytes")
        # Fetched HERE, one hop at a time with redirects off: a browser handed
        # a 3xx follows it without coming back through this door (the test
        # that showed it: tests/test_brand_import.py), so every hop is
        # checked here and the browser only ever sees the final answer.
        current = req.url
        for _hop in range(MAX_HOPS + 1):
            try:
                resp = await route.fetch(url=current, max_redirects=0, timeout=15_000)
            except Exception:
                return await refuse("no answer")
            if resp.status not in (301, 302, 303, 307, 308):
                break
            target = urljoin(current, resp.headers.get("location") or "")
            hop = urlparse(target)
            if hop.scheme not in ("http", "https") or hop.username or hop.password \
                    or not hop.hostname or not await is_public(hop.hostname):
                visit.blocked.append((target[:200], "not a public address"))
                return await route.abort("blockedbyclient")
            current = target
        else:
            return await refuse("too many redirects")
        try:
            body = await resp.body()
        except Exception:
            return await refuse("no answer")
        if len(body) > MAX_RESPONSE:
            return await refuse("too large")
        visit.bytes += len(body)
        headers = {k: v for k, v in resp.headers.items() if k.lower() != "location"}
        return await route.fulfill(status=resp.status, headers=headers, body=body)
    handle.is_public = is_public
    return handle


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
    Raises ImportRefused when the page cannot be read.

    A real visit (the default host check) runs in a CHILD PROCESS,
    `python -m src.brand_import --visit URL`, in a process group of its own
    that is killed at HARD_SECONDS: the per-request limit refuses new
    requests but cannot stop a page that hangs a load or a script, and a
    stuck visit in the API process would hold its job forever (the
    2026-10-21 eval run sat 40 minutes on one site). It also keeps a browser
    crash out of the server. A caller passing its own `public` (the tests,
    with a lambda that cannot cross a process) runs in this process."""
    if public is not None:
        return _visit(url=url, html=html, public=public, on_step=on_step)
    import os
    import pickle
    import signal
    import subprocess
    import sys

    if on_step:
        on_step("opening the website")
    args = [sys.executable, "-m", "src.brand_import", "--visit", url or ""]
    child = subprocess.Popen(args, stdin=subprocess.PIPE if html is not None else None,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             cwd=str(Path(__file__).resolve().parent.parent),
                             start_new_session=True)
    try:
        raw, _ = child.communicate(input=(html or "").encode() if html is not None else None,
                                   timeout=HARD_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)        # the browser goes with it
        except OSError:
            child.kill()
        child.communicate()
        raise ImportRefused(f"the website did not finish loading in {HARD_SECONDS} seconds") \
            from None
    try:
        kind, value = pickle.loads(raw)                 # our own child's answer
    except Exception:
        raise ImportRefused("the browser stopped unexpectedly") from None
    if kind == "ok":
        if on_step:
            on_step("measuring colours, fonts and the logo")
        return value
    if kind == "refused":
        raise ImportRefused(value)
    raise ImportRefused(f"the website could not be read ({value})")


def _child_main(argv) -> int:
    """`python -m src.brand_import --visit URL` (HTML on stdin when URL is
    empty): one visit, its result pickled to stdout."""
    import pickle
    import sys
    url = argv[argv.index("--visit") + 1] if "--visit" in argv else ""
    html = sys.stdin.read() if not url else None
    try:
        result = ("ok", _visit(url=url or None, html=html, public=None, on_step=None))
    except ImportRefused as e:
        result = ("refused", str(e))
    except Exception as e:                          # noqa: BLE001 -- said to the parent
        result = ("failed", f"{type(e).__name__}: {(str(e).splitlines() or [''])[0][:200]}")
    sys.stdout.buffer.write(pickle.dumps(result))
    sys.stdout.flush()
    return 0


# the chat's consent handling and media mask, as it ran them
CONSENT_JS = r"""() => {
  const rx = /^(accept|allow all|allow cookies|i agree|agree|got it|ok|okay|alle akzeptieren|tout accepter)/i;
  const scopes = Array.from(document.querySelectorAll(
    '[id*=cookie i],[class*=cookie i],[id*=consent i],[class*=consent i],[id*=onetrust i],'
    + '[class*=didomi i],[aria-label*=cookie i],[role=dialog],[aria-modal=true]'));
  let clicked = 0;
  for (const s of scopes) {
    for (const b of s.querySelectorAll('button, a, [role=button]')) {
      if (rx.test((b.innerText || '').trim())) { try { b.click(); clicked++; } catch (e) {} break; }
    }
  }
  const vw = innerWidth, vh = innerHeight; let hidden = 0;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    const r = el.getBoundingClientRect();
    const bigCover = r.width >= vw * 0.9 && r.height >= vh * 0.6;
    const isDialog = el.matches('[role=dialog],[aria-modal=true],[id*=cookie i],[class*=cookie i],'
      + '[id*=consent i],[class*=consent i]');
    if (bigCover || (isDialog && cs.position === 'fixed')) {
      el.style.setProperty('display', 'none', 'important'); hidden++;
    }
  }
  document.documentElement.style.setProperty('overflow', 'auto', 'important');
  document.body.style.setProperty('overflow', 'auto', 'important');
  return {clicked, hidden};
}"""
HIDE_MEDIA_JS = r"""() => {
  const rects = [];
  const add = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width > 4 && r.height > 4) rects.push([r.left, r.top + window.scrollY, r.width, r.height]);
  };
  document.querySelectorAll('img,video,picture,canvas,iframe,object,embed').forEach(add);
  for (const el of document.querySelectorAll('*')) {
    const bi = getComputedStyle(el).backgroundImage;
    if (bi && bi.includes('url(')) add(el);
  }
  const st = document.createElement('style');
  st.id = 'phantra-hide-media';
  st.textContent = 'img,video,picture,canvas,iframe,object,embed{visibility:hidden!important}';
  document.head.appendChild(st);
  for (const el of document.querySelectorAll('*')) {
    const bi = getComputedStyle(el).backgroundImage;
    if (bi && bi.includes('url(')) el.style.setProperty('background-image', 'none', 'important');
  }
  return rects;
}"""
TO_RGBA_JS = r"""(vals) => {
  const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d');
  return vals.map(v => {
    let s = (v || '').trim();
    if (/^-?[\d.]+(deg)?\s+[\d.]+%\s+[\d.]+%$/.test(s)) s = `hsl(${s})`;
    if (!CSS.supports('color', s) || /var\(/.test(s)) return null;
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = s; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255];
  });
}"""


async def _shoot(page, height: int, clip: Optional[dict] = None) -> Optional[bytes]:
    """A screenshot through raw CDP -- it does not wait for animations or
    fonts to settle, which hangs on WebGL-heavy pages (the chat's finding on
    raycast.com) -- falling back to Playwright's."""
    import base64
    clip = clip or {"x": 0, "y": 0, "width": VIEWPORT["width"], "height": height}
    try:
        cdp = await page.context.new_cdp_session(page)
        res = await cdp.send("Page.captureScreenshot", {"format": "png",
                                                        "captureBeyondViewport": True,
                                                        "clip": {**clip, "scale": 1}})
        await cdp.detach()
        return base64.b64decode(res["data"])
    except Exception:
        try:
            return await page.screenshot(clip=clip, full_page=True, animations="disabled",
                                         timeout=15_000)
        except Exception:
            return None


async def _guarded_get(ctx, url: str, is_public, visit: Visit):
    """A stylesheet or a manifest the page named, fetched outside the page
    (APIRequestContext is not routed) -- so held to the same rules here:
    public hosts only, every redirect hop checked, a size cap."""
    current = url
    for _hop in range(MAX_HOPS + 1):
        parsed = urlparse(current)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password \
                or not parsed.hostname or not await is_public(parsed.hostname):
            visit.blocked.append((current[:200], "not a public address"))
            return None
        try:
            resp = await ctx.request.get(current, max_redirects=0, timeout=10_000)
        except Exception:
            return None
        if resp.status in (301, 302, 303, 307, 308):
            current = urljoin(current, resp.headers.get("location") or "")
            continue
        try:
            body = await resp.body()
        except Exception:
            return None
        if len(body) > MAX_RESPONSE:
            return None
        visit.bytes += len(body)
        return body
    return None


def _visit(*, url: Optional[str] = None, html: Optional[str] = None,
           public: Optional[Callable[[str], bool]] = None,
           on_step: Optional[Callable[[str], None]] = None) -> dict:
    """The visit itself, in whichever process `visit_page` chose."""
    import asyncio
    return asyncio.run(_avisit(url=url, html=html, public=public, on_step=on_step))


async def _avisit(*, url: Optional[str], html: Optional[str],
                  public: Optional[Callable[[str], bool]],
                  on_step: Optional[Callable[[str], None]]) -> dict:
    """Load, accept the consent banner, scroll the lazy content in, probe,
    then the logo crop and the painted screen with photos and video masked."""
    import json as json_mod

    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright

    from . import refbin

    public = public or refbin.public_host
    say = on_step or (lambda _t: None)
    visit = Visit()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
                                           args=["--disable-blink-features=AutomationControlled"])
        try:
            context = await browser.new_context(viewport=VIEWPORT, user_agent=USER_AGENT,
                                                locale="en-US", device_scale_factor=2,
                                                service_workers="block", accept_downloads=False)
            guard = _guard(visit, public)
            await context.route("**/*", guard)

            async def close_socket(ws):
                await ws.close()
            try:
                await context.route_web_socket("**/*", close_socket)
            except AttributeError:
                pass
            page = await context.new_page()
            page.set_default_timeout(NAV_SECONDS * 1000)
            try:
                if html is not None:
                    say("reading the page")
                    await page.set_content(html, wait_until="load")
                else:
                    say("opening the website")
                    await page.goto(url, wait_until="domcontentloaded",
                                    timeout=NAV_SECONDS * 1000)
            except PlaywrightError as e:
                if html is None:
                    raise ImportRefused(f"the website did not open: {str(e).splitlines()[0]}") \
                        from None
            try:
                await page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightError:
                pass
            await page.evaluate(CONSENT_JS)
            await page.wait_for_timeout(500)
            # lazy content in, then back to the top -- in ONE round trip: on a
            # page whose main thread is busy (raycast.com's WebGL) every trip
            # into the page costs seconds
            await page.evaluate("""async () => {
              const pause = (ms) => new Promise((ok) => setTimeout(ok, ms));
              for (let y = 0; y < 5000; y += 900) { window.scrollTo(0, y); await pause(100); }
              window.scrollTo(0, 0); await pause(600);
            }""")
            try:
                await page.wait_for_function('document.fonts.status === "loaded"', timeout=6000)
            except PlaywrightError:
                pass
            say("measuring colours, fonts and the logo")
            ev = await page.evaluate(PROBE)
            logo_crop = None
            if ev.get("logos"):
                bx = ev["logos"][0]["box"]
                logo_crop = await _shoot(page, 0, {"x": max(0, bx["x"] - 4),
                                                   "y": max(0, bx["y"] - 4),
                                                   "width": bx["w"] + 8, "height": bx["h"] + 8})
            ev["mediaRects"] = await page.evaluate(HIDE_MEDIA_JS)
            await page.wait_for_timeout(250)
            screen = await _shoot(page, min(int(ev.get("docH") or 900), 6000))
            # custom properties in stylesheets the page could not read (another
            # origin), and the web manifest's theme colour
            extra = []
            for href in (ev.get("blockedSheets") or [])[:12]:
                body = await _guarded_get(context, href, guard.is_public, visit)
                if body:
                    css = body.decode("utf-8", "replace")
                    for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;}{]+)", css):
                        extra.append({"name": name, "raw": val.strip()[:80]})
            if extra:
                vals = list({v["raw"] for v in extra})[:400]
                conv = dict(zip(vals, await page.evaluate(TO_RGBA_JS, vals)))
                for v in extra:
                    v["rgba"] = conv.get(v["raw"])
            ev["crossOriginVars"] = extra
            ev["manifestThemeRgba"] = None
            if ev.get("manifestUrl"):
                body = await _guarded_get(context, ev["manifestUrl"], guard.is_public, visit)
                try:
                    theme = json_mod.loads(body or b"{}").get("theme_color")
                except Exception:
                    theme = None
                if theme:
                    ev["manifestThemeRgba"] = (await page.evaluate(TO_RGBA_JS, [theme])
                                               or [None])[0]
            # the mark alone, its pictures shown again and everything else hidden
            logo_png = None
            mark = await page.query_selector("[data-phantra-logo]")
            if mark is not None:
                await page.evaluate("() => document.getElementById('phantra-hide-media')?.remove()")
                await page.evaluate(_ISOLATE_LOGO)
                try:
                    logo_png = await mark.screenshot(type="png", omit_background=True,
                                                     timeout=10_000)
                except PlaywrightError:
                    logo_png = None
            source = url or "about:blank"
        finally:
            await browser.close()
    return {"probe": ev, "screen": screen, "logo_crop": logo_crop, "logo_png": logo_png,
            "css_width": VIEWPORT["width"], "blocked": visit.blocked, "source": source}


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
    kit = build(seen, source=url or "about:blank")
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
           "fetch_fonts", "google_font", "analyse", "visit_page"]


if __name__ == "__main__":
    import sys as _sys
    raise SystemExit(_child_main(_sys.argv))
