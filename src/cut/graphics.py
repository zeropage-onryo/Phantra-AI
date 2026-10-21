"""The editor's GRAPHICS track: motion graphics laid over the picture
(2026-10-20; BACKLOG #28, the motion-graphics layer; docs/tasks/task-motion-graphics.md).

A `graphic` track holds timed ITEMS the way a caption track holds cues:

    {"id": "G1", "kind": "graphic", "items": [
       {"id": "g1", "start": 0, "end": 60, "type": "headline",
        "text": "Find the right talent.", "position": "left",
        "anim_in": "rise", "anim_out": "fade", "size": "m", "color": "auto"},
       {"id": "g2", "start": 0, "end": 90, "type": "background_word",
        "text": "FIND", "anim_in": "fade", "anim_out": "fade", "drift": true},
       {"id": "g3", "start": 20, "end": 90, "type": "card", "media": "asset:7",
        "position": "right", "anim_in": "slide_left", "anim_out": "fade"}]}

Four types, the motion language of the Gygler reference:

  * headline        -- short kinetic text, the beat's line
  * background_word -- one oversized, faint word behind everything else
                       on the track below it, drifting slowly
  * card            -- a picture from the bin (a UI screenshot, a product
                       still) on a rounded card with a soft shadow
  * label           -- a small pill of text (a name, a price, a place)

HOW IT RENDERS. Nothing is generated. Each item is DRAWN ONCE, with Pillow,
as a canvas-sized transparent PNG with the item already at its resting
place (`draw`); the export then lays each PNG over the picture with
ffmpeg's `overlay`, moving it with an eased x/y expression and fading its
alpha in and out (`overlay_chain`). A brand kit, when the cut's project
has one, gives the fonts and colours (`Style.from_kit`); without one the
items are white in Pillow's own scalable font. Tracks stack in doc order:
G1 is drawn first, so a background word on G1 sits under a headline on G2.

A doc with no graphic track never reaches any of this: render.compile_args
builds exactly the argv it always did (tests/test_brand_kit_no_kit.py).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

TYPES = ("headline", "background_word", "card", "label")
POSITIONS = ("center", "left", "right", "top", "bottom", "lower_left")
ANIMS_IN = ("none", "fade", "rise", "slide_left", "slide_right")
ANIMS_OUT = ("none", "fade", "sink", "slide_left", "slide_right")
SIZES = ("s", "m", "l")
COLOR_ROLES = ("auto", "primary", "accent", "background", "text", "white", "black")
TEXT_MAX = 120
WORD_MAX = 24

# defaults per type: what a new item of that type starts as
DEFAULTS: dict[str, dict[str, Any]] = {
    "headline": {"position": "center", "anim_in": "rise", "anim_out": "fade", "size": "m"},
    "background_word": {"position": "center", "anim_in": "fade", "anim_out": "fade",
                        "size": "l", "drift": True},
    "card": {"position": "right", "anim_in": "slide_left", "anim_out": "fade", "size": "m"},
    "label": {"position": "lower_left", "anim_in": "fade", "anim_out": "fade", "size": "s"},
}

# how long a move takes, seconds, at most (a short item gets a third of
# its length each way)
MOVE_SECONDS = 0.5
# how far a move travels, as a fraction of the frame
RISE = 0.05
SLIDE = 0.28
DRIFT = 0.04
# the background word's ink, as alpha
WORD_ALPHA = 0.14


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def item_problems(t: dict, item: dict, out: list[str]) -> bool:
    """Append what is wrong with one item; True when it is usable. The
    validator (src/cut/validate.py) calls this for every graphic item."""
    from . import doc as d
    gid, tid = item.get("id") or "?", t.get("id")
    where = f"graphic {gid} on {tid}"
    ok = True
    if not (_is_int(item.get("start")) and _is_int(item.get("end"))):
        out.append(f"{where}: start and end must be whole frames")
        return False
    if item["start"] < 0 or item["end"] <= item["start"]:
        out.append(f"{where}: end must be after start, and start >= 0")
        ok = False
    kind = item.get("type")
    if kind not in TYPES:
        out.append(f"{where}: type must be one of {list(TYPES)}, got {kind!r}")
        return False
    text = item.get("text")
    if kind == "card":
        if d.parse_handle(item.get("media")) is None:
            out.append(f"{where}: a card needs a picture from the bin (gen:<id> or asset:<id>)")
            ok = False
        if text not in (None, "") and not isinstance(text, str):
            out.append(f"{where}: text must be text")
            ok = False
    else:
        if not isinstance(text, str) or not text.strip():
            out.append(f"{where}: text is empty")
            ok = False
        elif len(text) > (WORD_MAX if kind == "background_word" else TEXT_MAX):
            out.append(f"{where}: text is at most "
                       f"{WORD_MAX if kind == 'background_word' else TEXT_MAX} characters")
            ok = False
        if item.get("media") is not None:
            out.append(f"{where}: only a card takes a picture")
            ok = False
    for key, allowed in (("position", POSITIONS), ("anim_in", ANIMS_IN),
                         ("anim_out", ANIMS_OUT), ("size", SIZES)):
        if key in item and item[key] not in allowed:
            out.append(f"{where}: {key} must be one of {list(allowed)}, got {item[key]!r}")
            ok = False
    pill = item.get("pill", "auto")
    if pill not in COLOR_ROLES and not _hex(pill):
        out.append(f"{where}: pill must be a palette role ({', '.join(COLOR_ROLES)}) "
                   f"or #RRGGBB, got {pill!r}")
        ok = False
    color = item.get("color", "auto")
    if color not in COLOR_ROLES and not _hex(color):
        out.append(f"{where}: color must be a palette role ({', '.join(COLOR_ROLES)}) "
                   f"or #RRGGBB, got {color!r}")
        ok = False
    if "drift" in item and not isinstance(item["drift"], bool):
        out.append(f"{where}: drift must be true or false")
        ok = False
    return ok


def _hex(v) -> bool:
    if not isinstance(v, str) or len(v) != 7 or not v.startswith("#"):
        return False
    try:
        int(v[1:], 16)
        return True
    except ValueError:
        return False


def with_defaults(item: dict) -> dict:
    """The item with its type's defaults filled where it says nothing."""
    return {**DEFAULTS.get(item.get("type"), {}), "color": "auto", **item}


