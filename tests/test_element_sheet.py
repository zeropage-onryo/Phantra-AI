"""The element reference sheet (2026-09-18): drawn on save as a job,
listed LAST among the element's photos, never banked on the Assets
wall, and never able to fail the element that asked for it."""
from pathlib import Path

import pytest

from src import element_sheet, nano_banana


def test_every_kind_has_a_prompt_and_it_fills():
    for kind in element_sheet.KINDS:
        text = element_sheet.prompt_for(kind, "Michael", "the rider", "white leathers")
        assert "{" not in text and "}" not in text
        if kind != "character":
            assert "MICHAEL" in text
    # the character sheet is the landing page's prompt: five views, no text
    character = element_sheet.prompt_for("character", "Michael", "the rider", "white leathers")
    assert "three-quarter view" in character and "head-and-shoulders close-up" in character
    assert "wearing white leathers" in character and "no text" in character
    assert "light-grey studio background" in character      # Mike's call, 2026-10-11 (white 10-10, back to grey)
    assert "exact match to the person in the reference photos" in character
    bare = element_sheet.prompt_for("character", "Michael")
    assert "the same clothes as in the reference photo" in bare
    assert "PLACE: GARAGE" in element_sheet.prompt_for("location", "garage")
    with pytest.raises(ValueError):
        element_sheet.prompt_for("render", "x")


def test_the_sheet_prompt_leaves_no_placeholder_when_the_row_is_bare():
    text = element_sheet.prompt_for("prop", "Ducati 959")
    assert "TYPE: —" in text and "as in the attached photos" in text


def test_is_sheet_names_only_the_drawn_file():
    assert element_sheet.is_sheet("sheet.jpg") and element_sheet.is_sheet("SHEET.png")
    assert not element_sheet.is_sheet("IMG_0001.jpg")
    assert not element_sheet.is_sheet("sheet-music.jpg")


def test_draw_grounds_on_the_real_photos_and_lands_as_sheet_jpg(tmp_path, monkeypatch):
    monkeypatch.setattr(element_sheet, "SHEET_MODEL", "gemini-3-pro-image")
    folder = tmp_path / "michael"
    folder.mkdir()
    (folder / "b.jpg").write_bytes(b"photo-b")
    (folder / "a.jpg").write_bytes(b"photo-a")
    (folder / "sheet.jpg").write_bytes(b"an old drawing")   # a redraw must not ground on it
    rendered = tmp_path / "wf.png"
    rendered.write_bytes(b"\x89PNG-not-really")
    calls = []

    def fake_generate(prompt, **kw):
        calls.append((prompt, kw))
        return {"ok": True, "path": str(rendered), "generation_id": 7}

    monkeypatch.setattr(nano_banana, "generate_from_prompt", fake_generate)
    result = element_sheet.draw("character", "Michael",
                                [folder / "a.jpg", folder / "sheet.jpg", folder / "b.jpg"],
                                folder, detail="the rider", account_id=1)
    assert result["ok"] and result["generation_id"] == 7
    assert result["path"] == folder / "sheet.jpg"
    assert result["path"].read_bytes() != b"an old drawing"
    [(prompt, kw)] = calls
    assert "three-quarter view" in prompt
    assert kw["literal"] is True and kw["bank"] is False
    assert kw["source"] == "element_sheet" and kw["aspect_ratio"] == "16:9"
    # always Pro at 2K, whatever the keyframes draw on (2026-10-11)
    assert kw["model"] == element_sheet.SHEET_MODEL == "gemini-3-pro-image"   # the env-override lane
    assert kw["image_size"] == "2K"
    assert [label for label, _ in kw["reference_image"]] == ["Michael — photo 1", "Michael — photo 2"]
    assert [data for _, data in kw["reference_image"]] == [b"photo-a", b"photo-b"]


