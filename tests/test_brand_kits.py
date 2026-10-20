"""Brand kits with a kit SET (docs/tasks/task-brand-kit.md): the kit reaches
the writer, every still, keyframe and clip, the quote, and the Cut export --
and switching the project to a second kit changes all of it with no other
edit. The no-kit half is tests/test_brand_kit_no_kit.py.

Nothing here renders anything paid: providers are stubbed at their call,
and the one real ffmpeg export runs on testsrc clips.
"""
import io
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import (
    accounts,
    brand_kits,
    db,
    entities,
    fal,
    generative,
    imagery,
    nano_banana,
    preprod,
    pricing,
    project_context,
    projects,
    scene_chain,
    shootgen,
    timeline,
)
from src.cut import brand as cut_brand
from src.cut import doc as d
from src.cut import render

client = TestClient(app)

FONT_CANDIDATES = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial.ttf")
FONT = next((Path(p) for p in FONT_CANDIDATES if Path(p).is_file()), None)
needs_font = pytest.mark.skipif(FONT is None, reason="no TrueType font on this machine")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

KIT_A = {"identity": {"tagline": "Get a Gyg, stay for good.", "url": "gygler.com",
                      "positioning": "Shift work without the chaos", "audience": "hotel managers"},
         "palette": [{"hex": "#f7931e", "role": "primary", "name": "orange"},
                     {"hex": "#FFF4E6", "role": "background", "name": "cream"},
                     {"hex": "#8A4B08", "role": "text"}],
         "captions": {"font": "heading", "size": 0.05, "fill": "primary", "box": "background",
                      "position": "lower_third", "uppercase": True},
         "look": {"style": "Warm orange-on-cream, soft daylight, clean UI surfaces.",
                  "banned": ["neon", "night clubs"]},
         "voice": {"tone": "Friendly, brisk, confident.", "use": ["Gyg"], "avoid": ["gig economy"],
                   "cta": "Short imperative, ends with the URL."},
         "motion": {"transition": "fade", "seconds": 0.5},
         "end_card": {"seconds": 2}}
KIT_B = {"palette": [{"hex": "#0A2540", "role": "background"},
                     {"hex": "#00D4FF", "role": "primary"}],
         "look": {"style": "Deep navy, cool rim light, glossy product surfaces.",
                  "banned": ["warm tones"]},
         "voice": {"tone": "Precise and technical."},
         "captions": {"position": "top", "fill": "primary"}}


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    stub = {"id": 1, "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)


def png(w=64, h=32, colour=(200, 80, 20, 255)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def dbx(pg, monkeypatch, tmp_path):
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    generative.init(pg)
    brand_kits.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(brand_kits, "FILES_DIR", tmp_path / "brandkits")
    monkeypatch.delenv("PHANTRA_MOTION_DIRECTIVE", raising=False)
    mine = accounts.upsert_account("bk-mine", "Mine", "#fff", dsn=pg)
    theirs = accounts.upsert_account("bk-theirs", "Theirs", "#fff", dsn=pg)
    return pg, mine, theirs


@pytest.fixture
def kitted(dbx):
    """A project on kit A, a timed scene in it, and kit B ready to switch to."""
    pg, mine, _ = dbx
    a = brand_kits.create("Gygler", KIT_A, pg, account_id=mine)
    b = brand_kits.create("Northwind", KIT_B, pg, account_id=mine)
    brand_kits.add_asset(a["id"], "reference", png(), pg, account_id=mine)
    a = brand_kits.get(a["id"], pg, account_id=mine)          # with its file, and its hash
    project = projects.create("Launch", "Ads for the launch", pg, account_id=mine)
    projects.set_brand_kit(project["id"], a["id"], pg, account_id=mine)
    tl = {"seconds": 6, "planner": "split", "source": "x", "continuity": "Hotel kitchen.",
          "parts": [{"n": 1, "start": 0, "end": 3, "seconds": 3, "text": "t", "prompt": "A cook.",
                     "refs": ["/refs/a.jpg"], "reference_image": "https://cdn.example/k1.png"}]}
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                    "prompt": "A cook plates a dish.", "refs": ["/refs/a.jpg"],
                    "reference_image": "https://cdn.example/k0.png", "timeline": tl}]},
        dsn=pg, account_id=mine)
    with db.connect(pg) as conn:
        conn.execute("UPDATE shoot_concepts SET project_id = %s WHERE id = %s AND account_id = %s",
                     (project["id"], cid, mine))
    return {"pg": pg, "mine": mine, "a": a, "b": b, "project": project, "cid": cid}


