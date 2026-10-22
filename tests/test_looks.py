"""The free looks (src/looks.py, 2026-10-22, group 2 of
docs/tasks/task-overnight-2026-10-22.md): five non-generative effects and
the Make It Pro bundle, ffmpeg on this server, 0 credits, through the
effects door unchanged.

Every clip here is synthetic: ffmpeg's `testsrc2`, made in the test. The
whole file is skipped when ffmpeg is not on the PATH. Nothing in it
reaches a provider or takes a hold -- the tests that run the door assert
exactly that."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, effects, fal, generative, ledger, looks, looks_assets, render_assets

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="ffmpeg is not installed on this host")

FPS = 30


def _clip(path: Path, size="1280x720", seconds=2.0, audio=True) -> Path:
    """A moving test pattern, with a tone under it or silent."""
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={FPS}:duration={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac"]
    else:
        args += ["-an"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, timeout=120)
    return path


def _static(path: Path, seconds=2.0) -> Path:
    """One frame held for `seconds`: a zoom is measurable on it."""
    png = path.with_suffix(".png")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"testsrc2=size=1280x720:rate={FPS}", "-frames:v", "1", str(png)],
                   check=True, timeout=120)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1",
                    "-framerate", str(FPS), "-t", str(seconds), "-i", str(png),
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)],
                   check=True, timeout=120)
    return path


def _frames(path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                          "-show_entries", "stream=nb_read_frames", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True, timeout=120).stdout
    return int(json.loads(out)["streams"][0]["nb_read_frames"])


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("looks-clips")
    return {"moving": _clip(d / "moving.mp4"), "silent": _clip(d / "silent.mp4", audio=False),
            "static": _static(d / "static.mp4"), "odd": _clip(d / "odd.mp4", size="1000x600",
                                                              seconds=1.0, audio=False)}


@pytest.fixture(scope="module")
def assets(tmp_path_factory):
    """The generated assets, once per module (a LUT is 36k lines)."""
    return looks_assets.write_all(tmp_path_factory.mktemp("looks-assets"))


@pytest.fixture(autouse=True)
def looks_on(monkeypatch, output_roots_in_tmp, assets):
    monkeypatch.setenv(looks.ENV, "1")
    monkeypatch.setattr(looks, "ASSETS_DIR", assets["README.md"].parent)


def _mean_diff(a, b) -> float:
    from PIL import ImageChops, ImageStat
    return ImageStat.Stat(ImageChops.difference(a.convert("L"), b.convert("L"))).mean[0]


# ---------- the table ----------

def test_the_looks_are_free_rows_of_the_effects_table_behind_the_flag(monkeypatch):
    ids = ("film_grade", "noir", "flash_2000s", "crash_zoom", "vertical_ready", "make_it_pro")
    assert looks.LOOK_NAMES == ids
    probe = {"seconds": 6.0, "width": 1280, "height": 720, "fps": 30.0}
    for name in ids:
        row = effects.EFFECTS[name]
        assert row["provider"] == "local" and row["free"] is True and row["category"] == "look"
        assert row["takes"] == "video" and row["output"] == "video" and row["prompt"] == "none"
        assert set(row["tags"]) <= set(looks.TAGS) and row["tags"]
        assert effects.quote_usd(name, effects.check_options(name, {}), probe) == 0.0
        assert effects.is_free(name)
        listed = effects.catalogue(effect=name)[0]
        assert listed["free"] is True and listed["pricing"].startswith("free")
        assert "$" not in listed["pricing"] and "fal.ai" not in listed["page"]
    assert "look" in effects.CATEGORIES
    assert all(n in effects.listed_names() for n in ids)
    # an option off the legal set is refused, never clamped
    with pytest.raises(ValueError, match="not one of"):
        effects.check_options("crash_zoom", {"zoom": 2.0})
    assert effects.check_options("crash_zoom", {"zoom": 1.5}) == {"zoom": 1.5}
    assert effects.check_options("film_grade", {})["letterbox"] is True
    # OFF (the default): not listed, and refused by name at the one gate
    monkeypatch.delenv(looks.ENV)
    assert not looks.enabled()
    assert not set(ids) & set(effects.listed_names())
    assert not [r for r in effects.catalogue() if r["category"] == "look"]
    with pytest.raises(ValueError, match="not switched on"):
        effects.spec("noir")
    assert effects.spec("upscale")["endpoint"].startswith("fal-ai/")


def test_the_capability_is_off_by_default(monkeypatch):
    from app import api
    monkeypatch.setattr(api, "_rag_reachable", lambda: False)
    assert api.compute_capabilities(None)["free_looks"] is True
    monkeypatch.delenv(looks.ENV)
    assert api.compute_capabilities(None)["free_looks"] is False


# ---------- the assets ----------

def test_the_assets_are_generated_deterministic_and_say_so(tmp_path):
    first = looks_assets.write_all(tmp_path / "a")
    again = looks_assets.write_all(tmp_path / "b")
    assert set(first) == set(looks_assets.FILES)
    for name in looks_assets.FILES:
        assert first[name].stat().st_size > 0
        assert first[name].read_bytes() == again[name].read_bytes(), name
    head = first["film_grade.cube"].read_text().splitlines()
    assert head[1] == f"LUT_3D_SIZE {looks_assets.LUT_SIZE}"
    assert len(head) == 4 + looks_assets.LUT_SIZE ** 3
    noir = first["noir.cube"].read_text().splitlines()[-1].split()
    assert noir[0] == noir[1] == noir[2]                   # one value on every channel
    assert "GENERATED" in first["README.md"].read_text()
    assert "downloaded" in first["README.md"].read_text()
    # only_missing leaves a present file alone
    stamp = first["whoosh.wav"].stat().st_mtime_ns
    time.sleep(0.01)
    looks_assets.write_all(tmp_path / "a", only_missing=True)
    assert first["whoosh.wav"].stat().st_mtime_ns == stamp


# ---------- each look, and its time per second ----------

@pytest.mark.parametrize("look", ("film_grade", "noir", "flash_2000s", "crash_zoom",
                                  "vertical_ready"))
def test_each_look_runs_and_logs_its_time_per_second_of_input(look, clips, tmp_path, capfd):
    out = tmp_path / f"{look}.mp4"
    res = looks.apply(look, clips["moving"], out)
    facts = looks.probe(out)
    assert abs(facts["seconds"] - 2.0) < 0.1 and facts["audio"] is True
    timing = res["timing"]
    assert timing["seconds_in"] == pytest.approx(2.0, abs=0.05)
    assert timing["elapsed"] > 0 and timing["per_second"] > 0
    assert timing["per_second"] == pytest.approx(timing["elapsed"] / timing["seconds_in"],
                                                 rel=0.01)
    err = capfd.readouterr().err
    assert f"[looks] {look}: " in err and "per second of input" in err


def test_noir_is_true_greyscale(clips, tmp_path):
    out = tmp_path / "noir.mp4"
    looks.apply("noir", clips["moving"], out)
    for t in (0.0, 0.5, 1.0, 1.9):
        w, h, y, u, v = looks.frame_yuv(out, t)
        assert len(u) == len(v) == (w // 2) * (h // 2)
        assert 126 <= min(u) and max(u) <= 130, (t, min(u), max(u))
        assert 126 <= min(v) and max(v) <= 130, (t, min(v), max(v))
        assert max(y) - min(y) > 60                     # a picture, not a grey card


def test_vertical_ready_is_exactly_nine_by_sixteen(clips, tmp_path):
    for name in ("moving", "odd"):
        out = tmp_path / f"vertical-{name}.mp4"
        res = looks.apply("vertical_ready", clips[name], out)
        facts = looks.probe(out)
        assert facts["width"] * 16 == facts["height"] * 9, (facts["width"], facts["height"])
        assert facts["width"] % 2 == 0 and facts["height"] % 2 == 0
        assert tuple(res["size"]) == (facts["width"], facts["height"])
    assert looks.vertical_crop(1280, 720) == (396, 704)
    assert looks.vertical_crop(1000, 600) == (324, 576)
    assert looks.vertical_crop(720, 1280) == (720, 1280)
    with pytest.raises(ValueError, match="too small"):
        looks.vertical_crop(8, 8)


def test_film_grade_letterboxes_to_2_39(clips, tmp_path):
    out = tmp_path / "film.mp4"
    res = looks.apply("film_grade", clips["moving"], out)
    bar = res["params"]["letterbox_bar"]
    assert bar > 0 and res["params"]["active"]["height"] == 720 - 2 * bar
    for t in (0.2, 1.0):
        active = looks.nonblack_rows(out, t)
        assert abs(1280 / active - 2.39) <= 0.01, (t, active, 1280 / active)
    plain = tmp_path / "film-open.mp4"
    res = looks.apply("film_grade", clips["moving"], plain, {"letterbox": False})
    assert "letterbox_bar" not in res["params"]
    assert looks.nonblack_rows(plain, 0.5) == 720
    for w, h in ((1280, 720), (1920, 1080), (720, 1280)):
        bar = looks.letterbox_bar(w, h)
        assert abs(w / (h - 2 * bar) - 2.39) <= 0.01
    assert looks.letterbox_bar(2390, 1000) == 0           # already that wide


def test_crash_zoom_is_zoomed_on_the_first_beat_and_carries_a_whoosh(clips, tmp_path):
    out = tmp_path / "crash.mp4"
    res = looks.apply("crash_zoom", clips["static"], out)
    # from the parameters the graph was built with
    assert res["params"]["zoom_at_0"] == 1.0
    assert res["params"]["zoom_at_0.3"] >= 1.15
    assert looks.zoom_at(0.15, 1.35) == pytest.approx(1.175)
    assert looks.zoom_at(2.0, 1.35) == 1.0
    assert "zoompan" in res["graph"]
    # and on the frames themselves: the frame at 0.3s IS the centre of the
    # frame at 0 blown up by at least 1.15
    first = looks.frame_image(out, 0.0)
    assert looks.measured_zoom(first, looks.frame_image(out, 0.3)) >= 1.15
    assert looks.measured_zoom(first, looks.frame_image(out, 1.9)) == 1.0
    # the whoosh: a silent source comes back with sound
    assert looks.probe(clips["static"])["audio"] is False
    assert looks.probe(out)["audio"] is True
    stronger = looks.apply("crash_zoom", clips["static"], tmp_path / "hard.mp4", {"zoom": 1.5})
    assert stronger["params"]["zoom_at_0.3"] == 1.5


def test_flash_2000s_pops_and_stamps(clips, tmp_path):
    stamped = tmp_path / "flash.mp4"
    res = looks.apply("flash_2000s", clips["static"], stamped)
    assert res["params"]["stamp"] is True and res["params"]["flash"]["period"] == 2.4
    # a pop at t=0 (the first 0.1s): brighter than the frame after it
    from PIL import ImageStat
    pop = ImageStat.Stat(looks.frame_image(stamped, 0.03).convert("L")).mean[0]
    quiet = ImageStat.Stat(looks.frame_image(stamped, 0.5).convert("L")).mean[0]
    assert pop > quiet + 20, (pop, quiet)
    # the date stamp sits bottom-right: that corner differs from the
    # unstamped output, the opposite corner does not
    plain = tmp_path / "flash-plain.mp4"
    looks.apply("flash_2000s", clips["static"], plain, {"stamp": False})
    a, b = looks.frame_image(stamped, 0.5), looks.frame_image(plain, 0.5)
    corner = (1280 - 260, 720 - 90, 1280, 720)
    assert _mean_diff(a.crop(corner), b.crop(corner)) > 2
    assert _mean_diff(a.crop((0, 0, 260, 90)), b.crop((0, 0, 260, 90))) < 1.5


# ---------- the end card ----------

@pytest.mark.parametrize("name", ("moving", "silent"))
def test_the_end_card_adds_one_second_that_is_not_the_clip(name, clips, tmp_path):
    src = clips[name]
    out = tmp_path / f"card-{name}.mp4"
    res = looks.append_end_card(src, out)
    assert res["seconds"] == 1.0 and res["timing"]["per_second"] > 0
    assert abs(_frames(out) - (_frames(src) + FPS)) <= 1      # input + 1s, within a frame
    assert looks.probe(out)["audio"] is (name == "moving")   # sound only where there was sound
    last_in = looks.frame_image(src, 1.95)
    for t in (2.05, 2.5, 2.95):                               # the whole last second
        assert _mean_diff(last_in, looks.frame_image(out, t)) > 20
    assert _mean_diff(looks.frame_image(out, 2.5), looks.frame_image(out, 2.9)) < 1
    # the frame before the card is still the clip's
    assert _mean_diff(last_in, looks.frame_image(out, 1.95)) < 6


def test_the_end_card_is_drawn_without_drawtext(tmp_path):
    """The Mac's ffmpeg has no drawtext; the card and the stamp are drawn
    with Pillow's bundled font, so the words are there on any host."""
    png = looks.end_card_png(640, 360, tmp_path / "card.png")
    from PIL import Image
    im = Image.open(png).convert("RGB")
    assert im.size == (640, 360)
    centre = im.crop((160, 120, 480, 240))
    assert len(centre.getcolors(maxcolors=1 << 20)) > 50     # words and the dot, not a flat card
    assert im.getpixel((5, 5)) == looks.CARD_BG
    stamp = Image.open(looks.date_stamp_png(640, 360, tmp_path / "stamp.png")).convert("RGBA")
    alpha = stamp.getchannel("A")
    assert alpha.crop((400, 300, 640, 360)).getextrema()[1] > 200
    assert alpha.crop((0, 0, 240, 60)).getextrema() == (0, 0)
    assert isinstance(looks.has_drawtext(), bool)


