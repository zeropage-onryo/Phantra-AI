"""A voiceover for a cut (src/voiceover.py, the editor's Voiceover card): the
kit's default voice when its line names one, priced per character before it
is read, made through effects.run (the hold, the row, settle), filed as an
asset:<id> audio. fal is replaced at effects.run everywhere here; nothing is
generated or charged.
"""
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, brand_kits, effects, fal, ledger, preprod, projects, voiceover
from src import talking_photo as tp
from src.cut import doc as d
from src.cut import render, store

client = TestClient(app)
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
LINE = "Try Rachel first, warm and unhurried"


def _kit(line):
    return {"spec": brand_kits.clean_spec({"sound": {"voice": line}})}


# --------------------------------------------------------------------------
# the request: priced, checked, nothing spent
# --------------------------------------------------------------------------

def test_the_kit_line_picks_a_voice_only_when_it_names_one():
    assert voiceover.kit_voice(_kit("George, low and calm")) == "George"
    assert voiceover.kit_voice(_kit("a calm george")) == "George"       # any case
    assert voiceover.kit_voice(_kit("warm, mid-30s, unhurried")) is None
    assert voiceover.kit_voice(_kit("Williams-style")) is None          # whole words only
    assert voiceover.kit_voice(None) is None and voiceover.kit_line(None) == ""
    assert voiceover.kit_line(_kit(LINE)) == LINE


def test_a_voiceover_is_priced_per_character_and_a_pick_beats_the_kit():
    req = voiceover.request("Book a sitter tonight.", kit=_kit("George, low"))
    assert req["voice"] == "George" and req["characters"] == 22
    assert req["usd"] == tp.voice_usd("Book a sitter tonight.")
    assert voiceover.request("Hi there.", "aria", kit=_kit("George"))["voice"] == "Aria"
    assert voiceover.request("Hi there.", kit=_kit("warm, mid-30s"))["voice"] == tp.DEFAULT_VOICE
    # three words are a voiceover: no talking-photo floor here
    assert voiceover.request("Three short words.")["characters"] == 18


