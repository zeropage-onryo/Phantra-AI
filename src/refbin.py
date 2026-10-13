"""
The reference bin: `data/refs/` -- one owner for the directory, the
file naming, and the JPEG normalisation every reference goes through.

This existed as three private helpers inside app/api.py (`_to_jpeg`,
`_save_upload_ref`, `UPLOAD_REFS_DIR`) back when a composer upload was
the only thing that ever landed there. src/scout.py now writes to the
same place -- the research images behind a crawled spark -- and `src/`
never imports `app/`, so the rule would have had to be written twice.
Two implementations of a content-addressed filename is the shape of bug
this project has already paid for elsewhere (see asset_shelf's
docstring): the second writer drifts, and the same photo starts
existing under two names.

So the rule lives here and app/api.py delegates. The URL shape does not
change -- `/refs/<sha>.jpg`, served by the static mount in app/main.py,
resolved by `_resolve_asset_photo` -- which is exactly why a scouted
research image can ride into a generation through the existing
composer path without a single new route.

Everything is best-effort: a reference that cannot be read or written
is dropped and returns None. A reference is an enhancement, and the
standing rule in this repo is that a bad one must never fail the run
that was using it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFS_DIR = PROJECT_ROOT / "data" / "refs"

# A remote image that is bigger than this is almost certainly not a
# reference photo -- it is a page asset, a PDF, or something that will
# cost more to decode than it is worth. Bounded because scout fetches
# URLs it did not choose.
MAX_FETCH_BYTES = 8 * 1024 * 1024
# Who we say we are when we fetch a frame. requests' default
# ("python-requests/x") is refused outright by Wikimedia (403, its UA
# policy wants a name and a contact) and throttled by other image hosts,
# so a hunt from the deployed API came back "no candidate image could be
# fetched" while the same URLs loaded fine in the browser (2026-10-01).
FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Phantra/1.0; +https://phantra.ai)",
    "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8",
}
FETCH_TIMEOUT = 10


def to_jpeg(data: bytes) -> Optional[bytes]:
    """Any readable image -> upright RGB JPEG bytes, or None.

    `exif_transpose` runs BEFORE convert("RGB"), which drops the EXIF it
    reads. Every still off an iPhone is stored landscape with
    orientation 6 -- portrait only because a tag says so -- and
    converting first baked half this project's asset bank in sideways
    into data/refs, where nothing downstream could recover it
    (2026-08-28). pillow-heif is registered when present, because HEIC
    is otherwise accepted, listed, and silently dropped at render.
    """
    import io

    from PIL import Image
    try:
        import pillow_heif  # iPhone photos, when it is installed
        pillow_heif.register_heif_opener()
    except Exception:
        pass                    # degrade: .heic simply stays unreadable
    try:
        from PIL import ImageOps
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image).convert("RGB")
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return None             # not a readable image -- skip, never fail the run


def save(jpeg: bytes, account_id: Optional[int] = None) -> Optional[str]:
    """Persist one reference, return the URL it rides on.

    Content-addressed, so attaching the same photo to six scenes -- or
    the scout re-finding the same thumbnail on two consecutive nights --
    stores it once."""
    try:
        REFS_DIR.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(jpeg).hexdigest()[:24] + ".jpg"
        target = REFS_DIR / name
        if not target.exists():
            target.write_bytes(jpeg)
        mirror_to_r2(target, account_id)
        return f"/refs/{name}"
    except Exception:
        return None


def mirror_to_r2(target: Path, account_id: Optional[int] = None) -> Optional[str]:
    """Push one bin image up, best-effort. Delegates to `media.mirror`.

    data/refs/ is gitignored, dockerignored, AND on the deploy it is a
    fresh Fly volume, so a photo the composer took or the scout crawled
    on his Mac reaches no other machine (2026-09-08, Mike: "the
    reference photos aren't appearing"). The bytes go up here, at the
    one place they are written.

    The KEY this lands under is no longer built here. It was, and
    app/api.py built the asset-photo one its own way, and two writers of
    one scheme is the bug this repo has now paid for twice -- so
    `src/media.py` owns the scheme (tenant prefix, derivative) and this
    stays what it always was: the place that knows a bin image has just
    been written and that a failure here must never cost the save.
    """
    from . import media
    return media.mirror(target, f"refs/{target.name}", account_id,
                        content_type="image/jpeg")


def resolve(url_path: str) -> Optional[Path]:
    """`/refs/<name>.jpg` -> the file on disk, or None.

    Lives beside `save` deliberately. When the write lived here and the
    read stayed in app/api.py, patching one directory in a test moved
    the writer and left the reader pointing somewhere else -- a file
    saved successfully and then resolved to nothing, which is the exact
    silent-reference failure this module exists to prevent. One module
    owns the directory, both directions.

    Anything that escapes the directory resolves to None rather than
    raising: these URLs arrive from a form, and an attachment is an
    enhancement.
    """
    clean = (url_path or "").split("?")[0].strip("/")
    parts = clean.split("/")
    if len(parts) != 2 or parts[0] != "refs":
        return None
    try:
        target = (REFS_DIR / parts[1]).resolve()
        if REFS_DIR.resolve() != target.parent:
            return None
        return target if target.is_file() else None
    except Exception:
        return None


def public_host(host) -> bool:
    """SSRF guard: only addresses outside the private ranges.

    THE canonical one -- src/imagery.py delegates here. It moved down
    when the MCP surface gained bank_reference (2026-09-01): a crawl URL
    at least came from Reddit or YouTube, but an AGENT-supplied URL is
    whatever a page the agent read told it to fetch, and this fetch runs
    server-side. A guard that only one of two fetchers has is the shape
    of bug where the weaker one is the one that gets called.
    """
    import ipaddress
    import socket

    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return bool(infos)


def fetch(url: str) -> Optional[str]:
    """Download a remote image into the bin, normalised. None on
    anything that isn't a readable image within the size bound.

    Streamed with a hard byte cap rather than read whole, and refused
    outright for a private address: these URLs come off a crawl -- or,
    since bank_reference, off whatever page an agent happened to read --
    so nothing has vouched for what is behind them. The fetch itself is
    `public_bytes`, so that holds at every redirect and not only for the
    address that was handed in. Plain http stays allowed: an image host
    a search result names may still serve it.
    """
    try:
        data, _ = public_bytes(url, max_bytes=MAX_FETCH_BYTES)
        jpeg = to_jpeg(data)
        return save(jpeg) if jpeg else None
    except Exception:
        return None


class ImageRefused(ValueError):
    """Why a picture at an address was not taken, as a sentence a person
    can act on."""


MAX_REDIRECTS = 5
_REDIRECTS = (301, 302, 303, 307, 308)
# an address that answers with one of these is a page or a document, never
# a picture -- the commonest slip is a product PAGE handed over as its photo
_NOT_A_PICTURE = ("text/", "application/json", "application/xhtml", "application/xml",
                  "application/pdf")


def opens_as_image(data: bytes) -> bool:
    """True when the bytes open as a picture. Only the header is read;
    nothing is decoded."""
    import io

    from PIL import Image
    try:
        import pillow_heif  # iPhone photos, when it is installed
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    try:
        with Image.open(io.BytesIO(data)):
            return True
    except Exception:
        return False


def public_bytes(url: str, *, max_bytes: int, https_only: bool = False,
                 images_only: bool = False) -> tuple:
    """What a public address answers with -> (bytes, the content type it
    declared), or ImageRefused saying why.

    THE one fetch of an address nobody here vouched for: `fetch`,
    `fetch_public_image` and src/imagery.fetch_image_bytes all go through
    it. Until 2026-10-11 the two older ones checked the FIRST host and
    then let `requests` follow redirects on its own, so a public address
    that answered 302 to a private, loopback or metadata address was
    fetched from inside the network -- a guard only one fetcher has is
    the shape of bug where the weaker one is the one that gets called
    (see `public_host`). src/linkrefs.py walks its hops the same way.

    - Redirects are followed BY HAND. Every hop must be http or https
      (https alone with `https_only`), carry no username or password, and
      name a public host. A hop back to an address already asked is a
      loop and is not asked again; a chain stops after MAX_REDIRECTS.
    - An answer that says it is a page or a document is refused before a
      byte of it is read. With `images_only` it must say it is an image,
      or say nothing and open as one: those bytes go back to a caller
      that treats them as a picture without decoding them.
    - The body is streamed against `max_bytes`.
    """
    from urllib.parse import urljoin, urlparse

    import requests

    megabytes = max_bytes // (1024 * 1024)
    schemes = ("https",) if https_only else ("http", "https")
    current, asked = (url or "").strip(), set()
    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlparse(current)
        if parsed.scheme not in schemes or not parsed.hostname:
            raise ImageRefused("the picture's address must start with "
                               + ("https://" if https_only else "http:// or https://"))
        if parsed.username or parsed.password:
            raise ImageRefused("an address with a username or password in it is not taken")
        if not public_host(parsed.hostname):
            raise ImageRefused("that address is not on the public internet")
        if current in asked:
            break                       # a loop: never ask the same address twice
        asked.add(current)
        try:
            with requests.get(current, stream=True, timeout=FETCH_TIMEOUT,
                              headers=FETCH_HEADERS, allow_redirects=False) as response:
                if response.status_code in _REDIRECTS:
                    target = (response.headers.get("location") or "").strip()
                    if not target:
                        raise ImageRefused("that address redirects nowhere")
                    current = urljoin(current, target)
                    continue
                if response.status_code >= 400:
                    raise ImageRefused(f"that address answered {response.status_code}, "
                                       "not a picture")
                kind = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                if kind.startswith(_NOT_A_PICTURE):
                    raise ImageRefused(
                        "that address is a web page, not a picture -- pass the address "
                        "of the image file itself" if kind.startswith("text/html") else
                        f"that address answered with {kind}, not a picture")
                if images_only and kind and not kind.startswith("image/"):
                    raise ImageRefused(f"that address answered with {kind}, not a picture")
                try:
                    declared = int(response.headers.get("content-length") or 0)
                except ValueError:
                    declared = 0
                if declared > max_bytes:
                    raise ImageRefused(f"the picture is over {megabytes} MB")
                chunks, total = [], 0
                for chunk in response.iter_content(64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ImageRefused(f"the picture is over {megabytes} MB")
                    chunks.append(chunk)
        except ImageRefused:
            raise
        except Exception as exc:
            raise ImageRefused("that address could not be reached") from exc
        data = b"".join(chunks)
        if not data:
            raise ImageRefused("that address answered with nothing")
        if images_only and not kind and not opens_as_image(data):
            raise ImageRefused("that address did not say it is a picture and does not open as one")
        return data, kind
    raise ImageRefused("that address redirects too many times")


def fetch_public_image(url: str, *, max_bytes: int) -> bytes:
    """One picture from a public https address, or ImageRefused saying why.

    For an address a PERSON handed a tool (the connector's `add_element`,
    2026-10-11), where `fetch`'s silent None is the wrong answer: a caller
    who is told nothing tries the same address again. It is `public_bytes`
    with https required on the first address and on every redirect,
    because the address is a stranger's choice and this fetch runs on the
    server.

    The bytes are not decoded here; the caller checks they are a picture.
    """
    return public_bytes(url, max_bytes=max_bytes, https_only=True)[0]
