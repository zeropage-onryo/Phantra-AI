"""Scenes off one idea, and what happens to one afterwards.

A scene IS a one-shot concept (2026-08-26), so there is no second data
model here. Until 2026-10-11 the file was about the PICK that followed --
a board click recorded as the label -- and the Queue that approved it.
The board is gone (docs/tasks/task-higgsfield-shape.md): a scene is
rendered from the scene, `picked_at` is stamped by that approve, and
removing a scene is a plain hide that teaches nothing. The tests below say
so; the name of the file is historical.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import api
from app.main import app
from src import preprod, shootgen

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
    path = pg
    preprod.init(path)
    monkeypatch.setenv("DATABASE_URL", path)
    return path


def wait_for_job(job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never finished")


SEED_REF = "/refs/seed.jpg"


def _grounds_everything(concept_id, manual, account_id=None, *, idea=None):
    """A stand-in for api._attach_scene_refs that always grounds.

    The real one reads the asset bank and the composer's picks, neither
    of which a route test has; without it the reference gate archives
    every scene the route just wrote and the test is measuring the gate
    instead of the route. Signature matches the real one exactly -- a
    stub the code can call with kwargs it does not accept is a test that
    fails for a reason the test is not about.
    """
    concept = preprod.get_concept(concept_id, dsn=None, account_id=account_id)
    if not concept or not concept.get("shots"):
        return []
    shots = [dict(s) for s in concept["shots"]]
    shots[0]["refs"] = list(manual or []) or [SEED_REF]
    preprod.update_concept_shots(
        concept_id, {"shots": shots, "duration": concept.get("duration")},
        warnings=concept.get("warnings") or [], account_id=account_id)
    return shots[0]["refs"]


def a_scene(path, title="Cold Open", refs=None, prompt="P"):
    # The default carries ONE reference on purpose (2026-09-08): the
    # board and the Queue now refuse a scene with no photographs behind
    # it, and these tests are about parking, picking and rendering --
    # not about grounding. `refs=[]` still builds an ungrounded one, so
    # the gate itself stays testable; that is why this is a sentinel
    # check and not `refs or [SEED]`.
    return preprod.save_concept(
        {"title": title, "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
                    "desc": title, "prompt": prompt,
                    "refs": [SEED_REF] if refs is None else list(refs)}]},
             prompt_template="T", dsn=path, account_id=None)


# --- generating several to pick between -------------------------------------

def test_one_idea_writes_several_one_shot_concepts(tmp_db, monkeypatch):
    captured = {}

    def fake_model(client_, model, contents, **_):
        captured["prompt"] = contents if isinstance(contents, str) else contents[-1]
        return json.dumps({"scenes": [
            {"title": "Cold Open", "location": "garage", "prompt": "P1"},
            {"title": "The Door", "location": "", "prompt": "P2"},
            {"title": "Empty", "prompt": "  "},          # dropped, not saved
        ]})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    result = shootgen.generate_scene_concepts(
        "gearing up ritual", count=3, db_path=tmp_db,
        refs=["/locations/garage/photo/a.jpg"])

    assert [s["title"] for s in result["scenes"]] == ["Cold Open", "The Door"]
    # the idea reaches the model, and the takes are told to differ
    assert "gearing up ritual" in captured["prompt"]
    assert "STANDALONE" in captured["prompt"]

    saved = [preprod.get_concept(s["concept_id"], dsn=tmp_db, account_id=None) for s in result["scenes"]]
    for concept in saved:
        assert concept["is_scene"]                   # exactly one shot each
        assert len(concept["shots"]) == 1
        assert concept["picked"] is False            # unjudged until picked
        # the references ride ON the shot, so they reach every node later
        assert concept["refs"] == ["/locations/garage/photo/a.jpg"]
        assert concept["spark"] == "gearing up ritual"
    assert saved[0]["shots"][0]["location"] == "garage"


def test_attached_images_are_explicit_creative_authority(tmp_db, monkeypatch):
    captured = {}

    def fake_model(client_, model, contents, **_):
        captured["prompt"] = contents[-1]
        return '{"scenes": [{"title": "Reference Led", "prompt": "P"}]}'

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    shootgen.generate_scene_concepts(
        "a bright daytime reunion", count=1, db_path=tmp_db,
        image_refs=[(b"image bytes", "image/jpeg")])

    prompt = captured["prompt"]
    assert "a bright daytime reunion" in prompt
    assert "reference images are attached above" in prompt
    assert "Don't ignore them and write a generic idea" in prompt
    assert prompt.index("a bright daytime reunion") < prompt.index(
        "PROJECT (")


def test_the_run_route_refuses_an_empty_idea_and_a_missing_key(tmp_db, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert client.post("/api/scenes/run", data={"idea": "  "}).status_code == 400
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert client.post("/api/scenes/run", data={"idea": "x"}).status_code == 503


def test_the_run_route_saves_and_reports_one_scene(tmp_db, monkeypatch):
    """One Create, one scene (2026-09-10, Mike's call). A client still
    posting count=3 -- and a model answering with three takes anyway --
    gets ONE saved scene: the route clamps the ask and the generator
    never saves more than it asked for."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr("src.shootgen.reference_block",
                        lambda spark=None, client=None, db_path=None: "REFS")
    monkeypatch.setattr(
        "src.shootgen.generate_with_retry",
        lambda c, m, p, **_: json.dumps({"scenes": [
            {"title": f"S{i}", "prompt": f"P{i}"} for i in range(3)]}))
    # Something has to ground them or the reference gate archives all
    # three and they leave the board (2026-09-08). This test is about the
    # route saving and reporting; what happens to an UNgrounded Create is
    # test_create_archives_a_scene_it_could_not_ground.
    monkeypatch.setattr(api, "_attach_scene_refs", _grounds_everything)

    job = wait_for_job(client.post(
        "/api/scenes/run",
        data={"idea": "night ride", "count": 3},
    ).json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert "1 concept(s)" in job["detail"]

    body = client.get("/api/pipeline/concepts").json()
    scenes = [c for c in body["items"] if c["is_scene"]]
    assert len(scenes) == 1
    assert all(c["prompt"] for c in scenes)          # the card carries the prompt


def test_the_route_caps_the_count_at_one(tmp_db, monkeypatch):
    """The Studio composer no longer offers a count (2026-09-10). A
    hand-rolled request asking for forty is asked of the model as one."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr("src.shootgen.reference_block",
                        lambda spark=None, client=None, db_path=None: "")
    asked = {}

    def fake_model(client_, model, contents, **_):
        asked["prompt"] = contents if isinstance(contents, str) else contents[-1]
        return json.dumps({"scenes": [{"title": "S", "prompt": "P"}]})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    job = wait_for_job(client.post(
        "/api/scenes/run",
        data={"idea": "night ride", "count": "40"},
    ).json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert "40" not in asked["prompt"].split("night ride")[0]
    assert "You write 1 SEPARATE" in asked["prompt"]


# --- which brain writes (2026-09-09) ----------------------------------------
# The composer picks a model tier per run. Two things are worth pinning:
# that the tier reaches the model actually asked for, and that the SELECT
# is not the gate -- the clamp is here, for the same reason count's is.

def _records_the_call(monkeypatch, asked):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr("src.shootgen.reference_block",
                        lambda spark=None, client=None, db_path=None: "")

    def fake_model(client_, model, contents, **kwargs):
        asked["model"] = model
        asked["config"] = kwargs.get("config")
        asked["fallbacks"] = kwargs.get("fallbacks")
        return json.dumps({"scenes": [{"title": "S", "prompt": "P"}]})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)


def _create(**data):
    return wait_for_job(client.post("/api/scenes/run", data=data).json()["job_id"])


def test_create_writes_on_the_fast_tier_by_default(tmp_db, monkeypatch):
    from src import gemini_utils
    asked = {}
    _records_the_call(monkeypatch, asked)
    job = _create(idea="night ride", count="1")
    assert job["status"] == "done", job.get("error")
    assert asked["model"] == gemini_utils.FAST_MODEL
    # the fast tier's request is byte-for-byte the one this path has
    # always sent: no config, the standard fallback chain
    assert asked["config"] is None and asked["fallbacks"] is None
    assert "fast" not in job["detail"]          # the default is not narrated


def test_asking_for_the_reasoning_tier_reaches_the_writer(tmp_db, monkeypatch):
    from src import gemini_utils
    asked = {}
    _records_the_call(monkeypatch, asked)
    job = _create(idea="night ride", count="1", brain="reasoning")
    assert job["status"] == "done", job.get("error")
    assert asked["model"] == gemini_utils.REASONING_MODEL
    assert asked["config"].thinking_config.thinking_level == "HIGH"
    # and it takes no substitute -- an empty list, not None
    assert asked["fallbacks"] == []
    assert "reasoning" in job["detail"]         # the card says which brain wrote it


def test_an_invented_tier_writes_a_cheap_scene(tmp_db, monkeypatch):
    """A hand-rolled request naming a tier that does not exist must not
    fail a run, and must not reach the model as-is."""
    from src import gemini_utils
    asked = {}
    _records_the_call(monkeypatch, asked)
    job = _create(idea="night ride", count="1",
                  brain="gpt-9-ultra")
    assert job["status"] == "done", job.get("error")
    assert asked["model"] == gemini_utils.FAST_MODEL


def test_the_menu_is_a_projection_of_the_one_table(tmp_db):
    from src import gemini_utils
    body = client.get("/api/brains").json()
    assert [b["id"] for b in body["brains"]] == list(gemini_utils.BRAINS)
    assert body["default"] == gemini_utils.DEFAULT_BRAIN
    assert sum(1 for b in body["brains"] if b["default"]) == 1
    assert all(b["label"] and b["note"] for b in body["brains"])

# --- the pick ---------------------------------------------------------------

def test_there_is_no_pick_route_any_more(tmp_db):
    """The board's pick is gone (2026-10-11): a scene is rendered from the
    scene, and `picked_at` is stamped by that approve and nothing else."""
    scene_id = a_scene(tmp_db)
    res = client.post(f"/api/concepts/{scene_id}/pick", json={"picked": True})
    assert res.status_code in (404, 405)
    assert preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["picked_at"] is None


def test_the_label_is_still_recorded_and_counted(tmp_db):
    """The column and the rate stay (nothing is dropped): what was picked
    before is still counted, and windowable."""
    ids = [a_scene(tmp_db, f"S{i}") for i in range(4)]
    preprod.set_picked(ids[0], True, dsn=tmp_db, account_id=None)
    rate = preprod.pick_rate(dsn=tmp_db, account_id=None)
    assert (rate["picked"], rate["generated"], rate["rate"]) == (1, 4, 0.25)
    concept = preprod.get_concept(ids[0], dsn=tmp_db, account_id=None)
    assert concept["picked"] is True
    assert concept["picked_at"]                       # windowable, not a bare flag


def test_pick_rate_ignores_legacy_multi_shot_concepts(tmp_db):
    """A six-shot concept was never a single scene to pick between, so
    counting it would compare two different decisions."""
    a_scene(tmp_db, "a scene")
    preprod.save_concept(
        {"title": "old", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "prompt": "x"},
                   {"n": 2, "type": "BROLL", "source": "AI", "prompt": "y"}]}, dsn=tmp_db, account_id=None)
    assert preprod.pick_rate(dsn=tmp_db, account_id=None)["generated"] == 1


def test_pick_rate_on_an_empty_table_is_none_not_a_crash(tmp_db):
    assert preprod.pick_rate(dsn=tmp_db, account_id=None)["rate"] is None


# --- the references a scene carries -----------------------------------------

def test_refs_round_trip_on_the_shot(tmp_db):
    scene_id = a_scene(tmp_db)
    res = client.post(f"/api/concepts/{scene_id}/refs",
                      json={"refs": ["/a/face.jpg", "/b/jacket.jpg"]})
    assert res.json()["refs"] == ["/a/face.jpg", "/b/jacket.jpg"]
    concept = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)
    assert concept["refs"] == ["/a/face.jpg", "/b/jacket.jpg"]
    assert concept["shots"][0]["prompt"] == "P"       # the prompt is untouched
    # and the card surfaces them for the board
    card = [c for c in client.get("/api/pipeline/concepts").json()["items"]
            if c["id"] == scene_id][0]
    assert card["refs"] == ["/a/face.jpg", "/b/jacket.jpg"]


# --- removing a scene -------------------------------------------------------
# Archiving hides a scene; it never deletes one.
#
# From 2026-09-02 to 2026-10-11 the X was also a VERDICT: it filed the
# scene's prompt to be taught as something to avoid. The eval layer reads
# what happens to outputs now, so removing a scene is a plain hide and
# teaches nothing (docs/tasks/task-higgsfield-shape.md).

def test_archiving_hides_the_card_but_keeps_the_row(tmp_db):
    ids = [a_scene(tmp_db, f"S{i}") for i in range(3)]

    assert client.post(f"/api/concepts/{ids[0]}/archive",
                       json={"archived": True}).json()["archived"] is True

    open_board = client.get("/api/pipeline/concepts").json()["items"]
    assert [c["id"] for c in open_board] == [ids[2], ids[1]]      # newest first

    # still there, still counted, still ungraded
    everything = client.get(
        "/api/pipeline/concepts?brand=zeropage&archived=true").json()
    assert len(everything["items"]) == 3
    assert everything["pick"]["generated"] == 3
    archived = preprod.get_concept(ids[0], dsn=tmp_db, account_id=None)
    assert archived["archived"] is True
    assert archived["archived_at"]
    assert archived["graded"] is False        # the judge has not scored it yet


def test_archiving_is_reversible(tmp_db):
    scene_id = a_scene(tmp_db)
    client.post(f"/api/concepts/{scene_id}/archive", json={"archived": True})
    client.post(f"/api/concepts/{scene_id}/archive", json={"archived": False})
    assert preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["archived"] is False
    assert len(client.get("/api/pipeline/concepts").json()["items"]) == 1


# --- removing is a plain hide -----------------------------------------------

def test_removing_a_scene_files_no_verdict(tmp_db):
    """One tap off the list used to rule on the scene's prompt. It hides
    the scene and nothing else: no lesson is filed, nothing lands on the
    Teach tab."""
    from src import winners
    scene_id = a_scene(tmp_db, prompt="a prompt that did not land")

    res = client.post(f"/api/concepts/{scene_id}/archive", json={"archived": True})
    assert res.json() == {"ok": True, "archived": True, "ruled": False}
    assert winners.recorded(f"concept-{scene_id}-shot-1", dsn=tmp_db) == []


def test_a_reason_in_the_body_is_ignored(tmp_db):
    """Removing takes no reason: a client that still sends one hides the
    scene and records nothing about why."""
    scene_id = a_scene(tmp_db)
    res = client.post(f"/api/concepts/{scene_id}/archive",
                      json={"archived": True, "reason": "boring"})
    assert res.status_code == 200
    concept = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)
    assert concept["archived"] is True
    assert not concept.get("archive_reason")


def test_putting_a_scene_back_withdraws_a_lesson_filed_before(tmp_db):
    """A pass filed while the board still ruled, and not taught yet, goes
    when the scene comes back: a scene in its project must not keep a
    pending lesson saying it was turned down."""
    from src import winners
    scene_id = a_scene(tmp_db, prompt="the scene's prompt")
    ref = f"concept-{scene_id}-shot-1"
    winners.record_and_learn("runway", "the scene's prompt", note=api.BOARD_PASS_NOTE,
                             video_ref=ref, verdict="didnt_work", ingest=False, dsn=tmp_db)
    preprod.set_archived(scene_id, True, dsn=tmp_db, account_id=None)
    assert len(winners.recorded(ref, dsn=tmp_db)) == 1

    client.post(f"/api/concepts/{scene_id}/archive", json={"archived": False})
    assert winners.recorded(ref, dsn=tmp_db) == []


def test_a_verdict_you_considered_survives_a_remove_and_a_put_back(tmp_db):
    """A pair you wrote yourself -- a hand edit, or one filed on the old
    Grade tab -- means you read the prompt and rewrote it. Removing the
    scene, or putting it back, must not touch it."""
    from src import winners
    scene_id = a_scene(tmp_db, prompt="the model's prompt")
    winners.record_pair("runway", "the model's prompt", "my version", note="edited by hand",
                        video_ref=f"concept-{scene_id}-shot-1", dsn=tmp_db, ingest=False)
    before = winners.recorded(f"concept-{scene_id}-shot-1", dsn=tmp_db)

    client.post(f"/api/concepts/{scene_id}/archive", json={"archived": True})
    client.post(f"/api/concepts/{scene_id}/archive", json={"archived": False})
    after = winners.recorded(f"concept-{scene_id}-shot-1", dsn=tmp_db)
    assert [w["id"] for w in after] == [w["id"] for w in before]
    assert {w["prompt"] for w in after} == {"the model's prompt", "my version"}


def test_a_concept_with_no_prompt_just_archives(tmp_db):
    cid = preprod.save_concept({"title": "no prompt", "shots": []},
                               dsn=tmp_db, account_id=None)
    res = client.post(f"/api/concepts/{cid}/archive", json={"archived": True})
    assert res.json()["ruled"] is False
    assert preprod.get_concept(cid, dsn=tmp_db, account_id=None)["archived"] is True


def test_archiving_a_row_that_has_an_owner_works(tmp_db):
    """The X on the board archives a concept that belongs to an account.

    Regression, 2026-09-02. `concept_archive` declared
    `account_id: Optional[int] = None`, which to FastAPI is a *query
    parameter*, not the auth dependency -- so every archive arrived as
    None and set_archived's `WHERE ... AND account_id IS NOT DISTINCT FROM %s` matched
    nothing. Every card on the real board 404'd on "Not this one" while
    "Pick this", which took `Depends(current_account_id)`, worked.

    The rest of this file runs under conftest's unowned pool
    (account_id None), where a bare default and the dependency return
    the same value and the bug is invisible -- so this test seeds an
    OWNED row and an account to act as, which is the only shape that
    tells them apart."""
    from app import auth
    live = client.app   # the app THIS client is bound to -- app.main.app is a
    # different object after test_dev_tools reloads the module
    from src import accounts

    accounts.init(tmp_db)
    account_id = accounts.upsert_account("owned", "OWNED", dsn=tmp_db)

    owned = preprod.save_concept(
        {"title": "Owned", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
                    "desc": "Owned", "prompt": "P", "refs": []}]},
             prompt_template="T", dsn=tmp_db, account_id=account_id)

    previous = live.dependency_overrides[auth.current_account_id]
    live.dependency_overrides[auth.current_account_id] = lambda: account_id
    try:
        r = client.post(f"/api/concepts/{owned}/archive", json={"archived": True})
        assert r.status_code == 200, r.text
        assert preprod.get_concept(
            owned, dsn=tmp_db, account_id=account_id)["archived"] is True
    finally:
        live.dependency_overrides[auth.current_account_id] = previous


def test_archiving_something_that_does_not_exist_is_a_404(tmp_db):
    assert client.post("/api/concepts/9999/archive",
                       json={"archived": True}).status_code == 404


def test_archive_batch_keeps_the_ones_you_name(tmp_db):
    """One idea's concepts share its spark, which is what makes them a
    batch worth resolving together."""
    kept = preprod.save_concept(
        {"title": "keep", "shots": [{"n": 1, "source": "AI",
                                     "prompt": "p"}]}, spark="night ride", dsn=tmp_db, account_id=None)
    others = [preprod.save_concept(
        {"title": f"other{i}", "shots": [{"n": 1, "source": "AI",
                                          "prompt": "p"}]},
            spark="night ride", dsn=tmp_db, account_id=None) for i in range(2)]
    unrelated = preprod.save_concept(
        {"title": "different idea", "shots": [{"n": 1, "source": "AI",
                                               "prompt": "p"}]}, spark="garage", dsn=tmp_db, account_id=None)

    assert preprod.archive_batch("night ride", keep_ids=[kept], dsn=tmp_db, account_id=None) == 2
    assert preprod.get_concept(kept, dsn=tmp_db, account_id=None)["archived"] is False
    assert all(preprod.get_concept(i, dsn=tmp_db, account_id=None)["archived"] for i in others)
    assert preprod.get_concept(unrelated, dsn=tmp_db, account_id=None)["archived"] is False


# --- the approval gate ------------------------------------------------------
# Rendering is the only step that spends money, so it is the only one
# with a gate -- and since 2026-10-11 that gate is on the scene: POST
# /api/scenes/{id}/approve (the old /api/queue/{id}/approve is the same
# function for one release). No pick comes first. The /queue/pending
# listing is what is left of the Queue page: scenes a render was started
# on, or that a graph run parked, with no clip yet.

def _pick(path, *scene_ids):
    """What an approve stamps, written directly: the listing tests are
    about the listing, not about a render."""
    for scene_id in scene_ids:
        preprod.set_picked(scene_id, True, dsn=path, account_id=None)


def test_pending_is_what_was_started_and_not_yet_rendered(tmp_db):
    picked = a_scene(tmp_db, "render started")
    a_scene(tmp_db, "never started")
    rendered = a_scene(tmp_db, "already rendered")
    archived = a_scene(tmp_db, "removed")
    _pick(tmp_db, picked, rendered, archived)
    preprod.set_shot_media_url(rendered, 1, "https://x/clip.mp4", dsn=tmp_db, account_id=None)
    client.post(f"/api/concepts/{archived}/archive", json={"archived": True})

    body = client.get("/api/queue/pending").json()
    assert [c["id"] for c in body["items"]] == [picked]
    assert "spend_ok" in body["renderer"]     # the gate is stated, not guessed at
    # the Renders page reads the same rows, with nothing priced
    lean = client.get("/api/renders/unfinished").json()["items"]
    assert [c["id"] for c in lean] == [picked]
    assert "quote" not in lean[0] and lean[0]["blocked"] == ""


def test_a_parked_scene_is_pending_but_a_merely_keyframed_one_is_not(tmp_db):
    """The queue asks "is this waiting on me to spend", and only the
    chain's explicit park answers it. A reference_image alone must NOT:
    the Director canvas attaches one mid-work, and inferring from it
    would drag every scene anyone ever keyframed into the spend queue.
    """
    parked = a_scene(tmp_db, "parked by the chain")
    preprod.set_shot_reference_image(parked, 1, "https://cdn/key.png", dsn=tmp_db, account_id=None)
    preprod.set_shot_parked(parked, 1, "keyframe rendered", dsn=tmp_db, account_id=None)

    mid_work = a_scene(tmp_db, "keyframed in Director")
    preprod.set_shot_reference_image(mid_work, 1, "https://cdn/other.png", dsn=tmp_db, account_id=None)

    items = client.get("/api/queue/pending").json()["items"]
    assert [c["id"] for c in items] == [parked]
    card = items[0]
    assert card["parked"] is True
    assert card["park_reason"] == "keyframe rendered"
    assert card["reference_image"] == "https://cdn/key.png"
    assert card["picked"] is False            # approving is what picks it


def _renders(monkeypatch, db):
    """fal stood in for: the key is there and a render attaches a clip."""
    monkeypatch.setattr("src.fal.has_key", lambda account_id=None: True)
    made = []

    def fake_render(concept_id, shot_n, db_path=None, resolve_photo=None,
                    account_id=None, **picked):
        made.append((concept_id, shot_n))
        preprod.set_shot_media_url(concept_id, shot_n, "https://x/clip.mp4",
                                   dsn=db_path, account_id=account_id)
        return {"ok": True}

    monkeypatch.setattr("src.fal.generate_for_shot", fake_render)
    return made


def test_a_scene_is_rendered_from_the_scene_with_no_pick_first(tmp_db, monkeypatch):
    """THE CHANGE (2026-10-11). A scene that was never picked and never
    parked used to be refused with `not_queued`. The priced button on the
    scene is the whole decision now: the approve renders it, and stamps
    `picked_at` -- which means "rendered on purpose" -- before the spend."""
    made = _renders(monkeypatch, tmp_db)
    scene_id = a_scene(tmp_db)
    before = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)
    assert before["picked"] is False and before["parked"] is False

    res = client.post(f"/api/scenes/{scene_id}/approve")
    assert res.status_code == 200, res.text
    job = wait_for_job(res.json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert made == [(scene_id, 1)]
    # the job names its scene from the start: the Render card reads it live
    assert job["ref_id"] == scene_id
    after = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)
    assert after["picked"] is True and after["picked_at"]
    assert after["shots"][0]["media_url"] == "https://x/clip.mp4"


def test_the_old_queue_path_is_the_same_approve(tmp_db, monkeypatch):
    """`/api/queue/{id}/approve` and `/quote` answer for one more release,
    as the same functions under their old names."""
    made = _renders(monkeypatch, tmp_db)
    scene_id = a_scene(tmp_db)
    new = client.get(f"/api/scenes/{scene_id}/quote").json()
    old = client.get(f"/api/queue/{scene_id}/quote").json()
    assert {k: new[k] for k in ("provider", "model", "frame", "credits")} == \
           {k: old[k] for k in ("provider", "model", "frame", "credits")}
    job = wait_for_job(client.post(f"/api/queue/{scene_id}/approve").json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert made == [(scene_id, 1)]


def test_the_render_card_is_one_answer_for_one_scene(tmp_db, monkeypatch):
    """GET /api/scenes/{id}/render: the scene, the renderer it opens on,
    that pick's price, the reference gate's answer and the catalogue --
    for ANY scene, picked or not. It spends and writes nothing."""
    monkeypatch.setattr("src.fal.has_key", lambda account_id=None: True)
    # the reference rule is off in tests unless a test turns it on (conftest)
    monkeypatch.setenv(preprod.REQUIRE_REFS_ENV, "1")
    scene_id = a_scene(tmp_db, "Cold Open")
    blind = a_scene(tmp_db, "no photos", refs=[])

    body = client.get(f"/api/scenes/{scene_id}/render").json()
    card = body["scene"]
    assert card["id"] == scene_id and card["blocked"] == ""
    assert card["render_default"]["provider"] == "fal"
    assert card["quote"]["credits"] and card["quote"]["renders"]
    assert card["quote"]["model"] == card["render_default"]["model"]
    # no timed shots: up to a still per moment of its one move (BACKLOG #29)
    assert card["keyframes"]["stills"] == 2 and card["keyframes"]["up_to"] is True
    assert "fal" in body["renderers"] and "spend_ok" in body["renderer"]
    # nothing was written by asking
    assert preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["picked"] is False

    assert "reference" in client.get(f"/api/scenes/{blind}/render").json()["scene"]["blocked"]
    assert client.get("/api/scenes/9999/render").status_code == 404


def test_an_ungrounded_scene_is_listed_blocked_and_never_spendable(tmp_db):
    """The reference gate at the spend door (2026-09-08, Mike's call), and
    what the Queue PAGE may show of it (2026-09-17, also his).

    The case that prompted the gate: a scene the nightly graph parked with
    a keyframe, whose card read "KEYFRAMED · AWAITING APPROVAL IN QUEUE"
    beside "NO REFERENCES". The still was drawn by Nano from the prompt, so
    approving would have anchored a paid clip on the pipeline's own guess.

    It used to be dropped from the list outright, which made a picked scene
    with no photos look like a lost pick. Now it is LISTED -- marked
    `blocked` with the gate's reason, after every spendable card, and left
    out of `spendable` (the rail's badge). Still not approvable: see the
    next test. Grounded siblings are unaffected.
    """
    blind = a_scene(tmp_db, "no photos", refs=[])
    grounded = a_scene(tmp_db, "has photos")
    for scene_id in (grounded, blind):
        preprod.set_shot_reference_image(scene_id, 1, "https://cdn/key.png",
                                         dsn=tmp_db, account_id=None)
        preprod.set_shot_parked(scene_id, 1, "keyframe rendered",
                                dsn=tmp_db, account_id=None)

    body = client.get("/api/queue/pending").json()
    # spendable first, whatever order the rows were written in
    assert [c["id"] for c in body["items"]] == [grounded, blind]
    assert [bool(c["blocked"]) for c in body["items"]] == [False, True]
    assert "reference" in body["items"][1]["blocked"]
    assert body["spendable"] == 1


def test_with_the_reference_rule_off_nothing_is_blocked(tmp_db, monkeypatch):
    """`blocked` is reference_gate's answer, not a second rule: the one
    switch (PHANTRA_REQUIRE_REFS=0) turns it off here too."""
    monkeypatch.setenv(preprod.REQUIRE_REFS_ENV, "0")
    blind = a_scene(tmp_db, "no photos", refs=[])
    preprod.set_shot_parked(blind, 1, "keyframe rendered", dsn=tmp_db, account_id=None)
    body = client.get("/api/queue/pending").json()
    assert [(c["id"], c["blocked"]) for c in body["items"]] == [(blind, "")]
    assert body["spendable"] == 1


def test_approving_an_ungrounded_scene_is_refused_before_it_spends(tmp_db, monkeypatch):
    """Asked at the route too, not only in the listing. This one is
    reachable by id without ever reading the queue, and a concept can
    lose its refs between the two requests -- so the check has to sit
    where the money is actually spent.
    """
    monkeypatch.setattr("src.fal.has_key", lambda account_id=None: True)
    called = []
    monkeypatch.setattr("src.fal.generate_for_shot",
                        lambda *a, **k: called.append(a) or {"ok": True})

    blind = a_scene(tmp_db, "no photos", refs=[])
    preprod.set_shot_parked(blind, 1, "keyframe rendered", dsn=tmp_db,
                            account_id=None)
    for path in (f"/api/scenes/{blind}/approve", f"/api/queue/{blind}/approve"):
        res = client.post(path)
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "no_reference"
    assert called == []          # the point: nothing was billed
    # ...and it was not stamped as rendered on purpose either
    assert preprod.get_concept(blind, dsn=tmp_db, account_id=None)["picked"] is False


def test_the_prompt_is_not_re_judged_at_the_queue(tmp_db, monkeypatch):
    """Deliberately NOT a second bar. A prompt is on the row only
    because score_prompts put it there; re-judging it here would be a
    different opinion from the one that already ran, at the one place
    where disagreeing is expensive."""
    monkeypatch.setattr("src.fal.has_key", lambda account_id=None: True)
    thin = a_scene(tmp_db, "thin prompt", prompt="x")
    preprod.set_shot_parked(thin, 1, "keyframe rendered", dsn=tmp_db,
                            account_id=None)
    items = client.get("/api/queue/pending").json()["items"]
    assert [c["id"] for c in items] == [thin]


def test_approving_one_take_leaves_its_siblings_in_the_queue(tmp_db, monkeypatch):
    """Approving used to archive every unpicked sibling from the same
    spark, inferring "you have answered this batch". That was safe while
    picking was a separate bulk step done first. Now that approval IS
    the pick, that inference would archive takes 2-4 out from under you
    the moment you approved take 1 -- and racily, since it ran after
    the render returned. Rejecting is the only thing that archives now."""
    takes = [preprod.save_concept(
        {"title": f"take{i}", "shots": [{"n": 1, "source": "AI", "tool": "LTX",
                                         "prompt": "p", "refs": [SEED_REF]}]},
            spark="night ride", dsn=tmp_db, account_id=None) for i in range(3)]
    for scene_id in takes:
        preprod.set_shot_parked(scene_id, 1, "keyframe rendered", dsn=tmp_db, account_id=None)

    monkeypatch.setattr("src.fal.has_key", lambda account_id=None: True)
    rendered = {}

    def fake_render(concept_id, shot_n, db_path=None, resolve_photo=None,
                    account_id=None, **picked):
        # account_id because the route passes it now (2026-09-02). This
        # test runs in conftest's unowned pool, where it is None; the
        # owned case is test_the_render_path_carries_the_owner.
        # **picked because the route also passes the renderer choice now
        # (2026-09-08): model, duration and the frame, under whichever
        # name that vendor calls it. What lands in them is
        # test_queue_renderers.py's subject, not this test's.
        rendered["args"] = (concept_id, shot_n)
        preprod.set_shot_media_url(concept_id, shot_n, "https://x/clip.mp4",
                                   dsn=db_path, account_id=account_id)
        return {"ok": True}

    monkeypatch.setattr("src.fal.generate_for_shot", fake_render)

    job = wait_for_job(client.post(f"/api/queue/{takes[0]}/approve").json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert rendered["args"] == (takes[0], 1)

    # approving stamped the pick, and it stamped it before the spend
    assert preprod.get_concept(takes[0], dsn=tmp_db, account_id=None)["picked"] is True
    assert all(not preprod.get_concept(i, dsn=tmp_db, account_id=None)["archived"] for i in takes)
    # the rendered one leaves the queue on its own; the others stay
    pending = client.get("/api/queue/pending").json()["items"]
    assert sorted(c["id"] for c in pending) == takes[1:]   # newest-first listing


def test_approving_with_no_renderer_key_at_all_says_so(tmp_db, monkeypatch):
    """The suite inherits the operator's own .env on his machine, so
    "unconfigured" has to be asserted, not assumed."""
    from src import fal
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: False)
    scene_id = a_scene(tmp_db)
    assert client.post(f"/api/scenes/{scene_id}/approve").status_code == 503
    # refused before the stamp: nothing says it was rendered
    assert preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)["picked"] is False


def test_rejecting_unpicks_and_archives(tmp_db):
    """Rejected at the spend gate means it was generated and not picked,
    which is exactly what pick_rate should read."""
    scene_id = a_scene(tmp_db)
    _pick(tmp_db, scene_id)
    res = client.post(f"/api/queue/{scene_id}/reject")
    assert res.json()["pick"]["picked"] == 0
    concept = preprod.get_concept(scene_id, dsn=tmp_db, account_id=None)
    assert concept["picked"] is False and concept["archived"] is True


# --- the one line the board is read by ---------------------------------------
# A scene prompt is ~1200 characters of camera, grade, beats and
# avoid-list; four of them open at once is what the summary replaces
# (2026-08-31). The writer supplies `logline`, the card caps it to one
# line, and a row written before the prompt asked for one gets a line
# derived from its own prompt rather than a blank.

def test_writer_card_line_is_saved_and_served_as_the_card_summary(tmp_db, monkeypatch):
    def fake_model(client_, model, contents, **_):
        return json.dumps({"scenes": [{
            "title": "The Garage Guest",
            "card_line": "Michael finds a cyclops polishing silverware",
            "location": "garage", "prompt": "P1"}]})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    # the prompt template has to ASK for it, or nothing arrives to save
    assert "card_line" in shootgen.build_scenes_prompt("x",2, [])

    result = shootgen.generate_scene_concepts("x", count=1, db_path=tmp_db)
    saved = preprod.get_concept(result["scenes"][0]["concept_id"], dsn=tmp_db,
                                account_id=None)
    assert saved["card_line"] == "Michael finds a cyclops polishing silverware"

    card = next(c for c in client.get("/api/pipeline/concepts").json()["items"]
                if c["id"] == saved["id"])
    assert card["summary"] == "Michael finds a cyclops polishing silverware"


def test_a_rich_logline_is_never_squeezed_into_the_card_line(tmp_db, monkeypatch):
    """scene_brief_prompt.txt makes `logline` 2-4 sentences on purpose --
    "where the IDEA survives". The card gets its OWN field; the idea
    record is stored whole and is only a fallback for the card."""
    rich = ("Michael tries to repair his motorcycle in a cramped garage while a "
            "massive cyclops watches. He wants the ride more than he wants to be "
            "safe, and the creature is the price of admission.")

    def fake_model(client_, model, contents, **_):
        return json.dumps({"title": "Garage Giant", "hook": "a greasy wrench",
                           "card_line": "Cyclops watches Michael fix his bike",
                           "logline": rich, "brief": "Beats: he fixes it."})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    assert "card_line" in shootgen.build_scene_brief_prompt()

    out = shootgen.generate_scene_concept(db_path=tmp_db, cast="")
    saved = preprod.get_concept(out["concept_id"], dsn=tmp_db, account_id=None)
    assert saved["logline"] == rich                      # stored whole
    assert saved["card_line"] == "Cyclops watches Michael fix his bike"

    card = next(c for c in client.get("/api/pipeline/concepts").json()["items"]
                if c["id"] == saved["id"])
    assert card["summary"] == "Cyclops watches Michael fix his bike"
    assert not card["summary"].endswith("\u2026")

    # with no card line the rich logline is a TRIMMED fallback -- never
    # shown whole, and never rewritten in the row
    assert preprod.concept_summary("", rich).endswith("\u2026")



def test_a_missing_card_line_never_leaves_a_card_blank(tmp_db, monkeypatch):
    """The model skipping the key, or a row written before it existed."""
    def fake_model(client_, model, contents, **_):
        return json.dumps({"scenes": [{"title": "Untitled", "prompt": (
            "Ultra-realistic grounded dark comedy video in 9:16. "
            "Style: raw handheld, muted colour. "
            "Beats: Open on a low-angle shot of Michael wrestling a breathing "
            "sofa. He loses. No background music.")}]})

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    result = shootgen.generate_scene_concepts("x", count=1, db_path=tmp_db)
    card = next(c for c in client.get("/api/pipeline/concepts").json()["items"]
                if c["id"] == result["scenes"][0]["concept_id"])
    # derived from the BEATS block, with the camera direction taken off
    assert card["summary"].startswith("Michael wrestling a breathing sofa")
    assert "low-angle" not in card["summary"]


def test_the_summary_fits_one_line_of_the_narrowest_card():
    """Both caps, and both cut on a WORD boundary -- a line that ends
    mid-word is what "cuts off" looked like before."""
    out = preprod.concept_summary(" ".join(f"word{i}" for i in range(40)))
    assert len(out.split(" ")) == preprod.SUMMARY_WORDS and out.endswith("…")

    # 8 short words are under the word cap but over the character one
    wordy = "Michael investigates the extraordinarily complicated mechanical contraption downstairs"
    out = preprod.concept_summary(wordy)
    assert len(out) <= preprod.SUMMARY_CHARS + 1        # +1 for the ellipsis
    assert "…" in out and not out.replace("…", "").endswith(" ")
    assert wordy.startswith(out.replace("…", ""))       # never cut mid-word

    # one that already fits is printed whole, with no ellipsis at all
    fits = "Michael finds a cyclops asleep in his bed"
    assert preprod.concept_summary(fits) == fits

    assert "\n" not in preprod.concept_summary("two\nlines here")
    # nothing to say and nothing to derive from stays empty, so the card
    # drops the line rather than printing a stub
    assert preprod.concept_summary("", "") == ""


def test_the_backfill_writes_lines_by_the_same_rules_as_the_writers(monkeypatch):
    """One copy of the rules. A backfilled logline that obeyed different
    ones would be a second voice on the same board. All the rows go in
    ONE call -- the model is regularly throttled, and N calls is N waits."""
    seen = {}

    def fake_model(client_, model, contents, **_):
        seen["prompt"] = contents
        return ('```json\n{"card_lines": {"7": "  Michael wrestles a breathing sofa  ",\n'
                '"9": "Cyclops tears the wall open", "11": "  "}}\n```')

    monkeypatch.setattr("src.shootgen.generate_with_retry", fake_model)
    lines = shootgen.write_card_lines({7: "prompt seven", 9: "prompt nine", 11: "p"})

    # fences, padding and quotes gone; ids are ints; an empty line is
    # dropped rather than written over a real row
    assert lines == {7: "Michael wrestles a breathing sofa",
                     9: "Cyclops tears the wall open"}
    assert all(f"SCENE {i}" in seen["prompt"] for i in (7, 9, 11))
    assert shootgen.CARD_LINE_RULES in seen["prompt"]
    # and BOTH writer templates get that same block, not a copy
    for built in (shootgen.build_scenes_prompt("x",2, []),
                  shootgen.build_scene_brief_prompt()):
        assert shootgen.CARD_LINE_RULES in built
        assert "{card_line_rules}" not in built


def test_the_backfill_targets_anything_the_card_would_trim(tmp_db):
    """Empty AND too-long both count. It writes `card_line` and leaves
    `logline` alone -- the idea record is not a long card label."""
    from ops import backfill_loglines

    def concept(card_line):
        cid = preprod.save_concept(
            {"title": "T", "hook": "", "logline": "", "card_line": card_line,
             "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
                        "desc": "T", "prompt": "Beats: something happens."}]},
                 prompt_template="T", dsn=tmp_db, account_id=None)
        return preprod.get_concept(cid, dsn=tmp_db, account_id=None)

    assert backfill_loglines.needs_one(concept(""))
    assert backfill_loglines.needs_one(concept(
        "In a dark, gritty garage, Michael prepares his motorcycle for the "
        "night under the silent, watchful gaze of a massive cyclops"))
    assert not backfill_loglines.needs_one(
        concept("Michael finds a cyclops asleep in his bed"))



# --- the rooms stopped being the anchor (2026-08-31, Mike's call) -----------
#
# The Create path used to list every described room under "set scenes in
# these real spaces where they fit", which made the photographed rooms
# the default gravity of every generation. That was right when shots came
# off a camera. Since 2026-08-20 every shot is AI-generated, so a room is
# named material like cast -- and material nobody chose for this idea has
# no business steering it. Now only what was PICKED for the run appears.

LOCS = [
    {"name": "Front Hallway",
     "description": {"space": "narrow hallway", "light_sources": ["overhead practical"]}},
    {"name": "Garage", "description": {"space": "cold concrete garage"}},
]


def test_a_room_is_picked_by_attaching_its_photo():
    """`/locations/<slug>/photo/<file>` is the URL the asset bank hands
    out, so the slug in the path IS the pick -- no new form field and no
    client-side flag that can go stale."""
    picked = shootgen.picked_locations(
        ["/locations/garage/photo/x.jpg?thumb=1"], LOCS)
    assert [loc["name"] for loc in picked] == ["Garage"]


def test_uploads_and_other_assets_pick_no_room():
    assert shootgen.picked_locations(
        ["/refs/abc123.jpg", "/characters/michael/photo/1.jpg", "/props/bike/photo/2.jpg"],
        LOCS) == []


def test_no_pick_means_the_scene_may_be_set_anywhere():
    """The un-pinned run is the NORMAL case now, not a degraded one --
    which is why it reads as permission rather than as a missing-input
    note."""
    prompt = shootgen.build_scenes_prompt("a bench with one glove",3, [])
    assert "{locations}" not in prompt
    assert "no room picked" in prompt
    assert "NOT limited to real rooms" in prompt


def test_a_picked_room_reads_as_a_lock():
    """Picking is deliberate, so it gets the location_variety_note(lock)
    treatment: lean into the space, don't manufacture variety away from
    it."""
    block = shootgen.format_scene_locations(LOCS[1:])
    assert "cold concrete garage" in block
    assert "picked for this run" in block
    assert "Front Hallway" not in block


def test_unpicked_rooms_never_reach_the_prompt(tmp_db, monkeypatch):
    """The regression this exists for: a room on file steering an idea
    that never asked for it."""
    preprod.add_location("Front Hallway", {"space": "narrow hallway"},
                         photo_count=2, dsn=tmp_db, account_id=None)
    monkeypatch.setattr(shootgen, "generate_with_retry",
                        lambda client, model, contents, **kw: '{"scenes": []}')
    captured = {}
    real_build = shootgen.build_scenes_prompt

    def spy(idea, count, locations, **kw):
        captured["locations"] = locations
        return real_build(idea, count, locations, **kw)

    monkeypatch.setattr(shootgen, "build_scenes_prompt", spy)
    shootgen.generate_scene_concepts("a glove on a bench", count=1,
                                     db_path=tmp_db, refs=["/refs/abc.jpg"])
    assert captured["locations"] == []


def test_a_picked_room_does_reach_the_prompt(tmp_db, monkeypatch):
    preprod.add_location("Garage", {"space": "cold concrete garage"},
                         photo_count=2, dsn=tmp_db, account_id=None)
    monkeypatch.setattr(shootgen, "generate_with_retry",
                        lambda client, model, contents, **kw: '{"scenes": []}')
    captured = {}
    real_build = shootgen.build_scenes_prompt

    def spy(idea, count, locations, **kw):
        captured["locations"] = locations
        return real_build(idea, count, locations, **kw)

    monkeypatch.setattr(shootgen, "build_scenes_prompt", spy)
    shootgen.generate_scene_concepts(
        "a glove on a bench", count=1, db_path=tmp_db,
        refs=["/locations/garage/photo/x.jpg"])
    assert [loc["name"] for loc in captured["locations"]] == ["Garage"]


def test_validation_still_knows_every_real_room(tmp_db, monkeypatch):
    """Validated against the whole catalogue, not the picks: naming a
    real space you were not handed is fine, naming one that does not
    exist is the thing worth flagging."""
    preprod.add_location("Garage", {"space": "cold concrete garage"},
                         photo_count=2, dsn=tmp_db, account_id=None)
    warnings = shootgen.validate_concept(
        {"shots": [{"n": 1, "type": "CHARACTER", "source": "CAMERA",
                    "cam": "BMPCC", "location": "Garage"}]},
        [loc["name"] for loc in preprod.list_locations(dsn=tmp_db, account_id=None)])
    assert not any("unknown location" in w for w in warnings)


# --- the pick chooses; the priced approve draws ------------------------------
# From 2026-09-08 the pick drew the scene's still. Since 2026-09-29 a still
# costs credits, and Mike's rule is an approve button before every spend of
# credits: the pick records the choice, the card quotes the stills
# (`keyframes`), and POST /concepts/{id}/keyframes draws them -- refused
# with "top up" unless the WHOLE strip fits the balance.

def a_drawn_scene(path, title="Already drawn"):
    return preprod.save_concept(
        {"title": title, "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "RUNWAY",
                    "desc": title, "prompt": "P",
                    "reference_image": "https://example.test/still.jpg"}]},
             prompt_template="T", dsn=path, account_id=None)


@pytest.fixture
def keyframes(monkeypatch):
    """Records every keyframe_scene call instead of making one."""
    from src import scene_chain
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("PHANTRA_KEYFRAME_ON_PICK", raising=False)
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())

    def fake(concept_id, shot_n=None, **kw):
        calls.append((concept_id, shot_n))
        return {"ok": True, "media_url": "https://example.test/k.jpg", "frames": []}

    monkeypatch.setattr(scene_chain, "keyframe_scene", fake)
    return calls


def _draw(cid):
    return client.post(f"/api/scenes/{cid}/keyframes")


def test_the_card_quotes_the_stills_and_the_approve_draws_them(tmp_db, keyframes):
    """Drawing keyframes is on the scene too, and asks for no pick: the
    Render card carries the quote and the approve draws them."""
    from src import nano_banana, pricing
    cid = a_scene(tmp_db, "Cold Open")
    card = client.get(f"/api/scenes/{cid}/render").json()["scene"]
    each = pricing.still_credits(nano_banana.MODEL)
    # a scene with no timed shots is priced for the most it can draw: one
    # still per moment of its move, and marked as a ceiling (BACKLOG #29)
    assert card["keyframes"] == {"stills": 2, "each": each, "credits": 2 * each,
                                 "up_to": True}
    assert keyframes == []                    # asking drew nothing
    res = _draw(cid)
    assert res.status_code == 200, res.text
    job = wait_for_job(res.json()["job_id"])
    assert job["status"] == "done", job.get("error")
    assert job["ref_id"] == cid
    assert keyframes == [(cid, 1)]
    # stills are not the render: the scene is not stamped by drawing them
    assert preprod.get_concept(cid, dsn=tmp_db, account_id=None)["picked"] is False


def test_the_old_keyframes_path_still_draws(tmp_db, keyframes):
    cid = a_scene(tmp_db, "Cold Open")
    res = client.post(f"/api/concepts/{cid}/keyframes")
    assert res.status_code == 200, res.text
    wait_for_job(res.json()["job_id"])
    assert keyframes == [(cid, 1)]


def test_a_scene_that_already_has_a_still_has_nothing_to_draw(tmp_db, keyframes):
    """Re-picking must not quietly buy a second image, and the Director
    canvas's own keyframe is the one a person chose."""
    cid = a_drawn_scene(tmp_db)
    res = _draw(cid)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "nothing_to_draw"
    assert keyframes == []


def test_a_legacy_multi_shot_concept_has_nothing_to_draw(tmp_db, keyframes):
    """Six stills off one tap is not what a draw means."""
    cid = preprod.save_concept(
        {"title": "old", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "prompt": "x"},
                   {"n": 2, "type": "BROLL", "source": "AI", "prompt": "y"}]}, dsn=tmp_db, account_id=None)
    assert _draw(cid).status_code == 409
    assert keyframes == []


def test_the_drawing_can_be_turned_off(tmp_db, keyframes, monkeypatch):
    monkeypatch.setenv("PHANTRA_KEYFRAME_ON_PICK", "0")
    cid = a_scene(tmp_db, "Cold Open")
    assert _draw(cid).status_code == 409
    assert keyframes == []


def test_no_key_is_a_503_not_a_500(tmp_db, keyframes, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    cid = a_scene(tmp_db, "Cold Open")
    assert _draw(cid).status_code == 503
    assert keyframes == []


def test_a_keyframe_that_fails_leaves_the_scene_picked(tmp_db, keyframes,
                                                       monkeypatch):
    from src import scene_chain
    monkeypatch.setattr(scene_chain, "keyframe_scene",
                        lambda *a, **k: {"ok": False, "error": "the image model said 503"})
    cid = a_scene(tmp_db, "Cold Open")
    _pick(tmp_db, cid)
    job = wait_for_job(_draw(cid).json()["job_id"])
    assert job["status"] == "failed"
    assert "503" in (job.get("error") or "")
    assert preprod.get_concept(cid, dsn=tmp_db, account_id=None)["picked"] is True
