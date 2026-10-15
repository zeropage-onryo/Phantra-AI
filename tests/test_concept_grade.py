"""
Surfacing the taste + performance judge in the UI (BACKLOG #5): scores are
stored on the concept and a grade button scores on demand. The LLM call is
mocked; storage, the route, and the ungraded-only batch run for real.
"""

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.main import app
from src import autonomy, db, entities, evalstore, preprod, winners

client = TestClient(app)


@pytest.fixture
def tmp_db(pg, monkeypatch):
    path = pg
    preprod.init(path)
    entities.init(path)
    autonomy.init(path)
    winners.init(path)
    # the Grade tab counts the golden set alongside the ungraded pool,
    # so rendering it needs evalstore's tables too
    evalstore.init(path)
    monkeypatch.setenv("DATABASE_URL", path)
    return path


def _concept(title="A concept", prompt="Handheld, 35mm, a garage at dawn"):
    return {"title": title, "hook": "h", "logline": "l",
            "shots": [{"n": 1, "type": "scene", "tool": "runway", "prompt": prompt}]}


def _rule_on(concept_id, verdict="approve", shot_n=1, text="the prompt as written"):
    """Your verdict on a concept's scene -- what moves it out of the queue.
    Records only; nothing is taught until the scoring pass."""
    return client.post(f"/concepts/{concept_id}/shots/{shot_n}/verdict",
                       data={"verdict": verdict, "text": text, "tool": "runway"},
                       follow_redirects=False)


def _fake_judge(monkeypatch, overall=8.0):
    """Swap the one billed call for a recorder of who got scored."""
    calls = []

    def fake(concept, **k):
        calls.append(concept["id"])
        return {"overall": overall, "taste_fit": overall, "performance": overall,
                "reasons": ["fake judge"], "graded": True}

    monkeypatch.setattr(app_main.taste_judge, "score_concept", fake)
    return calls


def _rag_up(monkeypatch, ok=True):
    """The RAG store, present or down. Ingest is best-effort by contract,
    so 'down' is a state the loop has to survive, not an error case.

    The double stamps `ingested` exactly as the real ingest_to_rag does --
    that flag is what the state machine reads, so a fake that skipped it
    would pass while the loop never retired anything.
    """
    def fake(entry_id, dsn=None, project=None):
        if not ok:
            return {"ok": False, "error": "store unavailable"}
        with app_main.db.connect(dsn) as conn:
            conn.execute("UPDATE winning_prompts SET ingested = 1 WHERE id = %s",
                         (entry_id,))
        return {"ok": True, "chunks": 1}

    monkeypatch.setattr(app_main.winners, "ingest_to_rag", fake)


def test_save_judge_score_persists_on_the_concept(tmp_db):
    cid = preprod.save_concept(_concept(), dsn=tmp_db, account_id=None)
    preprod.save_judge_score(
        cid, {"overall": 8, "taste_fit": 9, "performance": 7, "reasons": ["r1", "r2"]},
        dsn=tmp_db, account_id=None)
    c = preprod.get_concept(cid, dsn=tmp_db, account_id=None)
    assert c["judge_overall"] == 8 and c["judge_taste"] == 9 and c["judge_perf"] == 7
    assert "r1" in c["judge_reason"]


def test_a_passed_concept_still_counts_against_pick_rate(tmp_db):
    """The whole reason archiving beats deleting: the row keeps counting
    as generated-and-not-picked, so the rate stays falsifiable."""
    cid = preprod.save_concept(_concept("passed on"), dsn=tmp_db,
                               account_id=None)
    before = preprod.pick_rate(dsn=tmp_db, account_id=None)["generated"]
    client.post(f"/concepts/{cid}/pass", data={"reason": "off-brand"},
                follow_redirects=False)
    assert preprod.pick_rate(dsn=tmp_db, account_id=None)["generated"] == before


def test_discard_all_clears_the_accounts_slate(tmp_db):
    """Every row carries one label since 2026-10-13, so the dev console's
    reset clears the account's scenes whatever brand cookie is set."""
    a = preprod.save_concept(_concept("one"), dsn=tmp_db, account_id=None)
    z = preprod.save_concept(_concept("two"), dsn=tmp_db, account_id=None)
    client.cookies.set("phantra_account", "something")
    r = client.post("/concepts/discard-all", follow_redirects=False)
    client.cookies.clear()
    assert r.status_code == 303
    assert preprod.get_concept(a, dsn=tmp_db, account_id=None) is None
    assert preprod.get_concept(z, dsn=tmp_db, account_id=None) is None


def test_a_brand_in_the_query_narrows_nothing(tmp_db, monkeypatch):
    """2026-10-13: `?brand=` is accepted and ignored; the list is the
    account's scenes, whatever label a row carries."""
    from app import auth
    stub = {"id": 1, "email": "t@example.com", "display_name": "T"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)
    preprod.save_concept(_concept("AH ONLY ONE"), dsn=tmp_db, account_id=None)
    preprod.save_concept(_concept("ZP ONLY ONE"), dsn=tmp_db, account_id=None)
    titles = [c["title"] for c in
              client.get("/api/pipeline/concepts?brand=zeropage").json()["items"]]
    assert "ZP ONLY ONE" in titles
    assert "AH ONLY ONE" in titles


def test_posted_outcomes_reads_the_latest_snapshot(tmp_db):
    """The join that closes the audience loop (2026-08-31).

    `videos.idea_id` pointed at the LEGACY pitch pipeline's table and was
    never once written, so a posted video could not be traced back to the
    concept that made it — whatever the audience taught was structurally
    unable to reach the generator.

    `metrics` is a growth curve on purpose (db.py: "a video has 8k views
    on day one and 40k on day thirty"), so the join must read the LATEST
    snapshot per video. Averaging would throw the curve away.
    """
    cid = preprod.save_concept(_concept("posted"), dsn=tmp_db,
                               account_id=None)
    assert preprod.posted_outcomes(dsn=tmp_db, account_id=None) == []

    with db.connect(tmp_db) as conn:
        conn.execute("INSERT INTO videos (concept_id, title, platform, posted_at) "
                     "VALUES (%s,%s,%s,%s)", (cid, "posted", "instagram", "2026-09-01"))
        vid = conn.execute("SELECT id FROM videos").fetchone()[0]
        for day, shares in (("2026-09-01", 10), ("2026-09-08", 170)):
            conn.execute("INSERT INTO metrics (video_id, captured_at, views, likes, "
                         "comments, saves, shares) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                         (vid, day, 9000, 800, 40, 150, shares))

    [row] = preprod.posted_outcomes(dsn=tmp_db, account_id=None)
    assert row["concept_id"] == cid
    assert row["shares"] == 170, "read the first snapshot, not the latest"


# --- the ungraded queue, listed --------------------------------------------
# The draw is random. A count alone ("12 waiting") says nothing about what
# is in the pool, so the Grade tab lists it (2026-09-02). Same filter the
# draw uses -- judge_overall IS NULL -- so the list and the count on the
# button can never disagree.

# --- the loop: queue -> your verdict -> the scoring pass -> gone ------------
# Mike's design, 2026-09-02. A concept has three states and is in exactly
# one: waiting on you, waiting on the pass, or retired into RAG. The tests
# below are the state machine, including the one failure it must not have
# (a concept that vanishes having taught nothing).
