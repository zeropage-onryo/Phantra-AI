"""A motion ad on the brand's own photos (step 2 of docs/tasks/task-url-to-ad.md):
a beat may sit on a photo full frame with a named camera move, and carry its
line of voiceover. The model is replaced at its seam everywhere; the one
render test runs real ffmpeg on generated pictures.
"""
import io
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import auth
from app.main import app
from src import accounts, brand_kits, charge, entities, preprod, projects
from src.cut import doc as d
from src.cut import lanes, render, store, uploads, validate
from src.cut import motion_ad as ma

client = TestClient(app)

KIT = {"palette": [{"hex": "#FF880B", "role": "primary"}, {"hex": "#FAF0E4", "role": "background"},
                   {"hex": "#151515", "role": "text"}],
       "identity": {"tagline": "Get a Gyg, stay for good.", "url": "gygler.com"},
       "never_claim": ["guaranteed savings"]}


def beat(**over):
    base = {"headline": "Find the right talent.", "big_word": "", "card": None,
            "card_caption": "", "label": "", "background": "background", "seconds": 2,
            "picture": None, "move": "hold", "voiceover": ""}
    return {**base, **over}


GYGLER = {"title": "Meet Gygler", "beats": [
    beat(headline="Staffing shouldn't be a gamble.", background="primary",
         voiceover="Short-staffed again?"),
    beat(headline="Find the right talent.", big_word="find", picture=1, move="push_in",
         voiceover="Gygler finds vetted people fast."),
    beat(headline="Check in where they work.", picture=2, move="pan_left",
         voiceover="They check in on site."),
    beat(headline="See every shift live.", picture=3, move="drift",
         voiceover="And you see every shift as it happens."),
    beat(headline="Get a Gyg, stay for good.", background="primary", voiceover="Get a Gyg."),
]}


# --- the moves (pure) ------------------------------------------------------

@pytest.mark.parametrize("move", list(ma.MOVES))
def test_every_move_is_inside_the_lanes_bounds_and_never_shows_an_edge(move):
    clip = {"id": "c1", "media": "asset:1", "src_in": 0, "src_out": 60, "at": 0, "speed": 1,
            "lanes": ma.move_lanes(move, 60)}
    if not clip["lanes"]:
        assert move == "hold"
        return
    assert lanes.check(clip, 60, "c1", lanes.PATHS) == []
    for ln in clip["lanes"]:
        assert ln["keys"][0]["frame"] == 0
        assert all(0 <= k["frame"] <= 59 for k in ln["keys"])
    zoom = {k["frame"]: k["value"] for k in next(x for x in clip["lanes"]
                                                 if x["path"] == "zoom")["keys"]}
    for ln in clip["lanes"]:
        if ln["path"] in ("x", "y"):
            spare = (min(zoom.values()) - 1) / 2
            assert all(abs(k["value"]) <= spare for k in ln["keys"]), move


def test_a_move_off_the_list_holds_and_says_so():
    plan = ma.clean({"beats": [beat(picture=1, move="whip_pan")]}, 2, 0, n_pictures=1)
    assert plan["beats"][0]["move"] == "hold"
    assert "not a camera move" in " ".join(plan["warnings"])


def test_a_move_without_a_photo_is_dropped_quietly():
    plan = ma.clean({"beats": [beat(move="push_in")]}, 2, 0, n_pictures=0)
    assert plan["beats"][0]["move"] == "hold" and plan["warnings"] == []


# --- checked against reality ----------------------------------------------

def test_a_photo_that_was_not_offered_is_refused_and_said():
    plan = ma.clean({"beats": [beat(picture=4)]}, 2, 0, n_pictures=3)
    assert plan["beats"][0]["picture"] is None
    assert "photo 4" in plan["warnings"][0]


def test_a_voiceover_number_or_a_banned_claim_is_flagged_not_dropped():
    raw = {"beats": [beat(voiceover="Save 40% with guaranteed savings every week.")]}
    plan = ma.clean(raw, 2, 0, facts="hire faster", never=["guaranteed savings"])
    assert plan["beats"][0]["voiceover"].startswith("Save 40%")
    said = " ".join(plan["warnings"])
    assert "voiceover" in said and "40" in said
    assert "never to make" in said and "guaranteed savings" in said


