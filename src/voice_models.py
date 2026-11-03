"""
The Voice section's second and third models (2026-10-27,
docs/tasks/task-voice-tab.md): a voice LIBRARY and multi-speaker DIALOGUE.

  * library  -- MiniMax Speech-02 HD on fal: one script, one voice picked from a
                library sorted by language, with emotion, speed and pitch;
  * dialogue -- VibeVoice 7B on fal: a conversation of up to four speakers,
                each a preset voice, in one audio track.

Both are one spend, priced before anything runs, through `effects.run` (the
cap, the CREDIT HOLD before the submit, the generations row, settle) exactly as
src/voiceover.py runs ElevenLabs v3, and both file the result as an
`asset:<id>` audio in the editor's bin (`file_audio`), so a read made here
lands on a voice track with the editor's ordinary ops.

Read on CHECKED:
  fal.ai/models/fal-ai/minimax/speech-02-hd (+ /api):
    `text` 1-5000 characters; `voice_setting` {voice_id (default "Wise_Woman";
    the page lists no others), speed 0.5-2.0, vol 0-10, pitch -12..12, emotion
    happy|sad|angry|fearful|disgusted|surprised|neutral}; `language_boost` (a
    language name or "auto"); `output_format` url|hex (default hex);
    output `audio` {url} and `duration_ms`. "$0.1 per 1000 characters."
  platform.minimax.io/docs/faq/system-voice-id: the system voice ids, 332 over
    24 languages. LIBRARY_VOICES carries the 45 English voices and the first
    six the page lists for six other languages. Whether every MiniMax platform
    id is accepted by fal's endpoint is NOT proven -- the first live read of a
    non-default voice settles it (see the task doc).
  fal.ai/models/fal-ai/vibevoice/7b (+ /api):
    `script` with "Speaker N:" prefixes, N counting from 0 and naming
    `speakers[N]`; `speakers` [{preset}], presets the eight listed below;
    `cfg_scale` (default 1.3); output `audio` {url}, `duration`. "Billing is
    calculated at $0.04 per minute of generated speech, with duration rounded
    to the nearest 15 seconds." The example says up to four speakers; no
    script limit is stated, so MAX_DIALOGUE_CHARS is the studio's own guard.

THE DIALOGUE'S PRICE is billed on the speech it makes, which is not known
until it is made. The quote is an upper bound from the words: at a slow 10
characters a second (speech runs ~14-16), rounded UP to the next 15 seconds.
The person is charged that quote, never more; fal bills the real length.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional

CHECKED = "2026-10-27"

LIBRARY = {
    "id": "minimax-speech-02-hd",
    "label": "MiniMax Speech-02 HD",
    "endpoint": "fal-ai/minimax/speech-02-hd",
    # "$0.1 per 1000 characters" (model page)
    "usd_per_1k_chars": 0.10,
    "source": "https://fal.ai/models/fal-ai/minimax/speech-02-hd",
    "checked": CHECKED,
}
DIALOGUE = {
    "id": "vibevoice-7b",
    "label": "VibeVoice 7B",
    "endpoint": "fal-ai/vibevoice/7b",
    # "$0.04 per minute of generated speech, with duration rounded to the
    # nearest 15 seconds" (model page)
    "usd_per_minute": 0.04,
    "billing_step_seconds": 15,
    "source": "https://fal.ai/models/fal-ai/vibevoice/7b",
    "checked": CHECKED,
}

SCRIPT_MAX_CHARS = 5000            # speech-02-hd `text` maxLength
MAX_DIALOGUE_CHARS = 5000          # the studio's guard: the page states none
MAX_SPEAKERS = 4                   # "supports up to four speakers at once"
MAX_LINES = 200
SLOW_CHARS_PER_SECOND = 10.0       # the quote's upper bound on speech length

EMOTIONS = ("neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised")
SPEED_MIN, SPEED_MAX = 0.5, 2.0
PITCH_MIN, PITCH_MAX = -12, 12

# fal's own default, then the system voice ids by language
# (platform.minimax.io/docs/faq/system-voice-id, read on CHECKED)
DEFAULT_LIBRARY_VOICE = "Wise_Woman"   # the one voice fal's page names
LIBRARY_VOICES: dict[str, list[tuple[str, str]]] = {
    "English": [
        ("Wise_Woman", "Wise Woman"),
        ("English_expressive_narrator", "Expressive Narrator"),
        ("English_radiant_girl", "Radiant Girl"),
        ("English_magnetic_voiced_man", "Magnetic-voiced Male"),
        ("English_compelling_lady1", "Compelling Lady"),
        ("English_Aussie_Bloke", "Aussie Bloke"),
        ("English_captivating_female1", "Captivating Female"),
        ("English_Upbeat_Woman", "Upbeat Woman"),
        ("English_Trustworth_Man", "Trustworthy Man"),
        ("English_CalmWoman", "Calm Woman"),
        ("English_UpsetGirl", "Upset Girl"),
        ("English_Gentle-voiced_man", "Gentle-voiced Man"),
        ("English_Whispering_girl", "Whispering Girl"),
        ("English_Diligent_Man", "Diligent Man"),
        ("English_Graceful_Lady", "Graceful Lady"),
        ("English_ReservedYoungMan", "Reserved Young Man"),
        ("English_PlayfulGirl", "Playful Girl"),
        ("English_ManWithDeepVoice", "Man With Deep Voice"),
        ("English_MaturePartner", "Mature Partner"),
        ("English_FriendlyPerson", "Friendly Guy"),
        ("English_MatureBoss", "Bossy Lady"),
        ("English_Debator", "Male Debater"),
        ("English_LovelyGirl", "Lovely Girl"),
        ("English_Steadymentor", "Reliable Man"),
        ("English_Deep-VoicedGentleman", "Deep-voiced Gentleman"),
        ("English_Wiselady", "Wise Lady"),
        ("English_CaptivatingStoryteller", "Captivating Storyteller"),
        ("English_DecentYoungMan", "Decent Young Man"),
        ("English_SentimentalLady", "Sentimental Lady"),
        ("English_ImposingManner", "Imposing Queen"),
        ("English_SadTeen", "Teen Boy"),
        ("English_PassionateWarrior", "Passionate Warrior"),
        ("English_WiseScholar", "Wise Scholar"),
        ("English_Soft-spokenGirl", "Soft-Spoken Girl"),
        ("English_SereneWoman", "Serene Woman"),
        ("English_ConfidentWoman", "Confident Woman"),
        ("English_PatientMan", "Patient Man"),
        ("English_Comedian", "Comedian"),
        ("English_BossyLeader", "Bossy Leader"),
        ("English_Strong-WilledBoy", "Strong-Willed Boy"),
        ("English_StressedLady", "Stressed Lady"),
        ("English_AssertiveQueen", "Assertive Queen"),
        ("English_AnimeCharacter", "Female Narrator"),
        ("English_Jovialman", "Jovial Man"),
        ("English_WhimsicalGirl", "Whimsical Girl"),
        ("English_Kind-heartedGirl", "Kind-Hearted Girl"),
    ],
    "Spanish": [
        ("Spanish_SereneWoman", "Serene Woman"),
        ("Spanish_MaturePartner", "Mature Partner"),
        ("Spanish_CaptivatingStoryteller", "Captivating Storyteller"),
        ("Spanish_Narrator", "Narrator"),
        ("Spanish_WiseScholar", "Wise Scholar"),
        ("Spanish_Kind-heartedGirl", "Kind-Hearted Girl"),
    ],
    "French": [
        ("French_Male_Speech_New", "Male Speech"),
        ("French_Female_News Anchor", "Female News Anchor"),
        ("French_CasualMan", "Casual Man"),
        ("French_MovieLeadFemale", "Movie Lead Female"),
        ("French_FemaleAnchor", "Female Anchor"),
        ("French_MaleNarrator", "Male Narrator"),
    ],
    "Portuguese": [
        ("Portuguese_SentimentalLady", "Sentimental Lady"),
        ("Portuguese_BossyLeader", "Bossy Leader"),
        ("Portuguese_Wiselady", "Wise Lady"),
        ("Portuguese_Strong-WilledBoy", "Strong-Willed Boy"),
        ("Portuguese_Deep-VoicedGentleman", "Deep-voiced Gentleman"),
        ("Portuguese_UpsetGirl", "Upset Girl"),
    ],
    "German": [
        ("German_FriendlyMan", "Friendly Man"),
        ("German_SweetLady", "Sweet Lady"),
        ("German_PlayfulMan", "Playful Man"),
    ],
    "Japanese": [
        ("Japanese_IntellectualSenior", "Intellectual Senior"),
        ("Japanese_DecisivePrincess", "Decisive Princess"),
        ("Japanese_LoyalKnight", "Loyal Knight"),
        ("Japanese_DominantMan", "Dominant Man"),
        ("Japanese_SeriousCommander", "Serious Commander"),
        ("Japanese_ColdQueen", "Cold Queen"),
    ],
    "Korean": [
        ("Korean_AirheadedGirl", "Airheaded Girl"),
        ("Korean_AthleticGirl", "Athletic Girl"),
        ("Korean_AthleticStudent", "Athletic Student"),
        ("Korean_BraveAdventurer", "Brave Adventurer"),
        ("Korean_BraveFemaleWarrior", "Brave Female Warrior"),
        ("Korean_BraveYouth", "Brave Youth"),
    ],
    "Chinese": [
        ("Chinese (Mandarin)_Reliable_Executive", "Reliable Executive"),
        ("Chinese (Mandarin)_News_Anchor", "News Anchor"),
        ("Chinese (Mandarin)_Unrestrained_Young_Man", "Unrestrained Young Man"),
        ("Chinese (Mandarin)_Mature_Woman", "Mature Woman"),
    ],
}
# voice id -> its language (also the model's `language_boost` value)
VOICE_LANGUAGE = {vid: lang for lang, voices in LIBRARY_VOICES.items() for vid, _ in voices}

DIALOGUE_PRESETS = ("Alice [EN]", "Carter [EN]", "Frank [EN]", "Mary [EN] (Background Music)",
                    "Maya [EN]", "Anchen [ZH] (Background Music)", "Bowen [ZH]", "Xinran [ZH]")


# --- the library: one script, one voice --------------------------------------

def library_usd(script: str) -> float:
    return round(len(script) * LIBRARY["usd_per_1k_chars"] / 1000, 6)


def check_script(script: str, limit: int = SCRIPT_MAX_CHARS) -> str:
    script = (script or "").strip()
    if not script:
        raise ValueError("write the words to be read")
    if len(script) > limit:
        raise ValueError(f"the script is {len(script)} characters; the voice model takes up to {limit}")
    return script


def check_library_voice(voice: str, clones: Optional[dict] = None) -> str:
    """A system voice, or one of this account's cloned voices (`clones`:
    voice id -> name, src/voice_clone.names)."""
    voice = (voice or "").strip() or DEFAULT_LIBRARY_VOICE
    if voice not in VOICE_LANGUAGE and voice not in (clones or {}):
        raise ValueError(f"{voice!r} is not a voice in the library -- pick one from the list")
    return voice


def check_emotion(emotion: str) -> Optional[str]:
    emotion = (emotion or "").strip().lower()
    if not emotion:
        return None
    if emotion not in EMOTIONS:
        raise ValueError(f"emotion is one of {', '.join(EMOTIONS)}, got {emotion!r}")
    return emotion


def check_speed(speed) -> float:
    if speed in (None, ""):
        return 1.0
    try:
        value = float(speed)
    except (TypeError, ValueError):
        raise ValueError(f"speed is a number, got {speed!r}") from None
    if not SPEED_MIN <= value <= SPEED_MAX or math.isnan(value):
        raise ValueError(f"speed is {SPEED_MIN} to {SPEED_MAX}, got {speed}")
    return round(value, 2)


def check_pitch(pitch) -> int:
    if pitch in (None, ""):
        return 0
    try:
        value = int(pitch)
    except (TypeError, ValueError):
        raise ValueError(f"pitch is a whole number, got {pitch!r}") from None
    if isinstance(pitch, float) and not float(pitch).is_integer():
        raise ValueError(f"pitch is a whole number, got {pitch!r}")
    if not PITCH_MIN <= value <= PITCH_MAX:
        raise ValueError(f"pitch is {PITCH_MIN} to {PITCH_MAX}, got {pitch}")
    return value


def library_request(script: str, voice: str = "", emotion: str = "", speed=None,
                    pitch=None, clones: Optional[dict] = None) -> dict:
    """A library read checked and priced, nothing spent. A cloned voice
    is priced the same (it is the same model) and its language is left to
    the model ("auto")."""
    script = check_script(script)
    voice = check_library_voice(voice, clones)
    clone = voice not in VOICE_LANGUAGE
    return {"script": script, "voice": voice, "clone": clone,
            "name": (clones or {}).get(voice) if clone else None,
            "language": "auto" if clone else VOICE_LANGUAGE[voice],
            "emotion": check_emotion(emotion), "speed": check_speed(speed),
            "pitch": check_pitch(pitch), "characters": len(script),
            "usd": library_usd(script), "label": LIBRARY["label"]}


def library_body(req: dict) -> tuple[str, dict]:
    """(endpoint, body) in the model's wire shape. The address comes back as
    a URL (`output_format` url), not the page's default hex."""
    setting: dict = {"voice_id": req["voice"], "speed": req["speed"]}
    if req.get("pitch"):
        setting["pitch"] = req["pitch"]
    if req.get("emotion"):
        setting["emotion"] = req["emotion"]
    return LIBRARY["endpoint"], {"text": req["script"], "voice_setting": setting,
                                 "language_boost": req["language"], "output_format": "url"}


