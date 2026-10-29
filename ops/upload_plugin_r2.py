"""Push an editor panel's release build to R2 (docs/tasks/task-plugin-repos.md, Part 2).

phantra.ai/download links `site/downloads/<plugin>/<version>/<file>`; the builds
are made in the panels' own repos (phantra-resolve-plugin's
scripts/build-pkg.sh, the Premiere panel's .ccx from Adobe's UXP Developer
Tool). This only uploads a finished build.

    venv/bin/python -m ops.upload_plugin_r2 <file> --plugin resolve|premiere --version <v> [--write]

Reports first: the file, its size and sha256, where it would go and what is
already under that version. With --write it uploads the file and a SHA256SUMS
beside it. It refuses to overwrite ANY key that already exists: a new build is a
new version, never a replacement (a browser, a mirror or a person's checksum may
hold the old one). It refuses a file whose name does not carry the plugin and
the version, so a download's name always says what it is.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from src import storage

# plugin -> (the release file's extension, its content type)
PLUGINS = {
    "resolve": (".pkg", "application/octet-stream"),  # the Mac installer
    "premiere": (".ccx", "application/octet-stream"),
}
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SUMS = "SHA256SUMS"


def expected_name(plugin: str, version: str) -> str:
    return f"phantra-{plugin}-plugin-{version}{PLUGINS[plugin][0]}"


def prefix_for(plugin: str, version: str) -> str:
    return f"site/downloads/{plugin}/{version}/"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--plugin", required=True, choices=sorted(PLUGINS))
    ap.add_argument("--version", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    if not VERSION.match(args.version):
        print(f"--version must look like 0.1.0, not {args.version!r}")
        return 1
    if not args.file.is_file():
        print(f"no file at {args.file}")
        return 1
    name = args.file.name
    want = expected_name(args.plugin, args.version)
    if name != want:
        print(f"refusing: the file is {name!r}; a {args.plugin} {args.version} build is named {want!r}")
        return 1

    size = args.file.stat().st_size
    digest = sha256_of(args.file)
    prefix = prefix_for(args.plugin, args.version)
    print(f"{name}: {size} bytes, sha256 {digest}")
    print(f"would go to {prefix}{name} and {prefix}{SUMS}")

    if not storage.configured():
        print("R2 is not configured here (R2_* in .env)")
        return 1
    there = sorted(storage.list_keys(prefix))
    print(f"{len(there)} already under {prefix}" + (": " + ", ".join(there) if there else ""))
    clash = [k for k in (f"{prefix}{name}", f"{prefix}{SUMS}") if k in there]
    if clash:
        print("refusing: never overwrite a release; make a new version instead")
        return 1
    if not args.write:
        print("report only; --write to upload")
        return 0

    # the build first, so a SHA256SUMS never names a file that is not up there
    content_type = PLUGINS[args.plugin][1]
    url = storage.upload_file(args.file, f"{prefix}{name}", content_type=content_type)
    storage.upload_bytes(f"{digest}  {name}\n".encode(), f"{prefix}{SUMS}",
                         content_type="text/plain; charset=utf-8")
    print(f"uploaded {url}")
    print(f"check:   curl -sI {url}  (200, content-length {size})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