def test_a_long_voiceover_line_is_shortened_and_said():
    plan = ma.clean({"beats": [beat(voiceover="word " * 80)]}, 2, 0)
    assert len(plan["beats"][0]["voiceover"]) <= ma.VOICEOVER_MAX
    assert "voiceover line was shortened" in plan["warnings"][0]


def test_an_older_answer_with_no_photo_fields_still_cleans():
    old = {k: v for k, v in beat().items() if k not in ("picture", "move", "voiceover")}
    b = ma.clean({"beats": [old]}, 2, 0)["beats"][0]
    assert (b["picture"], b["move"], b["voiceover"]) == (None, "hold", "")


def test_the_prompt_numbers_the_photos_and_names_the_moves():
    seen = []
    ma.write_beats("An ad", None, 10, [], account_id=None, pictures=[
        {"handle": "asset:5", "name": "Check-in screen"}],
        model=lambda prompt, account_id: seen.append(prompt) or GYGLER)
    assert "1. Check-in screen" in seen[0]
    assert "push_in" in seen[0] and "scale_in" in seen[0]
    none = []
    ma.write_beats("An ad", None, 10, [], account_id=None,
                   model=lambda prompt, account_id: none.append(prompt) or GYGLER)
    assert "set every \"picture\" to null" in none[0]


# --- the layout (pure) -----------------------------------------------------

PICS = [{"handle": "asset:11", "width": 1600, "height": 1200},     # 4:3 into 16:9: cropped
        {"handle": "asset:12", "width": 1280, "height": 720},      # already fits
        {"handle": "asset:13", "width": 200, "height": 1600}]      # too tall to crop: whole


def test_a_photo_beat_sits_on_the_photo_with_its_move_crop_and_white_type():
    plan = ma.clean(GYGLER, 10, 0, n_pictures=3)
    colours = ma.palette({"spec": brand_kits.clean_spec(KIT)})
    flats = {c: f"asset:{900 + i}" for i, c in enumerate(sorted(set(colours.values())))}
    doc = ma.layout(plan, size=(1280, 720), fps=30, colours=colours, backgrounds=flats,
                    cards=[], pictures=PICS)
    v1 = doc["tracks"][0]["clips"]
    assert [c["media"] for c in v1] == [flats["#FF880B"], "asset:11", "asset:12", "asset:13",
                                        flats["#FF880B"]]
    assert [ln["path"] for ln in v1[1]["lanes"]] == ["zoom"]
    assert v1[1]["crop"]["top"] > 0 and v1[1]["crop"]["left"] == 0
    assert "crop" not in v1[2] and "crop" not in v1[3]
    assert "lanes" not in v1[0]
    heads = {g["start"]: g for t in doc["tracks"] if t["id"] == "G2" for g in t["items"]}
    on_photo = next(g for s, g in heads.items() if v1[1]["at"] <= s < v1[2]["at"])
    assert on_photo["color"] == ma.PHOTO_INK
    assert [m["label"] for m in doc["markers"]][:2] == ["VO 1: Short-staffed again?",
                                                        "VO 2: Gygler finds vetted people fast."]
    media = {h: {"frames": 18000, "video": True, "audio": False, "still": True,
                 "width": 1280, "height": 720}
             for h in list(flats.values()) + [p["handle"] for p in PICS]}
    validate.validate(doc, media)


# --- a real render, exact length ------------------------------------------

def _png(path: Path, size, colour):
    Image.new("RGB", size, colour).save(path, "PNG")
    return path


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is not installed")
def test_a_gygler_shaped_ad_renders_with_ffmpeg_and_lasts_exactly_its_seconds(tmp_path):
    plan = ma.clean(GYGLER, 10, 0, n_pictures=3)
    colours = ma.palette({"spec": brand_kits.clean_spec(KIT)})
    flats = {c: f"asset:{900 + i}" for i, c in enumerate(sorted(set(colours.values())))}
    pics = [{"handle": "asset:21", "width": 1600, "height": 1200},
            {"handle": "asset:22", "width": 1280, "height": 720},
            {"handle": "asset:23", "width": 900, "height": 900}]
    size = (640, 360)
    doc = ma.layout(plan, size=size, fps=30, colours=colours, backgrounds=flats, cards=[],
                    pictures=pics)
    paths = {h: _png(tmp_path / f"{c[1:]}.png", size, c) for c, h in flats.items()}
    for p, colour in zip(pics, ((200, 120, 40), (40, 90, 160), (90, 160, 90))):
        paths[p["handle"]] = _png(tmp_path / f"{p['handle'][6:]}.png",
                                  (p["width"], p["height"]), colour)
    media = {h: {"frames": d.STILL_SECONDS * 30, "video": True, "audio": False, "still": True,
                 "width": w, "height": hh}
             for h, (w, hh) in [(h, size) for h in flats.values()]
             + [(p["handle"], (p["width"], p["height"])) for p in pics]}
    validate.validate(doc, media)
    out = render.render(doc, account_id=None, name="gygler-ad", paths=paths, media=media,
                        out_dir=tmp_path / "out")
    from src.cut import sources
    assert sources.video_frames(Path(out["path"]), 30) == 10 * 30 == doc["duration"]


