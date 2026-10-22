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


# --------------------------------------------------------------------------
# redo one beat
# --------------------------------------------------------------------------

def _made(kit_spec=KIT):
    """A made ad, laid out as make() lays it, with fake background handles."""
    kit = {"name": "Gygler", "spec": brand_kits.clean_spec(kit_spec)}
    colours = ma.palette(kit)
    handles = {h: f"asset:{900 + i}" for i, h in enumerate(sorted(set(colours.values())))}
    plan = ma.clean(SCRIPT, 14, 1)
    doc = ma.layout(plan, size=(1280, 720), fps=30, colours=colours, backgrounds=handles,
                    cards=["asset:7"])
    return doc, kit, colours, handles


def _flat(handles):
    by_handle = {h: c for c, h in handles.items()}
    return lambda handle: by_handle.get(handle)


NEW_BEAT = {"headline": "Hire in an afternoon.", "big_word": "hire", "card": 1,
            "card_caption": "", "label": "Gygler.com", "background": "primary", "seconds": 9}


def test_beats_are_read_from_the_cut_as_it_is():
    doc, *_ = _made()
    beats = ma.beats_of(doc)
    assert [(b["start"], b["end"]) for b in beats] == [(0, 90), (90, 210), (210, 330), (330, 420)]
    assert {g["type"] for _, g in beats[1]["items"]} == {"background_word", "headline", "card"}
    assert ma.beat_at(doc, 100)[0] == 2 and ma.card_handles(doc) == ["asset:7"]
    with pytest.raises(ma.MotionAdError, match="put the playhead on a beat"):
        ma.beat_at(doc, 999)


def test_the_prompt_shows_the_whole_ad_and_marks_the_beat():
    doc, kit, *_ = _made()
    prompt = ma.build_beat_prompt(doc, 2, kit, "make it about speed")
    assert ">> 2. (4.0s) headline “Find the right talent.”; big word FIND; card 1" in prompt
    assert "   3. (4.0s) headline “See the rate before you commit.”" in prompt
    assert "make it about speed" in prompt and "keep \"seconds\" at 4" in prompt
    assert "Friendly and brisk." in prompt and "{" not in prompt.replace('{"', "")


def test_redo_replaces_only_that_beat_and_swaps_its_flat_background(monkeypatch):
    from src.cut import projects as cut_projects
    doc, kit, colours, handles = _made()
    seen = []
    made = ma.redo_beat(doc, 100, "faster", kit=kit, account_id=1,
                        backgrounds_for=lambda used: handles,
                        flat_colour_of=_flat(handles), model=stub(NEW_BEAT, seen))
    assert made["n"] == 2 and made["warnings"] == []
    assert made["summary"] == "motion ad: beat 2 rewritten -- Hire in an afternoon."
    new = cut_projects.apply_all(doc, made["ops"], media=None)
    beats = ma.beats_of(new)
    texts = {g["type"]: g for _, g in beats[1]["items"]}
    assert texts["headline"]["text"] == "Hire in an afternoon."
    assert texts["background_word"]["text"] == "HIRE" and texts["card"]["media"] == "asset:7"
    assert texts["label"]["text"] == "Gygler.com"
    assert all(90 <= g["start"] and g["end"] <= 210 for _, g in beats[1]["items"])
    # the background turned primary; every other beat is exactly as it was
    assert beats[1]["clip"]["media"] == handles[colours["primary"]]
    for i in (0, 2, 3):
        old = ma.beats_of(doc)[i]
        assert beats[i]["clip"]["media"] == old["clip"]["media"]
        assert sorted(g["text"] for _, g in beats[i]["items"]) == \
            sorted(g["text"] for _, g in old["items"])
    assert new["duration"] == doc["duration"]


def test_a_footage_clip_under_the_beat_is_never_replaced():
    doc, kit, colours, handles = _made()
    doc["tracks"][0]["clips"][1]["media"] = "gen:55"             # a real clip, not a flat still
    made = ma.redo_beat(doc, 100, "", kit=kit, account_id=1,
                        backgrounds_for=lambda used: handles,
                        flat_colour_of=_flat(handles), model=stub(NEW_BEAT))
    assert not any(o["op"] == "overwrite" for o in made["ops"])


