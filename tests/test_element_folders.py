"""The element folders are shared by name, and a studio with its own
bucket keys does not use them (docs/BACKLOG.md #25, 2026-10-11).

`characters/<slug>/`, `props/<slug>/` and `locations/<slug>/` carry no
account. Two studios on one machine that each named a character "Me"
shared `characters/me/`: each was listed the other's photo, an upload
called `photo.jpg` replaced the other's file, the vision description of
one was handed the other's face, `sheet.jpg` was one drawing for both,
and the photo route served either file to anyone who knew its name.

The connector's door was closed first (tests/test_mcp_add_element.py).
This file is the studio's own doors -- the Elements page, the composer,
the readers every stage is handed, the sheet, the delete, the routes --
plus the RAG shelf, whose key had the same hole.

Everything here runs against a real throwaway database and a bucket
that is a dict. Nothing draws, nothing calls a model, nothing touches
the network.
"""
import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import api, auth, jobs
from app import main as app_main
from src import (
    accounts,
    asset_shelf,
    element_sheet,
    entities,
    generative,
    ledger,
    outcomes,
    preprod,
    projects,
    quote_redemptions,
    rag,
    render_assets,
    scene_chain,
    scout,
    storage,
)
from src import locations as locations_mod
from src.approvals import ElementRefused
from src.cut import store as cut_store

PUBLIC = "https://pub.example"


