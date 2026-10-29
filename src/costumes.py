"""
Halloween costumes (2026-10-27, Mike: "i want it to be easy and one click").

One photo in, the person shown in a costume they pick from a short list, face
kept. Two steps, each its own priced card and its own Approve:

1. the preview: the "costume-preview" row of src/effects.py, a STILL on Nano
   Banana edit (the edit model that keeps faces), with the costume as an
   option -- so the composer's card draws it as one tap per costume and the
   Effects page splits it into one tile per costume (lib/effects-wall.ts);
2. the video: the "costume_try_on" recipe (src/effect_recipes.py) on the
   person's ORIGINAL photo, the result's "Make it a video" (lib/continue.ts).
   The costume carries over as the recipe's one detail; `describe` turns the
   picked name back into the full description below.

The descriptions are ours, generic costumes only: no character anyone owns.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

CHECKED = "2026-10-27"
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "effects" / "costume_preview.txt"

# id -> what the person is dressed in. The order is the card's.
COSTUMES: dict[str, str] = {
    "vampire": "a vampire costume: a black high-collared cape lined in deep red, "
               "a dark Victorian waistcoat over a ruffled white shirt",
    "witch": "a witch costume: a long black dress, a tattered black cape and a tall pointed hat",
    "pirate": "a pirate captain costume: a long burgundy coat with brass buttons, "
              "a loose white shirt, a red sash and a tricorn hat",
    "skeleton": "a skeleton costume: a black bodysuit printed with white bones, and white skull face paint",
    "zombie_bride": "a zombie bride costume: a torn, dirt-stained white wedding dress and a "
                    "ragged veil, with pale grey makeup",
    "werewolf": "a werewolf costume: a torn plaid flannel shirt and ripped jeans, "
                "with fur at the collar and cuffs and wolf ears",
    "mummy": "a mummy costume: wrapped head to toe in aged linen bandages, the face left uncovered",
    "devil": "a devil costume: a sharp red suit, small red horns and a pointed tail",
    "angel": "an angel costume: a flowing white robe, large white feathered wings and a golden halo",
    "ghost": "a ghost costume: a flowing pale grey hooded shroud that drifts like mist, the face showing",
    "scarecrow": "a scarecrow costume: a patched flannel shirt and overalls with straw "
                 "poking out, and a frayed straw hat",
    "black_cat": "a black cat costume: a sleek black outfit, black cat ears, a tail and drawn-on whiskers",
}


def _key(text: str) -> str:
    return "_".join((text or "").strip().lower().replace("-", " ").split())


def describe(text: str) -> str:
    """A costume as the model is told it: the full description when `text`
    names one of COSTUMES (by id or as a person reads it, "Zombie bride" /
    "zombie bride costume"), else `text` itself, untouched."""
    key = _key(text)
    for cand in (key, key.removesuffix("_costume")):
        if cand in COSTUMES:
            return COSTUMES[cand]
    return text


@lru_cache(maxsize=1)
def _template() -> str:
    return PROMPT_FILE.read_text().strip()


def prompt_for(costume: str) -> str:
    """The preview's prompt for one costume id. KeyError on an unknown id:
    effects.check_options has refused it before this is reached."""
    return _template().replace("{costume}", COSTUMES[costume])
