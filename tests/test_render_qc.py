"""A look at every landed clip (2026-10-25, src/render_qc.py): four plain
facts and up to three notes, kept per shot and printed on the Render card.
Advice only: it never fails a render, never spends, and is off with
PHANTRA_RENDER_QC=0."""
import json

import pytest

from app import api, jobs
from src import gemini_utils, render_qc


def test_an_answer_is_held_to_the_four_facts_and_three_short_notes():
    raw = "```json\n" + json.dumps({
        "brand_said": "misspoken", "text": "garbled", "product": "sparkly", "people": "fine",
        "notes": ["at 3s the voice says Giggler", "  ", "at 5s the logo smears " * 20, "a", "b"]}) + "\n```"
    seen = render_qc.check(raw)
    assert seen["facts"] == {"brand_said": "misspoken", "text": "garbled", "people": "fine"}
    assert len(seen["notes"]) == 3 and seen["notes"][0] == "at 3s the voice says Giggler"
    assert len(seen["notes"][1]) <= render_qc.NOTE_MAX + 1
    assert render_qc.problems(seen["facts"]) == ["the brand name is said wrong",
                                                 "on-screen words are garbled"]
    assert render_qc.check("no json here") is None and render_qc.check(None) is None


def test_the_prompt_names_the_brand_products_and_quoted_words():
    assert render_qc.quoted_words('A phone shows “Shift booked” and a sign reads "OPEN"') == \
        ["Shift booked", "OPEN"]
    text = render_qc.build_prompt('the screen reads "Staffed"', "Gygler", ["Gygler app"], ["Staffed"])
    assert "The brand: Gygler" in text and "Gygler app" in text and '"Staffed"' in text
    assert "{" in text and "{prompt}" not in text


def test_a_clip_is_watched_once_and_a_failure_is_no_notes(tmp_path, monkeypatch):
    clip = tmp_path / "shot.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    asked = []

    def generate(client, model, contents, **kw):
        asked.append(kw)
        return json.dumps({"brand_said": "said", "text": "n/a", "product": "present",
                           "people": "fine", "notes": []})
    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    seen = render_qc.review(clip, prompt="x", client=object(), account_id=7)
    assert seen == {"facts": {"brand_said": "said", "text": "n/a", "product": "present",
                              "people": "fine"}, "notes": []}
    assert asked == [{"stage": "render_qc", "account_id": 7}]

    def broken(*a, **k):
        raise RuntimeError("gemini down")
    monkeypatch.setattr(gemini_utils, "generate_with_retry", broken)
    assert render_qc.review(clip, prompt="x", client=object()) is None
    assert render_qc.review(tmp_path / "missing.mp4", prompt="x", client=object()) is None
    monkeypatch.setenv("PHANTRA_RENDER_QC", "0")
    assert render_qc.review(clip, prompt="x", client=object()) is None


def test_checks_are_kept_per_shot_per_account_newest_first(pg):
    from src import accounts
    accounts.init(pg)
    one = accounts.upsert_account("qc-one", "One", "#fff", dsn=pg)
    two = accounts.upsert_account("qc-two", "Two", "#fff", dsn=pg)
    render_qc.init(pg)
    seen = {"facts": {"text": "garbled"}, "notes": ["at 2s the menu smears"]}
    render_qc.record(41, 2, "m/1/renders/a.mp4", seen, pg, account_id=one)
    render_qc.record(41, 2, "m/1/renders/b.mp4", {"facts": {}, "notes": []}, pg, account_id=one)
    render_qc.record(41, 3, "m/1/renders/c.mp4", seen, pg, account_id=one)
    render_qc.record(41, 3, "m/2/renders/d.mp4", {"facts": {}, "notes": []}, pg, account_id=two)
    got = render_qc.for_concept(41, pg, account_id=one)
    assert got["2"] == {"media": "m/1/renders/b.mp4", "problems": [], "notes": []}  # re-rendered
    assert got["3"]["problems"] == ["on-screen words are garbled"]
    assert render_qc.for_concept(41, pg, account_id=two)["3"]["media"] == "m/2/renders/d.mp4"
    assert render_qc.for_concept(99, pg, account_id=one) == {}


def test_a_landed_shot_is_checked_and_a_broken_check_never_fails_the_render(monkeypatch):
    from src import brand_kits
    job = jobs.start("render", "t", lambda j: {"detail": "ok"}, account_id=1)
    monkeypatch.setattr(brand_kits, "for_concept", lambda cid, account_id=None: {"name": "Gygler"})
    calls = []
    monkeypatch.setattr(render_qc, "check_shot", lambda *a, **k: calls.append((a, k)))
    api._check_clip(job, 5, 2, {"ok": True, "path": "/x.mp4"}, "shot two", 1)
    assert calls[0][0][:2] == (5, 2) and calls[0][1]["prompt"] == "shot two"
    assert calls[0][1]["kit"] == {"name": "Gygler"}

    def boom(*a, **k):
        raise RuntimeError("no")
    monkeypatch.setattr(render_qc, "check_shot", boom)
    api._check_clip(job, 5, 2, {"ok": True, "path": "/x.mp4"}, "p", 1)      # no raise
    monkeypatch.setenv("PHANTRA_RENDER_QC", "0")
    calls.clear()
    monkeypatch.setattr(render_qc, "check_shot", lambda *a, **k: calls.append(a))
    api._check_clip(job, 5, 2, {"ok": True, "path": "/x.mp4"}, "p", 1)
    assert calls == []


@pytest.fixture(autouse=True)
def _qc_on(monkeypatch):
    monkeypatch.delenv("PHANTRA_RENDER_QC", raising=False)
