"""
The social providers (2026-10-22, docs/tasks/task-social-connections.md):
one module per platform a person can connect their own account of, each
holding the same four things -- how a connect starts (`auth_url`), what
the platform hands back (`authenticate`), how a token is renewed
(`refresh`), and, for a platform where one OAuth grant is not yet one
channel, the in-between step (`options` / `pick`). The shape is Postiz's
SocialProvider, in Python; `src/social_connections.py` owns the rows and
the vault, and `app/social_routes.py` is the door.

Nothing here posts. Posting is the next build (the publish worker); a
provider module may grow `post_start` / `post_check` / `post_finish` then.

The registry is a dict on purpose: `providers.VIDEO_PROVIDERS`' shape. A
platform not in it is "not built", never a typo that reads as a 500.
"""
from __future__ import annotations

from types import ModuleType

from . import discord, instagram

PROVIDERS: dict[str, ModuleType] = {
    discord.IDENTIFIER: discord,
    instagram.IDENTIFIER: instagram,
}


def get(identifier: str) -> ModuleType | None:
    return PROVIDERS.get((identifier or "").strip().lower())


def catalogue() -> list[dict]:
    """What the settings page lists: every provider, whether this server
    has its developer app's credentials, and what connecting means."""
    out = []
    for key, mod in PROVIDERS.items():
        out.append({
            "id": key,
            "name": mod.NAME,
            "configured": mod.configured(),
            "connects": mod.CONNECTS,
            "pending_step": getattr(mod, "PENDING_STEP", None),
        })
    return out