def test_draw_never_raises_and_reports_the_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(element_sheet, "SHEET_MODEL", "gemini-3-pro-image")
    folder = tmp_path / "x"
    folder.mkdir()
    assert element_sheet.draw("prop", "x", [], folder)["error"] == "no photos to draw the sheet from"
    (folder / "a.jpg").write_bytes(b"photo")
    monkeypatch.setattr(nano_banana, "generate_from_prompt",
                        lambda *a, **k: {"ok": False, "error": "daily cap"})
    assert element_sheet.draw("prop", "x", [folder / "a.jpg"], folder)["error"] == "daily cap"
    monkeypatch.setattr(nano_banana, "generate_from_prompt",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert element_sheet.draw("prop", "x", [folder / "a.jpg"], folder)["error"] == "boom"
    assert not (folder / "sheet.jpg").exists()


def test_literal_skips_the_still_frame_wrapper_and_bank_false_keeps_it_off_the_wall(
        tmp_path, monkeypatch):
    """The two flags the sheet relies on, checked on the lane itself."""
    from src import generative, render_assets
    seen = {}
    monkeypatch.setattr(nano_banana, "has_key", lambda a=None: True)
    monkeypatch.setattr(generative, "init", lambda **k: None)
    # the adapter asks ensure() since 2026-10-11; with only init stubbed it
    # still drew nothing on the database but took the schema-init lock on it
    monkeypatch.setattr(generative, "ensure", lambda **k: None)
    monkeypatch.setattr(generative, "cap_error", lambda *a, **k: None)
    monkeypatch.setattr(nano_banana, "generations_today", lambda **k: 0)
    monkeypatch.setattr(nano_banana, "RENDER_DIR", tmp_path)
    # a still is charged since 2026-09-28; this test is about the two flags,
    # not the ledger, and passes no database -- so no hold is taken at all
    # (an unstubbed take() would read whatever DATABASE_URL resolves to)
    monkeypatch.setattr(nano_banana.charging.Charge, "take", lambda self: None)

    def fake_image(prompt, out_path, **kw):
        seen["prompt"] = prompt
        Path(out_path).write_bytes(b"png")
        return out_path

    monkeypatch.setattr(nano_banana, "generate_image", fake_image)
    monkeypatch.setattr(nano_banana, "_shot_row_for_prompt", lambda *a, **k: 1)
    monkeypatch.setattr(generative, "record_generation",
                        lambda *a, **k: seen.setdefault("params", k["params"]) and 42)
    monkeypatch.setattr(render_assets, "record_best_effort",
                        lambda **k: seen.setdefault("banked", True) or {"id": 1, "rag": None})
    from src import storage
    monkeypatch.setattr(storage, "configured", lambda: False)

    out = nano_banana.generate_from_prompt("Five panels, FACE CLOSE UP first",
                                           literal=True, bank=False, source="element_sheet",
                                           account_id=1)
    assert out["ok"], out
    assert seen["prompt"] == "Five panels, FACE CLOSE UP first"
    assert seen["params"]["framing"] == "literal" and seen["params"]["source"] == "element_sheet"
    assert "banked" not in seen and out["asset_id"] is None


# --- the photos, wherever they live (2026-10-11) ------------------------------


class _Reply:
    def __init__(self, content=b"", status=200):
        self.content, self.status_code = content, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_photo_files_reads_the_folder_first_and_the_bucket_when_there_is_none(
        tmp_path, monkeypatch):
    """One reader for every door that draws a sheet. A photo on this
    machine is the file itself; one that lives in the bucket only (the
    deployed API has no element folders) is fetched into the scratch
    folder; the sheet already drawn, a photo that cannot be fetched and an
    oversized one are skipped, never guessed at."""
    import requests

    from src import asset_shelf
    here = tmp_path / "characters" / "michael" / "a.jpg"
    here.parent.mkdir(parents=True)
    here.write_bytes(b"on disk")
    monkeypatch.setattr(asset_shelf, "resolve_photo",
                        lambda url, *a, **k: here if url.endswith("/a.jpg") else None)
    asked = []
    monkeypatch.setattr(asset_shelf, "fetch_url",
                        lambda url, account_id=None: asked.append((url, account_id)) or
                        ("" if url.endswith("/local-only.jpg") else f"https://cdn.test/m/7{url}"))
    bucket = {"https://cdn.test/m/7/characters/michael/photo/b.jpg": _Reply(b"in the bucket"),
              "https://cdn.test/m/7/characters/michael/photo/gone.jpg": _Reply(status=404),
              "https://cdn.test/m/7/characters/michael/photo/huge.jpg":
                  _Reply(b"x" * (element_sheet.PHOTO_BYTES_MAX + 1))}
    monkeypatch.setattr(requests, "get", lambda url, timeout=None: bucket[url])
    scratch = tmp_path / "scratch"
    names = ["a.jpg", "sheet.jpg", "b.jpg", "gone.jpg", "huge.jpg", "local-only.jpg"]
    files = element_sheet.photo_files(
        [f"/characters/michael/photo/{n}" for n in names], scratch, account_id=7)
    assert files[0] == here and len(files) == 2
    assert files[1].parent == scratch and files[1].read_bytes() == b"in the bucket"
    # the bucket is asked under THIS account's keys, and never for the sheet
    assert all(account == 7 for _, account in asked)
    assert not any(url.endswith("/sheet.jpg") or url.endswith("/a.jpg") for url, _ in asked)
    assert element_sheet.photo_files([], scratch) == []


def test_a_sheet_drawn_from_bucket_photos_is_not_left_alone_in_the_folder(tmp_path):
    """The photo listing reads disk FIRST. A machine that holds none of an
    element's photos must not be left a folder with only sheet.jpg in it,
    or the drawing becomes the element's only photo there."""
    folder, scratch = tmp_path / "characters" / "michael", tmp_path / "scratch"
    fetched = [scratch / "photo-0.jpg", scratch / "photo-1.jpg"]
    assert element_sheet.out_dir_for(folder, fetched, scratch) == scratch / "sheet"
    # any photo on this machine means the folder is the element's real one
    assert element_sheet.out_dir_for(folder, [folder / "a.jpg", fetched[0]], scratch) == folder
    assert element_sheet.out_dir_for(folder, [folder / "a.jpg"], scratch) == folder
    assert element_sheet.out_dir_for(folder, [], scratch) == folder


def test_the_reader_stops_at_as_many_photos_as_a_sheet_is_drawn_from(tmp_path, monkeypatch):
    """An element with nineteen photos is drawn from six, so six are read:
    the rest are never asked of the bucket. A photo that cannot be read
    does not use up a place."""
    import requests

    from src import asset_shelf
    monkeypatch.setattr(asset_shelf, "resolve_photo", lambda url, *a, **k: None)
    monkeypatch.setattr(asset_shelf, "fetch_url",
                        lambda url, account_id=None: f"https://cdn.test{url}")
    asked = []

    def get(url, timeout=None):
        asked.append(url.rsplit("/", 1)[-1])
        return _Reply(status=404) if url.endswith("/02.jpg") else _Reply(b"jpeg")

    monkeypatch.setattr(requests, "get", get)
    names = [f"{n:02d}.jpg" for n in range(1, 20)]
    urls = [f"/characters/michael/photo/{n}" for n in names] + ["/characters/michael/photo/sheet.jpg"]
    files = element_sheet.photo_files(urls, tmp_path / "scratch", account_id=1)
    assert len(files) == element_sheet.MAX_REFERENCES == 6
    # 02 could not be read, so 07 is the sixth -- and nothing past it was fetched
    assert asked == names[:7]
    # a caller may ask for fewer, or for all of them
    assert len(element_sheet.photo_files(urls, tmp_path / "two", limit=2)) == 2
    assert len(element_sheet.photo_files(urls, tmp_path / "all", limit=99)) == 18



# --- GPT Image 2.5 (2026-10-26, Mike: "its more accurate") -------------------


def test_the_sheet_defaults_to_gpt_image_25_sunburst_on_fal():
    from src import fal
    assert element_sheet.SHEET_MODEL == "gpt-image-2.5-sunburst"
    assert element_sheet.on_fal() and element_sheet.SHEET_MODEL in fal.IMAGE_MODELS
    assert fal.IMAGE_MODELS[element_sheet.SHEET_MODEL].get("edit")      # it takes photos
    assert element_sheet.price_usd() == fal.image_usd(element_sheet.SHEET_MODEL, "16:9")
    assert element_sheet.credits() > 0


def test_draw_on_fal_sends_every_photo_as_a_reference(tmp_path, monkeypatch):
    from src import fal
    folder = tmp_path / "michael"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"photo-a")
    (folder / "b.jpg").write_bytes(b"photo-b")
    (folder / "sheet.jpg").write_bytes(b"an old drawing")
    rendered = tmp_path / "gpt.jpg"
    rendered.write_bytes(b"not-really-a-jpeg")
    calls = []

    def fake_still(prompt, **kw):
        calls.append((prompt, kw))
        return {"ok": True, "path": str(rendered), "generation_id": 9,
                "references": len(kw["reference_urls"])}

    monkeypatch.setattr(fal, "as_image_url",
                        lambda data, account_id=None: "https://cdn.test/" + data.decode())
    monkeypatch.setattr(fal, "generate_image_from_prompt", fake_still)
    result = element_sheet.draw("character", "Michael",
                                [folder / "a.jpg", folder / "sheet.jpg", folder / "b.jpg"],
                                folder, account_id=1)
    assert result["ok"] and result["generation_id"] == 9
    [(prompt, kw)] = calls
    assert "three-quarter view" in prompt
    assert kw["model"] == "gpt-image-2.5-sunburst" and kw["aspect"] == "16:9"
    assert kw["reference_urls"] == ["https://cdn.test/photo-a", "https://cdn.test/photo-b"]
    assert kw["bank"] is False and kw["brand_kit"] is False
    assert kw["source"] == "element_sheet" and kw["approved"] is True


def test_draw_on_fal_refuses_rather_than_draw_from_fewer_photos(tmp_path, monkeypatch):
    from src import fal
    folder = tmp_path / "x"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"photo-a")
    (folder / "b.jpg").write_bytes(b"photo-b")
    monkeypatch.setattr(fal, "as_image_url",
                        lambda data, account_id=None: None if data == b"photo-b" else "https://cdn.test/a")
    monkeypatch.setattr(fal, "generate_image_from_prompt",
                        lambda *a, **k: pytest.fail("must not spend with a photo missing"))
    result = element_sheet.draw("character", "x", [folder / "a.jpg", folder / "b.jpg"], folder)
    assert not result["ok"] and "nothing was charged" in result["error"]
    assert not (folder / "sheet.jpg").exists()
