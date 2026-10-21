"""A music bed for a cut (src/music.py, the editor's Music card): priced
before it is made, refused off a model's legal length, made through
effects.run (the hold, the row, settle), filed as an asset:<id> audio. fal
is replaced at effects.run everywhere here; nothing is generated or charged.
"""
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, brand_kits, effects, fal, ledger, music, preprod, projects
from src.cut import doc as d
from src.cut import render, store

client = TestClient(app)
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
KIT = {"sound": {"music": {"genre": "warm acoustic pop", "bpm": 104, "mood": "optimistic"},
                 "loudness": -16}}


# --------------------------------------------------------------------------
# the request: priced, checked, nothing spent
# --------------------------------------------------------------------------

def test_a_bed_is_priced_per_model_and_off_range_is_refused():
    flat = music.request("stable-audio-25", 21.4)
    assert flat["seconds"] == 22 and flat["usd"] == 0.20            # whole seconds, up
    per_min = music.request("elevenlabs-music", 61)
    assert per_min["usd"] == 1.20                                   # two started minutes
    assert music.request("elevenlabs-music", 30)["usd"] == 0.60
    with pytest.raises(ValueError, match="1-190 seconds"):
        music.request("stable-audio-25", 200)                       # refused, never clamped
    with pytest.raises(ValueError, match="3-600 seconds"):
        music.request("elevenlabs-music", 2)
    with pytest.raises(ValueError, match="model must be one of"):
        music.request("suno", 20)


def test_the_kit_gives_the_direction_and_the_prompt_is_always_instrumental():
    kit = {"spec": brand_kits.clean_spec(KIT)}
    req = music.request("stable-audio-25", 20, "light claps", kit)
    assert req["from_kit"] == "warm acoustic pop, optimistic, 104 BPM"
    assert req["direction"] == "warm acoustic pop, optimistic, 104 BPM; light claps"
    assert "No vocals" in req["prompt"] and "20-second" in req["prompt"]
    assert "{" not in req["prompt"]
    plain = music.request("stable-audio-25", 20)
    assert plain["direction"] == "" and "modern, warm and upbeat" in plain["prompt"]


def test_each_model_is_sent_exactly_its_own_fields():
    a = music.request("stable-audio-25", 20)
    assert music.body(a) == ("fal-ai/stable-audio-25/text-to-audio",
                             {"prompt": a["prompt"], "seconds_total": 20})
    b = music.request("elevenlabs-music", 20)
    endpoint, sent = music.body(b)
    assert endpoint == "fal-ai/elevenlabs/music"
    assert sent == {"prompt": b["prompt"], "music_length_ms": 20000, "force_instrumental": True}


# --------------------------------------------------------------------------
# the run: through effects.run, filed in the bin
# --------------------------------------------------------------------------

@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    store.init(pg)
    brand_kits.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(render, "CUT_DIR", tmp_path / "cut")
    mine = accounts.upsert_account("mu-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("mu-theirs", "Theirs", "#fff", dsn=pg)
    return pg, mine, theirs, tmp_path


def _wav(path, seconds=3):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=f=330:d={seconds}", str(path)], check=True)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_run_files_the_bed_as_an_audio_asset(dbx, monkeypatch):
    pg, mine, _, tmp = dbx
    made = tmp / "made.wav"
    _wav(made)
    seen = {}

    def fake_run(effect, urls, prompt, options, **kw):
        seen.update(effect=effect, usd=kw["usd"], body=kw["endpoint_body"], row=kw["row"],
                    extra=kw["extra"])
        return {"ok": True, "path": str(made), "generation_id": 7}

    monkeypatch.setattr(effects, "run", fake_run)
    req = music.request("stable-audio-25", 3)
    got = music.run(req, account_id=mine, dsn=pg, source="editor")
    assert got["ok"] and got["audio"].startswith("asset:") and abs(got["seconds"] - 3) < 0.1
    assert seen["effect"] == "music-stable-audio-25" and seen["usd"] == 0.20
    assert seen["row"]["output"] == "audio" and seen["extra"]["music"]["seconds"] == 3
    row = store.get_media(int(got["audio"].split(":")[1]), account_id=mine, dsn=pg)
    assert row["kind"] == "audio" and row["filename"] == "music-stable-audio-25-3s.wav"


def test_a_failed_make_is_said_and_nothing_is_filed(dbx, monkeypatch):
    pg, mine, _, _ = dbx
    monkeypatch.setattr(effects, "run", lambda *a, **k: {"ok": False, "error": "fal said no"})
    got = music.run(music.request("stable-audio-25", 3), account_id=mine, dsn=pg, source="editor")
    assert got == {"ok": False, "error": "fal said no"}
    assert store.media_bin(account_id=mine, dsn=pg) == []


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

@pytest.fixture
def signed_in(dbx, monkeypatch):
    pg, mine, theirs, tmp = dbx
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@e.com",
                                                               "display_name": "T"})
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id=None, *a, **k: False)
    app.dependency_overrides[auth.current_account_id] = lambda: mine
    yield dbx
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _cut(pg, account, seconds=12, project=None):
    row = store.create_project(account_id=account, title="Ad", dsn=pg,
                               studio_project_id=project)
    doc = d.new_doc()
    doc["duration"] = seconds * 30
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": []},
                     {"id": "G1", "kind": "graphic", "items": [
                         {"id": "g1", "start": 0, "end": seconds * 30, "type": "headline",
                          "text": "Hi."}]}]
    store.save_version(row["timeline_key"], doc, account_id=account, author="user",
                       op_summary="seed", dsn=pg)
    return row["id"]


