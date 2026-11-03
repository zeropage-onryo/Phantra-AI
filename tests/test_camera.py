"""The Video page's Camera move and Lens cards (2026-11-03, src/camera.py,
prompts/camera.json, docs/tasks/task-camera-lens.md).

What has to hold: only LTX 2.5 gets its own camera setting, and only the
eight values its schema lists; every other model gets the move as words,
placed where its vendor says (lead or tail); lens is always words; a
reference clip rides only when switched on, on a model that holds video
references, on fal, with no start frame; a pick off the table or two
picks that contradict are refused, never dropped; and the route sends
exactly that.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import camera, fal, generative, ledger, nano_banana, render_assets, replicate, storage

ACCOUNT = 42


# ---------- the table ----------

def test_every_move_and_lens_line_is_present_and_ltx_values_are_real():
    t = camera.table()
    ids = [m["id"] for m in t["moves"]]
    assert len(ids) == len(set(ids)) == 12
    for m in t["moves"]:
        assert m["label"] and m["words"].endswith("."), m["id"]
        assert m["ltx"] is None or m["ltx"] in fal.CAMERA_MOTIONS_LTX25, m["id"]
    # every LTX value is reachable from a move
    assert {m["ltx"] for m in t["moves"] if m["ltx"]} == set(fal.CAMERA_MOTIONS_LTX25)
    for kind in ("focal", "aperture", "looks"):
        assert all(v["label"] and v["words"] for v in t[kind].values()), kind
    for a, b, why in t["conflicts"]:
        assert why and camera.conflict([a, b]) == why
    for platform in {s["platform"] for s in fal.VIDEO_MODELS.values()}:
        assert camera.table()["placement"].get(platform, "tail") in ("lead", "tail")


def test_only_ltx_25_has_a_camera_setting():
    for key, spec in fal.VIDEO_MODELS.items():
        has = bool(spec.get("camera_motions"))
        assert has == (key in ("ltx2.5", "ltx2.5-fast")), key


# ---------- modes and words ----------

def test_ltx_gets_the_setting_and_the_words():
    out = camera.dress("A sneaker on wet concrete.", "ltx2.5-fast", move_id="push_in")
    assert out["mode"] == "exact" and out["camera_motion"] == "dolly_in"
    # LTX wants the action first: the camera goes after it
    assert out["prompt"].startswith("A sneaker on wet concrete.\n\nThe camera slowly dollies in")
    # a move LTX has no value for is words on LTX too
    orbit = camera.dress("A sneaker.", "ltx2.5", move_id="orbit")
    assert orbit["mode"] == "guided" and orbit["camera_motion"] is None


def test_other_models_get_words_where_their_vendor_puts_them():
    veo = camera.dress("A sneaker.", "veo3.1", move_id="orbit", focal="85", aperture="f1.4")
    assert veo["mode"] == "guided" and veo["camera_motion"] is None and veo["video_refs"] == []
    assert veo["prompt"].startswith("The camera orbits")          # Veo leads with the camera
    assert "portrait-lens look" in veo["prompt"] and "bokeh" in veo["prompt"]
    assert veo["prompt"].endswith("A sneaker.")
    kling = camera.dress("A sneaker.", "kling4", move_id="crane_up")
    assert kling["prompt"].startswith("A sneaker.\n\n")           # Kling: after the scene


def test_lens_alone_is_words_and_no_pick_changes_nothing():
    out = camera.dress("A face.", "seedance2.5", look="anamorphic")
    assert out["mode"] is None and out["added"] == ["Lens: anamorphic lens with horizontal flares and oval bokeh."]
    same = camera.dress("A face.", "seedance2.5")
    assert same == {"prompt": "A face.", "mode": None, "camera_motion": None,
                    "video_refs": [], "added": []}


def test_off_table_and_contradicting_picks_are_refused():
    with pytest.raises(ValueError, match="no camera move"):
        camera.dress("x", "veo3.1", move_id="barrel_roll")
    with pytest.raises(ValueError, match="no focal"):
        camera.dress("x", "veo3.1", focal="300")
    with pytest.raises(ValueError, match="Rack focus"):
        camera.dress("x", "veo3.1", move_id="rack_focus", aperture="f11")
    with pytest.raises(ValueError, match="no camera setting"):
        fal.build_body("x", model="veo3.1", camera_motion="dolly_in")
    with pytest.raises(ValueError, match="no camera setting"):
        fal.build_body("x", model="ltx2.5", camera_motion="orbit")


def _with_clip(monkeypatch, move_id="orbit"):
    rows = json.loads(json.dumps(camera.table()))
    for m in rows["moves"]:
        if m["id"] == move_id:
            m["clip"] = f"site/camera/{move_id}.mp4"
    monkeypatch.setattr(camera, "table", lambda: rows)
    monkeypatch.setattr(storage, "public_base_url", lambda: "https://media.example")


def test_a_reference_clip_rides_only_when_on_on_fal_with_no_start_frame(monkeypatch):
    _with_clip(monkeypatch)
    # off by default: no clip is shot yet and its price is unmeasured
    monkeypatch.delenv(camera.CLIPS_ENV, raising=False)
    assert camera.mode("seedance2.5", "orbit", resolution="1080p") == "guided"
    monkeypatch.setenv(camera.CLIPS_ENV, "1")
    out = camera.dress("A sneaker.", "seedance2.5", move_id="orbit", resolution="1080p")
    assert out["mode"] == "clip" and out["video_refs"] == ["https://media.example/site/camera/orbit.mp4"]
    assert out["prompt"].startswith("Use @Video1 as the camera movement reference only")
    # Replicate renders Seedance 2.5 at 720p and takes no video input
    assert camera.mode("seedance2.5", "orbit", resolution="720p") == "guided"
    assert camera.menu_for("seedance2.5")["clip_resolutions"] == ["1080p"]
    # a start frame, or a model with no video field, is words
    assert camera.mode("seedance2.5", "orbit", start_frame=True, resolution="1080p") == "guided"
    assert camera.mode("kling4", "orbit") == "guided"


def test_video_references_go_to_the_reference_endpoint_on_fal_only():
    model_id, body = fal.build_body("Use @Video1 ...", model="seedance2.5", resolution="1080p",
                                    reference_videos=["https://m/orbit.mp4"])
    assert model_id == "bytedance/seedance-2.5/reference-to-video"
    assert body["video_urls"] == ["https://m/orbit.mp4"] and "image_urls" not in body
    with pytest.raises(ValueError, match="no video references"):
        fal.build_body("x", model="veo3.1", reference_videos=["https://m/o.mp4"])
    with pytest.raises(ValueError, match="not both"):
        fal.build_body("x", model="seedance2.5", image_url="https://a/0.jpg",
                       reference_videos=["https://m/o.mp4"])
    with pytest.raises(ValueError, match="fal only"):
        replicate.to_input({"prompt": "x", "video_urls": ["https://m/o.mp4"]})


def test_ltx_body_carries_the_camera_setting():
    _id, body = fal.build_body("x", model="ltx2.5-fast", camera_motion="jib_up")
    assert body["camera_motion"] == "jib_up"


# ---------- the route ----------

@pytest.fixture
def client(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    generative.init(pg)
    render_assets.init(pg)
    ledger.init(pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "camera-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)
    app.dependency_overrides[auth.current_account_id] = lambda: ACCOUNT
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)


def _wait(client, job_id):
    for _ in range(400):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(.01)
    raise AssertionError("job never finished")


def test_the_menu_carries_the_cards_and_each_models_exact_moves(client):
    menu = client.get("/api/direct/video").json()
    assert [m["id"] for m in menu["camera"]["moves"]][:2] == ["static", "push_in"]
    by = {i["id"]: i for i in menu["items"]}
    if "ltx2.5-fast" in by:
        assert "push_in" in by["ltx2.5-fast"]["camera"]["exact"]
    assert all(i["camera"]["clips"] == [] for i in menu["items"])   # off by default


def test_the_route_sends_the_dressed_prompt_and_the_ltx_setting(client, monkeypatch):
    sent = []
    monkeypatch.setattr(fal, "generate_from_prompt",
                        lambda prompt, **kw: sent.append((prompt, kw)) or {"ok": True, "media_url": "u", "asset_id": 2})
    pick = {"model": "ltx2.5-fast", "seconds": "6", "resolution": "720p", "aspect": "16:9"}
    price = client.post("/api/direct/video/quote", json={**pick, "seconds": 6}).json()["credits"]
    r = client.post("/api/direct/video/run", data={
        **pick, "prompt": "A sneaker on wet concrete.", "expect_credits": str(price),
        "camera_move": "crane_up", "lens_focal": "24"})
    assert r.status_code == 200, r.text
    assert _wait(client, r.json()["job_id"])["status"] == "done"
    prompt, kw = sent[0]
    assert kw["camera_motion"] == "jib_up" and "reference_videos" not in kw
    assert prompt.startswith("A sneaker on wet concrete.\n\nThe camera cranes up")
    assert "Lens: wide-angle view" in prompt


def test_the_route_refuses_a_bad_pick_before_anything_runs(client, monkeypatch):
    monkeypatch.setattr(fal, "generate_from_prompt", lambda *a, **k: pytest.fail("spent"))
    base = {"model": "veo3.1", "seconds": "8", "prompt": "x y z", "expect_credits": "1"}
    for extra, said in (({"camera_move": "barrel_roll"}, "no camera move"),
                        ({"camera_move": "rack_focus", "lens_aperture": "f11"}, "Rack focus")):
        r = client.post("/api/direct/video/run", data={**base, **extra})
        assert r.status_code == 400 and said in r.json()["error"]["message"], r.text