# ---------- the effects door: no key, no cap, no hold ----------

@pytest.fixture
def tmp_db(pg):
    generative.init(pg)
    render_assets.init(pg)
    ledger.init(pg)
    accounts.init(pg)
    return pg


@pytest.fixture
def account(tmp_db) -> int:
    """The workspace the clips and the looks belong to (the wall's rows
    carry a foreign key to it)."""
    return accounts.upsert_account("looks-test", "Looks", "#fff", dsn=tmp_db)


@pytest.fixture
def nothing_spends(monkeypatch):
    """Any hold, any fal call, any cap check is a test failure."""
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.delenv("FAL_API_KEY", raising=False)
    monkeypatch.setattr(fal.charging.Charge, "take",
                        lambda self: pytest.fail("a free look took a ledger hold"))
    monkeypatch.setattr(ledger, "hold_for_render",
                        lambda *a, **k: pytest.fail("a free look reached the ledger"))
    monkeypatch.setattr(fal, "_submit_and_wait",
                        lambda *a, **k: pytest.fail("a free look reached fal"))
    monkeypatch.setattr(generative, "cap_error",
                        lambda *a, **k: pytest.fail("a free look hit the stills' cap"))


def _on_wall(pg, path: Path, account_id, n=[0]) -> int:
    """A clip on this account's Assets wall whose file is on this disk."""
    n[0] += 1
    return render_assets.record(
        generation_id=n[0], tool="fal", model="ltx2.3", media_kind="video", prompt="a clip",
        media_url=f"https://cdn.example/clip-{n[0]}.mp4", output_path=str(path),
        dsn=pg, account_id=account_id)["id"]


