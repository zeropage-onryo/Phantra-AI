"""Studios: a preset bundle over the one engine (2026-10-26, Mike: "give it
its own UI and title 'Ad Studio' in the Phantra studio. Combine what we
already have").

A studio is NOT a second app. It is a config file in prompts/studios/ --
its formats, a short intake and a prompt overlay -- read the way
src/skills.py reads the shelf: plain files, never raises, an unreadable
file is no studio. The Ad Studio page (web/src/app/studio/ads) draws the
config; its "Start in Create" hands the person to the ONE composer with a
`studio` pick on the conversation's draft, and every brain turn that
carries the pick gets the studio's note (`turn_note`) beside the picked
skill. So the formats ride on the skills that already exist (ad, ugc,
motion-ad, product-still, social-cutdown), the product rides on Elements,
the look on brand kits, and every spend on the priced cards it always had.

What a pick is: {"id": "ads", "format": "<row id>", "aspect": "9:16",
"seconds": 15, "intake": {"platform": "tiktok", "audience": "...", ...}}.
`clean_pick` is the one cleaner: an unknown studio or format is no pick at
all, an aspect or length off the row is dropped back to the row's default
(it is a brief, not a model's legal set), and only intake answers the
config names survive, trimmed to their own caps.

Studios are a paid add-on (src/addons.py, `studios`): the page is open to
everyone, and the pick reaches the brain only for an account that has it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
STUDIOS_DIR = ROOT / "prompts" / "studios"
IDS = ("ads",)
OUTPUTS = ("image", "video")
NEEDS = ("product", "kit", "clip")
INTAKE_KINDS = ("text", "choice")
MAX_TEXT = 200

# the shapes a still or a clip can be asked for in the composer
# (app/api.py GENERATE_ASPECTS; the video frames are a subset)
LEGAL_ASPECTS = ("1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9")


def _read(studio_id: str) -> Optional[dict]:
    path = STUDIOS_DIR / f"{studio_id}.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("id") == studio_id else None


def get(studio_id) -> Optional[dict]:
    """The whole config (formats with their prompt notes), or None."""
    sid = str(studio_id or "").strip().lower()
    return _read(sid) if sid in IDS else None


def clean_id(studio_id) -> str:
    return get(studio_id)["id"] if get(studio_id) else ""


def format_of(studio: dict, format_id) -> Optional[dict]:
    fid = str(format_id or "").strip().lower()
    return next((f for f in studio.get("formats") or [] if f.get("id") == fid), None)


def _seconds_ok(fmt: dict, seconds: Any) -> Optional[int]:
    span = fmt.get("seconds")
    if not span or isinstance(seconds, bool):
        return None
    try:
        n = int(seconds)
    except (TypeError, ValueError):
        return None
    return n if span[0] <= n <= span[1] else None


def clean_intake(studio: dict, raw: Any) -> dict:
    """Only the answers the config asks for: a choice must be one of its
    options, a text is trimmed to the question's own cap."""
    raw = raw if isinstance(raw, dict) else {}
    out: dict = {}
    for q in studio.get("intake") or []:
        qid = q.get("id")
        value = raw.get(qid)
        if not isinstance(value, str):
            continue
        value = " ".join(value.split())
        if not value:
            continue
        if q.get("kind") == "choice":
            if value in {o.get("id") for o in q.get("options") or []}:
                out[qid] = value
        else:
            out[qid] = value[: int(q.get("max") or MAX_TEXT)]
    return out


