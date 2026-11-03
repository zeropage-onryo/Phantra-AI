"""
Dubbing -- a clip's dialogue spoken again in another language (2026-10-26,
docs/tasks/task-dubbing.md).

One spend, quoted and approved on its own: ElevenLabs Dubbing on fal, priced
per minute of the clip, rounded up. What is guarded: the table as read on
2026-10-26, every refusal before a quote, the wire body, the connector's
quote -> yes -> run conversation, and the whole thing on the real ledger
with a real clip through ffprobe and only fal's wire stood in for.
"""

import asyncio
import shutil
import subprocess

import pytest

from src import dubbing, effects, fal, ledger, mcp_server, mcp_shapes, pricing

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg is not installed")


# --------------------------------------------------------------------------
# the table
# --------------------------------------------------------------------------

def test_the_row_is_the_one_read_off_fal_that_day():
    assert dubbing.CHECKED == "2026-10-26"
    assert dubbing.DUB["endpoint"] == "fal-ai/elevenlabs/dubbing"
    assert dubbing.DUB["usd_per_minute"] == 0.60
    assert dubbing.DUB["source"].startswith("https://fal.ai/models/")
    # not a menu entry apply_effect could run without a consent
    assert dubbing.DUB["endpoint"] not in {r["endpoint"] for r in effects.EFFECTS.values()}


def test_the_languages_are_the_six_the_model_page_names():
    assert dict(dubbing.LANGUAGES) == {"es": "Spanish", "fr": "French", "de": "German",
                                       "ja": "Japanese", "pt": "Portuguese", "zh": "Chinese"}


@pytest.mark.parametrize("seconds, minutes, usd", [
    (0.5, 1, 0.6), (8.0, 1, 0.6), (60.0, 1, 0.6), (60.5, 2, 1.2),
    (61.0, 2, 1.2), (299.0, 5, 3.0), (300.0, 5, 3.0),
])
def test_a_clip_is_priced_in_whole_minutes_rounded_up_never_under_one(seconds, minutes, usd):
    assert dubbing.billed_minutes(seconds) == minutes and dubbing.dub_usd(seconds) == usd


def test_credits_carry_the_standard_markup():
    # $0.60 x 2.4 -> 144 credits for a minute; the five-minute ceiling is 720
    assert ledger.charge_credits(dubbing.dub_usd(30)) == 144
    assert ledger.charge_credits(dubbing.dub_usd(dubbing.MAX_SECONDS)) == 720
    assert 144 > pricing.CREDIT_FLOOR


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------

def test_the_target_language_is_one_the_page_names():
    assert dubbing.check_language(" ES ") == "es"
    for bad in ("", "it", "spanish", "en"):
        with pytest.raises(ValueError, match="target language must be one of"):
            dubbing.check_language(bad)


def test_the_spoken_language_is_a_code_that_is_not_the_target():
    assert dubbing.check_source_language("", "es") is None
    assert dubbing.check_source_language(" EN ", "es") == "en"
    with pytest.raises(ValueError, match="two-letter"):
        dubbing.check_source_language("english", "es")
    with pytest.raises(ValueError, match="already in Spanish"):
        dubbing.check_source_language("es", "es")


@pytest.mark.parametrize("given, want", [(None, None), ("", None), (0, None), (2, 2), ("3", 3)])
def test_speakers_are_a_count_or_left_to_the_model(given, want):
    assert dubbing.check_speakers(given) == want


@pytest.mark.parametrize("bad, match", [(51, "1 to 50"), (-1, "1 to 50"), ("two", "whole number")])
def test_a_bad_speaker_count_is_refused(bad, match):
    with pytest.raises(ValueError, match=match):
        dubbing.check_speakers(bad)


@pytest.mark.parametrize("consent", [False, None, "yes", 1, ""])
def test_only_a_true_consent_counts(consent):
    with pytest.raises(ValueError, match="consent"):
        dubbing.check_consent(consent)
    dubbing.check_consent(True)


@pytest.mark.parametrize("probe, sound, match", [
    ({"seconds": 0}, True, "could not be measured"),
    ({}, True, "could not be measured"),
    ({"seconds": 10}, None, "could not be checked"),
    ({"seconds": 10}, False, "no sound track"),
    ({"seconds": 301}, True, "up to 300s"),
])
def test_a_clip_that_cannot_be_dubbed_is_refused(probe, sound, match):
    with pytest.raises(ValueError, match=match):
        dubbing.check_clip(probe, sound)


