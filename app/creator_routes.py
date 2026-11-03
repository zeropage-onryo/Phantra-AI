"""
The HTTP half of Phantra Creators (2026-11-03; the logic is src/creators.py).
Registered onto api.router at the bottom of app/api.py, so every route sits
behind the session gate and inside the route audit in tests/test_tenancy.py
(each handler declares `Depends(auth.current_account_id)`).

  GET  /api/creators/me     -> {"status": null | "pending" | "approved" | "rejected"}
  POST /api/creators/apply  {"channel_url", "what_you_make", "accept_terms"}
                             (+ optional "full_name", "country", "more_links",
                             "contribute") -> the same status shape

Approving and rejecting are Mike's CLI (`python -m src.creators`), not routes:
he reads the work before he lets someone in.
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import creators

from . import auth


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message}})


class ApplyBody(BaseModel):
    channel_url: str = ""
    what_you_make: str = ""
    full_name: str = ""
    country: str = ""
    more_links: str = ""
    contribute: str = ""
    accept_terms: bool = False


def creator_me(account_id: int = Depends(auth.current_account_id)):
    if account_id is None:
        return _error(403, "no_account", "no workspace to apply from")
    return creators.get(account_id)


def creator_apply(body: ApplyBody, account_id: int = Depends(auth.current_account_id)):
    if account_id is None:
        return _error(403, "no_account", "no workspace to apply from")
    try:
        return creators.apply(account_id, channel_url=body.channel_url,
                              what_you_make=body.what_you_make, accept_terms=body.accept_terms,
                              full_name=body.full_name, country=body.country,
                              more_links=body.more_links, contribute=body.contribute)
    except creators.CreatorError as e:
        return _error(400, e.code, str(e))


API_ROUTES = (
    ("/creators/me", creator_me, ["GET"]),
    ("/creators/apply", creator_apply, ["POST"]),
)
