"""
A talking photo -- a photo of a person and a voice -> a clip of them saying
it (2026-10-20, docs/tasks/task-talking-photo.md).

Two spends, each quoted and approved on its own: a voice preview (a typed
script read aloud, priced per character) and the clip (OmniHuman v2, priced
per second of the voice, rounded up). What is guarded: the table as read on
2026-10-20, every refusal before a quote, the wire bodies, and the whole
conversation on the real ledger with only fal's wire stood in for.
"""

import asyncio
import shutil
import subprocess

import pytest

from src import effects, fal, ledger, mcp_server, mcp_shapes, pricing
from src import talking_photo as tp

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg is not installed")


# --------------------------------------------------------------------------
# the table
# --------------------------------------------------------------------------

def test_the_rows_are_the_ones_read_off_fal_that_day():
    assert tp.CHECKED == "2026-10-20"
    assert tp.TALK["endpoint"] == "bytedance/omnihuman/v2" and tp.TALK["usd_per_second"] == 0.105
    assert tp.VOICE["endpoint"] == "fal-ai/elevenlabs/tts/eleven-v3"
    assert tp.VOICE["usd_per_1k_chars"] == 0.10
    for row in (tp.TALK, tp.VOICE):
        assert row["source"].startswith("https://fal.ai/models/")
    # not a menu entry apply_effect could run without its voice
    assert not {tp.TALK["endpoint"], tp.VOICE["endpoint"]} & \
        {r["endpoint"] for r in effects.EFFECTS.values()}


def test_the_plan_caps_are_mikes_and_their_dearest_clips():
    assert tp.PLAN_AUDIO_CAP == {"starter": 30, "creator": 60, "studio": 120}
    assert set(tp.PLAN_AUDIO_CAP) == set(pricing.PLANS)
    assert [tp.talk_usd(s) for s in (30, 60, 120)] == [3.15, 6.3, 12.6]


@pytest.mark.parametrize("seconds, billed, usd", [
    (4.0, 4, 0.42), (10.0, 10, 1.05), (10.04, 11, 1.155), (29.999, 30, 3.15),
])
def test_the_clip_is_priced_per_whole_second_of_voice_rounded_up(seconds, billed, usd):
    assert tp.billed_seconds(seconds) == billed and tp.talk_usd(seconds) == usd


def test_credits_carry_the_standard_markup_and_floor():
    # 10s = $1.05 -> 2.4x -> 252 credits; 30s of speech (~450 characters) is
    # $0.045 -> 11 credits, and a short preview is the floor
    assert ledger.charge_credits(tp.talk_usd(10)) == 252
    assert ledger.charge_credits(tp.voice_usd("x" * 450)) == 11
    assert ledger.charge_credits(tp.voice_usd("x" * 200)) == pricing.CREDIT_FLOOR == 10


@pytest.mark.parametrize("seconds, kw, match", [
    (3.9, {}, "at least 4s"),
    (31.0, {}, "up to 30s"),
    (10, {"suffix": ".m4a"}, "an .mp3 or .wav"),
    (10, {"size_bytes": 16 * 1024 * 1024}, "up to 15MB"),
    (None, {}, "could not be measured"),
])
def test_a_voice_outside_the_limits_is_refused(seconds, kw, match):
    args = {"suffix": ".mp3", "size_bytes": 1000, "cap": 30, **kw}
    with pytest.raises(ValueError, match=match):
        tp.check_audio(seconds, **args)


def test_a_bigger_plan_takes_a_longer_voice_and_a_30s_file_is_30s():
    assert tp.check_audio(30.04, suffix=".mp3", size_bytes=1, cap=30) == 30.04
    assert tp.check_audio(90, suffix=".wav", size_bytes=1, cap=120) == 90


@pytest.mark.parametrize("w, h, match", [
    (200, 400, "300 to 6000"), (7000, 4000, "300 to 6000"),
    (300, 1000, "too narrow or too wide"), (None, None, "could not be read"),
])
def test_a_photo_the_model_cannot_take_is_refused(w, h, match):
    with pytest.raises(ValueError, match=match):
        tp.check_image(w, h)