def switch(k, kit):
    projects.set_brand_kit(k["project"]["id"], kit and kit["id"], k["pg"], account_id=k["mine"])


# --------------------------------------------------------------------------
# the spec: refused, never clamped
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad,field", [
    ({"palette": [{"hex": "orange", "role": "primary"}]}, "palette"),
    ({"palette": [{"hex": "#000000", "role": "primary"}, {"hex": "#111111", "role": "primary"}]},
     "palette"),
    ({"motion": {"transition": "spin3d"}}, "transition"),
    ({"captions": {"size": 0.5}}, "caption size"),
    ({"look": {"style": "x" * 2000}}, "style description"),
    ({"products": [{"kind": "character", "id": 1}]}, "products"),
])
def test_a_value_off_its_legal_set_is_refused(bad, field):
    with pytest.raises(brand_kits.KitError) as e:
        brand_kits.clean_spec(bad)
    assert e.value.field == field


def test_the_spec_keeps_what_was_given_and_fills_the_rest():
    spec = brand_kits.clean_spec(KIT_A)
    assert spec["palette"][0]["hex"] == "#F7931E"
    assert spec["look"]["banned"] == ["neon", "night clubs"]
    assert spec["end_card"] == {"on": True, "seconds": 2.0, "background": "background",
                                "show_url": True}
    assert spec["sound"]["loudness"] is None and spec["v"] == 1


# --------------------------------------------------------------------------
# tenancy
# --------------------------------------------------------------------------

def test_a_kit_is_invisible_to_another_account_and_cannot_be_picked_by_it(dbx):
    pg, mine, theirs = dbx
    kit = brand_kits.create("Mine", {}, pg, account_id=mine)
    assert brand_kits.get(kit["id"], pg, account_id=theirs) is None
    assert brand_kits.list_kits(pg, account_id=theirs) == []
    assert brand_kits.update(kit["id"], pg, account_id=theirs, name="stolen") is None
    their_project = projects.create("Theirs", "", pg, account_id=theirs)
    with pytest.raises(ValueError, match="no brand kit"):
        projects.set_brand_kit(their_project["id"], kit["id"], pg, account_id=theirs)


