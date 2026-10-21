"""A brand kit edited from the chat (2026-10-21,
docs/tasks/task-brand-kit-import-and-chat.md step 6).

Vesper proposes; the person applies. `propose_kit_change` is a WRITE tool
(src/guide_tools.py): the turn ends on it, the thread draws a card with each
field before and after, and only the card's Apply changes the kit, through
/creative-guide/act. This module is the arithmetic both ends share:

  * FIELDS -- the closed list of what may be changed, by a dotted name the
    model is handed as an enum. Files (logos, fonts, references), products,
    characters and the caption / end-card settings are the kit page's, never
    the chat's.
  * `apply` -- the kit's spec with the changes laid over it, run through
    `brand_kits.clean_spec`, so a change the kit page would refuse is refused
    here with the same message and the field named.
  * `diff` -- what the card shows: one row per field, before and after.

The kit is ALWAYS the one the thread's project picked: the model is handed
that id as a one-value enum, and the act route checks it against the
project the client is in.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Optional

from . import brand_kits

# field -> (what the card calls it, kind). Kind is how a value is read:
# "text" as typed, "list" split on commas / new lines, "lines" split on new
# lines or semicolons (a selling point may hold a comma), "aesthetics" as
# `tag: why` entries, "colour" a #RRGGBB for that palette role ("" removes it).
FIELDS: dict[str, tuple[str, str]] = {
    "identity.tagline": ("Tagline", "text"),
    "identity.positioning": ("Positioning", "text"),
    "identity.audience": ("Audience", "text"),
    "identity.url": ("Website", "text"),
    "identity.selling_points": ("Selling points", "lines"),
    "palette.primary": ("Primary colour", "colour"),
    "palette.accent": ("Accent colour", "colour"),
    "palette.background": ("Background colour", "colour"),
    "palette.text": ("Text colour", "colour"),
    "look.style": ("Style description", "text"),
    "look.banned": ("Banned elements", "list"),
    "look.aesthetics": ("Aesthetics", "aesthetics"),
    "voice.tone": ("Tone", "text"),
    "voice.use": ("Words to use", "list"),
    "voice.avoid": ("Words never to use", "list"),
    "voice.cta": ("Call-to-action style", "text"),
    "never_claim": ("Claims never to make", "list"),
}
MAX_CHANGES = 12
MAX_VALUE = 1600          # the longest field (the style description) and a little room
_HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


class ChangeError(ValueError):
    """A change the kit refuses, with the field it is about."""

    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field


def _hex(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        return ""
    m = _HEX.match(value)
    if not m:
        raise ChangeError(field, f"{value!r} is not a #RRGGBB colour")
    digits = m.group(1)
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    return "#" + digits.upper()


def _split(value: str, pattern: str) -> list[str]:
    out: list[str] = []
    for part in re.split(pattern, value or ""):
        part = part.strip()
        if part and part not in out:
            out.append(part)
    return out


def read(field: str, value: Any) -> Any:
    """The value the model gave, as the spec stores that field."""
    if field not in FIELDS:
        raise ChangeError(field, f"not a field the chat can change; one of {', '.join(FIELDS)}")
    if not isinstance(value, str):
        raise ChangeError(field, "the value must be text")
    if len(value) > MAX_VALUE:
        raise ChangeError(field, f"at most {MAX_VALUE} characters")
    kind = FIELDS[field][1]
    if kind == "colour":
        return _hex(value, field)
    if kind == "list":
        return _split(value, r"[\n,]")
    if kind == "lines":
        return _split(value, r"[\n;]")
    if kind == "aesthetics":
        out = []
        for entry in _split(value, r"[\n;]"):
            tag, _, why = entry.partition(":")
            out.append({"tag": tag.strip(), "because": why.strip()})
        return out
    return value.strip()


def current(spec: dict, field: str) -> Any:
    """The field's value in a stored spec, in the shape `read` returns."""
    group, _, key = field.partition(".")
    if group == "palette":
        found = next((s for s in spec.get("palette") or [] if s.get("role") == key), None)
        return found["hex"] if found else ""
    if not key:
        return list(spec.get(group) or [])
    value = (spec.get(group) or {}).get(key)
    if FIELDS[field][1] in ("list", "lines", "aesthetics"):
        return list(value or [])
    return value or ""


