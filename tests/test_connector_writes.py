"""
The write tools on the listed servers (2026-10-11,
docs/tasks/task-connector-overnight.md PR 4): reference roles on
`write_scene`, `duplicate_scene`, `feedback`, `preferences` /
`set_preferences`, and `recipes` / `recipe` / `save_recipe`.

What is guarded: a role is stored exactly as the composer stores one and a
look-only photo is never the anchor; a copy carries words and photos and
never a still, a clip or a timeline; every row is one account's and another
account's ids are as missing as nonexistent ones; a preference is refused
off the catalogue and read only where a caller passed nothing; a saved
recipe comes back as quoted data; nothing is ever overwritten.
"""
import asyncio

import pytest

from src import (
    accounts,
    asset_shelf,
    entities,
    generative,
    ledger,
    mcp_feedback,
    mcp_preferences,
    mcp_recipes,
    mcp_server,
    outcomes,
    preprod,
    projects,
    render_assets,
    skills,
)
from src.cut import store as cut_store

SCENE = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact face. "
         "Style: soft window light, true colour, a 35mm frame at chest height. "
         "(0-4s) Sam lifts the lid of a dented biscuit tin and freezes. "
         "(4-10s) Hard cut to the hallway: Sam backs away from the open door, the tin "
         "still in one hand. No background music. Only diegetic sound: the tin lid, "
         "a floorboard. Avoid: plastic sheen, cartoon reactions.")
FACE = "/characters/sam/photo/face.jpg"
SIDE = "/characters/sam/photo/side.jpg"
ROOM = "/locations/kitchen/photo/room.jpg"


@pytest.fixture
def world(pg, monkeypatch):
    for init in (preprod.init, entities.init, generative.init, render_assets.init,
                 projects.init, cut_store.init, ledger.init, outcomes.init,
                 mcp_feedback.init, mcp_preferences.init, mcp_recipes.init):
        init(pg)
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.delenv("QUOTE_SIGNING_SECRET", raising=False)
    # the same photos for both: the gate is what is under test, not the folder
    monkeypatch.setattr(asset_shelf, "catalogue",
                        lambda dsn=None, account_id=None:
                        [{"category": "character", "name": "Sam", "text": "a courier",
                          "photos": [FACE, SIDE]},
                         {"category": "location", "name": "Kitchen", "text": "",
                          "photos": [ROOM]}])
    project = projects.create("The Tin", "a courier, a dented tin", pg, account_id=a)
    bobs = projects.create("Bob's", "", pg, account_id=b)
    return {"dsn": pg, "a": a, "b": b, "project": project["id"], "bobs_project": bobs["id"]}


def _write(world, who="a", **kw):
    return mcp_server.write_scene(SCENE, dsn=world["dsn"], account_id=world[who], **kw)


def _shot(world, scene_id, who="a"):
    return preprod.get_concept(scene_id, dsn=world["dsn"], account_id=world[who])["shots"][0]


# --------------------------------------------------------------------------
# roles on write_scene
# --------------------------------------------------------------------------

def test_roles_are_stored_as_the_composer_stores_them_and_a_look_photo_is_never_first(world):
    out = _write(world, refs=[ROOM, FACE, SIDE],
                 roles={ROOM: "light", FACE: "subject", SIDE: "framing", "/nope.jpg": "style",
                        "x": "notarole"})
    shot = _shot(world, out["scene_id"])
    # look-only photos (the room's light, the side's framing) go last; the
    # face, the subject, anchors; the roles ride beside the refs by their keys
    assert shot["refs"] == [FACE, ROOM, SIDE]
    assert shot["ref_roles"] == {ROOM: "light", FACE: "subject", SIDE: "framing"}
    assert out["roles"] == shot["ref_roles"] and out["reference_photos"] == 3
    # no roles: no key on the shot, the order as given
    plain = _write(world, refs=[ROOM, FACE])
    assert "ref_roles" not in _shot(world, plain["scene_id"]) and plain["roles"] == {}
    assert _shot(world, plain["scene_id"])["refs"] == [ROOM, FACE]
    # a role whose ref is not in refs is dropped, never stored
    stray = _write(world, refs=[FACE], roles={ROOM: "light"})
    assert "ref_roles" not in _shot(world, stray["scene_id"])


