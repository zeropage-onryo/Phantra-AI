"""Which video models refuse a real person's photo as a reference (2026-11-02).

Tested that day with Mike's own headshot as a Seedance 2.5 reference, the
same 5 s 720p request on two hosts:

  * fal: 422 content_policy_violation, "The images or videos provided may
    contain likenesses of real people or other private information that
    cannot be processed" (reason `partner_validation_failed`: ByteDance's
    own check, applied before fal renders anything);
  * Replicate: failed in 3 s, "The input or output was flagged as
    sensitive. (E005)".

So the refusal is the model's, on every host, and a scene held to a person's
photo cannot render on Seedance anywhere. Nothing was charged either time.
Seven of the eight refused renders in the 2026-10-27 audit were content
filter blocks, most likely this.

What this module does about it is ADVICE, never a lock ("prompts request,
code advises"): the Render card says it before the click when the pick is
one of these models and the scene holds a person, and failures.plain says
it in place of "reword it" when the refusal comes back. A drawn creature
held as a character is still offered Seedance; the note says "if".

Pure: no database, no model, nothing from `app/`.
"""
from __future__ import annotations

from typing import Iterable, Optional

from . import asset_shelf, ref_roles

# fal.VIDEO_MODELS ids whose maker refuses a real person as a reference
REFUSE_REAL_PEOPLE: tuple[str, ...] = ("seedance2.5", "seedance2", "seedance2-fast")

# what to offer instead, in order: the people models in the table
FOR_PEOPLE: tuple[str, ...] = ("kling4", "veo3.1")

NOTE = ("Seedance won't take a photo of a real person as a reference; ByteDance refuses it "
        "on every host, and nothing is charged when it does. If this scene's person is real, "
        "render it on Kling 4.0 or Veo 3.1.")


def refuses_people(model: Optional[str]) -> bool:
    return (model or "") in REFUSE_REAL_PEOPLE


def holds_person(refs: Iterable[str], roles: Optional[dict] = None) -> bool:
    """True when any reference is a person: a `subject` role, or a
    character element's photo (asset_shelf.parse_ref)."""
    roles = ref_roles.clean(roles) if roles else {}
    for ref in refs or ():
        if roles.get(str(ref).strip().split("?")[0]) == "subject":
            return True
        parsed = asset_shelf.parse_ref(str(ref))
        if parsed and parsed.get("kind") == "character":
            return True
    return False


def shot_holds_person(shot: Optional[dict]) -> bool:
    shot = shot or {}
    return holds_person(shot.get("refs") or [], shot.get("ref_roles"))


def note_for(model: Optional[str], shot: Optional[dict]) -> str:
    """The card's sentence for this pick, or "" when it does not apply."""
    return NOTE if refuses_people(model) and shot_holds_person(shot) else ""


def card_fields(shot: Optional[dict]) -> dict:
    """What the Render card needs to say NOTE for whichever model is picked:
    whether the scene holds a person, which models refuse one, the sentence."""
    person = shot_holds_person(shot)
    return {"holds_person": person,
            "people_refusers": list(REFUSE_REAL_PEOPLE) if person else [],
            "people_note": NOTE if person else ""}