def _jpeg(colour) -> bytes:
    """A real, small JPEG that is unmistakably one person's."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), colour).save(buf, "JPEG")
    return buf.getvalue()


def _colour(data: bytes) -> str:
    """Whose photo these bytes are, for a reader that re-encodes them."""
    from PIL import Image
    r, g, b = Image.open(io.BytesIO(data)).convert("RGB").getpixel((4, 4))
    return {r: "red", g: "green", b: "blue"}[max(r, g, b)]


ALICE = _jpeg((200, 30, 30))        # red
BOB = _jpeg((30, 30, 200))          # blue
STRANGER = _jpeg((30, 200, 30))     # green: a file nobody here uploaded
REF = "/characters/me/photo/photo.jpg"


# --------------------------------------------------------------------------
# two studios, one machine
# --------------------------------------------------------------------------

@pytest.fixture
def studios(pg, tmp_path, monkeypatch):
    """Alice and Bob, each with a workspace and credits to create with;
    the element folders in tmp; every model call the create body makes
    stood in for, and what each was HANDED kept."""
    for init in (preprod.init, scout.init, entities.init, generative.init, render_assets.init,
                 projects.init, cut_store.init, ledger.init, outcomes.init,
                 quote_redemptions.init):
        init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    for acct in (a, b):
        ledger.grant(acct, 500, "promo", dsn=pg)

    dirs = {kind: tmp_path / f"{kind}s" for kind in ("character", "prop", "location")}
    monkeypatch.setattr(asset_shelf, "PHOTO_DIRS", dirs)
    for module in (api, app_main):
        monkeypatch.setattr(module, "CHARACTERS_DIR", dirs["character"])
        monkeypatch.setattr(module, "PROPS_DIR", dirs["prop"])
        monkeypatch.setattr(module, "LOCATIONS_DIR", dirs["location"])
    monkeypatch.setattr(api, "_PHOTO_ROOTS", {"characters": dirs["character"],
                                              "props": dirs["prop"],
                                              "locations": dirs["location"]})
    cache = tmp_path / "photo-cache"
    cache.mkdir()
    monkeypatch.setattr(asset_shelf, "_PHOTO_CACHE", cache)
    asset_shelf._OWNER_HITS.clear()

    seen = {"described": [], "places": [], "drawn": [], "jobs": []}

    def describe(kind, name, photos, account_id=None):
        seen["described"].append((account_id, [Path(p).read_bytes() for p in photos]))
        return {"ok": True, "description": {"look": f"{name} as photographed"}, "error": None}

    def describe_place(client, name, photos):
        seen["places"].append([Path(p).read_bytes() for p in photos])
        return {"space": f"{name} as photographed"}

    monkeypatch.setattr(api, "describe_entity_photos", describe)
    monkeypatch.setattr(locations_mod, "describe_location", describe_place)
    monkeypatch.setattr(api, "_gemini_key", lambda account_id=None: "a-key")
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *args, **kw: {"ok": True, "chunks": 1, "error": None})

    # a sheet job runs where it is started, so a test sees what it did
    def start(kind, label, work, cancellable=False, *, account_id=None):
        seen["jobs"].append(work({"id": 1}))
        return {"id": 1}

    monkeypatch.setattr(jobs, "start", start)
    monkeypatch.setattr(jobs, "progress", lambda *args, **kw: None)

    def draw(kind, name, photos, out_dir, *, detail="", notes="", account_id=None,
             db_path=None, quote=None):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "sheet.jpg"
        path.write_bytes(b"sheet of account %d" % account_id)
        seen["drawn"].append((account_id, [Path(p).read_bytes() for p in photos], out_dir))
        return {"ok": True, "path": path, "generation_id": None, "error": None}

    monkeypatch.setattr(element_sheet, "draw", draw)
    from src import fal, nano_banana

    def must_not_draw(*args, **kw):
        raise AssertionError("nothing in this file may reach an image model")

    monkeypatch.setattr(nano_banana, "generate_from_prompt", must_not_draw)
    monkeypatch.setattr(fal, "generate_image_from_prompt", must_not_draw)

    return {"dsn": pg, "a": a, "b": b, "dirs": dirs, "seen": seen,
            "slug": {a: accounts.slug_of(a, dsn=pg), b: "bobs-studio"}}


@pytest.fixture
def bucket(monkeypatch):
    """R2 configured on the `tenant` rung, as a dict: what was uploaded,
    under which key, and it can be read back. No boto3 call is made."""
    for name, value in (("R2_ACCOUNT_ID", "acct"), ("R2_ACCESS_KEY_ID", "key"),
                        ("R2_SECRET_ACCESS_KEY", "secret"), ("R2_BUCKET", "zpf"),
                        ("R2_PUBLIC_BASE_URL", PUBLIC + "/")):
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ZEROPAGE_MEDIA", "tenant")
    held: dict = {}

    def upload_file(path, key=None, content_type=None):
        held[key] = Path(path).read_bytes()
        storage._note_uploaded(key)
        return f"{PUBLIC}/{key}"

    def upload_bytes(data, key, content_type=None):
        held[key] = bytes(data)
        storage._note_uploaded(key)
        return f"{PUBLIC}/{key}"

    def read_key(key, max_bytes=None):
        data = held.get(key)
        return None if data is None or (max_bytes and len(data) > max_bytes) else data

    class Answer:
        def __init__(self, data):
            self.content = data

        def raise_for_status(self):
            if self.content is None:
                raise RuntimeError("404")

    import requests
    monkeypatch.setattr(storage, "upload_file", upload_file)
    monkeypatch.setattr(storage, "upload_bytes", upload_bytes)
    monkeypatch.setattr(storage, "read_key", read_key)
    monkeypatch.setattr(storage, "list_keys",
                        lambda prefix="": [k for k in held if k.startswith(prefix)])
    # the bucket's public address, for the one reader that asks it by URL
    monkeypatch.setattr(requests, "get", lambda url, timeout=None:
                        Answer(held.get(url.removeprefix(PUBLIC + "/"))))
    storage.forget_listings()
    yield held
    storage.forget_listings()


@pytest.fixture
def shelf(monkeypatch):
    """The RAG library as a dict of source -> record, with the two
    statements the assets shelf sends it. No embedding is made."""
    docs: dict = {}

    class Conn:
        def execute(self, sql, params=()):
            assert sql.startswith("DELETE FROM rag_documents WHERE source = %s AND project = %s")
            source, project = params
            if docs.get(source, {}).get("project") == project:
                del docs[source]

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    def ingest(records, client, conn):
        for record in records:
            docs[record["source"]] = record          # a source's chunks are replaced
        return len(records)

    monkeypatch.setattr(rag, "connect", lambda db_url=None: Conn())
    monkeypatch.setattr(rag, "init_store", lambda conn: None)
    monkeypatch.setattr(rag, "make_client", lambda: object())
    monkeypatch.setattr(rag, "ingest_records", ingest)
    monkeypatch.setattr(rag, "delete_source", lambda conn, source: docs.pop(source, None))
    return docs


def _me(studios, who, photo, **kw):
    """The Elements page's own create: a character called "Me", with an
    upload that is called photo.jpg whoever sends it."""
    kw.setdefault("sheet", False)
    return api.create_element("character", "Me", account_id=studios[who],
                              uploads=[("photo.jpg", photo)], **kw)


def _listed(studios, who) -> list:
    """What the Elements page and the composer are listed for "Me"."""
    items = api._assets_all(studios[who], "elements")
    return [photo for item in items if item["name"] == "Me" for photo in item["photos"]]


def _plant(studios, name="photo.jpg", data=STRANGER, kind="character", slug="me") -> Path:
    """A file in the shared folder that nobody in the test put there
    through the studio: another account's, or last week's."""
    folder = studios["dirs"][kind] / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return folder / name


def _folder_is_untouched(studios, *names) -> bool:
    folder = studios["dirs"]["character"] / "me"
    return sorted(p.name for p in folder.iterdir()) == sorted(names)


# --------------------------------------------------------------------------
# the listing, and what a create keeps
# --------------------------------------------------------------------------

def test_two_studios_with_the_same_element_name_are_listed_only_their_own(studios, bucket, shelf):
    """THE LEAK, closed for the studio's own door. Same machine, same
    name, the same file name, the deployed posture: each is listed one
    photo, each photo is its own bytes under its own account's keys, and
    neither was written to the folder the two would share."""
    assert _me(studios, "a", ALICE)["ok"] and _me(studios, "b", BOB)["ok"]
    for who, mine in (("a", ALICE), ("b", BOB)):
        assert _listed(studios, who) == [REF]
        assert bucket[f"m/{studios[who]}/characters/me/photo.jpg"] == mine
        # the catalogue the scene writer and the graph read says the same
        named = [item for item in asset_shelf.catalogue(studios["dsn"], account_id=studios[who])
                 if item["name"] == "Me"]
        assert [item["photos"] for item in named] == [[REF]]
    assert not (studios["dirs"]["character"] / "me").exists()


def test_a_file_left_in_the_shared_folder_is_listed_to_nobody(studios, bucket, shelf):
    """Whatever is in `characters/me/` -- another account's upload, a
    file from before today -- it is not this studio's, and no listing
    hands it out."""
    _plant(studios, "someone-elses-face.jpg")
    _plant(studios, "sheet.jpg", b"someone else's sheet")
    _me(studios, "a", ALICE)
    assert _listed(studios, "a") == [REF]
    assert _listed(studios, "b") == []                 # Bob has no element, and no photo
    # Bob makes his: still only his own
    _me(studios, "b", BOB)
    assert _listed(studios, "b") == [REF]
    assert [item["sheet"] for item in api._assets_all(studios["b"], "elements")] == [None]
    # ...and neither does the listing `src/` builds for itself, which is
    # what the scene writer, the graph and the connector read
    for who in ("a", "b"):
        assert asset_shelf.photo_urls("character", "me", studios[who]) == [REF]
        named = asset_shelf.catalogue(studios["dsn"], account_id=studios[who])
        assert [item["photos"] for item in named if item["name"] == "Me"] == [[REF]]
    assert _folder_is_untouched(studios, "someone-elses-face.jpg", "sheet.jpg")


def test_the_sheet_is_listed_last_from_the_bucket_as_it_is_from_the_folder(studios, bucket):
    """`refs[0]` is the frame a clip anchors on, and a sheet is a drawing
    of the face, never evidence of it. A name that sorts after "sheet"
    used to put the drawing first in the bucket's listing."""
    for name in ("sheet.jpg", "zoe-front.jpg", "amy.jpg"):
        bucket[f"m/{studios['a']}/characters/me/{name}"] = ALICE
    assert asset_shelf.photo_urls("character", "me", studios["a"]) == [
        "/characters/me/photo/amy.jpg", "/characters/me/photo/zoe-front.jpg",
        "/characters/me/photo/sheet.jpg"]