def test_a_deleted_kit_reads_as_none_and_undo_brings_it_back(kitted):
    k = kitted
    project = projects.get(k["project"]["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_project(project, k["pg"])["id"] == k["a"]["id"]
    brand_kits.delete(k["a"]["id"], k["pg"], account_id=k["mine"])
    assert brand_kits.for_project(project, k["pg"]) is None
    brand_kits.delete(k["a"]["id"], k["pg"], account_id=k["mine"], restore=True)
    assert brand_kits.for_project(project, k["pg"])["id"] == k["a"]["id"]


def test_a_project_without_a_kit_carries_no_kit_key(dbx):
    pg, mine, _ = dbx
    project = projects.create("Plain", "", pg, account_id=mine)
    assert "brand_kit_id" not in projects.get(project["id"], pg, account_id=mine)


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------

@needs_font
def test_a_font_needs_the_licence_and_is_read_by_family(dbx):
    pg, mine, _ = dbx
    kit = brand_kits.create("Fonts", {}, pg, account_id=mine)
    data = FONT.read_bytes()
    with pytest.raises(brand_kits.KitError, match="right to embed"):
        brand_kits.add_asset(kit["id"], "font_heading", data, pg, account_id=mine)
    added = brand_kits.add_asset(kit["id"], "font_heading", data, pg, account_id=mine,
                                 filename=FONT.name, licensed=True)
    assert added["meta"]["family"] and added["meta"]["licensed"] is True
    # one heading font per kit: a second replaces the first
    brand_kits.add_asset(kit["id"], "font_heading", data, pg, account_id=mine, licensed=True)
    fonts = [a for a in brand_kits.get(kit["id"], pg, account_id=mine)["assets"]
             if a["role"] == "font_heading"]
    assert len(fonts) == 1


def test_references_cap_at_eight_and_a_duplicate_shares_the_files(dbx):
    pg, mine, _ = dbx
    kit = brand_kits.create("Refs", {}, pg, account_id=mine)
    for i in range(8):
        brand_kits.add_asset(kit["id"], "reference", png(colour=(i, 0, 0, 255)), pg,
                             account_id=mine)
    with pytest.raises(brand_kits.KitError, match="at most 8"):
        brand_kits.add_asset(kit["id"], "reference", png(colour=(99, 0, 0, 255)), pg,
                             account_id=mine)
    with pytest.raises(brand_kits.KitError, match="must be png"):
        brand_kits.add_asset(kit["id"], "logo_light", b"not an image at all", pg, account_id=mine)
    copy = brand_kits.duplicate(kit["id"], pg, account_id=mine)
    assert copy["name"] == "Refs copy"
    assert sorted(a["stored"] for a in copy["assets"]) == sorted(
        a["stored"] for a in brand_kits.get(kit["id"], pg, account_id=mine)["assets"])
    assert copy["hash"] == brand_kits.get(kit["id"], pg, account_id=mine)["hash"]


# --------------------------------------------------------------------------
# the writer and the brain
# --------------------------------------------------------------------------

def test_the_writer_reads_the_kit_and_a_switch_changes_it(kitted, monkeypatch):
    k = kitted
    monkeypatch.setattr(shootgen, "gold_standard_example", lambda: "(x)")

    def written():
        project = projects.get(k["project"]["id"], k["pg"], account_id=k["mine"])
        with project_context.active(project):
            return shootgen.build_scene_brief_prompt(spark="s", seconds=6)

    on_a = written()
    assert "BRAND KIT “Gygler”" in on_a and "Friendly, brisk, confident." in on_a
    assert "Words never to use: gig economy" in on_a and "Never write into a scene: neon" in on_a
    switch(k, k["b"])
    on_b = written()
    assert "BRAND KIT “Northwind”" in on_b and "Precise and technical." in on_b
    assert "Gygler" not in on_b
    switch(k, None)
    assert "BRAND KIT" not in written()


def test_products_and_cast_are_named_from_the_elements(dbx):
    pg, mine, _ = dbx
    prop = entities.add_prop("Gyg App", dsn=pg, account_id=mine)
    kit = brand_kits.create("P", {"products": [{"kind": "prop", "id": prop, "claims": ["free"]}],
                                  "never_claim": ["guaranteed shifts"]}, pg, account_id=mine)
    block = brand_kits.brief_lines(kit, pg)
    assert "Product: Gyg App -- the only claims allowed: free" in block
    assert "Never claim: guaranteed shifts" in block


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def test_a_clip_carries_the_look_and_a_switch_changes_it(kitted, monkeypatch):
    k = kitted
    sent = {}

    def fake_video(prompt, out_path, **kw):
        sent.update(prompt=prompt, params=kw["track"]["params"])
        raise RuntimeError("stop")

    monkeypatch.setattr(fal, "generate_video", fake_video)
    monkeypatch.setattr(fal, "as_image_url", lambda ref, **kw: ref)
    monkeypatch.setattr(fal, "_cap_refusal", lambda *a, **kw: None)

    def clip():
        sent.clear()
        fal.generate_for_shot(k["cid"], 1, model="wan3", part=1, db_path=k["pg"],
                              account_id=k["mine"], approved=True)
        return dict(sent)

    a = clip()
    assert a["prompt"].endswith("Avoid: neon, night clubs.")
    assert "BRAND LOOK (Gygler): Warm orange-on-cream" in a["prompt"]
    assert "orange #F7931E (primary)" in a["prompt"]
    assert a["params"]["brand_kit"] == {"id": k["a"]["id"], "hash": k["a"]["hash"]}
    switch(k, k["b"])
    b = clip()
    assert "BRAND LOOK (Northwind): Deep navy" in b["prompt"] and "Gygler" not in b["prompt"]
    switch(k, None)
    plain = clip()
    assert "BRAND LOOK" not in plain["prompt"] and "brand_kit" not in plain["params"]


def test_a_keyframe_carries_the_look_and_its_references_after_the_scenes(kitted, monkeypatch):
    k = kitted
    calls = []

    def fake_nano(prompt, **kw):
        calls.append({"prompt": prompt, "refs": [lbl for lbl, _ in kw.get("reference_image") or []]})
        return {"ok": False, "error": "stop"}

    monkeypatch.setattr(nano_banana, "generate_from_prompt", fake_nano)
    monkeypatch.setattr(imagery, "image_bytes_for_gemini", lambda v, resolve_photo=None: b"x")
    monkeypatch.setattr(shootgen, "beat_moments", lambda p, gemini_client=None: [])
    monkeypatch.setattr(timeline, "ensure", lambda *a, **kw: None)
    scene_chain.keyframe_scene(k["cid"], 1, db_path=k["pg"], account_id=k["mine"],
                               resolve_photo=lambda u: None)
    got = calls[-1]
    assert "BRAND LOOK (Gygler)" in got["prompt"]
    assert got["refs"][-1] == brand_kits.REFERENCE_LABEL
    assert got["refs"][0] != brand_kits.REFERENCE_LABEL      # the scene's photo stays first


def test_a_still_filed_under_the_project_carries_the_look_in_words_only(kitted, monkeypatch):
    k = kitted
    seen = {}

    def fake_request(model, prompt, **kw):
        seen.update(prompt=prompt, refs=list(kw.get("reference_urls") or []))
        raise RuntimeError("stop")

    monkeypatch.setattr(fal, "image_request", fake_request)
    fal.generate_image_from_prompt("A cook.", db_path=k["pg"], account_id=k["mine"],
                                   project_id=k["project"]["id"], approved=True,
                                   reference_urls=["https://cdn.example/r.png"])
    assert "BRAND LOOK (Gygler)" in seen["prompt"]
    assert seen["refs"] == ["https://cdn.example/r.png"]     # no picture to move the price


def test_a_kit_switched_after_the_price_refuses_the_quote(kitted, monkeypatch):
    k = kitted
    monkeypatch.setenv("QUOTE_SIGNING_SECRET", "test-secret")
    shot = preprod.get_concept(k["cid"], dsn=k["pg"], account_id=k["mine"])["shots"][0]
    on_a = pricing.signed_hash(shot, None, account_id=k["mine"], shot_id=k["cid"])
    assert on_a == f"{pricing.content_hash(shot)}+{k['a']['hash']}"
    q = pricing.Quote(pricing_version=pricing.PRICING_VERSION, account_id=k["mine"],
                      shot_id=k["cid"], part=None, provider="fal", model="wan3", seconds=5,
                      frame="720p", provider_usd_micros=100000, credits=24,
                      content_hash=on_a, line_items=())
    token = pricing.sign(q)
    assert pricing.verify(token, account_id=k["mine"], shot=shot, shot_id=k["cid"]).credits == 24
    switch(k, k["b"])
    with pytest.raises(pricing.QuoteRefused) as e:
        pricing.verify(token, account_id=k["mine"], shot=shot, shot_id=k["cid"])
    assert e.value.reason == "stale_content"
    switch(k, None)
    assert pricing.signed_hash(shot, None, account_id=k["mine"],
                               shot_id=k["cid"]) == pricing.content_hash(shot)


# --------------------------------------------------------------------------
# the Cut
# --------------------------------------------------------------------------

def _caption_doc(style):
    doc = d.new_doc()
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": [
        {"id": "c1", "media": "gen:1", "src_in": 0, "src_out": 60, "at": 0, "speed": 1}]},
        {"id": "T1", "kind": "caption", "style": style,
         "cues": [{"id": "q1", "start": 0, "end": 30, "text": "book gygs"}]}]
    doc["duration"] = 60
    return doc


