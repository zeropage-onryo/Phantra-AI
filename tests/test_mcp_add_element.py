"""
A picture becomes an element from a chat (2026-10-11,
docs/tasks/task-connector-elements.md).

The connector could make nothing for a new person: `write_scene` takes
refs only from `elements`, a new account has none, and no tool added one.
`add_element` is that tool, on all three servers. What these tests guard,
in the order a mistake would cost:

- the picture's address is a stranger's choice fetched from the server:
  https at every hop, public hosts only, a size cap, and bytes that really
  are a picture (`refbin.fetch_public_image`);
- someone else's `gen:` / `asset:` is exactly as missing as one that never
  existed, and the ref it would have made cannot be used by anybody else;
- it goes through the Elements page's own create body, draws no sheet and
  holds no credits;
- and, since the same day, the render listing can draw a still behind the
  studio surface's signed single-use quote, in credits only.
"""
import asyncio
import hashlib
import io

import pytest

from app import api, mcp_mount
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
)
from src.approvals import ElementRefused
from src.cut import store as cut_store

URL = "https://cdn.example.com/can.png"


def _png(colour=(200, 30, 30), size=(8, 8)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------
# the fetch: a stranger's address, read from the server
# --------------------------------------------------------------------------

class _Response:
    def __init__(self, status=200, headers=None, body=b"", chunk=64 * 1024):
        self.status_code = status
        self.headers = headers or {}
        self._body, self._chunk = body, chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, size):
        for i in range(0, len(self._body), self._chunk):
            yield self._body[i:i + self._chunk]


@pytest.fixture
def web(monkeypatch):
    """The internet, as a table of address -> response. Every host is
    public unless the test says otherwise; every request is recorded with
    whether it was allowed to follow a redirect by itself."""
    import requests

    pages, seen, private = {}, [], set()

    def get(url, **kw):
        seen.append((url, kw.get("allow_redirects")))
        if url not in pages:
            raise ConnectionError("no route")
        return pages[url]

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(refbin, "public_host", lambda host: host not in private)
    return {"pages": pages, "seen": seen, "private": private}


def test_a_public_https_picture_is_fetched_without_following_redirects_itself(web):
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert refbin.fetch_public_image(URL, max_bytes=1024 * 1024) == _png()
    assert web["seen"] == [(URL, False)]          # every hop is ours to check


@pytest.mark.parametrize("address, why", [
    ("http://cdn.example.com/can.png", "must start with https://"),
    ("https://", "must start with https://"),
    ("ftp://cdn.example.com/can.png", "must start with https://"),
    ("https://user:pw@cdn.example.com/can.png", "username or password"),
    ("https://10.0.0.5/can.png", "not on the public internet"),
])
def test_an_address_that_is_not_public_https_is_refused_before_any_request(web, address, why):
    web["private"].add("10.0.0.5")
    with pytest.raises(refbin.ImageRefused, match=why):
        refbin.fetch_public_image(address, max_bytes=1024)
    assert web["seen"] == []


def test_a_redirect_is_followed_by_hand_and_only_to_public_https(web):
    """`requests` would follow these on its own -- to the metadata address,
    to a private host, to plain http. Each hop is checked instead."""
    hop = "https://img.example.com/real.png"
    web["pages"][URL] = _Response(302, {"location": hop})
    web["pages"][hop] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert refbin.fetch_public_image(URL, max_bytes=1024 * 1024) == _png()
    assert [u for u, _ in web["seen"]] == [URL, hop]

    for target, why in (("http://169.254.169.254/latest/meta-data/", "must start with https://"),
                        ("https://internal.example/secret.png", "not on the public internet"),
                        ("", "redirects nowhere")):
        web["seen"].clear()
        web["private"].add("internal.example")
        web["pages"][URL] = _Response(302, {"location": target})
        with pytest.raises(refbin.ImageRefused, match=why):
            refbin.fetch_public_image(URL, max_bytes=1024)
        assert [u for u, _ in web["seen"]] == [URL]      # the second hop was never asked

    web["pages"][URL] = _Response(302, {"location": URL})   # a loop
    with pytest.raises(refbin.ImageRefused, match="too many times"):
        refbin.fetch_public_image(URL, max_bytes=1024)


@pytest.mark.parametrize("response, why", [
    (_Response(headers={"content-type": "text/html; charset=utf-8"}, body=b"<html>"),
     "a web page, not a picture"),
    (_Response(headers={"content-type": "application/json"}, body=b"{}"),
     "answered with application/json"),
    (_Response(404, {"content-type": "image/png"}, b"x"), "answered 404"),
    (_Response(headers={"content-type": "image/png"}, body=b""), "answered with nothing"),
    (_Response(headers={"content-type": "image/png", "content-length": "99999999"}, body=b"x"),
     "over 1 MB"),
    (_Response(headers={"content-type": "image/png"}, body=b"x" * (1024 * 1024 + 1)),
     "over 1 MB"),
])
def test_what_is_not_a_picture_or_is_too_big_says_so(web, response, why):
    web["pages"][URL] = response
    with pytest.raises(refbin.ImageRefused, match=why):
        refbin.fetch_public_image(URL, max_bytes=1024 * 1024)


