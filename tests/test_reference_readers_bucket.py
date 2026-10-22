"""
The keyframe stage, the timeline planner, the writer's image refs and a
clip's start frame read a stored reference NAME from the bucket when this
machine has no file for it.

2026-10-22. The readers handed `resolve_photo` (imagery.image_bytes_for_gemini
for Gemini, fal.as_image_url for a clip) read only this machine's disk. On
Fly the element folders are gitignored and dockerignored, so a scene held to
an element photo had its keyframes, its timeline plan and its clips drawn
from the prompt alone. tests/test_photo_bytes_bucket.py pinned the same rule
for app/api._photo_bytes in October; these are the other two readers, held
to it: the caller's own keys, never the flat one every account shares; an
element photo with no account gets nothing; disk still wins; somebody
else's URL is used exactly as it was given.

Nothing here reaches the network: the bucket is a dict behind
imagery.fetch_image_bytes, and fal.as_image_url only returns addresses.
"""
import ast
from pathlib import Path

import pytest

from src import asset_shelf, fal, imagery, scene_chain, storage, timeline

BASE = "https://pub-abc123.r2.dev"
MICHAEL = "/characters/michael/photo/IMG_1.jpg"
FLAT_MICHAEL = f"{BASE}/characters/michael/IMG_1.jpg"
STILL = "/renders/nano/c375-20260918-154220.png"
SOMEBODY_ELSES = "https://cdn.example/props/can/front.jpg"
OBJECTS = {
    f"{BASE}/m/1/characters/michael/IMG_1.jpg": b"account 1's michael",
    f"{BASE}/m/2/characters/michael/IMG_1.jpg": b"account 2's michael",
    FLAT_MICHAEL: b"the flat key every account shares",
    f"{BASE}/m/1/renders/nano/c375-20260918-154220.png": b"account 1's still",
    SOMEBODY_ELSES: b"somebody else's picture",
}


@pytest.fixture(autouse=True)
def deployed(tmp_path, monkeypatch):
    """Fly's posture: R2 on, tenant keys, no photo folder on this machine."""
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key123")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret123")
    monkeypatch.setenv("R2_BUCKET", "zpf-clips")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", BASE + "/")
    monkeypatch.setenv("PHANTRA_MEDIA", "tenant")
    monkeypatch.setattr(storage, "list_keys", lambda prefix: [])
    storage.forget_listings()
    roots = {plural: tmp_path / plural for plural in asset_shelf.URL_ROOTS}
    monkeypatch.setattr(asset_shelf, "photo_roots", lambda: roots)
    monkeypatch.setattr(imagery, "render_bytes", lambda path: None)
    monkeypatch.setattr(fal, "_local_render_bytes", lambda path: None)
    yield roots
    storage.forget_listings()


@pytest.fixture
def bucket(monkeypatch):
    asked = []

    def fetch(url):
        asked.append(url)
        return OBJECTS.get(url)

    monkeypatch.setattr(imagery, "fetch_image_bytes", fetch)
    return asked


def read(value, account_id=None):
    return imagery.image_bytes_for_gemini(value, resolve_photo=asset_shelf.resolve_photo,
                                          account_id=account_id)


# --- the Gemini reader --------------------------------------------------------

def test_an_element_photo_is_read_from_the_callers_own_keys(bucket):
    assert read(MICHAEL, 1) == b"account 1's michael"
    assert read(MICHAEL, 2) == b"account 2's michael"
    assert read(MICHAEL, 3) is None                       # not a neighbour's, not the flat one
    assert bucket == [f"{BASE}/m/{n}/characters/michael/IMG_1.jpg" for n in (1, 2, 3)]


def test_with_no_account_an_element_photo_reads_nothing_and_asks_for_nothing(bucket):
    assert read(MICHAEL) is None
    assert bucket == []


