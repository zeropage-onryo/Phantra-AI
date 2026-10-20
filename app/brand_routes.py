"""/api/brand-kits: the Brand Kit page's routes, and the free prompt preview
(docs/tasks/task-brand-kit.md §5). Included into app.api's router at the
bottom of that file, so every route sits under /api, behind the session gate,
and inside the route audit in tests/test_tenancy.py. Nothing here spends:
the end card is drawn here with Pillow, and the preview composes text.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src import brand_kits, preprod, projects

from . import auth

router = APIRouter()


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message, **extra}})


def _kit_error(e: brand_kits.KitError) -> JSONResponse:
    return _error(400, "invalid", str(e), field=e.field)


def view(kit: dict) -> dict[str, Any]:
    """A kit as the page reads it: files by id and an address on this API,
    never a stored name or a bucket URL."""
    files = [{"id": a["id"], "role": a["role"], "mime": a["mime"],
              "filename": (a.get("meta") or {}).get("filename") or "",
              "family": (a.get("meta") or {}).get("family"),
              "width": (a.get("meta") or {}).get("width"),
              "height": (a.get("meta") or {}).get("height"),
              "url": f"/api/brand-kits/{kit['id']}/assets/{a['id']}/file"}
             for a in kit.get("assets") or []]
    return {"id": kit["id"], "name": kit["name"], "spec": kit["spec"], "hash": kit["hash"],
            "files": files, "projects": kit.get("projects"),
            "created_at": kit["created_at"], "updated_at": kit["updated_at"],
            "look_suffix": brand_kits.look_suffix(kit)}


class KitBody(BaseModel):
    name: Optional[str] = None
    spec: Optional[dict] = None


@router.get("/brand-kits")
def kits_list(account_id: int = Depends(auth.current_account_id)):
    return {"kits": [view(k) for k in brand_kits.list_kits(account_id=account_id)],
            "roles": {role: {"label": label, "max": keep}
                      for role, (label, _m, _c, keep) in brand_kits.ASSET_ROLES.items()}}


@router.post("/brand-kits")
def kits_create(body: KitBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return view(brand_kits.create(body.name, body.spec, account_id=account_id))
    except brand_kits.KitError as e:
        return _kit_error(e)


@router.get("/brand-kits/{kit_id}")
def kits_get(kit_id: int, account_id: int = Depends(auth.current_account_id)):
    kit = brand_kits.get(kit_id, account_id=account_id)
    if not kit:
        return _error(404, "not_found", f"no brand kit {kit_id}")
    return view(kit)


@router.patch("/brand-kits/{kit_id}")
def kits_update(kit_id: int, body: KitBody, account_id: int = Depends(auth.current_account_id)):
    try:
        kit = brand_kits.update(kit_id, account_id=account_id, name=body.name, spec=body.spec)
    except brand_kits.KitError as e:
        return _kit_error(e)
    if not kit:
        return _error(404, "not_found", f"no brand kit {kit_id}")
    return view(kit)


@router.post("/brand-kits/{kit_id}/duplicate")
def kits_duplicate(kit_id: int, account_id: int = Depends(auth.current_account_id)):
    kit = brand_kits.duplicate(kit_id, account_id=account_id)
    if not kit:
        return _error(404, "not_found", f"no brand kit {kit_id}")
    return view(kit)


@router.delete("/brand-kits/{kit_id}")
def kits_delete(kit_id: int, account_id: int = Depends(auth.current_account_id)):
    """Soft: Undo is POST /brand-kits/{id}/restore."""
    if not brand_kits.delete(kit_id, account_id=account_id):
        return _error(404, "not_found", f"no brand kit {kit_id}")
    return {"deleted": kit_id}


@router.post("/brand-kits/{kit_id}/restore")
def kits_restore(kit_id: int, account_id: int = Depends(auth.current_account_id)):
    if not brand_kits.delete(kit_id, account_id=account_id, restore=True):
        return _error(404, "not_found", f"no brand kit {kit_id}")
    kit = brand_kits.get(kit_id, account_id=account_id)
    return view(kit) if kit else {"restored": kit_id}


@router.post("/brand-kits/{kit_id}/assets")
async def kits_add_asset(kit_id: int, request: Request,
                         account_id: int = Depends(auth.current_account_id)):
    """multipart: `role`, `file`, and for a font `licensed=1` -- the person
    saying they may embed it in video. An SVG logo's PNG (drawn in the
    browser) goes up as the logo role, the SVG itself as `<role>_source`."""
    form = await request.form()
    role = (form.get("role") or "").strip()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return _error(400, "invalid", "attach a file", field=role or "file")
    cap = brand_kits.ASSET_ROLES.get(role, (None, None, 40 << 20, 0))[2]
    data = await upload.read(cap + 1)
    try:
        added = brand_kits.add_asset(
            kit_id, role, data, account_id=account_id,
            filename=getattr(upload, "filename", "") or "",
            licensed=(form.get("licensed") or "") in ("1", "true", "yes", "on"))
    except brand_kits.KitError as e:
        if e.field == "kit":
            return _error(404, "not_found", f"no brand kit {kit_id}")
        return _kit_error(e)
    kit = brand_kits.get(kit_id, account_id=account_id)
    return {"added": added["id"], "kit": view(kit)}


@router.delete("/brand-kits/{kit_id}/assets/{asset_id}")
def kits_remove_asset(kit_id: int, asset_id: int,
                      account_id: int = Depends(auth.current_account_id)):
    if not brand_kits.remove_asset(kit_id, asset_id, account_id=account_id):
        return _error(404, "not_found", f"no file {asset_id} on brand kit {kit_id}")
    kit = brand_kits.get(kit_id, account_id=account_id)
    return {"removed": asset_id, "kit": view(kit) if kit else None}


@router.get("/brand-kits/{kit_id}/assets/{asset_id}/file")
def kits_asset_file(kit_id: int, asset_id: int,
                    account_id: int = Depends(auth.current_account_id)):
    """The file's bytes, for the account that owns the kit only."""
    kit = brand_kits.get(kit_id, account_id=account_id)
    found = next((a for a in (kit or {}).get("assets") or [] if a["id"] == asset_id), None)
    if not found:
        return _error(404, "not_found", "no such file")
    data = brand_kits.file_bytes(found["stored"], account_id)
    if data is None:
        return _error(404, "not_found", "that file is not on this server or in the bucket")
    return Response(content=data, media_type=found["mime"],
                    headers={"Cache-Control": "private, max-age=3600"})