def test_an_unreachable_address_is_a_refusal_not_a_crash(web):
    with pytest.raises(refbin.ImageRefused, match="could not be reached"):
        refbin.fetch_public_image(URL, max_bytes=1024)


# --------------------------------------------------------------------------
# two people, a real database, the Elements page's own create body
# --------------------------------------------------------------------------

@pytest.fixture
def world(pg, tmp_path, monkeypatch):
    """Alice and Bob, each with their own workspace and credits to create
    with; the element folders in tmp; the model calls the create body
    makes (a description, a shelf chunk) stood in for and counted."""
    for init in (preprod.init, scout.init, entities.init, generative.init, render_assets.init,
                 projects.init, cut_store.init, ledger.init, outcomes.init,
                 quote_redemptions.init):
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

    calls = {"described": [], "shelved": [], "chunks": [], "sheets": [], "drawn": []}
    monkeypatch.setattr(api, "describe_entity_photos",
                        lambda kind, name, photos, account_id=None:
                        calls["described"].append((kind, name, len(photos))) or
                        {"ok": True, "description": {"look": f"{name} as photographed"},
                         "error": None})
    monkeypatch.setattr(api, "ingest_asset_chunk",
                        lambda kind, slug, name, fields, project=None:
                        calls["shelved"].append((kind, slug, project)) or
                        calls["chunks"].append(fields) or
                        {"ok": True, "chunks": 1, "error": None})
    monkeypatch.setattr(api, "_start_sheet_job",
                        lambda *args, **kw: calls["sheets"].append(args) or {"id": 1})
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *args, **kw: {"ok": True, "chunks": 1, "error": None})
    # anything that would DRAW: none of it may run
    from src import element_sheet, fal, nano_banana

    def drew(name):
        return lambda *args, **kw: calls["drawn"].append(name) or {"ok": False, "error": "no"}
    monkeypatch.setattr(nano_banana, "generate_from_prompt", drew("nano"))
    monkeypatch.setattr(element_sheet, "draw", drew("sheet"))
    monkeypatch.setattr(fal, "generate_image_from_prompt", drew("fal"))

    def render(account_id, n, kind="image", name=None):
        path = tmp_path / (name or f"render-{account_id}-{n}.png")
        path.write_bytes(_png((n * 40 % 255, 20, 20)) if kind == "image" else b"\x00" * 64)
        row = render_assets.record(generation_id=7000 + account_id * 100 + n, tool="fal",
                                   model="seedream4.5", media_kind=kind, prompt=f"render {n}",
                                   media_url=f"/renders/fal/{path.name}",
                                   output_path=str(path), account_id=account_id, dsn=pg)
        return f"gen:{row['id']}"

    return {"dsn": pg, "a": a, "b": b, "dirs": dirs, "calls": calls, "render": render,
            "create": mcp_mount.connector_element(api.create_element)}


def _add(world, who, kind, name, source, **kw):
    return mcp_server.add_element(kind, name, source, create_element=world["create"],
                                  dsn=world["dsn"], account_id=world[who], **kw)


def test_a_render_becomes_an_element_with_a_ref_a_scene_can_take(world):
    gen = world["render"](world["a"], 1)
    out = _add(world, "a", "prop", "Ghost Can", gen, notes="  the matte   black can ")
    assert out["added"] is True and out["kind"] == "prop" and out["name"] == "Ghost Can"
    assert out["credits"] == 0 and "no credits" in out["note"]
    photo = out["photo"]
    assert photo["label"].startswith("add-") and photo["label"].endswith(".jpg")
    assert photo["ref"] == f"/props/ghost-can/photo/{photo['label']}"
    assert out["element"]["photos"] == [photo]
    # it is the Elements page's row, with the page's description and shelf chunk
    [row] = entities.list_props(dsn=world["dsn"], account_id=world["a"])
    assert row["name"] == "Ghost Can" and row["notes"] == "the matte black can"
    assert row["description"]["look"] == "Ghost Can as photographed"
    assert world["calls"]["shelved"] == [("prop", "ghost-can", accounts.slug_of(
        world["a"], dsn=world["dsn"]))]
    # what was saved is an upright JPEG under the name of its own bytes
    saved = (world["dirs"]["prop"] / "ghost-can" / photo["label"]).read_bytes()
    assert saved[:3] == b"\xff\xd8\xff"
    assert photo["label"] == f"add-{hashlib.sha1(saved).hexdigest()[:16]}.jpg"
    # `elements` lists exactly it, and the render was "kept" (it became a reference)
    listed = mcp_server.list_elements(dsn=world["dsn"], account_id=world["a"])
    assert listed["count"] == 1 and listed["elements"][0]["photos"] == [photo]
    asset = int(gen.split(":")[1])
    kept = outcomes.events_for([asset], account_id=world["a"], dsn=world["dsn"])[asset]
    assert [(e["event"], e["source"]) for e in kept] == [("element_from", "mcp")]


