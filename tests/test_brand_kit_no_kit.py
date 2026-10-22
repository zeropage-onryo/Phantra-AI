"""A project with NO brand kit behaves exactly as before brand kits existed
(docs/tasks/task-brand-kit.md §8).

The goldens in tests/goldens/no_brand_kit.json were captured on main BEFORE
any brand-kit code landed (the branch's first commit), from the functions
every generator -- the studio's and the connector's -- goes through: the two
scene writers' prompts, the project block, the brain's instructions, the
render target, a keyframe's prompt and references, a clip's and a still's
provider arguments, the quote's content hash, and the Cut's ffmpeg argv and
caption file. A brand kit is opt-in; with none set, every one of these must
come out byte for byte the same.

A deliberate change to one of those prompts (a new line in a template, a
new caption preset) changes its golden for every project, kit or not; re-run
with PHANTRA_UPDATE_GOLDENS=1 and review the diff of the json file. A change
that only appears here and in no template is the bug this file exists for.
"""
import json
import os
from pathlib import Path

import pytest

from src import (
    creative_guide,
    fal,
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
from src.cut import assemble, ops, render
from src.cut import doc as d

GOLDENS = Path(__file__).parent / "goldens" / "no_brand_kit.json"
UPDATE = os.environ.get("PHANTRA_UPDATE_GOLDENS") == "1"

PROJECT = {"id": 7, "title": "Golden Project", "brief": "Short ads for a hiring app.",
           "look": "Warm tungsten practicals, 35mm, soft grain.",
           "memory": [{"kind": "pick", "text": "kept the kitchen take", "at": "t"},
                      {"kind": "pass", "text": "too dark", "at": "t"}]}

SCENE = ("(0-3s) A line cook in a white apron flips a pan; steam rolls up. "
         "(3-6s) She glances at a phone on the rail and smiles.\n"
         "Sound: pan sizzle, kitchen chatter. No background music.\n"
         "AVOID: no plastic skin, no text on screen.")
TIMELINE = {"seconds": 6, "planner": "split", "source": "x",
            "continuity": "Busy kitchen, warm practicals. AVOID: no plastic skin.",
            "parts": [{"n": 1, "start": 0, "end": 3, "seconds": 3, "text": "t1",
                       "prompt": "A line cook flips a pan; steam rolls up.",
                       "refs": ["/refs/a.jpg"], "reference_image": "https://cdn.example/k1.png"},
                      {"n": 2, "start": 3, "end": 6, "seconds": 3, "text": "t2",
                       "prompt": "She glances at the phone and smiles.",
                       "refs": ["/refs/a.jpg"], "reference_image": None}]}
SHOT = {"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
        "prompt": SCENE, "refs": ["/refs/a.jpg", "/refs/b.jpg"],
        "reference_image": "https://cdn.example/k0.png", "seconds": 6}

FAKE = {"gen:1": {"frames": 120, "video": True, "audio": True, "width": 720, "height": 1280},
        "gen:2": {"frames": 150, "video": True, "audio": True, "width": 641, "height": 361},
        "gen:3": {"frames": 90, "video": True, "audio": False, "width": 720, "height": 1280},
        "asset:5": {"frames": 900, "video": False, "audio": True},
        "asset:6": {"frames": 180, "video": False, "audio": True}}
CLIPS = [{"handle": "gen:1", "label": "p1"}, {"handle": "gen:2", "label": "p2"},
         {"handle": "gen:3", "label": "p3"}]


@pytest.fixture(scope="module")
def goldens():
    return json.loads(GOLDENS.read_text()) if GOLDENS.exists() else {}


def check(goldens, name, value):
    """`value` must equal the golden captured before brand kits existed."""
    text = value if isinstance(value, str) else json.dumps(value, indent=1, sort_keys=True)
    if UPDATE:
        stored = json.loads(GOLDENS.read_text()) if GOLDENS.exists() else {}
        stored[name] = text
        GOLDENS.parent.mkdir(parents=True, exist_ok=True)
        GOLDENS.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n")
        return
    assert name in goldens, f"no golden for {name}: run with PHANTRA_UPDATE_GOLDENS=1"
    assert text == goldens[name], f"{name} changed with no brand kit set"


@pytest.fixture
def fixed_writer(monkeypatch):
    # the exemplar is a file other sessions edit; the slot is what is under test
    monkeypatch.setattr(shootgen, "gold_standard_example", lambda: "(the exemplar)")
    monkeypatch.delenv("PHANTRA_MOTION_DIRECTIVE", raising=False)


# --------------------------------------------------------------------------
# writing: the two scene writers, the project block, the brain
# --------------------------------------------------------------------------

@pytest.mark.parametrize("inside", [True, False], ids=["in-project", "no-project"])
def test_scene_writer_prompts(goldens, fixed_writer, inside):
    with project_context.active(PROJECT if inside else None):
        brief = shootgen.build_scene_brief_prompt(
            spark="a cook finds the shift she wanted", references="REFS", cast="CAST",
            seconds=6)
        many = shootgen.build_scenes_prompt("a cook finds a shift", 3, [],
                                            references="REFS", cast="CAST", seconds=6)
        block = shootgen.project_brief()
    check(goldens, f"scene_brief_prompt/{inside}", brief)
    check(goldens, f"scenes_prompt/{inside}", many)
    check(goldens, f"project_brief/{inside}", block)


def test_project_block_and_brain(goldens, fixed_writer):
    check(goldens, "brief_block", projects.brief_block(PROJECT))
    with project_context.active(PROJECT):
        text = creative_guide.instructions(with_tools=True, maker=True)
    # the instructions end with the project block; the templates above it
    # are Vesper's and change on their own schedule
    check(goldens, "guide_project_tail", text[text.rindex("\n\nProject:\n"):])


# --------------------------------------------------------------------------
# rendering: the render target, the quote's hash
# --------------------------------------------------------------------------

def test_render_target_and_content_hash(goldens, fixed_writer):
    shot = {**SHOT, "timeline": TIMELINE}
    check(goldens, "render_target/scene", timeline.render_target(shot))
    check(goldens, "render_target/part1", timeline.render_target(shot, 1))
    check(goldens, "render_target/part2", timeline.render_target(shot, 2))
    check(goldens, "content_hash", pricing.content_hash(shot))


# --------------------------------------------------------------------------
# the providers' arguments, through a project that has no kit
# --------------------------------------------------------------------------

@pytest.fixture
def scene_in_project(pg, monkeypatch, fixed_writer):
    from src import accounts, db, entities, generative
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    generative.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    account = accounts.upsert_account("nk-mine", "Mine", "#fff", dsn=pg)
    project = projects.create("Golden", "brief", pg, account_id=account, look="warm")
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{**SHOT, "timeline": TIMELINE}]}, dsn=pg, account_id=account)
    with db.connect(pg) as conn:
        conn.execute("UPDATE shoot_concepts SET project_id = %s WHERE id = %s "
                     "AND account_id = %s", (project["id"], cid, account))
    return pg, account, project["id"], cid


