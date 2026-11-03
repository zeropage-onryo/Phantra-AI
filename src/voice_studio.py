"""
The Voice section's table (2026-10-26, docs/tasks/task-voice-tab.md).

Mike: "I want voice to have a separate UI section for all our voice models."
Every voice model the studio runs is listed here once, so the Voice page
(web/src/app/studio/voice) draws its model cards from the server and a new
model is one row, not a new page:

  * `speak` -- a script read aloud (ElevenLabs v3, src/talking_photo.VOICE),
    filed as an `asset:<id>` audio in the editor's bin, the voiceover's body
    (src/voiceover.py) with no project and no kit;
  * `library`  -- one script in a voice picked from a library by language, with
    emotion, speed and pitch (MiniMax Speech-02 HD, src/voice_models.py);
  * `dialogue` -- up to four speakers in one track (VibeVoice 7B,
    src/voice_models.py);
  * `clone`    -- the person's OWN voice copied, after they read a consent line
    (MiniMax Voice Clone, src/voice_clone.py); it then reads in the library;
  * `dub`   -- a clip spoken again in another language (src/dubbing.DUB).

The menu says how each is priced in words and never in dollars: the price
is the server's quote, shown on the card beside its click.
"""
from __future__ import annotations

from typing import Optional

# the order the page lists them in; each row's numbers come from its own module
KINDS = ("speak", "library", "dialogue", "clone", "dub")


def models() -> list[dict]:
    """The voice models, in page order: what each does and how it is priced,
    read off the modules that run them (never restated here)."""
    from . import dubbing, voice_clone, voice_models
    from . import talking_photo as tp
    lib, dia = voice_models.LIBRARY, voice_models.DIALOGUE
    voices = sum(len(v) for v in voice_models.LIBRARY_VOICES.values())
    return [
        {"id": tp.VOICE["id"], "kind": "speak", "label": tp.VOICE["label"],
         "title": "Text to speech",
         "what": "A script read aloud in one of the model's voices. Tags like [laughs] or "
                 "[whispers] set the delivery. The read lands in your Library's audio, "
                 "ready for the editor's voice track.",
         "priced": "by the characters in the script",
         "checked": tp.VOICE["checked"]},
        {"id": lib["id"], "kind": "library", "label": lib["label"],
         "title": "Voice library",
         "what": f"{voices} voices sorted by language, each with emotion, speed and pitch. "
                 "The read lands in your Library's audio.",
         "priced": "by the characters in the script",
         "checked": lib["checked"]},
        {"id": dia["id"], "kind": "dialogue", "label": dia["label"],
         "title": "Dialogue",
         "what": f"A conversation of up to {voice_models.MAX_SPEAKERS} speakers in one audio "
                 "track, each with their own voice. The track lands in your Library's audio.",
         "priced": "by the length of the dialogue, in 15-second steps",
         "checked": dia["checked"]},
        {"id": voice_clone.CLONE["id"], "kind": "clone", "label": voice_clone.CLONE["label"],
         "title": "Clone your voice",
         "what": "Your own voice, copied from a sample that starts with you reading a consent "
                 "line. It then reads any script in the voice library.",
         "priced": "once per voice",
         "checked": voice_clone.CLONE["checked"]},
        {"id": dubbing.DUB["id"], "kind": "dub", "label": dubbing.DUB["label"],
         "title": "Dub a clip",
         "what": "A clip with people speaking on it, spoken again in another language in "
                 "the same voices. The dubbed clip lands in your Library.",
         "priced": "by the clip's length, in whole minutes",
         "checked": dubbing.DUB["checked"]},
    ]


def menu(*, ready: bool, exempt: bool, account_id: Optional[int] = None, dsn=None) -> dict:
    """What the Voice page offers. Browsing it runs nothing and costs nothing.
    The account's own cloned voices lead the library, as "Your voices"."""
    from . import dubbing, voice_clone, voice_models, voiceover
    from . import talking_photo as tp
    clone = voice_clone.menu(account_id=account_id, dsn=dsn)
    library = voice_models.library_menu()
    if clone["voices"]:
        library = {**library, "languages": [
            {"language": "Your voices", "voices": [{"id": v["id"], "name": v["name"]}
                                                   for v in clone["voices"]]},
            *library["languages"]]}
    return {
        "models": models(),
        "speak": {"voices": list(tp.VOICES), "default_voice": tp.DEFAULT_VOICE,
                  "script_max": voiceover.SCRIPT_MAX_CHARS},
        "library": library,
        "clone": clone,
        "dialogue": voice_models.dialogue_menu(),
        "dub": dubbing.menu(),
        "ready": ready,
        "exempt": exempt,
    }


def speak_request(script: str, voice: str = "", language: str = "") -> dict:
    """A read checked and priced, nothing spent (the voiceover's checks with
    no kit: any length from one character, a voice off the list refused)."""
    from . import voiceover
    return voiceover.request(script, voice, language, None)


def speak(req: dict, *, account_id: Optional[int], dsn=None, source: str,
          project_id: Optional[int] = None) -> dict:
    """Read it and file it in the bin (voiceover.run): {ok, audio, seconds,
    stored, generation_id} or {ok: False, error}."""
    from . import voiceover
    return voiceover.run(req, account_id=account_id, dsn=dsn, source=source,
                         project_id=project_id)


__all__ = ["KINDS", "models", "menu", "speak_request", "speak"]
