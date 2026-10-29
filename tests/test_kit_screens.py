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


# ---------- the brain's make_screen ----------

def _resp(text=None, calls=()):
    import types as pytypes
    return pytypes.SimpleNamespace(
        text=text, function_calls=[pytypes.SimpleNamespace(name=n, args=a) for n, a in calls],
        candidates=[pytypes.SimpleNamespace(content=pytypes.SimpleNamespace(role="model",
                                                                              parts=[]))])


def _turn(monkeypatch, responses, *, kit):
    from src import creative_guide, gemini_utils, guide_tools
    seen = []

    def generate(client, model, contents, **kwargs):
        seen.append((list(contents), kwargs))
        r = responses.pop(0)
        return r if kwargs.get("raw") else r.text

    monkeypatch.setattr(gemini_utils, "generate_with_retry", generate)
    tools, run_tool = guide_tools.session(local=True, maker=True, brand_kit=kit)
    reply = creative_guide.respond(
        creative_guide.Conversation(messages=[{"role": "user",
                                               "content": "a Staffed schedule screen for Gygler"}]),
        client=object(), grounding={}, tools=tools, run_tool=run_tool, output="image",
        brand_kit=kit)
    return reply, seen


def test_a_maker_turn_with_a_kit_proposes_a_screen_its_card_can_draw(monkeypatch):
    reply, seen = _turn(monkeypatch, [_resp(calls=[("make_screen", {"kit_id": 1, **STAFFED})])],
                        kit=GYGLER)
    proposal = reply["proposal"]
    assert proposal["tool"] == "make_screen" and proposal["label"] == "Draw this screen"
    assert proposal["args"]["spec"] == kit_screens.clean(STAFFED)
    assert proposal["args"]["kit_id"] == 1 and proposal["args"]["warnings"] == []
    assert reply["message"].startswith("Here is the phone screen, 3-row schedule: Staffed")
    config = seen[0][1]["config"]
    assert "APP SCREENS FROM THE KIT" in config.system_instruction
    assert "make_screen" in [d.name for t in config.tools for d in t.function_declarations]


def test_a_wrong_kit_or_a_bad_shape_goes_back_to_the_model(monkeypatch):
    reply, seen = _turn(monkeypatch, [
        _resp(calls=[("make_screen", {"kit_id": 9, **STAFFED})]),
        _resp(calls=[("make_screen", {"kit_id": 1, "template": "map"})]),
        _resp(calls=[("make_screen", {"kit_id": 1, **HERO})]),
    ], kit=GYGLER)
    told = [p.function_response.response["result"] for c in seen[2][0]
            for p in (getattr(c, "parts", None) or []) if getattr(p, "function_response", None)]
    assert any("kit 1 (Gygler) only" in t for t in told)
    assert any("template is one of" in t for t in told)
    assert reply["proposal"]["args"]["spec"]["template"] == "hero_cta"


def test_no_kit_or_exploring_means_no_screen_tool():
    from src import guide_tools
    names = lambda **kw: [s["name"] for s in guide_tools.session(local=True, **kw)[0]]  # noqa: E731
    assert "make_screen" in names(maker=True, brand_kit=GYGLER)
    assert "make_screen" not in names(maker=True)
    assert "make_screen" not in names(maker=True, brand_kit=GYGLER, explore=True)
    assert "make_screen" not in names(brand_kit=GYGLER)


def test_the_routes_draw_free_and_keep_one_still(pg, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import app.main as app_main
    from app import auth
    from src import accounts, brand_kits, generative, render_assets, watermark
    from src.cut import sources
    for m in (accounts, generative, render_assets, brand_kits):
        m.init(pg)
    mine = accounts.upsert_account("ks-routes", "Mine", "#fff", dsn=pg)
    other = accounts.upsert_account("ks-other", "Other", "#fff", dsn=pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "bk")
    monkeypatch.setattr(sources, "RENDERS_DIR", tmp_path)
    monkeypatch.setattr(watermark, "publish_file", lambda *a, **k: None)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "u1", "email": "x@e.com"})
    kit = brand_kits.create("Gygler", GYGLER["spec"], pg, account_id=mine)
    theirs = brand_kits.create("Theirs", {}, pg, account_id=other)
    app_main.app.dependency_overrides[auth.current_account_id] = lambda: mine
    try:
        client = TestClient(app_main.app)
        seen = client.post(f"/api/brand-kits/{kit['id']}/screens/preview", json={"spec": STAFFED})
        assert seen.status_code == 200, seen.text
        assert seen.json()["image"].startswith("data:image/png;base64,")
        assert seen.json()["size"] == [1170, 2532]
        assert kit_rows(pg) == 0                             # a preview files nothing
        bad = client.post(f"/api/brand-kits/{kit['id']}/screens/preview",
                          json={"spec": {"template": "map"}})
        assert bad.status_code == 400 and "template" in bad.json()["error"]["message"]
        assert client.post(f"/api/brand-kits/{theirs['id']}/screens",
                           json={"spec": STAFFED}).status_code == 404
        kept = client.post(f"/api/brand-kits/{kit['id']}/screens", json={"spec": STAFFED})
        assert kept.status_code == 200, kept.text
        assert kept.json()["asset"].startswith("gen:")
        assert kit_rows(pg) == 1
    finally:
        app_main.app.dependency_overrides[auth.current_account_id] = lambda: None


def kit_rows(dsn) -> int:
    """How many kit screens the Library holds."""
    from src import db
    with db.connect(dsn) as conn:
        return conn.execute(
            "SELECT count(*) AS n FROM generated_assets WHERE tool = 'kit'").fetchone()["n"]