def test_add_element_draws_nothing_and_holds_no_credits(world, monkeypatch):
    """The sheet is a still that costs credits and has its own quoted
    tool. Here: no sheet job, no image model, no hold -- with an image key
    present, which is when the Elements page WOULD have drawn one. The one
    model call is the page's own description of the photo, which is free."""
    monkeypatch.setenv("GEMINI_API_KEY", "a-key-that-would-draw")
    before = ledger.available(world["a"], dsn=world["dsn"])
    for kind, name in (("character", "Sam"), ("prop", "Tin"), ("location", "Hallway")):
        _add(world, "a", kind, name, world["render"](world["a"], len(name)))
    assert world["calls"]["sheets"] == [] and world["calls"]["drawn"] == []
    assert ledger.available(world["a"], dsn=world["dsn"]) == before
    assert ledger.outstanding(world["a"], dsn=world["dsn"]) == 0
    assert [c[:2] for c in world["calls"]["described"]] == [("character", "Sam"),
                                                            ("prop", "Tin")]


def test_the_function_itself_calls_no_model_and_the_adapter_never_asks_for_a_sheet(world):
    """With the create body stood in for, `add_element` reads one file and
    calls nothing else -- the network guard is on -- and what it hands the
    body says: one photo, no sheet, an element or a refusal."""
    seen = {}

    def create(kind, name, **kw):
        seen.update(kind=kind, name=name, **kw)
        return {"ok": True, "slug": "sam"}

    out = mcp_server.add_element("character", "Sam", world["render"](world["a"], 2),
                                 create_element=mcp_mount.connector_element(create),
                                 dsn=world["dsn"], account_id=world["a"])
    assert seen["sheet"] is False and seen["strict"] is True
    assert seen["account_id"] == world["a"] and len(seen["uploads"]) == 1
    name, data = seen["uploads"][0]
    assert name.startswith("add-") and data[:3] == b"\xff\xd8\xff"
    assert "photo_urls" not in seen               # never a URL for the server to fetch again
    assert out["photo"] is None and "not listed yet" in out["note"]   # the stub saved nothing
    assert world["calls"]["drawn"] == [] and world["calls"]["described"] == []


def test_the_same_name_again_adds_the_photo_and_never_a_second_element(world):
    first = _add(world, "a", "character", "Sam", world["render"](world["a"], 1),
                 notes="a tired courier")
    second = _add(world, "a", "character", "  sam ", world["render"](world["a"], 2),
                  notes="in the rain")
    assert second["name"] == "Sam"                      # the element keeps its name
    assert len(second["element"]["photos"]) == 2
    assert first["photo"] in second["element"]["photos"]
    assert second["photo"] != first["photo"]
    [row] = entities.list_characters(dsn=world["dsn"], account_id=world["a"])
    assert row["name"] == "Sam" and row["notes"] == "a tired courier"
    # described once, from the first photo; the second add keeps that
    # description and the element's own notes, on the row AND on the shelf
    # (a later photo's note is not the element's)
    assert world["calls"]["described"] == [("character", "Sam", 1)]
    assert row["description"] == {"look": "Sam as photographed", "notes": "a tired courier"}
    assert world["calls"]["chunks"][-1] == {
        "role": "", "notes": "a tired courier",
        "description": {"look": "Sam as photographed", "notes": "a tired courier"}}
    # the very same picture again is the same file: nothing grows
    again = _add(world, "a", "character", "Sam", world["render"](world["a"], 1, name="copy.png"))
    assert again["photo"] == first["photo"] and len(again["element"]["photos"]) == 2


