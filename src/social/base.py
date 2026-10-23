"""
What every provider module in src/social/ shares: the result of a
connect, the refusal a person reads, and the one HTTP seam.

A provider module defines:

    IDENTIFIER, NAME, CONNECTS          -- 'instagram', 'Instagram', 'an
                                           Instagram professional account'
    SCOPES                              -- what the consent screen asks for
    configured() -> bool                -- this server has the app's keys
    auth_url(redirect_uri, state) -> str
    authenticate(code, redirect_uri, query) -> Connected
    refresh(access_token, refresh_token) -> Renewed | None
                                        -- None: this platform has no
                                           refresh; the person reconnects

and, when one grant is not yet one channel (Discord: a server, then a
channel in it):

    PENDING_STEP = 'channel'
    options(meta) -> list[{id, label, hint?}]
    pick(meta, choice) -> meta          -- the finished meta, or refuses

and, once it can post (src/publish_worker.py is the only caller):

    CAPTION_MAX                         -- the platform's limit
    check_post(source, caption, settings) -> None | reason (at creation)
    post_start(token, meta, post) -> PostResult
    post_check(token, meta, pending) -> PostResult      (while 'pending')
    post_finish(token, meta, pending) -> PostResult     (when 'ready')

`post` is {caption, media: {ref, url, kind, seconds, path}, settings}
where `url` is a PUBLIC address the platform can fetch (the worker makes
it so) and `path` a local file when this machine has it.

Every HTTP call goes through the module's own `_http`, one function, so
a test patches it and nothing can reach the network behind its back
(tests/conftest.py's guard is the backstop). A provider never raises a
raw `requests` error at a person: it raises ConnectRefused with the
words the settings page shows, the credential redacted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import requests

HTTP_TIMEOUT = 20


class ConnectRefused(Exception):
    """Said to the person, in plain words. Never carries a token."""


class PostFailed(Exception):
    """The platform said no to THIS post (a bad file, a refused caption, a
    quota): terminal, never retried. Plain words, no credential."""


@dataclass
class PostResult:
    """What a provider's post_start / post_check / post_finish answer.

    `status` is 'completed' with the platform's id and permalink, or
    'pending' with what the next check needs (`pending`), the Postiz
    contract: once post_finish has changed the platform, post_check must
    answer 'completed', never 'ready' again, so a retry cannot post twice.
    """
    status: str                              # 'pending' | 'ready' | 'completed'
    pending: dict[str, Any] = field(default_factory=dict)
    release_id: str = ""
    release_url: str = ""


@dataclass
class Connected:
    """One finished OAuth grant, before it is written down."""
    external_id: str
    display_name: str
    access_token: str
    handle: str = ""
    avatar_url: str = ""
    refresh_token: str = ""
    expires_in: Optional[int] = None        # seconds; None = does not expire
    scopes: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    pending: Optional[str] = None           # a PENDING_STEP still to do


@dataclass
class Renewed:
    access_token: str
    refresh_token: str = ""
    expires_in: Optional[int] = None


def redact(message: str, *secrets: Optional[str]) -> str:
    """A credential that reaches a row or a page is a credential to
    rotate; the same rule tiktok/instagram/youtube follow."""
    for s in secrets:
        if s:
            message = message.replace(s, "<redacted>")
    return message


def http(method: str, url: str, *, params: Optional[dict] = None,
         data: Optional[dict] = None, json: Optional[dict] = None,
         headers: Optional[dict] = None, timeout: int = HTTP_TIMEOUT) -> dict:
    """The shared request: raises requests' own errors on transport
    trouble or a non-2xx, returns the parsed JSON body otherwise. Each
    provider module wraps it as its own `_http` so tests patch the
    module, not this function."""
    response = requests.request(method, url, params=params, data=data, json=json,
                                headers=headers, timeout=timeout)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def problem(e: Exception, *secrets: Optional[str]) -> str:
    """The platform's answer as one redacted line: the status and the
    body when there is one, the exception otherwise."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            body = resp.text[:300]
        except Exception:  # pragma: no cover - defensive
            body = ""
        return redact(f"HTTP {resp.status_code}: {body}", *secrets)
    return redact(str(e), *secrets)