def handles(doc: dict) -> list[str]:
    """The pictures the cards on a doc name, in first-use order."""
    out: list[str] = []
    for t in doc.get("tracks", []):
        if t.get("kind") != "graphic":
            continue
        for item in t.get("items") or []:
            h = item.get("media")
            if h and h not in out:
                out.append(h)
    return out


def items_in_order(doc: dict) -> list[dict]:
    """Every graphic item, bottom of the stack first: track order, then
    start frame within a track."""
    out = []
    for t in doc.get("tracks", []):
        if t.get("kind") == "graphic":
            out.extend(sorted(t.get("items") or [], key=lambda i: (i["start"], i.get("id", ""))))
    return out


# --------------------------------------------------------------------------
# style: a brand kit's fonts and colours, or the studio's plain white
# --------------------------------------------------------------------------

@dataclass
class Style:
    heading_font: Optional[Path] = None
    body_font: Optional[Path] = None
    colours: dict = field(default_factory=dict)     # role -> #RRGGBB
    safe: float = 0.06

    @classmethod
    def from_kit(cls, kit: Optional[dict], fonts: Optional[dict] = None) -> "Style":
        """`fonts` is {"heading": Path, "body": Path}, the kit's files already
        written somewhere ffmpeg's working directory can reach."""
        if not kit:
            return cls()
        spec = kit.get("spec") or {}
        colours = {s["role"]: s["hex"] for s in spec.get("palette") or [] if s.get("role") != "extra"}
        fonts = fonts or {}
        safe = spec.get("safe_zone")
        return cls(heading_font=fonts.get("heading") or fonts.get("body"),
                   body_font=fonts.get("body") or fonts.get("heading"),
                   colours=colours, safe=float(safe) if safe is not None else 0.06)

    def colour(self, role: str, kind: str) -> str:
        if _hex(role):
            return role
        if role == "white":
            return "#FFFFFF"
        if role == "black":
            return "#000000"
        if role != "auto":
            return self.colours.get(role, "#FFFFFF")
        # auto: a kit's primary for headlines and the big word, its text for
        # a label; white with no kit
        if kind in ("headline", "background_word"):
            return self.colours.get("primary", "#FFFFFF")
        return self.colours.get("text", "#FFFFFF")

    @property
    def branded(self) -> bool:
        return bool(self.colours)