def test_a_place_is_listed_even_when_it_could_not_be_described(world, monkeypatch):
    """The page leaves an undescribed place's photos for a later describe
    and records no row. A connector's caller needs the ref now."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    out = _add(world, "a", "location", "The Hallway", world["render"](world["a"], 3))
    assert out["name"] == "the-hallway" and out["described"] is False
    assert out["photo"]["ref"].startswith("/locations/the-hallway/photo/add-")
    assert preprod.get_location_by_name("the-hallway", dsn=world["dsn"],
                                        account_id=world["a"]) is not None
    # and the page's own behaviour is untouched: saved, no row
    api.create_element("location", "Garage", account_id=world["a"],
                       uploads=[("a.png", _png())])
    assert preprod.get_location_by_name("garage", dsn=world["dsn"],
                                        account_id=world["a"]) is None


@pytest.mark.parametrize("kind, name, source, why", [
    ("vehicle", "Bike", "gen:1", "kind must be one of"),
    ("prop", "   ", "gen:1", "a name is required"),
    ("prop", "!!!", "gen:1", "a name is required"),
    ("prop", "x" * 81, "gen:1", "too long"),
    ("prop", "Can", "", "`source` is required"),
    ("prop", "Can", "http://cdn.example.com/can.png", "must start with https://"),
    ("prop", "Can", "https://10.0.0.5/can.png", "not on the public internet"),
    ("prop", "Can", "ftp://cdn.example.com/can.png", "is not a picture this takes"),
    ("prop", "Can", "data:image/png;base64,AAAA", "is not a picture this takes"),
    ("prop", "Can", "/characters/sam/photo/face.jpg", "is not a picture this takes"),
    ("prop", "Can", "candidate:abc", "is not a picture this takes"),
    ("prop", "Can", "gen:424242", "no render 424242 on this account"),
    ("prop", "Can", "asset:424242", "no import 424242 on this account"),
])
def test_every_bad_input_is_refused_before_anything_is_saved(world, web, kind, name,
                                                             source, why):
    web["private"].add("10.0.0.5")
    with pytest.raises(ValueError, match=why):
        _add(world, "a", kind, name, source)
    assert mcp_server.list_elements(dsn=world["dsn"], account_id=world["a"])["count"] == 0
    assert not any(d.exists() for d in world["dirs"].values())
    assert world["calls"]["described"] == [] and world["calls"]["shelved"] == []


def test_another_accounts_render_or_upload_is_exactly_as_missing(world):
    gen = world["render"](world["a"], 1)
    upload = cut_store.add_media(account_id=world["a"], kind="image", filename="can.png",
                                 media_url="/renders/cut/media/can.png",
                                 output_path=str(world["dirs"]["prop"].parent / "render-x.png"),
                                 seconds=None, sha256=None, dsn=world["dsn"])
    for source, why in ((gen, "no render"), (f"asset:{upload['id']}", "no import")):
        with pytest.raises(ValueError, match=why):
            _add(world, "b", "prop", "Can", source)
    assert mcp_server.list_elements(dsn=world["dsn"], account_id=world["b"])["count"] == 0


def test_only_an_image_can_be_an_elements_picture(world):
    clip = world["render"](world["a"], 4, kind="video", name="clip.mp4")
    with pytest.raises(ValueError, match="is video; an element's picture must be an image"):
        _add(world, "a", "prop", "Can", clip)
    sound = cut_store.add_media(account_id=world["a"], kind="audio", filename="bed.m4a",
                                media_url="/renders/cut/media/bed.m4a", output_path=None,
                                seconds=3.0, sha256=None, dsn=world["dsn"])
    with pytest.raises(ValueError, match="is audio"):
        _add(world, "a", "prop", "Can", f"asset:{sound['id']}")


def test_an_upload_from_the_editor_can_be_the_picture(world, tmp_path):
    path = tmp_path / "upload.png"
    path.write_bytes(_png((10, 200, 10)))
    upload = cut_store.add_media(account_id=world["a"], kind="image", filename="upload.png",
                                 media_url="/renders/cut/media/upload.png",
                                 output_path=str(path), seconds=None, sha256=None,
                                 dsn=world["dsn"])
    out = _add(world, "a", "character", "Mara", f"asset:{upload['id']}")
    assert out["photo"]["ref"].startswith("/characters/mara/photo/add-")


def test_an_oversize_picture_is_a_plain_refusal_never_a_crash(world, web, monkeypatch):
    """By address and by id, through the tool the model actually calls:
    a sentence it can relay, and nothing saved."""
    from mcp.server.mcpserver.exceptions import ToolError

    monkeypatch.setattr(mcp_server, "ELEMENT_PHOTO_BYTES", 1024 * 1024)
    web["pages"][URL] = _Response(headers={"content-type": "image/png"},
                                  body=b"\x89PNG" + b"0" * (1024 * 1024))
    server = mcp_server.build_server(dsn=world["dsn"], listed=True, account_id=world["a"],
                                     create_element=world["create"])
    with pytest.raises(ToolError, match="that picture was not added: the picture is over 1 MB"):
        asyncio.run(server.call_tool("add_element",
                                     {"kind": "prop", "name": "Can", "source": URL}))
    big = world["render"](world["a"], 5)
    monkeypatch.setattr(mcp_server, "ELEMENT_PHOTO_BYTES", 16)
    with pytest.raises(ToolError, match="is over 0 MB"):
        asyncio.run(server.call_tool("add_element",
                                     {"kind": "prop", "name": "Can", "source": big}))
    assert mcp_server.list_elements(dsn=world["dsn"], account_id=world["a"])["count"] == 0


def test_bytes_that_only_claim_to_be_a_picture_are_refused(world, web):
    web["pages"][URL] = _Response(headers={"content-type": "image/png"},
                                  body=b"<html>not a png at all</html>")
    with pytest.raises(ValueError, match="not an image this can read"):
        _add(world, "a", "prop", "Can", URL)
    assert not world["dirs"]["prop"].exists()


def test_a_picture_by_address_is_saved_as_the_persons_element(world, web):
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    out = _add(world, "a", "prop", "Can", URL)
    assert out["photo"]["ref"].startswith("/props/can/photo/add-")
    assert [u for u, _ in web["seen"]] == [URL]          # fetched once, by the guard


def test_an_account_with_nothing_to_create_with_is_told_so_and_nothing_is_fetched(
        world, web, monkeypatch):
    """The Elements page's own gate, asked before the picture is fetched:
    saving an element describes it, which is included in a plan."""
    from src import charge
    monkeypatch.setattr(charge, "create_refusal", lambda account_id, dsn=None: charge.CREATE_REFUSAL)
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    with pytest.raises(mcp_server.Refused, match="subscribe or top up"):
        _add(world, "a", "prop", "Can", URL)
    assert web["seen"] == [] and not world["dirs"]["prop"].exists()


def test_a_server_built_without_the_create_body_says_so(world):
    with pytest.raises(mcp_server.Refused, match="cannot be added through this server"):
        mcp_server.add_element("prop", "Can", "gen:1", dsn=world["dsn"], account_id=world["a"])


def test_the_desktop_server_reaches_the_same_create_body(world, pg_factory, monkeypatch):
    """`python -m src.mcp_server` hands `build_server` a creator that
    reaches app/api.py on its first call -- and refuses when the server
    was started on a database that body would not write to."""
    captured = {}

    class FakeServer:
        def run(self, transport):
            pass

    monkeypatch.setattr(mcp_server, "build_server",
                        lambda **kw: captured.update(kw) or FakeServer())
    assert mcp_server.main(["--db", world["dsn"]]) == 0
    out = mcp_server.add_element("prop", "Tin", world["render"](world["a"], 1),
                                 create_element=captured["create_element"],
                                 dsn=world["dsn"], account_id=world["a"])
    assert out["photo"]["ref"].startswith("/props/tin/photo/add-")
    assert [r["name"] for r in entities.list_props(dsn=world["dsn"],
                                                   account_id=world["a"])] == ["Tin"]

    elsewhere = pg_factory()
    assert mcp_server.main(["--db", elsewhere]) == 0
    with pytest.raises(mcp_server.Refused, match="started on another one"):
        captured["create_element"]("prop", "Can", photo=("a.jpg", b"x"), account_id=None)


# --------------------------------------------------------------------------
# the element folders are shared by NAME; the bucket is not
# --------------------------------------------------------------------------
# `characters/me/` is one folder for every account on a machine. Found
# while building this: two people who each call a character "Me" were
# each listed the other's photo. Where the bucket is the per-account
# store (the deployed studio), the connector keeps nothing in that folder
# and lists only the caller's own keys.

@pytest.fixture
def bucket(monkeypatch):
    """R2 configured on the `tenant` rung, as a dict: what was uploaded,
    under which key. No boto3 call is made."""
    from src import storage

    for name, value in (("R2_ACCOUNT_ID", "acct"), ("R2_ACCESS_KEY_ID", "key"),
                        ("R2_SECRET_ACCESS_KEY", "secret"), ("R2_BUCKET", "zpf"),
                        ("R2_PUBLIC_BASE_URL", "https://pub.example/")):
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ZEROPAGE_MEDIA", "tenant")
    held: dict = {}

    def upload_file(path, key=None, content_type=None):
        from pathlib import Path
        held[key] = Path(path).read_bytes()
        storage._note_uploaded(key)
        return f"https://pub.example/{key}"

    def upload_bytes(data, key, content_type=None):
        held[key] = bytes(data)
        storage._note_uploaded(key)
        return f"https://pub.example/{key}"

    monkeypatch.setattr(storage, "upload_file", upload_file)
    monkeypatch.setattr(storage, "upload_bytes", upload_bytes)
    monkeypatch.setattr(storage, "list_keys",
                        lambda prefix="": [k for k in held if k.startswith(prefix)])
    storage.forget_listings()
    yield held
    storage.forget_listings()


def test_two_people_with_the_same_element_name_never_see_each_others_photo(world, bucket):
    """THE LEAK, closed for this door. Same machine, same name, the
    deployed posture: each is listed their own photo and nothing else,
    each photo sits under its own account's keys, and neither is left in
    the folder the two would share."""
    alice = _add(world, "a", "character", "Me", world["render"](world["a"], 1))
    bob = _add(world, "b", "character", "Me", world["render"](world["b"], 2))
    assert alice["photo"]["ref"] != bob["photo"]["ref"]
    for who, mine, theirs in (("a", alice, bob), ("b", bob, alice)):
        listed = mcp_server.list_elements(dsn=world["dsn"], account_id=world[who])
        assert listed["elements"][0]["photos"] == [mine["photo"]]
        allowed = mcp_server._allowed_refs(world["dsn"], world[who])
        assert mine["photo"]["ref"] in allowed and theirs["photo"]["ref"] not in allowed
        key = f"m/{world[who]}/characters/me/{mine['photo']['label']}"
        assert bucket[key][:3] == b"\xff\xd8\xff"
    assert not (world["dirs"]["character"] / "me").exists()     # nothing in the shared folder
    # each description was drawn from that person's one photo, never the folder's two
    assert world["calls"]["described"] == [("character", "Me", 1), ("character", "Me", 1)]


def test_a_photo_somebody_else_left_in_the_shared_folder_is_not_listed(world, bucket):
    """The Elements page still writes that folder. A file another account
    put there under the same name is not this caller's, and the connector
    neither lists it nor takes its ref."""
    shared = world["dirs"]["character"] / "me"
    shared.mkdir(parents=True)
    (shared / "someone-elses-face.jpg").write_bytes(_png())
    mine = _add(world, "b", "character", "Me", world["render"](world["b"], 2))
    assert mine["element"]["photos"] == [mine["photo"]]
    listed = mcp_server.list_elements(dsn=world["dsn"], account_id=world["b"])
    assert [p["label"] for p in listed["elements"][0]["photos"]] == [mine["photo"]["label"]]
    with pytest.raises(ValueError, match="not one of your elements"):
        mcp_server.write_scene(SCENE, refs=["/characters/me/photo/someone-elses-face.jpg"],
                               dsn=world["dsn"], account_id=world["b"])
    assert sorted(f.name for f in shared.iterdir()) == ["someone-elses-face.jpg"]


def test_a_picture_the_bucket_did_not_take_is_refused_and_leaves_nothing(world, bucket,
                                                                        monkeypatch):
    """The bucket was to be the only copy. If it is not there, nothing
    was saved -- no row, no file -- and the person is told to try again."""
    from src import storage

    def down(*args, **kw):
        raise RuntimeError("bucket unreachable")

    monkeypatch.setattr(storage, "upload_file", down)
    for kind in ("prop", "location"):
        with pytest.raises(ValueError, match="could not be saved just now"):
            _add(world, "a", kind, "Can", world["render"](world["a"], 3))
    assert entities.list_props(dsn=world["dsn"], account_id=world["a"]) == []
    assert preprod.list_locations(dsn=world["dsn"], account_id=world["a"]) == []
    assert not any(d.exists() for d in world["dirs"].values()) and bucket == {}


def test_the_elements_page_still_writes_its_folder_where_the_bucket_is_the_store(world, bucket):
    """Only the connector's create is private. The page's own create is
    byte for byte what it was: the folder, and the mirror beside it."""
    made = api.create_element("prop", "Tin", account_id=world["a"],
                              uploads=[("lid.png", _png())])
    assert made["ok"] and (world["dirs"]["prop"] / "tin" / "lid.png").exists()
    assert f"m/{world['a']}/props/tin/lid.png" in bucket


def test_one_studio_on_one_machine_still_keeps_its_photos_in_the_folder(world):
    """No bucket: the folder IS the store, and the connector writes it."""
    out = _add(world, "a", "prop", "Tin", world["render"](world["a"], 1))
    assert (world["dirs"]["prop"] / "tin" / out["photo"]["label"]).exists()
    assert not asset_shelf.bucket_is_store(world["a"])


# --------------------------------------------------------------------------
# the create body's own contract, strict and not
# --------------------------------------------------------------------------

def test_strict_refuses_a_picture_that_could_not_be_saved_before_any_row(world, monkeypatch):
    """The page keeps a character with no photo (a name and notes are a
    thing a person can mean); the connector's caller asked for a photo."""
    monkeypatch.setattr(api, "_photo_bytes", lambda url: None)
    with pytest.raises(ElementRefused) as refused:
        api.create_element("character", "Sam", account_id=world["a"],
                           photo_urls=["/renders/nano/missing.png"], strict=True)
    assert refused.value.code == "no_photos" and refused.value.status == 400
    assert entities.list_characters(dsn=world["dsn"], account_id=world["a"]) == []
    # the page's behaviour, unchanged: the element saves without one
    made = api.create_element("character", "Sam", account_id=world["a"],
                              photo_urls=["/renders/nano/missing.png"])
    assert made["ok"] and made["photos"] == 0


