"""A brand kit's products and cast become real references (2026-10-22,
docs/tasks/task-kit-products-and-screens.md Part B).

Scene 442 named the Gygler app in shot 2 and the kit linked nothing, so the
app was drawn from words. Linked to the kit, an element named in a scene --
by its name or an alias -- is held to the scene as what it is FOR (a
product, a subject), and a timed part that names it is held to it too.
Opt-in byte for byte: no kit, or nothing named, changes nothing.
"""
import pytest

from app import api, auth
from src import accounts, brand_kits, entities, generative, preprod, pricing, project_context, timeline

APP = "/props/gygler-app/photo/app.jpg"
CHEF = "/characters/marco/photo/marco.jpg"
DISH = "https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-c438-x.jpg"
SCENE = ("(0-3s) Hands garnish the dish. (3-7s) A hand taps the tablet screen. "
         "(7-10s) Marco smiles at the lens.")


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})


@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    generative.init(pg)
    brand_kits.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("kp-mine", "Mine", "#fff", dsn=pg)
    prop = entities.add_prop("Gygler App", dsn=pg, account_id=mine)
    chef = entities.add_character("Marco", dsn=pg, account_id=mine)
    monkeypatch.setattr(api, "_assets_all", lambda account_id=None: [
        {"id": f"prop-{prop}", "category": "prop", "name": "Gygler App", "text": "",
         "photos": [APP]},
        {"id": f"character-{chef}", "category": "character", "name": "Marco", "text": "",
         "photos": [CHEF]}])
    return pg, mine, prop, chef


def kit_of(pg, mine, prop, chef=None, aliases=("the app", "tablet screen")):
    spec = {"products": [{"kind": "prop", "id": prop, "aliases": list(aliases)}]}
    if chef:
        spec["characters"] = [{"kind": "character", "id": chef}]
    return brand_kits.create("Gygler", spec, pg, account_id=mine)


def test_a_link_keeps_its_aliases_and_a_link_without_any_has_no_key(dbx):
    pg, mine, prop, _ = dbx
    with_aliases = kit_of(pg, mine, prop)
    assert with_aliases["spec"]["products"][0]["aliases"] == ["the app", "tablet screen"]
    plain = brand_kits.create("Plain", {"products": [{"kind": "prop", "id": prop}]}, pg,
                              account_id=mine)
    assert "aliases" not in plain["spec"]["products"][0]
    with pytest.raises(brand_kits.KitError):
        brand_kits.create("Many", {"products": [{"kind": "prop", "id": prop,
                                                 "aliases": [f"a{i}x" for i in range(9)]}]},
                          pg, account_id=mine)


def test_an_element_is_named_by_its_name_or_an_alias_as_a_whole_phrase(dbx):
    pg, mine, prop, chef = dbx
    kit = kit_of(pg, mine, prop, chef)
    assert [e["name"] for e in brand_kits.named(kit, "Marco taps THE  APP.", pg)] == \
        ["Marco", "Gygler App"]                              # the person first
    assert brand_kits.named(kit, "A hand taps the tablet screen", pg)[0]["role"] == "product"
    assert brand_kits.named(kit, "the apple on the counter; tablet screens", pg) == []
    assert brand_kits.named(None, "the app", pg) == []


def test_a_scene_that_names_a_kit_product_is_held_to_its_photo_as_a_product(dbx):
    pg, mine, prop, chef = dbx
    kit = kit_of(pg, mine, prop, chef)
    cid = preprod.save_concept({"title": "t", "shots": [{"n": 1, "source": "AI",
                                                         "prompt": SCENE}]},
                               dsn=pg, account_id=mine)
    with project_context.kit_active(kit):
        refs = api._attach_scene_refs(cid, [DISH], mine, idea="the Gygler ad")
    # the person's pick first, then character before prop
    assert refs == [DISH, CHEF, APP]
    shot = preprod.get_concept(cid, dsn=pg, account_id=mine)["shots"][0]
    assert shot["ref_roles"] == {CHEF: "subject", APP: "product"}


def test_no_kit_or_nothing_named_attaches_exactly_what_it_did(dbx):
    pg, mine, prop, chef = dbx
    cid = preprod.save_concept({"title": "t", "shots": [{"n": 1, "source": "AI",
                                                         "prompt": "(0-3s) A dish. (3-6s) Hands."}]},
                               dsn=pg, account_id=mine)
    before = api._attach_scene_refs(cid, [DISH], mine, idea="a dish")
    shot = preprod.get_concept(cid, dsn=pg, account_id=mine)["shots"][0]
    assert before == [DISH] and "ref_roles" not in shot
    with project_context.kit_active(kit_of(pg, mine, prop, chef)):
        again = api._attach_scene_refs(cid, [DISH], mine, idea="a dish")
    assert again == before
    assert "ref_roles" not in preprod.get_concept(cid, dsn=pg, account_id=mine)["shots"][0]


def test_a_timed_part_that_names_the_product_is_held_to_it(dbx, monkeypatch):
    pg, mine, prop, chef = dbx
    kit = kit_of(pg, mine, prop)
    cid = preprod.save_concept({"title": "t", "shots": [{"n": 1, "source": "AI",
                                                         "prompt": SCENE,
                                                         "refs": [DISH, APP]}]},
                               dsn=pg, account_id=mine)
    brand_kits.pick_for_concepts([cid], kit["id"], pg, account_id=mine)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    # a planner that put the app on the last shot only, not on the one that
    # says "tablet screen" (a ref on NO shot is timeline.keep's to spread)
    monkeypatch.setattr(timeline, "fallback", lambda scene, windows, refs: {
        "continuity": "", "parts": [timeline._part(n, w, w["text"], r)
                                    for (n, w), r in zip(enumerate(windows, start=1),
                                                         ([DISH], [DISH], [APP]))]})
    tl = timeline.ensure(cid, db_path=pg, account_id=mine)
    assert [p["refs"] for p in tl["parts"]] == [[DISH], [DISH, APP], [APP]]


def test_part_refs_only_narrow_the_scenes_set_and_leave_the_rest_alone():
    elements = [{"kind": "prop", "id": 1, "name": "Gygler App", "slug": "gygler-app",
                 "role": "product", "names": ["Gygler App", "the app"]}]
    parts = [{"n": 1, "text": "Hands garnish", "prompt": "", "refs": []},
             {"n": 2, "text": "A hand taps the app", "prompt": "", "refs": [DISH]}]
    out = brand_kits.part_refs(parts, [APP, DISH], elements)
    assert out[0] is parts[0]                               # untouched, the same object
    assert out[1]["refs"] == [APP, DISH]                    # in the scene's order
    # a product the scene is not held to is never added to a part
    assert brand_kits.part_refs(parts, [DISH], elements) == parts
    assert brand_kits.part_refs(parts, [APP], []) is parts


def test_an_attached_product_changes_the_price_hash():
    shot = {"prompt": SCENE, "refs": [DISH]}
    held = {"prompt": SCENE, "refs": [DISH, APP]}
    assert pricing.content_hash(shot) != pricing.content_hash(held)
