"""Vesper and the brand kit (2026-10-21): "a Gygler hero image" used to send
research_look and find_references to the WEB for a brand whose look, logo and
references were already in a kit, and the brain asked about musicians on
stage for a hospitality-staffing company. A kit the project picked, or one
of the account's kits the person NAMES, is now what the brain works from.
"""
import io
import json

import pytest
from google.genai import types

from app import api
from src import (
    accounts,
    assistant_brain,
    brand_kits,
    creative_guide,
    entities,
    guide_tools,
    look_research,
    preprod,
    projects,
)

KIT = {"identity": {"positioning": "Human logistics for hospitality: shift staff on demand",
                    "audience": "hotel and venue managers", "url": "gygler.com"},
       "palette": [{"hex": "#FF880B", "role": "primary", "name": "Gygler orange"},
                   {"hex": "#FAF0E4", "role": "background", "name": "Cream"}],
       "look": {"style": "Light, warm and clean. Natural daylight, real hospitality venues.",
                "banned": ["neon", "cold blue lighting"]},
       "voice": {"tone": "Direct, warm.", "use": ["Gyg"], "avoid": ["staffing agency"]}}


def png(colour=(255, 136, 11, 255)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (32, 16), colour).save(buf, "PNG")
    return buf.getvalue()


def jpg():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 16), (250, 240, 228)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def k(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    brand_kits.init(pg)
    projects.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    mine = accounts.upsert_account("bkg-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("bkg-theirs", "Theirs", "#fff", dsn=pg)
    kit = brand_kits.create("Gygler", KIT, pg, account_id=mine)
    brand_kits.add_asset(kit["id"], "logo_light", png(), pg, account_id=mine)
    brand_kits.add_asset(kit["id"], "reference", jpg(), pg, account_id=mine)
    other = brand_kits.create("Northwind", {}, pg, account_id=theirs)
    return {"pg": pg, "mine": mine, "theirs": theirs,
            "kit": brand_kits.get(kit["id"], pg, account_id=mine), "other": other}


# -- which kit a conversation is under ---------------------------------------

def test_a_kit_is_found_by_its_name_in_the_persons_words(k):
    found = brand_kits.named_in(["make a GYGLER hero image"], k["pg"], account_id=k["mine"])
    assert found and found["id"] == k["kit"]["id"]
    assert brand_kits.named_in(["Gygler's new ad"], k["pg"], account_id=k["mine"])


def test_a_word_that_only_contains_the_name_is_not_the_kit(k):
    assert brand_kits.named_in(["the gyglerverse"], k["pg"], account_id=k["mine"]) is None
    assert brand_kits.named_in(["a hero image"], k["pg"], account_id=k["mine"]) is None


def test_another_accounts_kit_is_never_found(k):
    assert brand_kits.named_in(["Northwind ad"], k["pg"], account_id=k["mine"]) is None
    assert brand_kits.named_in(["Gygler ad"], k["pg"], account_id=k["theirs"]) is None


def test_the_route_prefers_the_projects_pick_then_a_named_kit(k, monkeypatch):
    conv = creative_guide.Conversation.model_validate(
        {"messages": [{"role": "user", "content": "a Gygler hero image"}]})
    got = api._guide_kit(None, conv, k["mine"])
    assert got and got["id"] == k["kit"]["id"]
    second = brand_kits.create("Second", {}, k["pg"], account_id=k["mine"])
    project = projects.create("Launch", "x", k["pg"], account_id=k["mine"])
    projects.set_brand_kit(project["id"], second["id"], k["pg"], account_id=k["mine"])
    project = projects.get(project["id"], k["pg"], account_id=k["mine"])
    assert api._guide_kit(project, conv, k["mine"])["id"] == second["id"]
    plain = creative_guide.Conversation.model_validate(
        {"messages": [{"role": "user", "content": "a hero image"}]})
    assert api._guide_kit(None, plain, k["mine"]) is None


# -- what the brain is told and shown -----------------------------------------

def test_the_brain_is_told_who_the_brand_is_and_its_look(k):
    block = creative_guide.kit_instructions(k["kit"])
    for said in ("Gygler", "Human logistics for hospitality", "hotel and venue managers",
                 "#FF880B", "Natural daylight", "neon", "staffing agency", "gygler.com",
                 "Do not call research_look or find_references for the brand"):
        assert said in block
    assert "named it in this conversation" in block
    assert creative_guide.kit_instructions(None) == ""


def test_the_brain_sees_the_logo_and_the_look_references(k):
    contents = [types.Content(role="user", parts=[types.Part.from_text(text="hi")])]
    creative_guide._attach_kit(contents, k["kit"])
    labels = [p.text for p in contents[-1].parts if p.text]
    images = [p for p in contents[-1].parts if p.inline_data]
    assert len(images) == 2
    assert any("LOGO" in t for t in labels) and any("LOOK reference" in t for t in labels)
    untouched = [types.Content(role="user", parts=[types.Part.from_text(text="hi")])]
    creative_guide._attach_kit(untouched, None)
    assert len(untouched[-1].parts) == 1


# -- its reads answer the brand from the kit, never the web --------------------

def test_researching_the_brands_own_look_reads_the_kit_not_the_web(k, monkeypatch):
    monkeypatch.setattr(look_research, "research",
                        lambda *a, **kw: pytest.fail("the web was read for the kit's own look"))
    _, run_tool = guide_tools.session(account_id=k["mine"], local=True, brand_kit=k["kit"])
    text = run_tool("research_look", {"subject": "Gygler"})
    assert "BRAND KIT" in text and "#FF880B" in text and "Natural daylight" in text


def test_hunting_the_web_for_the_brand_is_refused_with_the_way_on(k, monkeypatch):
    monkeypatch.setattr(assistant_brain, "find_references",
                        lambda *a, **kw: pytest.fail("the web was hunted for the brand"))
    _, run_tool = guide_tools.session(account_id=k["mine"], local=True, brand_kit=k["kit"])
    with pytest.raises(guide_tools.Refused, match="without the brand's name"):
        run_tool("find_references", {"scene": "Gygler brand logo on a stage"})


def test_an_ordinary_hunt_still_runs_under_a_kit(k, monkeypatch):
    seen = {}

    def hunt(scene, **kw):
        seen["scene"] = scene
        return {"needs": [], "candidates": []}

    monkeypatch.setattr(assistant_brain, "find_references", hunt)
    monkeypatch.setattr(assistant_brain, "sheet_for_model", lambda result: json.dumps(result))
    _, run_tool = guide_tools.session(account_id=k["mine"], local=True, brand_kit=k["kit"])
    run_tool("find_references", {"scene": "a busy hotel kitchen at lunch"})
    assert seen["scene"] == "a busy hotel kitchen at lunch"


def test_a_still_that_names_the_kit_is_dressed_in_its_look(k):
    dressed = brand_kits.dress("Subject: hero image.",
                               brand_kits.named_in(["Gygler hero image"], k["pg"],
                                                   account_id=k["mine"]))
    assert "BRAND LOOK (Gygler)" in dressed and "#FF880B" in dressed
    assert brand_kits.dress("Subject: hero image.", None) == "Subject: hero image."
