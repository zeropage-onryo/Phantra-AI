"""Halloween costumes (src/costumes.py, 2026-10-27): a still preview with the
costume picked from a list, and the costume carried into the video recipe."""
from __future__ import annotations

import pytest

from src import costumes, effect_recipes, effects, fal


def test_the_preview_is_a_row_with_one_costume_per_value():
    row = effects.EFFECTS["costume-preview"]
    assert row["takes"] == "image" and row["output"] == "image" and row["sources"] == (1, 1)
    assert row["prompt"] == "none"                       # the words are ours
    assert tuple(row["options"]["costume"]["values"]) == tuple(costumes.COSTUMES)
    assert row["options"]["costume"]["required"] is True
    assert "costume-preview" in effects.listed_names()  # no flag: it is a plain still


def test_the_body_carries_the_written_prompt_and_no_costume_field():
    opts = effects.check_options("costume-preview", {"costume": "vampire"})
    endpoint, body = effects.build_body("costume-preview", ["https://m/p.jpg"], "", opts)
    assert endpoint == "fal-ai/nano-banana/edit"
    assert body["image_urls"] == ["https://m/p.jpg"] and body["num_images"] == 1
    assert "costume" not in body                          # not a field the model takes
    assert costumes.COSTUMES["vampire"] in body["prompt"]
    assert "same person" in body["prompt"] and "{" not in body["prompt"]


def test_an_unknown_costume_is_refused_never_guessed():
    with pytest.raises(ValueError, match="costume"):
        effects.check_options("costume-preview", {"costume": "a famous movie character"})
    with pytest.raises(ValueError, match="costume"):
        effects.check_options("costume-preview", {})


def test_the_preview_is_priced_like_one_still():
    assert effects.default_usd("costume-preview") == pytest.approx(0.039)


def test_the_picked_costume_reaches_the_video_recipe_in_full(monkeypatch):
    monkeypatch.setenv(effect_recipes.ENV, "1")
    for said in ("Zombie bride", "zombie_bride", "zombie bride costume"):
        _, body = effects.build_body("costume_try_on", ["https://m/p.jpg"], said, {"duration": "5"})
        assert costumes.COSTUMES["zombie_bride"] in body["prompt"], said
    # a costume of the person's own words stays their words
    _, body = effects.build_body("costume_try_on", ["https://m/p.jpg"], "a sushi chef", {"duration": "5"})
    assert "wearing a sushi chef" in body["prompt"]
    longest = max(costumes.COSTUMES.values(), key=len)
    assert len(effect_recipes.prompt_for("costume_try_on", longest)) <= fal.prompt_max(effect_recipes.MODEL)
