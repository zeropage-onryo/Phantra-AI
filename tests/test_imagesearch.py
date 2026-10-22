"""Reference images the agent PICKS instead of types.

On 2026-09-02 the research agent banked eleven references by writing
stock URLs from memory. The CDNs served a photo for every guess, so a
sunny tree was banked as "bark texture", a branded Harley product shot
landed on the faceless brand, and six of the Unsplash source pages
return 404 — while refbin's size/host/format guards all passed and
`bank_reference` stored an attribution nobody ever resolved.

These cover the structural answer: the candidate holds the URL and the
model holds an id. (Banking a candidate behind a spark went with the
research scout, 2026-10-14; `images_for` and the composer redeem ids.)
"""

import json

import pytest

from src import imagesearch, mcp_server, preprod, refbin

JPEG = b"\xff\xd8\xff" + b"pretend jpeg"

def real_jpeg() -> bytes:
    """An actual decodable JPEG. The local-frame path runs refbin's real
    normalisation rather than a patched fetch, so a fake header is not
    enough — it silently returns None and the frame never banks."""
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (48, 32), (40, 44, 52)).save(buf, "JPEG")
    return buf.getvalue()


REAL_SERPER = imagesearch.serper_images


@pytest.fixture(autouse=True)
def no_web(monkeypatch):
    """The web lanes (2026-09-05) are real HTTP; tests never make them.
    Each test that wants a lane patches it back in. Every lane's KEY is
    already unset by conftest (imagesearch.LANE_ENV); Openverse needs
    none and is on unless told otherwise, so it is switched off here."""
    for lane in ("openverse", "google_images", "serper_images", "unsplash", "pexels"):
        monkeypatch.setattr(imagesearch, lane, lambda q, limit=6: [])
    monkeypatch.setattr(imagesearch, "reddit", lambda q, limit=6: [])
    monkeypatch.setenv("OPENVERSE_LANE", "0")


@pytest.fixture
def tmp_db(pg, tmp_path, monkeypatch):
    path = pg
    preprod.init(path)
    imagesearch.init(path)
    monkeypatch.setenv("DATABASE_URL", path)
    monkeypatch.setattr(refbin, "REFS_DIR", tmp_path / "refs")
    return path


@pytest.fixture
def stock(monkeypatch):
    """A configured Unsplash lane with two real-shaped results."""
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "k")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.setattr(imagesearch, "unsplash", lambda q, limit=6: [
        {"source": "unsplash", "image_url": "https://images.example/a.jpg",
         "source_url": "https://unsplash.example/photos/real-a",
         "title": "cold light on wet tile", "credit": "A N on Unsplash"},
        {"source": "unsplash", "image_url": "https://images.example/b.jpg",
         "source_url": "https://unsplash.example/photos/real-b",
         "title": "an empty corridor", "credit": "B N on Unsplash"},
    ])


# ---------- the omitted field is the feature ----------

def test_the_search_hands_back_ids_and_no_urls(tmp_db, stock):
    out = mcp_server.find_images("cold light on wet tile",
                                 dsn=tmp_db)

    assert out["count"] == 2
    for img in out["images"]:
        assert img["id"] and img["shows"] and img["credit"]
        # nothing here for a model to copy, mistype or half-remember
        assert not any("url" in k.lower() for k in img)
        assert "http" not in json.dumps(img)


# ---------- "nothing configured" is not "nothing matched" ----------

def test_an_unconfigured_lane_says_so(tmp_db):
    """The distinction the empty scout bin hid for two days. No key is
    set: conftest unsets every lane's, whatever this machine's .env says."""
    out = mcp_server.find_images("anything",dsn=tmp_db)

    assert out["count"] == 0
    assert "no image source is configured" in out["note"]
    assert out["sources"] == {"openverse": False, "google": False,
                              "reddit": False,
                              "unsplash": False, "pexels": False,
                              "serper": False}


def test_the_lane_keys_the_suite_unsets_are_all_of_them(monkeypatch):
    """conftest unsets imagesearch.LANE_ENV for every test; this checks the
    list is whole. Every OTHER variable reads as set, the way a full .env
    does, so a lane keyed on anything missing from the list lights up here
    -- the SERPER_API_KEY leak of 2026-10-02, caught in CI instead of on
    one Mac."""
    import types

    class FullEnv(dict):
        def get(self, key, default=None):
            return default if key in imagesearch.LANE_ENV else "set"

    monkeypatch.setattr(imagesearch, "os", types.SimpleNamespace(environ=FullEnv()))
    live = imagesearch.sources()
    assert [lane for lane, on in live.items() if on] == ["openverse"]


