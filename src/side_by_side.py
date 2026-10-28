"""
Before and after, side by side (2026-10-27, Mike: "Am I able to do the before and after").

One JPEG of two pictures the person already has -- the photo they started from and
what an effect made of it (the Halloween costume preview first) -- drawn here with
Pillow: both at one height, the original on the left, the result on the right, a
small "Before" / "After" on each. Free, no model, nothing stored: the studio's
"Download side-by-side" asks for it and the file goes straight to the person.

Pure: bytes in, bytes out. Who may read which picture is the caller's business
(app/api.py side_by_side reads only the caller's own render and photo).
"""
from __future__ import annotations

import io
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps

HEIGHT = 1280          # each half's height; a wide pair is scaled down to MAX_WIDTH
MAX_WIDTH = 2560
GAP = 8                # the seam between the two, in the ground colour
GROUND = (11, 10, 8)   # the site's warm black (#0b0a08)
MARIGOLD = (255, 194, 31)
QUALITY = 90


def _open(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)        # a phone photo stands the way it was taken
    return img.convert("RGB")


def _to_height(img: Image.Image, height: int) -> Image.Image:
    w = max(1, round(img.width * height / img.height))
    return img.resize((w, height), Image.LANCZOS)


def _label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, *, fill, ink, size: int) -> None:
    font = ImageFont.load_default(size=size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pad_x, pad_y = size // 2, size // 3
    x, y = xy
    box = (x, y, x + (right - left) + 2 * pad_x, y + (bottom - top) + 2 * pad_y)
    draw.rounded_rectangle(box, radius=size // 2, fill=fill)
    draw.text((x + pad_x - left, y + pad_y - top), text, font=font, fill=ink)


def compose(before: bytes, after: bytes, *, height: int = HEIGHT, labels: bool = True) -> Optional[bytes]:
    """The pair as one JPEG, or None when either picture cannot be read."""
    try:
        a, b = _open(before), _open(after)
    except Exception:
        return None
    a, b = _to_height(a, height), _to_height(b, height)
    width = a.width + GAP + b.width
    if width > MAX_WIDTH:                      # two wide frames: keep the file postable
        scale = (MAX_WIDTH - GAP) / (a.width + b.width)
        h = max(1, round(height * scale))
        a, b = _to_height(a, h), _to_height(b, h)
        width, height = min(MAX_WIDTH, a.width + GAP + b.width), h
    out = Image.new("RGB", (width, height), GROUND)
    out.paste(a, (0, 0))
    out.paste(b, (a.width + GAP, 0))
    if labels:
        draw = ImageDraw.Draw(out)
        size = max(14, height // 28)
        margin = max(10, height // 40)
        _label(draw, (margin, margin), "Before", fill=(0, 0, 0), ink=(255, 255, 255), size=size)
        _label(draw, (a.width + GAP + margin, margin), "After", fill=MARIGOLD, ink=GROUND, size=size)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return buf.getvalue()
