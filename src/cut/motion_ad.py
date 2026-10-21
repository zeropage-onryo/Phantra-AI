"""A MOTION AD from a brief: the brain writes the beats, code places them
(2026-10-20; docs/tasks/task-motion-ad.md).

The Gygler reference is motion graphics, not footage: big type over flat brand
colours, one huge faint word behind each line, product screenshots on cards, a
label now and then, the logo at the end. Every piece of that exists in the
editor (the graphics track, src/cut/graphics.py; the brand kit's look and end
card, src/cut/brand.py). This is the part that PLACES them:

  1. `write_beats` -- ONE model call (free text on a plan, stage `motion_ad`):
     the brief, the project's brand kit and the attached screenshots in,
     a title and 3-15 beats out (headline, big word, which screenshot, a
     label, which brand colour, how long).
  2. `clean` -- the model's answer checked against reality, every fix a
     visible warning (the conventions: model output is advised, never
     rejected).
  3. `layout` -- pure: the beats -> a timeline. V1 is one flat-colour still per
     beat (`backgrounds` draws them with Pillow and files them in the bin);
     G1 the big words, G2 the headlines, G3 the cards, G4 the labels, each
     timed inside its beat with the motion the reference uses, each in a
     colour that reads on that beat's background.
  4. `make` -- a new Cut project filed under the studio project (so the
     kit's captions and end card reach its export), version 1 = the layout.

Nothing renders and nothing spends credits: no video model, no image model.
The person opens it in the editor to keep, change or throw away.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Callable, Optional

from . import doc as d
from . import graphics as gfx

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
SECONDS_MIN, SECONDS_MAX, SECONDS_DEFAULT = 8, 60, 20
BEAT_SECONDS_MIN, BEAT_SECONDS_MAX = 1.5, 8.0
BEATS_MAX = 15
CARDS_MAX = 8
HEADLINE_WORDS_MAX = 10
BRAIN = "fast"
ROLES = ("background", "primary", "accent", "text")
# a project with no brand kit: a quiet dark set, white type
PLAIN = {"background": "#111214", "primary": "#F2F1EE", "accent": "#2A2B30", "text": "#F2F1EE"}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "beats": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "big_word": {"type": "string"},
                "card": {"type": ["integer", "null"]},
                "card_caption": {"type": "string"},
                "label": {"type": "string"},
                "background": {"type": "string", "enum": list(ROLES)},
                "seconds": {"type": "number"},
            },
            "required": ["headline", "big_word", "card", "card_caption", "label", "background",
                         "seconds"]}},
    },
    "required": ["title", "beats"],
}


class MotionAdError(RuntimeError):
    """Said to the person in plain words; nothing was made."""


def beat_range(seconds: int) -> tuple[int, int]:
    low = max(3, round(seconds / 5))
    return low, min(BEATS_MAX, max(low + 1, round(seconds / 2.5)))


# --------------------------------------------------------------------------
# 1. the script
# --------------------------------------------------------------------------

def brand_block(kit: Optional[dict]) -> str:
    """What the prompt's {brand} slot reads: the kit's voice and identity, or
    a line saying there is none."""
    if not kit:
        return ("(No brand kit on this project: write in a plain, confident voice, and take "
                "the product's name and facts from the brief alone.)")
    from .. import brand_kits
    spec = kit.get("spec") or {}
    ident = spec.get("identity") or {}
    lines = [brand_kits.brief_lines(kit)]
    if ident.get("url"):
        lines.append(f"- Website: {ident['url']}")
    return "\n".join(ln for ln in lines if ln)


def cards_block(cards: list[dict]) -> str:
    if not cards:
        return "(none attached -- no beat shows a card; set every \"card\" to null)"
    return "\n".join(f"{i}. {c.get('name') or c['handle']}" for i, c in enumerate(cards, start=1))


def build_prompt(brief: str, kit: Optional[dict], seconds: int, cards: list[dict]) -> str:
    low, high = beat_range(seconds)
    return ((PROMPTS_DIR / "motion_ad_prompt.txt").read_text()
            .replace("{brief}", brief.strip())
            .replace("{brand}", brand_block(kit))
            .replace("{seconds}", str(seconds))
            .replace("{beats_min}", str(low))
            .replace("{beats_max}", str(high))
            .replace("{cards}", cards_block(cards)))


def _model(prompt: str, *, account_id: Optional[int]) -> dict:
    """THE seam a test replaces: one structured call, JSON back."""
    from google.genai import types

    from .. import gemini_utils
    if not gemini_utils.api_key_for(account_id):
        raise MotionAdError("this server has no Gemini key, so the script cannot be written")
    client = gemini_utils.client_for(account_id)
    brain = gemini_utils.resolve_brain(BRAIN)
    config = brain["config"] or types.GenerateContentConfig()
    config.response_mime_type = "application/json"
    config.response_json_schema = SCHEMA
    raw = gemini_utils.generate_with_retry(client, brain["model"], prompt, config=config,
                                           fallbacks=brain["fallbacks"], stage="motion_ad",
                                           account_id=account_id)
    return json.loads(raw)


def write_beats(brief: str, kit: Optional[dict], seconds: int, cards: list[dict], *,
                account_id: Optional[int],
                model: Optional[Callable[..., dict]] = None) -> dict:
    """The model's script, as it answered. Raises MotionAdError."""
    try:
        return (model or _model)(build_prompt(brief, kit, seconds, cards), account_id=account_id)
    except MotionAdError:
        raise
    except Exception as e:                       # a model call degrades, it does not crash
        raise MotionAdError(f"the script was not written ({type(e).__name__}). "
                            "Nothing was made or charged.") from e