def test_the_adapter_says_a_refusal_in_the_pages_words(world):
    def refuse(status, code, message):
        def create(kind, name, **kw):
            raise ElementRefused(status, code, message)
        return mcp_mount.connector_element(create)

    with pytest.raises(ValueError, match="the picture could not be read"):
        refuse(400, "no_photos", "the picture could not be read")(
            "prop", "Can", photo=("a.jpg", b"x"), account_id=1)
    with pytest.raises(mcp_server.Refused, match="subscribe or top up"):
        refuse(402, "subscribe_or_top_up", "subscribe or top up credits")(
            "prop", "Can", photo=("a.jpg", b"x"), account_id=1)
    assert mcp_mount.connector_element(None) is None


def test_an_unknown_kind_never_reaches_a_folder(world):
    with pytest.raises(ElementRefused) as refused:
        api.create_element("vehicle", "Bike", account_id=world["a"], uploads=[("a.png", _png())])
    assert refused.value.status == 404


# --------------------------------------------------------------------------
# through the real transport: empty studio -> a picture -> a scene -> a price
# --------------------------------------------------------------------------

SCENE = ("Ultra-realistic grounded video in 9:16; the attached photo is the exact can. "
         "Style: cold window light, true colour, a 35mm frame at table height. "
         "(0-4s) A hand sets the matte black can down on wet steel and lets go. "
         "(4-10s) Hard cut to the doorway: condensation runs down the can as the light "
         "shifts. No background music. Avoid: plastic sheen, floating labels.")


