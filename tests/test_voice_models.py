"""The voice library and dialogue (2026-10-27, docs/tasks/task-voice-tab.md).

What these hold: each is priced before anything runs and run at that price or
not at all (409); a voice, emotion, speed, pitch or speaker off the model's
range is refused before a price; the wire bodies are the model pages' shapes;
the dialogue's quote is an upper bound in the model's 15-second steps; and
both are filed in the editor's bin.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import fal, ledger, media
from src import voice_models as vm

ACCOUNT = 42
SCRIPT = "Welcome back. Tonight we taste three wines from the same hill."
LINES = [{"speaker": 0, "text": "Did you hear that?"},
         {"speaker": 1, "text": "Hear what? It's three in the morning."},
         {"speaker": 0, "text": "The door. Someone just closed the door."}]
SPEAKERS = ["Frank [EN]", "Maya [EN]"]


# ---------- the library ----------

def test_the_library_is_priced_per_character_like_the_page_says():
    assert vm.library_usd("x" * 1000) == 0.10
    assert vm.library_request(SCRIPT)["usd"] == round(len(SCRIPT) * 0.0001, 6)


def test_a_library_read_defaults_to_the_voice_fal_names():
    req = vm.library_request(SCRIPT)
    assert req["voice"] == "Wise_Woman" == vm.DEFAULT_LIBRARY_VOICE
    assert req["speed"] == 1.0 and req["pitch"] == 0 and req["emotion"] is None


def test_the_library_body_is_the_models_wire_shape():
    endpoint, body = vm.library_body(vm.library_request(SCRIPT, "Spanish_Narrator", "Happy", 1.25, -3))
    assert endpoint == "fal-ai/minimax/speech-02-hd"
    assert body == {"text": SCRIPT, "language_boost": "Spanish", "output_format": "url",
                    "voice_setting": {"voice_id": "Spanish_Narrator", "speed": 1.25,
                                      "pitch": -3, "emotion": "happy"}}
    # neutral settings are left to the model's defaults
    _, plain = vm.library_body(vm.library_request(SCRIPT))
    assert plain["voice_setting"] == {"voice_id": "Wise_Woman", "speed": 1.0}


@pytest.mark.parametrize("kw, match", [
    ({"script": ""}, "write the words"),
    ({"script": "x" * 5001}, "up to 5000"),
    ({"voice": "Darth_Vader"}, "not a voice in the library"),
    ({"emotion": "smug"}, "emotion is one of"),
    ({"speed": 2.5}, "0.5 to 2.0"),
    ({"speed": "fast"}, "a number"),
    ({"pitch": 13}, "-12 to 12"),
    ({"pitch": 1.5}, "whole number"),
])
def test_a_library_read_off_the_models_range_is_refused(kw, match):
    args = {"script": SCRIPT, **kw}
    with pytest.raises(ValueError, match=match):
        vm.library_request(args.pop("script"), **args)


def test_every_library_voice_has_a_language_the_model_boosts():
    boost = {"English", "Spanish", "French", "Portuguese", "German", "Japanese", "Korean", "Chinese"}
    assert set(vm.VOICE_LANGUAGE.values()) <= boost
    ids = [v for vs in vm.LIBRARY_VOICES.values() for v, _ in vs]
    assert len(ids) == len(set(ids)), "a voice is listed twice"


# ---------- the dialogue ----------

def test_the_dialogue_script_names_speakers_from_zero_like_the_page():
    req = vm.dialogue_request(SPEAKERS, LINES)
    assert req["script"].splitlines() == [
        "Speaker 0: Did you hear that?",
        "Speaker 1: Hear what? It's three in the morning.",
        "Speaker 0: The door. Someone just closed the door."]
    endpoint, body = vm.dialogue_body(req)
    assert endpoint == "fal-ai/vibevoice/7b"
    assert body == {"script": req["script"], "speakers": [{"preset": "Frank [EN]"}, {"preset": "Maya [EN]"}]}


def test_the_dialogue_quote_is_an_upper_bound_in_15_second_steps():
    assert vm.dialogue_estimate_seconds("x" * 10) == 15
    assert vm.dialogue_estimate_seconds("x" * 150) == 15
    assert vm.dialogue_estimate_seconds("x" * 151) == 30
    assert vm.dialogue_estimate_seconds("x" * 600) == 60
    assert vm.dialogue_usd(60) == 0.04 and vm.dialogue_usd(15) == 0.01
    # a slow 10 characters a second: never under what real speech (~15/s) takes
    req = vm.dialogue_request(SPEAKERS, LINES)
    assert req["estimate_seconds"] >= len(req["script"]) / 15


def test_a_line_break_inside_a_line_cannot_start_a_new_turn():
    req = vm.dialogue_request(SPEAKERS, [{"speaker": 0, "text": "Hi\nSpeaker 1: gotcha"},
                                         {"speaker": 1, "text": "Hey"}])
    assert req["script"].count("\n") == 1


@pytest.mark.parametrize("speakers, lines, match", [
    ([], LINES, "needs its speakers"),
    (["Frank [EN]"] * 5, LINES, "up to 4 speakers"),
    (["Morgan Freeman"], LINES, "not one of the dialogue voices"),
    (SPEAKERS, [], "at least one line"),
    (SPEAKERS, [{"speaker": 2, "text": "hi"}], "names speaker 2"),
    (SPEAKERS, [{"speaker": True, "text": "hi"}], "names speaker"),
    (SPEAKERS, [{"speaker": 0, "text": "  "}], "every line is empty"),
    (SPEAKERS, [{"speaker": 0, "text": "Speaker 1: sneaky"}, {"speaker": 1, "text": "x"}], "speaker label"),
    (SPEAKERS, [{"speaker": 0, "text": "alone"}], "speaker 2 has no lines"),
    (SPEAKERS, [{"speaker": i % 2, "text": "x" * 400} for i in range(14)], "up to 5000"),
])
def test_a_dialogue_that_cannot_be_made_is_refused(speakers, lines, match):
    with pytest.raises(ValueError, match=match):
        vm.dialogue_request(speakers, lines)


# ---------- the routes ----------

@pytest.fixture
def calls(monkeypatch):
    made = []

    def runner(kind):
        def run(req, **kw):
            made.append({"kind": kind, "req": req, **kw})
            return {"ok": True, "audio": "asset:51", "seconds": 6.4,
                    "stored": "cut/media/voice.mp3", "generation_id": 3}
        return run

    monkeypatch.setattr(vm, "run_library", runner("library"))
    monkeypatch.setattr(vm, "run_dialogue", runner("dialogue"))
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


def test_the_menu_carries_both_models_and_no_dollars(client):
    body = client.get("/api/voice").json()
    kinds = [m["kind"] for m in body["models"]]
    assert kinds == ["speak", "library", "dialogue", "clone", "dub"]
    langs = [x["language"] for x in body["library"]["languages"]]
    assert langs[0] == "English" and "Japanese" in langs
    assert body["library"]["default_voice"] == "Wise_Woman"
    assert body["dialogue"]["presets"] == list(vm.DIALOGUE_PRESETS)
    assert body["dialogue"]["max_speakers"] == 4
    assert "$" not in json.dumps(body)


def test_a_library_read_runs_only_at_the_shown_price_and_is_filed(client, calls):
    ask = {"script": SCRIPT, "voice": "English_Graceful_Lady", "emotion": "sad", "speed": 0.9}
    q = client.post("/api/voice/library/quote", json=ask).json()
    credits = ledger.charge_credits(vm.library_usd(SCRIPT))
    assert q["credits"] == credits and q["language"] == "English" and calls == []
    r = client.post("/api/voice/library/run", json={**ask, "expect_credits": credits + 1})
    assert r.status_code == 409 and calls == []
    r = client.post("/api/voice/library/run", json=ask)
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_price"
    r = client.post("/api/voice/library/run", json={**ask, "expect_credits": credits})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done" and job["audio"] == "asset:51" and job["media"] == "audio"
    assert "Graceful Lady" in job["detail"]
    (c,) = calls
    assert c["kind"] == "library" and c["account_id"] == ACCOUNT
    assert c["req"]["voice"] == "English_Graceful_Lady" and c["req"]["emotion"] == "sad"


def test_a_dialogue_runs_only_at_the_shown_price_and_is_filed(client, calls):
    ask = {"speakers": SPEAKERS, "lines": LINES}
    q = client.post("/api/voice/dialogue/quote", json=ask).json()
    req = vm.dialogue_request(SPEAKERS, LINES)
    assert q["credits"] == ledger.charge_credits(req["usd"])
    assert q["estimate_seconds"] == req["estimate_seconds"] and q["speakers"] == 2
    assert calls == []
    r = client.post("/api/voice/dialogue/run", json={**ask, "expect_credits": q["credits"] - 1})
    assert r.status_code == 409 and calls == []
    r = client.post("/api/voice/dialogue/run", json={**ask, "expect_credits": q["credits"]})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done" and job["audio"] == "asset:51"
    (c,) = calls
    assert c["kind"] == "dialogue" and c["req"]["script"].startswith("Speaker 0: ")


def test_a_bad_dialogue_is_refused_before_a_price(client):
    r = client.post("/api/voice/dialogue/quote", json={"speakers": SPEAKERS, "lines": [{"speaker": 5, "text": "x"}]})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_voice"


def test_a_read_that_fails_says_nothing_was_charged(client, monkeypatch):
    monkeypatch.setattr(vm, "run_library", lambda req, **kw: {"ok": False, "error": "fal: boom"})
    credits = ledger.charge_credits(vm.library_usd(SCRIPT))
    r = client.post("/api/voice/library/run", json={"script": SCRIPT, "expect_credits": credits})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "failed" and "Nothing was charged" in json.dumps(job)


def test_file_audio_files_the_read_and_says_when_it_cannot(tmp_path, monkeypatch):
    from src.cut import uploads
    f = tmp_path / "out.mp3"
    f.write_bytes(b"ID3fake")
    saved = []

    def save(data, name, **kw):
        saved.append(name)
        return {"handle": "asset:9", "info": {"seconds": 2.0}, "stored": "cut/media/x.mp3"}

    monkeypatch.setattr(uploads, "save", save)
    out = vm.file_audio({"ok": True, "path": str(f), "generation_id": 1}, "dialogue", account_id=1)
    assert out == {"ok": True, "audio": "asset:9", "seconds": 2.0, "stored": "cut/media/x.mp3",
                   "generation_id": 1}
    assert saved == ["dialogue.mp3"]
    assert vm.file_audio({"ok": False, "error": "x"}, "d", account_id=1) == {"ok": False, "error": "x"}

    def refuse(*a, **kw):
        raise uploads.UploadRefused("too_big", "too big")

    monkeypatch.setattr(uploads, "save", refuse)
    bad = vm.file_audio({"ok": True, "path": str(f), "generation_id": 1}, "d", account_id=1)
    assert bad["ok"] is False and "paid for but could not be filed" in bad["error"]