def test_brand_captions_draw_the_kit_and_fall_back_without_one():
    kit = {"id": 1, "account_id": 1, "name": "G", "spec": brand_kits.clean_spec(KIT_A),
           "assets": [{"role": "font_heading", "stored": "/brandkits/x.ttf",
                       "meta": {"family": "Gygler Sans"}}]}
    ass = render.ass_document(_caption_doc("brand"), cut_brand.caption_style(kit))
    style = next(ln for ln in ass.splitlines() if ln.startswith("Style:")).split(",")
    assert style[1] == "Gygler Sans"
    assert style[3] == cut_brand.ass_colour("#F7931E")          # fill = primary
    assert style[15] == "3" and style[18] == "1"                # boxed, lower third
    assert "BOOK GYGS" in ass                                   # uppercase
    # no kit: a brand track draws as the default preset, exactly
    assert render.ass_document(_caption_doc("brand")) == render.ass_document(
        _caption_doc("preset:bold_center"))


def test_the_end_card_is_appended_after_everything_and_crossfades_in():
    doc = _caption_doc("brand")
    out = cut_brand.with_end_card(doc, seconds=2, transition="fade", transition_seconds=0.5)
    card = out["tracks"][0]["clips"][-1]
    assert card["media"] == cut_brand.END_CARD_HANDLE and card["at"] == 60
    assert card["transition_in"] == {"kind": "xfade", "frames": 15, "style": "fade"}
    assert out["duration"] == 60 + 60 - 15
    assert doc["duration"] == 60 and len(doc["tracks"][0]["clips"]) == 1   # untouched
    argv = render.compile_args(out, {"gen:1": "/x/a.mp4", cut_brand.END_CARD_HANDLE: "/x/c.png"},
                               "/x/o.mp4", stills={cut_brand.END_CARD_HANDLE})
    graph = argv[argv.index("-filter_complex") + 1]
    assert "xfade=transition=fade" in graph and "-loop" in argv


