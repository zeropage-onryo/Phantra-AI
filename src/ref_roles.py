"""What each attached reference is FOR (2026-10-11; item 8 of
docs/tasks/task-studio-agent.md, from invideo's reference handling: "you
say what to take from it -- lighting, framing, palette").

Until now every picture attached to the box meant the same thing: an
element's photo was captioned by what it is (shootgen.reference_label:
"the EXACT face and likeness"), and an upload was only "a reference photo
supplied with this prompt". A frame attached for its LIGHT was therefore
read like a frame attached for its subject, and the model copied the
person in it.

A role is one word the person puts on a reference. It does two things,
both in code rather than left to a model:

  * the CAPTION the model reads immediately before that image says what to
    take from it and what to leave (`caption`), and
  * a reference that only lends its look is never put FIRST (`order`):
    the first reference is what a clip and a keyframe anchor on, and a
    light reference in that slot becomes the subject.

Roles ride beside the references, never inside them: `{ref: role}` keyed
by the same string the shot stores (`asset_shelf.storable_ref`), in
`shot["ref_roles"]`. A reference with no role reads exactly as it always
did.

Pure: no database, no model, nothing from `app/`.
"""
from __future__ import annotations

import json
from typing import Iterable, Optional

# role -> (what the page calls it, the caption's instruction)
ROLES: dict[str, tuple[str, str]] = {
    "subject": ("Subject",
                "the EXACT person or subject: match the face, hair, build and what they wear"),
    "product": ("Product",
                "the EXACT product: match its shape, label, colours and proportions; do not "
                "redesign it"),
    "place": ("Place",
              "the location: match the space and what is in it; do not copy this photo's framing"),
    "light": ("Light",
              "use ONLY its lighting -- direction, hardness, colour and contrast. Do not copy "
              "its subject, its place or its framing"),
    "palette": ("Palette",
                "use ONLY its colour palette and grade. Do not copy its subject, its place or "
                "its framing"),
    "framing": ("Framing",
                "use ONLY its composition -- camera height, angle, distance and where the "
                "subject sits in frame. Do not copy its subject or its place"),
    "style": ("Style",
              "use ONLY its overall look -- texture, finish and mood. Do not copy its subject "
              "or its place"),
}

# what the picture is OF: these may anchor a keyframe and a clip
IDENTITY = ("subject", "product")
# what is only BORROWED from the picture: never the anchor
LOOK_ONLY = ("light", "palette", "framing", "style")

MAX_ROLES = 16


def options() -> list[dict]:
    """The menu a page draws, in order."""
    return [{"id": key, "label": label, "look_only": key in LOOK_ONLY}
            for key, (label, _) in ROLES.items()]


def clean(raw) -> dict[str, str]:
    """`{ref: role}` out of whatever arrived -- a dict, or the JSON text of
    one (a form field). An unknown role, a blank ref, a non-string: dropped,
    never raised; a request with a bad role is a request with no role."""
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw or "{}")
        except (TypeError, ValueError):
            return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for ref, role in raw.items():
        if len(out) >= MAX_ROLES:
            break
        if isinstance(ref, str) and isinstance(role, str):
            key, value = ref.strip().split("?")[0], role.strip().lower()
            if key and value in ROLES:
                out[key] = value
    return out


def caption(role: str) -> str:
    """The line a model reads immediately before the image. "" for a role
    that is not one."""
    found = ROLES.get((role or "").strip().lower())
    return f"Reference photo — {found[1]}:" if found else ""


def label(ref: str, roles: Optional[dict]) -> str:
    """The caption for one reference: its role's when it has one, else what
    it has always been (the element's own name and kind, or the plain
    "supplied with this prompt")."""
    from . import shootgen
    role = (roles or {}).get(str(ref or "").split("?")[0])
    return caption(role) if role else shootgen.reference_label(ref)


def order(refs: Iterable[str], roles: Optional[dict]) -> list[str]:
    """The references with look-only ones moved LAST, everything else in
    the order it came (which is load-bearing: manual picks first, identity
    before place). Stable, and a list with no roles comes back as it is."""
    refs = list(refs or [])
    roles = roles or {}
    look = [r for r in refs if roles.get(str(r).split("?")[0]) in LOOK_ONLY]
    if not look:
        return refs
    return [r for r in refs if r not in look] + look


def for_refs(roles: Optional[dict], refs: Iterable[str]) -> dict[str, str]:
    """The roles of exactly these references -- what is stored on a shot
    beside its refs, so a role for a picture the shot does not carry is
    never kept."""
    held = {str(r).split("?")[0] for r in (refs or [])}
    return {ref: role for ref, role in (roles or {}).items() if ref in held}


def rekey(roles: Optional[dict], rename) -> dict[str, str]:
    """The same roles under the names a shot stores its refs by
    (`rename` = asset_shelf.storable_ref): the composer posts a URL, the
    shot keeps a logical name."""
    out: dict[str, str] = {}
    for ref, role in (roles or {}).items():
        try:
            key = rename(ref)
        except Exception:                                   # noqa: BLE001
            key = ref
        if key:
            out[str(key).split("?")[0]] = role
            out.setdefault(ref, role)
    return out


def prompt_note(refs: Iterable[str], roles: Optional[dict]) -> str:
    """For a model that is handed pictures with no caption slot (an image
    model's `image_urls`): the same instructions as one paragraph the
    prompt can carry, the pictures named by their position. "" when no
    reference has a role."""
    roles = roles or {}
    lines = []
    for i, ref in enumerate(refs or [], start=1):
        found = ROLES.get(roles.get(str(ref).split("?")[0], ""))
        if found:
            lines.append(f"Reference image {i}: {found[1]}.")
    return " ".join(lines)


__all__ = ["ROLES", "IDENTITY", "LOOK_ONLY", "MAX_ROLES", "options", "clean", "caption",
           "label", "order", "for_refs", "rekey", "prompt_note"]
