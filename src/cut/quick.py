"""
A clip or a still to a new shape, or a range of a clip, as a NEW item --
from a chat (2026-10-11, docs/tasks/task-connector-overnight.md PR 2).

Two simple edits the connector offers, `reformat` and `trim_clip`, built
the way `join.py` builds `assemble_clips`: nothing new is invented for
them. Each is a SCRATCH project in the editor (`cut:<uuid>`, version 1 by
the person) holding ONE clip, made through the same ops an editor would
click -- `insert`, `set_crop`, `set_canvas` -- validated by the same
validator, rendered by `render.render`, and filed on the Assets wall like
any render, so the result is a `gen:<id>` the next tool can name. The
source is never touched: a new file is written beside it.

REFORMAT. `aspect` is one of SIZES; `fit` is `pad` (the whole picture,
scaled to fit, black where the shapes differ -- what the renderer does
with every clip whose shape is not the canvas's) or `crop` (the picture
filling the frame, the middle kept: a static crop on the clip, the same
`crop` the editor's Inspector sets, computed here from the two shapes). A
crop past the editor's own bound (lanes.MAX_CROP per side) is refused
rather than clamped: two shapes that far apart leave too little picture.
A still comes back as a still (a PNG, `render(fmt="still")`), a clip as
a clip.

TRIM. `start` and `end` in seconds of the clip, turned into whole frames
at the project rate the way every op works; the range must lie inside
the clip and hold at least one frame. The clip's own sound comes along.

WHAT IT COSTS: nothing. ffmpeg runs on this server, no provider is
called, no credit is held, and the result says so. The wall's generations
row carries `cost_usd` NULL under the free log tool `cut`, as a join does.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional

from . import doc as d
from . import lanes, ops, render, sources, store

SIZES = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (1080, 1080), "4:5": (864, 1080)}
FITS = ("pad", "crop")
STILL_HOLD_SECONDS = 5           # a still on a timeline is held this long; a reformatted
LOG_TOOL = "cut"                 # still is exported as its first frame, so the hold is moot
FREE_NOTE = "Made on the studio's server with ffmpeg -- no credits were spent."


class QuickRefused(ValueError):
    """An edit that will not be made, and why -- a caller error, answered
    before anything is written or rendered."""


def _source(handle: str, *, account_id: Optional[int], dsn: Optional[str]) -> dict:
    """The row behind a `gen:<id>` render or an `asset:<id>` upload of
    this account's, with its kind (image or video). Somebody else's id is
    exactly as missing as one that never existed; audio is refused."""
    from .. import render_assets
    parsed = d.parse_handle(handle)
    if parsed is None:
        raise QuickRefused(f"{handle!r}: name the item as gen:<id> (a render) or asset:<id> "
                           "(an upload) -- `library` lists them. URLs are never taken")
    kind_of, id_ = parsed
    if kind_of == "asset":
        row = store.get_media(id_, account_id=account_id, dsn=dsn)
        if not row:
            raise QuickRefused(f"no upload {id_} on this account -- `library` lists them")
        media_kind = row.get("kind")
    else:
        row = render_assets.get(id_, dsn, account_id=account_id)
        if not row or row.get("deleted_at"):
            raise QuickRefused(f"no render {id_} on this account -- `library` lists them")
        media_kind = row.get("media_kind")
    if media_kind not in ("image", "video"):
        raise QuickRefused(f"{handle} is {media_kind or 'not a picture'}; this takes a clip "
                           "or a still")
    return {**row, "handle": handle, "media_kind": media_kind}


def _measured(handle: str, *, account_id: Optional[int], fps: int,
              dsn: Optional[str]) -> tuple[dict, dict]:
    media = sources.measure([handle], account_id=account_id, fps=fps, dsn=dsn)
    info = media.get(handle)
    if info is None:
        raise QuickRefused(f"could not read {handle} -- its file is not reachable right now")
    if not (info.get("width") and info.get("height")):
        raise QuickRefused(f"{handle} has no picture size this can work from")
    return media, info


def crop_for(width: int, height: int, size: tuple[int, int]) -> dict[str, float]:
    """The static crop that fills `size` with the middle of a `width` x
    `height` picture: fractions per side, zero where the shapes already
    agree. Raises QuickRefused when a side would pass the editor's bound."""
    source = width / height
    target = size[0] / size[1]
    sides = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
    if abs(source - target) <= 0.005 * target:
        return sides
    if source > target:                         # wider than the frame: trim the sides
        keep = target / source
        sides["left"] = sides["right"] = round((1 - keep) / 2, 4)
    else:                                       # taller: trim top and bottom
        keep = source / target
        sides["top"] = sides["bottom"] = round((1 - keep) / 2, 4)
    worst = max(sides.values())
    if worst > lanes.MAX_CROP:
        raise QuickRefused(
            f"a {width}x{height} picture is too far from {size[0]}x{size[1]} to crop "
            f"(it would cut {worst:.0%} off each side; the editor's bound is "
            f"{lanes.MAX_CROP:.0%}) -- use fit=\"pad\"")
    return sides


