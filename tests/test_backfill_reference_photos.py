"""ops/backfill_reference_photos_r2.py writes where the media rung READS
(docs/BACKLOG.md #25, 2026-10-11).

It used to write the flat keys -- `characters/<slug>/<file>` -- on every
rung. From `tenant` up the studio lists `m/<account>/characters/...`, so
a photo dropped into a folder by hand and backfilled landed where
nothing per-account looked.

Two halves, and the first is the one not to break:

  legacy          byte for byte what it was: every file, flat keys, no
                  derivative, no flag, nothing read from the database.
  tenant, signed  the element folders go to the ONE account the machine
                  names (ZEROPAGE_FOLDER_ACCOUNT), through media.mirror,
                  with the 480px derivative; data/refs to the shared
                  bin; a machine that names nobody is refused the
                  folders rather than given a guessed owner; and a run
                  is a report until --write.

A real throwaway database, a bucket that is a dict, folders in tmp.
Nothing touches the network.
"""
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from ops import backfill_reference_photos_r2 as backfill
from src import accounts, asset_shelf, media, refbin, storage

PUBLIC = "https://pub.example"
SECRET = "r2-secret-do-not-print"
ACCESS = "r2-access-key-do-not-print"


def _image(fmt: str = "JPEG", colour=(200, 30, 30)) -> bytes:
    """A real, small image: the derivative is made by decoding it."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), colour).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def disk(tmp_path, monkeypatch):
    """The three element folders and the bin, in tmp, as a Mac has them:
    photos, a PNG, and the two things that are not photos."""
    dirs = {kind: tmp_path / f"{kind}s" for kind in ("character", "prop", "location")}
    refs = tmp_path / "refs"
    monkeypatch.setattr(asset_shelf, "PHOTO_DIRS", dirs)
    monkeypatch.setattr(refbin, "REFS_DIR", refs)

    files = {
        dirs["character"] / "me" / "photo.jpg": _image(),
        dirs["character"] / "me" / "sheet.jpg": _image(colour=(30, 30, 200)),
        dirs["character"] / "me" / ".DS_Store": b"finder",
        dirs["prop"] / "can" / "front.png": _image("PNG"),
        dirs["prop"] / "can" / "notes.txt": b"the orange one",
        dirs["location"] / "loft" / "wide.JPG": _image(),
        refs / "0a1b2c.jpg": _image(colour=(30, 200, 30)),
    }
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    # a folder inside an element folder is walked by neither pass
    (dirs["character"] / "me" / "_extra").mkdir()
    (dirs["character"] / "me" / "_extra" / "more.jpg").write_bytes(_image())
    return {"dirs": dirs, "refs": refs, "files": files}


@pytest.fixture
def bucket(monkeypatch):
    """R2 configured, as a dict: what was uploaded, under which key and
    with which content type. No boto3 call is made. The rung is the
    test's to set."""
    for name, value in (("R2_ACCOUNT_ID", "acct"), ("R2_ACCESS_KEY_ID", ACCESS),
                        ("R2_SECRET_ACCESS_KEY", SECRET), ("R2_BUCKET", "zpf"),
                        ("R2_PUBLIC_BASE_URL", PUBLIC + "/")):
        monkeypatch.setenv(name, value)
    held: dict = {}
    calls = {"upload_file": [], "upload_bytes": [], "list_keys": [], "fail": set()}

    def upload_file(path, key=None, content_type=None):
        calls["upload_file"].append((key, content_type))
        if key in calls["fail"]:
            raise RuntimeError("the put was refused")
        held[key] = Path(path).read_bytes()
        storage._note_uploaded(key)
        return f"{PUBLIC}/{key}"

    def upload_bytes(data, key, content_type=None):
        calls["upload_bytes"].append((key, content_type))
        held[key] = bytes(data)
        storage._note_uploaded(key)
        return f"{PUBLIC}/{key}"

    def list_keys(prefix=""):
        calls["list_keys"].append(prefix)
        return [k for k in held if k.startswith(prefix)]

    monkeypatch.setattr(storage, "upload_file", upload_file)
    monkeypatch.setattr(storage, "upload_bytes", upload_bytes)
    monkeypatch.setattr(storage, "list_keys", list_keys)
    storage.forget_listings()
    yield SimpleNamespace(held=held, calls=calls)
    storage.forget_listings()