def test_the_same_colour_keeps_its_still():
    doc, kit, colours, handles = _made()
    made = ma.redo_beat(doc, 100, "", kit=kit, account_id=1, backgrounds_for=lambda u: handles,
                        flat_colour_of=_flat(handles),
                        model=stub({**NEW_BEAT, "background": "background"}))
    assert not any(o["op"] == "overwrite" for o in made["ops"])


def test_a_made_up_number_in_the_new_beat_is_flagged():
    doc, kit, _, handles = _made()
    made = ma.redo_beat(doc, 100, "", kit=kit, account_id=1, backgrounds_for=lambda u: handles,
                        flat_colour_of=_flat(handles),
                        model=stub({**NEW_BEAT, "label": "4.9 stars"}))
    assert any("4.9" in w and "beat 2" in w for w in made["warnings"])


def test_the_redo_route_keeps_one_undoable_version(signed_in, monkeypatch):
    pg, mine, theirs, tmp = signed_in
    made = client.post("/api/cut/motion-ad", json={"brief": "A launch ad", "seconds": 14})
    job = _wait(made.json()["job_id"])
    cut = job["cut_id"]
    project = store.get_project(cut, account_id=mine, dsn=pg)
    head = store.head(project["timeline_key"], account_id=mine, dsn=pg)
    url = f"/api/cut/projects/{cut}/motion-ad/beat"

    assert client.post(url, json={"base_id": head["id"] + 99, "frame": 100}).status_code == 409
    assert client.post(url, json={"base_id": head["id"], "frame": 99999}).json()["error"]["code"] \
        == "no_beat"
    monkeypatch.setattr(ma, "_beat_model", stub({**NEW_BEAT, "card": None}))
    done = _wait(client.post(url, json={"base_id": head["id"], "frame": 100,
                                        "note": "faster"}).json()["job_id"])
    assert done["status"] == "done" and done["n"] == 2
    now = store.head(project["timeline_key"], account_id=mine, dsn=pg)
    assert now["id"] == done["head_id"] and now["author"] == "agent"
    assert now["op_summary"].startswith("motion ad: beat 2 rewritten")
    assert any(g.get("text") == "Hire in an afternoon." for t in now["doc"]["tracks"]
               for g in t.get("items") or [])
    # the beat asked for primary: its flat still was swapped, found by its bin row
    v1 = next(t for t in now["doc"]["tracks"] if t["id"] == "V1")
    under = next(c for c in v1["clips"] if c["at"] <= 100 < d.clip_end(c))
    assert ma.flat_colour(under["media"], account_id=mine, dsn=pg) == "#F2F1EE"
    assert ma.flat_colour("gen:5", account_id=mine, dsn=pg) is None
    undone = client.post(f"/api/cut/projects/{cut}/undo").json()
    assert undone["head"]["id"] == head["id"]

    monkeypatch.setattr(charge, "create_refusal_code",
                        lambda account_id: ("subscribe_or_top_up", "add credits"))
    assert client.post(url, json={"base_id": head["id"], "frame": 100}).status_code == 402
    monkeypatch.setattr(charge, "create_refusal_code", lambda account_id: None)
    app.dependency_overrides[auth.current_account_id] = lambda: theirs
    assert client.post(url, json={"base_id": head["id"], "frame": 100}).status_code == 404


# --------------------------------------------------------------------------
# footage beats
# --------------------------------------------------------------------------

CLIP = {"handle": "gen:41", "name": "Barista pulls a shot", "frames": 75}   # 2.5s
FOOTAGE_SCRIPT = {"title": "Meet Gygler", "beats": [
    {**SCRIPT["beats"][0], "clip": None},
    {"headline": "Real staff, on shift tonight.", "big_word": "", "card": None, "clip": 1,
     "card_caption": "", "label": "", "background": "background", "seconds": 4},
    {**SCRIPT["beats"][3], "clip": 3}]}


def test_the_prompt_lists_the_clips_with_their_lengths():
    prompt = ma.build_prompt("A launch ad", None, 14, [], [CLIP])
    assert "1. Barista pulls a shot (2.5s)" in prompt and "{clips}" not in prompt
    assert "set every \"clip\" to null" in ma.build_prompt("A launch ad", None, 14, [])


def test_a_footage_beat_is_never_longer_than_its_clip_and_a_bad_number_is_dropped():
    plan = ma.clean(FOOTAGE_SCRIPT, 11, 0, clip_seconds=[2.5])
    assert [b["clip"] for b in plan["beats"]] == [None, 1, None]
    assert plan["beats"][1]["seconds"] == 2.5
    joined = " | ".join(plan["warnings"])
    assert "beat 2: clip 1 is only 2.5s" in joined and "beat 3: asked for clip 3" in joined


