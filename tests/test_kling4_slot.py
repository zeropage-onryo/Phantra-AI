"""The parked Kling 4.0 slot (fal.SLOTS; 2026-10-22, group 6 checkbox 4 of
the overnight task; docs/tasks/task-vesper-v2.md).

A row with the table's shape, its official endpoint ids and its price
None, OFF the live table: while its flag is off, or its price is None,
no picker, listing, quote, proposal or recommendation can see it. With a
fake fill-in and the flag on (here only) it joins the table, is priced
by the same estimators, and the routing rules prefer it for a 15-30s
single shot and a reference-heavy scene. Nothing points at a reseller.
"""
import json
from pathlib import Path

import pytest

from app import api
from src import fal, guide_tools, model_menu, model_pick, pricing, providers

ROOT = Path(__file__).resolve().parent.parent
FILL = {"t2v": "test/kling-4/text-to-video", "i2v": "test/kling-4/image-to-video",
        "prices": {"1080p": 0.2}, "checked": "2026-10-22", "source": "https://example.test/kling-4"}


@pytest.fixture
def off(monkeypatch):
    monkeypatch.delenv("PHANTRA_KLING_4", raising=False)
    fal.disable_slots()
    yield
    fal.disable_slots()


@pytest.fixture
def on(monkeypatch):
    """The slot filled in and its flag set, for one test; off again after."""
    monkeypatch.setenv("PHANTRA_KLING_4", "1")
    spec = fal.SLOTS["kling4"]
    saved = {k: spec[k] for k in FILL}
    spec.update(FILL)
    added = fal.enable_slots()
    try:
        yield added
    finally:
        fal.disable_slots()
        spec.update(saved)


def _nowhere():
    assert "kling4" not in fal.VIDEO_MODELS and "kling4" not in fal.MODELS
    assert "kling4" not in {m["id"] for m in providers.models_for("fal")}
    assert "kling4" not in {r["model"] for r in pricing.catalog_models()}
    assert "kling4" not in {m for _p, m, _n, _b in pricing.catalog_rows()}
    assert model_menu.video_id("kling4") == ""
    assert model_menu.slot_preference(20, 1) is None
    assert model_menu.slot_preference(8, 3, refs=5) is None
    assert model_menu.routing_line("kling4") == ""
    assert providers.proposed_default("kling4") is None
    assert api.compute_capabilities()["kling_4"] is False
    # the brain's proposal of it is dropped; its rule changes no scene
    clean = guide_tools.check_args("make_video", {"prompt": "one continuous 20s take of the can",
                                                  "seconds": 20, "shots": 1, "model": "kling4"})
    assert "model" not in clean and "model_why" not in clean


def test_the_slot_is_parked_with_no_id_and_no_price(off):
    spec = fal.SLOTS["kling4"]
    assert spec["available"] is False
    assert spec["t2v"] is None and spec["i2v"] is None and spec["prices"] is None
    assert spec["checked"] is None and spec["source"] is None
    assert spec["routing"] == {"single_shot_seconds": (15, 30), "reference_heavy": 3}
    assert fal.SLOT_FLAGS["kling4"] == "PHANTRA_KLING_4"
    assert fal.slot_enabled("kling4") is False and fal.slot_ready("kling4") is False
    _nowhere()


def test_the_flag_alone_offers_nothing_while_the_price_is_none(off, monkeypatch):
    monkeypatch.setenv("PHANTRA_KLING_4", "1")
    assert fal.slot_enabled("kling4") is True
    assert fal.slot_ready("kling4") is False
    assert fal.enable_slots() == [] and fal.ready_slots() == []
    _nowhere()
    # ids filled but no price: still nothing
    spec = fal.SLOTS["kling4"]
    saved = {k: spec[k] for k in ("t2v", "i2v")}
    spec.update({"t2v": FILL["t2v"], "i2v": FILL["i2v"]})
    try:
        assert fal.slot_ready("kling4") is False and fal.enable_slots() == []
        _nowhere()
    finally:
        spec.update(saved)


def test_the_brains_menu_and_the_connectors_ranking_never_name_it_off(off, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "x" * 20)
    assert "kling4" not in model_menu.for_model(None)
    assert "Kling 4.0" not in model_menu.for_model(None)
    rows = [{**r, "min_seconds": 4, "max_seconds": 30, "draft": None,
             "routing": fal.slot_routing(r["model"])} for r in pricing.catalog_models()]
    ranked = model_pick.rank("one continuous 20s take held to many references", seconds=20,
                             catalogue=rows, price=lambda m, s: (100, s or 5, "720p"))
    assert "kling4" not in {p["model"] for p in ranked["picks"]}
    assert all(r["routing"] is None for r in rows)


def test_nothing_points_at_a_reseller_or_a_relay():
    """Mike's call: Kling 4.0 is the official API or nothing."""
    blob = json.dumps(fal.SLOTS, default=str).lower()
    for word in ("higgsfield", "useapi", "piapi", "goapi", "relay"):
        assert word not in blob, word
    for path in ("src/fal.py", "src/model_menu.py", "src/model_pick.py", "src/pricing.py",
                 "src/providers.py", "app/api.py"):
        assert "useapi" not in (ROOT / path).read_text().lower(), path
    # the slot block itself (fal.py keeps one historical line on the retired
    # Higgsfield lane elsewhere; the slot names no reseller anywhere)
    text = (ROOT / "src/fal.py").read_text()
    block = text[text.index("SLOT_FLAGS"):text.index("enable_slots()\n\nMODELS")].lower()
    for word in ("higgsfield", "useapi", "reseller", "relay"):
        assert word not in block or word == "reseller", word
    for path in ("src/model_menu.py", "src/model_pick.py"):
        assert "higgsfield" not in (ROOT / path).read_text().lower(), path