def test_a_picture_the_bucket_did_not_take_is_refused_and_nothing_is_kept(studios, bucket, shelf,
                                                                           monkeypatch):
    """The bucket was to be the only copy. From the page too: no row, no
    file in the shared folder, and words a person can act on."""
    def down(*args, **kw):
        raise RuntimeError("bucket unreachable")

    monkeypatch.setattr(storage, "upload_file", down)
    with pytest.raises(ElementRefused) as refused:
        _me(studios, "a", ALICE)
    assert refused.value.code == "not_saved" and "try again" in refused.value.message
    with pytest.raises(ElementRefused):
        api.create_element("location", "Garage", account_id=studios["a"],
                           uploads=[("wide.jpg", ALICE)])
    assert entities.list_characters(dsn=studios["dsn"], account_id=studios["a"]) == []
    assert preprod.list_locations(dsn=studios["dsn"], account_id=studios["a"]) == []
    assert not any(d.exists() for d in studios["dirs"].values()) and bucket == {}


def test_the_media_listing_reads_no_date_off_a_file_that_is_not_the_accounts(studios, bucket,
                                                                            shelf):
    """`GET /api/media` dates a photo by its file. For an account the
    folder is not the store of, the file under that name is somebody
    else's: its photo is listed, from its own keys, with no date read."""
    import os
    planted = _plant(studios)
    os.utime(planted, (1_500_000_000, 1_500_000_000))
    _me(studios, "b", BOB)
    rows = api.media_list(q=None, category=None, kind="image", limit=500, scope="elements",
                          folder=None, starred=False, provider=None,
                          account_id=studios["b"])["items"]
    assert [(r["url"], r["ts"]) for r in rows] == [(REF, 0.0)]


# --------------------------------------------------------------------------
# reading the bytes back
# --------------------------------------------------------------------------

def test_one_name_reads_back_as_each_studios_own_bytes(studios, bucket, shelf):
    """The ref on a shot is a NAME, and it is the same name for both:
    `/characters/me/photo/photo.jpg`. Read as Alice it is Alice's bytes,
    read as Bob it is Bob's -- through the reader the composer uses, the
    one every stage is handed, and the one `src/` falls back to -- and a
    different file sitting under that name in the shared folder is never
    what either gets."""
    _plant(studios)                                    # characters/me/photo.jpg, a stranger's
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    for who, mine in (("a", ALICE), ("b", BOB)):
        account = studios[who]
        assert api._photo_bytes(REF, account) == mine
        assert api._resolver(account)(REF).read_bytes() == mine
        assert asset_shelf.resolver(account)(REF).read_bytes() == mine
        assert asset_shelf.own_photo_file(REF, account).read_bytes() == mine
        # ...and what the graph and the scene writer are shown, with no app
        # around to hand them a reader
        seen = scene_chain.as_image_refs([REF], account_id=account)
        assert [_colour(data) for data, _mime, _label in seen] == [
            "red" if mine is ALICE else "blue"]
    # the two copies are two files, and neither is the folder's
    paths = {asset_shelf.own_photo_file(REF, studios[who]) for who in ("a", "b")}
    assert len(paths) == 2 and not any(studios["dirs"]["character"] in p.parents for p in paths)
    assert (studios["dirs"]["character"] / "me" / "photo.jpg").read_bytes() == STRANGER


