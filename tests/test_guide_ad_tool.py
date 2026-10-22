"""The ad card's proposal (step 3 of docs/tasks/task-url-to-ad.md): make_ad
is a composer-only make, checked by code and never run by the Guide."""
import pytest

from src import guide_tools as gt


def test_make_ad_is_a_make_the_studio_runs_never_the_guide():
    assert gt.is_make(gt.AD_TOOL) and gt.is_write(gt.AD_TOOL)


def test_a_brief_is_kept_and_a_length_or_shape_off_the_list_is_refused():
    assert gt.check_args(gt.AD_TOOL, {"brief": "  A launch ad   for Gygler "}) == {
        "brief": "A launch ad for Gygler"}
    assert gt.check_args(gt.AD_TOOL, {"brief": "x", "seconds": 30, "aspect": "9:16"}) == {
        "brief": "x", "seconds": 30, "aspect": "9:16"}
    for bad in ({"brief": ""}, {"brief": "x", "seconds": 300}, {"brief": "x", "seconds": True},
                {"brief": "x", "aspect": "4:3"}):
        with pytest.raises(gt.Refused):
            gt.check_args(gt.AD_TOOL, bad)


def test_an_address_in_the_brief_is_refused_like_every_proposal():
    with pytest.raises(gt.Refused):
        gt.check_args(gt.AD_TOOL, {"brief": "an ad for https://gygler.com"})


def test_only_the_composer_is_handed_the_ad_card():
    def names(**kw):
        return {s["name"] for s in gt.session(local=True, **kw)[0]}
    assert gt.AD_TOOL in names(maker=True)
    assert gt.AD_TOOL not in names(maker=True, makes=("make_image",))   # the pill
    assert gt.AD_TOOL not in names()                                    # a talking turn
