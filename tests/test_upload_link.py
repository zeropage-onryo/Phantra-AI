"""
A file comes into the connector through a one-time page, and a product
page gives up its picture (2026-10-11, docs/tasks/task-connector-overnight.md
PR 1).

What these tests guard, in the order a mistake would cost:

- the token: signed under its own salt, bound to ONE account and person,
  expired after thirty minutes, and spent by ONE saved file -- a tampered
  or foreign token is refused before anything is read;
- the page: the file is typed by its first bytes and never its name, capped
  at the editor's sizes before and while the body is read, normalised to a
  JPEG, filed as an `asset:<id>` in the token's account and -- when the
  link was minted for an element -- added to that element through the
  Elements page's own create body; a refused file gives the link back;
- `add_element` from a product page: the page's main picture, never its
  logo, and what the page states kept as quoted data in the notes.
"""
import asyncio
import hashlib
import io
import shutil
import subprocess

import pytest

from app import api, mcp_mount, upload_page
from src import (
    accounts,
    asset_shelf,
    entities,
    generative,
    ledger,
    mcp_server,
    outcomes,
    preprod,
    projects,
    quote_redemptions,
    refbin,
    render_assets,
    scout,
    upload_links,
)
from src.cut import store as cut_store

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg is not installed")


def _png(colour=(200, 30, 30), size=(8, 8)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    return buf.getvalue()


def _jpeg(size=(8, 8)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, (20, 120, 200)).save(buf, "JPEG")
    return buf.getvalue()


# --------------------------------------------------------------------------
# the token
# --------------------------------------------------------------------------

@pytest.fixture
def signed(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("PHANTRA_MCP_RESOURCE", "https://api.example.test/mcp")
    monkeypatch.delenv(upload_links.ORIGIN_ENV, raising=False)
    return monkeypatch


def test_a_minted_token_verifies_to_its_account_person_and_purpose(signed):
    link = upload_links.mint(7, "user-7", "reference", element_kind="prop", element_name="Can")
    assert link["url"] == f"https://api.example.test/u/{link['token']}"
    assert link["expires_in_s"] == upload_links.MAX_AGE_S
    claims = upload_links.verify(link["token"])
    assert claims == {"token_id": link["token_id"], "account_id": 7, "user_id": "user-7",
                      "purpose": "reference", "element_kind": "prop", "element_name": "Can"}
    plain = upload_links.verify(upload_links.mint(7, "", "footage")["token"])
    assert plain["purpose"] == "footage" and plain["element_kind"] is None
    assert plain["user_id"] == ""


def test_a_token_expires_after_thirty_minutes(signed, monkeypatch):
    now = [1_800_000_000.0]
    monkeypatch.setattr(upload_links, "clock", lambda: now[0])
    token = upload_links.mint(7, "user-7", "reference")["token"]
    now[0] += upload_links.MAX_AGE_S - 5
    assert upload_links.verify(token)["account_id"] == 7
    now[0] += 10
    with pytest.raises(upload_links.LinkRefused, match="expired") as got:
        upload_links.verify(token)
    assert got.value.code == "expired"


def test_a_tampered_foreign_or_session_token_is_refused(signed, monkeypatch):
    token = upload_links.mint(7, "user-7", "reference")["token"]
    for bad in (token[:-2] + ("aa" if not token.endswith("aa") else "bb"), "", "not-a-token",
                token.replace(".", "x", 1)):
        with pytest.raises(upload_links.LinkRefused) as got:
            upload_links.verify(bad)
        assert got.value.code == "bad_signature"
    # minted by another server (another secret)
    monkeypatch.setenv("SESSION_SECRET", "somebody-elses-secret")
    foreign = upload_links.mint(7, "user-7", "reference")["token"]
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    with pytest.raises(upload_links.LinkRefused):
        upload_links.verify(foreign)
    # a session cookie's token, signed with the same secret under its salt
    from itsdangerous import URLSafeTimedSerializer
    session = URLSafeTimedSerializer("test-session-secret", salt="zp-session").dumps(
        {"t": "x", "a": 7, "u": "user-7", "p": "reference"})
    with pytest.raises(upload_links.LinkRefused):
        upload_links.verify(session)


def test_the_page_origin_is_the_resource_then_site_url_then_the_dev_server(monkeypatch):
    for var in (upload_links.ORIGIN_ENV, "PHANTRA_MCP_RESOURCE", "SITE_URL"):
        monkeypatch.delenv(var, raising=False)
    assert upload_links.page_origin() == "http://127.0.0.1:8000"
    monkeypatch.setenv("SITE_URL", "https://zeropage-studio.fly.dev/")
    assert upload_links.page_origin() == "https://zeropage-studio.fly.dev"
    monkeypatch.setenv("PHANTRA_MCP_RESOURCE", "https://api.phantra.ai/mcp")
    assert upload_links.page_origin() == "https://api.phantra.ai"
    monkeypatch.setenv(upload_links.ORIGIN_ENV, "https://uploads.example.test")
    assert upload_links.page_origin() == "https://uploads.example.test"


def test_a_missing_session_secret_is_generated_once_and_shared(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    first = upload_links.secret()
    assert first and upload_links.secret() == first
    from app import auth
    assert auth._session_secret() == first         # the app reads the same value


# --------------------------------------------------------------------------
# the world: two people, the create body's model calls stood in for
# --------------------------------------------------------------------------

@pytest.fixture
def world(pg, tmp_path, monkeypatch, signed):
    for init in (preprod.init, scout.init, entities.init, generative.init, render_assets.init,
                 projects.init, cut_store.init, ledger.init, outcomes.init,
                 quote_redemptions.init, upload_links.init):
        init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)        # app/api.py reads the process's own
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    for acct in (a, b):
        ledger.grant(acct, 500, "promo", dsn=pg)

    dirs = {kind: tmp_path / f"{kind}s" for kind in ("character", "prop", "location")}
    monkeypatch.setattr(asset_shelf, "PHOTO_DIRS", dirs)
    monkeypatch.setattr(api, "CHARACTERS_DIR", dirs["character"])
    monkeypatch.setattr(api, "PROPS_DIR", dirs["prop"])
    monkeypatch.setattr(api, "LOCATIONS_DIR", dirs["location"])
    from app import cut_routes
    media_dir = tmp_path / "cutmedia"
    monkeypatch.setattr(cut_routes, "MEDIA_DIR", media_dir)
    monkeypatch.setattr(cut_routes, "_start_preview", lambda *a, **k: False)

    calls = {"described": [], "sheets": [], "drawn": []}
    monkeypatch.setattr(api, "describe_entity_photos",
                        lambda kind, name, photos, account_id=None:
                        calls["described"].append((kind, name, len(photos))) or
                        {"ok": True, "description": {"look": f"{name} as photographed"},
                         "error": None})
    monkeypatch.setattr(api, "ingest_asset_chunk",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    monkeypatch.setattr(api, "_start_sheet_job",
                        lambda *args, **kw: calls["sheets"].append(args) or {"id": 1})
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *args, **kw: {"ok": True, "chunks": 1, "error": None})
    from src import element_sheet, fal, nano_banana

    def drew(name):
        return lambda *args, **kw: calls["drawn"].append(name) or {"ok": False, "error": "no"}
    monkeypatch.setattr(nano_banana, "generate_from_prompt", drew("nano"))
    monkeypatch.setattr(element_sheet, "draw", drew("sheet"))
    monkeypatch.setattr(fal, "generate_image_from_prompt", drew("fal"))
    return {"dsn": pg, "a": a, "b": b, "dirs": dirs, "calls": calls, "media_dir": media_dir,
            "create": mcp_mount.connector_element(api.create_element)}


def _mint(world, who="a", **kw):
    return mcp_server.upload_link(dsn=world["dsn"], account_id=world[who], **kw)


# --------------------------------------------------------------------------
# the tool
# --------------------------------------------------------------------------

def test_the_tool_mints_a_link_bound_to_the_account_and_the_person(world):
    token = mcp_server.CALLER_USER.set("user-alice")
    try:
        out = _mint(world, "a", element_kind="prop", element_name="Can")
    finally:
        mcp_server.CALLER_USER.reset(token)
    assert out["url"].startswith("https://api.example.test/u/")
    assert out["credits"] == 0 and out["element"] == {"kind": "prop", "name": "Can"}
    assert "elements" in out["next"]
    claims = upload_links.verify(out["url"].rsplit("/", 1)[1])
    assert claims["account_id"] == world["a"] and claims["user_id"] == "user-alice"
    assert claims["element_kind"] == "prop" and claims["element_name"] == "Can"
    plain = _mint(world, "b", purpose="footage")
    assert upload_links.verify(plain["url"].rsplit("/", 1)[1])["user_id"] == ""
    assert plain["element"] is None and "asset:<id>" in plain["next"]


@pytest.mark.parametrize("kwargs, match", [
    ({"purpose": "video"}, "purpose must be one of"),
    ({"element_kind": "prop"}, "together, or neither"),
    ({"element_name": "Can"}, "together, or neither"),
    ({"element_kind": "vehicle", "element_name": "Bike"}, "element_kind must be one of"),
    ({"element_kind": "prop", "element_name": "!!!"}, "needs letters or numbers"),
    ({"element_kind": "prop", "element_name": "x" * 81}, "too long"),
    ({"purpose": "footage", "element_kind": "prop", "element_name": "Can"},
     "an element is a picture"),
])
def test_every_bad_ask_is_refused_before_a_token_exists(world, kwargs, match):
    with pytest.raises(ValueError, match=match):
        _mint(world, "a", **kwargs)
    from src import db
    with db.connect(world["dsn"]) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM upload_claims").fetchone()["n"] == 0


def test_an_account_with_nothing_to_create_with_is_refused_only_for_an_element(world, monkeypatch):
    from src import charge
    monkeypatch.setattr(charge, "create_refusal", lambda account_id, dsn=None: charge.CREATE_REFUSAL)
    with pytest.raises(mcp_server.Refused):
        _mint(world, "a", element_kind="prop", element_name="Can")
    assert _mint(world, "a")["purpose"] == "reference"     # a plain upload asks no gate


def test_no_workspace_is_refused(pg, signed):
    upload_links.init(pg)
    with pytest.raises(mcp_server.Refused, match="no workspace"):
        mcp_server.upload_link(dsn=pg, account_id=None)


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------

@pytest.fixture
def client(world):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import auth
    auth._hits.clear()
    app = FastAPI()
    app.include_router(upload_page.router)
    return TestClient(app)


def _path(out: dict) -> str:
    return "/u/" + out["url"].rsplit("/", 1)[1]


def _post(client, path, data: bytes, name="photo.jpg", kind="image/jpeg"):
    return client.post(path, files={"file": (name, data, kind)})


def test_the_form_says_what_the_link_will_do(client, world):
    page = client.get(_path(_mint(world, "a", element_kind="prop", element_name="Can")))
    assert page.status_code == 200
    assert "Add a photo to the prop “Can”" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert "Upload a clip" in client.get(_path(_mint(world, "a", purpose="footage"))).text


def test_an_expired_or_foreign_link_shows_a_plain_page(client, world, monkeypatch):
    now = [1_800_000_000.0]
    monkeypatch.setattr(upload_links, "clock", lambda: now[0])
    path = _path(_mint(world, "a"))
    now[0] += upload_links.MAX_AGE_S + 1
    expired = client.get(path)
    assert expired.status_code == 410 and "expired" in expired.text
    assert _post(client, path, _png()).status_code == 410
    foreign = client.get("/u/not-a-token")
    assert foreign.status_code == 404 and "not an upload link" in foreign.text
    assert "<form" not in foreign.text


@needs_ffmpeg
def test_a_picture_is_filed_as_an_asset_in_the_tokens_account_and_the_link_is_spent(client, world):
    path = _path(_mint(world, "a", purpose="footage"))
    page = _post(client, path, _png(size=(16, 24)), name="anything.bin",
                 kind="application/octet-stream")
    assert page.status_code == 200 and "Saved" in page.text
    # a picture has a size and no length (the still's placeholder seconds are
    # the editor's, not the picture's -- the live page printed "600.0s")
    assert "16 × 24" in page.text and "Length" not in page.text
    rows = cut_store.media_bin(account_id=world["a"], dsn=world["dsn"])
    assert len(rows) == 1 and rows[0]["kind"] == "image"
    assert rows[0]["filename"].endswith(".jpg")                # normalised to a JPEG
    assert f"asset:{rows[0]['id']}" in page.text
    assert cut_store.media_bin(account_id=world["b"], dsn=world["dsn"]) == []
    # the claim carries what it made; the link is spent, for GET and POST alike
    token_id = upload_links.verify(path.rsplit("/", 1)[1])["token_id"]
    spent = upload_links.used(token_id, world["dsn"])
    assert spent["result"]["asset"] == f"asset:{rows[0]['id']}"
    again = client.get(path)
    assert again.status_code == 410 and "already used" in again.text
    assert f"asset:{rows[0]['id']}" in again.text
    assert _post(client, path, _png()).status_code == 410
    assert len(cut_store.media_bin(account_id=world["a"], dsn=world["dsn"])) == 1


@needs_ffmpeg
def test_a_picture_becomes_the_elements_photo_through_the_create_body(client, world):
    path = _path(_mint(world, "a", element_kind="prop", element_name="Can"))
    page = _post(client, path, _jpeg(size=(32, 32)))
    assert page.status_code == 200 and "Added to" in page.text and "Can" in page.text
    folder = world["dirs"]["prop"] / "can"
    saved = [p.name for p in folder.iterdir()]
    assert len(saved) == 1 and saved[0].startswith("up-") and saved[0].endswith(".jpg")
    listed = mcp_server.list_elements(dsn=world["dsn"], account_id=world["a"])
    assert [e["name"] for e in listed["elements"]] == ["Can"]
    assert listed["elements"][0]["photos"][0]["label"] == saved[0]
    assert world["calls"]["described"] == [("prop", "Can", 1)]
    assert world["calls"]["sheets"] == [] and world["calls"]["drawn"] == []
    # and it is an asset in the library too
    assert len(cut_store.media_bin(account_id=world["a"], dsn=world["dsn"])) == 1


def test_a_clip_cannot_be_an_elements_picture_and_the_link_stays_good(client, world):
    path = _path(_mint(world, "a", element_kind="prop", element_name="Can"))
    mp4_head = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64
    page = _post(client, path, mp4_head, name="clip.mp4", kind="video/mp4")
    assert page.status_code == 400 and "must be a picture" in page.text
    assert client.get(path).status_code == 200            # nothing was claimed


def test_what_is_not_a_picture_or_a_clip_is_refused_by_its_bytes_and_the_link_stays_good(client, world):
    path = _path(_mint(world, "a"))
    page = _post(client, path, b"hello, this is text pretending", name="photo.jpg")
    assert page.status_code == 400 and "judged by its contents" in page.text
    assert client.get(path).status_code == 200
    assert _post(client, path, b"", name="empty.png").status_code == 400
    assert cut_store.media_bin(account_id=world["a"], dsn=world["dsn"]) == []


def test_bytes_that_only_claim_to_be_a_picture_give_the_claim_back(client, world):
    path = _path(_mint(world, "a"))
    fake = b"\x89PNG\r\n\x1a\n" + b"garbage" * 20            # a PNG header, nothing behind it
    page = _post(client, path, fake)
    assert page.status_code == 400 and "could not be read" in page.text
    token_id = upload_links.verify(path.rsplit("/", 1)[1])["token_id"]
    assert upload_links.used(token_id, world["dsn"]) is None
    assert client.get(path).status_code == 200


def test_oversize_is_refused_before_anything_is_saved(client, world, monkeypatch):
    monkeypatch.setattr(upload_page, "IMAGE_CAP", 64)
    path = _path(_mint(world, "a"))
    page = _post(client, path, _png(size=(64, 64)))           # a real PNG over 64 bytes
    assert page.status_code == 413 and "over 0 MB" in page.text
    monkeypatch.setattr(upload_page, "VIDEO_CAP", 32)
    assert _post(client, path, _png(size=(64, 64))).status_code == 413
    assert cut_store.media_bin(account_id=world["a"], dsn=world["dsn"]) == []
    assert client.get(path).status_code == 200


def test_a_declared_length_over_the_cap_is_refused_before_the_body_is_parsed(client, world, monkeypatch):
    monkeypatch.setattr(upload_page, "VIDEO_CAP", 0)
    path = _path(_mint(world, "a"))
    big = b"x" * (upload_page.MB + 10)
    page = client.post(path, files={"file": ("big.bin", big, "application/octet-stream")})
    assert page.status_code == 413


def test_the_post_is_rate_limited_by_address(client, world, monkeypatch):
    from app import auth
    monkeypatch.setitem(auth.RATE_LIMITS, "upload", (1, 60.0))
    auth._hits.clear()
    path = _path(_mint(world, "a"))
    assert _post(client, path, b"nope").status_code == 400
    assert _post(client, path, b"nope").status_code == 429


def test_a_token_minted_for_one_account_cannot_be_turned_into_anothers(client, world):
    from itsdangerous import URLSafeTimedSerializer
    good = _mint(world, "a")["url"].rsplit("/", 1)[1]
    claims = upload_links.verify(good)
    assert claims["account_id"] == world["a"]
    # re-signed for Bob under a secret the server does not hold
    forged = URLSafeTimedSerializer("guess", salt=upload_links.SALT).dumps(
        {"t": claims["token_id"], "a": world["b"], "u": "", "p": "reference"})
    assert client.get(f"/u/{forged}").status_code == 404
    assert _post(client, f"/u/{forged}", _png()).status_code == 404


@needs_ffmpeg
def test_a_save_that_fails_gives_the_claim_back(client, world, monkeypatch):
    from src.cut import uploads as cut_uploads

    def boom(*a, **k):
        raise RuntimeError("disk on fire")
    monkeypatch.setattr(cut_uploads, "save", boom)
    path = _path(_mint(world, "a"))
    page = _post(client, path, _png())
    assert page.status_code == 500 and "could not be saved" in page.text
    assert "disk on fire" not in page.text
    assert client.get(path).status_code == 200


@needs_ffmpeg
def test_a_clip_is_filed_as_footage(client, world, tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "1",
                    "-i", "testsrc=size=160x284:rate=30", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(clip)], check=True, capture_output=True)
    path = _path(_mint(world, "a", purpose="footage"))
    page = _post(client, path, clip.read_bytes(), name="renamed.jpg", kind="image/jpeg")
    assert page.status_code == 200
    rows = cut_store.media_bin(account_id=world["a"], dsn=world["dsn"])
    assert len(rows) == 1 and rows[0]["kind"] == "video"
    assert rows[0]["filename"].endswith(".mp4") and rows[0]["seconds"] == pytest.approx(1.0, abs=0.1)
    assert "Length" in page.text and "160 × 284" in page.text


def test_sniff_reads_types_off_the_first_bytes_only():
    assert upload_page.sniff(_png()) == ("image", ".png")
    assert upload_page.sniff(_jpeg()) == ("image", ".jpg")
    assert upload_page.sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ("image", ".webp")
    assert upload_page.sniff(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8) == ("image", ".heic")
    assert upload_page.sniff(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 8) == ("video", ".mov")
    assert upload_page.sniff(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8) == ("video", ".mp4")
    assert upload_page.sniff(b"GIF89a" + b"\x00" * 20) is None
    assert upload_page.sniff(b"%PDF-1.4" + b"\x00" * 20) is None
    assert upload_page.sniff(b"") is None


def test_the_app_serves_the_page(signed):
    """Through the real app, not the router alone: a bad token gets OUR
    page (a 404 that says so), not FastAPI's JSON not-found."""
    from fastapi.testclient import TestClient

    from app import main
    reply = TestClient(main.app).get("/u/not-a-token")
    assert reply.status_code == 404 and "not an upload link" in reply.text


# --------------------------------------------------------------------------
# add_element from a product page
# --------------------------------------------------------------------------

class _Response:
    def __init__(self, status=200, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {}
        self.is_redirect = status in (301, 302, 303, 307, 308)
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, size):
        for i in range(0, len(self._body), size):
            yield self._body[i:i + size]


@pytest.fixture
def web(monkeypatch):
    import requests
    pages, seen = {}, []

    def get(url, **kw):
        seen.append(url)
        if url not in pages:
            raise ConnectionError("no route")
        return pages[url]

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(refbin, "public_host", lambda host: True)
    return {"pages": pages, "seen": seen}


PAGE = "https://shop.example.com/products/ghost-can"
PHOTO = "https://cdn.example.com/products/ghost-can-front.png"
LOGO = "https://cdn.example.com/site/logo.png"


def _html(images, product=True):
    tags = "".join(f'<meta property="og:image" content="{u}">' for u in images)
    ld = ('<script type="application/ld+json">{"@type": "Product", "name": "Ghost Energy", '
          '"brand": {"name": "Ghost"}, "color": "Sour Patch Blue", "offers": {"price": "2.99", '
          '"priceCurrency": "USD"}, "description": "A 16 oz can of <b>energy</b> -- see '
          'https://ghost.example for more"}</script>') if product else ""
    return (f'<html><head><title>Ghost Energy</title>{tags}{ld}</head>'
            '<body><h1>Buy now</h1></body></html>').encode()


def _add(world, kind, name, source, **kw):
    return mcp_server.add_element(kind, name, source, create_element=world["create"],
                                  dsn=world["dsn"], account_id=world["a"], **kw)


def test_a_product_page_gives_its_picture_and_its_facts_as_quoted_data(world, web):
    web["pages"][PAGE] = _Response(headers={"content-type": "text/html; charset=utf-8"},
                                   body=_html([LOGO, PHOTO]))
    web["pages"][PHOTO] = _Response(headers={"content-type": "image/png"}, body=_png((9, 9, 9)))
    out = _add(world, "prop", "Can", PAGE, notes="hero product")
    assert out["added"] and out["credits"] == 0
    assert out["page"]["url"] == PAGE and out["page"]["picture"] == PHOTO
    assert out["page"]["facts"]["name"] == "Ghost Energy"
    assert out["page"]["facts"]["brand"] == "Ghost" and out["page"]["facts"]["price"] == "2.99 USD"
    assert "https://" not in out["page"]["facts"]["description"]     # addresses stripped
    # the notes the create body was handed: the person's words, then the page's, quoted
    kind, name, n = world["calls"]["described"][0]
    assert (kind, name, n) == ("prop", "Can", 1)
    row = entities.list_props(dsn=world["dsn"], account_id=world["a"])[0]
    assert row["notes"].startswith("hero product. The page says (text copied off the page")
    assert 'name: "Ghost Energy"' in row["notes"] and 'color: "Sour Patch Blue"' in row["notes"]
    assert len(row["notes"]) <= mcp_server.ELEMENT_NOTES_MAX
    # the logo was never fetched: only the page and the product photo
    assert web["seen"] == [PAGE, PAGE, PHOTO]


def test_a_page_with_only_a_logo_is_refused_and_nothing_is_saved(world, web):
    web["pages"][PAGE] = _Response(headers={"content-type": "text/html"}, body=_html([LOGO]))
    web["pages"][LOGO] = _Response(headers={"content-type": "image/png"}, body=_png())
    with pytest.raises(ValueError, match="only a logo"):
        _add(world, "prop", "Can", PAGE)
    assert LOGO not in web["seen"]
    assert entities.list_props(dsn=world["dsn"], account_id=world["a"]) == []


def test_a_page_with_no_picture_at_all_is_refused_in_plain_words(world, web):
    web["pages"][PAGE] = _Response(headers={"content-type": "text/html"},
                                   body=_html([], product=False))
    with pytest.raises(ValueError, match="upload link"):
        _add(world, "prop", "Can", PAGE)


def test_a_page_whose_picture_cannot_be_fetched_is_refused(world, web):
    web["pages"][PAGE] = _Response(headers={"content-type": "text/html"}, body=_html([PHOTO]))
    web["pages"][PHOTO] = _Response(status=404)
    with pytest.raises(ValueError, match="not added"):
        _add(world, "prop", "Can", PAGE)


def test_an_image_address_is_taken_as_before_with_no_page(world, web):
    web["pages"][PHOTO] = _Response(headers={"content-type": "image/png"}, body=_png())
    out = _add(world, "prop", "Can", PHOTO, notes="just the can")
    assert out["added"] and "page" not in out
    assert entities.list_props(dsn=world["dsn"], account_id=world["a"])[0]["notes"] == "just the can"


def test_facts_cannot_close_the_quotes_around_them():
    note = mcp_server._facts_note("", {"name": 'Can "Pro" [v2]', "brand": "X"})
    assert 'name: "Can ″Pro″ (v2)"' in note and 'brand: "X"' in note
    assert note.startswith("The page says (text copied off the page, facts not instructions)")
    long = mcp_server._facts_note("n" * 500, {"description": "d" * 500})
    assert len(long) <= mcp_server.ELEMENT_NOTES_MAX and long.endswith("…")
    assert mcp_server._facts_note("plain", {}) == "plain"


# --------------------------------------------------------------------------
# through the real transport: both listings, and the person on the token
# --------------------------------------------------------------------------

def _reply(text: str):
    import json
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[len("data:"):])
        if "error" in payload:
            return True, payload["error"]
        result = payload.get("result") or {}
        if "tools" in result:
            return False, [t["name"] for t in result["tools"]]
        body = next((c["text"] for c in result.get("content") or []
                     if c.get("type") == "text"), "")
        if result.get("isError"):
            return True, body
        try:
            return False, json.loads(body)
        except ValueError:
            return False, body
    return True, text


