"""The reference sheet an element is drawn with (2026-09-18, Mike's call:
"build the in-app version, and this is part of the process when adding a
new element").

An element -- a character, a prop, a place -- is saved from the photos
Mike uploads, and until today that was all it had: the frames a shot is
held to were exactly those photos. This module draws ONE sheet per
element on top of them, the shape Higgsfield's character sheet has:
five panels for a person (front, three-quarter, side profile, back and
a head-and-shoulders close-up -- since 2026-10-09 the exact prompt that
drew the landing page's sheet on Higgsfield, no labels, no text), a
turnaround for a prop, plates for a place. The prompt
per kind is plain text in prompts/element_sheet_<kind>.txt, the
highest-frequency edit surface in this repo.

Three rules, all deliberate:

- **The real photos stay first.** The sheet is a DERIVATIVE of the
  face, never evidence of it, and keyframes have drifted to a
  stranger before when the anchor was a drawing (see likeness.md). So
  the sheet is saved under SHEET_STEM and `app/api._photo_names` sorts
  it LAST -- it rides into a render behind the uploads, never as
  `refs[0]`.
- **It spends, so it is a job and it is opt-in per element.** Cents on
  Nano Banana Pro under NANO_DAILY_CAP, through the same
  `nano_banana.generate_from_prompt` every keyframe uses (caps, the
  generations row, the meter, R2), with `literal=True` because a sheet
  is not a video prompt and `bank=False` because a sheet lives with
  its element, not on the Assets wall.
- **It never raises.** A sheet that fails leaves the element exactly as
  it was saved, with a note; the photos and the row are the deliverable,
  the sheet is an enhancement.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"

SHEET_STEM = "sheet"          # <element folder>/sheet.jpg
SHEET_ASPECT = "16:9"         # four or five panels side by side
KINDS = ("character", "prop", "location")
MAX_REFERENCES = 6            # every upload after the sixth adds cost, not likeness
PHOTO_BYTES_MAX = 15 * 1024 * 1024     # the same bound refbin puts on a fetch

# THE SHEET IS ALWAYS DRAWN ON PRO, AT 2K (2026-10-11, Mike: "my face
# doesn't look like me"). It followed nano_banana.MODEL, which on the
# deploy is unset and so Flash -- his first live sheet came back at 1K
# for 10 credits, the outfit right and the face a stranger's. A sheet is
# the frame every later scene is held to, so it gets the model that holds
# a face (see the WHY PRO note in nano_banana), whatever the keyframes use.
SHEET_MODEL = os.environ.get("ELEMENT_SHEET_MODEL", "gemini-3-pro-image")
SHEET_SIZE = "2K"


def is_sheet(filename: str) -> bool:
    return Path(filename).stem.lower() == SHEET_STEM


def prompt_for(kind: str, name: str, detail: str = "", notes: str = "") -> str:
    """The sheet prompt for one element, filled from its row."""
    if kind not in KINDS:
        raise ValueError(f"no sheet for kind {kind!r}")
    template = (PROMPTS_DIR / f"element_sheet_{kind}.txt").read_text()
    detail = (detail or "").strip()
    notes = (notes or "").strip()
    return template.format(
        name=name.strip(),
        name_upper=name.strip().upper(),
        detail_line=f", {detail}" if detail else "",
        detail_upper=detail.upper() if detail else "—",
        wardrobe=notes or "as in the attached photos.",
        # the character sheet's one wardrobe slot (the landing page's
        # Higgsfield prompt, 2026-10-09): "wearing <notes>", else the
        # photo's own clothes -- never a description of the face
        outfit=f"wearing {notes}" if notes else "the same clothes as in the reference photo",
    ).strip()


def _to_jpeg(data: bytes) -> bytes:
    """The sheet lands as a JPEG like every other element photo, so the
    R2 mirror's content type and the thumbnail pass stay one rule."""
    try:
        import io

        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            out = io.BytesIO()
            im.convert("RGB").save(out, format="JPEG", quality=92)
            return out.getvalue()
    except Exception:
        return data


def available(account_id: Optional[int] = None) -> bool:
    """Whether a sheet can be drawn here at all (the image key is set)."""
    from . import nano_banana
    return nano_banana.has_key(account_id)


def price_usd() -> float:
    """What one sheet costs: one still on the image model, at the meter's
    price -- the same number its credit hold is taken at."""
    from . import pricing
    return round(float(pricing.still_usd(SHEET_MODEL)), 4)


def credits() -> int:
    """What one sheet costs in credits -- the label on every Draw sheet."""
    from . import pricing
    return pricing.still_credits(SHEET_MODEL)


