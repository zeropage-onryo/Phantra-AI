"""
Voice cloning (2026-10-27, docs/tasks/task-voice-tab.md).

Mike's rules, 2026-10-27: a person may clone ONLY THEIR OWN voice, and proves
it by READING A CONSENT LINE. So the sample they upload starts with the line
below, read aloud in the voice being cloned, and the studio listens for it
(fal Whisper) before anything is paid for: no line heard, no clone, nothing
charged. The same recording carries the consent and the voice, so the voice
that agreed is the voice that is copied.

    sample (asset:<id>, 10 s - 5 min) -> Whisper hears the consent line
        -> MiniMax Voice Clone (fal)  -> a custom voice id, kept per account
        -> the voice library reads scripts in it (src/voice_models.py)

Read on CHECKED (fal.ai/models/fal-ai/minimax/voice-clone + /api):
  * `audio_url` "should be at least 10 seconds long"; accepted types mp3, ogg,
    wav, m4a, aac; `noise_reduction`, `need_volume_normalization`, `accuracy`;
    `text` a preview read in the new voice, on `model` (default speech-02-hd);
  * output `custom_voice_id` and `audio` (the preview);
  * "Each voice clone request will cost $1.5, with preview inputs costing $0.3
    per 1000 characters";
  * "To retain the voice permanently, use it with a TTS (text-to-speech)
    endpoint at least once within 7 days", else it "will be automatically
    deleted". Whether the clone's own preview counts as that use is NOT
    stated, so a clone counts as unused until its first library read here.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

from . import db

CHECKED = "2026-10-27"

CLONE = {
    "id": "minimax-voice-clone",
    "label": "MiniMax Voice Clone",
    "endpoint": "fal-ai/minimax/voice-clone",
    "usd_per_clone": 1.50,
    "usd_per_1k_preview_chars": 0.30,
    "source": "https://fal.ai/models/fal-ai/minimax/voice-clone",
    "checked": CHECKED,
}
CONSENT_LINE = "This is my own voice, and I agree to Phantra making a copy of it."
PREVIEW_TEXT = "Hello. This is my voice, made in Phantra."
SAMPLE_MIN_SECONDS = 10.0          # the model page
SAMPLE_MAX_SECONDS = 300.0         # the studio's guard
SAMPLE_TYPES = (".mp3", ".wav", ".m4a", ".ogg", ".aac")   # the model page's list
NAME_MAX = 40
MAX_CLONES = 10                    # per account: a clone is $1.50 and a real person's voice
KEEP_DAYS = 7                      # unused this long, MiniMax deletes it
# how much of the consent line must be heard, in order, near the start
CONSENT_MATCH = 0.8
CONSENT_WINDOW_EXTRA = 25          # words after the line's length that may hold it
WHISPER = "fal-ai/whisper"

SCHEMA = """
CREATE TABLE IF NOT EXISTS voice_clones (
    id              BIGSERIAL PRIMARY KEY,
    account_id      BIGINT,
    voice_id        TEXT NOT NULL,
    name            TEXT NOT NULL,
    sample          TEXT NOT NULL,
    consent_heard   TEXT NOT NULL,
    consent_score   REAL NOT NULL,
    preview_audio   TEXT,
    generation_id   BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ,
    removed_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voice_clones_account ON voice_clones (account_id, created_at);
"""

_ready: set[str] = set()


def init(dsn: Optional[str] = None) -> None:
    """Create and own the table. Idempotent; the app lifespan runs it."""
    with db.connect(dsn) as conn:
        conn.execute(SCHEMA)
        db.own_table(conn, "voice_clones")
    _ready.add(db.resolve_dsn(dsn))


def ensure(dsn: Optional[str] = None) -> None:
    if db.resolve_dsn(dsn) in _ready:
        return
    db.run_init(lambda: init(dsn), dsn)


# --- the money ---------------------------------------------------------------

def clone_usd() -> float:
    preview = len(PREVIEW_TEXT) * CLONE["usd_per_1k_preview_chars"] / 1000
    return round(CLONE["usd_per_clone"] + preview, 6)


# --- the consent line --------------------------------------------------------

def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower().replace("’", "'"))


def consent_score(transcript: str) -> float:
    """How much of the consent line was heard, in order, near the start of
    the transcript: 0..1 (matched words / the line's words)."""
    line = _words(CONSENT_LINE)
    heard = _words(transcript)[: len(line) + CONSENT_WINDOW_EXTRA]
    if not heard:
        return 0.0
    blocks = SequenceMatcher(None, line, heard, autojunk=False).get_matching_blocks()
    return round(sum(b.size for b in blocks) / len(line), 3)


def consent_heard(transcript: str) -> bool:
    return consent_score(transcript) >= CONSENT_MATCH


# --- the checks: every one before a quote ------------------------------------

def check_name(name: str) -> str:
    name = " ".join((name or "").split())
    if not name:
        raise ValueError("name the voice, so you can find it in the library")
    if len(name) > NAME_MAX:
        raise ValueError(f"keep the name under {NAME_MAX} characters")
    return name


def check_sample(seconds: Optional[float], suffix: str) -> float:
    suffix = (suffix or "").lower()
    if suffix not in SAMPLE_TYPES:
        raise ValueError(f"the sample must be {', '.join(SAMPLE_TYPES)}, not {suffix or 'that'}")
    if seconds is None:
        raise ValueError("the sample's length could not be measured")
    seconds = float(seconds)
    if seconds < SAMPLE_MIN_SECONDS:
        raise ValueError(f"the sample is {seconds:.1f}s; the model needs at least "
                         f"{SAMPLE_MIN_SECONDS:g}s -- read the line, then keep talking")
    if seconds > SAMPLE_MAX_SECONDS + 0.5:
        raise ValueError(f"the sample is {seconds:.0f}s; a clone takes up to "
                         f"{SAMPLE_MAX_SECONDS:g}s -- trim it")
    return seconds


def request(sample: str, name: str, *, account_id: Optional[int], dsn=None) -> dict:
    """A clone checked and priced, nothing spent. The consent line is heard
    at the run, before the spend, because hearing it is a model call."""
    from . import talking_photo as tp
    name = check_name(name)
    if len(clones(account_id=account_id, dsn=dsn)) >= MAX_CLONES:
        raise ValueError(f"you have {MAX_CLONES} voices; remove one before making another")
    row = tp.voice_row(sample, account_id=account_id, dsn=dsn)
    local = row.get("output_path") or ""
    suffix = Path((row.get("media_url") or row.get("filename") or "").split("?", 1)[0]).suffix
    seconds = check_sample(row.get("seconds"), suffix)
    audio_url = tp.fetchable_audio(row.get("media_url") or "", local, account_id=account_id)
    if not audio_url:
        raise ValueError(f"{sample} cannot be made fetchable for the model (its file is not in "
                         "the studio's bucket)")
    return {"sample": sample, "name": name, "seconds": seconds, "audio_url": audio_url,
            "usd": clone_usd(), "label": CLONE["label"]}


def clone_body(audio_url: str) -> tuple[str, dict]:
    return CLONE["endpoint"], {"audio_url": audio_url, "text": PREVIEW_TEXT,
                               "model": "speech-02-hd", "noise_reduction": True,
                               "need_volume_normalization": True}


# --- the run -----------------------------------------------------------------

def hear(audio_url: str, *, account_id: Optional[int], seconds: float, http=None) -> str:
    """The sample's words (fal Whisper). An operator cost on the transcribe
    stage, like the editor's index: hearing the line is the studio's check."""
    from . import fal, spend
    from .cut import index
    ok = False
    try:
        result, _ = fal._submit_and_wait(WHISPER, {"audio_url": audio_url, "task": "transcribe"},
                                         http=http, account_id=account_id)
        ok = True
    finally:
        spend.record_call(stage="transcribe", model_asked=WHISPER, usage={}, ok=ok,
                          account_id=account_id, cost_usd=index.whisper_usd(seconds))
    text = result.get("text")
    if not isinstance(text, str):
        text = " ".join(str(c.get("text") or "") for c in result.get("chunks") or [])
    return text.strip()


NOT_HEARD = ("the consent line was not heard at the start of the sample, so no clone was made "
             "and nothing was charged. Start the recording by reading: “" + CONSENT_LINE +
             "”, in your own voice, then keep talking")


def run(req: dict, *, account_id: Optional[int], dsn=None, source: str,
        project_id: Optional[int] = None, http=None) -> dict:
    """Hear the consent line, then clone (effects.run: the hold, the
    generations row, settle) and keep the voice. Never raises:
    {ok, voice_id, name, audio, seconds, stored} or {ok: False, error}."""
    from . import effects, voice_models
    try:
        transcript = hear(req["audio_url"], account_id=account_id, seconds=req["seconds"], http=http)
    except Exception as e:
        return {"ok": False, "error": f"the sample could not be heard ({type(e).__name__}); "
                                      "nothing was charged"}
    score = consent_score(transcript)
    if score < CONSENT_MATCH:
        return {"ok": False, "error": NOT_HEARD, "consent_score": score}
    res = effects.run(
        f"voice-{CLONE['id']}", [], f"voice clone: {req['name']}", {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, project_id=project_id,
        row={"label": CLONE["label"], "output": "audio"},
        endpoint_body=clone_body(req["audio_url"]),
        extra={"voice_clone": {"name": req["name"], "sample": req["sample"],
                               "consent_score": score}})
    if not res.get("ok"):
        return res
    voice_id = str(((res.get("result") or {}).get("custom_voice_id")) or "").strip()
    if not voice_id:
        return {"ok": False, "generation_id": res.get("generation_id"),
                "error": "the clone was made and paid for but the model sent back no voice id"}
    filed = voice_models.file_audio(res, f"clone-{_slug(req['name'])}", account_id=account_id,
                                    dsn=dsn)
    keep(account_id=account_id, voice_id=voice_id, name=req["name"], sample=req["sample"],
         consent_heard=transcript[:500], consent_score=score,
         preview_audio=filed.get("audio") if filed.get("ok") else None,
         generation_id=res.get("generation_id"), dsn=dsn)
    return {"ok": True, "voice_id": voice_id, "name": req["name"],
            "audio": filed.get("audio"), "seconds": filed.get("seconds"),
            "stored": filed.get("stored"), "generation_id": res.get("generation_id")}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "voice"


# --- the store: one account's cloned voices ----------------------------------

def keep(*, account_id: Optional[int], voice_id: str, name: str, sample: str,
         consent_heard: str, consent_score: float, preview_audio: Optional[str],
         generation_id: Optional[int], dsn=None) -> None:
    ensure(dsn)
    with db.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO voice_clones (account_id, voice_id, name, sample, consent_heard, "
            "consent_score, preview_audio, generation_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (account_id, voice_id, name, sample, consent_heard, consent_score, preview_audio,
             generation_id))


def _expires(created: datetime, used: Optional[datetime]) -> Optional[datetime]:
    """When MiniMax deletes it: a week after it was made, unless it has been
    read in since (then it is kept)."""
    return None if used else created + timedelta(days=KEEP_DAYS)


def clones(*, account_id: Optional[int], dsn=None, now: Optional[datetime] = None) -> list[dict]:
    """This account's voices, newest first, without the ones removed or
    gone (a week unused). Never raises: no table yet is no voices."""
    now = now or datetime.now(timezone.utc)
    try:
        ensure(dsn)
        with db.connect(dsn) as conn:
            rows = conn.execute(
                "SELECT voice_id, name, preview_audio, created_at, last_used_at FROM voice_clones "
                "WHERE account_id IS NOT DISTINCT FROM %s AND removed_at IS NULL "
                "ORDER BY created_at DESC, id DESC", (account_id,)).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        expires = _expires(r["created_at"], r["last_used_at"])
        if expires is not None and expires <= now:
            continue
        out.append({"id": r["voice_id"], "name": r["name"], "preview_audio": r["preview_audio"],
                    "created_at": r["created_at"].isoformat(),
                    "expires_at": expires.isoformat() if expires else None,
                    "kept": r["last_used_at"] is not None})
    return out


def names(*, account_id: Optional[int], dsn=None) -> dict[str, str]:
    """voice id -> name, for the library's check and its labels."""
    return {c["id"]: c["name"] for c in clones(account_id=account_id, dsn=dsn)}


def touch(voice_id: str, *, account_id: Optional[int], dsn=None) -> None:
    """A read was made in this voice: MiniMax keeps it now."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        conn.execute(
            "UPDATE voice_clones SET last_used_at = now() WHERE account_id IS NOT DISTINCT FROM %s "
            "AND voice_id = %s AND removed_at IS NULL", (account_id, voice_id))


def remove(voice_id: str, *, account_id: Optional[int], dsn=None) -> bool:
    """Take a voice off this account's list (the row is kept, marked)."""
    ensure(dsn)
    with db.connect(dsn) as conn:
        cur = conn.execute(
            "UPDATE voice_clones SET removed_at = now() WHERE account_id IS NOT DISTINCT FROM %s "
            "AND voice_id = %s AND removed_at IS NULL", (account_id, voice_id))
        return cur.rowcount > 0


def _preview_url(asset: Optional[str], *, account_id: Optional[int], dsn=None) -> Optional[str]:
    """Where the page plays a voice's preview: its bin row's address."""
    kind, _, rest = (asset or "").partition(":")
    if kind != "asset" or not rest.isdigit():
        return None
    try:
        from .cut import store as cut_store
        row = cut_store.get_media(int(rest), account_id=account_id, dsn=dsn)
    except Exception:
        return None
    return (row or {}).get("media_url") or None


def menu(*, account_id: Optional[int], dsn=None) -> dict[str, Any]:
    voices = [{**v, "preview_url": _preview_url(v["preview_audio"], account_id=account_id, dsn=dsn)}
              for v in clones(account_id=account_id, dsn=dsn)]
    return {"consent_line": CONSENT_LINE, "min_seconds": SAMPLE_MIN_SECONDS,
            "max_seconds": SAMPLE_MAX_SECONDS, "types": list(SAMPLE_TYPES),
            "name_max": NAME_MAX, "max_clones": MAX_CLONES, "keep_days": KEEP_DAYS,
            "voices": voices}


__all__ = ["CHECKED", "CLONE", "CONSENT_LINE", "PREVIEW_TEXT", "clone_usd", "consent_score",
           "consent_heard", "check_name", "check_sample", "request", "clone_body", "hear",
           "run", "keep", "clones", "names", "touch", "remove", "menu", "init", "ensure"]