# --- dialogue: up to four speakers in one track ------------------------------

def check_speakers(speakers) -> list[str]:
    """The speakers in order (Speaker 0 is the first), each a listed preset."""
    if not isinstance(speakers, (list, tuple)) or not speakers:
        raise ValueError("a dialogue needs its speakers: one to four preset voices")
    if len(speakers) > MAX_SPEAKERS:
        raise ValueError(f"a dialogue takes up to {MAX_SPEAKERS} speakers, got {len(speakers)}")
    out = []
    for s in speakers:
        if s not in DIALOGUE_PRESETS:
            raise ValueError(f"{s!r} is not one of the dialogue voices -- pick one from the list")
        out.append(s)
    return out


def check_lines(lines, n_speakers: int) -> list[dict]:
    """The conversation as [{speaker, text}], each speaker an index into the
    speakers, each line's words on one line (a newline would start a turn)."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("write the dialogue: at least one line")
    if len(lines) > MAX_LINES:
        raise ValueError(f"a dialogue takes up to {MAX_LINES} lines, got {len(lines)}")
    out = []
    for i, line in enumerate(lines, 1):
        if not isinstance(line, dict):
            raise ValueError(f"line {i} is not a line")
        who = line.get("speaker")
        if isinstance(who, bool) or not isinstance(who, int) or not 0 <= who < n_speakers:
            raise ValueError(f"line {i} names speaker {who!r}; there are {n_speakers}")
        text = " ".join(str(line.get("text") or "").split())
        if not text:
            continue
        if re.match(r"^speaker\s*\d+\s*:", text, re.IGNORECASE):
            raise ValueError(f"line {i} starts with a speaker label; the studio adds those")
        out.append({"speaker": who, "text": text})
    if not out:
        raise ValueError("write the dialogue: every line is empty")
    return out


def dialogue_script(lines: list[dict]) -> str:
    """The model's script: one "Speaker N: words" per line, N from 0."""
    return "\n".join(f"Speaker {ln['speaker']}: {ln['text']}" for ln in lines)


