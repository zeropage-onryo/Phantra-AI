"""Before and after as one image (src/side_by_side.py, GET /api/side-by-side, 2026-10-27)."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import api as api_mod
from app.main import app
from src import outcomes, side_by_side

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    from app import auth
    monkeypatch.setattr(auth, "current_user",
                        lambda request: {"id": 1, "email": "t@example.com", "display_name": "T"})


def _jpeg(w: int, h: int, colour) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "JPEG")
    return buf.getvalue()


def test_the_pair_is_one_image_at_one_height_original_on_the_left():
    out = side_by_side.compose(_jpeg(600, 800, (200, 0, 0)), _jpeg(900, 1200, (0, 0, 200)))
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and img.height == side_by_side.HEIGHT
    # 3:4 and 3:4 at 1280 tall: 960 + the seam + 960
    assert img.width == 960 + side_by_side.GAP + 960
    left = img.getpixel((480, 900))
    right = img.getpixel((960 + side_by_side.GAP + 480, 900))
    assert left[0] > 150 and left[2] < 80          # the original, red
    assert right[2] > 150 and right[0] < 80        # the result, blue


def test_a_wide_pair_is_kept_postable_and_garbage_is_none():
    out = side_by_side.compose(_jpeg(1920, 1080, (0, 0, 0)), _jpeg(1920, 1080, (0, 0, 0)))
    assert Image.open(io.BytesIO(out)).width <= side_by_side.MAX_WIDTH
    assert side_by_side.compose(b"not an image", _jpeg(10, 10, (0, 0, 0))) is None


def test_the_route_downloads_the_pair_for_the_callers_own_render(monkeypatch):
    seen = []
    monkeypatch.setattr(api_mod, "_picture_bytes",
                        lambda ref, account_id: seen.append(ref) or _jpeg(300, 400, (10, 200, 10)))
    monkeypatch.setattr(outcomes, "record_ref", lambda *a, **k: None)
    r = client.get("/api/side-by-side", params={"before": "/refs/me.jpg", "after": "gen:42"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert "attachment" in r.headers["content-disposition"]
    assert seen == ["/refs/me.jpg", "gen:42"]


def test_the_route_refuses_an_after_that_is_not_a_render_id_and_says_when_it_cannot_read(monkeypatch):
    monkeypatch.setattr(api_mod, "_picture_bytes", lambda ref, account_id: None)
    r = client.get("/api/side-by-side", params={"before": "x", "after": "https://example.com/a.jpg"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_after"
    r = client.get("/api/side-by-side", params={"before": "x", "after": "gen:7"})
    assert r.status_code == 404
