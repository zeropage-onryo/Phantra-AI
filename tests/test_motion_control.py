"""Motion control (2026-11-14, docs/tasks/task-motion-control.md): the one
effect that takes a STILL and a CLIP, in that order, and makes the still's
character perform the clip's movement (Kling 3 on fal).

What is pinned here: the table row's wire shape and price, the source rule
(two, still first), the driving clip's length cap by orientation, and both
doors -- the studio's quote/run routes and the connector's run_effect --
reading the still as a reference and the clip by id, priced off the CLIP."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import accounts, effects, fal, generative, ledger, mcp_server, render_assets

PROBE = {"seconds": 9.5, "width": 1920, "height": 1080, "fps": 30.0}


# ---------- the table ----------

@pytest.mark.parametrize("name,rate,endpoint", [
    ("motion-control", 0.126, "fal-ai/kling-video/v3/standard/motion-control"),
    ("motion-control-pro", 0.168, "fal-ai/kling-video/v3/pro/motion-control"),
])
def test_each_tier_is_priced_per_second_of_the_driving_clip(name, rate, endpoint):
    row = effects.spec(name)
    assert row["endpoint"] == endpoint and row["takes"] == effects.MIXED
    assert row["category"] == "motion" and row["output"] == "video"
    assert row["checked"] == effects.CHECKED_MOTION
    opts = effects.check_options(name, {})
    assert opts == {"character_orientation": "image", "keep_original_sound": False}
    assert effects.quote_usd(name, opts, PROBE) == round(9.5 * rate, 4)
    assert effects.default_usd(name) is None          # the clip's length decides


def test_the_sources_are_still_then_clip_then_any_face_photos():
    for n in (0, 1, 7):
        with pytest.raises(ValueError, match="the still of the character, then the clip"):
            effects.check_sources("motion-control", n, {"character_orientation": "video"})
    effects.check_sources("motion-control", 2, {"character_orientation": "image"})
    effects.check_sources("motion-control", 6, {"character_orientation": "video"})
    assert effects.split_mixed(["/refs/a.jpg", "gen:7", "/refs/face.jpg"]) == (
        ["/refs/a.jpg"], ["gen:7"], ["/refs/face.jpg"])


def test_face_lock_needs_the_clips_framing():
    """Kling binds the element only with character_orientation video."""
    with pytest.raises(ValueError, match="face lock works only when the framing follows"):
        effects.check_sources("motion-control", 3, {"character_orientation": "image"})


def test_face_lock_is_one_element_named_in_the_prompt():
    opts = effects.check_options("motion-control-pro", {"character_orientation": "video"})
    # one face photo: the still is the second angle
    _, body = effects.build_body("motion-control-pro",
                                 ["https://b/still.jpg", "https://b/clip.mp4", "https://b/face.jpg"],
                                 "", opts)
    assert body["elements"] == [{"frontal_image_url": "https://b/face.jpg",
                                 "reference_image_urls": ["https://b/still.jpg"]}]
    assert body["prompt"] == "@Element1"
    assert body["image_url"] == "https://b/still.jpg" and body["video_url"] == "https://b/clip.mp4"
    # more angles ride as themselves, and a prompt that names the tag is left alone
    _, body = effects.build_body("motion-control-pro",
                                 ["https://b/s.jpg", "https://b/c.mp4", "https://b/f1.jpg",
                                  "https://b/f2.jpg", "https://b/f3.jpg"],
                                 "a man strutting", opts)
    assert body["elements"][0]["reference_image_urls"] == ["https://b/f2.jpg", "https://b/f3.jpg"]
    assert body["prompt"] == "@Element1 a man strutting"
    _, body = effects.build_body("motion-control-pro",
                                 ["https://b/s.jpg", "https://b/c.mp4", "https://b/f1.jpg"],
                                 "@Element1 on a stage", opts)
    assert body["prompt"] == "@Element1 on a stage"
    # no face photos: no element, no tag
    _, body = effects.build_body("motion-control-pro", ["https://b/s.jpg", "https://b/c.mp4"],
                                 "", opts)
    assert "elements" not in body and "prompt" not in body


def test_the_wire_body_names_the_still_and_the_clip():
    opts = effects.check_options("motion-control", {"character_orientation": "video"})
    endpoint, body = effects.build_body(
        "motion-control", ["https://b/still.jpg", "https://b/clip.mp4"], "a man dancing", opts)
    assert endpoint == "fal-ai/kling-video/v3/standard/motion-control"
    assert body == {"image_url": "https://b/still.jpg", "video_url": "https://b/clip.mp4",
                    "character_orientation": "video", "keep_original_sound": False,
                    "prompt": "a man dancing"}
    # the prompt is optional, never required
    assert effects.check_prompt("motion-control", "") == ""


def test_the_driving_clip_is_capped_by_orientation_and_refused_not_cut():
    image = effects.check_options("motion-control", {"character_orientation": "image"})
    video = effects.check_options("motion-control", {"character_orientation": "video"})
    long = dict(PROBE, seconds=14.0)
    with pytest.raises(ValueError, match="up to 10s.*follow the clip"):
        effects.quote_usd("motion-control", image, long)
    assert effects.quote_usd("motion-control", video, long) == round(14 * 0.126, 4)
    with pytest.raises(ValueError, match="up to 30s"):
        effects.quote_usd("motion-control", video, dict(PROBE, seconds=31.0))
    with pytest.raises(ValueError, match="is not one of"):
        effects.check_options("motion-control", {"character_orientation": "sideways"})


# ---------- the studio's door ----------

@pytest.fixture
def client(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    generative.init(pg)
    render_assets.init(pg)
    ledger.init(pg)
    accounts.init(pg)
    me = accounts.upsert_account("mc-mine", "Mine", "#fff", dsn=pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "mc-user"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(effects, "probe_video", lambda target: dict(PROBE))
    app.dependency_overrides[auth.current_account_id] = lambda: me
    yield TestClient(app), me
    app.dependency_overrides.pop(auth.current_account_id, None)


def _clip(pg, account_id):
    return render_assets.record(
        generation_id=1, tool="fal", model="ltx2.3", media_kind="video", prompt="a strut",
        media_url="https://cdn.example/strut.mp4", dsn=pg, account_id=account_id)["id"]


def _wait(client, job_id):
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError("job never finished")


def test_the_studio_quotes_off_the_clip_and_runs_still_then_clip(client, pg, monkeypatch):
    http, me = client
    clip = _clip(pg, me)
    body = {"effect": "motion-control", "sources": ["/refs/jensen.jpg", f"gen:{clip}"],
            "options": {"character_orientation": "image"}}
    quote = http.post("/api/effects/quote", json=body)
    assert quote.status_code == 200, quote.text
    assert quote.json()["clip"] == {"seconds": 9.5, "width": 1920, "height": 1080}
    assert quote.json()["credits"] == ledger.charge_credits(round(9.5 * 0.126, 4))

    # the still second and the clip first is refused: a still is no clip
    flipped = http.post("/api/effects/quote", json={**body, "sources": body["sources"][::-1]})
    assert flipped.status_code == 400
    # face photos ride after the clip, and the price is still the clip's
    faced = http.post("/api/effects/quote", json={
        **body, "sources": [*body["sources"], "/refs/face.jpg"],
        "options": {"character_orientation": "video"}})
    assert faced.status_code == 200, faced.text
    assert faced.json()["credits"] == quote.json()["credits"]
    locked_wrong = http.post("/api/effects/quote", json={
        **body, "sources": [*body["sources"], "/refs/face.jpg"]})
    assert locked_wrong.status_code == 400 and "face lock" in locked_wrong.json()["error"]["message"]

    ran = []
    monkeypatch.setattr(api, "_photo_bytes", lambda url, account_id=None: b"jpeg")
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    monkeypatch.setattr(fal, "as_image_url", lambda value, **k: "https://bucket.example/still.jpg")
    monkeypatch.setattr(effects, "fetchable_video",
                        lambda media_url, local="", account_id=None: "https://bucket.example/clip.mp4")
    monkeypatch.setattr(effects, "run", lambda effect, urls, prompt, options, **kw: ran.append(
        {"urls": urls, "options": options, **kw}) or {"ok": True, "asset_id": 5,
                                                      "media_url": "https://b/out.mp4"})
    started = http.post("/api/effects/run", json={**body,
                                                   "expect_credits": quote.json()["credits"]})
    assert started.status_code == 200, started.text
    job = _wait(http, started.json()["job_id"])
    assert job["status"] == "done", job
    (call,) = ran
    assert call["urls"] == ["https://bucket.example/still.jpg", "https://bucket.example/clip.mp4"]
    assert call["probe"]["seconds"] == 9.5


def test_the_gallery_lists_it_under_its_own_heading(client):
    http, _ = client
    listing = http.get("/api/effects").json()
    item = next(i for i in listing["items"] if i["id"] == "motion-control")
    assert item["takes"] == "image+video" and item["credits"] is None
    assert {"id": "motion", "label": "Copy a movement"} in listing["categories"]


# ---------- the connector's door ----------

def test_the_connector_reads_the_still_as_a_reference_and_the_clip_by_id(monkeypatch):
    seen = {}
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **k: seen.setdefault("still", refs) and ["https://b/s.jpg"])
    monkeypatch.setattr(mcp_server, "_video_sources",
                        lambda refs, dsn, account_id, listed=False, fetch=True:
                        (seen.setdefault("clip", refs) and ["https://b/c.mp4"], dict(PROBE)))
    monkeypatch.setattr(mcp_server, "approval_gate",
                        lambda usd, token, **k: (None, None, {"usd": usd}))
    out = mcp_server.run_effect("motion-control", sources=["gen:3", "asset:8"],
                                options={"character_orientation": "image"},
                                dry_run=True, account_id=1)
    assert out["ok"] and out["dry_run"]
    assert seen == {"still": ["gen:3"], "clip": ["asset:8"]}
    assert out["quote"]["usd"] == round(9.5 * 0.126, 4)
    assert out["quote"]["source_clip"]["seconds"] == 9.5


def test_the_connector_puts_face_photos_after_the_clip(monkeypatch):
    monkeypatch.setattr(mcp_server, "resolve_references",
                        lambda refs, **k: [f"https://b/{r.replace(':', '-')}.jpg" for r in refs])
    monkeypatch.setattr(mcp_server, "_video_sources",
                        lambda refs, dsn, account_id, listed=False, fetch=True:
                        (["https://b/clip.mp4"], dict(PROBE)))
    monkeypatch.setattr(mcp_server, "approval_gate",
                        lambda usd, token, **k: (None, None, {"usd": usd}))
    ran = []
    monkeypatch.setattr(effects, "run", lambda effect, urls, *a, **k: ran.append(urls) or {"ok": True})
    monkeypatch.setattr(mcp_server, "approval_gate",
                        lambda usd, token, **k: (None, {"credits": 1}, {"usd": usd}))
    mcp_server.run_effect("motion-control", sources=["gen:3", "asset:8", "asset:9"],
                          options={"character_orientation": "video"}, account_id=1)
    assert ran == [["https://b/gen-3.jpg", "https://b/clip.mp4", "https://b/asset-9.jpg"]]
