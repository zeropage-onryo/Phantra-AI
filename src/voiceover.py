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

`write_script` drafts the words (free, one model call, stage
`voiceover_script`): the kit's voice rules, the cut's on-screen text and its
length in, a script out, checked against reality -- too long, a number the
inputs never give, a word the kit bans -- each a visible warning, never a
rejection. The person reads it in the box before anything is priced.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

from . import talking_photo as tp

SCRIPT_MAX_CHARS = tp.SCRIPT_MAX_CHARS
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
WORDS_PER_SECOND = 2.5
BRAIN = "fast"
SCHEMA = {"type": "object", "properties": {"script": {"type": "string"}},
          "required": ["script"]}


class ScriptError(Exception):
    """The script was not written; the message says why, in plain words."""


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


# --------------------------------------------------------------------------
# writing the script (free: one model call)
# --------------------------------------------------------------------------

def screen_lines(doc: dict) -> list[str]:
    """The words on screen in time order: headlines, labels and caption
    cues, each once."""
    found = []
    for t in doc.get("tracks", []):
        for g in t.get("items", []) or []:
            if g.get("type") in ("headline", "label") and (g.get("text") or "").strip():
                found.append((int(g["start"]), g["text"].strip()))
        for q in t.get("cues", []) or []:
            if (q.get("text") or "").strip():
                found.append((int(q["start"]), q["text"].strip()))
    return list(dict.fromkeys(text for _, text in sorted(found, key=lambda x: x[0])))


def word_budget(seconds: float) -> int:
    return max(3, int(round(seconds * WORDS_PER_SECOND)))


def build_prompt(doc: dict, kit: Optional[dict], direction: str = "") -> str:
    from .cut import motion_ad
    seconds = max(1.0, doc.get("duration", 0) / (doc.get("fps") or 30))
    words = word_budget(seconds)
    screen = screen_lines(doc)
    return ((PROMPTS_DIR / "voiceover_script_prompt.txt").read_text()
            .replace("{brand}", motion_ad.brand_block(kit))
            .replace("{screen}", "\n".join(f"- {ln}" for ln in screen) if screen
                     else "(nothing -- the picture carries no text)")
            .replace("{direction}", " ".join((direction or "").split())
                     or "(nothing more -- write the ad's voiceover from the above)")
            .replace("{seconds}", f"{seconds:g}")
            .replace("{words}", str(words))
            .replace("{words_max}", str(int(words * 1.2))))


def _model(prompt: str, *, account_id: Optional[int]) -> dict:
    """THE seam a test replaces: one structured call, JSON back."""
    from google.genai import types

    from . import gemini_utils
    if not gemini_utils.api_key_for(account_id):
        raise ScriptError("this server has no Gemini key, so the script cannot be written")
    client = gemini_utils.client_for(account_id)
    brain = gemini_utils.resolve_brain(BRAIN)
    config = brain["config"] or types.GenerateContentConfig()
    config.response_mime_type = "application/json"
    config.response_json_schema = SCHEMA
    raw = gemini_utils.generate_with_retry(client, brain["model"], prompt, config=config,
                                           fallbacks=brain["fallbacks"],
                                           stage="voiceover_script", account_id=account_id)
    return json.loads(raw)


def clean_script(raw: Any, *, seconds: float, kit: Optional[dict], facts: str) -> dict:
    """{"script", "warnings"}: the model's words, each thing to check said.
    Raises ScriptError when nothing usable came back."""
    from .cut import motion_ad
    text = (raw or {}).get("script") if isinstance(raw, dict) else None
    script = " ".join(str(text or "").split()).strip().strip('"\u201c\u201d').strip()
    if not script:
        raise ScriptError("the script came back empty. Nothing was charged.")
    warnings = []
    if len(script) > SCRIPT_MAX_CHARS:
        script = script[:SCRIPT_MAX_CHARS].rsplit(" ", 1)[0]
        warnings.append(f"the script was cut to {SCRIPT_MAX_CHARS} characters")
    words, budget = len(script.split()), word_budget(seconds)
    if words > budget * 1.3:
        warnings.append(f"it is {words} words, about {words / WORDS_PER_SECOND:.0f}s read "
                        f"aloud, on a {seconds:g}s cut -- trim it or it runs past the picture")
    made_up = motion_ad.unsourced_numbers(script, facts)
    if made_up:
        warnings.append(f"it says {', '.join(made_up)}, which nothing above gives "
                        "-- check it is true")
    banned = ((kit or {}).get("spec") or {}).get("voice", {}).get("avoid") or []
    said = [w for w in banned
            if re.search(rf"\b{re.escape(w)}\b", script, re.IGNORECASE)]
    if said:
        warnings.append(f"it uses {', '.join(said)}, which the kit says never to use")
    return {"script": script, "warnings": warnings}


def write_script(doc: dict, kit: Optional[dict], direction: str = "", *,
                 account_id: Optional[int],
                 model: Optional[Callable[..., dict]] = None) -> dict:
    """A voiceover script for this cut: {"script", "warnings", "words"}.
    Raises ScriptError; never spends credits."""
    from .cut import motion_ad
    prompt = build_prompt(doc, kit, direction)
    try:
        raw = (model or _model)(prompt, account_id=account_id)
    except ScriptError:
        raise
    except Exception as e:                       # a model call degrades, it does not crash
        raise ScriptError(f"the script was not written ({type(e).__name__}). "
                          "Nothing was charged.") from e
    seconds = max(1.0, doc.get("duration", 0) / (doc.get("fps") or 30))
    facts = "\n".join([motion_ad.brand_block(kit), *screen_lines(doc), direction or ""])
    out = clean_script(raw, seconds=seconds, kit=kit, facts=facts)
    return {**out, "words": len(out["script"].split())}
