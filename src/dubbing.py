"""
Dub a clip into another language (2026-10-26).

A clip that already has speech on it, spoken again in another language, in
the same voices: ElevenLabs Dubbing on fal. It is the gap the studio had
against Higgsfield's `dubbing` and Runway's `localize_ad`, and it is one
spend, priced before anything runs:

    video + target language  ->  the same video with its speech dubbed

It goes through `effects.run` exactly as `talking_photo` and `clip_edit` do
(the cap, the CREDIT HOLD before the submit, the generations row, settle,
the Library) with the endpoint handed in as `row` + `endpoint_body`, so no
third spending path grows beside it. It is deliberately NOT a row of
`effects.EFFECTS`: there `apply_effect` would run it in one call with no
consent, and it takes a language, not an option list.

WHY A CONSENT. The dub re-speaks the people on the clip in their own voices.
That is a likeness question in the same family as a talking photo's, so the
door asks the person to confirm the voices are theirs, or that whoever they
belong to agreed (`check_consent`, never pre-ticked, never set for them).

Read off the model page on CHECKED (fal.ai/models/fal-ai/elevenlabs/dubbing):
  * endpoint `fal-ai/elevenlabs/dubbing`; `audio_url` OR `video_url` (video
    wins when both are given); `target_lang` required, ISO 639-1;
    `source_lang` optional (auto-detected); `num_speakers` 1-50 optional
    (auto-detected); `highest_resolution` boolean, default true;
  * output: `video` (when a video went in), `audio`, `target_lang`;
  * "$0.6 per minute of media", rounded UP to the next whole minute.
The page lists NO file-size, length or format limits and names only six
target languages as examples, so:
  * LANGUAGES is those six and nothing else. Adding one is a one-line change
    once a live run has proved it (see docs/tasks/task-dubbing.md);
  * MAX_SECONDS is the studio's own guard, not the model's.
"""
from __future__ import annotations

import math
import subprocess
from typing import Optional

CHECKED = "2026-10-26"

DUB = {
    "id": "elevenlabs-dubbing",
    "label": "ElevenLabs Dubbing",
    "endpoint": "fal-ai/elevenlabs/dubbing",
    # "$0.6 per minute of media. Duration is rounded up to the next whole
    # minute for billing."
    "usd_per_minute": 0.60,
    "source": "https://fal.ai/models/fal-ai/elevenlabs/dubbing",
    "checked": CHECKED,
}

# The target languages the model page names (its examples). A language off
# this list is refused before a quote, never passed through.
LANGUAGES = {
    "es": "Spanish", "fr": "French", "de": "German",
    "ja": "Japanese", "pt": "Portuguese", "zh": "Chinese",
}
LANGUAGE_CODES = tuple(LANGUAGES)

# The studio's guard (the page states no limit): five minutes is $3.00 of
# fal, 720 credits at the standard markup.
MAX_SECONDS = 300.0
SPEAKERS_MIN, SPEAKERS_MAX = 1, 50


# --- the money ---------------------------------------------------------------

def billed_minutes(seconds: float) -> int:
    """The clip's length as fal bills it: whole minutes, rounded UP, never
    under one (a nine-second clip is a minute)."""
    return max(1, int(math.ceil(float(seconds) / 60.0 - 1e-9)))


def dub_usd(seconds: float) -> float:
    return round(billed_minutes(seconds) * DUB["usd_per_minute"], 4)


# --- the checks: every one before a quote ------------------------------------

def check_language(target: str) -> str:
    """The target language as its code, or ValueError listing the offered."""
    code = (target or "").strip().lower()
    if code not in LANGUAGES:
        offered = ", ".join(f"{c} ({n})" for c, n in LANGUAGES.items())
        raise ValueError(f"target language must be one of {offered}, got {target!r}")
    return code


def check_source_language(source: str, target: str) -> Optional[str]:
    """The language spoken on the clip as a two-letter code, or None to let
    the model tell. It may be any language the model hears, so only its
    shape is checked; it cannot be the language being dubbed into."""
    code = (source or "").strip().lower()
    if not code:
        return None
    if len(code) != 2 or not code.isalpha():
        raise ValueError(f"the spoken language is a two-letter code like en, es or fr, "
                         f"got {source!r}")
    if code == target:
        raise ValueError(f"the clip is already in {LANGUAGES.get(target, target)} -- "
                         "pick a different target language")
    return code


def check_speakers(speakers) -> Optional[int]:
    """How many people talk, or None to let the model count."""
    if speakers in (None, "", 0):
        return None
    try:
        n = int(speakers)
    except (TypeError, ValueError):
        raise ValueError(f"speakers is a whole number, got {speakers!r}") from None
    if not SPEAKERS_MIN <= n <= SPEAKERS_MAX:
        raise ValueError(f"speakers is {SPEAKERS_MIN} to {SPEAKERS_MAX}, got {n}")
    return n


def check_consent(consent) -> None:
    if consent is not True:
        raise ValueError("`consent` must be true: ask the person to confirm the voices on the "
                         "clip are theirs, or that whoever they belong to agreed to it being "
                         "dubbed -- the dub re-speaks them in their own voices")