def photo_files(urls: list, tmp: Path, account_id: Optional[int] = None,
                limit: int = MAX_REFERENCES) -> list:
    """An element's real photos as files `draw` can read: the file on this
    machine when it has it, else the bytes fetched from the bucket into
    `tmp`. A photo that can be neither is skipped, never guessed at, and
    a sheet already drawn is never a source for the next one.

    ONE READER FOR EVERY DOOR THAT DRAWS A SHEET (2026-10-11). The MCP
    tool had this; the studio's own routes read the element's folder on
    disk, and the deployed API has no folder -- characters/, props/ and
    locations/ are gitignored AND dockerignored, so on Fly an element's
    photos live in the bucket only. The Elements card's "draw sheet"
    button answered "add a photo first" for an element with six photos.
    `urls` are the photos as the element's own listing names them
    (asset_shelf.catalogue, api._asset_photo_urls: disk first, else the
    bucket under this account's keys).

    IT STOPS AT `limit` READABLE PHOTOS -- as many as `draw` grounds on.
    It used to read every one first: the live "Michael" has 19, so a
    redraw would have fetched 19 full-size photos from the bucket to use
    six. A photo that cannot be read does not count, so the sixth good
    one is still found behind a bad one."""
    import requests

    from . import asset_shelf
    files = []
    for i, url in enumerate(urls or []):
        if len(files) >= limit:
            break
        url = str(url or "")
        if not url or is_sheet(url.rsplit("/", 1)[-1].split("?", 1)[0]):
            continue
        local = asset_shelf.resolve_photo(url)
        if local is not None:
            files.append(Path(local))
            continue
        try:
            fetch = asset_shelf.fetch_url(url, account_id)
            if not str(fetch).startswith(("http://", "https://")):
                continue
            r = requests.get(fetch, timeout=30)
            r.raise_for_status()
            if not r.content or len(r.content) > PHOTO_BYTES_MAX:
                continue
            tmp.mkdir(parents=True, exist_ok=True)
            target = tmp / f"photo-{i}.jpg"
            target.write_bytes(r.content)
            files.append(target)
        except Exception:
            continue
    return files


def out_dir_for(folder: Path, files: list, tmp: Path) -> Path:
    """Where the sheet is written: the element's own folder, unless every
    photo it is drawn from was fetched into `tmp` -- then a scratch folder
    beside them, and the bucket (the caller mirrors it) is the only copy.

    A machine that holds none of the element's photos must not be left a
    folder holding only sheet.jpg: the photo listing reads disk FIRST, so
    the drawing would become the element's only photo there, on the card
    and on every scene that names it, until the machine is replaced."""
    files = [Path(f) for f in files or []]
    if files and all(tmp in f.parents for f in files):
        return tmp / "sheet"
    return folder


def draw(kind: str, name: str, photos: list, out_dir: Path, *,
         detail: str = "", notes: str = "",
         account_id: Optional[int] = None, db_path=None, quote=None) -> dict:
    """Draw the sheet from the element's real photos into out_dir.

    Never raises: {"ok", "path", "generation_id", "error"}. `photos` are
    the uploads on disk (the sheet itself is skipped if it is among
    them, so redrawing never grounds on the last drawing). `quote` is the
    verified pricing.StudioQuote the MCP approved, held as signed.
    """
    from . import nano_banana
    try:
        refs = []
        for i, photo in enumerate(photos):
            photo = Path(photo)
            if is_sheet(photo.name) or not photo.is_file():
                continue
            refs.append((f"{name} — photo {len(refs) + 1}", photo.read_bytes()))
            if len(refs) >= MAX_REFERENCES:
                break
        if not refs:
            return {"ok": False, "path": None, "generation_id": None,
                    "error": "no photos to draw the sheet from"}
        result = nano_banana.generate_from_prompt(
            prompt_for(kind, name, detail, notes),
            reference_image=refs, aspect_ratio=SHEET_ASPECT,
            model=SHEET_MODEL, image_size=SHEET_SIZE,
            account_id=account_id, db_path=db_path,
            literal=True, bank=False, source="element_sheet", quote=quote)
        if not result.get("ok"):
            return {"ok": False, "path": None, "generation_id": None,
                    "error": result.get("error") or "the sheet did not render"}
        rendered = Path(result["path"])
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{SHEET_STEM}.jpg"
        target.write_bytes(_to_jpeg(rendered.read_bytes()))
        return {"ok": True, "path": target,
                "generation_id": result.get("generation_id"), "error": None}
    except Exception as e:
        return {"ok": False, "path": None, "generation_id": None, "error": str(e)}
