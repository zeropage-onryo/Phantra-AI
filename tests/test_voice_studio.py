"""The Voice section (2026-10-26, docs/tasks/task-voice-tab.md).

One page for every voice model. What these hold: the menu lists every model
the studio runs, priced in words and never in dollars; a read runs at the
price the card showed or not at all (409); it is filed in the editor's bin;
and the page is behind its own flag.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import dubbing, fal, ledger, media, voice_clone, voice_models, voice_studio
from src import talking_photo as tp

ACCOUNT = 42
SCRIPT = "Welcome to the shop. [laughs] Everything here was made by hand."
CREDITS = ledger.charge_credits(tp.voice_usd(SCRIPT))


@pytest.fixture
def calls(monkeypatch):
    made = []

    def speak(req, **kw):
        made.append({"req": req, **kw})
        return {"ok": True, "audio": "asset:31", "seconds": 4.2,
                "stored": "cut/media/voiceover-rachel.mp3", "generation_id": 9}

    monkeypatch.setattr(voice_studio, "speak", speak)
    monkeypatch.setattr(media, "url_for", lambda stored, account_id=None: f"https://m/{stored}")
    return made


@pytest.fixture
def client(calls, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "voice-user"})
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


def test_the_menu_lists_every_voice_model_in_words_and_no_dollars(client):
    body = client.get("/api/voice").json()
    assert [m["kind"] for m in body["models"]] == list(voice_studio.KINDS)
    assert [m["id"] for m in body["models"]] == [tp.VOICE["id"], voice_models.LIBRARY["id"],
                                                 voice_models.DIALOGUE["id"], voice_clone.CLONE["id"],
                                                 dubbing.DUB["id"]]
    assert all(m["what"] and m["priced"] and m["label"] for m in body["models"])
    assert body["speak"]["voices"] == list(tp.VOICES)
    assert body["speak"]["default_voice"] == tp.DEFAULT_VOICE
    assert [x["code"] for x in body["dub"]["languages"]] == list(dubbing.LANGUAGE_CODES)
    assert body["ready"] is True and body["exempt"] is False
    assert "$" not in json.dumps(body)


def test_a_read_is_priced_by_its_characters_and_nothing_runs(client, calls):
    q = client.post("/api/voice/speak/quote", json={"script": SCRIPT, "voice": "aria"}).json()
    assert q == {"voice": "Aria", "language": None, "characters": len(SCRIPT),
                 "credits": CREDITS, "charged": True}
    assert calls == []


def test_a_short_line_is_fine_here(client):
    # the talking photo's 50-character floor is for its 4-second clip; a
    # read on its own can be three words
    r = client.post("/api/voice/speak/quote", json={"script": "Hi there."})
    assert r.status_code == 200 and r.json()["characters"] == 9


@pytest.mark.parametrize("body, match", [
    ({"script": ""}, "write the words"),
    ({"script": "  "}, "write the words"),
    ({"script": SCRIPT, "voice": "Darth"}, "voice"),
    ({"script": SCRIPT, "language": "english"}, "two-letter"),
])
def test_a_read_that_cannot_be_made_is_refused_before_a_price(client, body, match):
    r = client.post("/api/voice/speak/quote", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_voice"
    assert match in r.json()["error"]["message"]


def test_the_run_needs_the_shown_price(client, calls):
    r = client.post("/api/voice/speak/run", json={"script": SCRIPT})
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_price"
    r = client.post("/api/voice/speak/run", json={"script": SCRIPT, "expect_credits": CREDITS + 1})
    assert r.status_code == 409 and r.json()["credits"] == CREDITS
    assert calls == []


def test_an_approved_read_is_filed_and_playable(client, calls):
    r = client.post("/api/voice/speak/run",
                    json={"script": SCRIPT, "voice": "Roger", "language": "EN",
                          "expect_credits": CREDITS})
    assert r.json()["credits"] == CREDITS and r.json()["charged"] is True
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["audio"] == "asset:31" and job["seconds"] == 4.2 and job["media"] == "audio"
    assert job["output"] == "https://m/cut/media/voiceover-rachel.mp3"
    (c,) = calls
    assert c["account_id"] == ACCOUNT and c["source"] == "composer"
    assert c["req"]["voice"] == "Roger" and c["req"]["language"] == "en"
    assert c["req"]["script"] == SCRIPT


def test_a_read_that_fails_says_so_in_plain_words(client, monkeypatch):
    monkeypatch.setattr(voice_studio, "speak", lambda req, **kw: {"ok": False, "error": "fal: boom"})
    r = client.post("/api/voice/speak/run", json={"script": SCRIPT, "expect_credits": CREDITS})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "failed" and "Nothing was charged" in json.dumps(job)


def test_without_a_fal_key_the_run_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    r = client.post("/api/voice/speak/run", json={"script": SCRIPT, "expect_credits": CREDITS})
    assert r.status_code == 503 and r.json()["error"]["code"] == "effects_unavailable"


def test_a_project_that_is_not_yours_is_refused(client, monkeypatch):
    from src import projects
    monkeypatch.setattr(projects, "get", lambda pid, dsn=None, account_id=None: None)
    r = client.post("/api/voice/speak/quote", json={"script": SCRIPT, "project_id": 9})
    assert r.status_code == 400 and "no project 9" in r.json()["error"]["message"]


def test_the_page_is_behind_its_own_flag(client, monkeypatch):
    monkeypatch.delenv("PHANTRA_VOICE_TAB", raising=False)
    assert client.get("/api/capabilities").json()["voice_tab"] is False
    monkeypatch.setenv("PHANTRA_VOICE_TAB", "1")
    assert client.get("/api/capabilities").json()["voice_tab"] is True


def test_the_speak_body_is_the_voiceovers_wire_shape():
    req = voice_studio.speak_request(SCRIPT, "Sarah", "fr")
    assert req["usd"] == tp.voice_usd(SCRIPT) and req["voice"] == "Sarah"
    endpoint, body = tp.voice_body(req["script"], req["voice"], req["language"])
    assert endpoint == tp.VOICE["endpoint"]
    assert body == {"text": SCRIPT, "voice": "Sarah", "language_code": "fr"}
