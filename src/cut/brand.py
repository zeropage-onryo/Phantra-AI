"""A brand kit at Cut export: the `brand` caption style and the logo end card
(docs/tasks/task-brand-kit.md §6.6-6.7).

Pure pieces (`caption_style`, `end_card_png`, `with_end_card`) and one
preparer (`prepare`) that reads the kit's files into the export's working
directory. Nothing here runs for a cut whose project has no kit: the export
route asks `src.brand_kits.for_concept` first and passes `brand=None`, and
render() with `brand=None` is the render it always was.

The end card is added at EXPORT, not written into the timeline: the saved
versions stay exactly what the person edited, and switching the project to
another kit changes the next export with no edit. It is one still on V1 after
everything else, joined by the kit's transition; the cut grows by the card's
length (less the overlap), and the sound under it is the silence the mix
already pads to the end with (Mike's call, 2026-10-20).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Optional

from . import doc as d

END_CARD_HANDLE = "brand:end_card"
END_CARD_CLIP = "brand-end-card"
FONT_FALLBACK = "Arial"


def ass_colour(hex_colour: str, alpha: int = 0) -> str:
    """#RRGGBB -> ASS &HAABBGGRR (alpha 0 is opaque)."""
    h = (hex_colour or "#FFFFFF").lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _luma(hex_colour: str) -> float:
    h = (hex_colour or "#FFFFFF").lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _role(kit: dict, role: str, default: str) -> str:
    from .. import brand_kits
    return brand_kits.colour(kit, role, default)


def font_families(kit: dict) -> dict[str, str]:
    """{"heading": family, "body": family} from the kit's font files; a
    missing body falls back to the heading and vice versa."""
    from .. import brand_kits
    out = {}
    for which in ("heading", "body"):
        found = brand_kits.asset(kit, f"font_{which}")
        if found and (found.get("meta") or {}).get("family"):
            out[which] = found["meta"]["family"]
    out.setdefault("heading", out.get("body", FONT_FALLBACK))
    out.setdefault("body", out["heading"])
    return out


def caption_style(kit: dict) -> dict[str, Any]:
    """The kit's caption look, resolved to what an ASS Style line needs.
    Pure: colours by palette role, the font by family name."""
    spec = kit.get("spec") or {}
    cap = spec.get("captions") or {}
    safe = float(spec.get("safe_zone") if spec.get("safe_zone") is not None else 0.06)
    fill = _role(kit, cap.get("fill") or "text", "#FFFFFF")
    box_role, outline_role = cap.get("box") or "none", cap.get("outline") or "none"
    position = cap.get("position") or "bottom"
    align, margin = {"bottom": (2, safe + 0.06),
                     "lower_third": (1, max(safe, 0.12)),
                     "top": (8, safe + 0.02)}[position]
    return {"font": font_families(kit)[cap.get("font") or "heading"],
            "scale": float(cap.get("size") or 0.05),
            "fill": ass_colour(fill),
            "box": None if box_role == "none" else ass_colour(_role(kit, box_role, "#000000"), 0x22),
            "outline": (None if outline_role == "none"
                        else ass_colour(_role(kit, outline_role, "#000000"))),
            "align": align, "margin": margin, "side": max(safe, 0.04),
            "uppercase": bool(cap.get("uppercase"))}


# --------------------------------------------------------------------------
# the end card
# --------------------------------------------------------------------------

def _font(path: Optional[Path], size: int):
    from PIL import ImageFont
    if path is not None:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:                       # Pillow < 10.1
        return ImageFont.load_default()


def _fit_text(draw, text: str, font_path: Optional[Path], size: int, max_w: int):
    """The largest font at or under `size` whose line fits `max_w`."""
    while size > 10:
        font = _font(font_path, size)
        left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_w:
            return font
        size = int(size * 0.9)
    return _font(font_path, size)


