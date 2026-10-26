"""
/api/whats-new -- the Create wall's announcements for one person
(2026-10-25, src/whats_new.py, docs/tasks/task-whats-new.md). Nothing here
spends, renders or writes an announcement; it reads the live ones and keeps
what this person has seen, dismissed or asked to be told about.

    GET  /api/whats-new                  {items, unread}: the live tiles they can use
    POST /api/whats-new/seen             {ids: [...]} marks them seen (the New badge)
    POST /api/whats-new/{id}/dismiss     the tile's X: never shown to them again
    POST /api/whats-new/{id}/notify      Coming soon's Notify me

The operator's Showcase list (step 2), for the OWNERS of the house account
(whats_new.house_account_id, PHANTRA_SHOWCASE_ACCOUNT, default `phantra`)
and nobody else; anyone else gets a plain 404, the same for every caller:

    GET  /api/whats-new/showcase              every announcement, waiting ones first, priced
    PUT  /api/whats-new/showcase/{id}         words, prompt, seconds / resolution / aspect
    POST /api/whats-new/showcase/{id}/quote   the render's price on the house account
    POST /api/whats-new/showcase/{id}/approve {expect_credits}: render it (the ONLY spend)
    POST /api/whats-new/showcase/{id}/pick    {asset: "gen:<id>"} a house Library item instead
    POST /api/whats-new/showcase/{id}/keep    live for everyone
    POST /api/whats-new/showcase/{id}/redo    back to waiting; the take stays in the Library
    POST /api/whats-new/showcase/{id}/skip    never shown
    POST /api/whats-new/showcase/{id}/restore skipped -> waiting

Approve is the priced card's click: `expect_credits` must equal the quote
(409 price_changed if it moved), the render takes the house account's ledger
hold before fal is called, and a failure releases it (the adapter's rule).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src import whats_new

from . import auth

router = APIRouter(prefix="/whats-new")


class SeenBody(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=200)


def _user_id(request: Request) -> str:
    return str((auth.current_user(request) or {}).get("id") or "")


def _no_user() -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": {
        "code": "signed_out", "message": "Sign in to see what's new."}})


@router.get("")
def whats_new_feed(request: Request, account_id: int = Depends(auth.current_account_id)):
    user_id = _user_id(request)
    if not user_id:
        return _no_user()
    from . import api  # compute_capabilities lives there; api imports this module
    caps = api.compute_capabilities(account_id)
    return whats_new.feed(account_id, user_id, caps)


@router.post("/seen")
def whats_new_seen(body: SeenBody, request: Request,
                   account_id: int = Depends(auth.current_account_id)):
    user_id = _user_id(request)
    if not user_id:
        return _no_user()
    return {"marked": whats_new.mark(account_id, user_id, body.ids, "seen")}


@router.post("/{item_id}/dismiss")
def whats_new_dismiss(item_id: str, request: Request,
                      account_id: int = Depends(auth.current_account_id)):
    user_id = _user_id(request)
    if not user_id:
        return _no_user()
    return {"marked": whats_new.mark(account_id, user_id, [item_id], "dismissed")}


@router.post("/{item_id}/notify")
def whats_new_notify(item_id: str, request: Request,
                     account_id: int = Depends(auth.current_account_id)):
    user_id = _user_id(request)
    if not user_id:
        return _no_user()
    n = whats_new.mark(account_id, user_id, [item_id], "notify")
    if not n:
        return JSONResponse(status_code=404, content={"error": {
            "code": "not_coming_soon", "message": "That isn't a coming-soon item."}})
    return {"marked": n}


# --------------------------------------------------------------------------
# the operator's Showcase list
# --------------------------------------------------------------------------


def _operator(request: Request, account_id: int) -> Optional[int]:
    """The house account when the caller is one of its owners, else None."""
    house = whats_new.house_account_id()
    if house is None or int(account_id) != house:
        return None
    row = auth.tenant_account(request, account_id)
    return house if row and row.get("role") == "owner" else None


def _hidden() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": {
        "code": "not_found", "message": "Not found."}})


def _refused(e: Exception, status: int = 409) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {
        "code": "showcase_refused", "message": str(e)}})


def _priced(item: dict, house: int) -> dict:
    """An item with its render price when it is waiting to be rendered;
    credits only, never dollars."""
    if item["status"] == whats_new.PENDING and whats_new.renderable(item):
        try:
            item["credits"] = whats_new.quote(item, house)["credits"]
        except whats_new.Refused as e:
            item["credits"], item["price_note"] = None, str(e)
    return item


@router.get("/showcase")
def showcase_list(request: Request, account_id: int = Depends(auth.current_account_id)):
    house = _operator(request, account_id)
    if house is None:
        return _hidden()
    return {"items": [_priced(i, house) for i in whats_new.queue()]}


class EditBody(BaseModel):
    title: Optional[str] = None
    line: Optional[str] = None
    accent: Optional[str] = None
    size: Optional[str] = None
    prompt: Optional[str] = None
    seconds: Optional[int] = None
    resolution: Optional[str] = None
    aspect: Optional[str] = None


@router.put("/showcase/{item_id}")
def showcase_edit(item_id: str, body: EditBody, request: Request,
                  account_id: int = Depends(auth.current_account_id)):
    house = _operator(request, account_id)
    if house is None:
        return _hidden()
    try:
        return _priced(whats_new.edit(item_id, body.model_dump(exclude_none=True)), house)
    except whats_new.Refused as e:
        return _refused(e, 400)


@router.post("/showcase/{item_id}/quote")
def showcase_quote(item_id: str, request: Request,
                   account_id: int = Depends(auth.current_account_id)):
    house = _operator(request, account_id)
    if house is None:
        return _hidden()
    item = whats_new.get(item_id)
    if item is None:
        return _hidden()
    try:
        q = whats_new.quote(item, house)
    except whats_new.Refused as e:
        return _refused(e, 400)
    return {k: v for k, v in q.items() if k != "usd"}


class ApproveBody(BaseModel):
    expect_credits: int


@router.post("/showcase/{item_id}/approve")
def showcase_approve(item_id: str, body: ApproveBody, request: Request,
                     account_id: int = Depends(auth.current_account_id)):
    """Render the showcase on the house account. The click on the card that
    showed `expect_credits` is the approval; nothing else here spends."""
    from src import fal, render_assets

    from . import api, jobs
    house = _operator(request, account_id)
    if house is None:
        return _hidden()
    item = whats_new.get(item_id)
    if item is None:
        return _hidden()
    try:
        q = whats_new.quote(item, house)
    except whats_new.Refused as e:
        return _refused(e, 400)
    if q["credits"] != body.expect_credits:
        return api._price_moved(q["credits"])
    if not fal.has_key(house):
        return api._error(503, "generation_unavailable", "fal is not set up on this server")
    try:
        whats_new.start_render(item_id)
    except whats_new.Refused as e:
        return _refused(e)
    clip = item["media_kind"] == "clip"
    label, prompt = q["label"], item["prompt"]

    def work(job):
        try:
            jobs.progress(job, 0.1, f"rendering the {label} showcase")
            if clip:
                res = fal.generate_from_prompt(
                    prompt, model=q["model"], duration=q["seconds"], resolution=q["resolution"],
                    aspect_ratio=q["aspect"], approved=True, account_id=house,
                    source="showcase", bank=True)
            else:
                res = fal.generate_image_from_prompt(
                    prompt, model=q["model"], aspect=q["aspect"], approved=True, db_path=None,
                    account_id=house, source="showcase", bank=True, brand_kit=False)
            if not res.get("ok"):
                raise RuntimeError(api._render_failed(res.get("error"),
                                                      "The clip" if clip else "The still"))
            asset = res.get("asset_id")
            row = render_assets.get(int(asset), account_id=house) if asset else None
            if not row or not row.get("media_url"):
                raise RuntimeError("The render finished but wasn't filed in the Library.")
            whats_new.finish_render(item_id, media=row["media_url"],
                                    media_type="video" if clip else "image",
                                    account_id=house, gen_id=f"gen:{asset}",
                                    credits=q["credits"])
        except Exception as e:
            whats_new.fail_render(item_id, str(e))
            raise
        return {"detail": f"{label} showcase · ready to keep", "output": res.get("media_url"),
                "media": "video" if clip else "image", "asset": f"gen:{asset}"}

    job = jobs.start("make", f"showcase · {item['title'][:50]}", work, account_id=house)
    return {"job_id": job["id"], "credits": q["credits"], "charged": q["charged"]}


class PickBody(BaseModel):
    asset: str


@router.post("/showcase/{item_id}/pick")
def showcase_pick(item_id: str, body: PickBody, request: Request,
                  account_id: int = Depends(auth.current_account_id)):
    """Use a render already in the house Library as the tile's picture."""
    from src import render_assets
    house = _operator(request, account_id)
    if house is None:
        return _hidden()
    raw = body.asset.strip()
    asset_id = raw.removeprefix("gen:")
    if not asset_id.isdigit():
        return _refused("pick a Library item by its gen:<id>", 400)
    row = render_assets.get(int(asset_id), account_id=house)
    if not row or row.get("deleted_at"):
        return _refused("that isn't in the house Library", 400)
    try:
        return whats_new.pick(item_id, media=row["media_url"],
                              media_type="video" if row["media_kind"] == "video" else "image",
                              account_id=house, gen_id=f"gen:{asset_id}")
    except whats_new.Refused as e:
        return _refused(e)


def _transition(name: str):
    def route(item_id: str, request: Request,
              account_id: int = Depends(auth.current_account_id)):
        if _operator(request, account_id) is None:
            return _hidden()
        try:
            return getattr(whats_new, name)(item_id)
        except whats_new.Refused as e:
            return _refused(e)
    route.__name__ = f"showcase_{name}"
    return route


for _name in ("keep", "redo", "skip", "restore"):
    router.add_api_route(f"/showcase/{{item_id}}/{_name}", _transition(_name), methods=["POST"])