def test_a_free_look_runs_through_effects_run_with_no_key_no_cap_and_no_hold(
        tmp_db, account, clips, nothing_spends):
    asset_id = _on_wall(tmp_db, clips["moving"], account)
    res = effects.run("noir", [], "", {}, usd=0.0, sources=[f"gen:{asset_id}"],
                      account_id=account, db_path=tmp_db, source="composer",
                      publish=lambda path, ctype, account_id=None: f"/renders/looks/{path.name}")
    assert res["ok"] is True, res["error"]
    assert res["credits"] == 0 and res["media_kind"] == "video" and res["next"] is None
    assert res["media_url"].startswith("/renders/looks/look-noir-")
    assert res["asset_id"] and res["ref"] == f"gen:{res['asset_id']}"
    out = Path(res["path"])
    assert out.is_file() and out.parent == looks.RENDER_DIR
    assert abs(_frames(out) - (_frames(clips["moving"]) + FPS)) <= 1      # the end card is on
    assert res["timing"]["look"]["per_second"] > 0 and res["timing"]["end_card"]["per_second"] > 0
    with generative.connect(tmp_db) as conn:
        tool, cost, params = conn.execute(
            "SELECT tool, cost_usd, params_json FROM generations").fetchone()
    params = json.loads(params)
    assert tool == looks.LOG_TOOL and cost is None
    assert params["provider"] == "local" and params["free"] is True and params["credits"] == 0
    assert params["model"] == "noir" and params["sources"] == [f"gen:{asset_id}"]
    assert "ledger_ref" not in params                         # no hold, so no hold to find
    assert params["timing"]["look"]["seconds_in"] == pytest.approx(2.0, abs=0.05)
    row = render_assets.get(res["asset_id"], tmp_db, account_id=account)
    assert row["model"] == "noir" and row["media_kind"] == "video"
    assert row["metadata"]["free"] is True