PLAIN = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact face. "
         "Style: soft window light, true colour. Sam lifts the lid of a dented biscuit "
         "tin and freezes, both hands still on it. No background music. Only diegetic "
         "sound: the tin lid. Avoid: plastic sheen.")


def test_the_scene_length_comes_from_the_preference_only_when_nothing_is_passed(world):
    """A one-window scene: a TIMED prompt's windows fix its length whatever
    anybody prefers (the sum of the windows is the scene)."""
    def length(**kw):
        out = mcp_server.write_scene(PLAIN, refs=[FACE], dsn=world["dsn"],
                                     account_id=kw.pop("account_id", world["a"]), **kw)
        return _shot(world, out["scene_id"], "a" if "account_id" not in kw else "b")["seconds"]
    assert length() == 10
    mcp_server.set_preferences(seconds=15, dsn=world["dsn"], account_id=world["a"])
    assert length() == 15
    assert length(seconds=8) == 8
    # a timed prompt keeps the length its windows add up to
    assert _shot(world, _write(world, refs=[FACE])["scene_id"])["seconds"] == 10
    # Bob's workspace has no preference: the default
    out = mcp_server.write_scene(PLAIN, refs=[FACE], dsn=world["dsn"], account_id=world["b"])
    assert _shot(world, out["scene_id"], "b")["seconds"] == 10


# --------------------------------------------------------------------------
# duplicate_scene
# --------------------------------------------------------------------------

@pytest.fixture
def rendered(world):
    """A scene of Alice's in her project, with a still and a clip attached
    the way a render attaches them."""
    out = _write(world, refs=[FACE, ROOM], roles={ROOM: "place"}, title="Tin opening",
                 project_id=world["project"])
    sid = out["scene_id"]
    concept = preprod.get_concept(sid, dsn=world["dsn"], account_id=world["a"])
    shots = [dict(concept["shots"][0])]
    shots[0]["media_url"] = "/renders/fal/tin.mp4"
    shots[0]["reference_image"] = "/renders/nano/tin.png"
    for part in (shots[0].get("timeline") or {}).get("parts") or []:
        part["media_url"] = "/renders/fal/part.mp4"
    preprod.update_concept_shots(sid, {"shots": shots, "duration": concept.get("duration")},
                                 warnings=[], dsn=world["dsn"], account_id=world["a"])
    return sid


def test_a_copy_carries_the_words_photos_roles_and_project_and_never_a_render(world, rendered):
    out = mcp_server.duplicate_scene(rendered, dsn=world["dsn"], account_id=world["a"])
    assert out["scene_id"] != rendered and out["copied_from"] == rendered
    assert out["copied"] == {"prompt": True, "refs": True, "project": True}
    copy = preprod.get_concept(out["scene_id"], dsn=world["dsn"], account_id=world["a"])
    shot, source = copy["shots"][0], _shot(world, rendered)
    assert copy["title"] == "Tin opening (copy)" and copy["project_id"] == world["project"]
    assert shot["prompt"] == source["prompt"] and shot["refs"] == source["refs"]
    assert shot["ref_roles"] == source["ref_roles"] == {ROOM: "place"}
    assert not shot.get("media_url") and not shot.get("reference_image")
    assert all(not p.get("media_url") for p in shot["timeline"]["parts"])
    assert not out["rendered"] and out["clips"] == [] and out["keyframe"] is None
    # the source is untouched
    assert _shot(world, rendered)["media_url"] == "/renders/fal/tin.mp4"