# --- the route: the kit's pictures join -----------------------------------

@pytest.fixture
def signed_in(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    store.init(pg)
    brand_kits.init(pg)
    entities.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "bk")
    mine = accounts.upsert_account("map-mine", "Mine", "#fff", dsn=pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@e.com",
                                                               "display_name": "T"})
    monkeypatch.setattr(charge, "create_refusal_code", lambda account_id: None)
    import app.cut_routes as routes
    monkeypatch.setattr(routes, "MEDIA_DIR", tmp_path / "media")
    app.dependency_overrides[auth.current_account_id] = lambda: mine
    yield pg, mine, tmp_path
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _wait(job_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("the job never finished")


def _jpeg(size=(1600, 1200), colour=(200, 120, 40)):
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "JPEG")
    return buf.getvalue()


def test_the_kits_product_photo_and_look_reference_reach_the_ad(signed_in, monkeypatch):
    pg, mine, tmp = signed_in
    prop = entities.add_prop("Check-in screen", category="product", account_id=mine, dsn=pg)
    kit = brand_kits.create("Gygler", {**KIT, "products": [
        {"kind": "prop", "id": prop, "name": "Check-in screen"}]}, pg, account_id=mine)
    brand_kits.add_asset(kit["id"], "reference", _jpeg(colour=(10, 120, 60)), pg,
                         account_id=mine, filename="look.jpg")
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    photo = tmp / "screen.jpg"
    photo.write_bytes(_jpeg(colour=(30, 30, 200)))
    from src import element_sheet
    monkeypatch.setattr(element_sheet, "photo_files", lambda urls, tmp_, account_id, limit: [photo])
    seen = []
    monkeypatch.setattr(ma, "_model", lambda prompt, account_id: seen.append(prompt) or GYGLER)
    got = client.post("/api/cut/motion-ad", json={"brief": "A launch ad", "seconds": 10,
                                                 "project_id": project["id"]}).json()
    job = _wait(got["job_id"])
    assert job["status"] == "done", job
    assert "1. Check-in screen" in seen[0] and "2. look reference 1" in seen[0]
    assert job["pictures"] == 2 and job["screens"] == 0
    assert job["on_photos"] == 2                                # photos 1 and 2; 3 was not offered
    assert job["script"].startswith("Short-staffed again? Gygler finds")
    assert [v["beat"] for v in job["voiceover"]] == [1, 2, 3, 4, 5]
    assert any("photo 3" in w for w in job["warnings"])
    head = client.get(f"/api/cut/projects/{job['cut_id']}").json()["head"]["doc"]
    v1 = head["tracks"][0]["clips"]
    assert v1[1]["media"].startswith("asset:") and v1[1]["lanes"][0]["path"] == "zoom"
    # off: the kit's pictures stay out, and nothing else changes
    seen.clear()
    off = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "A launch ad", "seconds": 10, "project_id": project["id"],
        "kit_pictures": False}).json()["job_id"])
    assert off["status"] == "done" and off["pictures"] == 0 and off["on_photos"] == 0


def test_a_picture_that_is_not_the_callers_is_refused(signed_in):
    r = client.post("/api/cut/motion-ad", json={"brief": "x", "pictures": ["asset:999"]})
    assert r.status_code == 400 and r.json()["error"]["code"] == "not_a_still"