def test_a_clip_at_the_limit_is_taken():
    assert dubbing.check_clip({"seconds": 300.0}, True) == 300.0


def test_the_wire_body_is_the_schema():
    assert dubbing.dub_body("https://v/c.mp4", "es") == (
        "fal-ai/elevenlabs/dubbing", {"video_url": "https://v/c.mp4", "target_lang": "es"})
    assert dubbing.dub_body("https://v/c.mp4", "fr", "en", 2)[1] == {
        "video_url": "https://v/c.mp4", "target_lang": "fr", "source_lang": "en",
        "num_speakers": 2}


# --------------------------------------------------------------------------
# the tool, with the clip row, ffprobe and fal stood in for
# --------------------------------------------------------------------------

@pytest.fixture
def signed(monkeypatch):
    monkeypatch.setenv(pricing.SIGNING_ENV, "test-quote-secret")


@pytest.fixture
def world(monkeypatch):
    from src import render_assets
    from src.cut import store as cut_store
    media = {6: {"id": 6, "kind": "video", "media_url": "https://r2/c6.mp4", "output_path": ""},
             7: {"id": 7, "kind": "video", "media_url": "https://r2/c7.mp4", "output_path": ""},
             5: {"id": 5, "kind": "audio", "media_url": "https://r2/v.mp3", "output_path": ""}}
    renders = {12: {"id": 12, "media_kind": "video", "media_url": "https://r2/c12.mp4",
                    "output_path": "", "deleted_at": None},
               13: {"id": 13, "media_kind": "image", "media_url": "https://r2/i13.png",
                    "output_path": "", "deleted_at": None}}
    monkeypatch.setattr(cut_store, "get_media",
                        lambda i, account_id=None, dsn=None: media.get(int(i)))
    monkeypatch.setattr(render_assets, "get",
                        lambda i, dsn=None, account_id=None: renders.get(int(i)))
    monkeypatch.setattr(mcp_server, "_clip_file", lambda row, account_id: (row["media_url"], ".mp4", None))
    probes = {"seconds": 8.0, "width": 1280, "height": 720, "fps": 24.0}
    state = {"probe": probes, "sound": True}
    monkeypatch.setattr(effects, "probe_video", lambda target: state["probe"])
    monkeypatch.setattr(dubbing, "has_sound", lambda target: state["sound"])
    monkeypatch.setattr(effects, "fetchable_video",
                        lambda url, local="", account_id=None: url)
    calls = []

    def run(effect, urls, prompt, opts, **kw):
        calls.append({"effect": effect, "urls": urls, "prompt": prompt, **kw})
        return {"ok": True, "media_url": "https://r2/dubbed.mp4", "asset_id": 88,
                "media_kind": "video", "error": None}

    monkeypatch.setattr(effects, "run", run)
    return {"media": media, "renders": renders, "calls": calls, "state": state}


ASK = dict(source="gen:12", target_language="es", consent=True)


def test_the_dub_is_quoted_on_the_clips_length_in_minutes(world, signed):
    q = mcp_server.run_dub_clip(**ASK)
    assert q["needs_approval"] and world["calls"] == []
    quote = q["quote"]
    assert quote["clip_seconds"] == 8.0 and quote["billed_minutes"] == 1
    assert quote["usd"] == 0.6 and quote["credits"] == 144 and quote["language"] == "Spanish"
    assert quote["model"] == "ElevenLabs Dubbing"


def test_a_clip_past_the_minute_is_quoted_at_two(world, signed):
    world["state"]["probe"] = {"seconds": 61.0, "width": 1280, "height": 720, "fps": 24.0}
    quote = mcp_server.run_dub_clip(**ASK)["quote"]
    assert quote["billed_minutes"] == 2 and quote["usd"] == 1.2
    assert quote["credits"] == ledger.charge_credits(1.2)


def test_an_imported_clip_is_a_source_too(world, signed):
    assert mcp_server.run_dub_clip(**{**ASK, "source": "asset:6"})["quote"]["billed_minutes"] == 1


def test_an_approved_dub_sends_the_clip_and_the_languages(world, signed):
    ask = {**ASK, "source_language": " EN ", "speakers": 2}
    q = mcp_server.run_dub_clip(**ask)
    out = mcp_server.run_dub_clip(**ask, quote_token=q["quote"]["quote_token"])
    (c,) = world["calls"]
    assert c["effect"] == "dub-es" and c["urls"] == ["https://r2/c12.mp4"]
    assert c["row"] == {"label": "ElevenLabs Dubbing", "output": "video"}
    assert c["endpoint_body"] == ("fal-ai/elevenlabs/dubbing", {
        "video_url": "https://r2/c12.mp4", "target_lang": "es", "source_lang": "en",
        "num_speakers": 2})
    assert c["sources"] == ["gen:12"] and c["usd"] == 0.6
    assert c["quote"].credits == q["quote"]["credits"]
    assert c["extra"]["dubbing"] == {
        "source": "gen:12", "target": "es", "source_lang": "en", "speakers": 2,
        "clip_seconds": 8.0, "billed_minutes": 1, "consent": True}
    assert out["ok"] and out["asset_id"] == 88