def _rgba(hex_colour: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), max(0, min(255, round(alpha * 255))))


def _luma(hex_colour: str) -> float:
    r, g, b, _ = _rgba(hex_colour)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def _font(path: Optional[Path], size: int):
    from PIL import ImageFont
    if path is not None:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    return ImageFont.load_default(size)


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if line and draw.textlength(trial, font=font) > max_w:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return [ln for ln in lines if ln] or [""]


# --------------------------------------------------------------------------
# drawing one item
# --------------------------------------------------------------------------

def _anchor(position: str, size: tuple[int, int], box: tuple[int, int], safe: float):
    """Top-left of a box of `box` size resting at `position` in the frame."""
    w, h = size
    bw, bh = box
    pad_x, pad_y = round(w * max(safe, 0.04)), round(h * max(safe, 0.04))
    x = {"left": pad_x, "lower_left": pad_x, "right": w - pad_x - bw}.get(position, (w - bw) // 2)
    y = {"top": pad_y, "bottom": h - pad_y - bh,
         "lower_left": h - pad_y - bh - round(h * 0.06)}.get(position, (h - bh) // 2)
    return x, y


def draw(item: dict, size: tuple[int, int], style: Style,
         picture: Optional[bytes] = None) -> bytes:
    """The item as a canvas-sized transparent PNG, at rest. Pure but for
    Pillow; `picture` is a card's image bytes."""
    from PIL import Image, ImageDraw, ImageFilter

    item = with_defaults(item)
    w, h = size
    unit = min(w, h)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    kind = item["type"]
    scale = {"s": 0.75, "m": 1.0, "l": 1.35}[item.get("size", "m")]
    ink = style.colour(item.get("color", "auto"), kind)

    if kind == "background_word":
        text = item["text"].strip().upper()
        font = _font(style.heading_font, round(unit * 0.42 * scale))
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        left, top, right, bottom = d.textbbox((0, 0), text, font=font)
        bw, bh = right - left, bottom - top
        x, y = _anchor(item.get("position", "center"), (w, h), (bw, bh), 0)
        d.text((x - left, y - top), text, font=font, fill=_rgba(ink, WORD_ALPHA))
        canvas.alpha_composite(layer)

    elif kind in ("headline", "label"):
        heading = kind == "headline"
        px = round(unit * (0.09 if heading else 0.045) * scale)
        font = _font(style.heading_font if heading else style.body_font, px)
        d = ImageDraw.Draw(canvas)
        side = item.get("position") in ("left", "right", "lower_left")
        max_w = round(w * (0.46 if side and heading else 0.8))
        lines = _wrap(d, item["text"].strip(), font, max_w)
        gap = round(px * 0.18)
        boxes = [d.textbbox((0, 0), ln, font=font) for ln in lines]
        line_h = max(b[3] - b[1] for b in boxes)
        bw = max(b[2] - b[0] for b in boxes)
        bh = line_h * len(lines) + gap * (len(lines) - 1)
        pad = round(px * 0.45) if not heading else 0
        x, y = _anchor(item.get("position", "center"), (w, h), (bw + 2 * pad, bh + 2 * pad),
                       style.safe)
        if not heading:
            # a label is a pill in the kit's primary colour, lettered in its
            # background colour (dark glass and white with no kit) -- the
            # pill must read on any picture, so it is never the background
            pill = style.colours.get("primary") if style.branded else None
            # an explicit pill colour (a label on a primary-coloured beat
            # takes the background colour, or the pill would vanish)
            if item.get("pill", "auto") != "auto":
                pill = style.colour(item["pill"], "label")
            fill = _rgba(pill, 0.95) if pill else (0, 0, 0, 150)
            if item.get("color", "auto") == "auto":
                ink = style.colours.get("background", "#FFFFFF") if pill else "#FFFFFF"
            if pill and abs(_luma(pill) - _luma(ink)) < 0.3:
                ink = "#111111" if _luma(pill) > 0.5 else "#FFFFFF"
            d.rounded_rectangle((x, y, x + bw + 2 * pad, y + bh + 2 * pad),
                                radius=round(px * 0.6), fill=fill)
        centred = item.get("position") in ("center", "top", "bottom")
        if heading and not style.branded:
            # plain white needs a soft shadow to read over any picture
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            for i, ln in enumerate(lines):
                lw = boxes[i][2] - boxes[i][0]
                lx = x + pad + ((bw - lw) // 2 if centred else 0)
                sd.text((lx - boxes[i][0], y + pad + i * (line_h + gap) - boxes[i][1] + round(px * 0.04)),
                        ln, font=font, fill=(0, 0, 0, 170))
            canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(px * 0.08)))
            d = ImageDraw.Draw(canvas)
        for i, ln in enumerate(lines):
            lw = boxes[i][2] - boxes[i][0]
            lx = x + pad + ((bw - lw) // 2 if centred else 0)
            d.text((lx - boxes[i][0], y + pad + i * (line_h + gap) - boxes[i][1]), ln,
                   font=font, fill=_rgba(ink))

    elif kind == "card":
        if picture:
            try:
                pic = Image.open(io.BytesIO(picture)).convert("RGBA")
            except Exception:
                pic = None
        else:
            pic = None
        if pic is not None:
            box_w = round(w * (0.42 if w >= h else 0.72) * scale)
            box_h = round(h * 0.6 * scale)
            pic.thumbnail((box_w, box_h), Image.LANCZOS)
            radius = round(unit * 0.025)
            mask = Image.new("L", pic.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, *pic.size), radius=radius, fill=255)
            x, y = _anchor(item.get("position", "right"), (w, h), pic.size, style.safe)
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            off = round(unit * 0.012)
            ImageDraw.Draw(shadow).rounded_rectangle(
                (x, y + off, x + pic.width, y + off + pic.height), radius=radius, fill=(0, 0, 0, 110))
            canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(unit * 0.02)))
            canvas.paste(pic, (x, y), mask)
            caption = (item.get("text") or "").strip()
            if caption:
                font = _font(style.body_font, round(unit * 0.03))
                d = ImageDraw.Draw(canvas)
                d.text((x, y + pic.height + round(unit * 0.02)), caption, font=font,
                       fill=_rgba(style.colour("auto", "label")))

    out = io.BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()


