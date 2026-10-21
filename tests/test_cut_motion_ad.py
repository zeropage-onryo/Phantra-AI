"""A motion ad from a brief (src/cut/motion_ad.py): the brain's script is
checked, placed as a cut of flat brand colours and graphics, and filed under
the studio project so its brand kit reaches the export. The model is replaced
at its seam everywhere here; nothing renders and nothing is charged.
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, brand_kits, charge, preprod, projects
from src.cut import doc as d
from src.cut import motion_ad as ma
from src.cut import store, validate

client = TestClient(app)

KIT = {"palette": [{"hex": "#F7931E", "role": "primary"}, {"hex": "#FFF4E6", "role": "background"},
                   {"hex": "#8A4B08", "role": "text"}],
       "identity": {"tagline": "Get a Gyg, stay for good.", "url": "Gygler.com"},
       "voice": {"tone": "Friendly and brisk."}}

SCRIPT = {"title": "Meet Gygler", "beats": [
    {"headline": "Managing talent shouldn't feel like this.", "big_word": "", "card": None,
     "card_caption": "", "label": "", "background": "primary", "seconds": 3},
    {"headline": "Find the right talent.", "big_word": "find", "card": 1,
     "card_caption": "Alex R. · Line cook", "label": "", "background": "background", "seconds": 4},
    {"headline": "See the rate before you commit.", "big_word": "rate", "card": None,
     "card_caption": "", "label": "$24 / hr", "background": "background", "seconds": 4},
    {"headline": "Get a Gyg, stay for good.", "big_word": "", "card": None, "card_caption": "",
     "label": "", "background": "primary", "seconds": 3}]}


def stub(script=SCRIPT, seen=None):
    def model(prompt, *, account_id):
        if seen is not None:
            seen.append(prompt)
        return script
    return model


# --------------------------------------------------------------------------
# checked against reality
# --------------------------------------------------------------------------

def test_the_script_is_fitted_to_the_length_and_every_fix_is_said():
    raw = {"title": "x", "beats": [
        {"headline": " ".join(["word"] * 14), "big_word": "superlongbackgroundwordthatoverflows",
         "card": 9, "card_caption": "c", "label": "", "background": "neon", "seconds": 20},
        {"headline": "", "big_word": "", "card": None, "card_caption": "", "label": "",
         "background": "background", "seconds": 3},
        {"headline": "Two.", "big_word": "two", "card": None, "card_caption": "", "label": "",
         "background": "primary", "seconds": 2}]}
    plan = ma.clean(raw, 12, n_cards=1)
    first = plan["beats"][0]
    assert len(first["headline"].split()) == ma.HEADLINE_WORDS_MAX
    assert first["big_word"] == "" and first["card"] is None and first["background"] == "background"
    assert len(plan["beats"]) == 2                                  # the empty beat is left out
    assert abs(sum(b["seconds"] for b in plan["beats"]) - 12) < 0.05
    said = " ".join(plan["warnings"])
    for bit in ("shortened", "too long", "screenshot 9", "left out", "fitted to 12s"):
        assert bit in said, bit


def test_nothing_usable_is_a_plain_refusal():
    with pytest.raises(ma.MotionAdError, match="no beats"):
        ma.clean({"beats": []}, 20, 0)
    with pytest.raises(ma.MotionAdError, match="Nothing was made or charged"):
        ma.write_beats("x", None, 20, [], account_id=None,
                       model=lambda p, account_id: (_ for _ in ()).throw(ValueError("bad json")))


def test_the_prompt_carries_the_brief_the_brand_and_the_numbered_screenshots():
    seen = []
    kit = {"id": 1, "account_id": 1, "name": "Gygler", "assets": [],
           "spec": brand_kits.clean_spec(KIT)}
    ma.write_beats("A launch ad for Gygler", kit, 20, [{"handle": "asset:3", "name": "talent.png"}],
                   account_id=None, model=stub(seen=seen))
    prompt = seen[0]
    assert "A launch ad for Gygler" in prompt and "BRAND KIT “Gygler”" in prompt
    assert "Friendly and brisk." in prompt and "1. talent.png" in prompt
    assert "Website: Gygler.com" in prompt and "{" not in prompt.replace("{}", "")
    assert "4 to 8 beats" in prompt
    plain = ma.build_prompt("x", None, 20, [])
    assert "No brand kit" in plain and "no beat shows a card" in plain


# --------------------------------------------------------------------------
# placing it
# --------------------------------------------------------------------------

def test_the_layout_is_one_background_per_beat_and_a_track_per_kind():
    colours = ma.palette({"spec": brand_kits.clean_spec(KIT)})
    plan = ma.clean(SCRIPT, 14, 1)
    bgs = {colours["primary"]: "asset:10", colours["background"]: "asset:11"}
    doc = ma.layout(plan, size=(1280, 720), fps=30, colours=colours, backgrounds=bgs,
                    cards=["asset:3"])
    v1 = d.track(doc, "V1")["clips"]
    assert [c["media"] for c in v1] == ["asset:10", "asset:11", "asset:11", "asset:10"]
    assert [c["at"] for c in v1] == [0, 90, 210, 330] and doc["duration"] == 420
    kinds = {t["id"]: [i["type"] for i in t["items"]] for t in doc["tracks"] if t["kind"] == "graphic"}
    assert kinds == {"G1": ["background_word", "background_word"], "G2": ["headline"] * 4,
                     "G3": ["card"], "G4": ["label"]}
    head = d.track(doc, "G2")["items"]
    # on orange the type is the cream; on cream it is the orange; beside a card it moves left
    assert head[0]["color"] == "#FFF4E6" and head[1]["color"] == "#F7931E"
    assert head[1]["position"] == "left" and head[2]["position"] == "center"
    card = d.track(doc, "G3")["items"][0]
    assert card["media"] == "asset:3" and card["text"] == "Alex R. · Line cook"
    media = {h: {"frames": 18000, "video": True, "audio": False, "still": True,
                 "width": 400, "height": 300} for h in ("asset:10", "asset:11", "asset:3")}
    validate.validate(doc, media)


def test_a_number_the_brief_never_gave_is_flagged_not_dropped():
    raw = {"title": "x", "beats": [
        {"headline": "Book in 30 seconds.", "big_word": "", "card": None, "card_caption": "",
         "label": "4.9 Stars", "background": "background", "seconds": 4},
        {"headline": "From $24 an hour.", "big_word": "", "card": None, "card_caption": "",
         "label": "", "background": "background", "seconds": 4}]}
    plan = ma.clean(raw, 8, 0, facts="Shifts from $24 an hour. Book a shift in 30 seconds.")
    said = " ".join(plan["warnings"])
    assert "“4.9 Stars” has 4.9" in said
    assert "30" not in said.replace("4.9", "") and "24" not in said   # both were in the brief
    assert plan["beats"][0]["label"] == "4.9 Stars"                     # advised, never removed
    assert ma.unsourced_numbers("$26 / hr", "rate before you commit") == ["26"]


def test_a_label_on_a_primary_beat_gets_a_pill_that_shows():
    colours = ma.palette({"spec": brand_kits.clean_spec(KIT)})
    plan = ma.clean({"title": "x", "beats": [
        {"headline": "Go.", "big_word": "", "card": None, "card_caption": "", "label": "Gygler.com",
         "background": "primary", "seconds": 4}]}, 4, 0)
    doc = ma.layout(plan, size=(1280, 720), fps=30, colours=colours,
                    backgrounds={colours["primary"]: "asset:1"}, cards=[])
    label = d.track(doc, "G4")["items"][0]
    assert label["pill"] == "#FFF4E6" and label["color"] == "#F7931E"


def test_type_always_reads_on_its_background():
    assert ma.ink_on("#111214", ma.PLAIN) == "#F2F1EE"
    assert ma.ink_on("#F2F1EE", ma.PLAIN) == "#111214"
    assert ma.ink_on("#777777", {"primary": "#787878"}) == "#FFFFFF"   # nothing reads: white


# --------------------------------------------------------------------------
# the cut, end to end
# --------------------------------------------------------------------------

@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    store.init(pg)
    brand_kits.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "bk")
    mine = accounts.upsert_account("ma-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("ma-theirs", "Theirs", "#fff", dsn=pg)
    return pg, mine, theirs, tmp_path


def test_make_files_a_cut_under_the_project_and_its_kit_reaches_it(dbx):
    pg, mine, _, tmp = dbx
    kit = brand_kits.create("Gygler", KIT, pg, account_id=mine)
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    project = projects.get(project["id"], pg, account_id=mine)
    made = ma.make("A launch ad", account_id=mine, media_dir=tmp / "media", project=project,
                   seconds=14, aspect="16:9", cards=[], dsn=pg,
                   model=stub({**SCRIPT, "beats": [{**b, "card": None} for b in SCRIPT["beats"]]}))
    cut = store.get_project(made["cut"]["id"], account_id=mine, dsn=pg)
    assert cut["studio_project_id"] == project["id"] and cut["concept_id"] is None
    assert brand_kits.for_cut(cut, pg, account_id=mine)["id"] == kit["id"]
    head = store.head(cut["timeline_key"], account_id=mine, dsn=pg)
    assert head["author"] == "agent" and head["op_summary"] == "motion ad: 4 beats"
    assert head["doc"]["size"] == [1280, 720]
    # the two brand colours were filed once each as stills in the bin
    bin_rows = store.media_bin(account_id=mine, dsn=pg)
    assert sorted(r["filename"] for r in bin_rows) == ["background-f7931e.png",
                                                       "background-fff4e6.png"]
    # no project: plain colours, and the cut has no kit
    plain = ma.make("A launch ad", account_id=mine, media_dir=tmp / "media", seconds=14,
                    cards=[], dsn=pg, model=stub(SCRIPT_NO_CARDS))
    assert plain["brand_kit"] is None
    assert brand_kits.for_cut(store.get_project(plain["cut"]["id"], account_id=mine, dsn=pg),
                              pg, account_id=mine) is None


SCRIPT_NO_CARDS = {**SCRIPT, "beats": [{**b, "card": None} for b in SCRIPT["beats"]]}


@pytest.fixture
def signed_in(dbx, monkeypatch):
    pg, mine, theirs, tmp = dbx
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@e.com",
                                                               "display_name": "T"})
    monkeypatch.setattr(charge, "create_refusal_code", lambda account_id: None)
    monkeypatch.setattr(ma, "_model", stub(SCRIPT_NO_CARDS))
    import app.cut_routes as routes
    monkeypatch.setattr(routes, "MEDIA_DIR", tmp / "media")
    app.dependency_overrides[auth.current_account_id] = lambda: mine
    yield dbx
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _wait(job_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("the job never finished")


def test_the_route_makes_the_cut_and_refuses_what_is_not_the_callers(signed_in, monkeypatch):
    pg, mine, theirs, _ = signed_in
    project = projects.create("Launch", "", pg, account_id=mine)
    got = client.post("/api/cut/motion-ad", json={"brief": "A launch ad", "seconds": 14,
                                                 "project_id": project["id"]}).json()
    job = _wait(got["job_id"])
    assert job["status"] == "done", job
    assert job["beats"] == 4 and job["title"] == "Meet Gygler"
    opened = client.get(f"/api/cut/projects/{job['cut_id']}").json()
    assert [t["id"] for t in opened["head"]["doc"]["tracks"]] == ["V1", "G1", "G2", "G4"]

    theirs_project = projects.create("Theirs", "", pg, account_id=theirs)
    assert client.post("/api/cut/motion-ad", json={
        "brief": "x", "project_id": theirs_project["id"]}).status_code == 404
    assert client.post("/api/cut/motion-ad", json={
        "brief": "x", "cards": ["asset:999"]}).json()["error"]["code"] == "not_a_still"
    assert client.post("/api/cut/motion-ad", json={"brief": "x", "seconds": 300}).status_code == 422
    # an account the Create gate refuses is refused before any job or model call
    monkeypatch.setattr(charge, "create_refusal_code",
                        lambda account_id: ("subscribe_or_top_up", "no plan"))
    assert client.post("/api/cut/motion-ad", json={"brief": "x"}).status_code == 402