def test_the_end_card_png_is_the_canvas_size_on_the_background_colour():
    from PIL import Image
    kit = {"id": 1, "account_id": 1, "name": "Gygler", "spec": brand_kits.clean_spec(KIT_A),
           "assets": []}
    data = cut_brand.end_card_png(kit, (720, 1280), logo=png(300, 100))
    image = Image.open(io.BytesIO(data))
    assert image.size == (720, 1280)
    assert image.getpixel((5, 5)) == (0xFF, 0xF4, 0xE6)        # cream background


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_an_export_with_a_kit_grows_by_the_card(tmp_path):
    clip = tmp_path / "a.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc=s=720x1280:r=30:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast", str(clip)], check=True)
    doc = _caption_doc("brand")
    kit = {"id": 1, "account_id": 1, "name": "Gygler", "spec": brand_kits.clean_spec(KIT_A),
           "assets": []}
    media = {"gen:1": {"frames": 60, "video": True, "audio": False, "width": 720,
                       "height": 1280}}
    got = render.render(doc, account_id=None, name="brand-test", paths={"gen:1": clip},
                        media=media, out_dir=tmp_path, kit=kit)
    assert abs(got["seconds"] - (60 + 60 - 15) / 30) < 0.15
    assert any("brand end card" in n for n in got["notes"])
    off = render.render(doc, account_id=None, name="brand-off", paths={"gen:1": clip},
                        media=media, out_dir=tmp_path, kit=kit, end_card=False)
    assert abs(off["seconds"] - 2.0) < 0.15


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