def test_a_footage_beat_shows_the_clip_with_white_type_and_no_flat_still():
    kit = {"name": "Gygler", "spec": brand_kits.clean_spec(KIT)}
    colours = ma.palette(kit)
    plan = ma.clean(FOOTAGE_SCRIPT, 11, 0, clip_seconds=[2.5])
    handles = {colours["primary"]: "asset:1"}
    doc = ma.layout(plan, size=(1280, 720), fps=30, colours=colours, backgrounds=handles,
                    cards=[], clips=[CLIP])
    v1 = doc["tracks"][0]["clips"]
    assert v1[1]["media"] == "gen:41" and v1[1]["src_out"] == 75 and v1[1]["at"] == v1[0]["src_out"]
    headline = next(g for t in doc["tracks"] for g in t.get("items") or []
                    if g.get("text") == "Real staff, on shift tonight.")
    assert headline["color"] == ma.ON_FOOTAGE
    assert headline["shadow"] is True              # kit type over footage reads with a shadow
    flat = next(g for t in doc["tracks"] for g in t.get("items") or []
                if g.get("text") == "Managing talent shouldn't feel like this.")
    assert "shadow" not in flat
    media = {"asset:1": {"frames": 150, "video": True, "audio": False, "still": True},
             "gen:41": {"frames": 75, "video": True, "audio": True, "still": False}}
    validate.validate(doc, media)


def test_redoing_a_footage_beat_keeps_the_clip_and_sets_white_type():
    doc, kit, colours, handles = _made()
    doc["tracks"][0]["clips"][1]["media"] = "gen:41"
    assert ma.beats_of(doc)[1]["footage"] is True
    prompt = ma.build_beat_prompt(doc, 2, kit, "")
    assert ">> 2. (4.0s, over a video clip)" in prompt
    made = ma.redo_beat(doc, 100, "", kit=kit, account_id=1, backgrounds_for=lambda u: handles,
                        flat_colour_of=_flat(handles), model=stub(NEW_BEAT))
    assert not any(o["op"] == "overwrite" for o in made["ops"])
    added = [o["args"] for o in made["ops"] if o["op"] == "set_graphic"]
    assert {a["type"] for a in added} == {"headline", "card", "label"}    # no big word on footage
    assert next(a for a in added if a["type"] == "headline")["color"] == ma.ON_FOOTAGE


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg not installed")
def test_the_route_takes_your_clips_and_refuses_what_is_not_one(signed_in, monkeypatch):
    import subprocess

    from src.cut import uploads
    pg, mine, theirs, tmp = signed_in
    clip_file = tmp / "shot.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=blue:s=320x180:d=2.5:r=30", "-pix_fmt", "yuv420p", str(clip_file)],
                   check=True)
    clip = uploads.save(clip_file.read_bytes(), "shot.mp4", account_id=mine,
                        media_dir=tmp / "media", dsn=pg)["handle"]
    still = uploads.save(ma.background_png("#123456", (64, 64)), "s.png", account_id=mine,
                         media_dir=tmp / "media", dsn=pg)["handle"]
    listed = client.get("/api/cut/media").json()["items"]
    assert {i["handle"] for i in listed} >= {clip, still}

    bad = client.post("/api/cut/motion-ad", json={"brief": "x", "footage": [still]})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "not_a_clip"
    assert client.post("/api/cut/motion-ad", json={"brief": "x", "footage": ["gen:999999"]}
                       ).json()["error"]["code"] == "not_a_clip"

    seen = []
    monkeypatch.setattr(ma, "_model", stub(FOOTAGE_SCRIPT, seen))
    job = _wait(client.post("/api/cut/motion-ad", json={"brief": "A launch ad", "seconds": 10,
                                                        "footage": [clip]}).json()["job_id"])
    assert job["status"] == "done", job
    assert "1. shot.mp4 (2.5s)" in seen[0]
    cut = store.get_project(job["cut_id"], account_id=mine, dsn=pg)
    v1 = store.head(cut["timeline_key"], account_id=mine, dsn=pg)["doc"]["tracks"][0]["clips"]
    assert v1[1]["media"] == clip and v1[1]["src_out"] == 75
