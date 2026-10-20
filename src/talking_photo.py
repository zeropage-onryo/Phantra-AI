"""
A talking photo: a photo of a person plus a voice -> a clip of that person
speaking or singing it (2026-10-20, docs/tasks/task-talking-photo.md;
Mike approved the plan that day).

Two spends, each quoted and approved on its own, both through
`effects.run` (the cap, the CREDIT HOLD before the submit, the
generations row, settle) exactly as `clip_edit` does -- a third spending
path is not grown beside it:

1. A VOICE PREVIEW (optional): a typed script read aloud by ElevenLabs v3.
   Priced per character, so it is known before anything runs. The audio is
   filed as an `asset:<id>` in the editor's media bin, the same handle an
   uploaded voiceover gets, so the person hears it, and its exact length --
   which is what prices step 2 -- is measured, not guessed.
2. THE CLIP: OmniHuman v2 on the photo and that audio (an upload or the
   preview). Billed by fal per second of the audio, so it is priced on the
   MEASURED length, rounded UP to the whole second.

WHY NOT A ROW IN effects.EFFECTS. Every effect there takes ONE kind of
source (`takes`: image or video) and `apply_effect` runs whatever the menu
names; this takes a photo AND a sound, and the sound has its own limits and
a per-plan cap. A row there would be listed by `effects` and then refused
by `apply_effect` -- so, like `clip_edit`, this module keeps its own dated
rows and hands `effects.run` the (endpoint, body) to submit.

Read off each endpoint's OpenAPI schema
(fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>) and the
`endpointBilling` record / price on its model page, on CHECKED. Re-check
before trusting a number; fal changes these.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

CHECKED = "2026-10-20"

# --- OmniHuman v2: photo + audio -> clip -----------------------------------
TALK = {
    "id": "omnihuman-v2",
    "label": "OmniHuman v2",
    "endpoint": "bytedance/omnihuman/v2",
    # endpointBilling: billing_unit "seconds", price 0.105; the output's
    # `duration` is "duration of audio input/video output as used for billing"
    "usd_per_second": 0.105,
    "source": "https://fal.ai/models/bytedance/omnihuman/v2",
    "checked": CHECKED,
}
# the schema's own limits, every one refused before a quote
AUDIO_MIN_SECONDS = 4.0
AUDIO_MAX_SECONDS = 300.0         # the model's; a plan's cap is below it
AUDIO_MAX_BYTES = 15 * 1024 * 1024
AUDIO_TYPES = (".mp3", ".wav")
IMAGE_MIN_PX, IMAGE_MAX_PX = 300, 6000
IMAGE_MIN_RATIO, IMAGE_MAX_RATIO = 0.4, 2.5
# "Supported languages: Chinese, English, Japanese, Korean, Spanish
# (Mexican) and Indonesian" -- for the PROMPT only; the audio may be any
# language. Not enforced (a prompt is advice to the model).
PROMPT_MAX = 1000

# Audio length per plan (Mike, 2026-10-20): the dearest clip a plan can
# make is 30s / 60s / 120s x $0.105 = $3.15 / $6.30 / $12.60. An account
# with no plan (the sign-up trial) gets Starter's: its credits are the wall.
PLAN_AUDIO_CAP = {"starter": 30, "creator": 60, "studio": 120}
DEFAULT_AUDIO_CAP = PLAN_AUDIO_CAP["starter"]

# --- ElevenLabs v3: script -> voice ----------------------------------------
VOICE = {
    "id": "eleven-v3",
    "label": "ElevenLabs v3",
    "endpoint": "fal-ai/elevenlabs/tts/eleven-v3",
    "usd_per_1k_chars": 0.10,      # "$0.10 per 1,000 characters" (model page)
    "source": "https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3",
    "checked": CHECKED,
}
# `text`: minLength 1, maxLength 5000 on the schema
SCRIPT_MAX_CHARS = 5000
# Under ~4 seconds the clip is refused (AUDIO_MIN_SECONDS), so a preview
# that would come out that short is refused BEFORE it is paid for. Speech
# runs ~14-16 characters a second; 50 characters is about 3.5s at the
# fastest, so a script under it cannot reach 4s and one over it usually
# does. The measured length still decides at the clip.
SCRIPT_MIN_CHARS = 50
# `voice` is a free string on the schema (default "Rachel"); these are the
# names its examples list. Anything else is refused, never passed through.
VOICES = ("Rachel", "Aria", "Roger", "Sarah", "Laura", "Charlie", "George", "Callum",
          "River", "Liam", "Charlotte", "Alice", "Matilda", "Will", "Jessica", "Eric",
          "Chris", "Brian", "Daniel", "Lily", "Bill")
DEFAULT_VOICE = "Rachel"
NORMALIZATION = ("auto", "on", "off")


# --- the money ---------------------------------------------------------------

def billed_seconds(seconds: float) -> int:
    """The audio's length as priced: whole seconds, rounded UP (fal bills
    the float; the quote is never under it)."""
    return int(math.ceil(float(seconds) - 1e-9))


def talk_usd(seconds: float) -> float:
    return round(billed_seconds(seconds) * TALK["usd_per_second"], 4)


def voice_usd(script: str) -> float:
    return round(len(script) * VOICE["usd_per_1k_chars"] / 1000, 6)


# --- the checks: every one before a quote -------------------------------------

def audio_cap(account_id: Optional[int], dsn=None) -> int:
    from . import accounts
    plan = accounts.plan_of(account_id, dsn=dsn) if account_id is not None else None
    return PLAN_AUDIO_CAP.get(plan or "", DEFAULT_AUDIO_CAP)


def check_audio(seconds: Optional[float], *, suffix: str, size_bytes: Optional[int],
                cap: int) -> float:
    """The voice track, or ValueError saying what to change."""
    suffix = (suffix or "").lower()
    if suffix not in AUDIO_TYPES:
        raise ValueError(f"the voice must be an .mp3 or .wav file, not {suffix or 'that'}")
    if size_bytes is not None and size_bytes > AUDIO_MAX_BYTES:
        raise ValueError(f"the voice file is {size_bytes / 1024 / 1024:.1f}MB; "
                         "the model takes up to 15MB")
    if seconds is None:
        raise ValueError("the voice track's length could not be measured, and the clip "
                         "is priced by it")
    seconds = float(seconds)
    if seconds < AUDIO_MIN_SECONDS:
        raise ValueError(f"the voice is {seconds:.1f}s; the model needs at least "
                         f"{AUDIO_MIN_SECONDS:g}s -- add a few words")
    limit = min(cap, AUDIO_MAX_SECONDS)
    if seconds > limit + 0.5:      # half a second of slack: a "30s" file measures 30.04
        raise ValueError(f"the voice is {seconds:.1f}s; your plan makes talking clips up to "
                         f"{limit:g}s -- trim it, or a bigger plan takes longer ones")
    return seconds


def check_image(width: Optional[int], height: Optional[int]) -> None:
    if not width or not height:
        raise ValueError("the photo's size could not be read")
    if not (IMAGE_MIN_PX <= width <= IMAGE_MAX_PX and IMAGE_MIN_PX <= height <= IMAGE_MAX_PX):
        raise ValueError(f"the photo is {width}x{height}; the model takes {IMAGE_MIN_PX} "
                         f"to {IMAGE_MAX_PX} pixels on each side")
    ratio = width / height
    if not IMAGE_MIN_RATIO <= ratio <= IMAGE_MAX_RATIO:
        raise ValueError(f"the photo's shape ({width}x{height}) is too narrow or too wide; "
                         "the model takes width/height between 0.4 and 2.5")


def check_prompt(prompt: str) -> str:
    prompt = " ".join((prompt or "").split())
    if len(prompt) > PROMPT_MAX:
        raise ValueError(f"the direction is {len(prompt)} characters; keep it under {PROMPT_MAX}")
    return prompt


def check_script(script: str) -> str:
    script = (script or "").strip()
    if not script:
        raise ValueError("a voice preview needs the words to say")
    if len(script) > SCRIPT_MAX_CHARS:
        raise ValueError(f"the script is {len(script)} characters; the voice model takes "
                         f"up to {SCRIPT_MAX_CHARS}")
    if len(script) < SCRIPT_MIN_CHARS:
        raise ValueError(f"the script is {len(script)} characters, which reads in under "
                         f"{AUDIO_MIN_SECONDS:g} seconds -- the shortest a talking photo "
                         f"takes. Write at least {SCRIPT_MIN_CHARS} characters")
    return script


def check_voice(voice: str) -> str:
    voice = (voice or "").strip() or DEFAULT_VOICE
    match = next((v for v in VOICES if v.lower() == voice.lower()), None)
    if match is None:
        raise ValueError(f"voice must be one of {list(VOICES)}, got {voice!r}")
    return match


def check_language(language: str) -> Optional[str]:
    """An ISO 639-1 code (two letters), or None to let the model tell."""
    language = (language or "").strip().lower()
    if not language:
        return None
    if len(language) != 2 or not language.isalpha():
        raise ValueError(f"language is a two-letter code like en, es or fr, got {language!r}")
    return language


# --- the bodies --------------------------------------------------------------

def talk_body(image_url: str, audio_url: str, prompt: str = "") -> tuple[str, dict]:
    body = {"image_url": image_url, "audio_url": audio_url}
    if prompt:
        body["prompt"] = prompt
    return TALK["endpoint"], body


def voice_body(script: str, voice: str, language: Optional[str] = None) -> tuple[str, dict]:
    body = {"text": script, "voice": voice}
    if language:
        body["language_code"] = language
    return VOICE["endpoint"], body


# --- making the voice fetchable ----------------------------------------------

def fetchable_audio(media_url: str, output_path: str = "", *,
                    account_id: Optional[int] = None) -> Optional[str]:
    """A voice track as a URL fal's servers can fetch: where the bucket
    holds it for this account, else this disk's file uploaded, else None
    (the caller refuses: a clip must not be paid for against a voice the
    renderer cannot hear)."""
    import hashlib

    from . import media, storage
    found = media.bucket_url_for(media_url, account_id)
    if found:
        return found
    path = Path(output_path) if output_path else None
    if path is None or not path.is_file() or not storage.configured():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    suffix = path.suffix.lower() or ".mp3"
    try:
        return storage.upload_file(
            path, key=media.object_key(f"refs/fal/{digest}{suffix}", account_id),
            content_type="audio/wav" if suffix == ".wav" else "audio/mpeg")
    except Exception:
        return None


def image_size(target: str) -> tuple[Optional[int], Optional[int]]:
    """(width, height) of a still by ffprobe (a path or a URL), or (None, None)."""
    import json
    import subprocess
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "json", str(target)],
            capture_output=True, text=True, timeout=60, check=True).stdout
        stream = json.loads(out)["streams"][0]
        return int(stream["width"]), int(stream["height"])
    except Exception:
        return None, None


# --- the two bodies, shared by both doors -------------------------------------
# The connector (mcp_server.run_voice_preview / run_talking_photo, a signed
# quote token) and the studio's card (app/api.py /api/talking-photo/*, the
# person's click at the price it showed) differ only in their gate and in how
# they turn a photo id into an address. Everything else is here, once.

def voice_request(script: str, voice: str = "", language: str = "") -> dict:
    """A voice preview checked and priced, nothing spent."""
    script = check_script(script)
    voice = check_voice(voice)
    language = check_language(language)
    return {"script": script, "voice": voice, "language": language,
            "characters": len(script), "usd": voice_usd(script)}


def run_voice(req: dict, *, account_id: Optional[int], dsn=None, source: str,
              quote=None) -> dict:
    """Read the script aloud (effects.run: the hold, the generations row,
    settle) and file the audio as an `asset:<id>` in the editor's media bin.
    Returns {ok, audio, seconds, stored, generation_id} or {ok: False, error}."""
    from . import effects
    from .cut import render, uploads
    res = effects.run(
        f"voice-{VOICE['id']}", [], req["script"], {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, quote=quote,
        row={"label": VOICE["label"], "output": "audio"},
        endpoint_body=voice_body(req["script"], req["voice"], req["language"]),
        extra={"voice_preview": {"voice": req["voice"], "language": req["language"],
                                 "characters": req["characters"]}})
    if not res.get("ok"):
        return res
    path = Path(res["path"])
    try:
        saved = uploads.save(path.read_bytes(), f"voice-{req['voice'].lower()}{path.suffix}",
                             account_id=account_id, media_dir=render.CUT_DIR / "media",
                             types={k: uploads.AUDIO_TYPES[k] for k in AUDIO_TYPES},
                             dsn=dsn)
    except (OSError, uploads.UploadRefused) as e:
        return {"ok": False, "generation_id": res.get("generation_id"),
                "error": f"the voice was made and paid for but could not be filed ({e})"}
    return {"ok": True, "audio": saved["handle"], "seconds": saved["info"].get("seconds"),
            "stored": saved["stored"], "generation_id": res.get("generation_id")}


def voice_row(ref: str, *, account_id: Optional[int], dsn=None) -> dict:
    """A talking photo's voice by id -> its `cut_media` row: an `asset:<id>`
    of kind audio. URLs are never taken."""
    from .cut import store as cut_store
    kind, _, rest = (ref or "").strip().partition(":")
    if kind != "asset" or not rest.isdigit():
        raise ValueError(f"{ref!r}: the voice is an asset:<id> -- a voice_preview, or an "
                         ".mp3 / .wav uploaded in the editor or imported. URLs are never taken")
    row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
    if not row:
        raise ValueError(f"no upload {rest} on this account")
    if row.get("kind") != "audio":
        raise ValueError(f"{ref} is {row.get('kind')}; the voice must be sound")
    return row


def check_consent(consent) -> None:
    if consent is not True:
        raise ValueError("`consent` must be true: ask the person to confirm the face in the "
                         "photo is theirs, or that its owner agreed to it being animated")


def talk_request(photo: str, audio: str, *, size: tuple, prompt: str = "",
                 account_id: Optional[int], dsn=None) -> dict:
    """A talking photo checked and priced, nothing spent. The door has
    already checked the consent and turned `photo` into `size` (width,
    height); this checks the photo's size and shape, the voice's format,
    size and MEASURED length against the plan's cap, makes the voice
    fetchable for the renderer, and prices it in whole seconds."""
    check_image(*size)
    row = voice_row(audio, account_id=account_id, dsn=dsn)
    local = row.get("output_path") or ""
    nbytes = Path(local).stat().st_size if local and Path(local).is_file() else None
    suffix = Path((row.get("media_url") or row.get("filename") or "").split("?", 1)[0]).suffix
    cap = audio_cap(account_id, dsn)
    seconds = check_audio(row.get("seconds"), suffix=suffix, size_bytes=nbytes, cap=cap)
    audio_url = fetchable_audio(row.get("media_url") or "", local, account_id=account_id)
    if not audio_url:
        raise ValueError(f"{audio} cannot be made fetchable for the renderer (its file is "
                         "not in the studio's bucket)")
    return {"photo": photo, "audio": audio, "prompt": prompt, "seconds": seconds,
            "billed_seconds": billed_seconds(seconds), "cap": cap,
            "width": size[0], "height": size[1], "audio_url": audio_url,
            "usd": talk_usd(seconds)}


def run_talk(req: dict, image_url: str, *, account_id: Optional[int], dsn=None,
             source: str, quote=None, project_id: Optional[int] = None) -> dict:
    """Render the clip (effects.run: the hold, the generations row, settle,
    the Assets wall)."""
    from . import effects
    return effects.run(
        f"talk-{TALK['id']}", [image_url], req["prompt"], {}, usd=req["usd"],
        sources=[req["photo"], req["audio"]], account_id=account_id, db_path=dsn,
        source=source, project_id=project_id, quote=quote,
        row={"label": TALK["label"], "output": "video"},
        endpoint_body=talk_body(image_url, req["audio_url"], req["prompt"]),
        extra={"talking_photo": {"photo": req["photo"], "audio": req["audio"],
                                 "audio_seconds": round(req["seconds"], 3), "consent": True}})


__all__ = ["CHECKED", "TALK", "VOICE", "VOICES", "DEFAULT_VOICE", "PLAN_AUDIO_CAP",
           "DEFAULT_AUDIO_CAP", "AUDIO_MIN_SECONDS", "AUDIO_MAX_SECONDS",
           "SCRIPT_MIN_CHARS", "SCRIPT_MAX_CHARS", "billed_seconds", "talk_usd",
           "voice_usd", "audio_cap", "check_audio", "check_image", "check_prompt",
           "check_script", "check_voice", "check_language", "talk_body", "voice_body",
           "fetchable_audio", "image_size", "voice_request", "run_voice", "voice_row",
           "check_consent", "talk_request", "run_talk"]