def test_a_file_on_this_disk_can_be_handed_straight_to_the_door(tmp_db, account, clips,
                                                                nothing_spends):
    """The showcase stream runs the looks on files it holds: effects.run
    takes the path where a paid effect takes a URL."""
    res = effects.run("vertical_ready", [str(clips["silent"])], "", {}, usd=0.0,
                      account_id=account, db_path=tmp_db,
                      publish=lambda path, ctype, account_id=None: f"/renders/looks/{path.name}")
    assert res["ok"] is True, res["error"]
    facts = looks.probe(res["path"])
    assert facts["width"] * 16 == facts["height"] * 9


def test_make_it_pro_runs_the_free_part_and_hands_back_a_priced_sound_pass_card(
        tmp_db, account, clips, nothing_spends, monkeypatch):
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    asset_id = _on_wall(tmp_db, clips["moving"], account)
    res = effects.run("make_it_pro", [], "", {}, usd=0.0, sources=[f"gen:{asset_id}"],
                      account_id=account, db_path=tmp_db,
                      publish=lambda path, ctype, account_id=None: f"/renders/looks/{path.name}")
    assert res["ok"] is True, res["error"]
    assert res["credits"] == 0
    facts = looks.probe(res["path"])
    assert facts["width"] * 16 == facts["height"] * 9           # Vertical Ready
    row = render_assets.get(res["asset_id"], tmp_db, account_id=account)
    assert "lut3d" in row["metadata"]["graph"] and "crop=" in row["metadata"]["graph"]
    # the Sound Pass SLOT: a priced card on the clip just made, not a run
    card = res["next"]
    assert card["effect"] == "add-sound" and card["label"] == "Sound Pass"
    assert card["sources"] == [res["ref"]] and card["prompt"]
    expected = ledger.charge_credits(effects.quote_usd("add-sound", {}, looks.probe(res["path"])))
    assert card["credits"] == expected and expected >= 10 and card["charged"] is True
    assert card["clip"]["seconds"] == pytest.approx(facts["seconds"])
    assert "Approve" in card["note"]
    with generative.connect(tmp_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0] == 1


