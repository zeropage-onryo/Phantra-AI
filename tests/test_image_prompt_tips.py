"""Per-model prompt tips for stills (src/image_prompt_tips.py). Nothing here
reaches a network or a model."""
import pytest

from src import fal, image_prompt_tips, model_menu, nano_banana


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)


def test_every_tip_names_a_real_still_model_and_a_source():
    for model, row in image_prompt_tips.TIPS.items():
        assert model == model_menu.NANO_ID or model in fal.IMAGE_MODELS, model
        assert row["tip"].strip() and row["sources"] and row["checked"]


def test_models_without_a_vendor_guide_have_no_row():
    # FLUX 1.1 Pro: no first-party guide was read; silence, not a guess
    assert image_prompt_tips.tip_for("flux-pro1.1") is None
    assert image_prompt_tips.tip_for("not-a-model") is None


def test_the_brain_is_shown_the_tip_beside_its_model(keyed):
    text = model_menu.for_model()
    assert "How to write its prompt" in text
    ideo = [i for i, row in enumerate(text.splitlines()) if row.startswith("- ideogram4.5")]
    assert ideo and "quotes" in text.splitlines()[ideo[0] + 1]


def test_switch_off_is_the_old_list(keyed, monkeypatch):
    monkeypatch.setenv(image_prompt_tips.SWITCH_ENV, "0")
    assert "How to write its prompt" not in model_menu.for_model()