def apply(spec: dict, changes: list[dict]) -> dict:
    """The spec with every change laid over it, checked as the kit page's
    save is (`brand_kits.clean_spec`) after each one, so the change that
    breaks it is the one ChangeError names."""
    raw = copy.deepcopy(spec or {})
    cleaned = brand_kits.clean_spec(raw)
    for change in changes:
        field, value = change["field"], read(change["field"], change["value"])
        group, _, key = field.partition(".")
        if group == "palette":
            palette = list(raw.get("palette") or [])
            at = next((i for i, s in enumerate(palette) if s.get("role") == key), None)
            if not value:
                if at is not None:
                    palette.pop(at)
            elif at is None:
                palette.append({"hex": value, "role": key, "name": ""})
            else:
                palette[at] = {**palette[at], "hex": value}
            raw["palette"] = palette
        elif not key:
            raw[group] = value
        else:
            raw[group] = {**(raw.get(group) or {}), key: value}
        try:
            cleaned = brand_kits.clean_spec(raw)
        except brand_kits.KitError as e:
            raise ChangeError(field, str(e)) from None
    return cleaned


def _shown(field: str, value: Any) -> str:
    kind = FIELDS[field][1]
    if kind == "aesthetics":
        return "\n".join(f"{a['tag']}: {a['because']}" if a.get("because") else a["tag"]
                         for a in value)
    if kind == "lines":
        return "\n".join(value)
    if kind == "list":
        return ", ".join(value)
    return value or ""


def diff(spec: dict, changes: list[dict]) -> list[dict]:
    """One row per changed field for the card: {field, label, kind, before, after}."""
    after = apply(spec, changes)
    rows = []
    for change in changes:
        field = change["field"]
        label, kind = FIELDS[field]
        rows.append({"field": field, "label": label,
                     "kind": "colour" if kind == "colour" else "text",
                     "before": _shown(field, current(spec, field)),
                     "after": _shown(field, current(after, field))})
    return rows


def clean(args: dict) -> dict:
    """The model's call, shaped: {kit_id, changes: [{field, value}]}. Says
    nothing yet about whether the kit would take the values (that is
    `check`, which needs the kit)."""
    try:
        kit_id = int(args.get("kit_id"))
    except (TypeError, ValueError):
        raise ChangeError("kit_id", "name the brand kit by its id") from None
    raw = args.get("changes")
    if not isinstance(raw, list) or not raw:
        raise ChangeError("changes", "list at least one change as {field, value}")
    if len(raw) > MAX_CHANGES:
        raise ChangeError("changes", f"at most {MAX_CHANGES} changes at once")
    changes, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ChangeError("changes", "each change is {field, value}")
        field = str(item.get("field") or "").strip()
        value = item.get("value")
        value = "" if value is None else value
        read(field, value)                     # the field exists and the value reads
        if field in seen:
            changes = [c for c in changes if c["field"] != field]
        seen.add(field)
        changes.append({"field": field, "value": value if isinstance(value, str) else ""})
    return {"kit_id": kit_id, "changes": changes}


def check(args: dict, kit: Optional[dict]) -> dict:
    """The proposal as the card draws it: the call shaped, held to the
    thread's kit, and every change shown before and after. ChangeError when
    the kit is not the thread's, or a value would be refused."""
    shaped = clean(args)
    if not kit:
        raise ChangeError("kit_id", "this project has no brand kit to change")
    if shaped["kit_id"] != kit["id"]:
        raise ChangeError("kit_id", f"the project's kit is {kit['id']} ({kit['name']})")
    rows = diff(kit.get("spec") or {}, shaped["changes"])
    return {**shaped, "kit_name": kit["name"], "diff": rows}


def summary(kit: dict) -> str:
    """The kit as the model reads it beside the tool: each field it may change
    and its value now."""
    spec = kit.get("spec") or {}
    lines = [f"Brand kit {kit['id']} “{kit['name']}”, as it is now:"]
    for field, (label, _kind) in FIELDS.items():
        shown = _shown(field, current(spec, field)).replace("\n", " / ")
        lines.append(f"- {field} ({label}): {shown or '(empty)'}")
    return "\n".join(lines)