def clean_pick(raw: Any) -> Optional[dict]:
    """A studio pick off a form or a draft (a dict or its JSON), or None."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else None
        except ValueError:
            return None
    if not isinstance(raw, dict):
        return None
    studio = get(raw.get("id"))
    if studio is None:
        return None
    fmt = format_of(studio, raw.get("format"))
    if fmt is None:
        return None
    aspects = fmt.get("aspects") or []
    aspect = raw.get("aspect") if raw.get("aspect") in aspects else (aspects[0] if aspects else None)
    seconds = _seconds_ok(fmt, raw.get("seconds"))
    if seconds is None:
        seconds = fmt.get("default_seconds")
    return {"id": studio["id"], "format": fmt["id"], "aspect": aspect, "seconds": seconds,
            "intake": clean_intake(studio, raw.get("intake"))}


def for_account(raw: Any, account_id: Optional[int]) -> Optional[dict]:
    """A form's pick, cleaned, for an account that has the studio's add-on;
    None otherwise. Without the add-on the turn is the plain composer's --
    never a refusal (the page is where the upgrade is offered)."""
    pick = clean_pick(raw)
    if pick is None:
        return None
    from . import addons
    addon = (get(pick["id"]) or {}).get("addon")
    return pick if not addon or addons.active(account_id, addon) else None


def _answer_label(studio: dict, qid: str, value: str) -> str:
    q = next((x for x in studio.get("intake") or [] if x.get("id") == qid), {})
    if q.get("kind") == "choice":
        return next((o.get("label") or value for o in q.get("options") or []
                     if o.get("id") == value), value)
    return value


def intake_line(studio: dict, intake: dict) -> str:
    """The intake as one line of the turn note."""
    parts = [f"{q.get('label', '').rstrip('?')}: {_answer_label(studio, q['id'], intake[q['id']])}"
             for q in studio.get("intake") or [] if q.get("id") in intake]
    return ". ".join(parts) + "." if parts else "Nothing else on the brief was filled in."


def turn_note(pick: Optional[dict]) -> str:
    """What a brain turn carrying the pick is told (prompts/studios/
    <id>_turn.txt), or "" for no pick. Never raises."""
    if not pick:
        return ""
    studio = get(pick.get("id"))
    fmt = format_of(studio, pick.get("format")) if studio else None
    if fmt is None:
        return ""
    try:
        template = (STUDIOS_DIR / f"{studio['id']}_turn.txt").read_text().strip()
    except OSError:
        return ""
    from . import skills
    seconds = pick.get("seconds")
    return (template
            .replace("{format}", fmt.get("title") or fmt["id"])
            .replace("{blurb}", fmt.get("blurb") or "")
            .replace("{aspect}", pick.get("aspect") or "any shape")
            .replace("{seconds}", f", {seconds} seconds" if seconds else "")
            .replace("{intake}", intake_line(studio, pick.get("intake") or {}))
            .replace("{skill_title}", skills.title_of(fmt.get("skill")) or "studio's")
            .replace("{note}", fmt.get("note") or ""))


def public(studio_id, *, account_id: Optional[int] = None) -> Optional[dict]:
    """What the studio's page draws: the config without its prompt notes,
    whether this account has the add-on, and how to buy it."""
    studio = get(studio_id)
    if studio is None:
        return None
    from . import addons, billing, pricing, skills
    addon_key = studio.get("addon") or ""
    addon = pricing.ADDONS.get(addon_key)
    formats = []
    for f in studio.get("formats") or []:
        skill = skills.get(f.get("skill"))
        formats.append({k: v for k, v in f.items() if k != "note"}
                       | {"skill_title": skill["title"] if skill else None})
    return {
        "id": studio["id"],
        "title": studio.get("title") or studio["id"],
        "tagline": studio.get("tagline") or "",
        "intake": studio.get("intake") or [],
        "formats": formats,
        "entitled": addons.active(account_id, addon_key) if addon_key else True,
        "gated": addons.gate_on(),
        "addon": {
            "key": addon.key, "name": addon.name, "blurb": addon.blurb,
            "monthly_usd": addon.monthly_usd,
            "on_sale": billing.configured() and bool(billing.price_id(addon.key)),
            "has_plan": bool(account_id and _plan(account_id)),
        } if addon else None,
    }


def _plan(account_id: int) -> Optional[str]:
    from . import accounts
    return accounts.plan_of(account_id)


def problems(studio_id) -> list[str]:
    """What is wrong with a config, for the test that keeps it honest: a
    skill that is not on the shelf, an output or aspect nothing makes, a
    length outside what the format's tool accepts."""
    from . import guide_tools, skills
    studio = get(studio_id)
    if studio is None:
        return [f"no studio {studio_id!r} in {STUDIOS_DIR}"]
    out: list[str] = []
    if not studio.get("title"):
        out.append("no title")
    if studio.get("addon"):
        from . import pricing
        if studio["addon"] not in pricing.ADDONS:
            out.append(f"addon {studio['addon']!r} is not in pricing.ADDONS")
    for q in studio.get("intake") or []:
        if q.get("kind") not in INTAKE_KINDS:
            out.append(f"intake {q.get('id')}: kind {q.get('kind')!r}")
        if q.get("kind") == "choice" and not q.get("options"):
            out.append(f"intake {q.get('id')}: a choice with no options")
        for o in q.get("options") or []:
            if o.get("aspect") and o["aspect"] not in LEGAL_ASPECTS:
                out.append(f"intake {q.get('id')}: option {o.get('id')} aspect {o['aspect']}")
    seen = set()
    for f in studio.get("formats") or []:
        fid = f.get("id")
        if fid in seen:
            out.append(f"format {fid}: listed twice")
        seen.add(fid)
        if not skills.get(f.get("skill")):
            out.append(f"format {fid}: skill {f.get('skill')!r} is not on the shelf")
        if f.get("output") not in OUTPUTS:
            out.append(f"format {fid}: output {f.get('output')!r}")
        if not f.get("aspects"):
            out.append(f"format {fid}: no aspects")
        for a in f.get("aspects") or []:
            if a not in LEGAL_ASPECTS:
                out.append(f"format {fid}: aspect {a}")
        for n in f.get("needs") or []:
            if n not in NEEDS:
                out.append(f"format {fid}: need {n!r}")
        if not (f.get("note") or "").strip():
            out.append(f"format {fid}: no prompt note")
        span, default = f.get("seconds"), f.get("default_seconds")
        if f.get("output") == "image":
            if span or default:
                out.append(f"format {fid}: a still has no length")
            continue
        if not span or len(span) != 2 or span[0] > span[1]:
            out.append(f"format {fid}: seconds {span!r}")
            continue
        legal = guide_tools.AD_SECONDS if f.get("skill") == "motion-ad" else guide_tools.MAKE_SECONDS
        if span[0] < legal[0] or span[1] > legal[1]:
            out.append(f"format {fid}: {span} is outside what its tool takes {legal}")
        if not (default and span[0] <= default <= span[1]):
            out.append(f"format {fid}: default {default!r} is outside {span}")
    return out