def test_a_reader_that_names_nobody_opens_no_element_folder_here(studios, bucket):
    """The deployed posture: a per-account bucket, and the machine names
    no folder account. The un-scoped reader -- what a stage was handed
    until today -- resolves an element photo to nothing, however real
    the file in the folder is. The bin is shared by decision and still
    resolves."""
    _plant(studios)
    assert asset_shelf.resolve_photo(REF) is None
    assert api._resolve_asset_photo(REF) is None
    assert api._photo_bytes(REF) is None                # nobody's, and no flat copy either
    assert asset_shelf.folder_is_store(None) is False
    assert asset_shelf.folder_is_store(studios["a"]) is False


def test_a_photo_another_studio_never_had_reads_as_nothing(studios, bucket, shelf):
    """Bob has no "Me". Alice's name, asked as Bob, is not Alice's photo."""
    _me(studios, "a", ALICE)
    assert api._photo_bytes(REF, studios["b"]) is None
    assert api._resolver(studios["b"])(REF) is None


def test_a_photo_written_again_is_read_fresh(studios, bucket, shelf, monkeypatch):
    """One key can be written twice: the same upload name, a sheet
    redrawn. The copy a reader holds is dropped by the write, so the
    next read is of the new bytes -- and within the cache's life an
    unchanged photo is not fetched twice."""
    _me(studios, "a", ALICE)
    reads = []
    real = storage.read_key
    monkeypatch.setattr(storage, "read_key",
                        lambda key, max_bytes=None: reads.append(key) or real(key, max_bytes))
    assert api._photo_bytes(REF, studios["a"]) == ALICE
    assert api._photo_bytes(REF, studios["a"]) == ALICE
    assert len(reads) == 1
    _me(studios, "a", BOB)                             # the same name, new bytes
    assert api._photo_bytes(REF, studios["a"]) == BOB
    assert len(reads) == 2
    # a bucket that stops answering leaves the studio its own last copy
    monkeypatch.setattr(asset_shelf, "PHOTO_CACHE_TTL", 0.0)
    monkeypatch.setattr(storage, "read_key", lambda key, max_bytes=None: None)
    assert api._photo_bytes(REF, studios["a"]) == BOB


def test_copies_nobody_has_read_for_an_hour_are_removed(studios, bucket, shelf, monkeypatch):
    """The copies are scratch, on a small disk. One that has not been
    fetched for an hour goes at the next sweep, a fresh one stays, and a
    sweep comes round on its own as copies are written."""
    import os
    import time
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    old = asset_shelf.own_photo_file(REF, studios["a"])
    fresh = asset_shelf.own_photo_file(REF, studios["b"])
    long_ago = time.time() - asset_shelf.PHOTO_CACHE_KEEP - 60
    os.utime(old, (long_ago, long_ago))
    assert asset_shelf._sweep_photo_cache() == 1
    assert not old.exists() and fresh.read_bytes() == BOB
    # and it is read again when it is next wanted
    assert asset_shelf.own_photo_file(REF, studios["a"]).read_bytes() == ALICE

    os.utime(old, (long_ago, long_ago))
    monkeypatch.setattr(asset_shelf, "PHOTO_CACHE_SWEEP_EVERY", 1)
    bucket[f"m/{studios['b']}/characters/me/second.jpg"] = BOB
    asset_shelf.own_photo_file("/characters/me/photo/second.jpg", studios["b"])
    assert not old.exists()


# --------------------------------------------------------------------------
# the description
# --------------------------------------------------------------------------

def test_each_description_is_of_that_studios_photo_alone(studios, bucket, shelf):
    """The vision step used to read the whole folder: the second "Me"
    was described from both faces. Each is described from the one photo
    its own request wrote, whatever else sits under that name."""
    _plant(studios, "someone-elses-face.jpg")
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    assert studios["seen"]["described"] == [(studios["a"], [ALICE]), (studios["b"], [BOB])]

    _plant(studios, "wide.jpg", kind="location", slug="garage")
    for who, mine in (("a", ALICE), ("b", BOB)):
        made = api.create_element("location", "Garage", account_id=studios[who],
                                  uploads=[("wide.jpg", mine)])
        assert made["described"] and made["photos"] == 1
    assert studios["seen"]["places"] == [[ALICE], [BOB]]
    rows = preprod.list_locations(dsn=studios["dsn"], account_id=studios["a"])
    assert [r["photo_count"] for r in rows] == [1]     # its own one, not the folder's


