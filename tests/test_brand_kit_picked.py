"""A brand kit picked in the composer with no project (2026-10-22, Mike: "i
don't want to always save it as a project, sometimes i just want to generate
an ad"). The pick lasts for the conversation (the draft keeps it, New session
clears it) and reaches Vesper, stills and the scenes written there -- whose
keyframes, clips, quotes and editor exports then read it through
`brand_kits.for_concept`. A project's own pick always wins, and a kit is
never another account's.
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import (
    accounts,
    assistant_store,
    brand_kits,
    charge,
    creative_guide,
    entities,
    nano_banana,
    preprod,
    project_context,
    projects,
    scene_chain,
    shootgen,
)

client = TestClient(app)
KIT = {"identity": {"positioning": "Human logistics for hospitality", "url": "gygler.com"},
       "palette": [{"hex": "#FF880B", "role": "primary", "name": "Gygler orange"}],
       "look": {"style": "Light, warm and clean.", "banned": ["neon"]},
       "voice": {"tone": "Direct, warm.", "use": ["Gyg"]}}


@pytest.fixture
def k(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    brand_kits.init(pg)
    projects.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("bkp-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("bkp-theirs", "Theirs", "#fff", dsn=pg)
    kit = brand_kits.create("Gygler", KIT, pg, account_id=mine)
    other = brand_kits.create("Northwind", {"look": {"style": "Navy."}}, pg, account_id=theirs)
    return {"pg": pg, "mine": mine, "theirs": theirs, "kit": kit, "other": other}


def _scene(k, project_id=None):
    cid = preprod.save_concept({"title": "S", "hook": "", "logline": "",
                                "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN",
                                           "desc": "d", "prompt": "A cook plates a dish."}]},
                               dsn=k["pg"], account_id=k["mine"])
    if project_id:
        projects.tag_concepts([cid], project_id, k["pg"], account_id=k["mine"])
    return cid


# -- the conversation keeps the pick ------------------------------------------

def test_the_draft_keeps_a_kit_id_and_nothing_else_there():
    assert assistant_store._clean_draft({"brand_kit_id": 7})["brand_kit_id"] == 7
    for bad in (None, "7", 0, -2, True, 1.5):
        assert assistant_store._clean_draft({"brand_kit_id": bad})["brand_kit_id"] is None
    assert assistant_store.EMPTY_DRAFT["brand_kit_id"] is None


# -- the writer --------------------------------------------------------------

def test_the_writer_reads_a_picked_kit_only_when_there_is_no_project(k):
    plain = shootgen.project_brief()
    with project_context.kit_active(k["kit"]):
        picked = shootgen.project_brief()
    assert picked.startswith(plain) and "BRAND KIT “Gygler”" in picked
    project = projects.create("Launch", "the brief", k["pg"], account_id=k["mine"])
    with project_context.active(project), project_context.kit_active(k["kit"]):
        inside = shootgen.project_brief()
    assert "BRAND KIT" not in inside and "the brief" in inside     # the project's own block


# -- a scene keeps the kit ----------------------------------------------------

def test_a_scene_outside_a_project_renders_under_its_picked_kit(k):
    cid = _scene(k)
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"]) is None
    brand_kits.pick_for_concepts([cid], k["kit"]["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"])["id"] == k["kit"]["id"]
    # another account reads nothing through the same scene id
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["theirs"]) is None


def test_a_project_decides_for_its_scenes_even_with_no_kit(k):
    project = projects.create("Launch", "", k["pg"], account_id=k["mine"])
    cid = _scene(k, project["id"])
    brand_kits.pick_for_concepts([cid], k["kit"]["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"]) is None
    second = brand_kits.create("Second", {}, k["pg"], account_id=k["mine"])
    projects.set_brand_kit(project["id"], second["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"])["id"] == second["id"]


def test_another_accounts_kit_cannot_be_picked_for_a_scene(k):
    cid = _scene(k)
    with pytest.raises(brand_kits.KitError):
        brand_kits.pick_for_concepts([cid], k["other"]["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"]) is None


# -- Vesper ------------------------------------------------------------------

def test_vesper_works_under_the_picked_kit_unless_a_project_has_one(k):
    conv = creative_guide.Conversation.model_validate(
        {"messages": [{"role": "user", "content": "an ad for the summer launch"}]})
    assert api._guide_kit(None, conv, k["mine"]) is None              # names no kit
    assert api._guide_kit(None, conv, k["mine"], picked=k["kit"])["id"] == k["kit"]["id"]
    second = brand_kits.create("Second", {}, k["pg"], account_id=k["mine"])
    project = projects.create("Launch", "", k["pg"], account_id=k["mine"])
    projects.set_brand_kit(project["id"], second["id"], k["pg"], account_id=k["mine"])
    project = projects.get(project["id"], k["pg"], account_id=k["mine"])
    assert api._guide_kit(project, conv, k["mine"], picked=k["kit"])["id"] == second["id"]


# -- the routes ----------------------------------------------------------------

@pytest.fixture
def as_mine(k, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **kw: None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key=None: object())
    app.dependency_overrides[auth.current_account_id] = lambda: k["mine"]
    yield k
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _wait(job_id):
    deadline = time.time() + 10
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError("job never finished")


def test_a_still_with_a_picked_kit_is_dressed_and_its_scene_keeps_the_kit(as_mine, monkeypatch):
    k = as_mine
    monkeypatch.setattr(shootgen, "reference_block", lambda **kw: "")
    monkeypatch.setattr(api, "_enhance_generate_prompt", lambda c, p, **kw: f"ENHANCED[{p}]")
    prompts = []

    def fake(prompt, reference_image=None, db_path=None, **kw):
        prompts.append(prompt)
        return {"ok": True, "media_url": "/renders/frame.png"}

    monkeypatch.setattr(nano_banana, "generate_from_prompt", fake)
    job = _wait(client.post("/api/generate/run", data={
        "prompt": "a summer ad", "output": "image",
        "brand_kit_id": str(k["kit"]["id"])}).json()["job_id"])
    assert job["status"] == "done", job
    assert "BRAND LOOK (Gygler)" in prompts[0]
    assert brand_kits.for_concept(job["ref_id"], k["pg"], account_id=k["mine"])["id"] == k["kit"]["id"]
    # no pick: as before
    job = _wait(client.post("/api/generate/run", data={
        "prompt": "a summer ad", "output": "image"}).json()["job_id"])
    assert "BRAND LOOK" not in prompts[1]
    assert brand_kits.for_concept(job["ref_id"], k["pg"], account_id=k["mine"]) is None
    # another account's kit is a 404, before any job
    r = client.post("/api/generate/run", data={"prompt": "x", "output": "image",
                                               "brand_kit_id": str(k["other"]["id"])})
    assert r.status_code == 404


def test_a_scene_written_under_a_picked_kit_hears_it_and_keeps_it(as_mine, monkeypatch):
    k = as_mine
    cid = _scene(k)
    heard = []

    def fake_run(idea, **kw):
        heard.append(shootgen.project_brief())
        return {"scenes": [{"concept_id": cid}], "notes": []}

    monkeypatch.setattr(scene_chain, "run", fake_run)
    r = client.post("/api/scenes/run", data={"idea": "a summer ad", "count": "1",
                                             "brand_kit_id": str(k["kit"]["id"])})
    assert r.status_code == 200, r.text
    job = _wait(r.json()["job_id"])
    assert job["status"] == "done", job
    assert "BRAND KIT “Gygler”" in heard[0]
    assert brand_kits.for_concept(cid, k["pg"], account_id=k["mine"])["id"] == k["kit"]["id"]
    r = client.post("/api/scenes/run", data={"idea": "x", "brand_kit_id": str(k["other"]["id"])})
    assert r.status_code == 404
