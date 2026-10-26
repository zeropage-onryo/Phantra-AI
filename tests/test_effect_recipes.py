"""The recipe effects (src/effect_recipes.py, 2026-10-26): a written prompt in
prompts/effects/ run on one video model with the person's photo, as rows of
src/effects.py -- so the quote, the hold and the run are the table's own."""
from __future__ import annotations

import pytest

from src import effect_recipes, effects, fal, ledger


@pytest.fixture
def recipes_on(monkeypatch):
    monkeypatch.setenv(effect_recipes.ENV, "1")


def test_every_recipe_is_a_row_with_its_prompt_on_disk():
    assert len(effect_recipes.RECIPES) == 10
    for name in effect_recipes.RECIPES:
        row = effects.EFFECTS[name]
        assert row["recipe"] is True and row["category"] == "video_effect"
        assert row["takes"] == "image" and row["output"] == "video" and row["sources"] == (1, 1)
        assert (effect_recipes.PROMPTS_DIR / f"{name}.txt").is_file()
        # the prompt is written, and the slot only where the file has one
        assert row["prompt"] == ("optional" if effect_recipes.has_detail(name) else "none")
        assert bool(row["hint"]) == effect_recipes.has_detail(name), name
        assert "{" not in effect_recipes.prompt_for(name), name


def test_the_model_and_its_price_are_the_video_tables_own():
    spec = fal.VIDEO_MODELS[effect_recipes.MODEL]
    row = effects.EFFECTS["meltdown"]
    assert row["endpoint"] == spec["i2v"] and row["source"] == spec["source"]
    lo, hi = spec["durations"]
    assert all(lo <= int(d) <= hi for d in effect_recipes.DURATIONS)
    assert len(effect_recipes.prompt_for("float_drop", "x" * 200)) <= fal.prompt_max(effect_recipes.MODEL)


def test_off_by_default_listed_and_runnable_only_with_the_flag(monkeypatch, recipes_on):
    assert "meltdown" in effects.listed_names()
    monkeypatch.delenv(effect_recipes.ENV)
    assert not set(effect_recipes.RECIPES) & set(effects.listed_names())
    with pytest.raises(ValueError, match=effect_recipes.ENV):
        effects.spec("meltdown")


def test_a_five_second_recipe_is_priced_off_the_models_rate(recipes_on):
    rate = fal.VIDEO_MODELS[effect_recipes.MODEL]["prices"]["1080p"]
    assert effects.default_usd("gone") == pytest.approx(rate * 5)
    assert effects.quote_usd("gone", effects.check_options("gone", {"duration": "10"})) == pytest.approx(rate * 10)
    assert ledger.charge_credits(effects.default_usd("gone")) > 0
    with pytest.raises(ValueError):
        effects.check_options("gone", {"duration": "7"})        # refused, never clamped


def test_the_person_adds_one_detail_never_the_prompt(recipes_on):
    _, body = effects.build_body("float_drop", ["https://m/p.jpg"], "a red sneaker", {"duration": "5"})
    assert body["image_url"] == "https://m/p.jpg" and body["duration"] == "5"
    assert "lingering longest on a red sneaker" in body["prompt"]
    assert body["prompt"].startswith("The person in the image tips backward")
    # nothing typed: the recipe's default stands in the slot, or nothing does
    _, plain = effects.build_body("iris_dive", ["https://m/p.jpg"], "", {"duration": "5"})
    assert "a vast sunlit landscape seen from above" in plain["prompt"]
    _, drop = effects.build_body("float_drop", ["https://m/p.jpg"], "", {"duration": "5"})
    assert "lingering" not in drop["prompt"] and "{detail}" not in drop["prompt"]
    # a recipe with no slot takes no words, and a detail is short
    with pytest.raises(ValueError, match="takes no prompt"):
        effects.check_prompt("gone", "make it purple")
    with pytest.raises(ValueError, match="short detail"):
        effects.check_prompt("float_drop", "x" * (effects.RECIPE_MAX_NOTE + 1))


def test_the_gallery_lists_them_with_their_words_and_their_box(recipes_on):
    rows = {r["id"]: r for r in effects.catalogue()}
    assert rows["window_grab"]["pricing"].endswith(f"({effect_recipes.MODEL})")
    from app import api
    view = api._effect_view("window_grab")
    assert view["recipe"] is True and view["hint"] == "The product on the seat (optional)"
    assert view["blurb"] == effect_recipes.RECIPES["window_grab"]["blurb"]
    assert view["tags"] == ["product"] and view["credits"] == ledger.charge_credits(0.14 * 5)
    assert view["made_with"] == effect_recipes.MODEL_LABEL
