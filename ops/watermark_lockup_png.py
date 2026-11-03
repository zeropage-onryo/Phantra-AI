#!/usr/bin/env python3
"""
Draw src/assets/watermark_lockup.png: the Phantra lockup (the owl hiding behind
the hand-drawn lowercase "phantra", at rest) in the landing page's yellow, on a
transparent background -- the free plan's watermark since 2026-11-03 (Mike:
"the yellow logo one and replicate the lettering on the main landing page").

The geometry is read from web/src/components/owl-lockup-paths.ts, the same paths
the site header draws, so the mark and the site never disagree. Every path is
M / L / Z only, filled even-odd; the owl shows only outside the WALL (the
letters with a small gap), exactly as owl-lockup.tsx clips it.

    python3 ops/watermark_lockup_png.py          # rewrites the PNG
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PATHS = ROOT / "web" / "src" / "components" / "owl-lockup-paths.ts"
OUT = ROOT / "src" / "assets" / "watermark_lockup.png"
LEMON = (243, 244, 139)          # --lemon on the landing page (#f3f48b)
SCALE = 2.0                      # pixels per lockup unit (viewbox 960 x 204 -> 1920 x 408)


def _const(src: str, name: str) -> str:
    return re.search(rf'export const {name} = "([^"]+)"', src).group(1)


def _viewbox(src: str) -> tuple[float, float, float, float]:
    m = re.search(r"VIEWBOX = \{ x: (-?[\d.]+), y: (-?[\d.]+), w: ([\d.]+), h: ([\d.]+) \}", src)
    return tuple(float(v) for v in m.groups())


def _subpaths(d: str) -> list[list[tuple[float, float]]]:
    out, cur = [], []
    for cmd, x, y in re.findall(r"([MLZ])\s*(?:(-?[\d.]+)\s+(-?[\d.]+))?", d):
        if cmd == "M":
            if cur:
                out.append(cur)
            cur = [(float(x), float(y))]
        elif cmd == "L":
            cur.append((float(x), float(y)))
        else:
            if cur:
                out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _mask(d: str, size, origin) -> Image.Image:
    """The path filled even-odd, as an L mask."""
    ox, oy = origin
    mask = Image.new("L", size, 0)
    for poly in _subpaths(d):
        one = Image.new("L", size, 0)
        ImageDraw.Draw(one).polygon([((x - ox) * SCALE, (y - oy) * SCALE) for x, y in poly], fill=255)
        mask = ImageChops.logical_xor(mask.convert("1"), one.convert("1")).convert("L")
    return mask


def draw() -> Image.Image:
    src = PATHS.read_text()
    x, y, w, h = _viewbox(src)
    size = (int(round(w * SCALE)), int(round(h * SCALE)))
    word = _mask(_const(src, "WORD"), size, (x, y))
    owl = _mask(_const(src, "OWL"), size, (x, y))
    wall = _mask(_const(src, "WALL"), size, (x, y))
    shown = ImageChops.multiply(owl, ImageChops.invert(wall))      # owl outside the wall
    alpha = ImageChops.lighter(word, shown)
    im = Image.new("RGBA", size, (*LEMON, 0))
    im.putalpha(alpha)
    return im.crop(im.getbbox())


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = draw()
    img.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} {img.size}")
