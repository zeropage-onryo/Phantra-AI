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
import re
from pathlib import Path
from typing import Any, Callable, Optional

from . import doc as d
from . import graphics as gfx

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
SECONDS_MIN, SECONDS_MAX, SECONDS_DEFAULT = 8, 60, 20
BEAT_SECONDS_MIN, BEAT_SECONDS_MAX = 1.5, 8.0
BEATS_MAX = 15
CARDS_MAX = 8
PICTURES_MAX = 12        # full-frame photos a beat may sit on (step 2 of task-url-to-ad)
VOICEOVER_MAX = 200      # characters of voiceover per beat
HEADLINE_WORDS_MAX = 10
BRAIN = "fast"
ROLES = ("background", "primary", "accent", "text")
# a project with no brand kit: a quiet dark set, white type
PLAIN = {"background": "#111214", "primary": "#F2F1EE", "accent": "#2A2B30", "text": "#F2F1EE"}

# The camera moves a photo beat may take: a closed list, each a fixed set
# of keyframes in code (clip-relative: 0 is the beat's first frame, 1 its
# last), never numbers from a model. Every value sits inside lanes.PATHS,
# and a pan or a rise is zoomed in far enough that the picture's edge never
# shows (x / y travel stays under half the zoom's spare width).
MOVES: dict[str, tuple] = {
    "hold": (),
    "push_in": (("zoom", ((0, 1.0, "ease"), (1, 1.15, "linear"))),),
    "pull_out": (("zoom", ((0, 1.15, "ease"), (1, 1.0, "linear"))),),
    "pan_left": (("zoom", ((0, 1.12, "linear"),)),
                 ("x", ((0, 0.04, "linear"), (1, -0.04, "linear")))),
    "pan_right": (("zoom", ((0, 1.12, "linear"),)),
                  ("x", ((0, -0.04, "linear"), (1, 0.04, "linear")))),
    "rise": (("zoom", ((0, 1.1, "linear"),)),
             ("y", ((0, 0.035, "ease"), (1, -0.035, "linear")))),
    "drift": (("zoom", ((0, 1.05, "linear"), (1, 1.1, "linear"))),
              ("x", ((0, 0.015, "linear"), (1, -0.015, "linear")))),
    "scale_in": (("zoom", ((0, 0.85, "ease"), (0.35, 1.0, "linear"))),),
}
PHOTO_INK = "#FFFFFF"    # type over a photo: white, which graphics.py shadows to read


def move_lanes(move: str, length: int) -> list[dict]:
    """The lanes one named move puts on a clip `length` frames long. Pure."""
    out = []
    last = max(1, int(length) - 1)
    for path, keys in MOVES.get(move, ()):
        out.append({"path": path, "keys": [
            {"frame": int(round(pos * last)), "value": value, "ease": ease}
            for pos, value, ease in keys]})
    return out


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
                # step 2 of docs/tasks/task-url-to-ad.md: a beat may sit on one
                # of the brand's PHOTOS, full frame, with a named camera move,
                # and carry its line of voiceover. Optional: an older answer,
                # and the redo-one-beat prompt, leave them out.
                "picture": {"type": ["integer", "null"]},
                "move": {"type": "string", "enum": list(MOVES)},
                "voiceover": {"type": "string"},
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


def pictures_block(pictures: list[dict]) -> str:
    if not pictures:
        return ("(none -- every beat sits on a flat brand colour; set every \"picture\" to "
                "null and every \"move\" to \"hold\")")
    return "\n".join(f"{i}. {p.get('name') or p['handle']}"
                     for i, p in enumerate(pictures, start=1))


def build_prompt(brief: str, kit: Optional[dict], seconds: int, cards: list[dict],
                 pictures: Optional[list[dict]] = None) -> str:
    low, high = beat_range(seconds)
    return ((PROMPTS_DIR / "motion_ad_prompt.txt").read_text()
            .replace("{brief}", brief.strip())
            .replace("{pictures}", pictures_block(pictures or []))
            .replace("{moves}", ", ".join(MOVES))
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
                model: Optional[Callable[..., dict]] = None,
                pictures: Optional[list[dict]] = None) -> dict:
    """The model's script, as it answered. Raises MotionAdError."""
    try:
        return (model or _model)(build_prompt(brief, kit, seconds, cards, pictures),
                                 account_id=account_id)
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


def claims_broken(text: str, never: list[str]) -> list[str]:
    """The kit's never-claim phrases that `text` makes, word for word."""
    low = " ".join((text or "").lower().split())
    return [c for c in never if c and " ".join(c.lower().split()) in low]