def test_the_shelf_catch_up_describes_a_studios_own_photos(studios, bucket, shelf, monkeypatch):
    """`POST /api/assets/backfill` with describe on walks an account's
    undescribed cast. It read the shared folder by name; it reads the
    account's own keys."""
    _plant(studios, "someone-elses-face.jpg")
    for who, mine in (("a", ALICE), ("b", BOB)):
        entities.add_character(name="Me", role="", description=None, reference_image="",
                               photo_count=1, notes="", account_id=studios[who],
                               dsn=studios["dsn"])
        bucket[f"m/{studios[who]}/characters/me/photo.jpg"] = mine
    handed = []
    monkeypatch.setattr(locations_mod, "describe_entity",
                        lambda client, kind, name, photos:
                        handed.append([Path(p).read_bytes() for p in photos]) or {"look": "x"})
    for who in ("a", "b"):
        out = asset_shelf.backfill(db_path=studios["dsn"], describe=True,
                                   gemini_client=object(), account_id=studios[who])
        assert out["described"] == 1 and out["failed"] == 0
    assert handed == [[ALICE], [BOB]]


# --------------------------------------------------------------------------
# the sheet
# --------------------------------------------------------------------------

def test_a_sheet_is_drawn_from_and_saved_to_its_own_studio(studios, bucket, shelf):
    """`sheet.jpg` is ONE name per folder. Made with the element, it is
    drawn from the photo that request wrote -- by then held only under
    the account's keys -- and it lands under those keys and nowhere a
    second studio would find it."""
    _plant(studios, "someone-elses-face.jpg")
    made = _me(studios, "a", ALICE, sheet=True)
    assert made["sheet_job"] == 1
    account, photos, out_dir = studios["seen"]["drawn"][0]
    assert (account, photos) == (studios["a"], [ALICE])
    assert studios["dirs"]["character"] not in out_dir.parents
    assert bucket[f"m/{studios['a']}/characters/me/sheet.jpg"] == b"sheet of account %d" % account
    assert _listed(studios, "a") == [REF, "/characters/me/photo/sheet.jpg"]

    # Bob's "Me" has no sheet, and Alice's is not his
    _me(studios, "b", BOB)
    assert _listed(studios, "b") == [REF]
    assert api._photo_bytes("/characters/me/photo/sheet.jpg", studios["b"]) is None
    assert _folder_is_untouched(studios, "someone-elses-face.jpg")


def test_a_sheet_is_never_written_into_a_folder_that_is_not_the_accounts(studios, bucket,
                                                                        tmp_path, monkeypatch):
    """Wherever its photos were read from. The folder is the place for a
    sheet only for the account the folder is the store of."""
    folder, scratch = studios["dirs"]["character"] / "me", tmp_path / "scratch"
    on_disk = [folder / "photo.jpg"]
    assert element_sheet.out_dir_for(folder, on_disk, scratch, studios["a"]) == scratch / "sheet"
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", str(studios["a"]))
    assert element_sheet.out_dir_for(folder, on_disk, scratch, studios["a"]) == folder
    assert element_sheet.out_dir_for(folder, on_disk, scratch, studios["b"]) == scratch / "sheet"


def test_a_redraw_never_reads_or_replaces_another_studios_drawing(studios, bucket, shelf):
    """The Elements card's redraw, for both, with a stranger's sheet and
    a stranger's face already under that name in the folder."""
    _plant(studios, "someone-elses-face.jpg")
    planted = _plant(studios, "sheet.jpg", b"someone else's sheet")
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    for who, mine in (("a", ALICE), ("b", BOB)):
        account = studios[who]
        row = entities.list_characters(dsn=studios["dsn"], account_id=account)[0]
        assert api.asset_draw_sheet("characters", row["id"], account_id=account) == {"job_id": 1}
        drawn_as, photos, out_dir = studios["seen"]["drawn"][-1]
        assert (drawn_as, photos) == (account, [mine])
        assert studios["dirs"]["character"] not in out_dir.parents
        assert bucket[f"m/{account}/characters/me/sheet.jpg"] == b"sheet of account %d" % account
        assert api._photo_bytes("/characters/me/photo/sheet.jpg", account) == (
            b"sheet of account %d" % account)
    assert planted.read_bytes() == b"someone else's sheet"


# --------------------------------------------------------------------------
# the delete, and the shelf
# --------------------------------------------------------------------------

