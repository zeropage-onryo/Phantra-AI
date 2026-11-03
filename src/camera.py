"""Camera move and lens on the Video page (2026-11-03, Mike: "wire in the
camera move option and lens options"; docs/tasks/task-camera-lens.md).

Verified against each model's queue schema that day: only LTX 2.5 (Fast
and Pro) has a camera setting (`camera_motion`, eight values); no clip
model has a lens setting. So one pick reaches a model one of three ways,
and the page says which ("mode"):

- ``exact``  -- LTX 2.5 and a move it has: the move goes in
  `camera_motion`, and its words go in the prompt as well (LTX wants the
  camera in the prose too, prompts/models/ltx.md).
- ``clip``   -- a model that holds video references (fal.REF2V
  `video_field`), a move Mike has shot a reference clip of, no start
  frame, and fal as the host (Replicate takes no video input): the clip rides as @Video1 with `clip_line`. OFF until
  PHANTRA_CAMERA_CLIPS=1: no clip is shot yet, and whether a video
  reference changes the provider's price is unmeasured.
- ``guided`` -- everything else: the move's fixed words.

Lens is words on every model, describing what the lens does to the
picture. Nothing here calls a model or spends: it decides the words and
the fields, and the route sends them. Every line of copy is in
prompts/camera.json.

A pick off the table is REFUSED (ValueError), never dropped.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

TABLE = Path(__file__).resolve().parent.parent / "prompts" / "camera.json"
CLIPS_ENV = "PHANTRA_CAMERA_CLIPS"


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8"))


def moves() -> list[dict]:
    return list(table()["moves"])


def move(move_id: Optional[str]) -> Optional[dict]:
    if not move_id:
        return None
    for m in table()["moves"]:
        if m["id"] == move_id:
            return m
    raise ValueError(f"no camera move called {move_id!r}")


def _pick(kind: str, key: Optional[str]) -> Optional[dict]:
    if not key:
        return None
    entry = table()[kind].get(key)
    if entry is None:
        raise ValueError(f"no {kind.rstrip('s')} called {key!r}")
    return entry


def clips_on() -> bool:
    return os.environ.get(CLIPS_ENV, "").strip() == "1"


def ltx_values(model: str) -> tuple[str, ...]:
    """The camera_motion values the model takes, () when it has none."""
    from . import fal
    return tuple(fal.VIDEO_MODELS.get(model, {}).get("camera_motions") or ())


def video_ref_field(model: str) -> Optional[str]:
    from . import fal
    return (fal.ref_spec(model) or {}).get("video_field")


def _clip_ready(model: str, m: dict, resolution: Optional[str]) -> bool:
    from . import fal
    return bool(clips_on() and m.get("clip") and video_ref_field(model)
                and fal.host_for(model, resolution) == "fal")


def mode(model: str, move_id: Optional[str], *, start_frame: bool = False,
         resolution: Optional[str] = None) -> Optional[str]:
    """How this move reaches this model: exact / clip / guided, None for
    no move."""
    m = move(move_id)
    if m is None:
        return None
    if m.get("ltx") and m["ltx"] in ltx_values(model):
        return "exact"
    if not start_frame and _clip_ready(model, m, resolution):
        return "clip"
    return "guided"


def menu_for(model: str) -> dict:
    """What the page shows per model: the moves it takes exactly, the moves
    a reference clip can carry and at which resolutions."""
    exact = [m["id"] for m in table()["moves"]
             if m.get("ltx") and m["ltx"] in ltx_values(model)]
    from . import fal
    clips = [m["id"] for m in table()["moves"]
             if clips_on() and m.get("clip") and video_ref_field(model)]
    tiers = (fal.VIDEO_MODELS.get(model) or {}).get("resolutions") or ()
    # a clip rides only where fal renders (Replicate takes no video input)
    clip_tiers = [r for r in tiers if fal.host_for(model, r) == "fal"] if clips else []
    return {"exact": exact, "clips": clips if clip_tiers else [],
            "clip_resolutions": clip_tiers}


def catalogue() -> dict:
    """The cards' contents, for the page: moves, focal lengths, apertures,
    looks and the pairs that contradict each other."""
    t = table()
    return {
        "moves": [{"id": m["id"], "label": m["label"], "words": m["words"]}
                  for m in t["moves"]],
        "focal": [{"id": k, **v} for k, v in t["focal"].items()],
        "aperture": [{"id": k, **v} for k, v in t["aperture"].items()],
        "looks": [{"id": k, **v} for k, v in t["looks"].items()],
        "conflicts": [{"a": a, "b": b, "why": why} for a, b, why in t["conflicts"]],
    }


def conflict(picks) -> Optional[str]:
    """Why two picks contradict each other, or None."""
    chosen = {p for p in picks if p}
    for a, b, why in table()["conflicts"]:
        if a in chosen and b in chosen:
            return why
    return None


def lens_words(focal: Optional[str] = None, aperture: Optional[str] = None,
               look: Optional[str] = None) -> str:
    parts = [e["words"] for e in (_pick("focal", focal), _pick("aperture", aperture),
                                  _pick("looks", look)) if e]
    return ("Lens: " + "; ".join(parts) + ".") if parts else ""


def placement(model: str) -> str:
    from . import fal
    platform = fal.VIDEO_MODELS.get(model, {}).get("platform", "")
    return table()["placement"].get(platform, "tail")


def clip_url(move_id: str) -> Optional[str]:
    """The public address of Mike's reference clip of the move, None when
    there is none or no bucket is configured."""
    from . import storage
    m = move(move_id)
    key = (m or {}).get("clip")
    base = storage.public_base_url()
    return f"{base}/{key}" if key and base else None


def dress(prompt: str, model: str, *, move_id: Optional[str] = None,
          focal: Optional[str] = None, aperture: Optional[str] = None,
          look: Optional[str] = None, start_frame: bool = False,
          resolution: Optional[str] = None, video_tag: str = "@Video1") -> dict:
    """The prompt with the camera and lens lines placed for the model, and
    the fields that go beside it:

        {"prompt", "mode", "camera_motion" (or None), "video_refs" (list),
         "added" (the lines added, as shown on the page's chips)}

    ValueError on a pick off the table or two picks that contradict."""
    why = conflict([move_id, focal, aperture, look])
    if why:
        raise ValueError(why)
    m = move(move_id)
    how = mode(model, move_id, start_frame=start_frame, resolution=resolution)
    lens = lens_words(focal, aperture, look)
    camera_line = ""
    video_refs: list = []
    if how == "clip":
        url = clip_url(m["id"])
        if url:
            video_refs = [url]
            camera_line = table()["clip_line"].format(tag=video_tag)
        else:  # a clip named but unreachable: the words, said as guided
            how = "guided"
    if how in ("exact", "guided"):
        camera_line = m["words"]
    added = [line for line in (camera_line, lens) if line]
    if not added:
        return {"prompt": prompt, "mode": None, "camera_motion": None,
                "video_refs": [], "added": []}
    block = " ".join(added)
    text = (f"{block}\n\n{prompt}" if placement(model) == "lead"
            else f"{prompt}\n\n{block}")
    return {"prompt": text, "mode": how,
            "camera_motion": m["ltx"] if how == "exact" else None,
            "video_refs": video_refs, "added": added}