@pytest.mark.parametrize("kwargs, match", [
    ({**ASK, "consent": False}, "consent"),
    ({**ASK, "target_language": "it"}, "target language must be one of"),
    ({**ASK, "target_language": ""}, "target language must be one of"),
    ({**ASK, "source_language": "es"}, "already in Spanish"),
    ({**ASK, "speakers": 99}, "1 to 50"),
    ({**ASK, "source": ""}, "needs `source`"),
    ({**ASK, "source": "https://x/c.mp4"}, "URLs are never taken"),
    ({**ASK, "source": "gen:404"}, "no render 404"),
    ({**ASK, "source": "gen:13"}, "this effect takes a clip"),
    ({**ASK, "source": "asset:5"}, "this takes a clip"),
])
def test_refusals_come_before_any_quote(world, signed, kwargs, match):
    with pytest.raises(ValueError, match=match):
        mcp_server.run_dub_clip(**kwargs)
    assert world["calls"] == []


def test_a_clip_with_no_voice_on_it_is_refused_before_a_quote(world, signed):
    world["state"]["sound"] = False
    with pytest.raises(ValueError, match="no sound track"):
        mcp_server.run_dub_clip(**ASK)
    world["state"]["sound"] = None
    with pytest.raises(ValueError, match="could not be checked"):
        mcp_server.run_dub_clip(**ASK)


def test_a_clip_that_cannot_be_made_fetchable_is_refused(world, signed, monkeypatch):
    monkeypatch.setattr(effects, "fetchable_video", lambda *a, **k: None)
    with pytest.raises(ValueError, match="cannot be made fetchable"):
        mcp_server.run_dub_clip(**ASK)


def test_a_yes_for_another_clip_or_language_starts_nothing(world, signed):
    q = mcp_server.run_dub_clip(**ASK)
    token = q["quote"]["quote_token"]
    for changed in ({**ASK, "source": "asset:6"}, {**ASK, "target_language": "fr"}):
        with pytest.raises(ValueError):
            mcp_server.run_dub_clip(**changed, quote_token=token)
    assert world["calls"] == []


def test_the_tool_is_studio_only_and_answers_typed(pg, world, signed):
    from src import preprod
    preprod.init(pg)
    server = mcp_server.build_server(dsn=pg, surface="studio")
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert "dub_clip" in names
    res = asyncio.run(server.call_tool("dub_clip", dict(ASK)))
    data = res.structured_content
    mcp_shapes.SpendResult.model_validate(data)
    assert data["state"] == "quote" and data["quote"]["billed_minutes"] == 1
    assert "dub_clip" in mcp_shapes.SPEND_TOOLS
    for listed in (dict(listed=True), dict(listed="claude")):
        offered = {t.name for t in asyncio.run(
            mcp_server.build_server(dsn=pg, **listed).list_tools())}
        assert "dub_clip" not in offered


# --------------------------------------------------------------------------
# the conversation on the real ledger, the real wall and a real clip through
# ffprobe: quote -> yes -> dub. Only fal's wire and the bucket are stood in for.
# --------------------------------------------------------------------------

