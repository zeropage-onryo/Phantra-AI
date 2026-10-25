"""
/api/whats-new -- the Create wall's announcements for one person
(2026-10-25, src/whats_new.py, docs/tasks/task-whats-new.md). Nothing here
spends, renders or writes an announcement; it reads the live ones and keeps
what this person has seen, dismissed or asked to be told about.

    GET  /api/whats-new                  {items, unread}: the live tiles they can use
    POST /api/whats-new/seen             {ids: [...]} marks them seen (the New badge)
    POST /api/whats-new/{id}/dismiss     the tile's X: never shown to them again
    POST /api/whats-new/{id}/notify      Coming soon's Notify me
"""
from __future__ import annotations

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