# ---------- the studio door (POST /api/effects/run) ----------

@pytest.fixture
def client(tmp_db, account, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", tmp_db)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "looks-user"})
    monkeypatch.setattr(auth, "current_account", lambda request: {"slug": "phantra"})
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)   # no fal at all
    app.dependency_overrides[auth.current_account_id] = lambda: account
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)


def _wait(client, job_id):
    for _ in range(600):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(.05)
    raise AssertionError("job never finished")


def test_the_gallery_lists_the_looks_free_and_tagged_only_when_on(client, monkeypatch):
    body = client.get("/api/effects").json()
    by = {e["id"]: e for e in body["items"]}
    for name in looks.LOOK_NAMES:
        assert by[name]["credits"] == 0 and by[name]["free"] is True
        assert by[name]["category"] == "look" and by[name]["tags"]
        assert by[name]["blurb"] == looks.LOOKS[name]["blurb"]
    assert {"id": "look", "label": "Free looks"} in body["categories"]
    assert all(e["free"] is False for e in body["items"] if e["category"] != "look")
    assert "$" not in json.dumps(body)
    monkeypatch.delenv(looks.ENV)
    off = client.get("/api/effects").json()
    assert not {e["id"] for e in off["items"]} & set(looks.LOOK_NAMES)
    assert "look" not in {c["id"] for c in off["categories"]}
    refused = client.post("/api/effects/quote", json={"effect": "noir", "sources": ["gen:1"]})
    assert refused.status_code == 400 and "not switched on" in refused.json()["error"]["message"]