def check_clip(probe: dict, has_sound: Optional[bool]) -> float:
    """The clip's length in seconds, or ValueError saying what to change.
    A clip with no sound track has nothing to dub, and a clip whose sound
    could not be checked is not paid for blind."""
    seconds = float((probe or {}).get("seconds") or 0)
    if seconds <= 0:
        raise ValueError("the clip's length could not be measured, and the dub is priced by it")
    if has_sound is None:
        raise ValueError("the clip's sound could not be checked -- the dub needs a clip "
                         "with a voice on it")
    if not has_sound:
        raise ValueError("this clip has no sound track, so there is nothing to dub. Add the "
                         "voice first (sound, or a talking photo), then dub it")
    if seconds > MAX_SECONDS:
        raise ValueError(f"the clip is {seconds:.0f}s; a dub takes up to {MAX_SECONDS:.0f}s "
                         "-- trim it first")
    return seconds


def has_sound(target: str) -> Optional[bool]:
    """Whether a clip (a path or a URL) carries an audio stream, by
    ffprobe; None when it could not be read."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", str(target)],
            capture_output=True, text=True, timeout=60, check=True).stdout
    except Exception:
        return None
    return "audio" in out


# --- the body ----------------------------------------------------------------

def dub_body(video_url: str, target: str, source_lang: Optional[str] = None,
             speakers: Optional[int] = None) -> tuple[str, dict]:
    """(endpoint, body) in the model's wire shape. `highest_resolution` is
    left at the model's default (true)."""
    body: dict = {"video_url": video_url, "target_lang": target}
    if source_lang:
        body["source_lang"] = source_lang
    if speakers:
        body["num_speakers"] = int(speakers)
    return DUB["endpoint"], body


# --- the request, shared by both doors ---------------------------------------
# The connector (mcp_server.run_dub_clip, a signed quote token) and the
# studio (app/api.py /api/dubbing/*, the person's click at the price it
# showed) differ only in their gate. Everything else is here, once.

def request(source: str, target: str, *, source_lang: str = "", speakers=None,
            account_id: Optional[int], dsn=None) -> dict:
    """A dub checked and priced, nothing spent. `source` is a clip by id
    (`gen:<id>` on the Assets wall, or an `asset:<id>` imported); a URL is
    never taken. Raises ValueError saying what is wrong."""
    from . import effects, mcp_server
    target = check_language(target)
    source_lang = check_source_language(source_lang, target)
    speakers = check_speakers(speakers)
    source = (source or "").strip()
    if not source:
        raise ValueError("a dub needs `source`: the clip to dub, by id")
    row = mcp_server._clip_row(source, dsn, account_id)
    local = row.get("output_path") or ""
    file, _suffix, _size = mcp_server._clip_file(row, account_id)
    probe = effects.probe_video(file)
    seconds = check_clip(probe, has_sound(file))
    video_url = effects.fetchable_video(row["media_url"], local, account_id=account_id)
    if not video_url:
        raise ValueError(f"{source} cannot be made fetchable for the renderer (its file is "
                         "not in the studio's bucket)")
    return {"source": source, "target": target, "language": LANGUAGES[target],
            "source_lang": source_lang, "speakers": speakers, "seconds": seconds,
            "billed_minutes": billed_minutes(seconds), "video_url": video_url,
            "probe": probe, "usd": dub_usd(seconds)}


def run(req: dict, *, account_id: Optional[int], dsn=None, source: str, quote=None,
        project_id: Optional[int] = None) -> dict:
    """Dub the clip (effects.run: the hold, the generations row, settle, the
    Assets wall). Returns effects.run's {ok, media_url, asset_id, ...}."""
    from . import effects
    return effects.run(
        f"dub-{req['target']}", [req["video_url"]], f"Dubbed into {req['language']}", {},
        usd=req["usd"], sources=[req["source"]], account_id=account_id, db_path=dsn,
        source=source, project_id=project_id, quote=quote,
        row={"label": DUB["label"], "output": "video"},
        endpoint_body=dub_body(req["video_url"], req["target"], req["source_lang"],
                               req["speakers"]),
        extra={"dubbing": {"source": req["source"], "target": req["target"],
                           "source_lang": req["source_lang"], "speakers": req["speakers"],
                           "clip_seconds": round(req["seconds"], 3),
                           "billed_minutes": req["billed_minutes"], "consent": True}})


def menu() -> dict:
    """What a dub card offers: the languages and the price rule. Browsing it
    runs nothing and costs nothing."""
    return {"languages": [{"code": c, "name": n} for c, n in LANGUAGES.items()],
            "max_seconds": MAX_SECONDS, "speakers_max": SPEAKERS_MAX,
            "label": DUB["label"], "checked": CHECKED}


__all__ = ["CHECKED", "DUB", "LANGUAGES", "LANGUAGE_CODES", "MAX_SECONDS", "billed_minutes",
           "dub_usd", "check_language", "check_source_language", "check_speakers",
           "check_consent", "check_clip", "has_sound", "dub_body", "request", "run", "menu"]