@pytest.fixture
def mounted(world, monkeypatch):
    """The mount as the app builds it -- the real create body injected,
    the real job registry -- with Alice and Bob behind the OAuth door."""
    pytest.importorskip("mcp")
    pytest.importorskip("httpx")
    from app import jobs
    from app import mcp_auth as auth_module

    monkeypatch.setenv(mcp_mount.ENABLED_ENV, "1")
    monkeypatch.setenv(mcp_mount.TOKEN_ENV, "operator-key")
    monkeypatch.setenv(mcp_mount.HOSTS_ENV, "*")
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    people = {"alice": world["a"], "bob": world["b"]}
    monkeypatch.setattr(auth_module, "account_for_token",
                        lambda token, dsn=None: (people[token], "ok") if token in people
                        else (None, "invalid_token"))
    approved: list = []
    app, sessions = mcp_mount.build(
        dsn=world["dsn"], start_job=jobs.start, job_status=jobs.get,
        approve_render=lambda *args: approved.append(args) or {"job_id": 1},
        approve_keyframes=lambda *args: approved.append(args) or {"job_id": 2},
        create_element=api.create_element)
    assert app is not None
    return {**world, "app": app, "sessions": sessions, "approved": approved}


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
        if isinstance(result.get("structuredContent"), dict):
            return False, result["structuredContent"]
        try:
            return False, json.loads(body)
        except ValueError:
            return False, body
    return True, text