def _make_clip(path, seconds, sound=True):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(seconds),
           "-i", "color=c=black:s=160x120:r=4"]
    if sound:
        cmd += ["-f", "lavfi", "-t", str(seconds), "-i", "sine=frequency=220",
                "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


@pytest.fixture
def studio(pg, monkeypatch, tmp_path):
    import types

    from src import accounts, db, generative, preprod, quote_redemptions, render_assets
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
    talk = _make_clip(tmp_path / "talk.mp4", 8)
    long = _make_clip(tmp_path / "long.mp4", 62)
    mute = _make_clip(tmp_path / "mute.mp4", 8, sound=False)

    def filed(path, prompt):
        row = render_assets.record(generation_id=9100 + len(prompt), tool="fal", model="kling",
                                   media_kind="video", prompt=prompt,
                                   media_url=f"https://r2/m/1/renders/fal/{path.name}",
                                   output_path=str(path), account_id=acct, dsn=pg)
        return f"gen:{row['id']}"

    from src import media
    monkeypatch.setattr(media, "mirror", lambda *a, **k: None)
    sent, downloaded = [], []

    def download(url, out):
        downloaded.append(url)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00" * 2048)
        return out

    monkeypatch.setattr(fal, "_download", download)
    monkeypatch.setattr(fal, "_publish",
                        lambda path, ctype, acct=None: f"https://r2/m/1/renders/fal/{path.name}")

    def wire(url, payload=None, account_id=None):
        if payload is not None and payload is not fal.CANCEL:
            sent.append((url, payload))
            return {"request_id": "r", "status_url": "https://q/s", "response_url": "https://q/r",
                    "cancel_url": "https://q/c"}
        if url == "https://q/s":
            return {"status": "COMPLETED"}
        # both outputs, the audio listed first: the clip must be the video's
        return {"audio": {"url": "https://cdn/dub.mp3"}, "video": {"url": "https://cdn/dub.mp4"},
                "target_lang": "es"}

    monkeypatch.setattr(fal, "_request", wire)
    results = []

    def start_job(kind, label, fn, cancellable=False, account_id=None):
        results.append(fn({})["result"])
        return {"id": len(results), "status": "done"}

    server = mcp_server.build_server(dsn=pg, surface="studio", start_job=start_job,
                                     job_status=lambda i, account_id=None: None,
                                     account_id=acct)
    return types.SimpleNamespace(
        dsn=pg, account_id=acct, server=server, sent=sent, results=results,
        downloaded=downloaded, talk=filed(talk, "a shopkeeper talking"),
        long=filed(long, "a long talk to camera and then some"),
        mute=filed(mute, "a quiet shot"))


def _tool(studio, name, **args):
    return asyncio.run(studio.server.call_tool(name, args)).structured_content


@needs_ffmpeg
def test_quote_then_yes_dubs_once_and_charges_once(studio):
    balance = lambda: ledger.available(studio.account_id, dsn=studio.dsn)   # noqa: E731
    ask = dict(source=studio.talk, target_language="es", consent=True)
    q = _tool(studio, "dub_clip", **ask)
    assert q["state"] == "quote" and q["quote"]["credits"] == 144 and balance() == 1000
    assert q["quote"]["clip_seconds"] == pytest.approx(8.0, abs=0.5)

    _tool(studio, "dub_clip", **ask, quote_token=q["quote"]["quote_token"])
    done = studio.results[0]
    assert done["ok"] and done["media_kind"] == "video" and done["asset_id"]
    assert balance() == 1000 - 144
    (url, body) = studio.sent[0]
    assert url.endswith("fal-ai/elevenlabs/dubbing")
    assert body == {"video_url": "https://r2/m/1/renders/fal/talk.mp4", "target_lang": "es"}
    assert studio.downloaded == ["https://cdn/dub.mp4"]      # the video, not the audio

    again = _tool(studio, "dub_clip", **ask, quote_token=q["quote"]["quote_token"])
    assert again["already_used"] is True and len(studio.sent) == 1
    kinds = [e["kind"] for e in ledger.entries(studio.account_id, studio.dsn)]
    assert kinds.count("settle") == 1 and "release" not in kinds


@needs_ffmpeg
def test_a_clip_just_past_a_minute_is_billed_two(studio):
    ask = dict(source=studio.long, target_language="fr", consent=True)
    q = _tool(studio, "dub_clip", **ask)
    assert q["quote"]["billed_minutes"] == 2
    assert q["quote"]["credits"] == ledger.charge_credits(1.2) == 288


@needs_ffmpeg
def test_a_clip_with_no_sound_is_refused_by_the_real_probe(studio):
    with pytest.raises(Exception, match="no sound track"):
        mcp_server.run_dub_clip(source=studio.mute, target_language="es", consent=True,
                                dsn=studio.dsn, account_id=studio.account_id)


def test_a_failed_dub_releases_the_hold(studio, monkeypatch):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")

    def boom(url, payload=None, account_id=None):
        raise RuntimeError("fal said no")

    ask = dict(source=studio.talk, target_language="de", consent=True)
    q = _tool(studio, "dub_clip", **ask)
    monkeypatch.setattr(fal, "_request", boom)
    _tool(studio, "dub_clip", **ask, quote_token=q["quote"]["quote_token"])
    assert studio.results[0]["ok"] is False
    assert ledger.available(studio.account_id, dsn=studio.dsn) == 1000
