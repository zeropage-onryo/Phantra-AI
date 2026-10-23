"""Grok Imagine Video 1.5 and 1.5 Lite on fal (2026-10-23).

Pins what was read off fal's queue OpenAPI schemas that day -- the
endpoint ids in xAI's own namespace, the integer 1-15 duration, the three
resolutions and their rates, aspect_ratio only on text-to-video -- and
that the rows reach the bands, the public catalog and the shot dialect.
Nothing here spends money: no test calls fal (conftest blocks the network).
"""
import pytest

from src import fal, pricing, providers, shot

GROK = ("grok1.5", "grok1.5-lite")


@pytest.mark.parametrize("model", GROK)
def test_the_rows_use_xais_own_namespace(model):
    spec = fal.model_spec(model)
    assert spec["t2v"].startswith("xai/grok-imagine-video/v1.5/")
    assert spec["i2v"].startswith("xai/grok-imagine-video/v1.5/")
    assert spec["t2v"].endswith("/text-to-video") and spec["i2v"].endswith("/image-to-video")
    assert spec["platform"] == "grok"


@pytest.mark.parametrize("model", GROK)
def test_any_whole_second_from_one_to_fifteen_travels_as_an_integer(model):
    for seconds in (1, 6, 15):
        _, body = fal.build_body("a cat knocks a pen off a desk", model=model, duration=seconds)
        assert body["duration"] == seconds and isinstance(body["duration"], int)


@pytest.mark.parametrize("model", GROK)
def test_the_house_default_is_720p_and_1080p_is_one_pick_away(model):
    spec = fal.model_spec(model)
    assert spec["default_resolution"] == "720p"
    assert spec["resolutions"] == ("480p", "720p", "1080p")


def test_the_rates_are_the_model_pages_rate_cards():
    assert fal.model_spec("grok1.5")["prices"] == {"480p": 0.08, "720p": 0.14, "1080p": 0.25}
    assert fal.model_spec("grok1.5-lite")["prices"] == {"480p": 0.02, "720p": 0.03, "1080p": 0.14}
    assert fal.estimate_cost(1, model="grok1.5", duration=6, resolution="720p") == pytest.approx(0.84)
    assert fal.estimate_cost(1, model="grok1.5-lite", duration=10, resolution="1080p") == pytest.approx(1.40)


@pytest.mark.parametrize("model", GROK)
def test_aspect_is_sent_on_text_to_video_and_not_beside_a_start_frame(model):
    _, t2v = fal.build_body("x", model=model, aspect_ratio="3:2")
    assert t2v["aspect_ratio"] == "3:2"
    model_id, i2v = fal.build_body("x", model=model, image_url="https://media.phantra.ai/k.jpg")
    assert model_id.endswith("/image-to-video") and "aspect_ratio" not in i2v
    assert i2v["image_url"] == "https://media.phantra.ai/k.jpg"
    assert set(fal.t2v_aspects(model)) == {"16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"}


def test_the_platform_renders_on_lite_and_logs_as_grok():
    assert fal.PLATFORM_MODELS["grok"] == "grok1.5-lite"
    assert "grok" in fal.VIDEO_LOG_TOOLS
    assert providers.platform_default("grok") == ("fal", "grok1.5-lite")


def test_both_are_banded_and_1080p_grok_is_a_creator_render():
    assert providers.band_for("fal", "grok1.5-lite").tier == "standard"
    assert providers.band_for("fal", "grok1.5", "720p").tier == "standard"
    assert providers.band_for("fal", "grok1.5", "1080p").tier == "creator"


def test_both_are_in_the_public_catalog():
    names = {m: n for _p, m, n, _b in pricing.catalog_rows()}
    assert names["grok1.5"] == "Grok Imagine 1.5"
    assert names["grok1.5-lite"] == "Grok Imagine 1.5 Lite"


def test_the_grok_dialect_names_the_camera_then_the_action_and_the_sound():
    s = shot.Shot(subject="a gloved hand", action="closes a steel drawer", camera="push_in",
                  size="close", setting="a cramped garage at night",
                  lighting="one warm practical", audio="the metallic clunk", look="")
    prompt = shot.render(s, "grok")
    assert prompt.startswith("The camera pushes in slowly on a close shot: a gloved hand closes")
    assert "in a cramped garage at night." in prompt
    assert prompt.endswith("Sound: the metallic clunk.")
