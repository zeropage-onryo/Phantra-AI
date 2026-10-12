"""
The one-time upload page the connector's `upload_link` mints (2026-10-11,
docs/tasks/task-connector-overnight.md, PR 1): `GET /u/<token>` is a small
form, `POST /u/<token>` files the picked file into the token's account.

THE TOKEN IS THE AUTH (src/upload_links.py). There is no sign-in on this
page: whoever holds the token may upload ONE file into the account it
was minted for, within thirty minutes. So the page trusts nothing else
about the request -- not the file's name, not its declared type -- and
every check is on the bytes:

- the file is typed by its first bytes (`sniff`), never by its extension:
  jpg, png, webp or heic, mp4 or mov; anything else is refused;
- the size is capped at the editor's own caps (100 MB for a picture,
  500 MB for a clip), checked against the declared length before the
  body is parsed and again as it is read;
- a picture is normalised to an upright JPEG (`refbin.to_jpeg`, which is
  what reads a HEIC) before it is kept, so what lands in the studio is
  what every later reader expects;
- the file is then filed through the editor's own upload body
  (`src/cut/uploads.save`): probed, content-addressed, mirrored, recorded
  as an `asset:<id>`; and, when the link was minted for an element,
  added to that element through the Elements page's own create body --
  the same adapter the connector's `add_element` uses.

The POST is rate-limited by address like the sign-in forms. The token is
claimed before the file is saved and given back when the file was
refused, so a wrong file does not spend the link.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src import refbin, upload_links
from src.cut import uploads as cut_uploads

from . import auth

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

PAGE = upload_links.PAGE_PATH + "/{token}"
IMAGE_CAP = cut_uploads.MAX_MEDIA_BYTES          # the editor's: 100 MB
VIDEO_CAP = cut_uploads.MAX_VIDEO_BYTES          # 500 MB
READ_CHUNK = 1 << 20
MB = 1024 * 1024
ACCEPT = "image/jpeg,image/png,image/webp,image/heic,.heic,video/mp4,video/quicktime"
TAKES = "a jpg, png, webp or heic picture, or an mp4 or mov clip"

_HEIC_BRANDS = (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heif")


def sniff(data: bytes) -> Optional[tuple[str, str]]:
    """(kind, extension) read off the first bytes -- never the file name.
    None for anything that is not one of the six types the page takes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image", ".png"
    if data[:2] == b"\xff\xd8":
        return "image", ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", ".webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in _HEIC_BRANDS:
            return "image", ".heic"
        if brand.startswith(b"qt"):
            return "video", ".mov"
        return "video", ".mp4"            # isom, mp42, avc1, M4V ... ffprobe decides
    return None


def _page(request: Request, status: int = 200, **context: Any) -> HTMLResponse:
    response = templates.TemplateResponse(request, "upload.html", context, status_code=status)
    response.headers["Cache-Control"] = "no-store"
    return response


def _problem(request: Request, message: str, status: int = 400) -> HTMLResponse:
    return _page(request, status, problem=message)


def _state(token: str) -> tuple[Optional[dict], Optional[str], int]:
    """(claims, problem, status): the token's claims when it is good, or
    the plain sentence the page shows and the status that goes with it."""
    try:
        claims = upload_links.verify(token)
    except upload_links.LinkRefused as e:
        return None, str(e), 410 if e.code == "expired" else 404
    spent = upload_links.used(claims["token_id"])
    if spent is not None:
        made = (spent.get("result") or {}).get("asset")
        return None, ("this upload link was already used" +
                      (f" -- it saved {made}" if made else "") +
                      ". Ask the chat for a new one to upload another file."), 410
    return claims, None, 200


def _what(claims: dict) -> str:
    """The sentence the form opens with: what this link will do."""
    if claims.get("element_kind"):
        kind = claims["element_kind"]
        return (f"Add a photo to the {kind} “{claims.get('element_name') or ''}” "
                "in your studio.")
    if claims["purpose"] == "footage":
        return "Upload a clip (or a still) to your studio's library."
    return "Upload a reference picture to your studio's library."


