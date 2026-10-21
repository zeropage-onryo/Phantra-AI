"""A voiceover for a cut (2026-10-21, docs/tasks/task-music-layer.md, "the
default voice").

The kit has stored a default voice (`sound.voice`) since it was built, and
nothing read it. This reads a typed script aloud for the editor's Audio tab,
priced before it is made:

  * the VOICE is the person's pick; with none, the kit's default when that
    line names one of the voices the model offers (`talking_photo.VOICES`),
    else the model's own default. A kit line that names no offered voice
    ("warm, mid-30s, unhurried") is shown beside the picker, never sent;
  * the PRICE is the talking photo's voice preview's: per character on
    ElevenLabs v3 (`talking_photo.voice_usd`), the same endpoint and body;
  * it runs through `effects.run` (the cap, the CREDIT HOLD before the
    submit, the generations row, settle), and the read is filed as an
    `asset:<id>` audio in the editor's media bin, so the editor lays it on
    the voice track with its ordinary, undoable ops.

Unlike the talking photo's preview there is no 50-character floor: that
floor exists because the talking clip refuses audio under four seconds, and
a voiceover line can be three words.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from . import talking_photo as tp

SCRIPT_MAX_CHARS = tp.SCRIPT_MAX_CHARS


def kit_line(kit: Optional[dict]) -> str:
    """The kit's default-voice line as written, or ""."""
    if not kit:
        return ""
    return (((kit.get("spec") or {}).get("sound") or {}).get("voice") or "").strip()


def kit_voice(kit: Optional[dict]) -> Optional[str]:
    """The offered voice the kit's line names, as a whole word, or None."""
    line = kit_line(kit)
    for name in tp.VOICES:
        if re.search(rf"\b{re.escape(name)}\b", line, re.IGNORECASE):
            return name
    return None


def check_script(script: str) -> str:
    script = (script or "").strip()
    if not script:
        raise ValueError("write the words to be read")
    if len(script) > SCRIPT_MAX_CHARS:
        raise ValueError(f"the script is {len(script)} characters; the voice model takes "
                         f"up to {SCRIPT_MAX_CHARS}")
    return script


def request(script: str, voice: str = "", language: str = "",
            kit: Optional[dict] = None) -> dict:
    """A voiceover checked and priced, nothing spent. Raises ValueError
    saying what is wrong -- a voice off the model's list is refused."""
    script = check_script(script)
    picked = tp.check_voice(voice or kit_voice(kit) or tp.DEFAULT_VOICE)
    return {"script": script, "voice": picked, "language": tp.check_language(language),
            "characters": len(script), "usd": tp.voice_usd(script),
            "label": tp.VOICE["label"]}


def run(req: dict, *, account_id: Optional[int], dsn=None, source: str, quote=None,
        project_id: Optional[int] = None) -> dict:
    """Read the script (effects.run: the hold, the generations row, settle)
    and file it as an `asset:<id>` audio in the editor's media bin. Returns
    {ok, audio, seconds, stored, generation_id} or {ok: False, error}."""
    from . import effects
    from .cut import render, uploads
    res = effects.run(
        f"voiceover-{tp.VOICE['id']}", [], req["script"], {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, quote=quote,
        project_id=project_id,
        row={"label": tp.VOICE["label"], "output": "audio"},
        endpoint_body=tp.voice_body(req["script"], req["voice"], req["language"]),
        extra={"voiceover": {"voice": req["voice"], "language": req["language"],
                             "characters": req["characters"]}})
    if not res.get("ok"):
        return res
    path = Path(res["path"])
    name = f"voiceover-{req['voice'].lower()}{path.suffix}"
    try:
        saved = uploads.save(path.read_bytes(), name, account_id=account_id,
                             media_dir=render.CUT_DIR / "media", types=uploads.AUDIO_TYPES,
                             dsn=dsn)
    except (OSError, uploads.UploadRefused) as e:
        return {"ok": False, "generation_id": res.get("generation_id"),
                "error": f"the voiceover was made and paid for but could not be filed ({e})"}
    return {"ok": True, "audio": saved["handle"], "seconds": saved["info"].get("seconds"),
            "stored": saved["stored"], "generation_id": res.get("generation_id")}