# --------------------------------------------------------------------------
# 2. checked against reality
# --------------------------------------------------------------------------

def _clip(text, limit: int) -> tuple[str, bool]:
    text = " ".join(str(text or "").split())
    return (text[:limit].rstrip(), True) if len(text) > limit else (text, False)


def unsourced_numbers(text: str, facts: str) -> list[str]:
    """The numbers in `text` that `facts` (the brief and the brand) never
    gives -- a price or a rating the model may have made up."""
    import re
    said = set(re.findall(r"\d+(?:[.,]\d+)?", facts or ""))
    return [n for n in re.findall(r"\d+(?:[.,]\d+)?", text or "") if n not in said]


def clean(raw: Any, seconds: int, n_cards: int, facts: Optional[str] = None) -> dict:
    """{"title", "beats", "warnings"}: the beats the layout can place, each fix
    the model needed said in a warning. `facts` is the brief and the brand:
    a number on screen that neither gives is flagged (code advises -- the
    person decides whether it is true). Raises MotionAdError when nothing
    usable came back."""
    warnings: list[str] = []
    raw = raw if isinstance(raw, dict) else {}
    beats_in = [b for b in raw.get("beats") or [] if isinstance(b, dict)]
    if len(beats_in) > BEATS_MAX:
        warnings.append(f"the script had {len(beats_in)} beats; kept the first {BEATS_MAX}")
        beats_in = beats_in[:BEATS_MAX]
    beats = []
    for n, b in enumerate(beats_in, start=1):
        headline, cut = _clip(b.get("headline"), gfx.TEXT_MAX)
        words = headline.split()
        if len(words) > HEADLINE_WORDS_MAX:
            headline, cut = " ".join(words[:HEADLINE_WORDS_MAX]), True
        if cut:
            warnings.append(f"beat {n}: the headline was shortened")
        word = (b.get("big_word") or "").strip().split()
        word = word[0] if word else ""
        if len(word) > gfx.WORD_MAX:
            warnings.append(f"beat {n}: the big word was too long and was dropped")
            word = ""
        card = b.get("card")
        if card is not None:
            try:
                card = int(card)
            except (TypeError, ValueError):
                card = None
            if card is not None and not 1 <= card <= n_cards:
                warnings.append(f"beat {n}: asked for screenshot {card}, which was not attached")
                card = None
        label, cut = _clip(b.get("label"), 40)
        caption, _ = _clip(b.get("card_caption"), 60)
        background = b.get("background") if b.get("background") in ROLES else "background"
        try:
            secs = float(b.get("seconds"))
        except (TypeError, ValueError):
            secs = 3.0
        if not headline and not word and card is None:
            warnings.append(f"beat {n} was empty and was left out")
            continue
        if facts is not None:
            for where, text in (("headline", headline), ("label", label),
                                ("card caption", caption if card is not None else "")):
                made_up = unsourced_numbers(text, facts)
                if made_up:
                    warnings.append(f"beat {n}: the {where} “{text}” has "
                                    f"{', '.join(made_up)}, which the brief does not give "
                                    "-- check it is true")
        beats.append({"headline": headline, "big_word": word, "card": card,
                      "card_caption": caption if card is not None else "", "label": label,
                      "background": background,
                      "seconds": min(BEAT_SECONDS_MAX, max(BEAT_SECONDS_MIN, secs))})
    if not beats:
        raise MotionAdError("the script came back with no beats to place. Nothing was made.")
    total = sum(b["seconds"] for b in beats)
    if abs(total - seconds) > 0.5:
        scale = seconds / total
        for b in beats:
            b["seconds"] = round(b["seconds"] * scale, 2)
        warnings.append(f"the beats added up to {total:.1f}s; fitted to {seconds}s")
    title, _ = _clip(raw.get("title") or "Motion ad", 80)
    return {"title": title or "Motion ad", "beats": beats, "warnings": warnings}