def test_the_script_voice_and_language_are_checked():
    with pytest.raises(ValueError, match="at least 50 characters"):
        tp.check_script("Hi there!")
    with pytest.raises(ValueError, match="up to 5000"):
        tp.check_script("a" * 5001)
    with pytest.raises(ValueError, match="voice must be one of"):
        tp.check_voice("Morgan Freeman")
    assert tp.check_voice("") == "Rachel" and tp.check_voice("aria") == "Aria"
    assert tp.check_language(" EN ") == "en" and tp.check_language("") is None
    with pytest.raises(ValueError, match="two-letter"):
        tp.check_language("english")


def test_the_wire_bodies_are_the_schemas():
    assert tp.talk_body("https://i", "https://a") == (
        "bytedance/omnihuman/v2", {"image_url": "https://i", "audio_url": "https://a"})
    assert tp.talk_body("https://i", "https://a", "slow push in")[1]["prompt"] == "slow push in"
    assert tp.voice_body("hello", "Aria", "es") == (
        "fal-ai/elevenlabs/tts/eleven-v3",
        {"text": "hello", "voice": "Aria", "language_code": "es"})


def test_the_plan_cap_follows_the_account(monkeypatch):
    from src import accounts
    monkeypatch.setattr(accounts, "plan_of", lambda a, dsn=None: {1: "studio", 2: None}[a])
    assert tp.audio_cap(1) == 120 and tp.audio_cap(2) == 30 and tp.audio_cap(None) == 30


# --------------------------------------------------------------------------
# the tools, with the voice row, the photo and fal stood in for
# --------------------------------------------------------------------------

SCRIPT = ("Hi, I'm Maya. Welcome to the shop -- everything you see here was "
          "made by hand, in this room.")


@pytest.fixture
def signed(monkeypatch):
    monkeypatch.setenv(pricing.SIGNING_ENV, "test-quote-secret")


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
    calls = []

    def run(effect, urls, prompt, opts, **kw):
        calls.append({"effect": effect, "urls": urls, "prompt": prompt, **kw})
        return {"ok": True, "media_url": "https://r2/out.mp4", "asset_id": 77,
                "media_kind": "video", "error": None}

    monkeypatch.setattr(effects, "run", run)
    return {"media": media, "calls": calls}


ASK = dict(photo="gen:12", audio="asset:5", consent=True)


def test_the_clip_is_quoted_on_the_voices_measured_length(world, signed):
    q = mcp_server.run_talking_photo(**ASK)
    assert q["needs_approval"] and world["calls"] == []
    quote = q["quote"]
    assert quote["audio_seconds"] == 10.04 and quote["billed_seconds"] == 11
    assert quote["usd"] == 1.155 and quote["credits"] == ledger.charge_credits(1.155)
    assert quote["plan_cap_seconds"] == 30 and quote["photo_size"] == "1024x1536"


def test_an_approved_clip_sends_the_photo_and_the_voice(world, signed):
    q = mcp_server.run_talking_photo(**ASK, prompt="  a slow   push in ")
    out = mcp_server.run_talking_photo(**ASK, prompt="a slow push in",
                                       quote_token=q["quote"]["quote_token"])
    (c,) = world["calls"]
    assert c["row"] == {"label": "OmniHuman v2", "output": "video"}
    assert c["endpoint_body"] == ("bytedance/omnihuman/v2", {
        "image_url": "https://r2/face.jpg", "audio_url": "https://r2/v.mp3",
        "prompt": "a slow push in"})
    assert c["sources"] == ["gen:12", "asset:5"] and c["usd"] == 1.155
    assert c["quote"].credits == q["quote"]["credits"]
    assert c["extra"]["talking_photo"]["consent"] is True
    assert out["ok"] and out["asset_id"] == 77


