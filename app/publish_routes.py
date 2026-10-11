"""
/api/publish -- the review page's routes (2026-10-11, src/publish_review.py).

`prepare` drafts a post (the studio's own button; the MCP tool calls
publish_review.prepare directly). `GET /{id}` is what the review page
renders, fetched fresh each time. `POST /{id}/submit` is the press of Post:
it needs the signed-in session cookie this router is mounted behind, so it
is a person in the studio and never a model. Every route is scoped to the
caller's account.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src import publish_review

from . import auth

router = APIRouter(prefix="/publish")


def _refused(e: Exception) -> JSONResponse:
    return JSONResponse(status_code=400,
                        content={"error": {"code": "publish_refused", "message": str(e)}})


class PrepareBody(BaseModel):
    source: str = Field(..., description="gen:<id> or asset:<id>")
    platform: str = "tiktok"
    caption: str = ""


class Commercial(BaseModel):
    enabled: bool = False
    your_brand: bool = False
    branded_content: bool = False


class SubmitBody(BaseModel):
    caption: Optional[str] = None
    privacy_level: Optional[str] = None
    allow_comment: bool = False
    allow_duet: bool = False
    allow_stitch: bool = False
    commercial: Commercial = Commercial()
    is_aigc: bool = True
    consent: bool = False


@router.get("")
def publish_recent(limit: int = 20, account_id: int = Depends(auth.current_account_id)):
    return {"posts": publish_review.recent(account_id=account_id, limit=limit)}


@router.post("/prepare")
def publish_prepare(body: PrepareBody, account_id: int = Depends(auth.current_account_id)):
    try:
        return publish_review.prepare(body.source, platform=body.platform,
                                      caption=body.caption, account_id=account_id,
                                      created_via="studio")
    except publish_review.PublishError as e:
        return _refused(e)


@router.get("/{session_id}")
def publish_get(session_id: str, account_id: int = Depends(auth.current_account_id)):
    try:
        return publish_review.review(session_id, account_id=account_id)
    except publish_review.PublishError as e:
        return JSONResponse(status_code=404,
                            content={"error": {"code": "not_found", "message": str(e)}})


@router.post("/{session_id}/submit")
def publish_submit(session_id: str, body: SubmitBody, request: Request,
                   account_id: int = Depends(auth.current_account_id)):
    user = auth.current_user(request) or {}
    choices = body.model_dump()
    if body.caption is None:
        choices.pop("caption")
    try:
        return publish_review.submit(session_id, choices, account_id=account_id,
                                     user_id=user.get("id"))
    except publish_review.PublishError as e:
        return _refused(e)


@router.post("/{session_id}/cancel")
def publish_cancel(session_id: str, account_id: int = Depends(auth.current_account_id)):
    try:
        return publish_review.cancel(session_id, account_id=account_id)
    except publish_review.PublishError as e:
        return _refused(e)
