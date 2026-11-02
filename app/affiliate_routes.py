"""
The HTTP half of the affiliate program (2026-10-26; the logic is
src/affiliates.py). Registered onto api.router at the bottom of
app/api.py, so every route sits behind the session gate and inside the
route audit in tests/test_tenancy.py (each handler declares
`Depends(auth.current_account_id)`).

  GET  /api/affiliates/me        -> src/affiliates.summary: status, link,
                                    tier, progress, earnings
  POST /api/affiliates/apply     {"channel_url", "audience", "plan",
                                  "accept_terms"} -> the summary
  POST /api/affiliates/attribute {"code"} -> {"attributed", "reason"}:
       the studio calls this once after sign-in with the `phantra_ref`
       cookie's value, for the doors that do not pass the cookie to the
       API's own callback (the cookie is also read at sign-up in
       app/auth.py). Safe to call repeatedly.

Approving, rejecting, paying and the cash payout are Mike's CLI
(`python -m src.affiliates`), not routes: a human reads every channel.
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import affiliates

from . import auth


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message}})


class ApplyBody(BaseModel):
    channel_url: str = ""
    audience: str = ""
    plan: str = ""
    accept_terms: bool = False


class AttributeBody(BaseModel):
    code: str = ""


def affiliate_me(account_id: int = Depends(auth.current_account_id)):
    if account_id is None:
        return _error(403, "no_account", "no workspace to earn on")
    return affiliates.summary(account_id)


def affiliate_apply(body: ApplyBody, account_id: int = Depends(auth.current_account_id)):
    if account_id is None:
        return _error(403, "no_account", "no workspace to earn on")
    try:
        affiliates.apply(account_id, channel_url=body.channel_url, audience=body.audience,
                         plan=body.plan, accept_terms=body.accept_terms)
    except affiliates.AffiliateError as e:
        return _error(400, e.code, str(e))
    return affiliates.summary(account_id)


def affiliate_attribute(body: AttributeBody, account_id: int = Depends(auth.current_account_id)):
    if account_id is None:
        return _error(403, "no_account", "no workspace to attribute")
    return affiliates.attribute(account_id, body.code)


API_ROUTES = (
    ("/affiliates/me", affiliate_me, ["GET"]),
    ("/affiliates/apply", affiliate_apply, ["POST"]),
    ("/affiliates/attribute", affiliate_attribute, ["POST"]),
)
