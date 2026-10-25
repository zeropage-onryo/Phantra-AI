"""The direct generators (/studio/image and /studio/video, 2026-10-22;
src/direct.py, docs/tasks/task-direct-generators.md).

What makes them safe to put a priced button on: every menu and price is a
projection of the tables the other doors price with (and shows credits,
never dollars); a pick off a model's legal set is refused, never clamped;
a run happens at the price the button showed or not at all; the prompt
reaches the model as typed; and a clip needs no photograph, because no
scene is written. Also here: the composer's Video line pick reaches the
brain, which is then told to propose no other model.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import (
    charge,
    creative_guide,
    direct,
    fal,
    generative,
    ledger,
    model_menu,
    nano_banana,
    pricing,
    providers,
    render_assets,
    scene_chain,
)

ACCOUNT = 42


@pytest.fixture
def client(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    generative.init(pg)
    render_assets.init(pg)
    ledger.init(pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "direct-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)
    # a direct make must never reach the enhance or the brain
    monkeypatch.setattr(api, "_enhance_generate_prompt",
                        lambda *a, **k: pytest.fail("a direct make was enhanced"))
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


# ---------- the tables ----------

def test_every_clip_model_has_its_text_to_video_frames_read():
    """A model added to VIDEO_MODELS (or a slot) without its frames would be
    offered the platform vertical alone; this says so the day it lands."""
    for key in list(fal.VIDEO_MODELS) + list(fal.SLOTS):
        assert key in fal.T2V_ASPECTS, f"{key}: read its t2v aspect_ratio enum off fal's schema"
        frames = fal.T2V_ASPECTS[key]
        assert frames and len(set(frames)) == len(frames), key
        # 3:2 and 2:3 are Grok Imagine's (2026-10-23)
        assert all(f in ("16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "3:2", "2:3") for f in frames), key
        # neither of the non-frames a person cannot pick
        assert "auto" not in frames and "adaptive" not in frames
    assert fal.t2v_aspects("no-such-model") == (fal.DEFAULT_ASPECT,)


# ---------- the video menu and its price ----------

def test_the_video_menu_is_the_catalogue_in_credits(client):
    body = client.get("/api/direct/video").json()
    assert body["ready"] is True and body["exempt"] is False
    assert [m["id"] for m in body["items"]] == [m for _p, m, _n, _b in pricing.catalog_rows()]
    assert "$" not in json.dumps(body) and "usd" not in json.dumps(body)
    assert body["default"] in [m["id"] for m in body["items"]]
    for m in body["items"]:
        spec = providers.model_options("fal", m["id"])
        assert m["seconds"] == spec["duration"]
        assert m["resolutions"] == list(spec["frame"]["values"])
        assert m["aspects"] == list(fal.t2v_aspects(m["id"])) and m["aspect"] in m["aspects"]
        opening = providers.check_render_choice("fal", m["id"], None, None)
        assert m["resolution"] == opening["frame"]
        assert m["credits"] == ledger.charge_credits(opening["estimate_usd"])


def test_no_renderer_key_lists_nothing(client, monkeypatch):
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    body = client.get("/api/direct/video").json()
    assert body == {"ready": False, "items": [], "default": "", "exempt": False}


def test_a_video_quote_is_the_pick_exactly_or_a_refusal(client):
    ok = client.post("/api/direct/video/quote", json={
        "model": "veo3.1", "seconds": 8, "resolution": "1080p", "aspect": "16:9"})
    assert ok.status_code == 200, ok.text
    q = ok.json()
    assert q == {"model": "veo3.1", "label": "Veo 3.1", "seconds": 8, "resolution": "1080p",
                 "aspect": "16:9", "start_frame": False, "references": 0, "charged": True,
                 "credits": ledger.charge_credits(fal.estimate_cost(
                     1, model="veo3.1", duration=8, resolution="1080p"))}

    def refused(**body):
        r = client.post("/api/direct/video/quote", json=body)
        assert r.status_code == 400 and r.json()["error"]["code"] == "bad_choice", r.text
        return r.json()["error"]["message"]

    # refused, never clamped: a length, a resolution, a frame off the set
    assert "10" in refused(model="veo3.1", seconds=10)
    assert "4k" in refused(model="veo3.1", resolution="4k")
    assert "does not render 1:1" in refused(model="veo3.1", aspect="1:1")
    assert "no video model" in refused(model="sora-9")
    # a start frame takes the picture's shape: no frame is quoted or sent
    framed = client.post("/api/direct/video/quote", json={
        "model": "kling3-turbo-pro", "aspect": "1:1", "start_frame": True}).json()
    assert framed["aspect"] is None and framed["start_frame"] is True
    # an unknown field is refused, not dropped
    assert client.post("/api/direct/video/quote", json={"model": "veo3.1", "usd": 1}).status_code == 422


# ---------- the video run ----------

def test_a_clip_runs_at_the_shown_price_from_text_alone(client, monkeypatch):
    sent = []

    def render(prompt, **kw):
        sent.append({"prompt": prompt, **kw})
        return {"ok": True, "media_url": "https://bucket.example/clip.mp4",
                "generation_id": 7, "asset_id": 31}

    monkeypatch.setattr(fal, "generate_from_prompt", render)
    pick = {"model": "seedance2.5", "seconds": "12", "resolution": "720p", "aspect": "21:9"}
    price = client.post("/api/direct/video/quote", json={
        **pick, "seconds": 12}).json()["credits"]
    text = "  A lone rider pulls up,\n steam rising off the asphalt  "

    missing = client.post("/api/direct/video/run", data={**pick, "prompt": text})
    assert missing.status_code == 400 and missing.json()["error"]["code"] == "missing_price"
    stale = client.post("/api/direct/video/run",
                        data={**pick, "prompt": text, "expect_credits": str(price + 1)})
    assert stale.status_code == 409 and stale.json()["credits"] == price
    empty = client.post("/api/direct/video/run", data={**pick, "prompt": "  ", "expect_credits": str(price)})
    assert empty.status_code == 400
    assert sent == []                                   # none of them spent

    r = client.post("/api/direct/video/run", data={**pick, "prompt": text, "expect_credits": str(price)})
    assert r.status_code == 200, r.text
    assert r.json()["credits"] == price and r.json()["charged"] is True
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["output"] == "https://bucket.example/clip.mp4" and job["asset"] == "gen:31"
    assert job["kind"] == "make"
    # no photograph and no scene: the prompt as typed, the exact pick, approved
    # by the click, filed on the Library wall
    assert sent == [{"prompt": "A lone rider pulls up, steam rising off the asphalt",
                     "reference_image": None, "model": "seedance2.5", "duration": 12,
                     "resolution": "720p", "aspect_ratio": "21:9", "approved": True,
                     "account_id": ACCOUNT, "source": "direct", "bank": True}]


def test_a_start_frame_is_sent_and_takes_the_frame(client, monkeypatch):
    sent = []
    monkeypatch.setattr(api, "_photo_bytes", lambda url, account_id=None: b"jpeg-bytes")
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    monkeypatch.setattr(fal, "generate_from_prompt",
                        lambda prompt, **kw: sent.append(kw) or {"ok": True, "media_url": "u", "asset_id": 2})
    # the button priced it WITH a start frame; the same pick without one
    # must not be quoted for a frame the picture overrides
    price = client.post("/api/direct/video/quote", json={
        "model": "kling3-turbo-pro", "seconds": 5, "start_frame": True}).json()["credits"]
    r = client.post("/api/direct/video/run", data={
        "model": "kling3-turbo-pro", "seconds": "5", "aspect": "1:1", "prompt": "she turns",
        "expect_credits": str(price), "asset_photos": "/refs/still.jpg"})
    assert r.status_code == 200, r.text
    assert _wait(client, r.json()["job_id"])["status"] == "done"
    assert sent[0]["reference_image"] == b"jpeg-bytes" and sent[0]["aspect_ratio"] is None


def test_every_reference_row_is_a_live_model_with_a_tag_and_a_cap():
    """REF2V is read off fal's schemas; a row for a model that left the
    table, or one with no tag, would put pictures the model never sees."""
    for key, spec in fal.REF2V.items():
        assert key in fal.VIDEO_MODELS or key in fal.SLOTS, key
        assert spec["endpoint"].endswith("reference-to-video") and spec["max"] >= 2, key
        assert "{n}" in spec["tag"] and spec["field"].endswith("urls"), key
    assert fal.ref_tags("seedance2.5", 2) == ["@Image1", "@Image2"]
    assert fal.ref_tags("grok1.5", 2) == ["<IMAGE_0>", "<IMAGE_1>"]
    assert fal.ref_max("veo3.1") == 0 and fal.ref_tags("veo3.1", 3) == []
    # every advertised model has its own prompt cap, or the house guard
    for key in fal.VIDEO_MODELS:
        assert 3000 <= fal.prompt_max(key) <= 26000, key


def test_references_go_to_the_reference_endpoint_or_are_refused():
    model_id, body = fal.build_body("@Image1 runs past @Image2", model="seedance2.5",
                                    aspect_ratio="9:16", resolution="720p",
                                    reference_urls=["https://a/1.jpg", "https://a/2.jpg"])
    assert model_id == "bytedance/seedance-2.5/reference-to-video"
    assert body["image_urls"] == ["https://a/1.jpg", "https://a/2.jpg"]
    assert body["aspect_ratio"] == "9:16"     # pictures held for content set no frame
    with pytest.raises(ValueError, match="start frame"):
        fal.build_body("x", model="veo3.1", reference_urls=["https://a/1.jpg"])
    with pytest.raises(ValueError, match="not both"):
        fal.build_body("x", model="seedance2.5", image_url="https://a/0.jpg",
                       reference_urls=["https://a/1.jpg"])
    with pytest.raises(ValueError, match="up to 9"):
        fal.build_body("x", model="seedance2", reference_urls=[f"https://a/{i}.jpg" for i in range(10)])


def test_a_reference_quote_counts_pictures_and_refuses_what_the_model_cannot(client):
    def quote(**body):
        return client.post("/api/direct/video/quote", json=body)

    q = quote(model="seedance2.5", seconds=8, resolution="720p", references=3).json()
    assert q["references"] == 3 and q["start_frame"] is False and q["aspect"] == "9:16"
    # Seedance prices references like text: three pictures cost nothing more
    assert q["credits"] == quote(model="seedance2.5", seconds=8, resolution="720p").json()["credits"]
    if "grok1.5" in fal.VIDEO_MODELS:
        plain = fal.estimate_cost(1, model="grok1.5", duration=6, resolution="720p")
        held = quote(model="grok1.5", seconds=6, resolution="720p", references=4).json()
        assert held["credits"] == ledger.charge_credits(plain + 0.04)

    def refused(**body):
        r = quote(**body)
        assert r.status_code == 400 and r.json()["error"]["code"] == "bad_choice", r.text
        return r.json()["error"]["message"]

    assert "one start frame" in refused(model="veo3.1", references=2)
    assert "not both" in refused(model="seedance2.5", references=2, start_frame=True)
    assert "up to 9" in refused(model="seedance2", references=10)


def test_pictures_held_as_references_all_reach_the_model(client, monkeypatch):
    sent = []
    monkeypatch.setattr(api, "_photo_bytes", lambda url, account_id=None: url.encode())
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    monkeypatch.setattr(fal, "generate_from_prompt",
                        lambda prompt, **kw: sent.append(kw) or {"ok": True, "media_url": "u", "asset_id": 2})
    price = client.post("/api/direct/video/quote", json={
        "model": "seedance2.5", "seconds": 8, "resolution": "720p", "references": 2}).json()["credits"]
    r = client.post("/api/direct/video/run", data={
        "model": "seedance2.5", "seconds": "8", "resolution": "720p", "aspect": "9:16",
        "prompt": "@Image1 holds the phone from @Image2", "ref_mode": "references",
        "expect_credits": str(price), "asset_photos": ["/refs/her.jpg", "/refs/app.jpg"]})
    assert r.status_code == 200, r.text
    assert _wait(client, r.json()["job_id"])["status"] == "done"
    assert sent[0]["reference_image"] is None and sent[0]["aspect_ratio"] == "9:16"
    assert len(sent[0]["references"]) == 2


def test_a_clip_prompt_is_held_to_its_models_own_cap(client):
    long = "a slow push in on the storefront " * 160          # ~5,300 characters
    assert direct.clean_prompt(long, video_model="seedance2.5")    # past the old 4,000
    with pytest.raises(ValueError, match="up to 3072"):
        direct.clean_prompt(long, video_model="kling3-turbo-pro")
    with pytest.raises(ValueError, match="under 4000"):
        direct.clean_prompt(long)                                   # a still keeps its cap
    items = {m["id"]: m for m in client.get("/api/direct/video").json()["items"]}
    assert items["kling3-turbo-pro"]["prompt_max"] == 3072
    assert items["seedance2.5"]["max_refs"] == 30 and items["seedance2.5"]["ref_tag"] == "@Image1"
    assert items["veo3.1"]["max_refs"] == 0 and items["veo3.1"]["ref_tag"] is None


def test_a_refused_render_is_a_failed_job_in_plain_words(client, monkeypatch):
    monkeypatch.setattr(fal, "generate_from_prompt",
                        lambda prompt, **kw: {"ok": False, "error": "fal HTTP 500: boom"})
    price = client.post("/api/direct/video/quote", json={"model": "ltx2.3"}).json()["credits"]
    r = client.post("/api/direct/video/run", data={
        "model": "ltx2.3", "prompt": "rain", "expect_credits": str(price)})
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "failed" and "fal HTTP" not in (job.get("error") or "")


# ---------- images ----------

def test_the_image_menu_is_the_composers_picker_with_frames_and_caps(client):
    body = client.get("/api/direct/image").json()
    picker = model_menu.image_menu(ACCOUNT)
    assert [m["id"] for m in body["items"]] == [m["id"] for m in picker["items"]]
    assert body["default"] == picker["default"]
    assert body["aspects"] == list(fal.IMAGE_SIZES) and body["aspect"] in body["aspects"]
    assert "$" not in json.dumps(body)
    caps = {m["id"]: m["max_refs"] for m in body["items"]}
    assert caps[model_menu.NANO_ID] == direct.IMAGE_REF_CAP
    for key in fal.IMAGE_MODELS:
        assert caps[key] == min(direct.IMAGE_REF_CAP, fal.image_max_refs(key))


def test_an_image_quote_counts_only_the_pictures_that_reach_the_model(client):
    for key in fal.IMAGE_MODELS:
        q = client.post("/api/direct/image/quote", json={
            "model": key, "aspect": "16:9", "references": 3}).json()
        used = min(3, fal.image_max_refs(key))
        assert q["references"] == used, key
        assert q["credits"] == ledger.charge_credits(fal.image_usd(key, "16:9", references=used)), key
    nano = client.post("/api/direct/image/quote", json={"model": "nano"}).json()
    assert nano["credits"] == pricing.still_credits(nano_banana.MODEL) and nano["aspect"] == "1:1"
    bad = client.post("/api/direct/image/quote", json={"model": "nano", "aspect": "7:3"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "bad_choice"
    assert client.post("/api/direct/image/quote", json={"model": "dall-e-1"}).status_code == 400


def test_a_still_is_drawn_from_the_prompt_as_typed(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(fal, "generate_image_from_prompt", lambda prompt, **kw: seen.update(
        prompt=prompt, **kw) or {"ok": True, "media_url": "https://bucket.example/s.jpg",
                                 "asset_id": 5, "references": 0})
    key = next(k for k in fal.IMAGE_MODELS if not fal.image_max_refs(k))
    price = client.post("/api/direct/image/quote", json={"model": key, "aspect": "4:5"}).json()["credits"]
    r = client.post("/api/direct/image/run", data={
        "model": key, "aspect": "4:5", "prompt": "a matte black bottle on wet stone",
        "expect_credits": str(price)})
    assert r.status_code == 200, r.text
    job = _wait(client, r.json()["job_id"])
    assert job["status"] == "done" and job["asset"] == "gen:5" and job["media"] == "image"
    assert seen["prompt"] == "a matte black bottle on wet stone"
    assert seen["model"] == key and seen["aspect"] == "4:5" and seen["approved"] is True
    assert seen["bank"] is True and seen["source"] == "direct" and seen["brand_kit"] is False


def test_nano_is_sent_its_references_and_the_literal_prompt(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(api, "_photo_bytes", lambda url, account_id=None: b"jpeg")
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    monkeypatch.setattr(nano_banana, "generate_from_prompt", lambda prompt, **kw: seen.update(
        prompt=prompt, **kw) or {"ok": True, "media_url": "u", "asset_id": 1})
    price = client.post("/api/direct/image/quote", json={
        "model": "nano", "aspect": "9:16", "references": 2}).json()["credits"]
    r = client.post("/api/direct/image/run", data={
        "model": "nano", "aspect": "9:16", "prompt": "her, in the red jacket",
        "expect_credits": str(price), "asset_photos": ["/refs/a.jpg", "/refs/b.jpg"]})
    assert _wait(client, r.json()["job_id"])["status"] == "done"
    assert seen["literal"] is True and seen["aspect_ratio"] == "9:16"
    assert [data for _label, data in seen["reference_image"]] == [b"jpeg", b"jpeg"]


# ---------- the composer's Video line, told to the brain ----------

def test_the_clip_model_note_names_the_pick_and_says_nothing_on_auto():
    assert creative_guide.clip_model_note("") == ""
    assert creative_guide.clip_model_note(None) == ""
    line = creative_guide.clip_model_note("Kling 4.0")
    assert "Kling 4.0" in line and "Do not propose another" in line


def test_the_picked_clip_model_reaches_the_brain_and_a_stranger_is_auto(client, monkeypatch):
    async def refs(form, **kwargs):
        return [], [], []

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(charge, "create_refusal_code", lambda *a, **k: None)
    monkeypatch.setattr(api, "_collect_refs", refs)
    monkeypatch.setattr(scene_chain, "ground", lambda *a, **k: {})
    monkeypatch.setattr(api, "_guide_tools", lambda account_id, **k: (None, None))
    seen = []
    monkeypatch.setattr(creative_guide, "respond",
                        lambda conversation, **kw: seen.append(kw.get("clip_model")) or {"message": "ok"})
    guarded = TestClient(app, headers={"X-Phantra-Model-Connection": "1"})
    convo = json.dumps({"messages": [{"role": "user", "content": "a chase at night"}]})
    for pick in ("veo3.1", "sora-9", ""):
        r = guarded.post("/api/creative-guide", data={
            "conversation": convo, "output": "video", "clip_model": pick})
        assert r.status_code == 200, r.text
        _wait(guarded, r.json()["job_id"])
    assert seen == ["Veo 3.1", None, None]
