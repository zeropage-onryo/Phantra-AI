"""A talking photo from the studio (2026-10-20, docs/tasks/task-talking-photo.md).

The connector had the feature first; these routes are the studio card's door
onto the same body (src/talking_photo.py). What they hold: every spend runs
at the price the card showed or not at all (409), the consent box is asked
before the clip, a voice is an asset:<id> and never an address, and the
brain can open the card but never spend.
"""
import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import api, auth
from app.main import app
from src import accounts, fal, guide_tools, ledger, mcp_server
from src import talking_photo as tp

ACCOUNT = 42
SCRIPT = ("Hi, I'm Maya. Welcome to the shop -- everything you see here was "
          "made by hand, in this room.")


@pytest.fixture
def world(monkeypatch):
    from src.cut import store as cut_store
    media = {5: {"id": 5, "kind": "audio", "media_url": "/renders/cut/media/v.mp3",
                 "output_path": "", "seconds": 10.04, "filename": "v.mp3"},
             6: {"id": 6, "kind": "video", "media_url": "/renders/cut/media/c.mp4",
                 "output_path": "", "seconds": 8.0, "filename": "c.mp4"}}
    monkeypatch.setattr(cut_store, "get_media",
                        lambda i, account_id=None, dsn=None: media.get(int(i)))
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **kw: ["https://r2/face.jpg"] if refs else [])
    monkeypatch.setattr(tp, "image_size", lambda t: (1024, 1536))
    monkeypatch.setattr(tp, "fetchable_audio",
                        lambda url, local="", account_id=None: "https://r2/v.mp3")
    monkeypatch.setattr(accounts, "plan_of", lambda a, dsn=None: None)
    calls = {"talk": [], "voice": []}

    def run_talk(req, image_url, **kw):
        calls["talk"].append({"req": req, "image_url": image_url, **kw})
        return {"ok": True, "media_url": "https://r2/out.mp4", "asset_id": 77,
                "media_kind": "video", "error": None}

    def run_voice(req, **kw):
        calls["voice"].append({"req": req, **kw})
        return {"ok": True, "audio": "asset:9", "seconds": 6.2,
                "stored": "/renders/cut/media/voice-aria.mp3", "generation_id": 3}

    monkeypatch.setattr(tp, "run_talk", run_talk)
    monkeypatch.setattr(tp, "run_voice", run_voice)
    return {"media": media, "calls": calls}


@pytest.fixture
def client(world, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "tp-user"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    app.dependency_overrides[auth.current_account_id] = lambda: ACCOUNT
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)


def _wait(client, job_id):
    for _ in range(500):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(.01)
    raise AssertionError("job never finished")


def _png(w, h) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(out, "PNG")
    return out.getvalue()


ASK = {"photo": "gen:12", "audio": "asset:5"}
CREDITS_11S = ledger.charge_credits(11 * 0.105)


# ---------- the menu ----------

def test_the_menu_lists_the_voices_and_this_accounts_longest_voice(client):
    body = client.get("/api/talking-photo").json()
    assert body["voices"] == list(tp.VOICES) and body["default_voice"] == "Rachel"
    assert body["audio_cap"] == 30 and body["script_min"] == tp.SCRIPT_MIN_CHARS
    assert body["ready"] is True and "$" not in json.dumps(body)


# ---------- the voice preview ----------

def test_the_voice_is_priced_by_its_script_and_nothing_runs(client, world):
    q = client.post("/api/talking-photo/voice/quote",
                    json={"script": SCRIPT, "voice": "aria"}).json()
    assert q["voice"] == "Aria" and q["characters"] == len(SCRIPT)
    assert q["credits"] == ledger.charge_credits(tp.voice_usd(SCRIPT)) == 10
    assert world["calls"]["voice"] == []


@pytest.mark.parametrize("body, match", [
    ({"script": "too short"}, "at least 50"),
    ({"script": SCRIPT, "voice": "Darth"}, "voice must be one of"),
    ({"script": SCRIPT, "language": "english"}, "two-letter"),
])
def test_a_voice_that_cannot_be_made_is_refused_before_a_price(client, body, match):
    r = client.post("/api/talking-photo/voice/quote", json=body)
    assert r.status_code == 400 and match in r.json()["error"]["message"]


def test_the_voice_runs_only_at_the_price_the_card_showed(client, world):
    ask = {"script": SCRIPT, "voice": "Aria"}
    r = client.post("/api/talking-photo/voice/run", json=ask)
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_price"
    r = client.post("/api/talking-photo/voice/run", json={**ask, "expect_credits": 9})
    assert r.status_code == 409 and r.json()["credits"] == 10
    assert world["calls"]["voice"] == []
    r = client.post("/api/talking-photo/voice/run", json={**ask, "expect_credits": 10})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["audio"] == "asset:9" and job["seconds"] == 6.2 and job["media"] == "audio"
    (c,) = world["calls"]["voice"]
    assert c["req"]["voice"] == "Aria" and c["account_id"] == ACCOUNT
    assert c["source"] == "composer"


# ---------- the clip ----------

def test_the_clip_is_priced_on_the_voices_measured_length_without_spending(client, world):
    q = client.post("/api/talking-photo/quote", json=ASK).json()
    assert q["audio_seconds"] == 10.04 and q["billed_seconds"] == 11
    assert q["credits"] == CREDITS_11S and q["audio_cap"] == 30
    assert q["photo_size"] == [1024, 1536] and world["calls"]["talk"] == []