def test_deleting_an_element_leaves_the_other_studios_alone(studios, bucket, shelf):
    """Alice deletes her "Me". Bob's row, his photo, his listing and his
    shelf entry are exactly as they were, and nothing in the folder was
    touched. (What a delete removes is unchanged: the row and the shelf
    entry. The photo stays under its account's keys.)"""
    _plant(studios, "someone-elses-face.jpg")
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    key = {who: f"assets/a{studios[who]}/character-me" for who in ("a", "b")}
    assert set(shelf) == set(key.values())

    row = entities.list_characters(dsn=studios["dsn"], account_id=studios["a"])[0]
    assert api.asset_delete_character(row["id"], account_id=studios["a"]) == {"deleted": row["id"]}

    assert entities.list_characters(dsn=studios["dsn"], account_id=studios["a"]) == []
    assert [c["name"] for c in entities.list_characters(dsn=studios["dsn"],
                                                        account_id=studios["b"])] == ["Me"]
    assert set(shelf) == {key["b"]} and shelf[key["b"]]["project"] == "bobs-studio"
    assert _listed(studios, "b") == [REF] and api._photo_bytes(REF, studios["b"]) == BOB
    assert bucket[f"m/{studios['a']}/characters/me/photo.jpg"] == ALICE     # bytes stay
    assert _folder_is_untouched(studios, "someone-elses-face.jpg")


def test_the_shelf_keeps_two_same_named_elements_apart(studios, shelf):
    """The shelf key was `assets/character-me` for everybody: the second
    save replaced the first studio's description, and either delete
    dropped the other's."""
    a, b = studios["a"], studios["b"]
    for account, look in ((a, "a red jacket"), (b, "a blue coat")):
        out = asset_shelf.ingest_one("character", "me", "Me", {"notes": look},
                                     project=studios["slug"][account], account_id=account)
        assert out["ok"]
    assert "a red jacket" in shelf[f"assets/a{a}/character-me"]["text"]
    assert "a blue coat" in shelf[f"assets/a{b}/character-me"]["text"]
    asset_shelf.drop_one("character", "me", account_id=b, project="bobs-studio")
    assert set(shelf) == {f"assets/a{a}/character-me"}


def test_an_old_flat_entry_is_retired_only_by_the_studio_it_is_labelled_for(studios, shelf):
    """Entries written before the account was in the key sit under the
    flat one. Saving the element again replaces the studio's OWN old
    entry (or it would be retrieved twice); one labelled for another
    studio, or for nobody, is not this caller's to remove."""
    a, b = studios["a"], studios["b"]
    flat = "assets/character-me"
    shelf[flat] = {"source": flat, "text": "old", "project": studios["slug"][a]}
    asset_shelf.ingest_one("character", "me", "Me", {"notes": "Bob's"},
                           project="bobs-studio", account_id=b)
    assert flat in shelf                                # Alice's, and Bob left it
    asset_shelf.drop_one("character", "me", account_id=b, project="bobs-studio")
    assert flat in shelf
    asset_shelf.ingest_one("character", "me", "Me", {"notes": "Alice's"},
                           project=studios["slug"][a], account_id=a)
    assert set(shelf) == {f"assets/a{a}/character-me"}  # her new one replaced her old one

    shelf[flat] = {"source": flat, "text": "nobody's", "project": None}
    asset_shelf.drop_one("character", "me", account_id=a, project=studios["slug"][a])
    assert set(shelf) == {flat}
    # with no account the key is the flat one, as it always was
    assert asset_shelf.source_key("character", "me") == flat


# --------------------------------------------------------------------------
# the photo routes
# --------------------------------------------------------------------------

@pytest.fixture
def browser(monkeypatch):
    """The studio's own origin asking a photo route, signed in as an
    account or as nobody."""
    asked = []

    def whose(request):
        """Each test session cookie names its account: `session-<id>`."""
        token = request.cookies.get(auth.SESSION_COOKIE) or ""
        asked.append(token)
        return int(token.removeprefix("session-")) if token else None

    monkeypatch.setattr(auth, "optional_account_id", whose)
    app_main._PHOTO_CALLERS.clear()
    client = TestClient(app_main.app, follow_redirects=False)

    def get(path, account=None):
        client.cookies.clear()
        if account is not None:
            client.cookies.set(auth.SESSION_COOKIE, f"session-{account}")
        return client.get(path)

    get.asked = asked
    yield get
    app_main._PHOTO_CALLERS.clear()


def test_a_photo_route_serves_each_caller_their_own_photo(studios, bucket, shelf, browser):
    """`/characters/me/photo/photo.jpg` is one address. Signed in as
    Alice it goes to Alice's object, as Bob to Bob's; and the file a
    stranger left under that name in the folder is served to neither,
    to a third account, nor to somebody signed out."""
    planted = _plant(studios)                          # characters/me/photo.jpg
    _plant(studios, "only-in-the-folder.jpg")
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    for who in ("a", "b"):
        res = browser(REF, studios[who])
        assert res.status_code == 302
        assert res.headers["location"] == f"{PUBLIC}/m/{studios[who]}/characters/me/photo.jpg"
        assert res.headers["cache-control"] == "private" and res.headers["vary"] == "Cookie"
    for account in (studios["a"], studios["b"], 999, None):
        for path in (REF, "/characters/me/photo/only-in-the-folder.jpg"):
            res = browser(path, account)
            assert res.content != STRANGER and res.status_code in (302, 404)
            # the one redirect left is the old flat key, where nothing of theirs is
            if account in (999, None) or path != REF:
                assert res.headers["location"] == f"{PUBLIC}/{path.replace('/photo/', '/')[1:]}"
    assert planted.read_bytes() == STRANGER


