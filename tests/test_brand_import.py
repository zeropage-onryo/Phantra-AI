"""A brand kit from a website (src/brand_import.py, step 3 of
docs/tasks/task-brand-kit-import-and-chat.md).

The browser tests render local fixtures with `page.set_content` (and one
local redirect server) and never reach the web: every request the page makes
goes through the import's own guard, and the tests hand it the only host
allowed. The route test patches `brand_import.extract`.
"""
import http.server
import os
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import auth, brand_routes
from app.main import app
from src import accounts, brand_import, brand_kits

client = TestClient(app)


def _chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


HAS_CHROMIUM = _chromium()
# skipped on a machine without the browser, never in CI (which installs it)
needs_chromium = pytest.mark.skipif(not HAS_CHROMIUM and not os.environ.get("CI"),
                                    reason="Playwright's Chromium is not installed")

PAGE = """<!doctype html><html><head><title>Acme Rockets | Fly further</title>
<meta name="description" content="Rockets for small businesses,
  built in Ohio.">
<meta name="theme-color" content="#E4572E">
<style>:root{--brand:#E4572E;--ink:#1B1B1E;--unused:#00FF00}
body{margin:0;background:#FFF8F0;color:var(--ink);font-family:"Poppins",sans-serif}
header{padding:16px 32px}
.logo svg{width:160px;height:48px}
h1{font-family:"Playfair Display",serif;font-size:56px;margin:80px 32px 16px}
p{font-size:18px;margin:0 32px;max-width:640px}
.btn{display:inline-block;margin:32px;padding:18px 40px;background:var(--brand);color:#fff;
  border-radius:999px;font-weight:700}
.band{background:#2E86AB;color:#fff;padding:40px 32px}
</style>%(extra_head)s</head><body>
<header><a href="/" class="logo"><svg viewBox="0 0 160 48"><rect width="48" height="48" rx="12"
  fill="#E4572E"/><text x="58" y="34" font-size="28" fill="#1B1B1E">Acme</text></svg></a></header>
<h1>Fly further for less</h1><p>Rockets for small businesses, built in Ohio, with a real person
on the line for every launch and a refund if the weather says no.</p>
<a class="btn" href="#">Book a launch</a><a class="btn" href="#">See prices</a>
<div class="band">Trusted by 400 launch sites.</div>%(extra_body)s
</body></html>"""


def page(extra_head="", extra_body=""):
    return PAGE % {"extra_head": extra_head, "extra_body": extra_body}


@needs_chromium
def test_a_fixture_page_becomes_a_spec_the_kit_takes():
    kit = brand_import.extract(page(), public=lambda host: False)
    spec = kit["spec"]
    assert brand_kits.clean_spec(spec) == spec                  # valid as stored
    roles = {s["role"]: s["hex"] for s in spec["palette"]}
    assert roles["primary"] == "#E4572E" and roles["accent"] == "#2E86AB"
    assert roles["background"] == "#FFF8F0" and roles["text"] == "#1B1B1E"
    # white type reads 3.5:1 on that red, black 5.7:1: the WCAG rule picks black
    assert roles["extra"] == "#000000"
    ev = spec["import"]["roles"]
    assert ev["primary"]["confidence"] == "high"
    assert "--brand" in ev["primary"]["why"] and "logo" in ev["primary"]["why"]
    assert "--unused" not in str(ev)                            # the visibility gate
    assert kit["name"] == "Acme Rockets"
    assert spec["identity"]["positioning"] == "Rockets for small businesses, built in Ohio."
    assert spec["identity"]["tagline"] == "Fly further for less"
    assert kit["fonts"] == {"heading": "Playfair Display", "body": "Poppins"}
    (logo,) = kit["files"]
    assert logo["role"] == "logo_light" and logo["data"][:4] == b"\x89PNG"


@needs_chromium
def test_private_and_metadata_addresses_are_aborted():
    kit = brand_import.extract(page(extra_body=(
        '<img src="http://169.254.169.254/latest/meta-data/">'
        '<img src="http://127.0.0.1/admin.png">'
        '<link rel="stylesheet" href="http://10.0.0.5/x.css">')))
    blocked = {url: why for url, why in kit["blocked"]}
    assert blocked["http://169.254.169.254/latest/meta-data/"] == "not a public address"
    assert blocked["http://127.0.0.1/admin.png"] == "not a public address"
    assert blocked["http://10.0.0.5/x.css"] == "not a public address"


