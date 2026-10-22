"""The public read behind a shared render's page (2026-10-20, src/shares.py).

`GET /public/share/<token>` answers the site's /v/<token> page with what it
may show: the media kind, a playable address minted now, the poster and the
workspace's name -- never the prompt, the model or a price. There is no
sign-in here: the token is the address, and an unknown, revoked or deleted
one is a plain 404. Outside /api on purpose, which requires a signed-in user.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src import shares

router = APIRouter()


@router.get("/public/share/{token}")
def public_share(token: str):
    found = shares.public(token)
    if found is None:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found",
                                                                 "message": "no such share"}},
                            headers={"Cache-Control": "no-store"})
    # a minute is short enough that an Unshare lands quickly and a presigned
    # address (two hours on the signed rung) is never served stale
    return JSONResponse(content=found, headers={"Cache-Control": "public, max-age=60"})