def dialogue_estimate_seconds(script: str) -> int:
    """The quote's upper bound on the speech, rounded UP to fal's 15-second step."""
    step = DIALOGUE["billing_step_seconds"]
    raw = max(1.0, len(script) / SLOW_CHARS_PER_SECOND)
    return int(math.ceil(raw / step - 1e-9) * step)


def dialogue_usd(seconds: int) -> float:
    return round(seconds / 60 * DIALOGUE["usd_per_minute"], 6)


def dialogue_request(speakers, lines) -> dict:
    """A dialogue checked and priced (an upper bound), nothing spent."""
    speakers = check_speakers(speakers)
    lines = check_lines(lines, len(speakers))
    script = dialogue_script(lines)
    if len(script) > MAX_DIALOGUE_CHARS:
        raise ValueError(f"the dialogue is {len(script)} characters; it takes up to "
                         f"{MAX_DIALOGUE_CHARS} -- make it shorter or split it")
    used = {ln["speaker"] for ln in lines}
    if len(used) < len(speakers):
        idle = [str(i + 1) for i in range(len(speakers)) if i not in used]
        raise ValueError(f"speaker {', '.join(idle)} has no lines -- give them one or remove them")
    seconds = dialogue_estimate_seconds(script)
    return {"speakers": speakers, "lines": lines, "script": script,
            "characters": len(script), "estimate_seconds": seconds,
            "usd": dialogue_usd(seconds), "label": DIALOGUE["label"]}