@router.get("/brand-kits/{kit_id}/end-card.png")
def kits_end_card(kit_id: int, aspect: str = "16:9",
                  account_id: int = Depends(auth.current_account_id)):
    """The end card as an export would draw it, at the editor's canvas for
    `aspect`. Drawn here with Pillow -- nothing is generated or spent."""
    import tempfile
    from pathlib import Path

    from src.cut import brand as cut_brand
    from src.cut import doc as cut_doc

    kit = brand_kits.get(kit_id, account_id=account_id)
    if not kit:
        return _error(404, "not_found", f"no brand kit {kit_id}")
    if aspect not in cut_doc.ASPECT_SIZES:
        return _error(400, "invalid", f"aspect must be one of {', '.join(cut_doc.ASPECT_SIZES)}")
    with tempfile.TemporaryDirectory(prefix="phantra-card-") as tmp:
        prepared = cut_brand.prepare(kit, Path(tmp), cut_doc.ASPECT_SIZES[aspect], end_card=True)
        png = prepared["end_card"]["path"].read_bytes()
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "private, no-cache"})


# --------------------------------------------------------------------------
# a project picks a kit
# --------------------------------------------------------------------------

class ProjectKitBody(BaseModel):
    brand_kit_id: Optional[int] = None


@router.put("/projects/{project_id}/brand-kit")
def project_set_kit(project_id: int, body: ProjectKitBody,
                    account_id: int = Depends(auth.current_account_id)):
    """Pick the project's brand kit, or clear it with null. Every scene the
    project writes and every render it makes from here on reads it."""
    try:
        project = projects.set_brand_kit(project_id, body.brand_kit_id, account_id=account_id)
    except ValueError as e:
        return _error(404, "not_found", str(e))
    kit = brand_kits.for_project(project)
    return {"project_id": project["id"],
            "brand_kit": {"id": kit["id"], "name": kit["name"]} if kit else None}


@router.get("/projects/{project_id}/brand-kit")
def project_get_kit(project_id: int, account_id: int = Depends(auth.current_account_id)):
    project = projects.get(project_id, account_id=account_id)
    if project is None:
        return _error(404, "not_found", f"no project {project_id}")
    kit = brand_kits.for_project(project)
    return {"project_id": project["id"],
            "picked": project.get("brand_kit_id"),
            "brand_kit": ({"id": kit["id"], "name": kit["name"],
                           "palette": kit["spec"].get("palette") or []} if kit else None)}


# --------------------------------------------------------------------------
# what a render would send -- the free way to see a kit applied
# --------------------------------------------------------------------------

@router.get("/scenes/{concept_id}/prompt-preview")
def scene_prompt_preview(concept_id: int, account_id: int = Depends(auth.current_account_id)):
    """The clip and keyframe prompts this scene's renders would send, with
    and without its project's brand kit, and how many of the kit's look
    references a keyframe would carry. Composes text only: no model call,
    no spend. (A per-model prompt rule, when one is switched on, reshapes
    the clip prompt before the kit's lines are added; this shows the
    prompt as written.)"""
    from src import shootgen, timeline

    concept = preprod.get_concept(concept_id, account_id=account_id)
    if concept is None or not concept.get("shots"):
        return _error(404, "not_found", f"no scene {concept_id}")
    shot = concept["shots"][0]
    kit = brand_kits.for_concept(concept_id, account_id=account_id)
    tl = shot.get("timeline") or {}
    parts = [None] + [p.get("n") for p in tl.get("parts") or []]
    clips, stills = [], []
    for part in parts:
        target = timeline.render_target(shot, part)
        if not target:
            continue
        clips.append({"part": part, "prompt": target["prompt"],
                      "branded": brand_kits.dress(target["prompt"], kit)})
        still = (shot.get("prompt") or "").strip() if part is None else timeline.render_prompt(
            next(p for p in tl["parts"] if p.get("n") == part), tl)
        still = shootgen.bind_references(still, list(target.get("refs") or []))
        stills.append({"part": part, "prompt": still, "branded": brand_kits.dress(still, kit)})
    refs = [a for a in (kit or {}).get("assets") or [] if a["role"] == "reference"]
    return {"concept_id": concept_id,
            "brand_kit": ({"id": kit["id"], "name": kit["name"], "hash": kit["hash"]}
                          if kit else None),
            "look_suffix": brand_kits.look_suffix(kit),
            "kit_references": min(len(refs), brand_kits.STILL_REFS_MAX),
            "writer_block": brand_kits.brief_lines(kit),
            "clips": clips, "stills": stills}
