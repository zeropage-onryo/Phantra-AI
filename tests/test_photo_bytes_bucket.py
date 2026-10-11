"""
A stored reference NAME is read from the bucket when this machine has no
file for it.

2026-10-11. From the `tenant` rung up an element photo is listed and
stored as its name, `/characters/<slug>/photo/<file>`
(asset_shelf.photo_url / storable_ref). On the deployed API that is
neither a file -- the photo folders are gitignored AND dockerignored --
nor an http URL, and `api._photo_bytes` read only those two. So a face
picked in the composer went on the shot and reached no model, "Make
element" from one saved nothing, and an effect could not read it as its
source. The reader takes the caller's account now and asks
asset_shelf.bucket_url where the bucket holds the photo for THAT account.

What these hold: the bytes come from the caller's own keys and never the
flat one every account shares; an element photo with no account gets
nothing; the bin is the shared address for anyone; disk still wins;
somebody else's URL is fetched exactly as it was given; and each of the
three doors that read a reference says whose it is.

Nothing here reaches the network. The bucket is a dict behind
imagery.fetch_image_bytes -- the one fetch the reader makes -- and
conftest's guard fails anything that slips past it.
"""
import ast
import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import FormData

from app import api, auth, jobs
from app.main import app
from src import (
    accounts,
    asset_shelf,
    effects,
    entities,
    fal,
    generative,
    imagery,
    ledger,
    outcomes,
    preprod,
    render_assets,
    storage,
)

BASE = "https://pub-abc123.r2.dev"

MICHAEL = "/characters/michael/photo/IMG_1.jpg"
BIN = "/refs/0a1b2c.jpg"
FLAT_MICHAEL = f"{BASE}/characters/michael/IMG_1.jpg"
SOMEBODY_ELSES = "https://cdn.example/props/can/front.jpg"

# Two accounts each have a `michael`, and the flat key the bucket moved
# away from still answers -- with bytes no test below may ever be handed
# on the `tenant` rung unless it asked for that URL by name.
OBJECTS = {
    f"{BASE}/m/1/characters/michael/IMG_1.jpg": b"account 1's michael",
    f"{BASE}/m/2/characters/michael/IMG_1.jpg": b"account 2's michael",
    f"{BASE}/m/shared/refs/0a1b2c.jpg": b"a bin image",
    FLAT_MICHAEL: b"the flat key every account shares",
    f"{BASE}/refs/0a1b2c.jpg": b"the bin's flat key",
    SOMEBODY_ELSES: b"somebody else's picture",
}


@pytest.fixture(autouse=True)
def no_photo_folders(tmp_path, monkeypatch):
    """The deployed posture: no photo folder on this machine (the bin is
    already pointed at an empty tmp dir by conftest's output roots)."""
    roots = {plural: tmp_path / plural for plural in asset_shelf.URL_ROOTS}
    monkeypatch.setattr(api, "_PHOTO_ROOTS", roots)
    monkeypatch.setattr(api, "CHARACTERS_DIR", roots["characters"])
    monkeypatch.setattr(api, "PROPS_DIR", roots["props"])
    monkeypatch.setattr(api, "LOCATIONS_DIR", roots["locations"])
    return roots


@pytest.fixture(autouse=True)
def fresh_listing_cache(monkeypatch):
    # nothing here is about the listing; a route that asks gets an empty one
    monkeypatch.setattr(storage, "list_keys", lambda prefix: [])
    storage.forget_listings()
    yield
    storage.forget_listings()


@pytest.fixture
def r2_on(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key123")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret123")
    monkeypatch.setenv("R2_BUCKET", "zpf-clips")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", BASE + "/")


@pytest.fixture
def tenant(monkeypatch, r2_on):
    monkeypatch.setenv("ZEROPAGE_MEDIA", "tenant")


@pytest.fixture
def legacy(monkeypatch, r2_on):
    monkeypatch.setenv("ZEROPAGE_MEDIA", "legacy")


@pytest.fixture
def bucket(monkeypatch):
    """The bucket, and every address the reader asked it for, in order."""
    asked = []

    def fetch(url):
        asked.append(url)
        return OBJECTS.get(url)

    monkeypatch.setattr(imagery, "fetch_image_bytes", fetch)
    return asked


# --- where the bucket holds a stored reference (asset_shelf.bucket_url) ------

