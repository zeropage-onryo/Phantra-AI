"""
The photo routes' bucket fallback redirects to where the photo LIVES.

2026-10-11, found on the live site: opening an element drew a dead main
picture. `/characters/michael/photo/01-headshot.jpg` has no file on the
deployed machine, so the route answers a 302 into the bucket -- and that
302 was built as the flat `characters/michael/01-headshot.jpg`, a key
the bucket stopped holding once media moved to `m/<account>/...`
(src/media.py). The object was there all along, one prefix over.

What these hold: on `legacy` the redirect is the flat key it always was;
from `tenant` up it is the key of the account the SESSION names, the
bin's shared key for anyone, and nothing at all for an element photo
nobody is signed in to see. The account never comes from the path, so
no request can be redirected to another account's key.

Nothing here reaches the network: the bucket listing is faked at
storage.list_keys and a session is a real signed cookie over a faked
users table.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app import auth
from src import storage

BASE = "https://pub-abc123.r2.dev"

# who is signed in -> the accounts they belong to. `both` belongs to two;
# the tenant is the oldest (lowest id), which is what every /api route uses.
MEMBERS = {
    "mike": [{"id": 1, "slug": "phantra"}],
    "other": [{"id": 2, "slug": "second-studio"}],
    "both": [{"id": 3, "slug": "newer"}, {"id": 1, "slug": "phantra"}],
    "nobody": [],                      # signed in, no workspace
}

# the derivatives the bucket holds: account 1 has one for IMG_1 only
THUMBS = {
    "t/1/characters/": ["t/1/characters/michael/IMG_1.jpg"],
    "t/2/characters/": ["t/2/characters/michael/IMG_1.jpg"],
}


@pytest.fixture(autouse=True)
def fresh_listing_cache():
    storage.forget_listings()
    yield
    storage.forget_listings()


@pytest.fixture(autouse=True)
def no_photo_folders(tmp_path, monkeypatch):
    """The deployed posture: no photo folder on this machine."""
    monkeypatch.setattr(app_main, "LOCATIONS_DIR", tmp_path / "locations")
    monkeypatch.setattr(app_main, "CHARACTERS_DIR", tmp_path / "characters")
    monkeypatch.setattr(app_main, "PROPS_DIR", tmp_path / "props")
    return tmp_path


@pytest.fixture
def r2_on(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key123")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret123")
    monkeypatch.setenv("R2_BUCKET", "zpf-clips")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", BASE + "/")


@pytest.fixture
def listing(monkeypatch):
    calls = []

    def list_keys(prefix):
        calls.append(prefix)
        return list(THUMBS.get(prefix, []))

    monkeypatch.setattr(storage, "list_keys", list_keys)
    return calls


@pytest.fixture
def people(monkeypatch):
    """A users table and its memberships, read by the REAL session path:
    cookie -> auth.current_user -> auth.current_account_id."""
    monkeypatch.setenv("SESSION_SECRET", "photo-fallback-test")
    looked_up = []

    def get_user(uid, dsn=None):
        looked_up.append(uid)
        return {"id": uid} if uid in MEMBERS else None

    monkeypatch.setattr(auth.accounts, "get_user", get_user)
    monkeypatch.setattr(auth.accounts, "memberships",
                        lambda uid, dsn=None: list(MEMBERS.get(uid, [])))
    return looked_up


def _client(uid=None):
    client = TestClient(app_main.app, follow_redirects=False)
    if uid:
        client.cookies.set(auth.SESSION_COOKIE, auth._serializer().dumps({"uid": uid}))
    return client


def _where(response):
    assert response.status_code == 302, response.text
    return response.headers["location"]


# --- legacy: byte for byte what it was --------------------------------------

@pytest.fixture
def legacy(monkeypatch, r2_on):
    monkeypatch.setenv("PHANTRA_MEDIA", "legacy")


def test_on_legacy_the_redirect_is_the_flat_key_for_anyone(legacy, people, listing):
    anon = _client()
    assert _where(anon.get("/characters/michael/photo/IMG_1.jpg")) == (
        f"{BASE}/characters/michael/IMG_1.jpg")
    assert _where(anon.get("/props/ducati/photo/side.png")) == f"{BASE}/props/ducati/side.png"
    assert _where(anon.get("/locations/garage/photo/plate.jpg")) == (
        f"{BASE}/locations/garage/plate.jpg")
    assert _where(anon.get("/refs/0a1b2c.jpg")) == f"{BASE}/refs/0a1b2c.jpg"
    # nobody was looked up and nothing was listed to answer any of those
    assert people == [] and listing == []


def test_on_legacy_a_session_and_a_thumb_change_nothing(legacy, people, listing):
    response = _client("mike").get("/characters/michael/photo/IMG_1.jpg?thumb=1")
    assert _where(response) == f"{BASE}/characters/michael/IMG_1.jpg"
    assert "cache-control" not in response.headers
    assert people == [] and listing == []


# --- tenant: the caller's own key -------------------------------------------

@pytest.fixture
def tenant(monkeypatch, r2_on):
    monkeypatch.setenv("PHANTRA_MEDIA", "tenant")


def test_on_tenant_a_signed_in_account_is_sent_to_its_own_key(tenant, people, listing):
    mike = _client("mike")
    response = mike.get("/characters/michael/photo/01-headshot.jpg")
    assert _where(response) == f"{BASE}/m/1/characters/michael/01-headshot.jpg"
    # it differs per caller, so no shared cache may keep it
    assert response.headers["cache-control"] == "private, no-store"
    assert _where(mike.get("/characters/michael/photo/sheet.jpg")) == (
        f"{BASE}/m/1/characters/michael/sheet.jpg")
    assert _where(mike.get("/props/ducati/photo/side.png")) == f"{BASE}/m/1/props/ducati/side.png"
    assert _where(mike.get("/locations/garage/photo/plate.jpg")) == (
        f"{BASE}/m/1/locations/garage/plate.jpg")


def test_on_tenant_a_thumb_is_the_derivative_when_the_bucket_has_one(tenant, people, listing):
    mike = _client("mike")
    assert _where(mike.get("/characters/michael/photo/IMG_1.jpg?thumb=1")) == (
        f"{BASE}/t/1/characters/michael/IMG_1.jpg")
    # no derivative for this one: the master, a slow tile and not a dead one
    assert _where(mike.get("/characters/michael/photo/IMG_2.jpg?thumb=1")) == (
        f"{BASE}/m/1/characters/michael/IMG_2.jpg")
    # one listing answered both, and a full-size request never lists
    assert _where(mike.get("/characters/michael/photo/IMG_1.jpg")) == (
        f"{BASE}/m/1/characters/michael/IMG_1.jpg")
    assert listing == ["t/1/characters/"]


def test_a_failed_listing_hands_out_the_master(tenant, people, monkeypatch):
    def broken(prefix):
        raise RuntimeError("cloudflare is down")

    monkeypatch.setattr(storage, "list_keys", broken)
    assert _where(_client("mike").get("/characters/michael/photo/IMG_1.jpg?thumb=1")) == (
        f"{BASE}/m/1/characters/michael/IMG_1.jpg")


def test_on_tenant_nobody_signed_in_gets_no_element_photo(tenant, people, listing):
    """Two accounts can each have a `michael`; the path does not say
    whose. No session is no redirect -- and never the flat key."""
    for client in (_client(), _client("nobody"), _client("stranger")):
        for path in ("/characters/michael/photo/IMG_1.jpg",
                     "/characters/michael/photo/IMG_1.jpg?thumb=1",
                     "/props/ducati/photo/side.png",
                     "/locations/garage/photo/plate.jpg"):
            response = client.get(path)
            assert response.status_code == 404, path
            assert "location" not in response.headers
    garbage = TestClient(app_main.app, follow_redirects=False)
    garbage.cookies.set(auth.SESSION_COOKIE, "not.a.session")
    assert garbage.get("/characters/michael/photo/IMG_1.jpg").status_code == 404
    assert listing == []


def test_one_account_is_never_redirected_to_anothers_key(tenant, people, listing):
    """The same path, three people. Each lands in the prefix of the
    account their own session names, whatever they ask for."""
    path = "/characters/michael/photo/IMG_1.jpg"
    assert _where(_client("mike").get(path)) == f"{BASE}/m/1/characters/michael/IMG_1.jpg"
    assert _where(_client("other").get(path)) == f"{BASE}/m/2/characters/michael/IMG_1.jpg"
    assert _where(_client("other").get(path + "?thumb=1")) == (
        f"{BASE}/t/2/characters/michael/IMG_1.jpg")
    # a member of two acts as the tenant every /api route acts as: the oldest
    assert _where(_client("both").get(path)) == f"{BASE}/m/1/characters/michael/IMG_1.jpg"

    # nothing in the path can name another account's prefix
    other = _client("other")
    for attempt in ("/characters/m/photo/1", "/characters/..%2F..%2Fm%2F1/photo/IMG_1.jpg",
                    "/characters/michael/photo/..%2F..%2F..%2Fm%2F1%2Fcharacters%2Fmichael%2FIMG_1.jpg",
                    "/characters/michael/photo/IMG_1.jpg%3Fx=/m/1/"):
        response = other.get(attempt)
        assert "/m/1/" not in response.headers.get("location", ""), attempt
        assert "/t/1/" not in response.headers.get("location", ""), attempt


def test_on_tenant_the_bin_is_the_shared_key_for_anyone(tenant, people, listing):
    """`refs/` is shared by design (media.SHARED_ROOTS): one address,
    signed in or not, and nobody is looked up to build it."""
    for client in (_client(), _client("mike"), _client("other")):
        assert _where(client.get("/refs/0a1b2c.jpg")) == f"{BASE}/m/shared/refs/0a1b2c.jpg"
    assert people == [] and listing == []


def test_no_redirect_on_any_rung_is_a_flat_key_above_legacy(tenant, people, listing):
    """The flat keys are gone from the bucket. Whatever is asked, by
    whoever, a redirect from `tenant` up starts with m/ or t/."""
    paths = ("/characters/michael/photo/IMG_1.jpg", "/characters/michael/photo/IMG_1.jpg?thumb=1",
             "/props/ducati/photo/side.png", "/locations/garage/photo/plate.jpg",
             "/refs/0a1b2c.jpg")
    for uid in (None, "mike", "other", "both", "nobody"):
        for path in paths:
            where = _client(uid).get(path).headers.get("location")
            if where is not None:
                assert where.startswith((f"{BASE}/m/", f"{BASE}/t/")), (uid, path, where)


# --- signed: a signature for the caller's key, or nothing --------------------

def test_on_signed_the_signature_is_for_the_callers_own_key(monkeypatch, r2_on, people, listing):
    monkeypatch.setenv("PHANTRA_MEDIA", "signed")
    signed = []

    def sign(key, ttl=None):
        signed.append(key)
        return f"https://acct123.r2.cloudflarestorage.com/zpf-clips/{key}?X-Amz-Signature=abc"

    monkeypatch.setattr(storage, "signed_url_for_key", sign)
    where = _where(_client("other").get("/characters/michael/photo/IMG_1.jpg"))
    assert where.startswith("https://acct123.r2.cloudflarestorage.com/zpf-clips/m/2/characters/")
    assert _client().get("/characters/michael/photo/IMG_1.jpg").status_code == 404
    assert signed == ["m/2/characters/michael/IMG_1.jpg"]


# --- what did not change ------------------------------------------------------

def test_a_file_on_this_machine_is_served_and_nobody_is_looked_up(
        tenant, people, listing, no_photo_folders):
    folder = no_photo_folders / "characters" / "michael"
    folder.mkdir(parents=True)
    (folder / "local.jpg").write_bytes(b"jpeg bytes")
    response = _client("mike").get("/characters/michael/photo/local.jpg")
    assert response.status_code == 200 and response.content == b"jpeg bytes"
    assert people == [] and listing == []


def test_with_no_bucket_a_missing_photo_is_a_404(monkeypatch, people, listing):
    monkeypatch.setenv("PHANTRA_MEDIA", "tenant")
    assert _client("mike").get("/characters/michael/photo/IMG_1.jpg").status_code == 404
    assert _client("mike").get("/refs/0a1b2c.jpg").status_code == 404
    assert people == [] and listing == []


def test_a_name_that_is_not_a_photo_is_never_redirected(tenant, people, listing):
    mike = _client("mike")
    assert mike.get("/characters/michael/photo/notes.txt").status_code == 404
    assert mike.get("/characters/..%2F..%2Fetc/photo/passwd").status_code == 404