def _session(world, script):
    """Run `script(call)` inside ONE session-manager run -- a manager can
    be entered once per instance, so a test is one conversation. `call`
    is `await call(token, tool, arguments, path="/")` -> (is_error,
    payload); `tools/list` as the tool name lists the tools."""
    import httpx

    async def go():
        async with world["sessions"].run():
            transport = httpx.ASGITransport(app=world["app"])
            async with httpx.AsyncClient(transport=transport,
                                         base_url="https://api.zeropage.studio") as client:
                count = 0

                async def call(token, name, args=None, path="/"):
                    nonlocal count
                    count += 1
                    body = ({"method": "tools/list"} if name == "tools/list" else
                            {"method": "tools/call",
                             "params": {"name": name, "arguments": args or {}}})
                    reply = await client.post(path, headers={
                        "authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": count, **body})
                    return _reply(reply.text)

                return await script(call)

    return asyncio.run(go())


def _talk(world, steps):
    """`_session` for a fixed list of (token, tool, arguments) steps; a
    step may be a function of the answers so far that returns one."""
    async def script(call):
        out = []
        for step in steps:
            token, name, args = step(out) if callable(step) else step
            out.append(await call(token, name, args))
        return out

    return _session(world, script)


def test_from_an_empty_studio_to_a_priced_scene_and_nobody_elses_photo(mounted, monkeypatch):
    """THE TASK, end to end, as two strangers through the real transport.
    Alice has nothing; she adds a picture, writes a scene held to it and
    gets a price. Bob cannot see her element, cannot use its ref, cannot
    add her render, and what he tried made nothing."""
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    w = mounted
    gen = w["render"](w["a"], 1)
    (e0, empty), (e1, added), (e2, listed), (e3, written), (e4, priced), \
        (e5, bobs), (e6, stolen), (e7, taken), (e8, bob_after) = _talk(w, [
            ("alice", "elements", {}),
            ("alice", "add_element", {"kind": "prop", "name": "Ghost Can", "source": gen,
                                      "notes": "matte black can"}),
            ("alice", "elements", {}),
            lambda out: ("alice", "write_scene", {
                "prompt": SCENE, "seconds": 10, "title": "Cold can",
                "refs": [out[1][1]["photo"]["ref"]]}),
            lambda out: ("alice", "quote", {"scene_id": out[3][1]["scene_id"]}),
            ("bob", "elements", {}),
            lambda out: ("bob", "write_scene", {"prompt": SCENE,
                                                "refs": [out[1][1]["photo"]["ref"]]}),
            ("bob", "add_element", {"kind": "prop", "name": "Mine now", "source": gen}),
            ("bob", "elements", {}),
        ])
    assert not e0 and empty["count"] == 0 and "add_element" in empty["note"]
    assert not e1 and added["added"] is True and added["credits"] == 0
    ref = added["photo"]["ref"]
    assert not e2 and listed["count"] == 1
    assert listed["elements"][0]["photos"] == [added["photo"]]
    assert not e3 and written["reference_photos"] == 1 and "needs_reference" not in written
    assert written["shots_written"] == 2
    assert not e4 and priced["clip"]["credits"] > 0 and priced["balance"] == 500
    assert priced["credits_needed"] > 0 and "estimate_usd" not in str(priced)
    # Bob: nothing of hers, by any door
    assert not e5 and bobs["count"] == 0
    assert e6 and "not one of your elements" in stolen
    assert e7 and "no render" in taken
    assert not e8 and bob_after["count"] == 0
    assert entities.list_props(dsn=w["dsn"], account_id=w["b"]) == []
    scene = preprod.get_concept(written["scene_id"], dsn=w["dsn"], account_id=w["a"])
    assert scene["shots"][0]["refs"] == [ref]
    assert preprod.list_concepts(dsn=w["dsn"], account_id=w["b"]) == []
    assert w["approved"] == [] and w["calls"]["drawn"] == []     # nothing rendered or drawn


def test_that_run_fails_if_the_ref_gate_is_bypassed(mounted, monkeypatch):
    """The isolation above rests on `_allowed_refs`. With it standing
    open, Bob's scene against Alice's photo is written -- which is what
    the assertion in the test above would catch."""
    monkeypatch.setattr(preprod, "refs_required", lambda: True)
    w = mounted
    added = _add(w, "a", "prop", "Ghost Can", w["render"](w["a"], 1))
    ref = added["photo"]["ref"]

    class Anything(dict):
        def __contains__(self, key):
            return True

        def __getitem__(self, key):
            return key

    monkeypatch.setattr(mcp_server, "_allowed_refs", lambda dsn, account_id: Anything())
    (failed, stolen), = _talk(w, [("bob", "write_scene", {"prompt": SCENE, "refs": [ref]})])
    assert not failed and stolen["reference_photos"] == 1      # the hole, open