@pytest.fixture
def studios(pg, monkeypatch):
    """Two accounts on one database: the Mac's own, and somebody else's
    that is OLDER -- so "the oldest account" is the wrong guess."""
    accounts.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    other = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    mine = accounts.upsert_account("zeropage", "Zero Page Films", "#8b5cf6", dsn=pg)
    assert other < mine
    asset_shelf._OWNER_HITS.clear()
    yield {"mine": mine, "other": other, "dsn": pg}
    asset_shelf._OWNER_HITS.clear()


def _no_database(monkeypatch):
    """Any read of the accounts table fails the test."""
    def touched(*args, **kwargs):
        raise AssertionError("this run must not read the database")
    monkeypatch.setattr(accounts, "resolve_account", touched)
    monkeypatch.setattr(accounts, "slug_of", touched)


def _rung(monkeypatch, rung: str, owner: str = "") -> None:
    monkeypatch.setenv("ZEROPAGE_MEDIA", rung)
    if owner:
        monkeypatch.setenv("ZEROPAGE_FOLDER_ACCOUNT", owner)
    asset_shelf._OWNER_HITS.clear()


# --------------------------------------------------------------------------
# legacy: byte for byte what it was
# --------------------------------------------------------------------------

LEGACY_KEYS = [                     # the order the old script walked them in
    "refs/0a1b2c.jpg",
    "characters/me/.DS_Store",
    "characters/me/photo.jpg",
    "characters/me/sheet.jpg",
    "props/can/front.png",
    "props/can/notes.txt",
    "locations/loft/wide.JPG",
]


def test_legacy_is_what_it_always_was(disk, bucket, monkeypatch, capsys):
    """Every file, the flat key, `image/jpeg`, one line each, and the
    summary -- with a folder account named and the database off limits,
    because on `legacy` neither is asked."""
    _rung(monkeypatch, "legacy", owner="zeropage")
    _no_database(monkeypatch)

    assert backfill.main([]) == 0

    assert bucket.calls["upload_file"] == [(k, "image/jpeg") for k in LEGACY_KEYS]
    assert bucket.calls["upload_bytes"] == []           # no derivative
    assert bucket.calls["list_keys"] == []              # and no listing
    assert sorted(bucket.held) == sorted(LEGACY_KEYS)
    assert capsys.readouterr().out == "".join(
        f"  OK   {k} -> {PUBLIC}/{k}\n" for k in LEGACY_KEYS
    ) + "\n7/7 photos uploaded\n"


def test_legacy_is_the_default_rung_and_ignores_the_flag(disk, bucket, monkeypatch, capsys):
    """No ZEROPAGE_MEDIA at all, or a typo in it, is `legacy`; and
    --write there is what a bare run already does."""
    for rung, argv in ((None, []), ("tennant", []), ("legacy", ["--write"])):
        bucket.held.clear()
        if rung is None:
            monkeypatch.delenv("ZEROPAGE_MEDIA", raising=False)
        else:
            monkeypatch.setenv("ZEROPAGE_MEDIA", rung)
        assert backfill.main(argv) == 0
        assert sorted(bucket.held) == sorted(LEGACY_KEYS)
        assert capsys.readouterr().out.endswith("\n7/7 photos uploaded\n")


def test_legacy_reports_a_failed_upload_as_it_did(disk, bucket, monkeypatch, capsys):
    _rung(monkeypatch, "legacy")
    bucket.calls["fail"].add("props/can/front.png")

    assert backfill.main([]) == 2

    out = capsys.readouterr().out
    assert "  FAIL props/can/front.png: RuntimeError: the put was refused\n" in out
    assert out.endswith("\n6/7 photos uploaded, 1 failed\n")


def test_unconfigured_is_the_same_one_line(disk, monkeypatch, capsys):
    """On any rung: no bucket, nothing to do, exit 1."""
    for rung in ("legacy", "tenant"):
        monkeypatch.setenv("ZEROPAGE_MEDIA", rung)
        assert backfill.main(["--write"]) == 1
        assert capsys.readouterr().out == (
            "R2 is not configured (see ops/r2-setup.md) -- nothing to do.\n")


