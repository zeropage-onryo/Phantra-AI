"""
The social providers (2026-10-22, docs/tasks/task-social-connections.md):
one module per platform a person can connect their own account of, each
holding the same four things -- how a connect starts (`auth_url`), what
the platform hands back (`authenticate`), how a token is renewed
(`refresh`), and, for a platform where one OAuth grant is not yet one
channel, the in-between step (`options` / `pick`). The shape is Postiz's
SocialProvider, in Python; `src/social_connections.py` owns the rows and
the vault, and `app/social_routes.py` is the door.

Posting is the second half of the same module (`post_start` /
`post_check` / `post_finish`, `check_post`, `CAPTION_MAX`), read by the
publish worker; `SETTINGS` is the per-post form the calendar's drawer
draws (a subreddit, a story-or-reel switch); `recent_media` feeds the
calendar's Feed view.

The registry is a dict on purpose: `providers.VIDEO_PROVIDERS`' shape. A
platform not in it is "not built", never a typo that reads as a 500.
"""
from __future__ import annotations

from types import ModuleType

from . import discord, instagram, linkedin, linkedin_page, reddit, x

PROVIDERS: dict[str, ModuleType] = {
    discord.IDENTIFIER: discord,
    instagram.IDENTIFIER: instagram,
    reddit.IDENTIFIER: reddit,
    linkedin.IDENTIFIER: linkedin,
    linkedin_page.IDENTIFIER: linkedin_page,
    x.IDENTIFIER: x,
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
            # the per-post form the drawer draws for this platform (2026-10-22)
            "settings": [dict(f) for f in getattr(mod, "SETTINGS", ())],
            "caption_max": int(getattr(mod, "CAPTION_MAX", 5000)),
            "feed": hasattr(mod, "recent_media"),
        })
    return out