def test_clip_arguments(goldens, scene_in_project, monkeypatch):
    pg, account, _pid, cid = scene_in_project
    sent = {}

    def fake_video(prompt, out_path, **kw):
        sent.update(prompt=prompt, negative=kw.get("negative_prompt"),
                    image=kw.get("image_url"), model=kw.get("model"))
        raise RuntimeError("stop: the provider is not the subject")

    monkeypatch.setattr(fal, "generate_video", fake_video)
    monkeypatch.setattr(fal, "as_image_url", lambda ref, **k: ref)
    monkeypatch.setattr(fal, "_cap_refusal", lambda *a, **k: None)
    for part in (None, 1, 2):
        sent.clear()
        fal.generate_for_shot(cid, 1, model="wan3", part=part, db_path=pg,
                              account_id=account, approved=True)
        check(goldens, f"clip/{part}", dict(sent))


def test_keyframe_arguments(goldens, scene_in_project, monkeypatch):
    pg, account, _pid, cid = scene_in_project
    calls = []

    def fake_nano(prompt, **kw):
        refs = kw.get("reference_image") or []
        calls.append({"prompt": prompt, "beat": kw.get("beat"),
                      "refs": [label for label, _data in refs]})
        return {"ok": False, "error": "stop"}

    monkeypatch.setattr(nano_banana, "generate_from_prompt", fake_nano)
    monkeypatch.setattr(imagery, "image_bytes_for_gemini", lambda v, resolve_photo=None, account_id=None: b"x")
    monkeypatch.setattr(shootgen, "beat_moments", lambda p, gemini_client=None: [])
    # the whole-scene keyframe (no timeline), then the timed strip
    monkeypatch.setattr(timeline, "ensure", lambda *a, **k: None)
    scene_chain.keyframe_scene(cid, 1, db_path=pg, account_id=account,
                               resolve_photo=lambda u: None)
    scene_chain._keyframe_timeline(cid, 1, TIMELINE, db_path=pg,
                                   resolve_photo=lambda u: None, account_id=account,
                                   roles={})
    check(goldens, "keyframes", calls)