def plan_reformat(handle: str, aspect: str, fit: str = "pad", *, account_id: Optional[int],
                  fps: int = d.DEFAULT_FPS, dsn: Optional[str] = None) -> dict[str, Any]:
    """Every check, and the one-clip cut that would render. Writes nothing
    (the probe cache aside). Raises QuickRefused."""
    aspect = (aspect or "").strip()
    if aspect not in SIZES:
        raise QuickRefused(f"aspect must be one of {list(SIZES)}, got {aspect!r}")
    fit = (fit or "pad").strip().lower()
    if fit not in FITS:
        raise QuickRefused(f"fit must be one of {list(FITS)}, got {fit!r}")
    row = _source(handle, account_id=account_id, dsn=dsn)
    media, info = _measured(handle, account_id=account_id, fps=fps, dsn=dsn)
    size = SIZES[aspect]
    still = bool(info.get("still")) or row["media_kind"] == "image"
    if not still and not info.get("video"):
        raise QuickRefused(f"{handle} has no picture in it")
    if (info["width"], info["height"]) == size:
        raise QuickRefused(f"{handle} is already {size[0]}x{size[1]} ({aspect})")
    doc = d.starter_doc(fps, size)
    clip = {"media": handle, "src_in": 0,
            "src_out": STILL_HOLD_SECONDS * fps if still else int(info["frames"])}
    args: dict[str, Any] = {"track_id": "V1", "clip": clip}
    if not still and info.get("audio"):
        args["sound_track"] = "A1"
    doc = ops.apply(doc, "insert", args, media=media)
    clip_id = d.track(doc, "V1")["clips"][0]["id"]
    crop = None
    if fit == "crop":
        crop = crop_for(int(info["width"]), int(info["height"]), size)
        if any(crop.values()):
            doc = ops.apply(doc, "set_crop", {"clip_id": clip_id, **crop}, media=media)
        else:
            crop = None                 # the shapes already agree: nothing to cut
    return {"doc": doc, "media": media, "handle": handle, "aspect": aspect, "fit": fit,
            "size": list(size), "still": still, "crop": crop,
            "source_size": [int(info["width"]), int(info["height"])],
            "seconds": 0.0 if still else round(doc["duration"] / fps, 2), "fps": fps}


def plan_trim(handle: str, start: float, end: float, *, account_id: Optional[int],
              fps: int = d.DEFAULT_FPS, dsn: Optional[str] = None) -> dict[str, Any]:
    """Every check, and the one-clip cut holding `start`..`end` seconds of
    the clip. Raises QuickRefused."""
    try:
        start_s, end_s = float(start), float(end)
    except (TypeError, ValueError):
        raise QuickRefused("start and end are seconds, as numbers") from None
    if start_s < 0 or end_s <= start_s:
        raise QuickRefused(f"the range must run forward from 0: got {start_s:g}s to {end_s:g}s")
    row = _source(handle, account_id=account_id, dsn=dsn)
    if row["media_kind"] != "video":
        raise QuickRefused(f"{handle} is a still; only a clip has a range to keep")
    media, info = _measured(handle, account_id=account_id, fps=fps, dsn=dsn)
    if not info.get("video") or info.get("still"):
        raise QuickRefused(f"{handle} has no moving picture; only a clip can be trimmed")
    total = int(info["frames"])
    src_in, src_out = d.to_frames(start_s, fps), d.to_frames(end_s, fps)
    if src_out > total:
        raise QuickRefused(f"the range ends at {end_s:g}s, past the end of {handle} "
                           f"({total / fps:.2f}s long)")
    if src_out - src_in < 1:
        raise QuickRefused(f"a range of {end_s - start_s:g}s is shorter than one frame "
                           f"at {fps} fps")
    doc = d.starter_doc(fps, (int(info["width"]), int(info["height"]))
                        if int(info["width"]) % 2 == 0 and int(info["height"]) % 2 == 0
                        else d.DEFAULT_SIZE)
    args: dict[str, Any] = {"track_id": "V1",
                            "clip": {"media": handle, "src_in": src_in, "src_out": src_out}}
    if info.get("audio"):
        args["sound_track"] = "A1"
    doc = ops.apply(doc, "insert", args, media=media)
    return {"doc": doc, "media": media, "handle": handle, "start": start_s, "end": end_s,
            "frames": [src_in, src_out], "seconds": round((src_out - src_in) / fps, 2),
            "size": list(doc["size"]), "fps": fps}