@pytest.fixture
def as_mine(dbx):
    pg, mine, _ = dbx
    app.dependency_overrides[auth.current_account_id] = lambda: mine
    yield dbx
    app.dependency_overrides[auth.current_account_id] = lambda: None


def test_the_page_round_trip(as_mine, monkeypatch):
    pg, mine, theirs = as_mine
    made = client.post("/api/brand-kits", json={"name": "Gygler", "spec": KIT_A}).json()
    assert "id" in made, made
    kid = made["id"]
    assert client.post("/api/brand-kits", json={"name": "", "spec": {}}).json()[
        "error"]["field"] == "name"
    bad = client.patch(f"/api/brand-kits/{kid}",
                       json={"spec": {"palette": [{"hex": "nope"}]}}).json()
    assert bad["error"]["field"] == "palette"
    up = client.post(f"/api/brand-kits/{kid}/assets", data={"role": "logo_light"},
                     files={"file": ("logo.png", png(), "image/png")}).json()
    file_url = up["kit"]["files"][0]["url"]
    got = client.get(file_url)
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    card = client.get(f"/api/brand-kits/{kid}/end-card.png?aspect=9:16")
    assert card.status_code == 200 and card.content[:4] == b"\x89PNG"
    copy = client.post(f"/api/brand-kits/{kid}/duplicate").json()
    assert copy["name"] == "Gygler copy" and len(copy["files"]) == 1
    listed = client.get("/api/brand-kits").json()["kits"]
    assert {k["id"] for k in listed} == {kid, copy["id"]}

    project = projects.create("Launch", "", pg, account_id=mine)
    picked = client.put(f"/api/projects/{project['id']}/brand-kit",
                        json={"brand_kit_id": kid}).json()
    assert picked["brand_kit"]["name"] == "Gygler"
    assert client.get("/api/brand-kits").json()["kits"][-1]["projects"] in (0, 1)
    cleared = client.put(f"/api/projects/{project['id']}/brand-kit",
                         json={"brand_kit_id": None}).json()
    assert cleared["brand_kit"] is None

    assert client.delete(f"/api/brand-kits/{kid}").json() == {"deleted": kid}
    assert client.get(f"/api/brand-kits/{kid}").status_code == 404
    assert client.post(f"/api/brand-kits/{kid}/restore").json()["id"] == kid

    # another account sees none of it and cannot pick it
    app.dependency_overrides[auth.current_account_id] = lambda: theirs
    assert client.get(f"/api/brand-kits/{kid}").status_code == 404
    assert client.get(file_url).status_code == 404
    theirs_project = projects.create("T", "", pg, account_id=theirs)
    assert client.put(f"/api/projects/{theirs_project['id']}/brand-kit",
                      json={"brand_kit_id": kid}).status_code == 404


def test_the_prompt_preview_shows_the_kit_without_spending(kitted, monkeypatch):
    k = kitted
    app.dependency_overrides[auth.current_account_id] = lambda: k["mine"]
    try:
        got = client.get(f"/api/scenes/{k['cid']}/prompt-preview").json()
        assert "brand_kit" in got, got
    finally:
        app.dependency_overrides[auth.current_account_id] = lambda: None
    assert got["brand_kit"]["name"] == "Gygler" and got["kit_references"] == 1
    whole = got["clips"][0]
    assert whole["part"] is None and "BRAND LOOK" not in whole["prompt"]
    assert whole["branded"].endswith("Avoid: neon, night clubs.")
    assert "Friendly, brisk, confident." in got["writer_block"]