# --------------------------------------------------------------------------
# moving it: the overlay's expressions
# --------------------------------------------------------------------------

def _s(frames: int, fps: int) -> str:
    return f"{frames / fps:.6f}".rstrip("0").rstrip(".") or "0"


def timing(item: dict, fps: int) -> dict[str, float]:
    """Seconds: start, end, and how long the move in and the move out take."""
    item = with_defaults(item)
    start, end = item["start"] / fps, item["end"] / fps
    move = min(MOVE_SECONDS, (end - start) / 3)
    return {"start": start, "end": end,
            "in": 0.0 if item.get("anim_in") == "none" else move,
            "out": 0.0 if item.get("anim_out") == "none" else move}


def _num(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".") or "0"


def motion(item: dict, size: tuple[int, int], fps: int) -> tuple[str, str]:
    """The overlay's x and y, as ffmpeg expressions of `t`: 0 at rest, an
    eased offset while moving in or out. Pure."""
    item = with_defaults(item)
    w, h = size
    tm = timing(item, fps)
    s, e = tm["start"], tm["end"]
    xs, ys = [], []
    if tm["in"]:
        p = f"min(1,max(0,(t-{_num(s)})/{_num(tm['in'])}))"
        rest = f"pow(1-{p},3)"                 # 1 -> 0, eased out
        a = item["anim_in"]
        if a == "rise":
            ys.append(f"{_num(h * RISE)}*{rest}")
        elif a == "slide_left":                # comes in from the right
            xs.append(f"{_num(w * SLIDE)}*{rest}")
        elif a == "slide_right":
            xs.append(f"-{_num(w * SLIDE)}*{rest}")
    if tm["out"]:
        q = f"min(1,max(0,(t-{_num(e - tm['out'])})/{_num(tm['out'])}))"
        gone = f"pow({q},3)"                   # 0 -> 1, eased in
        a = item["anim_out"]
        if a == "sink":
            ys.append(f"{_num(h * RISE)}*{gone}")
        elif a == "slide_left":
            xs.append(f"-{_num(w * SLIDE)}*{gone}")
        elif a == "slide_right":
            xs.append(f"{_num(w * SLIDE)}*{gone}")
    if item.get("type") == "background_word" and item.get("drift", True):
        xs.append(f"-{_num(w * DRIFT)}*min(1,max(0,(t-{_num(s)})/{_num(e - s)}))")
    return ("+".join(xs) or "0", "+".join(ys) or "0")


