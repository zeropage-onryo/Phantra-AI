"""The public read behind phantra.ai/whats-new and its RSS feed (2026-10-26,
docs/tasks/task-whats-new.md step 4).

`GET /public/whats-new` answers the site's page with the live announcements,
newest first, as src/whats_new.public_feed shapes them: the tag, the words,
the picture, a link and the date -- never a prompt, a model id, a price or
anything about a person. Outside /api on purpose, which requires a signed-in
user: the page is for anybody, search engines included. Five minutes of
cache, so a Keep shows up quickly and the page is never a database load.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src import whats_new

router = APIRouter()


@router.get("/public/whats-new")
def public_whats_new():
    from . import api  # the server's own switches, for no account
    try:
        caps = api.compute_capabilities(None)
    except Exception:
        caps = {}
    return JSONResponse(content={"items": whats_new.public_feed(caps)},
                        headers={"Cache-Control": "public, max-age=300"})