def test_on_tenant_the_address_is_under_the_callers_own_keys(tenant):
    assert asset_shelf.bucket_url(MICHAEL, 1) == f"{BASE}/m/1/characters/michael/IMG_1.jpg"
    assert asset_shelf.bucket_url(MICHAEL, 2) == f"{BASE}/m/2/characters/michael/IMG_1.jpg"
    assert asset_shelf.bucket_url("/props/can/photo/front.png?thumb=1", 7) == (
        f"{BASE}/m/7/props/can/front.png")
    assert asset_shelf.bucket_url("/locations/garage/photo/plate.jpg", 7) == (
        f"{BASE}/m/7/locations/garage/plate.jpg")


def test_an_element_photo_with_no_account_has_no_address(tenant):
    """Two accounts can each have a `michael`; the name alone does not say
    whose is meant, and the flat key is the one string they would share."""
    for name in (MICHAEL, "/props/can/photo/front.png", "/locations/garage/photo/plate.jpg"):
        assert asset_shelf.bucket_url(name, None) is None
    # the bin is shared by design and needs nobody
    assert asset_shelf.bucket_url(BIN, None) == f"{BASE}/m/shared/refs/0a1b2c.jpg"
    assert asset_shelf.bucket_url(BIN, 2) == f"{BASE}/m/shared/refs/0a1b2c.jpg"


def test_on_legacy_the_address_is_the_flat_key_for_anyone(legacy):
    assert asset_shelf.bucket_url(MICHAEL, None) == FLAT_MICHAEL
    assert asset_shelf.bucket_url(MICHAEL, 2) == FLAT_MICHAEL
    assert asset_shelf.bucket_url(BIN, None) == f"{BASE}/refs/0a1b2c.jpg"


def test_what_is_not_a_stored_reference_of_ours_has_no_address(tenant):
    for url in ("", None, "/renders/nano/still.png", "/characters/../secrets/x.jpg",
                "data:image/png;base64,AAAA",
                # a stranger's URL whose path happens to look like one of ours
                SOMEBODY_ELSES, "https://cdn.example/refs/0a1b2c.jpg",
                # already an address in this bucket: fetched as it stands
                f"{BASE}/m/2/characters/michael/IMG_1.jpg"):
        assert asset_shelf.bucket_url(url, 1) is None, url


def test_with_r2_off_there_is_no_address(monkeypatch):
    monkeypatch.setenv("ZEROPAGE_MEDIA", "tenant")
    assert asset_shelf.bucket_url(MICHAEL, 1) is None
    assert asset_shelf.bucket_url(BIN, 1) is None


def test_a_url_a_row_kept_from_the_legacy_rung_reads_as_the_name_it_stands_for(tenant):
    """Rows written before the bucket moved carry the flat public URL. The
    photo is one prefix over now, under the account that owns it."""
    assert asset_shelf.bucket_url(FLAT_MICHAEL, 2) == (
        f"{BASE}/m/2/characters/michael/IMG_1.jpg")
    assert asset_shelf.bucket_url(f"{BASE}/refs/0a1b2c.jpg", None) == (
        f"{BASE}/m/shared/refs/0a1b2c.jpg")
    assert asset_shelf.bucket_url(FLAT_MICHAEL, None) is None


def test_on_signed_the_address_is_a_signature_over_the_same_key(monkeypatch, r2_on):
    monkeypatch.setenv("ZEROPAGE_MEDIA", "signed")
    monkeypatch.setattr(storage, "signed_url_for_key",
                        lambda key, ttl=None: f"https://s3.example/{key}?sig=1")
    assert asset_shelf.bucket_url(MICHAEL, 2) == (
        "https://s3.example/m/2/characters/michael/IMG_1.jpg?sig=1")
    assert asset_shelf.bucket_url(MICHAEL, None) is None


# --- the reader (api._photo_bytes) --------------------------------------------

def test_a_picked_face_is_read_from_the_callers_own_keys(tenant, bucket):
    assert api._photo_bytes(MICHAEL, 1) == b"account 1's michael"
    assert api._photo_bytes(MICHAEL, 2) == b"account 2's michael"
    # an account with no such photo gets nothing -- not a neighbour's, not the flat one
    assert api._photo_bytes(MICHAEL, 3) is None
    assert bucket == [f"{BASE}/m/{n}/characters/michael/IMG_1.jpg" for n in (1, 2, 3)]