def input_args(path: str, item: dict, fps: int) -> list[str]:
    """The ffmpeg input for one drawn item: the PNG held to the item's end."""
    tm = timing(item, fps)
    return ["-loop", "1", "-framerate", str(fps), "-t", _num(tm["end"]), "-i", str(path)]


def overlay_chain(base: str, items: list[dict], first_input: int, size: tuple[int, int],
                  fps: int, parts: list[str]) -> str:
    """Lay every drawn item over `base`, bottom first; append the filters to
    `parts` and return the label of the result. Input n+i is item i's PNG."""
    acc = base
    for i, item in enumerate(items):
        tm = timing(item, fps)
        fades = ["format=rgba"]
        if tm["in"]:
            fades.append(f"fade=t=in:st={_num(tm['start'])}:d={_num(tm['in'])}:alpha=1")
        if tm["out"]:
            fades.append(f"fade=t=out:st={_num(tm['end'] - tm['out'])}:d={_num(tm['out'])}:alpha=1")
        layer, out = f"gl{i}", f"go{i}"
        parts.append(f"[{first_input + i}:v]{','.join(fades)}[{layer}]")
        x, y = motion(item, size, fps)
        parts.append(f"[{acc}][{layer}]overlay=x='{x}':y='{y}':eval=frame:eof_action=pass:"
                     f"enable='between(t,{_num(tm['start'])},{_num(tm['end'])})'[{out}]")
        acc = out
    return acc


def prepare(doc: dict, work: Path, paths: dict, style: Style) -> list[dict]:
    """Draw every item into `work/graphics/`; [{item, path}] bottom first.
    `paths` maps a card's handle to its file. A card whose picture cannot be
    read draws nothing (an empty layer), never fails the export."""
    items = items_in_order(doc)
    if not items:
        return []
    folder = work / "graphics"
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, item in enumerate(items):
        picture = None
        if item.get("type") == "card" and item.get("media") in paths:
            try:
                picture = Path(paths[item["media"]]).read_bytes()
            except OSError:
                picture = None
        target = folder / f"g{i:03d}.png"
        target.write_bytes(draw(item, tuple(doc["size"]), style, picture))
        out.append({"item": item, "path": str(target)})
    return out