def test_an_uploaded_still_can_be_a_photo_beat(signed_in, monkeypatch):
    pg, mine, tmp = signed_in
    saved = uploads.save(_jpeg((1280, 720)), "shot.jpg", account_id=mine,
                         media_dir=tmp / "media", dsn=pg)
    monkeypatch.setattr(ma, "_model", lambda prompt, account_id: {"title": "t", "beats": [
        beat(picture=1, move="scale_in", seconds=10)]})
    job = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "x", "seconds": 10, "pictures": [saved["handle"]]}).json()["job_id"])
    assert job["status"] == "done", job
    head = client.get(f"/api/cut/projects/{job['cut_id']}").json()["head"]["doc"]
    assert head["tracks"][0]["clips"][0]["media"] == saved["handle"]


def test_an_app_screen_from_the_import_rides_on_a_card_never_full_frame(signed_in, monkeypatch):
    """The reference's rule: a screen of the app sits on a card beside its
    headline; only a real photo sits under a beat."""
    from app.brand_routes import SCREEN_NOTE
    pg, mine, tmp = signed_in
    screen = entities.add_prop("Check-in screen", category="product", account_id=mine, dsn=pg,
                               notes=SCREEN_NOTE + "From the website: https://gygler.com/")
    kit = brand_kits.create("Gygler", {**KIT, "products": [
        {"kind": "prop", "id": screen, "name": "Check-in screen"}]}, pg, account_id=mine)
    brand_kits.add_asset(kit["id"], "reference", _jpeg(colour=(10, 120, 60)), pg,
                         account_id=mine, filename="look.jpg")
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    photo = tmp / "screen.jpg"
    photo.write_bytes(_jpeg((900, 1600), colour=(30, 30, 200)))
    from src import element_sheet
    monkeypatch.setattr(element_sheet, "photo_files", lambda urls, tmp_, account_id, limit: [photo])
    seen = []
    script = {"title": "t", "beats": [beat(headline="Check in on site.", card=1, seconds=5),
                                      beat(headline="Look.", picture=1, move="drift", seconds=5)]}
    monkeypatch.setattr(ma, "_model", lambda prompt, account_id: seen.append(prompt) or script)
    job = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "A launch ad", "seconds": 10, "project_id": project["id"]}).json()["job_id"])
    assert job["status"] == "done", job
    assert job["screens"] == 1 and job["pictures"] == 1
    screens_block = seen[0].split("THE PRODUCT'S SCREENS")[1].split("THE BRAND'S PHOTOS")[0]
    photos_block = seen[0].split("THE BRAND'S PHOTOS")[1].split("FOR EVERY BEAT")[0]
    assert "1. Check-in screen" in screens_block and "Check-in" not in photos_block
    assert "1. look reference 1" in photos_block
    head = client.get(f"/api/cut/projects/{job['cut_id']}").json()["head"]["doc"]
    cards = [g for t in head["tracks"] if t.get("kind") == "graphic"
             for g in t["items"] if g["type"] == "card"]
    v1 = head["tracks"][0]["clips"]
    assert len(cards) == 1 and cards[0]["media"] != v1[1]["media"]
    assert v1[1].get("lanes")                                     # the photo beat drifts


# --- step 3: the chat's ad card -------------------------------------------

def test_a_preview_writes_the_beats_and_saves_nothing(signed_in, monkeypatch):
    pg, mine, tmp = signed_in
    monkeypatch.setattr(ma, "_model", lambda prompt, account_id: GYGLER)
    before = len(store.media_bin(account_id=mine, dsn=pg))
    job = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "A launch ad", "seconds": 10, "preview": True}).json()["job_id"])
    assert job["status"] == "done", job
    assert job["preview"] is True and "cut_id" not in job
    assert len(job["beats"]) == 5 and job["title"] == "Meet Gygler"
    assert job["script"].startswith("Short-staffed again?")
    assert [v["at"] for v in job["voiceover"]] == [0.0, 2.0, 4.0, 6.0, 8.0]
    assert job["cards"] == [] and job["pictures"] == []
    assert len(store.media_bin(account_id=mine, dsn=pg)) == before   # not even a colour plate


