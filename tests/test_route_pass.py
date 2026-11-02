"""What the route pass of the QA review found (2026-11-02, docs/qa/2026-11-02
03-backend-e2e.md E3, E6, E11, E12 and 02-studio-ui.md T10).

- E3: another workspace's element photo could be put on a scene through the
  studio's two refs routes (the connector's `write_scene` already refused).
- E6: a place whose describe call failed was never listed.
- T10: an element drew a paid reference sheet whenever the form left `sheet`
  out.
- E11: the whole route map was public on production.
- E12: a 1 MB title, folder, workflow or prompt was stored.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import api as api_mod
from app import auth
from app import main as main_mod
from app.main import app
from src import accounts, entities, preprod, workflows

client = TestClient(app)
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    stub = {"id": 1, "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)
    monkeypatch.setattr(auth, "current_account",
                        lambda request, user=None: {"slug": "a", "display_name": "A"})


@pytest.fixture(autouse=True)
def no_real_rag_store(monkeypatch):
    def refused(db_url=None):
        raise ConnectionError("no rag store in tests")
    monkeypatch.setattr(api_mod.rag, "connect", refused)


@pytest.fixture
def two_workspaces(pg, monkeypatch):
    """Workspaces A (the caller) and B, each with a character."""
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    workflows.init(pg)
    a = accounts.upsert_account("qa-a", "A", dsn=pg)
    b = accounts.upsert_account("qa-b", "B", dsn=pg)
    entities.add_character("QA Hero", photo_count=1, dsn=pg, account_id=a)
    entities.add_character("QAB Hero", photo_count=1, dsn=pg, account_id=b)
    app.dependency_overrides[auth.current_account_id] = lambda: a
    yield pg, a, b
    app.dependency_overrides.pop(auth.current_account_id, None)


def _scene(pg, account_id, refs):
    return preprod.save_concept(
        {"title": "QA", "shots": [{"n": 1, "prompt": "(0-4s) a rider passes a wall",
                                   "seconds": 4, "refs": refs}]},
        dsn=pg, account_id=account_id)


OURS = "/characters/qa-hero/photo/a.png"
THEIRS = "/characters/qab-hero/photo/qaB.png"


# --- E3: another workspace's photo is not put on a scene -----------------------

def test_the_scene_refs_route_refuses_another_workspaces_photo(two_workspaces):
    pg, a, _ = two_workspaces
    sid = _scene(pg, a, [OURS])
    res = client.post(f"/api/concepts/{sid}/refs", json={"refs": [OURS, THEIRS]})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "not_your_reference"
    assert preprod.get_concept(sid, dsn=pg, account_id=a)["shots"][0]["refs"] == [OURS]
    # its own photos, a pasted link and the shared bin still go on
    ok = client.post(f"/api/concepts/{sid}/refs",
                     json={"refs": [OURS, "https://example.com/a.jpg", "/refs/abc.jpg"]})
    assert ok.status_code == 200


def test_the_canvas_refs_route_refuses_another_workspaces_photo(two_workspaces):
    pg, a, _ = two_workspaces
    sid = _scene(pg, a, [OURS])
    res = client.put(f"/api/concepts/{sid}/shots/1/refs", json={"refs": [OURS, THEIRS]})
    assert res.status_code == 403
    assert preprod.get_concept(sid, dsn=pg, account_id=a)["shots"][0]["refs"] == [OURS]


def test_a_ref_the_scene_already_carries_is_never_refused(two_workspaces):
    """A renamed or deleted element leaves its old ref on the scene, and the
    canvas re-sends the whole list on every save: only NEW refs are judged."""
    pg, a, _ = two_workspaces
    sid = _scene(pg, a, [OURS, THEIRS])
    res = client.put(f"/api/concepts/{sid}/shots/1/refs", json={"refs": [THEIRS, OURS]})
    assert res.status_code == 200


def test_a_slug_both_workspaces_use_is_the_callers(two_workspaces):
    pg, a, _ = two_workspaces
    entities.add_character("QAB Hero", photo_count=1, dsn=pg, account_id=a)
    sid = _scene(pg, a, [OURS])
    assert client.post(f"/api/concepts/{sid}/refs",
                       json={"refs": [OURS, THEIRS]}).status_code == 200


# --- E6: a place whose describe failed is still saved ---------------------------

def test_a_place_whose_describe_failed_is_listed(two_workspaces, tmp_path, monkeypatch):
    import src.locations as locations_mod
    pg, a, _ = two_workspaces
    monkeypatch.setattr(api_mod, "LOCATIONS_DIR", tmp_path / "locations")
    monkeypatch.setattr(api_mod, "_gemini_key", lambda a=None: "k")
    monkeypatch.setattr(api_mod, "_gate_or_refuse", lambda account_id: None)
    monkeypatch.setattr(api_mod, "_mirror_or_refuse", lambda *a, **k: None)
    monkeypatch.setattr(api_mod, "_keeps_no_folder", lambda *a, **k: False)

    def fails(*a, **k):
        raise RuntimeError("model said no")
    monkeypatch.setattr(locations_mod, "describe_location", fails)
    res = client.post("/api/assets/locations", data={"name": "garage", "sheet": "0"},
                      files=[("photos", ("a.png", TINY_PNG, "image/png"))])
    assert res.status_code == 200 and res.json()["described"] is False
    assert preprod.get_location_by_name("garage", dsn=pg, account_id=a) is not None


def test_a_failed_describe_keeps_an_earlier_description(two_workspaces, tmp_path,
                                                        monkeypatch):
    import src.locations as locations_mod
    pg, a, _ = two_workspaces
    preprod.add_location("garage", {"space": "a concrete garage"}, photo_count=1,
                         dsn=pg, account_id=a)
    monkeypatch.setattr(api_mod, "LOCATIONS_DIR", tmp_path / "locations")
    monkeypatch.setattr(api_mod, "_gemini_key", lambda a=None: "k")
    monkeypatch.setattr(api_mod, "_gate_or_refuse", lambda account_id: None)
    monkeypatch.setattr(api_mod, "_mirror_or_refuse", lambda *a, **k: None)
    monkeypatch.setattr(api_mod, "_keeps_no_folder", lambda *a, **k: False)
    monkeypatch.setattr(locations_mod, "describe_location",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no")))
    client.post("/api/assets/locations", data={"name": "garage", "sheet": "0"},
                files=[("photos", ("b.png", TINY_PNG, "image/png"))])
    kept = preprod.get_location_by_name("garage", dsn=pg, account_id=a)
    assert kept["description"] == {"space": "a concrete garage"}


# --- T10: no sheet unless asked ---------------------------------------------

def test_a_form_without_sheet_draws_none():
    class Form(dict):
        pass
    assert api_mod._sheet_wanted(Form()) is False
    assert api_mod._sheet_wanted(Form(sheet="1")) is True
    assert api_mod._sheet_wanted(Form(sheet="0")) is False


# --- E11: the route map is not public in production -------------------------

def test_the_api_docs_are_off_unless_dev_tools():
    off = main_mod.docs_urls(False)
    assert off == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert main_mod.docs_urls(True)["openapi_url"] == "/openapi.json"
    built = {"docs_url": app.docs_url, "redoc_url": app.redoc_url, "openapi_url": app.openapi_url}
    assert built == main_mod.docs_urls(main_mod.DEV_TOOLS)


# --- E12: a megabyte is not a title ------------------------------------------

BIG = "x" * 1_000_000


def test_a_megabyte_title_folder_or_prompt_is_refused(two_workspaces):
    pg, a, _ = two_workspaces
    sid = _scene(pg, a, [OURS])
    assert client.post("/api/projects", json={"title": BIG}).status_code == 422
    assert client.patch("/api/projects/1", json={"title": BIG}).status_code == 422
    assert client.patch("/api/assets/generated/1", json={"folder": BIG}).status_code == 422
    assert client.post(f"/api/concepts/{sid}/shots/1/prompt",
                       json={"prompt": BIG}).status_code == 422
    assert client.post("/api/workflows", json={"name": BIG}).status_code == 422
    graph = {"nodes": [{"id": 1, "properties": {"text": BIG}}], "links": []}
    assert client.post("/api/workflows", json={"name": "w", "graph": graph}).status_code == 422
    assert client.put("/api/workflows/1", json={"graph": graph}).status_code == 422


def test_ordinary_sizes_still_pass(two_workspaces):
    ok = client.post("/api/workflows", json={"name": "A canvas",
                                             "graph": {"nodes": [], "links": []}})
    assert ok.status_code == 200
    assert len(json.dumps({"title": "t" * 200})) < api_mod.MAX_TITLE + 20