def test_a_copy_takes_the_fields_passed_and_runs_the_reference_gate(world, rendered, monkeypatch):
    monkeypatch.setattr(preprod, "refs_required", lambda: True)   # the suite's default is off
    new_prompt = SCENE.replace("biscuit tin", "cake tin")
    out = mcp_server.duplicate_scene(rendered, prompt=new_prompt, refs=[SIDE],
                                     seconds=6, project_id=0, dsn=world["dsn"],
                                     account_id=world["a"])
    shot = _shot(world, out["scene_id"])
    assert "cake tin" in shot["prompt"] and shot["refs"] == [SIDE]
    assert out["copied"] == {"prompt": False, "refs": False, "project": False}
    copy = preprod.get_concept(out["scene_id"], dsn=world["dsn"], account_id=world["a"])
    assert copy["project_id"] is None
    draft = mcp_server.duplicate_scene(rendered, refs=[], dsn=world["dsn"],
                                       account_id=world["a"])
    assert draft["needs_reference"] and _shot(world, draft["scene_id"])["refs"] == []
    with pytest.raises(ValueError, match="not one of your elements"):
        mcp_server.duplicate_scene(rendered, refs=["https://x/y.jpg"], dsn=world["dsn"],
                                   account_id=world["a"])
    with pytest.raises(ValueError, match="no project"):
        mcp_server.duplicate_scene(rendered, project_id=world["bobs_project"],
                                   dsn=world["dsn"], account_id=world["a"])


def test_another_accounts_scene_cannot_be_copied(world, rendered):
    with pytest.raises(ValueError, match=f"no scene {rendered}"):
        mcp_server.duplicate_scene(rendered, dsn=world["dsn"], account_id=world["b"])
    with pytest.raises(ValueError, match="no scene 999"):
        mcp_server.duplicate_scene(999, dsn=world["dsn"], account_id=world["a"])


# --------------------------------------------------------------------------
# feedback
# --------------------------------------------------------------------------

def test_feedback_is_kept_with_who_said_it_and_bounded(world):
    token = mcp_server.CALLER_USER.set("user-alice")
    try:
        out = mcp_server.give_feedback("the crop was too tight on 9:16", ref="gen:12",
                                       tool="reformat", dsn=world["dsn"], account_id=world["a"])
    finally:
        mcp_server.CALLER_USER.reset(token)
    assert out["saved"] and out["tool"] == "reformat" and out["ref"] == "gen:12"
    (row,) = mcp_feedback.recent(world["a"], dsn=world["dsn"])
    assert row["user_id"] == "user-alice" and row["text"].startswith("the crop")
    assert mcp_feedback.recent(world["b"], dsn=world["dsn"]) == []
    for kwargs, match in ((dict(text=""), "say what"),
                          (dict(text="x" * 2001), "at most 2000"),
                          (dict(text="ok", tool="board"), "tool names"),
                          (dict(text="ok", ref="r" * 121), "short id")):
        with pytest.raises(ValueError, match=match):
            mcp_server.give_feedback(dsn=world["dsn"], account_id=world["a"], **kwargs)
    # a second note is a second row, never an edit of the first
    mcp_server.give_feedback("and the pad was fine", dsn=world["dsn"], account_id=world["a"])
    assert len(mcp_feedback.recent(world["a"], dsn=world["dsn"])) == 2


# --------------------------------------------------------------------------
# preferences
# --------------------------------------------------------------------------

def test_preferences_start_empty_and_list_the_choices(world):
    out = mcp_server.read_preferences(dsn=world["dsn"], account_id=world["a"])
    assert all(out[f] is None for f in mcp_server.PREFERENCE_FIELDS) and out["set_at"] is None
    assert "9:16" in out["choices"]["aspect"] and out["choices"]["seconds"] == [4, 30]
    assert "wan3" in out["choices"]["video_model"]


