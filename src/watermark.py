"""
The free tier's watermark (2026-10-11, Mike's call).

A render made by an account with no plan -- the 100-credit trial -- is
published with a small "Zero Page" mark in the bottom-right corner. Paid
accounts and the operator's exempt accounts never get one. The point is
twofold: paying removes something, and a free render posted to TikTok or
Instagram carries the studio's name.

THREE RULES, and each one is the reason for a part of this module:

1. THE CLEAN ORIGINAL IS NEVER LOST. The watermarked copy is what goes up
   at the render's normal key, so every URL the studio already stores and
   serves is the marked one and no reader has to change. The untouched
   original goes up beside it under an unguessable key
   (`clean/<uuid4>/<name>`, through media.object_key so the tenant fence
   applies), recorded in `watermarked_media`. The local file on this
   machine's disk is the clean one too: only the PUBLISHED copy is marked.

2. A MODEL NEVER SEES THE MARK. A free still is often fed straight back in
   -- Animate, a keyframe anchoring a clip, an edit, an effect -- and a
   video model handed a logo animates the logo. `clean_url(url)` swaps a
   marked URL for its clean original, and the three functions that hand a
   render to a model call it: `fal.as_image_url`, `effects.fetchable_video`
   and `imagery.fetch_image_bytes` (which the Nano/Gemini paths use).
   Anything else that reads the local `output_path` already gets the clean
   file.

3. UPGRADING UNLOCKS EVERYTHING ALREADY MADE. `unlock(account_id)` copies
   each clean original over its marked key (server side, `storage.copy_key`)
   so every URL already stored anywhere now serves the clean file -- no row
   is rewritten. The billing webhook calls it when an invoice for a plan is
   paid. A CDN may serve the old bytes until its cache expires.

WHEN NOTHING IS MARKED, on purpose:
- No bucket (`storage.configured()` false). The render is served off this
  machine's own disk, and the only machine like that is the operator's dev
  box. Marking the one local file would also mark the model inputs.
- Unowned work (account None: the CLI, a script) and exempt accounts.
- A transparent or ProRes clip (.webm / .mov -- the background-removal
  effects). A mark on an alpha channel is a different job; not built.
- `ZEROPAGE_WATERMARK=0`.
- Any error deciding or burning. This FAILS OPEN -- the clean file is
  published as before, with a line on stderr -- because the person paid
  credits for this render, and a render lost to a watermark bug is worse
  than one trial render without a mark. Deciding fails open for the same
  reason: a flaky read must never brand a paying customer's work.

OWNED (db.OWNED_TABLES): one account's media.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from . import db

ENV = "ZEROPAGE_WATERMARK"
TEXT = "Zero Page"
SIGNAL_RED = (228, 0, 43)      # the studio's --signal
OPACITY = 0.78                 # the mark's own alpha, over the picture
FONT_SHARE = 0.04              # the text's height against the frame's short side
MIN_FONT = 14
MARGIN_SHARE = 0.03            # distance from the right and bottom edges
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4"}
FFMPEG_TIMEOUT = 600

SCHEMA = """
CREATE TABLE IF NOT EXISTS watermarked_media (
    id           BIGSERIAL PRIMARY KEY,
    account_id   BIGINT NOT NULL,
    public_key   TEXT NOT NULL UNIQUE,
    clean_key    TEXT NOT NULL,
    media_kind   TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    unlocked_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS watermarked_media_account
    ON watermarked_media (account_id) WHERE unlocked_at IS NULL;
"""


def init(dsn: Optional[str] = None) -> None:
    """Create and own the table. Idempotent."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        db.own_table(conn, "watermarked_media")


def _log(message: str) -> None:
    print(f"[watermark] {message}", file=sys.stderr)


# --------------------------------------------------------------------------
# who gets one
# --------------------------------------------------------------------------

def enabled() -> bool:
    return (os.environ.get(ENV) or "1").strip() != "0"


def applies(account_id: Optional[int], dsn: Optional[str] = None) -> bool:
    """Does a render made by this account get marked? True only for an
    owned, non-exempt account with no plan -- the free trial. Fails OPEN
    (False) on any error: see the module docstring."""
    if account_id is None or not enabled():
        return False
    # read here, not through accounts.plan_of / is_credit_exempt: both
    # swallow a database error into "no plan" / "not exempt", which here
    # would brand a paying customer's render on a flaky read
    try:
        with db.connect(dsn) as conn:
            cols = db.columns(conn, "accounts")
            row = conn.execute(
                "SELECT " + ("plan" if "plan" in cols else "NULL AS plan") + ", "
                + ("credit_exempt" if "credit_exempt" in cols else "FALSE AS credit_exempt")
                + " FROM accounts WHERE id = %s", (int(account_id),)).fetchone()
        if row is None:
            return False
        return not row["credit_exempt"] and not row["plan"]
    except Exception as e:  # noqa: BLE001 -- see docstring
        _log(f"could not tell whether account {account_id} is on a plan "
             f"({type(e).__name__}); publishing unmarked")
        return False


def markable(path: Path) -> Optional[str]:
    """'image' / 'video' when this file type can be marked, else None."""
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return None


# --------------------------------------------------------------------------
# drawing it
# --------------------------------------------------------------------------

def mark_layer(width: int, height: int):
    """A transparent RGBA layer the size of the frame with the mark drawn
    in its bottom-right corner: a red dot and the studio's name, white,
    over a soft shadow so it reads on a light frame as well as a dark one.
    The same layer marks a still and every frame of a clip."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    short = max(1, min(width, height))
    size = max(MIN_FONT, int(round(short * FONT_SHARE)))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:                               # Pillow < 10.1
        font = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), TEXT, font=font)
    text_w, text_h = right - left, bottom - top
    dot = max(4, int(round(size * 0.42)))
    gap = max(3, int(round(size * 0.35)))
    margin = max(8, int(round(short * MARGIN_SHARE)))
    x1 = width - margin
    x0 = x1 - (dot + gap + text_w)
    y1 = height - margin
    y0 = y1 - text_h
    alpha = int(round(255 * OPACITY))

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((x0 + dot + gap - left, y0 - top), TEXT, font=font, fill=(0, 0, 0, 150))
    cy = y0 + text_h // 2
    sd.ellipse((x0, cy - dot // 2, x0 + dot, cy - dot // 2 + dot), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, size // 8)))

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((x0, cy - dot // 2, x0 + dot, cy - dot // 2 + dot), fill=(*SIGNAL_RED, alpha))
    d.text((x0 + dot + gap - left, y0 - top), TEXT, font=font, fill=(255, 255, 255, alpha))
    return Image.alpha_composite(shadow, layer)


def burn_image(src: Path, dst: Path) -> None:
    """Mark a still. The output keeps the input's format."""
    from PIL import Image, ImageOps

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        base = im.convert("RGBA")
    marked = Image.alpha_composite(base, mark_layer(*base.size))
    suffix = Path(dst).suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        marked.convert("RGB").save(dst, "JPEG", quality=92)
    elif suffix == ".webp":
        marked.save(dst, "WEBP", quality=92)
    else:
        marked.save(dst, "PNG")


def _video_size(src: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(src)],
        capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    w, _, h = out.partition("x")
    return int(w), int(h)


def burn_video(src: Path, dst: Path) -> None:
    """Mark every frame of a clip, sound copied untouched. One overlay of
    the same layer burn_image draws -- `overlay` is in every ffmpeg build,
    where drawtext needs libfreetype."""
    width, height = _video_size(src)
    with tempfile.TemporaryDirectory() as tmp:
        layer_path = Path(tmp) / "mark.png"
        mark_layer(width, height).save(layer_path, "PNG")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(layer_path),
             "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
             "-map", "[v]", "-map", "0:a?",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "copy", "-movflags", "+faststart", str(dst)],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if proc.returncode != 0 or not Path(dst).is_file():
        tail = " | ".join((proc.stderr or "").strip().splitlines()[-3:])
        raise RuntimeError(f"ffmpeg could not mark the clip: {tail or proc.returncode}")