def test_build_from_the_cards_beats_calls_no_model_and_keeps_the_edit(signed_in, monkeypatch):
    pg, mine, tmp = signed_in

    def never(*a, **k):
        raise AssertionError("a script the card holds is built with no model call")
    monkeypatch.setattr(ma, "_model", never)
    edited = {"title": "Meet Gygler", "beats": [
        {**b, "headline": "Hire people you can count on." if n == 1 else b["headline"]}
        for n, b in enumerate(GYGLER["beats"]) if n != 2]}     # beat 3 removed, beat 2 rewritten
    job = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "A launch ad", "seconds": 10, "script": edited}).json()["job_id"])
    assert job["status"] == "done", job
    assert job["beats"] == 4
    head = client.get(f"/api/cut/projects/{job['cut_id']}").json()["head"]["doc"]
    heads = [g["text"] for t in head["tracks"] if t["id"] == "G2" for g in t["items"]]
    assert "Hire people you can count on." in heads and "Check in where they work." not in heads
    assert head["duration"] == 10 * 30                              # the others fit around it
    # the same checks hold for a script the person typed: a number the brief never gave
    typed = {"title": "t", "beats": [beat(headline="Save 70% today.", seconds=10)]}
    job = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "x", "seconds": 10, "script": typed}).json()["job_id"])
    assert any("70" in w for w in job["warnings"])


# --------------------------------------------------------------------------
# step 4: the voice on a built ad, through the editor's own routes and ops
# (the chat card's order: quote, run at that price, then the placement
# lib/cut/voiceover.ts sends). effects.run is replaced, so nothing is read
# or charged; that a failed effect releases its hold is effects' own test
# (tests/test_effects.py::test_a_failed_effect_releases_its_hold).
# --------------------------------------------------------------------------

@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                    reason="ffmpeg/ffprobe not installed")
def test_a_read_of_the_built_ads_script_lands_on_its_voice_track(signed_in, monkeypatch, tmp_path):
    import subprocess

    from src import effects, failures, fal, ledger
    pg, mine, _ = signed_in
    monkeypatch.setattr(ma, "_model", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model")))
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id=None, *a, **k: False)
    monkeypatch.setattr(render, "CUT_DIR", tmp_path / "cut")
    built = _wait(client.post("/api/cut/motion-ad", json={
        "brief": "A launch ad", "seconds": 10, "script": GYGLER}).json()["job_id"])
    assert built["status"] == "done" and built["script"], built
    cut, script = built["cut_id"], built["script"]

    quote = client.post(f"/api/cut/projects/{cut}/voiceover/quote", json={"script": script}).json()
    read = tmp_path / "read.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=3",
                    str(read)], check=True)
    monkeypatch.setattr(effects, "run", lambda *a, **k: {"ok": True, "path": str(read),
                                                         "generation_id": 1})
    job = _wait(client.post(f"/api/cut/projects/{cut}/voiceover/run", json={
        "script": script, "expect_credits": quote["credits"]}).json()["job_id"])
    assert job["status"] == "done" and job["audio"].startswith("asset:"), job

    head = client.get(f"/api/cut/projects/{cut}").json()["head"]
    assert not any(t.get("role") == "voice" for t in head["doc"]["tracks"])
    for op, args in (("add_track", {"kind": "audio", "role": "voice"}), ("overwrite", None)):
        if args is None:
            voice = next(t for t in head["doc"]["tracks"] if t.get("role") == "voice")
            frames = d.to_frames(job["seconds"], head["doc"]["fps"])   # as lib/cut/voiceover.ts
            args = {"track_id": voice["id"], "at": 0,
                    "clip": {"media": job["audio"], "src_in": 0, "src_out": frames}}
        res = client.post(f"/api/cut/projects/{cut}/ops",
                          json={"base_id": head["id"], "op": op, "args": args})
        assert res.status_code == 200, res.json()
        head = res.json()["head"]
    voice = next(t for t in head["doc"]["tracks"] if t.get("role") == "voice")
    assert [(c["media"], c["at"]) for c in voice["clips"]] == [(job["audio"], 0)]

    # a read that fails is said in plain words and lands nothing
    monkeypatch.setattr(effects, "run", lambda *a, **k: {"ok": False, "error": "fal said no"})
    failed = _wait(client.post(f"/api/cut/projects/{cut}/voiceover/run", json={
        "script": script, "expect_credits": quote["credits"]}).json()["job_id"])
    assert failed["status"] == "failed"
    assert failed["error"] == failures.plain("fal said no", "The voiceover")