@pytest.mark.parametrize("kwargs, match", [
    ({}, "nothing to set"),
    ({"aspect": "2:1"}, "aspect is one of"),
    ({"seconds": 3}, "seconds is 4 to 30"),
    ({"seconds": 31}, "seconds is 4 to 30"),
    ({"seconds": "ten"}, "whole number"),
    ({"video_model": "sora"}, "video_model is one of"),
    ({"image_model": "dalle"}, "image_model is one of"),
    ({"draft_first": "yes"}, "true or false"),
])
def test_a_value_off_the_catalogue_is_refused_never_clamped(world, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mcp_server.set_preferences(dsn=world["dsn"], account_id=world["a"], **kwargs)
    assert mcp_preferences.history(world["a"], dsn=world["dsn"]) == []


def test_set_preferences_merges_and_every_change_is_a_new_row(world):
    first = mcp_server.set_preferences(aspect="4:5", seconds=12, dsn=world["dsn"],
                                       account_id=world["a"])
    assert first["aspect"] == "4:5" and first["seconds"] == 12 and first["changed"] == ["aspect", "seconds"]
    second = mcp_server.set_preferences(video_model="wan3", draft_first=True, dsn=world["dsn"],
                                        account_id=world["a"])
    assert second["aspect"] == "4:5" and second["seconds"] == 12          # kept
    assert second["video_model"] == "wan3" and second["draft_first"] is True
    assert len(mcp_preferences.history(world["a"], dsn=world["dsn"])) == 2
    assert mcp_server.read_preferences(dsn=world["dsn"], account_id=world["b"])["aspect"] is None


def test_a_quote_uses_the_preferred_model_and_draft_frame_only_when_nothing_is_named(world):
    sid = _write(world, refs=[FACE])["scene_id"]
    plain = mcp_server.quote_render(sid, dsn=world["dsn"], account_id=world["a"],
                                    listing="claude")
    assert "preference" not in plain and plain["clip"]["model"] == "ltx2.3"
    mcp_server.set_preferences(video_model="wan3", draft_first=True, dsn=world["dsn"],
                               account_id=world["a"])
    preferred = mcp_server.quote_render(sid, dsn=world["dsn"], account_id=world["a"],
                                        listing="claude")
    assert preferred["preference"]["model"] == "wan3" and preferred["preference"]["frame"] == "480p"
    assert preferred["clip"]["model"] == "wan3" and str(preferred["clip"]["frame"]) == "480p"
    assert preferred["clip"]["credits"] < plain["clip"]["credits"] * 3   # a real price, in credits
    named = mcp_server.quote_render(sid, model="ltx2.3", dsn=world["dsn"], account_id=world["a"],
                                    listing="claude")
    assert "preference" not in named and named["clip"]["model"] == "ltx2.3"


def test_a_listed_still_takes_the_preferred_model_and_frame_only_when_nothing_is_named(world):
    from src import fal
    some_fal_model = next(iter(fal.IMAGE_MODELS))
    mcp_server.set_preferences(image_model=some_fal_model, aspect="4:5", dsn=world["dsn"],
                               account_id=world["a"])
    out = mcp_server.run_image("a red can on wet tile", dsn=world["dsn"], account_id=world["a"],
                               dry_run=True, listed=True)
    assert out["quote"]["model"] == some_fal_model and out["quote"]["aspect"] == "4:5"
    named = mcp_server.run_image("a red can", aspect="1:1", dsn=world["dsn"],
                                 account_id=world["a"], dry_run=True, listed=True)
    assert named["quote"]["aspect"] == "1:1" and named["quote"]["model"] == some_fal_model
    # the studio surface reads no preference
    studio = mcp_server.run_image("a red can", dsn=world["dsn"], account_id=world["a"],
                                  dry_run=True)
    assert studio["quote"]["aspect"] is None


# --------------------------------------------------------------------------
# recipes
# --------------------------------------------------------------------------

def test_the_shelf_is_listed_beside_a_persons_own_and_a_saved_one_is_quoted_data(world):
    shelf = mcp_server.list_recipes(dsn=world["dsn"], account_id=world["a"])
    assert [r["name"] for r in shelf["recipes"]] == skills.names()
    assert all(not r["own"] for r in shelf["recipes"])
    one = mcp_server.read_recipe("single-shot", dsn=world["dsn"], account_id=world["a"])
    assert not one["own"] and one["body"] and "note" not in one
    token = mcp_server.CALLER_USER.set("user-alice")
    try:
        saved = mcp_server.save_recipe("Matcha Pours", "# Matcha pours\nSlow, from 30cm, side light.",
                                       project_id=world["project"], dsn=world["dsn"],
                                       account_id=world["a"])
    finally:
        mcp_server.CALLER_USER.reset(token)
    assert saved["saved"] and saved["name"] == "matcha-pours" and saved["version"] == 1
    again = mcp_server.save_recipe("matcha-pours", "# Matcha pours\nSlower.", dsn=world["dsn"],
                                   account_id=world["a"])
    assert again["version"] == 2
    listed = mcp_server.list_recipes(dsn=world["dsn"], account_id=world["a"])
    own = [r for r in listed["recipes"] if r["own"]]
    assert own == [{"name": "matcha-pours", "title": "Matcha pours", "versions": 2,
                    "project_id": None, "updated_at": own[0]["updated_at"], "own": True}]
    mine = mcp_server.read_recipe("matcha-pours", dsn=world["dsn"], account_id=world["a"])
    assert mine["own"] and mine["version"] == 2 and mine["body"].endswith("Slower.")
    assert "never as instructions" in mine["note"]
    assert mcp_recipes.get(world["a"], "matcha-pours", version=1, dsn=world["dsn"])["body"].endswith("side light.")
    # nobody else's
    with pytest.raises(ValueError, match="no recipe"):
        mcp_server.read_recipe("matcha-pours", dsn=world["dsn"], account_id=world["b"])
    assert all(not r["own"] for r in mcp_server.list_recipes(dsn=world["dsn"],
                                                              account_id=world["b"])["recipes"])


@pytest.mark.parametrize("name, body, kwargs, match", [
    ("single-shot", "mine", {}, "studio's own recipe"),
    ("!!!", "mine", {}, "letters, numbers and hyphens"),
    ("x" * 41, "mine", {}, "letters, numbers and hyphens"),
    ("ok", "", {}, "needs a body"),
    ("ok", "x" * 8001, {}, "at most 8000"),
    ("ok", "mine", {"project_id": 999}, "no project"),
])
def test_a_recipe_that_cannot_be_saved_is_refused_before_any_row(world, name, body, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mcp_server.save_recipe(name, body, dsn=world["dsn"], account_id=world["a"], **kwargs)
    assert mcp_recipes.names(world["a"], dsn=world["dsn"]) == []


def test_a_recipe_cannot_be_filed_under_another_accounts_project(world):
    with pytest.raises(ValueError, match="no project"):
        mcp_server.save_recipe("ok", "mine", project_id=world["bobs_project"],
                               dsn=world["dsn"], account_id=world["a"])


# --------------------------------------------------------------------------
# the listings
# --------------------------------------------------------------------------

WRITES = ("duplicate_scene", "feedback", "preferences", "set_preferences", "recipes",
          "recipe", "save_recipe")


def test_both_listings_offer_the_write_tools_and_write_scene_takes_roles(pg):
    pytest.importorskip("mcp")
    preprod.init(pg)
    for listed in (True, "claude"):
        server = mcp_server.build_server(dsn=pg, listed=listed,
                                         job_status=lambda i, account_id=None: None)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        for name in WRITES:
            assert name in tools, (listed, name)
            assert tools[name].annotations.destructive_hint is False
        assert "roles" in tools["write_scene"].input_schema["properties"]
        assert "roles" in tools["duplicate_scene"].input_schema["properties"]
        assert tools["write_scene"].input_schema["properties"]["seconds"].get("default") is None
    studio = {t.name for t in asyncio.run(mcp_server.build_server(dsn=pg).list_tools())}
    assert not set(WRITES) & studio


def test_a_voiceover_that_will_not_fit_its_window_is_said_on_the_written_scene(world):
    """write_scene plans with no model (timeline.fallback); the split is
    checked the way the studio's planned timeline is (timeline.keep), so
    the card says when a voiceover cannot be said in its window."""
    long_line = " ".join(["word"] * 30)
    scene = SCENE.replace("and freezes.", f'and freezes. VO: "{long_line}"')
    out = mcp_server.write_scene(scene, dsn=world["dsn"], account_id=world["a"], refs=[FACE])
    shot = _shot(world, out["scene_id"])
    [why] = [w for w in shot["timeline"]["warnings"] if "voiceover" in w]
    assert why.startswith("shot 1 (0-4s): the voiceover is 30 words")
    assert "it will not fit" in why
    assert long_line in shot["timeline"]["parts"][0]["prompt"]       # kept all the same