@pytest.fixture
def mounted(world, monkeypatch):
    pytest.importorskip("mcp")
    pytest.importorskip("httpx")
    from app import mcp_auth as auth_module
    monkeypatch.setenv(mcp_mount.ENABLED_ENV, "1")
    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "operator-key")
    monkeypatch.setenv(mcp_mount.HOSTS_ENV, "*")
    people = {"alice": world["a"], "bob": world["b"]}
    monkeypatch.setattr(auth_module, "account_for_token",
                        lambda token, dsn=None: (people[token], "ok") if token in people
                        else (None, "invalid_token"))
    # the bearer tokens here are not JWTs; the subject a real token carries
    monkeypatch.setattr(mcp_mount, "_token_subject",
                        lambda token: {"alice": "user-alice", "bob": "user-bob"}.get(token, ""))
    app, sessions = mcp_mount.build(dsn=world["dsn"], job_status=lambda i, account_id=None: None,
                                    approve_render=lambda *a: {"job_id": 1},
                                    approve_keyframes=lambda *a: {"job_id": 2},
                                    create_element=api.create_element)
    assert app is not None
    return {**world, "app": app, "sessions": sessions}


def _talk(world, steps):
    import httpx

    async def go():
        out = []
        async with world["sessions"].run():
            transport = httpx.ASGITransport(app=world["app"])
            async with httpx.AsyncClient(transport=transport,
                                         base_url="https://api.example.test") as client:
                for n, (token, name, args, path) in enumerate(steps, 1):
                    body = ({"method": "tools/list"} if name == "tools/list" else
                            {"method": "tools/call", "params": {"name": name,
                                                                "arguments": args or {}}})
                    reply = await client.post(path, headers={
                        "authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": n, **body})
                    out.append(_reply(reply.text))
        return out

    return asyncio.run(go())


