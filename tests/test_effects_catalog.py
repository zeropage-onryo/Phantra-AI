"""
The public /effects pages read web/src/content/effects-catalog.json, which
is GENERATED from src/effects.py by `python -m ops.export_effects_catalog`
and committed (2026-11-05, docs/tasks/task-public-effects-pages.md). This is
the wire between the two, as tests/test_plans.py is for pricing.json: add or
change an effect without re-exporting and CI fails here.
"""

import json
import os
from pathlib import Path

from app.api import EFFECTS_CATALOG_PATH, public_effects_catalog
from src import effect_recipes, effects, free_looks

ROOT = Path(__file__).resolve().parent.parent


def test_the_committed_catalog_is_what_the_table_says():
    committed = json.loads((ROOT / EFFECTS_CATALOG_PATH).read_text())
    live = json.loads(json.dumps(public_effects_catalog(), ensure_ascii=False))
    assert committed == live, (
        "web/src/content/effects-catalog.json is stale -- run "
        "`venv/bin/python -m ops.export_effects_catalog` and commit the result")


def test_every_row_is_listed_whatever_the_switches(monkeypatch):
    monkeypatch.delenv(free_looks.ENV, raising=False)
    monkeypatch.delenv(effect_recipes.ENV, raising=False)
    ids = [e["id"] for e in public_effects_catalog()["items"]]
    assert ids == list(effects.EFFECT_NAMES)
    # and the switches are put back as they were
    assert os.environ.get(free_looks.ENV) is None
    assert os.environ.get(effect_recipes.ENV) is None