def test_with_no_account_an_element_photo_reads_nothing_and_asks_for_nothing(tenant, bucket):
    assert api._photo_bytes(MICHAEL) is None
    assert api._photo_bytes(MICHAEL, None) is None
    assert bucket == []


def test_the_bin_is_read_from_the_shared_address(tenant, bucket):
    assert api._photo_bytes(BIN, 2) == b"a bin image"
    assert api._photo_bytes(BIN) == b"a bin image"
    assert set(bucket) == {f"{BASE}/m/shared/refs/0a1b2c.jpg"}


def test_a_file_on_this_machine_still_wins(tenant, bucket, no_photo_folders):
    folder = no_photo_folders["characters"] / "michael"
    folder.mkdir(parents=True)
    (folder / "IMG_1.jpg").write_bytes(b"off this disk")
    assert api._photo_bytes(MICHAEL, 1) == b"off this disk"
    assert api._photo_bytes(MICHAEL) == b"off this disk"
    assert bucket == []


def test_somebody_elses_url_is_fetched_exactly_as_it_was_given(tenant, bucket):
    assert api._photo_bytes(SOMEBODY_ELSES, 1) == b"somebody else's picture"
    theirs = f"{BASE}/m/2/characters/michael/IMG_1.jpg"
    assert api._photo_bytes(theirs, 2) == b"account 2's michael"
    assert bucket == [SOMEBODY_ELSES, theirs]


def test_a_flat_url_from_the_legacy_rung_is_read_under_the_callers_keys(tenant, bucket):
    assert api._photo_bytes(FLAT_MICHAEL, 2) == b"account 2's michael"
    assert bucket == [f"{BASE}/m/2/characters/michael/IMG_1.jpg"]


def test_a_url_the_bucket_cannot_answer_for_the_caller_is_still_tried_as_given(tenant, bucket):
    """What an absolute URL did before this is its last resort, not its
    first: the row said this address, so it is asked once the caller's own
    key has had nothing."""
    assert api._photo_bytes(FLAT_MICHAEL, 3) == b"the flat key every account shares"
    assert bucket == [f"{BASE}/m/3/characters/michael/IMG_1.jpg", FLAT_MICHAEL]


def test_on_legacy_a_name_is_read_from_the_flat_key_once(legacy, bucket):
    assert api._photo_bytes(MICHAEL) == b"the flat key every account shares"
    assert api._photo_bytes(FLAT_MICHAEL, 2) == b"the flat key every account shares"
    assert bucket == [FLAT_MICHAEL, FLAT_MICHAEL]          # never asked twice for one read


def test_with_r2_off_a_name_reads_nothing_as_before(monkeypatch, bucket):
    monkeypatch.setenv("ZEROPAGE_MEDIA", "tenant")
    assert api._photo_bytes(MICHAEL, 1) is None
    assert api._photo_bytes(BIN, 1) is None
    assert bucket == []


# --- the three doors ----------------------------------------------------------

def _picked(*names, account_id):
    form = FormData([("asset_photos", name) for name in names])
    return asyncio.run(api._collect_refs(form, account_id=account_id))


def test_the_composers_picks_reach_the_model_and_the_shot_keeps_their_names(
        tenant, bucket, monkeypatch):
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    image_refs, ref_urls, _videos = _picked(MICHAEL, BIN, account_id=2)
    assert [data for data, _mime, _label in image_refs] == [b"account 2's michael", b"a bin image"]
    # what goes ON the shot is still the name, never the address it was read from
    assert ref_urls == [MICHAEL, BIN]


def test_a_pick_nobody_can_be_asked_about_goes_on_the_shot_with_no_pixels(
        tenant, bucket, monkeypatch):
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    image_refs, ref_urls, _videos = _picked(MICHAEL, BIN, account_id=None)
    assert [data for data, _mime, _label in image_refs] == [b"a bin image"]
    assert ref_urls == [MICHAEL, BIN]


def test_every_door_that_reads_a_reference_says_whose_it_is():
    """A reference that cannot be read is skipped, never an error -- so a
    call that forgets the account fails in silence, on the deployed machine
    only. Held at the source: each call names the account."""
    needs = {"_collect_refs": 99, "_photo_bytes": 2, "_photos_from_urls": 3}
    tree = ast.parse(Path(api.__file__).read_text())
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call) and getattr(node.func, "id", None) in needs]
    assert {node.func.id for node in calls} == set(needs)
    for node in calls:
        named = any(k.arg == "account_id" for k in node.keywords)
        assert named or len(node.args) >= needs[node.func.id], (
            f"app/api.py:{node.lineno} calls {node.func.id} without the account")