def test_both_listings_offer_the_link_and_it_binds_the_signed_in_person(mounted):
    (e1, render), (e2, claude), (e3, link), (e4, bob), (e5, op) = _talk(mounted, [
        ("alice", "tools/list", None, "/"),
        ("alice", "tools/list", None, "/claude/"),
        ("alice", "upload_link", {"element_kind": "character", "element_name": "Me"}, "/claude/"),
        ("bob", "upload_link", {"purpose": "footage"}, "/"),
        # the operator's key reaches the studio surface at /mcp, which has no
        # upload_link (it has import_file); on the Claude path it sees the listing
        ("operator-key", "upload_link", {}, "/claude/"),
    ])
    assert not (e1 or e2 or e3 or e4 or e5)
    assert "upload_link" in render and "upload_link" in claude
    assert render == list(mcp_server.LISTED_TOOLS) and claude == list(mcp_server.CLAUDE_LISTED_TOOLS)
    alice = upload_links.verify(link["url"].rsplit("/", 1)[1])
    assert (alice["account_id"], alice["user_id"]) == (mounted["a"], "user-alice")
    assert alice["element_kind"] == "character" and alice["element_name"] == "Me"
    bobs = upload_links.verify(bob["url"].rsplit("/", 1)[1])
    assert (bobs["account_id"], bobs["user_id"], bobs["purpose"]) == (mounted["b"], "user-bob", "footage")
    # the operator's key is nobody in particular, acting as the bootstrap account
    ops = upload_links.verify(op["url"].rsplit("/", 1)[1])
    assert ops["user_id"] == "" and ops["account_id"] == mounted["a"]
    assert mcp_server.CALLER_USER.get() is None          # reset after the request


def test_the_studio_surface_has_no_upload_link(world):
    server = mcp_server.build_server(dsn=world["dsn"], surface="studio")
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert "upload_link" not in names and "import_file" in names


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