def _wait(job_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("the job never finished")


def test_the_card_prices_the_cuts_length_and_holds_the_run_to_it(signed_in, monkeypatch):
    pg, mine, theirs, _ = signed_in
    kit = brand_kits.create("Gygler", KIT, pg, account_id=mine)
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    cut = _cut(pg, mine, 12, project["id"])

    menu = client.get(f"/api/cut/projects/{cut}/music").json()
    assert menu["kit_direction"] == "warm acoustic pop, optimistic, 104 BPM"
    assert menu["kit_name"] == "Gygler"
    stable = next(m for m in menu["models"] if m["id"] == "stable-audio-25")
    assert stable["seconds"] == 12 and stable["credits"] == ledger.charge_credits(0.20)

    quote = client.post(f"/api/cut/projects/{cut}/music/quote",
                        json={"model": "elevenlabs-music"}).json()
    assert quote["credits"] == ledger.charge_credits(0.60) and quote["seconds"] == 12

    run = f"/api/cut/projects/{cut}/music/run"
    assert client.post(run, json={"model": "stable-audio-25"}).json()["error"]["code"] == "missing_price"
    moved = client.post(run, json={"model": "stable-audio-25", "expect_credits": 1})
    assert moved.status_code == 409 and moved.json()["credits"] == stable["credits"]
    assert client.post(run, json={"model": "stable-audio-25", "seconds": 500,
                                  "expect_credits": 1}).json()["error"]["code"] == "bad_music"

    sent = {}

    def fake(req, **kw):
        sent.update(req=req, kw=kw)
        return {"ok": True, "audio": "asset:42", "seconds": 12.0, "stored": "/x.wav",
                "generation_id": 1}

    monkeypatch.setattr(music, "run", fake)
    job = _wait(client.post(run, json={"model": "stable-audio-25", "direction": "light claps",
                                       "expect_credits": stable["credits"]}).json()["job_id"])
    assert job["status"] == "done" and job["audio"] == "asset:42"
    assert sent["req"]["direction"].endswith("light claps")
    assert sent["kw"]["project_id"] == project["id"] and sent["kw"]["source"] == "editor"

    # someone else's cut is not there
    app.dependency_overrides[auth.current_account_id] = lambda: theirs
    assert client.get(f"/api/cut/projects/{cut}/music").status_code == 404


# --------------------------------------------------------------------------
# the kit's loudness at export
# --------------------------------------------------------------------------

def test_a_kits_loudness_masters_the_export_and_no_kit_stays_at_minus_14():
    doc = d.new_doc()
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": [
        {"id": "c1", "media": "gen:1", "src_in": 0, "src_out": 30, "at": 0, "speed": 1}]},
        {"id": "A2", "kind": "audio", "role": "music", "clips": [
            {"id": "m1", "media": "asset:2", "src_in": 0, "src_out": 30, "at": 0, "speed": 1}]}]
    doc["duration"] = 30
    paths = {"gen:1": "/x/a.mp4", "asset:2": "/x/m.wav"}
    plain = render.compile_args(doc, paths, "/x/o.mp4")
    kitted = render.compile_args(doc, paths, "/x/o.mp4", loudness=-16)
    assert "loudnorm=I=-14:" in " ".join(plain) and "loudnorm=I=-16:" in " ".join(kitted)
