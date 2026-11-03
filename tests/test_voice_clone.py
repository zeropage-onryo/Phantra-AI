"""Voice cloning (2026-10-27, docs/tasks/task-voice-tab.md).

Mike's rules: a person clones ONLY THEIR OWN voice, and proves it by READING A
CONSENT LINE at the start of the sample. What these hold: the line is listened
for before anything is paid for (not heard: no clone, no charge); a clone runs
at the price the panel showed or not at all (409); a kept voice belongs to one
account; and the library reads in it and so keeps it alive.
"""
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import effects, fal, ledger, media, voice_clone, voice_models
from src import talking_photo as tp

ACCOUNT = 42
LINE = voice_clone.CONSENT_LINE
SPOKEN = LINE + " So this is me, talking about my day and the coffee I had this morning."


# ---------- the consent line ----------

@pytest.mark.parametrize("heard, ok", [
    (SPOKEN, True),
    (LINE, True),
    # Whisper's usual slips: a name it does not know, a dropped comma, case
    ("this is my own voice and i agree to fantra making a copy of it. hi there", True),
    ("Um, okay. " + LINE + " Right.", True),
    ("This is my own voice. Anyway, let's talk about the weather today.", False),
    ("Hello everyone, welcome to the channel, today we review a phone.", False),
    ("", False),
])
def test_the_consent_line_must_be_heard(heard, ok):
    assert voice_clone.consent_heard(heard) is ok


def test_the_line_must_come_near_the_start():
    late = " ".join(["word"] * 60) + " " + LINE
    assert voice_clone.consent_heard(late) is False
    assert voice_clone.consent_score(LINE) == 1.0


# ---------- the checks ----------

@pytest.mark.parametrize("seconds, suffix, match", [
    (9.9, ".mp3", "at least 10s"),
    (301.0, ".wav", "up to 300s"),
    (20.0, ".flac", "must be"),
    (None, ".mp3", "could not be measured"),
])
def test_a_sample_the_model_cannot_take_is_refused(seconds, suffix, match):
    with pytest.raises(ValueError, match=match):
        voice_clone.check_sample(seconds, suffix)


def test_names_are_trimmed_and_bounded():
    assert voice_clone.check_name("  My   voice ") == "My voice"
    with pytest.raises(ValueError, match="name the voice"):
        voice_clone.check_name(" ")
    with pytest.raises(ValueError, match="under 40"):
        voice_clone.check_name("x" * 41)


def test_the_price_is_the_clone_plus_its_preview():
    assert voice_clone.clone_usd() == round(1.5 + len(voice_clone.PREVIEW_TEXT) * 0.0003, 6)


def test_the_clone_body_is_the_models_wire_shape():
    endpoint, body = voice_clone.clone_body("https://r2/s.mp3")
    assert endpoint == "fal-ai/minimax/voice-clone"
    assert body["audio_url"] == "https://r2/s.mp3" and body["model"] == "speech-02-hd"
    # a preview is always asked for: it is the audio effects.run downloads
    assert body["text"] == voice_clone.PREVIEW_TEXT


# ---------- the run: consent first, then the spend ----------

@pytest.fixture
def pg(pg):
    """The throwaway schema with the two accounts these tests act as."""
    from src import db
    with db.connect(pg) as conn:
        for aid in (ACCOUNT, ACCOUNT + 1):
            conn.execute("INSERT INTO accounts (id, created_at, slug, display_name) "
                         "VALUES (%s, now(), %s, %s) ON CONFLICT DO NOTHING",
                         (aid, f"acct-{aid}", f"Account {aid}"))
    return pg


@pytest.fixture
def sample(monkeypatch):
    monkeypatch.setattr(tp, "voice_row", lambda ref, account_id=None, dsn=None: {
        "kind": "audio", "media_url": "/renders/cut/media/me.m4a", "output_path": "",
        "seconds": 24.0, "filename": "me.m4a"})
    monkeypatch.setattr(tp, "fetchable_audio", lambda url, local="", account_id=None: "https://r2/me.m4a")


def _effects_run(calls, voice_id="moss_audio_123"):
    def run(effect, urls, prompt, options, **kw):
        calls.append({"effect": effect, **kw})
        return {"ok": True, "generation_id": 5, "path": "/tmp/none.mp3", "media_kind": "audio",
                "result": {"custom_voice_id": voice_id, "audio": {"url": "https://fal/p.mp3"}}}
    return run