@router.get(PAGE, response_class=HTMLResponse)
def upload_form(request: Request, token: str):
    upload_links.ensure()
    claims, problem, status = _state(token)
    if problem:
        return _problem(request, problem, status)
    return _page(request, what=_what(claims), accept=ACCEPT, takes=TAKES,
                 image_mb=IMAGE_CAP // MB, video_mb=VIDEO_CAP // MB)


async def _read_capped(upload, cap: int) -> Optional[bytes]:
    """The file's bytes, or None once it runs past `cap`."""
    chunks, total = [], 0
    while True:
        chunk = await upload.read(READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _save(data: bytes, kind: str, ext: str, claims: dict) -> dict[str, Any]:
    """File the bytes as an upload (and as an element's photo when asked),
    through the two bodies the studio already has. Raises
    cut_uploads.UploadRefused with a reason a person can act on."""
    from . import cut_routes
    account_id = claims["account_id"]
    if kind == "image":
        jpeg = refbin.to_jpeg(data)
        if not jpeg:
            raise cut_uploads.UploadRefused("not_an_image",
                                            "that file could not be read as a picture")
        data, ext = jpeg, ".jpg"
    sha = hashlib.sha256(data).hexdigest()
    saved = cut_uploads.save(data, f"{sha[:24]}{ext}", account_id=account_id,
                             media_dir=cut_routes.MEDIA_DIR)
    # a picture has no length to show: the probe's seconds for a still is the
    # editor's placeholder (cut.uploads.STILL_SECONDS), which the live page
    # printed as "Length 600.0s" on 2026-10-12; the save itself stores none
    result: dict[str, Any] = {"asset": saved["handle"], "kind": saved["kind"],
                              "seconds": (None if saved["kind"] == "image"
                                          else saved["info"].get("seconds")),
                              "width": saved["info"].get("width"),
                              "height": saved["info"].get("height"),
                              "size": saved["size"]}
    try:
        cut_routes._start_preview(saved["handle"], saved["stored"], account_id)
    except Exception as exc:                                    # noqa: BLE001
        print(f"[upload] no preview for {saved['handle']}: {exc}", file=sys.stderr)
    if claims.get("element_kind"):
        from . import api, mcp_mount
        add = mcp_mount.connector_element(api.create_element)
        photo = (f"up-{hashlib.sha1(data).hexdigest()[:16]}.jpg", data)
        try:
            made = add(claims["element_kind"], claims.get("element_name") or "",
                       photo=photo, notes="", account_id=account_id) or {}
            result["element"] = {"kind": claims["element_kind"],
                                 "name": claims.get("element_name") or "",
                                 "slug": made.get("slug"),
                                 "described": bool(made.get("described"))}
        except Exception as exc:                                # noqa: BLE001
            # the file IS saved; only the element step failed, and the page
            # says so in the body's own words
            result["element_problem"] = str(exc) or "the element could not be made"
    return result


@router.post(PAGE, response_class=HTMLResponse)
async def upload_post(request: Request, token: str):
    if auth._rate_limited(request, "upload"):
        return _problem(request, "too many uploads from this address in a minute -- "
                                 "wait a moment and try again", 429)
    upload_links.ensure()
    claims, problem, status = _state(token)
    if problem:
        return _problem(request, problem, status)
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > VIDEO_CAP + MB:
        return _problem(request, f"that file is over {VIDEO_CAP // MB} MB", 413)
    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return _problem(request, "pick a file first")
    data = await _read_capped(upload, VIDEO_CAP)
    if data is None:
        return _problem(request, f"that file is over {VIDEO_CAP // MB} MB", 413)
    if not data:
        return _problem(request, "that file is empty")
    sniffed = sniff(data)
    if sniffed is None:
        return _problem(request, f"that file is not {TAKES} -- it is judged by its "
                                 "contents, not its name")
    kind, ext = sniffed
    if kind == "image" and len(data) > IMAGE_CAP:
        return _problem(request, f"that picture is over {IMAGE_CAP // MB} MB", 413)
    if claims.get("element_kind") and kind != "image":
        return _problem(request, "an element's picture must be a picture, not a clip")

    if not upload_links.claim(claims):
        return _problem(request, "this upload link was already used -- ask the chat "
                                 "for a new one", 410)
    try:
        result = _save(data, kind, ext, claims)
    except cut_uploads.UploadRefused as e:
        upload_links.forget(claims["token_id"], claims["account_id"])
        return _problem(request, str(e), 413 if e.code == "too_big" else 400)
    except Exception as exc:                                    # noqa: BLE001
        upload_links.forget(claims["token_id"], claims["account_id"])
        print(f"[upload] could not save ({type(exc).__name__}: {exc})", file=sys.stderr)
        return _problem(request, "the file could not be saved just now -- try again", 500)
    upload_links.record(claims["token_id"], claims["account_id"], result)
    return _page(request, saved=result, what=_what(claims))


__all__ = ["router", "sniff", "PAGE", "IMAGE_CAP", "VIDEO_CAP"]
