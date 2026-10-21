"""ops/import_brand_kit.py: a kit folder into one account, report first.

A dry run writes nothing; --write creates the kit and its files (a font only
with a licence file, whose line is kept on the font); a second run changes
nothing; another account's kit of the same name is never touched.
"""
import io
import json
import shutil
from pathlib import Path

import pytest

from ops import import_brand_kit as imp
from src import accounts, brand_kits, db

FONT_CANDIDATES = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial.ttf")
FONT = next((Path(p) for p in FONT_CANDIDATES if Path(p).is_file()), None)
needs_font = pytest.mark.skipif(FONT is None, reason="no TrueType font on this machine")

SPEC = {"identity": {"tagline": "Get a Gyg, stay for good.", "url": "gygler.com"},
        "palette": [{"hex": "#FF880B", "role": "primary"},
                    {"hex": "#371901", "role": "accent"},
                    {"hex": "#FAF0E4", "role": "background"},
                    {"hex": "#151515", "role": "text"},
                    {"hex": "#FFFFFF", "role": "extra"}],
        "look": {"style": "Warm, clean, orange on cream.", "banned": ["neon"]}}
LICENCE = "Urbanist, SIL Open Font License 1.1, https://fonts.google.com/specimen/Urbanist"


def image(fmt="PNG", colour=(255, 136, 11)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 32), colour).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    brand_kits.init(pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("bk-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("bk-theirs", "Theirs", "#fff", dsn=pg)
    return pg, mine, theirs


@pytest.fixture
def folder(tmp_path):
    """A kit folder like the Gygler one: spec, two logos, an SVG source,
    two fonts, three references and the licence line."""
    f = tmp_path / "kit"
    f.mkdir()
    (f / "kit.json").write_text(json.dumps({"name": "Gygler", "spec": SPEC}))
    (f / "logo_light.png").write_bytes(image())
    (f / "logo_dark.png").write_bytes(image(colour=(255, 255, 255)))
    (f / "logo_light_source.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    for n in (1, 2, 3):
        (f / f"reference_{n}.jpg").write_bytes(image("JPEG", (n * 40, 90, 20)))
    if FONT:
        shutil.copy(FONT, f / "font_heading_Test-Bold.ttf")
        shutil.copy(FONT, f / "font_body_Test-Regular.ttf")
    (f / imp.LICENCE_FILE).write_text(LICENCE + "\n")
    return f


def _kits(pg, account_id):
    return brand_kits.list_kits(pg, account_id=account_id)


def _rows(pg):
    with db.connect(pg) as conn:
        return (conn.execute("SELECT COUNT(*) AS n FROM brand_kits").fetchone()["n"],
                conn.execute("SELECT COUNT(*) AS n FROM brand_kit_assets").fetchone()["n"])


@needs_font
def test_a_dry_run_writes_no_row(dbx, folder):
    pg, _mine, _ = dbx
    out = io.StringIO()
    result = imp.run(folder, "bk-mine", dsn=pg, out=out)
    assert result["written"] is False and result["kit_id"] is None
    assert _rows(pg) == (0, 0)
    text = out.getvalue()
    assert "CREATE" in text and "palette: 5 roles" in text and "files: 8" in text
    assert "nothing written" in text


@needs_font
def test_write_creates_the_kit_its_files_and_the_font_licence(dbx, folder):
    pg, mine, _ = dbx
    result = imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    assert result["created"] is True
    kit = brand_kits.get(result["kit_id"], pg, account_id=mine)
    assert kit["name"] == "Gygler"
    assert [s["hex"] for s in kit["spec"]["palette"]][0] == "#FF880B"
    roles = sorted(a["role"] for a in kit["assets"])
    assert roles == sorted(["logo_light", "logo_dark", "logo_light_source", "font_heading",
                            "font_body", "reference", "reference", "reference"])
    for font in (a for a in kit["assets"] if a["role"] in brand_kits.FONT_ROLES):
        assert font["meta"]["licensed"] is True
        assert font["meta"]["licence"] == LICENCE
        assert font["meta"]["family"]
    refs = [a["meta"]["filename"] for a in kit["assets"] if a["role"] == "reference"]
    assert refs == ["reference_1.jpg", "reference_2.jpg", "reference_3.jpg"]


@needs_font
def test_a_second_run_changes_nothing(dbx, folder):
    pg, mine, _ = dbx
    first = imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    before = _rows(pg)
    out = io.StringIO()
    again = imp.run(folder, "bk-mine", write=True, dsn=pg, out=out)
    assert again["kit_id"] == first["kit_id"] and again["created"] is False
    assert {s["action"] for s in again["files"]} == {"skip"}
    assert _rows(pg) == before
    assert f"UPDATE kit {first['kit_id']}" in out.getvalue()


@needs_font
def test_a_font_without_a_licence_file_is_refused(dbx, folder):
    pg, _mine, _ = dbx
    (folder / imp.LICENCE_FILE).unlink()
    with pytest.raises(brand_kits.KitError) as e:
        imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    assert e.value.field == "font_heading"
    assert _rows(pg) == (0, 0)


def test_a_folder_without_fonts_needs_no_licence(dbx, folder):
    pg, mine, _ = dbx
    for f in list(folder.glob("font_*")) + [folder / imp.LICENCE_FILE]:
        f.unlink()
    result = imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    kit = brand_kits.get(result["kit_id"], pg, account_id=mine)
    assert not [a for a in kit["assets"] if a["role"] in brand_kits.FONT_ROLES]


def test_a_bad_spec_is_refused_before_anything_is_written(dbx, folder):
    pg, _mine, _ = dbx
    (folder / "kit.json").write_text(json.dumps(
        {"name": "Gygler", "spec": {"palette": [{"hex": "orange", "role": "primary"}]}}))
    with pytest.raises(brand_kits.KitError) as e:
        imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    assert e.value.field == "palette"
    assert _rows(pg) == (0, 0)


def test_too_many_files_for_a_role_is_refused(dbx, folder):
    pg, _mine, _ = dbx
    for n in range(4, 10):
        (folder / f"reference_{n}.jpg").write_bytes(image("JPEG"))
    with pytest.raises(imp.FolderError):
        imp.run(folder, "bk-mine", dsn=pg, out=io.StringIO())


def test_another_accounts_kit_is_never_touched(dbx, folder):
    pg, mine, theirs = dbx
    for f in list(folder.glob("font_*")):
        f.unlink()
    theirs_kit = brand_kits.create("Gygler", {"look": {"style": "Theirs."}}, pg,
                                   account_id=theirs)
    result = imp.run(folder, "bk-mine", write=True, dsn=pg, out=io.StringIO())
    assert result["created"] is True and result["kit_id"] != theirs_kit["id"]
    after = brand_kits.get(theirs_kit["id"], pg, account_id=theirs)
    assert after["spec"] == theirs_kit["spec"] and after["assets"] == []
    assert after["updated_at"] == theirs_kit["updated_at"]
    assert [k["name"] for k in _kits(pg, mine)] == ["Gygler"]
    assert len(_kits(pg, theirs)) == 1


def test_main_reports_a_refusal_in_one_line(dbx, folder, capsys, monkeypatch):
    pg, _mine, _ = dbx
    monkeypatch.setenv("DATABASE_URL", pg)
    (folder / "kit.json").unlink()
    assert imp.main([str(folder), "--account", "bk-mine"]) == 1
    assert "refused:" in capsys.readouterr().err
