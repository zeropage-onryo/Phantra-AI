"""
LinkedIn Page: a Company Page the member can post for (2026-10-23).

`linkedin.py` is the member's own profile, on the self-serve products.
A Page is LinkedIn's Community Management API, a partner application:
it needs its OWN developer app (LinkedIn allows no other product beside
it, so there is no OpenID sign-in here), approved by LinkedIn before any
member outside the app's team can connect. Until SOCIAL_LINKEDIN_PAGE_*
is set the provider says "not set up on this server yet", like any other.

WHAT A CONNECTION IS. One grant (`w_organization_social` to post,
`r_organization_admin` to list the Pages) and then one Page. The token's
member may hold a posting role on several, so `authenticate` lists them
off `organizationAcls` and keeps the list on the row: one Page finishes
at once, several leave the row PENDING (`PENDING_STEP = 'page'`) until
`pick`. The connection's meta is then {person_urn, pages,
organization_urn, page_name}. The row's external_id is the member, so a
member connects one Page per workspace; connecting again re-picks.

WHAT A POST IS. `linkedin.py`'s, with the Page as author and owner of
the upload. Always public: a Page has followers, not connections.

A Community Management app is granted programmatic refresh (a refresh
token good for a year), so `refresh` renews through `linkedin.refresh_with`.

Dated 2026-10-23 against Organization Access Control and the Posts API
at `linkedin.LINKEDIN_VERSION`.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import quote, urlencode

import requests

from . import base, linkedin
from .base import Connected, ConnectRefused, PostResult, Renewed

IDENTIFIER = "linkedin_page"
NAME = "LinkedIn Page"
CONNECTS = "a LinkedIn Company Page you admin"
PENDING_STEP = "page"
SCOPES = ("w_organization_social", "r_organization_admin")

API = linkedin.API
AUTHORIZE_URL = linkedin.AUTHORIZE_URL
TOKEN_URL = linkedin.TOKEN_URL

CLIENT_ID_ENV = "SOCIAL_LINKEDIN_PAGE_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_LINKEDIN_PAGE_CLIENT_SECRET"

# the Page roles the Posts API lets post for the organization
POSTING_ROLES = {
    "ADMINISTRATOR": "Admin",
    "CONTENT_ADMINISTRATOR": "Content admin",
    "DIRECT_SPONSORED_CONTENT_POSTER": "Sponsored content poster",
}
PAGES_MAX = 100

CAPTION_MAX = linkedin.CAPTION_MAX


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV))


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("LinkedIn Pages are not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": _env(CLIENT_ID_ENV),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(SCOPES),
    })


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "LinkedIn-Version": linkedin.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0"}


def _org_id(urn: str) -> str:
    return urn.rsplit(":", 1)[-1] if urn.startswith("urn:li:organization:") else ""


def _pages(token: str) -> tuple[str, list[dict[str, Any]]]:
    """The member's urn and the Pages they can post for, by name."""
    try:
        acls = _http("GET", f"{API}/rest/organizationAcls", headers=_headers(token), params={
            "q": "roleAssignee", "state": "APPROVED", "count": PAGES_MAX})
    except requests.RequestException as e:
        raise ConnectRefused("LinkedIn did not list your Pages: " + base.problem(e, token))
    member = ""
    roles: dict[str, str] = {}
    for el in acls.get("elements") or []:
        member = member or str(el.get("roleAssignee") or "")
        org = _org_id(str(el.get("organization") or el.get("organizationTarget") or ""))
        role = str(el.get("role") or "")
        if org and role in POSTING_ROLES and org not in roles:
            roles[org] = POSTING_ROLES[role]
    pages = []
    for org, role in roles.items():
        try:
            got = _http("GET", f"{API}/rest/organizations/{org}", headers=_headers(token))
        except requests.RequestException:
            got = {}
        page = {"id": org, "label": str(got.get("localizedName") or f"Page {org}"), "hint": role}
        picture = _logo(token, got)
        if picture:
            page["picture"] = picture
        pages.append(page)
    pages.sort(key=lambda p: p["label"].lower())
    return member, pages


def _logo(token: str, org: dict[str, Any]) -> str:
    """The Page's logo for the picker's card: the organization names an
    image urn, the Images API answers its (expiring) download address.
    Display only, never a reference; '' when there is none or LinkedIn
    does not say."""
    urn = str(((org.get("logoV2") or {}).get("original")) or "")
    if not urn.startswith("urn:li:image:"):
        return ""
    try:
        got = _http("GET", f"{API}/rest/images/{quote(urn, safe='')}", headers=_headers(token))
    except requests.RequestException:
        return ""
    url = str(got.get("downloadUrl") or "")
    return url if url.startswith("https://") else ""


def _finish(meta: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    done = dict(meta)
    done["organization_urn"] = f"urn:li:organization:{page['id']}"
    done["page_name"] = page["label"]
    return done


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("LinkedIn did not accept the sign-in: " + base.problem(e, secret, code))
    access = tok.get("access_token") or ""
    if not access:
        raise ConnectRefused("LinkedIn sent no token back.")
    granted = set((tok.get("scope") or "").replace(",", " ").split())
    if granted and "w_organization_social" not in granted:
        raise ConnectRefused("LinkedIn did not grant posting for a Page.")
    member, pages = _pages(access)
    if not pages:
        raise ConnectRefused("You hold no posting role on a LinkedIn Page. An admin of the Page "
                             "can make you an admin or content admin, then connect again.")
    member_id = member.rsplit(":", 1)[-1] if member else ""
    meta: dict[str, Any] = {"person_urn": member, "pages": pages}
    pending: Optional[str] = PENDING_STEP
    if len(pages) == 1:
        meta, pending = _finish(meta, pages[0]), None
    return Connected(
        external_id=member_id or pages[0]["id"],
        display_name=meta.get("page_name") or "LinkedIn Page",
        handle="",
        avatar_url="",
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=int(tok.get("expires_in") or linkedin.TOKEN_SECONDS),
        scopes=sorted(granted) or list(SCOPES),
        meta=meta,
        pending=pending,
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    return linkedin.refresh_with(_env(CLIENT_ID_ENV), _env(CLIENT_SECRET_ENV),
                                 access_token, refresh_token)


# --------------------------------------------------------------------------
# the in-between step: which Page
# --------------------------------------------------------------------------

def options(meta: dict[str, Any]) -> list[dict[str, Any]]:
    """The Pages listed at connect time (the row keeps them, so picking
    needs no token)."""
    return [dict(p) for p in meta.get("pages") or []]


def pick(meta: dict[str, Any], choice: str) -> dict[str, Any]:
    wanted = str(choice or "").strip()
    for p in options(meta):
        if p["id"] == wanted:
            return _finish(meta, p)
    raise ConnectRefused("That Page is not one you can post for. Pick one from the list.")


def display_label(meta: dict[str, Any]) -> str:
    return str(meta.get("page_name") or "")


# --------------------------------------------------------------------------
# posting: linkedin.py's, as the Page
# --------------------------------------------------------------------------

def check_post(source: dict, caption: str, settings: dict) -> Optional[str]:
    return linkedin.check_post(source, caption, settings)


def post_start(token: str, meta: dict[str, Any], post: dict[str, Any]) -> PostResult:
    return linkedin.post_start(token, meta, post)


def post_check(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    return linkedin.post_check(token, meta, pending)


def post_finish(token: str, meta: dict[str, Any], pending: dict[str, Any]) -> PostResult:
    return linkedin.post_finish(token, meta, pending)