@pytest.mark.parametrize("body, match", [
    ({**ASK, "audio": "https://x/v.mp3"}, "URLs are never taken"),
    ({**ASK, "audio": "asset:6"}, "must be sound"),
    ({**ASK, "audio": "asset:404"}, "no upload 404"),
    ({**ASK, "photo": ""}, "pick the photo"),
])
def test_a_clip_that_cannot_be_made_is_refused_before_a_price(client, body, match):
    r = client.post("/api/talking-photo/quote", json=body)
    assert r.status_code == 400 and match in r.json()["error"]["message"]


def test_a_voice_over_the_plans_cap_is_refused(client, world):
    world["media"][5]["seconds"] = 45.0
    r = client.post("/api/talking-photo/quote", json=ASK)
    assert r.status_code == 400 and "up to 30s" in r.json()["error"]["message"]


def test_the_clip_needs_the_consent_box_and_the_shown_price(client, world):
    r = client.post("/api/talking-photo/run", json={**ASK, "expect_credits": CREDITS_11S})
    assert r.status_code == 400 and "consent" in r.json()["error"]["message"]
    r = client.post("/api/talking-photo/run",
                    json={**ASK, "consent": True, "expect_credits": CREDITS_11S - 1})
    assert r.status_code == 409 and r.json()["credits"] == CREDITS_11S
    assert world["calls"]["talk"] == []


def test_an_approved_clip_renders_the_photo_and_the_voice_into_the_library(client, world):
    r = client.post("/api/talking-photo/run",
                    json={**ASK, "consent": True, "prompt": " a slow  push in ",
                          "expect_credits": CREDITS_11S})
    assert r.json()["credits"] == CREDITS_11S
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["asset"] == "gen:77" and job["media"] == "video"
    assert job["output"] == "https://r2/out.mp4"
    (c,) = world["calls"]["talk"]
    assert c["image_url"] == "https://r2/face.jpg" and c["account_id"] == ACCOUNT
    assert c["req"]["audio_url"] == "https://r2/v.mp3" and c["req"]["prompt"] == "a slow push in"
    assert c["req"]["usd"] == tp.talk_usd(10.04) and c["source"] == "composer"


def test_a_photo_from_the_box_is_measured_then_made_fetchable_at_the_run(client, world,
                                                                         monkeypatch):
    seen = []
    monkeypatch.setattr(api, "_photo_bytes", lambda url, a=None: seen.append(url) or _png(400, 600))
    monkeypatch.setattr(fal, "as_image_url", lambda data, account_id=None: "https://fal/up.jpg")
    body = {**ASK, "photo": "/photos/characters/maya/1.jpg?v=2", "consent": True}
    q = client.post("/api/talking-photo/quote", json=body).json()
    assert q["photo_size"] == [400, 600] and seen == ["/photos/characters/maya/1.jpg"]
    r = client.post("/api/talking-photo/run", json={**body, "expect_credits": q["credits"]})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert world["calls"]["talk"][0]["image_url"] == "https://fal/up.jpg"


def test_a_photo_the_model_cannot_take_is_refused(client, monkeypatch):
    monkeypatch.setattr(api, "_photo_bytes", lambda url, a=None: _png(200, 200))
    r = client.post("/api/talking-photo/quote", json={**ASK, "photo": "/photos/x.jpg"})
    assert r.status_code == 400 and "300 to 6000" in r.json()["error"]["message"]


def test_a_project_that_is_not_yours_is_refused(client, monkeypatch):
    from src import projects
    monkeypatch.setattr(projects, "get", lambda pid, dsn=None, account_id=None: None)
    r = client.post("/api/talking-photo/quote", json={**ASK, "project_id": 9})
    assert r.status_code == 400 and "no project 9" in r.json()["error"]["message"]


# ---------- the brain opens the card, never spends ----------

RESULTS = [{"n": 1, "kind": "still", "label": ""}, {"n": 2, "kind": "clip", "label": ""}]


def test_the_brain_proposes_the_card_with_a_still_and_words():
    args = guide_tools.check_args("talking_photo", {"on": 1, "script": "  Hello there. ",
                                                    "prompt": "slow  push"}, RESULTS)
    assert args == {"on": 1, "script": "Hello there.", "prompt": "slow push"}
    assert guide_tools.is_make("talking_photo") and guide_tools.is_write("talking_photo")
    with pytest.raises(guide_tools.Refused, match="takes a still"):
        guide_tools.check_args("talking_photo", {"on": 2}, RESULTS)
    with pytest.raises(guide_tools.Refused, match="URL"):
        guide_tools.check_args("talking_photo", {"script": "see https://x.y/a.mp3"}, RESULTS)
    assert "click" in guide_tools.talk_line(args)


def test_the_card_is_offered_only_to_the_composer_and_never_run_by_the_server(client):
    names = lambda **k: {s["name"] for s in guide_tools.session(local=True, **k)[0]}  # noqa: E731
    assert "talking_photo" in names(maker=True)
    assert "talking_photo" not in names(maker=True, makes=("make_image",))
    assert "talking_photo" not in names()
    with pytest.raises(guide_tools.Refused):
        guide_tools.run("talking_photo", {})
    r = client.post("/api/creative-guide/act", json={"tool": "talking_photo", "args": {}},
                    headers={"x-phantra-model-connection": "1"})
    assert r.status_code == 400 and "studio's send" in r.json()["error"]["message"]
