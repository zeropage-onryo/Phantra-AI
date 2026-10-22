"""
Instagram, through Instagram Business Login (2026-10-22): the standalone
route, no Facebook Page involved.

Mike pressed this screen on Postiz on 2026-10-22 for @phantra.ai: the
consent lists four toggles, one per scope below, and the required one is
greyed. This module asks for exactly those four and nothing more, because
Meta's reviewer asks why about every extra one.

THE TOGGLES ARE THE PERSON'S. "Access and publish content" can be switched
off and Allow still pressed. Meta answers the code exchange with the
permissions it actually granted, and a connection that cannot publish is
REFUSED here rather than stored: a channel that can read but never post
is a card that lies.

THE TOKEN. A short-lived token comes back from the code; it is exchanged
at once for a LONG-LIVED one (60 days). There is no refresh token on this
route: a long-lived token is renewed with `refresh_access_token` while it
is still valid and at least a day old, which is what `refresh` does and
what social_connections.token_for calls inside the last seven days. A
token that lapsed is a reconnect, said so on the card.

Dated 2026-10-22 against Meta's "Instagram API with Instagram Login"
(Business Login) docs: oauth/authorize, oauth/access_token,
access_token?grant_type=ig_exchange_token, refresh_access_token, /me.
The old instagram.py keeps the operator's env-token path for publishing
and insights; this one only connects.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, Renewed

IDENTIFIER = "instagram"
NAME = "Instagram"
CONNECTS = "an Instagram professional (Business or Creator) account"
SCOPES = (
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_insights",
)
# Without this one the connection cannot post; without basic nothing
# answers at all.
REQUIRED = ("instagram_business_basic", "instagram_business_content_publish")

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH = "https://graph.instagram.com"
GRAPH_VERSION = "v21.0"
LONG_LIVED_SECONDS = 60 * 24 * 3600

APP_ID_ENV = "SOCIAL_INSTAGRAM_APP_ID"
APP_SECRET_ENV = "SOCIAL_INSTAGRAM_APP_SECRET"


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(APP_ID_ENV) and _env(APP_SECRET_ENV))


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("Instagram is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": _env(APP_ID_ENV),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
        # the Business Login screen, not Facebook's; ask every time so a
        # second workspace can connect a second account
        "enable_fb_login": "0",
        "force_authentication": "1",
    })


def _granted(tok: dict) -> set[str]:
    raw = tok.get("permissions")
    if isinstance(raw, list):
        return {str(p) for p in raw}
    return {p.strip() for p in str(raw or "").split(",") if p.strip()}


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    """code -> short-lived token (+ the permissions really granted) ->
    long-lived token -> the account's name and picture."""
    secret = _env(APP_SECRET_ENV)
    # Instagram appends "#_" to the code on the way back
    code = (code or "").split("#", 1)[0]
    try:
        tok = _http("POST", TOKEN_URL, data={
            "client_id": _env(APP_ID_ENV), "client_secret": secret,
            "grant_type": "authorization_code", "redirect_uri": redirect_uri,
            "code": code,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not accept the sign-in: " + base.problem(e, secret, code))
    short = tok.get("access_token") or ""
    if not short:
        raise ConnectRefused("Instagram sent no token back.")
    granted = _granted(tok)
    missing = [s for s in REQUIRED if granted and s not in granted]
    if missing:
        raise ConnectRefused("Instagram was connected without permission to publish. "
                             "Connect again and leave \"Access and publish content\" switched on.")
    try:
        long = _http("GET", f"{GRAPH}/access_token", params={
            "grant_type": "ig_exchange_token", "client_secret": secret,
            "access_token": short,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not issue a long-lived token: "
                             + base.problem(e, secret, short))
    access = long.get("access_token") or short
    expires_in = int(long.get("expires_in") or LONG_LIVED_SECONDS)
    try:
        me = _http("GET", f"{GRAPH}/{GRAPH_VERSION}/me", params={
            "fields": "user_id,username,name,profile_picture_url",
            "access_token": access,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not say which account this is: "
                             + base.problem(e, access, short))
    user_id = str(me.get("user_id") or me.get("id") or tok.get("user_id") or "")
    if not user_id:
        raise ConnectRefused("Instagram named no account id.")
    username = me.get("username") or ""
    return Connected(
        external_id=user_id,
        display_name=me.get("name") or username or f"Instagram {user_id}",
        handle=username,
        avatar_url=me.get("profile_picture_url") or "",
        access_token=access,
        refresh_token="",
        expires_in=expires_in,
        scopes=sorted(granted) if granted else list(SCOPES),
        meta={"ig_user_id": user_id},
    )


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """A long-lived token renews itself while still valid (and a day old).
    A lapsed one cannot, and the person reconnects."""
    try:
        res = _http("GET", f"{GRAPH}/refresh_access_token", params={
            "grant_type": "ig_refresh_token", "access_token": access_token,
        })
    except requests.RequestException as e:
        raise ConnectRefused("Instagram did not renew the token: " + base.problem(e, access_token))
    new = res.get("access_token") or ""
    if not new:
        raise ConnectRefused("Instagram did not renew the token.")
    return Renewed(access_token=new, expires_in=int(res.get("expires_in") or LONG_LIVED_SECONDS))


def display_label(meta: dict[str, Any]) -> str:
    return ""