def clean(raw: Any, seconds: int, n_cards: int, facts: Optional[str] = None,
          n_pictures: int = 0, never: Optional[list[str]] = None) -> dict:
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
        picture = b.get("picture")
        if picture is not None:
            try:
                picture = int(picture)
            except (TypeError, ValueError):
                picture = None
            if picture is not None and not 1 <= picture <= n_pictures:
                warnings.append(f"beat {n}: asked for photo {picture}, which is not one of the "
                                "brand's pictures")
                picture = None
        move = b.get("move") or "hold"
        if move not in MOVES:
            warnings.append(f"beat {n}: “{str(move)[:30]}” is not a camera move; it holds")
            move = "hold"
        if picture is None:
            move = "hold"
        voiceover, cut_vo = _clip(b.get("voiceover"), VOICEOVER_MAX)
        if cut_vo:
            warnings.append(f"beat {n}: the voiceover line was shortened")
        label, cut = _clip(b.get("label"), 40)
        caption, _ = _clip(b.get("card_caption"), 60)
        background = b.get("background") if b.get("background") in ROLES else "background"
        try:
            secs = float(b.get("seconds"))
        except (TypeError, ValueError):
            secs = 3.0
        if not headline and not word and card is None and picture is None:
            warnings.append(f"beat {n} was empty and was left out")
            continue
        said = (("headline", headline), ("label", label),
                ("card caption", caption if card is not None else ""), ("voiceover", voiceover))
        if facts is not None:
            for where, text in said:
                made_up = unsourced_numbers(text, facts)
                if made_up:
                    warnings.append(f"beat {n}: the {where} “{text}” has "
                                    f"{', '.join(made_up)}, which the brief does not give "
                                    "-- check it is true")
        for where, text in said:
            for claim in claims_broken(text, never or []):
                warnings.append(f"beat {n}: the {where} makes a claim the brand kit says never "
                                f"to make (“{claim}”) -- change it before this is posted")
        beats.append({"headline": headline, "big_word": word, "card": card,
                      "card_caption": caption if card is not None else "", "label": label,
                      "background": background, "picture": picture, "move": move,
                      "voiceover": voiceover,
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


def photo_crop(width: int, height: int, size: tuple[int, int]) -> Optional[dict]:
    """The static crop that fills the frame with a photo's middle, or None
    when it already fits or would pass the editor's bound (it is then shown
    whole, letterboxed). Pure."""
    from . import quick
    if not (width and height):
        return None
    try:
        sides = quick.crop_for(int(width), int(height), size)
    except quick.QuickRefused:
        return None
    return sides if any(sides.values()) else None


def layout(plan: dict, *, size: tuple[int, int], fps: int, colours: dict[str, str],
           backgrounds: dict[str, str], cards: list[str],
           pictures: Optional[list[dict]] = None) -> dict:
    """The beats -> a doc. Pure. `backgrounds` maps a #RRGGBB to the bin
    handle of its flat still; `cards` is the attached screenshots' handles,
    in the order the prompt numbered them; `pictures` the brand's photos
    ({"handle", "width", "height"}), in the order the prompt numbered them.
    A beat on a photo sits on it full frame, cropped to fill, with its
    named move as keyframes; a beat's voiceover line is a marker at its
    start, for the read (step 4)."""
    pictures = list(pictures or [])
    doc = d.new_doc()
    doc["size"], doc["fps"] = [int(size[0]), int(size[1])], int(fps)
    v1: list[dict] = []
    markers: list[dict] = []
    tracks = {k: [] for k in ("G1", "G2", "G3", "G4")}
    at = 0
    for n, b in enumerate(plan["beats"], start=1):
        length = max(int(round(b["seconds"] * fps)), round(BEAT_SECONDS_MIN * fps))
        bg = colours[b["background"]]
        photo = pictures[b["picture"] - 1] if b.get("picture") else None
        clip = {"id": f"c{n}", "media": photo["handle"] if photo else backgrounds[bg],
                "src_in": 0, "src_out": length, "at": at, "speed": 1}
        if photo:
            lanes = move_lanes(b.get("move") or "hold", length)
            if lanes:
                clip["lanes"] = lanes
            crop = photo_crop(photo.get("width"), photo.get("height"), size)
            if crop:
                clip["crop"] = crop
        v1.append(clip)
        if b.get("voiceover"):
            markers.append({"frame": at, "label": f"VO {n}: {b['voiceover']}"})
        ink = PHOTO_INK if photo else ink_on(bg, colours)
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
            if not photo and bg.upper() == colours["primary"].upper():
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
    doc["markers"] = markers
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
         model: Optional[Callable[..., dict]] = None, progress=None,
         pictures: Optional[list[dict]] = None, script: Optional[dict] = None,
         dry: bool = False) -> dict:
    """Write, check, place and save. Returns {"cut": row, "version": v,
    "title", "beats", "warnings", "voiceover"}. `pictures` are the brand's
    photos already in the bin ({"handle", "name", "width", "height"}).

    `script` is a script already written -- the chat's ad card, after the
    person changed it (step 3 of docs/tasks/task-url-to-ad.md): no model is
    called, and it is checked exactly as the model's answer is. `dry`
    stops after the checks and saves nothing: {"title", "beats",
    "warnings", "voiceover", "script"}, what the card shows before Build.
    Raises MotionAdError."""
    from .. import brand_kits
    from . import store
    brief = (brief or "").strip()
    if not brief:
        raise MotionAdError("say what the ad is for")
    cards = list(cards or [])[:CARDS_MAX]
    pictures = list(pictures or [])[:PICTURES_MAX]
    kit = brand_kits.for_project(project, dsn) if project else None
    never = list(((kit or {}).get("spec") or {}).get("never_claim") or [])
    say = progress or (lambda *_: None)
    if script is None:
        say(0.15, "writing the script")
        raw = write_beats(brief, kit, seconds, cards, account_id=account_id, model=model,
                          pictures=pictures)
    else:
        raw = script
    plan = clean(raw, seconds, len(cards), facts=f"{brief}\n{brand_block(kit)}",
                 n_pictures=len(pictures), never=never)
    if dry:
        voiceover, at = [], 0.0
        for n, b in enumerate(plan["beats"], start=1):
            if b.get("voiceover"):
                voiceover.append({"beat": n, "at": round(at, 2), "line": b["voiceover"]})
            at += b["seconds"]
        return {"title": plan["title"], "beats": plan["beats"], "warnings": plan["warnings"],
                "brand_kit": kit["name"] if kit else None, "voiceover": voiceover,
                "script": " ".join(v["line"] for v in voiceover)}
    say(0.6, "placing the beats")
    size = d.ASPECT_SIZES[aspect]
    colours = palette(kit)
    used = {colours[b["background"]] for b in plan["beats"] if not b.get("picture")}
    handles = backgrounds(used, size, account_id=account_id, media_dir=media_dir, dsn=dsn)
    doc = layout(plan, size=size, fps=d.DEFAULT_FPS, colours=colours, backgrounds=handles,
                 cards=[c["handle"] for c in cards], pictures=pictures)
    from . import validate
    media = {h: {"frames": d.STILL_SECONDS * d.DEFAULT_FPS, "video": True, "audio": False,
                 "still": True, "width": size[0], "height": size[1]}
             for h in list(handles.values()) + [c["handle"] for c in cards]}
    for p in pictures:
        media[p["handle"]] = {"frames": d.STILL_SECONDS * d.DEFAULT_FPS, "video": True,
                              "audio": False, "still": True,
                              "width": p.get("width") or size[0],
                              "height": p.get("height") or size[1]}
    validate.validate(doc, media)
    row = store.create_project(account_id=account_id, title=plan["title"][:200],
                               fps=d.DEFAULT_FPS, dsn=dsn,
                               studio_project_id=project["id"] if project else None)
    n = len(plan["beats"])
    tl = store.save_version(row["timeline_key"], doc, account_id=account_id, author="agent",
                            op_summary=f"motion ad: {n} beat{'s' if n != 1 else ''}", dsn=dsn)
    v1 = next(t for t in doc["tracks"] if t["id"] == "V1")["clips"]
    voiceover = [{"beat": n, "at": round(c["at"] / d.DEFAULT_FPS, 2), "line": b["voiceover"]}
                 for n, (b, c) in enumerate(zip(plan["beats"], v1), start=1)
                 if b.get("voiceover")]
    return {"cut": row, "version": tl, "title": plan["title"], "beats": plan["beats"],
            "warnings": plan["warnings"], "brand_kit": kit["name"] if kit else None,
            "voiceover": voiceover, "script": " ".join(v["line"] for v in voiceover)}


# --------------------------------------------------------------------------
# 5. redo one beat (2026-10-21)
# --------------------------------------------------------------------------
# A beat in a made ad is a V1 clip and the graphics that START inside it.
# The brain rewrites that one beat with the rest of the ad in front of it;
# code turns the answer into ordinary ops (delete the beat's graphics, set
# the new ones, overwrite the flat background when its colour changed) and
# the editor keeps them as ONE version by "agent", so Undo takes it back.
# The background is only ever swapped when the clip there is one of the
# flat stills `backgrounds` files (a bin row named background-<hex>.png;
# every save is its own row, so handles alone cannot tell): a footage clip
# under graphics is never replaced.

BEAT_SCHEMA = SCHEMA["properties"]["beats"]["items"]
NOTE_MAX = 400


def beats_of(doc: dict) -> list[dict]:
    """The ad's beats as they are now: each V1 clip's span and what is on
    screen in it (graphics by the track they sit on)."""
    v1 = next((t for t in doc.get("tracks", []) if t["id"] == "V1"), None)
    clips = sorted((v1 or {}).get("clips") or [], key=lambda c: c["at"])
    out = []
    for c in clips:
        start, end = int(c["at"]), d.clip_end(c)
        items = [(t["id"], g) for t in doc["tracks"] if t.get("kind") == "graphic"
                 for g in t.get("items") or [] if start <= int(g["start"]) < end]
        out.append({"clip": c, "start": start, "end": end, "items": items})
    return out


def beat_at(doc: dict, frame: int) -> tuple[int, dict]:
    """(1-based number, beat) under `frame`. Raises MotionAdError."""
    for n, b in enumerate(beats_of(doc), start=1):
        if b["start"] <= frame < b["end"]:
            return n, b
    raise MotionAdError("put the playhead on a beat -- there is no picture under it")


def _beat_line(n: int, beat: dict, cards: list[str], mark: bool) -> str:
    by_type = {}
    for _, g in beat["items"]:
        by_type.setdefault(g["type"], g)
    bits = []
    if "headline" in by_type:
        bits.append(f"headline “{by_type['headline'].get('text', '')}”")
    if "background_word" in by_type:
        bits.append(f"big word {by_type['background_word'].get('text', '')}")
    if "card" in by_type and by_type["card"].get("media") in cards:
        bits.append(f"card {cards.index(by_type['card']['media']) + 1}")
    if "label" in by_type:
        bits.append(f"label “{by_type['label'].get('text', '')}”")
    secs = (beat["end"] - beat["start"]) / d.DEFAULT_FPS
    return (f"{'>>' if mark else '  '} {n}. ({secs:.1f}s) "
            + ("; ".join(bits) if bits else "(nothing on screen)"))


def card_handles(doc: dict) -> list[str]:
    """The screenshots the ad already shows, in first-shown order."""
    seen = []
    for b in beats_of(doc):
        for _, g in b["items"]:
            if g.get("type") == "card" and g.get("media") and g["media"] not in seen:
                seen.append(g["media"])
    return seen


def build_beat_prompt(doc: dict, n: int, kit: Optional[dict], note: str) -> str:
    beats = beats_of(doc)
    cards = card_handles(doc)
    secs = (beats[n - 1]["end"] - beats[n - 1]["start"]) / (doc.get("fps") or d.DEFAULT_FPS)
    return ((PROMPTS_DIR / "motion_ad_beat_prompt.txt").read_text()
            .replace("{brand}", brand_block(kit))
            .replace("{beats}", "\n".join(_beat_line(i, b, cards, i == n)
                                          for i, b in enumerate(beats, start=1)))
            .replace("{n}", str(n))
            .replace("{note}", note or "(nothing in particular -- a fresh take that fits)")
            .replace("{seconds}", f"{secs:g}")
            .replace("{cards}", "\n".join(f"{i}. screenshot {i}" for i in
                                          range(1, len(cards) + 1)) if cards
                     else "(none -- set \"card\" to null)"))


def _beat_model(prompt: str, *, account_id: Optional[int]) -> dict:
    """THE seam a test replaces: one structured call, one beat back."""
    from google.genai import types

    from .. import gemini_utils
    if not gemini_utils.api_key_for(account_id):
        raise MotionAdError("this server has no Gemini key, so the beat cannot be written")
    client = gemini_utils.client_for(account_id)
    brain = gemini_utils.resolve_brain(BRAIN)
    config = brain["config"] or types.GenerateContentConfig()
    config.response_mime_type = "application/json"
    config.response_json_schema = BEAT_SCHEMA
    raw = gemini_utils.generate_with_retry(client, brain["model"], prompt, config=config,
                                           fallbacks=brain["fallbacks"], stage="motion_ad",
                                           account_id=account_id)
    return json.loads(raw)


def screen_text(doc: dict) -> str:
    return "\n".join(g.get("text") or "" for b in beats_of(doc) for _, g in b["items"])


FLAT_NAME = re.compile(r"background-([0-9a-f]{6})\.png")


def flat_colour(handle: str, *, account_id: Optional[int],
                dsn: Optional[str] = None) -> Optional[str]:
    """The #RRGGBB of a flat colour still a motion ad filed, or None for
    anything else (footage, a render, someone's upload)."""
    from . import store
    kind, _, rest = (handle or "").partition(":")
    if kind != "asset" or not rest.isdigit():
        return None
    row = store.get_media(int(rest), account_id=account_id, dsn=dsn)
    found = FLAT_NAME.fullmatch((row or {}).get("filename") or "")
    return f"#{found.group(1).upper()}" if found else None


def redo_ops(doc: dict, n: int, beat: dict, *, kit: Optional[dict],
             backgrounds_for: Callable[[set], dict],
             flat_colour_of: Callable[[str], Optional[str]]) -> list[dict]:
    """The ops that put `beat` (one cleaned beat) in place of beat `n`.
    Applied one by one here so a track this adds has the id the later ops
    name; `keep` re-applies the same list to the head."""
    from . import ops
    span = beats_of(doc)[n - 1]
    fps = doc.get("fps") or d.DEFAULT_FPS
    length = span["end"] - span["start"]
    colours = palette(kit)
    cards = card_handles(doc)
    plan = {"beats": [{**beat, "seconds": length / fps}]}
    handles = backgrounds_for(set(colours.values()))
    placed = layout(plan, size=tuple(doc["size"]), fps=fps, colours=colours,
                    backgrounds=handles, cards=cards)
    work, op_list = doc, []

    def run(op, args):
        nonlocal work
        work = ops.apply(work, op, args)
        op_list.append({"op": op, "args": args})

    for track_id, g in span["items"]:
        run("delete_graphic", {"track_id": track_id, "graphic_id": g["id"]})
    # the tracks the layout uses, by what is on them now (G1 words, G2
    # headlines, G3 cards, G4 labels in a made ad); a missing one is added
    for t in placed["tracks"]:
        if t["kind"] != "graphic":
            continue
        kind = t["items"][0]["type"]
        target = next((x["id"] for x in work["tracks"] if x.get("kind") == "graphic"
                       and any(g["type"] == kind for g in x.get("items") or [])), None)
        if target is None:
            target = t["id"] if not d.track(work, t["id"]) else None
            run("add_track", {"kind": "graphic", **({"track_id": target} if target else {})})
            target = target or work["tracks"][-1]["id"]
        for g in t["items"]:
            args = {k: v for k, v in g.items() if k != "id"}
            args["start"] += span["start"]
            args["end"] += span["start"]
            run("set_graphic", {"track_id": target, **args})
    new_bg = placed["tracks"][0]["clips"][0]["media"]
    was = flat_colour_of(span["clip"]["media"])
    if was and was.upper() != colours[beat["background"]].upper():
        run("overwrite", {"track_id": "V1", "at": span["start"],
                          "clip": {"media": new_bg, "src_in": 0, "src_out": length}})
    return op_list


def redo_beat(doc: dict, frame: int, note: str = "", *, kit: Optional[dict],
              account_id: Optional[int], backgrounds_for: Callable[[set], dict],
              flat_colour_of: Callable[[str], Optional[str]],
              model: Optional[Callable[..., dict]] = None) -> dict:
    """Rewrite the beat under `frame`: {"n", "beat", "ops", "warnings",
    "summary"}. Nothing is saved here. Raises MotionAdError."""
    note = " ".join((note or "").split())[:NOTE_MAX]
    n, span = beat_at(doc, int(frame))
    cards = card_handles(doc)
    try:
        raw = (model or _beat_model)(build_beat_prompt(doc, n, kit, note),
                                     account_id=account_id)
    except MotionAdError:
        raise
    except Exception as e:                       # a model call degrades, it does not crash
        raise MotionAdError(f"the beat was not rewritten ({type(e).__name__}). "
                            "Nothing changed or was charged.") from e
    fps = doc.get("fps") or d.DEFAULT_FPS
    secs = (span["end"] - span["start"]) / fps
    raw = dict(raw) if isinstance(raw, dict) else {}
    raw["seconds"] = secs
    plan = clean({"title": "", "beats": [raw]}, secs, len(cards),
                 facts=f"{note}\n{brand_block(kit)}\n{screen_text(doc)}")
    beat = plan["beats"][0]
    warnings = [w.replace("beat 1", f"beat {n}") for w in plan["warnings"]
                if "fitted to" not in w]
    op_list = redo_ops(doc, n, beat, kit=kit, backgrounds_for=backgrounds_for,
                       flat_colour_of=flat_colour_of)
    what = beat["headline"] or beat["big_word"] or "a card"
    return {"n": n, "beat": beat, "ops": op_list, "warnings": warnings,
            "summary": f"motion ad: beat {n} rewritten -- {what}"[:200]}