# --------------------------------------------------------------------------
# tenant: the account's own keys, and the derivative
# --------------------------------------------------------------------------

def _mine(studios) -> list:
    a = studios["mine"]
    return [f"m/{a}/characters/me/photo.jpg", f"m/{a}/characters/me/sheet.jpg",
            f"m/{a}/props/can/front.png", f"m/{a}/locations/loft/wide.JPG"]


SHARED = "m/shared/refs/0a1b2c.jpg"


@pytest.mark.parametrize("rung", ["tenant", "signed"])
def test_a_write_lands_where_the_rung_reads(disk, bucket, studios, monkeypatch, capsys, rung):
    """The account's keys, the shared bin, a derivative beside each --
    and no flat key, which is where it all went before."""
    _rung(monkeypatch, rung, owner="zeropage")
    a = studios["mine"]

    assert backfill.main(["--write"]) == 0

    dirs = disk["dirs"]
    masters = {                                         # key -> the file it is
        f"m/{a}/characters/me/photo.jpg": dirs["character"] / "me" / "photo.jpg",
        f"m/{a}/characters/me/sheet.jpg": dirs["character"] / "me" / "sheet.jpg",
        f"m/{a}/props/can/front.png": dirs["prop"] / "can" / "front.png",
        f"m/{a}/locations/loft/wide.JPG": dirs["location"] / "loft" / "wide.JPG",
        SHARED: disk["refs"] / "0a1b2c.jpg",
    }
    thumbs = ["t" + key[1:] for key in masters]
    assert sorted(bucket.held) == sorted([*masters, *thumbs])
    for key, source in masters.items():
        assert bucket.held[key] == source.read_bytes()
    for key in thumbs:                                  # a JPEG, from a PNG too
        assert bucket.held[key][:3] == b"\xff\xd8\xff"

    # ... which is where the studio's listing looks, for that account only
    storage.forget_listings()
    assert asset_shelf.r2_photo_urls("character", "me", a) == [
        "/characters/me/photo/photo.jpg", "/characters/me/photo/sheet.jpg"]
    assert asset_shelf.r2_photo_urls("prop", "can", a) == ["/props/can/photo/front.png"]
    assert asset_shelf.r2_photo_urls("character", "me", studios["other"]) == []
    assert media.master_key("/refs/0a1b2c.jpg", studios["other"]) == SHARED

    out = capsys.readouterr().out
    assert f"belong to account {a} (zeropage)" in out
    assert f"  OK   m/{a}/characters/me/photo.jpg\n" in out
    assert "\n5/5 photos uploaded\n" in out
    assert "5/5 have a 480px derivative under t/" in out
    assert "2 other files in the element folders: not a photo, left." in out


def test_the_owner_can_be_named_by_id(disk, bucket, studios, monkeypatch):
    _rung(monkeypatch, "tenant", owner=str(studios["mine"]))
    assert backfill.main(["--write"]) == 0
    assert set(_mine(studios)) <= set(bucket.held)


def test_a_bare_run_is_a_report(disk, bucket, studios, monkeypatch, capsys):
    """Nothing is uploaded until --write, and the report names whose
    keys, how many, and which are not in the bucket yet."""
    _rung(monkeypatch, "tenant", owner="zeropage")
    a = studios["mine"]
    bucket.held[f"m/{a}/characters/me/photo.jpg"] = b"already there"

    assert backfill.main([]) == 0

    assert list(bucket.held) == [f"m/{a}/characters/me/photo.jpg"]
    assert bucket.calls["upload_file"] == bucket.calls["upload_bytes"] == []
    out = capsys.readouterr().out
    assert f"belong to account {a} (zeropage), by ZEROPAGE_FOLDER_ACCOUNT." in out
    assert "      1  m/shared/refs/   (1 not in the bucket yet)\n" in out
    assert f"      2  m/{a}/characters/   (1 not in the bucket yet)\n" in out
    assert f"    new  m/{a}/characters/me/sheet.jpg\n" in out
    assert f"    new  m/{a}/characters/me/photo.jpg\n" not in out
    assert "\n5 photos to send, 4 not in the bucket yet\n" in out
    assert "report only -- re-run with --write to upload." in out