def test_a_file_on_this_machine_still_wins(bucket, deployed):
    folder = deployed["characters"] / "michael"
    folder.mkdir(parents=True)
    (folder / "IMG_1.jpg").write_bytes(b"off this disk")
    assert read(MICHAEL, 1) == b"off this disk"
    assert bucket == []


def test_a_render_this_machine_lost_is_read_under_the_callers_keys(bucket):
    assert read(STILL, 1) == b"account 1's still"
    assert read(STILL) is None
    assert bucket == [f"{BASE}/m/1/renders/nano/c375-20260918-154220.png"]


def test_urls_are_read_where_the_bucket_holds_them_or_as_given(bucket):
    assert read(FLAT_MICHAEL, 2) == b"account 2's michael"     # a legacy row's flat URL
    assert read(SOMEBODY_ELSES, 1) == b"somebody else's picture"
    assert bucket == [f"{BASE}/m/2/characters/michael/IMG_1.jpg", SOMEBODY_ELSES]


def test_a_name_read_from_the_bucket_is_turned_upright(bucket, monkeypatch):
    turned = []
    monkeypatch.setattr(imagery, "upright", lambda data: turned.append(data) or b"upright")
    assert read(MICHAEL, 1) == b"upright"
    assert read(SOMEBODY_ELSES, 1) == b"somebody else's picture"   # a URL handed in: as before
    assert turned == [b"account 1's michael"]


def test_with_r2_off_a_name_reads_nothing_as_before(bucket, monkeypatch):
    monkeypatch.delenv("R2_ACCOUNT_ID")
    assert read(MICHAEL, 1) is None
    assert bucket == []


# --- the clip's start frame (fal) ----------------------------------------------

def test_a_clip_is_sent_the_callers_bucket_address_for_a_name():
    def url(value, account_id=None):
        return fal.as_image_url(value, resolve_photo=asset_shelf.resolve_photo,
                                account_id=account_id)
    assert url(MICHAEL, 1) == f"{BASE}/m/1/characters/michael/IMG_1.jpg"
    assert url(MICHAEL, 2) == f"{BASE}/m/2/characters/michael/IMG_1.jpg"
    assert url(MICHAEL) is None
    assert url(STILL, 1) == f"{BASE}/m/1/renders/nano/c375-20260918-154220.png"
    assert url(FLAT_MICHAEL, 2) == f"{BASE}/m/2/characters/michael/IMG_1.jpg"
    assert url(SOMEBODY_ELSES, 1) == SOMEBODY_ELSES


def test_a_clip_with_r2_off_gets_no_address_as_before(monkeypatch):
    monkeypatch.delenv("R2_ACCOUNT_ID")
    assert fal.as_image_url(MICHAEL, resolve_photo=asset_shelf.resolve_photo,
                            account_id=1) is None


# --- the doors carry the account to the reader ---------------------------------

def test_the_writer_and_the_planner_see_the_callers_photo(bucket):
    refs = scene_chain.as_image_refs([MICHAEL], account_id=1)
    assert [r[0] for r in refs] == [b"account 1's michael"]
    assert scene_chain.as_image_refs([MICHAEL]) == []
    parts = timeline._reference_contents([MICHAEL], asset_shelf.resolve_photo, 2)
    assert len(parts) == 2 and parts[1].inline_data.data == b"account 2's michael"


def test_every_reader_call_in_a_door_says_whose_it_is():
    """A call to the Gemini reader with no account_id is how a door goes
    back to reading this machine's disk only. The one allowed is the
    content graph's writer, which runs by hand with no account at all."""
    root = Path(__file__).resolve().parent.parent
    missing = []
    for rel in ("src/scene_chain.py", "src/timeline.py", "src/imagery.py",
                "app/workflow_runner.py", "app/api.py"):
        tree = ast.parse((root / rel).read_text())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "attr", getattr(node.func, "id", None))
                    == "image_bytes_for_gemini"
                    and not any(k.arg == "account_id" for k in node.keywords)):
                missing.append(f"{rel}:{node.lineno}")
    assert missing == []