def test_the_claude_listing_adds_a_picture_and_still_draws_nothing(mounted, web):
    """/mcp/claude: `add_element` is there and works by address; a still
    is not a tool; and what it added is the same element the other
    listing sees."""
    w = mounted
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())

    async def script(call):
        claude = "/claude/"
        return [await call("alice", "tools/list", path=claude),
                await call("alice", "add_element",
                           {"kind": "prop", "name": "Can", "source": URL}, path=claude),
                await call("alice", "generate_image", {"prompt": "a can on wet steel"},
                           path=claude),
                await call("alice", "elements")]            # the render listing's view

    (e0, names), (e1, added), (e2, still), (e3, listed) = _session(w, script)
    assert not e0 and names == list(mcp_server.CLAUDE_LISTED_TOOLS)
    # (`job` is on this listing since the overnight build's PR 2: the free edits run as jobs)
    assert "add_element" in names and not {"generate_image", "image_models", "approve"} & set(names)
    assert not e1 and added["photo"]["ref"].startswith("/props/can/photo/add-")
    assert e2 and "generate_image" in str(still)
    assert not e3 and listed["elements"][0]["photos"] == [added["photo"]]
    assert w["calls"]["drawn"] == []


def test_the_operators_door_can_add_a_picture_too(mounted):
    """The studio surface over HTTP (the static key acts as the oldest
    account): the same tool, answered typed."""
    w = mounted
    (failed, added), = _talk(w, [("operator-key", "add_element", {
        "kind": "character", "name": "Sam", "source": w["render"](w["a"], 2)})])
    assert not failed and added["added"] is True and added["name"] == "Sam"
    assert added["photo"]["ref"].startswith("/characters/sam/photo/add-")
    assert [c["name"] for c in entities.list_characters(dsn=w["dsn"],
                                                        account_id=w["a"])] == ["Sam"]


# --------------------------------------------------------------------------
# a still on the render listing: quote -> yes -> once (Mike's D1)
# --------------------------------------------------------------------------

def test_a_signed_in_caller_quotes_approves_and_cannot_spend_the_yes_twice(mounted,
                                                                           monkeypatch):
    """The listed door goes through `approval_gate` exactly as the studio
    door does: no token -> a quote and nothing spent; the token -> one
    job; the token again -> that same job, and the renderer is not called
    a second time. In credits only -- no dollars, no server path."""
    from src import fal

    w = mounted
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-secret-for-quotes")
    drawn = []

    def still(prompt, **kw):
        drawn.append({"prompt": prompt, **kw})
        return {"ok": True, "media_url": "/renders/fal/still.jpg", "generation_id": 91,
                "path": "/app/data/renders/fal/still.jpg", "references": 0,
                "asset_id": 55, "credits": 10, "error": None}

    monkeypatch.setattr(fal, "generate_image_from_prompt", still)
    ask = {"prompt": "a matte black can on wet steel", "model": "seedream4.5",
           "aspect": "1:1"}

    async def script(call):
        e0, models = await call("alice", "image_models")
        assert not e0 and all("credits" in m and "usd" not in m for m in models["models"])
        e1, quoted = await call("alice", "generate_image", ask)
        assert not e1 and quoted["needs_approval"] is True and quoted["can_approve"] is True
        quote = quoted["quote"]
        assert quote["credits"] > 0 and quote["balance"] == 500
        assert quote["balance_after"] == 500 - quote["credits"]
        assert "usd" not in quote and "usd" not in str(quoted).lower()
        assert drawn == []                                      # a quote spends nothing
        token = quote["quote_token"]

        e2, wrong = await call("bob", "generate_image", {**ask, "quote_token": token})
        assert e2 and "wrong_account" in wrong                  # not his yes
        e3, changed = await call("alice", "generate_image",
                                 {**ask, "prompt": "a red can", "quote_token": token})
        assert e3 and "stale_content" in changed
        assert drawn == []

        e4, started = await call("alice", "generate_image", {**ask, "quote_token": token})
        assert not e4 and started["job_id"] and "cancel_job" not in started["note"]
        for _ in range(200):
            failed, job = await call("alice", "job", {"job_id": started["job_id"]})
            assert not failed
            if job["status"] in ("done", "failed", "cancelled"):
                break
            await asyncio.sleep(0.05)
        assert job["status"] == "done"
        result = job["result"]
        assert result["ok"] and result["ref"] == "gen:55"
        assert "path" not in result and "usd" not in str(result).lower()
        assert len(drawn) == 1 and drawn[0]["account_id"] == w["a"]
        assert drawn[0]["quote"].credits == quote["credits"]    # the hold IS the yes
        # somebody else's job is no job
        assert (await call("bob", "job", {"job_id": started["job_id"]}))[0]

        e5, again = await call("alice", "generate_image", {**ask, "quote_token": token})
        assert not e5 and again["already_used"] is True
        assert again["job_id"] == started["job_id"]
        assert len(drawn) == 1                                  # and nothing drew again

    _session(w, script)


def test_a_still_the_balance_cannot_cover_is_a_structured_refusal(mounted, monkeypatch):
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-secret-for-quotes")
    monkeypatch.setattr(mcp_server, "_balance", lambda account_id, dsn: 3)
    (failed, out), = _talk(mounted, [("alice", "generate_image",
                                      {"prompt": "a can", "model": "seedream4.5"})])
    assert not failed and out["refused"] == "insufficient_credits"
    assert out["available"] == 3 and out["needs"] > 3 and "usd" not in str(out).lower()