def dialogue_body(req: dict) -> tuple[str, dict]:
    return DIALOGUE["endpoint"], {"script": req["script"],
                                  "speakers": [{"preset": s} for s in req["speakers"]]}


# --- running either, and filing the read in the editor's bin -----------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "voice"


def file_audio(res: dict, name: str, *, account_id: Optional[int], dsn=None) -> dict:
    """effects.run's audio file, saved to the editor's bin as an asset:<id>
    (src/voiceover.py's filing, shared). The read is paid for by then, so a
    file that cannot be saved says so plainly."""
    from .cut import render, uploads
    if not res.get("ok"):
        return res
    path = Path(res["path"])
    try:
        saved = uploads.save(path.read_bytes(), f"{name}{path.suffix or '.mp3'}",
                             account_id=account_id, media_dir=render.CUT_DIR / "media",
                             types=uploads.AUDIO_TYPES, dsn=dsn)
    except (OSError, uploads.UploadRefused) as e:
        return {"ok": False, "generation_id": res.get("generation_id"),
                "error": f"the voice was made and paid for but could not be filed ({e})"}
    return {"ok": True, "audio": saved["handle"], "seconds": saved["info"].get("seconds"),
            "stored": saved["stored"], "generation_id": res.get("generation_id")}


def run_library(req: dict, *, account_id: Optional[int], dsn=None, source: str,
                project_id: Optional[int] = None) -> dict:
    from . import effects
    res = effects.run(
        f"voice-{LIBRARY['id']}", [], req["script"], {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, project_id=project_id,
        row={"label": LIBRARY["label"], "output": "audio"},
        endpoint_body=library_body(req),
        extra={"voice_library": {"voice": req["voice"], "emotion": req["emotion"],
                                 "speed": req["speed"], "pitch": req["pitch"],
                                 "characters": req["characters"]}})
    if res.get("ok") and req.get("clone"):
        # a read in a cloned voice is what keeps it (MiniMax deletes one
        # unused for a week); best effort -- the read is made either way
        try:
            from . import voice_clone
            voice_clone.touch(req["voice"], account_id=account_id, dsn=dsn)
        except Exception:
            pass
    return file_audio(res, f"voice-{_slug(req.get('name') or req['voice'])}",
                      account_id=account_id, dsn=dsn)


def run_dialogue(req: dict, *, account_id: Optional[int], dsn=None, source: str,
                 project_id: Optional[int] = None) -> dict:
    from . import effects
    res = effects.run(
        f"voice-{DIALOGUE['id']}", [], req["script"], {}, usd=req["usd"],
        account_id=account_id, db_path=dsn, source=source, project_id=project_id,
        row={"label": DIALOGUE["label"], "output": "audio"},
        endpoint_body=dialogue_body(req),
        extra={"voice_dialogue": {"speakers": req["speakers"], "lines": len(req["lines"]),
                                  "characters": req["characters"],
                                  "estimate_seconds": req["estimate_seconds"]}})
    return file_audio(res, "dialogue", account_id=account_id, dsn=dsn)


def library_menu() -> dict:
    return {"languages": [{"language": lang, "voices": [{"id": v, "name": n} for v, n in voices]}
                          for lang, voices in LIBRARY_VOICES.items()],
            "default_voice": DEFAULT_LIBRARY_VOICE, "emotions": list(EMOTIONS),
            "speed": [SPEED_MIN, SPEED_MAX], "pitch": [PITCH_MIN, PITCH_MAX],
            "script_max": SCRIPT_MAX_CHARS}


def dialogue_menu() -> dict:
    return {"presets": list(DIALOGUE_PRESETS), "max_speakers": MAX_SPEAKERS,
            "max_lines": MAX_LINES, "script_max": MAX_DIALOGUE_CHARS}


__all__ = ["CHECKED", "LIBRARY", "DIALOGUE", "LIBRARY_VOICES", "VOICE_LANGUAGE",
           "DIALOGUE_PRESETS", "EMOTIONS", "library_request", "library_body", "run_library",
           "dialogue_request", "dialogue_body", "dialogue_script", "dialogue_estimate_seconds",
           "run_dialogue", "file_audio", "library_menu", "dialogue_menu"]