def test_the_studio_door_runs_a_look_at_zero_credits_and_opens_the_sound_pass_card(
        client, tmp_db, account, clips, nothing_spends):
    asset_id = _on_wall(tmp_db, clips["moving"], account)
    body = {"effect": "make_it_pro", "sources": [f"gen:{asset_id}"]}
    quote = client.post("/api/effects/quote", json=body)
    assert quote.status_code == 200, quote.text
    assert quote.json()["credits"] == 0 and quote.json()["charged"] is False
    assert quote.json()["clip"]["seconds"] == pytest.approx(2.0, abs=0.05)
    # the card's own rules still hold: the price it showed, or nothing
    assert client.post("/api/effects/run", json=body).json()["error"]["code"] == "missing_price"
    stale = client.post("/api/effects/run", json={**body, "expect_credits": 10})
    assert stale.status_code == 409 and stale.json()["credits"] == 0
    started = client.post("/api/effects/run", json={**body, "expect_credits": 0})
    assert started.status_code == 200, started.text          # no fal key needed
    assert started.json() == {"job_id": started.json()["job_id"], "credits": 0, "charged": False}
    job = _wait(client, started.json()["job_id"])
    assert job["status"] == "done", job
    assert job["detail"] == "Make It Pro · done · free" and job["media"] == "video"
    assert job["output"].startswith("/renders/looks/look-make_it_pro-")
    assert job["asset"].startswith("gen:") and job["kind"] == "effect"
    card = job["next"]
    assert card["effect"] == "add-sound" and card["sources"] == [job["asset"]]
    assert card["credits"] >= 10 and card["charged"] is True
    # ...and that card prices on the real door exactly as the slot said
    priced = client.post("/api/effects/quote", json={
        "effect": card["effect"], "sources": card["sources"], "prompt": card["prompt"]})
    assert priced.status_code == 200, priced.text
    assert priced.json()["credits"] == card["credits"]
    # the paid effects are still refused without fal, as before
    assert client.post("/api/effects/run", json={
        "effect": "add-sound", "sources": card["sources"], "prompt": card["prompt"],
        "expect_credits": card["credits"]}).status_code == 503


# ---------- the connector ----------

def test_the_connector_quotes_a_look_at_zero_and_runs_it_with_no_token(
        tmp_db, account, clips, nothing_spends):
    from src import mcp_server
    asset_id = _on_wall(tmp_db, clips["silent"], account)
    dry = mcp_server.run_effect("vertical_ready", [f"gen:{asset_id}"], dsn=tmp_db,
                                account_id=account, dry_run=True)
    assert dry == {"ok": True, "dry_run": True, "approved": None, "quote": dry["quote"]}
    assert dry["quote"]["credits"] == 0 and dry["quote"]["charged"] is False
    assert dry["quote"]["usd"] == 0.0 and dry["quote"]["note"] == looks.FREE_NOTE
    with pytest.raises(ValueError, match="not one of"):
        mcp_server.run_effect("crash_zoom", [f"gen:{asset_id}"], options={"zoom": 9},
                              dsn=tmp_db, account_id=account, dry_run=True)
    with pytest.raises(ValueError, match="takes no prompt"):
        mcp_server.run_effect("noir", [f"gen:{asset_id}"], prompt="moody", dsn=tmp_db,
                              account_id=account, dry_run=True)
    res = mcp_server.run_effect("vertical_ready", [f"gen:{asset_id}"], dsn=tmp_db,
                                account_id=account)
    assert res["ok"] is True, res.get("error")
    assert res["credits"] == 0 and res["quote"]["credits"] == 0
    facts = looks.probe(res["path"])
    assert facts["width"] * 16 == facts["height"] * 9
