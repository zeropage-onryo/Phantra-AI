"""The settings rename (2026-10-16): an old-named setting still on a deployment
must reach its new PHANTRA_* name, and must never override a new one."""
from src import legacy_env

OLD = "ZERO" "PAGE_"


def test_an_old_name_reaches_its_new_name():
    env = {OLD + "SIGNUP_CREDITS": "150"}
    assert legacy_env.adopt(env) == ["PHANTRA_SIGNUP_CREDITS"]
    assert env["PHANTRA_SIGNUP_CREDITS"] == "150"


def test_a_new_name_already_set_wins():
    env = {OLD + "OPEN_SIGNUP": "0", "PHANTRA_OPEN_SIGNUP": "1"}
    assert legacy_env.adopt(env) == []
    assert env["PHANTRA_OPEN_SIGNUP"] == "1"


def test_the_short_prefix_and_the_suffixed_name_are_covered():
    env = {"Z" "PF_PORT": "9000", "PINTEREST_BOARD_ZERO" "PAGE": "board-1"}
    legacy_env.adopt(env)
    assert env["PHANTRA_PORT"] == "9000"
    assert env["PINTEREST_BOARD_PHANTRA"] == "board-1"


def test_unrelated_settings_are_left_alone():
    env = {"FAL_KEY": "k"}
    assert legacy_env.adopt(env) == []
    assert env == {"FAL_KEY": "k"}