def end_card_png(kit: dict, size: tuple[int, int], *, logo: Optional[bytes] = None,
                 logo_dark: Optional[bytes] = None, heading_font: Optional[Path] = None,
                 body_font: Optional[Path] = None) -> bytes:
    """The card as PNG bytes: the background-role colour, the logo that reads
    on it (the light-background logo on a light card), the tagline in the
    heading font and the url in the body font, all inside the safe zone."""
    from PIL import Image, ImageDraw

    w, h = size
    spec = kit.get("spec") or {}
    ident, card = spec.get("identity") or {}, spec.get("end_card") or {}
    safe = float(spec.get("safe_zone") if spec.get("safe_zone") is not None else 0.06)
    bg = _role(kit, card.get("background") or "background", "#FFFFFF")
    light_card = _luma(bg) >= 0.5
    ink = _role(kit, "text", "#111111" if light_card else "#FFFFFF")
    if abs(_luma(ink) - _luma(bg)) < 0.3:   # a text colour that vanishes on the card
        ink = "#111111" if light_card else "#FFFFFF"
    accent = _role(kit, "primary", ink)
    if abs(_luma(accent) - _luma(bg)) < 0.15:
        accent = ink

    image = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(image)
    inner_w = int(w * (1 - 2 * max(safe, 0.05)))
    unit = min(w, h)
    cursor = int(h * 0.5)

    chosen = (logo if light_card else logo_dark) or logo or logo_dark
    if chosen:
        try:
            mark = Image.open(io.BytesIO(chosen)).convert("RGBA")
            box_w, box_h = int(inner_w * 0.62), int(h * 0.26)
            mark.thumbnail((box_w, box_h), Image.LANCZOS)
            top = int(h * 0.44) - mark.height
            image.paste(mark, ((w - mark.width) // 2, max(int(h * safe), top)), mark)
            cursor = max(int(h * safe), top) + mark.height + int(unit * 0.05)
        except Exception:
            chosen = None
    if not chosen:
        name_font = _fit_text(draw, kit.get("name") or "", heading_font, int(unit * 0.12), inner_w)
        draw.text((w // 2, int(h * 0.42)), kit.get("name") or "", font=name_font, fill=accent,
                  anchor="ms")
        cursor = int(h * 0.42) + int(unit * 0.06)

    tagline = (ident.get("tagline") or "").strip()
    if tagline:
        font = _fit_text(draw, tagline, heading_font, int(unit * 0.055), inner_w)
        draw.text((w // 2, cursor), tagline, font=font, fill=accent, anchor="mt")
        bottom = draw.textbbox((w // 2, cursor), tagline, font=font, anchor="mt")[3]
        cursor = bottom + int(unit * 0.03)
    url = (ident.get("url") or "").strip()
    if url and card.get("show_url", True):
        font = _fit_text(draw, url, body_font or heading_font, int(unit * 0.032), inner_w)
        draw.text((w // 2, cursor), url, font=font, fill=ink, anchor="mt")
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def with_end_card(doc: dict, *, seconds: float, transition: str,
                  transition_seconds: float) -> dict:
    """The doc with the card appended on V1 after everything else. Pure; the
    saved doc is never touched (a deep enough copy is made here)."""
    fps = doc["fps"]
    length = max(1, round(seconds * fps))
    overlap = min(round(transition_seconds * fps), length - 1, doc["duration"])
    tracks, placed, pulled = [], False, 0
    for t in doc["tracks"]:
        t = {**t, "clips": list(t.get("clips") or [])} if "clips" in t else dict(t)
        if t.get("kind") == "video" and not placed:
            clip = {"id": END_CARD_CLIP, "media": END_CARD_HANDLE, "src_in": 0,
                    "src_out": length, "at": doc["duration"], "speed": 1}
            if overlap > 0 and t["clips"]:
                clip["transition_in"] = {"kind": "xfade", "frames": overlap,
                                         "style": transition or d.DEFAULT_TRANSITION_STYLE}
                pulled = overlap
            t["clips"].append(clip)
            placed = True
        tracks.append(t)
    if not placed:
        return doc
    # a crossfade pulls the card in by its overlap (render's xfade rule)
    return {**doc, "tracks": tracks, "duration": doc["duration"] + length - pulled}


# --------------------------------------------------------------------------
# preparing an export
# --------------------------------------------------------------------------

def prepare(kit: Optional[dict], work: Path, size: tuple[int, int], *,
            end_card: Optional[bool] = None) -> Optional[dict]:
    """Everything render() needs from a kit, written under `work`: the fonts
    in `work/fonts/` (for libass's fontsdir and the card), the card PNG, and
    the resolved caption style. None for no kit. `end_card` False leaves the
    card off for this export; None follows the kit."""
    if not kit:
        return None
    from .. import brand_kits
    fonts_dir = work / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    font_paths: dict[str, Path] = {}
    for which in ("heading", "body"):
        found = brand_kits.asset(kit, f"font_{which}")
        if not found:
            continue
        data = brand_kits.file_bytes(found["stored"], kit["account_id"])
        if data:
            target = fonts_dir / Path(found["stored"]).name
            target.write_bytes(data)
            font_paths[which] = target
    out: dict[str, Any] = {"kit": kit, "caption": caption_style(kit),
                           "fonts_dir": fonts_dir if font_paths else None,
                           "font_paths": font_paths, "end_card": None}
    spec = kit.get("spec") or {}
    card = spec.get("end_card") or {}
    on = card.get("on", True) if end_card is None else bool(end_card)
    if on:
        def logo(role):
            found = brand_kits.asset(kit, role)
            return brand_kits.file_bytes(found["stored"], kit["account_id"]) if found else None
        png = end_card_png(kit, size, logo=logo("logo_light"), logo_dark=logo("logo_dark"),
                           heading_font=font_paths.get("heading") or font_paths.get("body"),
                           body_font=font_paths.get("body") or font_paths.get("heading"))
        path = work / "brand_end_card.png"
        path.write_bytes(png)
        motion = spec.get("motion") or {}
        out["end_card"] = {"path": path, "seconds": float(card.get("seconds") or 2.5),
                           "transition": motion.get("transition") or d.DEFAULT_TRANSITION_STYLE,
                           "transition_seconds": float(motion.get("seconds") or 0.6)}
    return out
