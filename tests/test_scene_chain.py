"""The stages a scene goes through, and which caller runs which.

`src/scene_chain.py` holds one implementation of each stage. Pressing
Create runs ground -> write -> attach and STOPS on the concepts board;
the Director canvas and the nightly graph do the rest. The split matters
because the alternative is three copies of "render a keyframe" drifting
apart, which is how this project lost its references once already.

Every model seam is patched BY NAME and asserted called. A missed patch
here does not merely fail: the job runs in a daemon thread that can
outlive the test, monkeypatch tears the socket guard down with it, and a
real billed call escapes -- which is the exact failure conftest.py
exists for.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src import imagery, nano_banana, preprod, scene_chain, shootgen

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    from app import auth
    stub = {"id": 1, "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)
    monkeypatch.setattr(
        auth, "current_account",
        lambda request, user=None: {"slug": "phantra", "display_name": "Phantra AI"})


@pytest.fixture
def tmp_db(pg, monkeypatch):
    from src import entities, generative
    path = pg
    preprod.init(path)
    entities.init(path)
    generative.init(path)
    monkeypatch.setenv("DATABASE_URL", path)
    return path


@pytest.fixture
def seams(monkeypatch):
    """Everything that would cost money or touch the network, replaced
    and counted."""
    calls = {"write": 0, "enhance": [], "nano": [], "ground": 0}

    def fake_model(client_, model, contents, **_):
        calls["write"] += 1
        return json.dumps({"scenes": [
            {"title": "Cold Open", "location": "", "prompt": "P1"},
            {"title": "The Door", "location": "", "prompt": "P2"},
        ]})

    def fake_ground(spark=None, client=None, db_path=None, **kw):
        calls["ground"] += 1
        return "THE SHELF"

    def fake_enhance(system, user, images=None, **kw):
        calls["enhance"].append(user)
        return f"ENHANCED[{user}]"

    def fake_nano(prompt, *, reference_image=None, db_path=None, concept_id=None,
                  beat="", **kw):
        calls["nano"].append({"prompt": prompt, "refs": list(reference_image or []),
                              "concept_id": concept_id, "beat": beat})
        return {"ok": True, "media_url": f"https://cdn/key-{concept_id}.png",
                "generation_id": 1, "path": "x", "error": None}

    monkeypatch.setattr(shootgen, "generate_with_retry", fake_model)
    monkeypatch.setattr(shootgen, "reference_block", fake_ground)
    monkeypatch.setattr(imagery, "enhance", fake_enhance)
    monkeypatch.setattr(nano_banana, "generate_from_prompt", fake_nano)
    # The beat splitter is a billed call too, and it runs on the way into
    # every keyframe. [] is "this shot holds one moment", so an unpatched
    # test keeps exactly the single-still behaviour it was written against.
    monkeypatch.setattr(shootgen, "beat_moments", lambda prompt, **kw: [])
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    return calls


def wait_for_job(job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never finished")


def create(count="2"):
    res = client.post("/api/scenes/run",
                      data={"idea": "gearing up ritual", "count": count})
    assert res.status_code == 200, res.text
    return wait_for_job(res.json()["job_id"])


# --- Create stops at the concepts board -------------------------------------

def test_create_writes_concepts_and_stops(tmp_db, seams):
    """Mike's call, 2026-08-29: pressing Create is for reading concepts,
    not for a minute of billed work nobody asked for. The enhance and
    the keyframe belong to the Director canvas when a person is driving,
    and to the nightly graph when nobody is."""
    job = create()
    assert job["status"] == "done", job.get("error")

    concepts = preprod.list_concepts(dsn=tmp_db, account_id=None)
    # One Create, one scene (2026-09-10): the seam's model answers with
    # two takes and the form still posts count=2, and ONE is saved.
    assert len(concepts) == 1
    assert seams["write"] == 1
    assert seams["enhance"] == []       # nothing enhanced
    assert seams["nano"] == []          # nothing rendered, nothing spent

    for c in concepts:
        assert c["shots"][0]["prompt"] in ("P1", "P2")
        assert "written_prompt" not in c["shots"][0]
        assert c["parked"] is False
        assert c["picked"] is False
    # unparked and unpicked: NOT waiting on a spend decision
    assert client.get("/api/queue/pending").json()["items"] == []


def test_no_scene_at_all_is_a_failed_run_not_a_silent_one(tmp_db, seams, monkeypatch):
    monkeypatch.setattr(shootgen, "generate_with_retry",
                        lambda c, m, contents, **_: json.dumps({"scenes": []}))
    job = create()
    assert job["status"] == "failed"
    assert "no usable scene" in (job["error"] or "")
    assert preprod.list_concepts(dsn=tmp_db, account_id=None) == []


# --- the stages the other two callers use -----------------------------------

SEED_REF = "/refs/seed.jpg"


def a_scene(path, prompt="a rider suits up", refs=None):
    # The default carries ONE reference on purpose (2026-09-08): the
    # board and the Queue now refuse a scene with no photographs behind
    # it, and these tests are about parking, picking and rendering --
    # not about grounding. `refs=[]` still builds an ungrounded one, so
    # the gate itself stays testable; that is why this is a sentinel
    # check and not `refs or [SEED]`.
    return preprod.save_concept(
        {"title": "Cold Open", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
                    "desc": "x", "prompt": prompt,
                    "refs": [SEED_REF] if refs is None else list(refs)}]},
             prompt_template="T", dsn=path, account_id=None)


def test_persist_prompt_keeps_the_generators_own_words(tmp_db):
    """Whatever polished the prompt, the row has to end up holding it --
    or Runway renders the draft while the good version lives in a job
    payload. The model's original stays as written_prompt: the grade
    queue teaches on what the MODEL wrote, and the Director canvas seeds
    from it so pressing Run doesn't enhance an already-enhanced prompt.
    """
    scene_id = a_scene(tmp_db, prompt="the draft")
    assert scene_chain.persist_prompt(scene_id, 1, "the polished version",
                                      db_path=tmp_db) is True
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["prompt"] == "the polished version"
    assert shot["written_prompt"] == "the draft"

    # polishing twice must not lose the original under the first polish
    scene_chain.persist_prompt(scene_id, 1, "polished again", db_path=tmp_db)
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["prompt"] == "polished again"
    assert shot["written_prompt"] == "the draft"

    # nothing to store is not an error, and does not touch the row
    assert scene_chain.persist_prompt(scene_id, 1, "  ", db_path=tmp_db) is False
    assert scene_chain.persist_prompt(scene_id, 1, "polished again",
                                      db_path=tmp_db) is False
    assert scene_chain.persist_prompt(9999, 1, "x", db_path=tmp_db) is False


def test_keyframe_attaches_the_still_and_names_every_reference(tmp_db, seams,
                                                               monkeypatch):
    """The still is what the clip anchors on, so this is the frame the
    whole spend hangs off. References go in NAMED: four references are
    four named things the model can bind to the prompt's words, not four
    pictures it has to sort out."""
    photo = "/characters/michael/photo/a.jpg"
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8jacket")
    scene_id = a_scene(tmp_db, refs=[photo])

    result = scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)
    assert result["ok"]
    assert seams["nano"][0]["refs"] == [(shootgen.reference_label(photo),
                                         b"\xff\xd8jacket")]
    assert seams["nano"][0]["concept_id"] == scene_id     # names its own file
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["reference_image"] == f"https://cdn/key-{scene_id}.png"


def test_the_keyframe_prompt_names_only_references_that_resolved(
        tmp_db, seams, monkeypatch):
    """The prompt the keyframe renders from has to agree with the
    captions the images carry.

    The scene writers invent "@Image 1 / @Image 2" -- a syntax nothing
    here emits and no renderer receives -- so the sentence naming the
    face pointed at nothing while the jacket bound anyway off its own
    name. And a HEIC Pillow could not decode is dropped before the call,
    so naming it would promise a picture that never rode along.
    """
    monkeypatch.setattr(
        imagery, "image_bytes_for_gemini",
        lambda url, resolve_photo=None, account_id=None: (b"\xff\xd8ok"
                                         if url.lower().endswith(".jpg") else None))
    scene_id = a_scene(
        tmp_db,
        prompt=("REFERENCES: Use @Image 1 for Michael's face.\n\n"
                "ACTION: he waits by the @Image 2 bike."),
        refs=["/characters/michael/photo/a.jpg",
              "/props/motorcycle/photo/b.heic"])

    assert scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)["ok"]
    prompt = seams["nano"][0]["prompt"]
    assert "@Image" not in prompt
    assert '"Michael"' in prompt
    assert "Motorcycle" not in prompt          # dropped, so never promised
    assert len(seams["nano"][0]["refs"]) == 1  # and never sent either
    # the stored shot keeps the writer's text; only the render is rebound
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert "@Image 1" in shot["prompt"]


def test_a_failed_keyframe_is_a_result_not_an_exception(tmp_db, monkeypatch):
    monkeypatch.setattr(nano_banana, "generate_from_prompt",
                        lambda prompt, **kw: {"ok": False, "media_url": None,
                                              "error": "daily cap: 20/20 images"})
    scene_id = a_scene(tmp_db)
    result = scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)
    assert result["ok"] is False and "daily cap" in result["error"]
    assert "reference_image" not in preprod.get_concept(scene_id,
                                                        dsn=tmp_db, account_id=None)["shots"][0]
    # a scene with no prompt has nothing to render, and says so
    empty = preprod.save_concept(
        {"title": "Empty", "shots": [{"n": 1, "source": "AI", "tool": "RUNWAY"}]}, dsn=tmp_db, account_id=None)
    assert "no prompt" in scene_chain.keyframe_scene(empty, 1,
                                                     db_path=tmp_db)["error"]


def test_parking_is_what_puts_a_scene_in_the_queue(tmp_db):
    """Only the automation parks. A scene made by hand reaches the Queue
    by being picked -- and a scene that merely HAS a keyframe (the
    Director canvas attaches one mid-work) is not waiting on anybody."""
    parked = a_scene(tmp_db)
    scene_chain.park_scene(parked, "keyframe rendered", db_path=tmp_db)

    mid_work = a_scene(tmp_db)
    preprod.set_shot_reference_image(mid_work, 1, "https://cdn/other.png",
                                     dsn=tmp_db, account_id=None)

    items = client.get("/api/queue/pending").json()["items"]
    assert [c["id"] for c in items] == [parked]
    assert items[0]["park_reason"] == "keyframe rendered"
    assert items[0]["picked"] is False        # approving is what picks it


# --- the shape of the module itself -----------------------------------------

def test_the_stages_stay_callable_from_a_graph_and_from_a_request():
    """A guard on a decision (2026-08-29). These are plain functions so
    the request path can call them directly and src/orchestrator.py's
    StateGraph can call them from its nodes. If scene_chain ever grows
    its own graph, that is a real architectural change -- make it
    deliberately, and delete this test."""
    import pathlib
    source = pathlib.Path(scene_chain.__file__).read_text()
    assert "import langgraph" not in source
    assert "StateGraph(" not in source      # the prose names it; the code must not
    # and src/ never imports app/: the app-layer capabilities are injected
    assert "from app" not in source and "import app" not in source
    assert "attach_refs" in source and "resolve_photo" in source


# --- separate images, not one combined one (Mike, 2026-09-02) --------------
#
# A shot prompt describes a MOVE and the move stays -- it is how the shot is
# directed and the generator reads it. But one call asking for one picture of
# the whole move returns one picture OF the whole move: concept 167 came back
# with the hallway, the phone, and a head floating across the top third. So
# each moment of the move gets its own call and its own image.

def test_each_beat_is_its_own_image(tmp_db, seams, monkeypatch):
    monkeypatch.setattr(
        shootgen, "beat_moments",
        lambda prompt, **kw: ["the hand holding the phone, screen lit",
                              "the face the tilt lands on"])
    scene_id = a_scene(tmp_db)

    result = scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)

    assert result["ok"]
    assert len(seams["nano"]) == 2                  # two calls, two images
    assert [c["beat"] for c in seams["nano"]] == [
        "the hand holding the phone, screen lit", "the face the tilt lands on"]
    assert len(result["frames"]) == 2
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert len(shot["frames"]) == 2
    # the FIRST beat is the anchor Runway builds the clip from
    assert shot["reference_image"] == result["frames"][0]["url"]


def test_the_move_stays_in_every_beats_prompt(tmp_db, seams, monkeypatch):
    """The beat pins the FRAME. It does not edit the shot -- each call
    still carries the full prompt, camera move included, because that is
    what carries the grade, the lens and the texture."""
    monkeypatch.setattr(shootgen, "beat_moments",
                        lambda prompt, **kw: ["the hand", "the face"])
    scene_id = a_scene(tmp_db, prompt="Tilt up from the hand to his face. Handheld.")

    scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)

    for call in seams["nano"]:
        assert "Tilt up from the hand to his face. Handheld." == call["prompt"]


def test_one_moment_renders_one_still_exactly_as_before(tmp_db, seams,
                                                        monkeypatch):
    """[] from the splitter means "this shot holds one moment" -- and a
    single-moment shot must cost exactly one call, the way it always did."""
    monkeypatch.setattr(shootgen, "beat_moments", lambda prompt, **kw: [])
    scene_id = a_scene(tmp_db)

    result = scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)

    assert result["ok"] and len(seams["nano"]) == 1
    assert seams["nano"][0]["beat"] == ""
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert "frames" not in shot        # no strip, nothing to scroll


def test_the_cap_stops_the_strip_and_keeps_what_rendered(tmp_db, monkeypatch):
    """Beat two hitting NANO_DAILY_CAP must not throw away beat one, and
    must not keep spending against a wall we already hit."""
    calls = []

    def capped(prompt, *, beat="", concept_id=None, **kw):
        calls.append(beat)
        if len(calls) == 1:
            return {"ok": True, "media_url": "https://cdn/beat1.png",
                    "generation_id": 1, "path": "x", "error": None}
        return {"ok": False, "media_url": None, "error": "daily cap: 20/20 images"}

    monkeypatch.setattr(nano_banana, "generate_from_prompt", capped)
    monkeypatch.setattr(shootgen, "beat_moments",
                        lambda prompt, **kw: ["a", "b", "c"])
    scene_id = a_scene(tmp_db)

    result = scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)

    assert result["ok"] is True
    assert len(result["frames"]) == 1
    assert len(calls) == 2                    # stopped, did not try "c"
    assert "daily cap" in result["error"]     # and says why the strip is short
    shot = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["reference_image"] == "https://cdn/beat1.png"


def test_a_sibling_shot_is_not_erased_by_the_strip(tmp_db, seams, monkeypatch):
    """update_concept_shots replaces shots_json wholesale, so writing the
    strip back as [shot] would delete every other shot on the concept."""
    monkeypatch.setattr(shootgen, "beat_moments",
                        lambda prompt, **kw: ["a", "b"])
    scene_id = preprod.save_concept(
        {"title": "Two Shots", "shots": [
            {"n": 1, "source": "AI", "tool": "RUNWAY", "prompt": "one"},
            {"n": 2, "source": "AI", "tool": "RUNWAY", "prompt": "two"}]}, dsn=tmp_db, account_id=None)

    scene_chain.keyframe_scene(scene_id, 1, db_path=tmp_db)

    shots = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["shots"]
    assert [s["n"] for s in shots] == [1, 2]
    assert shots[1]["prompt"] == "two"



# --- ground() / scoped_cast_and_locations() ---------------------------------
# 2026-09-03, Mike's call: a Create run should ground only on what the
# idea names or what was explicitly picked -- never the whole asset
# bank by default, which is what cast_for's unfiltered
# entities.list_characters/list_props always did before this.

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
    b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def cast_photo_dirs(tmp_path, monkeypatch):
    from src import asset_shelf
    dirs = {}
    for kind in ("location", "character", "prop"):
        d = tmp_path / ("ground-" + kind + "s")
        d.mkdir()
        dirs[kind] = d
    monkeypatch.setattr(asset_shelf, "PHOTO_DIRS", dirs)
    return dirs


def _with_photo(dirs, kind, slug):
    d = dirs[kind] / slug
    d.mkdir(parents=True)
    (d / "a.png").write_bytes(TINY_PNG)


def test_ground_only_offers_a_character_the_idea_names(tmp_db, cast_photo_dirs, monkeypatch):
    from src import entities
    entities.add_character("Mike", role="protagonist", dsn=tmp_db, account_id=None)
    entities.add_character("Guest", role="bartender", dsn=tmp_db, account_id=None)
    _with_photo(cast_photo_dirs, "character", "mike")
    _with_photo(cast_photo_dirs, "character", "guest")
    monkeypatch.setattr(shootgen, "reference_block", lambda **kw: "")

    grounded = scene_chain.ground("Mike gears up for the ride",
                                  db_path=tmp_db, account_id=None)

    assert "Mike" in grounded["cast"]
    assert "Guest" not in grounded["cast"]


def test_ground_offers_nothing_when_nothing_is_named_or_picked(tmp_db, cast_photo_dirs, monkeypatch):
    from src import entities
    entities.add_character("Mike", role="protagonist", dsn=tmp_db, account_id=None)
    _with_photo(cast_photo_dirs, "character", "mike")
    monkeypatch.setattr(shootgen, "reference_block", lambda **kw: "")

    grounded = scene_chain.ground("a ritual at dusk",
                                  db_path=tmp_db, account_id=None)

    assert "Mike" not in grounded["cast"]


def test_ground_honours_an_explicit_pick(tmp_db, cast_photo_dirs, monkeypatch):
    from src import entities
    entities.add_character("Mike", role="protagonist", dsn=tmp_db, account_id=None)
    _with_photo(cast_photo_dirs, "character", "mike")
    monkeypatch.setattr(shootgen, "reference_block", lambda **kw: "")

    grounded = scene_chain.ground("a ritual at dusk",
                                  db_path=tmp_db, account_id=None,
                                  refs=["/characters/mike/photo/a.png"])

    assert "Mike" in grounded["cast"]


# --- the cue cards' per-shot approve (2026-10-04) ----------------------------

def _timed(path, parts=3, drawn=()):
    """A one-shot scene whose CURRENT timeline has `parts` shots; the
    parts numbered in `drawn` already carry a still."""
    from src import timeline
    shot = {"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX",
            "prompt": "(0-3s) a. (3-6s) b. (6-9s) c.", "refs": [SEED_REF]}
    shot["timeline"] = {
        "seconds": 9, "planner": "split", "continuity": "",
        "source": timeline.source_hash(shot["prompt"], shot["refs"]),
        "parts": [{"n": i + 1, "start": 3 * i, "end": 3 * i + 3, "seconds": 3,
                   "text": f"shot {i + 1}", "prompt": f"shot {i + 1}", "refs": [SEED_REF],
                   **({"reference_image": f"https://cdn/had-{i + 1}.png"}
                      if i + 1 in drawn else {})}
                  for i in range(parts)]}
    return preprod.save_concept({"title": "T", "hook": "", "logline": "", "shots": [shot]}, prompt_template="T",
                                dsn=path,
                                account_id=None)


def _parts(path, cid):
    return preprod.get_concept(cid, dsn=path, account_id=None)["shots"][0]["timeline"]["parts"]


def test_a_part_draws_one_shot_and_leaves_the_rest(tmp_db, seams, monkeypatch):
    """Shot 2 approved from its card: one still, on part 2 only, and the
    scene's own frame (shot 1's) is NOT set from a mid-scene still."""
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8ok")
    cid = _timed(tmp_db)
    assert scene_chain.pick_skip_reason(
        preprod.get_concept(cid, dsn=tmp_db, account_id=None), part=2) is None
    assert scene_chain.stills_to_draw(
        preprod.get_concept(cid, dsn=tmp_db, account_id=None), part=2) == 1

    result = scene_chain.keyframe_scene(cid, 1, db_path=tmp_db, part=2)
    assert result["ok"], result
    assert len(seams["nano"]) == 1
    assert "SHOT 2 OF 3" in seams["nano"][0]["prompt"]
    parts = _parts(tmp_db, cid)
    assert [bool(p.get("reference_image")) for p in parts] == [False, True, False]
    shot = preprod.get_concept(cid, dsn=tmp_db, account_id=None)["shots"][0]
    assert not shot.get("reference_image")        # shot 1 is still the card's frame

    # the quote now prices the two still missing, and part 2 is a skip
    concept = preprod.get_concept(cid, dsn=tmp_db, account_id=None)
    assert scene_chain.stills_to_draw(concept) == 2
    assert scene_chain.pick_skip_reason(concept, part=2) == "already has a still"
    assert scene_chain.pick_skip_reason(concept, part=9) == "no shot 9"

    # shot 1 next: drawn alone, and it IS the scene's frame
    assert scene_chain.keyframe_scene(cid, 1, db_path=tmp_db, part=1)["ok"]
    assert len(seams["nano"]) == 2
    shot = preprod.get_concept(cid, dsn=tmp_db, account_id=None)["shots"][0]
    assert shot["reference_image"] == f"https://cdn/key-{cid}.png"
    assert [bool(p.get("reference_image")) for p in _parts(tmp_db, cid)] == [True, True, False]


def test_a_part_rides_the_previous_still_only_when_that_shot_has_one(
        tmp_db, seams, monkeypatch):
    """Continuity is the previous shot's still, labelled; with shot 1 undrawn,
    shot 2 is drawn with its refs alone rather than with a blank."""
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8ok")
    cid = _timed(tmp_db)
    scene_chain.keyframe_scene(cid, 1, db_path=tmp_db, part=2)
    assert [label for label, _ in seams["nano"][0]["refs"]] == [shootgen.reference_label(SEED_REF)]
    cid2 = _timed(tmp_db, drawn=(1,))
    scene_chain.keyframe_scene(cid2, 1, db_path=tmp_db, part=2)
    assert scene_chain.CONTINUITY_REF_LABEL in [label for label, _ in seams["nano"][1]["refs"]]


def test_a_part_on_a_scene_that_renders_whole_is_a_skip(tmp_db, seams):
    concept = preprod.get_concept(a_scene(tmp_db), dsn=tmp_db, account_id=None)
    assert scene_chain.pick_skip_reason(concept, part=1) == "not a timed scene"
    assert scene_chain.keyframe_quote(concept, part=1) is None
    assert scene_chain.keyframe_quote(concept) is not None


# --- a signed quote for the stills, and the draw it caps (2026-10-11) --------
# The chat connector's `approve` drew a scene's keyframes on the scene id
# alone; it takes the quote's token now. These are the two halves in src/:
# what the token binds, and that a draw approved with one cannot outrun it.

QUOTE_SECRET = "dGVzdC1zZWNyZXQtdGhpcnR5LXR3by1ieXRlcy1sb25nLW9r"


def _concept(path, cid):
    return preprod.get_concept(cid, dsn=path, account_id=None)


def test_shots_to_draw_names_the_shots_the_quote_prices(tmp_db):
    """The list a token binds is the count the card prints, shot by shot:
    one rule, so the two can never disagree about a strip."""
    concept = _concept(tmp_db, _timed(tmp_db, drawn=(2,)))
    assert scene_chain.shots_to_draw(concept) == [1, 3]
    assert scene_chain.stills_to_draw(concept) == 2
    assert scene_chain.shots_to_draw(concept, part=3) == [3]
    assert scene_chain.shots_to_draw(concept, part=2) == []        # already drawn
    whole = _concept(tmp_db, a_scene(tmp_db))
    # a scene that renders whole is drawn as up to a still per moment of its
    # move, and they belong to no shot
    assert scene_chain.shots_to_draw(whole) == []
    assert scene_chain.stills_to_draw(whole) == shootgen.BEATS_PER_SHOT
    done = _concept(tmp_db, _timed(tmp_db, drawn=(1, 2, 3)))
    assert scene_chain.shots_to_draw(done) == [] and scene_chain.stills_to_draw(done) == 0


def test_no_keyframe_token_without_a_secret_or_a_still_to_draw(tmp_db, monkeypatch):
    from src import pricing
    concept = _concept(tmp_db, _timed(tmp_db))
    monkeypatch.delenv(pricing.SIGNING_ENV, raising=False)
    assert scene_chain.keyframe_token(concept, None) is None
    monkeypatch.setenv(pricing.SIGNING_ENV, QUOTE_SECRET)
    assert scene_chain.keyframe_token(concept, None).startswith("phq.")
    done = _concept(tmp_db, _timed(tmp_db, drawn=(1, 2, 3)))
    assert scene_chain.keyframe_token(done, None) is None


def test_a_keyframe_token_stops_working_when_the_strip_or_the_scene_moves(
        tmp_db, monkeypatch):
    """Minted and checked off the SAME reading of the scene: draw one of
    its stills, or edit its prompt, and the old price is stale."""
    from src import pricing, timeline
    monkeypatch.setenv(pricing.SIGNING_ENV, QUOTE_SECRET)
    cid = _timed(tmp_db)
    token = scene_chain.keyframe_token(_concept(tmp_db, cid), None)
    q = scene_chain.verify_keyframe_token(token, _concept(tmp_db, cid), None)
    assert (q.shot_id, q.shots, q.stills) == (cid, (1, 2, 3), 3)
    assert q.credits == scene_chain.keyframe_quote(_concept(tmp_db, cid))["credits"]
    # another scene's token is not this scene's
    other = _timed(tmp_db)
    with pytest.raises(pricing.QuoteRefused) as refused:
        scene_chain.verify_keyframe_token(token, _concept(tmp_db, other), None)
    assert refused.value.reason == "wrong_render"
    # a still landed since the price: two to draw, not three
    timeline.attach_part(cid, 1, 2, "reference_image", "https://cdn/2.png",
                         db_path=tmp_db, account_id=None)
    with pytest.raises(pricing.QuoteRefused) as refused:
        scene_chain.verify_keyframe_token(token, _concept(tmp_db, cid), None)
    assert refused.value.reason == "stale_content"
    # ...and the token itself still reads: that is what lets a repeat be
    # answered "already used" while its own strip is being drawn
    assert scene_chain.read_keyframe_token(token, _concept(tmp_db, cid), None).stills == 3
    # an edited prompt is a different scene to price
    fresh = scene_chain.keyframe_token(_concept(tmp_db, other), None)
    concept = _concept(tmp_db, other)
    concept["shots"][0]["prompt"] += " Rain on the glass."
    with pytest.raises(pricing.QuoteRefused) as refused:
        scene_chain.verify_keyframe_token(fresh, concept, None)
    assert refused.value.reason == "stale_content"


def test_a_whole_scene_is_priced_for_the_most_it_can_draw(tmp_db, seams, monkeypatch):
    """A scene that renders whole is drawn as one still per moment of its
    move, up to BEATS_PER_SHOT. It was priced as ONE still and drew two
    (docs/BACKLOG.md #29). The price is the ceiling now and says so
    (`up_to`); drawn under that cap it makes every beat, and never more."""
    from src import pricing
    each = pricing.still_credits(nano_banana.MODEL)
    monkeypatch.setattr(shootgen, "beat_moments",
                        lambda prompt, **kw: ["the hand on the latch", "the door swings"])
    cid = a_scene(tmp_db)
    quote = scene_chain.keyframe_quote(_concept(tmp_db, cid))
    assert quote == {"stills": 2, "each": each, "credits": 2 * each, "up_to": True}
    result = scene_chain.draw_on_pick(cid, db_path=tmp_db, account_id=None,
                                      limit=quote["stills"])
    assert result["ok"] and result["drawn"] == 2
    assert [f["beat"] for f in result["frames"]] == ["the hand on the latch",
                                                     "the door swings"]
    assert len(seams["nano"]) == 2
    assert _concept(tmp_db, cid)["shots"][0]["reference_image"]
    # drawn: nothing left to price
    assert scene_chain.keyframe_quote(_concept(tmp_db, cid)) is None
    # the cap is the caller's number whatever the splitter says: one draws
    # the first beat alone -- the frame the clip anchors on
    one = a_scene(tmp_db)
    result = scene_chain.keyframe_scene(one, 1, db_path=tmp_db, limit=1)
    assert result["drawn"] == 1 and len(seams["nano"]) == 3
    assert [f["beat"] for f in result["frames"]] == ["the hand on the latch"]


def test_a_shot_that_holds_one_moment_draws_one_still_under_the_ceiling(tmp_db, seams):
    """The ceiling is not a count: the splitter reads this shot as a single
    moment ([] -- the `seams` default), so one still is drawn though two
    were priced. One call to the image model is one charge."""
    cid = a_scene(tmp_db)
    assert scene_chain.keyframe_quote(_concept(tmp_db, cid))["stills"] == 2
    result = scene_chain.draw_on_pick(cid, db_path=tmp_db, account_id=None, limit=2)
    assert result["ok"] and result["drawn"] == 1 and not result["error"]
    assert len(seams["nano"]) == 1


def test_a_ceiling_of_one_is_not_called_a_ceiling(tmp_db, monkeypatch):
    """`up_to` only where the count can come in under: with one beat a shot
    the price is one still and it is exact."""
    from src import pricing
    monkeypatch.setattr(shootgen, "BEATS_PER_SHOT", 1)
    each = pricing.still_credits(nano_banana.MODEL)
    quote = scene_chain.keyframe_quote(_concept(tmp_db, a_scene(tmp_db)))
    assert quote == {"stills": 1, "each": each, "credits": each}
    # a timed scene's count is what a draw makes: never marked
    assert "up_to" not in scene_chain.keyframe_quote(_concept(tmp_db, _timed(tmp_db)))


# --- an edited timed scene is priced by the shots it will be drawn as -------
# (2026-10-11, docs/BACKLOG.md #29.) A prompt or reference edit makes the
# stored timeline stale; the draw re-plans it first and makes one still per
# shot. The quote only read a CURRENT timeline, so it said one still.

EDITED = "(0-2s) a hand. (2-5s) a door. (5-8s) the street. (8-10s) rain."


def _edit(path, cid, prompt=EDITED):
    """The scene's prompt rewritten in place, as the canvas saves it: the
    stored timeline is left where it was, and is stale."""
    concept = _concept(path, cid)
    shots = concept["shots"]
    shots[0]["prompt"] = prompt
    preprod.update_concept_shots(cid, {"shots": shots}, dsn=path, account_id=None)
    from src import timeline
    assert not timeline.is_current(_concept(path, cid)["shots"][0])


@pytest.fixture
def no_planner(monkeypatch):
    """The one billed call a re-plan makes, refused: timeline.plan falls
    back to its deterministic split, one shot per window."""
    from src import gemini_utils
    calls = []

    def refuse(client_, model, contents, **kw):
        calls.append(model)
        raise RuntimeError("no planner in tests")

    monkeypatch.setattr(gemini_utils, "generate_with_retry", refuse)
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8ok")
    return calls


def test_an_edited_scene_nothing_has_drawn_is_priced_shot_by_shot(tmp_db, seams, no_planner):
    """Three shots planned, the prompt rewritten to four, no still anywhere:
    the price is the four shots the prompt carries -- what the card already
    draws as frames -- and the capped draw makes exactly those."""
    cid = _timed(tmp_db)
    _edit(tmp_db, cid)
    concept = _concept(tmp_db, cid)
    assert scene_chain.stills_to_draw(concept) == 4
    assert scene_chain.shots_to_draw(concept) == [1, 2, 3, 4]
    assert "up_to" not in scene_chain.keyframe_quote(concept)
    # one shot of it can be drawn alone, as the card offers
    assert scene_chain.pick_skip_reason(concept, part=4) is None
    assert scene_chain.pick_skip_reason(concept, part=5) == "no shot 5"
    assert scene_chain.keyframe_quote(concept, part=4)["stills"] == 1

    result = scene_chain.draw_on_pick(cid, db_path=tmp_db, account_id=None, limit=4)
    assert result["ok"] and result["drawn"] == 4 and result["parts"] == 4
    assert len(seams["nano"]) == 4 and len(no_planner) == 1
    assert all(p.get("reference_image") for p in _parts(tmp_db, cid))
    assert scene_chain.keyframe_quote(_concept(tmp_db, cid)) is None


def test_an_edited_scene_that_has_a_still_is_priced_as_one_and_drawn_as_one(
        tmp_db, seams, no_planner):
    """With a still somewhere, which shots keep theirs is the re-plan's
    answer. The price stays one still and the cap is what makes it true:
    the re-plan here leaves four shots undrawn and the draw makes ONE."""
    cid = _timed(tmp_db, drawn=(2,))
    _edit(tmp_db, cid)                  # every window's words changed: nothing carries
    concept = _concept(tmp_db, cid)
    quote = scene_chain.keyframe_quote(concept)
    assert quote["stills"] == 1 and "up_to" not in quote
    assert scene_chain.shots_to_draw(concept) == []
    assert scene_chain.pick_skip_reason(concept, part=1) == "not a timed scene"

    result = scene_chain.draw_on_pick(cid, db_path=tmp_db, account_id=None,
                                      limit=quote["stills"])
    assert result["ok"] and result["drawn"] == 1
    assert len(seams["nano"]) == 1
    assert [bool(p.get("reference_image")) for p in _parts(tmp_db, cid)] == \
        [True, False, False, False]
    # planned now, so the rest is priced shot by shot
    assert scene_chain.stills_to_draw(_concept(tmp_db, cid)) == 3
    # uncapped -- the graph, which shows nobody a price -- the same scene
    # would have drawn all four
    other = _timed(tmp_db, drawn=(2,))
    _edit(tmp_db, other)
    assert scene_chain.keyframe_scene(other, 1, db_path=tmp_db)["drawn"] == 4


def test_an_edited_scene_with_its_own_still_has_nothing_to_draw(tmp_db):
    """Unchanged: the scene's own frame is a still a person already has,
    and a re-pick must not buy another."""
    cid = _timed(tmp_db, drawn=(1, 2, 3))
    preprod.set_shot_reference_image(cid, 1, "https://cdn/had-1.png", dsn=tmp_db,
                                     account_id=None)
    _edit(tmp_db, cid)
    concept = _concept(tmp_db, cid)
    assert scene_chain.pick_skip_reason(concept) == "already has a still"
    assert scene_chain.keyframe_quote(concept) is None


def test_drawn_counts_what_this_call_made_not_what_the_strip_holds(tmp_db, seams,
                                                                 monkeypatch):
    """`frames` lists the stills the shots already had as well; `drawn` is
    what was drawn -- and charged -- now. The job's line reads it."""
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8ok")
    cid = _timed(tmp_db, drawn=(1,))
    result = scene_chain.keyframe_scene(cid, 1, db_path=tmp_db)
    assert len(result["frames"]) == 3 and result["drawn"] == 2
    assert len(seams["nano"]) == 2


def test_a_capped_draw_of_a_timed_scene_stops_at_the_cap(tmp_db, seams, monkeypatch):
    """`limit` counts stills DRAWN, not shots passed: a shot that already
    has its still costs nothing and does not use the cap up."""
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None, account_id=None: b"\xff\xd8ok")
    cid = _timed(tmp_db, parts=4, drawn=(1,))
    result = scene_chain.draw_on_pick(cid, db_path=tmp_db, account_id=None, limit=2)
    assert result["ok"], result
    assert len(seams["nano"]) == 2
    assert [bool(p.get("reference_image")) for p in _parts(tmp_db, cid)] == \
        [True, True, True, False]
    # the rest is another quote's to draw
    assert scene_chain.shots_to_draw(_concept(tmp_db, cid)) == [4]