def test_a_report_stands_when_the_bucket_cannot_be_listed(
        disk, bucket, studios, monkeypatch, capsys):
    """It then cannot say which photos are new, and says so -- on
    stderr, with the counts it does have on stdout."""
    _rung(monkeypatch, "tenant", owner="zeropage")

    class ClientError(Exception):                      # botocore's shape
        response = {"Error": {"Code": "AccessDenied", "Message": f"key {ACCESS} may not list"}}

    def refused(prefix=""):
        raise ClientError(f"AccessDenied for {ACCESS}")

    monkeypatch.setattr(storage, "list_keys", refused)

    assert backfill.main([]) == 0

    said = capsys.readouterr()
    assert "note: the bucket could not be listed (ClientError: AccessDenied)" in said.err
    assert ACCESS not in said.err + said.out            # its code, never its text
    assert f"      2  m/{studios['mine']}/characters/\n" in said.out
    assert "\n5 photos to send\n" in said.out
    assert "not in the bucket yet" not in said.out
    capsys.readouterr()
    assert backfill.main(["--write"]) == 0              # and a write still goes
    assert "\n5/5 photos uploaded\n" in capsys.readouterr().out


def test_a_second_run_sends_everything_again(disk, bucket, studios, monkeypatch, capsys):
    """Re-runnable, and it skips nothing: a file replaced under the same
    name on disk replaces the object."""
    _rung(monkeypatch, "tenant", owner="zeropage")
    assert backfill.main(["--write"]) == 0
    first = dict(bucket.held)
    redrawn = _image(colour=(1, 2, 3))
    (disk["dirs"]["character"] / "me" / "sheet.jpg").write_bytes(redrawn)

    assert backfill.main(["--write"]) == 0

    key = f"m/{studios['mine']}/characters/me/sheet.jpg"
    assert sorted(bucket.held) == sorted(first)
    assert bucket.held[key] == redrawn != first[key]
    capsys.readouterr()
    assert backfill.main([]) == 0                       # and now nothing is new
    assert "\n5 photos to send, 0 not in the bucket yet\n" in capsys.readouterr().out


def test_a_failed_upload_is_counted_and_the_rest_go(disk, bucket, studios, monkeypatch, capsys):
    _rung(monkeypatch, "tenant", owner="zeropage")
    lost = f"m/{studios['mine']}/props/can/front.png"
    bucket.calls["fail"].add(lost)

    assert backfill.main(["--write"]) == 2

    assert lost not in bucket.held and "t" + lost[1:] not in bucket.held
    assert f"m/{studios['mine']}/locations/loft/wide.JPG" in bucket.held
    out = capsys.readouterr().out
    assert f"  FAIL {lost}" in out
    assert "\n4/5 photos uploaded, 1 failed\n" in out


def test_a_photo_that_cannot_be_decoded_is_said_to_have_no_derivative(
        disk, bucket, studios, monkeypatch, capsys):
    """media.mirror sends the master and makes no derivative, silently."""
    _rung(monkeypatch, "tenant", owner="zeropage")
    (disk["dirs"]["prop"] / "can" / "front.png").write_bytes(b"not an image at all")

    assert backfill.main(["--write"]) == 0

    a = studios["mine"]
    assert f"m/{a}/props/can/front.png" in bucket.held
    assert f"t/{a}/props/can/front.png" not in bucket.held
    out = capsys.readouterr().out
    assert "4/5 have a 480px derivative under t/" in out
    assert "    none for  props/can/front.png\n" in out


# --------------------------------------------------------------------------
# an owner is never guessed
# --------------------------------------------------------------------------

def _element_keys(bucket) -> list:
    return [k for k in bucket.held if "/refs/" not in k]


