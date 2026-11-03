"""The Image and Video pages' model menus, for a visitor who is not signed in
(2026-11-03, QA 2026-11-02 P14).

/studio/image and /studio/video take a prompt signed out and open the sign-up
sheet on Generate; their model picker read GET /api/direct/{image,video},
which is behind the sign-in, so it was empty. This is the same menu asked for
no account: the catalogue in credits that /pricing and /models already
publish -- names, notes, lengths, frames, reference caps -- and `exempt`
False. Nothing about any person, and nothing here prices a pick or runs one:
the quote and the run stay under /api. Outside /api on purpose (that router
requires a signed-in user), like /public/whats-new; five minutes of cache.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src import direct

router = APIRouter()

_CACHE = {"Cache-Control": "public, max-age=300"}


@router.get("/public/direct/video")
def public_video_menu():
    return JSONResponse(content=direct.video_menu(None), headers=_CACHE)


@router.get("/public/direct/image")
def public_image_menu():
    return JSONResponse(content=direct.image_menu(None), headers=_CACHE)