def test_a_strip_of_photos_asks_who_is_signed_in_once(studios, bucket, shelf, browser):
    """A session costs two database reads to resolve. One per photo of a
    fourteen-frame element is twenty-eight; it is asked once a minute per
    session, each session is its own answer, and nobody signed out is
    looked up at all."""
    _me(studios, "a", ALICE)
    _me(studios, "b", BOB)
    for _ in range(5):
        assert browser(REF, studios["a"]).headers["location"].startswith(
            f"{PUBLIC}/m/{studios['a']}/")
        assert browser(REF, studios["b"]).headers["location"].startswith(
            f"{PUBLIC}/m/{studios['b']}/")
        browser(REF)
    assert sorted(browser.asked) == [f"session-{studios['a']}", f"session-{studios['b']}"]


def test_a_thumbnail_is_the_callers_own_too(studios, bucket, shelf, browser):
    _me(studios, "a", ALICE)
    assert f"t/{studios['a']}/characters/me/photo.jpg" in bucket     # made by the mirror
    res = browser(REF + "?thumb=1", studios["a"])
    assert res.headers["location"] == f"{PUBLIC}/t/{studios['a']}/characters/me/photo.jpg"
    # no derivative on file: the full photo, never a broken tile
    del bucket[f"t/{studios['a']}/characters/me/photo.jpg"]
    storage.forget_listings()
    res = browser(REF + "?thumb=1", studios["a"])
    assert res.headers["location"] == f"{PUBLIC}/m/{studios['a']}/characters/me/photo.jpg"


# --------------------------------------------------------------------------
# the operator's own machine, and a machine with no bucket
# --------------------------------------------------------------------------

@pytest.mark.parametrize("named_by", ["slug", "id"])
def test_the_machine_that_names_its_folder_account_reads_that_folder_first(
        studios, bucket, shelf, browser, monkeypatch, named_by):
    """Mike's Mac: R2 on the `tenant` rung, and one line in its .env.
    The folder is that account's -- a photo dropped into it by hand is
    listed and read off disk, a create writes it (and mirrors) -- while
    a second account on the same machine still gets its own bucket keys
    and nothing from the folder."""
    a, b = studios["a"], studios["b"]
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT",
                       studios["slug"][a] if named_by == "slug" else str(a))
    dropped = _plant(studios, "dropped-by-hand.jpg", ALICE)
    entities.add_character(name="Me", role="", description=None, reference_image="",
                           photo_count=1, notes="", account_id=a, dsn=studios["dsn"])
    by_hand = "/characters/me/photo/dropped-by-hand.jpg"
    assert _listed(studios, "a") == [by_hand]           # not in the bucket, and listed
    assert api._resolver(a)(by_hand) == dropped         # off disk, not a copy
    assert api._photo_bytes(by_hand, a) == ALICE
    assert asset_shelf.resolve_photo(by_hand, roots=api._PHOTO_ROOTS) == dropped   # the CLI's reader
    assert browser(by_hand, a).content == ALICE

    _me(studios, "a", ALICE)                            # the page's create: the folder, and the mirror
    assert (studios["dirs"]["character"] / "me" / "photo.jpg").read_bytes() == ALICE
    assert bucket[f"m/{a}/characters/me/photo.jpg"] == ALICE
    assert studios["seen"]["described"][-1] == (a, [ALICE, ALICE])   # the whole folder, as ever

    # Bob, on the same machine, is not the folder's account
    _me(studios, "b", BOB)
    assert _listed(studios, "b") == [REF] and api._photo_bytes(REF, b) == BOB
    assert api._photo_bytes(by_hand, b) is None
    assert studios["seen"]["described"][-1] == (b, [BOB])
    assert browser(by_hand, b).content != ALICE and browser(REF, b).status_code == 302
    assert (studios["dirs"]["character"] / "me" / "photo.jpg").read_bytes() == ALICE


def test_on_the_operators_machine_a_second_accounts_sheet_is_still_its_own(
        studios, bucket, shelf, monkeypatch):
    """The folder has an owner here, so a reader that names nobody opens
    it. A second account's sheet must not: its "Me" shares the owner's
    folder name AND file name, and its drawing is from its own photo,
    saved under its own keys, with the owner's folder left as it was."""
    a, b = studios["a"], studios["b"]
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", str(a))
    _me(studios, "a", ALICE)                            # characters/me/photo.jpg, the owner's
    _me(studios, "b", BOB)
    row = entities.list_characters(dsn=studios["dsn"], account_id=b)[0]
    assert api.asset_draw_sheet("characters", row["id"], account_id=b) == {"job_id": 1}
    drawn_as, photos, out_dir = studios["seen"]["drawn"][-1]
    assert (drawn_as, photos) == (b, [BOB])
    assert studios["dirs"]["character"] not in out_dir.parents
    assert _folder_is_untouched(studios, "photo.jpg")
    assert bucket[f"m/{b}/characters/me/sheet.jpg"] == b"sheet of account %d" % b
    assert f"m/{a}/characters/me/sheet.jpg" not in bucket
    # the owner's own redraw reads its folder and writes its folder, as ever
    row = entities.list_characters(dsn=studios["dsn"], account_id=a)[0]
    api.asset_draw_sheet("characters", row["id"], account_id=a)
    drawn_as, photos, out_dir = studios["seen"]["drawn"][-1]
    assert (drawn_as, photos, out_dir) == (a, [ALICE], studios["dirs"]["character"] / "me")


