"""The Kling 4.0 slot (fal.SLOTS; parked 2026-10-22 by group 6 checkbox 4 of
the overnight task, FILLED the same day when fal's API opened;
docs/tasks/task-vesper-v2.md).

A slot is a row with the table's shape plus a flag and a routing rule. On
the live table (fal's official ids and prices filled in, the flag not
parked) it is in every picker, listing and quote, priced by the same
estimators, and the routing rules prefer it for a 15-30s single shot and
a reference-heavy scene. Parked with PHANTRA_KLING_4=0, or with an id or
a price of None, no picker, listing, quote, proposal or recommendation
can see it. Nothing points at a reseller.
"""
import json
from pathlib import Path

import pytest

from app import api
from src import fal, guide_tools, model_menu, model_pick, pricing, providers

ROOT = Path(__file__).resolve().parent.parent
PRICES = {"720p": 0.157, "1080p": 0.235}


@pytest.fixture
def off(monkeypatch):
    """Parked for one test; the table restored after."""
    monkeypatch.setenv("PHANTRA_KLING_4", "0")
    fal.disable_slots()
    yield
    monkeypatch.delenv("PHANTRA_KLING_4", raising=False)
    fal.disable_slots()
    fal.enable_slots()


@pytest.fixture
def on(monkeypatch):
    """The slot as shipped: flag unset (on), fal's ids and prices."""
    monkeypatch.delenv("PHANTRA_KLING_4", raising=False)
    monkeypatch.delenv("FAL_PRICE_KLING4", raising=False)
    fal.disable_slots()
    added = fal.enable_slots()
    try:
        yield added
    finally:
        fal.disable_slots()
        fal.enable_slots()


def _nowhere():
    assert "kling4" not in fal.VIDEO_MODELS
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


def test_the_slot_is_filled_from_fals_published_api():
    """What fal's queue schema and model listing said on 2026-10-22."""
    spec = fal.SLOTS["kling4"]
    assert spec["available"] is True
    assert spec["t2v"] == "kling/v4/text-to-video" and spec["i2v"] == "kling/v4/image-to-video"
    assert spec["prices"] == PRICES and spec["resolutions"] == ("720p", "1080p")
    assert spec["default_resolution"] == "720p"        # the house rule: cheap 720p first
    assert spec["durations"] == (3, 30) and spec["duration_wire"] == "int"
    assert spec["params"] == ("duration", "resolution", "aspect_ratio")
    assert spec["checked"] == "2026-10-22" and spec["source"].startswith("https://fal.ai/models/kling/v4/")
    assert spec["routing"] == {"single_shot_seconds": (15, 30), "reference_heavy": 3}
    assert fal.SLOT_FLAGS["kling4"] == "PHANTRA_KLING_4"


def test_on_by_default_it_is_on_the_live_table(on):
    assert on == ["kling4"] and fal.slot_ready("kling4") is True and fal.slot_enabled("kling4") is True
    assert "kling4" in fal.VIDEO_MODELS
    row = fal.VIDEO_MODELS["kling4"]
    assert row["t2v"] == "kling/v4/text-to-video" and row["prices"] == PRICES
    assert "routing" not in row and "available" not in row       # a table row's shape
    assert "kling4" in {m["id"] for m in providers.models_for("fal")}
    assert providers.band_for("fal", "kling4").tier == "creator"
    choice = providers.check_render_choice("fal", "kling4", 20, None)
    assert choice["frame"] == "720p" and choice["estimate_usd"] == pytest.approx(0.157 * 20)
    hd = providers.check_render_choice("fal", "kling4", 20, "1080p")
    assert hd["estimate_usd"] == pytest.approx(0.235 * 20)
    cat = next(r for r in pricing.catalog_models() if r["model"] == "kling4")
    assert cat["name"] == "Kling 4.0" and cat["frame"] == "720p"
    assert cat["credits"] == pricing.credits_for(pricing.usd_micros(0.157 * 5), model="kling4")
    assert model_menu.video_id("kling4") == "kling4" and model_menu.label_for("kling4") == "Kling 4.0"
    # the table's rails: lengths fitted up to 30 and never past; the default
    # is already the cheapest tier so no draft is offered; the price by tier
    assert fal.fit_duration("kling4", 40) == 30 and fal.fit_duration("kling4", 7) == 7
    assert fal.draft_resolution("kling4") is None
    assert fal.estimate_cost(1, model="kling4", duration=10, resolution="1080p") == pytest.approx(2.35)
    assert fal.estimate_cost(1, model="kling4", duration=10, resolution="720p") == pytest.approx(1.57)
    assert api.compute_capabilities()["kling_4"] is True


