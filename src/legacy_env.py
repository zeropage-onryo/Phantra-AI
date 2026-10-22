"""The settings were renamed to PHANTRA_* on 2026-10-16 (the studio is Phantra).

A deployment may still carry the old names -- Fly secrets, a launchd job's
environment -- until they are renamed too. `adopt()` copies each old name onto
its new one when the new one is not set, so nothing silently falls back to a
default in the meantime. It runs once, when `src` or `app` is first imported.

Delete this module (and its two callers in src/__init__.py, app/__init__.py)
once `fly secrets list` and every .env show no old name.
"""
import os

_OLD_PREFIXES = ("ZERO" "PAGE_", "Z" "PF_")  # split so a repo-wide search for the old name stays honest
_OLD_EXACT = {"PINTEREST_BOARD_ZERO" "PAGE": "PINTEREST_BOARD_PHANTRA"}


def adopt(environ=None) -> list:
    """Copy old-named settings to their PHANTRA_* names. Returns the new names set."""
    env = os.environ if environ is None else environ
    adopted = []
    for key, value in list(env.items()):
        new = _OLD_EXACT.get(key)
        if new is None:
            for prefix in _OLD_PREFIXES:
                if key.startswith(prefix):
                    new = "PHANTRA_" + key[len(prefix):]
                    break
        if new and new not in env:
            env[new] = value
            adopted.append(new)
    return adopted