def test_still_arguments(goldens, scene_in_project, monkeypatch):
    pg, account, pid, cid = scene_in_project
    seen = {}

    def fake_request(model, prompt, **kw):
        seen.update(model=model, prompt=prompt, refs=list(kw.get("reference_urls") or []))
        raise RuntimeError("stop: the provider is not the subject")

    monkeypatch.setattr(fal, "image_request", fake_request)
    fal.generate_image_from_prompt("A cook at the pass, warm light.", db_path=pg,
                                   account_id=account, project_id=pid, concept_id=cid,
                                   reference_urls=["https://cdn.example/r.png"],
                                   approved=True)
    check(goldens, "still", dict(seen))


# --------------------------------------------------------------------------
# the Cut: the export's argv and its caption file
# --------------------------------------------------------------------------

def _caption_doc():
    doc = d.new_doc()
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": [
        {"id": "c1", "media": "gen:1", "src_in": 0, "src_out": 90, "at": 0, "speed": 1}]}]
    doc["duration"] = 90
    # the three presets that existed before brand kits, named here so a
    # later style cannot change what this golden pins
    for i, style in enumerate(("preset:bold_center", "preset:lower_third",
                               "preset:minimal_top"), start=1):
        doc["tracks"].append({"id": f"T{i}", "kind": "caption", "style": style,
                              "cues": [{"id": f"q{i}", "start": 10 * i, "end": 10 * i + 20,
                                        "text": f"line {i}"}]})
    return doc


def test_cut_export(goldens):
    doc, notes = assemble.build_doc(CLIPS, FAKE, music="asset:5", voice="asset:6",
                                    captions=[{"start": 0, "end": 2, "text": "hi"}])
    doc = ops.add_transition(doc, d.track(doc, "V1")["clips"][1]["id"], 8)
    check(goldens, "cut/assembled_doc", {"doc": doc, "notes": notes})
    paths = {h: f"/x/{h.replace(':', '_')}" for h in d.handles(doc)}
    check(goldens, "cut/argv_assembled",
          render.compile_args(doc, paths, "/x/out.mp4", burn="captions.ass"))
    check(goldens, "cut/ass_assembled", render.ass_document(doc))

    caps = _caption_doc()
    check(goldens, "cut/ass_three_styles", render.ass_document(caps))
    check(goldens, "cut/argv_three_styles",
          render.compile_args(caps, {"gen:1": "/x/a.mp4"}, "/x/o.mp4", burn="c.ass"))

    still = d.new_doc()
    still["tracks"] = [{"id": "V1", "kind": "video", "clips": [
        {"id": "c1", "media": "asset:9", "src_in": 0, "src_out": 60, "at": 0, "speed": 1}]}]
    still["duration"] = 60
    check(goldens, "cut/argv_still",
          render.compile_args(still, {"asset:9": "/x/card.png"}, "/x/o.mp4",
                              stills={"asset:9"}))
