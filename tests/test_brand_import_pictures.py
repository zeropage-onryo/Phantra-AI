"""The site's pictures in a brand import (step 1 of docs/tasks/task-url-to-ad.md).

The browser test serves a two-page site from a local server and never
reaches the web; every other test is pure or stubs the model and the
element create.
"""
import http.server
import io
import os
import threading

import pytest
from PIL import Image

from app import brand_routes
from src import accounts, brand_import, brand_kits, entities


def _chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


# skipped on a machine without the browser, never in CI (which installs it)
needs_chromium = pytest.mark.skipif(not _chromium() and not os.environ.get("CI"),
                                    reason="Playwright's Chromium is not installed")


def _png(w, h, colour=(200, 120, 40)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


# --- ranking (pure) --------------------------------------------------------

def test_the_page_preview_leads_and_logos_icons_and_svgs_are_left_out():
    drawn = [
        {"url": "https://a.example/logo.png", "w": 200, "h": 60, "logo": True},
        {"url": "https://a.example/icon.png", "w": 32, "h": 32},
        {"url": "https://a.example/badge.png", "w": 300, "h": 200, "chrome": True},
        {"url": "https://a.example/mark.svg", "w": 800, "h": 600},
        {"url": "https://a.example/small.jpg", "w": 300, "h": 300, "alt": "a phone"},
        {"url": "https://a.example/hero.jpg", "w": 1200, "h": 700},
        {"url": "http://a.example/hero.jpg", "w": 1200, "h": 700},          # one file, two schemes
    ]
    meta = ["https://a.example/og.jpg"]
    urls = [c["url"] for c in brand_import.rank_pictures(drawn, meta)]
    assert urls == ["https://a.example/og.jpg", "https://a.example/hero.jpg",
                    "https://a.example/small.jpg"]


def test_a_big_picture_in_the_header_still_counts_but_ranks_lower():
    drawn = [{"url": "https://a.example/banner.jpg", "w": 1400, "h": 500, "chrome": True},
             {"url": "https://a.example/body.jpg", "w": 900, "h": 600}]
    urls = [c["url"] for c in brand_import.rank_pictures(drawn, [])]
    assert urls == ["https://a.example/body.jpg", "https://a.example/banner.jpg"]


# --- keeping (pure) --------------------------------------------------------

def test_small_unreadable_and_repeated_pictures_are_not_kept():
    raw = [{"url": "u1", "data": _png(900, 600)},
           {"url": "u2", "data": _png(900, 600)},                 # the same picture again
           {"url": "u3", "data": _png(300, 200)},                 # under the floor
           {"url": "u4", "data": b"not a picture"},
           {"url": "u5", "data": _png(500, 1000, (10, 10, 10))}]
    kept, notes = brand_import.keep_pictures(raw)
    assert [k["url"] for k in kept] == ["u1", "u5"]
    assert all(k["data"][:2] == b"\xff\xd8" for k in kept)       # JPEG
    assert (kept[1]["w"], kept[1]["h"]) == (500, 1000)
    assert any("could not be opened" in n for n in notes)
    assert any("under 400 px" in n for n in notes)


def test_at_most_twelve_are_kept():
    raw = [{"url": f"u{i}", "data": _png(800, 600, (i * 9, 50, 50))} for i in range(20)]
    kept, _ = brand_import.keep_pictures(raw)
    assert len(kept) == brand_import.PICTURES_MAX == 12


# --- sorting (the model stubbed) -------------------------------------------

PICS = [{"url": f"u{i}", "page": "https://a.example/", "data": b""} for i in range(1, 6)]


def test_products_and_screens_become_products_and_the_rest_look():
    def model(brand, pictures, *, account_id):
        assert brand == "Acme" and len(pictures) == 5
        return {"pictures": [
            {"n": 1, "kind": "product", "keep": True, "name": "Orange rocket on a stand"},
            {"n": 2, "kind": "interface", "keep": True, "name": "Booking screen https://x.io"},
            {"n": 3, "kind": "person", "keep": True, "name": "Woman smiling"},
            {"n": 4, "kind": "other", "keep": False, "name": "Award badge"},
            {"n": 9, "kind": "product", "keep": True, "name": "out of range"},
            {"n": 5, "kind": "made-up", "keep": True, "name": ""}]}
    out, notes = brand_import.sort_pictures("Acme", PICS, account_id=1, model=model)
    assert [p["role"] for p in out] == ["product", "product", "reference", "drop", "reference"]
    assert out[0]["name"] == "Orange rocket on a stand"
    assert out[1]["name"] == "Booking screen"                    # no address survives
    assert out[2]["kind"] == "person"                            # a person is look, never cast
    assert notes == []


def test_a_model_that_fails_leaves_every_picture_as_look():
    def broken(*a, **k):
        raise RuntimeError("no Gemini key")
    out, notes = brand_import.sort_pictures("Acme", PICS, account_id=1, model=broken)
    assert {p["role"] for p in out} == {"reference"}
    assert notes and "not sorted" in notes[0]


def test_a_picture_the_model_skipped_is_kept_as_look():
    out, notes = brand_import.sort_pictures(
        "Acme", PICS[:2], account_id=1,
        model=lambda *a, **k: {"pictures": [{"n": 1, "kind": "product", "keep": True,
                                             "name": "Box"}]})
    assert [p["role"] for p in out] == ["product", "reference"]
    assert "did not answer" in notes[0]


# --- filing onto the kit ---------------------------------------------------

@pytest.fixture
def kitdb(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    brand_kits.init(pg)
    entities.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("bip-mine", "Mine", "#fff", dsn=pg)
    return pg, mine


def _pics(n):
    return [{"url": f"https://a.example/{i}.jpg", "page": "https://a.example/",
             "data": brand_import.keep_pictures([{"data": _png(800, 600, (i * 20, 90, 90))}])[0][0]["data"]}
            for i in range(n)]


def test_products_are_made_as_elements_and_linked_and_the_rest_are_references(kitdb, monkeypatch):
    pg, mine = kitdb
    monkeypatch.setattr("src.charge.create_refusal_code", lambda account_id: None)
    kit = brand_kits.create("Acme", {}, pg, account_id=mine)
    made = []

    def create(kind, name, *, account_id, field, notes, uploads, strict):
        assert kind == "prop" and field == "product" and strict and account_id == mine
        assert notes.startswith("From the website: https://a.example/")
        made.append(name)
        entities.add_prop(name=name, category="product", account_id=account_id)
        return {"ok": True}

    def sort(brand, pictures, *, account_id):
        roles = ["product", "product", "reference", "drop"]
        return [dict(p, role=r, name="Rocket") for p, r in zip(pictures, roles)], []

    counts, notes = brand_routes.file_pictures(kit, _pics(4), account_id=mine,
                                               sort=sort, create=create)
    assert counts == {"products": 2, "references": 1, "dropped": 1}
    assert made == ["Rocket", "Rocket 2"]                        # never a second photo on one
    kit = brand_kits.get(kit["id"], pg, account_id=mine)
    assert [p["name"] for p in kit["spec"]["products"]] == ["Rocket", "Rocket 2"]
    assert [a["role"] for a in kit["assets"]] == ["reference"]
    assert any("left out" in n for n in notes)


def test_an_account_that_may_not_spend_text_gets_references_only(kitdb, monkeypatch):
    pg, mine = kitdb
    monkeypatch.setattr("src.charge.create_refusal_code",
                        lambda account_id: ("subscribe_or_top_up", "choose a plan to continue"))
    kit = brand_kits.create("Acme", {}, pg, account_id=mine)

    def never(*a, **k):
        raise AssertionError("no model, no element, when the gate says no")

    counts, notes = brand_routes.file_pictures(kit, _pics(10), account_id=mine,
                                               sort=never, create=never)
    assert counts == {"products": 0, "references": 8, "dropped": 0}  # a kit keeps eight
    assert "without sorting: choose a plan" in notes[0]
    assert any("2 more pictures not kept" in n for n in notes)


# --- a real visit to a two-page local site -----------------------------------

class _Site(http.server.BaseHTTPRequestHandler):
    seen: list = []
    base = ""

    def do_GET(self):
        _Site.seen.append(self.path)
        b = _Site.base
        pages = {
            "/": (f'<html><head><meta property="og:image" content="{b}/og.png"></head><body>'
                  f'<header><img src="{b}/logo.png" class="logo" width="160" height="48">'
                  f'<nav><a href="{b}/about">About</a><a href="{b}/private">Private</a></nav></header>'
                  f'<main><img src="{b}/hero.png" width="900" height="600">'
                  f'<img src="{b}/tiny.png" width="400" height="300"></main>'
                  f'<footer><img src="{b}/badge.png" width="80" height="80"></footer></body></html>'),
            "/about": f'<html><head><meta property="og:image" content="{b}/about.png"></head></html>',
            "/private": f'<html><head><meta property="og:image" content="{b}/secret.png"></head></html>',
            "/robots.txt": "User-agent: *\nDisallow: /private\n",
        }
        pictures = {"/og.png": (1200, 630), "/logo.png": (160, 48), "/hero.png": (900, 600),
                    "/tiny.png": (200, 150), "/badge.png": (80, 80), "/about.png": (1000, 800),
                    "/secret.png": (1000, 800)}
        if self.path in pages:
            body, kind = pages[self.path].encode(), (
                "text/plain" if self.path.endswith(".txt") else "text/html")
        elif self.path in pictures:
            body, kind = _png(*pictures[self.path], (len(self.path) * 7 % 255, 80, 120)), "image/png"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def site():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Site)
    _Site.seen = []
    _Site.base = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield _Site.base
    server.shutdown()


@needs_chromium
def test_a_visit_brings_back_the_sites_pictures_and_honours_robots(site):
    seen = brand_import._visit(url=site + "/", public=lambda host: host == "127.0.0.1")
    urls = [p["url"] for p in seen["pictures"]]
    assert urls[0] == site + "/og.png"                           # the page's own preview first
    assert site + "/hero.png" in urls and site + "/about.png" in urls
    assert site + "/logo.png" not in urls and site + "/badge.png" not in urls
    assert site + "/secret.png" not in urls and "/private" not in _Site.seen
    assert any("robots.txt" in n for n in seen["picture_notes"])
    kept, _ = brand_import.keep_pictures(seen["pictures"])
    assert site + "/tiny.png" not in [k["url"] for k in kept]   # drawn big, too small a file
    assert {k["url"] for k in kept} >= {site + "/og.png", site + "/hero.png", site + "/about.png"}
