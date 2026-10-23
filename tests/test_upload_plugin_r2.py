"""ops/upload_plugin_r2.py puts a panel's release build under
site/downloads/<plugin>/<version>/ (docs/tasks/task-plugin-repos.md, Part 2).

A report until --write; never an overwrite (a new build is a new version);
never a file whose name does not say which panel and which version it is.
A bucket that is a dict; nothing touches the network.
"""
import hashlib

import pytest

from ops import upload_plugin_r2 as up
from src import storage


@pytest.fixture
def bucket(monkeypatch):
    keys: dict[str, tuple[bytes, str | None]] = {}
    monkeypatch.setattr(storage, "configured", lambda: True)
    monkeypatch.setattr(storage, "list_keys", lambda prefix="": [k for k in keys if k.startswith(prefix)])

    def upload_file(path, key=None, content_type=None):
        keys[key] = (path.read_bytes(), content_type)
        return f"https://media.example/{key}"

    def upload_bytes(data, key, content_type=None):
        keys[key] = (data, content_type)
        return f"https://media.example/{key}"

    monkeypatch.setattr(storage, "upload_file", upload_file)
    monkeypatch.setattr(storage, "upload_bytes", upload_bytes)
    return keys


def build(tmp_path, name="phantra-resolve-plugin-0.1.0.pkg", data=b"PK release"):
    f = tmp_path / name
    f.write_bytes(data)
    return f


def test_a_run_without_write_reports_and_uploads_nothing(tmp_path, bucket, capsys):
    f = build(tmp_path)
    assert up.main([str(f), "--plugin", "resolve", "--version", "0.1.0"]) == 0
    out = capsys.readouterr().out
    assert hashlib.sha256(b"PK release").hexdigest() in out
    assert "site/downloads/resolve/0.1.0/phantra-resolve-plugin-0.1.0.pkg" in out
    assert "report only" in out
    assert bucket == {}


def test_write_uploads_the_build_and_its_checksum_beside_it(tmp_path, bucket):
    f = build(tmp_path)
    assert up.main([str(f), "--plugin", "resolve", "--version", "0.1.0", "--write"]) == 0
    prefix = "site/downloads/resolve/0.1.0/"
    assert bucket[prefix + "phantra-resolve-plugin-0.1.0.pkg"] == (b"PK release", "application/octet-stream")
    sums, kind = bucket[prefix + "SHA256SUMS"]
    assert sums.decode() == f"{hashlib.sha256(b'PK release').hexdigest()}  phantra-resolve-plugin-0.1.0.pkg\n"
    assert kind.startswith("text/plain")


@pytest.mark.parametrize("already", ["phantra-resolve-plugin-0.1.0.pkg", "SHA256SUMS"])
def test_an_existing_release_is_never_overwritten(tmp_path, bucket, capsys, already):
    bucket[f"site/downloads/resolve/0.1.0/{already}"] = (b"the old build", None)
    f = build(tmp_path)
    assert up.main([str(f), "--plugin", "resolve", "--version", "0.1.0", "--write"]) == 1
    assert "never overwrite" in capsys.readouterr().out
    assert list(bucket) == [f"site/downloads/resolve/0.1.0/{already}"]
    assert bucket[f"site/downloads/resolve/0.1.0/{already}"][0] == b"the old build"


def test_another_version_goes_up_beside_the_first(tmp_path, bucket):
    bucket["site/downloads/resolve/0.1.0/phantra-resolve-plugin-0.1.0.pkg"] = (b"old", None)
    f = build(tmp_path, "phantra-resolve-plugin-0.1.1.pkg")
    assert up.main([str(f), "--plugin", "resolve", "--version", "0.1.1", "--write"]) == 0
    assert "site/downloads/resolve/0.1.1/phantra-resolve-plugin-0.1.1.pkg" in bucket


@pytest.mark.parametrize("name, plugin, version", [
    ("phantra-resolve-plugin.pkg", "resolve", "0.1.0"),          # no version in the name
    ("phantra-resolve-plugin-0.1.0.zip", "resolve", "0.1.0"),    # Resolve ships the .pkg now
    ("phantra-resolve-plugin-0.1.1.pkg", "resolve", "0.1.0"),    # the wrong version
    ("phantra-resolve-plugin-0.1.0.pkg", "premiere", "0.1.0"),   # the other panel
    ("phantra-premiere-plugin-0.1.0.zip", "premiere", "0.1.0"),  # Premiere ships a .ccx
    ("phantra-resolve-plugin-..pkg", "resolve", "."),            # not a version at all
])
def test_a_build_whose_name_does_not_say_what_it_is_is_refused(tmp_path, bucket, name, plugin, version):
    f = build(tmp_path, name)
    assert up.main([str(f), "--plugin", plugin, "--version", version, "--write"]) == 1
    assert bucket == {}


def test_no_bucket_is_said_not_guessed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(storage, "configured", lambda: False)
    f = build(tmp_path)
    assert up.main([str(f), "--plugin", "resolve", "--version", "0.1.0"]) == 1
    assert "not configured" in capsys.readouterr().out