WHO = {}


def _wait(client, job_id):
    for _ in range(300):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(.02)
    raise AssertionError("job never finished")


@pytest.fixture
def client(pg, monkeypatch, tenant):
    """Signed in as `mine`, one of two accounts that each have a michael."""
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    generative.init(pg)
    ledger.init(pg)
    render_assets.init(pg)
    outcomes.init(pg)
    WHO["mine"] = accounts.upsert_account("b-mine", "Mine", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("b-theirs", "Theirs", "#fff", dsn=pg)
    for who in ("mine", "theirs"):
        monkeypatch.setitem(OBJECTS, f"{BASE}/m/{WHO[who]}/characters/michael/IMG_1.jpg",
                            f"michael as {who} uploaded him".encode())
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "b-user"})
    monkeypatch.setattr(auth, "current_account", lambda request, user=None: {"slug": "b-mine"})
    monkeypatch.setattr(api, "_create_gate", lambda account_id: None)
    monkeypatch.setattr(api, "_to_jpeg", lambda raw: raw)
    jobs.clear_all_for_tests()
    app.dependency_overrides[auth.current_account_id] = lambda: WHO["mine"]
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)
    jobs.clear_all_for_tests()


def test_a_still_is_drawn_from_the_face_that_was_picked(client, bucket, monkeypatch):
    """/api/generate/run, the composer's still: the picked photo is on no
    disk here, and the model is handed the caller's own -- by the route,
    not by a stub of the reader."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr("src.shootgen.reference_block",
                        lambda spark=None, client=None, db_path=None: "REFS")
    monkeypatch.setattr(api, "_enhance_generate_prompt",
                        lambda gemini_client, prompt, **kw: f"ENHANCED[{prompt}]")
    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key=None: object())
    seen = []

    def draw(prompt, reference_image=None, db_path=None, **kw):
        seen.append((kw.get("account_id"), reference_image))
        return {"ok": True, "media_url": "/renders/frame.png"}

    monkeypatch.setattr("src.nano_banana.generate_from_prompt", draw)
    started = client.post("/api/generate/run", data={
        "prompt": "michael at the window", "output": "image", "asset_photos": [MICHAEL]})
    job = _wait(client, started.json()["job_id"])
    assert job["status"] == "done", job.get("error")
    ((account, references),) = seen
    assert account == WHO["mine"]
    assert [data for _label, data in references] == [b"michael as mine uploaded him"]
    assert bucket == [f"{BASE}/m/{WHO['mine']}/characters/michael/IMG_1.jpg"]


def test_make_element_from_a_stored_name_saves_the_callers_photo(
        client, bucket, monkeypatch, no_photo_folders):
    monkeypatch.setattr(api, "_mirror_photos_to_r2", lambda *a, **k: 0)
    monkeypatch.setattr(api, "describe_entity_photos",
                        lambda *a, **k: {"ok": False, "description": {}, "error": "no key"})
    monkeypatch.setattr(api, "ingest_asset_chunk",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    res = client.post("/api/assets/props",
                      data={"name": "His Jacket", "sheet": "0", "photo_urls": [MICHAEL]})
    assert res.status_code == 200, res.text
    assert res.json()["photos"] == 1
    (saved,) = (no_photo_folders["props"] / "his-jacket").iterdir()
    assert saved.read_bytes() == b"michael as mine uploaded him"


def test_an_effect_is_run_on_the_callers_own_photo(client, bucket, monkeypatch):
    monkeypatch.setattr(ledger, "credit_exempt", lambda account_id, dsn=None: False)
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    handed = []

    def as_image_url(value, **kw):
        handed.append((value, kw.get("account_id")))
        return "https://bucket.example/src.jpg"

    monkeypatch.setattr(fal, "as_image_url", as_image_url)
    monkeypatch.setattr(effects, "run", lambda *a, **k: {
        "ok": True, "media_url": "https://bucket.example/out.png", "asset_id": 9})
    body = {"effect": "remove-background", "sources": [MICHAEL]}
    price = client.post("/api/effects/quote", json=body).json()["credits"]
    job = _wait(client, client.post("/api/effects/run",
                                    json={**body, "expect_credits": price}).json()["job_id"])
    assert job["status"] == "done", job
    assert handed == [(b"michael as mine uploaded him", WHO["mine"])]