# --------------------------------------------------------------------------
# publishing
# --------------------------------------------------------------------------

def publish(path, tail: str, account_id: Optional[int], content_type: str, *,
            dsn: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Publish a free account's render marked. None when this render is not
    marked (no bucket, a paid or exempt account, a type that cannot be
    marked, or any failure) -- the caller then publishes exactly as it
    always did. Otherwise {"url", "marked_path"}: the marked copy is up at
    the render's normal key and its URL is the one to store; the clean
    original is up under its own key; `marked_path` is a temp file the
    caller may draw a poster from and must remove (`discard`)."""
    from . import media, storage

    path = Path(path)
    kind = markable(path)
    try:
        if kind is None or not storage.configured() or not path.is_file():
            return None
    except Exception:  # noqa: BLE001
        return None
    if not applies(account_id, dsn=dsn):
        return None

    marked = Path(tempfile.mkdtemp(prefix="zpwm-")) / path.name
    try:
        (burn_image if kind == "image" else burn_video)(path, marked)
        public_key = media.object_key(tail, account_id)
        clean_key = media.object_key(f"clean/{uuid.uuid4().hex}/{path.name}", account_id)
        storage.upload_file(path, key=clean_key, content_type=content_type)
        url = storage.upload_file(marked, key=public_key, content_type=content_type)
        with db.connect(dsn) as conn:
            conn.execute(
                "INSERT INTO watermarked_media (account_id, public_key, clean_key, media_kind) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (public_key) DO UPDATE SET "
                "clean_key = excluded.clean_key, account_id = excluded.account_id, "
                "media_kind = excluded.media_kind, unlocked_at = NULL",
                (int(account_id), public_key, clean_key, kind))
        return {"url": url, "marked_path": marked}
    except Exception as e:  # noqa: BLE001 -- fails open, see the module docstring
        _log(f"{tail}: not marked, published clean ({type(e).__name__}: {e})")
        discard(marked)
        return None


def discard(marked_path) -> None:
    """Remove publish()'s temp copy and its folder."""
    if not marked_path:
        return
    shutil.rmtree(Path(marked_path).parent, ignore_errors=True)


def publish_file(path, tail: str, account_id: Optional[int], content_type: str, *,
                 dsn: Optional[str] = None, poster: bool = False) -> Optional[str]:
    """publish() for a caller that only wants the URL: draws the clip's
    poster from the MARKED copy when asked (the wall's tile matches the
    file) and removes the temp file. None means publish as before."""
    out = publish(path, tail, account_id, content_type, dsn=dsn)
    if out is None:
        return None
    try:
        if poster:
            from . import media
            media.mirror_poster(out["marked_path"], tail, account_id)
    finally:
        discard(out["marked_path"])
    return out["url"]


# --------------------------------------------------------------------------
# reading it back
# --------------------------------------------------------------------------

def _keys_for(url: str) -> list[str]:
    """The bucket keys a URL could name: its path after the host, and the
    same with a first segment dropped (the S3 endpoint's bucket name, on a
    presigned URL). Our own bucket only -- anything else names no key."""
    from . import storage
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return []
    try:
        base = (storage.public_base_url() or "").rstrip("/")
        bkt = storage.bucket() or ""
    except Exception:  # noqa: BLE001
        return []
    bare = url.split("?", 1)[0].split("#", 1)[0]
    if base and bare.startswith(base + "/"):
        return [bare[len(base) + 1:]]
    path = urlparse(bare).path.lstrip("/")
    if bkt and path.startswith(bkt + "/") and "r2.cloudflarestorage.com" in bare:
        return [path[len(bkt) + 1:]]
    return []


def clean_url(url, dsn: Optional[str] = None):
    """The clean original behind a marked render, as a URL a model can
    fetch; anything else back unchanged. Never raises: on any doubt the
    caller gets what it passed in."""
    keys = _keys_for(url) if isinstance(url, str) else []
    if not keys:
        return url
    try:
        with db.connect(dsn) as conn:
            if not db.table_exists(conn, "watermarked_media"):
                return url
            row = conn.execute(
                "SELECT clean_key FROM watermarked_media "
                "WHERE public_key = ANY(%s) AND unlocked_at IS NULL LIMIT 1",
                (keys,)).fetchone()
        if not row:
            return url
        from . import media, storage
        clean = (storage.signed_url_for_key(row["clean_key"]) if media.signing()
                 else storage.url_for_key(row["clean_key"]))
        return clean or url
    except Exception as e:  # noqa: BLE001
        _log(f"clean original not looked up ({type(e).__name__}); using the URL as given")
        return url


def is_marked(url, dsn: Optional[str] = None) -> bool:
    """Is this URL a render still carrying its mark? For the UI and tests."""
    keys = _keys_for(url)
    if not keys:
        return False
    try:
        with db.connect(dsn) as conn:
            if not db.table_exists(conn, "watermarked_media"):
                return False
            return conn.execute(
                "SELECT 1 FROM watermarked_media WHERE public_key = ANY(%s) "
                "AND unlocked_at IS NULL", (keys,)).fetchone() is not None
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------
# upgrading
# --------------------------------------------------------------------------

def unlock(account_id: int, *, dsn: Optional[str] = None) -> dict[str, int]:
    """Take the mark off everything this account made: copy each clean
    original over its marked key. Every stored URL now serves the clean
    file; nothing else is rewritten. Idempotent, and a row whose copy
    fails stays marked for the next call. Never raises -- the caller is
    the billing webhook, and the money must be recorded whatever happens
    here. Returns {"unlocked", "failed"}."""
    from . import storage
    done = failed = 0
    try:
        with db.connect(dsn) as conn:
            if not db.table_exists(conn, "watermarked_media"):
                return {"unlocked": 0, "failed": 0}
            rows = conn.execute(
                "SELECT id, public_key, clean_key FROM watermarked_media "
                "WHERE account_id = %s AND unlocked_at IS NULL ORDER BY id",
                (int(account_id),)).fetchall()
    except Exception as e:  # noqa: BLE001
        _log(f"account {account_id}: renders not unlocked ({type(e).__name__}: {e})")
        return {"unlocked": 0, "failed": 0}
    for row in rows:
        try:
            storage.copy_key(row["clean_key"], row["public_key"])
            with db.connect(dsn) as conn:
                conn.execute("UPDATE watermarked_media SET unlocked_at = now() "
                             "WHERE id = %s AND account_id = %s",
                             (row["id"], int(account_id)))
            done += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            _log(f"{row['public_key']}: still marked ({type(e).__name__}: {e})")
    return {"unlocked": done, "failed": failed}


__all__ = ["applies", "burn_image", "burn_video", "clean_url", "discard", "enabled",
           "init", "is_marked", "mark_layer", "markable", "publish", "publish_file",
           "unlock"]
