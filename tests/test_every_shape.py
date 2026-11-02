"""
Every shape (2026-11-02, docs/tasks/task-every-shape.md): one click makes the
shapes an ad runs in from one finished clip or still, each a free reformat.

What is guarded:
- the plan: a shape the source already is is not made, a near shape is
  cropped and a far one padded, an unknown shape or somebody else's item is
  refused before anything is made
- with real ffmpeg: the missing shapes come back at their sizes, free, the
  source untouched, and a second click hands back what was made, not again
- the route checks before it starts a job, and the job lists every shape
- an ad that ran on a shape counts toward its source's scene (its variant)
"""
import hashlib
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.cut import quick
from tests.test_connector_library import FPS, needs_ffmpeg
from tests.test_connector_library import wall as _wall  # noqa: F401 -- registers the `wall` fixture

pytestmark = needs_ffmpeg


@pytest.fixture
def wall(_wall):  # noqa: F811 -- the imported fixture, by its own name
    """A clip (160x284, so already 9:16) and a still on a real database: the
    connector-library tests' own fixture."""
    return _wall


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_plan_skips_the_shape_it_is_crops_near_and_pads_far(wall):
    plan = quick.plan_every_shape(wall["refs"]["clip"], account_id=wall["account_id"],
                                  dsn=wall["dsn"])
    got = {x["aspect"]: (x["do"], x.get("fit")) for x in plan["shapes"]}
    # the clip is 160x284: already 9:16; 1:1 keeps more than half (crop); 16:9 would not (pad)
    assert got == {"9:16": ("same", None), "1:1": ("make", "crop"), "16:9": ("make", "pad")}


@pytest.mark.parametrize("shapes", [["3:2"], ["  "], ["9:16", "21:9"]])
def test_an_unknown_shape_is_refused(wall, shapes):
    with pytest.raises(quick.QuickRefused, match="shapes are"):
        quick.plan_every_shape(wall["refs"]["clip"], shapes, account_id=wall["account_id"],
                               dsn=wall["dsn"])


def test_somebody_elses_item_is_refused(wall):
    with pytest.raises(quick.QuickRefused, match="no render"):
        quick.plan_every_shape(wall["refs"]["clip"], account_id=wall["account_id"] + 999,
                               dsn=wall["dsn"])


def test_the_missing_shapes_are_made_free_and_a_second_click_makes_nothing(wall):
    from src import ledger, render_assets
    from src.cut import sources
    before = _sha(wall["files"]["clip"])
    plan = quick.plan_every_shape(wall["refs"]["clip"], account_id=wall["account_id"],
                                  dsn=wall["dsn"])
    told = []
    out = quick.every_shape(plan, account_id=wall["account_id"], dsn=wall["dsn"],
                            on_shape=lambda i, n, a: told.append((i, n, a)))
    by = {x["aspect"]: x for x in out}
    assert by["9:16"]["status"] == "same" and by["9:16"]["ref"] == wall["refs"]["clip"]
    assert told == [(0, 2, "1:1"), (1, 2, "16:9")]
    for aspect in ("1:1", "16:9"):
        assert by[aspect]["status"] == "made", by[aspect]
        row = render_assets.get(by[aspect]["asset_id"], wall["dsn"], account_id=wall["account_id"])
        probe = sources.probe(Path(row["output_path"]), FPS)
        assert [probe["width"], probe["height"]] == list(quick.SIZES[aspect])
        assert row["metadata"]["source_ref"] == wall["refs"]["clip"]
    assert by["1:1"]["fit"] == "crop" and by["16:9"]["fit"] == "pad"
    assert _sha(wall["files"]["clip"]) == before
    assert ledger.entries(wall["account_id"], wall["dsn"]) == []
    # again: nothing new, the two made are handed back
    again = quick.plan_every_shape(wall["refs"]["clip"], account_id=wall["account_id"],
                                   dsn=wall["dsn"])
    assert [x["do"] for x in again["shapes"]] == ["same", "have", "have"]
    second = quick.every_shape(again, account_id=wall["account_id"], dsn=wall["dsn"])
    assert {x["aspect"]: x.get("asset_id") for x in second if x["status"] == "have"} == {
        "1:1": by["1:1"]["asset_id"], "16:9": by["16:9"]["asset_id"]}


def test_a_still_stays_a_still_in_every_shape(wall):
    from src import render_assets
    plan = quick.plan_every_shape(wall["refs"]["still"], account_id=wall["account_id"],
                                  dsn=wall["dsn"])
    out = quick.every_shape(plan, account_id=wall["account_id"], dsn=wall["dsn"])
    made = [x for x in out if x["status"] == "made"]
    assert made
    for x in made:
        row = render_assets.get(x["asset_id"], wall["dsn"], account_id=wall["account_id"])
        assert row["media_kind"] == "image"


def test_an_ad_on_a_shape_counts_toward_its_source_scene(wall):
    from src import ad_results, db
    pg, acct = wall["dsn"], wall["account_id"]
    clip_id = int(wall["refs"]["clip"].split(":")[1])
    with db.connect(pg) as conn:
        conn.execute("UPDATE generated_assets SET concept_id = 55 WHERE id = %s", (clip_id,))
    plan = quick.plan_every_shape(wall["refs"]["clip"], ["1:1"], account_id=acct, dsn=pg)
    (square,) = quick.every_shape(plan, account_id=acct, dsn=pg)
    ad_results.init(pg)
    ad_results.record_variant(55, account_id=acct, group_id="g1", label="Hook: the spill", dsn=pg)
    csv = ("Ad name,Amount spent (USD),Results\n"
           f"Square PH{square['asset_id']},50,10\n").encode()
    ad_results.import_csv(csv, account_id=acct, dsn=pg)
    (ad,) = ad_results.summary(account_id=acct, dsn=pg)["ads"]
    assert ad["asset_id"] == square["asset_id"] and ad["concept_id"] == 55
    assert ad["variant"] == "Hook: the spill"


# --- the route --------------------------------------------------------------------

@pytest.fixture
def signed_in(wall, monkeypatch):
    from app import auth
    from app.main import app
    monkeypatch.setenv("DATABASE_URL", wall["dsn"])
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "m@example.com"})
    app.dependency_overrides[auth.current_account_id] = lambda: wall["account_id"]
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)


def test_the_route_checks_first_and_its_job_lists_every_shape(signed_in, wall):
    client = signed_in
    bad = client.post("/api/every-shape", json={"source": "https://x.test/a.mp4"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "bad_edit"
    r = client.post("/api/every-shape", json={"source": wall["refs"]["clip"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["credits"] == 0 and body["making"] == ["1:1", "16:9"]
    deadline = time.time() + 60
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{body['job_id']}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert job["status"] == "done", job
    assert [(x["aspect"], x["status"]) for x in job["shapes"]] == [
        ("9:16", "same"), ("1:1", "made"), ("16:9", "made")]
    assert all("error" not in x for x in job["shapes"])
