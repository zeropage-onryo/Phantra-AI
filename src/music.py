"""A music bed for a cut (2026-10-21, docs/tasks/task-music-layer.md).

The Gygler reference runs one continuous music feel under the whole ad; the
editor had a music track but nothing to put on it but an upload. This makes
an instrumental bed, priced before it is made, sized to the cut:

  * the DIRECTION comes from the project's brand kit (`sound.music`: genre,
    BPM, mood -- stored since the kit was built, read by nothing until now)
    plus whatever the person types, wrapped in `prompts/music_prompt.txt`
    (always instrumental, made to sit under text and a voiceover);
  * the LENGTH is the cut's, in whole seconds, and a length off the model's
    legal range is refused, never clamped;
  * it runs through `effects.run` exactly as the talking photo's voice
    preview does (the cap, the CREDIT HOLD before the submit, the
    generations row, settle), and the track is filed as an `asset:<id>`
    audio in the editor's media bin -- the same handle an uploaded bed has --
    so the editor lays it on the music track with its ordinary, undoable ops.

Models and prices read off each endpoint's OpenAPI schema
(fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>) and its model page,
on CHECKED. Re-check before trusting a number; fal changes these.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

CHECKED = "2026-10-21"
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DIRECTION_MAX = 600

MODELS: dict[str, dict] = {
    # "Your request will cost $0.2 per audio." `seconds_total` integer 1-190,
    # default 190; `prompt` required. Output: audio File.
    "stable-audio-25": {
        "label": "Stable Audio 2.5",
        "note": "a flat price for any length up to 3 minutes",
        "endpoint": "fal-ai/stable-audio-25/text-to-audio",
        "min_seconds": 1, "max_seconds": 190,
        "usd_flat": 0.20,
        "source": "https://fal.ai/models/fal-ai/stable-audio-25/text-to-audio",
        "checked": CHECKED,
    },
    # "$0.6 per output audio minute ... rounded up to the closest minute."
    # `music_length_ms` 3000-600000; `force_instrumental` (with `prompt`);
    # `prompt` max 4100. Output: audio File (mp3 by default).
    "elevenlabs-music": {
        "label": "ElevenLabs Music",
        "note": "richer arrangement; billed per started minute",
        "endpoint": "fal-ai/elevenlabs/music",
        "min_seconds": 3, "max_seconds": 600,
        "usd_per_minute": 0.60,
        "source": "https://fal.ai/models/fal-ai/elevenlabs/music",
        "checked": CHECKED,
    },
}
DEFAULT_MODEL = "stable-audio-25"


def usd(model: str, seconds: int) -> float:
    spec = MODELS[model]
    if "usd_flat" in spec:
        return spec["usd_flat"]
    return round(math.ceil(seconds / 60) * spec["usd_per_minute"], 4)


def direction_from_kit(kit: Optional[dict]) -> str:
    """The kit's music direction as one line, or ""."""
    if not kit:
        return ""
    music = ((kit.get("spec") or {}).get("sound") or {}).get("music") or {}
    bits = []
    if music.get("genre"):
        bits.append(music["genre"])
    if music.get("mood"):
        bits.append(music["mood"])
    if music.get("bpm"):
        bits.append(f"{int(music['bpm'])} BPM")
    return ", ".join(bits)


def build_prompt(seconds: int, direction: str) -> str:
    line = f"Style: {direction.strip()}." if direction.strip() else \
        "Style: modern, warm and upbeat, suited to a product video."
    return ((PROMPTS_DIR / "music_prompt.txt").read_text()
            .replace("{seconds}", str(seconds)).replace("{direction}", line)).strip()


def request(model: str, seconds, direction: str = "", kit: Optional[dict] = None) -> dict:
    """A bed checked and priced, nothing spent. Raises ValueError saying
    what is wrong -- a model or a length off the table is refused."""
    if model not in MODELS:
        raise ValueError(f"model must be one of {', '.join(MODELS)}")
    spec = MODELS[model]
    try:
        whole = int(math.ceil(float(seconds) - 1e-9))
    except (TypeError, ValueError):
        raise ValueError("say how long the music should be, in seconds") from None
    if not spec["min_seconds"] <= whole <= spec["max_seconds"]:
        raise ValueError(f"{spec['label']} makes {spec['min_seconds']}-{spec['max_seconds']} "
                         f"seconds of music, not {whole}")
    typed = " ".join((direction or "").split())
    if len(typed) > DIRECTION_MAX:
        raise ValueError(f"the direction is at most {DIRECTION_MAX} characters")
    from_kit = direction_from_kit(kit)
    full = "; ".join(x for x in (from_kit, typed) if x)
    return {"model": model, "label": spec["label"], "seconds": whole,
            "direction": full, "from_kit": from_kit,
            "prompt": build_prompt(whole, full), "usd": usd(model, whole)}


def body(req: dict) -> tuple[str, dict]:
    """(endpoint, body) for fal -- exactly the schema's own fields."""
    spec = MODELS[req["model"]]
    if req["model"] == "stable-audio-25":
        return spec["endpoint"], {"prompt": req["prompt"], "seconds_total": req["seconds"]}
    return spec["endpoint"], {"prompt": req["prompt"][:4100],
                              "music_length_ms": req["seconds"] * 1000,
                              "force_instrumental": True}


def run(req: dict, *, account_id: Optional[int], dsn=None, source: str, quote=None,
        project_id: Optional[int] = None) -> dict:
    """Make the bed (effects.run: the hold, the generations row, settle) and
    file it as an `asset:<id>` audio in the editor's media bin. Returns
    {ok, audio, seconds, stored, generation_id} or {ok: False, error}."""
    from . import effects
    from .cut import render, uploads
    res = effects.run(
        f"music-{req['model']}", [], req["prompt"], {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, quote=quote,
        project_id=project_id,
        row={"label": req["label"], "output": "audio"},
        endpoint_body=body(req),
        extra={"music": {"model": req["model"], "seconds": req["seconds"],
                         "direction": req["direction"]}})
    if not res.get("ok"):
        return res
    path = Path(res["path"])
    name = f"music-{req['model']}-{req['seconds']}s{path.suffix}"
    try:
        saved = uploads.save(path.read_bytes(), name, account_id=account_id,
                             media_dir=render.CUT_DIR / "media", types=uploads.AUDIO_TYPES,
                             dsn=dsn)
    except (OSError, uploads.UploadRefused) as e:
        return {"ok": False, "generation_id": res.get("generation_id"),
                "error": f"the music was made and paid for but could not be filed ({e})"}
    return {"ok": True, "audio": saved["handle"], "seconds": saved["info"].get("seconds"),
            "stored": saved["stored"], "generation_id": res.get("generation_id")}
