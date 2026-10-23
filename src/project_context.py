"""The project a generation is running inside, for the prompts that read it.

A ContextVar rather than a parameter because the brand block is read in a
dozen prompt builders (`shootgen.project_brief`) several calls below the route
that knows the project, and threading an argument through every one of them
is how one builder gets missed and quietly writes without the brief. The
routes set it around the work (`active(project)`); scene_chain's worker
threads run on copied contexts, so they see it too. Unset means no project:
the studio's neutral block alone.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

_ACTIVE: ContextVar[Optional[dict]] = ContextVar("phantra_project", default=None)
# a brand kit picked in the composer for a run OUTSIDE a project
# (2026-10-22); a project's own pick is read through the project instead
_KIT: ContextVar[Optional[dict]] = ContextVar("phantra_picked_kit", default=None)


def current() -> Optional[dict]:
    return _ACTIVE.get()


@contextmanager
def active(project: Optional[dict]) -> Iterator[None]:
    token = _ACTIVE.set(project)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


@contextmanager
def kit_active(kit: Optional[dict]) -> Iterator[None]:
    token = _KIT.set(kit)
    try:
        yield
    finally:
        _KIT.reset(token)


def kit() -> Optional[dict]:
    """The brand kit the run is held to: the project's pick inside a
    project, else the one picked in the composer, else None."""
    project = current()
    if project:
        from . import brand_kits
        return brand_kits.for_project(project)
    return _KIT.get()


def kit_block() -> str:
    """The BRAND block of a kit picked outside a project, or "" (also ""
    inside a project: the project's block carries its own kit)."""
    kit = _KIT.get()
    if not kit or current():
        return ""
    from . import brand_kits
    return brand_kits.brief_lines(kit)


def block() -> str:
    """The text appended to the brand block, or "" outside a project."""
    project = current()
    if not project:
        return ""
    from . import projects
    return projects.brief_block(project)
