"""
/api/posts -- the calendar's and the composer's door onto `posts`
(2026-10-22, src/posts.py). Every route is one account's; nothing here
sends anything -- the worker does, on the clock -- and nothing spends.

    GET    /api/posts?start&end&state   the calendar's read
    POST   /api/posts                   schedule (or draft) one post
    GET    /api/posts/{id}              one post, with its own log
    PATCH  /api/posts/{id}              caption / settings
    PUT    /api/posts/{id}/date         move it
    POST   /api/posts/{id}/state        queued | draft | cancelled
    DELETE /api/posts/{id}              soft

A refusal is 400 `post_refused` with the words posts.py wrote.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src import posts
from src.posts import PostRefused

from . import auth

router = APIRouter(prefix="/posts")


def _refused(e: Exception) -> JSONResponse:
    return JSONResponse(status_code=400,
                        content={"error": {"code": "post_refused", "message": str(e)}})


class CreateBody(BaseModel):
    connection_id: int
    source: str = Field(..., description="gen:<id> or asset:<id>")
    caption: str = ""
    publish_at: Optional[str] = Field(None, description="ISO 8601; empty = now")
    settings: dict[str, Any] = Field(default_factory=dict)
    draft: bool = False
    project_id: Optional[int] = None
    group_id: Optional[str] = None


class PatchBody(BaseModel):
    caption: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class DateBody(BaseModel):
    publish_at: Optional[str] = None


class StateBody(BaseModel):
    state: str


@router.get("")
def posts_list(start: Optional[str] = None, end: Optional[str] = None,
               state: Optional[str] = None, limit: int = 500,
               account_id: int = Depends(auth.current_account_id)):
    try:
        return {"posts": posts.list_for(account_id, start=start, end=end, state=state, limit=limit)}
    except PostRefused as e:
        return _refused(e)


@router.post("")
def posts_create(body: CreateBody, request: Request,
                 account_id: int = Depends(auth.current_account_id)):
    user = auth.current_user(request) or {}
    try:
        return posts.create(account_id, connection_id=body.connection_id, source_ref=body.source,
                            caption=body.caption, publish_at=body.publish_at, settings=body.settings,
                            draft=body.draft, project_id=body.project_id, group_id=body.group_id,
                            creation_method="web", created_by=user.get("id"))
    except PostRefused as e:
        return _refused(e)


@router.get("/{post_id}")
def posts_get(post_id: int, account_id: int = Depends(auth.current_account_id)):
    post = posts.get(account_id, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="no such post")
    post["events"] = posts.events(account_id, post_id)
    return post


@router.patch("/{post_id}")
def posts_patch(post_id: int, body: PatchBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return posts.update(account_id, post_id, caption=body.caption, settings=body.settings)
    except PostRefused as e:
        return _refused(e)


@router.put("/{post_id}/date")
def posts_move(post_id: int, body: DateBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return posts.set_date(account_id, post_id, body.publish_at)
    except PostRefused as e:
        return _refused(e)


@router.post("/{post_id}/state")
def posts_state(post_id: int, body: StateBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return posts.set_state(account_id, post_id, body.state)
    except PostRefused as e:
        return _refused(e)


@router.delete("/{post_id}")
def posts_delete(post_id: int, account_id: int = Depends(auth.current_account_id)):
    try:
        gone = posts.remove(account_id, post_id)
    except PostRefused as e:
        return _refused(e)
    if not gone:
        raise HTTPException(status_code=404, detail="no such post")
    return {"ok": True, "id": post_id}
