"""App screens drawn from a brand kit, in code (2026-10-22, docs/tasks/
task-kit-products-and-screens.md Part C): each template renders under
kit 1's own spec (the live Gygler palette and voice) with Pillow's built-in
font standing in for the kit's, no network, no spend."""
import io

import pytest
from PIL import Image

from src import kit_screens

# kit 1 ("Gygler") as the live row has it, 2026-10-22
GYGLER = {"id": 1, "account_id": 1, "name": "Gygler", "assets": [], "hash": "abc",
          "spec": {"palette": [{"hex": "#FF880B", "role": "primary"},
                               {"hex": "#371901", "role": "accent"},
                               {"hex": "#FAF0E4", "role": "background"},
                               {"hex": "#151515", "role": "text"},
                               {"hex": "#FFFFFF", "role": "extra"}],
                   "voice": {"avoid": ["staffing agency"],
                             "cta": "Short first-person buttons in title case"},
                   "never_claim": ["guaranteed shifts"]}}

STAFFED = {"template": "schedule", "title": "Staffed", "subtitle": "Friday dinner service",
           "rows": [{"name": "Maria Lopez", "role": "Line cook", "time": "5-11pm",
                     "status": "Staffed"},
                    {"name": "Dev Patel", "role": "Server", "time": "6-12pm", "status": "Staffed"},
                    {"name": "Sam Ortiz", "role": "Dishwasher", "time": "5-10pm",
                     "status": "Open"}]}
CARDS = {"template": "list_cards", "title": "Your Talent Pool",
         "cards": [{"title": "Maria Lopez", "subtitle": "Line cook, 6 years, fine dining",
                    "meta": "4.9 rating", "tag": "Available"},
                   {"title": "Dev Patel", "subtitle": "Server, wine certified",
                    "meta": "4.8 rating", "tag": "Booked"}]}
HERO = {"template": "hero_cta", "headline": "Built Around People, Not Just Systems",
        "body": "Human logistics for the heat of the kitchen.", "button": "I Need Talent",
        "secondary": "Get Gygs"}


def _image(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGB")


def _has(img: Image.Image, rgb, tol=6) -> bool:
    small = img.resize((img.width // 6, img.height // 6), Image.NEAREST)
    return any(all(abs(a - b) <= tol for a, b in zip(px, rgb)) for px in small.getdata())


@pytest.mark.parametrize("raw", [STAFFED, CARDS, HERO])
@pytest.mark.parametrize("device", ["phone", "tablet", "tablet_portrait"])
def test_each_template_draws_in_the_kits_colours_at_the_device_size(raw, device):
    spec = kit_screens.clean({**raw, "device": device})
    img = _image(kit_screens.render(spec, GYGLER))
    assert img.size == kit_screens.SIZES[device]
    assert img.getpixel((5, img.height - 5)) == (0xFA, 0xF0, 0xE4)     # the cream background
    assert _has(img, (0xFF, 0x88, 0x0B))                                # Gygler orange on it
    assert _has(img, (0x15, 0x15, 0x15), tol=40)                        # near-black type


def test_the_staffed_pill_is_the_primary_and_open_waits():
    c = kit_screens.palette(GYGLER)
    assert kit_screens._status_colours("Staffed", c)[0] == "#FF880B"
    assert kit_screens._status_colours("Open", c)[0] != "#FF880B"
    assert c["on_primary"] in ("#FFFFFF", "#151515")


def test_a_spec_off_the_shapes_is_refused_with_what_is_wrong():
    for bad, why in (({"template": "map"}, "template"),
                     ({**STAFFED, "device": "watch"}, "device"),
                     ({**STAFFED, "rows": []}, "rows"),
                     ({**STAFFED, "rows": [{"role": "cook"}]}, "rows 1 name"),
                     ({**HERO, "button": ""}, "button"),
                     ({**HERO, "headline": "see https://x.example"}, "address"),
                     ({**STAFFED, "rows": STAFFED["rows"] * 3}, "at most")):
        with pytest.raises(kit_screens.ScreenError, match=why):
            kit_screens.clean(bad)


def test_words_the_kit_never_uses_are_advised_not_refused():
    spec = kit_screens.clean({**HERO, "body": "Not a staffing agency. Guaranteed shifts!"})
    said = kit_screens.check_words(spec, GYGLER)
    assert len(said) == 2 and "staffing agency" in said[0] and "guaranteed shifts" in said[1]
    assert kit_screens.check_words(kit_screens.clean(HERO), GYGLER) == []
    assert kit_screens.render(spec, GYGLER)[:8] == b"\x89PNG\r\n\x1a\n"


def test_a_kit_with_no_palette_still_draws_readably():
    img = _image(kit_screens.render(kit_screens.clean(STAFFED), {"name": "Plain", "spec": {}}))
    assert img.getpixel((5, img.height - 5)) == (255, 255, 255)
    assert kit_screens.summary(kit_screens.clean(STAFFED)) == "phone screen, 3-row schedule: Staffed"


def test_keeping_a_screen_files_one_free_library_still(pg, monkeypatch, tmp_path):
    """Kept on click: one PNG under renders/kit with an unguessable name, one
    Library row labelled Kit screen, and a generation that cost nothing."""
    from src import accounts, db, generative, render_assets, watermark
    from src.cut import sources
    accounts.init(pg)
    generative.init(pg)
    mine = accounts.upsert_account("ks-mine", "Mine", "#fff", dsn=pg)
    monkeypatch.setattr(sources, "RENDERS_DIR", tmp_path)
    monkeypatch.setattr(watermark, "publish_file", lambda *a, **k: None)
    kit = {**GYGLER, "account_id": mine}
    out = kit_screens.keep(kit_screens.clean(STAFFED), kit, account_id=mine, dsn=pg)
    assert out["stored"].startswith("/renders/kit/screen-schedule-k1-")
    assert (tmp_path / "kit" / out["stored"].rsplit("/", 1)[1]).read_bytes()[:4] == b"\x89PNG"
    with db.connect(pg) as conn:
        row = conn.execute("SELECT * FROM generated_assets WHERE id = %s",
                           (out["asset_id"],)).fetchone()
        gen = conn.execute("SELECT cost_usd FROM generations WHERE id = %s",
                           (row["generation_id"],)).fetchone()
    assert row["account_id"] == mine and row["media_kind"] == "image"
    assert render_assets._label(row["tool"], row["model"]) == "Kit screen"
    assert gen["cost_usd"] is None