# --------------------------------------------------------------------------
# 3. placing it
# --------------------------------------------------------------------------

def palette(kit: Optional[dict]) -> dict[str, str]:
    """Role -> #RRGGBB, the kit's where it has them, the plain set elsewhere."""
    colours = dict(PLAIN)
    if kit:
        for s in (kit.get("spec") or {}).get("palette") or []:
            if s.get("role") in ROLES:
                colours[s["role"]] = s["hex"]
        if not any(s.get("role") == "text" for s in (kit.get("spec") or {}).get("palette") or []):
            colours["text"] = colours["primary"]
    return colours


def _luma(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on(background: str, colours: dict[str, str]) -> str:
    """The colour type is set in on a background: the brand's primary where
    it reads clearly, else whichever brand colour stands out most from the
    background (cream on orange, as the reference does), else black or white."""
    bg = _luma(background)
    primary = colours.get("primary")
    # big display type: the brand's own colour wins at a lower contrast than
    # body text would need (orange on cream, as the reference sets it)
    if primary and primary.upper() != background.upper() and abs(_luma(primary) - bg) >= 0.3:
        return primary
    best, gap = None, 0.0
    for role in ("primary", "text", "background"):
        hex_colour = colours.get(role)
        if hex_colour and hex_colour.upper() != background.upper():
            diff = abs(_luma(hex_colour) - bg)
            if diff > gap:
                best, gap = hex_colour, diff
    if best and gap >= 0.25:
        return best
    return "#111111" if bg > 0.5 else "#FFFFFF"


def background_png(hex_colour: str, size: tuple[int, int]) -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", tuple(size), hex_colour).save(out, "PNG")
    return out.getvalue()


def layout(plan: dict, *, size: tuple[int, int], fps: int, colours: dict[str, str],
           backgrounds: dict[str, str], cards: list[str]) -> dict:
    """The beats -> a doc. Pure. `backgrounds` maps a #RRGGBB to the bin
    handle of its flat still; `cards` is the attached screenshots' handles,
    in the order the prompt numbered them."""
    doc = d.new_doc()
    doc["size"], doc["fps"] = [int(size[0]), int(size[1])], int(fps)
    v1: list[dict] = []
    tracks = {k: [] for k in ("G1", "G2", "G3", "G4")}
    at = 0
    for n, b in enumerate(plan["beats"], start=1):
        length = max(int(round(b["seconds"] * fps)), round(BEAT_SECONDS_MIN * fps))
        bg = colours[b["background"]]
        v1.append({"id": f"c{n}", "media": backgrounds[bg], "src_in": 0, "src_out": length,
                   "at": at, "speed": 1})
        ink = ink_on(bg, colours)
        has_card = b["card"] is not None
        lead = round(0.15 * fps)
        if b["big_word"]:
            tracks["G1"].append({"id": f"g{n}w", "start": at, "end": at + length,
                                 "type": "background_word", "text": b["big_word"].upper(),
                                 "position": "center", "anim_in": "fade", "anim_out": "fade",
                                 "size": "l", "color": ink, "drift": True})
        if b["headline"]:
            tracks["G2"].append({"id": f"g{n}h", "start": at + lead,
                                 "end": at + length, "type": "headline",
                                 "text": b["headline"],
                                 "position": "left" if has_card else "center",
                                 "anim_in": "rise", "anim_out": "fade", "size": "m",
                                 "color": ink})
        if has_card:
            card = {"id": f"g{n}c", "start": at + 2 * lead, "end": at + length, "type": "card",
                    "media": cards[b["card"] - 1], "position": "right",
                    "anim_in": "slide_left", "anim_out": "fade", "size": "m", "color": "auto"}
            if b["card_caption"]:
                card["text"] = b["card_caption"]
            tracks["G3"].append(card)
        if b["label"] and length > 4 * lead:
            label = {"id": f"g{n}l", "start": at + 4 * lead, "end": at + length,
                     "type": "label", "text": b["label"], "position": "lower_left",
                     "anim_in": "fade", "anim_out": "fade", "size": "s", "color": "auto"}
            if bg.upper() == colours["primary"].upper():
                # a primary pill would vanish on a primary beat: the
                # pill takes the other brand colour, lettered in primary
                label["pill"] = ink
                label["color"] = colours["primary"]
            tracks["G4"].append(label)
        at += length
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": v1}]
    for tid, items in tracks.items():
        if items:
            doc["tracks"].append({"id": tid, "kind": "graphic", "items": items})
    doc["duration"] = d.compute_duration(doc)
    doc["markers"] = []
    return doc


def backgrounds(colours_used: set[str], size: tuple[int, int], *, account_id: Optional[int],
                media_dir: Path, dsn: Optional[str] = None) -> dict[str, str]:
    """A flat still per colour, filed in the bin (content-addressed, so the
    same colour at the same size is one file, ever); #RRGGBB -> handle."""
    from . import uploads
    out = {}
    for hex_colour in sorted(colours_used):
        saved = uploads.save(background_png(hex_colour, size),
                             f"background-{hex_colour.lstrip('#').lower()}.png",
                             account_id=account_id, media_dir=media_dir, dsn=dsn)
        out[hex_colour] = saved["handle"]
    return out


# --------------------------------------------------------------------------
# 4. the cut
# --------------------------------------------------------------------------

def make(brief: str, *, account_id: Optional[int], media_dir: Path,
         project: Optional[dict] = None, seconds: int = SECONDS_DEFAULT, aspect: str = "16:9",
         cards: Optional[list[dict]] = None, dsn: Optional[str] = None,
         model: Optional[Callable[..., dict]] = None, progress=None) -> dict:
    """Write, check, place and save. Returns {"cut": row, "version": v,
    "title", "beats", "warnings"}. Raises MotionAdError."""
    from .. import brand_kits
    from . import store
    brief = (brief or "").strip()
    if not brief:
        raise MotionAdError("say what the ad is for")
    cards = list(cards or [])[:CARDS_MAX]
    kit = brand_kits.for_project(project, dsn) if project else None
    say = progress or (lambda *_: None)
    say(0.15, "writing the script")
    raw = write_beats(brief, kit, seconds, cards, account_id=account_id, model=model)
    plan = clean(raw, seconds, len(cards), facts=f"{brief}\n{brand_block(kit)}")
    say(0.6, "placing the beats")
    size = d.ASPECT_SIZES[aspect]
    colours = palette(kit)
    used = {colours[b["background"]] for b in plan["beats"]}
    handles = backgrounds(used, size, account_id=account_id, media_dir=media_dir, dsn=dsn)
    doc = layout(plan, size=size, fps=d.DEFAULT_FPS, colours=colours, backgrounds=handles,
                 cards=[c["handle"] for c in cards])
    from . import validate
    media = {h: {"frames": d.STILL_SECONDS * d.DEFAULT_FPS, "video": True, "audio": False,
                 "still": True, "width": size[0], "height": size[1]}
             for h in list(handles.values()) + [c["handle"] for c in cards]}
    validate.validate(doc, media)
    row = store.create_project(account_id=account_id, title=plan["title"][:200],
                               fps=d.DEFAULT_FPS, dsn=dsn,
                               studio_project_id=project["id"] if project else None)
    n = len(plan["beats"])
    tl = store.save_version(row["timeline_key"], doc, account_id=account_id, author="agent",
                            op_summary=f"motion ad: {n} beat{'s' if n != 1 else ''}", dsn=dsn)
    return {"cut": row, "version": tl, "title": plan["title"], "beats": plan["beats"],
            "warnings": plan["warnings"], "brand_kit": kit["name"] if kit else None}
