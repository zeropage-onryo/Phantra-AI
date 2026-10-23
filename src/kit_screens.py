"""App screens drawn from a brand kit, in code (2026-10-22, docs/tasks/
task-kit-products-and-screens.md Part C).

Video and image models cannot draw readable UI: scene 442's tablet showed an
orange smear where the "Staffed" schedule was meant to be. The kit already
holds what a screen needs -- its palette, its heading and body fonts, its
logo -- so a screen is DRAWN here, with Pillow, from a small spec of plain
data, and filed in the Library as a picture like any other: a shot can be
held to it as its first reference, or it can be made an element.

It costs nothing. No ledger hold, no provider call, no model: a screen is a
layout of the kit's own type and colour. Three templates to start:

  schedule    a shift list -- rows of name, role, time and a status pill
              ("Staffed", "Open")
  list_cards  profile or listing cards -- a title, a line under it, a meta
              line and a tag
  hero_cta    a headline, a line of body copy and the kit's call to action
              as a button ("I Need Talent")

Sizes are a phone (1170x2532) and a tablet either way round (2048x1536,
1536x2048). The spec's words are checked against the kit's never-lists
(`voice.avoid`, `never_claim`): a hit is a WARNING on the card -- the words
are the brain's, and code advises -- never a refusal. A spec that is not one
of these shapes is refused, with what is wrong.

`clean`, `check_words` and `render` are pure (no database, no network); the
fonts and the logo are read off the kit by `kit_files`, and `keep` writes the
one file and the Library row.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Optional

TEMPLATES = ("schedule", "list_cards", "hero_cta")
SIZES = {"phone": (1170, 2532), "tablet": (2048, 1536), "tablet_portrait": (1536, 2048)}
LIBRARY_TOOL = "kit"
LIBRARY_MODEL = "kit screen"        # render_assets._label says "Kit screen"

MAX_ROWS = 8
MAX_CARDS = 6
TITLE_MAX = 40
LINE_MAX = 80
BODY_MAX = 160
BUTTON_MAX = 28
CELL_MAX = 32

# status words that read as done / waiting on the pill (anything else is neutral)
_GOOD = re.compile(r"(?i)\b(staffed|confirmed|booked|filled|done|paid|live|accepted)\b")
_WAIT = re.compile(r"(?i)\b(open|pending|needed|waiting|unfilled|requested)\b")


class ScreenError(ValueError):
    """A spec that is not a screen this module draws; the message says why."""


# --------------------------------------------------------------------------
# the spec
# --------------------------------------------------------------------------

def _text(value, field: str, limit: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ScreenError(f"{field} is text")
    text = " ".join(str(value).split())
    if re.search(r"(?i)\b(?:https?://|www\.)", text):
        raise ScreenError(f"{field} carries an address; a screen shows words, not links")
    if required and not text:
        raise ScreenError(f"{field} is needed")
    if len(text) > limit:
        raise ScreenError(f"{field} is at most {limit} characters")
    return text


def _items(value, field: str, limit: int, keys: dict) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ScreenError(f"{field} is a list of at least one")
    if len(value) > limit:
        raise ScreenError(f"{field} holds at most {limit}")
    out = []
    for i, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ScreenError(f"each of {field} is an object")
        first = next(iter(keys))             # the one cell a row cannot leave empty
        out.append({k: _text(item.get(k), f"{field} {i} {k}", cap, required=(k == first))
                    for k, cap in keys.items()})
    return out


def clean(raw) -> dict:
    """A screen spec, checked and bounded, or ScreenError naming what is wrong."""
    if not isinstance(raw, dict):
        raise ScreenError("a screen is described by an object")
    template = str(raw.get("template") or "").strip()
    if template not in TEMPLATES:
        raise ScreenError(f"template is one of {', '.join(TEMPLATES)}")
    device = str(raw.get("device") or "phone").strip()
    if device not in SIZES:
        raise ScreenError(f"device is one of {', '.join(SIZES)}")
    spec: dict[str, Any] = {"template": template, "device": device,
                            "title": _text(raw.get("title"), "title", TITLE_MAX,
                                           required=template != "hero_cta")}
    subtitle = _text(raw.get("subtitle"), "subtitle", LINE_MAX)
    if subtitle:
        spec["subtitle"] = subtitle
    if template == "schedule":
        spec["rows"] = _items(raw.get("rows"), "rows", MAX_ROWS,
                              {"name": CELL_MAX, "role": CELL_MAX, "time": CELL_MAX,
                               "status": CELL_MAX})
    elif template == "list_cards":
        spec["cards"] = _items(raw.get("cards"), "cards", MAX_CARDS,
                               {"title": CELL_MAX, "subtitle": LINE_MAX, "meta": CELL_MAX,
                                "tag": CELL_MAX})
    else:
        spec["headline"] = _text(raw.get("headline"), "headline", LINE_MAX, required=True)
        body = _text(raw.get("body"), "body", BODY_MAX)
        if body:
            spec["body"] = body
        spec["button"] = _text(raw.get("button"), "button", BUTTON_MAX, required=True)
        second = _text(raw.get("secondary"), "secondary", BUTTON_MAX)
        if second:
            spec["secondary"] = second
    return spec


def words_of(spec: dict) -> str:
    """Every word the screen shows, as one string."""
    parts = [str(v) for k, v in spec.items() if isinstance(v, str) and k not in
             ("template", "device")]
    for item in [*(spec.get("rows") or []), *(spec.get("cards") or [])]:
        parts.extend(str(v) for v in item.values())
    return " ".join(p for p in parts if p)


def check_words(spec: dict, kit: Optional[dict]) -> list[str]:
    """Advice for words the kit says never to use or claim. [] when clean."""
    if not kit:
        return []
    kspec = kit.get("spec") or {}
    shown = words_of(spec)
    out = []
    for word in (kspec.get("voice") or {}).get("avoid") or []:
        if word and re.search(rf"(?i)(?<!\w){re.escape(word)}(?!\w)", shown):
            out.append(f"the screen says “{word}”, a word the kit says never to use")
    for claim in kspec.get("never_claim") or []:
        if claim and re.search(rf"(?i)(?<!\w){re.escape(claim)}(?!\w)", shown):
            out.append(f"the screen makes a claim the kit says never to make: “{claim}”")
    return out


def summary(spec: dict) -> str:
    """One line for the card and the Library: what the screen shows."""
    what = {"schedule": f"{len(spec.get('rows') or [])}-row schedule",
            "list_cards": f"{len(spec.get('cards') or [])} cards",
            "hero_cta": "call to action"}[spec["template"]]
    head = spec.get("title") or spec.get("headline") or ""
    device = {"phone": "phone", "tablet": "tablet", "tablet_portrait": "tablet"}[spec["device"]]
    return f"{device} screen, {what}" + (f": {head}" if head else "")


# --------------------------------------------------------------------------
# colours
# --------------------------------------------------------------------------

def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = (hex_colour or "#FFFFFF").lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luma(hex_colour: str) -> float:
    r, g, b = (c / 255 for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ra, rb))


def palette(kit: Optional[dict]) -> dict[str, str]:
    """The screen's colours off the kit's palette roles, each checked to
    read on what it sits on: background, surface (a card), ink, muted ink,
    primary (buttons, pills) and the ink on a primary."""
    from . import brand_kits
    k = kit or {}
    bg = brand_kits.colour(k, "background", "#FFFFFF")
    light = _luma(bg) >= 0.5
    ink = brand_kits.colour(k, "text", "#151515" if light else "#FFFFFF")
    if abs(_luma(ink) - _luma(bg)) < 0.35:
        ink = "#151515" if light else "#FFFFFF"
    primary = brand_kits.colour(k, "primary", ink)
    if abs(_luma(primary) - _luma(bg)) < 0.12:
        primary = ink
    accent = brand_kits.colour(k, "accent", primary)
    on_primary = "#FFFFFF" if _luma(primary) < 0.6 else "#151515"
    surface = _mix(bg, "#FFFFFF" if light else "#000000", 0.75 if light else 0.35)
    if surface.upper() == bg.upper():
        surface = _mix(bg, ink, 0.05)
    return {"bg": bg, "surface": surface, "ink": ink, "muted": _mix(ink, bg, 0.45),
            "line": _mix(ink, bg, 0.85), "primary": primary, "on_primary": on_primary,
            "accent": accent, "wait": _mix(primary, bg, 0.75)}


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def _font(path: Optional[Path], size: int):
    from .cut.brand import _font as brand_font
    return brand_font(path, max(8, int(size)))


def _fit(draw, text: str, path: Optional[Path], size: int, max_w: int):
    from .cut.brand import _fit_text
    return _fit_text(draw, text, path, int(size), int(max_w))


def _clip(draw, text: str, font, max_w: int) -> str:
    """The text cut with an ellipsis to fit max_w (a row never wraps)."""
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(draw, text: str, font, max_w: int, lines: int) -> list[str]:
    out, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not line:
            line = trial
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = _clip(draw, out[-1] + " …", font, max_w)
    return out


def _pill(draw, x_right: int, y_mid: int, text: str, font, fill: str, ink: str, pad: int):
    w = int(draw.textlength(text, font=font)) + 2 * pad
    h = int(font.size * 1.6) if hasattr(font, "size") else 2 * pad
    box = (x_right - w, y_mid - h // 2, x_right, y_mid + h // 2)
    draw.rounded_rectangle(box, radius=h // 2, fill=fill)
    draw.text(((box[0] + box[2]) // 2, y_mid), text, font=font, fill=ink, anchor="mm")
    return box


def render(spec: dict, kit: Optional[dict], *, heading_font: Optional[Path] = None,
           body_font: Optional[Path] = None, logo: Optional[bytes] = None) -> bytes:
    """The screen as PNG bytes. Pure: the spec (already `clean`), the kit's
    palette and name, and the font files and logo handed in."""
    from PIL import Image, ImageDraw

    w, h = SIZES[spec["device"]]
    c = palette(kit)
    u = min(w, h) / 1170            # one phone-width unit
    pad = int(64 * u)
    body_font = body_font or heading_font
    image = Image.new("RGB", (w, h), c["bg"])
    draw = ImageDraw.Draw(image)

    # the app bar: the logo (else the kit's name in the heading font) and a dot of colour
    bar = int(150 * u) + (int(70 * u) if spec["device"] == "phone" else 0)
    top = bar - int(110 * u)
    placed = False
    if logo:
        try:
            mark = Image.open(io.BytesIO(logo)).convert("RGBA")
            mark.thumbnail((int(w * 0.38), int(80 * u)), Image.LANCZOS)
            image.paste(mark, (pad, top + (int(90 * u) - mark.height) // 2), mark)
            placed = True
        except Exception:                                   # noqa: BLE001
            placed = False
    if not placed:
        name = (kit or {}).get("name") or ""
        draw.text((pad, top + int(45 * u)), name, font=_font(heading_font, 60 * u),
                  fill=c["primary"], anchor="lm")
    r = int(30 * u)
    draw.ellipse((w - pad - 2 * r, top + int(45 * u) - r, w - pad, top + int(45 * u) + r),
                 fill=c["primary"])
    draw.line((0, bar, w, bar), fill=c["line"], width=max(1, int(2 * u)))

    y = bar + int(70 * u)
    inner = w - 2 * pad
    if spec.get("title"):
        font = _fit(draw, spec["title"], heading_font, 96 * u, inner)
        draw.text((pad, y), spec["title"], font=font, fill=c["ink"], anchor="lt")
        y = draw.textbbox((pad, y), spec["title"], font=font, anchor="lt")[3] + int(24 * u)
    if spec.get("subtitle"):
        font = _font(body_font, 40 * u)
        for line in _wrap(draw, spec["subtitle"], font, inner, 2):
            draw.text((pad, y), line, font=font, fill=c["muted"], anchor="lt")
            y += int(54 * u)
    y += int(40 * u)

    if spec["template"] == "schedule":
        _schedule(draw, spec["rows"], c, pad, y, w, h, u, heading_font, body_font)
    elif spec["template"] == "list_cards":
        _cards(draw, spec["cards"], c, pad, y, w, h, u, heading_font, body_font)
    else:
        _hero(draw, spec, c, pad, y, w, h, u, heading_font, body_font)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _status_colours(status: str, c: dict) -> tuple[str, str]:
    if _GOOD.search(status or ""):
        return c["primary"], c["on_primary"]
    if _WAIT.search(status or ""):
        return c["wait"], c["ink"]
    return c["line"], c["ink"]


def _schedule(draw, rows, c, pad, y, w, h, u, heading_font, body_font):
    gap = int(28 * u)
    room = h - y - pad
    row_h = int(min(230 * u, max(150 * u, (room - gap * (len(rows) - 1)) / max(1, len(rows)))))
    name_f, role_f = _font(heading_font, 50 * u), _font(body_font, 38 * u)
    time_f, pill_f = _font(body_font, 40 * u), _font(heading_font, 34 * u)
    for row in rows:
        if y + row_h > h - pad:
            break
        draw.rounded_rectangle((pad, y, w - pad, y + row_h), radius=int(36 * u),
                               fill=c["surface"], outline=c["line"], width=max(1, int(2 * u)))
        x = pad + int(44 * u)
        mid = y + row_h // 2
        # an avatar dot with the initial
        r = int(52 * u)
        draw.ellipse((x, mid - r, x + 2 * r, mid + r), fill=c["accent"])
        initial = (row["name"][:1] or "?").upper()
        draw.text((x + r, mid), initial, font=_font(heading_font, 48 * u),
                  fill=c["on_primary"] if _luma(c["accent"]) < 0.6 else c["ink"], anchor="mm")
        x += 2 * r + int(36 * u)
        right = w - pad - int(44 * u)
        pill = (0, 0, right, 0)
        if row.get("status"):
            fill, ink = _status_colours(row["status"], c)
            pill = _pill(draw, right, mid, row["status"], pill_f, fill, ink, int(30 * u))
        limit = pill[0] - int(30 * u)
        if row.get("time"):
            tw = int(draw.textlength(row["time"], font=time_f))
            draw.text((limit, mid), row["time"], font=time_f, fill=c["ink"], anchor="rm")
            limit -= tw + int(30 * u)
        draw.text((x, mid - int(8 * u)), _clip(draw, row["name"], name_f, limit - x),
                  font=name_f, fill=c["ink"], anchor="ls")
        if row.get("role"):
            draw.text((x, mid + int(14 * u)), _clip(draw, row["role"], role_f, limit - x),
                      font=role_f, fill=c["muted"], anchor="lt")
        y += row_h + gap


def _cards(draw, cards, c, pad, y, w, h, u, heading_font, body_font):
    cols = 2 if w > h else 1
    gap = int(32 * u)
    card_w = (w - 2 * pad - gap * (cols - 1)) // cols
    rows = -(-len(cards) // cols)
    card_h = int(min(380 * u, max(240 * u, (h - y - pad - gap * (rows - 1)) / max(1, rows))))
    title_f, sub_f = _font(heading_font, 54 * u), _font(body_font, 38 * u)
    meta_f, tag_f = _font(body_font, 36 * u), _font(heading_font, 32 * u)
    for i, card in enumerate(cards):
        col, row = i % cols, i // cols
        x0, y0 = pad + col * (card_w + gap), y + row * (card_h + gap)
        if y0 + card_h > h - pad:
            break
        draw.rounded_rectangle((x0, y0, x0 + card_w, y0 + card_h), radius=int(40 * u),
                               fill=c["surface"], outline=c["line"], width=max(1, int(2 * u)))
        draw.rounded_rectangle((x0, y0, x0 + int(18 * u), y0 + card_h), radius=int(9 * u),
                               fill=c["primary"])
        x, inner = x0 + int(60 * u), card_w - int(100 * u)
        ty = y0 + int(50 * u)
        draw.text((x, ty), _clip(draw, card["title"], title_f, inner), font=title_f,
                  fill=c["ink"], anchor="lt")
        ty += int(76 * u)
        for line in _wrap(draw, card.get("subtitle") or "", sub_f, inner, 2):
            draw.text((x, ty), line, font=sub_f, fill=c["muted"], anchor="lt")
            ty += int(52 * u)
        base = y0 + card_h - int(56 * u)
        if card.get("meta"):
            draw.text((x, base), _clip(draw, card["meta"], meta_f, inner // 2), font=meta_f,
                      fill=c["ink"], anchor="lm")
        if card.get("tag"):
            fill, ink = _status_colours(card["tag"], c)
            _pill(draw, x0 + card_w - int(40 * u), base, card["tag"], tag_f, fill, ink,
                  int(26 * u))


def _hero(draw, spec, c, pad, y, w, h, u, heading_font, body_font):
    inner = w - 2 * pad
    y = max(y, int(h * 0.30))
    head_f = _font(heading_font, 120 * u)
    for line in _wrap(draw, spec["headline"], head_f, inner, 4):
        draw.text((pad, y), line, font=head_f, fill=c["ink"], anchor="lt")
        y += int(140 * u)
    if spec.get("body"):
        y += int(20 * u)
        body_f = _font(body_font, 46 * u)
        for line in _wrap(draw, spec["body"], body_f, inner, 4):
            draw.text((pad, y), line, font=body_f, fill=c["muted"], anchor="lt")
            y += int(64 * u)
    y += int(80 * u)
    bh = int(150 * u)
    btn_w = min(inner, int(w * 0.62)) if w > h else inner
    draw.rounded_rectangle((pad, y, pad + btn_w, y + bh), radius=bh // 2, fill=c["primary"])
    btn_f = _fit(draw, spec["button"], heading_font, 56 * u, btn_w - int(80 * u))
    draw.text((pad + btn_w // 2, y + bh // 2), spec["button"], font=btn_f,
              fill=c["on_primary"], anchor="mm")
    if spec.get("secondary"):
        y += bh + int(36 * u)
        draw.rounded_rectangle((pad, y, pad + btn_w, y + bh), radius=bh // 2,
                               outline=c["ink"], width=max(2, int(4 * u)))
        sec_f = _fit(draw, spec["secondary"], heading_font, 52 * u, btn_w - int(80 * u))
        draw.text((pad + btn_w // 2, y + bh // 2), spec["secondary"], font=sec_f,
                  fill=c["ink"], anchor="mm")


# --------------------------------------------------------------------------
# the kit's files, and keeping one
# --------------------------------------------------------------------------

def kit_files(kit: Optional[dict], work: Path) -> dict:
    """The kit's heading and body fonts as files under `work` and its logo
    as bytes (the one that reads on the screen's background), each None
    when the kit has none or it cannot be read."""
    from . import brand_kits
    out: dict = {"heading_font": None, "body_font": None, "logo": None}
    if not kit:
        return out
    work.mkdir(parents=True, exist_ok=True)
    for which in ("heading", "body"):
        found = brand_kits.asset(kit, f"font_{which}")
        data = brand_kits.file_bytes(found["stored"], kit["account_id"]) if found else None
        if data:
            target = work / Path(found["stored"]).name
            target.write_bytes(data)
            out[f"{which}_font"] = target
    light = _luma(palette(kit)["bg"]) >= 0.5
    for role in (("logo_light", "logo_dark") if light else ("logo_dark", "logo_light")):
        found = brand_kits.asset(kit, role)
        data = brand_kits.file_bytes(found["stored"], kit["account_id"]) if found else None
        if data:
            out["logo"] = data
            break
    return out


def draw(spec: dict, kit: Optional[dict]) -> bytes:
    """`render` with the kit's own fonts and logo. Free; writes nothing
    that outlives the call."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="phantra-screen-") as tmp:
        files = kit_files(kit, Path(tmp))
        return render(spec, kit, **files)


def keep(spec: dict, kit: dict, *, account_id: Optional[int],
         dsn: Optional[str] = None) -> dict:
    """Draw the screen and file it in the Library (a still, model "kit
    screen", no provider and no credits), so a shot can be held to it or
    it can be made an element. Returns {"asset_id", "stored", "url",
    "summary"}; the PNG exists whether or not the bookkeeping did."""
    from . import generative, media, render_assets, render_names, watermark
    from .cut.sources import RENDERS_DIR
    from .shot import Shot
    png = draw(spec, kit)
    out_dir = Path(RENDERS_DIR) / "kit"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = render_names.unguessable(f"screen-{spec['template']}-k{kit['id']}") + ".png"
    path = out_dir / name
    path.write_bytes(png)
    tail = f"renders/kit/{name}"
    stored = f"/{tail}"
    # a free trial's still goes up marked, as every published still does
    # (src/watermark.py); a model reading it gets the clean original
    if watermark.publish_file(path, tail, account_id, "image/png") is None:
        media.mirror(path, tail, account_id, content_type="image/png")
    text = f"Kit screen ({kit['name']}): {summary(spec)}"
    params = {"provider": LIBRARY_TOOL, "model": LIBRARY_MODEL, "source": "studio",
              "brand_kit": {"id": kit["id"], "hash": kit.get("hash")}, "screen": spec}
    asset_id = None
    try:
        generative.ensure(dsn)      # once per process (never an init per request)
        render_assets.ensure(dsn)
        shot_id = generative.add_shot(Shot(subject=kit["name"][:100], action="kit screen"),
                                      notes="drawn from the brand kit", dsn=dsn,
                                      account_id=account_id)
        generation_id = generative.record_generation(
            shot_id, LIBRARY_TOOL, text, params=params, output_path=str(path), cost_usd=None,
            notes="drawn in code from the kit -- no provider, no credits", dsn=dsn,
            account_id=account_id)
        asset_id = render_assets.record_best_effort(
            account_id=account_id, generation_id=generation_id, tool=LIBRARY_TOOL,
            model=LIBRARY_MODEL, media_kind="image", prompt=text, media_url=stored,
            output_path=str(path), metadata=params, dsn=dsn).get("id")
    except Exception as e:                                   # noqa: BLE001
        import sys
        print(f"  kit screen not filed in the Library: {e}", file=sys.stderr)
    return {"asset_id": asset_id, "stored": stored, "url": media.url_for(stored, account_id),
            "summary": summary(spec)}