def test_a_voiceover_off_the_table_is_refused():
    with pytest.raises(ValueError, match="voice must be one of"):
        voiceover.request("Hello.", "Morgan")
    with pytest.raises(ValueError, match="write the words"):
        voiceover.request("   ")
    with pytest.raises(ValueError, match="up to 5000"):
        voiceover.request("x" * 5001)
    with pytest.raises(ValueError, match="two-letter code"):
        voiceover.request("Hello.", language="english")


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
    mine = accounts.upsert_account("vo-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("vo-theirs", "Theirs", "#fff", dsn=pg)
    return pg, mine, theirs, tmp_path


def _wav(path, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=f=220:d={seconds}", str(path)], check=True)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_run_sends_the_voice_body_and_files_the_read(dbx, monkeypatch):
    pg, mine, _, tmp = dbx
    made = tmp / "read.mp3"
    _wav(made)
    seen = {}

    def fake_run(effect, urls, prompt, options, **kw):
        seen.update(effect=effect, usd=kw["usd"], body=kw["endpoint_body"], row=kw["row"],
                    extra=kw["extra"], project=kw["project_id"])
        return {"ok": True, "path": str(made), "generation_id": 9}

    monkeypatch.setattr(effects, "run", fake_run)
    req = voiceover.request("Book a sitter tonight.", "George", "en")
    got = voiceover.run(req, account_id=mine, dsn=pg, source="editor", project_id=5)
    assert got["ok"] and got["audio"].startswith("asset:") and abs(got["seconds"] - 2) < 0.2
    assert seen["effect"] == "voiceover-eleven-v3" and seen["usd"] == req["usd"]
    assert seen["body"] == ("fal-ai/elevenlabs/tts/eleven-v3",
                            {"text": "Book a sitter tonight.", "voice": "George",
                             "language_code": "en"})
    assert seen["row"]["output"] == "audio" and seen["project"] == 5
    assert seen["extra"]["voiceover"]["characters"] == 22
    row = store.get_media(int(got["audio"].split(":")[1]), account_id=mine, dsn=pg)
    assert row["kind"] == "audio" and row["filename"] == "voiceover-george.mp3"


def test_a_failed_read_is_said_and_nothing_is_filed(dbx, monkeypatch):
    pg, mine, _, _ = dbx
    monkeypatch.setattr(effects, "run", lambda *a, **k: {"ok": False, "error": "fal said no"})
    got = voiceover.run(voiceover.request("Hello."), account_id=mine, dsn=pg, source="editor")
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


def _cut(pg, account, project=None):
    row = store.create_project(account_id=account, title="Ad", dsn=pg,
                               studio_project_id=project)
    doc = d.new_doc()
    doc["duration"] = 300
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": []},
                     {"id": "G1", "kind": "graphic", "items": [
                         {"id": "g1", "start": 0, "end": 300, "type": "headline",
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


def test_the_card_starts_on_the_kits_voice_and_holds_the_run_to_its_price(signed_in, monkeypatch):
    pg, mine, theirs, _ = signed_in
    kit = brand_kits.create("Gygler", {"sound": {"voice": LINE}}, pg, account_id=mine)
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    cut = _cut(pg, mine, project["id"])

    menu = client.get(f"/api/cut/projects/{cut}/voiceover").json()
    assert menu["default_voice"] == "Rachel" and menu["kit_voice"] == "Rachel"
    assert menu["kit_line"] == LINE and menu["kit_name"] == "Gygler"
    assert menu["voices"] == list(tp.VOICES) and menu["ready"] is True

    script = "Book a sitter tonight."
    quote = client.post(f"/api/cut/projects/{cut}/voiceover/quote",
                        json={"script": script}).json()
    assert quote["voice"] == "Rachel" and quote["characters"] == 22
    assert quote["credits"] == ledger.charge_credits(tp.voice_usd(script))
    bad = client.post(f"/api/cut/projects/{cut}/voiceover/quote",
                      json={"script": script, "voice": "Morgan"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "bad_voiceover"

    run = f"/api/cut/projects/{cut}/voiceover/run"
    assert client.post(run, json={"script": script}).json()["error"]["code"] == "missing_price"
    moved = client.post(run, json={"script": script, "expect_credits": quote["credits"] + 1})
    assert moved.status_code == 409 and moved.json()["credits"] == quote["credits"]

    sent = {}

    def fake(req, **kw):
        sent.update(req=req, kw=kw)
        return {"ok": True, "audio": "asset:43", "seconds": 1.6, "stored": "/x.mp3",
                "generation_id": 1}

    monkeypatch.setattr(voiceover, "run", fake)
    job = _wait(client.post(run, json={"script": script, "voice": "George",
                                       "expect_credits": quote["credits"]}).json()["job_id"])
    assert job["status"] == "done" and job["audio"] == "asset:43" and job["seconds"] == 1.6
    assert sent["req"]["voice"] == "George" and sent["req"]["script"] == script
    assert sent["kw"]["project_id"] == project["id"] and sent["kw"]["source"] == "editor"

    # no kit: the model's default, and no line
    plain = client.get(f"/api/cut/projects/{_cut(pg, mine)}/voiceover").json()
    assert plain["default_voice"] == tp.DEFAULT_VOICE and plain["kit_voice"] is None
    assert plain["kit_line"] == "" and plain["kit_name"] is None

    # someone else's cut is not there
    app.dependency_overrides[auth.current_account_id] = lambda: theirs
    assert client.get(f"/api/cut/projects/{cut}/voiceover").status_code == 404


def test_without_a_fal_key_the_card_says_so_and_nothing_runs(signed_in, monkeypatch):
    pg, mine, _, _ = signed_in
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    cut = _cut(pg, mine)
    assert client.get(f"/api/cut/projects/{cut}/voiceover").json()["ready"] is False
    script = "Hello there."
    credits = ledger.charge_credits(tp.voice_usd(script))
    res = client.post(f"/api/cut/projects/{cut}/voiceover/run",
                      json={"script": script, "expect_credits": credits})
    assert res.status_code == 503 and res.json()["error"]["code"] == "voiceover_unavailable"


# --------------------------------------------------------------------------
# writing the script: free, one model call, checked
# --------------------------------------------------------------------------

TONE = {"voice": {"tone": "warm, direct", "avoid": ["cheap", "hustle"], "cta": "an invitation"},
        "identity": {"tagline": "Get a Gyg, stay for good."}}
SCREEN_DOC = {"fps": 30, "duration": 300, "tracks": [
    {"id": "G2", "kind": "graphic", "items": [
        {"id": "b", "start": 120, "end": 200, "type": "headline", "text": "Book in seconds."},
        {"id": "a", "start": 0, "end": 100, "type": "headline", "text": "Find the right talent."},
        {"id": "w", "start": 0, "end": 100, "type": "background_word", "text": "FIND"},
        {"id": "c", "start": 210, "end": 300, "type": "label", "text": "Gygler.com"}]},
    {"id": "C1", "kind": "caption", "cues": [
        {"id": "q", "start": 60, "end": 90, "text": "Rated 4.8 by 200 venues"}]}]}


def test_the_screen_is_read_in_time_order_without_the_big_words():
    assert voiceover.screen_lines(SCREEN_DOC) == [
        "Find the right talent.", "Rated 4.8 by 200 venues", "Book in seconds.", "Gygler.com"]


def test_the_prompt_carries_the_kit_the_screen_and_the_length():
    kit = {"name": "Gygler", "spec": brand_kits.clean_spec(TONE)}
    prompt = voiceover.build_prompt(SCREEN_DOC, kit, "mention the app store")
    assert "Tone: warm, direct" in prompt and "Words never to use: cheap, hustle" in prompt
    assert "- Book in seconds." in prompt and "mention the app store" in prompt
    assert "10 seconds" in prompt and "about 25 words" in prompt and "{" not in prompt
    bare = voiceover.build_prompt({"fps": 30, "duration": 150, "tracks": []}, None)
    assert "No brand kit" in bare and "the picture carries no text" in bare


def test_a_script_is_checked_and_each_problem_is_a_warning():
    kit = {"name": "Gygler", "spec": brand_kits.clean_spec(TONE)}
    seen = {}

    def model(prompt, account_id=None):
        seen["prompt"] = prompt
        return {"script": '"Find great people fast. Rated 4.8, from just $9. No hustle."'}

    got = voiceover.write_script(SCREEN_DOC, kit, account_id=1, model=model)
    assert got["script"] == "Find great people fast. Rated 4.8, from just $9. No hustle."
    assert got["words"] == 11
    joined = " | ".join(got["warnings"])
    assert "9, which nothing above gives" in joined and "4.8" not in joined
    assert "uses hustle" in joined
    long = voiceover.write_script(SCREEN_DOC, None, account_id=1,
                                  model=lambda p, account_id=None: {"script": "word " * 40})
    assert "40 words" in long["warnings"][0]


def test_a_failed_or_empty_script_is_said_not_raised_as_a_crash():
    def boom(prompt, account_id=None):
        raise TimeoutError("slow")
    with pytest.raises(voiceover.ScriptError, match="TimeoutError"):
        voiceover.write_script(SCREEN_DOC, None, account_id=1, model=boom)
    with pytest.raises(voiceover.ScriptError, match="empty"):
        voiceover.write_script(SCREEN_DOC, None, account_id=1,
                               model=lambda p, account_id=None: {"script": "  "})


def test_the_script_route_writes_from_the_head_and_spends_nothing(signed_in, monkeypatch):
    from src import charge
    pg, mine, theirs, _ = signed_in
    monkeypatch.setattr(charge, "create_refusal_code", lambda account_id: None)
    kit = brand_kits.create("Gygler", TONE, pg, account_id=mine)
    project = projects.create("Launch", "", pg, account_id=mine)
    projects.set_brand_kit(project["id"], kit["id"], pg, account_id=mine)
    cut = _cut(pg, mine, project["id"])
    seen = {}

    def model(prompt, account_id=None):
        seen.update(prompt=prompt, account=account_id)
        return {"script": "Find the people you need. Get a Gyg, stay for good."}

    monkeypatch.setattr(voiceover, "_model", model)
    monkeypatch.setattr(effects, "run", lambda *a, **k: pytest.fail("a script must not spend"))
    job = _wait(client.post(f"/api/cut/projects/{cut}/voiceover/script",
                            json={"direction": "keep it short"}).json()["job_id"])
    assert job["status"] == "done" and job["script"].startswith("Find the people")
    assert job["warnings"] == [] and job["words"] == 11
    assert "- Hi." in seen["prompt"] and "keep it short" in seen["prompt"]
    assert "warm, direct" in seen["prompt"] and seen["account"] == mine

    monkeypatch.setattr(charge, "create_refusal_code",
                        lambda account_id: ("subscribe_or_top_up", "add credits"))
    refused = client.post(f"/api/cut/projects/{cut}/voiceover/script", json={})
    assert refused.status_code == 402

    app.dependency_overrides[auth.current_account_id] = lambda: theirs
    monkeypatch.setattr(charge, "create_refusal_code", lambda account_id: None)
    assert client.post(f"/api/cut/projects/{cut}/voiceover/script", json={}).status_code == 404