def test_openverse_is_the_keyless_floor(tmp_db, monkeypatch):
    """With no key at all the agent still gets real photographs off the
    internet -- Mike's 2026-09-05 call: references are images pulled off
    the web for the spark, not his footage."""
    monkeypatch.setenv("OPENVERSE_LANE", "1")
    monkeypatch.setattr(imagesearch, "openverse", lambda q, limit=6: [
        {"source": "openverse", "image_url": "https://live.example/x_b.jpg",
         "source_url": "https://www.flickr.com/photos/someone/1", "title": "wet street",
         "credit": "someone on flickr"}])
    out = mcp_server.find_images("wet street night",dsn=tmp_db)
    assert out["count"] == 1 and out["sources"]["openverse"] is True
    assert out["images"][0]["source"] == "openverse" and "image_url" not in out["images"][0]


def test_web_lanes_interleave_reddit_google_openverse(monkeypatch):
    monkeypatch.setattr(imagesearch, "reddit", lambda q, limit=6: [
        {
          "source": "reddit",
          "image_url": "https://i.example/r1.jpg",
          "source_url": "https://www.reddit.com/r/x/1",
          "title": "",
          "credit": ""
         }])
    monkeypatch.setattr(imagesearch, "google_images", lambda q, limit=6: [
        {
          "source": "google",
          "image_url": "https://i.example/g1.jpg",
          "source_url": "https://p.example/g1",
          "title": "",
          "credit": ""
         },
        {
          "source": "google",
          "image_url": "https://i.example/g2.jpg",
          "source_url": "https://p.example/g2",
          "title": "",
          "credit": ""
         }])
    monkeypatch.setattr(imagesearch, "openverse", lambda q, limit=6: [
        {
          "source": "openverse",
          "image_url": "https://i.example/o1.jpg",
          "source_url": "https://p.example/o1",
          "title": "",
          "credit": ""
         }])
    monkeypatch.setattr(imagesearch, "remember", lambda c, query="", dsn=None: c)
    got = [c["source"] for c in imagesearch.search("q", limit=6)]
    assert got == ["reddit", "google", "openverse", "google"]


def test_a_configured_lane_that_matched_nothing_says_something_else(tmp_db,
                                                                    monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "k")
    monkeypatch.setattr(imagesearch, "unsplash", lambda q, limit=6: [])
    monkeypatch.setattr(imagesearch, "pexels", lambda q, limit=6: [])

    out = mcp_server.find_images("nothing at all",dsn=tmp_db)
    assert out["count"] == 0 and "nothing matched" in out["note"]


# ---------- serper: the whole-web lane that can find a NAMED thing ----------

def test_serper_is_off_without_a_key(monkeypatch):
    monkeypatch.setattr(imagesearch, "serper_images", REAL_SERPER)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    assert imagesearch.serper_images("Ghost energy orange cream can") == []
    assert imagesearch.sources()["serper"] is False


def test_serper_maps_results_and_keeps_the_thumbnail_as_a_second_address(monkeypatch):
    import requests

    monkeypatch.setattr(imagesearch, "serper_images", REAL_SERPER)
    monkeypatch.setenv("SERPER_API_KEY", "k")
    seen = {}

    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"images": [
                {"title": "Ghost Orange Cream", "imageUrl": "https://cdn.shop/ghost.jpg",
                 "thumbnailUrl": "https://encrypted-tbn0.gstatic.com/t.jpg",
                 "link": "https://shop.example/ghost", "source": "shop.example"},
                {"title": "no page", "imageUrl": "https://cdn.shop/x.jpg"},
                {"title": "not http", "imageUrl": "data:image/png;base64,AA", "link": "https://p"},
            ]}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, key=headers.get("X-API-KEY"), q=json["q"])
        return _R()

    monkeypatch.setattr(requests, "post", post)
    out = imagesearch.serper_images("Ghost energy orange cream can", limit=6)
    assert seen == {"url": "https://google.serper.dev/images", "key": "k",
                    "q": "Ghost energy orange cream can"}
    assert out == [{"source": "google", "image_url": "https://cdn.shop/ghost.jpg",
                    "source_url": "https://shop.example/ghost", "title": "Ghost Orange Cream",
                    "credit": "shop.example",
                    "fallback_url": "https://encrypted-tbn0.gstatic.com/t.jpg"}]


def test_the_second_address_is_stored_and_redeemed(tmp_db):
    imagesearch.remember([{"source": "openverse", "image_url": "https://live.staticflickr.com/a.jpg",
                           "source_url": "https://flickr.com/p/a", "title": "a",
                           "fallback_url": "https://api.openverse.org/v1/images/a/thumb/"}],
                         query="q", dsn=tmp_db)
    cid = imagesearch._cid("openverse", "https://live.staticflickr.com/a.jpg")
    row = imagesearch.get(cid, dsn=tmp_db)
    assert row["fallback_url"] == "https://api.openverse.org/v1/images/a/thumb/"