def test_filled_in_and_on_it_joins_the_table_and_is_priced_by_the_same_estimators(on):
    assert on == ["kling4"] and fal.slot_ready("kling4") is True
    row = fal.VIDEO_MODELS["kling4"]
    assert row["t2v"] == FILL["t2v"] and row["prices"] == {"1080p": 0.2}
    assert "routing" not in row and "available" not in row       # a table row's shape
    assert "kling4" in {m["id"] for m in providers.models_for("fal")}
    assert providers.band_for("fal", "kling4").tier == "creator"
    choice = providers.check_render_choice("fal", "kling4", 20, None)
    assert choice["estimate_usd"] == pytest.approx(0.2 * 20)
    cat = next(r for r in pricing.catalog_models() if r["model"] == "kling4")
    assert cat["name"] == "Kling 4.0" and cat["credits"] == pricing.credits_for(pricing.usd_micros(0.2 * 5))
    assert model_menu.video_id("kling4") == "kling4" and model_menu.label_for("kling4") == "Kling 4.0"
    assert fal.fit_duration("kling4", 40) == 30 and fal.draft_resolution("kling4") is None
    assert api.compute_capabilities()["kling_4"] is True
    # the existing table rails hold on the merged row
    assert row["checked"] and row["source"].startswith("https://")
    assert fal.estimate_cost(1, model="kling4", duration=10, resolution="1080p") == pytest.approx(2.0)


def test_the_routing_rules_prefer_it_for_long_single_shots_and_reference_heavy_scenes(on, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "x" * 20)
    assert model_menu.slot_preference(20, 1) == ("kling4", "Kling 4.0: a single continuous take of 20s")
    assert model_menu.slot_preference(15, 1)[0] == "kling4" and model_menu.slot_preference(30, 1)[0] == "kling4"
    assert model_menu.slot_preference(10, 1) is None            # too short a take
    assert model_menu.slot_preference(20, 3) is None            # not a single shot
    assert model_menu.slot_preference(8, 3, refs=3)[1] == "Kling 4.0: a scene held to 3 references"
    assert model_menu.slot_preference(8, 3, refs=2) is None
    assert "prefer it for a single continuous shot of 15-30s" in model_menu.for_model(None)
    # a scene with no model proposed takes the rule; a proposed model stands
    results = [{"n": n, "kind": "still", "label": f"still {n}"} for n in (1, 2, 3)]
    clean = guide_tools.check_args("make_video", {"prompt": "one continuous take of the can on wet steel",
                                                  "seconds": 20, "shots": 1})
    assert clean["model"] == "kling4" and "single continuous take" in clean["model_why"]
    held = guide_tools.check_args("make_video", {"prompt": "the can, held to the stills",
                                                 "results": [1, 2, 3]}, results)
    assert held["model"] == "kling4" and "3 references" in held["model_why"]
    kept = guide_tools.check_args("make_video", {"prompt": "one continuous take of the can",
                                                 "seconds": 20, "shots": 1, "model": "veo3.1"})
    assert kept["model"] == "veo3.1"
    plain = guide_tools.check_args("make_video", {"prompt": "a three shot ad", "seconds": 10, "shots": 3})
    assert "model" not in plain
    # the connector's ranking (src/model_pick.py) leans the same way
    rows = [{**r, "min_seconds": int((fal.VIDEO_MODELS.get(r["model"]) or {}).get("durations", (4, 30))[0]),
             "max_seconds": int((fal.VIDEO_MODELS.get(r["model"]) or {}).get("durations", (4, 30))[1]),
             "draft": None, "routing": fal.slot_routing(r["model"])} for r in pricing.catalog_models()]
    ranked = model_pick.rank("one continuous 20s take", seconds=20, catalogue=rows,
                             price=lambda m, s: (100, s or 5, "1080p"))
    assert ranked["picks"][0]["model"] == "kling4"
    assert "single continuous take" in ranked["picks"][0]["reason"]
    refs = model_pick.rank("a scene held to five reference photos of the product", catalogue=rows,
                           price=lambda m, s: (100, s or 5, "1080p"))
    assert refs["picks"][0]["model"] == "kling4"
    cheap = model_pick.rank("the cheapest quick test", seconds=6, catalogue=rows,
                            price=lambda m, s: (100 if m != "ltx2.3" else 20, s or 5, "1080p"))
    assert cheap["picks"][0]["model"] == "ltx2.3"


def test_disabled_again_it_is_gone_from_everywhere(on):
    assert fal.disable_slots() == ["kling4"]
    assert "kling4" not in fal.VIDEO_MODELS
    assert "kling4" not in {m["id"] for m in providers.models_for("fal")}
    assert model_menu.video_id("kling4") == ""