@pytest.mark.parametrize("kwargs, match", [
    ({**ASK, "consent": False}, "consent"),
    ({**ASK, "audio": "https://x/v.mp3"}, "URLs are never taken"),
    ({**ASK, "audio": "asset:9"}, "no upload 9"),
    ({**ASK, "audio": "asset:6"}, "must be sound"),
    ({**ASK, "photo": ""}, "needs `photo`"),
    ({**ASK, "prompt": "x" * 1001}, "keep it under"),
])
def test_refusals_come_before_any_quote(world, signed, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mcp_server.run_talking_photo(**kwargs)
    assert world["calls"] == []


def test_a_voice_over_the_plans_cap_is_refused_before_a_quote(world, signed):
    world["media"][5]["seconds"] = 45.0
    with pytest.raises(ValueError, match="up to 30s"):
        mcp_server.run_talking_photo(**ASK)


def test_a_changed_voice_after_the_yes_is_refused(world, signed):
    q = mcp_server.run_talking_photo(**ASK)
    world["media"][7] = {**world["media"][5], "id": 7}
    with pytest.raises(ValueError):
        mcp_server.run_talking_photo(**{**ASK, "audio": "asset:7"},
                                     quote_token=q["quote"]["quote_token"])
    assert world["calls"] == []


def test_the_voice_preview_is_quoted_by_the_script(world, signed):
    q = mcp_server.run_voice_preview(SCRIPT, voice="aria")
    assert q["needs_approval"] and world["calls"] == []
    assert q["quote"]["voice"] == "Aria" and q["quote"]["characters"] == len(SCRIPT)
    assert q["quote"]["credits"] == 10


def test_the_tools_are_studio_only_and_answer_typed(pg, world, signed):
    from src import preprod
    preprod.init(pg)
    server = mcp_server.build_server(dsn=pg, surface="studio")
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"voice_preview", "talking_photo"} <= names
    res = asyncio.run(server.call_tool("talking_photo", dict(ASK)))
    data = res.structured_content
    mcp_shapes.SpendResult.model_validate(data)
    assert data["state"] == "quote" and data["quote"]["billed_seconds"] == 11
    for listed in (dict(listed=True), dict(listed="claude")):
        offered = {t.name for t in asyncio.run(
            mcp_server.build_server(dsn=pg, **listed).list_tools())}
        assert not {"voice_preview", "talking_photo"} & offered


# --------------------------------------------------------------------------
# the conversation, on the real ledger, the real media bin and the real
# wall: script -> voice -> listen -> clip. Only fal's wire, the bucket and
# the photo's measurement are stood in for.
# --------------------------------------------------------------------------