def test_no_consent_line_means_no_clone_and_no_charge(pg, sample, monkeypatch):
    calls = []
    monkeypatch.setattr(effects, "run", _effects_run(calls))
    monkeypatch.setattr(voice_clone, "hear", lambda *a, **kw: "hello everyone and welcome back")
    req = voice_clone.request("asset:7", "Me", account_id=ACCOUNT, dsn=pg)
    res = voice_clone.run(req, account_id=ACCOUNT, dsn=pg, source="composer")
    assert res["ok"] is False and "nothing was charged" in res["error"]
    assert calls == [], "the spend never started"
    assert voice_clone.clones(account_id=ACCOUNT, dsn=pg) == []


def test_a_heard_line_clones_and_keeps_the_voice(pg, sample, monkeypatch):
    calls = []
    monkeypatch.setattr(effects, "run", _effects_run(calls))
    monkeypatch.setattr(voice_clone, "hear", lambda *a, **kw: SPOKEN)
    monkeypatch.setattr(voice_models, "file_audio", lambda res, name, **kw: {
        "ok": True, "audio": "asset:9", "seconds": 3.1, "stored": "cut/media/clone.mp3"})
    req = voice_clone.request("asset:7", "Studio me", account_id=ACCOUNT, dsn=pg)
    res = voice_clone.run(req, account_id=ACCOUNT, dsn=pg, source="composer")
    assert res["ok"] is True and res["voice_id"] == "moss_audio_123" and res["audio"] == "asset:9"
    (c,) = calls
    assert c["usd"] == voice_clone.clone_usd() and c["row"]["output"] == "audio"
    assert c["endpoint_body"][0] == "fal-ai/minimax/voice-clone"
    (v,) = voice_clone.clones(account_id=ACCOUNT, dsn=pg)
    assert v["id"] == "moss_audio_123" and v["name"] == "Studio me" and v["kept"] is False
    assert v["expires_at"] is not None
    # another account sees none of it
    assert voice_clone.clones(account_id=ACCOUNT + 1, dsn=pg) == []
    assert voice_clone.remove("moss_audio_123", account_id=ACCOUNT + 1, dsn=pg) is False


def test_a_clone_with_no_voice_id_says_it_was_paid_for(pg, sample, monkeypatch):
    monkeypatch.setattr(effects, "run", _effects_run([], voice_id=""))
    monkeypatch.setattr(voice_clone, "hear", lambda *a, **kw: SPOKEN)
    req = voice_clone.request("asset:7", "Me", account_id=ACCOUNT, dsn=pg)
    res = voice_clone.run(req, account_id=ACCOUNT, dsn=pg, source="composer")
    assert res["ok"] is False and "no voice id" in res["error"]


def test_an_unused_voice_drops_off_after_a_week_and_a_used_one_stays(pg):
    for vid in ("a", "b"):
        voice_clone.keep(account_id=ACCOUNT, voice_id=vid, name=vid, sample="asset:1",
                         consent_heard=LINE, consent_score=1.0, preview_audio=None,
                         generation_id=None, dsn=pg)
    voice_clone.touch("b", account_id=ACCOUNT, dsn=pg)
    later = datetime.now(timezone.utc) + timedelta(days=8)
    assert [v["id"] for v in voice_clone.clones(account_id=ACCOUNT, dsn=pg, now=later)] == ["b"]
    assert voice_clone.remove("b", account_id=ACCOUNT, dsn=pg) is True
    assert voice_clone.clones(account_id=ACCOUNT, dsn=pg, now=later) == []


def test_ten_voices_is_the_most(pg, sample):
    for i in range(voice_clone.MAX_CLONES):
        voice_clone.keep(account_id=ACCOUNT, voice_id=f"v{i}", name=f"v{i}", sample="asset:1",
                         consent_heard=LINE, consent_score=1.0, preview_audio=None,
                         generation_id=None, dsn=pg)
    with pytest.raises(ValueError, match="remove one"):
        voice_clone.request("asset:7", "One more", account_id=ACCOUNT, dsn=pg)


# ---------- the library reads in a clone ----------

def test_the_library_takes_this_accounts_clone_and_nobody_elses():
    req = voice_models.library_request("Hi there.", "moss_audio_1", clones={"moss_audio_1": "Me"})
    assert req["clone"] is True and req["language"] == "auto" and req["name"] == "Me"
    assert voice_models.library_body(req)[1]["voice_setting"]["voice_id"] == "moss_audio_1"
    with pytest.raises(ValueError, match="not a voice in the library"):
        voice_models.library_request("Hi there.", "moss_audio_1", clones={})