def test_signed_out_the_folder_is_served_only_on_the_operators_own_box(
        studios, bucket, browser, monkeypatch):
    """The dev console is open and draws these routes with no session,
    which is right on the operator's machine and nowhere else."""
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", str(studios["a"]))
    _plant(studios, "photo.jpg", ALICE)
    assert browser(REF).content == ALICE                # dev tools on, an owner named
    monkeypatch.setattr(app_main, "DEV_TOOLS", False)
    assert browser(REF).content != ALICE
    monkeypatch.setattr(app_main, "DEV_TOOLS", True)
    monkeypatch.delenv("ZEROPAGE_FOLDER_ACCOUNT")
    assert browser(REF).content != ALICE


def test_a_photo_the_folder_account_holds_only_in_the_bucket_is_still_read(studios, bucket, shelf,
                                                                           monkeypatch):
    """The folder first, the account's bucket copy behind it: a photo
    uploaded from another machine reads on this one."""
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", str(studios["a"]))
    bucket[f"m/{studios['a']}/characters/me/photo.jpg"] = ALICE
    assert api._photo_bytes(REF, studios["a"]) == ALICE


def test_with_no_bucket_the_folder_is_the_store_for_everybody(studios, shelf, browser):
    """One studio on one machine, no R2: nothing changed. The create
    writes the folder, the listing and the readers use it, the route
    serves it."""
    made = _me(studios, "a", ALICE)
    assert made["ok"] and (studios["dirs"]["character"] / "me" / "photo.jpg").exists()
    assert _listed(studios, "a") == [REF]
    assert api._photo_bytes(REF, studios["a"]) == ALICE
    assert api._resolve_asset_photo(REF).read_bytes() == ALICE
    assert asset_shelf.folder_is_store(studios["a"]) and asset_shelf.folder_is_store(None)
    res = browser(REF, studios["a"])
    assert res.status_code == 200 and res.content == ALICE
    assert "vary" not in res.headers


def test_the_legacy_rung_is_not_a_per_account_bucket(studios, bucket, monkeypatch):
    """On `legacy` the bucket is flat too: nothing there is per account,
    so the folder stays the store, exactly as before."""
    monkeypatch.setenv("ZEROPAGE_MEDIA", "legacy")
    assert not asset_shelf.per_account_bucket()
    assert asset_shelf.folder_is_store(studios["a"])


# --------------------------------------------------------------------------
# the rule itself, and the guard against the next call site
# --------------------------------------------------------------------------

def test_whose_the_folder_is(studios, bucket, monkeypatch):
    a, b = studios["a"], studios["b"]
    assert not asset_shelf.folder_is_store(a) and not asset_shelf.folder_is_store(None)
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", "bobs-studio")
    assert asset_shelf.folder_is_store(b) and not asset_shelf.folder_is_store(a)
    assert asset_shelf.folder_is_store(None)            # the CLI, on a machine with an owner
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", "no-such-studio")
    assert not asset_shelf.folder_is_store(a) and not asset_shelf.folder_is_store(b)
    monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", "  ")
    assert not asset_shelf.folder_is_store(b)


def test_no_stage_in_the_api_is_handed_the_reader_that_names_nobody():
    """A stage handed `_resolve_asset_photo` reads the folder for
    whoever asks, on any machine where the folder is somebody's. Every
    hand-off in app/api.py goes through `_resolver(account_id)`, and
    every `_photo_bytes` call says whose photo it wants."""
    source = Path(api.__file__).read_text()
    assert "resolve_photo=_resolve_asset_photo" not in source
    assert len(re.findall(r"resolve_photo=_resolver\(account_id\)", source)) >= 10
    calls = [c for c in re.findall(r"_photo_bytes\(([^\n]*)", source)
             if not c.startswith("url: str")]
    assert calls and all("account_id" in c for c in calls), calls


def test_read_key_never_raises_and_respects_the_bound(monkeypatch):
    for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", PUBLIC)

    class Client:
        def get_object(self, Bucket, Key):
            if Key == "gone":
                raise KeyError("NoSuchKey")
            return {"ContentLength": 4, "Body": io.BytesIO(b"abcd")}

    monkeypatch.setattr(storage, "_client", lambda: Client())
    assert storage.read_key("here") == b"abcd"
    assert storage.read_key("here", max_bytes=4) == b"abcd"
    assert storage.read_key("here", max_bytes=3) is None
    assert storage.read_key("gone") is None and storage.read_key("") is None
    monkeypatch.delenv("R2_BUCKET")
    assert storage.read_key("here") is None             # R2 off: nothing, and no call
