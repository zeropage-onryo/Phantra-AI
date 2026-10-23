"""
Discord: a server's channel, posted to by Phantra's bot (2026-10-22).

The first provider on purpose: no review, no business verification, and
the channel Mike is about to open for growth -- the studio posts to its
own Discord before any platform audit clears.

WHAT A CONNECTION IS. Discord has no "post to my profile". A post goes to
a CHANNEL in a SERVER, by a bot that was added to that server. So the
grant here is Discord's combined screen -- "add Phantra to a server" (the
`bot` scope, with the permissions the bot needs) plus `identify` so the
row can say who connected it -- and the token response names the server
(`guild`). That is one grant but not yet one channel, so the row is
saved PENDING (`PENDING_STEP = 'channel'`): the settings page lists the
server's text channels off the bot's own token and the person picks one.
`pick` finishes it. The connection's meta is then
{guild_id, guild_name, channel_id, channel_name, connected_user}.

WHOSE TOKEN POSTS. The BOT's (SOCIAL_DISCORD_BOT_TOKEN, one for the
installation), never the person's: a bot token is what Discord issues
for posting to a server it was added to. The person's user token is kept
on the row only so `handle` is honest and a later feature (listing the
servers they admin) has it; posting does not read it, so its 7-day
expiry is not a reconnect.

Dated 2026-10-22 against Discord's OAuth2 and Channel docs (API v10).
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from . import base
from .base import Connected, ConnectRefused, Renewed

IDENTIFIER = "discord"
NAME = "Discord"
CONNECTS = "a channel in a Discord server you manage"
PENDING_STEP = "channel"
SCOPES = ("identify", "guilds", "bot")

API = "https://discord.com/api/v10"
AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = f"{API}/oauth2/token"
CDN = "https://cdn.discordapp.com"

# View Channel (1024) + Send Messages (2048) + Embed Links (16384) +
# Attach Files (32768): what posting a clip and a caption needs, nothing
# that manages the server.
BOT_PERMISSIONS = 1024 | 2048 | 16384 | 32768

# Channel types a post can land in: GUILD_TEXT and GUILD_ANNOUNCEMENT.
POSTABLE_TYPES = {0: "text", 5: "announcement"}

CLIENT_ID_ENV = "SOCIAL_DISCORD_CLIENT_ID"
CLIENT_SECRET_ENV = "SOCIAL_DISCORD_CLIENT_SECRET"
BOT_TOKEN_ENV = "SOCIAL_DISCORD_BOT_TOKEN"


def _http(method: str, url: str, **kw) -> dict:
    return base.http(method, url, **kw)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured() -> bool:
    return bool(_env(CLIENT_ID_ENV) and _env(CLIENT_SECRET_ENV) and _env(BOT_TOKEN_ENV))


def bot_token() -> str:
    return _env(BOT_TOKEN_ENV)


def auth_url(redirect_uri: str, state: str) -> str:
    if not configured():
        raise ConnectRefused("Discord is not set up on this server yet.")
    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": _env(CLIENT_ID_ENV),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "permissions": str(BOT_PERMISSIONS),
        "state": state,
    })


def _icon(kind: str, id_: str, icon: Optional[str]) -> str:
    return f"{CDN}/{kind}/{id_}/{icon}.png" if icon else ""


def authenticate(code: str, redirect_uri: str, query: dict[str, Any]) -> Connected:
    """The code becomes the person's token and, because `bot` was in the
    grant, Discord's answer names the server the bot was added to."""
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("Discord did not accept the sign-in: " + base.problem(e, secret, code))
    access = tok.get("access_token") or ""
    if not access:
        raise ConnectRefused("Discord sent no token back.")
    granted = set((tok.get("scope") or "").split())
    # The server named in the answer (or the callback's guild_id) is the
    # proof the bot joined. Discord leaves `bot` OUT of the token's `scope`
    # even when it was granted (its own example answer says "identify"),
    # so reading `scope` refused every real connect (2026-10-23).
    guild = tok.get("guild") or {}
    guild_id = str(guild.get("id") or query.get("guild_id") or "")
    if not guild_id:
        raise ConnectRefused("The bot was not added to a server. Pick a server on "
                             "Discord's screen and press Authorize.")
    granted.add("bot")
    try:
        me = _http("GET", f"{API}/users/@me", headers={"Authorization": f"Bearer {access}"})
    except requests.RequestException as e:
        raise ConnectRefused("Discord did not say who you are: " + base.problem(e, access))
    handle = me.get("username") or ""
    if not guild.get("name"):
        guild = _guild(guild_id) or {"id": guild_id, "name": f"Server {guild_id}"}
    return Connected(
        external_id=guild_id,
        display_name=guild.get("name") or f"Server {guild_id}",
        handle=handle,
        avatar_url=_icon("icons", guild_id, guild.get("icon")),
        access_token=access,
        refresh_token=tok.get("refresh_token") or "",
        expires_in=tok.get("expires_in"),
        scopes=sorted(granted),
        meta={"guild_id": guild_id, "guild_name": guild.get("name") or "",
              "connected_user": handle, "connected_user_id": str(me.get("id") or "")},
        pending=PENDING_STEP,
    )


