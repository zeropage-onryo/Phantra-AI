"""Push an editor panel's release build to R2 (docs/tasks/task-plugin-repos.md, Part 2).

phantra.ai/download links `site/downloads/<plugin>/<version>/<file>`; the builds
are made in the panels' own repos (phantra-resolve-plugin's
scripts/build-pkg.sh; phantra-premiere-plugin's scripts/build-pkg.sh and
build-zxp.sh, the ONE Adobe panel for Premiere Pro and After Effects, a Mac
.pkg and a Windows .zxp, 2026-11-03). This only uploads a finished build.

    venv/bin/python -m ops.upload_plugin_r2 <file> --plugin resolve|adobe --version <v> [--write]

Reports first: the file, its size and sha256, where it would go and what is
already under that version. With --write it uploads the file and a SHA256SUMS
beside it. It refuses to overwrite a build that already exists: a new build is a
new version, never a replacement (a browser, a mirror or a person's checksum may
hold the old one). A version's SHA256SUMS is the one key that grows: a second
file of the same version (the Adobe .zxp beside its .pkg) is appended to it,
and a name already listed there is refused. It refuses a file whose name does
not carry the plugin and the version, so a download's name always says what
it is.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from src import storage

# plugin -> the release files' extensions (web/src/lib/downloads.ts FILES)
PLUGINS = {
    "resolve": (".pkg",),            # the Mac installer
    "adobe": (".pkg", ".zxp"),       # the Mac installer; the ZXP for Windows
}
CONTENT_TYPE = "application/octet-stream"
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SUMS = "SHA256SUMS"


def expected_names(plugin: str, version: str) -> list[str]:
    return [f"phantra-{plugin}-plugin-{version}{ext}" for ext in PLUGINS[plugin]]


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
    want = expected_names(args.plugin, args.version)
    if name not in want:
        print(f"refusing: the file is {name!r}; a {args.plugin} {args.version} build is named "
              + " or ".join(repr(w) for w in want))
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
    sums = ""
    if f"{prefix}{SUMS}" in there:
        sums = (storage.read_key(f"{prefix}{SUMS}") or b"").decode("utf-8", "replace")
    if f"{prefix}{name}" in there or name in sums.split():
        print("refusing: never overwrite a release; make a new version instead")
        return 1
    if not args.write:
        print("report only; --write to upload")
        return 0

    # the build first, so a SHA256SUMS never names a file that is not up there
    url = storage.upload_file(args.file, f"{prefix}{name}", content_type=CONTENT_TYPE)
    if sums and not sums.endswith("\n"):
        sums += "\n"
    storage.upload_bytes(f"{sums}{digest}  {name}\n".encode(), f"{prefix}{SUMS}",
                         content_type="text/plain; charset=utf-8")
    print(f"uploaded {url}")
    print(f"check:   curl -sI {url}  (200, content-length {size})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