def _make(planned: dict, *, account_id: Optional[int], model: str, text: str,
          params: dict, fmt: str, media_kind: str, title: str,
          project_id: Optional[int] = None, dsn: Optional[str] = None) -> dict[str, Any]:
    """Save the planned cut as version 1 of a scratch project, render it in
    `fmt`, file the result on the Assets wall under the free log tool.
    Raises render.RenderError / sources.SourceError with a reason."""
    from .. import generative, render_assets
    from .. import media as media_mod
    from ..shot import Shot
    doc, fps = planned["doc"], planned["fps"]
    row = store.create_project(account_id=account_id, title=title[:200], fps=fps, dsn=dsn)
    tl = store.save_version(row["timeline_key"], doc, account_id=account_id, author="user",
                           op_summary=text[:200], dsn=dsn)
    name = f"{row['timeline_key'].replace(':', '-')}-v{tl['version']}-{tl['id']}"
    with tempfile.TemporaryDirectory(prefix="phantra-quick-") as tmp:
        paths, media = sources.gather(d.handles(doc), account_id=account_id, fps=fps,
                                      workdir=Path(tmp), dsn=dsn)
        result = render.render(doc, account_id=account_id, name=name, paths=paths,
                               media=media, dsn=dsn, fmt=fmt)
    stored = result["stored"] or result["url"]
    if fmt == "mp4":
        store.set_export(tl["id"], stored, account_id=account_id, dsn=dsn)
        try:                                    # the wall's tile, as fal._publish draws one
            media_mod.mirror_poster(Path(result["path"]),
                                    f"renders/cut/{Path(result['path']).name}", account_id)
        except Exception:                       # noqa: BLE001 -- the tile falls back to the clip
            pass
    params = {"provider": LOG_TOOL, "model": model, "source": "mcp",
              "cut_project": row["id"], "timeline_id": tl["id"],
              "seconds": result["seconds"], **params,
              **({"project_id": int(project_id)} if project_id else {})}
    shot_id = generative.add_shot(Shot(subject=title[:100], action=model),
                                  notes=f"{model} by the studio MCP", dsn=dsn,
                                  account_id=account_id)
    generation_id = generative.record_generation(
        shot_id, LOG_TOOL, text, params=params, output_path=result["path"],
        cost_usd=None, notes="made locally with ffmpeg -- no provider, no credits",
        dsn=dsn, account_id=account_id)
    asset = render_assets.record_best_effort(
        account_id=account_id, generation_id=generation_id, tool=LOG_TOOL, model=model,
        media_kind=media_kind, prompt=text, media_url=stored, output_path=result["path"],
        metadata=params, dsn=dsn)
    asset_id = asset.get("id")
    return {"ok": True, "media_url": media_mod.url_for(stored, account_id) if stored else None,
            "asset_id": asset_id, "ref": f"gen:{asset_id}" if asset_id else None,
            "generation_id": generation_id, "media_kind": media_kind,
            "seconds": result["seconds"], "size": planned["size"],
            "cut_project": {"id": row["id"], "title": title, "version": tl["version"]},
            "notes": result["notes"], "credits": 0, "note": FREE_NOTE}


def reformat(planned: dict, *, account_id: Optional[int], title: Optional[str] = None,
             project_id: Optional[int] = None, dsn: Optional[str] = None) -> dict[str, Any]:
    h, aspect, fit = planned["handle"], planned["aspect"], planned["fit"]
    text = f"Reformatted {h} to {aspect} ({fit})"
    params = {"source_ref": h, "aspect": aspect, "fit": fit, "crop": planned["crop"],
              "canvas": {"width": planned["size"][0], "height": planned["size"][1],
                         "aspect": aspect},
              "source_size": planned["source_size"]}
    return _make(planned, account_id=account_id, model="reformat", text=text, params=params,
                 fmt="still" if planned["still"] else "mp4",
                 media_kind="image" if planned["still"] else "video",
                 title=(title or "").strip() or f"{h} as {aspect}",
                 project_id=project_id, dsn=dsn)


def trim(planned: dict, *, account_id: Optional[int], title: Optional[str] = None,
         project_id: Optional[int] = None, dsn: Optional[str] = None) -> dict[str, Any]:
    h = planned["handle"]
    text = f"Trimmed {h} to {planned['start']:g}-{planned['end']:g}s"
    params = {"source_ref": h, "start": planned["start"], "end": planned["end"],
              "frames": planned["frames"]}
    return _make(planned, account_id=account_id, model="trim", text=text, params=params,
                 fmt="mp4", media_kind="video",
                 title=(title or "").strip() or f"{h} {planned['start']:g}-{planned['end']:g}s",
                 project_id=project_id, dsn=dsn)


__all__ = ["SIZES", "FITS", "FREE_NOTE", "QuickRefused", "crop_for", "plan_reformat",
           "plan_trim", "reformat", "trim"]