class _Server(http.server.BaseHTTPRequestHandler):
    seen: list = []

    def do_GET(self):
        _Server.seen.append(self.path)
        if self.path.startswith("/hop"):
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/iam")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "font/woff2")
            self.end_headers()
            self.wfile.write(b"wOF2")

    def log_message(self, *a):
        pass


@pytest.fixture
def local_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Server)
    _Server.seen = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@needs_chromium
def test_a_redirect_to_a_private_address_is_refused_at_the_hop(local_server):
    """The page's first host may pass the check and redirect inside the
    network; every hop comes back through the guard."""
    kit = brand_import.extract(page(extra_body=f'<img src="{local_server}/hop.png">'),
                               public=lambda host: host == "127.0.0.1")
    assert "/hop.png" in _Server.seen                            # the allowed hop was asked
    assert ("http://169.254.169.254/latest/meta-data/iam", "not a public address") in kit["blocked"]


@needs_chromium
def test_the_sites_font_files_are_never_downloaded(local_server):
    head = ("<style>@font-face{font-family:Brand;src:url(%s/brand.woff2) format('woff2')}"
            "h1{font-family:Brand}</style>" % local_server)
    kit = brand_import.extract(page(extra_head=head), public=lambda host: host == "127.0.0.1")
    assert (f"{local_server}/brand.woff2", "font files are never downloaded") in kit["blocked"]
    assert "/brand.woff2" not in _Server.seen
    assert kit["fonts"]["heading"] == "Brand"                    # named, not fetched


def test_a_page_with_no_strong_colour_says_so():
    probe = {"colours": [{"rgb": [255, 255, 255], "area": 1e6, "kind": "bg", "where": "body"},
                         {"rgb": [30, 30, 30], "area": 4e4, "kind": "text", "where": "body"}],
             "meta": {}}
    roles = brand_import.pick_roles(probe, [], [])
    assert roles["primary"]["confidence"] == "low" and "no strong colour" in roles["primary"]["why"]
    assert brand_import.hexof(roles["background"]["rgb"]) == "#FFFFFF"


def test_two_close_reds_are_one_and_the_runner_up_is_offered():
    probe = {"colours": [
        {"rgb": [255, 255, 255], "area": 1e6, "kind": "bg", "where": "body"},
        {"rgb": [20, 20, 20], "area": 5e4, "kind": "text", "where": "body"},
        {"rgb": [228, 87, 46], "area": 2e4, "kind": "bg", "where": "button"},
        {"rgb": [230, 89, 47], "area": 1e4, "kind": "bg", "where": "button"},
        {"rgb": [46, 134, 171], "area": 3e4, "kind": "bg", "where": "body"},
        {"rgb": [120, 60, 200], "area": 2e3, "kind": "text", "where": "link"}], "meta": {}}
    roles = brand_import.pick_roles(probe, [], [])
    assert brand_import.hexof(roles["primary"]["rgb"]) in ("#E4572E", "#E6592F")
    assert brand_import.hexof(roles["accent"]["rgb"]) == "#2E86AB"
    assert {c["hex"] for c in roles["candidates"]} >= {"#2E86AB", "#783CC8"}


class _Resp:
    def __init__(self, status=200, text="", content=b""):
        self.status_code, self.text, self.content = status, text, content


def test_a_google_font_comes_from_google_and_any_other_is_only_named():
    asked = []

    def get(url, **kw):
        asked.append(url)
        if "family=Urbanist" in url:
            return _Resp(text="src: url(https://fonts.gstatic.com/s/urbanist/v1/u.ttf) "
                              "format('truetype');")
        if url.startswith("https://fonts.gstatic.com/"):
            return _Resp(content=b"\x00\x01\x00\x00font")
        return _Resp(status=400)

    files, notes = brand_import.fetch_fonts({"heading": "Urbanist", "body": "Brand Sans"}, get=get)
    assert [f["role"] for f in files] == ["font_heading"]
    assert "Brand Sans: not on Google Fonts" in notes[0]
    assert all(u.startswith(("https://fonts.googleapis.com/", "https://fonts.gstatic.com/"))
               for u in asked)
    assert brand_import.google_font("system-ui", 400, get=get) is None