@pytest.mark.parametrize("argv", [[], ["--write"]])
def test_a_machine_that_names_nobody_is_refused_the_folders(
        disk, bucket, studios, monkeypatch, capsys, argv):
    """Not the oldest account, not any account: the folders stay where
    they are, the reason is said, and the exit code is not a pass. The
    bin has no owner to get wrong and still goes."""
    _rung(monkeypatch, "tenant")
    _no_database(monkeypatch)                           # nobody is looked up

    assert backfill.main(argv) == 3

    assert _element_keys(bucket) == []
    assert (SHARED in bucket.held) is bool(argv)
    out = capsys.readouterr().out
    assert "REFUSED  the element folders: 4 photos under characters/, props/, locations/." in out
    assert "1 photo to send" in out if not argv else "\n1/1 photos uploaded\n" in out
    assert "other file" not in out                      # the folders were not walked for sending
    assert "this machine names no folder account (ZEROPAGE_FOLDER_ACCOUNT is unset)" in out
    assert "ZEROPAGE_FOLDER_ACCOUNT=<the account's slug or id>" in out
    assert f"m/{studios['other']}/" not in out and f"m/{studios['mine']}/" not in out


def test_a_name_no_account_has_is_refused(disk, bucket, studios, monkeypatch, capsys):
    _rung(monkeypatch, "tenant", owner="zeropge")

    assert backfill.main(["--write"]) == 3

    assert _element_keys(bucket) == []
    out = capsys.readouterr().out
    assert "ZEROPAGE_FOLDER_ACCOUNT=zeropge: no account 'zeropge'" in out
    assert "The element folders were NOT uploaded" in out


def test_an_id_no_account_has_is_refused(disk, bucket, studios, monkeypatch, capsys):
    _rung(monkeypatch, "tenant", owner="987654")

    assert backfill.main(["--write"]) == 3

    assert _element_keys(bucket) == []
    assert "ZEROPAGE_FOLDER_ACCOUNT=987654 names no account" in capsys.readouterr().out


def test_a_name_the_studio_would_not_match_is_refused(disk, bucket, studios, monkeypatch, capsys):
    """`Zeropage` finds the row (the lookup lowercases) but is NOT how
    asset_shelf.folder_is_store reads the folders, which matches the
    slug exactly: uploading would put the photos under keys whose owner
    the studio does not think the folder belongs to."""
    _rung(monkeypatch, "tenant", owner="Zeropage")
    assert asset_shelf.folder_is_store(studios["mine"]) is False

    assert backfill.main(["--write"]) == 3

    assert _element_keys(bucket) == []
    assert "is not how the studio would read it" in capsys.readouterr().out


def test_no_element_photos_means_nobody_to_name(disk, bucket, monkeypatch, capsys):
    """The deployment: no folders, nobody named. The bin goes up and
    that is a clean run -- there was nothing to refuse."""
    import shutil
    for directory in disk["dirs"].values():
        shutil.rmtree(directory)
    _rung(monkeypatch, "tenant")
    _no_database(monkeypatch)

    assert backfill.main(["--write"]) == 0

    assert sorted(bucket.held) == [SHARED, "t" + SHARED[1:]]
    assert "REFUSED" not in capsys.readouterr().out


# --------------------------------------------------------------------------
# nothing printed is a credential
# --------------------------------------------------------------------------

def test_a_database_error_is_named_by_type_only(disk, bucket, monkeypatch, capsys):
    """A driver's message can quote the connection string."""
    _rung(monkeypatch, "tenant", owner="zeropage")
    dsn = "postgresql://postgres:hunter2@db.example:5432/postgres"
    monkeypatch.setenv("DATABASE_URL", dsn)

    def down(slug=None, dsn_=None):
        raise ConnectionError(f"could not connect with {dsn}")

    monkeypatch.setattr(accounts, "resolve_account", down)

    assert backfill.main(["--write"]) == 3

    said = "".join(capsys.readouterr())
    assert "did not answer (ConnectionError)" in said
    assert "hunter2" not in said and "db.example" not in said


@pytest.mark.parametrize("argv", [[], ["--write"]])
def test_a_per_account_run_prints_keys_never_addresses(
        disk, bucket, studios, monkeypatch, capsys, argv):
    """Under `signed` an address carries a signature. What is printed is
    the key; and neither R2 secret nor the DSN, on any path."""
    _rung(monkeypatch, "signed", owner="zeropage")
    monkeypatch.setattr(storage, "signed_url_for_key",
                        lambda key, ttl=None: f"{PUBLIC}/{key}?X-Amz-Signature=abc")

    assert backfill.main(argv) == 0

    said = "".join(capsys.readouterr())
    for secret in ("http", "X-Amz", SECRET, ACCESS, studios["dsn"]):
        assert secret not in said
