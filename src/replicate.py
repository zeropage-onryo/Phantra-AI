"""Replicate as a second HOST for a fal.VIDEO_MODELS row (2026-11-02).

WHY. fal charges exactly twice ByteDance's per-token price for Seedance
($21.40 / $10.70 per million tokens on 2.5). ByteDance's own API (BytePlus
ModelArk) does not sign up US accounts; Replicate resells it at ByteDance's
rate: Seedance 2.5 at $0.1028/s (480p) and $0.2312/s (720p) with no video
input, against fal's $0.2205 and $0.4730 (read off replicate.com/bytedance/
seedance-2.5 and its model schema, 2026-11-02). Replicate has no 1080p, so
1080p stays on fal. docs/tasks/task-replicate-seedance.md.

HOW. Not a new provider. The row stays a fal.VIDEO_MODELS row (same id,
same picker, same quote), and `fal.host_for(model, resolution)` says which
host renders it. `fal.price_per_second` prices the host that will render,
so the card, the quote, the hold and the invoice are one number.

The live loop is fal's own `_submit_and_wait`, given `queue_http` below as
its transport: a Replicate prediction read back in fal's queue shapes
(IN_PROGRESS / COMPLETED, an `error` field, `{"video": {"url"}}`, a
CANCELLATION_REQUESTED answer). So the deadline, the cancel rules and the
receipt in fal_requests are the SAME code, and the boot sweep
(fal_requests.recover) finishes a Replicate job a dead worker left by the
same steps: it picks this transport for a row whose model_id starts
`replicate:`.

A request body is fal's (`fal.build_body`), translated here (`to_input`):
the reference tags (`@Image1` -> `[Image1]`), image fields, an integer
duration. A key that has no Replicate twin is dropped, never sent.

Replicate bills a video model per second of OUTPUT, so a failed or
cancelled prediction makes nothing and costs nothing -- the same rule fal's
cancel handling already relies on.

Pure transport: no database, nothing from `app/`.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional

API = os.environ.get("REPLICATE_API", "https://api.replicate.com/v1").rstrip("/")
TOKEN_ENV = ("REPLICATE_API_TOKEN",)
# fal_requests.model_id prefix: how the sweep tells a Replicate receipt
PREFIX = "replicate:"

# fal body key -> Replicate input key (Seedance 2.5's schema, 2026-11-02)
FIELDS = {
    "prompt": "prompt",
    "duration": "duration",
    "resolution": "resolution",
    "aspect_ratio": "aspect_ratio",
    "image_url": "image",
    "end_image_url": "last_frame_image",
    "image_urls": "reference_images",
    "generate_audio": "generate_audio",
    "seed": "seed",
}
# fal's "auto" frame is Replicate's "adaptive"
ASPECTS = {"auto": "adaptive"}


def token() -> Optional[str]:
    return next((os.environ[n] for n in TOKEN_ENV if os.environ.get(n)), None)


def has_token() -> bool:
    return token() is not None


def model_id(replicate_model: str) -> str:
    """What fal_requests stores as model_id for a Replicate job."""
    return PREFIX + replicate_model


def is_ours(model_id_or_url: Optional[str]) -> bool:
    s = str(model_id_or_url or "")
    return s.startswith(PREFIX) or s.startswith(API + "/")


def submit_url(replicate_model: str) -> str:
    return f"{API}/models/{replicate_model}/predictions"


def to_input(body: dict) -> dict:
    """fal's body for a Seedance row -> Replicate's `input`. A video
    reference is REFUSED, not dropped: its price here is not the one quoted,
    and dropping it would render a different clip (fal.generate_video
    refuses first; this is the second lock)."""
    if (body or {}).get("video_urls"):
        raise ValueError("video references render on fal only")
    out: dict = {}
    for key, value in (body or {}).items():
        name = FIELDS.get(key)
        if name is None or value is None:
            continue
        if key == "prompt":
            value = re.sub(r"@Image(\d+)", r"[Image\1]", str(value))
        elif key == "duration":
            value = int(str(value).rstrip("s"))
        elif key == "aspect_ratio":
            value = ASPECTS.get(str(value), value)
        out[name] = value
    # a first frame decides the shape: Replicate's schema requires "adaptive"
    # for first/last-frame mode, and its default (16:9) would crop a 9:16 still
    if "image" in out:
        out["aspect_ratio"] = "adaptive"
    return out


def _call(url: str, data: Optional[dict] = None, *, method: Optional[str] = None) -> dict:
    key = token()
    if key is None:
        raise RuntimeError("REPLICATE_API_TOKEN not set (create one at replicate.com/account/api-tokens)")
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json"},
        method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode(errors="replace")[:600]
        except Exception:
            detail = ""
        raise RuntimeError(
            f"HTTP Error {e.code}: {e.reason}" + (f" -- {detail}" if detail else "")) from e


def _output_url(prediction: dict) -> Optional[str]:
    out = prediction.get("output")
    if isinstance(out, str):
        return out
    if isinstance(out, list):
        return next((u for u in out if isinstance(u, str)), None)
    if isinstance(out, dict):
        return out.get("url") or out.get("video")
    return None


def as_fal(prediction: dict) -> dict:
    """A Replicate prediction in fal's queue shapes (see fal._submit_and_wait)."""
    status = str(prediction.get("status") or "")
    get_url = (prediction.get("urls") or {}).get("get")
    cancel_url = (prediction.get("urls") or {}).get("cancel")
    out: dict = {"request_id": prediction.get("id"), "status_url": get_url,
                 "response_url": get_url, "cancel_url": cancel_url}
    if status == "succeeded":
        out["status"] = "COMPLETED"
        url = _output_url(prediction)
        if url:
            out["video"] = {"url": url}
    elif status == "failed":
        out["status"] = "COMPLETED"
        out["error"] = str(prediction.get("error") or "the prediction failed")
        out["error_type"] = "replicate_failed"
    elif status == "canceled":
        out["status"] = "COMPLETED"
        out["error"] = "the prediction was cancelled"
        out["error_type"] = "client_cancelled"
    else:                       # starting, processing
        out["status"] = "IN_PROGRESS"
    return out


def queue_http(call=None):
    """fal's `http(url, payload=None)` transport, spoken to Replicate.

    POST to a predictions URL submits (the fal body is translated), a GET
    reads the prediction back, and fal's CANCEL sentinel posts the cancel
    URL. `call` is injected by tests, exactly as fal's `http` is."""
    from . import fal
    call = call or _call

    def http(url: str, payload=None) -> dict:
        if payload is fal.CANCEL:
            call(url, {}, method="POST")
            return {"status": fal.CANCEL_REQUESTED}
        if payload is not None:
            prediction = call(url, {"input": to_input(payload)})
            return as_fal(prediction)
        return as_fal(call(url))
    return http