def test_an_import_starts_only_from_a_public_web_address():
    for bad in ("", "ftp://example.com", "http://user:pw@example.com", "http://127.0.0.1",
                "http://169.254.169.254/latest", "https://10.1.2.3"):
        with pytest.raises(brand_import.ImportRefused):
            brand_import.check_address(bad)


# ---------- the route ----------

@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    brand_kits.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "t@example.com"})
    monkeypatch.setattr(brand_import, "check_address", lambda url: "https://acme.example")
    monkeypatch.setattr(brand_routes, "_imports", {})
    mine = accounts.upsert_account("bi-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("bi-theirs", "Theirs", "#fff", dsn=pg)
    app.dependency_overrides[auth.current_account_id] = lambda: mine
    yield pg, mine, theirs
    app.dependency_overrides[auth.current_account_id] = lambda: None


def _wait(job_id):
    deadline = time.time() + 10
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError("job never finished")


def _found(**over):
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (120, 40), (228, 87, 46, 255)).save(buf, "PNG")
    return {"name": "Acme Rockets", "files": [{"role": "logo_light", "data": buf.getvalue(),
                                               "filename": "acme.png"}],
            "spec": brand_kits.clean_spec({
                "palette": [{"hex": "#E4572E", "role": "primary"}],
                "import": {"source": "https://acme.example", "at": "2026-10-21T00:00:00Z",
                           "roles": {"primary": {"why": "the buttons", "confidence": "high"}}}}),
            "notes": ["heading font Brand: not on Google Fonts"], "blocked": [], **over}


def test_the_route_makes_a_new_kit_for_the_caller_only(dbx, monkeypatch):
    pg, mine, theirs = dbx
    existing = brand_kits.create("Acme Rockets", {}, pg, account_id=mine)
    monkeypatch.setattr(brand_import, "extract", lambda **kw: _found())
    r = client.post("/api/brand-kits/import", json={"url": "acme.example"})
    assert r.status_code == 200, r.text
    job = _wait(r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["kit_id"] != existing["id"]                       # new, never an overwrite
    kit = brand_kits.get(job["kit_id"], pg, account_id=mine)
    assert kit["spec"]["import"]["roles"]["primary"]["confidence"] == "high"
    assert [a["role"] for a in kit["assets"]] == ["logo_light"]
    assert brand_kits.get(existing["id"], pg, account_id=mine)["spec"]["palette"] == []
    assert brand_kits.list_kits(pg, account_id=theirs) == []
    assert job["notes"] == ["heading font Brand: not on Google Fonts"]


def test_the_route_refuses_a_bad_address_and_the_eleventh_import(dbx, monkeypatch):
    def refuse(url):
        raise brand_import.ImportRefused("that address is not on the public internet")

    monkeypatch.setattr(brand_import, "check_address", refuse)
    r = client.post("/api/brand-kits/import", json={"url": "http://127.0.0.1"})
    assert r.status_code == 400 and r.json()["error"]["field"] == "url"

    monkeypatch.setattr(brand_import, "check_address", lambda url: "https://acme.example")
    monkeypatch.setattr(brand_import, "extract", lambda **kw: _found())
    for _ in range(brand_routes.IMPORTS_PER_HOUR):
        assert client.post("/api/brand-kits/import", json={"url": "acme.example"}).status_code == 200
    r = client.post("/api/brand-kits/import", json={"url": "acme.example"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"


def test_a_white_mark_is_the_dark_logo_and_gets_a_light_one_in_the_primary():
    import io

    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((10, 10, 110, 30), fill=(255, 255, 255, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    files = brand_import.logo_files(buf.getvalue(), {"primary": {"rgb": (255, 136, 11)}}, "gygler.com")
    assert [f["role"] for f in files] == ["logo_dark", "logo_light"]
    light = Image.open(io.BytesIO(files[1]["data"])).convert("RGBA")
    assert light.getpixel((50, 20)) == (255, 136, 11, 255) and light.getpixel((2, 2))[3] == 0
    # a mark in two colours is filed once, by how light it reads
    ImageDraw.Draw(im).rectangle((10, 10, 40, 30), fill=(228, 87, 46, 255))
    ImageDraw.Draw(im).rectangle((41, 10, 110, 30), fill=(20, 20, 20, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    assert [f["role"] for f in brand_import.logo_files(buf.getvalue(), {}, "x")] == ["logo_light"]