def test_a_read_in_a_clone_keeps_it(monkeypatch):
    touched = []
    monkeypatch.setattr(effects, "run", lambda *a, **kw: {"ok": True, "path": "/tmp/x.mp3"})
    monkeypatch.setattr(voice_models, "file_audio", lambda res, name, **kw: {"ok": True, "name": name})
    monkeypatch.setattr(voice_clone, "touch", lambda vid, **kw: touched.append(vid))
    req = voice_models.library_request("Hi.", "moss_audio_1", clones={"moss_audio_1": "Me"})
    out = voice_models.run_library(req, account_id=ACCOUNT, source="composer")
    assert touched == ["moss_audio_1"] and out["name"] == "voice-me"
    voice_models.run_library(voice_models.library_request("Hi."), account_id=ACCOUNT, source="composer")
    assert touched == ["moss_audio_1"], "a system voice touches nothing"


# ---------- the routes ----------

@pytest.fixture
def client(pg, sample, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "clone-user"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(media, "url_for", lambda stored, account_id=None: f"https://m/{stored}")
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


CREDITS = ledger.charge_credits(voice_clone.clone_usd())


def test_the_menu_shows_the_consent_line_and_no_dollars(client):
    body = client.get("/api/voice").json()
    assert [m["kind"] for m in body["models"]] == ["speak", "library", "dialogue", "clone", "dub"]
    assert body["clone"]["consent_line"] == LINE and body["clone"]["voices"] == []
    assert "$" not in json.dumps(body)


def test_a_clone_runs_only_at_the_shown_price(client, monkeypatch):
    calls = []
    monkeypatch.setattr(voice_clone, "run", lambda req, **kw: calls.append(req) or {"ok": True})
    q = client.post("/api/voice/clone/quote", json={"sample": "asset:7", "name": "Me"}).json()
    assert q == {"name": "Me", "sample_seconds": 24.0, "credits": CREDITS, "charged": True}
    r = client.post("/api/voice/clone/run", json={"sample": "asset:7", "name": "Me"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_price"
    r = client.post("/api/voice/clone/run", json={"sample": "asset:7", "name": "Me", "expect_credits": CREDITS - 1})
    assert r.status_code == 409 and calls == []


def test_a_cloned_voice_lands_in_the_library(client, monkeypatch):
    def run(req, **kw):
        voice_clone.keep(account_id=ACCOUNT, voice_id="moss_audio_9", name=req["name"],
                         sample=req["sample"], consent_heard=LINE, consent_score=1.0,
                         preview_audio="asset:9", generation_id=1)
        return {"ok": True, "voice_id": "moss_audio_9", "name": req["name"], "audio": "asset:9",
                "seconds": 3.0, "stored": "cut/media/clone.mp3"}
    monkeypatch.setattr(voice_clone, "run", run)
    r = client.post("/api/voice/clone/run", json={"sample": "asset:7", "name": "Me", "expect_credits": CREDITS})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done" and job["voice_id"] == "moss_audio_9" and job["audio"] == "asset:9"
    lib = client.get("/api/voice").json()["library"]["languages"]
    assert lib[0] == {"language": "Your voices", "voices": [{"id": "moss_audio_9", "name": "Me"}]}
    q = client.post("/api/voice/library/quote", json={"script": "Hello.", "voice": "moss_audio_9"})
    assert q.status_code == 200 and q.json()["language"] == "auto"
    assert client.delete("/api/voice/clones/moss_audio_9").status_code == 200
    assert client.delete("/api/voice/clones/moss_audio_9").status_code == 404
    q = client.post("/api/voice/library/quote", json={"script": "Hello.", "voice": "moss_audio_9"})
    assert q.status_code == 400


def test_a_refused_consent_fails_the_job_in_plain_words(client, monkeypatch):
    monkeypatch.setattr(voice_clone, "run", lambda req, **kw: {
        "ok": False, "error": voice_clone.NOT_HEARD, "consent_score": 0.2})
    r = client.post("/api/voice/clone/run", json={"sample": "asset:7", "name": "Me", "expect_credits": CREDITS})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "failed" and "consent line was not heard" in json.dumps(job)