def test_the_request_body_is_what_fals_schema_takes(on):
    """duration an integer 3-30, resolution and aspect_ratio by name; the
    schema's multi_prompt is never sent (the studio's timed shots are its
    own)."""
    model_id, body = fal.build_body("a single take", model="kling4", duration=20,
                                    resolution="1080p", aspect_ratio="16:9")
    assert model_id == "kling/v4/text-to-video"
    assert body["duration"] == 20 and isinstance(body["duration"], int)
    assert body["resolution"] == "1080p" and body["aspect_ratio"] == "16:9"
    assert "multi_prompt" not in body
    model_id, body = fal.build_body("a single take", model="kling4", duration=30,
                                    resolution="720p", aspect_ratio="9:16",
                                    image_url="https://example.test/start.jpg")
    assert model_id == "kling/v4/image-to-video" and body["duration"] == 30
    assert body["resolution"] == "720p"


def test_parked_with_the_flag_it_is_offered_nowhere(off):
    assert fal.slot_enabled("kling4") is False and fal.slot_ready("kling4") is False
    assert fal.enable_slots() == [] and fal.ready_slots() == []
    _nowhere()


def test_an_id_or_a_price_of_none_parks_it_whatever_the_flag_says(monkeypatch):
    monkeypatch.delenv("PHANTRA_KLING_4", raising=False)
    spec = fal.SLOTS["kling4"]
    saved = {k: spec[k] for k in ("t2v", "i2v", "prices")}
    fal.disable_slots()
    try:
        spec["prices"] = None
        assert fal.slot_ready("kling4") is False and fal.enable_slots() == []
        _nowhere()
        spec["prices"] = dict(PRICES)
        spec["i2v"] = None
        assert fal.slot_ready("kling4") is False and fal.enable_slots() == []
        _nowhere()
        spec["i2v"] = saved["i2v"]
        spec["prices"] = {"720p": 0.157, "1080p": None}       # one tier unpriced: still parked
        assert fal.slot_ready("kling4") is False
    finally:
        spec.update(saved)
        fal.disable_slots()
        fal.enable_slots()


def test_the_brains_menu_and_the_connectors_ranking_never_name_it_parked(off, monkeypatch):
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
    assert fal.SLOTS["kling4"]["t2v"].startswith("kling/v4/")
    assert fal.SLOTS["kling4"]["source"].startswith("https://fal.ai/")
    for path in ("src/fal.py", "src/model_menu.py", "src/model_pick.py", "src/pricing.py",
                 "src/providers.py", "app/api.py"):
        assert "useapi" not in (ROOT / path).read_text().lower(), path
    text = (ROOT / "src/fal.py").read_text()
    block = text[text.index("SLOT_FLAGS"):text.index("enable_slots()\n\nMODELS")].lower()
    for word in ("higgsfield", "useapi", "relay"):
        assert word not in block, word
    for path in ("src/model_menu.py", "src/model_pick.py"):
        assert "higgsfield" not in (ROOT / path).read_text().lower(), path


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


def test_the_default_kling_pick_stays_kling_3(on):
    """The `kling` platform's default tier is still Kling 3 Turbo Pro (the
    cheaper rate); Kling 4.0 is reached by name, by the pickers, or by the
    routing rule, never by silently replacing the default."""
    assert fal.PLATFORM_MODELS["kling"] == "kling3-turbo-pro"


def test_disabled_again_it_is_gone_from_everywhere(on):
    assert fal.disable_slots() == ["kling4"]
    assert "kling4" not in fal.VIDEO_MODELS
    assert "kling4" not in {m["id"] for m in providers.models_for("fal")}
    assert model_menu.video_id("kling4") == ""