def _guild(guild_id: str) -> Optional[dict]:
    try:
        return _http("GET", f"{API}/guilds/{guild_id}",
                     headers={"Authorization": f"Bot {bot_token()}"})
    except requests.RequestException:
        return None


def refresh(access_token: str, refresh_token: str) -> Optional[Renewed]:
    """The person's token renews, though nothing posts with it."""
    if not refresh_token:
        return None
    secret = _env(CLIENT_SECRET_ENV)
    try:
        tok = _http("POST", TOKEN_URL, data={
            "client_id": _env(CLIENT_ID_ENV), "client_secret": secret,
            "grant_type": "refresh_token", "refresh_token": refresh_token,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except requests.RequestException as e:
        raise ConnectRefused("Discord did not renew the token: "
                             + base.problem(e, secret, refresh_token))
    return Renewed(access_token=tok.get("access_token") or "",
                   refresh_token=tok.get("refresh_token") or refresh_token,
                   expires_in=tok.get("expires_in"))


# --------------------------------------------------------------------------
# the in-between step: which channel
# --------------------------------------------------------------------------

def options(meta: dict[str, Any]) -> list[dict[str, Any]]:
    """The server's text and announcement channels, read with the bot's
    own token (it is a member now). Grouped by category in `hint`."""
    guild_id = str(meta.get("guild_id") or "")
    if not guild_id:
        raise ConnectRefused("This connection names no server.")
    try:
        rows = _http("GET", f"{API}/guilds/{guild_id}/channels",
                     headers={"Authorization": f"Bot {bot_token()}"})
    except requests.RequestException as e:
        raise ConnectRefused("Discord did not list the server's channels: "
                             + base.problem(e, bot_token()))
    if not isinstance(rows, list):
        return []
    categories = {str(r.get("id")): r.get("name") or "" for r in rows if r.get("type") == 4}
    out = []
    for r in rows:
        kind = POSTABLE_TYPES.get(r.get("type"))
        if not kind:
            continue
        out.append({"id": str(r.get("id")), "label": "#" + (r.get("name") or ""),
                    "hint": categories.get(str(r.get("parent_id") or ""), ""),
                    "kind": kind, "position": r.get("position", 0)})
    # the server's own order: channels in no category first, then each
    # category's, by name
    out.sort(key=lambda c: (c["hint"] != "", c["hint"].lower(), c["position"]))
    for c in out:
        c.pop("position", None)
    return out


def pick(meta: dict[str, Any], choice: str) -> dict[str, Any]:
    """The finished meta, or a refusal: a channel the server does not
    have, or one a post cannot land in, is never written down."""
    wanted = str(choice or "").strip()
    for c in options(meta):
        if c["id"] == wanted:
            done = dict(meta)
            done["channel_id"] = c["id"]
            done["channel_name"] = c["label"]
            return done
    raise ConnectRefused("That channel is not one the bot can post to. Pick one from the list.")


def display_label(meta: dict[str, Any]) -> str:
    """'<server> · #channel' once picked, the server alone before."""
    name = meta.get("guild_name") or ""
    ch = meta.get("channel_name") or ""
    return f"{name} · {ch}" if ch else name
