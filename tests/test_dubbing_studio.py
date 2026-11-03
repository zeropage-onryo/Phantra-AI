"""Dubbing from the studio (2026-10-26, docs/tasks/task-dubbing.md).

The connector had the feature first; these routes are the studio card's door
onto the same body (src/dubbing.py). What they hold: every spend runs at the
price the card showed or not at all (409), the consent box is asked before
the run, a clip is an id and never an address, and the menu says nothing in
dollars.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import dubbing, effects, fal, guide_tools, ledger, mcp_server

ACCOUNT = 42
ASK = {"source": "gen:12", "target_language": "es"}
CREDITS_1MIN = ledger.charge_credits(0.6)


@pytest.fixture
def world(monkeypatch):
    from src import render_assets
    from src.cut import store as cut_store
    media = {6: {"id": 6, "kind": "video", "media_url": "https://r2/c6.mp4", "output_path": ""},
             5: {"id": 5, "kind": "audio", "media_url": "https://r2/v.mp3", "output_path": ""}}
    renders = {12: {"id": 12, "media_kind": "video", "media_url": "https://r2/c12.mp4",
                    "output_path": "", "deleted_at": None}}
    monkeypatch.setattr(cut_store, "get_media",
                        lambda i, account_id=None, dsn=None: media.get(int(i)))
    monkeypatch.setattr(render_assets, "get",
                        lambda i, dsn=None, account_id=None: renders.get(int(i)))
    monkeypatch.setattr(mcp_server, "_clip_file",
                        lambda row, account_id: (row["media_url"], ".mp4", None))
    state = {"probe": {"seconds": 8.0, "width": 1280, "height": 720, "fps": 24.0},
             "sound": True}
    monkeypatch.setattr(effects, "probe_video", lambda target: state["probe"])
    monkeypatch.setattr(dubbing, "has_sound", lambda target: state["sound"])
    monkeypatch.setattr(effects, "fetchable_video", lambda url, local="", account_id=None: url)
    calls = []

    def run(req, **kw):
        calls.append({"req": req, **kw})
        return {"ok": True, "media_url": "https://r2/dubbed.mp4", "asset_id": 88,
                "media_kind": "video", "error": None}

    monkeypatch.setattr(dubbing, "run", run)
    return {"state": state, "calls": calls}


@pytest.fixture
def client(world, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "dub-user"})
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


def test_the_menu_lists_the_languages_and_the_limit_in_no_dollars(client):
    body = client.get("/api/dubbing").json()
    assert [x["code"] for x in body["languages"]] == list(dubbing.LANGUAGE_CODES)
    assert body["max_seconds"] == 300 and body["speakers_max"] == 50
    assert body["ready"] is True and "$" not in json.dumps(body)


def test_the_dub_is_priced_by_the_clips_minutes_and_nothing_runs(client, world):
    q = client.post("/api/dubbing/quote", json=ASK).json()
    assert q["credits"] == CREDITS_1MIN == 144 and q["billed_minutes"] == 1
    assert q["language"] == "Spanish" and q["clip_seconds"] == 8.0 and q["charged"] is True
    assert world["calls"] == []
    world["state"]["probe"] = {"seconds": 61.0, "width": 1, "height": 1, "fps": 24.0}
    assert client.post("/api/dubbing/quote", json=ASK).json()["credits"] == \
        ledger.charge_credits(1.2)


@pytest.mark.parametrize("body, match", [
    ({**ASK, "source": "https://x/c.mp4"}, "URLs are never taken"),
    ({**ASK, "source": "asset:5"}, "this takes a clip"),
    ({**ASK, "source": "gen:404"}, "no render 404"),
    ({**ASK, "source": ""}, "needs `source`"),
    ({**ASK, "target_language": "it"}, "target language must be one of"),
    ({**ASK, "source_language": "es"}, "already in Spanish"),
    ({**ASK, "speakers": 60}, "1 to 50"),
])
def test_a_dub_that_cannot_be_made_is_refused_before_a_price(client, body, match):
    r = client.post("/api/dubbing/quote", json=body)
    assert r.status_code == 400 and match in r.json()["error"]["message"]
    assert r.json()["error"]["code"] == "bad_dubbing"


def test_a_clip_with_no_voice_is_refused(client, world):
    world["state"]["sound"] = False
    r = client.post("/api/dubbing/quote", json=ASK)
    assert r.status_code == 400 and "no sound track" in r.json()["error"]["message"]


def test_the_run_needs_the_consent_box_and_the_shown_price(client, world):
    r = client.post("/api/dubbing/run", json={**ASK, "expect_credits": CREDITS_1MIN})
    assert r.status_code == 400 and "consent" in r.json()["error"]["message"]
    r = client.post("/api/dubbing/run", json={**ASK, "consent": True})
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_price"
    r = client.post("/api/dubbing/run",
                    json={**ASK, "consent": True, "expect_credits": CREDITS_1MIN - 1})
    assert r.status_code == 409 and r.json()["credits"] == CREDITS_1MIN
    assert world["calls"] == []


def test_an_approved_dub_runs_into_the_library(client, world):
    r = client.post("/api/dubbing/run",
                    json={**ASK, "consent": True, "source_language": "en", "speakers": 2,
                          "expect_credits": CREDITS_1MIN})
    assert r.json()["credits"] == CREDITS_1MIN
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["asset"] == "gen:88" and job["media"] == "video"
    assert job["output"] == "https://r2/dubbed.mp4"
    (c,) = world["calls"]
    assert c["account_id"] == ACCOUNT and c["source"] == "composer"
    assert c["req"]["target"] == "es" and c["req"]["source_lang"] == "en"
    assert c["req"]["speakers"] == 2 and c["req"]["usd"] == 0.6
    assert c["req"]["video_url"] == "https://r2/c12.mp4"


def test_a_dub_that_fails_says_so_in_plain_words(client, world, monkeypatch):
    monkeypatch.setattr(dubbing, "run", lambda req, **kw: {"ok": False, "error": "fal: boom"})
    r = client.post("/api/dubbing/run",
                    json={**ASK, "consent": True, "expect_credits": CREDITS_1MIN})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "failed" and "Nothing was charged" in json.dumps(job)


def test_without_a_fal_key_the_run_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    r = client.post("/api/dubbing/run",
                    json={**ASK, "consent": True, "expect_credits": CREDITS_1MIN})
    assert r.status_code == 503 and r.json()["error"]["code"] == "effects_unavailable"


def test_a_project_that_is_not_yours_is_refused(client, monkeypatch):
    from src import projects
    monkeypatch.setattr(projects, "get", lambda pid, dsn=None, account_id=None: None)
    r = client.post("/api/dubbing/quote", json={**ASK, "project_id": 9})
    assert r.status_code == 400 and "no project 9" in r.json()["error"]["message"]


# ---------- the brain opens the card, never spends ----------

RESULTS = [{"n": 1, "kind": "still", "label": ""}, {"n": 2, "kind": "clip", "label": ""}]


def test_the_brain_proposes_the_card_with_a_clip_and_a_language():
    args = guide_tools.check_args("dub_clip", {"on": 2, "target_language": " ES "}, RESULTS)
    assert args == {"on": 2, "target_language": "es"}
    assert guide_tools.check_args("dub_clip", {}, RESULTS) == {}
    assert guide_tools.is_make("dub_clip") and guide_tools.is_write("dub_clip")
    with pytest.raises(guide_tools.Refused, match="takes a clip"):
        guide_tools.check_args("dub_clip", {"on": 1}, RESULTS)
    with pytest.raises(guide_tools.Refused, match="target language must be one of"):
        guide_tools.check_args("dub_clip", {"target_language": "klingon"}, RESULTS)
    line = guide_tools.dub_line(args)
    assert "Spanish" in line and "click" in line and "$" not in line


def test_the_card_is_offered_only_to_the_composer_and_never_run_by_the_server(client):
    names = lambda **k: {s["name"] for s in guide_tools.session(local=True, **k)[0]}  # noqa: E731
    assert "dub_clip" in names(maker=True)
    assert "dub_clip" not in names(maker=True, makes=("make_image",))
    assert "dub_clip" not in names()
    with pytest.raises(guide_tools.Refused):
        guide_tools.run("dub_clip", {})
    r = client.post("/api/creative-guide/act", json={"tool": "dub_clip", "args": {}},
                    headers={"x-phantra-model-connection": "1"})
    assert r.status_code == 400 and "studio's send" in r.json()["error"]["message"]