@pytest.fixture
def studio(pg, monkeypatch, tmp_path):
    import types

    from src import accounts, db, generative, preprod, quote_redemptions, render_assets
    from src.cut import render as cut_render
    from src.cut import store as cut_store
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("FAL_KEY", "k")
    monkeypatch.setenv(pricing.SIGNING_ENV, "test-quote-secret")
    monkeypatch.setattr(fal, "POLL_SECONDS", 0)
    for mod in (preprod, generative, render_assets, ledger, quote_redemptions, cut_store):
        mod.init(pg)
    accounts.seed("mike@example.com", dsn=pg)
    with db.connect(pg) as conn:
        acct = int(conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"])
    ledger.grant(acct, 1000, "purchase", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    still = render_assets.record(generation_id=9002, tool="fal", model="flux",
                                 media_kind="image", prompt="a woman behind a shop counter",
                                 media_url="https://r2/m/1/renders/fal/face.png",
                                 output_path="", account_id=acct, dsn=pg)
    monkeypatch.setattr(cut_render, "CUT_DIR", tmp_path / "cut")
    monkeypatch.setattr(mcp_server, "_fetchable", lambda raw, a: raw)
    monkeypatch.setattr(tp, "image_size", lambda t: (1024, 1536))
    monkeypatch.setattr(tp, "fetchable_audio",
                        lambda url, local="", account_id=None: "https://r2/voice.mp3")
    from src import media
    monkeypatch.setattr(media, "mirror", lambda *a, **k: None)

    def download(url, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix == ".mp3":           # the voice: six real seconds of sound
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "6.2",
                            "-i", "sine=frequency=220", "-c:a", "libmp3lame", str(out)],
                           check=True, capture_output=True)
        else:
            out.write_bytes(b"\x00" * 2048)
        return out

    monkeypatch.setattr(fal, "_download", download)
    monkeypatch.setattr(fal, "_publish",
                        lambda path, ctype, acct=None: f"https://r2/m/1/renders/fal/{path.name}")
    sent = []

    def wire(url, payload=None, account_id=None):
        if payload is not None and payload is not fal.CANCEL:
            sent.append((url, payload))
            return {"request_id": "r", "status_url": "https://q/s", "response_url": "https://q/r",
                    "cancel_url": "https://q/c"}
        if url == "https://q/s":
            return {"status": "COMPLETED"}
        if "elevenlabs" in sent[-1][0]:
            return {"audio": {"url": "https://cdn/voice.mp3"}}
        return {"video": {"url": "https://cdn/talk.mp4"}, "duration": 6.2}

    monkeypatch.setattr(fal, "_request", wire)
    results = []

    def start_job(kind, label, fn, cancellable=False, account_id=None):
        results.append(fn({})["result"])
        return {"id": len(results), "status": "done"}

    server = mcp_server.build_server(dsn=pg, surface="studio", start_job=start_job,
                                     job_status=lambda i, account_id=None: None,
                                     account_id=acct)
    return types.SimpleNamespace(dsn=pg, account_id=acct, server=server, sent=sent,
                                 results=results, photo=f"gen:{still['id']}")


def _tool(studio, name, **args):
    return asyncio.run(studio.server.call_tool(name, args)).structured_content


@needs_ffmpeg
def test_script_then_voice_then_clip_charges_each_once(studio):
    balance = lambda: ledger.available(studio.account_id, dsn=studio.dsn)   # noqa: E731

    # 1. the voice: quoted by its characters, approved, read, filed in the bin
    q1 = _tool(studio, "voice_preview", script=SCRIPT, voice="Aria")
    assert q1["state"] == "quote" and q1["quote"]["credits"] == 10 and balance() == 1000
    _tool(studio, "voice_preview", script=SCRIPT, voice="Aria",
          quote_token=q1["quote"]["quote_token"])
    voice = studio.results[0]
    assert voice["ok"] and voice["audio"].startswith("asset:") and balance() == 990
    assert 6.0 < voice["seconds"] < 6.5
    url, body = studio.sent[0]
    assert url.endswith("fal-ai/elevenlabs/tts/eleven-v3")
    assert body == {"text": SCRIPT, "voice": "Aria"}

    # 2. the clip: quoted off that voice's measured 6.2s -> 7 billed seconds
    ask = dict(photo=studio.photo, audio=voice["audio"], consent=True)
    q2 = _tool(studio, "talking_photo", **ask)
    assert q2["quote"]["billed_seconds"] == 7
    credits = ledger.charge_credits(7 * 0.105)
    assert q2["quote"]["credits"] == credits and q2["quote"]["balance_after"] == 990 - credits
    _tool(studio, "talking_photo", **ask, quote_token=q2["quote"]["quote_token"])
    clip = studio.results[1]
    assert clip["ok"] and clip["media_kind"] == "video" and clip["asset_id"]
    assert balance() == 990 - credits
    url, body = studio.sent[1]
    assert url.endswith("bytedance/omnihuman/v2")
    assert body == {"image_url": "https://r2/m/1/renders/fal/face.png",
                    "audio_url": "https://r2/voice.mp3"}

    # the same yes again starts nothing and charges nothing
    again = _tool(studio, "talking_photo", **ask, quote_token=q2["quote"]["quote_token"])
    assert again["already_used"] is True and len(studio.sent) == 2
    kinds = [e["kind"] for e in ledger.entries(studio.account_id, studio.dsn)]
    assert kinds.count("settle") == 2 and "release" not in kinds
